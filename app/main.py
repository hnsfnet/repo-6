from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import user, group, message, websocket

app = FastAPI(
    title="信达 - 实时消息推送中心",
    description="基于 FastAPI 的实时消息推送服务，支持 WebSocket 实时推送、用户和分组管理、消息存储与查询",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(group.router)
app.include_router(message.router)
app.include_router(websocket.router)


@app.get("/health", summary="健康检查")
def health_check():
    """
    服务健康检查接口
    """
    return {"status": "ok", "service": "信达 - 实时消息推送中心", "version": "1.0.0"}


@app.get("/", summary="根路径")
def root():
    return {
        "name": "信达 - 实时消息推送中心",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
