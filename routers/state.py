from fastapi import APIRouter, HTTPException, Request
import json
import os

router = APIRouter()

STATE_FILE = os.path.join("config", "state.json")


def save_state(state_data):
    """保存状态到文件，自动清理零值库存"""
    if 'inventory_crops' in state_data:
        state_data['inventory_crops'] = {k: v for k, v in state_data['inventory_crops'].items() if v != 0}
    if 'inventory_items' in state_data and isinstance(state_data['inventory_items'], dict):
        state_data['inventory_items'] = {k: v for k, v in state_data['inventory_items'].items() if v != 0}
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=4, ensure_ascii=False)


@router.get("/state")
async def get_state(request: Request):
    """返回当前状态"""
    return request.app.state.state_data


@router.post("/set_state")
async def set_state(request: Request):
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    if not key:
        raise HTTPException(status_code=400, detail="缺少 key")

    state_data = request.app.state.state_data

    # 处理 inventory.<作物>
    if key.startswith("inventory."):
        parts = key.split('.')
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="格式错误，应为 inventory.<作物名>")
        crop = parts[1]
        if crop not in state_data['inventory_crops']:
            state_data['inventory_crops'][crop] = 0
        try:
            val = int(value)
        except ValueError:
            raise HTTPException(status_code=400, detail="库存数量必须为整数")
        state_data['inventory_crops'][crop] = val
        save_state(state_data)
        return {"message": f"库存作物 {crop} 已更新为 {val}"}

    # 普通状态键
    if key not in state_data:
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

    state_data[key] = val
    save_state(state_data)
    return {"message": f"状态项 {key} 已更新", "new_value": val}