#!/usr/bin/env python3
"""
產生早上掛鉤問題專用審核頁面
"""

import json
from pathlib import Path

# 讀取早上的掛鉤問題資料
data_file = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/早上_高處作業.json')
with open(data_file, 'r', encoding='utf-8') as f:
    logs = json.load(f)

print(f"載入 {len(logs)} 筆早上掛鉤問題記錄")

# 產生卡片 HTML
cards_html = []
for idx, log in enumerate(logs, 1):
    time = log['time']
    mesg = log['mesg']

    card_html = f'''
    <div class="card" data-index="{idx}">
        <div class="card-header">
            <span class="card-number">#{idx}</span>
            <span class="card-time">{time}</span>
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
    cards_html.append(card_html)

# 產生完整 HTML
html = f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>4/7 早上掛鉤問題審核 (382筆)</title>
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
            <h1>4/7 早上掛鉤問題審核</h1>
            <p>時段：06:00-12:00 | 類型：掛鉤未確實掛於施工架上</p>
        </div>
        <div class="header-right">
            <div class="stats">
                <div class="stat">
                    <div class="stat-number" id="totalCount">{len(logs)}</div>
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
        <button class="filter-btn active" onclick="filterCards('all')">全部 ({len(logs)})</button>
        <button class="filter-btn" onclick="filterCards('pass')">已放行 (<span id="passFilterCount">0</span>)</button>
        <button class="filter-btn" onclick="filterCards('notify')">需通報 (<span id="notifyFilterCount">0</span>)</button>
        <button class="filter-btn" onclick="filterCards('pending')">待審核 (<span id="pendingFilterCount">{len(logs)}</span>)</button>
    </div>

    <div class="grid" id="cardsContainer">
        {''.join(cards_html)}
    </div>

    <script>
        const reviewData = {json.dumps(logs, ensure_ascii=False)};
        let decisions = {{}};

        // 載入已儲存的審核結果
        const savedData = localStorage.getItem('morning_hook_review_2026-04-07');
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
            localStorage.setItem('morning_hook_review_2026-04-07', JSON.stringify(decisions));
            updateStats();
        }}

        function updateStats() {{
            const passCount = Object.values(decisions).filter(d => d === 'pass').length;
            const notifyCount = Object.values(decisions).filter(d => d === 'notify').length;
            const pendingCount = {len(logs)} - passCount - notifyCount;

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
            link.download = '4-7早上掛鉤問題審核結果.csv';
            link.click();
        }}
    </script>
</body>
</html>'''

# 儲存檔案
output_file = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/07/早上掛鉤問題_審核.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✓ 審核頁面已建立: {output_file}")
print(f"  - 共 {len(logs)} 筆記錄")
print(f"  - 時段: 06:00-12:00")
print(f"  - 類型: 掛鉤未確實掛於施工架上")
