#!/usr/bin/env python3
"""
取得 4/14 的 Camera 758 資料（高處作業）
"""
import json
import re
import urllib.request
import ssl

API_URL = "https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter"

def fetch_data(camera_id, date_str):
    """取得指定 camera 和日期的資料"""
    all_logs = []
    page = 1
    per_page = 1000

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"取得 Camera {camera_id} 於 {date_str} 的資料...")

    while True:
        payload = {
            "start_time": f"{date_str}T08:00:00",
            "end_time": f"{date_str}T13:30:00",
            "camera_id": camera_id,
            "per_page": per_page,
            "page": page
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0'
                }
            )

            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                logs = result.get('logs', [])
                total = result.get('total', 0)
                total_pages = result.get('total_pages', 1)

                all_logs.extend(logs)

                if page == 1:
                    print(f"  ✓ 取得 {total} 筆原始資料")
                    if total > per_page:
                        print(f"    總共 {total} 筆，分 {total_pages} 頁取得...")

                if page >= total_pages or not logs:
                    break

                page += 1

        except Exception as e:
            print(f"  ✗ API 錯誤: {e}")
            break

    return all_logs

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
date_str = '2026-04-14'

data_758 = fetch_data('758', date_str)

# 去重
data_758_unique = deduplicate_by_time_person(data_758)

# 儲存
with open('/tmp/758_unique_0414.json', 'w', encoding='utf-8') as f:
    json.dump(data_758_unique, f, ensure_ascii=False, indent=2)

print(f"\n已儲存:")
print(f"  Camera 758 (高處作業): {len(data_758_unique)} 筆 → /tmp/758_unique_0414.json")
