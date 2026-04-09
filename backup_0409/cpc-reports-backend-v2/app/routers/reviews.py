"""
審核 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import review_service
from app.schemas.review import BulkReviewRequest

router = APIRouter()


@router.post("/reviews/actions/bulk")
async def bulk_review_actions(
    request: BulkReviewRequest,
    db: Session = Depends(get_db)
):
    """
    批次提交審核動作（替代 localStorage 儲存）

    請求:
        - date: 日期
        - category: 類別
        - actions: 審核動作列表
        - reviewer_ip: 審核人 IP

    回應:
        - success: 是否成功
        - data: 處理結果統計
    """
    try:
        # 轉換 Pydantic 模型為字典
        actions_list = [action.model_dump() for action in request.actions]

        result = review_service.process_bulk_actions(
            db,
            date=request.date,
            category=request.category,
            actions=actions_list,
            reviewer_ip=request.reviewer_ip or "unknown"
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/{date}/{category}")
async def get_review_summary(
    date: str,
    category: str,
    db: Session = Depends(get_db)
):
    """
    取得審核狀態摘要

    參數:
        - date: 日期（YYYY-MM-DD）
        - category: 類別

    回應:
        - success: 是否成功
        - data: 審核摘要統計
    """
    try:
        summary = review_service.get_review_summary(db, date, category)
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
