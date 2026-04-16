import aiohttp
import re
import http.cookiejar
from typing import List, Dict
import urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes

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
    
    url = f"https://www.pinterest.com/search/pins/?q={encoded_query}&rs=typed"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    results = []
    
    try:
        # بارگذاری کوکی‌ها
        cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
            async with session.get(url, headers=headers, timeout=20) as response:
                print(f"[Pinterest] Status: {response.status}")
                html = await response.text()
                print(f"[Pinterest] HTML size: {len(html)} bytes")
                
                # استخراج تمام URLهای تصویر
                image_pattern = r'https://i\.pinimg\.com/[^"\'>\s]+'
                all_images = re.findall(image_pattern, html)
                
                # حذف تکراری‌ها
                unique_images = []
                seen = set()
                
                for img_url in all_images:
                    # استخراج ID یکتا
                    match = re.search(r'/([a-f0-9]{32,})\.(jpg|png|gif)', img_url)
                    if match:
                        img_id = match.group(1)
                        if img_id not in seen and len(img_id) >= 32:
                            seen.add(img_id)
                            # ساخت URL با کیفیت بالا
                            original_url = f"https://i.pinimg.com/originals/{img_id[:2]}/{img_id[2:4]}/{img_id[4:6]}/{img_id}.jpg"
                            thumb_url = f"https://i.pinimg.com/236x/{img_id[:2]}/{img_id[2:4]}/{img_id[4:6]}/{img_id}.jpg"
                            unique_images.append((thumb_url, original_url))
                
                print(f"[Pinterest] Found {len(unique_images)} unique images")
                
                for i, (thumb_url, orig_url) in enumerate(unique_images[:limit], start=1):
                    results.append({
                        'id': str(i),
                        'title': f'Pinterest Image {i}',
                        'thumbnail': thumb_url,
                        'original': orig_url
                    })
                
                print(f"[Pinterest] Returning {len(results)} results")
                    
    except Exception as e:
        print(f"[Pinterest] Exception: {e}")
        import traceback
        traceback.print_exc()
    
    return results


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفاً یک عبارت برای جستجو وارد کنید.\nمثال: `/pin cats`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    processing_msg = await update.message.reply_text(f"🔍 در حال جستجوی تصاویر برای '{query}'...")

    results = await search_pinterest_rss(query, limit=10)

    if not results:
        await processing_msg.edit_text("❌ نتیجه‌ای یافت نشد. لطفاً دوباره تلاش کنید.")
        return

    context.user_data['pin_results'] = results

    cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'image/avif,image/webp,*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.pinterest.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    await processing_msg.delete()

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
        for item in results:
            try:
                async with session.get(item['thumbnail'], headers=headers, timeout=15) as img_response:
                    print(f"[Pinterest] Image {item['id']} status: {img_response.status}")
                    if img_response.status == 200:
                        img_bytes = await img_response.read()
                        
                        # دکمه دانلود برای هر تصویر
                        keyboard = [[InlineKeyboardButton(
                            text=f"📥 دانلود کیفیت اصلی",
                            callback_data=f"pindl_{item['id']}"
                        )]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # ارسال تک‌تک با شماره
                        await update.message.reply_photo(
                            photo=img_bytes,
                            caption=f"🖼 تصویر شماره {item['id']}",
                            reply_markup=reply_markup
                        )
                        
                        print(f"[Pinterest] Sent image {item['id']} ({len(img_bytes)} bytes)")
                    else:
                        print(f"[Pinterest] Failed to download image {item['id']}: {img_response.status}")
            except Exception as e:
                print(f"[Pinterest] Error downloading image {item['id']}: {e}")
                continue
# async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if not context.args:
#         await update.message.reply_text("لطفاً یک عبارت برای جستجو وارد کنید.\nمثال: `/pin cats`", parse_mode="Markdown")
#         return

#     query = " ".join(context.args)
#     processing_msg = await update.message.reply_text(f"🔍 در حال جستجوی تصاویر برای '{query}'...")

#     results = await search_pinterest_rss(query, limit=10)

#     if not results:
#         await processing_msg.edit_text("❌ نتیجه‌ای یافت نشد. لطفاً دوباره تلاش کنید.")
#         return

#     context.user_data['pin_results'] = results

#     # بارگذاری کوکی‌ها برای دانلود تصاویر
#     cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
    
#     # دانلود تصاویر با هدرهای کامل
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'image/avif,image/webp,*/*',
#         'Accept-Language': 'en-US,en;q=0.5',
#         'Accept-Encoding': 'gzip, deflate, br',
#         'Referer': 'https://www.pinterest.com/',
#         'DNT': '1',
#         'Connection': 'keep-alive',
#         'Sec-Fetch-Dest': 'image',
#         'Sec-Fetch-Mode': 'no-cors',
#         'Sec-Fetch-Site': 'cross-site',
#     }

#     media_group = []
#     keyboard = []
#     row = []

#     connector = aiohttp.TCPConnector(ssl=False)
#     async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#         for item in results:
#             try:
#                 async with session.get(item['thumbnail'], headers=headers, timeout=15) as img_response:
#                     print(f"[Pinterest] Image {item['id']} status: {img_response.status}")
#                     if img_response.status == 200:
#                         img_bytes = await img_response.read()
#                         media_group.append(InputMediaPhoto(media=img_bytes))
                        
#                         btn = InlineKeyboardButton(text=item['id'], callback_data=f"pindl_{item['id']}")
#                         row.append(btn)
#                         if len(row) == 5:
#                             keyboard.append(row)
#                             row = []
                        
#                         print(f"[Pinterest] Downloaded image {item['id']} ({len(img_bytes)} bytes)")
#                     else:
#                         print(f"[Pinterest] Failed to download image {item['id']}: {img_response.status}")
#             except Exception as e:
#                 print(f"[Pinterest] Error downloading image {item['id']}: {e}")
#                 continue

#     if row:
#         keyboard.append(row)

#     if not media_group:
#         await processing_msg.edit_text("❌ خطا در بارگذاری تصاویر.")
#         return

#     await processing_msg.delete()
#     await update.message.reply_media_group(media=media_group)

#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await update.message.reply_text(
#         "👇 برای دانلود عکس با کیفیت اصلی، شماره آن را انتخاب کنید:",
#         reply_markup=reply_markup
#     )


async def pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pin_id = query.data.replace("pindl_", "")
    results = context.user_data.get('pin_results', [])

    selected = next((item for item in results if item['id'] == pin_id), None)
    if not selected:
        await query.edit_message_text("❌ خطا: تصویر یافت نشد.")
        return

    await query.message.reply_text(f"⏳ در حال دانلود تصویر شماره {pin_id}...")

    # بارگذاری کوکی‌ها
    cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'image/avif,image/webp,*/*',
        'Referer': 'https://www.pinterest.com/',
        'DNT': '1',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
            async with session.get(selected['original'], headers=headers, timeout=20) as response:
                if response.status == 200:
                    img_bytes = await response.read()
                    await query.message.reply_photo(photo=img_bytes, caption=f"✅ تصویر شماره {pin_id}")
                else:
                    await query.message.reply_text(f"❌ خطا در دانلود: {response.status}")
    except Exception as e:
        await query.message.reply_text(f"❌ خطا: {str(e)}")


async def pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pin_id = query.data.replace("pindl_", "")
    results = context.user_data.get('pin_results', [])

    selected = next((item for item in results if item['id'] == pin_id), None)
    if not selected:
        await query.message.reply_text("❌ خطا: تصویر یافت نشد.")
        return

    status_msg = await query.message.reply_text(f"⏳ در حال دانلود تصویر شماره {pin_id}...")

    cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Accept': 'image/avif,image/webp,*/*',
        'Referer': 'https://www.pinterest.com/',
        'DNT': '1',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
            # اول original را امتحان کن
            async with session.get(selected['original'], headers=headers, timeout=20) as response:
                print(f"[Pinterest] Download original status: {response.status}")
                if response.status == 200:
                    img_bytes = await response.read()
                    await status_msg.delete()
                    await query.message.reply_document(
                        document=img_bytes,
                        filename=f"pinterest_{pin_id}.jpg",
                        caption=f"✅ تصویر شماره {pin_id} - کیفیت اصلی"
                    )
                    return

                # اگر original 403 داد، thumbnail را بفرست
                print(f"[Pinterest] Original failed, trying thumbnail...")
                async with session.get(selected['thumbnail'], headers=headers, timeout=20) as fallback:
                    if fallback.status == 200:
                        img_bytes = await fallback.read()
                        await status_msg.delete()
                        await query.message.reply_document(
                            document=img_bytes,
                            filename=f"pinterest_{pin_id}.jpg",
                            caption=f"✅ تصویر شماره {pin_id}"
                        )
                    else:
                        await status_msg.edit_text(f"❌ خطا در دانلود تصویر: {fallback.status}")

    except Exception as e:
        print(f"[Pinterest] Download error: {e}")
        await status_msg.edit_text(f"❌ خطا: {str(e)}")
