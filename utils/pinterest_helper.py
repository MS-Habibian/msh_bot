import aiohttp
import re
from typing import List, Dict

import urllib

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
                html = await response.text()
                
                # Pinterest embeds data in a <script> tag with __PWS_DATA__
                # Extract the JSON data
                match = re.search(r'<script[^>]*id="__PWS_DATA__"[^>]*>([^<]+)</script>', html)
                
                if match:
                    import json
                    json_text = match.group(1).strip()
                    data = json.loads(json_text)
                    
                    # Navigate through the nested structure
                    props = data.get('props', {}).get('initialReduxState', {})
                    pins_data = props.get('pins', {})
                    
                    # Extract all pin objects
                    pin_list = []
                    for key, pin in pins_data.items():
                        if isinstance(pin, dict) and 'images' in pin:
                            pin_list.append(pin)
                    
                    print(f"[Pinterest] Found {len(pin_list)} pins")
                    
                    for i, pin in enumerate(pin_list[:limit], start=1):
                        images = pin.get('images', {})
                        
                        # Get best quality available
                        original = images.get('orig', {}).get('url')
                        if not original:
                            original = images.get('736x', {}).get('url')
                        
                        thumbnail = images.get('236x', {}).get('url', original)
                        
                        if original:
                            results.append({
                                'id': str(i),
                                'title': pin.get('grid_title', f'Pinterest Image {i}')[:100],
                                'thumbnail': thumbnail,
                                'original': original
                            })
                else:
                    print("[Pinterest] Could not find __PWS_DATA__ script tag")
                    
    except Exception as e:
        print(f"[Pinterest] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return results
