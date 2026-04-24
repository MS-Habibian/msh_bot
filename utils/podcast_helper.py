import logging
import os
import time
import aiohttp

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
    """دانلود فایل صوتی و گزارش پیشرفت (مشابه یوتیوب ولی کاملا Async)"""
    os.makedirs(output_dir, exist_ok=True)
    filename = url.split('/')[-1].split('?')[0] or f"podcast_{int(time.time())}.mp3"
    filepath = os.path.join(output_dir, filename)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            total_bytes = int(response.headers.get('content-length', 0))
            downloaded_bytes = 0
            last_update_time = time.time()

            with open(filepath, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024 * 1024):  # دانلود در تکه های 1 مگابایتی
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_bytes += len(chunk)

                    current_time = time.time()
                    # آپدیت وضعیت هر 3 ثانیه (همانند منطق youtube_helper)
                    if progress_callback and (current_time - last_update_time > 3):
                        last_update_time = current_time
                        # چون خود aiohttp غیرهمگام است، نیازی به threadsafe نداریم
                        await progress_callback(downloaded_bytes, total_bytes)

    return filepath
