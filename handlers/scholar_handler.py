from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.scholar_utils import search_papers_combined, user_search_cache
from utils.download_helper import download_file_async, split_file
import os
import uuid
import shutil

async def scholar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /scholar <query> - Search for academic papers
    """
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "لطفاً عنوان یا کلمات کلیدی مقاله را وارد کنید.\n"
            "مثال: /scholar attention is all you need"
        )
        return
    
    query = ' '.join(context.args)
    loading_msg = await update.message.reply_text("🔍 در حال جستجو...")
    
    # Use combined search (Semantic Scholar + Google fallback)
    results = search_papers_combined(query, chat_id)
    
    if not results:
        await loading_msg.edit_text("❌ هیچ نتیجه‌ای یافت نشد.")
        return
    
    # Format results
    message = f"📚 نتایج جستجو برای: {query}\n\n"
    keyboard = []
    
    for item in results:
        title = item['title']
        author = item['author']
        year = item['year']
        pdf_available = "✅ PDF موجود" if item['pdf_url'] else "❌ PDF ناموجود"
        source = item.get('source', 'Semantic Scholar')
        
        message += f"📄 {title}\n"
        message += f"👤 {author} ({year})\n"
        message += f"📥 {pdf_available}\n"
        message += f"🔗 منبع: {source}\n\n"
        
        # Add download button only if PDF exists
        if item['pdf_url']:
            keyboard.append([
                InlineKeyboardButton(
                    f"دانلود: {title[:30]}...",
                    callback_data=f"dl_{item['id']}"
                )
            ])
    
    await loading_msg.edit_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )


async def handle_scholar_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle paper download button clicks
    """
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    paper_id = int(query.data.split('_')[1])
    
    # Get cached results
    if chat_id not in user_search_cache:
        await query.edit_message_text("❌ نتایج منقضی شده. لطفاً دوباره جستجو کنید.")
        return
    
    results = user_search_cache[chat_id]
    if paper_id >= len(results):
        await query.edit_message_text("❌ مقاله یافت نشد.")
        return
    
    paper = results[paper_id]
    pdf_url = paper.get('pdf_url')
    
    if not pdf_url:
        await query.edit_message_text("❌ لینک PDF موجود نیست.")
        return
    
    # Create temp download folder
    download_folder = f"downloads/{uuid.uuid4()}"
    os.makedirs(download_folder, exist_ok=True)
    
    progress_msg = await query.edit_message_text(
        f"📥 در حال دانلود: {paper['title'][:50]}...\n⏳ 0%"
    )
    
    async def update_progress(current, total):
        percent = int((current / total) * 100) if total > 0 else 0
        try:
            await progress_msg.edit_text(
                f"📥 در حال دانلود: {paper['title'][:50]}...\n⏳ {percent}%"
            )
        except:
            pass
    
    try:
        # Download PDF
        filepath = await download_file_async(pdf_url, download_folder, progress_callback=update_progress)
        
        if not filepath or not os.path.exists(filepath):
            await progress_msg.edit_text("❌ دانلود ناموفق بود.")
            shutil.rmtree(download_folder, ignore_errors=True)
            return
        
        # Split file if needed
        parts = split_file(filepath)
        
        # Schedule cleanup
        context.job_queue.run_once(
            cleanup_folder_job,
            5 * 3600,
            data=download_folder
        )
        
        # Upload parts
        for idx, part_path in enumerate(parts):
            file_id = str(uuid.uuid4())
            keyboard = [[
                InlineKeyboardButton("🔄 آپلود مجدد", callback_data=f"reup:{file_id}:{idx}")
            ]]
            
            with open(part_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    filename=os.path.basename(part_path),
                    caption=f"📄 {paper['title']}\nقسمت {idx + 1}/{len(parts)}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        
        await progress_msg.delete()
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ خطا: {str(e)}")
        shutil.rmtree(download_folder, ignore_errors=True)


def cleanup_folder_job(context):
    """Delete download folder after timeout"""
    folder = context.job.data
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)


# Handlers to register in main.py
scholar_handler = CommandHandler('scholar', scholar_command)
scholar_download_handler = CallbackQueryHandler(
    handle_scholar_download_callback,
    pattern=r'^dl_\d+$'
)
