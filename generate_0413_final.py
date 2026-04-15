#!/usr/bin/env python3
import json, re, os

# === 設定 ===
DATE = '2026-04-13'
OUTPUT_DIR = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/13'
TEMPLATE_DIR = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/09'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 讀取資料
with open('/tmp/867_unique_0413.json') as f: data_867 = json.load(f)
with open('/tmp/758_unique_0413.json') as f: data_758 = json.load(f)

print(f"資料載入:")
print(f"  Camera 867 (高處A): {len(data_867)} 筆")
print(f"  Camera 758 (高處B): {len(data_758)} 筆\n")

# === 處理函數 ===
def extract_video_path(vk):
    if 'path:' in vk:
        m = re.search(r'path:([^\s,]+)', vk)
        if m: return m.group(1)
    return vk

def process(raw):
    proc = []
    for it in raw:
        t = it.get('time','').split('T')[1][:8] if 'T' in it.get('time','') else ''
        ids = ', '.join(re.findall(r'ID:(\d+)', it.get('mesg','')))
        proc.append({
            'id': it['id'], 'time_display': t, 'mesg': it.get('mesg',''),
            'type': it.get('type',''), 'person_ids': ids,
            'image_url': f"https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image?key={it.get('key','')}",
            'video_url': f"https://apigatewayiseek.intemotech.com/vision_logic/video?key={extract_video_path(it.get('video_key',''))}"
        })
    proc.sort(key=lambda x: x['time_display'], reverse=True)
    return proc

data_867_proc = process(data_867)
data_758_proc = process(data_758)

# === 產生頁面 ===
with open(f'{TEMPLATE_DIR}/高處作業_審核.html') as f: tmpl = f.read()
with open(f'{TEMPLATE_DIR}/高處作業_報告_管理版.html') as f: rep_tmpl = f.read()

def gen(cat, proc_data):
    dj = json.dumps(proc_data, ensure_ascii=False)
    tot = len(proc_data)
    
    # 審核頁
    h = tmpl.replace('2026-04-09', DATE)
    h = re.sub(r'<span class="highlight">高處作業</span>', f'<span class="highlight">{cat}</span>', h)
    h = re.sub(r"const CATEGORY = '高處作業';", f"const CATEGORY = '{cat}';", h)
    h = re.sub(r'const DATA = \[.*?\];', f'const DATA = {dj};', h, flags=re.DOTALL)
    h = re.sub(r'id="pending-count">356<', f'id="pending-count">{tot}<', h)
    h = re.sub(r'let (confirmed|deleted)Ids = new Set\(.*?\);', r'let \1Ids = new Set();', h)
    
    # 報告頁  
    r = rep_tmpl.replace('2026-04-09', DATE)
    r = re.sub(r'高處作業', cat, r)
    r = re.sub(r"const CATEGORY = '.*?';", f"const CATEGORY = '{cat}';", r)
    
    return h, r

h_a, r_a = gen('高處A', data_867_proc)
h_b, r_b = gen('高處B', data_758_proc)

with open(f'{OUTPUT_DIR}/高處A_審核.html', 'w', encoding='utf-8') as f: f.write(h_a)
with open(f'{OUTPUT_DIR}/高處A_報告_管理版.html', 'w', encoding='utf-8') as f: f.write(r_a)
with open(f'{OUTPUT_DIR}/高處B_審核.html', 'w', encoding='utf-8') as f: f.write(h_b)
with open(f'{OUTPUT_DIR}/高處B_報告_管理版.html', 'w', encoding='utf-8') as f: f.write(r_b)

print(f"✓ 高處A 審核頁面 ({len(data_867_proc)} 筆)")
print(f"✓ 高處A 報告頁面")
print(f"✓ 高處B 審核頁面 ({len(data_758_proc)} 筆)")
print(f"✓ 高處B 報告頁面")
print(f"\n檔案位置: {OUTPUT_DIR}")
