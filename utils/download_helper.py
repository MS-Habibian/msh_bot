# utils/download_helper.py
import os
import time
import aiohttp
import urllib.parse


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


def split_file(filepath, chunk_size=20 * 1024 * 1024):  # 49 MB chunks
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
