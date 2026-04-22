
import os
import uuid
import shutil
import re

import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_all_sources, search_openalex # Updated import
from utils.download_helper import download_file_async, split_file


async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا کلمه کلیدی را وارد کنید. مثال: /scholar machine learning")
        return

    query = " ".join(context.args)
    # Save the query in user_data for pagination
    context.user_data['scholar_query'] = query 
    
    await update.message.reply_text(f"در حال جستجو برای: {query} ...")
    
    # results = search_openalex(query, page=1)
    results = search_all_sources(query, page=1)

    
    if not results:
        await update.message.reply_text("مقاله‌ای یافت نشد.")
        return

    # Send the first 5 results
    text = f"📚 *نتایج جستجو برای:* {query}\n\n"
    download_buttons = []
    sh_buttons = []

    for i, res in enumerate(results, 1):
        authors = ", ".join(res.get('authors', [])) if res.get('authors') else "نامشخص"
        pdf_status = "✅ دارد" if res.get('pdf_link') else "❌ ندارد"
        
        text += f"**{i}. {res.get('title', 'بدون عنوان')}**\n"
        text += f"👤 نویسندگان: {authors}\n"
        text += f"📖 ژورنال: {res.get('journal', 'نامشخص')} | 📅 سال: {res.get('year', 'نامشخص')}\n"
        text += f"🔗 تعداد ارجاعات: {res.get('citation', 0)}\n"
        text += f"📄 فایل آزاد (Open Access): {pdf_status}\n"
        text += "➖➖➖➖➖➖➖➖\n"

        # دکمه دانلود مستقیم خودتان
        if res.get('pdf_link'):
            download_buttons.append(InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['pdf_link'][:50]}"))
            
        # دکمه Sci-Hub (تغییر یافته به callback برای دانلود داخلی)
        if res.get('doi'):
            sh_buttons.append(InlineKeyboardButton(f"SH {i}", callback_data=f"sh_pdf|{res['doi']}"))

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)

    if sh_buttons:
        keyboard.append(sh_buttons)
        
    keyboard.append([InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data="scholar_page|2")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)
# --- Add this NEW function for the Next button ---
async def paper_paginate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_call = update.callback_query
    await query_call.answer()
    
    _, page_str = query_call.data.split("|")
    page = int(page_str)
    
    query_text = context.user_data.get('scholar_query')
    if not query_text:
        await query_call.message.reply_text("جستجوی شما منقضی شده است. لطفا دوباره جستجو کنید.")
        return

    # حفظ دکمه‌های دانلود پیام قبلی و حذف فقط دکمه "صفحه بعدی"
    if query_call.message.reply_markup:
        old_keyboard = query_call.message.reply_markup.inline_keyboard
        new_old_keyboard = []
        for row in old_keyboard:
            # فقط دکمه‌هایی که مربوط به صفحه بعد نیستند را نگه می‌داریم
            clean_row = [btn for btn in row if not (btn.callback_data and btn.callback_data.startswith("scholar_page"))]
            if clean_row:
                new_old_keyboard.append(clean_row)
        await query_call.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_old_keyboard))
    
    status_msg = await context.bot.send_message(
        chat_id=query_call.message.chat_id, 
        text=f"در حال بارگذاری صفحه {page}..."
    )

    results = search_openalex(query_text, page=page) # فرض بر این است که این تابع از قبل ایمپورت شده
    
    if not results:
        await status_msg.edit_text("مقاله بیشتری یافت نشد.")
        return

    start_num = (page - 1) * 5 + 1
    text = f"📚 *نتایج صفحه {page} برای:* {query_text}\n\n"
    download_buttons = []
    sh_buttons = []

    for i, res in enumerate(results, start_num):
        authors = ", ".join(res.get('authors', [])) if res.get('authors') else "نامشخص"
        pdf_status = "✅ دارد" if res.get('pdf_link') else "❌ ندارد"
        
        text += f"**{i}. {res.get('title', 'بدون عنوان')}**\n"
        text += f"👤 نویسندگان: {authors}\n"
        text += f"📖 ژورنال: {res.get('journal', 'نامشخص')} | 📅 سال: {res.get('year', 'نامشخص')}\n"
        text += f"🔗 تعداد ارجاعات: {res.get('citation', 0)}\n"
        text += f"📄 فایل آزاد (Open Access): {pdf_status}\n"
        text += "➖➖➖➖➖➖➖➖\n"

        # دکمه دانلود مستقیم خودتان
        if res.get('pdf_link'):
            download_buttons.append(InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['pdf_link'][:50]}"))
            
        # دکمه Sci-Hub (تغییر یافته به callback برای دانلود داخلی)
        if res.get('doi'):
            sh_buttons.append(InlineKeyboardButton(f"SH {i}", callback_data=f"sh_pdf|{res['doi']}"))

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)

    if sh_buttons:
        keyboard.append(sh_buttons)
        
    keyboard.append([InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data=f"scholar_page|{page+1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extract URL from the new prefix
    _, pdf_url = query.data.split("|", 1)
    
    await context.bot.send_message(chat_id=query.message.chat_id, text="در حال دانلود مقاله...")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Pass the DIRECTORY (download_dir), not the file path. 
        # The function will return the final path to the downloaded file.
        downloaded_file = await download_file_async(pdf_url, download_dir)
        
        # Split and send using the returned file path
        parts = split_file(downloaded_file)
        for part in parts:
            with open(part, 'rb') as f:
                await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"خطا در دانلود مقاله: {e}")
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)





async def sh_download_callback(update, context):
    query_call = update.callback_query
    await query_call.answer("در حال دریافت از Sci-Hub، لطفا چند لحظه صبر کنید...")
    
    # استخراج DOI و تمیز کردن آن (گاهی OpenAlex لینک کامل doi.org را برمی‌گرداند)
    _, doi = query_call.data.split("|", 1)
    doi = doi.replace("https://doi.org/", "").strip()
    chat_id = update.effective_chat.id
    
    try:
        # هدرهای کامل‌تر مرورگر برای جلوگیری از بلاک شدن
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        mirrors = ["https://sci-hub.se", "https://sci-hub.ru", "https://sci-hub.st"]
        response = None
        sh_url = None

        # 1. پیدا کردن یک میرور سالم (حلقه فقط برای برقراری ارتباط است)
        for mirror in mirrors:
            sh_url = f"{mirror}/{doi}"
            print(f"\n[*] Requesting Sci-Hub: {sh_url}")
            try:
                response = requests.get(sh_url, headers=headers, timeout=15)
                response.raise_for_status() # Raises an exception for 4xx or 5xx status codes
                break  # ارتباط موفق بود، پس از حلقه خارج می‌شویم تا سراغ دانلود برویم
            except requests.exceptions.RequestException as e:
                print(f"[!] Failed to connect to {mirror}: {e}")
                response = None # پاک کردن متغیر برای امتحان میرور بعدی
        
        # 2. بررسی بیرون از حلقه: آیا ارتباط با تمام میرورها با شکست مواجه شد؟
        if not response:
            await context.bot.send_message(chat_id=chat_id, text="متاسفانه در حال حاضر ارتباط با هیچ‌کدام از سرورهای Sci-Hub امکان‌پذیر نیست (مشکل شبکه یا DNS).")
            return
            
        print(f"[*] Sci-Hub Status Code: {response.status_code}")
        
        pdf_url = None
        
        # 3. روش اول: پیدا کردن تگ embed یا iframe (پشتیبانی از کوتیشن‌های سینگل و جفت)
        tag_match = re.search(r'<(?:embed|iframe)[^>]*id=[\'"]pdf[\'"][^>]*>', response.text, re.IGNORECASE)
        if tag_match:
            src_match = re.search(r'src=[\'"]([^\'"]+)[\'"]', tag_match.group(0), re.IGNORECASE)
            if src_match:
                pdf_url = src_match.group(1)
        
        # 4. روش دوم: اگر تگ بالا نبود، جستجوی مستقیم اکشن دکمه دانلود
        if not pdf_url:
            button_match = re.search(r'location\.href=[\'"]([^\'"]+)[\'"]', response.text, re.IGNORECASE)
            if button_match:
                pdf_url = button_match.group(1)
                
        if not pdf_url:
            # چاپ بخشی از سورس صفحه برای دیباگ کردن در لاگ‌های سرور (کپچا، ارور و غیره)
            print("[!] PDF link not found. HTML Snippet:")
            print(response.text[:500]) 
            await context.bot.send_message(chat_id=chat_id, text="متاسفانه PDF این مقاله در Sci-Hub یافت نشد (احتمال مسدودی آی‌پی سرور یا عدم وجود مقاله).")
            return
            
        print(f"[*] Extracted PDF URL: {pdf_url}")
        
        # اصلاح لینک در صورتی که // یا / داشته باشد
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            # استخراج دامنه میروری که کار کرده است برای آدرس‌های نسبی (مثلاً https://sci-hub.se)
            base_url = "/".join(sh_url.split("/")[:3]) 
            pdf_url = base_url + pdf_url
            
        # 5. دانلود فایل PDF و ارسال به کاربر
        await context.bot.send_message(chat_id=chat_id, text="فایل یافت شد. در حال آپلود...")
        
        print(f"[*] Downloading PDF from: {pdf_url}")
        pdf_resp = requests.get(pdf_url, headers=headers, timeout=60)
        
        if pdf_resp.status_code == 200:
            # بررسی اینکه فایل دریافتی واقعا PDF باشد
            if pdf_resp.content.startswith(b'%PDF'):
                safe_doi = doi.split('/')[-1] if '/' in doi else doi
                await context.bot.send_document(
                    chat_id=chat_id, 
                    document=pdf_resp.content, 
                    filename=f"SciHub_{safe_doi}.pdf"
                )
                print("[*] Upload to Telegram successful.")
            else:
                await context.bot.send_message(chat_id=chat_id, text="فایل دریافت شده خراب است یا از سمت سای‌هاب مسدود شده است.")
                print("[!] Downloaded content is not a PDF (Missing %PDF header).")
        else:
            await context.bot.send_message(chat_id=chat_id, text="خطا در دانلود فایل از سرور Sci-Hub.")
            print(f"[!] PDF Download failed with status: {pdf_resp.status_code}")
            
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text="خطای غیرمنتظره در پردازش درخواست رخ داد.")
        print(f"[!] Exception occurred: {e}")
