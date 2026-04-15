#!/usr/bin/env node

/**
 * AI 自動審核腳本
 * 使用 Claude API 自動審核高處作業安全違規案例
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// 從環境變數讀取 API Key
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;

if (!ANTHROPIC_API_KEY) {
    console.error('❌ 錯誤: 請設定 ANTHROPIC_API_KEY 環境變數');
    console.error('   export ANTHROPIC_API_KEY="your-api-key"');
    process.exit(1);
}

const INPUT_FILE = process.argv[2] || '高處A_審核.html';
const OUTPUT_FILE = INPUT_FILE.replace('.html', '_AI審核結果.html');
const TEST_LIMIT = parseInt(process.argv[3]) || 10; // 預設只測試 10 個案例

console.log('🤖 AI 自動審核系統');
console.log('================================');
console.log('輸入檔案:', INPUT_FILE);
console.log('輸出檔案:', OUTPUT_FILE);
console.log('');

// 從 HTML 提取案例資料
function extractCasesFromHTML(html) {
    const cases = [];
    const dataMatch = html.match(/const DATA = (\[[\s\S]*?\]);/);

    if (!dataMatch) {
        console.error('❌ 無法從 HTML 中提取案例資料');
        return cases;
    }

    try {
        const data = eval(dataMatch[1]);
        return data.map(item => ({
            id: item.id,
            image_url: item.image_url,
            video_url: item.video_url,
            mesg: item.mesg,
            time_display: item.time_display,
            person_ids: item.person_ids
        }));
    } catch (e) {
        console.error('❌ 解析案例資料失敗:', e.message);
        return cases;
    }
}

// 下載圖片並轉換為 base64
function downloadImageAsBase64(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            if (res.statusCode !== 200) {
                reject(new Error(`HTTP ${res.statusCode}`));
                return;
            }

            const chunks = [];
            res.on('data', chunk => chunks.push(chunk));
            res.on('end', () => {
                const buffer = Buffer.concat(chunks);
                const base64 = buffer.toString('base64');
                resolve({
                    base64,
                    mediaType: res.headers['content-type'] || 'image/jpeg'
                });
            });
        }).on('error', reject);
    });
}

// 使用 Claude API 分析圖片
async function analyzeImage(imageData, caseInfo) {
    const prompt = `你是一位工地安全專家，專門審核高處作業的安全違規案例。

案例資訊：
- 偵測訊息：${caseInfo.mesg}
- 時間：${caseInfo.time_display}
- 人員 ID：${caseInfo.person_ids}

請仔細檢查這張工地監控畫面，判斷這是否為真實的安全違規：

【審核重點】
1. 是否有人員在鷹架（施工架）上作業？
2. 人員的安全掛鉤是否**確實掛在施工架的橫桿上**？
3. 還是掛鉤只是掛在自己的安全帶上，或者懸空沒有掛好？

【判斷標準】
- **真實違規**：明確看到人員在高處，但安全掛鉤沒有掛在施工架上
- **誤判**：沒有人員在鷹架上 / 掛鉤已正確掛好 / 畫面不清楚無法判斷是否在高處作業
- **需複審**：畫面模糊、角度不佳、無法確定是否正確掛好

請用以下格式回答（只回答一個詞）：
violation（真實違規）
false（誤判）
unclear（需複審）

然後用一句話說明你的判斷理由。

格式：
判斷: [violation/false/unclear]
理由: [一句話說明]`;

    const requestBody = {
        model: 'claude-3-5-sonnet-20241022',
        max_tokens: 200,
        messages: [{
            role: 'user',
            content: [
                {
                    type: 'image',
                    source: {
                        type: 'base64',
                        media_type: imageData.mediaType,
                        data: imageData.base64
                    }
                },
                {
                    type: 'text',
                    text: prompt
                }
            ]
        }]
    };

    return new Promise((resolve, reject) => {
        const req = https.request({
            hostname: 'api.anthropic.com',
            path: '/v1/messages',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': ANTHROPIC_API_KEY,
                'anthropic-version': '2023-06-01'
            }
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                if (res.statusCode !== 200) {
                    reject(new Error(`API Error: ${res.statusCode} - ${data}`));
                    return;
                }

                try {
                    const response = JSON.parse(data);
                    const text = response.content[0].text;

                    // 解析回應
                    const judgmentMatch = text.match(/判斷[:\s]*([a-z]+)/i);
                    const reasonMatch = text.match(/理由[:\s]*(.+)/i);

                    resolve({
                        judgment: judgmentMatch ? judgmentMatch[1].toLowerCase() : 'unclear',
                        reason: reasonMatch ? reasonMatch[1].trim() : text.substring(0, 100),
                        fullText: text
                    });
                } catch (e) {
                    reject(new Error('解析 API 回應失敗: ' + e.message));
                }
            });
        });

        req.on('error', reject);
        req.write(JSON.stringify(requestBody));
        req.end();
    });
}

// 主要處理流程
async function main() {
    // 讀取 HTML
    const html = fs.readFileSync(INPUT_FILE, 'utf8');
    console.log('✓ 已讀取 HTML 檔案\n');

    // 提取案例
    let cases = extractCasesFromHTML(html);
    console.log(`✓ 找到 ${cases.length} 個案例`);

    // 測試模式：只處理前 N 個案例
    if (TEST_LIMIT && TEST_LIMIT < cases.length) {
        console.log(`⚠️  測試模式：只審核前 ${TEST_LIMIT} 個案例\n`);
        cases = cases.slice(0, TEST_LIMIT);
    } else {
        console.log(`\n`);
    }

    if (cases.length === 0) {
        console.error('❌ 沒有找到任何案例');
        process.exit(1);
    }

    // 審核結果
    const results = {};
    const stats = { violation: 0, false: 0, unclear: 0, error: 0 };

    // 處理每個案例
    for (let i = 0; i < cases.length; i++) {
        const caseData = cases[i];
        const progress = `[${i + 1}/${cases.length}]`;

        console.log(`${progress} 審核案例 ID: ${caseData.id}`);
        console.log(`    訊息: ${caseData.mesg}`);

        try {
            // 下載圖片
            process.stdout.write('    下載圖片... ');
            const imageData = await downloadImageAsBase64(caseData.image_url);
            console.log('✓');

            // AI 分析
            process.stdout.write('    AI 分析中... ');
            const analysis = await analyzeImage(imageData, caseData);
            console.log('✓');

            console.log(`    判斷: ${analysis.judgment}`);
            console.log(`    理由: ${analysis.reason}`);
            console.log('');

            results[caseData.id] = {
                judgment: analysis.judgment,
                reason: analysis.reason
            };

            stats[analysis.judgment] = (stats[analysis.judgment] || 0) + 1;

            // 避免 API 速率限制，每個請求間隔 1 秒
            if (i < cases.length - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

        } catch (error) {
            console.log('✗');
            console.error(`    錯誤: ${error.message}`);
            console.log('');

            results[caseData.id] = {
                judgment: 'unclear',
                reason: '審核失敗: ' + error.message
            };
            stats.error++;
        }
    }

    // 顯示統計
    console.log('================================');
    console.log('📊 審核統計');
    console.log('================================');
    console.log(`真實違規: ${stats.violation}`);
    console.log(`誤判: ${stats.false}`);
    console.log(`需複審: ${stats.unclear}`);
    console.log(`錯誤: ${stats.error}`);
    console.log('');

    // 將結果寫入 HTML
    console.log('正在生成結果檔案...');

    const resultsJson = JSON.stringify(results, null, 2);
    const resultsScript = `
        // AI 審核結果（自動生成）
        const AI_REVIEW_RESULTS = ${resultsJson};

        // 自動套用審核結果
        window.addEventListener('load', () => {
            for (const [id, result] of Object.entries(AI_REVIEW_RESULTS)) {
                reviewStatus[id] = result.judgment;
                const card = document.getElementById('card-' + id);
                if (card) {
                    card.classList.add('review-' + result.judgment);

                    // 設定備註
                    const noteInput = document.getElementById('note-' + id);
                    if (noteInput && !noteInput.value) {
                        noteInput.value = 'AI: ' + result.reason;
                        notes[id] = 'AI: ' + result.reason;
                    }
                }
            }
            updateReviewStats();
            console.log('✓ 已載入 AI 審核結果');
        });
    `;

    let outputHtml = html.replace('</script>', resultsScript + '\n    </script>');

    fs.writeFileSync(OUTPUT_FILE, outputHtml, 'utf8');

    console.log('✓ 結果已儲存至:', OUTPUT_FILE);
    console.log('\n🎉 審核完成！請開啟輸出檔案查看結果。');
}

// 執行
main().catch(err => {
    console.error('\n❌ 發生錯誤:', err);
    process.exit(1);
});
