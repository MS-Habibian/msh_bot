# utils/download_helper.py
import os
import time
import tempfile
import aiohttp
from urllib.parse import urlparse, unquote

def get_filename(url: str, headers: dict) -> str:
    """Tries to figure out the best filename from the headers or the URL."""
    if 'Content-Disposition' in headers:
        content_disposition = headers.get('Content-Disposition')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
            return filename

    parsed_url = urlparse(url)
    filename = unquote(os.path.basename(parsed_url.path))
    if not filename:
        filename = "downloaded_file.unknown"
    return filename

def format_size(bytes_size: int) -> str:
    """Converts bytes to a readable format (MB)."""
    return f"{bytes_size / (1024 * 1024):.2f} MB"

async def download_file_async(url: str, progress_callback=None) -> str:
    """
    Downloads a file asynchronously, checks size, and reports progress.
    """
    async with aiohttp.ClientSession() as session:
        # Start the request, but don't download the body yet
        async with session.get(url) as response:
            response.raise_for_status()

            # 1. Detect file size from headers (if the server provides it)
            total_size = int(response.headers.get('Content-Length', 0))
            
            # Telegram bot limit is 50MB (52,428,800 bytes)
            if total_size > 52428800:
                raise ValueError(f"File is too large ({format_size(total_size)}). Telegram limit is 50 MB.")

            filename = get_filename(url, response.headers)
            filepath = os.path.join(tempfile.gettempdir(), filename)

            downloaded_size = 0
            last_update_time = time.time()

            # 2. Download the file in chunks
            with open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    # 3. Report progress every 2 seconds (to avoid Telegram rate limits)
                    now = time.time()
                    if now - last_update_time > 2:
                        if progress_callback:
                            await progress_callback(downloaded_size, total_size)
                        last_update_time = now

            return filepath
    