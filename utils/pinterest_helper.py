import http
import json
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


# async def _search_pinterest_html(query: str, limit: int, cookies: dict) -> List[Dict]:
#     """Fallback: parse initial Redux state from HTML"""
#     clean_query = query.replace('/pin', '').strip()
#     encoded_query = urllib.parse.quote(clean_query)
#     url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#         'Referer': 'https://www.pinterest.com/',
#     }
    
#     results = []
#     connector = aiohttp.TCPConnector(ssl=False)
#     async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#         async with session.get(url, headers=headers, timeout=20) as response:
#             html = await response.text()
            
#             # Try to find Redux state with pins
#             patterns = [
#                 r'<script[^>]*id="__PWS_DATA__"[^>]*>(.*?)</script>',
#                 r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?});</script>',
#                 r'"resource_response":\s*({.*?"data".*?})',
#             ]
            
#             for pattern in patterns:
#                 match = re.search(pattern, html, re.DOTALL)
#                 if match:
#                     try:
#                         data = json.loads(match.group(1))
                        
#                         # Try different paths to find pins
#                         pin_sources = [
#                             data.get('props', {}).get('initialReduxState', {}).get('pins', {}),
#                             data.get('initialReduxState', {}).get('pins', {}),
#                             data.get('resourceResponses', [{}])[0].get('response', {}).get('data', {}).get('results', []),
#                             data.get('data', {}).get('results', []),
#                         ]
                        
#                         for pins_data in pin_sources:
#                             if isinstance(pins_data, dict):
#                                 # pins is a dict of pin_id -> pin_data
#                                 for i, (pin_id, pin) in enumerate(list(pins_data.items())[:limit], start=1):
#                                     if not isinstance(pin, dict):
#                                         continue
#                                     result = _extract_pin_data(pin, pin_id, i)
#                                     if result:
#                                         results.append(result)
#                             elif isinstance(pins_data, list):
#                                 # pins is a list
#                                 for i, pin in enumerate(pins_data[:limit], start=1):
#                                     if not isinstance(pin, dict):
#                                         continue
#                                     pin_id = pin.get('id', str(i))
#                                     result = _extract_pin_data(pin, pin_id, i)
#                                     if result:
#                                         results.append(result)
                            
#                             if results:
#                                 print(f"[Pinterest] Found {len(results)} pins in HTML")
#                                 return results
                    
#                     except Exception as e:
#                         print(f"[Pinterest] Error parsing pattern: {e}")
#                         continue
            
#             # Final fallback: regex scraping
#             print("[Pinterest] All JSON parsing failed, using regex")
#             img_urls = re.findall(r'https://i\.pinimg\.com/originals/[a-f0-9]{2}/[a-f0-9]{2}/[a-f0-9]{2}/[a-f0-9]+\.(?:jpg|png|gif)', html)
            
#             for i, img_url in enumerate(img_urls[:limit], start=1):
#                 thumb_url = re.sub(r'/originals/', '/236x/', img_url)
#                 results.append({
#                     'id': str(i),
#                     'pin_id': '',
#                     'title': f'Pinterest Image {i}',
#                     'description': '',
#                     'author': '',
#                     'domain': '',
#                     'link': '',
#                     'url': '',
#                     'thumbnail': thumb_url,
#                     'original': img_url
#                 })
    
#     print(f"[Pinterest] HTML fallback returned {len(results)} results")
#     return results

async def _search_pinterest_html(query: str, limit: int, cookies: dict) -> List[Dict]:
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.pinterest.com/',
    }
    
    results = []
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        async with session.get(url, headers=headers, timeout=20) as response:
            html = await response.text()
            
            # Only parse __PWS_DATA__ — other patterns grab broken JSON
            match = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    
                    # Save for debugging
                    with open('/tmp/pinterest_pws_debug.json', 'w') as f:
                        json.dump(data, f, indent=2)
                    
                    # Print top-level keys to find where pins are
                    print(f"[Pinterest] __PWS_DATA__ top keys: {list(data.keys())}")
                    
                    props = data.get('props', {})
                    print(f"[Pinterest] props keys: {list(props.keys())}")
                    
                    redux = props.get('initialReduxState', {})
                    print(f"[Pinterest] redux keys: {list(redux.keys())}")
                    
                    pins_data = redux.get('pins', {})
                    print(f"[Pinterest] pins count: {len(pins_data)}")
                    
                    for i, (pin_id, pin) in enumerate(list(pins_data.items())[:limit], start=1):
                        if not isinstance(pin, dict):
                            continue
                        result = _extract_pin_data(pin, pin_id, i)
                        if result:
                            results.append(result)
                    
                    if results:
                        print(f"[Pinterest] Got {len(results)} pins from __PWS_DATA__")
                        return results
                    else:
                        print(f"[Pinterest] __PWS_DATA__ parsed OK but no pins found")
                
                except json.JSONDecodeError as e:
                    print(f"[Pinterest] __PWS_DATA__ JSON error: {e}")
            else:
                print("[Pinterest] __PWS_DATA__ tag not found in HTML")
            
            # Regex fallback
            print("[Pinterest] Using regex fallback")
            img_urls = re.findall(
                r'https://i\.pinimg\.com/originals/[a-f0-9]{2}/[a-f0-9]{2}/[a-f0-9]{2}/[a-f0-9]+\.(?:jpg|png|gif)',
                html
            )
            for i, img_url in enumerate(img_urls[:limit], start=1):
                thumb_url = re.sub(r'/originals/', '/236x/', img_url)
                results.append({
                    'id': str(i), 'pin_id': '', 'title': f'Pinterest Image {i}',
                    'description': '', 'author': '', 'domain': '', 'link': '',
                    'url': '', 'thumbnail': thumb_url, 'original': img_url
                })
    
    print(f"[Pinterest] HTML fallback returned {len(results)} results")
    return results


def _extract_pin_data(pin: dict, pin_id: str, index: int) -> dict:
    """Extract pin data from various Pinterest JSON structures"""
    images = pin.get('images', {}) or {}
    orig = images.get('orig', {}) or images.get('originals', {}) or {}
    img_url = orig.get('url', '') or pin.get('image_large_url', '')
    
    if not img_url:
        return None
    
    description = pin.get('description', '') or pin.get('grid_description', '') or pin.get('rich_summary', {}).get('display_description', '') or ''
    pinner = pin.get('pinner', {}) or {}
    author = pinner.get('full_name', '') or pinner.get('username', '') or pin.get('attribution', {}).get('author_name', '')
    domain = pin.get('domain', '') or pin.get('rich_summary', {}).get('display_name', '')
    link = pin.get('link', '') or pin.get('rich_summary', {}).get('url', '')
    
    thumb_url = re.sub(r'/originals/', '/236x/', img_url)
    
    return {
        'id': str(index),
        'pin_id': pin_id,
        'title': description[:100] if description else f'Pinterest Image {index}',
        'description': description,
        'author': author,
        'domain': domain,
        'link': link,
        'url': f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else '',
        'thumbnail': thumb_url,
        'original': img_url
    }