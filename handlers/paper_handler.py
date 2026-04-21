import os
import uuid
import shutil
from telegram import Update
from telegram.ext import ContextTypes

from utils.search_papers import search_arxiv
from utils.download_helper import download_file_async, split_file

async def paper_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً یک عبارت برای جستجو وارد کنید!\nمثال: `/search attention is all you need`", 
            parse_mode="Markdown"
        )
        return
        
    query = " ".join(context.args)
    status_msg = await update.message.reply_text(f"🔍 در حال جستجوی مقاله:\n{query}...")
    
    papers = search_arxiv(query, max_results=1)
    
    if not papers:
        await status_msg.edit_text("❌ مقاله‌ای با لینک مستقیم PDF یافت نشد.")
        return
        
    paper = papers[0]
    pdf_url = paper['pdf_link']
    title = paper['title']
    
    await status_msg.edit_text(f"✅ مقاله یافت شد:\n*{title}*\n\n📥 در حال دانلود...", parse_mode="Markdown")
    
    # Generate a unique folder for downloading (similar to your downloader.py logic)
    task_id = str(uuid.uuid4())
    dest_folder = os.path.join("downloads", task_id)
    os.makedirs(dest_folder, exist_ok=True)
    
    try:
        # Download the PDF using your existing async helper
        downloaded_file = await download_file_async(pdf_url, dest_folder)
        
        # Split file if it exceeds Telegram limits (unlikely for papers, but safe to include)
        parts = split_file(downloaded_file)
        
        await status_msg.edit_text("📤 در حال آپلود...")
        
        # Upload the file back to the user
        for part in parts:
            with open(part, 'rb') as f:
                await update.message.reply_document(document=f)
                
        await status_msg.edit_text("✅ مقاله با موفقیت ارسال شد.")
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در پردازش مقاله:\n{e}")
        
    finally:
        # Clean up the downloaded files
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder, ignore_errors=True)
