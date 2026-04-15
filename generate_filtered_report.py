#!/usr/bin/env python3
"""
產生高處B的過濾報告 - 只包含8筆確認違規
"""
import json
import re

# 讀取原始資料
with open('/tmp/758_unique.json', 'r') as f:
    data_758 = json.load(f)

# 確認違規的時間
confirmed_times = [
    '09:45:18',
    '09:34:44',
    '09:32:40',
    '09:30:33',
    '09:29:39',
    '09:01:37',
    '09:01:15',
    '08:58:39'
]

def extract_video_path(video_key):
    if 'path:' in video_key:
        match = re.search(r'path:([^\s,]+)', video_key)
        if match:
            return match.group(1)
    return video_key

def process_item(item):
    video_key = extract_video_path(item.get('video_key', ''))
    time_str = item.get('time', '')
    time_display = time_str.split('T')[1][:8] if 'T' in time_str else ''

    mesg = item.get('mesg', '')
    ids_match = re.findall(r'ID:(\d+)', mesg)
    person_ids = ', '.join(ids_match) if ids_match else ''

    return {
        'id': item.get('id'),
        'time_display': time_display,
        'mesg': mesg,
        'type': item.get('type', ''),
        'person_ids': person_ids,
        'image_url': f"https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image?key={item.get('key', '')}",
        'video_url': f"https://apigatewayiseek.intemotech.com/vision_logic/video?key={video_key}"
    }

# 處理所有資料並找出確認的項目
all_processed = [process_item(item) for item in data_758]
confirmed_items = [item for item in all_processed if item['time_display'] in confirmed_times]
confirmed_ids = [item['id'] for item in confirmed_items]
all_ids = [item['id'] for item in all_processed]
deleted_ids = [id for id in all_ids if id not in confirmed_ids]

print(f"總資料: {len(all_processed)} 筆")
print(f"確認違規: {len(confirmed_items)} 筆")
print(f"已刪除: {len(deleted_ids)} 筆")
print(f"\n確認的項目:")
for item in confirmed_items:
    print(f"  - {item['time_display']} {item['mesg']}")

# 輸出資料
output = {
    'confirmed_items': confirmed_items,
    'confirmed_ids': confirmed_ids,
    'deleted_ids': deleted_ids,
    'all_processed': all_processed
}

with open('/tmp/filtered_report_758.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n已儲存至 /tmp/filtered_report_758.json")
