#!/usr/bin/env python3
"""
從影片中擷取第一幀作為縮圖
"""

import subprocess
import urllib.request
import ssl
from pathlib import Path
import os

# 影片 URL
video_url = "https://apigatewayiseek.intemotech.com/vision_logic/video?key=/app/image/kafka_notify_videos/production/20260407/865_%E5%85%A8%E6%94%9D%E5%BD%B1%E6%A9%9F%E5%8D%80%E5%9F%9F_161716333.mp4"

# 輸出路徑
output_dir = Path('/Users/ada/Documents/C.客製化/3.中油/2026/需通報列表/cpc通報查詢/2026/04/02')
output_dir.mkdir(parents=True, exist_ok=True)
temp_video = output_dir / 'temp_video.mp4'
output_file = output_dir / 'ID21_thumbnail.jpg'

print(f"步驟 1: 下載影片...")
print(f"  影片 URL: {video_url}")

# 下載影片
try:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(video_url, context=ctx, timeout=30) as response:
        video_data = response.read()

    with open(temp_video, 'wb') as f:
        f.write(video_data)

    print(f"  ✓ 影片已下載 ({len(video_data) / 1024:.1f} KB)")

except Exception as e:
    print(f"  ✗ 下載失敗: {e}")
    exit(1)

print(f"\n步驟 2: 擷取第一幀...")
print(f"  輸出路徑: {output_file}")

# 使用 ffmpeg 擷取第一幀
try:
    cmd = [
        'ffmpeg',
        '-i', str(temp_video),
        '-vframes', '1',  # 只輸出一幀
        '-f', 'image2',  # 輸出格式為圖片
        '-y',  # 覆蓋現有檔案
        str(output_file)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and output_file.exists():
        print(f"  ✓ 成功擷取縮圖")
        print(f"  檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

        # 刪除臨時影片
        temp_video.unlink()
        print(f"  ✓ 已清理臨時檔案")

        print(f"\n完成！")
        print(f"縮圖檔案: {output_file}")

    else:
        print(f"  ✗ 擷取失敗")
        if result.stderr:
            print(f"錯誤訊息: {result.stderr[-500:]}")  # 只顯示最後 500 字元

except FileNotFoundError:
    print("  ✗ 找不到 ffmpeg 指令")
    print("請先安裝 ffmpeg: brew install ffmpeg")
except Exception as e:
    print(f"  ✗ 發生錯誤: {e}")
finally:
    # 清理臨時檔案
    if temp_video.exists():
        temp_video.unlink()
