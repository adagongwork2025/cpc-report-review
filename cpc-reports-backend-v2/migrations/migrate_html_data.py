#!/usr/bin/env python3
"""
資料遷移工具：從 HTML 檔案提取 DATA 陣列，匯入 PostgreSQL 資料庫

使用方式:
    python migrations/migrate_html_data.py
"""
import re
import json
import sys
from pathlib import Path
from datetime import datetime

# 將 app 加入 Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import DetectionLog, ReviewState
from app.config import settings


def extract_data_from_html(html_path: Path) -> list:
    """
    從 HTML 檔案中提取 DATA 陣列

    Args:
        html_path: HTML 檔案路徑

    Returns:
        list: DATA 陣列
    """
    content = html_path.read_text(encoding='utf-8')

    # 正則匹配 const DATA = [...];
    match = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
    if match:
        data_str = match.group(1)
        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            print(f"  ⚠️  JSON 解析失敗: {e}")
            return []
    return []


def parse_date_from_path(html_path: Path) -> tuple:
    """
    從檔案路徑解析日期和類別

    路徑格式: .../2026/04/07/高處作業_審核.html
    """
    parts = html_path.parts

    year = parts[-4]
    month = parts[-3]
    day = parts[-2]
    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # 從檔名提取類別
    filename = html_path.stem
    category = filename.replace('_審核', '').replace('_報告', '').replace('_報告_管理版', '')

    return date_str, category


def migrate_detection_logs(html_dir: Path, session):
    """
    遷移偵測記錄到資料庫

    Args:
        html_dir: HTML 檔案根目錄
        session: 資料庫 session
    """
    # 找到所有審核頁面
    audit_files = list(html_dir.rglob('*_審核.html'))

    print(f"\n找到 {len(audit_files)} 個審核頁面")
    print("=" * 60)

    total_imported = 0
    total_skipped = 0

    for html_file in audit_files:
        date_str, category = parse_date_from_path(html_file)

        print(f"\n處理: {date_str} / {category}")
        print(f"  檔案: {html_file.name}")

        # 提取 DATA
        data_array = extract_data_from_html(html_file)

        if not data_array:
            print(f"  ⚠️  無資料")
            continue

        print(f"  找到 {len(data_array)} 筆記錄")

        # 匯入資料庫
        imported = 0
        skipped = 0

        for item in data_array:
            try:
                # 檢查是否已存在（避免重複匯入）
                existing = session.query(DetectionLog).filter_by(
                    date=date_str,
                    category=category,
                    original_id=item['id']
                ).first()

                if existing:
                    skipped += 1
                    continue

                # 解析時間
                try:
                    time_str = item['time']
                    if time_str.endswith('Z'):
                        time_str = time_str.replace('Z', '+00:00')
                    detection_time = datetime.fromisoformat(time_str)
                except Exception as e:
                    print(f"    ⚠️  時間解析失敗 (ID {item['id']}): {e}")
                    # 使用預設時間
                    detection_time = datetime.fromisoformat(f"{date_str}T00:00:00")

                # 建立偵測記錄
                log = DetectionLog(
                    original_id=item['id'],
                    detection_time=detection_time,
                    time_display=item.get('time_display', ''),
                    message=item.get('mesg', ''),
                    type=item.get('type', ''),
                    person_ids=item.get('person_ids', ''),
                    image_url=item.get('image_url', ''),
                    video_url=item.get('video_url', ''),
                    date=date_str,
                    category=category
                )
                session.add(log)
                session.flush()  # 取得 log.id

                # 同時建立審核狀態記錄（初始為 pending）
                state = ReviewState(
                    detection_log_id=log.id,
                    date=date_str,
                    category=category,
                    status='pending'
                )
                session.add(state)

                imported += 1

            except Exception as e:
                print(f"    ❌ 錯誤 (ID {item.get('id', '?')}): {e}")
                continue

        # 提交這個檔案的資料
        try:
            session.commit()
            print(f"  ✓ 匯入 {imported} 筆，跳過 {skipped} 筆（已存在）")
            total_imported += imported
            total_skipped += skipped
        except Exception as e:
            print(f"  ❌ 提交失敗: {e}")
            session.rollback()

    print("\n" + "=" * 60)
    print(f"總計：匯入 {total_imported} 筆，跳過 {total_skipped} 筆")


def show_database_stats(session):
    """顯示資料庫統計"""
    from sqlalchemy import func

    print("\n" + "=" * 60)
    print("資料庫統計")
    print("=" * 60)

    stats = session.query(
        DetectionLog.date,
        DetectionLog.category,
        func.count(DetectionLog.id).label('count')
    ).group_by(
        DetectionLog.date,
        DetectionLog.category
    ).order_by(
        DetectionLog.date.desc()
    ).all()

    if not stats:
        print("（目前無資料）")
        return

    for date, category, count in stats:
        print(f"{date} {category:10s} : {count:4d} 筆")

    total = session.query(func.count(DetectionLog.id)).scalar()
    print(f"\n總計: {total} 筆記錄")


def main():
    """主程式"""
    print("=" * 60)
    print("中油偵測報告系統 - 資料遷移工具")
    print("從 HTML 檔案匯入資料到 PostgreSQL")
    print("=" * 60)

    # 建立資料庫連線
    try:
        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        print(f"\n✓ 資料庫連線成功: {settings.DATABASE_URL}")
    except Exception as e:
        print(f"\n❌ 資料庫連線失敗: {e}")
        print("\n請確認:")
        print("1. PostgreSQL 服務已啟動")
        print("2. 資料庫 cpc_reports 已建立")
        print("3. .env 檔案中的 DATABASE_URL 設定正確")
        return

    try:
        # HTML 檔案目錄
        html_dir = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026')

        if not html_dir.exists():
            print(f"\n❌ 目錄不存在: {html_dir}")
            print("\n請確認路徑是否正確")
            return

        print(f"✓ HTML 目錄: {html_dir}")

        # 執行遷移
        migrate_detection_logs(html_dir, session)

        # 顯示統計
        show_database_stats(session)

        print("\n" + "=" * 60)
        print("✅ 遷移完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 遷移失敗: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == '__main__':
    main()
