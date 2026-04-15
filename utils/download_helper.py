# utils/download_helper.py
import os
import time
import aiohttp
import urllib.parse
import subprocess
import math
import glob

def format_size(bytes_size: int) -> str:
    """Converts bytes to a readable format (MB)."""
    return f"{bytes_size / (1024 * 1024):.2f} MB"

async def download_file_async(url, dest_folder, progress_callback=None):
    # Modified to save inside a specific dest_folder
    os.makedirs(dest_folder, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()

            # Extract filename (simplified for this example)
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(urllib.parse.unquote(parsed_url.path))
            if not filename:
                filename = "downloaded_file.dat"

            filepath = os.path.join(dest_folder, filename)
            total_size = int(response.headers.get("Content-Length", 0))
            print("file size:", total_size)
            # Telegram bot limit is 5GB (52,428,800 bytes)
            if total_size > 5242880000:
                raise ValueError(
                    f"File is too large ({format_size(total_size)}). Telegram limit is 5 GB."
                )

            downloaded_size = 0
            last_update_time = time.time()

            # 2. Download the file in chunks
            with open(filepath, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    # 3. Report progress every 2 seconds (to avoid Telegram rate limits)
                    now = time.time()
                    if now - last_update_time > 4:
                        if progress_callback:
                            await progress_callback(downloaded_size, total_size)
                        last_update_time = now
            return filepath


def split_file(filepath, chunk_size=20 * 1024 * 1024):  # 20 MB chunks
    """Splits a file into binary chunks and returns a list of part paths."""
    file_size = os.path.getsize(filepath)
    if file_size <= chunk_size:
        return [filepath]

    part_files = []
    part_num = 1
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            # Create extensions like .part001, .part002
            part_name = f"{filepath}.part{part_num:03d}"
            with open(part_name, "wb") as p:
                p.write(chunk)
            part_files.append(part_name)
            part_num += 1

    # Remove the original large file to save disk space
    os.remove(filepath)
    return part_files


def split_media_playable(filepath, max_size_mb=19):
    """Splits audio/video into playable segments using FFmpeg explicitly and returns paths."""
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(filepath)
    
    if file_size <= max_size_bytes:
        return [filepath]
        
    parts_count = math.ceil(file_size / max_size_bytes)
    
    try:
        cmd_duration = [
            'ffprobe', '-v', 'error', '-show_entries', 
            'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath
        ]
        duration_str = subprocess.check_output(cmd_duration).decode('utf-8').strip()
        total_duration = float(duration_str)
    except Exception as e:
        print(f"Error getting duration: {e}")
        # اگر زمان تشخیص داده نشد، برمی‌گردیم به حالت باینری ساده تا ربات از کار نیفتد
        return split_file(filepath, chunk_size=max_size_bytes)

    # محاسبه دقیق زمان هر بخش
    segment_time = math.ceil(total_duration / parts_count)
    base_name, ext = os.path.splitext(filepath)
    split_files = []
    
    for i in range(parts_count):
        start_time = i * segment_time
        if start_time >= total_duration:
            break
            
        output_file = f"{base_name}_part{i+1:03d}{ext}"
        
        cmd_split = [
            'ffmpeg', '-y', '-i', filepath,
            '-ss', str(start_time),  # نقطه شروع
            '-t', str(segment_time), # مدت زمان این بخش
            '-c', 'copy',            # کپی بدون افت کیفیت
            output_file
        ]
        
        subprocess.run(cmd_split, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            split_files.append(output_file)

    # حذف فایل اصلی پس از اتمام برش
    if len(split_files) > 0 and os.path.exists(filepath):
        os.remove(filepath)
        
    return split_files
