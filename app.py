from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import json
import os
from core.engine import FarmEngine

# 导入路由模块
from routers import config as config_router
from routers import state as state_router
from routers import crops as crops_router
from routers import analyze as analyze_router

app = FastAPI(title="农场策略引擎 Web 界面")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 加载数据
CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
CROPS_FILE = os.path.join(CONFIG_DIR, "crops.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

with open(CROPS_FILE, 'r', encoding='utf-8') as f:
    crops_data = json.load(f)
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config_data = json.load(f)
with open(STATE_FILE, 'r', encoding='utf-8') as f:
    state_data = json.load(f)

# 创建引擎并存储在 app.state 中
app.state.engine = FarmEngine(crops_data, config_data)
app.state.crops_data = crops_data
app.state.config_data = config_data
app.state.state_data = state_data

# 注册路由
app.include_router(config_router.router, prefix="/api", tags=["config"])
app.include_router(state_router.router, prefix="/api", tags=["state"])
app.include_router(crops_router.router, prefix="/api", tags=["crops"])
app.include_router(analyze_router.router, prefix="/api", tags=["analyze"])


@app.get("/", response_class=templates.TemplateResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)