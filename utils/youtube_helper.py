# utils/youtube_helper.py
import asyncio
import yt_dlp
import os
import subprocess
import sys

async def search_youtube_async(query: str, limit: int = 5) -> list:
    """جستجوی یوتیوب"""
    search_query = f"ytsearch{limit}:{query}"
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': False,
        'no_warnings': False,
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
        print(f"Search Error: {e}")
        raise e

async def download_youtube_video_async(url: str, output_dir: str, progress_callback=None) -> str:
    """دانلود هوشمند با اطمینان از خروجی MP4"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # تعریف پست-پردازنده برای تبدیل خودکار به MP4
    # این کار باعث می‌شود حتی اگر فایل webm دانلود شد، به mp4 تبدیل شود
    postprocessors = [{
        'key': 'FFmpegVideoConvertor',
        'preferedformat': 'mp4',
        'other': '-c:v libx264 -c:a aac', # تنظیمات استاندارد برای تلگرام
    }]

    ydl_opts = {
        # 🔥 کلید تغییر: 
        # 'best' یعنی بهترین کیفیت موجود را بگیر (چه ویدیو+صدا جدا باشند چه یکی باشند).
        # اگر جدا بودند، yt-dlp سعی میکند ترکیبشان کند.
        # اگر نتوانست ترکیب کند، بهترین فرمت تک (مثلا webm) را می‌گیرد.
        'format': 'best', 
        
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'ignoreerrors': False,
        
        # اضافه کردن پست-پردازنده برای تبدیل نهایی
        'postprocessors': postprocessors,
        
        # جلوگیری از دانلود مجدد اگر فایل قبلاً دانلود شده (اختیاری)
        'writethumbnail': False,
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # پیدا کردن فایل نهایی (ممکن است نام فایل بعد از تبدیل تغییر کرده باشد)
            # yt-dlp معمولا فایل اصلی را برمی‌گرداند، اما مطمئن شویم که پسوند mp4 دارد
            filename = ydl.prepare_filename(info)
            
            # اگر فایل اصلی mp4 نبود، شاید نامش را تغییر داده باشد (مثلا .webm.mp4)
            # یا شاید تبدیل انجام نشده باشد. بیایید پوشه را چک کنیم تا فایل mp4 را پیدا کنیم.
            files = [f for f in os.listdir(os.path.dirname(filename)) if f.endswith('.mp4')]
            if files:
                return os.path.join(os.path.dirname(filename), files[0])
            
            return filename

    try:
        downloaded_file_path = await asyncio.to_thread(_download)
        
        # بررسی نهایی: آیا فایل وجود دارد؟
        if not os.path.exists(downloaded_file_path):
            # تلاش برای پیدا کردن فایل در پوشه با پسوند mp4
            folder_path = os.path.dirname(downloaded_file_path)
            mp4_files = [f for f in os.listdir(folder_path) if f.endswith('.mp4')]
            if mp4_files:
                downloaded_file_path = os.path.join(folder_path, mp4_files[0])
            else:
                raise FileNotFoundError("فایل ویدیویی یافت نشد.")
                
        return downloaded_file_path

    except Exception as e:
        # اگر ارور خاصی از yt-dlp آمد، جزئیات بیشتر بدهیم
        error_msg = str(e)
        if "Requested format is not available" in error_msg:
            # این خطا دیگر نباید بیاید با استراتژی جدید، اما اگر آمد:
            # یعنی ویدیو اصلاً قابل دانلود نیست (مثلاً خصوصی یا حذف شده)
            raise Exception(f"ویدیو قابل دسترسی نیست یا فرمت‌های آن موجود نمی‌باشد. ({error_msg})")
        raise e

# تابع کمکی برای نمایش حجم (اگر در فایل دیگر نیست)
def format_size(num):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} TB"