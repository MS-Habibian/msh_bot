# utils/download_helper.py
import os
import time
import aiohttp
import urllib.parse

from utils import get_file_size_from_url
from config import MAX_FILE_SIZE


def format_size(bytes_size: int) -> str:
    """Converts bytes to a readable format (MB)."""
    return f"{bytes_size / (1024 * 1024):.2f} MB"


async def download_file_async(url, dest_folder, progress_callback=None):
    # first check the download size limit
    # TODO: different limit for admin, regular user
    total_size = get_file_size_from_url(url)
    if total_size > MAX_FILE_SIZE:
        raise ValueError(
            f"حجم فایل خواسته شده {format_size(total_size)} بیش از حد مجاز {format_size(MAX_FILE_SIZE)} است."
        )

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
