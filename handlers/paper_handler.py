
import os
import uuid
import shutil
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
        text += f"📖 ژورنال: {journal}\n"
        text += f"📅 سال: {res['year']} (ارجاعات: {res.get('citation', 0)})\n"
        
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
        text += f"📖 ژورنال: {journal}\n"
        text += f"📅 سال:  {res['year']} (ارجاعات: {res.get('citation', 0)})\n"
        
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

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, pdf_url = query.data.split("|", 1)
    
    status_msg = await context.bot.send_message(chat_id=query.message.chat_id, text="در حال دریافت مقاله...")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        downloaded_file = await download_file_async(pdf_url, download_dir)
        
        # بررسی اینکه آیا فایل دانلود شده واقعاً یک PDF است یا یک صفحه وب (HTML)
        if not is_real_pdf(downloaded_file):
            await status_msg.edit_text(
                f"⚠️ ناشر لینک مستقیم PDF را محدود کرده یا این یک صفحه وب است.\n\n"
                f"🔗 می‌تونید از لینک زیر مستقیماً به مقاله دسترسی پیدا کنید:\n{pdf_url}"
            )
            return

        parts = split_file(downloaded_file)
        for part in parts:
            with open(part, 'rb') as f:
                file_name = os.path.basename(part)
                if not file_name.lower().endswith('.pdf'):
                    file_name += '.pdf'
                
                await context.bot.send_document(
                    chat_id=query.message.chat_id, 
                    document=f,
                    filename=file_name
                )
        await status_msg.delete()
                
    except Exception as e:
        await status_msg.edit_text(f"خطا در دریافت مقاله. ممکن است لینک منقضی شده باشد.\nلینک: {pdf_url}")
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)