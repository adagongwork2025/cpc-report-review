#!/usr/bin/env python3
"""
替換 generate_daily_review.py 中的 consolidate_confined_space_logs 函式
"""

# 新的函式內容
new_function = '''def consolidate_confined_space_logs(logs):
    """
    合併局限空間的通報
    - 設備缺失：每種類型只保留一筆有圖片的記錄
    - person相關（confined_person, heartbeat, harness）：同一個人ID在30分鐘內的多種違規類型合併為一筆
    - confined_space：同一個物件只保留一筆
    """
    if not logs:
        return logs

    # 分離不同類型
    equipment_logs = []
    person_logs = []  # confined_person, heartbeat, harness
    space_logs = []
    other_logs = []

    CONFINED_SPACE_EQUIPMENT_TYPES = [
        'No_rescue_tripod', 'No_venturi_tube', 'No_air_breathing_apparatus_cylinder',
        'No_notice_board', 'No_fire_extinguisher', 'equipment_missing'
    ]

    for log in logs:
        log_type = log.get('type', '')
        if log_type in CONFINED_SPACE_EQUIPMENT_TYPES:
            equipment_logs.append(log)
        elif log_type in ['confined_person', 'heartbeat', 'harness']:
            person_logs.append(log)
        elif log_type == 'confined_space':
            space_logs.append(log)
        else:
            other_logs.append(log)

    consolidated = []

    # 處理設備缺失：每種類型只保留一筆（優先選擇有圖片和影片的）
    if equipment_logs:
        type_groups = {}
        for log in equipment_logs:
            eq_type = log.get('type', '')
            if eq_type not in type_groups:
                type_groups[eq_type] = []
            type_groups[eq_type].append(log)

        type_names = {
            'No_rescue_tripod': '偵測到缺少救援三腳架',
            'No_venturi_tube': '偵測到未設置通風設備',
            'No_air_breathing_apparatus_cylinder': '偵測到缺少空氣呼吸器',
            'No_notice_board': '偵測到未設置局限空間佈告欄',
            'No_fire_extinguisher': '偵測到缺少滅火器'
        }

        for eq_type, type_logs in type_groups.items():
            best_log = None
            best_score = -1

            for log in type_logs:
                has_image = bool(log.get('key', ''))
                has_video = bool(log.get('video_key', ''))
                score = (2 if has_image else 0) + (1 if has_video else 0)

                if score > best_score:
                    best_log = log
                    best_score = score

            if best_log:
                best_log = dict(best_log)
                if eq_type in type_names:
                    best_log['mesg'] = type_names[eq_type]
                consolidated.append(best_log)

    # 處理人員相關違規：同一個人ID在30分鐘內的多種違規類型合併為一筆
    if person_logs:
        person_logs.sort(key=lambda x: x.get('time', ''))

        # 按照 ID 和時間分組
        person_groups = {}  # {(person_id, time_group): [logs]}

        for log in person_logs:
            mesg = log.get('mesg', '')
            match = re.search(r'ID[:\s]*(\d+)', mesg, re.IGNORECASE)
            person_id = match.group(1) if match else ''

            if not person_id:
                person_id = str(log.get('person_ids', ''))

            if not person_id:
                continue

            # 解析時間
            log_time_str = log.get('time', '')
            try:
                log_time = datetime.fromisoformat(log_time_str.replace('Z', '+00:00'))
            except:
                continue

            # 找到屬於哪個時間組
            found_group = False
            for (existing_id, group_time), group_logs in person_groups.items():
                if existing_id == person_id:
                    time_diff = abs(log_time - group_time)
                    if time_diff <= timedelta(minutes=30):
                        group_logs.append(log)
                        found_group = True
                        break

            if not found_group:
                person_groups[(person_id, log_time)] = [log]

        # 合併每個組的違規類型
        for (person_id, group_time), group_logs in person_groups.items():
            # 取第一筆作為基礎
            merged_log = dict(group_logs[0])

            # 收集所有違規類型
            violation_types = []
            type_map = {
                'confined_person': '局限人員安全',
                'heartbeat': '缺少生命偵測器',
                'harness': '缺少安全帶'
            }

            for log in group_logs:
                log_type = log.get('type', '')
                if log_type in type_map:
                    type_name = type_map[log_type]
                    if type_name not in violation_types:
                        violation_types.append(type_name)

            # 更新訊息，列出所有違規類型
            if violation_types:
                merged_log['mesg'] = '、'.join(violation_types) + f' ID:{person_id}'
                # 保存原始違規類型列表（用於顯示）
                merged_log['violation_types'] = violation_types

            consolidated.append(merged_log)

    # 處理 confined_space：同一個物件只保留一筆
    if space_logs:
        space_logs.sort(key=lambda x: x.get('time', ''))
        seen_objects = set()
        for log in space_logs:
            mesg = log.get('mesg', '')
            object_key = re.sub(r'ID[:\s]*\d+', '', mesg).strip()
            object_key = re.sub(r'\d{2}:\d{2}:\d{2}', '', object_key).strip()

            if object_key and object_key in seen_objects:
                continue
            if object_key:
                seen_objects.add(object_key)
            consolidated.append(log)

    # 加入其他類型
    consolidated.extend(other_logs)

    return consolidated
'''

# 讀取檔案
file_path = '/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/generate_daily_review.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到函式的起始和結束位置
start_line = 123  # 第 124 行（索引 123）
end_line = 313    # 第 314 行之前（索引 313）

# 替換函式
new_lines = lines[:start_line] + [new_function + '\n\n'] + lines[end_line:]

# 寫回檔案
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ 已更新 consolidate_confined_space_logs 函式")
print(f"  原本：第 124-{end_line} 行")
print(f"  新增：{len(new_function.split(chr(10)))} 行")
