from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.search_papers import search_semantic_scholar
import uuid
import os
from utils.search_papers import get_paper_pdf_url
from utils.download_helper import download_file_async, split_file

async def scholar_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("⚠️ لطفاً موضوع مورد نظر را وارد کنید.\nمثال: `/scholar machine learning`", parse_mode="Markdown")
        return

    status_message = await update.message.reply_text("🔍 در حال جستجو در Semantic Scholar...")
    papers = search_semantic_scholar(query, max_results=5)

    if not papers:
        await status_message.edit_text("❌ مقاله‌ای یافت نشد یا سرور پاسخگو نبود.")
        return

    message_text = "📚 **نتایج یافت شده:**\n\n"
    keyboard = []

    for index, paper in enumerate(papers, start=1):
        title = paper.get('title', 'Unknown Title')
        authors = paper.get('formatted_authors')
        year = paper.get('year', 'N/A')
        has_pdf = bool(paper.get('openAccessPdf'))
        
        pdf_status = "🟢 فایل موجود است" if has_pdf else "🔴 نیازمند خرید (Paywall)"
        
        message_text += f"*{index}. {title}*\n"
        message_text += f"👤 نویسندگان: {authors} | 📅 سال: {year}\n"
        message_text += f"📄 وضعیت: {pdf_status}\n\n"

        # Only add a download button if a free PDF is available
        if has_pdf:
            paper_id = paper.get('paperId')
            # Using 'schdl|' prefix to keep callback data short
            button = InlineKeyboardButton(f"📥 دانلود مقاله {index}", callback_data=f"schdl|{paper_id}")
            keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await status_message.edit_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)



async def scholar_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Acknowledge the button click immediately

    # Extract paper ID from callback_data (format: "schdl|<paperId>")
    paper_id = query.data.split("|")[1]
    
    await query.edit_message_text("🔍 در حال یافتن لینک مستقیم PDF...")
    
    pdf_url = get_paper_pdf_url(paper_id)
    if not pdf_url:
        await query.edit_message_text("❌ متاسفانه لینک PDF این مقاله منقضی شده یا در دسترس نیست.")
        return

    # Create a unique download folder (reusing your bot's logic)
    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    
    async def update_progress(downloaded, total):
        # Optional: You can implement your progress bar logic here
        pass

    try:
        await query.edit_message_text("📥 در حال دانلود مقاله در سرور ربات...")
        
        # Using your existing download helper
        downloaded_filepath = await download_file_async(
            pdf_url, 
            download_folder, 
            progress_callback=update_progress
        )
        
        await query.edit_message_text("📤 در حال ارسال فایل برای شما...")
        
        # Send the file to the user
        with open(downloaded_filepath, 'rb') as doc:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=doc,
                caption="✅ مقاله شما با موفقیت دریافت شد."
            )
            
        await query.edit_message_text("✅ عملیات با موفقیت انجام شد.")

    except Exception as e:
        print(f"Download Error: {e}")
        await query.edit_message_text("❌ خطا در دانلود یا ارسال فایل.")
        
    finally:
        # Cleanup folder logic (you can schedule this via your job_queue as well)
        if os.path.exists(download_folder):
             for f in os.listdir(download_folder):
                 os.remove(os.path.join(download_folder, f))
             os.rmdir(download_folder)
