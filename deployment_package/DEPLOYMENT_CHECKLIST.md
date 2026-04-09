# 部署檢查清單 / Deployment Checklist

## 部署前檢查 / Pre-deployment

- [ ] 確認所有 HTML 檔案完整無誤
- [ ] 確認圖片檔案已包含（ID21_thumbnail.jpg）
- [ ] 確認 index.html 中的 REPORT_DATA 陣列正確
- [ ] 測試 API 端點連線（apigatewayiseek.intemotech.com）

## 部署步驟 / Deployment Steps

- [ ] 上傳檔案到伺服器或雲端儲存
- [ ] 設定 Web Server（Nginx/Apache）或啟用靜態網站託管
- [ ] 啟用 HTTPS（必須）
- [ ] 設定 CORS（如有跨域需求）
- [ ] 測試主頁面載入（index.html）

## 功能測試 / Functional Testing

- [ ] 測試主頁面顯示所有報告列表
- [ ] 測試點擊「審核」連結進入審核頁面
- [ ] 測試影片播放功能
- [ ] 測試縮圖顯示
- [ ] 測試審核按鈕（違規/誤報）
- [ ] 測試「產生偵測報告」按鈕
- [ ] 測試報告頁面顯示
- [ ] 測試未審核時報告按鈕為灰色

## 安全性檢查 / Security Check

- [ ] 確認使用 HTTPS
- [ ] 檢查是否有敏感資訊外洩
- [ ] 設定適當的 CORS policy
- [ ] 檢查 API 端點的存取權限

## 效能檢查 / Performance Check

- [ ] 測試頁面載入速度
- [ ] 測試影片載入速度
- [ ] 檢查瀏覽器 Console 是否有錯誤
- [ ] 測試不同瀏覽器相容性（Chrome, Safari, Firefox）

## 已知資料說明 / Known Data Notes

### 特殊處理記錄

1. **4/2 局限空間 - ID 21**
   - 手動新增的記錄
   - 缺少生命偵測器
   - 時間：09:04:55
   - 縮圖：ID21_thumbnail.jpg

2. **4/7 高處作業**
   - 已合併重複 ID（559 → 70 筆）
   - 上午/下午各保留一筆
   - 時間由新到舊排序
   - 標題已移除「（掛鉤問題）」

3. **已移除的資料**
   - 4/2 高處作業（已刪除）
   - 3/31 局限空間（已刪除）

### 目前包含的日期

- 3/30：高處作業、局限空間
- 3/31：高處作業
- 4/1：高處作業
- 4/2：局限空間
- 4/7：高處作業

---

## 緊急聯絡 / Emergency Contact

如遇部署問題，請檢查：
1. 瀏覽器 Console 的錯誤訊息
2. Network 面板的 API 請求狀態
3. 部署說明.md 中的疑難排解章節

---

**部署日期 / Deployment Date**: _______________
**部署人員 / Deployed By**: _______________
**環境 / Environment**: □ Production  □ Staging  □ Testing
**URL**: _______________
