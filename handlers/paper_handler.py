
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





async def sh_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    # data format: "sh_dl_<doi>"
    doi = data[6:]

    status_msg = await query.message.reply_text("⏳ در حال دریافت از Sci-Hub...")

    mirrors = ["https://sci-hub.se", "https://sci-hub.ru", "https://sci-hub.st"]
    response = None
    successful_mirror = None

    for mirror in mirrors:
        url = f"{mirror}/{doi}"
        print(f"[*] Requesting Sci-Hub: {url}")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                successful_mirror = mirror
                break  # Stop trying mirrors if successful
        except Exception as e:
            print(f"[!] Failed to connect to {mirror}: {e}")

    if not response or response.status_code != 200:
        await status_msg.edit_text("❌ خطا در ارتباط با سرورهای Sci-Hub.")
        return

    print(f"[*] Sci-Hub Status Code: {response.status_code}")
    
    # ==========================================
    # DEBUG: ذخیره سورس صفحه برای بررسی ساختار
    # ==========================================
    try:
        with open("scihub_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("[*] Saved Sci-Hub HTML to scihub_debug.html")
    except Exception as e:
        print(f"[!] Could not write debug file: {e}")
    # ==========================================

    pdf_url = None
    
    # 1. پیدا کردن هر تگ embed یا iframe و استخراج src
    tag_match = re.search(r'<(?:embed|iframe)[^>]*src=[\'"]([^\'"]+)[\'"]', response.text, re.IGNORECASE)
    if tag_match:
        pdf_url = tag_match.group(1)
    
    # 2. جستجوی مستقیم
    if not pdf_url:
        direct_match = re.search(r'[\'"](//[^\'"]+\.pdf[^\'"]*)[\'"]', response.text, re.IGNORECASE)
        if direct_match:
            pdf_url = direct_match.group(1)
            
    # 3. جستجوی دکمه دانلود
    if not pdf_url:
        btn_match = re.search(r'href=[\'"]([^\'"]+\.pdf[^\'"]*)[\'"]', response.text, re.IGNORECASE)
        if btn_match:
            pdf_url = btn_match.group(1)

    print(f"[*] Extracted PDF URL: {pdf_url}")

    # اگر لینک پیدا نشد، متوقف شو تا خطا ندهد
    if not pdf_url:
        await status_msg.edit_text("❌ لینک فایل PDF در صفحه یافت نشد (ممکن است نیاز به کپچا باشد یا مقاله موجود نباشد). فایل scihub_debug.html را در سرور بررسی کنید.")
        return

    try:
        if pdf_url.startswith("//"):
            pdf_url = "https:" + pdf_url
        elif pdf_url.startswith("/"):
            pdf_url = successful_mirror + pdf_url
        elif not pdf_url.startswith("http"):
            pdf_url = f"{successful_mirror}/{pdf_url}"

        print(f"[*] Final PDF Download URL: {pdf_url}")

        pdf_response = requests.get(pdf_url, stream=True, timeout=20)
        if pdf_response.status_code == 200:
            pdf_data = io.BytesIO(pdf_response.content)
            pdf_data.name = f"{doi.replace('/', '_')}.pdf"

            await status_msg.edit_text("✅ در حال ارسال فایل...")
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=pdf_data,
                filename=pdf_data.name,
                caption=f"📄 {doi}\n📥 دانلود شده از Sci-Hub"
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ خطا در دانلود فایل PDF از لینک استخراج شده.")
    except Exception as e:
        print(f"[!] Exception occurred: {e}")
        await status_msg.edit_text(f"❌ خطای سیستمی رخ داد.")

