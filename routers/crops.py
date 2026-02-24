from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/crops")
async def get_crops(request: Request):
    """返回所有作物数据（前端根据等级过滤）"""
    return request.app.state.crops_data