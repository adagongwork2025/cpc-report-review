-- ============================================
-- 中油偵測報告系統 - PostgreSQL 資料庫 Schema
-- ============================================
-- 版本: 1.0.0
-- 日期: 2026-04-08
-- 說明: 將 localStorage 架構升級為資料庫儲存
-- ============================================

-- 1. 偵測記錄主表
-- 對應 HTML 中的 DATA 陣列
-- ============================================
CREATE TABLE IF NOT EXISTS detection_logs (
    id BIGSERIAL PRIMARY KEY,

    -- 原始資料（對應 DATA 陣列欄位）
    original_id INTEGER NOT NULL,
    detection_time TIMESTAMP NOT NULL,
    time_display VARCHAR(20),
    message TEXT NOT NULL,
    type VARCHAR(100) NOT NULL,
    person_ids TEXT,
    image_url TEXT,
    video_url TEXT,

    -- 分類資訊
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    camera_id VARCHAR(20),

    -- 系統欄位
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 唯一約束：同一天、同一類別、同一 original_id 不重複
    CONSTRAINT unique_detection UNIQUE (date, category, original_id)
);

-- 索引：加速日期+類別查詢（最常用的查詢條件）
CREATE INDEX idx_detection_date_category ON detection_logs(date, category);

-- 索引：加速時間範圍查詢
CREATE INDEX idx_detection_time ON detection_logs(detection_time);

-- 索引：加速類型篩選
CREATE INDEX idx_detection_type ON detection_logs(type);

COMMENT ON TABLE detection_logs IS '偵測記錄主表，儲存所有 API 原始偵測資料';
COMMENT ON COLUMN detection_logs.original_id IS 'HTML DATA 陣列中的原始 id';
COMMENT ON COLUMN detection_logs.detection_time IS '偵測時間（完整時間戳）';
COMMENT ON COLUMN detection_logs.time_display IS '顯示用時間（HH:MM:SS 格式）';
COMMENT ON COLUMN detection_logs.message IS '違規訊息';
COMMENT ON COLUMN detection_logs.type IS '違規類型（hooked, harness 等）';


-- ============================================
-- 2. 審核動作歷史表
-- 記錄每一次審核操作，支援審核歷史追蹤
-- ============================================
CREATE TABLE IF NOT EXISTS review_actions (
    id BIGSERIAL PRIMARY KEY,

    -- 關聯資訊
    detection_log_id BIGINT NOT NULL REFERENCES detection_logs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,

    -- 審核動作
    action VARCHAR(20) NOT NULL CHECK (action IN ('confirmed', 'deleted', 'unconfirmed')),
    note TEXT,

    -- 審核人資訊（預留欄位，未來可接使用者登入系統）
    reviewer_id INTEGER,
    reviewer_ip VARCHAR(50),
    reviewer_user_agent TEXT,

    -- 時間戳記
    action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 唯一約束：同一 detection_log_id 在同一時間只能有一個動作
    CONSTRAINT unique_review_action UNIQUE (detection_log_id, action_at)
);

-- 索引：加速單一記錄的審核歷史查詢
CREATE INDEX idx_review_detection ON review_actions(detection_log_id);

-- 索引：加速日期+類別的審核歷史查詢
CREATE INDEX idx_review_date_category ON review_actions(date, category);

-- 索引：加速時間範圍查詢
CREATE INDEX idx_review_action_at ON review_actions(action_at);

COMMENT ON TABLE review_actions IS '審核動作歷史表，記錄所有審核操作';
COMMENT ON COLUMN review_actions.action IS '審核動作: confirmed(確認違規) | deleted(誤報) | unconfirmed(取消確認)';
COMMENT ON COLUMN review_actions.reviewer_id IS '審核人ID（預留，未來實作使用者登入）';
COMMENT ON COLUMN review_actions.reviewer_ip IS '審核人IP位址';


-- ============================================
-- 3. 審核狀態表（快取表）
-- 儲存每筆記錄的當前最新狀態，避免每次都掃描 actions 表
-- ============================================
CREATE TABLE IF NOT EXISTS review_states (
    id BIGSERIAL PRIMARY KEY,

    -- 關聯資訊
    detection_log_id BIGINT NOT NULL REFERENCES detection_logs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,

    -- 當前狀態
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'confirmed', 'deleted')),
    note TEXT,

    -- 審核資訊
    last_action_at TIMESTAMP,
    last_reviewer_id INTEGER,

    -- 時間戳記
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 唯一約束：每個 detection_log_id 只有一個當前狀態
    CONSTRAINT unique_review_state UNIQUE (detection_log_id)
);

-- 複合索引：加速日期+類別+狀態的組合查詢（報告頁面最常用）
CREATE INDEX idx_state_date_category_status ON review_states(date, category, status);

-- 索引：加速單一記錄的狀態查詢
CREATE INDEX idx_state_detection ON review_states(detection_log_id);

COMMENT ON TABLE review_states IS '審核狀態表（快取表），儲存每筆記錄的當前狀態';
COMMENT ON COLUMN review_states.status IS '當前狀態: pending(待審核) | confirmed(已確認違規) | deleted(已刪除/誤報)';


-- ============================================
-- 4. 匯出記錄表
-- 記錄報表匯出歷史
-- ============================================
CREATE TABLE IF NOT EXISTS export_logs (
    id BIGSERIAL PRIMARY KEY,

    -- 匯出資訊
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    format VARCHAR(20) NOT NULL CHECK (format IN ('pdf', 'excel', 'csv', 'word')),

    -- 匯出內容統計
    total_items INTEGER NOT NULL,
    file_path TEXT,
    file_size_bytes BIGINT,

    -- 匯出者資訊
    exporter_id INTEGER,
    exporter_ip VARCHAR(50),

    -- 時間戳記
    exported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引：加速日期+類別的匯出歷史查詢
CREATE INDEX idx_export_date_category ON export_logs(date, category);

-- 索引：加速時間範圍查詢
CREATE INDEX idx_export_exported_at ON export_logs(exported_at);

COMMENT ON TABLE export_logs IS '匯出記錄表，記錄所有報表匯出操作';
COMMENT ON COLUMN export_logs.format IS '匯出格式: pdf | excel | csv | word';


-- ============================================
-- 5. 統計視圖
-- 提供審核摘要統計，簡化查詢
-- ============================================
CREATE OR REPLACE VIEW review_summary AS
SELECT
    date,
    category,
    COUNT(*) as total_items,
    COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_count,
    COUNT(CASE WHEN status = 'deleted' THEN 1 END) as deleted_count,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
    MAX(last_action_at) as last_review_time
FROM review_states
GROUP BY date, category;

COMMENT ON VIEW review_summary IS '審核摘要統計視圖，用於儀表板和報告頁面';


-- ============================================
-- 6. 觸發器：自動更新 updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 應用到 detection_logs
CREATE TRIGGER update_detection_logs_updated_at
    BEFORE UPDATE ON detection_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 應用到 review_states
CREATE TRIGGER update_review_states_updated_at
    BEFORE UPDATE ON review_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMENT ON FUNCTION update_updated_at_column() IS '自動更新 updated_at 欄位為當前時間';


-- ============================================
-- 7. 初始化完成
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '=========================================';
    RAISE NOTICE '中油偵測報告系統 - 資料庫初始化完成';
    RAISE NOTICE '=========================================';
    RAISE NOTICE '已建立:';
    RAISE NOTICE '  - 4 個資料表';
    RAISE NOTICE '  - 8 個索引';
    RAISE NOTICE '  - 1 個統計視圖';
    RAISE NOTICE '  - 2 個觸發器';
    RAISE NOTICE '=========================================';
END $$;
