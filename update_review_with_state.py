#!/usr/bin/env python3
"""
更新審核頁面，預設已確認和已刪除的狀態
"""
import json
import re

# 讀取過濾結果
with open('/tmp/filtered_report_758.json', 'r') as f:
    filtered = json.load(f)

confirmed_ids = filtered['confirmed_ids']
deleted_ids = filtered['deleted_ids']

print(f"確認: {len(confirmed_ids)} 筆")
print(f"刪除: {len(deleted_ids)} 筆")

# 讀取審核頁面
review_file = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10/高處B_審核.html'
with open(review_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 替換 confirmedIds 和 deletedIds 的初始化
confirmed_ids_str = ','.join(map(str, confirmed_ids))
deleted_ids_str = ','.join(map(str, deleted_ids))

html = re.sub(
    r'let confirmedIds = new Set\(\);',
    f'let confirmedIds = new Set([{confirmed_ids_str}]);',
    html
)

html = re.sub(
    r'let deletedIds = new Set\(\);',
    f'let deletedIds = new Set([{deleted_ids_str}]);',
    html
)

# 寫回檔案
with open(review_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✓ 已更新審核頁面")

# 產生報告資料
confirmed_items = filtered['confirmed_items']

# 讀取報告模板
report_file = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10/高處B_報告_管理版.html'
with open(report_file, 'r', encoding='utf-8') as f:
    report_html = f.read()

# 產生報告 JavaScript 資料
report_data_js = json.dumps({
    'date': '2026-04-10',
    'category': '高處B',
    'items': confirmed_items
}, ensure_ascii=False)

# 在報告頁面嵌入資料（替換從 localStorage 載入的部分）
report_html = re.sub(
    r'const stored = localStorage\.getItem\(REPORT_KEY\);[\s\S]*?function showNoViolationWithVideos\(\)',
    f'''const stored = null; // 使用嵌入資料
            reportData = {report_data_js};
            if (reportData.items && reportData.items.length > 0) {{
                render();
            }} else {{
                showNoViolationWithVideos();
            }}
        }}

        function showNoViolationWithVideos()''',
    report_html
)

# 寫回報告檔案
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report_html)

print(f"✓ 已更新報告頁面（嵌入 {len(confirmed_items)} 筆資料）")
