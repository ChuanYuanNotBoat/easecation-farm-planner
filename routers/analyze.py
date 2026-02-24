from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/analyze")
async def analyze(state: dict, request: Request):
    """接收状态字典，返回分析结果"""
    engine = request.app.state.engine
    result = engine.analyze(state)
    return result