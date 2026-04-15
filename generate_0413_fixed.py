#!/usr/bin/env python3
"""
專門產生 4/10 高處A 和 高處B 審核頁面
"""
import json
import re

# 讀取 API 資料
with open('/tmp/758_filtered_0413.json', 'r') as f:
    data_758 = json.load(f)

with open('/tmp/867_filtered_0413.json', 'r') as f:
    data_867 = json.load(f)

print(f"Camera 758 資料筆數: {len(data_758)}")
print(f"Camera 837 資料筆數: {len(data_867)}")

# 處理資料並產生所需格式
def process_data(raw_data):
    """處理 API 原始資料為頁面所需格式"""
    processed = []
    for item in raw_data:
        # 提取 video path
        video_key = item.get('video_key', '')
        if 'path:' in video_key:
            path_match = re.search(r'path:([^\s,]+)', video_key)
            if path_match:
                video_key = path_match.group(1)

        # 提取時間
        time_str = item.get('time', '')
        time_display = time_str.split('T')[1][:8] if 'T' in time_str else ''

        # 提取 person IDs
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

# 產生卡片 HTML
def generate_card_html(item):
    """產生單張卡片 HTML"""
    idx = item['id']
    mesg = item.get('mesg', '')
    person_ids = item.get('person_ids', '')
    time_display = item.get('time_display', '')
    image_url = item.get('image_url', '')
    video_url = item.get('video_url', '')
    log_type = item.get('type', '')

    # 取得顯示標籤
    type_display_map = {
        'hooked': '掛鉤未確實掛於施工架上',
        'harness': '人員無穿戴安全帶'
    }
    tag = type_display_map.get(log_type, mesg.split(' ')[0] if mesg else '')

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

# 完整的 HTML 模板
def generate_review_html(category, date_str, total, cards_html, data_json, report_path):
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>{category} 違規審核 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --success: #10B981;
            --success-bg: #ECFDF5;
            --error: #EF4444;
            --error-bg: #FEF2F2;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #FFFFFF;
            color: var(--text-dark);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{
            background: #FFFFFF;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        .header-title .highlight {{
            color: var(--accent-blue);
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .meta-divider {{
            width: 1px;
            height: 16px;
            background: var(--border-color);
        }}

        .stats-row {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .stat-box {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 8px;
            background: var(--bg-light);
        }}
        .stat-box.pending {{ background: var(--warning-bg); }}
        .stat-box.success {{ background: var(--success-bg); }}
        .stat-box.error {{ background: var(--error-bg); }}
        .stat-num {{
            font-size: 18px;
            font-weight: 700;
        }}
        .stat-box.pending .stat-num {{ color: var(--warning); }}
        .stat-box.success .stat-num {{ color: var(--success); }}
        .stat-box.error .stat-num {{ color: var(--error); }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            text-decoration: none;
        }}
        .btn-dark {{
            background: var(--text-dark);
            color: white;
        }}
        .btn-dark:hover {{
            background: #1E293B;
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1px solid var(--border-color);
        }}
        .btn-outline:hover {{
            background: var(--bg-light);
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1.5px solid var(--border-color);
        }}
        .btn-outline:hover {{
            border-color: var(--text-secondary);
            background: var(--bg-light);
        }}
        .btn-sm {{
            padding: 8px 14px;
            font-size: 12px;
            border-radius: 8px;
        }}
        .btn-confirm {{
            background: white;
            color: var(--success);
            border: 1.5px solid var(--success);
        }}
        .btn-confirm:hover {{
            background: var(--success-bg);
        }}
        .btn-confirm.confirmed {{
            background: var(--success);
            color: white;
        }}
        .btn-delete {{
            background: white;
            color: var(--error);
            border: 1.5px solid var(--error);
        }}
        .btn-delete:hover {{
            background: var(--error-bg);
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
            padding-top: 100px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 24px;
        }}

        .card {{
            background: white;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: all 0.25s ease;
        }}
        .card:hover {{
            border-color: #CBD5E1;
            box-shadow: 0 8px 24px rgba(15,23,42,0.08);
            transform: translateY(-4px);
        }}
        .card.removing {{
            animation: fadeOut 0.3s ease forwards;
        }}
        .card.confirmed {{
            border-color: var(--success);
        }}
        @keyframes fadeOut {{
            to {{ opacity: 0; transform: scale(0.96); }}
        }}

        .card-media {{
            position: relative;
            aspect-ratio: 16/9;
            background: #F1F5F9;
            overflow: hidden;
        }}
        .card-media img, .card-media video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .play-btn {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 56px;
            height: 56px;
            background: rgba(0,0,0,0.6);
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }}
        .play-btn:hover {{
            background: rgba(0,0,0,0.8);
            transform: translate(-50%, -50%) scale(1.1);
        }}
        .play-btn svg {{
            width: 24px;
            height: 24px;
            fill: white;
            margin-left: 4px;
        }}
        .confirmed-badge {{
            position: absolute;
            top: 12px;
            right: 12px;
            background: var(--success);
            color: white;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            display: none;
        }}
        .card.confirmed .confirmed-badge {{
            display: block;
        }}

        .card-body {{
            padding: 20px;
        }}
        .card-top {{
            margin-bottom: 12px;
        }}
        .card-title {{
            font-size: 15px;
            font-weight: 600;
            color: var(--text-dark);
            margin-bottom: 6px;
        }}
        .card-tag {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            background: var(--warning-bg);
            color: var(--warning);
        }}
        .card-info {{
            display: flex;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 12px;
        }}
        .card-note {{
            margin-bottom: 16px;
        }}
        .note-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 13px;
            font-family: inherit;
            transition: border-color 0.2s ease;
        }}
        .note-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        .card-actions {{
            display: flex;
            gap: 12px;
        }}
        .card-actions .btn {{
            flex: 1;
        }}

        .empty-state {{
            text-align: center;
            padding: 80px 32px;
            color: var(--text-secondary);
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-left">
                <div class="header-title">
                    <span class="highlight">中油</span> {category}審核
                </div>
                <div class="header-meta">
                    <span>{date_str}</span>
                    <div class="meta-divider"></div>
                    <span>共 {total} 筆</span>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-box pending">
                    <span class="stat-num" id="pending-count">{total}</span>
                    <span class="stat-label">待審核</span>
                </div>
                <div class="stat-box success">
                    <span class="stat-num" id="confirmed-count">0</span>
                    <span class="stat-label">已確認</span>
                </div>
                <div class="stat-box error">
                    <span class="stat-num" id="deleted-count">0</span>
                    <span class="stat-label">已刪除</span>
                </div>
            </div>
            <div style="display: flex; gap: 12px;">
                <button class="btn btn-outline" onclick="window.location.href='../../../index.html'">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    返回列表
                </button>
                <button class="btn btn-dark" onclick="generateReport()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    偵測報告
                </button>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="grid" id="grid">
{cards_html}
        </div>
    </main>

    <script>
        const DATA = {data_json};
        const STORAGE_KEY = 'reviewState_{date_str}_{category}';
        const REPORT_KEY = 'reportData_{date_str}_{category}';
        let reviewState = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');

        function updateCounts() {{
            const cards = document.querySelectorAll('.card:not(.removing)');
            let pending = 0, confirmed = 0, deleted = 0;
            cards.forEach(card => {{
                const id = card.dataset.id;
                const state = reviewState[id];
                if (state === 'confirmed') confirmed++;
                else if (state === 'deleted') deleted++;
                else pending++;
            }});
            document.getElementById('pending-count').textContent = pending;
            document.getElementById('confirmed-count').textContent = confirmed;
            document.getElementById('deleted-count').textContent = deleted;
        }}

        function confirmCard(id) {{
            reviewState[id] = 'confirmed';
            localStorage.setItem(STORAGE_KEY, JSON.stringify(reviewState));
            const card = document.getElementById('card-' + id);
            if (card) {{
                card.classList.add('confirmed');
                document.getElementById('btn-confirm-' + id).classList.add('confirmed');
            }}
            updateCounts();
        }}

        function deleteCard(id) {{
            reviewState[id] = 'deleted';
            localStorage.setItem(STORAGE_KEY, JSON.stringify(reviewState));
            const card = document.getElementById('card-' + id);
            if (card) {{
                card.classList.add('removing');
                setTimeout(() => card.style.display = 'none', 300);
            }}
            updateCounts();
        }}

        function saveNote(id, value) {{
            if (!reviewState.notes) reviewState.notes = {{}};
            reviewState.notes[id] = value;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(reviewState));
        }}

        function playVideo(id) {{
            const video = document.getElementById('video-' + id);
            const img = document.getElementById('thumb-' + id);
            if (video && img) {{
                if (video.style.display === 'none') {{
                    img.style.display = 'none';
                    video.style.display = 'block';
                    video.play();
                }} else {{
                    video.pause();
                    video.style.display = 'none';
                    img.style.display = 'block';
                }}
            }}
        }}

        function saveReportData() {{
            const confirmed = DATA.filter(item => reviewState[item.id] === 'confirmed');
            localStorage.setItem(REPORT_KEY, JSON.stringify(confirmed));
        }}

        function restoreState() {{
            Object.keys(reviewState).forEach(id => {{
                if (id === 'notes') return;
                const state = reviewState[id];
                const card = document.getElementById('card-' + id);
                if (!card) return;
                if (state === 'confirmed') {{
                    card.classList.add('confirmed');
                    const btn = document.getElementById('btn-confirm-' + id);
                    if (btn) btn.classList.add('confirmed');
                }} else if (state === 'deleted') {{
                    card.style.display = 'none';
                }}
            }});
            if (reviewState.notes) {{
                Object.keys(reviewState.notes).forEach(id => {{
                    const input = document.getElementById('note-' + id);
                    if (input) input.value = reviewState.notes[id];
                }});
            }}
            updateCounts();
        }}

        restoreState();
    </script>
</body>
</html>'''

# 產生管理版報告 HTML
def generate_manager_report_html(category, date_str):
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 偵測報告 - {date_str}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8fafc; padding: 32px; }}
        .header {{ text-align: center; margin-bottom: 32px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header p {{ color: #64748b; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; max-width: 1200px; margin: 0 auto; }}
        .card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card img {{ width: 100%; aspect-ratio: 16/9; object-fit: cover; }}
        .card-body {{ padding: 16px; }}
        .card-title {{ font-weight: 600; margin-bottom: 4px; }}
        .card-info {{ color: #64748b; font-size: 14px; }}
        .empty {{ text-align: center; padding: 60px; color: #64748b; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{category} 偵測報告</h1>
        <p>{date_str}</p>
    </div>
    <div class="grid" id="grid"></div>
    <script>
        const REPORT_KEY = 'reportData_{date_str}_{category}';
        const data = JSON.parse(localStorage.getItem(REPORT_KEY) || '[]');
        const grid = document.getElementById('grid');
        if (data.length === 0) {{
            grid.innerHTML = '<div class="empty">尚無已確認的違規項目</div>';
        }} else {{
            data.forEach(item => {{
                grid.innerHTML += `
                    <div class="card">
                        <img src="${{item.image_url}}" alt="">
                        <div class="card-body">
                            <div class="card-title">${{item.mesg}}</div>
                            <div class="card-info">${{item.time_display}} · ID: ${{item.person_ids}}</div>
                        </div>
                    </div>
                `;
            }});
        }}
    </script>
</body>
</html>'''

# 處理資料
data_758_processed = process_data(data_758)
data_867_processed = process_data(data_867)

print(f"\n758 第一筆: ID={data_758_processed[0]['id']}, time={data_758_processed[0]['time_display']}")
print(f"837 第一筆: ID={data_867_processed[0]['id']}, time={data_867_processed[0]['time_display']}")

# 產生卡片 HTML
cards_758 = '\n'.join([generate_card_html(item) for item in data_758_processed])
cards_867 = '\n'.join([generate_card_html(item) for item in data_867_processed])

# 產生完整 HTML
date_str = '2026-04-13'

# 高處A = Camera 837
html_a = generate_review_html(
    '高處A', date_str, len(data_867_processed),
    cards_867, json.dumps(data_867_processed, ensure_ascii=False),
    '高處A_報告_管理版.html'
)

# 高處B = Camera 758
html_b = generate_review_html(
    '高處B', date_str, len(data_758_processed),
    cards_758, json.dumps(data_758_processed, ensure_ascii=False),
    '高處B_報告_管理版.html'
)

# 產生報告頁面
report_a = generate_manager_report_html('高處A', date_str)
report_b = generate_manager_report_html('高處B', date_str)

# 輸出路徑
output_dir = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/13'

# 寫入檔案
with open(f'{output_dir}/高處A_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_a)
print(f"✓ 已產生 高處A_審核.html (Camera 837, 從 {data_867_processed[0]['time_display']} 開始)")

with open(f'{output_dir}/高處B_審核.html', 'w', encoding='utf-8') as f:
    f.write(html_b)
print(f"✓ 已產生 高處B_審核.html (Camera 758, 從 {data_758_processed[0]['time_display']} 開始)")

with open(f'{output_dir}/高處A_報告_管理版.html', 'w', encoding='utf-8') as f:
    f.write(report_a)
print(f"✓ 已產生 高處A_報告_管理版.html")

with open(f'{output_dir}/高處B_報告_管理版.html', 'w', encoding='utf-8') as f:
    f.write(report_b)
print(f"✓ 已產生 高處B_報告_管理版.html")

print("\n完成！")
