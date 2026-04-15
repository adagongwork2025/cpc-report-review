#!/usr/bin/env python3
"""
產生最終的審核和報告頁面 - 只包含8筆
"""
import json
import re

# 讀取最終 8 筆
with open('/tmp/final_8_items.json', 'r') as f:
    final_8 = json.load(f)

print(f"產生頁面: {len(final_8)} 筆")

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

    return f'''            <div class="card confirmed" data-id="{idx}" id="card-{idx}">
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
                        <button class="btn btn-sm btn-confirm confirmed" id="btn-confirm-{idx}" onclick="confirmCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            已確認 ✓
                        </button>
                        <button class="btn btn-sm btn-delete" onclick="deleteCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            誤報刪除
                        </button>
                    </div>
                </div>
            </div>'''

# === 產生審核頁面 ===
cards_html = '\n'.join([generate_card_html(item) for item in final_8])
data_json = json.dumps(final_8, ensure_ascii=False)

# 讀取 4/9 模板
with open('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/09/高處作業_審核.html', 'r', encoding='utf-8') as f:
    template = f.read()

html = template
html = re.sub(r'<title>.*?</title>', '<title>高處B 違規審核 - 2026-04-10</title>', html)
html = re.sub(r'<span class="highlight">高處作業</span> 違規審核', '<span class="highlight">高處B</span> 違規審核', html)
html = re.sub(r'<span>2026-04-09</span>', '<span>2026-04-10</span>', html)
html = re.sub(
    r'(<div class="header-meta">\s*<span>2026-04-10</span>)',
    r'\1\n                    <span>共 8 筆</span>',
    html
)
html = re.sub(r'id="pending-count">356</span>', 'id="pending-count">0</span>', html)
html = re.sub(r'id="confirmed-count">0</span>', 'id="confirmed-count">8</span>', html)
html = re.sub(r'href="高處作業_報告_管理版\.html"', 'href="高處B_報告_管理版.html"', html)
html = re.sub(r"const DATE = '2026-04-09';", "const DATE = '2026-04-10';", html)
html = re.sub(r"const CATEGORY = '高處作業';", "const CATEGORY = '高處B';", html)
html = re.sub(r"const REPORT_PATH = '高處作業_報告.html';", "const REPORT_PATH = '高處B_報告_管理版.html';", html)
html = re.sub(r'const DATA = \[.*?\];', f'const DATA = {data_json};', html, flags=re.DOTALL)

confirmed_ids_str = ','.join(str(item['id']) for item in final_8)
html = re.sub(r'let confirmedIds = new Set\(\);', f'let confirmedIds = new Set([{confirmed_ids_str}]);', html)
html = re.sub(r'let deletedIds = new Set\(.*?\);', 'let deletedIds = new Set();', html)

grid_pattern = r'(<div class="grid" id="grid">).*?(</div>\s*</main>)'
html = re.sub(grid_pattern, rf'\1\n{cards_html}\n        \2', html, flags=re.DOTALL)

with open('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10/高處B_審核.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✓ 審核頁面（8 筆）")

# === 產生報告頁面 ===
report_file = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/10/高處B_報告_管理版.html'
with open(report_file, 'r', encoding='utf-8') as f:
    report_html = f.read()

report_data_js = json.dumps({
    'date': '2026-04-10',
    'category': '高處B',
    'items': final_8
}, ensure_ascii=False)

report_html = re.sub(
    r'const stored = localStorage\.getItem\(REPORT_KEY\);[\s\S]*?function showNoViolationWithVideos\(\)',
    f'''const stored = null;
            reportData = {report_data_js};
            if (reportData.items && reportData.items.length > 0) {{
                render();
            }} else {{
                showNoViolationWithVideos();
            }}
        }}

        function showNoViolationWithVideos()''',
    report_html
)

with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report_html)

print(f"✓ 報告頁面（8 筆）")
