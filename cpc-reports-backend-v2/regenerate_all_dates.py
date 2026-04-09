#!/usr/bin/env python3
"""
重新產生所有歷史日期的審核頁面（使用 API 版本）
"""

import sys
from pathlib import Path
from datetime import datetime

# 加入路徑
sys.path.insert(0, str(Path(__file__).parent))

from generate_daily_review import (
    fetch_api_data, categorize_logs, consolidate_confined_space_logs,
    generate_review_html, generate_report_html, generate_manager_report_html,
    generate_card_html, update_index_html, BASE_DIR, CATEGORIES,
    extract_id_from_mesg
)
import json

def generate_for_date(date_str):
    """產生指定日期的審核工具"""
    print(f"\n=== 產生 {date_str} ===")

    year, month, day = date_str.split('-')
    date_dir = BASE_DIR / year / month / day
    date_dir.mkdir(parents=True, exist_ok=True)

    # 取得資料
    all_logs = []
    for camera_id in ['758', '837']:
        logs = fetch_api_data(date_str, camera_id)
        print(f"  Camera {camera_id}: {len(logs)} 筆")
        all_logs.extend(logs)

    if not all_logs:
        print(f"  沒有資料，跳過")
        return

    # 分類
    categorized = categorize_logs(all_logs)

    for category, logs in categorized.items():
        if not logs or category == '待分類':
            continue

        # 局限空間合併
        if category == '局限空間':
            logs = consolidate_confined_space_logs(logs)

        # 高處作業合併重複 ID
        if category == '高處作業':
            # 按 ID 分組，每個 ID 只保留一筆
            seen_ids = {}
            unique_logs = []
            for log in logs:
                mesg = log.get('mesg', '')
                person_id = extract_id_from_mesg(mesg)
                if person_id and person_id not in seen_ids:
                    seen_ids[person_id] = True
                    unique_logs.append(log)
                elif not person_id:
                    unique_logs.append(log)

            skipped = len(logs) - len(unique_logs)
            if skipped > 0:
                print(f"  {category}: 合併重複 ID，跳過 {skipped} 筆")
            logs = unique_logs

        print(f"  產生 {category} ({len(logs)} 筆)")

        # 產生資料
        data = []
        cards_html = ''

        for idx, log in enumerate(logs):
            item = {
                'id': log.get('id', idx),
                'mesg': log.get('mesg', ''),
                'person_ids': str(log.get('person_id', '')),
                'time_display': log.get('time', ''),
                'image_url': log.get('image_url', ''),
                'video_url': log.get('video_url', ''),
                'type': log.get('type', '')
            }
            data.append(item)
            cards_html += generate_card_html(item, item['id'])

        data_json = json.dumps(data, ensure_ascii=False)

        # 檔案路徑
        review_filename = f"{category}_審核.html"
        report_filename = f"{category}_報告.html"
        manager_filename = f"{category}_報告_管理版.html"

        # 產生審核頁面
        html_content = generate_review_html(
            category=category,
            date_str=date_str,
            total=len(data),
            cards_html=cards_html,
            data_json=data_json,
            report_path=manager_filename
        )

        with open(date_dir / review_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # 產生報告頁面
        report_content = generate_report_html(category, date_str)
        with open(date_dir / report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 產生管理版報告
        manager_content = generate_manager_report_html(category, date_str)
        with open(date_dir / manager_filename, 'w', encoding='utf-8') as f:
            f.write(manager_content)

        print(f"    ✓ {review_filename}")


def main():
    # 要重新產生的日期
    dates = [
        '2026-03-30',
        '2026-03-31',
        '2026-04-01',
        '2026-04-02',
        '2026-04-07',
        '2026-04-08',
    ]

    print("=== 重新產生所有日期 (API 版本) ===")

    for date_str in dates:
        generate_for_date(date_str)

    # 更新 index.html
    print("\n更新 index.html...")
    update_index_html(BASE_DIR)

    print("\n=== 完成 ===")


if __name__ == '__main__':
    main()
