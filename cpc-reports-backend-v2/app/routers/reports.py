"""
報告 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import review_service

router = APIRouter()


@router.get("/reports/{date}/{category}")
async def get_report(
    date: str,
    category: str,
    db: Session = Depends(get_db)
):
    """
    取得已審核的報告資料（替代 localStorage 讀取）

    參數:
        - date: 日期（YYYY-MM-DD）
        - category: 類別

    回應:
        - success: 是否成功
        - data: 報告資料（只包含已確認的項目）
    """
    try:
        report = review_service.get_report_data(db, date, category)
        return {
            "success": True,
            "data": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
