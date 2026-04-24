import logging
import os
import time
import aiohttp
import aiofiles


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

async def download_podcast_async(url, output_dir, progress_callback=None):
    # اضافه کردن هدر مرورگر واقعی برای جلوگیری از خطای 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, allow_redirects=True) as response:
            response.raise_for_status()  # بررسی وجود خطا
            
            total_size = int(response.headers.get('content-length', 0))
            
            # ایجاد یک نام فایل یکتا
            file_name = f"podcast_{int(time.time())}.mp3"
            file_path = os.path.join(output_dir, file_name)
            
            downloaded_size = 0
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    await f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    if progress_callback:
                        await progress_callback(downloaded_size, total_size)
                        
            return file_path
