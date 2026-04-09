"""
偵測記錄 ORM 模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class DetectionLog(Base):
    """
    偵測記錄主表
    對應 HTML 中的 DATA 陣列
    """
    __tablename__ = "detection_logs"

    # 主鍵
    id = Column(BigInteger, primary_key=True, index=True)

    # 原始資料（對應 DATA 陣列欄位）
    original_id = Column(Integer, nullable=False, comment="HTML DATA 陣列中的原始 id")
    detection_time = Column(DateTime, nullable=False, comment="偵測時間")
    time_display = Column(String(20), comment="顯示用時間（HH:MM:SS）")
    message = Column(Text, nullable=False, comment="違規訊息")
    type = Column(String(100), nullable=False, comment="違規類型")
    person_ids = Column(Text, comment="人員 ID")
    image_url = Column(Text, comment="圖片 URL")
    video_url = Column(Text, comment="影片 URL")

    # 分類資訊
    date = Column(Date, nullable=False, comment="偵測日期")
    category = Column(String(50), nullable=False, comment="類別（高處作業、局限空間）")
    camera_id = Column(String(20), comment="攝影機 ID")

    # 系統欄位
    created_at = Column(DateTime, default=datetime.now, comment="建立時間")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新時間")

    # 關聯
    review_actions = relationship("ReviewAction", back_populates="detection_log", cascade="all, delete-orphan")
    review_state = relationship("ReviewState", back_populates="detection_log", uselist=False, cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_detection_date_category', 'date', 'category'),
        Index('idx_detection_time', 'detection_time'),
        Index('idx_detection_type', 'type'),
        {'comment': '偵測記錄主表，儲存所有 API 原始偵測資料'}
    )

    def __repr__(self):
        return f"<DetectionLog(id={self.id}, date={self.date}, category={self.category}, message={self.message[:20]}...)>"

    def to_dict(self):
        """轉換為字典格式（API 回應用）"""
        return {
            "id": self.id,
            "original_id": self.original_id,
            "time": self.detection_time.isoformat() if self.detection_time else None,
            "time_display": self.time_display,
            "message": self.message,
            "type": self.type,
            "person_ids": self.person_ids,
            "image_url": self.image_url,
            "video_url": self.video_url,
            "date": self.date.isoformat() if self.date else None,
            "category": self.category,
        }
