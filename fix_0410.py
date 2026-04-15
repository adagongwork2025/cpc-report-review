#!/usr/bin/env python3
"""
修正 4/10 頁面：時間排序（新到舊）
"""
import json
import re

# 讀取 API 資料
with open('/tmp/758_unique.json', 'r') as f:
    data_758 = json.load(f)

with open('/tmp/837_unique.json', 'r') as f:
    data_837 = json.load(f)

def extract_video_path(video_key):
    if 'path:' in video_key:
        match = re.search(r'path:([^\s,]+)', video_key)
        if match:
            return match.group(1)
    return video_key

def process_data(raw_data):
    processed = []
    for item in raw_data:
        video_key = extract_video_path(item.get('video_key', ''))
        time_str = item.get('time', '')
        time_display = time_str.split('T')[1][:8] if 'T' in time_str else ''

        mesg = item.get('mesg', '')
        ids_match = re.findall(r'ID:(\d+)', mesg)
        person_ids = ', '.join(ids_match) if ids_match else ''

        processed.append({
            'id': item.get('id'),
            'time_display': time_display,
            'mesg': mesg,
            'type': item.get('type', ''),
            'person_ids': person_ids,
            'image_url': f"https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image?key={item.get('key', '')}",
            'video_url': f"https://apigatewayiseek.intemotech.com/vision_logic/video?key={video_key}"
        })

    # 按時間排序（新到舊）
    processed.sort(key=lambda x: x['time_display'], reverse=True)
    return processed

def get_display_tag(mesg, log_type):
    type_map = {
        'hooked': '掛鉤未確實掛於施工架上',
        'harness': '人員無穿戴安全帶'
    }
    return type_map.get(log_type, mesg.split(' ')[0] if mesg else '')

def generate_card_html(item):
    idx = item['id']
    mesg = item.get('mesg', '')
    person_ids = item.get('person_ids', '')
    time_display = item.get('time_display', '')
    image_url = item.get('image_url', '')
    video_url = item.get('video_url', '')
    log_type = item.get('type', '')
    tag = get_display_tag(mesg, log_type)

    return f'''            <div class="card" data-id="{idx}" id="card-{idx}">
                <div class="card-media">
                    <img src="{image_url}" alt="預覽圖" id="thumb-{idx}">
                    <video src="{video_url}" id="video-{idx}" preload="none" style="display:none" loop></video>
                    <button class="play-btn" onclick="playVideo({idx})">
                        <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    </button>
                    <div class="confirmed-badge">✓ 已確認</div>
                </div>
                <div class="card-body">
                    <div class="card-top">
                        <div class="card-title">{mesg}</div>
                        <div class="card-tag">{tag}</div>
                    </div>
                    <div class="card-info">
                        <span>{time_display}</span>
                        <span>ID: {person_ids}</span>
                    </div>
                    <div class="card-note">
                        <input type="text" class="note-input" id="note-{idx}" placeholder="備註..." onchange="saveNote({idx}, this.value)">
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-sm btn-confirm" id="btn-confirm-{idx}" onclick="confirmCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            確認違規
                        </button>
                        <button class="btn btn-sm btn-delete" onclick="deleteCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            誤報刪除
                        </button>
                    </div>
                </div>
            </div>'''

# 處理資料（按時間新到舊排序）
data_758_processed = process_data(data_758)
data_837_processed = process_data(data_837)

print(f"高處A (837): {len(data_837_processed)} 筆, 第一筆 {data_837_processed[0]['time_display']}")
print(f"高處B (758): {len(data_758_processed)} 筆, 第一筆 {data_758_processed[0]['time_display']}")

# 讀取 4/9 模板
with open('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/09/高處作業_審核.html', 'r', encoding='utf-8') as f:
    template = f.read()

def create_page(category, date_str, processed_data, report_path):
    cards_html = '\n'.join([generate_card_html(item) for item in processed_data])
    data_json = json.dumps(processed_data, ensure_ascii=False)
    total = len(processed_data)

    html = template

    # 替換標題
    html = re.sub(r'<title>.*?</title>', f'<title>{category} 違規審核 - {date_str}</title>', html)

    # 替換 header
    html = re.sub(
        r'<span class="highlight">高處作業</span> 違規審核',
        f'<span class="highlight">{category}</span> 違規審核',
        html
    )
    html = re.sub(r'<span>2026-04-09</span>', f'<span>{date_str}</span>', html)

    # 替換筆數顯示
    html = re.sub(r'共 \d+ 筆', f'共 {total} 筆', html)

    # 替換待審核數字
    html = re.sub(r'id="pending-count">356</span>', f'id="pending-count">{total}</span>', html)

    # 替換報告連結
    html = re.sub(r'href="高處作業_報告_管理版\.html"', f'href="{report_path}"', html)

    # 替換 JavaScript 常數
    html = re.sub(r"const DATE = '2026-04-09';", f"const DATE = '{date_str}';", html)
    html = re.sub(r"const CATEGORY = '高處作業';", f"const CATEGORY = '{category}';", html)

    # 替換 DATA 陣列
    html = re.sub(r'const DATA = \[.*?\];', f'const DATA = {data_json};', html, flags=re.DOTALL)

    # 替換卡片區塊
    grid_pattern = r'(<div class="grid" id="grid">).*?(</div>\s*</main>)'
    html = re.sub(grid_pattern, rf'\1\n{cards_html}\n        \2', html, flags=re.DOTALL)

    return html

# 產生頁面
date_str = '2026-04-10'
output_dir = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10'

html_a = create_page('高處A', date_str, data_837_processed, '高處A_報告_管理版.html')
with open(f'{output_dir}/高處A_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_a)
print(f"✓ 高處A_審核.html (時間排序: {data_837_processed[0]['time_display']} → {data_837_processed[-1]['time_display']})")

html_b = create_page('高處B', date_str, data_758_processed, '高處B_報告_管理版.html')
with open(f'{output_dir}/高處B_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_b)
print(f"✓ 高處B_審核.html (時間排序: {data_758_processed[0]['time_display']} → {data_758_processed[-1]['time_display']})")
