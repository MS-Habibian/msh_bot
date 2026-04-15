import os
import re
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
    os.makedirs(dest_folder, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()

            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(urllib.parse.unquote(parsed_url.path)) or "downloaded_file.dat"
            filepath = os.path.join(dest_folder, filename)
            
            total_size = int(response.headers.get("Content-Length", 0))
            if total_size > 5242880000:
                raise ValueError(f"File is too large ({format_size(total_size)}). Telegram limit is 5 GB.")

            downloaded_size = 0
            last_update_time = time.time()

            with open(filepath, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    now = time.time()
                    if now - last_update_time > 4:
                        if progress_callback:
                            await progress_callback(downloaded_size, total_size)
                        last_update_time = now
            return filepath


def split_file(filepath, chunk_size=19 * 1024 * 1024):  # Default 19 MB chunks
    """Splits a file into binary chunks."""
    file_size = os.path.getsize(filepath)
    if file_size <= chunk_size:
        return [filepath]

    part_files = []
    with open(filepath, "rb") as f:
        part_num = 1
        while chunk := f.read(chunk_size):
            part_name = f"{filepath}.part{part_num:03d}"
            with open(part_name, "wb") as p:
                p.write(chunk)
            part_files.append(part_name)
            part_num += 1

    os.remove(filepath)
    return part_files


def split_media_playable(filepath, max_size_mb=19):
    """Splits audio/video into playable segments using FFmpeg explicitly."""
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = os.path.getsize(filepath)
    
    if file_size <= max_size_bytes:
        return [filepath]
        
    parts_count = math.ceil(file_size / max_size_bytes)
    
    try:
        cmd_duration = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
        total_duration = float(subprocess.check_output(cmd_duration).decode('utf-8').strip())
    except Exception as e:
        print(f"Error getting duration: {e}")
        return split_file(filepath, chunk_size=max_size_bytes)

    segment_time = math.ceil(total_duration / parts_count)
    base_name, ext = os.path.splitext(filepath)
    split_files = []
    
    for i in range(parts_count):
        start_time = i * segment_time
        if start_time >= total_duration:
            break
            
        output_file = f"{base_name}_part{i+1:03d}{ext}"
        cmd_split = ['ffmpeg', '-y', '-i', filepath, '-ss', str(start_time), '-t', str(segment_time), '-c', 'copy', output_file]
        subprocess.run(cmd_split, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            split_files.append(output_file)

    if split_files and os.path.exists(filepath):
        os.remove(filepath)
        
    return split_files


def split_file_rar(filepath, max_size_mb=19.5):
    """Splits a file into multi-part RAR archives."""
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    if os.path.getsize(filepath) <= max_size_bytes:
        return [filepath]

    base_name, _ = os.path.splitext(filepath)
    rar_base_name = f"{base_name}.rar"

    cmd = ['rar', 'a', f'-v{max_size_mb}M', '-m0', '-ep', rar_base_name, filepath]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception as e:
        print(f"Error creating RAR: {e}")
        return split_file(filepath, chunk_size=max_size_bytes)

    split_files = glob.glob(f"{base_name}.part*.rar")
    split_files.sort(key=lambda f: int(re.search(r'part(\d+)\.rar$', f).group(1)) if re.search(r'part(\d+)\.rar$', f) else 0)

    if split_files and os.path.exists(filepath):
        os.remove(filepath)

    return split_files
