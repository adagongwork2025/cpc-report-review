#!/usr/bin/env python3
"""
取得 4/13 的 Camera 867 和 758 資料
"""
import requests
import json
from datetime import datetime

API_URL = "https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter"

def fetch_data(camera_id, date_str):
    """取得指定 camera 和日期的資料"""
    params = {
        'camera_id': camera_id,
        'start_time': f'{date_str}T00:00:00',
        'end_time': f'{date_str}T23:59:59',
        'page': 1,
        'page_size': 1000
    }

    print(f"取得 Camera {camera_id} 於 {date_str} 的資料...")
    response = requests.get(API_URL, params=params)

    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            items = result.get('data', {}).get('items', [])
            print(f"  ✓ 取得 {len(items)} 筆原始資料")
            return items
        else:
            print(f"  ✗ API 回應失敗: {result.get('message')}")
            return []
    else:
        print(f"  ✗ HTTP 錯誤: {response.status_code}")
        return []

def deduplicate_by_time_person(items):
    """根據時間和 person_ids 去重"""
    seen = set()
    unique = []

    for item in items:
        # 提取時間（只取到秒）
        time_str = item.get('time', '')
        time_key = time_str.split('T')[1][:8] if 'T' in time_str else ''

        # 提取 person IDs
        mesg = item.get('mesg', '')
        import re
        ids = sorted(re.findall(r'ID:(\d+)', mesg))
        ids_key = ','.join(ids)

        # 組合唯一鍵
        key = f"{time_key}_{ids_key}_{item.get('type')}"

        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"  去重後: {len(unique)} 筆")
    return unique

# 取得資料
date_str = '2026-04-13'

data_867 = fetch_data('867', date_str)
data_758 = fetch_data('758', date_str)

# 去重
data_867_unique = deduplicate_by_time_person(data_867)
data_758_unique = deduplicate_by_time_person(data_758)

# 儲存
with open('/tmp/867_unique_0413.json', 'w', encoding='utf-8') as f:
    json.dump(data_867_unique, f, ensure_ascii=False, indent=2)

with open('/tmp/758_unique_0413.json', 'w', encoding='utf-8') as f:
    json.dump(data_758_unique, f, ensure_ascii=False, indent=2)

print(f"\n已儲存:")
print(f"  Camera 867 (高處A): {len(data_867_unique)} 筆 → /tmp/867_unique_0413.json")
print(f"  Camera 758 (高處B): {len(data_758_unique)} 筆 → /tmp/758_unique_0413.json")
