# import aiohttp
# import http.cookiejar
# from typing import List, Dict
# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import ContextTypes
# from utils.pinterest_helper import search_pinterest_rss, load_cookies

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

#     cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'application/json, text/javascript, */*, q=0.01',
#         'Accept-Language': 'en-US,en;q=0.5',
#         'Accept-Encoding': 'gzip, deflate, br',
#         'X-Requested-With': 'XMLHttpRequest',
#         'X-APP-VERSION': 'cb1c7f9',  # Update this - check network tab in browser
#         'X-Pinterest-AppState': 'active',
#         'X-CSRFToken': cookies.get('csrftoken', ''),  # Add CSRF token from cookies
#         'Referer': f'https://www.pinterest.com/search/pins/?q={query}&rs=typed',
#         'Origin': 'https://www.pinterest.com',
#         'DNT': '1',
#         'Connection': 'keep-alive',
#         'Sec-Fetch-Dest': 'empty',
#         'Sec-Fetch-Mode': 'cors',
#         'Sec-Fetch-Site': 'same-origin',
#         'TE': 'trailers',
#     }

#     await processing_msg.delete()

#     connector = aiohttp.TCPConnector(ssl=False)
#     async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#         for item in results:
#             try:
#                 async with session.get(item['thumbnail'], headers=headers, timeout=15) as img_response:
#                     print(f"[Pinterest] Image {item['id']} status: {img_response.status}")
#                     if img_response.status == 200:
#                         img_bytes = await img_response.read()
                        
#                         keyboard = [[InlineKeyboardButton(
#                             text=f"📥 دانلود کیفیت اصلی",
#                             callback_data=f"pindl_{item['id']}"
#                         )]]
#                         reply_markup = InlineKeyboardMarkup(keyboard)
                        
#                         # ساخت caption با توضیحات و لینک
#                         caption = f"🖼 تصویر شماره {item['id']}\n"
#                         if item.get('description'):
#                             caption += f"\n📝 {item['description'][:200]}\n"
#                         if item.get('author'):
#                             caption += f"\n👤 {item['author']}\n"
#                         if item.get('domain'):
#                             caption += f"🌐 {item['domain']}\n"
#                         if item.get('link'):
#                             caption += f"🔗 {item['link']}\n"
#                         elif item.get('url'):
#                             caption += f"🔗 {item['url']}\n"
                        
#                         await update.message.reply_photo(
#                             photo=img_bytes,
#                             caption=caption,
#                             reply_markup=reply_markup
#                         )
                        
#                         print(f"[Pinterest] Sent image {item['id']} ({len(img_bytes)} bytes)")
#                     else:
#                         print(f"[Pinterest] Failed to download image {item['id']}: {img_response.status}")
#             except Exception as e:
#                 print(f"[Pinterest] Error downloading image {item['id']}: {e}")
#                 continue



# async def pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     pin_id = query.data.replace("pindl_", "")
#     results = context.user_data.get('pin_results', [])

#     selected = next((item for item in results if item['id'] == pin_id), None)
#     if not selected:
#         await query.edit_message_text("❌ خطا: تصویر یافت نشد.")
#         return

#     await query.message.reply_text(f"⏳ در حال دانلود تصویر شماره {pin_id}...")

#     # بارگذاری کوکی‌ها
#     cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')
    
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'image/avif,image/webp,*/*',
#         'Referer': 'https://www.pinterest.com/',
#         'DNT': '1',
#         'Sec-Fetch-Dest': 'image',
#         'Sec-Fetch-Mode': 'no-cors',
#         'Sec-Fetch-Site': 'cross-site',
#     }

#     try:
#         connector = aiohttp.TCPConnector(ssl=False)
#         async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#             async with session.get(selected['original'], headers=headers, timeout=20) as response:
#                 if response.status == 200:
#                     img_bytes = await response.read()
#                     await query.message.reply_photo(photo=img_bytes, caption=f"✅ تصویر شماره {pin_id}")
#                 else:
#                     await query.message.reply_text(f"❌ خطا در دانلود: {response.status}")
#     except Exception as e:
#         await query.message.reply_text(f"❌ خطا: {str(e)}")


# async def pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()

#     pin_id = query.data.replace("pindl_", "")
#     results = context.user_data.get('pin_results', [])

#     selected = next((item for item in results if item['id'] == pin_id), None)
#     if not selected:
#         await query.message.reply_text("❌ خطا: تصویر یافت نشد.")
#         return

#     status_msg = await query.message.reply_text(f"⏳ در حال دانلود تصویر شماره {pin_id}...")

#     cookies = load_cookies('/root/msh_bot/pinterest_cookies.txt')

#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
#         'Accept': 'image/avif,image/webp,*/*',
#         'Referer': 'https://www.pinterest.com/',
#         'DNT': '1',
#         'Sec-Fetch-Dest': 'image',
#         'Sec-Fetch-Mode': 'no-cors',
#         'Sec-Fetch-Site': 'cross-site',
#     }

#     try:
#         connector = aiohttp.TCPConnector(ssl=False)
#         async with aiohttp.ClientSession(cookies=cookies, connector=connector) as session:
#             # اول original را امتحان کن
#             async with session.get(selected['original'], headers=headers, timeout=20) as response:
#                 print(f"[Pinterest] Download original status: {response.status}")
#                 if response.status == 200:
#                     img_bytes = await response.read()
#                     await status_msg.delete()
#                     await query.message.reply_document(
#                         document=img_bytes,
#                         filename=f"pinterest_{pin_id}.jpg",
#                         caption=f"✅ تصویر شماره {pin_id} - کیفیت اصلی"
#                     )
#                     return

#                 # اگر original 403 داد، thumbnail را بفرست
#                 print(f"[Pinterest] Original failed, trying thumbnail...")
#                 async with session.get(selected['thumbnail'], headers=headers, timeout=20) as fallback:
#                     if fallback.status == 200:
#                         img_bytes = await fallback.read()
#                         await status_msg.delete()
#                         await query.message.reply_document(
#                             document=img_bytes,
#                             filename=f"pinterest_{pin_id}.jpg",
#                             caption=f"✅ تصویر شماره {pin_id}"
#                         )
#                     else:
#                         await status_msg.edit_text(f"❌ خطا در دانلود تصویر: {fallback.status}")

#     except Exception as e:
#         print(f"[Pinterest] Download error: {e}")
#         await status_msg.edit_text(f"❌ خطا: {str(e)}")
import os
import logging
import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.pinterest_helper import load_cookies, search_pinterest_rss
from utils.download_helper import download_file_async, split_file

logger = logging.getLogger(__name__)

async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """جستجوی تصاویر در پینترست"""
    if not context.args:
        await update.message.reply_text(
            "لطفاً یک کلمه کلیدی برای جستجو وارد کنید.\\nمثال: `/pin nature`", 
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"🔍 در حال جستجوی پینترست برای: {query}...")

    # ذخیره کوئری و صفحه در user_data برای استفاده در صفحات بعدی
    context.user_data['pin_query'] = query
    context.user_data['pin_page'] = 1
    
    await send_pinterest_page(update.message, context, query, page=1)

async def pin_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دکمه دریافت نتایج بعدی پینترست"""
    query_cb = update.callback_query
    await query_cb.answer()

    query = context.user_data.get('pin_query')
    current_page = context.user_data.get('pin_page', 1)
    
    if not query:
        await query_cb.message.reply_text("خطا: اطلاعات جستجو یافت نشد. لطفا دوباره جستجو کنید.")
        return

    next_page = current_page + 1
    context.user_data['pin_page'] = next_page

    # حذف دکمه "نتایج بعدی" از پیام قبلی
    old_markup = query_cb.message.reply_markup
    if old_markup and old_markup.inline_keyboard:
        new_keyboard = [row for row in old_markup.inline_keyboard if not (row and row[0].callback_data.startswith('pin_page|'))]
        await query_cb.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))

    await send_pinterest_page(query_cb.message, context, query, page=next_page)

async def send_pinterest_page(message, context, query, page):
    """تابع کمکی برای ارسال یک صفحه از نتایج پینترست"""
    limit = 10
    offset = (page - 1) * limit
    
    # دریافت تعداد بیشتری از نتایج (مثلا ۵۰ تا) تا بتوانیم صفحه‌بندی کنیم
    # نکته: باید در pinterest_helper.py تابع search_pinterest_rss را طوری تنظیم کنید که limit بزرگتر را بپذیرد
    pins = await search_pinterest_rss(query, limit=50) 
    
    if not pins:
        if page == 1:
            await message.reply_text("😕 نتیجه‌ای یافت نشد.")
        else:
            await message.reply_text("پایان نتایج.")
        return

    # برش لیست برای صفحه فعلی
    page_pins = pins[offset : offset + limit]
    
    if not page_pins:
        await message.reply_text("نتیجه بیشتری یافت نشد.")
        return

    text = f"📌 نتایج جستجوی *{query}* (صفحه {page}):\n\n"
    keyboard = []

    for i, pin in enumerate(page_pins, start=offset + 1):
        title = pin.get("title", "بدون عنوان")
        pin_url = pin.get("link", "")
        text += f"{i}. {title}\n{pin_url}\n\n"

        keyboard.append([InlineKeyboardButton(
            f"📥 دانلود شماره {i}",
            callback_data=f"pindl_{pin['id']}"
        )])

    # اگر نتایج بیشتری وجود دارد، دکمه صفحه بعد را اضافه کن
    if len(pins) > offset + limit:
        keyboard.append([InlineKeyboardButton("⬇️ دریافت 10 تصویر بعدی", callback_data="pin_page|next")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown", disable_web_page_preview=True)


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
