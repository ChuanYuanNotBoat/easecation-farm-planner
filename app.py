from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
import json
import os
from core.engine import FarmEngine

app = FastAPI(title="农场策略引擎 Web 界面")

# 全局数据
CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CROPS_FILE = os.path.join(CONFIG_DIR, "crops.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

# 加载数据
with open(CROPS_FILE, 'r', encoding='utf-8') as f:
    crops = json.load(f)
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)
with open(STATE_FILE, 'r', encoding='utf-8') as f:
    state = json.load(f)

# 创建引擎
engine = FarmEngine(crops, config)

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def save_state():
    # 保存前清理零值库存（与 cli.py 保持一致）
    if 'inventory_crops' in state:
        state['inventory_crops'] = {k: v for k, v in state['inventory_crops'].items() if v != 0}
    if 'inventory_items' in state and isinstance(state['inventory_items'], dict):
        state['inventory_items'] = {k: v for k, v in state['inventory_items'].items() if v != 0}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def reload_engine():
    global engine
    engine = FarmEngine(crops, config)

# ---------- API 端点 ----------

@app.get("/", response_class=HTMLResponse)
async def root():
    """返回简洁的 Web 界面"""
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/api/config")
async def get_config():
    return config

@app.get("/api/state")
async def get_state():
    return state

@app.get("/api/crops")
async def get_crops():
    # 返回所有作物，由前端根据等级过滤
    return crops

@app.post("/api/analyze")
async def analyze(state_data: dict):
    """接收状态字典，返回分析结果"""
    result = engine.analyze(state_data)
    return result

@app.post("/api/set_config")
async def set_config(request: Request):
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    if not key:
        raise HTTPException(status_code=400, detail="缺少 key")
    
    # 禁止修改 objective_presets
    if key == "objective_presets":
        raise HTTPException(status_code=400, detail="objective_presets 不可直接修改，请编辑 config.json")
    
    if key not in config:
        raise HTTPException(status_code=404, detail=f"配置键 {key} 不存在")
    
    # 尝试转换类型（数字或保持字符串）
    try:
        if isinstance(value, str) and '.' in value:
            val = float(value)
        elif isinstance(value, str):
            val = int(value)
        else:
            val = value  # 已经是数字
    except ValueError:
        val = value
    
    config[key] = val
    save_config()
    reload_engine()
    return {"message": f"配置项 {key} 已更新", "new_value": val}

@app.post("/api/set_state")
async def set_state(request: Request):
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    if not key:
        raise HTTPException(status_code=400, detail="缺少 key")
    
    # 处理 inventory.<作物>
    if key.startswith("inventory."):
        parts = key.split('.')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="格式错误，应为 inventory.<作物名>")
        crop = parts[1]
        if crop not in state['inventory_crops']:
            state['inventory_crops'][crop] = 0
        try:
            val = int(value)
        except:
            raise HTTPException(status_code=400, detail="库存数量必须为整数")
        state['inventory_crops'][crop] = val
        save_state()
        return {"message": f"库存作物 {crop} 已更新为 {val}"}
    
    # 普通状态键
    if key not in state:
        raise HTTPException(status_code=404, detail=f"状态键 {key} 不存在")
    
    try:
        if isinstance(value, str) and '.' in value:
            val = float(value)
        elif isinstance(value, str):
            val = int(value)
        else:
            val = value
    except ValueError:
        val = value
    
    state[key] = val
    save_state()
    return {"message": f"状态项 {key} 已更新", "new_value": val}

# ---------- HTML 模板（简洁界面） ----------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>农场策略引擎 · 简洁面板</title>
    <style>
        * { box-sizing: border-box; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
        body { background: #f5f7fa; margin: 0; padding: 20px; display: flex; justify-content: center; }
        .container { max-width: 1200px; width: 100%; background: white; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); padding: 24px; }
        h1 { font-size: 1.8rem; margin-top: 0; margin-bottom: 20px; font-weight: 500; color: #1e293b; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; }
        h2 { font-size: 1.4rem; font-weight: 500; color: #334155; margin: 24px 0 12px; }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
        .card { background: #f8fafc; border-radius: 12px; padding: 16px; border: 1px solid #e2e8f0; }
        .card h3 { font-size: 1.2rem; margin-top: 0; margin-bottom: 16px; font-weight: 500; color: #0f172a; display: flex; align-items: center; gap: 8px; }
        .kv-list { display: flex; flex-direction: column; gap: 8px; }
        .kv-item { display: flex; align-items: center; }
        .kv-key { width: 130px; color: #475569; }
        .kv-value { font-weight: 500; color: #0f172a; }
        button { background: #3b82f6; border: none; color: white; padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; cursor: pointer; transition: 0.2s; }
        button:hover { background: #2563eb; }
        button.secondary { background: #e2e8f0; color: #1e293b; }
        button.secondary:hover { background: #cbd5e1; }
        input, select { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.9rem; width: 100%; }
        .flex { display: flex; gap: 8px; align-items: center; }
        .mt-4 { margin-top: 16px; }
        .mb-2 { margin-bottom: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th { text-align: left; background: #f1f5f9; padding: 10px 8px; font-weight: 500; color: #334155; }
        td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
        .badge { background: #dbeafe; color: #1e40af; padding: 4px 8px; border-radius: 20px; font-size: 0.8rem; }
        .result-box { background: #f1f5f9; border-radius: 12px; padding: 16px; margin-top: 24px; }
        .mono { font-family: monospace; }
        .warning { color: #b45309; background: #fffbeb; padding: 8px; border-radius: 8px; }
    </style>
</head>
<body>
<div class="container">
    <h1>🌾 农场策略引擎 · 简洁面板</h1>

    <div class="grid-2">
        <!-- 当前配置 -->
        <div class="card">
            <h3>⚙️ 当前配置</h3>
            <div id="config-display" class="kv-list">加载中...</div>
            <div class="mt-4">
                <h4 style="margin:0 0 8px 0; font-size:1rem;">修改配置</h4>
                <div class="flex">
                    <select id="config-key" style="flex:2;">
                        <option value="land_units">土地数量</option>
                        <option value="current_level">当前等级</option>
                        <option value="active_preset">活动预设</option>
                        <option value="simulation_days">模拟天数</option>
                    </select>
                    <input type="text" id="config-value" placeholder="新值" style="flex:1;">
                    <button onclick="updateConfig()">更新</button>
                </div>
                <p class="warning" style="margin-top:8px; font-size:0.85rem;">※ 预设权重不可直接修改，请编辑 config.json</p>
            </div>
        </div>

        <!-- 当前状态 -->
        <div class="card">
            <h3>📦 当前状态</h3>
            <div id="state-display" class="kv-list">加载中...</div>
            <div class="mt-4">
                <h4 style="margin:0 0 8px 0; font-size:1rem;">修改状态</h4>
                <div class="flex">
                    <select id="state-key" style="flex:2;">
                        <option value="cash">现金</option>
                        <option value="sell_limit_remaining">剩余原价额度</option>
                        <option value="reduced_sell_multiplier">折扣系数</option>
                        <option value="online_duration">可操作时间</option>
                        <option value="sleep_duration">非操作时间</option>
                        <option value="inventory.wheat">小麦库存</option>
                        <option value="inventory.lettuce">生菜库存</option>
                        <!-- 更多作物可通过JS动态添加，这里仅示例 -->
                    </select>
                    <input type="text" id="state-value" placeholder="新值" style="flex:1;">
                    <button onclick="updateState()">更新</button>
                </div>
                <p class="warning" style="margin-top:8px; font-size:0.85rem;">※ 库存用 inventory.作物名 修改</p>
            </div>
        </div>
    </div>

    <!-- 作物列表（仅显示已解锁） -->
    <h2>🌱 已解锁作物</h2>
    <div id="crops-table">加载中...</div>

    <!-- 分析按钮与结果 -->
    <div style="margin: 24px 0 12px;">
        <button onclick="runAnalysis()" style="padding:12px 24px; font-size:1rem;">🔍 运行分析</button>
    </div>
    <div id="result-box" class="result-box" style="display:none;">
        <h3 style="margin-top:0;">📊 分析结果</h3>
        <div id="result-content"></div>
    </div>
</div>

<script>
    // 加载所有数据
    async function loadConfig() {
        const res = await fetch('/api/config');
        const data = await res.json();
        let html = '';
        for (let [k, v] of Object.entries(data)) {
            if (k === 'objective_presets') {
                html += `<div class="kv-item"><span class="kv-key">${k}:</span> <span class="kv-value">(预设对象)</span></div>`;
            } else {
                html += `<div class="kv-item"><span class="kv-key">${k}:</span> <span class="kv-value">${JSON.stringify(v)}</span></div>`;
            }
        }
        document.getElementById('config-display').innerHTML = html;
    }

    async function loadState() {
        const res = await fetch('/api/state');
        const data = await res.json();
        let html = '';
        html += `<div class="kv-item"><span class="kv-key">现金:</span> <span class="kv-value">${data.cash} FC</span></div>`;
        html += `<div class="kv-item"><span class="kv-key">剩余原价额度:</span> <span class="kv-value">${data.sell_limit_remaining}</span></div>`;
        html += `<div class="kv-item"><span class="kv-key">折扣系数:</span> <span class="kv-value">${data.reduced_sell_multiplier}</span></div>`;
        html += `<div class="kv-item"><span class="kv-key">可操作时间:</span> <span class="kv-value">${data.online_duration} 小时</span></div>`;
        html += `<div class="kv-item"><span class="kv-key">非操作时间:</span> <span class="kv-value">${data.sleep_duration} 小时</span></div>`;
        html += `<div style="margin-top:8px;"><strong>库存作物:</strong> `;
        if (Object.keys(data.inventory_crops).length === 0) html += '无';
        else {
            html += '<ul style="margin:4px 0 0 16px;">';
            for (let [c, q] of Object.entries(data.inventory_crops)) {
                html += `<li>${c}: ${q}</li>`;
            }
            html += '</ul>';
        }
        html += `</div>`;
        document.getElementById('state-display').innerHTML = html;
    }

    async function loadCrops() {
        const configRes = await fetch('/api/config');
        const config = await configRes.json();
        const currentLevel = config.current_level || 0;
        const cropsRes = await fetch('/api/crops');
        const crops = await cropsRes.json();
        let table = '<table><tr><th>名称</th><th>生长(h)</th><th>产量</th><th>售价</th><th>种子价</th><th>利润/块</th><th>利润/h</th><th>解锁等级</th></tr>';
        crops.forEach(c => {
            if (c.unlock_level > currentLevel) return;
            const profitPlot = c.expected_yield * c.sell_price - c.seed_cost;
            const profitHour = profitPlot / c.growth_time;
            table += `<tr>
                <td>${c.name}</td>
                <td>${c.growth_time}</td>
                <td>${c.expected_yield}</td>
                <td>${c.sell_price}</td>
                <td>${c.seed_cost}</td>
                <td>${profitPlot.toFixed(1)}</td>
                <td>${profitHour.toFixed(2)}</td>
                <td>${c.unlock_level}</td>
            </tr>`;
        });
        table += '</table>';
        document.getElementById('crops-table').innerHTML = table;
    }

    // 更新配置
    async function updateConfig() {
        const key = document.getElementById('config-key').value;
        const value = document.getElementById('config-value').value;
        if (!value.trim()) return;
        const res = await fetch('/api/set_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key, value})
        });
        if (res.ok) {
            alert('配置已更新');
            loadConfig();
            loadCrops(); // 等级变化可能影响作物列表
        } else {
            const err = await res.json();
            alert('错误：' + (err.detail || '未知错误'));
        }
    }

    // 更新状态
    async function updateState() {
        const key = document.getElementById('state-key').value;
        const value = document.getElementById('state-value').value;
        if (!value.trim()) return;
        const res = await fetch('/api/set_state', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({key, value})
        });
        if (res.ok) {
            alert('状态已更新');
            loadState();
        } else {
            const err = await res.json();
            alert('错误：' + (err.detail || '未知错误'));
        }
    }

    // 运行分析
    async function runAnalysis() {
        // 获取当前状态
        const stateRes = await fetch('/api/state');
        const state = await stateRes.json();
        const analyzeRes = await fetch('/api/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(state)
        });
        const result = await analyzeRes.json();

        let html = `<p><strong>预设：</strong> ${result.preset}</p>`;

        // 种植分配
        html += '<h4>🌱 种植分配</h4><ul>';
        for (let [crop, qty] of Object.entries(result.allocation)) {
            html += `<li>${crop}: ${qty} 块</li>`;
        }
        html += '</ul>';

        // 销售建议
        if (result.sales && result.sales.length) {
            html += '<h4>💰 建议卖出</h4><ul>';
            result.sales.forEach(s => html += `<li>${s.crop}: ${s.qty}</li>`);
            html += '</ul>';
        } else {
            html += '<p>无需卖出库存</p>';
        }

        // 购买种子
        if (result.purchases && result.purchases.length) {
            html += '<h4>🌰 需购买种子</h4><ul>';
            result.purchases.forEach(p => html += `<li>${p.crop}: ${p.seeds}</li>`);
            html += '</ul>';
        }

        // 收获预测（新字段）
        if (result.harvest && Object.keys(result.harvest).length) {
            html += '<h4>📈 收获预测</h4><table><tr><th>作物</th><th>收获量</th><th>原价总价值</th><th>经验</th></tr>';
            for (let crop in result.harvest) {
                let qty = result.harvest[crop];
                let val = result.harvest_value_full[crop];
                let exp = result.harvest_exp[crop];
                html += `<tr><td>${crop}</td><td>${qty.toFixed(1)}</td><td>${val.toFixed(1)} FC</td><td>${exp.toFixed(1)}</td></tr>`;
            }
            html += '</table>';
            html += `<p>全部卖出总收入（考虑软上限）: <strong>${result.harvest_value_after_limit.toFixed(1)} FC</strong></p>`;
        }

        // 最终状态
        html += '<h4>🏁 最终状态</h4>';
        html += `<p>现金: ${result.final_cash} FC<br>`;
        html += `剩余原价额度: ${result.sell_limit_remaining}<br>`;
        html += `剩余库存: <pre class="mono">${JSON.stringify(result.remaining_inventory, null, 2)}</pre></p>`;

        document.getElementById('result-content').innerHTML = html;
        document.getElementById('result-box').style.display = 'block';
    }

    // 初始化
    loadConfig();
    loadState();
    loadCrops();

    // 动态添加更多作物选项（简单示例，实际可更全）
    // 这里仅作示意，已硬编码常用作物，如需完整可自动生成
</script>
</body>
</html>
"""
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)