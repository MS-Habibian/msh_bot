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

async def download_youtube_video_async(url: str, output_dir: str, progress_callback=None) -> str:
    """دانلود ویدیو از یوتیوب"""
    
    # اطمینان از اینکه پوشه خروجی وجود دارد
    os.makedirs(output_dir, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        
        # حذف کامل web و استفاده انحصاری از کلاینت‌های موبایل و تلویزیون
        'extractor_args': {
            'youtube': {
                'client': ['android', 'ios', 'tv'],
                'player_client': ['android', 'ios']
            }
        },
        
        'quiet': False,
        'no_warnings': False,
    }

    # اگر از progress_callback استفاده می‌کنید
    if progress_callback:
        class MyLogger(object):
            def debug(self, msg): pass
            def warning(self, msg): pass
            def error(self, msg): print(msg)

        def progress_hook(d):
            if d['status'] == 'downloading':
                # جلوگیری از اسپم شدن تلگرام با آپدیت‌های زیاد (مثلا هر 10 درصد آپدیت کند)
                # برای سادگی در اینجا فراخوانی را محدود کنید یا مستقیما پاس دهید
                pass 
                
        ydl_opts['logger'] = MyLogger()
        ydl_opts['progress_hooks'] = [progress_hook]

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    # اجرای عملیات دانلود در یک thread جداگانه
    downloaded_file_path = await asyncio.to_thread(_download)
    return downloaded_file_path
