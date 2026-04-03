import asyncio
import yt_dlp
import os
import time

async def search_youtube_async(query: str, limit: int = 5) -> list:
    """جستجوی یوتیوب به صورت غیرهمزمان"""
    search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': False,       
        'no_warnings': False,
        # 'proxy': 'http://127.0.0.1:10809', # در صورت نیاز از کامنت خارج کنید
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
    """دانلود ویدیو از یوتیوب با پشتیبانی از نوار پیشرفت"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # گرفتن Event Loop برای اجرای تابع async پیشرفت در داخل thread
    loop = asyncio.get_running_loop()
    last_update_time = [0] # استفاده از لیست برای تغییر مقدار در توابع داخلی (nonlocal)

    def progress_hook(d):
        if d['status'] == 'downloading':
            current_time = time.time()
            # آپدیت پیام تلگرام هر 3 ثانیه یکبار برای جلوگیری از ارور FloodWait
            if current_time - last_update_time[0] > 3:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                
                if progress_callback:
                    # فراخوانی امن تابع async از داخل یک thread همزمان
                    asyncio.run_coroutine_threadsafe(
                        progress_callback(downloaded, total), loop
                    )
                last_update_time[0] = current_time

    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        
        # کلاینت‌های مختلف را تست می‌کنیم تا سخت‌گیری یوتیوب کمتر شود
        'extractor_args': {'youtube': ['player_client=ios,android,web']},
        
        'progress_hooks': [progress_hook],
        
        # ✅ این خط را اضافه کنید و مسیر دقیق فایل کوکی را بدهید
        'cookiefile': 'cookie.txt',  
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    downloaded_file_path = await asyncio.to_thread(_download)
    return downloaded_file_path
