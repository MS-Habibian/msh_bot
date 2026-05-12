# import asyncio
# import yt_dlp
# import os
# import time

# def format_duration(seconds: int | float | None) -> str:
#     """تبدیل ثانیه به فرمت خوانای زمان"""
#     if not seconds:
#         return "N/A"
#     mins, secs = divmod(int(seconds), 60)
#     hours, mins = divmod(mins, 60)
#     if hours > 0:
#         return f"{hours}:{mins:02d}:{secs:02d}"
#     return f"{mins}:{secs:02d}"

# async def search_youtube_async(query: str, limit: int = 5, offset: int = 0) -> list:
#     search_query = f"ytsearch{limit + offset}:{query}"
#     ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
    
#     def _search():
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             return ydl.extract_info(search_query, download=False)
            
#     try:
#         result = await asyncio.to_thread(_search)
#         entries = result.get('entries', [])
#         sliced_entries = entries[offset : offset + limit]
        
#         results = []
#         for e in sliced_entries:
#             # Extract the best thumbnail available
#             thumbnail = e.get('thumbnail')
#             if not thumbnail and e.get('thumbnails'):
#                 thumbnail = e.get('thumbnails')[-1].get('url')
                
#             results.append({
#                 'id': e.get('id'), 
#                 'title': e.get('title', 'Unknown Title'),
#                 'duration': format_duration(e.get('duration')),
#                 'thumbnail': thumbnail
#             })
#         return results
#     except Exception as e:
#         print(f"yt-dlp Search Error: {e}")
#         raise e

# async def get_youtube_qualities_async(video_url: str) -> list:
#     ydl_opts = {'cookiefile': 'cookie.txt', 'js_runtimes': {'node': {}}, 'remote_components': 'ejs:github', 'quiet': True, 'no_warnings': True}
    
#     def _get_info():
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             return ydl.extract_info(video_url, download=False)
            
#     try:
#         info = await asyncio.to_thread(_get_info)
#         resolutions = {f.get('height') for f in info.get('formats', []) if f.get('height') and f.get('vcodec') != 'none'}
#         return sorted(list(resolutions))
#     except Exception as e:
#         print(f"Error fetching formats: {e}")
#         return []

# async def download_youtube_video_async(url: str, output_dir: str, format_str: str = 'b', progress_callback=None) -> str:
#     os.makedirs(output_dir, exist_ok=True)
#     last_update_time = [0.0]
#     main_loop = asyncio.get_running_loop()
    
#     def my_hook(d):
#         if d['status'] == 'downloading' and progress_callback:
#             current_time = time.time()
#             if current_time - last_update_time[0] > 3:
#                 last_update_time[0] = current_time
#                 downloaded = d.get('downloaded_bytes', 0)
#                 total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
#                 if asyncio.iscoroutinefunction(progress_callback):
#                     asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

#     ydl_opts = {
#         'format': format_str,
#         'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
#         'cookiefile': 'cookie.txt', 
#         'js_runtimes': {'node': {}},    
#         'remote_components': 'ejs:github',
#         'progress_hooks': [my_hook],
#         'quiet': True,
#         'no_warnings': True,
#     }

#     def _download():
#         with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=True)
#             return ydl.prepare_filename(info)

#     return await asyncio.to_thread(_download)
import asyncio
import yt_dlp
import os
import time

def format_duration(seconds: int | float | None) -> str:
    if not seconds:
        return "N/A"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

async def search_youtube_async(query: str, limit: int = 5, offset: int = 0) -> list:
    search_query = f"ytsearch{limit + offset}:{query}"
    ydl_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
    
    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(search_query, download=False)
            
    try:
        result = await asyncio.to_thread(_search)
        entries = result.get('entries', [])
        sliced_entries = entries[offset : offset + limit]
        
        results = []
        for e in sliced_entries:
            thumbnail = e.get('thumbnail')
            if not thumbnail and e.get('thumbnails'):
                thumbnail = e.get('thumbnails')[-1].get('url')
                
            results.append({
                'id': e.get('id'), 
                'title': e.get('title', 'Unknown Title'),
                'duration': format_duration(e.get('duration')),
                'thumbnail': thumbnail
            })
        return results
    except Exception as e:
        print(f"yt-dlp Search Error: {e}")
        raise e

async def get_channel_videos_async(channel_id: str, limit: int = 5, offset: int = 0) -> list:
    """دریافت ویدیوهای یک کانال با صفحه بندی و پشتیبانی از جستجوی نام کانال"""
    def _get_channel():
        target_url = channel_id
        
        # بررسی اینکه آیا ورودی لینک یا آیدی است یا یک کلمه جستجو (مثل نام فارسی)
        if not target_url.startswith("http"):
            if target_url.startswith("@"):
                target_url = f"https://www.youtube.com/{target_url}/videos"
            else:
                # اگر کلمه جستجو باشد، اولین ویدیوی مرتبط را پیدا کرده و لینک کانالش را استخراج می‌کنیم
                search_opts = {'extract_flat': True, 'quiet': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(search_opts) as ydl:
                    search_info = ydl.extract_info(f"ytsearch1:{channel_id}", download=False)
                    if not search_info or not search_info.get('entries'):
                        raise ValueError("CHANNEL_NOT_FOUND")
                    
                    first_video = search_info['entries'][0]
                    uploader_url = first_video.get('channel_url') or first_video.get('uploader_url')
                    
                    if not uploader_url:
                        raise ValueError("CHANNEL_NOT_FOUND")
                    
                    target_url = uploader_url.rstrip("/") + "/videos"
        else:
            if not target_url.endswith("/videos"):
                target_url = target_url.rstrip("/") + "/videos"

        # تعیین رنج ویدیوهایی که باید استخراج شوند (1-based index)
        start = offset + 1
        end = offset + limit
        ydl_opts = {
            'extract_flat': True, 
            'quiet': True, 
            'no_warnings': True,
            'playlist_items': f'{start}-{end}'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(target_url, download=False)
            
    try:
        result = await asyncio.to_thread(_get_channel)
        entries = result.get('entries', [])
        
        results = []
        for e in entries:
            if not e: continue
            thumbnail = e.get('thumbnail')
            if not thumbnail and e.get('thumbnails'):
                thumbnail = e.get('thumbnails')[-1].get('url')
                
            results.append({
                'id': e.get('id'), 
                'title': e.get('title', 'Unknown Title'),
                'duration': format_duration(e.get('duration')),
                'thumbnail': thumbnail
            })
        return results
    except Exception as e:
        # شناسایی خطاهای مربوط به پیدا نشدن کانال
        if "CHANNEL_NOT_FOUND" in str(e) or "404" in str(e) or "HTTP Error 404" in str(e):
            raise ValueError("CHANNEL_NOT_FOUND")
        print(f"yt-dlp Channel Error: {e}")
        raise e

    
    def _get_channel():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(channel_url, download=False)
            
    try:
        result = await asyncio.to_thread(_get_channel)
        entries = result.get('entries', [])
        
        results = []
        for e in entries:
            if not e: continue
            thumbnail = e.get('thumbnail')
            if not thumbnail and e.get('thumbnails'):
                thumbnail = e.get('thumbnails')[-1].get('url')
                
            results.append({
                'id': e.get('id'), 
                'title': e.get('title', 'Unknown Title'),
                'duration': format_duration(e.get('duration')),
                'thumbnail': thumbnail
            })
        return results
    except Exception as e:
        print(f"yt-dlp Channel Error: {e}")
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
                speed = d.get('speed', 0)  # دریافت سرعت از yt-dlp
                if asyncio.iscoroutinefunction(progress_callback):
                    asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total, speed), main_loop)

    ydl_opts = {
        'format': format_str,
        'outtmpl': os.path.join(output_dir, '%(title)s_%(id)s.%(ext)s'),
        'cookiefile': 'cookie.txt', 
        'js_runtimes': {'node': {}},    
        'remote_components': 'ejs:github',
        'progress_hooks': [my_hook],
        'quiet': True,
        'no_warnings': True,
        'cachedir': False,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    return await asyncio.to_thread(_download)
