from fastapi import APIRouter, HTTPException, Request
import json
import os
from core.engine import FarmEngine

router = APIRouter()

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CROPS_FILE = os.path.join(CONFIG_DIR, "crops.json")


@router.get("/config")
async def get_config(request: Request):
    """返回当前配置"""
    return request.app.state.config_data


@router.post("/set_config")
async def set_config(request: Request):
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    if not key:
        raise HTTPException(status_code=400, detail="缺少 key")

    # 禁止直接修改 objective_presets
    if key == "objective_presets":
        raise HTTPException(status_code=400, detail="objective_presets 不可直接修改，请编辑 config.json")

    config_data = request.app.state.config_data
    if key not in config_data:
        raise HTTPException(status_code=404, detail=f"配置键 {key} 不存在")

    # 对 active_preset 进行额外校验
    if key == "active_preset":
        if value not in config_data["objective_presets"]:
            raise HTTPException(status_code=400, detail=f"预设 '{value}' 不存在")

    # 尝试转换类型
    try:
        if isinstance(value, str) and '.' in value:
            val = float(value)
        elif isinstance(value, str):
            val = int(value)
        else:
            val = value
    except ValueError:
        val = value

    config_data[key] = val

    # 保存到文件
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

    # 重新创建引擎并更新 app.state
    request.app.state.engine = FarmEngine(request.app.state.crops_data, config_data)

    return {"message": f"配置项 {key} 已更新", "new_value": val}