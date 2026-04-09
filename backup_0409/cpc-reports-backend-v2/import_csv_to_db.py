#!/usr/bin/env python3
"""
從 CSV 匯入確認的違規資料到資料庫
"""

import csv
import json
import urllib.request
from pathlib import Path
from datetime import datetime

API_BASE = 'http://192.168.53.96:8001/api/v1'

# 要匯入的 CSV 檔案
CSV_FILES = [
    '/Users/ada/Downloads/偵測報告_高處作業_20260407.csv',
    '/Users/ada/Downloads/偵測報告_高處作業_20260401 (1).csv',
    '/Users/ada/Downloads/偵測報告_高處作業_20260331.csv',
    '/Users/ada/Downloads/偵測報告_高處作業_20260330 (1).csv',
    '/Users/ada/Downloads/偵測報告_局限空間_20260402.csv',
    '/Users/ada/Downloads/偵測報告_局限空間_20260330 (3).csv',
]


def parse_csv(filepath):
    """解析 CSV 檔案"""
    items = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append({
                'date': row['日期'],
                'time': row['時間'],
                'category': row['類型'],
                'mesg': row['違規事項'],
                'person_id': row['人員ID'],
                'note': row.get('備註', ''),
                'image_url': row['圖片連結'],
                'video_url': row['影片連結'],
            })
    return items


def get_detection_logs(date, category):
    """從 API 取得該日期類別的所有偵測記錄"""
    url = f"{API_BASE}/detection-logs/{date}/{urllib.parse.quote(category)}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('success'):
                return result['data']['items']
    except Exception as e:
        print(f"  取得偵測記錄失敗: {e}")
    return []


def find_matching_log(csv_item, logs):
    """根據時間和人員 ID 找到對應的偵測記錄"""
    csv_time = csv_item['time']
    csv_person_id = csv_item['person_id']

    for log in logs:
        # 比對時間（取時間部分）
        log_time = log.get('time_display', '')
        if log_time and csv_time in log_time:
            # 比對人員 ID
            log_person_ids = str(log.get('person_ids', ''))
            if csv_person_id in log_person_ids or log_person_ids in csv_person_id:
                return log

        # 也檢查圖片 URL
        if csv_item['image_url'] == log.get('image_url'):
            return log

    return None


def submit_review_actions(date, category, actions):
    """提交審核動作到 API"""
    url = f"{API_BASE}/reviews/actions/bulk"
    payload = {
        'date': date,
        'category': category,
        'actions': actions,
        'reviewer_ip': 'csv_import'
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"  提交失敗: {e}")
        return None


def main():
    print("=== CSV 匯入工具 ===\n")

    total_imported = 0
    total_failed = 0

    # 按日期和類別分組
    grouped = {}

    for filepath in CSV_FILES:
        if not Path(filepath).exists():
            print(f"檔案不存在: {filepath}")
            continue

        print(f"讀取: {Path(filepath).name}")
        items = parse_csv(filepath)
        print(f"  找到 {len(items)} 筆資料")

        for item in items:
            key = (item['date'], item['category'])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)

    print(f"\n共 {len(grouped)} 個日期/類別組合\n")

    # 處理每個組合
    for (date, category), items in sorted(grouped.items()):
        print(f"處理: {date} {category} ({len(items)} 筆)")

        # 取得該日期的偵測記錄
        logs = get_detection_logs(date, category)
        if not logs:
            print(f"  無法取得偵測記錄，跳過")
            total_failed += len(items)
            continue

        print(f"  資料庫有 {len(logs)} 筆偵測記錄")

        # 比對並建立審核動作
        actions = []
        matched = 0

        for item in items:
            log = find_matching_log(item, logs)
            if log:
                actions.append({
                    'detection_log_id': log['id'],
                    'action': 'confirmed',
                    'note': item['note'] if item['note'] else None
                })
                matched += 1
            else:
                print(f"  找不到對應記錄: {item['time']} ID:{item['person_id']}")

        print(f"  比對成功: {matched}/{len(items)}")

        if actions:
            result = submit_review_actions(date, category, actions)
            if result and result.get('success'):
                print(f"  ✓ 已匯入 {result['data']['confirmed_count']} 筆")
                total_imported += result['data']['confirmed_count']
            else:
                print(f"  ✗ 匯入失敗")
                total_failed += len(actions)

        print()

    print("=== 完成 ===")
    print(f"成功匯入: {total_imported} 筆")
    print(f"失敗: {total_failed} 筆")


if __name__ == '__main__':
    import urllib.parse
    main()
