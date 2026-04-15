// 為審核工具添加底色標示功能的腳本
const fs = require('fs');
const path = require('path');

const filePath = process.argv[2];
if (!filePath) {
    console.error('請提供 HTML 檔案路徑');
    process.exit(1);
}

let html = fs.readFileSync(filePath, 'utf8');

// 1. 添加新的 CSS 樣式（在 .card.confirmed 後面添加）
const newStyles = `
        /* 審核狀態底色 */
        .card.review-violation {
            background: linear-gradient(to bottom, #FEE2E2 0%, #FEF2F2 100%);
            border-color: #EF4444;
        }
        .card.review-false {
            background: linear-gradient(to bottom, #D1FAE5 0%, #ECFDF5 100%);
            border-color: #10B981;
        }
        .card.review-unclear {
            background: linear-gradient(to bottom, #FEF3C7 0%, #FFFBEB 100%);
            border-color: #F59E0B;
        }

        .review-badge {
            position: absolute;
            top: 12px;
            left: 12px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            display: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .card.review-violation .review-badge {
            display: block;
            background: #EF4444;
            color: white;
        }
        .card.review-violation .review-badge::before {
            content: "🚨 真實違規";
        }
        .card.review-false .review-badge {
            display: block;
            background: #10B981;
            color: white;
        }
        .card.review-false .review-badge::before {
            content: "✓ 誤判";
        }
        .card.review-unclear .review-badge {
            display: block;
            background: #F59E0B;
            color: white;
        }
        .card.review-unclear .review-badge::before {
            content: "⚠ 需複審";
        }

        .review-buttons {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border-color);
        }
        .btn-review {
            flex: 1;
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-review-violation {
            background: white;
            border-color: #EF4444;
            color: #EF4444;
        }
        .btn-review-violation:hover {
            background: #EF4444;
            color: white;
        }
        .btn-review-false {
            background: white;
            border-color: #10B981;
            color: #10B981;
        }
        .btn-review-false:hover {
            background: #10B981;
            color: white;
        }
        .btn-review-unclear {
            background: white;
            border-color: #F59E0B;
            color: #F59E0B;
        }
        .btn-review-unclear:hover {
            background: #F59E0B;
            color: white;
        }

        .review-stats {
            display: flex;
            gap: 12px;
            margin-top: 12px;
            font-size: 13px;
        }
        .review-stat {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .review-stat-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .review-stat-dot.violation { background: #EF4444; }
        .review-stat-dot.false { background: #10B981; }
        .review-stat-dot.unclear { background: #F59E0B; }
`;

// 插入新樣式（在第一個 </style> 之前）
html = html.replace('</style>', newStyles + '\n    </style>');

// 2. 在每個 card-media 中添加 review-badge div
html = html.replace(/<div class="confirmed-badge">✓ 已確認<\/div>/g,
    '<div class="confirmed-badge">✓ 已確認</div>\n                    <div class="review-badge"></div>');

// 3. 在每個 card-actions 中添加審核按鈕
const reviewButtons = `
                    <div class="review-buttons">
                        <button class="btn-review btn-review-violation" onclick="setReviewStatus(ID_PLACEHOLDER, 'violation')" title="快捷鍵: 1">
                            🚨 真實違規
                        </button>
                        <button class="btn-review btn-review-false" onclick="setReviewStatus(ID_PLACEHOLDER, 'false')" title="快捷鍵: 2">
                            ✓ 誤判
                        </button>
                        <button class="btn-review btn-review-unclear" onclick="setReviewStatus(ID_PLACEHOLDER, 'unclear')" title="快捷鍵: 3">
                            ⚠ 需複審
                        </button>
                    </div>`;

// 使用正則表達式匹配每個 card，並在 card-actions 後添加審核按鈕
html = html.replace(
    /<div class="card" data-id="(\d+)" id="card-\1">[\s\S]*?<div class="card-actions">([\s\S]*?)<\/div>/g,
    (match, id) => {
        const buttons = reviewButtons.replace(/ID_PLACEHOLDER/g, id);
        return match.replace('</div>', buttons + '\n                </div>');
    }
);

// 4. 添加新的 JavaScript 功能（在現有 script 結束前添加）
const newScript = `
        // 審核狀態管理
        const reviewStatus = {}; // { id: 'violation' | 'false' | 'unclear' }

        function setReviewStatus(id, status) {
            const card = document.getElementById('card-' + id);
            if (!card) return;

            // 移除所有審核狀態
            card.classList.remove('review-violation', 'review-false', 'review-unclear');

            // 設置新狀態
            if (reviewStatus[id] === status) {
                // 如果點擊相同狀態，則取消
                delete reviewStatus[id];
            } else {
                reviewStatus[id] = status;
                card.classList.add('review-' + status);
            }

            updateReviewStats();
            saveReviewState();
        }

        function updateReviewStats() {
            const violationCount = Object.values(reviewStatus).filter(s => s === 'violation').length;
            const falseCount = Object.values(reviewStatus).filter(s => s === 'false').length;
            const unclearCount = Object.values(reviewStatus).filter(s => s === 'unclear').length;

            // 更新統計（可選：在頁面上顯示）
            console.log('審核統計 - 真實違規:', violationCount, '誤判:', falseCount, '需複審:', unclearCount);
        }

        function saveReviewState() {
            localStorage.setItem('reviewStatus_' + DATE + '_' + CATEGORY, JSON.stringify(reviewStatus));
        }

        function loadReviewState() {
            const saved = localStorage.getItem('reviewStatus_' + DATE + '_' + CATEGORY);
            if (saved) {
                Object.assign(reviewStatus, JSON.parse(saved));
                // 恢復視覺狀態
                for (const [id, status] of Object.entries(reviewStatus)) {
                    const card = document.getElementById('card-' + id);
                    if (card) {
                        card.classList.add('review-' + status);
                    }
                }
                updateReviewStats();
            }
        }

        // 鍵盤快捷鍵
        let currentFocusedCard = null;

        document.addEventListener('keydown', (e) => {
            // 如果在輸入框中，不處理快捷鍵
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

            // 獲取當前聚焦的卡片
            const cards = Array.from(document.querySelectorAll('.card')).filter(c => c.style.display !== 'none');

            if (e.key === '1') {
                e.preventDefault();
                if (currentModalId) {
                    setReviewStatus(currentModalId, 'violation');
                }
            } else if (e.key === '2') {
                e.preventDefault();
                if (currentModalId) {
                    setReviewStatus(currentModalId, 'false');
                }
            } else if (e.key === '3') {
                e.preventDefault();
                if (currentModalId) {
                    setReviewStatus(currentModalId, 'unclear');
                }
            }
        });

        // 頁面載入時恢復審核狀態
        window.addEventListener('load', () => {
            loadReviewState();
        });

        // 導出審核結果
        function exportReviewResults() {
            const results = {
                date: DATE,
                category: CATEGORY,
                violation: [],
                false: [],
                unclear: []
            };

            for (const [id, status] of Object.entries(reviewStatus)) {
                const item = DATA.find(d => d.id == id);
                if (item) {
                    results[status].push({
                        id: item.id,
                        time: item.time_display,
                        message: item.mesg,
                        person_ids: item.person_ids,
                        image_url: item.image_url,
                        note: notes[id] || ''
                    });
                }
            }

            // 下載 JSON
            const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = \`審核結果_\${DATE}_\${CATEGORY}.json\`;
            a.click();
            URL.revokeObjectURL(url);
        }
`;

html = html.replace('    </script>', newScript + '\n    </script>');

// 5. 在 header 添加審核統計顯示
const statsHTML = `
                <div class="review-stats">
                    <div class="review-stat">
                        <div class="review-stat-dot violation"></div>
                        <span>真實違規: <strong id="violation-stat">0</strong></span>
                    </div>
                    <div class="review-stat">
                        <div class="review-stat-dot false"></div>
                        <span>誤判: <strong id="false-stat">0</strong></span>
                    </div>
                    <div class="review-stat">
                        <div class="review-stat-dot unclear"></div>
                        <span>需複審: <strong id="unclear-stat">0</strong></span>
                    </div>
                </div>`;

html = html.replace(
    /<div style="display: flex; gap: 12px;">/,
    statsHTML + '\n            <div style="display: flex; gap: 12px;">'
);

// 更新統計數字的函數
const updateStatsFunc = `
            document.getElementById('violation-stat').textContent = violationCount;
            document.getElementById('false-stat').textContent = falseCount;
            document.getElementById('unclear-stat').textContent = unclearCount;`;

html = html.replace(
    /console\.log\('審核統計 - 真實違規:', violationCount, '誤判:', falseCount, '需複審:', unclearCount\);/,
    updateStatsFunc
);

// 輸出修改後的檔案
const outputPath = filePath.replace('.html', '_審核增強版.html');
fs.writeFileSync(outputPath, html, 'utf8');

console.log('✅ 已生成增強版審核工具:', outputPath);
console.log('\n功能說明:');
console.log('1. 點擊底部的三個按鈕可標記審核狀態');
console.log('   - 🚨 真實違規（紅色底）');
console.log('   - ✓ 誤判（綠色底）');
console.log('   - ⚠ 需複審（黃色底）');
console.log('2. 在彈窗中可使用鍵盤快捷鍵:');
console.log('   - 按 1 = 真實違規');
console.log('   - 按 2 = 誤判');
console.log('   - 按 3 = 需複審');
console.log('3. 審核狀態會自動儲存在瀏覽器中');
console.log('4. 頂部會顯示各類別的統計數字');
