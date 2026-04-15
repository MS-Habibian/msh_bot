import aiohttp
import urllib.parse
from typing import List, Dict

async def search_pinterest_async(query: str, limit: int = 10) -> List[Dict]:
    """
    جستجوی تصاویر Pinterest با استفاده از API عمومی
    """
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    
    # استفاده از endpoint عمومی Pinterest
    url = f"https://www.pinterest.com/resource/BaseSearchResource/get/"
    
    params = {
        'source_url': f'/search/pins/?q={encoded_query}',
        'data': '{"options":{"query":"' + clean_query + '","scope":"pins"},"context":{}}'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # استخراج پین‌ها از پاسخ
                    pins = data.get('resource_response', {}).get('data', {}).get('results', [])
                    
                    for i, pin in enumerate(pins[:limit], start=1):
                        images = pin.get('images', {})
                        
                        # انتخاب بهترین کیفیت موجود
                        original = images.get('orig', {}).get('url')
                        if not original:
                            original = images.get('736x', {}).get('url')
                        if not original:
                            original = images.get('564x', {}).get('url')
                        
                        thumbnail = images.get('236x', {}).get('url', original)
                        
                        if original:
                            results.append({
                                'id': str(i),
                                'title': pin.get('grid_title', f'Pinterest Image {i}')[:100],
                                'thumbnail': thumbnail,
                                'original': original,
                                'pin_url': f"https://pinterest.com/pin/{pin.get('id', '')}"
                            })
                            
    except Exception as e:
        print(f"Pinterest Search Error: {e}")
    
    return results


async def search_pinterest_google(query: str, limit: int = 10) -> List[Dict]:
    """
    جستجوی تصاویر Pinterest از طریق Google Images
    """
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    encoded_query = urllib.parse.quote(search_query)
    
    url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # استخراج URL های تصاویر از HTML
                    import re
                    pattern = r'"(https://i\.pinimg\.com/[^"]+)"'
                    matches = re.findall(pattern, html)
                    
                    unique_urls = list(dict.fromkeys(matches))
                    
                    for i, img_url in enumerate(unique_urls[:limit], start=1):
                        # تبدیل به کیفیت بالاتر
                        original = img_url.replace('/236x/', '/originals/')
                        
                        results.append({
                            'id': str(i),
                            'title': f'Pinterest Image {i}',
                            'thumbnail': img_url,
                            'original': original
                        })
                        
    except Exception as e:
        print(f"Google Pinterest Search Error: {e}")
    
    return results
