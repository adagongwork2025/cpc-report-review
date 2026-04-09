# 中油偵測報告系統 - 資料備份 (2026-04-09)

## 備份檔案

- `cpc_confirmed_violations_20260409.csv` - 所有已確認的違規記錄

## 統計摘要

| 日期 | 類別 | 確認數 |
|------|------|--------|
| 2026-03-30 | 局限空間 | 4 |
| 2026-03-30 | 高處作業 | 8 |
| 2026-03-31 | 高處作業 | 6 |
| 2026-04-01 | 高處作業 | 27 |
| 2026-04-02 | 局限空間 | 2 |
| 2026-04-07 | 高處作業 | 7 |
| **總計** | | **54 筆** |

## CSV 欄位說明

| 欄位 | 說明 |
|------|------|
| date | 日期 (YYYY-MM-DD) |
| category | 類別 (高處作業/局限空間) |
| detection_log_id | 資料庫內部 ID |
| original_id | 原始 API ID |
| message | 違規訊息 |
| status | 狀態 (confirmed) |
| note | 備註 |

## 還原方法

如需還原資料到資料庫，可執行以下 SQL：

```sql
-- 1. 先更新 review_states 表
UPDATE review_states
SET status = 'confirmed'
WHERE detection_log_id IN (
    -- 從 CSV 取得的 detection_log_id 列表
    2, 77, 95, 119,  -- 3/30 局限空間
    151, 153, 155, 156, 157, 165, 168, 177,  -- 3/30 高處作業
    452, 491, 541, 545, 554, 589,  -- 3/31 高處作業
    593, 600, 602, 603, 607, 609, 620, 621, 642, 658, 668, 673, 682, 699, 700, 701, 702, 707, 708, 711, 715, 725, 748, 752, 757, 758, 759,  -- 4/1 高處作業
    763, 766,  -- 4/2 局限空間
    790, 795, 802, 806, 807, 812, 825  -- 4/7 高處作業
);

-- 2. 同時更新 review_actions 表
DELETE FROM review_actions WHERE detection_log_id IN (...上述 ID...);
INSERT INTO review_actions (detection_log_id, date, category, action)
SELECT detection_log_id, date, category, 'confirmed'
FROM detection_logs WHERE id IN (...上述 ID...);
```

## 伺服器資訊

- 主機：192.168.53.96
- 網站：https://cpcreportlist.intemotech.com/
- API：http://192.168.53.96:8001/api/v1
- 資料庫：PostgreSQL (cpc_reports)
- 使用者：cpc_user

## 備份日期

2026-04-09 12:05
