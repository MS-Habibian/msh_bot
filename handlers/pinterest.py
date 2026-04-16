import aiohttp
import http.cookiejar
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.pinterest_helper import search_pinterest_rss, load_cookies




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
                        
                        keyboard = [[InlineKeyboardButton(
                            text=f"📥 دانلود کیفیت اصلی",
                            callback_data=f"pindl_{item['id']}"
                        )]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # ساخت caption با توضیحات و لینک
                        caption = f"🖼 تصویر شماره {item['id']}\n"
                        if item.get('description'):
                            caption += f"\n📝 {item['description'][:200]}\n"
                        if item.get('author'):
                            caption += f"\n👤 {item['author']}\n"
                        if item.get('domain'):
                            caption += f"🌐 {item['domain']}\n"
                        if item.get('link'):
                            caption += f"🔗 {item['link']}\n"
                        elif item.get('url'):
                            caption += f"🔗 {item['url']}\n"
                        
                        await update.message.reply_photo(
                            photo=img_bytes,
                            caption=caption,
                            reply_markup=reply_markup
                        )
                        
                        print(f"[Pinterest] Sent image {item['id']} ({len(img_bytes)} bytes)")
                    else:
                        print(f"[Pinterest] Failed to download image {item['id']}: {img_response.status}")
            except Exception as e:
                print(f"[Pinterest] Error downloading image {item['id']}: {e}")
                continue



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
