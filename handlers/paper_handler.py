
import logging
import os
import uuid
import shutil
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_openalex # Updated import
from utils.download_helper import download_file_async, split_file



def is_real_pdf(filepath):
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF' # فایل‌های PDF با این بایت‌ها شروع می‌شوند
    except Exception:
        return False
async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا کلمه کلیدی را وارد کنید.\nمثال: `/scholar machine learning | yr 2023`", parse_mode='Markdown')
        return

    raw_query = " ".join(context.args)
    query = raw_query
    from_year = None
    
    # بررسی وجود فیلتر سال با فرمت yr 2023
    if "|" in raw_query:
        parts = [p.strip() for p in raw_query.split("|")]
        query = parts[0]
        for part in parts[1:]:
            if part.lower().startswith("yr "):
                from_year = part.lower().replace("yr", "").strip()

    context.user_data['scholar_query'] = query 
    context.user_data['scholar_year'] = from_year 
    
    msg_text = f"در حال جستجو برای: {query}"
    if from_year:
        msg_text += f" (از سال {from_year} به بعد)"
    msg_text += " ..."
        
    await update.message.reply_text(msg_text)
    
    results = search_openalex(query, page=1, from_year=from_year)
    
    if not results:
        await update.message.reply_text("مقاله‌ای یافت نشد.")
        return

    text = f"📚 *نتایج جستجو برای:* {query}\n\n"
    download_buttons = []

    for i, res in enumerate(results, 1):
        text += f"*{i}. {res['title']}*\n"
        text += f"👤 نویسندگان: {res['authors']}\n"
        
        journal = res.get('journal', 'نامشخص')
        doi = res.get('doi', 'نامشخص')
        text += f"📖 ژورنال: {journal}\n"
        text += f"📅 سال: {res['year']} (ارجاعات: {res.get('citation', 0)})\n"
        text += f"📖 doi: {doi}\n"
        
        if res.get('doi'):
            text += "✅ امکان دریافت از Libgen\n\n"
            # Pass DOI instead of URL (Callback data limit is 64 bytes)
            download_buttons.append(
                InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['doi'][:50]}")
            )
        else:
            text += "❌ شناسه DOI برای دانلود یافت نشد\n\n"

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)
        
    keyboard.append([InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data="scholar_page|2")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def paper_paginate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_call = update.callback_query
    await query_call.answer()
    
    _, page_str = query_call.data.split("|")
    page = int(page_str)
    
    query_text = context.user_data.get('scholar_query')
    from_year = context.user_data.get('scholar_year') # گرفتن فیلتر سال
    
    if not query_text:
        await query_call.message.reply_text("جستجوی شما منقضی شده است. لطفا دوباره جستجو کنید.")
        return

    # حفظ دکمه‌های دانلود پیام قبلی
    if query_call.message.reply_markup:
        old_keyboard = query_call.message.reply_markup.inline_keyboard
        new_old_keyboard = []
        for row in old_keyboard:
            clean_row = [btn for btn in row if not (btn.callback_data and btn.callback_data.startswith("scholar_page"))]
            if clean_row:
                new_old_keyboard.append(clean_row)
        await query_call.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_old_keyboard))
    
    status_msg = await context.bot.send_message(
        chat_id=query_call.message.chat_id, 
        text=f"در حال بارگذاری صفحه {page}..."
    )

    # پاس دادن متغیرها به جستجو
    results = search_openalex(query_text, page=page, from_year=from_year)
    
    if not results:
        await status_msg.edit_text("مقاله بیشتری یافت نشد.")
        return

    start_num = (page - 1) * 5 + 1
    text = f"📚 *نتایج صفحه {page} برای:* {query_text}\n\n"
    download_buttons = []

    for i, res in enumerate(results, start_num):
        text += f"*{i}. {res['title']}*\n"
        text += f"👤 نویسندگان:  {res['authors']}\n"
        
        journal = res.get('journal', 'نامشخص')
        doi = res.get('doi', 'نامشخص')
        text += f"📖 ژورنال: {journal}\n"
        text += f"📅 سال:  {res['year']} (ارجاعات: {res.get('citation', 0)})\n"
        text += f"📖 doi: {doi}\n"
        
        if res.get('pdf_link'):
            text += "✅ فایل PDF موجود است\n\n"
            download_buttons.append(
                InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['pdf_link'][:50]}")
            )
        else:
            text += "❌ فایل PDF موجود نیست\n\n"

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)
        
    keyboard.append([InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data=f"scholar_page|{page+1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)



HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://scholar.google.com/'
}

async def fetch_and_save(url, filepath):
    """دانلود فایل با هدرهای واقعی مرورگر"""
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, allow_redirects=True, timeout=20) as response:
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            return filepath, response.headers.get('Content-Type', '')


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def get_libgen_download_link(doi):
    """جستجوی مقاله در Libgen بر اساس DOI و استخراج لینک مستقیم PDF با لاگینگ"""
    logger.info(f"🔍 Starting Libgen search for DOI: {doi}")
    
    # روش 1: دسترسی مستقیم به صفحه دانلود از طریق libgen.lc (سریع‌تر و پایدارتر)
    direct_mirror_url = f"http://libgen.lc/scimag/ads.php?doi={doi}"
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info(f"🌐 Accessing direct mirror: {direct_mirror_url}")
            async with session.get(direct_mirror_url, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # پیدا کردن لینک GET یا لینک دانلود مستقیم
                    download_tag = soup.select_one('a[href^="get.php"]') or soup.select_one('#download h2 a')
                    
                    if download_tag and download_tag.has_attr('href'):
                        link = download_tag['href']
                        # اگر لینک نسبی است، آن را کامل کنید
                        if link.startswith('get.php'):
                            link = f"http://libgen.lc/scimag/{link}"
                        logger.info(f"✅ Found download link: {link}")
                        return link
                    else:
                        logger.warning("⚠️ Accessed direct mirror but couldn't find download link tag in HTML.")
                else:
                    logger.warning(f"⚠️ Direct mirror returned HTTP status: {response.status}")
        except Exception as e:
            logger.error(f"❌ Error accessing direct mirror: {e}")

        # روش 2: جستجو در صفحه اصلی لیبجن (اگر روش اول کار نکرد)
        search_url = f"http://libgen.is/scimag/?q={doi}"
        try:
            logger.info(f"🌐 Fallback searching main Libgen: {search_url}")
            async with session.get(search_url, timeout=15) as response:
                if response.status != 200:
                    logger.error(f"❌ Main Libgen search returned HTTP status: {response.status}")
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # پیدا کردن لینک میرورها در جدول نتایج
                mirror_link_tag = soup.select_one('table.catalog a[href*="libgen.lc"], table.catalog a[href*="library.lol"]')
                if not mirror_link_tag:
                    logger.error("❌ Could not find any mirror links in search results table.")
                    return None
                    
                mirror_url = mirror_link_tag['href']
                logger.info(f"🔗 Found mirror URL from search: {mirror_url}")

            # رفتن به صفحه میرور استخراج شده
            async with session.get(mirror_url, timeout=15) as response:
                if response.status != 200:
                    logger.error(f"❌ Fallback mirror returned HTTP status: {response.status}")
                    return None
                    
                mirror_html = await response.text()
                mirror_soup = BeautifulSoup(mirror_html, 'html.parser')
                
                download_tag = mirror_soup.select_one('a[href^="get.php"]') or mirror_soup.select_one('#download h2 a')
                if download_tag and download_tag.has_attr('href'):
                    link = download_tag['href']
                    if link.startswith('get.php') and 'libgen.lc' in mirror_url:
                        link = f"http://libgen.lc/scimag/{link}"
                    logger.info(f"✅ Found download link via fallback: {link}")
                    return link
                else:
                    logger.error("❌ Could not find download tag on fallback mirror.")
                    
        except Exception as e:
            logger.error(f"❌ Error in fallback search: {e}", exc_info=True)

    return None

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, doi = query.data.split("|", 1)
    logger.info(f"📥 Received download request for DOI: {doi}")
    
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ در حال ارتباط با سرورهای Libgen...")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    
    # جایگزین کردن کاراکترهای غیرمجاز در نام فایل
    safe_doi = doi.replace('/', '_').replace('\\', '_')
    temp_file = os.path.join(download_dir, f"{safe_doi}.pdf")
    
    try:
        # 1. پیدا کردن لینک مستقیم
        pdf_url = await get_libgen_download_link(doi)
        
        if not pdf_url:
            await status_msg.edit_text(f"❌ مقاله در پایگاه Libgen یافت نشد یا دسترسی مسدود است.\nDOI: {doi}")
            return
            
        await status_msg.edit_text("📥 لینک دانلود یافت شد. در حال دریافت فایل...")
        logger.info(f"⬇️ Downloading PDF from {pdf_url} to {temp_file}")
        
        # 2. دانلود فایل PDF
        await fetch_and_save(pdf_url, temp_file)
        
        if not is_real_pdf(temp_file):
            logger.warning(f"⚠️ Downloaded file is not a valid PDF for DOI: {doi}")
            await status_msg.edit_text("⚠️ فایل دریافت شده نامعتبر است (احتمالاً صفحه کپچا یا خطا دریافت شده).")
            return

        # 3. ارسال فایل به کاربر
        await status_msg.edit_text("📤 در حال آپلود به تلگرام...")
        logger.info(f"📤 Uploading file to Telegram for DOI: {doi}")
        
        parts = split_file(temp_file)
        for part in parts:
            with open(part, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id, 
                    document=f,
                    filename=f"{safe_doi}.pdf"
                )
        await status_msg.delete()
        logger.info(f"✅ Successfully sent PDF for DOI: {doi}")
                
    except Exception as e:
        # چاپ خطای کامل در کنسول
        logger.error(f"❌ Critical error in paper_download_callback: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ خطا در دریافت مقاله:\nلطفاً چند دقیقه دیگر امتحان کنید.")
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
            logger.info(f"🧹 Cleaned up temporary directory: {download_dir}")