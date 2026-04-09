"""
匯出記錄 ORM 模型
"""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, DateTime, Index
from datetime import datetime
from app.database import Base


class ExportLog(Base):
    """
    匯出記錄表
    記錄報表匯出歷史
    """
    __tablename__ = "export_logs"

    # 主鍵
    id = Column(BigInteger, primary_key=True, index=True)

    # 匯出資訊
    date = Column(Date, nullable=False, comment="報表日期")
    category = Column(String(50), nullable=False, comment="類別")
    format = Column(String(20), nullable=False, comment="匯出格式: pdf | excel | csv | word")

    # 匯出內容統計
    total_items = Column(Integer, nullable=False, comment="匯出項目總數")
    file_path = Column(Text, comment="檔案路徑")
    file_size_bytes = Column(BigInteger, comment="檔案大小（bytes）")

    # 匯出者資訊
    exporter_id = Column(Integer, comment="匯出人 ID")
    exporter_ip = Column(String(50), comment="匯出人 IP")

    # 時間戳記
    exported_at = Column(DateTime, default=datetime.now, comment="匯出時間")

    # 索引
    __table_args__ = (
        Index('idx_export_date_category', 'date', 'category'),
        Index('idx_export_exported_at', 'exported_at'),
        {'comment': '匯出記錄表，記錄所有報表匯出操作'}
    )

    def __repr__(self):
        return f"<ExportLog(id={self.id}, date={self.date}, category={self.category}, format={self.format})>"

    def to_dict(self):
        """轉換為字典格式"""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "category": self.category,
            "format": self.format,
            "total_items": self.total_items,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
        }
