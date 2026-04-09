#!/usr/bin/env python3
"""
升級報告頁面：改為從 API 讀取已審核的報告資料
"""
import re
from pathlib import Path

API_BASE_URL = 'http://192.168.53.96:8001/api/v1'

def upgrade_report_page(html_path: Path):
    """修改報告頁面，連接 API"""

    content = html_path.read_text(encoding='utf-8')

    # 找到 loadData() 函數
    load_data_pattern = r'function loadData\(\) \{[\s\S]*?\n        \}'

    match = re.search(load_data_pattern, content)
    if not match:
        print(f"⚠️  找不到 loadData 函數: {html_path.name}")
        return False

    # 提取 DATE 和 CATEGORY
    date_match = re.search(r"const DATE = '([^']+)';", content)
    category_match = re.search(r"const CATEGORY = '([^']+)';", content)

    if not date_match or not category_match:
        print(f"⚠️  找不到 DATE 或 CATEGORY: {html_path.name}")
        return False

    date_val = date_match.group(1)
    category_val = category_match.group(1)

    # 建立新的 loadData 函數
    new_load_data = f'''function loadData() {{
            // 優先從 API 載入
            loadDataFromAPI();
        }}

        async function loadDataFromAPI() {{
            try {{
                const response = await fetch(`{API_BASE_URL}/reports/${{DATE}}/${{encodeURIComponent(CATEGORY)}}`);
                const result = await response.json();

                if (result.success && result.data.items && result.data.items.length > 0) {{
                    reportData = {{
                        date: result.data.date,
                        category: result.data.category,
                        items: result.data.items
                    }};
                    renderReport();
                    console.log(`✓ 從 API 載入 ${{reportData.items.length}} 筆已確認違規`);
                }} else {{
                    // 降級到 localStorage
                    console.log('API 無資料，嘗試從 localStorage 載入');
                    loadDataFromLocalStorage();
                }}
            }} catch (error) {{
                console.error('API 載入失敗:', error);
                // 降級到 localStorage
                loadDataFromLocalStorage();
            }}
        }}

        function loadDataFromLocalStorage() {{
            const stored = localStorage.getItem(REPORT_KEY);
            if (stored) {{
                reportData = JSON.parse(stored);
                renderReport();
                console.log('✓ 從 localStorage 載入 ' + reportData.items.length + ' 筆');
            }} else {{
                showError('無報告資料');
            }}
        }}

        function renderReport() {{
            if (!reportData.items || reportData.items.length === 0) {{
                showError('無已確認的違規項目');
                return;
            }}
            updateSummary();
            renderTable();
            updateDateTime();
        }}

        function showError(message) {{
            const container = document.querySelector('.report-content');
            if (container) {{
                container.innerHTML = `
                    <div style="padding: 60px 20px; text-align: center; color: #94A3B8;">
                        <div style="font-size: 64px; margin-bottom: 20px;">📄</div>
                        <div style="font-size: 18px; font-weight: 600; color: #64748B; margin-bottom: 12px;">${{message}}</div>
                        <div style="font-size: 14px; color: #94A3B8; margin-bottom: 30px;">請先完成違規審核</div>
                        <button onclick="history.back()" style="padding: 12px 24px; background: #3B82F6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500;">
                            返回審核頁面
                        </button>
                    </div>
                `;
            }}
        }}'''

    # 取代 loadData 函數
    new_content = re.sub(load_data_pattern, new_load_data, content)

    # 寫回檔案
    html_path.write_text(new_content, encoding='utf-8')

    return True


def main():
    """批次處理所有報告頁面"""

    base_dir = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026')

    report_files = list(base_dir.rglob('*_報告_管理版.html'))

    print(f"找到 {len(report_files)} 個報告頁面")
    print("=" * 60)

    success_count = 0

    for html_file in report_files:
        print(f"\n處理: {html_file.relative_to(base_dir)}")

        if upgrade_report_page(html_file):
            print(f"  ✓ 已升級")
            success_count += 1
        else:
            print(f"  ✗ 升級失敗")

    print("\n" + "=" * 60)
    print(f"完成！成功升級 {success_count} / {len(report_files)} 個頁面")


if __name__ == '__main__':
    main()
