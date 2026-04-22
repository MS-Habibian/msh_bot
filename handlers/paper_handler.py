
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
    
    # استخراج DOI از دکمه
    _, doi = query_call.data.split("|", 1)
    chat_id = update.effective_chat.id
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        sh_url = f"https://sci-hub.st/{doi}"
        
        # 1. دریافت صفحه HTML سای‌هاب
        response = requests.get(sh_url, headers=headers, timeout=15)
        
        # 2. پیدا کردن لینک مخفی PDF در سورس صفحه با Regex
        match = re.search(r'src="(.*?\.pdf.*?)"', response.text)
        if not match:
            await context.bot.send_message(chat_id=chat_id, text="متاسفانه PDF این مقاله در Sci-Hub یافت نشد.")
            return
            
        pdf_url = match.group(1)
        # اصلاح لینک در صورتی که // یا / داشته باشد
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = 'https://sci-hub.st' + pdf_url
            
        # 3. دانلود فایل PDF و ارسال به کاربر
        await context.bot.send_message(chat_id=chat_id, text="فایل یافت شد. در حال آپلود...")
        pdf_resp = requests.get(pdf_url, headers=headers, timeout=30)
        
        if pdf_resp.status_code == 200:
            await context.bot.send_document(
                chat_id=chat_id, 
                document=pdf_resp.content, 
                filename=f"SciHub_{doi.replace('/', '_')}.pdf"
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text="خطا در دانلود فایل از سرور Sci-Hub.")
            
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text="ارتباط با Sci-Hub برقرار نشد یا زمان‌بر شد.")
        print(f"Sci-Hub error: {e}")