
import os
import uuid
import shutil
import aiohttp
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_openalex # Updated import
from utils.download_helper import download_file_async, split_file

# async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     if not context.args:
#         await update.message.reply_text("لطفا موضوع مقاله را وارد کنید.\nمثال: /scholar deep learning")
#         return

#     query = " ".join(context.args)
#     message = await update.message.reply_text("در حال جستجو در OpenAlex...")
    
#     # Call the new OpenAlex search
#     results = search_openalex(query, max_results=5)
    
#     if not results:
#         await message.edit_text("مقاله ای یافت نشد یا خطایی رخ داد.")
#         return

#     text = f"نتایج جستجو برای: {query}\n\n"
#     keyboard = []
#     row = []
    
#     for i, res in enumerate(results, 1):
#         text += f"*{i}. {res['title']}*\n"
#         text += f"👤 نویسندگان: {res['authors']}\n"
#         text += f"📅 سال: {res['year']}\n"
        
#         if res['pdf_link']:
#             text += "✅ فایل PDF موجود است\n\n"
#             # Changed prefix to paper_pdf
#             # Note: Telegram limits callback_data to 64 bytes. 
#             # If the URL is very long, this might need a workaround like storing URLs in a temp dict.
#             cb_data = f"paper_pdf|{res['pdf_link']}" 
#             if len(cb_data.encode('utf-8')) <= 64:
#                 row.append(InlineKeyboardButton(str(i), callback_data=cb_data))
#         else:
#             text += "❌ فایل PDF رایگان یافت نشد\n\n"
            
#     if row:
#         keyboard.append(row)
        
#     reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
#     await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
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
        
        if res.get('pdf_link'):
            text += "✅ لینک دسترسی موجود است\n\n"
            download_buttons.append(
                InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['pdf_link'][:50]}")
            )
        else:
            text += "❌ لینک دسترسی رایگان یافت نشد\n\n"

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

async def extract_pdf_from_html(html_filepath):
    """جستجوی تگ‌های متای استاندارد علمی برای پیدا کردن لینک واقعی PDF"""
    try:
        with open(html_filepath, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            # ناشران علمی معمولا لینک PDF را در این تگ قرار می‌دهند
            meta_tag = soup.find('meta', attrs={'name': 'citation_pdf_url'})
            if meta_tag and meta_tag.get('content'):
                return meta_tag['content']
    except Exception:
        pass
    return None

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, pdf_url = query.data.split("|", 1)
    
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="⏳ در حال تلاش برای دور زدن محدودیت‌ها و دریافت مقاله...")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    temp_file = os.path.join(download_dir, "temp_download.file")
    
    try:
        # مرحله ۱: تلاش برای دانلود با هدرهای مرورگر
        await fetch_and_save(pdf_url, temp_file)
        
        # مرحله ۲: اگر فایل متنی/HTML بود (Landing Page)، لینک واقعی را از داخلش استخراج کن
        if not is_real_pdf(temp_file):
            real_pdf_url = await extract_pdf_from_html(temp_file)
            if real_pdf_url:
                await status_msg.edit_text("🔍 لینک پنهان PDF یافت شد، در حال دریافت...")
                # تلاش مجدد برای دانلود لینک واقعی
                await fetch_and_save(real_pdf_url, temp_file)
        
        # مرحله ۳: بررسی نهایی
        if not is_real_pdf(temp_file):
            await status_msg.edit_text(
                f"⚠️ ناشر این مقاله دسترسی مستقیم ربات‌ها را کاملاً مسدود کرده است.\n\n"
                f"🔗 لینک مستقیم/صفحه مقاله:\n{pdf_url}\n"
            )
            return

        # اگر واقعا PDF بود، ارسال کن
        parts = split_file(temp_file)
        for part in parts:
            with open(part, 'rb') as f:
                await context.bot.send_document(
                    chat_id=query.message.chat_id, 
                    document=f,
                    filename='Paper.pdf'
                )
        await status_msg.delete()
                
    except Exception as e:
        await status_msg.edit_text(
            f"❌ دریافت مقاله با خطای مسدودسازی سرور (403/Timeout) مواجه شد.\n\n"
            f"🔗 لینک منبع:\n{pdf_url}"
        )
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)