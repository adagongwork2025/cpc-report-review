#!/usr/bin/env python3
"""
重新產生高處作業審核工具，只包含掛鉤問題（使用完整範本）
"""

import json
import re
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# 從 generate_daily_review.py 導入需要的函式
import sys
sys.path.insert(0, '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢')
from generate_daily_review import (
    generate_review_html,
    generate_card_html,
    get_display_tag,
    extract_id_from_mesg
)

# API 設定
API_URL = 'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter'
CAMERA_ID = '758'  # 高處作業
DATE = '2026-04-07'
CATEGORY = '高處作業（掛鉤問題）'

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
                total = result.get('total', 0)
                total_pages = result.get('total_pages', 1)

                all_logs.extend(logs)

                if page == 1 and total > per_page:
                    print(f"    總共 {total} 筆，分 {total_pages} 頁取得...")

                if page >= total_pages or not logs:
                    break
                page += 1

        except Exception as e:
            print(f"API 錯誤: {e}")
            break

    return all_logs

def filter_and_prepare_hooked_logs(logs):
    """篩選掛鉤問題並準備資料"""
    hooked_logs = []

    for log in logs:
        if log.get('type', '') != 'hooked':
            continue

        # 解析時間
        time_str = log.get('time', '')
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            time_display = dt.strftime('%H:%M:%S')
        except:
            time_display = time_str

        # 提取人員 ID
        mesg = log.get('mesg', '')
        mesg_clean, person_id = extract_id_from_mesg(mesg)

        # 準備圖片和影片 URL
        image_key = log.get('key', '')
        video_key = log.get('video_key', '')

        # 處理圖片 URL - 使用 API Gateway 端點
        if image_key:
            image_url = f'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image?key={image_key}'
        else:
            image_url = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect fill="%23ddd" width="400" height="300"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3E無圖片%3C/text%3E%3C/svg%3E'

        # 處理影片 URL - 從 video_key 中提取 path
        video_url = ''
        if video_key:
            # video_key 格式: offset:123,container_id:80,host:192.168.53.14,path:/app/image/...
            path_match = re.search(r'path:([^,]+)', video_key)
            if path_match:
                video_path = path_match.group(1)
                video_url = f"https://apigatewayiseek.intemotech.com/vision_logic/video?key={video_path}"

        # 準備資料項目
        item = {
            'mesg': mesg,
            'type': 'hooked',
            'time_display': time_display,
            'person_ids': person_id,
            'image_url': image_url,
            'video_url': video_url,
            'time': time_str
        }

        hooked_logs.append(item)

    return hooked_logs

def main():
    print("=" * 60)
    print("重新產生高處作業審核工具（只含掛鉤問題）")
    print("使用完整範本樣式")
    print("=" * 60)

    # 取得資料
    all_logs = fetch_data()
    print(f"\n取得 {len(all_logs)} 筆記錄")

    # 篩選並準備掛鉤問題
    hooked_logs = filter_and_prepare_hooked_logs(all_logs)
    print(f"篩選出 {len(hooked_logs)} 筆掛鉤問題")

    # 產生卡片 HTML
    print("\n產生卡片 HTML...")
    cards_html = []
    for idx, item in enumerate(hooked_logs, 1):
        item['id'] = idx  # 添加 id 字段供前端使用
        cards_html.append(generate_card_html(item, idx))

    cards_html_str = '\n'.join(cards_html)

    # 準備資料 JSON（用於前端）
    data_json = json.dumps(hooked_logs, ensure_ascii=False)

    # 產生完整 HTML（使用 generate_review_html）
    print("產生完整審核頁面...")
    report_path = '高處作業_報告_管理版.html'

    html = generate_review_html(
        category=CATEGORY,
        date_str=DATE,
        total=len(hooked_logs),
        cards_html=cards_html_str,
        data_json=data_json,
        report_path=report_path,
        preset_times=None
    )

    # 儲存檔案
    output_file = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/高處作業_審核.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✓ 已更新審核頁面: {output_file}")
    print(f"  - 篩選後：{len(hooked_logs)} 筆（只含掛鉤問題）")
    print(f"  - 樣式：使用完整範本（與 4/01 相同）")
    print(f"  - 檔案大小：{len(html) / 1024:.1f} KB")

if __name__ == '__main__':
    main()
