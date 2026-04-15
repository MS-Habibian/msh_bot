import aiohttp
import urllib.parse
from typing import List, Dict

async def search_pinterest_async(query: str, limit: int = 10) -> List[Dict]:
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    
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
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=15) as response:
                print(f"[Pinterest] Status: {response.status}")
                text = await response.text()
                print(f"[Pinterest] Response preview: {text[:500]}")  # <-- اضافه کن
    except Exception as e:
        print(f"[Pinterest] Exception: {e}")
    
    return []


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

async def search_pinterest_rss(query: str, limit: int = 10) -> List[Dict]:
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    results = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=20) as response:
                print(f"[RSS] Status: {response.status}")
                html = await response.text()
                
                import re
                # Pinterest embeds image data in a JSON blob inside the HTML
                pattern = r'"images":\{"orig":\{"url":"([^"]+)"[^}]*\}[^}]*"236x":\{"url":"([^"]+)"'
                matches = re.findall(pattern, html)
                print(f"[RSS] Found {len(matches)} images")
                
                for i, (orig_url, thumb_url) in enumerate(matches[:limit], start=1):
                    results.append({
                        'id': str(i),
                        'title': f'Pinterest Image {i}',
                        'thumbnail': thumb_url.replace('\\/', '/'),
                        'original': orig_url.replace('\\/', '/')
                    })
                    
    except Exception as e:
        print(f"[RSS] Exception: {e}")
    
    return results

