#!/usr/bin/env python3
"""
中油偵測報告產生器
每日從 API 取得資料，依類別產生審核工具頁面
"""

import json
import re
import urllib.request
import ssl
from datetime import datetime, timedelta
from pathlib import Path

# 設定
API_URL = 'https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/filter'
BASE_DIR = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/cpc-reports-backend-v2')

# 審核系統 API（替代 localStorage）
REVIEW_API_BASE = 'http://192.168.53.96:8001/api/v1'

# Camera ID 設定
CAMERA_IDS = ['758', '837']  # 758=高處作業, 837=局限空間

# 類別分類規則
CATEGORIES = {
    '高處作業': {
        'camera_id': '758',
        'types': ['hooked', 'harness'],
        'display_types': ['已掛鉤', '背負式安全帶']
    },
    '局限空間': {
        'camera_id': '837',
        'types': ['No_rescue_tripod', 'No_venturi_tube', 'No_air_breathing_apparatus_cylinder', 'No_notice_board', 'No_fire_extinguisher', 'heartbeat', 'harness', 'confined_person', 'confined_space', 'equipment_missing'],
        'display_types': ['無救援三腳架', '無文氏管', '無空氣呼吸器鋼瓶', '無告示牌', '無滅火器', '生命偵測器', '未穿戴安全帶', '局限人員安全', '局限空間場域安全', '設備缺失']
    },
    '待分類': {
        'camera_id': None,  # 任何 camera 都可能有
        'types': ['no_hardhat', 'no_safety_vest'],
        'display_types': ['未戴安全帽', '未穿安全背心']
    }
}


def fetch_api_data(date_str, camera_id):
    """呼叫 API 取得當天所有資料（支援分頁）"""
    all_logs = []
    page = 1
    per_page = 1000

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    while True:
        payload = {
            "start_time": f"{date_str}T00:00:00",
            "end_time": f"{date_str}T23:59:59",
            "camera_id": camera_id,
            "per_page": per_page,
            "page": page
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0'
                }
            )

            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                logs = result.get('logs', [])
                total = result.get('total', 0)
                total_pages = result.get('total_pages', 1)

                all_logs.extend(logs)

                if page == 1 and total > per_page:
                    print(f"    總共 {total} 筆，分 {total_pages} 頁取得...")

                if page >= total_pages or not logs:
                    break

                page += 1

        except Exception as e:
            print(f"  API 錯誤 (camera_id={camera_id}, page={page}): {e}")
            break

    return all_logs


def categorize_logs(logs):
    """將 logs 依類別分類（優先使用 camera_id，其次用 type）"""
    categorized = {cat: [] for cat in CATEGORIES}

    for log in logs:
        log_type = log.get('type', '')
        camera_id = str(log.get('camera_id', ''))
        categorized_flag = False

        # 優先依 camera_id 分類
        for cat, config in CATEGORIES.items():
            if config.get('camera_id') and camera_id == config['camera_id']:
                categorized[cat].append(log)
                categorized_flag = True
                break

        # 如果沒有匹配的 camera_id，則依 type 分類（用於待分類等）
        if not categorized_flag:
            for cat, config in CATEGORIES.items():
                if log_type in config['types']:
                    categorized[cat].append(log)
                    break

    return categorized


# 局限空間設備缺失類型（每種只保留一筆有圖片的）
CONFINED_SPACE_EQUIPMENT_TYPES = ['No_rescue_tripod', 'No_venturi_tube', 'No_air_breathing_apparatus_cylinder', 'No_notice_board', 'No_fire_extinguisher']


def consolidate_confined_space_logs(logs):
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


def extract_id_from_mesg(mesg):
    """從 mesg 中提取 ID 並清理"""
    if not mesg:
        return '', ''

    # 嘗試匹配最後一個 ID
    match = re.search(r'\s*ID[:\s]*(\d+)\s*,?\s*$', mesg, re.IGNORECASE)
    if match:
        id_val = match.group(1)
        mesg_clean = mesg[:match.start()].strip()
        # 移除所有 ID 標記（可能有多個）
        mesg_clean = re.sub(r'\s*ID[:\s]*[\d,\s]+', '', mesg_clean, flags=re.IGNORECASE).strip()
        return mesg_clean, id_val

    # 嘗試匹配任何位置的 ID
    match = re.search(r'ID[:\s]*(\d+)', mesg, re.IGNORECASE)
    if match:
        id_val = match.group(1)
        mesg_clean = re.sub(r'\s*ID[:\s]*[\d,\s]+', '', mesg, flags=re.IGNORECASE).strip()
        return mesg_clean, id_val

    return mesg, ''


def get_display_tag(mesg, log_type):
    """根據 mesg 和 type 取得顯示用的標籤"""
    mesg_clean, person_id = extract_id_from_mesg(mesg)

    # 如果 mesg 是「人員未穿戴必要裝備」，根據 type 顯示具體缺少什麼
    if '人員未穿戴必要裝備' in mesg_clean:
        type_to_equipment = {
            'heartbeat': '缺少生命偵測器',
            'harness': '缺少安全帶',
            'no_hardhat': '未戴安全帽',
            'no_safety_vest': '未穿安全背心'
        }
        if log_type in type_to_equipment:
            tag = type_to_equipment[log_type]
            # 特殊處理：ID 746 顯示為「未戴安全帽」
            if person_id == '746' and log_type == 'heartbeat':
                tag = '未戴安全帽'
            if person_id:
                tag += f' (ID:{person_id})'
            return tag

    return mesg_clean


def generate_review_html(category, date_str, total, cards_html, data_json, report_path, preset_times=None, api_base=None):
    """產生審核工具 HTML
    preset_times: 預設要確認的 time_display 列表（可選）
    api_base: 審核系統 API 基礎 URL
    """
    if api_base is None:
        api_base = REVIEW_API_BASE
    preset_times_json = json.dumps(preset_times or [], ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 違規審核 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --success: #10B981;
            --success-bg: #ECFDF5;
            --error: #EF4444;
            --error-bg: #FEF2F2;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #FFFFFF;
            color: var(--text-dark);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{
            background: #FFFFFF;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        .header-title .highlight {{
            color: var(--accent-blue);
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .meta-divider {{
            width: 1px;
            height: 16px;
            background: var(--border-color);
        }}

        .stats-row {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .stat-box {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 8px;
            background: var(--bg-light);
        }}
        .stat-box.pending {{ background: var(--warning-bg); }}
        .stat-box.success {{ background: var(--success-bg); }}
        .stat-box.error {{ background: var(--error-bg); }}
        .stat-num {{
            font-size: 18px;
            font-weight: 700;
        }}
        .stat-box.pending .stat-num {{ color: var(--warning); }}
        .stat-box.success .stat-num {{ color: var(--success); }}
        .stat-box.error .stat-num {{ color: var(--error); }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            text-decoration: none;
        }}
        .btn-dark {{
            background: var(--text-dark);
            color: white;
        }}
        .btn-dark:hover {{
            background: #1E293B;
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1.5px solid var(--border-color);
        }}
        .btn-outline:hover {{
            border-color: var(--text-secondary);
            background: var(--bg-light);
        }}
        .btn-sm {{
            padding: 8px 14px;
            font-size: 12px;
            border-radius: 8px;
        }}
        .btn-confirm {{
            background: white;
            color: var(--success);
            border: 1.5px solid var(--success);
        }}
        .btn-confirm:hover {{
            background: var(--success-bg);
        }}
        .btn-confirm.confirmed {{
            background: var(--success);
            color: white;
        }}
        .btn-delete {{
            background: white;
            color: var(--error);
            border: 1.5px solid var(--error);
        }}
        .btn-delete:hover {{
            background: var(--error-bg);
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
            padding-top: 100px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 24px;
        }}

        .card {{
            background: white;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: all 0.25s ease;
        }}
        .card:hover {{
            border-color: #CBD5E1;
            box-shadow: 0 8px 24px rgba(15,23,42,0.08);
            transform: translateY(-4px);
        }}
        .card.removing {{
            animation: fadeOut 0.3s ease forwards;
        }}
        .card.confirmed {{
            border-color: var(--success);
        }}
        @keyframes fadeOut {{
            to {{ opacity: 0; transform: scale(0.96); }}
        }}

        .card-media {{
            position: relative;
            aspect-ratio: 16/9;
            background: #0F172A;
            overflow: hidden;
        }}
        .card-media img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        .card:hover .card-media img {{
            transform: scale(1.05);
        }}
        .play-btn {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(255,255,255,0.95);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .play-btn:hover {{
            transform: translate(-50%, -50%) scale(1.1);
        }}
        .play-btn svg {{
            width: 24px;
            height: 24px;
            fill: var(--text-dark);
            margin-left: 4px;
        }}
        .confirmed-badge {{
            position: absolute;
            top: 12px;
            right: 12px;
            background: var(--success);
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            display: none;
        }}
        .card.confirmed .confirmed-badge {{
            display: block;
        }}

        .card-body {{
            padding: 16px;
        }}
        .card-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .card-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            line-height: 1.4;
        }}
        .card-tag {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            background: var(--warning-bg);
            color: var(--warning);
            word-break: keep-all;
        }}
        .card-info {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }}
        .card-note {{
            margin-bottom: 12px;
        }}
        .note-input {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 13px;
            background: var(--bg-light);
            transition: border-color 0.2s;
        }}
        .note-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
            background: #fff;
        }}
        .note-input::placeholder {{
            color: var(--text-muted);
        }}
        .card-actions {{
            display: flex;
            gap: 8px;
        }}
        .card-actions .btn {{
            flex: 1;
        }}

        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 32px;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal {{
            background: white;
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
        }}
        .modal-title {{
            font-size: 16px;
            font-weight: 600;
        }}
        .modal-close {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: none;
            background: var(--bg-light);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-body {{
            padding: 24px;
            overflow-y: auto;
        }}
        .modal-video {{
            width: 100%;
            border-radius: 8px 8px 0 0;
            background: #000;
            min-height: 300px;
        }}
        .modal-video::-webkit-media-controls-panel {{
            background: linear-gradient(transparent, rgba(0,0,0,0.7)) !important;
        }}
        .modal-info {{
            margin-top: 16px;
            font-size: 14px;
            color: var(--text-secondary);
        }}
        .modal-actions {{
            display: flex;
            gap: 12px;
            padding: 20px 24px;
            border-top: 1px solid var(--border-color);
        }}
        .modal-actions .btn {{
            flex: 1;
            padding: 14px 24px;
            font-size: 14px;
            font-weight: 600;
        }}

        .confirm-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: var(--bg-light);
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        .confirm-item-thumb {{
            width: 80px;
            height: 45px;
            object-fit: cover;
            border-radius: 4px;
            flex-shrink: 0;
        }}
        .confirm-item-info {{
            flex: 1;
            min-width: 0;
        }}
        .confirm-item-mesg {{
            font-size: 13px;
            font-weight: 500;
            color: var(--text-dark);
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .confirm-item-meta {{
            font-size: 11px;
            color: var(--text-secondary);
        }}
        .confirm-item-remove {{
            width: 28px;
            height: 28px;
            border-radius: 6px;
            border: none;
            background: transparent;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            flex-shrink: 0;
        }}
        .confirm-item-remove:hover {{
            background: var(--error-bg);
            color: var(--error);
        }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-left">
                <div class="header-title">
                    <span class="highlight">{category}</span> 違規審核
                </div>
                <div class="header-meta">
                    <span>{date_str}</span>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-box pending">
                    <span class="stat-num" id="pending-count">{total}</span>
                    <span class="stat-label">待審核</span>
                </div>
                <div class="stat-box success">
                    <span class="stat-num" id="confirmed-count">0</span>
                    <span class="stat-label">已確認</span>
                </div>
                <div class="stat-box error">
                    <span class="stat-num" id="deleted-count">0</span>
                    <span class="stat-label">已刪除</span>
                </div>
            </div>
            <div style="display: flex; gap: 12px;">
                <button class="btn btn-outline" onclick="window.location.href='../../../index.html'">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    返回列表
                </button>
                <button class="btn btn-dark" onclick="generateReport()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    偵測報告
                </button>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="grid" id="grid">
{cards_html}
        </div>
    </main>

    <div class="modal-overlay" id="modal" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modal-title">違規詳情</div>
                <button class="modal-close" onclick="closeModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                <video class="modal-video" id="modal-video" controls crossorigin="anonymous" playsinline></video>
                <div class="modal-info" id="modal-info"></div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-confirm" id="modal-btn-confirm" onclick="modalConfirm()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    確認違規
                </button>
                <button class="btn btn-delete" id="modal-btn-delete" onclick="modalDelete()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                    誤報刪除
                </button>
            </div>
        </div>
    </div>

    <!-- 確認列表 Modal -->
    <div class="modal-overlay" id="confirm-modal" onclick="closeConfirmModal(event)">
        <div class="modal" style="max-width:700px;" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title">已確認違規列表</div>
                <button class="modal-close" onclick="closeConfirmModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <div class="modal-body" style="max-height:60vh;overflow-y:auto;">
                <div id="confirm-list" style="display:flex;flex-direction:column;gap:12px;"></div>
            </div>
            <div class="modal-actions">
                <button class="btn btn-outline" onclick="closeConfirmModal()">取消</button>
                <button class="btn btn-dark" onclick="proceedToReport()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    產生報告
                </button>
            </div>
        </div>
    </div>

    <footer class="footer">
        iSeek AI 影像辨識系統 — {category}安全監控
    </footer>

    <script>
        const DATA = {data_json};
        const DATE = '{date_str}';
        const CATEGORY = '{category}';
        const REPORT_PATH = '{report_path}';
        const PRESET_TIMES = {preset_times_json};  // 預設確認的時間列表
        const API_BASE_URL = '{api_base}';

        let confirmedIds = new Set();
        let deletedIds = new Set();
        let currentModalId = null;
        let notes = {{}};  // 備註資料 {{id: note}}
        let pendingActions = [];  // 待同步的操作

        // 儲存單筆審核動作到 API
        async function saveAction(id, action, note = null) {{
            try {{
                const response = await fetch(API_BASE_URL + '/reviews/actions/bulk', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        date: DATE,
                        category: CATEGORY,
                        actions: [{{
                            detection_log_id: id,
                            action: action,
                            note: note
                        }}],
                        reviewer_ip: null
                    }})
                }});
                if (!response.ok) throw new Error('API 錯誤');
                console.log('✓ 已同步到資料庫:', action, id);
            }} catch (err) {{
                console.error('同步失敗:', err);
                // 加入待同步列表
                pendingActions.push({{ id, action, note }});
            }}
        }}

        // 批次同步所有審核狀態到 API
        async function syncAllToAPI() {{
            const actions = [];
            confirmedIds.forEach(id => {{
                actions.push({{
                    detection_log_id: id,
                    action: 'confirmed',
                    note: notes[id] || null
                }});
            }});
            deletedIds.forEach(id => {{
                actions.push({{
                    detection_log_id: id,
                    action: 'deleted',
                    note: null
                }});
            }});

            if (actions.length === 0) return;

            try {{
                const response = await fetch(API_BASE_URL + '/reviews/actions/bulk', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        date: DATE,
                        category: CATEGORY,
                        actions: actions,
                        reviewer_ip: null
                    }})
                }});
                if (!response.ok) throw new Error('API 錯誤');
                console.log('✓ 批次同步完成:', actions.length, '筆');
            }} catch (err) {{
                console.error('批次同步失敗:', err);
            }}
        }}

        // 從 API 載入審核狀態
        async function loadState() {{
            let stateLoaded = false;

            // 優先從 API 載入
            try {{
                const response = await fetch(API_BASE_URL + '/detection-logs/' + DATE + '/' + encodeURIComponent(CATEGORY));
                if (response.ok) {{
                    const result = await response.json();
                    if (result.success && result.data && result.data.items) {{
                        result.data.items.forEach(item => {{
                            const id = item.id;
                            const status = item.review_status;
                            const note = item.note;

                            if (status === 'confirmed') {{
                                confirmedIds.add(id);
                                const card = document.getElementById('card-' + id);
                                const btn = document.getElementById('btn-confirm-' + id);
                                if (card && btn) {{
                                    card.classList.add('confirmed');
                                    btn.classList.add('confirmed');
                                    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
                                }}
                                if (note) {{
                                    notes[id] = note;
                                    const input = document.getElementById('note-' + id);
                                    if (input) input.value = note;
                                }}
                                stateLoaded = true;
                            }} else if (status === 'deleted') {{
                                deletedIds.add(id);
                                const card = document.getElementById('card-' + id);
                                if (card) card.style.display = 'none';
                                stateLoaded = true;
                            }}
                        }});
                        console.log('✓ 從 API 載入審核狀態');
                    }}
                }}
            }} catch (err) {{
                console.warn('API 載入失敗，使用預設值:', err);
            }}

            // 如果 API 沒有資料，檢查是否有預設確認時間
            if (!stateLoaded && PRESET_TIMES && PRESET_TIMES.length > 0) {{
                const presetSet = new Set(PRESET_TIMES);

                DATA.forEach(d => {{
                    if (presetSet.has(d.time_display)) {{
                        confirmedIds.add(d.id);
                        const card = document.getElementById('card-' + d.id);
                        const btn = document.getElementById('btn-confirm-' + d.id);
                        if (card && btn) {{
                            card.classList.add('confirmed');
                            btn.classList.add('confirmed');
                            btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
                        }}
                    }} else {{
                        deletedIds.add(d.id);
                        const card = document.getElementById('card-' + d.id);
                        if (card) card.style.display = 'none';
                    }}
                }});

                // 同步預設狀態到 API
                syncAllToAPI();
                console.log('已載入預設確認 ' + confirmedIds.size + ' 筆');
            }}

            updateStats();
        }}

        // 儲存備註
        function saveNote(id, value) {{
            notes[id] = value;
            // 如果已確認，更新備註到 API
            if (confirmedIds.has(id)) {{
                saveAction(id, 'confirmed', value);
            }}
        }}

        // 頁面載入時載入狀態
        window.addEventListener('load', loadState);

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
                saveAction(id, 'pending');  // 取消確認，改回待處理
            }} else {{
                confirmedIds.add(id);
                card.classList.add('confirmed');
                btn.classList.add('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
                saveAction(id, 'confirmed', notes[id] || null);  // 儲存到 API
            }}
            updateStats();
        }}

        function deleteCard(id) {{
            const card = document.getElementById('card-' + id);
            card.classList.add('removing');
            setTimeout(() => {{
                card.style.display = 'none';
                deletedIds.add(id);
                confirmedIds.delete(id);
                updateStats();
                saveAction(id, 'deleted');  // 儲存到 API
            }}, 300);
        }}

        function playVideo(id) {{
            currentModalId = id;
            const d = DATA.find(item => item.id === id);
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            const title = document.getElementById('modal-title');
            const info = document.getElementById('modal-info');

            video.src = d.video_url;
            title.textContent = d.mesg;
            info.innerHTML = `時間：${{d.time_display}} | ID：${{d.person_ids}}`;

            modal.classList.add('active');
            video.load();
            video.play().catch(e => console.log('Auto-play blocked:', e));
            updateModalButtons();
        }}

        function closeModal(e) {{
            if (e && e.target !== e.currentTarget) return;
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            video.pause();
            modal.classList.remove('active');
            currentModalId = null;
        }}

        function updateModalButtons() {{
            const btn = document.getElementById('modal-btn-confirm');
            if (confirmedIds.has(currentModalId)) {{
                btn.classList.add('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 已確認 ✓';
            }} else {{
                btn.classList.remove('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 確認違規';
            }}
        }}

        function modalConfirm() {{
            if (currentModalId === null) return;
            confirmCard(currentModalId);
            updateModalButtons();
        }}

        function modalDelete() {{
            if (currentModalId === null) return;
            const idToDelete = currentModalId;
            closeModal();
            deleteCard(idToDelete);
        }}

        function generateReport() {{
            const confirmedData = DATA.filter(d => confirmedIds.has(d.id));
            if (confirmedData.length === 0) {{
                alert('請先確認至少一筆違規記錄');
                return;
            }}

            // 顯示確認列表
            showConfirmModal(confirmedData);
        }}

        function cleanMesg(mesg) {{
            return mesg.replace(/\\s*ID[:\\s]*[\\d,\\s]+/gi, '').trim();
        }}

        function getDisplayTag(mesg, type) {{
            const cleaned = cleanMesg(mesg);
            if (cleaned.includes('人員未穿戴必要裝備')) {{
                const typeMap = {{
                    'heartbeat': '缺少生命偵測器',
                    'harness': '缺少安全帶',
                    'no_hardhat': '未戴安全帽',
                    'no_safety_vest': '未穿安全背心'
                }};
                if (typeMap[type]) {{
                    const idMatch = mesg.match(/ID[:\\s]*(\\d+)/i);
                    let tag = typeMap[type];
                    // 特殊處理：ID 746 顯示為「未戴安全帽」
                    if (idMatch && idMatch[1] === '746' && type === 'heartbeat') {{
                        tag = '未戴安全帽';
                    }}
                    return tag + (idMatch ? ` (ID:${{idMatch[1]}})` : '');
                }}
            }}
            return cleaned;
        }}

        function showConfirmModal(items) {{
            const list = document.getElementById('confirm-list');
            list.innerHTML = items.map((d, idx) => `
                <div class="confirm-item" data-id="${{d.id}}">
                    <img class="confirm-item-thumb" src="${{d.image_url}}" onerror="this.style.display='none'">
                    <div class="confirm-item-info">
                        <div class="confirm-item-mesg">${{cleanMesg(d.mesg)}}</div>
                        <div class="confirm-item-meta">${{d.time_display}} | ID: ${{d.person_ids}}</div>
                    </div>
                    <button class="confirm-item-remove" onclick="removeFromConfirm(${{d.id}})" title="移除">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                        </svg>
                    </button>
                </div>
            `).join('');

            document.getElementById('confirm-modal').classList.add('active');
        }}

        function closeConfirmModal(e) {{
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('confirm-modal').classList.remove('active');
        }}

        function removeFromConfirm(id) {{
            confirmedIds.delete(id);
            // 更新卡片狀態
            const card = document.getElementById('card-' + id);
            const btn = document.getElementById('btn-confirm-' + id);
            if (card) card.classList.remove('confirmed');
            if (btn) {{
                btn.classList.remove('confirmed');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> 確認違規';
            }}
            updateStats();

            // 從列表中移除該項目
            const item = document.querySelector(`.confirm-item[data-id="${{id}}"]`);
            if (item) item.remove();

            // 若無確認項目則關閉 modal
            if (confirmedIds.size === 0) {{
                closeConfirmModal();
            }}
        }}

        function proceedToReport() {{
            // 資料已透過 saveAction 同步到 API，直接跳轉到報告頁面
            // 報告頁面會從 API 載入已確認的項目
            window.location.href = REPORT_PATH;
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeModal();
                closeConfirmModal();
            }}
        }});
    </script>
</body>
</html>'''


def generate_card_html(item, idx):
    """產生單張卡片 HTML"""
    mesg = item.get('mesg', '')
    person_ids = item.get('person_ids', '')
    time_display = item.get('time_display', '')
    image_url = item.get('image_url', '')
    video_url = item.get('video_url', '')
    log_type = item.get('type', '')

    # 根據 type 取得顯示用的標籤
    tag = get_display_tag(mesg, log_type)

    return f'''
            <div class="card" data-id="{idx}" id="card-{idx}">
                <div class="card-media">
                    <img src="{image_url}" alt="預覽圖" id="thumb-{idx}">
                    <video src="{video_url}" id="video-{idx}" preload="none" style="display:none" loop></video>
                    <button class="play-btn" onclick="playVideo({idx})">
                        <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    </button>
                    <div class="confirmed-badge">✓ 已確認</div>
                </div>
                <div class="card-body">
                    <div class="card-top">
                        <div class="card-title">{mesg}</div>
                        <div class="card-tag">{tag}</div>
                    </div>
                    <div class="card-info">
                        <span>{time_display}</span>
                        <span>ID: {person_ids}</span>
                    </div>
                    <div class="card-note">
                        <input type="text" class="note-input" id="note-{idx}" placeholder="備註..." onchange="saveNote({idx}, this.value)">
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-sm btn-confirm" id="btn-confirm-{idx}" onclick="confirmCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            確認違規
                        </button>
                        <button class="btn btn-sm btn-delete" onclick="deleteCard({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            誤報刪除
                        </button>
                    </div>
                </div>
            </div>'''


def generate_pending_card_html(item, idx):
    """產生待分類卡片 HTML"""
    mesg = item.get('mesg', '')
    person_ids = item.get('person_ids', '')
    time_display = item.get('time_display', '')
    image_url = item.get('image_url', '')
    video_url = item.get('video_url', '')
    log_type = item.get('type', '')

    # 根據 type 取得顯示用的標籤
    tag = get_display_tag(mesg, log_type)

    return f'''
            <div class="card" data-id="{idx}" data-type="{log_type}" id="card-{idx}">
                <div class="card-media">
                    <img src="{image_url}" alt="預覽圖" id="thumb-{idx}">
                    <video src="{video_url}" id="video-{idx}" preload="none" style="display:none" loop></video>
                    <button class="play-btn" onclick="playVideo({idx})">
                        <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    </button>
                    <div class="category-badge height-badge">高處作業</div>
                    <div class="category-badge confined-badge">局限空間</div>
                </div>
                <div class="card-body">
                    <div class="card-top">
                        <div class="card-title">{mesg}</div>
                        <div class="card-tag">{tag}</div>
                    </div>
                    <div class="card-info">
                        <span>{time_display}</span>
                        <span>ID: {person_ids}</span>
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-sm btn-height" id="btn-height-{idx}" onclick="classifyAsHeight({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                            高處作業
                        </button>
                        <button class="btn btn-sm btn-confined" id="btn-confined-{idx}" onclick="classifyAsConfined({idx})">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>
                            局限空間
                        </button>
                    </div>
                </div>
            </div>'''


def generate_pending_review_html(date_str, total, cards_html, data_json):
    """產生待分類審核工具 HTML"""
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>待分類 違規審核 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --accent-purple: #8B5CF6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --success: #10B981;
            --success-bg: #ECFDF5;
            --error: #EF4444;
            --error-bg: #FEF2F2;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
            --height-color: #F97316;
            --height-bg: #FFF7ED;
            --confined-color: #6366F1;
            --confined-bg: #EEF2FF;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #FFFFFF;
            color: var(--text-dark);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{
            background: #FFFFFF;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        .header-title .highlight {{
            color: var(--accent-purple);
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .meta-divider {{
            width: 1px;
            height: 16px;
            background: var(--border-color);
        }}

        .stats-row {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .stat-box {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 8px;
            background: var(--bg-light);
        }}
        .stat-box.pending {{ background: var(--warning-bg); }}
        .stat-box.height {{ background: var(--height-bg); }}
        .stat-box.confined {{ background: var(--confined-bg); }}
        .stat-num {{
            font-size: 18px;
            font-weight: 700;
        }}
        .stat-box.pending .stat-num {{ color: var(--warning); }}
        .stat-box.height .stat-num {{ color: var(--height-color); }}
        .stat-box.confined .stat-num {{ color: var(--confined-color); }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            text-decoration: none;
        }}
        .btn-dark {{
            background: var(--text-dark);
            color: white;
        }}
        .btn-dark:hover {{
            background: #1E293B;
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1.5px solid var(--border-color);
        }}
        .btn-outline:hover {{
            border-color: var(--text-secondary);
            background: var(--bg-light);
        }}
        .btn-sm {{
            padding: 8px 14px;
            font-size: 12px;
            border-radius: 8px;
        }}
        .btn-height {{
            background: white;
            color: var(--height-color);
            border: 1.5px solid var(--height-color);
        }}
        .btn-height:hover {{
            background: var(--height-bg);
        }}
        .btn-height.selected {{
            background: var(--height-color);
            color: white;
        }}
        .btn-confined {{
            background: white;
            color: var(--confined-color);
            border: 1.5px solid var(--confined-color);
        }}
        .btn-confined:hover {{
            background: var(--confined-bg);
        }}
        .btn-confined.selected {{
            background: var(--confined-color);
            color: white;
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 100px 32px 32px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}

        .card {{
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: all 0.2s ease;
        }}
        .card:hover {{
            border-color: var(--text-secondary);
        }}
        .card.classified-height {{
            border-color: var(--height-color);
            box-shadow: 0 0 0 1px var(--height-color);
        }}
        .card.classified-confined {{
            border-color: var(--confined-color);
            box-shadow: 0 0 0 1px var(--confined-color);
        }}
        .card.removing {{
            opacity: 0;
            transform: scale(0.9);
        }}

        .card-media {{
            position: relative;
            aspect-ratio: 16/9;
            background: var(--bg-light);
            overflow: hidden;
        }}
        .card-media img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .card-media video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        .play-btn {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: rgba(255,255,255,0.95);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .play-btn:hover {{
            transform: translate(-50%, -50%) scale(1.1);
        }}
        .play-btn svg {{
            width: 20px;
            height: 20px;
            fill: var(--text-dark);
            margin-left: 2px;
        }}

        .category-badge {{
            position: absolute;
            top: 12px;
            right: 12px;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            display: none;
        }}
        .height-badge {{
            background: var(--height-color);
            color: white;
        }}
        .confined-badge {{
            background: var(--confined-color);
            color: white;
        }}
        .card.classified-height .height-badge {{
            display: block;
        }}
        .card.classified-confined .confined-badge {{
            display: block;
        }}

        .card-body {{
            padding: 16px;
        }}
        .card-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 8px;
        }}
        .card-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            flex: 1;
        }}
        .card-tag {{
            font-size: 11px;
            padding: 4px 8px;
            background: var(--bg-light);
            border-radius: 4px;
            color: var(--text-secondary);
            white-space: nowrap;
        }}
        .card-info {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 12px;
        }}
        .card-note {{
            margin-bottom: 12px;
        }}
        .note-input {{
            width: 100%;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            font-size: 13px;
            background: var(--bg-light);
            transition: border-color 0.2s;
        }}
        .note-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
            background: #fff;
        }}
        .note-input::placeholder {{
            color: var(--text-muted);
        }}
        .card-actions {{
            display: flex;
            gap: 8px;
        }}
        .card-actions .btn {{
            flex: 1;
        }}

        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.6);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 32px;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal {{
            background: white;
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
        }}
        .modal-title {{
            font-size: 16px;
            font-weight: 600;
        }}
        .modal-close {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: none;
            background: var(--bg-light);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-close:hover {{
            background: var(--border-color);
        }}
        .modal-video {{
            width: 100%;
            aspect-ratio: 16/9;
            background: black;
        }}
        .modal-body {{
            padding: 20px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            border-top: 1px solid var(--border-color);
        }}
        .modal-info {{
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .modal-actions {{
            display: flex;
            gap: 12px;
        }}

        .empty-state {{
            text-align: center;
            padding: 80px 32px;
            color: var(--text-muted);
        }}
        .empty-state svg {{
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            opacity: 0.5;
        }}
        .empty-state h3 {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-left">
                <div class="header-title"><span class="highlight">待分類</span> 違規審核</div>
                <div class="header-meta">
                    <span>{date_str}</span>
                    <div class="meta-divider"></div>
                    <span>共 {total} 筆待分類</span>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-box pending">
                    <span class="stat-num" id="stat-pending">{total}</span>
                    <span class="stat-label">待分類</span>
                </div>
                <div class="stat-box height">
                    <span class="stat-num" id="stat-height">0</span>
                    <span class="stat-label">高處作業</span>
                </div>
                <div class="stat-box confined">
                    <span class="stat-num" id="stat-confined">0</span>
                    <span class="stat-label">局限空間</span>
                </div>
                <button class="btn btn-dark" onclick="exportClassified()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    匯出分類結果
                </button>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="grid" id="cards-container">
{cards_html}
        </div>
    </main>

    <div class="modal-overlay" id="modal" onclick="closeModal(event)">
        <div class="modal">
            <div class="modal-header">
                <div class="modal-title" id="modal-title">違規詳情</div>
                <button class="modal-close" onclick="closeModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <video class="modal-video" id="modal-video" controls loop></video>
            <div class="modal-body">
                <div class="modal-info" id="modal-info"></div>
                <div class="modal-actions">
                    <button class="btn btn-height" id="modal-btn-height" onclick="modalClassifyHeight()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                        高處作業
                    </button>
                    <button class="btn btn-confined" id="modal-btn-confined" onclick="modalClassifyConfined()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>
                        局限空間
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const DATE = '{date_str}';
        const DATA = {data_json};

        let heightIds = new Set();
        let confinedIds = new Set();
        let currentModalId = null;

        // 從 localStorage 載入已分類的資料
        function loadClassified() {{
            const saved = localStorage.getItem('pendingClassified_' + DATE);
            if (saved) {{
                const data = JSON.parse(saved);
                heightIds = new Set(data.height || []);
                confinedIds = new Set(data.confined || []);

                // 更新卡片狀態
                heightIds.forEach(id => {{
                    const card = document.getElementById('card-' + id);
                    const btn = document.getElementById('btn-height-' + id);
                    if (card) card.classList.add('classified-height');
                    if (btn) btn.classList.add('selected');
                }});
                confinedIds.forEach(id => {{
                    const card = document.getElementById('card-' + id);
                    const btn = document.getElementById('btn-confined-' + id);
                    if (card) card.classList.add('classified-confined');
                    if (btn) btn.classList.add('selected');
                }});
                updateStats();
            }}
        }}

        function saveClassified() {{
            const data = {{
                height: Array.from(heightIds),
                confined: Array.from(confinedIds)
            }};
            localStorage.setItem('pendingClassified_' + DATE, JSON.stringify(data));
        }}

        function updateStats() {{
            const pending = DATA.length - heightIds.size - confinedIds.size;
            document.getElementById('stat-pending').textContent = pending;
            document.getElementById('stat-height').textContent = heightIds.size;
            document.getElementById('stat-confined').textContent = confinedIds.size;
        }}

        function classifyAsHeight(id) {{
            const card = document.getElementById('card-' + id);
            const btnHeight = document.getElementById('btn-height-' + id);
            const btnConfined = document.getElementById('btn-confined-' + id);

            // 移除局限空間分類
            confinedIds.delete(id);
            card.classList.remove('classified-confined');
            btnConfined.classList.remove('selected');

            // 切換高處作業分類
            if (heightIds.has(id)) {{
                heightIds.delete(id);
                card.classList.remove('classified-height');
                btnHeight.classList.remove('selected');
            }} else {{
                heightIds.add(id);
                card.classList.add('classified-height');
                btnHeight.classList.add('selected');
            }}

            updateStats();
            saveClassified();
        }}

        function classifyAsConfined(id) {{
            const card = document.getElementById('card-' + id);
            const btnHeight = document.getElementById('btn-height-' + id);
            const btnConfined = document.getElementById('btn-confined-' + id);

            // 移除高處作業分類
            heightIds.delete(id);
            card.classList.remove('classified-height');
            btnHeight.classList.remove('selected');

            // 切換局限空間分類
            if (confinedIds.has(id)) {{
                confinedIds.delete(id);
                card.classList.remove('classified-confined');
                btnConfined.classList.remove('selected');
            }} else {{
                confinedIds.add(id);
                card.classList.add('classified-confined');
                btnConfined.classList.add('selected');
            }}

            updateStats();
            saveClassified();
        }}

        function playVideo(id) {{
            currentModalId = id;
            const d = DATA.find(item => item.id === id);
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            const title = document.getElementById('modal-title');
            const info = document.getElementById('modal-info');

            video.src = d.video_url;
            title.textContent = d.mesg;
            info.innerHTML = `時間：${{d.time_display}} | ID：${{d.person_ids}}`;

            modal.classList.add('active');
            video.load();
            video.play().catch(e => console.log('Auto-play blocked:', e));
            updateModalButtons();
        }}

        function closeModal(e) {{
            if (e && e.target !== e.currentTarget) return;
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            video.pause();
            modal.classList.remove('active');
            currentModalId = null;
        }}

        function updateModalButtons() {{
            const btnHeight = document.getElementById('modal-btn-height');
            const btnConfined = document.getElementById('modal-btn-confined');

            btnHeight.classList.toggle('selected', heightIds.has(currentModalId));
            btnConfined.classList.toggle('selected', confinedIds.has(currentModalId));
        }}

        function modalClassifyHeight() {{
            if (currentModalId === null) return;
            classifyAsHeight(currentModalId);
            updateModalButtons();
        }}

        function modalClassifyConfined() {{
            if (currentModalId === null) return;
            classifyAsConfined(currentModalId);
            updateModalButtons();
        }}

        function exportClassified() {{
            const heightData = DATA.filter(d => heightIds.has(d.id));
            const confinedData = DATA.filter(d => confinedIds.has(d.id));

            if (heightData.length === 0 && confinedData.length === 0) {{
                alert('請先分類至少一筆資料');
                return;
            }}

            // 儲存分類結果到 localStorage，供報告頁面使用
            if (heightData.length > 0) {{
                localStorage.setItem('reportData_' + DATE + '_高處作業_pending', JSON.stringify({{
                    date: DATE,
                    category: '高處作業',
                    source: '待分類',
                    items: heightData
                }}));
            }}

            if (confinedData.length > 0) {{
                localStorage.setItem('reportData_' + DATE + '_局限空間_pending', JSON.stringify({{
                    date: DATE,
                    category: '局限空間',
                    source: '待分類',
                    items: confinedData
                }}));
            }}

            // 匯出 CSV
            let csv = '\\uFEFF分類,日期,時間,違規事項,人員ID,圖片連結,影片連結\\n';

            heightData.forEach(d => {{
                csv += `高處作業,${{DATE}},${{d.time_display}},"${{d.mesg}}",${{d.person_ids}},${{d.image_url}},${{d.video_url}}\\n`;
            }});

            confinedData.forEach(d => {{
                csv += `局限空間,${{DATE}},${{d.time_display}},"${{d.mesg}}",${{d.person_ids}},${{d.image_url}},${{d.video_url}}\\n`;
            }});

            const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `待分類結果_${{DATE}}.csv`;
            a.click();
            URL.revokeObjectURL(url);

            alert(`匯出完成！\\n高處作業：${{heightData.length}} 筆\\n局限空間：${{confinedData.length}} 筆`);
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});

        // 初始化
        loadClassified();
    </script>
</body>
</html>'''


def generate_report_html(category, date_str, api_base=None):
    """產生報告頁面 HTML（從 API 讀取已確認違規）"""
    if api_base is None:
        api_base = REVIEW_API_BASE
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 偵測報告 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #FFFFFF;
            color: var(--text-dark);
            line-height: 1.5;
        }}

        .header {{
            background: #FFFFFF;
            border-bottom: 1px solid var(--border-color);
            padding: 16px 24px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 24px;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 700;
        }}
        .header-title .highlight {{
            color: var(--accent-blue);
        }}
        .header-meta {{
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .header-actions {{
            display: flex;
            gap: 8px;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            text-decoration: none;
        }}
        .btn-dark {{
            background: var(--text-dark);
            color: white;
        }}
        .btn-dark:hover {{
            background: #1E293B;
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1.5px solid var(--border-color);
        }}
        .btn-outline:hover {{
            background: var(--bg-light);
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 16px 24px;
        }}

        .summary {{
            display: flex;
            gap: 16px;
            margin-bottom: 16px;
        }}
        .summary-card {{
            background: var(--bg-light);
            border-radius: 8px;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .summary-num {{
            font-size: 20px;
            font-weight: 700;
            color: var(--accent-blue);
        }}
        .summary-label {{
            font-size: 12px;
            color: var(--text-secondary);
        }}

        .table-container {{
            background: white;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            overflow: auto;
            max-height: calc(100vh - 180px);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead {{
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: var(--bg-light);
            font-weight: 600;
            font-size: 12px;
            color: var(--text-secondary);
        }}
        td {{
            font-size: 13px;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        tr:hover td {{
            background: var(--bg-light);
        }}
        .thumb {{
            width: 100px;
            height: 56px;
            object-fit: cover;
            border-radius: 4px;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        .thumb:hover {{
            transform: scale(1.05);
        }}
        .video-link {{
            color: var(--accent-blue);
            text-decoration: none;
            font-size: 12px;
        }}
        .video-link:hover {{
            text-decoration: underline;
        }}

        .footer {{
            text-align: center;
            padding: 16px;
            color: var(--text-muted);
            font-size: 11px;
        }}

        .export-section {{
            background: var(--bg-light);
            border-top: 1px solid var(--border-color);
            padding: 16px 24px;
        }}
        .export-inner {{
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 12px;
        }}
        .export-label {{
            font-size: 13px;
            color: var(--text-secondary);
        }}

        /* Lightbox */
        .lightbox {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.9);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            cursor: zoom-out;
        }}
        .lightbox.active {{
            display: flex;
        }}
        .lightbox img {{
            max-width: 90vw;
            max-height: 90vh;
            object-fit: contain;
            border-radius: 8px;
        }}
        .lightbox-close {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .lightbox-close:hover {{
            background: rgba(255,255,255,0.3);
        }}
        .lightbox-close svg {{
            width: 24px;
            height: 24px;
            stroke: white;
        }}

        @media print {{
            .header-actions, .btn {{ display: none; }}
            .header {{ position: static; }}
            .table-container {{ max-height: none; overflow: visible; }}
            thead {{ position: static; }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-left">
                <div class="header-title">
                    <span class="highlight">{category}</span> 偵測報告
                </div>
                <div class="header-meta">{date_str}</div>
                <div class="summary">
                    <div class="summary-card">
                        <span class="summary-num" id="total-count">0</span>
                        <span class="summary-label">違規總數</span>
                    </div>
                    <div class="summary-card">
                        <span class="summary-num" id="time-range" style="font-size:14px;">--</span>
                        <span class="summary-label">偵測時段</span>
                    </div>
                </div>
            </div>
            <button class="btn btn-outline" onclick="window.location.href='../../../index.html'">返回列表</button>
        </div>
    </header>

    <main class="main">
        <div class="table-container">
            <table id="report-table">
                <thead>
                    <tr>
                        <th style="width:50px">序號</th>
                        <th style="width:80px">時間</th>
                        <th>違規事項</th>
                        <th style="width:80px">人員 ID</th>
                        <th style="width:120px">截圖</th>
                        <th style="width:80px">影片</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                </tbody>
            </table>
        </div>
    </main>

    <!-- Lightbox -->
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <button class="lightbox-close">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
        </button>
        <img id="lightbox-img" src="" alt="放大圖片">
    </div>

    <div class="export-section" id="export-section" style="display:none;">
        <div class="export-inner">
            <span class="export-label">匯出報告：</span>
            <button class="btn btn-outline" onclick="exportCSV()">CSV</button>
            <button class="btn btn-dark" onclick="exportWord()">違規單</button>
        </div>
    </div>

    <footer class="footer">
        iSeek AI 影像辨識系統 | 報告產生：<span id="gen-time"></span>
    </footer>

    <script>
        const CATEGORY = '{category}';
        const DATE = '{date_str}';
        const API_BASE_URL = '{api_base}';

        let reportData = null;

        async function loadData() {{
            try {{
                // 從 API 載入已確認的違規項目
                const response = await fetch(API_BASE_URL + '/reports/' + DATE + '/' + encodeURIComponent(CATEGORY));
                if (response.ok) {{
                    const result = await response.json();
                    if (result.success && result.data && result.data.items && result.data.items.length > 0) {{
                        reportData = result.data;
                        renderTable();
                        document.getElementById('export-section').style.display = 'block';
                        console.log('✓ 從 API 載入 ' + reportData.items.length + ' 筆報告資料');
                        return;
                    }}
                }}
            }} catch (err) {{
                console.error('API 載入失敗:', err);
            }}

            // 沒有資料
            document.getElementById('table-body').innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:#94A3B8;">尚無資料，請先在審核頁面確認違規項目</td></tr>';
        }}

        // 清理 mesg 中的 ID（用於顯示）
        function cleanMesg(mesg) {{
            return mesg.replace(/\\s*ID[:\\s]*[\\d,\\s]+/gi, '').trim();
        }}

        function getDisplayTag(mesg, type) {{
            const cleaned = cleanMesg(mesg);
            if (cleaned.includes('人員未穿戴必要裝備')) {{
                const typeMap = {{
                    'heartbeat': '缺少生命偵測器',
                    'harness': '缺少安全帶',
                    'no_hardhat': '未戴安全帽',
                    'no_safety_vest': '未穿安全背心'
                }};
                if (typeMap[type]) {{
                    const idMatch = mesg.match(/ID[:\\s]*(\\d+)/i);
                    let tag = typeMap[type];
                    // 特殊處理：ID 746 顯示為「未戴安全帽」
                    if (idMatch && idMatch[1] === '746' && type === 'heartbeat') {{
                        tag = '未戴安全帽';
                    }}
                    return tag + (idMatch ? ` (ID:${{idMatch[1]}})` : '');
                }}
            }}
            return cleaned;
        }}

        function renderTable() {{
            const tbody = document.getElementById('table-body');
            const items = reportData.items;

            document.getElementById('total-count').textContent = items.length;

            if (items.length > 0) {{
                const times = items.map(d => d.time_display).sort();
                document.getElementById('time-range').textContent = times[0] + ' - ' + times[times.length - 1];
            }}

            tbody.innerHTML = items.map((d, idx) => {{
                const imageUrl = d.image_url || '';
                const videoUrl = d.video_url || '';
                const tag = getDisplayTag(d.mesg, d.type);
                return `<tr>
                    <td>${{idx + 1}}</td>
                    <td>${{d.time_display}}</td>
                    <td>${{tag}}</td>
                    <td>${{d.person_ids}}</td>
                    <td><img src="${{imageUrl}}" class="thumb" onclick="openLightbox('${{imageUrl}}')" onerror="this.style.display='none'"></td>
                    <td><a href="${{videoUrl}}" target="_blank" class="video-link">觀看</a></td>
                </tr>`;
            }}).join('');

            document.getElementById('gen-time').textContent = new Date().toLocaleString('zh-TW');
        }}

        function openLightbox(url) {{
            document.getElementById('lightbox-img').src = url;
            document.getElementById('lightbox').classList.add('active');
        }}

        function closeLightbox() {{
            document.getElementById('lightbox').classList.remove('active');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeLightbox();
        }});

        function exportCSV() {{
            if (!reportData) return;
            const items = reportData.items;
            let csv = '\\uFEFF序號,日期,時間,類型,違規事項,人員ID,圖片連結,影片連結\\n';
            items.forEach((d, idx) => {{
                const tag = getDisplayTag(d.mesg, d.type);
                csv += `${{idx+1}},${{DATE}},${{d.time_display}},${{CATEGORY}},"${{tag}}",${{d.person_ids}},${{d.image_url}},${{d.video_url}}\\n`;
            }});

            const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `偵測報告_${{CATEGORY}}_${{DATE.replace(/-/g,'')}}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        }}

        async function exportWord() {{
            if (!reportData) return;
            const items = reportData.items;

            // 顯示載入中
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '載入圖片中...';
            btn.disabled = true;

            // 下載所有圖片轉 base64
            const imagePromises = items.map(async (d) => {{
                try {{
                    const response = await fetch(d.image_url);
                    const blob = await response.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = () => resolve('');
                        reader.readAsDataURL(blob);
                    }});
                }} catch (e) {{
                    console.log('圖片載入失敗:', d.image_url);
                    return '';
                }}
            }});

            const base64Images = await Promise.all(imagePromises);

            let html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>違規單 - ${{CATEGORY}} - ${{DATE}}</title>
<style>
@media print {{
    @page {{ size: A4 landscape; margin: 1cm; }}
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: '微軟正黑體', -apple-system, sans-serif; font-size: 16px; background: #f5f5f5; }}
.page {{
    width: 277mm; height: 190mm;
    background: white;
    margin: 10px auto;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    page-break-after: always;
    display: flex;
    flex-direction: column;
}}
.page:last-child {{ page-break-after: auto; }}
.header {{
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    padding: 12px;
    background: #f0f0f0;
    border: 2px solid #333;
    margin-bottom: 20px;
}}
.content {{ display: flex; gap: 30px; flex: 1; }}
.left {{ width: 40%; font-size: 16px; }}
.right {{ width: 60%; display: flex; align-items: center; justify-content: center; background: #fafafa; border: 1px solid #ddd; }}
.right img {{ max-width: 100%; max-height: 155mm; object-fit: contain; }}
.info-table {{ width: 100%; border-collapse: collapse; }}
.info-table td {{ padding: 12px 14px; border-bottom: 1px solid #ddd; font-size: 16px; }}
.info-table .label {{ font-weight: bold; background: #f0f0f0; width: 100px; font-size: 16px; }}
.info-table .value {{ font-size: 16px; }}
.info-table .link {{ font-size: 11px; color: #0066cc; word-break: break-all; }}
.print-btn {{
    position: fixed; top: 20px; right: 20px;
    padding: 12px 24px;
    background: #0066cc; color: white;
    border: none; border-radius: 8px;
    font-size: 14px; cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.print-btn:hover {{ background: #0052a3; }}
@media print {{ .print-btn {{ display: none; }} }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">存成 PDF</button>`;

            for (let i = 0; i < items.length; i++) {{
                const d = items[i];
                const tag = getDisplayTag(d.mesg, d.type);
                const imgSrc = base64Images[i] || d.image_url;
                html += `
<div class="page">
    <div class="header">違規通報單 #${{i + 1}}</div>
    <div class="content">
        <div class="left">
            <table class="info-table">
                <tr><td class="label">日期</td><td class="value">${{DATE}}</td></tr>
                <tr><td class="label">時間</td><td class="value">${{d.time_display}}</td></tr>
                <tr><td class="label">類型</td><td class="value">${{CATEGORY}}</td></tr>
                <tr><td class="label">違規事項</td><td class="value">${{tag}}</td></tr>
                <tr><td class="label">人員 ID</td><td class="value">${{d.person_ids}}</td></tr>
                <tr><td class="label">影片連結</td><td class="link"><a href="${{d.video_url}}" target="_blank">${{d.video_url}}</a></td></tr>
            </table>
        </div>
        <div class="right">
            ${{imgSrc ? `<img src="${{imgSrc}}"/>` : '<div style="color:#999;">圖片載入失敗</div>'}}
        </div>
    </div>
</div>`;
            }}

            html += '</body></html>';

            // 還原按鈕
            btn.textContent = originalText;
            btn.disabled = false;

            // 開新視窗顯示
            const win = window.open('', '_blank');
            win.document.write(html);
            win.document.close();
        }}

        loadData();
    </script>
</body>
</html>'''


def generate_manager_report_html(category, date_str, api_base=None):
    """產生管理版報告頁面 HTML（從 API 讀取已確認違規）"""
    if api_base is None:
        api_base = REVIEW_API_BASE
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category} 偵測報告 - {date_str}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #FFFFFF;
            color: var(--text-dark);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        .header {{
            background: #FFFFFF;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
        }}
        .header-inner {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .header-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-dark);
        }}
        .header-title .highlight {{
            color: var(--accent-blue);
        }}
        .header-meta {{
            display: flex;
            align-items: center;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .stats-row {{
            display: flex;
            align-items: center;
            gap: 20px;
        }}
        .stat-box {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            border-radius: 8px;
            background: var(--bg-light);
        }}
        .stat-num {{
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-blue);
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            text-decoration: none;
        }}
        .btn-dark {{
            background: var(--text-dark);
            color: white;
        }}
        .btn-dark:hover {{
            background: #1E293B;
        }}
        .btn-outline {{
            background: white;
            color: var(--text-dark);
            border: 1.5px solid var(--border-color);
        }}
        .btn-outline:hover {{
            border-color: var(--text-secondary);
            background: var(--bg-light);
        }}

        .main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px;
            padding-top: 100px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 24px;
        }}

        .card {{
            background: white;
            border-radius: 16px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: all 0.25s ease;
        }}
        .card:hover {{
            border-color: #CBD5E1;
            box-shadow: 0 8px 24px rgba(15,23,42,0.08);
            transform: translateY(-4px);
        }}

        .card-media {{
            position: relative;
            aspect-ratio: 16/9;
            background: #0F172A;
            overflow: hidden;
        }}
        .card-media img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        .card:hover .card-media img {{
            transform: scale(1.05);
        }}
        .play-btn {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(255,255,255,0.95);
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .play-btn:hover {{
            transform: translate(-50%, -50%) scale(1.1);
        }}
        .play-btn svg {{
            width: 24px;
            height: 24px;
            fill: var(--text-dark);
            margin-left: 4px;
        }}

        .card-body {{
            padding: 16px;
        }}
        .card-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .card-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dark);
            line-height: 1.4;
        }}
        .card-tag {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            background: var(--warning-bg);
            color: var(--warning);
            word-break: keep-all;
        }}
        .card-info {{
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 8px;
        }}
        .card-note {{
            margin-top: 8px;
        }}
        .note-input {{
            width: 100%;
            padding: 6px 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 12px;
            background: #fff;
        }}
        .note-input:focus {{
            outline: none;
            border-color: var(--accent-blue);
        }}
        .note-input::placeholder {{
            color: var(--text-muted);
        }}

        .card-note-display {{
            padding: 8px 12px;
            background: #F1F5F9;
            border-radius: 6px;
            font-size: 12px;
            color: #475569;
            margin-top: 8px;
        }}
        .card-media {{
            position: relative;
        }}

        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 32px;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal {{
            background: white;
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 24px;
            border-bottom: 1px solid var(--border-color);
        }}
        .modal-title {{
            font-size: 16px;
            font-weight: 600;
        }}
        .modal-close {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: none;
            background: var(--bg-light);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .modal-body {{
            padding: 24px;
            overflow-y: auto;
        }}
        .modal-video {{
            width: 100%;
            border-radius: 8px 8px 0 0;
            background: #000;
            min-height: 300px;
        }}
        .modal-video::-webkit-media-controls-panel {{
            background: linear-gradient(transparent, rgba(0,0,0,0.7)) !important;
        }}
        .modal-info {{
            margin-top: 16px;
            font-size: 14px;
            color: var(--text-secondary);
        }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-left">
                <div class="header-title">
                    <span class="highlight">{category}</span> 偵測報告
                </div>
                <div class="header-meta">
                    <span>{date_str}</span>
                </div>
            </div>
            <div class="stats-row">
                <div class="stat-box">
                    <span class="stat-num" id="total-count">0</span>
                    <span class="stat-label">違規總數</span>
                </div>
            </div>
            <div style="display: flex; gap: 12px;">
                <button class="btn btn-outline" onclick="window.location.href='../../../index.html'">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                    返回列表
                </button>
                <button class="btn btn-outline" onclick="exportCSV()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    CSV
                </button>
                <button class="btn btn-dark" onclick="exportWord()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    違規單
                </button>
            </div>
        </div>
    </header>

    <main class="main">
        <div class="grid" id="grid">
        </div>
    </main>

    <div class="modal-overlay" id="modal" onclick="closeModal(event)">
        <div class="modal" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-title" id="modal-title">違規詳情</div>
                <button class="modal-close" onclick="closeModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
            <div class="modal-body">
                <video class="modal-video" id="modal-video" controls crossorigin="anonymous" playsinline></video>
                <div class="modal-info" id="modal-info"></div>
            </div>
        </div>
    </div>

    <footer class="footer">
        iSeek AI 影像辨識系統 — {category}安全監控
    </footer>

    <script>
        const DATE = '{date_str}';
        const CATEGORY = '{category}';
        const API_BASE_URL = '{api_base}';

        let reportData = null;

        async function loadData() {{
            try {{
                // 從 API 載入已確認的違規項目
                const response = await fetch(API_BASE_URL + '/reports/' + DATE + '/' + encodeURIComponent(CATEGORY));
                if (response.ok) {{
                    const result = await response.json();
                    if (result.success && result.data && result.data.items && result.data.items.length > 0) {{
                        reportData = result.data;
                        render();
                        console.log('✓ 從 API 載入 ' + reportData.items.length + ' 筆報告資料');
                        return;
                    }}
                }}
            }} catch (err) {{
                console.error('API 載入失敗:', err);
            }}

            // 沒有資料
            document.getElementById('grid').innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:60px;color:#94A3B8;">尚無資料，請先在審核頁面確認違規項目</div>';
            document.getElementById('total-count').textContent = '0';
        }}

        function cleanMesg(mesg) {{
            return mesg.replace(/\\s*ID[:\\s]*[\\d,\\s]+/gi, '').trim();
        }}

        function getDisplayTag(mesg, type) {{
            const cleaned = cleanMesg(mesg);
            if (cleaned.includes('人員未穿戴必要裝備')) {{
                const typeMap = {{
                    'heartbeat': '缺少生命偵測器',
                    'harness': '缺少安全帶',
                    'no_hardhat': '未戴安全帽',
                    'no_safety_vest': '未穿安全背心'
                }};
                if (typeMap[type]) {{
                    const idMatch = mesg.match(/ID[:\\s]*(\\d+)/i);
                    let tag = typeMap[type];
                    // 特殊處理：ID 746 顯示為「未戴安全帽」
                    if (idMatch && idMatch[1] === '746' && type === 'heartbeat') {{
                        tag = '未戴安全帽';
                    }}
                    return tag + (idMatch ? ` (ID:${{idMatch[1]}})` : '');
                }}
            }}
            return cleaned;
        }}

        function render() {{
            const items = reportData.items;
            document.getElementById('total-count').textContent = items.length;

            const grid = document.getElementById('grid');
            grid.innerHTML = items.map((d, idx) => {{
                const mesg = d.mesg || '';
                const tag = getDisplayTag(mesg, d.type);
                const note = d.note || '';

                return `<div class="card">
                    <div class="card-media">
                        <img src="${{d.image_url}}" alt="預覽圖" onerror="this.style.display='none'">
                        <button class="play-btn" onclick="playVideo(${{d.id}})">
                            <svg viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="card-top">
                            <div class="card-title">${{tag}}</div>
                            <div class="card-tag">${{tag}}</div>
                        </div>
                        <div class="card-info">
                            <span>${{d.time_display}}</span>
                            <span>ID: ${{d.person_ids}}</span>
                        </div>
                        ${{note ? `<div class="card-note-display">${{note}}</div>` : ''}}
                    </div>
                </div>`;
            }}).join('');
        }}

        function playVideo(id) {{
            if (!reportData) return;
            const d = reportData.items.find(item => item.id === id);
            if (!d) return;
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            const title = document.getElementById('modal-title');
            const info = document.getElementById('modal-info');

            video.src = d.video_url;
            title.textContent = cleanMesg(d.mesg);
            info.innerHTML = `時間：${{d.time_display}} | ID：${{d.person_ids}}`;

            modal.classList.add('active');
            video.load();
            video.play().catch(e => console.log('Auto-play blocked:', e));
        }}

        function closeModal(e) {{
            if (e && e.target !== e.currentTarget) return;
            const modal = document.getElementById('modal');
            const video = document.getElementById('modal-video');
            video.pause();
            modal.classList.remove('active');
        }}

        function exportCSV() {{
            if (!reportData) return;
            let csv = '\\uFEFF序號,日期,時間,類型,違規事項,人員ID,備註,圖片連結,影片連結\\n';
            reportData.items.forEach((d, idx) => {{
                const tag = getDisplayTag(d.mesg, d.type);
                const note = d.note || '';
                csv += `${{idx+1}},${{DATE}},${{d.time_display}},${{CATEGORY}},"${{tag}}",${{d.person_ids}},"${{note}}",${{d.image_url}},${{d.video_url}}\\n`;
            }});

            const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `偵測報告_${{CATEGORY}}_${{DATE.replace(/-/g,'')}}.csv`;
            a.click();
            URL.revokeObjectURL(url);
        }}

        async function exportWord() {{
            if (!reportData) return;
            // 顯示載入中
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '載入圖片中...';
            btn.disabled = true;

            // 下載所有圖片轉 base64
            const imagePromises = reportData.items.map(async (d) => {{
                try {{
                    const response = await fetch(d.image_url);
                    const blob = await response.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = () => resolve('');
                        reader.readAsDataURL(blob);
                    }});
                }} catch (e) {{
                    console.log('圖片載入失敗:', d.image_url);
                    return '';
                }}
            }});

            const base64Images = await Promise.all(imagePromises);

            let html = `<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>違規單 - ${{CATEGORY}} - ${{DATE}}</title>
<style>
@media print {{
    @page {{ size: A4 landscape; margin: 1cm; }}
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: '微軟正黑體', -apple-system, sans-serif; font-size: 16px; background: #f5f5f5; }}
.page {{
    width: 277mm; height: 190mm;
    background: white;
    margin: 10px auto;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    page-break-after: always;
    display: flex;
    flex-direction: column;
}}
.page:last-child {{ page-break-after: auto; }}
.header {{
    text-align: center;
    font-size: 22px;
    font-weight: bold;
    padding: 12px;
    background: #f0f0f0;
    border: 2px solid #333;
    margin-bottom: 20px;
}}
.content {{ display: flex; gap: 30px; flex: 1; }}
.left {{ width: 40%; font-size: 16px; }}
.right {{ width: 60%; display: flex; align-items: center; justify-content: center; background: #fafafa; border: 1px solid #ddd; }}
.right img {{ max-width: 100%; max-height: 155mm; object-fit: contain; }}
.info-table {{ width: 100%; border-collapse: collapse; }}
.info-table td {{ padding: 12px 14px; border-bottom: 1px solid #ddd; font-size: 16px; }}
.info-table .label {{ font-weight: bold; background: #f0f0f0; width: 100px; font-size: 16px; }}
.info-table .value {{ font-size: 16px; }}
.info-table .link {{ font-size: 11px; color: #0066cc; word-break: break-all; }}
.print-btn {{
    position: fixed; top: 20px; right: 20px;
    padding: 12px 24px;
    background: #0066cc; color: white;
    border: none; border-radius: 8px;
    font-size: 14px; cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.print-btn:hover {{ background: #0052a3; }}
@media print {{ .print-btn {{ display: none; }} }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">存成 PDF</button>`;

            for (let i = 0; i < reportData.items.length; i++) {{
                const d = reportData.items[i];
                const tag = getDisplayTag(d.mesg, d.type);
                const note = d.note || '';
                const imgSrc = base64Images[i] || d.image_url;
                html += `
<div class="page">
    <div class="header">違規通報單 #${{i + 1}}</div>
    <div class="content">
        <div class="left">
            <table class="info-table">
                <tr><td class="label">日期</td><td class="value">${{DATE}}</td></tr>
                <tr><td class="label">時間</td><td class="value">${{d.time_display}}</td></tr>
                <tr><td class="label">類型</td><td class="value">${{CATEGORY}}</td></tr>
                <tr><td class="label">違規事項</td><td class="value">${{tag}}</td></tr>
                <tr><td class="label">人員 ID</td><td class="value">${{d.person_ids}}</td></tr>
                <tr><td class="label">備註</td><td class="value">${{note}}</td></tr>
                <tr><td class="label">影片連結</td><td class="link"><a href="${{d.video_url}}" target="_blank">${{d.video_url}}</a></td></tr>
            </table>
        </div>
        <div class="right">
            ${{imgSrc ? `<img src="${{imgSrc}}"/>` : '<div style="color:#999;">圖片載入失敗</div>'}}
        </div>
    </div>
</div>`;
            }}

            html += '</body></html>';

            // 還原按鈕
            btn.textContent = originalText;
            btn.disabled = false;

            const win = window.open('', '_blank');
            win.document.write(html);
            win.document.close();
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        loadData();
    </script>
</body>
</html>'''


def generate_index_html(reports_data):
    """產生總覽頁面 HTML"""
    reports_json = json.dumps(reports_data, ensure_ascii=False)
    return f'''<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>中油偵測報告系統</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --text-dark: #0F172A;
            --text-secondary: #64748B;
            --text-muted: #94A3B8;
            --accent-blue: #3B82F6;
            --border-color: #E2E8F0;
            --bg-light: #F8FAFC;
            --success: #10B981;
            --warning: #F59E0B;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-light);
            color: var(--text-dark);
            line-height: 1.5;
            min-height: 100vh;
        }}

        .header {{
            background: white;
            border-bottom: 1px solid var(--border-color);
            padding: 24px 32px;
        }}
        .header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .header-title {{
            font-size: 24px;
            font-weight: 700;
        }}
        .header-title .highlight {{
            color: var(--accent-blue);
        }}

        .main {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 32px;
        }}

        .month-section {{
            margin-bottom: 32px;
        }}
        .month-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-dark);
        }}

        .date-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}

        .date-card {{
            background: white;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            padding: 20px;
            transition: all 0.2s ease;
        }}
        .date-card:hover {{
            border-color: var(--accent-blue);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
        }}
        .date-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }}
        .date-day {{
            font-size: 28px;
            font-weight: 700;
            color: var(--accent-blue);
        }}
        .date-weekday {{
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .category-list {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .category-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            background: var(--bg-light);
            border-radius: 12px;
            font-size: 15px;
            font-weight: 500;
        }}
        .category-name {{
            color: var(--text-dark);
            font-size: 16px;
        }}
        .category-links {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .category-links a {{
            text-decoration: none;
            font-weight: 600;
            transition: all 0.15s ease;
        }}
        .link-review {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            color: #9CA3AF;
            background: transparent;
        }}
        .link-review:hover {{
            color: #6B7280;
            background: #F3F4F6;
        }}
        .link-report {{
            padding: 12px 28px;
            border-radius: 8px;
            font-size: 15px;
            background: #059669;
            color: white;
            box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3);
        }}
        .link-report:hover {{
            background: #047857;
            box-shadow: 0 4px 12px rgba(5, 150, 105, 0.4);
            transform: translateY(-1px);
        }}
        .link-report.disabled {{
            background: #D1D5DB;
            color: #9CA3AF;
            cursor: not-allowed;
            box-shadow: none;
        }}
        .link-report.disabled:hover {{
            background: #D1D5DB;
            transform: none;
            box-shadow: none;
        }}

        .empty-state {{
            text-align: center;
            padding: 80px 32px;
            color: var(--text-secondary);
        }}
        .empty-state svg {{
            width: 80px;
            height: 80px;
            margin-bottom: 24px;
            opacity: 0.3;
        }}

        .footer {{
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <header class="header">
        <div class="header-inner">
            <div class="header-title">
                <span class="highlight">中油</span> 偵測報告系統
            </div>
            <div style="font-size: 14px; color: var(--text-secondary);">
                iSeek AI 影像辨識
            </div>
        </div>
    </header>

    <main class="main" id="main">
    </main>

    <footer class="footer">
        iSeek AI 影像辨識系統 — 工安監控平台
    </footer>

    <script>
        const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];
        const REPORT_DATA = {reports_json};

        function checkReportAccess(reportKey, category) {{
            const hasData = localStorage.getItem(reportKey);
            if (!hasData) {{
                alert('請先完成「' + category + '」的審核作業，\\n按下「偵測報告」按鈕後才能檢視報告。');
                return false;
            }}
            return true;
        }}

        function render() {{
            if (!REPORT_DATA || REPORT_DATA.length === 0) {{
                document.getElementById('main').innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
                        </svg>
                        <h3>尚無偵測報告</h3>
                        <p>執行 generate_daily_review.py 產生審核工具</p>
                    </div>`;
                return;
            }}

            // 依月份分組
            const byMonth = {{}};
            REPORT_DATA.forEach(r => {{
                const key = r.date.substring(0, 7);
                if (!byMonth[key]) byMonth[key] = [];
                byMonth[key].push(r);
            }});

            let html = '';
            const sortedMonths = Object.keys(byMonth).sort().reverse();

            sortedMonths.forEach(month => {{
                const [year, mon] = month.split('-');
                html += `<div class="month-section">
                    <div class="month-title">${{year}} 年 ${{parseInt(mon)}} 月</div>
                    <div class="date-grid">`;

                const dateMap = {{}};
                byMonth[month].forEach(r => {{
                    if (!dateMap[r.date]) dateMap[r.date] = [];
                    dateMap[r.date].push(r);
                }});

                Object.keys(dateMap).sort().reverse().forEach(date => {{
                    const items = dateMap[date];
                    const d = new Date(date);
                    const day = d.getDate();
                    const weekday = WEEKDAYS[d.getDay()];

                    html += `<div class="date-card">
                        <div class="date-header">
                            <div>
                                <div class="date-day">${{day}}</div>
                                <div class="date-weekday">星期${{weekday}}</div>
                            </div>
                        </div>
                        <div class="category-list">`;

                    items.forEach(item => {{
                        const reportKey = 'reportData_' + item.date + '_' + item.category;
                        const hasReviewedData = localStorage.getItem(reportKey);
                        html += `<div class="category-item">
                            <span class="category-name">${{item.category}}</span>
                            <div class="category-links">
                                <a href="${{item.reviewPath}}" class="link-review">審核</a>
                                ${{item.reportPath ? `<a href="${{item.reportPath}}" class="link-report${{hasReviewedData ? '' : ' disabled'}}" onclick="return checkReportAccess('${{reportKey}}', '${{item.category}}')">報告</a>` : ''}}
                            </div>
                        </div>`;
                    }});

                    html += `</div></div>`;
                }});

                html += '</div></div>';
            }});

            document.getElementById('main').innerHTML = html;
        }}

        render();
    </script>
</body>
</html>'''


def main():
    import argparse
    parser = argparse.ArgumentParser(description='產生中油偵測報告審核工具')
    parser.add_argument('--date', type=str, default=datetime.now().strftime('%Y-%m-%d'),
                        help='指定日期 (YYYY-MM-DD)，預設為今天')
    args = parser.parse_args()

    date_str = args.date
    print(f"\n=== 中油偵測報告產生器 ===")
    print(f"日期: {date_str}")
    print(f"輸出目錄: {BASE_DIR}")

    # 建立日期資料夾
    year, month, day = date_str.split('-')
    date_dir = BASE_DIR / year / month / day
    date_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n建立資料夾: {date_dir}")

    # 取得 API 資料
    print(f"\n從 API 取得資料...")
    all_logs = []
    for cam_id in CAMERA_IDS:
        print(f"  查詢 camera_id: {cam_id}")
        logs = fetch_api_data(date_str, cam_id)
        print(f"    取得 {len(logs)} 筆記錄")
        all_logs.extend(logs)

    print(f"總共取得 {len(all_logs)} 筆記錄")

    if not all_logs:
        print("\n沒有取得任何資料，結束。")
        return

    # 分類
    categorized = categorize_logs(all_logs)

    # 產生各類別的審核工具
    for category, logs in categorized.items():
        if not logs:
            print(f"\n{category}: 無資料，跳過")
            continue

        # 局限空間：合併同一時段的設備缺失通報
        if category == '局限空間':
            original_count = len(logs)
            logs = consolidate_confined_space_logs(logs)
            if len(logs) < original_count:
                print(f"\n{category}: 合併設備缺失通報 ({original_count} → {len(logs)} 筆)")

        print(f"\n產生 {category} 審核工具 ({len(logs)} 筆)...")

        # 處理資料（合併相同 ID，只保留第一筆）
        processed_logs = []
        seen_ids = set()
        skipped_count = 0

        for log in logs:
            mesg, person_ids = extract_id_from_mesg(log.get('mesg', ''))
            if not person_ids:
                person_ids = str(log.get('person_ids', ''))

            # 跳過已出現過的 ID
            if person_ids and person_ids in seen_ids:
                skipped_count += 1
                continue
            if person_ids:
                seen_ids.add(person_ids)

            time_str = log.get('time', '')
            time_display = ''
            if time_str:
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    time_display = dt.strftime('%H:%M:%S')
                except:
                    time_display = time_str

            # 處理圖片 URL
            image_url = log.get('image_url', '')
            if not image_url and log.get('key'):
                image_url = f"https://apigatewayiseek.intemotech.com/vision_logic/logs/notify/image?key={log.get('key')}"

            # 處理影片 URL - 從 video_key 中提取 path
            video_url = log.get('video_url', '')
            if not video_url and log.get('video_key'):
                video_key = log.get('video_key', '')
                # video_key 格式: offset:123,container_id:80,host:192.168.53.14,path:/app/image/...
                path_match = re.search(r'path:([^,]+)', video_key)
                if path_match:
                    video_path = path_match.group(1)
                    video_url = f"https://apigatewayiseek.intemotech.com/vision_logic/video?key={video_path}"

            # 特殊處理：ID 746 的 heartbeat 顯示為「未戴安全帽」
            mesg = log.get('mesg', '')
            if log.get('type') == 'heartbeat' and '746' in str(person_ids):
                mesg = f'未戴安全帽 ID: {person_ids}'

            processed_logs.append({
                'id': log.get('id', len(processed_logs)),  # 使用 API 原始 ID
                'time': time_str,
                'time_display': time_display,
                'mesg': mesg,
                'type': log.get('type', ''),   # 加入 type 欄位
                'person_ids': person_ids,
                'image_url': image_url,
                'video_url': video_url
            })

        if skipped_count > 0:
            print(f"    (合併重複 ID，跳過 {skipped_count} 筆)")

        # 待分類類別使用專用模板
        if category == '待分類':
            # 產生待分類卡片 HTML（需要保留 type 欄位）
            for log in processed_logs:
                # 找回原始 log 的 type
                original_log = next((l for l in logs if l.get('mesg', '') == log['mesg'] or
                                    extract_id_from_mesg(l.get('mesg', ''))[1] == log['person_ids']), None)
                if original_log:
                    log['type'] = original_log.get('type', '')

            cards_html = ''.join(generate_pending_card_html(log, log['id']) for log in processed_logs)

            # 產生待分類審核工具 HTML
            review_filename = f"{category}_審核.html"
            html_content = generate_pending_review_html(
                date_str=date_str,
                total=len(processed_logs),
                cards_html=cards_html,
                data_json=json.dumps(processed_logs, ensure_ascii=False)
            )

            review_path = date_dir / review_filename
            with open(review_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  審核工具: {review_path}")
            # 待分類不產生報告頁面
            continue

        # 產生卡片 HTML
        cards_html = ''.join(generate_card_html(log, log['id']) for log in processed_logs)

        # 檢查是否有預設確認的 CSV 檔案
        preset_times = None
        csv_patterns = [
            Path(f'/Users/ada/Documents/C.客製化/3.中油/2026/{date_str.replace("-", "")}_violations.csv'),
            Path(f'/Users/ada/Documents/C.客製化/3.中油/2026/{date_str.replace("-", "")[4:]}_violations.csv'),
        ]
        for csv_path in csv_patterns:
            if csv_path.exists():
                import csv
                with open(csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    preset_times = [row['time_display'] for row in reader if row.get('time_display')]
                print(f"    載入預設確認資料: {csv_path.name} ({len(preset_times)} 筆)")
                break

        # 產生審核工具 HTML
        review_filename = f"{category}_審核.html"
        report_filename = f"{category}_報告.html"

        html_content = generate_review_html(
            category=category,
            date_str=date_str,
            total=len(processed_logs),
            cards_html=cards_html,
            data_json=json.dumps(processed_logs, ensure_ascii=False),
            report_path=report_filename,
            preset_times=preset_times
        )

        review_path = date_dir / review_filename
        with open(review_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  審核工具: {review_path}")

        # 產生報告頁面（審核用，有按鈕）
        report_content = generate_report_html(category, date_str)
        report_path = date_dir / report_filename
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"  報告頁面: {report_path}")

        # 產生管理版報告頁面（從 API 讀取已確認違規）
        manager_filename = f"{category}_報告_管理版.html"
        manager_content = generate_manager_report_html(category, date_str)
        manager_path = date_dir / manager_filename
        with open(manager_path, 'w', encoding='utf-8') as f:
            f.write(manager_content)
        print(f"  管理版報告: {manager_path}")

    # 更新 index.html
    print(f"\n更新 index.html...")
    update_index_html(BASE_DIR)

    print(f"\n=== 完成 ===")
    print(f"審核工具位置: {date_dir}")
    print(f"總覽頁面: {BASE_DIR}/index.html")


def update_index_html(base_dir):
    """掃描所有報告並更新 index.html"""
    reports = []

    # 掃描所有日期資料夾
    for year_dir in sorted(base_dir.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for day_dir in sorted(month_dir.iterdir()):
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue

                date_str = f"{year_dir.name}-{month_dir.name}-{day_dir.name}"
                rel_path = f"{year_dir.name}/{month_dir.name}/{day_dir.name}"

                for category in CATEGORIES.keys():
                    review_file = day_dir / f"{category}_審核.html"
                    manager_file = day_dir / f"{category}_報告_管理版.html"

                    if review_file.exists():
                        reports.append({
                            'date': date_str,
                            'category': category,
                            'reviewPath': f"{rel_path}/{category}_審核.html",
                            'reportPath': f"{rel_path}/{category}_報告_管理版.html" if manager_file.exists() else None
                        })

    # 產生 index.html
    index_content = generate_index_html(reports)
    index_path = base_dir / 'index.html'
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)
    print(f"  index.html 已更新")


if __name__ == '__main__':
    main()
