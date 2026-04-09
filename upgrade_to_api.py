#!/usr/bin/env python3
"""
升級審核頁面：改為從 API 讀取資料和儲存審核狀態
"""
import re
from pathlib import Path

API_BASE_URL = 'http://192.168.53.96:8001/api/v1'

def upgrade_review_page(html_path: Path):
    """修改審核頁面，連接 API"""

    content = html_path.read_text(encoding='utf-8')

    # 找到 <script> 標籤的位置
    script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
    if not script_match:
        print(f"⚠️  找不到 script 標籤: {html_path.name}")
        return False

    original_script = script_match.group(1)

    # 提取 DATE 和 CATEGORY
    date_match = re.search(r"const DATE = '([^']+)';", original_script)
    category_match = re.search(r"const CATEGORY = '([^']+)';", original_script)

    if not date_match or not category_match:
        print(f"⚠️  找不到 DATE 或 CATEGORY: {html_path.name}")
        return False

    date_val = date_match.group(1)
    category_val = category_match.group(1)

    # 建立新的 script 內容
    new_script = f'''
        // API 配置
        const API_BASE_URL = '{API_BASE_URL}';
        const DATE = '{date_val}';
        const CATEGORY = '{category_val}';
        const REPORT_PATH = '{category_val}_報告.html';
        const PRESET_TIMES = [];  // 預設確認的時間列表

        let DATA = [];  // 從 API 載入
        let confirmedIds = new Set();
        let deletedIds = new Set();
        let currentModalId = null;
        let notes = {{}};  // 備註資料 {{id: note}}

        const STORAGE_KEY = 'reviewState_' + DATE + '_' + CATEGORY;

        // 從 API 載入資料
        async function loadDataFromAPI() {{
            try {{
                const response = await fetch(`${{API_BASE_URL}}/detection-logs/${{DATE}}/${{encodeURIComponent(CATEGORY)}}`);
                const result = await response.json();

                if (result.success && result.data.items) {{
                    DATA = result.data.items;

                    // 根據 API 回傳的 review_status 設定初始狀態
                    DATA.forEach(item => {{
                        if (item.review_status === 'confirmed') {{
                            confirmedIds.add(item.id);
                        }} else if (item.review_status === 'deleted') {{
                            deletedIds.add(item.id);
                        }}
                        if (item.note) {{
                            notes[item.id] = item.note;
                        }}
                    }});

                    // 渲染卡片
                    renderAllCards();

                    // 應用審核狀態
                    applyReviewStates();

                    updateStats();

                    console.log(`✓ 從 API 載入 ${{DATA.length}} 筆資料`);
                }} else {{
                    console.error('API 回應格式錯誤');
                    showError('資料載入失敗，請重新整理頁面');
                }}
            }} catch (error) {{
                console.error('API 載入失敗:', error);
                showError('無法連接伺服器，請檢查網路連線');
            }}
        }}

        // 渲染所有卡片
        function renderAllCards() {{
            const container = document.getElementById('card-container');
            if (!container) return;

            container.innerHTML = DATA.map(d => `
                <div class="card" id="card-${{d.id}}" data-time="${{d.time_display}}">
                    <div class="card-header">
                        <span class="card-time">${{d.time_display}}</span>
                        <span class="card-id">ID: ${{d.person_ids || '-'}}</span>
                    </div>
                    <div class="card-body">
                        <div class="card-message">${{d.mesg || d.message}}</div>
                        <div class="card-actions">
                            <button class="btn-confirm" id="btn-confirm-${{d.id}}" onclick="confirmCard(${{d.id}})">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="20 6 9 17 4 12"/>
                                </svg>
                                確認違規
                            </button>
                            <button class="btn-video" onclick="playVideo(${{d.id}})">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="5 3 19 12 5 21 5 3"/>
                                </svg>
                                播放
                            </button>
                            <button class="btn-delete" onclick="deleteCard(${{d.id}})">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                                </svg>
                                刪除
                            </button>
                        </div>
                        <div class="card-note">
                            <input type="text" id="note-${{d.id}}" placeholder="新增備註..."
                                   onchange="saveNote(${{d.id}}, this.value)"
                                   value="${{notes[d.id] || ''}}">
                        </div>
                    </div>
                </div>
            `).join('');
        }}

        // 應用審核狀態到 UI
        function applyReviewStates() {{
            confirmedIds.forEach(id => {{
                const card = document.getElementById('card-' + id);
                const btn = document.getElementById('btn-confirm-' + id);
                if (card && btn) {{
                    card.classList.add('confirmed');
                    btn.classList.add('confirmed');
                    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
                }}
            }});

            deletedIds.forEach(id => {{
                const card = document.getElementById('card-' + id);
                if (card) {{
                    card.style.display = 'none';
                }}
            }});

            Object.keys(notes).forEach(id => {{
                const input = document.getElementById('note-' + id);
                if (input && notes[id]) {{
                    input.value = notes[id];
                }}
            }});
        }}

        // 提交審核到 API
        async function submitReviewToAPI(action = null) {{
            const actions = [];

            // 已確認的項目
            confirmedIds.forEach(id => {{
                actions.push({{
                    detection_log_id: id,
                    action: 'confirmed',
                    note: notes[id] || null
                }});
            }});

            // 已刪除的項目
            deletedIds.forEach(id => {{
                actions.push({{
                    detection_log_id: id,
                    action: 'deleted',
                    note: null
                }});
            }});

            if (actions.length === 0) return;

            try {{
                const response = await fetch(`${{API_BASE_URL}}/reviews/actions/bulk`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        date: DATE,
                        category: CATEGORY,
                        actions: actions,
                        reviewer_ip: 'web_client'
                    }})
                }});

                if (response.ok) {{
                    console.log('✓ 審核已提交到伺服器');
                    return true;
                }} else {{
                    console.error('提交失敗:', response.status);
                    return false;
                }}
            }} catch (error) {{
                console.error('提交審核失敗:', error);
                return false;
            }}
        }}

        // 儲存狀態（提交到 API）
        function saveState() {{
            submitReviewToAPI();
        }}

        // 載入狀態（從 API 載入）
        function loadState() {{
            // 已在 loadDataFromAPI() 中處理
        }}

        // 顯示錯誤訊息
        function showError(message) {{
            const container = document.getElementById('card-container');
            if (container) {{
                container.innerHTML = `
                    <div style="padding: 40px; text-align: center; color: #EF4444;">
                        <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
                        <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">載入失敗</div>
                        <div style="color: #94A3B8;">${{message}}</div>
                        <button onclick="location.reload()" style="margin-top: 20px; padding: 10px 20px; background: #3B82F6; color: white; border: none; border-radius: 6px; cursor: pointer;">
                            重新載入
                        </button>
                    </div>
                `;
            }}
        }}

        // 頁面載入時從 API 載入資料
        window.addEventListener('load', loadDataFromAPI);

        function updateStats() {{
            const pending = DATA.length - confirmedIds.size - deletedIds.size;
            document.getElementById('pending-count').textContent = pending;
            document.getElementById('confirmed-count').textContent = confirmedIds.size;
            document.getElementById('deleted-count').textContent = deletedIds.size;
        }}

        function confirmCard(id) {{
            const card = document.getElementById('card-' + id);
            const btn = document.getElementById('btn-confirm-' + id);
            if (confirmedIds.has(id)) {{
                confirmedIds.delete(id);
                card.classList.remove('confirmed');
                btn.classList.remove('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 確認違規';
            }} else {{
                confirmedIds.add(id);
                card.classList.add('confirmed');
                btn.classList.add('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
            }}
            updateStats();
            saveState();
        }}

        function deleteCard(id) {{
            const card = document.getElementById('card-' + id);
            card.classList.add('removing');
            setTimeout(() => {{
                card.style.display = 'none';
                deletedIds.add(id);
                confirmedIds.delete(id);
                updateStats();
                saveState();
            }}, 300);
        }}

        function playVideo(id) {{
            currentModalId = id;
            const d = DATA.find(item => item.id === id);
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            const title = document.getElementById('modal-title');
            const info = document.getElementById('modal-info');

            if (d) {{
                title.textContent = d.mesg || d.message;
                info.textContent = `${{d.time_display}} • ID: ${{d.person_ids || '-'}}`;
                video.src = d.video_url;
                modal.style.display = 'flex';
                video.play();
            }}
        }}

        function closeModal() {{
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            modal.style.display = 'none';
            video.pause();
            video.src = '';
        }}

        function saveNote(id, value) {{
            notes[id] = value;
            saveState();
        }}

        function generateReport() {{
            if (confirmedIds.size === 0) {{
                alert('請至少確認一筆違規記錄才能產生報告');
                return;
            }}

            const reportData = {{
                date: DATE,
                category: CATEGORY,
                items: DATA.filter(d => confirmedIds.has(d.id)).map(d => ({{
                    ...d,
                    note: notes[d.id] || ''
                }}))
            }};

            // 儲存報告資料
            localStorage.setItem('reportData_' + DATE + '_' + CATEGORY, JSON.stringify(reportData));

            // 跳轉到報告頁面
            window.location.href = REPORT_PATH;
        }}
    '''

    # 取代 script 內容
    new_content = content.replace(script_match.group(0), f'<script>{new_script}</script>')

    # 寫回檔案
    html_path.write_text(new_content, encoding='utf-8')

    return True


def main():
    """批次處理所有審核頁面"""

    base_dir = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026')

    review_files = list(base_dir.rglob('*_審核.html'))

    print(f"找到 {len(review_files)} 個審核頁面")
    print("=" * 60)

    success_count = 0

    for html_file in review_files:
        print(f"\n處理: {html_file.relative_to(base_dir)}")

        if upgrade_review_page(html_file):
            print(f"  ✓ 已升級")
            success_count += 1
        else:
            print(f"  ✗ 升級失敗")

    print("\n" + "=" * 60)
    print(f"完成！成功升級 {success_count} / {len(review_files)} 個頁面")


if __name__ == '__main__':
    main()
