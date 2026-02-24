# EaseCation Farm 规划工具

一个用于 [EaseCation](https://www.easecation.net/) 服务器 **Farm 小游戏** 的策略规划工具。  
帮助你优化种植决策，最大化利润/经验，并自动考虑出售限额、库存、可操作时间等因素。

> ⚠️ 当前为**初始版本**，核心逻辑已实现，并提供 Web 面板与命令行两种交互方式。

---

## ✨ 功能特点

- **多目标策略**：支持利润优先、经验优先、平衡、懒人模式四种预设，可自由调整权重。
- **智能种植推荐**：基于当前现金、库存、可操作时间，自动分配土地，并考虑多轮种植。
- **销售模拟**：自动卖出库存以筹集资金，优先消耗原价额度，超出部分按折扣计算。
- **库存管理**：实时查看/修改库存、现金、剩余额度。
- **作物解锁**：根据等级自动过滤未解锁作物。
- **双界面**：
  - **Web 面板**（FastAPI + Jinja2）：可视化修改配置、状态，一键运行分析。
  - **交互式命令行**（Python cmd）：适合快速调试，支持全部功能。

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 依赖库：`fastapi`, `uvicorn[standard]`, `jinja2`, `colorama`, `tabulate`

### 安装步骤
1. 克隆仓库
   ```bash
   git clone https://github.com/yourname/easecation-farm-planner.git
   cd easecation-farm-planner
   ```
2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

### 运行 Web 界面
```bash
python app.py
```
访问 http://127.0.0.1:8000 即可打开面板。

### 运行命令行工具
```bash
python cli.py
```
输入 `help` 查看可用命令。

---

## 📁 项目结构

```
.
├── app.py                 # FastAPI 入口
├── cli.py                 # 命令行交互工具
├── requirements.txt       # 依赖列表
├── config/                # 配置文件目录
│   ├── config.json        # 全局配置（土地、等级、策略预设）
│   ├── crops.json         # 作物数据（名称、生长时间、售价等）
│   └── state.json         # 当前状态（现金、库存、额度等）
├── core/                  # 核心逻辑
│   ├── engine.py          # FarmEngine 主引擎
│   ├── models.py          # 数据类
│   └── simulator.py       # 仿真器（封装）
├── routers/               # FastAPI 路由
│   ├── config.py
│   ├── state.py
│   ├── crops.py
│   └── analyze.py
└── templates/             # HTML 模板
    └── index.html
```

---

## ⚙️ 配置说明

### `config.json`
```json
{
    "land_units": 82,                 // 总土地块数
    "current_level": 13,              // 当前等级（影响作物解锁）
    "objective_presets": {            // 策略预设（权重可调）
        "money": { "profit": 1.0, "exp": 0.0, "complexity": 0.1 },
        "exp": { "profit": 0.5, "exp": 1.0, "complexity": 0.1 },
        "balanced": { "profit": 1.0, "exp": 0.6, "complexity": 0.3 },
        "lazy_mode": { "profit": 0.8, "exp": 0.3, "complexity": 1.2 }
    },
    "active_preset": "money"          // 当前使用的预设
}
```

### `crops.json`
作物列表，每个作物包含：
- `name`: 名称（必须与库存键一致）
- `growth_time`: 生长小时数
- `expected_yield`: 预期产量
- `sell_price`: 单个售价
- `seed_cost`: 种子价格
- `exp_per_unit`: 每单位经验（可选）
- `unlock_level`: 解锁等级

### `state.json`
当前状态：
- `cash`: 现金
- `sell_limit_remaining`: 剩余原价出售额度
- `reduced_sell_multiplier`: 超出额度后的折扣系数
- `inventory_crops`: 各作物库存数量
- `inventory_items`: 其他道具（预留）
- `online_duration`: 可操作时间（小时）
- `sleep_duration`: 非操作时间（小时）

---

## 🧠 核心算法简介

1. **作物过滤**：只保留等级 ≤ `current_level` 的作物。
2. **评分函数**：  
   `score = profit权重 × 利润/小时 + exp权重 × 经验/小时 - 复杂度权重 / 生长时间`  
   复杂度惩罚使生长时间短的作物（需频繁操作）得分降低。
3. **种植分配**：按评分从高到低依次种植，资金不足时自动卖出低分库存作物筹集。
4. **多轮次预测**：根据 `online_duration` 和 `sleep_duration` 计算每种作物的可种植轮次（在线期间可多次种植，睡眠期间最多一次）。
5. **销售模拟**：卖出新收获时，优先消耗原价额度，超出部分按折扣计算，最终得到净收益。

---

## 🤝 贡献指南

欢迎提交 Issue 或 Pull Request。  
目前项目处于早期，任何建议或功能扩展都非常欢迎！

---

## 📄 许可证

[MIT](LICENSE)