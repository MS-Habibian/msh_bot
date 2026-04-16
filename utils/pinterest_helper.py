# import aiohttp
# import re
# from typing import List, Dict

# import urllib

# async def search_pinterest_rss(query: str, limit: int = 10) -> List[Dict]:
#     clean_query = query.replace('/pin', '').strip()
#     encoded_query = urllib.parse.quote(clean_query)
    
#     url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
#         'Accept': 'text/html,application/xhtml+xml',
#         'Accept-Language': 'en-US,en;q=0.9',
#     }
    
#     results = []
    
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, headers=headers, timeout=20) as response:
#                 html = await response.text()
                
#                 # Pinterest embeds data in a <script> tag with __PWS_DATA__
#                 # Extract the JSON data
#                 match = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>([^<]+)</script>', html)
                
#                 if match:
#                     import json
#                     json_text = match.group(1).strip()
#                     data = json.loads(json_text)
                    
#                     # Navigate through the nested structure
#                     props = data.get('props', {}).get('initialReduxState', {})
#                     pins_data = props.get('pins', {})
                    
#                     # Extract all pin objects
#                     pin_list = []
#                     for key, pin in pins_data.items():
#                         if isinstance(pin, dict) and 'images' in pin:
#                             pin_list.append(pin)
                    
#                     print(f"[Pinterest] Found {len(pin_list)} pins")
                    
#                     for i, pin in enumerate(pin_list[:limit], start=1):
#                         images = pin.get('images', {})
                        
#                         # Get best quality available
#                         original = images.get('orig', {}).get('url')
#                         if not original:
#                             original = images.get('736x', {}).get('url')
                        
#                         thumbnail = images.get('236x', {}).get('url', original)
                        
#                         if original:
#                             results.append({
#                                 'id': str(i),
#                                 'title': pin.get('grid_title', f'Pinterest Image {i}')[:100],
#                                 'thumbnail': thumbnail,
#                                 'original': original
#                             })
#                 else:
#                     print("[Pinterest] Could not find __PWS_DATA__ script tag")
                    
#     except Exception as e:
#         print(f"[Pinterest] Exception: {e}")
#         import traceback
#         traceback.print_exc()
    
#     return results
import aiohttp
import json

import urllib

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
