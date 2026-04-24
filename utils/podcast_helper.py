import asyncio
import logging
import os
import time
import aiohttp
import yt_dlp


logger = logging.getLogger(__name__)

async def search_podcast_async(query, limit=5, offset=0):
    url = f"https://itunes.apple.com/search?term={query}&entity=podcastEpisode&limit={limit}&offset={offset}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json(content_type=None)
                results = []
                for item in data.get('results', []):
                    results.append({
                        'id': item.get('trackId'),
                        'title': item.get('trackName', 'Unknown Title'),
                        'podcast_name': item.get('collectionName', 'Unknown Podcast'),
                        # لینک دانلود را همینجا در مرحله سرچ ذخیره می‌کنیم تا مشکل دانلود حل شود
                        'audio_url': item.get('episodeUrl') 
                    })
                return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

async def get_podcast_url_async(track_id):
    # گاهی اوقات lookup آیتونز episodeUrl را برنمی‌گرداند.
    url = f"https://itunes.apple.com/lookup?id={track_id}&entity=podcastEpisode"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json(content_type=None)
                if data.get('results'):
                    episode_url = data['results'][0].get('episodeUrl')
                    if episode_url:
                        return episode_url
                    else:
                        logger.error(f"No episodeUrl in iTunes data! Data: {data['results'][0]}")
                else:
                    logger.error(f"Empty results for track {track_id}. Data: {data}")
    except Exception as e:
        logger.error(f"Error fetching url: {e}")
    return None

async def download_podcast_async(url: str, output_dir: str, progress_callback=None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    last_update_time = [0.0]
    main_loop = asyncio.get_running_loop()

    def my_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            current_time = time.time()
            if current_time - last_update_time[0] > 3:  # آپدیت هر 3 ثانیه
                last_update_time[0] = current_time
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if asyncio.iscoroutinefunction(progress_callback):
                    asyncio.run_coroutine_threadsafe(progress_callback(downloaded, total), main_loop)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, 'podcast_%(id)s.%(ext)s'),
        'cookiefile': 'cookie.txt', # استفاده از کوکی فایل در صورت نیاز
        'progress_hooks': [my_hook],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*'
        }
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    # اجرای عملیات دانلود در یک ترد جداگانه تا ربات بلاک نشود
    filepath = await asyncio.to_thread(_download)
    return filepath
