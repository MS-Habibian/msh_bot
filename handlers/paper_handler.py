# import os
# import uuid
# import shutil
# from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
# from telegram.ext import ContextTypes

# from utils.search_papers import search_arxiv
# from utils.download_helper import download_file_async, split_file

# async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     if not context.args:
#         await update.message.reply_text("⚠️ لطفاً یک عبارت برای جستجو وارد کنید!\nمثال: `/search attention is all you need`", parse_mode="Markdown")
#         return
        
#     query = " ".join(context.args)
#     status_msg = await update.message.reply_text(f"🔍 در حال جستجو...\n{query}")
    
#     papers = search_arxiv(query, max_results=5)
    
#     if not papers:
#         await status_msg.edit_text("❌ مقاله‌ای یافت نشد.")
#         return
        
#     text = f"📚 **نتایج جستجو برای:** {query}\n\n"
#     keyboard_row = []
    
#     for i, paper in enumerate(papers, 1):
#         # Add paper info to the message text
#         text += f"*{i}. {paper['title']}*\n"
#         text += f"👨‍🔬 {paper['authors']} | 📅 {paper['year']}\n\n"
        
#         # Telegram callback_data limit is 64 bytes. Arxiv URLs are short enough.
#         callback_data = f"arxiv_pdf|{paper['pdf_link']}"
#         keyboard_row.append(InlineKeyboardButton(str(i), callback_data=callback_data))
        
#     reply_markup = InlineKeyboardMarkup([keyboard_row])
#     await status_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer() # Acknowledge the button click
    
#     # Extract the PDF URL from the callback data
#     pdf_url = query.data.split("|")[1]
    
#     # Edit the message to show download status
#     await query.edit_message_text("📥 در حال دانلود مقاله انتخاب شده...")
    
#     task_id = str(uuid.uuid4())
#     dest_folder = os.path.join("downloads", task_id)
#     os.makedirs(dest_folder, exist_ok=True)
    
#     try:
#         downloaded_file = await download_file_async(pdf_url, dest_folder)
#         parts = split_file(downloaded_file)
        
#         await query.edit_message_text("📤 در حال آپلود...")
        
#         for part in parts:
#             with open(part, 'rb') as f:
#                 # Send the document to the chat where the button was clicked
#                 await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                
#         await query.edit_message_text("✅ مقاله با موفقیت ارسال شد.")
        
#     except Exception as e:
#         await query.edit_message_text(f"❌ خطا در پردازش مقاله:\n{e}")
        
#     finally:
#         if os.path.exists(dest_folder):
#             shutil.rmtree(dest_folder, ignore_errors=True)


import os
import uuid
import shutil
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_openalex # Updated import
from utils.download_helper import download_file_async, split_file

async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفا موضوع مقاله را وارد کنید.\nمثال: /scholar deep learning")
        return

    query = " ".join(context.args)
    message = await update.message.reply_text("در حال جستجو در OpenAlex...")
    
    # Call the new OpenAlex search
    results = search_openalex(query, max_results=5)
    
    if not results:
        await message.edit_text("مقاله ای یافت نشد یا خطایی رخ داد.")
        return

    text = f"نتایج جستجو برای: {query}\n\n"
    keyboard = []
    row = []
    
    for i, res in enumerate(results, 1):
        text += f"*{i}. {res['title']}*\n"
        text += f"👤 نویسندگان: {res['authors']}\n"
        text += f"📅 سال: {res['year']}\n"
        
        if res['pdf_link']:
            text += "✅ فایل PDF موجود است\n\n"
            # Changed prefix to paper_pdf
            # Note: Telegram limits callback_data to 64 bytes. 
            # If the URL is very long, this might need a workaround like storing URLs in a temp dict.
            cb_data = f"paper_pdf|{res['pdf_link']}" 
            if len(cb_data.encode('utf-8')) <= 64:
                row.append(InlineKeyboardButton(str(i), callback_data=cb_data))
        else:
            text += "❌ فایل PDF رایگان یافت نشد\n\n"
            
    if row:
        keyboard.append(row)
        
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Extract URL from the new prefix
    _, pdf_url = query.data.split("|", 1)
    
    await context.bot.send_message(chat_id=query.message.chat_id, text="در حال دانلود مقاله...")
    
    download_dir = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        file_path = os.path.join(download_dir, "paper.pdf")
        # Download the file
        await download_file_async(pdf_url, file_path)
        
        # Split and send
        parts = split_file(file_path)
        for part in parts:
            with open(part, 'rb') as f:
                await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                
    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"خطا در دانلود مقاله: {e}")
    finally:
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
