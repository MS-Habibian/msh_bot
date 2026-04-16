import http
import aiohttp
import re
from typing import List, Dict
import urllib.parse


def load_cookies(cookie_file: str) -> dict:
    """Load cookies from Netscape format file"""
    jar = http.cookiejar.MozillaCookieJar()
    jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
    cookies = {}
    for cookie in jar:
        if 'pinterest' in cookie.domain:
            cookies[cookie.name] = cookie.value
    print(f"[Pinterest] Loaded {len(cookies)} cookies")
    return cookies

async def search_pinterest_rss(query: str, limit: int = 10) -> List[Dict]:
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    
    # Pinterest's internal search API
    url = (
        f"https://www.pinterest.com/resource/BaseSearchResource/get/"
        f"?source_url=/search/pins/?q={encoded_query}"
        f"&data=%7B%22options%22%3A%7B%22query%22%3A%22{encoded_query}%22%2C"
        f"%22scope%22%3A%22pins%22%2C%22page_size%22%3A{limit}%7D%7D"
    )
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'application/json, text/javascript, */*, q=0.01',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'X-APP-VERSION': 'a90ce93d',
        'X-Pinterest-AppState': 'active',
        'Referer': f'https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    
    results = []
    
    try:
        cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
        print(f"[Pinterest] Loaded {len(cookies)} cookies")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
            async with session.get(url, headers=headers, timeout=20) as response:
                print(f"[Pinterest] API Status: {response.status}")
                
                if response.status != 200:
                    print(f"[Pinterest] Bad status, falling back to HTML method")
                    return await _search_pinterest_html(query, limit, cookies)
                
                import json
                data = await response.json()
                
                # ذخیره برای دیباگ
                with open('/tmp/pinterest_api_debug.json', 'w') as f:
                    json.dump(data, f, indent=2)
                print("[Pinterest] API response saved to /tmp/pinterest_api_debug.json")
                
                pins = data.get('resource_response', {}).get('data', {}).get('results', [])
                print(f"[Pinterest] Found {len(pins)} pins from API")
                
                for i, pin in enumerate(pins[:limit], start=1):
                    try:
                        pin_id = pin.get('id', '')
                        description = pin.get('description', '') or pin.get('grid_description', '') or ''
                        pin_url = f"https://www.pinterest.com/pin/{pin_id}/"
                        
                        # نام نویسنده
                        pinner = pin.get('pinner', {}) or {}
                        author = pinner.get('full_name', '') or pinner.get('username', '')
                        
                        # لینک سایت منبع
                        domain = pin.get('domain', '')
                        link = pin.get('link', '')
                        
                        # تصویر
                        images = pin.get('images', {}) or {}
                        orig = images.get('orig', {}) or {}
                        img_url = orig.get('url', '')
                        
                        if not img_url:
                            # fallback به هر سایز موجود
                            for size in ['736x', '474x', '236x']:
                                sized = images.get(size, {}) or {}
                                img_url = sized.get('url', '')
                                if img_url:
                                    break
                        
                        if img_url and pin_id:
                            thumb_url = re.sub(r'/\d+x/', '/236x/', img_url)
                            
                            results.append({
                                'id': str(i),
                                'pin_id': pin_id,
                                'title': description[:100] if description else f'Pinterest Image {i}',
                                'description': description,
                                'author': author,
                                'domain': domain,
                                'link': link,
                                'url': pin_url,
                                'thumbnail': thumb_url,
                                'original': img_url
                            })
                            print(f"[Pinterest] Pin {i}: {pin_id} | author={author} | desc={description[:50]}")
                    
                    except Exception as e:
                        print(f"[Pinterest] Error parsing pin {i}: {e}")
                        continue
                
    except Exception as e:
        print(f"[Pinterest] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return results


async def _search_pinterest_html(query: str, limit: int, cookies: dict) -> List[Dict]:
    """fallback روش قدیمی regex"""
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.pinterest.com/',
    }
    
    results = []
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        async with session.get(url, headers=headers, timeout=20) as response:
            html = await response.text()
            image_pattern = r'https://i\.pinimg\.com/[^"\'>\s]+'
            all_images = re.findall(image_pattern, html)
            
            seen = set()
            unique_images = []
            for img_url in all_images:
                match = re.search(r'/([a-f0-9]{32,})\.(jpg|png|gif)', img_url)
                if match:
                    img_id = match.group(1)
                    if img_id not in seen and len(img_id) >= 32:
                        seen.add(img_id)
                        original_url = f"https://i.pinimg.com/originals/{img_id[:2]}/{img_id[2:4]}/{img_id[4:6]}/{img_id}.jpg"
                        thumb_url = f"https://i.pinimg.com/236x/{img_id[:2]}/{img_id[2:4]}/{img_id[4:6]}/{img_id}.jpg"
                        unique_images.append((thumb_url, original_url))
            
            for i, (thumb_url, orig_url) in enumerate(unique_images[:limit], start=1):
                results.append({
                    'id': str(i),
                    'pin_id': '',
                    'title': f'Pinterest Image {i}',
                    'description': '',
                    'author': '',
                    'domain': '',
                    'link': '',
                    'url': '',
                    'thumbnail': thumb_url,
                    'original': orig_url
                })
    
    print(f"[Pinterest] HTML fallback returned {len(results)} results")
    return results
