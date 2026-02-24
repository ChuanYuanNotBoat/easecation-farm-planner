#!/usr/bin/env python3
"""
农场策略引擎交互式命令行工具（中文版）
支持实时修改配置、查看作物、运行分析，并自动保存修改。
所有提示信息均已中文化。
"""

import json
import shutil
import cmd
import sys
import os
from colorama import init, Fore, Style
from tabulate import tabulate
from core.engine import FarmEngine

# 初始化 colorama（Windows 兼容）
init(autoreset=True)

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CROPS_FILE = os.path.join(CONFIG_DIR, "crops.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")


class OutputFormatter:
    """封装所有输出格式，便于统一修改样式"""

    def __init__(self):
        self.term_width = shutil.get_terminal_size().columns

    def title(self, text):
        """显示标题（带上下分割线）"""
        print(f"{Fore.YELLOW}{'=' * self.term_width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")

    def separator(self):
        """显示分割线"""
        print(f"{Fore.YELLOW}{'=' * self.term_width}{Style.RESET_ALL}")

    def info(self, msg, color=Fore.GREEN, indent=0):
        """显示普通信息，可指定颜色和缩进"""
        print(f"{color}{' ' * indent}{msg}{Style.RESET_ALL}")

    def key_value(self, key, value, indent=2):
        """显示键值对"""
        print(f"{' ' * indent}{Fore.GREEN}{key}:{Style.RESET_ALL} {value}")

    def warning(self, msg):
        """显示警告信息（黄色）"""
        print(f"{Fore.YELLOW}{msg}{Style.RESET_ALL}")

    def error(self, msg):
        """显示错误信息（红色）"""
        print(f"{Fore.RED}{msg}{Style.RESET_ALL}")


class FarmCLI(cmd.Cmd):
    intro = (
        f"{Fore.GREEN}欢迎使用农场策略引擎交互式命令行！\n"
        f"输入 {Fore.YELLOW}help{Fore.GREEN} 或 {Fore.YELLOW}?{Fore.GREEN} 查看可用命令。{Style.RESET_ALL}"
    )
    prompt = f"{Fore.CYAN}farm> {Style.RESET_ALL}"

    def __init__(self):
        super().__init__()
        self.out = OutputFormatter()
        self.load_data()

    def load_data(self):
        """从文件加载数据，并重建引擎"""
        with open(CROPS_FILE, 'r', encoding='utf-8') as f:
            self.crops = json.load(f)
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            self.state = json.load(f)
        # 创建引擎（自动过滤作物）
        self.engine = FarmEngine(self.crops, self.config)

    def save_config(self):
        """保存当前配置到文件"""
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        self.out.info("配置已保存。")

    def save_state(self):
        """保存当前状态到文件，自动清理库存中数量为0的项"""
        # 清理库存中数量为0的作物
        if 'inventory_crops' in self.state:
            self.state['inventory_crops'] = {k: v for k, v in self.state['inventory_crops'].items() if v != 0}
        # 清理道具中数量为0的项（假设值是数字）
        if 'inventory_items' in self.state and isinstance(self.state['inventory_items'], dict):
            self.state['inventory_items'] = {k: v for k, v in self.state['inventory_items'].items() if v != 0}
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=4, ensure_ascii=False)
        self.out.info("状态已保存。")

    def save_all(self):
        self.save_config()
        self.save_state()
        # 重新加载引擎（因为配置可能变化）
        self.engine = FarmEngine(self.crops, self.config)

    # ---------- 自定义帮助系统（全中文）----------

    # 帮助信息集中管理
    COMMAND_HELP = {
        "show": {
            "brief": "显示当前配置、状态或作物列表。用法: show [config|state|crops]",
            "detail": """\
命令: show [config|state|crops]
  显示当前配置、状态或已解锁作物列表。
  示例:
    show config   - 显示配置详情
    show state    - 显示当前状态
    show crops    - 列出已解锁作物及其属性"""
        },
        "set": {
            "brief": "修改配置或状态。用法: set [config|state] <键> <值>",
            "detail": """\
命令: set [config|state] <键> <值>
  修改配置或状态项。修改后自动保存。
  可用配置键:
    - land_units : 土地数量
    - current_level : 当前等级
    - active_preset : 当前使用的预设名称
  注意：objective_presets 为复杂对象，不可直接修改，请编辑 config.json 文件调整内部权重。

  可用状态键:
    - cash : 现金
    - sell_limit_remaining : 剩余原价额度
    - reduced_sell_multiplier : 折扣系数
    - inventory_crops : 库存作物（整体替换）
    - inventory_items : 其他道具
    - online_duration : 可操作时间
    - sleep_duration : 非操作时间
    - inventory.<作物名> : 修改指定作物库存（例如 inventory.wheat）

  示例:
    set config land_units 80
    set config current_level 6
    set config active_preset money
    set state cash 1500
    set state inventory.wheat 50
    set state sell_limit_remaining 3000"""
        },
        "analyze": {
            "brief": "运行分析，显示推荐方案",
            "detail": """\
命令: analyze
  运行策略分析，根据当前配置和状态生成推荐方案。
  输出包括：种植分配、建议卖出、需购买种子、最终现金等。"""
        },
        "save": {
            "brief": "手动保存当前配置和状态到文件",
            "detail": """\
命令: save
  手动将当前内存中的配置和状态保存到文件。
  注意：set 命令会自动保存，通常无需手动执行。"""
        },
        "reload": {
            "brief": "重新从文件加载配置和状态",
            "detail": """\
命令: reload
  从文件重新加载配置和状态，放弃未保存的修改。"""
        },
        "exit": {
            "brief": "退出交互式命令行",
            "detail": """\
命令: exit / quit / q
  退出交互式命令行。"""
        },
        "help": {
            "brief": "显示本帮助信息",
            "detail": """\
命令: help / h
  显示本帮助信息。"""
        }
    }

    def do_help(self, arg):
        """显示帮助信息。输入 help <命令> 查看详细帮助。"""
        if arg:
            self._command_help(arg.strip().lower())
        else:
            self._general_help()

    def _general_help(self):
        """显示所有可用命令的简要说明（中文）"""
        self.out.separator()
        self.out.info("可用命令:", color=Fore.CYAN)
        print()
        for cmd_name, info in self.COMMAND_HELP.items():
            if cmd_name in ("exit", "help"):
                continue
            print(f"  {Fore.GREEN}{cmd_name:<16}{Style.RESET_ALL} - {info['brief']}")
        print(f"  {Fore.GREEN}exit / quit / q{Style.RESET_ALL}   - {self.COMMAND_HELP['exit']['brief']}")
        print(f"  {Fore.GREEN}help / h{Style.RESET_ALL}          - {self.COMMAND_HELP['help']['brief']}")
        print(f"\n提示：输入 {Fore.YELLOW}help <命令>{Style.RESET_ALL} 查看详细用法。")
        self.out.separator()

    def _command_help(self, command):
        """显示特定命令的详细帮助（中文）"""
        # 处理别名
        if command in ("quit", "q"):
            command = "exit"
        elif command in ("h",):
            command = "help"
        elif command in ("sh",):
            command = "show"
        elif command in ("s",):
            command = "set"
        elif command in ("a",):
            command = "analyze"
        elif command in ("sa",):
            command = "save"
        elif command in ("r",):
            command = "reload"

        if command in self.COMMAND_HELP:
            print(f"\n{Fore.CYAN}{self.COMMAND_HELP[command]['detail']}{Style.RESET_ALL}\n")
        else:
            self.out.error(f"未知命令: {command}")

    def do_h(self, arg):
        """帮助命令的别名（同 help）"""
        return self.do_help(arg)

    # ---------- 显示命令 ----------

    def do_show(self, arg):
        """显示当前配置、状态或作物列表。用法: show [config|state|crops]"""
        if not arg:
            self.out.error("请指定要显示的内容: config, state 或 crops")
            return
        arg = arg.strip().lower()
        if arg == "config":
            self._show_config()
        elif arg == "state":
            self._show_state()
        elif arg == "crops":
            self._show_crops()
        else:
            self.out.error(f"未知的显示对象: {arg}")

    def _show_config(self):
        """以友好格式显示配置，增加复杂度解释"""
        self.out.title("当前配置")
        self.out.key_value("土地数量", self.config['land_units'])
        self.out.key_value("当前等级", self.config.get('current_level', 0))
        self.out.key_value("活动预设", self.config['active_preset'])
        self.out.info("预设权重 (利润/经验/操作复杂度):", indent=2)
        for name, weights in self.config['objective_presets'].items():
            self.out.info(f"    {name}: 利润={weights['profit']}, 经验={weights['exp']}, 操作复杂度={weights['complexity']}")
        self.out.warning("\n【操作复杂度说明】")
        self.out.info("  操作复杂度 = 1 / 生长时间 × 复杂度权重")
        self.out.info("  生长时间越短的作物，操作频率越高，复杂度惩罚越大。")
        self.out.info("  调高「操作复杂度」权重会使引擎更倾向于选择生长时间长的作物（懒人模式）。")
        self.out.separator()

    def _show_state(self):
        """显示当前状态"""
        self.out.title("当前状态")
        self.out.key_value("现金", f"{self.state['cash']} FC")
        self.out.key_value("剩余原价额度", f"{self.state['sell_limit_remaining']} FC")
        self.out.key_value("折扣系数", self.state['reduced_sell_multiplier'])
        self.out.info("库存作物:")
        # 只显示数量大于0的作物
        for crop, qty in self.state['inventory_crops'].items():
            if qty > 0:
                self.out.info(f"    {crop}: {qty}")
        self.out.key_value("其他道具", self.state.get('inventory_items', {}))
        self.out.key_value("可操作时间", f"{self.state.get('online_duration', 0)} 小时")
        self.out.key_value("非操作时间", f"{self.state.get('sleep_duration', 0)} 小时")
        self.out.separator()

    def _show_crops(self):
        """列出所有已解锁作物及其属性（使用 tabulate 美化）"""
        self.out.title(f"已解锁作物 (当前等级 {self.config.get('current_level', 0)})")
        headers = ["名称", "生长(h)", "产量", "售价", "种子价", "利润/块", "利润/h", "解锁等级"]
        table = []
        for crop in self.crops:
            unlock = crop.get('unlock_level', 0)
            if unlock > self.config.get('current_level', 0):
                continue
            name = crop['name']
            growth = crop['growth_time']
            yield_ = crop['expected_yield']
            price = crop['sell_price']
            seed = crop['seed_cost']
            profit_per_plot = yield_ * price - seed
            profit_per_hour = profit_per_plot / growth if growth > 0 else 0
            table.append([
                name, f"{growth:.1f}", f"{yield_:.1f}", price, seed,
                f"{profit_per_plot:.1f}", f"{profit_per_hour:.2f}", unlock
            ])
        print(tabulate(table, headers=headers, tablefmt="grid"))
        self.out.separator()

    # ---------- 设置命令 ----------

    def do_set(self, arg):
        """修改配置或状态。用法: set [config|state] <键> <值>"""
        parts = arg.split()
        if len(parts) < 1:
            self.out.error("用法: set [config|state] <键> <值>")
            return
        if len(parts) < 3:
            # 参数不足，提示可用键
            target = parts[0].lower() if parts else ""
            if target == "config":
                self.out.warning("可用的配置键:")
                self._list_config_keys()
            elif target == "state":
                self.out.warning("可用的状态键:")
                self._list_state_keys()
            else:
                self.out.error("用法: set [config|state] <键> <值>")
                self._list_config_keys()
                self._list_state_keys()
            return

        target = parts[0].lower()
        key = parts[1]
        value = ' '.join(parts[2:])

        if target == "config":
            self._set_config(key, value)
        elif target == "state":
            self._set_state(key, value)
        else:
            self.out.error(f"未知目标: {target}，应为 config 或 state")

    def _list_config_keys(self):
        """列出配置文件中所有可修改的顶级键，带中文说明"""
        key_descriptions = {
            "land_units": "土地数量",
            "current_level": "当前等级",
            "objective_presets": "策略预设（包含利润/经验/复杂度权重）- 不可直接修改，请编辑 config.json",
            "active_preset": "当前使用的预设名称",
        }
        for key in self.config.keys():
            desc = key_descriptions.get(key, "无说明")
            self.out.info(f"    - {key} : {desc}")

    def _list_state_keys(self):
        """列出状态文件中所有可修改的顶级键，带中文说明，包括库存子键"""
        key_descriptions = {
            "cash": "现金",
            "sell_limit_remaining": "剩余原价额度",
            "reduced_sell_multiplier": "折扣系数",
            "inventory_crops": "库存作物（整体替换）",
            "inventory_items": "其他道具",
            "online_duration": "可操作时间",
            "sleep_duration": "非操作时间"
        }
        for key in self.state.keys():
            if key != "inventory_crops":
                desc = key_descriptions.get(key, "无说明")
                self.out.info(f"    - {key} : {desc}")
        # 库存作物特殊提示
        self.out.info("    - inventory.<作物名> : 修改指定作物库存（例如 inventory.wheat）")

    def _set_config(self, key, value):
        """修改配置项"""
        # 禁止直接修改 objective_presets
        if key == "objective_presets":
            self.out.error("objective_presets 是复杂对象，无法直接修改。请编辑 config.json 文件调整内部权重。")
            return

        # 对 active_preset 进行合法性校验
        if key == "active_preset":
            if value not in self.config["objective_presets"]:
                self.out.error(f"预设 '{value}' 不存在，可选: {', '.join(self.config['objective_presets'].keys())}")
                return

        try:
            if '.' in value:
                val = float(value)
            else:
                val = int(value)
        except ValueError:
            val = value  # 保持字符串

        if key in self.config:
            old = self.config[key]
            self.config[key] = val
            self.out.info(f"配置项 {key} 已从 {old} 修改为 {self.config[key]}")
            self.save_config()
            # 重建引擎
            self.engine = FarmEngine(self.crops, self.config)
        else:
            self.out.error(f"未知配置键: {key}")
            self._list_config_keys()

    def _set_state(self, key, value):
        """修改状态项"""
        try:
            if '.' in value:
                val = float(value)
            else:
                val = int(value)
        except ValueError:
            val = value

        if key.startswith("inventory."):
            parts = key.split('.')
            if len(parts) == 2 and parts[0] == "inventory":
                crop = parts[1]
                if crop not in self.state['inventory_crops']:
                    self.state['inventory_crops'][crop] = 0
                old = self.state['inventory_crops'][crop]
                self.state['inventory_crops'][crop] = int(val)
                self.out.info(f"库存作物 {crop} 从 {old} 修改为 {val}")
                self.save_state()
            else:
                self.out.error("格式错误，应为 inventory.<作物名>")
        elif key in self.state:
            old = self.state[key]
            self.state[key] = val
            self.out.info(f"状态项 {key} 已从 {old} 修改为 {self.state[key]}")
            self.save_state()
        else:
            self.out.error(f"未知状态键: {key}")
            self._list_state_keys()

    # ---------- 分析命令 ----------

    def do_analyze(self, arg):
        """运行分析，显示推荐方案"""
        self.engine = FarmEngine(self.crops, self.config)
        result = self.engine.analyze(self.state)
        self._print_result(result)
        
    def _print_result(self, result):
        """格式化输出分析结果（使用 tabulate 美化）"""
        self.out.title(f"推荐方案 (预设: {result['preset']})")

        # 种植分配
        self.out.info("种植分配:", color=Fore.GREEN)
        if result['allocation']:
            alloc_table = [[crop, qty] for crop, qty in result['allocation'].items()]
            print(tabulate(alloc_table, headers=["作物", "数量"], tablefmt="plain"))
        else:
            self.out.info("  无种植计划")

        # 销售建议
        if result['sales']:
            self.out.warning("建议卖出:")
            sale_table = [[s['crop'], s['qty']] for s in result['sales']]
            print(tabulate(sale_table, headers=["作物", "数量"], tablefmt="plain"))
        else:
            self.out.info("无需卖出库存")

        # 购买种子
        if result['purchases']:
            self.out.info("需购买种子:", color=Fore.MAGENTA)
            pur_table = [[p['crop'], p['seeds']] for p in result['purchases']]
            print(tabulate(pur_table, headers=["作物", "种子数"], tablefmt="plain"))

        # ----- 增强的收获预测 -----
        if result['harvest']:
            self.out.info("\n收获明细:", color=Fore.CYAN)
            harvest_table = []
            total_seed_cost = result['total_seed_cost']
            for crop, qty in result['harvest'].items():
                plant_qty = result['allocation'].get(crop, 0)
                rounds = result['harvest_rounds'][crop]
                value = result['harvest_value_full'][crop]
                exp = result['harvest_exp'][crop]
                # 单批次净收益（每块地每轮原价收入）
                per_batch = value / (plant_qty * rounds) if plant_qty > 0 and rounds > 0 else 0
                harvest_table.append([
                    crop, plant_qty, rounds,
                    f"{per_batch:.1f}",
                    f"{value:.1f}",
                    f"{exp:.1f}"
                ])
            print(tabulate(harvest_table,
                          headers=["作物", "块数", "轮次", "单批收益(FC)", "总收益(FC)", "经验"],
                          tablefmt="grid"))
            self.out.info(f"全部卖出总收入（考虑软上限）: {result['harvest_value_after_limit']:.1f} FC")
            self.out.info(f"总种子成本: {total_seed_cost:.1f} FC")
            self.out.info(f"总净收益: {result['harvest_value_after_limit'] - total_seed_cost:.1f} FC")
            self.out.info(f"闲置土地: {result.get('idle_land', 0)} 块")
            self.out.info(f"浪费时间: {result.get('wasted_time_hours', 0):.1f} 小时")
        # ----- 结束新增 -----

        # 最终状态
        self.out.info("\n最终状态:", color=Fore.CYAN)
        self.out.key_value("现金", f"{result['final_cash']} FC")
        self.out.key_value("剩余原价额度", f"{result['sell_limit_remaining']} FC")
        self.out.key_value("剩余库存", result['remaining_inventory'])
        self.out.separator()

    # ---------- 文件操作 ----------

    def do_save(self, arg):
        """手动保存当前配置和状态到文件"""
        self.save_all()
        self.out.info("已保存。")

    def do_reload(self, arg):
        """重新从文件加载配置和状态"""
        self.load_data()
        self.out.info("已重新加载。")

    # ---------- 退出命令 ----------

    def do_exit(self, arg):
        """退出交互式命令行"""
        self.out.info("再见！")
        return True

    def do_quit(self, arg):
        """退出（同 exit）"""
        return self.do_exit(arg)

    def do_q(self, arg):
        """退出（同 exit）"""
        return self.do_exit(arg)

    # 空行处理（避免重复执行上次命令）
    def emptyline(self):
        pass


def main():
    # 如果命令行有参数，则运行一次性分析（兼容原 cli.py 用法）
    if len(sys.argv) > 1:
        with open(CROPS_FILE, 'r', encoding='utf-8') as f:
            crops = json.load(f)
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        engine = FarmEngine(crops, config)
        result = engine.analyze(state)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 进入交互模式
        FarmCLI().cmdloop()


if __name__ == "__main__":
    main()