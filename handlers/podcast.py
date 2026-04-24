import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.podcast_helper import search_podcast_async, get_podcast_url_async, download_podcast_async
import time

logger = logging.getLogger(__name__)

async def pod_command(update, context):
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("لطفاً نام پادکست یا موضوع را وارد کنید. مثال:\n/podcast channel b")
        return

    await send_podcast_results(update.message, query, offset=0)

async def send_podcast_results(message, query, offset):
    loading_msg = await message.reply_text(f"در حال جستجو برای: {query} (نتایج {offset+1} تا {offset+5})...")
    
    results = await search_podcast_async(query, limit=5, offset=offset)
    
    if not results:
        await loading_msg.edit_text("❌ پادکستی با این نام یافت نشد.")
        return

    # ذخیره نتایج در context برای دسترسی سریع به لینک‌ها در زمان دانلود
    if not hasattr(message.bot, 'podcast_cache'):
        message.bot.podcast_cache = {}

    text = f"🎧 نتایج جستجو برای: {query}\n\n"
    keyboard = []
    
    for i, res in enumerate(results, 1):
        text += f"{i}. {res['title']}\n🎙 {res['podcast_name']}\n\n"
        # کلید کیبورد برای دانلود
        keyboard.append([InlineKeyboardButton(f"📥 دانلود شماره {i}", callback_data=f"poddl:{res['id']}")])
        
        # کش کردن لینک تا نیازی به lookup دوباره نباشد (رفع مشکل پیدا نشدن لینک)
        if res['audio_url']:
            message.bot.podcast_cache[str(res['id'])] = res['audio_url']

    # دکمه نمایش بیشتر (Next Page)
    # محدود کردن طول کوئری در کال‌بک دیتا تا به لیمیت 64 بایت تلگرام نخورد
    safe_query = query[:20] 
    keyboard.append([InlineKeyboardButton("⬇️ نتایج بعدی", callback_data=f"podmore:{offset+5}:{safe_query}")])

    await loading_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pod_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("podmore:"):
        # مدیریت دکمه نتایج بعدی
        parts = data.split(':', 2)
        offset = int(parts[1])
        search_query = parts[2]
        
        # فراخوانی مجدد برای ارسال پیام جدید شامل 5 نتیجه بعدی
        await send_podcast_results(query.message, search_query, offset)

    elif data.startswith("poddl:"):
        # مدیریت دکمه دانلود
        track_id = data.split(":")[1]
        
        # ابتدا بررسی می‌کنیم لینک در کش موجود است یا خیر
        audio_url = getattr(context.bot, 'podcast_cache', {}).get(track_id)
        
        if not audio_url:
            # اگر در کش نبود، تلاش برای گرفتن لینک از API
            audio_url = await get_podcast_url_async(track_id)

        if not audio_url:
            await query.message.reply_text("❌ خطا در دریافت لینک پادکست. (لاگ‌ها را بررسی کنید)")
            logger.error(f"Failed to get audio URL for track_id: {track_id}")
            return

        status_msg = await query.message.reply_text("⏳ در حال دانلود پادکست...")
        
        last_edit_time = 0
        async def update_progress(current, total):
            nonlocal last_edit_time
            now = time.time()
            if now - last_edit_time > 3:
                percent = (current / total) * 100 if total else 0
                try:
                    await status_msg.edit_text(f"⏳ در حال دانلود...\nپیشرفت: {percent:.1f}%")
                    last_edit_time = now
                except:
                    pass

        output_dir = "downloads"
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            file_path = await download_podcast_async(audio_url, output_dir, update_progress)
            await status_msg.edit_text("✅ دانلود کامل شد. در حال ارسال...")
            
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=open(file_path, 'rb'),
                title="Podcast Episode",
                performer="Podcast Bot"
            )
            await status_msg.delete()
            os.remove(file_path) # پاک کردن فایل محلی پس از ارسال
        except Exception as e:
            logger.error(f"Download/Send error: {e}")
            await status_msg.edit_text("❌ خطایی در طول دانلود یا ارسال رخ داد.")
