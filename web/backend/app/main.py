"""
周易占卜 API — FastAPI 主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import divination, ai, auth, credits
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动和关闭时的生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield
    # 关闭时清理资源（如有需要）


app = FastAPI(
    title="周易占卜 API",
    description="周易自动占卜 + AI 智能解卦接口",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境可改为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(divination.router)
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(credits.router)


@app.get("/")
async def root():
    return {
        "message": "周易占卜 API",
        "version": "1.1.0",
        "endpoints": {
            "占卜": "POST /api/divination/cast",
            "查询卦象": "GET /api/divination/hexagram/{name}",
            "全部64卦": "GET /api/divination/hexagrams",
            "八卦": "GET /api/divination/ba-gua",
            "AI解读": "POST /api/ai/interpret",
            "Google登录": "GET /auth/google",
            "Google回调": "GET /auth/google/callback",
            "当前用户": "GET /auth/me",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
