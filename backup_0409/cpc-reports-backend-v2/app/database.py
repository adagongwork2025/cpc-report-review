"""
資料庫連線設定
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# 建立資料庫引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,           # 連線池大小
    max_overflow=40,        # 超過 pool_size 後的最大連線數
    pool_pre_ping=True,     # 自動檢測斷線並重連
    echo=settings.DEBUG      # DEBUG 模式下顯示 SQL 查詢
)

# 建立 SessionLocal 類別
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 建立 Base 類別（所有 ORM 模型的基礎類別）
Base = declarative_base()


def get_db():
    """
    取得資料庫 session 的依賴注入函數

    使用範例:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
