"""
FastAPI 主程式
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import detection_logs, reviews, reports, stats

# 建立所有資料表（如果不存在）
Base.metadata.create_all(bind=engine)

# 建立 FastAPI 應用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="工安違規偵測審核與報告系統 - RESTful API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 設定（允許前端跨域請求）
origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(detection_logs.router, prefix=settings.API_V1_STR, tags=["偵測記錄"])
app.include_router(reviews.router, prefix=settings.API_V1_STR, tags=["審核"])
app.include_router(reports.router, prefix=settings.API_V1_STR, tags=["報告"])
app.include_router(stats.router, prefix=settings.API_V1_STR, tags=["統計"])


@app.get("/")
async def root():
    """根路徑"""
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }
