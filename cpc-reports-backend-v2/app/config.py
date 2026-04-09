"""
設定檔：讀取環境變數
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """應用程式設定"""

    # 資料庫設定
    DATABASE_URL: str = "postgresql://cpc_user:password@localhost:5432/cpc_reports"

    # 開發模式
    DEBUG: bool = False

    # CORS 設定
    CORS_ORIGINS: str = "*"

    # API 版本
    API_V1_STR: str = "/api/v1"

    # 應用程式資訊
    APP_NAME: str = "中油偵測報告系統 API"
    APP_VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 建立全域設定實例
settings = Settings()
