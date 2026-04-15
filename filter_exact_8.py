#!/usr/bin/env python3
"""
精確過濾出8筆違規（根據使用者指定的 person IDs）
"""
import json
import re

# 讀取過濾結果
with open('/tmp/filtered_report_758.json', 'r') as f:
    filtered = json.load(f)

# 使用者指定的8筆（時間 + person IDs）
specified = {
    '09:45:18': ['179', '176'],
    '09:34:44': ['168'],
    '09:32:40': ['167'],
    '09:30:33': ['164', '163'],
    '09:29:39': ['162'],
    '09:01:37': ['97', '82', '95', '98'],
    '09:01:15': ['94', '82', '95'],
    '08:58:39': ['84', '82']
}

confirmed_items = filtered['confirmed_items']

# 過濾出精確符合的 8 筆
final_8 = []
for item in confirmed_items:
    time = item['time_display']
    if time in specified:
        # 檢查 person_ids 是否符合
        item_ids = set(item['person_ids'].replace(' ', '').split(','))
        specified_ids = set(specified[time])

        if item_ids == specified_ids:
            final_8.append(item)
            print(f"✓ {time} {item['mesg']}")

print(f"\n總共: {len(final_8)} 筆")

# 按時間排序（新到舊）
final_8.sort(key=lambda x: x['time_display'], reverse=True)

# 儲存結果
with open('/tmp/final_8_items.json', 'w', encoding='utf-8') as f:
    json.dump(final_8, f, ensure_ascii=False, indent=2)

print(f"已儲存至 /tmp/final_8_items.json")
