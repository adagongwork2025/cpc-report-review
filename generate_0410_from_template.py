#!/usr/bin/env python3
"""
從 4/9 模板產生 4/10 高處A 和 高處B 審核頁面
"""
import json
import re

# 讀取 4/9 審核頁面作為模板
with open('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/09/高處作業_審核.html', 'r', encoding='utf-8') as f:
    template = f.read()

# 讀取 API 資料
with open('/tmp/758_unique.json', 'r') as f:
    data_758 = json.load(f)

with open('/tmp/837_unique.json', 'r') as f:
    data_837 = json.load(f)

print(f"Camera 758 資料筆數: {len(data_758)}")
print(f"Camera 837 資料筆數: {len(data_837)}")

def extract_video_path(video_key):
    """從 video_key 提取 path"""
    if 'path:' in video_key:
        match = re.search(r'path:([^\s,]+)', video_key)
        if match:
            return match.group(1)
    return video_key

def process_data(raw_data):
    """處理 API 原始資料為頁面所需格式"""
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
    return processed

def get_display_tag(mesg, log_type):
    """取得顯示標籤"""
    type_map = {
        'hooked': '掛鉤未確實掛於施工架上',
        'harness': '人員無穿戴安全帶'
    }
    return type_map.get(log_type, mesg.split(' ')[0] if mesg else '')

def generate_card_html(item):
    """產生單張卡片 HTML"""
    idx = item['id']
    mesg = item.get('mesg', '')
    person_ids = item.get('person_ids', '')
    time_display = item.get('time_display', '')
    image_url = item.get('image_url', '')
    video_url = item.get('video_url', '')
    log_type = item.get('type', '')
    tag = get_display_tag(mesg, log_type)

    return f'''
            <div class="card" data-id="{idx}" id="card-{idx}">
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

def create_page(category, date_str, data, report_path):
    """從模板創建新頁面"""
    processed = process_data(data)
    cards_html = '\n'.join([generate_card_html(item) for item in processed])
    data_json = json.dumps(processed, ensure_ascii=False)
    total = len(processed)

    # 從模板開始
    html = template

    # 替換標題
    html = re.sub(r'<title>.*?</title>', f'<title>{category} 違規審核 - {date_str}</title>', html)

    # 替換 header 中的類別名稱和日期
    html = re.sub(r'<span class="highlight">中油</span> 高處作業審核', f'<span class="highlight">中油</span> {category}審核', html)
    html = re.sub(r'<span>2026-04-09</span>', f'<span>{date_str}</span>', html)

    # 替換筆數
    html = re.sub(r'<span>共 \d+ 筆</span>', f'<span>共 {total} 筆</span>', html)

    # 替換報告連結
    html = re.sub(r'href="高處作業_報告_管理版\.html"', f'href="{report_path}"', html)

    # 替換 DATA 陣列
    html = re.sub(r'const DATA = \[.*?\];', f'const DATA = {data_json};', html, flags=re.DOTALL)

    # 替換 STORAGE_KEY 和 REPORT_KEY
    html = re.sub(r"const STORAGE_KEY = 'reviewState_2026-04-09_高處作業';", f"const STORAGE_KEY = 'reviewState_{date_str}_{category}';", html)
    html = re.sub(r"const REPORT_KEY = 'reportData_2026-04-09_高處作業';", f"const REPORT_KEY = 'reportData_{date_str}_{category}';", html)

    # 替換 DATE 和 CATEGORY 常數
    html = re.sub(r"const DATE = '2026-04-09';", f"const DATE = '{date_str}';", html)
    html = re.sub(r"const CATEGORY = '高處作業';", f"const CATEGORY = '{category}';", html)

    # 替換卡片區塊
    # 找到 <div class="grid" id="grid"> 到 </div>\s*</main> 之間的內容
    grid_pattern = r'(<div class="grid" id="grid">).*?(</div>\s*</main>)'
    html = re.sub(grid_pattern, rf'\1\n{cards_html}\n        \2', html, flags=re.DOTALL)

    return html

# 處理資料
date_str = '2026-04-10'

# 高處A = Camera 837
html_a = create_page('高處A', date_str, data_837, '高處A_報告_管理版.html')

# 高處B = Camera 758
html_b = create_page('高處B', date_str, data_758, '高處B_報告_管理版.html')

# 輸出路徑
output_dir = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10'

# 寫入檔案
with open(f'{output_dir}/高處A_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_a)
print(f"✓ 已產生 高處A_審核.html (Camera 837, {len(data_837)} 筆)")

with open(f'{output_dir}/高處B_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_b)
print(f"✓ 已產生 高處B_審核.html (Camera 758, {len(data_758)} 筆)")

# 驗證
print("\n驗證第一筆資料:")
d758 = process_data(data_758)
d837 = process_data(data_837)
print(f"  高處A (837): {d837[0]['time_display']}, ID {d837[0]['id']}")
print(f"  高處B (758): {d758[0]['time_display']}, ID {d758[0]['id']}")
