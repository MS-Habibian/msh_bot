
import asyncio
import logging
import os
import uuid
import shutil
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import urllib
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

async def fetch_and_save(url: str, save_path: str):
    """Downloads the file from the given URL and saves it."""
    
    # Add headers to mimic a real web browser and bypass 403 blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        # allow_redirects=True is important for publishers that redirect to a final PDF URL
        async with session.get(url, allow_redirects=True, timeout=60) as response:
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)



logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")


async def get_scihub_download_link(doi):
    """جستجوی مقاله فقط در Sci-Hub.ru با استفاده از ScraperAPI"""
    
    # Using your API key directly
    API_KEY = os.getenv("SCRAPERAPI_KEY", "dc58ddcba2dbb3bd1e6a1d4ee8bedcda")
    
    base_url = "https://sci-hub.ru"
    target_url = f"{base_url}/{doi}"
    
    # URL-encode the Sci-Hub URL
    encoded_url = urllib.parse.quote(target_url)
    
    # Build the ScraperAPI request URL
    api_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={encoded_url}"
    
    async with aiohttp.ClientSession() as session:
        try:
            logger.info(f"🌐 Accessing {target_url} VIA SCRAPERAPI...")
            
            # 60 seconds timeout - scraping APIs take time to bypass captchas
            async with session.get(api_url, timeout=60) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    pdf_url = None
                    
                    # 1. Try to find standard PDF embed/iframe
                    pdf_container = soup.find('embed', id='pdf') or soup.find('iframe', id='pdf') or soup.find('embed')
                    if pdf_container and pdf_container.has_attr('src'):
                        pdf_url = pdf_container['src']
                    
                    # 2. Try to find the download button if embed is missing
                    if not pdf_url:
                        button = soup.find('button', onclick=lambda x: x and 'location.href' in x)
                        if button:
                            parts = button['onclick'].split("'")
                            if len(parts) >= 3:
                                pdf_url = parts[1]

                    if pdf_url:
                        # Fix relative URLs
                        if pdf_url.startswith('//'):
                            pdf_url = f"https:{pdf_url}"
                        elif pdf_url.startswith('/'):
                            pdf_url = f"{base_url}{pdf_url}"
                            
                        logger.info(f"✅ Found Sci-Hub download link: {pdf_url}")
                        return pdf_url
                    else:
                        logger.warning(f"⚠️ Page loaded via ScraperAPI, but no PDF found.")
                        return None
                else:
                    logger.error(f"❌ ScraperAPI returned HTTP status: {response.status}")
                    return None
        
        except asyncio.TimeoutError:
            logger.error("❌ ScraperAPI request timed out (took longer than 60s).")
            return None
        except Exception as e:
            logger.error(f"❌ Error accessing API: {e}")
            return None

async def get_libgen_download_link(doi):
    """جستجوی مقاله در Libgen بر اساس DOI و استخراج لینک مستقیم PDF با لاگینگ"""
    logger.info(f"🔍 Starting Libgen search for DOI: {doi}")
    
    # Use HTTPS and .lc mirror
    direct_mirror_url = f"https://libgen.lc/scimag/ads.php?doi={doi}"
    
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        try:
            logger.info(f"🌐 Accessing direct mirror: {direct_mirror_url}")
            async with session.get(direct_mirror_url, timeout=20) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    download_tag = soup.select_one('a[href^="get.php"]') or soup.select_one('#download h2 a')
                    
                    if download_tag and download_tag.has_attr('href'):
                        link = download_tag['href']
                        if link.startswith('get.php'):
                            link = f"https://libgen.lc/scimag/{link}"
                        logger.info(f"✅ Found download link: {link}")
                        return link
                    else:
                        logger.warning("⚠️ Direct mirror loaded but no download link found (Paper might not be in Libgen).")
                else:
                    logger.warning(f"⚠️ Direct mirror returned HTTP status: {response.status}")
        except asyncio.TimeoutError:
            logger.error("❌ Direct mirror timed out.")
        except Exception as e:
            logger.error(f"❌ Error accessing direct mirror: {e}")

        # Fallback using a more stable domain (libgen.rs) and a longer timeout
        search_url = f"https://libgen.im/scimag/?q={doi}"
        try:
            logger.info(f"🌐 Fallback searching main Libgen: {search_url}")
            async with session.get(search_url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"❌ Main Libgen search returned HTTP status: {response.status}")
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                mirror_link_tag = soup.select_one('table.catalog a[href*="libgen.lc"], table.catalog a[href*="library.lol"], ul.record_mirrors li a')
                if not mirror_link_tag or not mirror_link_tag.has_attr('href'):
                    logger.error("❌ Could not find any mirror links in search results table. Paper is likely not on Libgen.")
                    return None
                    
                mirror_url = mirror_link_tag['href']
                if mirror_url.startswith('//'):
                    mirror_url = f"https:{mirror_url}"
                logger.info(f"🔗 Found mirror URL from search: {mirror_url}")

            # Access the mirror page
            async with session.get(mirror_url, timeout=30) as response:
                if response.status != 200:
                    logger.error(f"❌ Fallback mirror returned HTTP status: {response.status}")
                    return None
                    
                mirror_html = await response.text()
                mirror_soup = BeautifulSoup(mirror_html, 'html.parser')
                
                download_tag = mirror_soup.select_one('a[href^="get.php"]') or mirror_soup.select_one('#download h2 a')
                if download_tag and download_tag.has_attr('href'):
                    link = download_tag['href']
                    if link.startswith('get.php'):
                        # Extract the base domain from the mirror_url dynamically
                        from urllib.parse import urlparse
                        parsed_uri = urlparse(mirror_url)
                        base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
                        link = f"{base_url}/scimag/{link}"
                    logger.info(f"✅ Found download link via fallback: {link}")
                    return link
                else:
                    logger.error("❌ Could not find download tag on fallback mirror.")
                    
        except asyncio.TimeoutError:
            logger.error("❌ Fallback search timed out (Server might be blocking the connection or it's too slow).")
        except Exception as e:
            logger.error(f"❌ Error in fallback search: {e}")

    return None


async def get_paper_pdf_link(doi: str) -> str:
    print(f"Starting paper download process for DOI: {doi}")
    
    # 1. Try Unpaywall First
    print("Attempting to fetch from Unpaywall...")
    unpaywall_link = await get_unpaywall_pdf_link(doi)
    if unpaywall_link:
        print(f"Success! Found Unpaywall PDF link: {unpaywall_link}")
        return unpaywall_link
    
    print("Unpaywall failed or paper is not Open Access. Falling back to Sci-Hub...")

    # 2. Try Sci-Hub via ScraperAPI (Libgen removed)
    try:
        scihub_link = await get_scihub_download_link(doi)
        if scihub_link:
            print(f"Success! Found Sci-Hub PDF link: {scihub_link}")
            return scihub_link
    except Exception as e:
        print(f"Sci-Hub attempt failed: {e}")

    print("All download methods failed.")
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
        pdf_url = await get_paper_pdf_link(doi)
        
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


async def get_unpaywall_pdf_link(doi: str, email: str = "mehdifcb7997@gmail.com") -> str:
    """
    Checks Unpaywall for an open-access PDF link using the DOI.
    """
    url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check if the paper is Open Access
                    if data.get("is_oa"):
                        best_location = data.get("best_oa_location")
                        if best_location and best_location.get("url_for_pdf"):
                            return best_location.get("url_for_pdf")
                else:
                    print(f"Unpaywall returned status {response.status} for DOI {doi}")
    except asyncio.TimeoutError:
        print("Unpaywall request timed out.")
    except Exception as e:
        print(f"Error checking Unpaywall: {e}")
        
    return None