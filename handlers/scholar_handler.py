# handlers/scholar_handler.py
import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# ایمپورت توابع از utils
from utils.scholar_utils import search_semantic_scholar, user_search_cache
from utils.download_helper import download_file_async, format_size, split_file

# ایمپورت جاب پاکسازی از دانلودر (با فرض وجود این تابع در downloader.py شما)
from handlers.downloader import cleanup_folder_job

async def scholar_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /scholar برای جستجوی مقاله"""
    chat_id = update.effective_chat.id
    query = " ".join(context.args)
    
    if not query:
        await update.message.reply_text("لطفاً عنوان مقاله یا کلمات کلیدی را بعد از دستور وارد کنید.\nمثال:\n/scholar attention is all you need")
        return

    loading_msg = await update.message.reply_text("🔍 در حال جستجوی مقاله در Semantic Scholar...")
    
    results = search_semantic_scholar(query, chat_id)
    
    if not results:
        await loading_msg.edit_text("❌ مقاله‌ای یافت نشد یا خطایی در ارتباط با سرور رخ داد.")
        return

    # ساخت پیام و دکمه‌های شیشه‌ای
    text = "📚 **نتایج جستجو:**\n\n"
    keyboard = []
    row = []
    
    for item in results:
        has_pdf = "✅ (PDF دارد)" if item['pdf_url'] else "❌ (فقط چکیده)"
        text += f"{item['id'] + 1}. **{item['title']}**\n👤 {item['author']} ({item['year']}) - {has_pdf}\n\n"
        
        # فقط برای مقالاتی که PDF دارند دکمه دانلود می‌گذاریم
        if item['pdf_url']:
            row.append(InlineKeyboardButton(str(item['id'] + 1), callback_data=f"dl_{item['id']}"))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    if not keyboard:
        text += "\n⚠️ متاسفانه هیچکدام از مقالات لینک مستقیم رایگان (Open Access) نداشتند."

    await loading_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def handle_scholar_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه‌های دانلود مقاله"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    try:
        article_index = int(query.data.split("_")[1])
    except ValueError:
        return

    # دریافت اطلاعات مقاله از کش
    user_results = user_search_cache.get(chat_id, [])
    if not user_results or article_index >= len(user_results):
        await query.message.reply_text("❌ نشست شما منقضی شده است. لطفاً دوباره جستجو کنید.")
        return
        
    article = user_results[article_index]
    pdf_url = article.get('pdf_url')
    
    if not pdf_url:
        await query.message.reply_text("❌ لینک مستقیم PDF برای این مقاله موجود نیست.")
        return

    # ساخت پوشه موقت برای دانلود
    unique_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", unique_id)
    os.makedirs(download_folder, exist_ok=True)
    
    progress_message = await query.message.reply_text("⬇️ در حال دانلود مقاله...")

    # تابع آپدیت پیشرفت برای پاس دادن به download_helper
    async def update_progress(downloaded, total):
        try:
            percent = (downloaded / total) * 100 if total else 0
            text = f"⬇️ *در حال دانلود مقاله...*\nپیشرفت: {percent:.1f}%\nحجم: {format_size(downloaded)} / {format_size(total)}"
            # برای جلوگیری از اسپم شدن API بله/تلگرام، می‌توانید شرط زمان اضافه کنید
            await progress_message.edit_text(text, parse_mode="Markdown")
        except:
            pass

    try:
        # استفاده از تابع دانلود اصلی شما
        filepath = await download_file_async(pdf_url, download_folder, progress_callback=update_progress)
        
        # استفاده از تابع برش فایل در صورت نیاز
        part_files = split_file(filepath)
        
        await progress_message.edit_text("📤 در حال آپلود فایل...")
        
        for part in part_files:
            with open(part, 'rb') as f:
                await context.bot.send_document(
                    chat_id=chat_id, 
                    document=f,
                    caption=f"📄 {article['title']}"
                )
                
        await progress_message.delete()

    except Exception as e:
        await progress_message.edit_text(f"❌ خطا در دانلود یا آپلود مقاله:\n{str(e)}")
    finally:
        # اجرای جاب پاکسازی پوشه (۵ ساعت بعد)
        context.job_queue.run_once(
            cleanup_folder_job, 
            5 * 3600, 
            data=download_folder, 
            name=f"cleanup_{unique_id}"
        )
