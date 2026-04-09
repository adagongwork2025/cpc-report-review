#!/usr/bin/env python3
"""
更新 4/2 局限空間審核頁面
1. 增加一筆資料：缺少生命偵測器/09:04:55/ID21
2. ID 425 那筆只保留缺少生命偵測器，刪除缺少安全帶
"""

import json
import re
from pathlib import Path

# 讀取原始 HTML 檔案
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
for item in data:
    print(f"  - {item['mesg']} ({item['time_display']})")

# 修改 ID 425 那筆資料
for item in data:
    if item['person_ids'] == '425':
        print(f"\n修改 ID 425：")
        print(f"  原本：{item['mesg']}")
        item['mesg'] = '缺少生命偵測器 ID:425'
        print(f"  修改後：{item['mesg']}")

# 檢查是否已有 ID 21 的記錄
has_id21 = any(item['person_ids'] == '21' for item in data)

if not has_id21:
    # 新增一筆資料（ID 21）
    new_record = {
        "id": 700000,  # 使用一個不衝突的 ID
        "time": "2026-04-02T09:04:55.000000",
        "time_display": "09:04:55",
        "mesg": "缺少生命偵測器 ID:21",
        "type": "heartbeat",
        "person_ids": "21",
        "image_url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23ddd' width='400' height='300'/%3E%3Ctext fill='%23999' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E無圖片%3C/text%3E%3C/svg%3E",
        "video_url": "https://apigatewayiseek.intemotech.com/vision_logic/video?key=/app/image/kafka_notify_videos/production/20260407/865_%E5%85%A8%E6%94%9D%E5%BD%B1%E6%A9%9F%E5%8D%80%E5%9F%9F_161716333.mp4"
    }

    # 將新記錄插入到最前面（依時間排序，09:04:55 是最早的）
    data.insert(0, new_record)

    print(f"\n新增記錄：")
    print(f"  - {new_record['mesg']} ({new_record['time_display']})")
else:
    print(f"\nID 21 記錄已存在，跳過新增")

# 按時間排序
data.sort(key=lambda x: x['time'])

print(f"\n更新後資料：{len(data)} 筆")
for item in data:
    print(f"  - {item['mesg']} ({item['time_display']})")

# 重新生成 JSON
new_data_json = json.dumps(data, ensure_ascii=False)

# 替換 HTML 中的 DATA
new_html = html_content.replace(match.group(0), f'const DATA = {new_data_json};')

# 修改卡片 HTML - ID 425 的 card-title 和 card-tag
new_html = new_html.replace(
    '<div class="card-title">缺少生命偵測器、缺少安全帶 ID:425</div>',
    '<div class="card-title">缺少生命偵測器 ID:425</div>'
)
new_html = new_html.replace(
    '<div class="card-tag">缺少生命偵測器、缺少安全帶</div>',
    '<div class="card-tag">缺少生命偵測器</div>'
)

# 新增 ID 21 的卡片 HTML
new_card_html = '''
            <div class="card" data-id="700000" id="card-700000">
                <div class="card-media">
                    <img src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23ddd' width='400' height='300'/%3E%3Ctext fill='%23999' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3E無圖片%3C/text%3E%3C/svg%3E" alt="預覽圖" id="thumb-700000">
                    <video src="https://apigatewayiseek.intemotech.com/vision_logic/video?key=/app/image/kafka_notify_videos/production/20260407/865_%E5%85%A8%E6%94%9D%E5%BD%B1%E6%A9%9F%E5%8D%80%E5%9F%9F_161716333.mp4" id="video-700000" preload="none" style="display:none" loop></video>
                    <button class="play-btn" onclick="playVideo(700000)">
                        <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    </button>
                    <div class="confirmed-badge">✓ 已確認</div>
                </div>
                <div class="card-body">
                    <div class="card-top">
                        <div class="card-title">缺少生命偵測器 ID:21</div>
                        <div class="card-tag">缺少生命偵測器</div>
                    </div>
                    <div class="card-info">
                        <span>09:04:55</span>
                        <span>ID: 21</span>
                    </div>
                    <div class="card-note">
                        <input type="text" class="note-input" id="note-700000" placeholder="備註..." onchange="saveNote(700000, this.value)">
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-sm btn-confirm" id="btn-confirm-700000" onclick="confirmCard(700000)">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            確認違規
                        </button>
                        <button class="btn btn-sm btn-delete" onclick="deleteCard(700000)">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            誤報刪除
                        </button>
                    </div>
                </div>
            </div>
'''

# 在第一張卡片前插入新卡片
new_html = new_html.replace(
    '<div class="card" data-id="731859" id="card-731859">',
    new_card_html + '            <div class="card" data-id="731859" id="card-731859">'
)

# 更新統計數字（從 3 改為 4）
new_html = re.sub(
    r'<div class="stat-num" id="totalNum">3</div>',
    '<div class="stat-num" id="totalNum">4</div>',
    new_html
)

# 儲存更新後的 HTML
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"\n✓ 已更新 DATA 數組")
print(f"✓ 已修改 ID 425 卡片文字")
print(f"✓ 已新增 ID 21 卡片")
print(f"✓ 已更新統計數字")
print(f"\n完成：{html_path}")
