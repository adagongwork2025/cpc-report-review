# 中油偵測報告系統 - 後端 API

FastAPI + PostgreSQL 後端服務，提供偵測記錄、審核、報告的 RESTful API。

## 快速開始

### 1. 建立資料庫

```bash
# 建立 PostgreSQL 資料庫
createdb cpc_reports

# 建立使用者
psql -c "CREATE USER cpc_user WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE cpc_reports TO cpc_user;"

# 執行 Schema
psql cpc_reports < schema.sql

# 驗證
psql cpc_reports -c "\dt"
```

### 2. 安裝Python套件

```bash
# 建立虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
# 複製範例檔案
cp .env.example .env

# 編輯 .env，修改資料庫連線資訊
# DATABASE_URL=postgresql://cpc_user:your_password@localhost:5432/cpc_reports
```

### 4. 執行資料遷移

```bash
# 從 HTML 檔案匯入資料到資料庫
python migrations/migrate_html_data.py
```

### 5. 啟動API服務

```bash
# 開發模式（自動重載）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生產模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. 測試API

開啟瀏覽器訪問：
- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

## API 端點

### 偵測記錄
- `GET /api/v1/detection-logs/{date}/{category}` - 取得偵測記錄
- `POST /api/v1/detection-logs/bulk` - 批次新增記錄

### 審核
- `GET /api/v1/reviews/{date}/{category}` - 取得審核狀態
- `POST /api/v1/reviews/actions/bulk` - 批次提交審核
- `GET /api/v1/reviews/states/{detection_log_id}` - 取得特定記錄狀態

### 報告
- `GET /api/v1/reports/{date}/{category}` - 取得報告資料
- `POST /api/v1/reports/{date}/{category}/export` - 匯出報告

### 統計
- `GET /api/v1/stats/dates` - 取得有資料的日期列表
- `GET /api/v1/stats/dashboard` - 儀表板統計

## 專案結構

```
cpc-reports-backend/
├── app/
│   ├── main.py              # FastAPI 主程式
│   ├── config.py            # 設定檔
│   ├── database.py          # 資料庫連線
│   ├── models/              # SQLAlchemy ORM 模型
│   ├── schemas/             # Pydantic 驗證 Schema
│   ├── routers/             # API 路由
│   ├── services/            # 業務邏輯層
│   └── utils/               # 工具函數
├── migrations/              # 資料遷移腳本
├── tests/                   # 測試
├── requirements.txt         # Python 套件
├── .env                     # 環境變數（不提交到 Git）
└── README.md                # 本文件
```

## 開發指南

### 執行測試

```bash
pytest tests/ -v
```

### 資料庫操作

```bash
# 查看資料筆數
psql cpc_reports -c "SELECT date, category, COUNT(*) FROM detection_logs GROUP BY date, category;"

# 查看審核統計
psql cpc_reports -c "SELECT * FROM review_summary;"

# 備份資料庫
pg_dump cpc_reports > backup_$(date +%Y%m%d).sql
```

## 部署

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Systemd 服務

```ini
# /etc/systemd/system/cpc-api.service
[Unit]
Description=CPC Reports API
After=network.target postgresql.service

[Service]
User=www-data
WorkingDirectory=/opt/cpc-reports-backend
Environment="PATH=/opt/cpc-reports-backend/venv/bin"
ExecStart=/opt/cpc-reports-backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

## 授權

內部專案，請勿外流。
