import os
import time
import aiohttp

async def search_podcast_async(query: str, limit: int = 5) -> list:
    """جستجوی اپیزودهای پادکست در iTunes"""
    url = f"https://itunes.apple.com/search?media=podcast&entity=podcastEpisode&term={query}&limit={limit}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            results = []
            
            for item in data.get('results', []):
                # تبدیل میلی‌ثانیه به فرمت دقیقه:ثانیه
                millis = item.get('trackTimeMillis', 0)
                seconds = (millis / 1000) % 60
                minutes = (millis / (1000 * 60)) % 60
                duration_str = f"{int(minutes):02d}:{int(seconds):02d}"

                results.append({
                    'id': str(item.get('trackId')),
                    'title': item.get('trackName', 'عنوان نامشخص'),
                    'duration': duration_str,
                    'audio_url': item.get('episodeUrl')
                })
            return results

async def get_podcast_url_async(track_id: str) -> str:
    """پیدا کردن لینک مستقیم دانلود بر اساس آیدی اپیزود"""
    url = f"https://itunes.apple.com/lookup?id={track_id}&entity=podcastEpisode"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data.get('results'):
                return data['results'][0].get('episodeUrl')
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
