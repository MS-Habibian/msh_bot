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

# utils/youtube_helper.py
import aiohttp
import os

async def download_youtube_video_async(url: str, output_dir: str, progress_callback=None) -> str:
    """دانلود ویدیو از یوتیوب با استفاده از Cobalt API"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        # درخواست لینک دانلود
        async with session.post(
            'https://api.cobalt.tools/api/json',
            json={
                'url': url,
                'vQuality': '720'  # یا '1080', 'max'
            },
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'}
        ) as resp:
            data = await resp.json()
            
            if data.get('status') != 'stream':
                raise Exception(f"خطا در دریافت لینک: {data.get('text', 'نامشخص')}")
            
            download_url = data['url']
        
        # دانلود فایل
        async with session.get(download_url) as resp:
            filename = f"video_{url.split('=')[-1]}.mp4"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)
            
            return filepath

