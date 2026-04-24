import os
import asyncio
import aiohttp
import yt_dlp
from urllib.parse import quote

async def search_podcast_async(query: str, limit: int = 50) -> list:
    """جستجوی پادکست در iTunes و دریافت ۵۰ نتیجه برای صفحه‌بندی محلی"""
    url = f"https://itunes.apple.com/search?media=podcast&term={quote(query)}&limit={limit}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"خطای API: {response.status}")
            
            data = await response.json(content_type=None)
            results = []
            for item in data.get('results', []):
                # اگر لینک مستقیم اپیزود وجود نداشت، از لینک فید (در صورت وجود) استفاده می‌کنیم
                ep_url = item.get('episodeUrl') or item.get('feedUrl')
                if ep_url:
                    results.append({
                        'id': str(item.get('trackId', item.get('collectionId', ''))),
                        'title': item.get('trackName', item.get('collectionName', 'نامشخص')),
                        'artist': item.get('artistName', 'نامشخص'),
                        'url': ep_url
                    })
            return results

async def download_podcast_async(url: str, dest_folder: str, progress_callback=None) -> str:
    """دانلود پادکست با استفاده از yt-dlp برای جلوگیری از خطای 403"""
    os.makedirs(dest_folder, exist_ok=True)
    
    def my_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            # فراخوانی تابع آپدیت تلگرام در event loop اصلی
            asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), asyncio.get_running_loop())

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(dest_folder, 'podcast_%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [my_hook]
    }

    def extract_and_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    return await asyncio.to_thread(extract_and_download)
