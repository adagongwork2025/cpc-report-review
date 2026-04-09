"""
偵測記錄 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import detection_service

router = APIRouter()


@router.get("/detection-logs/{date}/{category}")
async def get_detection_logs(
    date: str,
    category: str,
    db: Session = Depends(get_db)
):
    """
    取得特定日期和類別的偵測記錄（替代 HTML 內嵌 DATA）

    參數:
        - date: 日期（YYYY-MM-DD）
        - category: 類別（高處作業、局限空間）

    回應:
        - success: 是否成功
        - data: 偵測記錄列表
    """
    try:
        logs = detection_service.get_logs_with_review_status(db, date, category)
        return {
            "success": True,
            "data": {
                "date": date,
                "category": category,
                "total": len(logs),
                "items": logs
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
