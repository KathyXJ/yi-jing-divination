"""
周易占卜 API — FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import divination, ai

app = FastAPI(
    title="周易占卜 API",
    description="周易自动占卜 + AI 智能解卦接口",
    version="1.0.0",
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


@app.get("/")
async def root():
    return {
        "message": "周易占卜 API",
        "version": "1.0.0",
        "endpoints": {
            "占卜": "POST /api/divination/cast",
            "查询卦象": "GET /api/divination/hexagram/{name}",
            "全部64卦": "GET /api/divination/hexagrams",
            "八卦": "GET /api/divination/ba-gua",
            "AI解读": "POST /api/ai/interpret",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
