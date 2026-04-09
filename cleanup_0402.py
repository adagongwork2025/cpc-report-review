#!/usr/bin/env python3
"""清理重複的 ID 21 記錄"""

import json
import re
from pathlib import Path

html_path = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/02/局限空間_審核.html')
with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# 找到 DATA 數組
match = re.search(r'const DATA = (\[.*?\]);', html_content, re.DOTALL)
if not match:
    print("找不到 DATA 數組")
    exit(1)

data_json = match.group(1)
data = json.loads(data_json)

print(f"原始資料：{len(data)} 筆")

# 移除重複的 ID 21 記錄（只保留一個）
seen_ids = set()
cleaned_data = []
for item in data:
    person_id = item['person_ids']
    if person_id == '21' and person_id in seen_ids:
        print(f"移除重複記錄：{item['mesg']}")
        continue
    seen_ids.add(person_id)
    cleaned_data.append(item)

print(f"清理後資料：{len(cleaned_data)} 筆")

# 重新生成 JSON
new_data_json = json.dumps(cleaned_data, ensure_ascii=False)

# 替換 HTML 中的 DATA
new_html = html_content.replace(match.group(0), f'const DATA = {new_data_json};')

# 移除重複的卡片 HTML（第一個 ID 700000 的卡片）
# 找到所有 data-id="700000" 的卡片
cards_700000 = list(re.finditer(r'<div class="card" data-id="700000"[^>]*>.*?</div>\s*</div>\s*</div>', new_html, re.DOTALL))
if len(cards_700000) > 1:
    # 移除第一個重複的卡片（保留第二個）
    card_to_remove = cards_700000[0].group(0)
    new_html = new_html.replace(card_to_remove, '', 1)
    print(f"移除重複的卡片 HTML")

# 儲存
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"\n✓ 清理完成")
