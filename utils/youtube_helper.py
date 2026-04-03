import asyncio
import yt_dlp
import os
import aiohttp
import aiofiles
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
    os.makedirs(output_dir, exist_ok=True)
    
    # هدرهای شبیه‌سازی مرورگر برای دور زدن فایروال کوبالت
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://cobalt.tools",
        "Referer": "https://cobalt.tools/",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # ساختار جدید (v7) برای API کوبالت
    payload = {
        "url": url,
        "videoQuality": "720", 
        "filenamePattern": "basic"
    }

    # تنظیم تایم‌اوت برای جلوگیری از گیر کردن ربات
    timeout = aiohttp.ClientTimeout(total=600)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # ۱. درخواست لینک مستقیم از API
        # نکته: اندپوینت جدید کوبالت مستقیماً آدرس روت است
        api_url = "https://api.cobalt.tools/" 
        
        async with session.post(api_url, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Cobalt API Error ({resp.status}): {error_text}")
            
            data = await resp.json()
            
            # در نسخه جدید، وضعیت موفقیت با url برمی‌گردد
            if "url" not in data:
                raise Exception(f"Cobalt Response Error: {data}")
                
            download_url = data["url"]
            filename = data.get("filename", f"youtube_video_{int(time.time())}.mp4")
            
            # اطمینان از داشتن پسوند
            if not filename.endswith('.mp4'):
                filename += ".mp4"
                
            file_path = os.path.join(output_dir, filename)

        # ۲. دانلود فایل ویدیو از لینک استخراج شده
        async with session.get(download_url, headers={"User-Agent": headers["User-Agent"]}) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download file from generated link. Status: {resp.status}")
                
            total_size = int(resp.headers.get('content-length', 0))
            downloaded = 0
            last_update_time = time.time()
            
            async with aiofiles.open(file_path, mode='wb') as f:
                async for chunk in resp.content.iter_chunked(2 * 1024 * 1024): # تکه‌های ۲ مگابایتی
                    await f.write(chunk)
                    downloaded += len(chunk)
                    
                    # آپدیت پروگرس بار هر 3 ثانیه (برای جلوگیری از فلود شدن API بله/تلگرام)
                    current_time = time.time()
                    if progress_callback and (current_time - last_update_time > 3 or downloaded == total_size):
                        try:
                            # اجرای تابع به صورت غیرهمزمان
                            if asyncio.iscoroutinefunction(progress_callback):
                                await progress_callback(downloaded, total_size)
                            else:
                                progress_callback(downloaded, total_size)
                        except Exception:
                            pass # نادیده گرفتن ارورهای آپدیت پیام
                        last_update_time = current_time

    return file_path