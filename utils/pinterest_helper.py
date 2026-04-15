import aiohttp
import random
import json

# لیست گسترده‌تری از سرورهای SearXNG
SEARX_INSTANCES = [
    "https://searx.be",
    "https://searx.tiekoetter.com",
    "https://search.rowie.at",
    "https://searx.work",
    "https://paulgo.io",
    "https://searx.roastgopher.com",
    "https://searx.ox2.fr"
]

async def search_pinterest_async(query: str, limit: int = 10) -> list:
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    
    instances = random.sample(SEARX_INSTANCES, len(SEARX_INSTANCES))
    
    # اضافه کردن هدرهای شبیه‌ساز مرورگر
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        for instance in instances:
            try:
                url = f"{instance}/search"
                params = {
                    "q": search_query,
                    "categories": "images",
                    "format": "json",
                    "safesearch": "0"
                }
                
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        # غیرفعال کردن چک کردن نوع محتوا برای جلوگیری از خطای mimetype
                        try:
                            data = await resp.json(content_type=None)
                        except json.JSONDecodeError:
                            # اگر سرور به جای JSON فایل HTML فرستاد (بسته بودن API)، این سرور را رد کن
                            continue
                            
                        results = data.get('results', [])
                        if not results:
                            continue
                            
                        parsed_results = []
                        for i, item in enumerate(results[:limit], start=1):
                            original_url = item.get('img_src')
                            thumbnail_url = item.get('thumbnail_src') or original_url
                            
                            parsed_results.append({
                                'id': str(i),
                                'title': item.get('title', 'Pinterest Image'),
                                'thumbnail': thumbnail_url,
                                'original': original_url
                            })
                            
                        return parsed_results
                        
            except Exception as e:
                # نادیده گرفتن خطا و رفتن به سرور بعدی
                # print(f"Skipping {instance} due to error: {e}")
                continue
                
    return []
