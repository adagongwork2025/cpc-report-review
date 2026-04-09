#!/usr/bin/env python3
"""
更新 ID 21 的縮圖 URL
"""

import json
import re
from pathlib import Path

html_path = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/02/局限空間_審核.html')

with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# 新的圖片 URL（相對路徑）
new_image_url = "ID21_thumbnail.jpg"

# 舊的占位圖 URL
old_placeholder = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23ddd' width='400' height='300'/%3E%3Ctext fill='%23999' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E無圖片%3C/text%3E%3C/svg%3E"

print("更新 ID 21 的縮圖...")

# 1. 更新 DATA 數組中的 image_url
match = re.search(r'const DATA = (\[.*?\]);', html_content, re.DOTALL)
if match:
    data_str = match.group(1)
    data = json.loads(data_str)

    for item in data:
        if item.get('person_ids') == '21' and item.get('image_url') == old_placeholder:
            item['image_url'] = new_image_url
            print(f"  ✓ 已更新 DATA 中的 image_url")
            break

    new_data_str = json.dumps(data, ensure_ascii=False)
    html_content = html_content.replace(match.group(0), f'const DATA = {new_data_str};')

# 2. 更新卡片 HTML 中的 img src (ID 700000)
html_content = html_content.replace(
    f'<img src="{old_placeholder}" alt="預覽圖" id="thumb-700000">',
    f'<img src="{new_image_url}" alt="預覽圖" id="thumb-700000">'
)
print(f"  ✓ 已更新卡片 HTML 中的 img src")

# 儲存
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"\n完成！")
print(f"圖片路徑: {new_image_url}")
