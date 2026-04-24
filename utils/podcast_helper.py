import os
import asyncio
import time
import uuid
import yt_dlp
from urllib.parse import quote

async def download_podcast_async(url: str, output_dir: str, progress_callback=None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    last_update_time = [0.0]
    main_loop = asyncio.get_running_loop()

    def my_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            current_time = time.time()
            if current_time - last_update_time[0] > 3:  # آپدیت هر 3 ثانیه
                last_update_time[0] = current_time
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if asyncio.iscoroutinefunction(progress_callback):
                    asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

    # ایجاد یک شناسه کوتاه و یکتا (8 کاراکتر) برای نام فایل
    short_id = str(uuid.uuid4())[:8]

    ydl_opts = {
        'format': 'bestaudio/best',
        # استفاده از شناسه کوتاه به جای %(id)s برای جلوگیری از خطای نام طولانی
        'outtmpl': os.path.join(output_dir, f'podcast_{short_id}.%(ext)s'),
        'cookiefile': 'cookie.txt', # در صورت عدم نیاز می‌توانید این خط را حذف کنید
        'progress_hooks': [my_hook],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*'
        }
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    # اجرای عملیات دانلود در یک ترد جداگانه
    filepath = await asyncio.to_thread(_download)
    return filepath
