#!/bin/bash

# 中油偵測報告系統 - 部署腳本
# 目標：https://cpcreportlist.intemotech.com/
# 伺服器：192.168.53.96

set -e  # 發生錯誤時停止

# ================================
# 設定區（請填寫正確資訊）
# ================================

# SSH 使用者和主機
SSH_USER="請填寫SSH使用者名稱"  # 例如：root, admin, ubuntu
SSH_HOST="192.168.53.96"

# 遠端網站根目錄
REMOTE_DIR="請填寫網站根目錄路徑"  # 例如：/var/www/cpc-reports, /usr/share/nginx/html

# 本地目錄
LOCAL_DIR="/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢"

# ================================
# 檢查設定
# ================================

if [[ "$SSH_USER" == "請填寫SSH使用者名稱" ]]; then
    echo "❌ 錯誤：請先在腳本中設定 SSH_USER"
    echo "   編輯檔案：deploy.sh"
    echo "   修改 SSH_USER 為實際的 SSH 使用者名稱"
    exit 1
fi

if [[ "$REMOTE_DIR" == "請填寫網站根目錄路徑" ]]; then
    echo "❌ 錯誤：請先在腳本中設定 REMOTE_DIR"
    echo "   編輯檔案：deploy.sh"
    echo "   修改 REMOTE_DIR 為實際的網站根目錄"
    exit 1
fi

# ================================
# 部署函數
# ================================

deploy_date() {
    local DATE_PATH=$1
    local CATEGORY=$2

    echo "📤 部署 $DATE_PATH - $CATEGORY"

    # 上傳審核頁面
    scp "${LOCAL_DIR}/${DATE_PATH}/${CATEGORY}_審核.html" \
        "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/${DATE_PATH}/"

    # 上傳報告頁面
    scp "${LOCAL_DIR}/${DATE_PATH}/${CATEGORY}_報告_管理版.html" \
        "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/${DATE_PATH}/"
}

deploy_index() {
    echo "📤 部署 index.html"
    scp "${LOCAL_DIR}/index.html" \
        "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/"
}

# ================================
# 主程式
# ================================

echo "========================================="
echo "中油偵測報告系統 - 部署工具"
echo "========================================="
echo ""
echo "目標伺服器：${SSH_USER}@${SSH_HOST}"
echo "目標目錄：${REMOTE_DIR}"
echo ""

# 測試 SSH 連線
echo "🔍 測試 SSH 連線..."
if ! ssh -o ConnectTimeout=5 "${SSH_USER}@${SSH_HOST}" "echo '連線成功'" 2>/dev/null; then
    echo "❌ SSH 連線失敗"
    echo "   請檢查："
    echo "   1. SSH_USER 是否正確"
    echo "   2. SSH_HOST 是否可連線"
    echo "   3. SSH 金鑰是否已設定"
    exit 1
fi

echo "✅ SSH 連線成功"
echo ""

# 選擇部署模式
echo "請選擇部署模式："
echo "1) 只部署 4/13 高處A 和高處B"
echo "2) 只部署 4/14 高處作業"
echo "3) 部署 4/13 和 4/14"
echo "4) 只部署 index.html"
echo "5) 全部部署（包含 index.html）"
echo ""
read -p "請選擇 (1-5): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "📦 部署 4/13 高處A 和高處B..."
        deploy_date "2026/04/13" "高處A"
        deploy_date "2026/04/13" "高處B"
        ;;
    2)
        echo ""
        echo "📦 部署 4/14 高處作業..."
        deploy_date "2026/04/14" "高處作業"
        ;;
    3)
        echo ""
        echo "📦 部署 4/13 和 4/14..."
        deploy_date "2026/04/13" "高處A"
        deploy_date "2026/04/13" "高處B"
        deploy_date "2026/04/14" "高處作業"
        ;;
    4)
        echo ""
        echo "📦 部署 index.html..."
        deploy_index
        ;;
    5)
        echo ""
        echo "📦 部署全部..."
        deploy_date "2026/04/13" "高處A"
        deploy_date "2026/04/13" "高處B"
        deploy_date "2026/04/14" "高處作業"
        deploy_index
        ;;
    *)
        echo "❌ 無效的選擇"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""
echo "請檢查網站："
echo "https://cpcreportlist.intemotech.com/"
echo ""
echo "如需清除瀏覽器快取，請使用："
echo "開啟 清除快取.html"
echo ""
