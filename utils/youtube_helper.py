# utils/youtube_helper.py
import asyncio
import yt_dlp
import os
import time

async def search_youtube_async(query: str, limit: int = 5) -> list:
    """جستجوی یوتیوب به صورت غیرهمزمان"""
    
    # روش امن‌تر و مطمئن‌تر برای جستجو در yt-dlp
    search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': False,       # False کردیم تا ارورهای شبکه در لاگ سرور چاپ شود
        'no_warnings': False,
        
        # ⚠️ مهم: اگر سرور شما در ایران است، یوتیوب فیلتر است و باید پروکسی تنظیم کنید
        # 'proxy': 'http://127.0.0.1:10809', # یا آدرس پروکسی سرور خودتان
    }

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(search_query, download=False)

    try:
        result = await asyncio.to_thread(_search)
        
        videos = []
        if result and 'entries' in result:
            for entry in result['entries']:
                videos.append({
                    'id': entry.get('id'),
                    'title': entry.get('title', 'Unknown Title'),
                })
        return videos
    except Exception as e:
        print(f"yt-dlp Search Error: {e}")
        raise e # ارور را پاس می‌دهیم تا در تلگرام/بله چاپ شود

async def download_youtube_video_async(video_url: str, download_folder: str, progress_callback=None) -> str:
    """دانلود ویدیو یوتیوب با پشتیبانی از آپدیت پیشرفت"""
    os.makedirs(download_folder, exist_ok=True)
    
    loop = asyncio.get_running_loop()
    last_update_time = [0] # استفاده از لیست برای تغییر در scope داخلی

    def yt_progress_hook(d):
        if not progress_callback:
            return
            
        if d['status'] == 'downloading':
            current_time = time.time()
            # آپدیت پیام تلگرام هر 2 ثانیه یکبار برای جلوگیری از خطای FloodWait
            if current_time - last_update_time[0] > 2:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
                
                # فراخوانی تابع غیرهمزمان تلگرام از داخل ترد (thread)
                asyncio.run_coroutine_threadsafe(
                    progress_callback(downloaded, total), 
                    loop
                )
                last_update_time[0] = current_time

    # تنظیمات yt-dlp (دانلود بهترین کیفیت mp4)
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        
        # 👇 این بخش را برای دور زدن سیستم ضد ربات یوتیوب اضافه کنید 👇
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'client': ['android', 'ios']
            }
        },
        
        'quiet': False,
        'no_warnings': False,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            return ydl.prepare_filename(info)

    # اجرای دانلود در ترد پس‌زمینه
    filepath = await asyncio.to_thread(_download)
    return filepath
