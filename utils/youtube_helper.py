import asyncio
import yt_dlp
import os
import aiohttp
import aiofiles

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
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    payload = {
        "url": url,
        "vQuality": "720", # کیفیت مورد نظر
        "isAudioOnly": False
    }

    async with aiohttp.ClientSession() as session:
        # درخواست به API کوبالت برای دریافت لینک مستقیم
        async with session.post("https://api.cobalt.tools/api/json", json=payload, headers=headers) as resp:
            if resp.status != 200:
                raise Exception("Failed to get download link from Cobalt API")
            
            data = await resp.json()
            if "url" not in data:
                raise Exception(f"Cobalt API Error: {data.get('text', 'Unknown')}")
                
            download_url = data["url"]
            filename = data.get("filename", "video.mp4")
            if not filename.endswith('.mp4'):
                filename += ".mp4"
                
            file_path = os.path.join(output_dir, filename)

        # دانلود فایل از لینک مستقیم به دست آمده
        async with session.get(download_url) as resp:
            if resp.status != 200:
                raise Exception("Failed to download the actual video file")
                
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            
            async with aiofiles.open(file_path, mode='wb') as f:
                async for chunk in resp.content.iter_chunked(1024 * 1024): # تکه های 1 مگابایتی
                    await f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        # به‌روزرسانی پیشرفت (می‌توانید منطق تاخیر ۳ ثانیه‌ای را اینجا پیاده کنید)
                        await progress_callback(downloaded, total_size)

    return file_path