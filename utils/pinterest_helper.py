import aiohttp
import re
import json
from typing import List, Dict
import urllib.parse


from handlers.pinterest import load_cookies

# async def search_pinterest_rss(query: str, limit: int = 10) -> List[Dict]:
#     clean_query = query.replace('/pin', '').strip()
#     encoded_query = urllib.parse.quote(clean_query)
    
#     url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
#         'Accept-Language': 'en-US,en;q=0.5',
#         'Accept-Encoding': 'gzip, deflate, br',
#         'DNT': '1',
#         'Connection': 'keep-alive',
#         'Upgrade-Insecure-Requests': '1',
#         'Sec-Fetch-Dest': 'document',
#         'Sec-Fetch-Mode': 'navigate',
#         'Sec-Fetch-Site': 'none',
#         'Cache-Control': 'max-age=0',
#     }
    
#     results = []
    
#     try:
#         cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
        
#         connector = aiohttp.TCPConnector(ssl=False)
#         async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#             async with session.get(url, headers=headers, timeout=20) as response:
#                 print(f"[Pinterest] Status: {response.status}")
#                 html = await response.text()
#                 print(f"[Pinterest] HTML size: {len(html)} bytes")
                
#                 # ذخیره HTML برای بررسی
#                 with open('/tmp/pinterest_debug.html', 'w', encoding='utf-8') as f:
#                     f.write(html)
#                 print("[Pinterest] HTML saved to /tmp/pinterest_debug.html")
                
#                 # جستجوی JSON data
#                 json_pattern = r'<script id="__PWS_DATA__" type="application/json">({.*?})</script>'
#                 json_match = re.search(json_pattern, html, re.DOTALL)
                
#                 if json_match:
#                     print("[Pinterest] Found __PWS_DATA__ script tag")
#                 else:
#                     print("[Pinterest] __PWS_DATA__ NOT FOUND")
#                     # جستجوی سایر script tagها
#                     if 'window.__INITIAL_STATE__' in html:
#                         print("[Pinterest] Found window.__INITIAL_STATE__")
#                     if 'window.__PWS_DATA__' in html:
#                         print("[Pinterest] Found window.__PWS_DATA__")
                    
#                     # نمایش اول 3000 کاراکتر
#                     print(f"[Pinterest] HTML start:\n{html[:3000]}")
                
#     except Exception as e:
#         print(f"[Pinterest] Exception: {e}")
#         import traceback
#         traceback.print_exc()
    
#     return results

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





async def debug_pinterest(query: str):
    """
    کد دیباگ برای دیدن ساختار دقیق پاسخ Pinterest
    """
    clean_query = query.replace('/pin', '').strip()
    encoded_query = urllib.parse.quote(clean_query)
    
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=20) as response:
                print(f"\n{'='*60}")
                print(f"Status Code: {response.status}")
                print(f"{'='*60}\n")
                
                html = await response.text()
                
                # ذخیره HTML کامل
                with open("pinterest_full.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"✅ HTML saved to pinterest_full.html (size: {len(html)} bytes)\n")
                
                # جستجوی تگ script
                import re
                script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
                print(f"Found {len(script_tags)} script tags\n")
                
                # پیدا کردن __PWS_DATA__
                pws_match = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>([^<]+)</script>', html)
                if pws_match:
                    print("✅ Found __PWS_DATA__ tag")
                    json_text = pws_match.group(1).strip()
                    
                    # ذخیره JSON
                    with open("pinterest_data.json", "w", encoding="utf-8") as f:
                        f.write(json_text)
                    print(f"✅ JSON saved to pinterest_data.json (size: {len(json_text)} bytes)\n")
                    
                    # تلاش برای parse کردن
                    try:
                        data = json.loads(json_text)
                        print("✅ JSON parsed successfully")
                        print(f"Top-level keys: {list(data.keys())}\n")
                        
                        # بررسی ساختار
                        if 'props' in data:
                            print("✅ 'props' key exists")
                            props = data['props']
                            print(f"Props keys: {list(props.keys())}\n")
                            
                            if 'initialReduxState' in props:
                                print("✅ 'initialReduxState' key exists")
                                redux = props['initialReduxState']
                                print(f"Redux keys: {list(redux.keys())}\n")
                                
                                if 'pins' in redux:
                                    pins = redux['pins']
                                    print(f"✅ 'pins' key exists with {len(pins)} items")
                                    print(f"Sample pin keys: {list(list(pins.values())[0].keys()) if pins else 'empty'}\n")
                                else:
                                    print("❌ 'pins' key NOT found in redux")
                                    print(f"Available keys: {list(redux.keys())}\n")
                            else:
                                print("❌ 'initialReduxState' key NOT found")
                        else:
                            print("❌ 'props' key NOT found")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parse error: {e}\n")
                        print(f"First 500 chars of JSON:\n{json_text[:500]}\n")
                else:
                    print("❌ __PWS_DATA__ tag NOT found")
                    
                    # جستجوی الگوهای دیگر
                    print("\nSearching for alternative patterns...")
                    
                    # الگوی 1: window.__PWS_DATA__
                    window_pws = re.search(r'window\.__PWS_DATA__\s*=\s*({.+?});', html, re.DOTALL)
                    if window_pws:
                        print("✅ Found window.__PWS_DATA__ pattern")
                    
                    # الگوی 2: JSON در script بدون id
                    json_scripts = re.findall(r'<script[^>]*>(\s*{[^<]+})\s*</script>', html)
                    print(f"Found {len(json_scripts)} potential JSON scripts")
                    
                    # الگوی 3: pinimg URLs
                    pinimg_urls = re.findall(r'"(https://i\.pinimg\.com/[^"]+)"', html)
                    print(f"Found {len(set(pinimg_urls))} unique pinimg URLs")
                    if pinimg_urls:
                        print(f"Sample: {pinimg_urls[0][:100]}")
                
                print(f"\n{'='*60}\n")
                
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()
