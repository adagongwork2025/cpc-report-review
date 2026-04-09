#!/usr/bin/env python3
"""
保守修復審核頁面：只修改資料載入部分，保留原有邏輯
"""
import re
from pathlib import Path

API_BASE_URL = 'http://192.168.53.96:8001/api/v1'

def fix_review_page(html_path: Path):
    """保守修復審核頁面"""

    content = html_path.read_text(encoding='utf-8')

    # 檢查是否已經有 const DATA = [...] 格式
    data_match = re.search(r'const DATA = (\[.*?\]);', content, re.DOTALL)
    if not data_match:
        print(f"⚠️  找不到 DATA 陣列: {html_path.name}")
        return False

    # 提取 DATE 和 CATEGORY
    date_match = re.search(r"const DATE = '([^']+)';", content)
    category_match = re.search(r"const CATEGORY = '([^']+)';", content)

    if not date_match or not category_match:
        print(f"⚠️  找不到 DATE 或 CATEGORY: {html_path.name}")
        return False

    date_val = date_match.group(1)
    category_val = category_match.group(1)

    # 找到整個 <script> 區塊
    script_match = re.search(r'(<script>)(.*?)(</script>)', content, re.DOTALL)
    if not script_match:
        return False

    original_script = script_match.group(2)

    # 替換 DATA 陣列為空陣列 + API 載入
    new_data_section = f'''const API_BASE_URL = '{API_BASE_URL}';
        const DATA = [];  // 從 API 動態載入
        const DATE = '{date_val}';
        const CATEGORY = '{category_val}';'''

    # 移除舊的 const DATA, DATE, CATEGORY 定義
    modified_script = re.sub(
        r'const DATA = \[.*?\];.*?const DATE = .*?;.*?const CATEGORY = .*?;',
        new_data_section,
        original_script,
        flags=re.DOTALL
    )

    # 在 loadState() 函數之前插入 API 載入邏輯
    api_load_function = '''

        // 從 API 載入資料
        async function loadDataFromAPI() {
            try {
                const response = await fetch(`${API_BASE_URL}/detection-logs/${DATE}/${encodeURIComponent(CATEGORY)}`);
                const result = await response.json();

                if (result.success && result.data.items) {
                    // 將 API 資料填入 DATA 陣列
                    DATA.push(...result.data.items);

                    // 套用審核狀態
                    DATA.forEach(item => {
                        if (item.review_status === 'confirmed') {
                            confirmedIds.add(item.id);
                            const card = document.getElementById('card-' + item.id);
                            const btn = document.getElementById('btn-confirm-' + item.id);
                            if (card && btn) {
                                card.classList.add('confirmed');
                                btn.classList.add('confirmed');
                                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
                            }
                        } else if (item.review_status === 'deleted') {
                            deletedIds.add(item.id);
                            const card = document.getElementById('card-' + item.id);
                            if (card) card.style.display = 'none';
                        }
                        if (item.note) {
                            notes[item.id] = item.note;
                            const input = document.getElementById('note-' + item.id);
                            if (input) input.value = item.note;
                        }
                    });

                    updateStats();
                    console.log(`✓ 從 API 載入 ${DATA.length} 筆資料`);
                } else {
                    console.error('API 資料格式錯誤');
                }
            } catch (error) {
                console.error('API 載入失敗:', error);
            }
        }

        // 提交審核到 API
        async function submitReviewToAPI() {
            const actions = [];
            confirmedIds.forEach(id => {
                actions.push({ detection_log_id: id, action: 'confirmed', note: notes[id] || null });
            });
            deletedIds.forEach(id => {
                actions.push({ detection_log_id: id, action: 'deleted', note: null });
            });

            if (actions.length === 0) return;

            try {
                await fetch(`${API_BASE_URL}/reviews/actions/bulk`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        date: DATE,
                        category: CATEGORY,
                        actions: actions,
                        reviewer_ip: 'web_client'
                    })
                });
            } catch (error) {
                console.error('提交失敗:', error);
            }
        }

'''

    # 插入 API 函數
    if 'function loadState()' in modified_script:
        modified_script = modified_script.replace(
            'function loadState()',
            api_load_function + '        function loadState()'
        )
    else:
        print(f"⚠️  找不到 loadState 函數: {html_path.name}")
        return False

    # 修改 saveState() 改為呼叫 API
    modified_script = re.sub(
        r'function saveState\(\) \{[\s\S]*?localStorage\.setItem\(STORAGE_KEY.*?\);[\s\S]*?\}',
        'function saveState() { submitReviewToAPI(); }',
        modified_script
    )

    # 修改頁面載入邏輯
    modified_script = modified_script.replace(
        "window.addEventListener('load', loadState);",
        "window.addEventListener('load', () => { loadDataFromAPI().then(loadState); });"
    )

    # 組合新的內容
    new_content = content.replace(
        script_match.group(0),
        f'<script>{modified_script}</script>'
    )

    # 寫回檔案
    html_path.write_text(new_content, encoding='utf-8')
    return True


def main():
    """批次修復所有審核頁面"""

    base_dir = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026')
    review_files = list(base_dir.rglob('*_審核.html'))

    print(f"找到 {len(review_files)} 個審核頁面")
    print("=" * 60)

    success_count = 0
    for html_file in review_files:
        print(f"\n處理: {html_file.relative_to(base_dir)}")
        if fix_review_page(html_file):
            print(f"  ✓ 已修復")
            success_count += 1
        else:
            print(f"  ✗ 修復失敗")

    print("\n" + "=" * 60)
    print(f"完成！成功修復 {success_count} / {len(review_files)} 個頁面")


if __name__ == '__main__':
    main()
