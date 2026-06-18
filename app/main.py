import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import user, group, message, websocket, template, event
from app.core.config import load_config
from app.services.rule_engine import rule_engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app_config_path = os.path.join(base_dir, "config", "app_config.yaml")
    rules_config_path = os.path.join(base_dir, "config", "push_rules.yaml")

    load_config(app_config_path)
    rule_engine.load_from_yaml(rules_config_path)
    yield


app = FastAPI(
    title="信达 - 实时消息推送中心",
    description="基于 FastAPI 的实时消息推送服务，支持可插拔推送通道、可插拔消息存储、事件总线解耦",
    version="3.0.0",
    lifespan=lifespan
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
app.include_router(template.router)
app.include_router(event.router)


@app.get("/health", summary="健康检查")
def health_check():
    """
    服务健康检查接口
    """
    return {"status": "ok", "service": "信达 - 实时消息推送中心", "version": "3.0.0"}


@app.get("/", summary="根路径")
def root():
    return {
        "name": "信达 - 实时消息推送中心",
        "version": "3.0.0",
        "docs": "/docs",
        "health": "/health"
    }
