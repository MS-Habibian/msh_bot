import logging
import os
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from handlers.downloader import cleanup_folder_job
from utils.download_helper import split_media_playable
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

async def send_podcast_results(message, context, search_query, offset=0):
    # Fetch a larger number of results (e.g., 50) since iTunes API doesn't use offset
    # Make sure search_podcasts_async has limit=50 inside it or pass it as an argument
    all_results = await search_podcast_async(search_query) 
    
    if not all_results:
        await message.reply_text("❌ پادکستی یافت نشد.")
        return

    # Slice the results based on the current offset
    current_results = all_results[offset : offset + 5]
    
    if not current_results:
        await message.reply_text("پادکست دیگری یافت نشد.")
        return

    text = f"🔎 نتایج جستجو برای: {search_query}\n\n"
    keyboard = []
    
    for i, pod in enumerate(current_results):
        track_name = pod.get('trackName', 'Unknown')
        artist_name = pod.get('artistName', 'Unknown')
        
        # Fallback to collectionId if trackId is missing
        track_id = pod.get('trackId') or pod.get('collectionId')
        
        # Skip this result if there is no valid ID
        if not track_id:
            continue
        
        text += f"**{i + 1 + offset}.** {track_name}\n👤 {artist_name}\n\n"
        
        context.bot_data.setdefault('podcast_cache', {})[str(track_id)] = pod.get('feedUrl')
        
        keyboard.append([InlineKeyboardButton(f"📥 دانلود شماره {i + 1 + offset}", callback_data=f"poddl:{track_id}")])

    # Add the "Next 5" button ONLY if there are more results left
    if offset + 5 < len(all_results):
        next_offset = offset + 5
        keyboard.append([InlineKeyboardButton("➡️ 5 نتیجه بعدی", callback_data=f"podmore:{next_offset}:{search_query}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # If this is an edit (clicking next), edit the message. Otherwise, reply.
    if offset == 0:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_pod_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("podmore:"):
        parts = data.split(':', 2)
        offset = int(parts[1])
        search_query = parts[2]
        await send_podcast_results(query.message, context, search_query, offset)

    elif data.startswith("poddl:"):
        track_id = data.split(":")[1]
        
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

        # Create unique folder like in YouTube handler
        file_id = str(uuid.uuid4())
        output_dir = os.path.join("downloads", file_id)
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            file_path = await download_podcast_async(audio_url, output_dir, update_progress)
            await status_msg.edit_text("✂️ در حال پردازش و بررسی حجم فایل...")
            
            # Split the podcast file into playable audio chunks
            part_files = split_media_playable(file_path)
            
            # Schedule folder cleanup
            context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=output_dir, name=f"cleanup_pod_{file_id}")
            
            await status_msg.edit_text(f"✅ آماده‌سازی کامل شد. در حال ارسال {len(part_files)} بخش...")
            
            for i, part_path in enumerate(part_files):
                try:
                    with open(part_path, 'rb') as f:
                        await context.bot.send_audio(
                            chat_id=query.message.chat_id,
                            audio=f,
                            caption=f"🎧 بخش {i+1} از {len(part_files)}",
                            title=f"Podcast Part {i+1}",
                            performer="Podcast Bot",
                            read_timeout=120, 
                            write_timeout=300, 
                            connect_timeout=120
                        )
                except Exception as upload_err:
                    logger.error(f"Podcast upload error part {i+1}: {upload_err}")
                    await context.bot.send_message(chat_id=query.message.chat_id, text=f"❌ آپلود بخش {i+1} ناموفق بود.")
            
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Download/Send error: {e}")
            await status_msg.edit_text("❌ خطایی در طول دانلود یا ارسال رخ داد.")
