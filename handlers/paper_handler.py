
import asyncio
import os
import uuid
import shutil
from scidownl import scihub_download
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_openalex # Updated import
from utils.download_helper import download_file_async, split_file

async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا کلمه کلیدی را وارد کنید. مثال: /scholar machine learning")
        return

    query = " ".join(context.args)
    # Save the query in user_data for pagination
    context.user_data['scholar_query'] = query 
    
    await update.message.reply_text(f"در حال جستجو برای: {query} ...")
    
    results = search_openalex(query, page=1)
    
    if not results:
        await update.message.reply_text("مقاله‌ای یافت نشد.")
        return

    # Send the first 5 results
    text = f"📚 *نتایج جستجو برای:* {query}\n\n"
    download_buttons = []

    for i, res in enumerate(results, 1):
        text += f"*{i}. {res['title']}*\n"
        text += f"👤 نویسندگان: {res['authors']}\n"
        
        # اضافه کردن ژورنال و سال و تعداد ارجاعات
        journal = res.get('journal', 'نامشخص')
        text += f"📖 ژورنال: {journal}\n"
        text += f"📅 سال: {res['year']}\n"
        
        # if res.get('pdf_link'):
        #     text += "✅ فایل PDF موجود است\n\n"
        #     download_buttons.append(
        #         InlineKeyboardButton(str(i), callback_data=f"paper_pdf|{res['pdf_link'][:50]}")
        #     )
        if res.get('doi'):
            text += "✅ دانلود فایل از sci hub\n\n"
            callback_data = f"paper_dl_doi|{res['doi']}"
        elif res.get('pdf_link'):
            text += "✅ فایل PDF موجود است\n\n"
            callback_data = f"paper_pdf|{res['pdf_link'][:50]}"
        else:
            text += "❌ فایل PDF موجود نیست\n\n"

        download_buttons.append(
            InlineKeyboardButton(str(i), callback_data)
        )

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)
        
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

    for i, res in enumerate(results, start_num):
            text += f"📄 **{i}. {res['title']}**\n"
            text += f"👤 نویسندگان: {res['authors']}\n"
            text += f"📅 سال: {res['year']}\n"
            
            if res.get('doi'):
                text += "✅ دانلود از Sci-Hub\n\n"
                # Use DOI instead of a broken 50-character PDF link
                callback_data = f"paper_dl_doi|{res['doi']}"
                download_buttons.append(InlineKeyboardButton(str(i), callback_data=callback_data))
            elif res.get('pdf_link'):
                text += "✅ لینک مستقیم موجود است\n\n"
                # Pass the link directly (Be careful, Telegram limits callback_data to 64 bytes)
                callback_data = f"paper_pdf|{res['pdf_link'][:54]}"
                download_buttons.append(InlineKeyboardButton(str(i), callback_data=callback_data))
            else:
                text += "❌ فایل موجود نیست\n\n"

    keyboard = []
    if download_buttons:
        keyboard.append(download_buttons)
        
    keyboard.append([InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data=f"scholar_page|{page+1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await status_msg.edit_text(text, parse_mode='Markdown', reply_markup=reply_markup)

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    await context.bot.send_message(chat_id=query.message.chat_id, text="در حال پردازش و دانلود مقاله... لطفاً کمی صبر کنید.")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        downloaded_file = None
        
        # --- حالت اول: دانلود از Sci-Hub با استفاده از DOI ---
        if data.startswith("paper_dl_doi|"):
            _, doi = data.split("|", 1)
            out_path = os.path.join(download_dir, f"{doi.replace('/', '_')}.pdf")
            
            # آدرس سایت scihub حذف شده تا خود کتابخانه لینک سالم را پیدا کند
            await asyncio.to_thread(scihub_download, doi, paper_type="doi", out=out_path)
            
            if os.path.exists(out_path):
                downloaded_file = out_path
            else:
                raise Exception("فایل از Sci-Hub دریافت نشد.")
                
        # --- حالت دوم: دانلود مستقیم از لینک PDF ---
        elif data.startswith("paper_pdf|"):
            _, pdf_url = data.split("|", 1)
            
            # هشدار: اگر لینک به خاطر محدودیت تلگرام ناقص شده باشد، اینجا خطا می‌دهد.
            downloaded_file = await download_file_async(pdf_url, download_dir)
            
        # ارسال فایل دانلود شده
        if downloaded_file and os.path.exists(downloaded_file):
            parts = split_file(downloaded_file)
            for part in parts:
                with open(part, 'rb') as f:
                    await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                    
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"خطا در دانلود مقاله: {e}")
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
    # query = update.callback_query
    # await query.answer()
    
    # # Extract URL from the new prefix
    # _, pdf_url = query.data.split("|", 1)
    
    # await context.bot.send_message(chat_id=query.message.chat_id, text="در حال دانلود مقاله...")
    
    # download_dir = f"downloads/{uuid.uuid4()}"
    # os.makedirs(download_dir, exist_ok=True)
    
    # try:
    #     # Pass the DIRECTORY (download_dir), not the file path. 
    #     # The function will return the final path to the downloaded file.
    #     downloaded_file = await download_file_async(pdf_url, download_dir)
        
    #     # Split and send using the returned file path
    #     parts = split_file(downloaded_file)
    #     for part in parts:
    #         with open(part, 'rb') as f:
    #             await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                
    # except Exception as e:
    #     await context.bot.send_message(chat_id=query.message.chat_id, text=f"خطا در دانلود مقاله: {e}")
    # finally:
    #     if os.path.exists(download_dir):
    #         shutil.rmtree(download_dir)