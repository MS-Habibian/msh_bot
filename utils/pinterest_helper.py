import asyncio
# در نسخه جدید ممکن است نام ایمپورت همچنان duckduckgo_search باشد اما پکیج ddgs نصب شده است
from ddgs import DDGS

async def search_pinterest_async(query: str, limit: int = 10) -> list:
    """جستجوی تصاویر در پینترست با استفاده از داک‌داک‌گو"""
    # دقت کنید که کلمه /pin به اشتباه در کوئری شما ارسال شده بود، آن را تمیز می‌کنیم
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    
    def _search():
        # اگر سرور شما در دیتاسنتر معروفی است که بن شده (مثل هتزنر)، ممکن است به پروکسی نیاز داشته باشید:
        # proxy = "http://username:password@proxyserver:port"
        # with DDGS(proxy=proxy) as ddgs:
        with DDGS() as ddgs:
            # استفاده از پارامتر safesearch خاموش برای نتایج بهتر
            results = list(ddgs.images(search_query, max_results=limit, safesearch='off'))
            return results
            
    try:
        results = await asyncio.to_thread(_search)
        if not results:
            return []
            
        return [
            {
                'id': str(i),
                'title': item.get('title', 'Pinterest Image'),
                'thumbnail': item.get('thumbnail'),
                'original': item.get('image')
            }
            for i, item in enumerate(results, start=1)
        ]
    except Exception as e:
        print(f"Pinterest Search Error: {e}")
        return []
