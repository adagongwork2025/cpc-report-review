#!/usr/bin/env python3
"""
恢復缺失日期的資料：從 API 取得偵測記錄並匯入資料庫
"""

import json
import ssl
import urllib.request
import sys
from pathlib import Path
from datetime import datetime

# 將 app 加入 Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import DetectionLog, ReviewState
from app.config import settings

API_URL = 'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter'

def fetch_api_data(date_str, camera_id):
    """呼叫 API 取得當天所有資料"""
    all_logs = []
    page = 1
    per_page = 1000

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    while True:
        payload = {
            "start_time": f"{date_str}T00:00:00",
            "end_time": f"{date_str}T23:59:59",
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

                if page == 1 and total > per_page:
                    print(f"    總共 {total} 筆，分 {total_pages} 頁取得...")

                if page >= total_pages or not logs:
                    break

                page += 1

        except Exception as e:
            print(f"  API 錯誤: {e}")
            break

    return all_logs


def categorize_logs(logs):
    """依 camera_id 和 type 分類"""
    categories_map = {
        '758': {
            'hooked': '高處作業',
            'harness': '高處作業',
        },
        '837': {
            'No_rescue_tripod': '局限空間',
            'No_venturi_tube': '局限空間',
            'No_air_breathing_apparatus_cylinder': '局限空間',
            'No_notice_board': '局限空間',
            'No_fire_extinguisher': '局限空間',
            'heartbeat': '局限空間',
            'confined_person': '局限空間',
            'confined_space': '局限空間',
        }
    }

    categorized = {'高處作業': [], '局限空間': []}

    for log in logs:
        camera_id = str(log.get('camera_id', ''))
        log_type = log.get('type', '')

        if camera_id in categories_map and log_type in categories_map[camera_id]:
            category = categories_map[camera_id][log_type]
            categorized[category].append(log)

    return categorized


def import_date(date_str, session):
    """匯入特定日期的資料"""
    print(f"\n處理: {date_str}")

    all_logs = []
    for camera_id in ['758', '837']:
        logs = fetch_api_data(date_str, camera_id)
        print(f"  Camera {camera_id}: {len(logs)} 筆")
        all_logs.extend(logs)

    if not all_logs:
        print(f"  無資料")
        return

    # 分類
    categorized = categorize_logs(all_logs)

    for category, logs in categorized.items():
        if not logs:
            continue

        print(f"  匯入 {category}: {len(logs)} 筆")

        imported = 0
        for log in logs:
            try:
                # 檢查是否已存在
                existing = session.query(DetectionLog).filter_by(
                    date=date_str,
                    category=category,
                    original_id=log['id']
                ).first()

                if existing:
                    continue

                # 解析時間
                try:
                    time_str = log['time']
                    if time_str.endswith('Z'):
                        time_str = time_str.replace('Z', '+00:00')
                    detection_time = datetime.fromisoformat(time_str)
                except:
                    detection_time = datetime.fromisoformat(f"{date_str}T00:00:00")

                # 建立記錄
                det_log = DetectionLog(
                    original_id=log['id'],
                    detection_time=detection_time,
                    time_display=log.get('time', ''),
                    message=log.get('mesg', ''),
                    type=log.get('type', ''),
                    person_ids=str(log.get('person_id', '')),
                    image_url=log.get('image_url', ''),
                    video_url=log.get('video_url', ''),
                    date=date_str,
                    category=category
                )
                session.add(det_log)
                session.flush()

                # 建立審核狀態
                state = ReviewState(
                    detection_log_id=det_log.id,
                    date=date_str,
                    category=category,
                    status='pending'
                )
                session.add(state)

                imported += 1

            except Exception as e:
                print(f"    錯誤: {e}")
                continue

        session.commit()
        print(f"    ✓ 已匯入 {imported} 筆")


def main():
    # 連接資料庫
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("=" * 60)
    print("恢復缺失日期的資料")
    print("=" * 60)

    # 要恢復的日期
    dates = ['2026-03-30', '2026-03-31', '2026-04-01', '2026-04-02']

    for date_str in dates:
        import_date(date_str, session)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)

    session.close()


if __name__ == '__main__':
    main()
