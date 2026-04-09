#!/usr/bin/env python3
"""
重新產生高處作業審核工具，只包含掛鉤問題
"""

import json
import urllib.request
import ssl
from datetime import datetime
from pathlib import Path

# API 設定
API_URL = 'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter'
CAMERA_ID = '758'  # 高處作業
DATE = '2026-04-07'

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

def filter_hooked_only(logs):
    """只保留掛鉤問題"""
    hooked_logs = []
    for log in logs:
        if log.get('type', '') == 'hooked':
            hooked_logs.append(log)
    return hooked_logs

# 讀取原本的 generate_daily_review.py 中的 HTML 範本
# 為了簡化，我們直接使用類似的結構

def generate_card_html(item, idx):
    """產生卡片 HTML"""
    time_str = item.get('time', '')
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        time_display = dt.strftime('%H:%M:%S')
        date_display = dt.strftime('%Y-%m-%d')
    except:
        time_display = time_str
        date_display = DATE

    mesg = item.get('mesg', '')
    log_type = item.get('type', '')

    card_html = f'''
    <div class="card" data-index="{idx}" data-type="{log_type}">
        <div class="card-header">
            <span class="card-number">#{idx}</span>
            <span class="card-time">{time_display}</span>
        </div>
        <div class="card-body">
            <div class="card-message">{mesg}</div>
        </div>
        <div class="card-actions">
            <button class="btn-pass" onclick="markAsPass({idx})">✓ 放行</button>
            <button class="btn-notify" onclick="markAsNotify({idx})">✗ 需通報</button>
        </div>
    </div>
    '''
    return card_html

def main():
    # 取得資料
    print("=" * 50)
    print("重新產生高處作業審核工具（只含掛鉤問題）")
    print("=" * 50)

    all_logs = fetch_data()
    print(f"\n取得 {len(all_logs)} 筆記錄")

    # 篩選掛鉤問題
    hooked_logs = filter_hooked_only(all_logs)
    print(f"篩選出 {len(hooked_logs)} 筆掛鉤問題")

    # 產生卡片
    cards_html = []
    for idx, log in enumerate(hooked_logs, 1):
        cards_html.append(generate_card_html(log, idx))

    # 產生完整 HTML（使用與早上審核工具相同的樣式）
    html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4/7 高處作業審核 - 掛鉤問題 ({len(hooked_logs)}筆)</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f7fa;
            padding: 20px;
        }}

        .header {{
            background: white;
            padding: 20px 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-left h1 {{
            font-size: 24px;
            color: #1a1a1a;
            margin-bottom: 5px;
        }}

        .header-left p {{
            color: #666;
            font-size: 14px;
        }}

        .header-right {{
            text-align: right;
        }}

        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 10px;
        }}

        .stat {{
            text-align: center;
        }}

        .stat-number {{
            font-size: 28px;
            font-weight: bold;
            color: #3b82f6;
        }}

        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-top: 2px;
        }}

        .btn-export {{
            padding: 10px 20px;
            background: #10b981;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
        }}

        .btn-export:hover {{
            background: #059669;
        }}

        .filters {{
            background: white;
            padding: 15px 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
        }}

        .filter-btn {{
            padding: 8px 16px;
            border: 1px solid #ddd;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
        }}

        .filter-btn.active {{
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 16px;
        }}

        .card {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            transition: all 0.2s;
        }}

        .card:hover {{
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }}

        .card.pass {{
            background: #f0fdf4;
            border: 2px solid #10b981;
        }}

        .card.notify {{
            background: #fef2f2;
            border: 2px solid #ef4444;
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 12px;
            align-items: center;
        }}

        .card-number {{
            font-weight: bold;
            color: #3b82f6;
            font-size: 14px;
        }}

        .card-time {{
            color: #666;
            font-size: 13px;
            font-family: monospace;
        }}

        .card-body {{
            margin-bottom: 15px;
        }}

        .card-message {{
            color: #1a1a1a;
            font-size: 15px;
            line-height: 1.5;
        }}

        .card-actions {{
            display: flex;
            gap: 10px;
        }}

        .card-actions button {{
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .btn-pass {{
            background: #10b981;
            color: white;
        }}

        .btn-pass:hover {{
            background: #059669;
        }}

        .btn-notify {{
            background: #ef4444;
            color: white;
        }}

        .btn-notify:hover {{
            background: #dc2626;
        }}

        .card.pass .btn-pass,
        .card.notify .btn-notify {{
            opacity: 0.5;
            cursor: default;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <h1>4/7 高處作業審核（掛鉤問題）</h1>
            <p>日期：2026-04-07 | 類型：掛鉤未確實掛於施工架上</p>
        </div>
        <div class="header-right">
            <div class="stats">
                <div class="stat">
                    <div class="stat-number" id="totalCount">{len(hooked_logs)}</div>
                    <div class="stat-label">總計</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="passCount" style="color: #10b981;">0</div>
                    <div class="stat-label">放行</div>
                </div>
                <div class="stat">
                    <div class="stat-number" id="notifyCount" style="color: #ef4444;">0</div>
                    <div class="stat-label">需通報</div>
                </div>
            </div>
            <button class="btn-export" onclick="exportResults()">匯出審核結果</button>
        </div>
    </div>

    <div class="filters">
        <span style="color: #666; font-size: 14px;">篩選：</span>
        <button class="filter-btn active" onclick="filterCards('all')">全部 ({len(hooked_logs)})</button>
        <button class="filter-btn" onclick="filterCards('pass')">已放行 (<span id="passFilterCount">0</span>)</button>
        <button class="filter-btn" onclick="filterCards('notify')">需通報 (<span id="notifyFilterCount">0</span>)</button>
        <button class="filter-btn" onclick="filterCards('pending')">待審核 (<span id="pendingFilterCount">{len(hooked_logs)}</span>)</button>
    </div>

    <div class="grid" id="cardsContainer">
        {''.join(cards_html)}
    </div>

    <script>
        const reviewData = {json.dumps(hooked_logs, ensure_ascii=False)};
        let decisions = {{}};

        // 載入已儲存的審核結果
        const savedData = localStorage.getItem('reportData_2026-04-07_高處作業');
        if (savedData) {{
            decisions = JSON.parse(savedData);
            // 套用已儲存的決定
            Object.keys(decisions).forEach(idx => {{
                const card = document.querySelector(`.card[data-index="${{idx}}"]`);
                if (card) {{
                    card.classList.add(decisions[idx]);
                }}
            }});
            updateStats();
        }}

        function markAsPass(idx) {{
            const card = document.querySelector(`.card[data-index="${{idx}}"]`);
            card.classList.remove('notify');
            card.classList.add('pass');
            decisions[idx] = 'pass';
            saveAndUpdate();
        }}

        function markAsNotify(idx) {{
            const card = document.querySelector(`.card[data-index="${{idx}}"]`);
            card.classList.remove('pass');
            card.classList.add('notify');
            decisions[idx] = 'notify';
            saveAndUpdate();
        }}

        function saveAndUpdate() {{
            localStorage.setItem('reportData_2026-04-07_高處作業', JSON.stringify(decisions));
            updateStats();
        }}

        function updateStats() {{
            const passCount = Object.values(decisions).filter(d => d === 'pass').length;
            const notifyCount = Object.values(decisions).filter(d => d === 'notify').length;
            const pendingCount = {len(hooked_logs)} - passCount - notifyCount;

            document.getElementById('passCount').textContent = passCount;
            document.getElementById('notifyCount').textContent = notifyCount;
            document.getElementById('passFilterCount').textContent = passCount;
            document.getElementById('notifyFilterCount').textContent = notifyCount;
            document.getElementById('pendingFilterCount').textContent = pendingCount;
        }}

        function filterCards(type) {{
            const cards = document.querySelectorAll('.card');
            const buttons = document.querySelectorAll('.filter-btn');

            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            cards.forEach(card => {{
                const idx = card.dataset.index;
                const decision = decisions[idx];

                if (type === 'all') {{
                    card.style.display = 'block';
                }} else if (type === 'pass') {{
                    card.style.display = decision === 'pass' ? 'block' : 'none';
                }} else if (type === 'notify') {{
                    card.style.display = decision === 'notify' ? 'block' : 'none';
                }} else if (type === 'pending') {{
                    card.style.display = !decision ? 'block' : 'none';
                }}
            }});
        }}

        function exportResults() {{
            const results = reviewData.map((log, idx) => {{
                const decision = decisions[idx + 1] || '待審核';
                return {{
                    序號: idx + 1,
                    時間: log.time,
                    訊息: log.mesg,
                    審核結果: decision === 'pass' ? '放行' : decision === 'notify' ? '需通報' : '待審核'
                }};
            }});

            // 轉換為 CSV
            const headers = ['序號', '時間', '訊息', '審核結果'];
            const csvContent = [
                headers.join(','),
                ...results.map(r => `${{r.序號}},${{r.時間}},"${{r.訊息}}",${{r.審核結果}}`)
            ].join('\\n');

            // 下載
            const blob = new Blob(['\\ufeff' + csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = '4-7高處作業掛鉤問題審核結果.csv';
            link.click();
        }}
    </script>
</body>
</html>'''

    # 儲存檔案（覆蓋原檔案）
    output_file = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/高處作業_審核.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✓ 已更新審核頁面: {output_file}")
    print(f"  - 原本：13,012 筆")
    print(f"  - 更新後：{len(hooked_logs)} 筆（只含掛鉤問題）")
    print(f"  - 檔案大小：{len(html) / 1024:.1f} KB")

if __name__ == '__main__':
    main()
