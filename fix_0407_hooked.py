#!/usr/bin/env python3
"""
修正 4/7 高處作業審核頁面
1. 刪除標題中的「（掛鉤問題）」
2. ID 相同的合併，但上午和下午各保留一筆
"""

import json
import re
from pathlib import Path
from datetime import datetime

html_path = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/高處作業_審核.html')

with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

print("=" * 60)
print("修正 4/7 高處作業審核頁面")
print("=" * 60)

# 1. 修改標題
print("\n步驟 1: 修改標題")
old_title = '高處作業（掛鉤問題） 違規審核'
new_title = '高處作業 違規審核'

html_content = html_content.replace(
    f'<title>{old_title} - 2026-04-07</title>',
    f'<title>{new_title} - 2026-04-07</title>'
)
print(f"  ✓ 標題已更新：{new_title}")

# 2. 讀取並合併 DATA
print("\n步驟 2: 合併相同 ID 的記錄")

match = re.search(r'const DATA = (\[.*?\]);', html_content, re.DOTALL)
if not match:
    print("  ✗ 找不到 DATA 數組")
    exit(1)

data_str = match.group(1)
data = json.loads(data_str)

print(f"  原始記錄：{len(data)} 筆")

# 依 person_id 和上午/下午分組
grouped = {}  # {(person_id, period): [records]}

for item in data:
    person_id = item['person_ids']
    time_str = item['time_display']  # 格式: HH:MM:SS

    # 判斷上午（06:00-12:00）或下午（12:00-18:00）
    hour = int(time_str.split(':')[0])
    if 6 <= hour < 12:
        period = 'morning'
    else:
        period = 'afternoon'

    key = (person_id, period)
    if key not in grouped:
        grouped[key] = []
    grouped[key].append(item)

# 每組只保留第一筆（時間最早的）
merged_data = []
for (person_id, period), items in grouped.items():
    # 按時間排序，取最早的一筆
    items.sort(key=lambda x: x['time'])
    merged_data.append(items[0])

# 按時間重新排序
merged_data.sort(key=lambda x: x['time'])

# 重新分配 id（從 1 開始）
for idx, item in enumerate(merged_data, 1):
    item['id'] = idx

print(f"  合併後記錄：{len(merged_data)} 筆")
print(f"  減少了：{len(data) - len(merged_data)} 筆")

# 統計
morning_count = sum(1 for item in merged_data if 6 <= int(item['time_display'].split(':')[0]) < 12)
afternoon_count = len(merged_data) - morning_count
print(f"  上午：{morning_count} 筆，下午：{afternoon_count} 筆")

# 更新 DATA 數組
new_data_json = json.dumps(merged_data, ensure_ascii=False)
html_content = html_content.replace(match.group(0), f'const DATA = {new_data_json};')

# 3. 重新生成卡片 HTML（需要完全重寫）
print("\n步驟 3: 重新生成卡片 HTML")
print("  註：由於記錄數量大幅減少，建議重新執行 regenerate_hooked_only_v2.py")
print("      或手動刪除舊的卡片並重新生成")

# 儲存
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n完成！")
print(f"已儲存至：{html_path}")
print(f"\n建議：請重新執行 regenerate_hooked_only_v2.py 來完整更新頁面")
