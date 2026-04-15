import aiohttp
import random

# لیستی از سرورهای عمومی SearXNG که جستجوی عکس و خروجی JSON را پشتیبانی می‌کنند
SEARX_INSTANCES = [
    "https://searx.be",
    "https://searx.tiekoetter.com",
    "https://search.rowie.at",
    "https://searx.work"
]

async def search_pinterest_async(query: str, limit: int = 10) -> list:
    """جستجوی تصاویر با استفاده از موتورهای عمومی SearXNG برای دور زدن محدودیت IP"""
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    
    # سرورها را به صورت تصادفی مرتب می‌کنیم تا فشار روی یک سرور نیفتد
    instances = random.sample(SEARX_INSTANCES, len(SEARX_INSTANCES))
    
    async with aiohttp.ClientSession() as session:
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
                        data = await resp.json()
                        results = data.get('results', [])
                        
                        if not results:
                            continue # اگر نتیجه نداشت، سرور بعدی را امتحان کن
                            
                        parsed_results = []
                        for i, item in enumerate(results[:limit], start=1):
                            # استخراج لینک عکس و پیش‌نمایش
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
                print(f"SearXNG Error on {instance}: {e}")
                continue # در صورت بروز خطا، به سراغ سرور بعدی در لیست می‌رود
                
    return []
