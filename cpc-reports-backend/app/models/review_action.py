"""
審核動作歷史 ORM 模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ReviewAction(Base):
    """
    審核動作歷史表
    記錄每一次審核操作，支援審核歷史追蹤
    """
    __tablename__ = "review_actions"

    # 主鍵
    id = Column(BigInteger, primary_key=True, index=True)

    # 關聯資訊
    detection_log_id = Column(
        BigInteger,
        ForeignKey("detection_logs.id", ondelete="CASCADE"),
        nullable=False,
        comment="關聯的偵測記錄 ID"
    )
    date = Column(Date, nullable=False, comment="日期")
    category = Column(String(50), nullable=False, comment="類別")

    # 審核動作
    action = Column(String(20), nullable=False, comment="審核動作: confirmed | deleted | unconfirmed")
    note = Column(Text, comment="備註")

    # 審核人資訊（預留欄位）
    reviewer_id = Column(Integer, comment="審核人 ID（預留）")
    reviewer_ip = Column(String(50), comment="審核人 IP")
    reviewer_user_agent = Column(Text, comment="瀏覽器資訊")

    # 時間戳記
    action_at = Column(DateTime, default=datetime.now, comment="審核時間")

    # 關聯
    detection_log = relationship("DetectionLog", back_populates="review_actions")

    # 索引
    __table_args__ = (
        Index('idx_review_detection', 'detection_log_id'),
        Index('idx_review_date_category', 'date', 'category'),
        Index('idx_review_action_at', 'action_at'),
        {'comment': '審核動作歷史表，記錄所有審核操作'}
    )

    def __repr__(self):
        return f"<ReviewAction(id={self.id}, detection_log_id={self.detection_log_id}, action={self.action})>"

    def to_dict(self):
        """轉換為字典格式"""
        return {
            "id": self.id,
            "detection_log_id": self.detection_log_id,
            "action": self.action,
            "note": self.note,
            "reviewer_ip": self.reviewer_ip,
            "action_at": self.action_at.isoformat() if self.action_at else None,
        }
