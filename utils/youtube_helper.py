import asyncio
import yt_dlp
import os
import time

async def search_youtube_async(query: str, limit: int = 5) -> list:
    search_query = f"ytsearch{limit}:{query}"
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
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

async def get_youtube_qualities_async(video_url: str) -> list:
    """دریافت کیفیت‌های ویدیویی موجود (رزولوشن‌ها)"""
    ydl_opts = {
        'cookiefile': 'cookie.txt',
        'js_runtimes': {'node': {}},
        'quiet': True,
        'no_warnings': True,
    }
    def _get_info():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(video_url, download=False)
            
    try:
        info = await asyncio.to_thread(_get_info)
        formats = info.get('formats', [])
        
        # استخراج رزولوشن‌های یکتا (فقط آنهایی که ویدیو دارند)
        resolutions = set()
        for f in formats:
            height = f.get('height')
            if height and f.get('vcodec') != 'none':
                resolutions.add(height)
                
        # مرتب‌سازی کیفیت‌ها (از کم به زیاد)
        sorted_res = sorted(list(resolutions))
        return sorted_res
    except Exception as e:
        print(f"Error fetching formats: {e}")
        return []

async def download_youtube_video_async(url: str, output_dir: str, format_str: str = 'b', progress_callback=None) -> str:
    """دانلود ویدیو یوتیوب با فرمت درخواستی"""
    os.makedirs(output_dir, exist_ok=True)
    last_update_time = [0.0]
    main_loop = asyncio.get_running_loop()
    
    def my_hook(d):
        if d['status'] == 'downloading':
            if progress_callback:
                current_time = time.time()
                if current_time - last_update_time[0] > 3:
                    last_update_time[0] = current_time
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    if asyncio.iscoroutinefunction(progress_callback):
                        asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

    ydl_opts = {
        'format': format_str, # استفاده از فرمت انتخابی کاربر
        'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
        'cookiefile': 'cookie.txt', 
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
