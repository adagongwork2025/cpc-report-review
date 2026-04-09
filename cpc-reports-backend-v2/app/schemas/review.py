"""
審核相關的 Pydantic Schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ReviewActionCreate(BaseModel):
    """單筆審核動作"""
    detection_log_id: int = Field(..., description="偵測記錄 ID")
    action: str = Field(..., description="審核動作: confirmed | deleted | unconfirmed")
    note: Optional[str] = Field(None, description="備註")


class BulkReviewRequest(BaseModel):
    """批次審核請求"""
    date: str = Field(..., description="日期（YYYY-MM-DD）")
    category: str = Field(..., description="類別（高處作業、局限空間）")
    actions: List[ReviewActionCreate] = Field(..., description="審核動作列表")
    reviewer_ip: Optional[str] = Field(None, description="審核人 IP")


class ReviewSummaryResponse(BaseModel):
    """審核摘要回應"""
    date: str
    category: str
    total_items: int
    confirmed_count: int
    deleted_count: int
    pending_count: int
    last_review_time: Optional[datetime] = None


class ReviewStateResponse(BaseModel):
    """審核狀態回應"""
    id: int
    detection_log_id: int
    status: str
    note: Optional[str] = None
    last_action_at: Optional[datetime] = None

    class Config:
        from_attributes = True
