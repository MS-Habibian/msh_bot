import asyncio
from duckduckgo_search import DDGS

async def search_pinterest_async(query: str, limit: int = 10) -> list:
    """جستجوی تصاویر در پینترست با استفاده از داک‌داک‌گو"""
    # Adding site:pinterest.com ensures we only get Pinterest images
    search_query = f"{query} site:pinterest.com"
    
    def _search():
        with DDGS() as ddgs:
            results = list(ddgs.images(search_query, max_results=limit))
            return results
            
    try:
        results = await asyncio.to_thread(_search)
        # return a cleaned list of dicts with thumbnail and original url
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
