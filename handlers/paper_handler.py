
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
    for res in results:
        text = f"📚 *{res['title']}*\n👤 {res['authors']}\n📅 {res['year']}"
        reply_markup = None
        if res['pdf_link']:
            keyboard = [[InlineKeyboardButton("📥 دانلود PDF", callback_data=f"paper_pdf|{res['pdf_link'][-40:]}")]] # Truncated URL if needed, or implement ID mapping
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    # Send the Pagination button
    keyboard = [[InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data="scholar_page|2")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("صفحه 1", reply_markup=reply_markup)

# --- Add this NEW function for the Next button ---
async def paper_paginate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_call = update.callback_query
    await query_call.answer()
    
    # Extract the requested page number
    _, page_str = query_call.data.split("|")
    page = int(page_str)
    
    # Retrieve the original query from user_data
    query_text = context.user_data.get('scholar_query')
    if not query_text:
        await query_call.message.reply_text("جستجوی شما منقضی شده است. لطفا دوباره جستجو کنید.")
        return

    # Remove the old "Next" button from the chat so it doesn't clutter
    await query_call.edit_message_reply_markup(reply_markup=None)
    await context.bot.send_message(chat_id=query_call.message.chat_id, text=f"در حال بارگذاری صفحه {page}...")

    results = search_openalex(query_text, page=page)
    
    if not results:
        await context.bot.send_message(chat_id=query_call.message.chat_id, text="مقاله بیشتری یافت نشد.")
        return

    # Send the new results
    for res in results:
        text = f"📚 *{res['title']}*\n👤 {res['authors']}\n📅 {res['year']}"
        reply_markup = None
        if res['pdf_link']:
            # CAUTION: PDF URLs might exceed 64 bytes in callback_data
            keyboard = [[InlineKeyboardButton("📥 دانلود PDF", callback_data=f"paper_pdf|{res['pdf_link'][:50]}")]] 
            reply_markup = InlineKeyboardMarkup(keyboard)
            
        await context.bot.send_message(chat_id=query_call.message.chat_id, text=text, parse_mode='Markdown', reply_markup=reply_markup)

    # Send a new Pagination button for the next page
    keyboard = [[InlineKeyboardButton("⬇️ دریافت 5 مقاله بعدی", callback_data=f"scholar_page|{page+1}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=query_call.message.chat_id, text=f"صفحه {page}", reply_markup=reply_markup)

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