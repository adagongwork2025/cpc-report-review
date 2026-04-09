#!/usr/bin/env python3
"""
篩選早上的高處作業記錄
"""

import json
import urllib.request
import ssl
from datetime import datetime

# API 設定
API_URL = 'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter'
CAMERA_ID = '758'  # 高處作業
DATE = '2026-04-07'

# 早上時段定義
MORNING_START = '06:00:00'
MORNING_END = '12:00:00'

def fetch_data():
    """取得 4/7 的資料"""
    all_logs = []
    page = 1
    per_page = 1000

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"取得 {DATE} 的高處作業資料...")

    while True:
        payload = {
            "start_time": f"{DATE}T00:00:00",
            "end_time": f"{DATE}T23:59:59",
            "camera_id": CAMERA_ID,
            "per_page": per_page,
            "page": page
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={'Content-Type': 'application/json'}
            )

            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                logs = result.get('logs', [])
                total_pages = result.get('total_pages', 1)

                all_logs.extend(logs)

                if page >= total_pages or not logs:
                    break
                page += 1

        except Exception as e:
            print(f"API 錯誤: {e}")
            break

    return all_logs

def filter_morning(logs):
    """篩選早上的記錄（只保留掛鉤問題）"""
    morning_logs = []

    for log in logs:
        time_str = log.get('time', '')
        log_type = log.get('type', '')

        # 只保留掛鉤問題
        if log_type != 'hooked':
            continue

        try:
            # 解析時間
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            time_only = dt.strftime('%H:%M:%S')

            # 判斷是否在早上時段
            if MORNING_START <= time_only < MORNING_END:
                morning_logs.append({
                    'time': dt.strftime('%H:%M:%S'),
                    'type': log.get('type', ''),
                    'mesg': log.get('mesg', ''),
                    'camera_id': log.get('camera_id', '')
                })
        except:
            continue

    return morning_logs

def main():
    # 取得資料
    all_logs = fetch_data()
    print(f"總共 {len(all_logs)} 筆記錄")

    # 篩選早上
    morning_logs = filter_morning(all_logs)
    print(f"早上時段 ({MORNING_START} - {MORNING_END}): {len(morning_logs)} 筆")

    # 統計類型
    type_count = {}
    for log in morning_logs:
        log_type = log['type']
        type_count[log_type] = type_count.get(log_type, 0) + 1

    print("\n=== 早上記錄統計 ===")
    for log_type, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
        print(f"{log_type}: {count} 筆")

    # 輸出所有記錄
    print(f"\n=== 所有掛鉤問題記錄（共 {len(morning_logs)} 筆）===")
    for i, log in enumerate(morning_logs, 1):
        print(f"{i}. [{log['time']}] {log['mesg']}")

    # 儲存 JSON
    output_file = f"/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/早上_高處作業.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(morning_logs, f, ensure_ascii=False, indent=2)

    print(f"\n完整資料已儲存至: {output_file}")

if __name__ == '__main__':
    main()
