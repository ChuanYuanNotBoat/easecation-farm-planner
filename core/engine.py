import math
import copy

class FarmEngine:

    def __init__(self, crops, config):
        self.config = config
        self.current_level = config.get("current_level", 0)  # 默认0级

        # 根据解锁等级过滤作物
        self.crops = []
        for c in crops:
            unlock_level = c.get("unlock_level", 0)  # 默认为0
            if unlock_level <= self.current_level:
                self.crops.append(c)

        self.crop_dict = {c["name"]: c for c in self.crops}
        self._prepare_metrics()

    def _prepare_metrics(self):
        for c in self.crops:
            c["profit_per_plot"] = (
                c["expected_yield"] * c["sell_price"] - c["seed_cost"]
            )
            exp_per_unit = c.get("exp_per_unit") or 0
            c["exp_per_plot"] = c["expected_yield"] * exp_per_unit
            c["profit_per_hour"] = c["profit_per_plot"] / c["growth_time"]
            c["exp_per_hour"] = (
                c["exp_per_plot"] / c["growth_time"] if c["growth_time"] > 0 else 0
            )

    def _score(self, crop, weights):
        complexity_penalty = (1 / crop["growth_time"]) * weights["complexity"]
        return (
            weights["profit"] * crop["profit_per_hour"]
            + weights["exp"] * crop["exp_per_hour"]
            - complexity_penalty
        )

    def _sell_to_raise_cash(self, state, needed, crop_scores_asc):
        """卖出库存以筹集所需现金，返回新state、实际筹集金额、销售记录"""
        state = copy.deepcopy(state)
        cash = state["cash"]
        inventory = state["inventory_crops"]
        limit = state["sell_limit_remaining"]
        discount = state["reduced_sell_multiplier"]
        raised = 0
        sales = []

        for crop_name in crop_scores_asc:
            if needed - raised <= 0:
                break
            qty = inventory.get(crop_name, 0)
            if qty == 0:
                continue
            crop = self.crop_dict.get(crop_name)
            if not crop:
                continue
            price = crop["sell_price"]

            remaining_need = needed - raised

            # 原价额度部分
            sell_in_limit = min(qty, limit)
            potential_normal = sell_in_limit * price
            if potential_normal >= remaining_need:
                sell_q = math.ceil(remaining_need / price)
                sell_q = min(sell_q, sell_in_limit)
                income = sell_q * price
                raised += income
                limit -= sell_q
                inventory[crop_name] -= sell_q
                sales.append({"crop": crop_name, "qty": sell_q})
                break
            else:
                if sell_in_limit > 0:
                    raised += potential_normal
                    limit -= sell_in_limit
                    inventory[crop_name] -= sell_in_limit
                    sales.append({"crop": crop_name, "qty": sell_in_limit})
                    qty -= sell_in_limit
                    remaining_need -= potential_normal

                # 折扣部分
                if qty > 0 and remaining_need > 0:
                    discounted_price = price * discount
                    sell_q = math.ceil(remaining_need / discounted_price)
                    sell_q = min(sell_q, qty)
                    income = sell_q * discounted_price
                    raised += income
                    inventory[crop_name] -= sell_q
                    sales.append({"crop": crop_name, "qty": sell_q})
                    # 折扣销售不影响limit
                    if income >= remaining_need:
                        break

        state["cash"] = cash + raised
        state["inventory_crops"] = inventory
        state["sell_limit_remaining"] = limit
        return state, raised, sales

    def _sell_all(self, inventory, sell_limit, discount):
        """模拟卖出指定库存中的所有作物（按价格降序），返回总收入"""
        total_income = 0
        remaining_limit = sell_limit
        # 按价格从高到低排序，以最大化收入
        sorted_crops = sorted(
            inventory.keys(),
            key=lambda c: self.crop_dict[c]["sell_price"],
            reverse=True
        )
        for crop_name in sorted_crops:
            qty = inventory[crop_name]
            if qty <= 0:
                continue
            crop = self.crop_dict[crop_name]
            price = crop["sell_price"]
            # 原价部分（消耗额度）
            sell_in_limit = min(qty, remaining_limit)
            if sell_in_limit > 0:
                total_income += sell_in_limit * price
                remaining_limit -= sell_in_limit
                qty -= sell_in_limit
            # 折扣部分（不消耗额度）
            if qty > 0:
                total_income += qty * price * discount
        return total_income

    def analyze(self, state):
        preset_name = self.config["active_preset"]
        weights = self.config["objective_presets"][preset_name]

        # 获取时间窗口（小时）
        online_duration = state.get("online_duration", 6)    # 默认6小时
        sleep_duration = state.get("sleep_duration", 8)      # 默认8小时
        total_time = online_duration + sleep_duration

        sim_state = copy.deepcopy(state)
        land_total = self.config["land_units"]
        remaining_land = land_total

        # 过滤作物：必须在可操作时间或睡眠时间内能收获
        viable_crops = []
        for crop in self.crops:
            gt = crop["growth_time"]
            # 只要能在任一时间段内收获即可
            if gt <= online_duration or gt <= sleep_duration:
                viable_crops.append(crop)
            # 否则舍弃（无法在任一阶段内收获）

        # 计算所有可行作物的评分并排序（高→低）
        scored_crops = sorted(
            viable_crops,
            key=lambda c: self._score(c, weights),
            reverse=True
        )

        # 计算库存作物的当前评分（仅考虑可行且库存>0的作物）
        inventory_scores = []
        for crop_name in sim_state["inventory_crops"]:
            if crop_name in self.crop_dict and sim_state["inventory_crops"][crop_name] > 0:
                crop = self.crop_dict[crop_name]
                # 检查库存作物是否在当前可行列表中（即能否收获）
                if crop in viable_crops:
                    score = self._score(crop, weights)
                    inventory_scores.append((crop_name, score))
        inventory_scores.sort(key=lambda x: x[1])  # 升序，低分优先卖
        sell_priority = [name for name, _ in inventory_scores]

        allocation = {}
        purchases = []
        all_sales = []

        for crop in scored_crops:
            if remaining_land <= 0:
                break
            name = crop["name"]
            seed_cost = crop["seed_cost"]
            max_afford = int(sim_state["cash"] // seed_cost) if seed_cost > 0 else remaining_land

            if max_afford == 0 and remaining_land > 0:
                needed = seed_cost
                sim_state, raised, sales = self._sell_to_raise_cash(sim_state, needed, sell_priority)
                all_sales.extend(sales)
                if raised >= needed:
                    max_afford = int(sim_state["cash"] // seed_cost)
                else:
                    continue

            plant_qty = min(remaining_land, max_afford)
            if plant_qty > 0:
                allocation[name] = plant_qty
                sim_state["cash"] -= plant_qty * seed_cost
                remaining_land -= plant_qty
                purchases.append({"crop": name, "seeds": plant_qty})

        # 记录第一轮实际种植地块数（用于计算闲置）
        first_round_planted = sum(allocation.values())

        # ----- 收获预测：考虑时间窗口内可种植的轮次 -----
        harvest = {}
        harvest_value_full = {}
        harvest_exp = {}
        harvest_rounds = {}   # 记录每种作物在总时间内的可种植轮数

        for crop_name, plant_qty in allocation.items():
            crop = self.crop_dict[crop_name]
            gt = crop["growth_time"]
            # 计算轮次
            rounds = 0
            if gt <= online_duration:
                rounds += online_duration // gt
            if gt <= sleep_duration:
                rounds += 1   # 睡眠期间只能种一轮
            # 如果两个条件都满足，则总轮数为 online_duration//gt + 1
            harvest_rounds[crop_name] = rounds

            per_plot_yield = crop["expected_yield"]
            total_yield = plant_qty * per_plot_yield * rounds
            harvest[crop_name] = total_yield
            harvest_value_full[crop_name] = total_yield * crop["sell_price"]
            exp = total_yield * (crop.get("exp_per_unit") or 0)
            harvest_exp[crop_name] = exp

        # 计算全部卖出新收获（考虑当前剩余额度和折扣）的总收入
        harvest_value_after_limit = self._sell_all(
            harvest,
            sim_state["sell_limit_remaining"],
            sim_state["reduced_sell_multiplier"]
        )

        # ----- 新增统计：种子总成本、闲置土地、浪费时间 -----
        total_seed_cost = 0
        total_occupied_hours = 0
        for crop_name, plant_qty in allocation.items():
            crop = self.crop_dict[crop_name]
            rounds = harvest_rounds.get(crop_name, 0)
            seed_cost_per_round = plant_qty * crop["seed_cost"]
            total_seed_cost += seed_cost_per_round * rounds
            total_occupied_hours += plant_qty * crop["growth_time"] * rounds

        idle_land = land_total - first_round_planted
        wasted_time_hours = land_total * total_time - total_occupied_hours
        if wasted_time_hours < 0:
            wasted_time_hours = 0  # 防止计算误差
        # ----- 结束新增 -----

        return {
            "preset": preset_name,
            "allocation": allocation,
            "sales": all_sales,
            "purchases": purchases,
            "final_cash": sim_state["cash"],
            "remaining_inventory": sim_state["inventory_crops"],
            "sell_limit_remaining": sim_state["sell_limit_remaining"],
            "harvest": harvest,
            "harvest_value_full": harvest_value_full,
            "harvest_value_after_limit": harvest_value_after_limit,
            "harvest_exp": harvest_exp,
            "harvest_rounds": harvest_rounds,
            "total_seed_cost": total_seed_cost,
            "idle_land": idle_land,
            "wasted_time_hours": wasted_time_hours,
        }