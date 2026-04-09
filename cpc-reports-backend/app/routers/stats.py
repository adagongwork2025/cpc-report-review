"""
統計 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import detection_service
from typing import Optional

router = APIRouter()


@router.get("/stats/dates")
async def get_dates_list(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    db: Session = Depends(get_db)
):
    """
    取得有資料的日期列表（替代 index.html 的 REPORT_DATA）

    參數:
        - year: 年份（選填）
        - month: 月份（選填）

    回應:
        - success: 是否成功
        - data: 日期列表及統計資訊
    """
    try:
        dates = detection_service.get_all_dates_with_stats(db, year, month)
        return {
            "success": True,
            "data": dates
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
