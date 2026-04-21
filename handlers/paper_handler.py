import os
import uuid
import shutil
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.search_papers import search_arxiv
from utils.download_helper import download_file_async, split_file

async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً یک عبارت برای جستجو وارد کنید!\nمثال: `/search attention is all you need`", parse_mode="Markdown")
        return
        
    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 در حال جستجو...\n{query}")
    
    papers = search_arxiv(query, max_results=5)
    
    if not papers:
        await status_msg.edit_text("❌ مقاله‌ای یافت نشد.")
        return
        
    text = f"📚 **نتایج جستجو برای:** {query}\n\n"
    keyboard_row = []
    
    for i, paper in enumerate(papers, 1):
        # Add paper info to the message text
        text += f"*{i}. {paper['title']}*\n"
        text += f"👨‍🔬 {paper['authors']} | 📅 {paper['year']}\n\n"
        
        # Telegram callback_data limit is 64 bytes. Arxiv URLs are short enough.
        callback_data = f"arxiv_pdf|{paper['pdf_link']}"
        keyboard_row.append(InlineKeyboardButton(str(i), callback_data=callback_data))
        
    reply_markup = InlineKeyboardMarkup([keyboard_row])
    await status_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def paper_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer() # Acknowledge the button click
    
    # Extract the PDF URL from the callback data
    pdf_url = query.data.split("|")[1]
    
    # Edit the message to show download status
    await query.edit_message_text("📥 در حال دانلود مقاله انتخاب شده...")
    
    task_id = str(uuid.uuid4())
    dest_folder = os.path.join("downloads", task_id)
    os.makedirs(dest_folder, exist_ok=True)
    
    try:
        downloaded_file = await download_file_async(pdf_url, dest_folder)
        parts = split_file(downloaded_file)
        
        await query.edit_message_text("📤 در حال آپلود...")
        
        for part in parts:
            with open(part, 'rb') as f:
                # Send the document to the chat where the button was clicked
                await context.bot.send_document(chat_id=query.message.chat_id, document=f)
                
        await query.edit_message_text("✅ مقاله با موفقیت ارسال شد.")
        
    except Exception as e:
        await query.edit_message_text(f"❌ خطا در پردازش مقاله:\n{e}")
        
    finally:
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder, ignore_errors=True)
