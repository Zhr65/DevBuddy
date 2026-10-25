"""
main.py —— FastAPI 应用入口

启动方式：
    # 开发模式（自动热重载）
    uvicorn app.api.main:app --reload --port 8000

    # 生产模式
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000

然后浏览器打开 http://localhost:8000/docs 可以看到 Swagger UI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(
    title="DevBuddy — React 文档知识库 Agent",
    description="M2 阶段：FastAPI + SSE 流式接口层，对接 M1 的 RAG 管线",
    version="0.2.0",
)

# CORS —— 前端 React（localhost:5173 / 3000）能跨域调这个接口
# allow_origins=["*"] 是开发时偷懒，生产环境要白名单
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["chat"])


@app.get("/")
async def root():
    """根路径 —— 简单告诉你这个服务活着"""
    return {
        "name": "DevBuddy",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/api/health",
    }
