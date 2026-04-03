import asyncio
import yt_dlp
import os
from pytubefix import YouTube

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
    
    def on_progress(stream, chunk, bytes_remaining):
        if progress_callback:
            total = stream.filesize
            downloaded = total - bytes_remaining
            try:
                loop = asyncio.get_event_loop()
                if asyncio.iscoroutinefunction(progress_callback):
                    asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), loop)
            except Exception:
                pass

    def _download():
        # نکته کلیدی اینجاست: 
        # ۱. پارامتر use_po_token=True اضافه شده است.
        # ۲. از کلاینت ANDROID یا WEB_CREATOR استفاده می‌کنیم که حساسیت کمتری دارند.
        yt = YouTube(
            url, 
            on_progress_callback=on_progress, 
            client='ANDROID', # یا 'WEB'
            use_po_token=True
        )
        
        # فیلتر برای گرفتن ویدیویی که صدا و تصویر یکپارچه داشته باشد
        video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not video:
            raise Exception("هیچ فرمت باکیفیتی پیدا نشد.")
            
        return video.download(output_path=output_dir)

    # اجرای دانلود در یک Thread جداگانه برای قفل نشدن ربات
    file_path = await asyncio.to_thread(_download)
    return file_path