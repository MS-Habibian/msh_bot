import asyncio
import yt_dlp
import os
import time

def format_duration(seconds: int | float | None) -> str:
    """تبدیل ثانیه به فرمت خوانای زمان"""
    if not seconds:
        return "N/A"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

async def search_youtube_async(query: str, limit: int = 5) -> list:
    search_query = f"ytsearch{limit}:{query}"
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
    
    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(search_query, download=False)
            
    try:
        result = await asyncio.to_thread(_search)
        # Added duration extraction here
        return [{
            'id': e.get('id'), 
            'title': e.get('title', 'Unknown Title'),
            'duration': format_duration(e.get('duration'))
        } for e in result.get('entries', [])]
    except Exception as e:
        print(f"yt-dlp Search Error: {e}")
        raise e

async def get_youtube_qualities_async(video_url: str) -> list:
    ydl_opts = {'cookiefile': 'cookie.txt', 'js_runtimes': {'node': {}}, 'remote_components': 'ejs:github', 'quiet': True, 'no_warnings': True}
    
    def _get_info():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(video_url, download=False)
            
    try:
        info = await asyncio.to_thread(_get_info)
        resolutions = {f.get('height') for f in info.get('formats', []) if f.get('height') and f.get('vcodec') != 'none'}
        return sorted(list(resolutions))
    except Exception as e:
        print(f"Error fetching formats: {e}")
        return []

async def download_youtube_video_async(url: str, output_dir: str, format_str: str = 'b', progress_callback=None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    last_update_time = [0.0]
    main_loop = asyncio.get_running_loop()
    
    def my_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            current_time = time.time()
            if current_time - last_update_time[0] > 3:
                last_update_time[0] = current_time
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if asyncio.iscoroutinefunction(progress_callback):
                    asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

    ydl_opts = {
        'format': format_str,
        'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
        'cookiefile': 'cookie.txt', 
        'js_runtimes': {'node': {}},    
        'remote_components': 'ejs:github',
        'progress_hooks': [my_hook],
        'quiet': True,
        'no_warnings': True,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    return await asyncio.to_thread(_download)