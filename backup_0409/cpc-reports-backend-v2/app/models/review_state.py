"""
審核狀態 ORM 模型（快取表）
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ReviewState(Base):
    """
    審核狀態表（快取表）
    儲存每筆記錄的當前最新狀態，避免每次都掃描 actions 表
    """
    __tablename__ = "review_states"

    # 主鍵
    id = Column(BigInteger, primary_key=True, index=True)

    # 關聯資訊
    detection_log_id = Column(
        BigInteger,
        ForeignKey("detection_logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="關聯的偵測記錄 ID"
    )
    date = Column(Date, nullable=False, comment="日期")
    category = Column(String(50), nullable=False, comment="類別")

    # 當前狀態
    status = Column(String(20), nullable=False, comment="當前狀態: pending | confirmed | deleted")
    note = Column(Text, comment="備註")

    # 審核資訊
    last_action_at = Column(DateTime, comment="最後審核時間")
    last_reviewer_id = Column(Integer, comment="最後審核人 ID")

    # 時間戳記
    created_at = Column(DateTime, default=datetime.now, comment="建立時間")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新時間")

    # 關聯
    detection_log = relationship("DetectionLog", back_populates="review_state")

    # 索引
    __table_args__ = (
        Index('idx_state_date_category_status', 'date', 'category', 'status'),
        Index('idx_state_detection', 'detection_log_id'),
        {'comment': '審核狀態表（快取表），儲存每筆記錄的當前狀態'}
    )

    def __repr__(self):
        return f"<ReviewState(id={self.id}, detection_log_id={self.detection_log_id}, status={self.status})>"

    def to_dict(self):
        """轉換為字典格式"""
        return {
            "id": self.id,
            "detection_log_id": self.detection_log_id,
            "status": self.status,
            "note": self.note,
            "last_action_at": self.last_action_at.isoformat() if self.last_action_at else None,
        }
