import asyncio
import yt_dlp
import os
import time

async def search_youtube_async(query: str, limit: int = 5) -> list:
    """جستجوی یوتیوب به صورت غیرهمزمان"""
    search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,       
        'no_warnings': True,
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
        raise e


async def download_youtube_video_async(url: str, output_dir: str, progress_callback=None) -> str:
    """دانلود ویدیو یوتیوب با استفاده از yt-dlp بر اساس تنظیماتی که در ترمینال جواب داد"""
    os.makedirs(output_dir, exist_ok=True)
    
    # برای جلوگیری از اسپم شدن تلگرام و ارور Flood Control
    last_update_time = [0.0]
    
    # گرفتن Event Loop ترد اصلی (Main Thread) قبل از ورود به ترد دانلود
    main_loop = asyncio.get_running_loop()
    
    def my_hook(d):
        if d['status'] == 'downloading':
            if progress_callback:
                current_time = time.time()
                # هر ۳ ثانیه یکبار پیام تلگرام آپدیت شود
                if current_time - last_update_time[0] > 3:
                    last_update_time[0] = current_time
                    
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    
                    # استفاده از Event loop ترد اصلی برای اجرای Coroutine
                    if asyncio.iscoroutinefunction(progress_callback):
                        asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

    ydl_opts = {
        'format': 'b',  # بهترین کیفیتی که صدا و تصویر با هم ادغام شده باشند
        'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
        'cookiefile': 'cookie.txt', # استفاده از کوکی شما
        
        # اصلاح ارور js_runtimes (تبدیل لیست به دیکشنری)
        'js_runtimes': {'node': {}},    
        
        'progress_hooks': [my_hook],
        'quiet': True,
        'no_warnings': True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    file_path = await asyncio.to_thread(_download)
    return file_path
