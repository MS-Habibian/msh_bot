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

    # ارسال context به تابع
    await send_podcast_results(update.message, context, query, offset=0)

async def send_podcast_results(message, context, query, offset):
    loading_msg = await message.reply_text(f"در حال جستجو برای: {query} (نتایج {offset+1} تا {offset+5})...")
    
    results = await search_podcast_async(query, limit=5, offset=offset)
    
    if not results:
        await loading_msg.edit_text("❌ پادکستی با این نام یافت نشد.")
        return

    # استفاده از bot_data برای ذخیره کش به جای message.bot
    if 'podcast_cache' not in context.bot_data:
        context.bot_data['podcast_cache'] = {}

    text = f"🎧 نتایج جستجو برای: {query}\n\n"
    keyboard = []
    
    for i, res in enumerate(results, 1):
        text += f"{i}. {res['title']}\n🎙 {res['podcast_name']}\n\n"
        keyboard.append([InlineKeyboardButton(f"📥 دانلود شماره {i}", callback_data=f"poddl:{res['id']}")])
        
        # ذخیره لینک در کش
        if res['audio_url']:
            context.bot_data['podcast_cache'][str(res['id'])] = res['audio_url']

    safe_query = query[:20] 
    keyboard.append([InlineKeyboardButton("⬇️ نتایج بعدی", callback_data=f"podmore:{offset+5}:{safe_query}")])

    await loading_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pod_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("podmore:"):
        parts = data.split(':', 2)
        offset = int(parts[1])
        search_query = parts[2]
        
        # ارسال context به تابع در فراخوانی مجدد
        await send_podcast_results(query.message, context, search_query, offset)

    elif data.startswith("poddl:"):
        track_id = data.split(":")[1]
        
        # خواندن از کش با استفاده از bot_data
        audio_url = context.bot_data.get('podcast_cache', {}).get(track_id)
        
        if not audio_url:
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
            os.remove(file_path)
        except Exception as e:
            logger.error(f"Download/Send error: {e}")
            await status_msg.edit_text("❌ خطایی در طول دانلود یا ارسال رخ داد.")
