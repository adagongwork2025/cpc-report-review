#!/usr/bin/env python3
"""
中油偵測報告去重工具
分別清理每個審核頁面內部的重複資料

去重規則：
- 相同 ID + 相同時間段（都是早上 or 都是下午）→ 才算重複，只保留一筆
- 相同 ID + 不同時間段（一個早上一個下午）→ 不算重複，兩筆都保留
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def get_time_period(time_str):
    """判斷時間是早上還是下午"""
    if not time_str:
        return None

    try:
        if ':' in time_str:
            time_part = time_str.split()[-1]
            hour = int(time_part.split(':')[0])
            return 'AM' if hour < 12 else 'PM'
    except:
        pass

    return None

def extract_data_from_html(html_path):
    """從 HTML 文件中提取 DATA 變量的內容"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'const DATA = (\[.*?\]);'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        raise ValueError(f"無法在 {html_path} 中找到 DATA 變量")

    data_json = match.group(1)
    data = json.loads(data_json)

    return {
        'data': data,
        'full_content': content,
        'data_match': match
    }

def deduplicate_violations(data_list):
    """根據違規類型和時間段去重"""
    
    equipment_types = {
        'No_rescue_tripod', 'No_venturi_tube',
        'No_air_breathing_apparatus_cylinder',
        'No_notice_board', 'NO_fire_extinguisher'
    }

    person_types = {'heartbeat', 'harness', 'confined_person'}
    object_types = {'confined_space'}

    unique_data = []
    equipment_seen = set()
    person_seen = defaultdict(set)
    object_seen = defaultdict(set)
    other_seen = set()
    removed_count = 0

    for item in data_list:
        violation_type = item.get('type', '')
        time_display = item.get('time_display', '')
        time_period = get_time_period(time_display)

        if violation_type in equipment_types:
            camera_id = item.get('camera_id', '')
            key = (camera_id, violation_type, time_period)
            if key in equipment_seen:
                print(f"  🗑️  設備缺失重複: {violation_type} @ camera {camera_id} ({time_period})")
                removed_count += 1
                continue
            equipment_seen.add(key)
            unique_data.append(item)

        elif violation_type in person_types:
            person_id = item.get('person_id') or item.get('id')
            key = (person_id, time_period)
            if person_id and key in person_seen[violation_type]:
                print(f"  🗑️  人員重複: {violation_type} - 人員 ID {person_id} ({time_period})")
                removed_count += 1
                continue
            if person_id:
                person_seen[violation_type].add(key)
            unique_data.append(item)

        elif violation_type in object_types:
            object_id = item.get('object_id') or item.get('id')
            key = (object_id, time_period)
            if object_id and key in object_seen[violation_type]:
                print(f"  🗑️  物件重複: {violation_type} - 物件 ID {object_id} ({time_period})")
                removed_count += 1
                continue
            if object_id:
                object_seen[violation_type].add(key)
            unique_data.append(item)

        else:
            item_id = item.get('id')
            key = (item_id, time_period)
            if item_id and key in other_seen:
                print(f"  🗑️  重複 ID: {item_id} - {violation_type} ({time_period})")
                removed_count += 1
                continue
            if item_id:
                other_seen.add(key)
            unique_data.append(item)

    return unique_data, removed_count

def update_html_with_deduped_data(html_path, deduped_data):
    """更新 HTML 文件中的 DATA 變量"""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r'(const DATA = )\[.*?\];'
    new_data_json = json.dumps(deduped_data, ensure_ascii=False, indent=4)
    new_content = re.sub(pattern, r'\1' + new_data_json + ';', content, flags=re.DOTALL)

    total_count = len(deduped_data)
    new_content = re.sub(
        r'(<span class="stat-num" id="pending-count">)\d+(</span>)',
        r'\g<1>' + str(total_count) + r'\g<2>',
        new_content
    )

    backup_path = html_path.replace('.html', '_備份.html')
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return backup_path

def process_single_page(html_path):
    """處理單個頁面的去重"""
    print(f"\n{'='*60}")
    print(f"📄 處理: {Path(html_path).name}")
    print(f"{'='*60}")

    info = extract_data_from_html(html_path)
    original_data = info['data']
    original_count = len(original_data)

    print(f"📊 去重前: {original_count} 筆記錄")

    deduped_data, removed_count = deduplicate_violations(original_data)
    deduped_count = len(deduped_data)

    print(f"\n✅ 去重後: {deduped_count} 筆記錄")
    print(f"🗑️  已移除: {removed_count} 筆重複")

    if removed_count > 0:
        backup_path = update_html_with_deduped_data(html_path, deduped_data)
        print(f"\n💾 已更新原文件")
        print(f"📦 備份保存於: {Path(backup_path).name}")
    else:
        print(f"\n✨ 無重複資料，無需更新")

    return {
        'path': html_path,
        'original_count': original_count,
        'deduped_count': deduped_count,
        'removed_count': removed_count
    }

def main():
    pages = [
        "2026/04/14/高處作業_審核.html",
        "2026/04/13/高處作業_審核.html"
    ]

    print("\n" + "="*60)
    print("中油偵測報告 - 各頁面內部去重工具")
    print("="*60)
    print("規則：相同 ID + 相同時間段才算重複")
    print("     早上和下午的記錄都會保留")
    print("="*60)

    base_dir = Path(__file__).parent

    results = []
    for page_path in pages:
        full_path = base_dir / page_path
        if not full_path.exists():
            print(f"\n⚠️  檔案不存在: {page_path}")
            continue

        result = process_single_page(str(full_path))
        results.append(result)

    print(f"\n{'='*60}")
    print("📋 處理總結")
    print(f"{'='*60}")

    total_original = sum(r['original_count'] for r in results)
    total_deduped = sum(r['deduped_count'] for r in results)
    total_removed = sum(r['removed_count'] for r in results)

    for r in results:
        print(f"\n{Path(r['path']).name}:")
        print(f"  原始: {r['original_count']} 筆")
        print(f"  去重後: {r['deduped_count']} 筆")
        print(f"  移除: {r['removed_count']} 筆")

    print(f"\n總計:")
    print(f"  原始總數: {total_original} 筆")
    print(f"  去重後總數: {total_deduped} 筆")
    print(f"  移除總數: {total_removed} 筆")
    print(f"\n{'='*60}")

if __name__ == '__main__':
    main()
