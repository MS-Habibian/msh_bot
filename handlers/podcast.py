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
        await query.edit_message_reply_markup(reply_markup=None)
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



async def podchannel_command(update, context):
    """
    Allows users to search a specific podcast channel.
    Usage: /podchannel <Podcast Name> | <Search Term>
    Example: /podchannel TED Radio Hour | space
    """
    try:
        # Extract the text after the command
        user_input = update.message.text.split(maxsplit=1)[1]
        
        # Split by a separator like '|' or '-'
        if '|' in user_input:
            channel_name, search_term = user_input.split('|', 1)
        else:
            await update.message.reply_text("Please use the format: /podchannel Podcast Name | Search Term\nExample: /podchannel TED Radio Hour | space")
            return
            
        # Clean up the strings
        channel_name = channel_name.strip()
        search_term = search_term.strip()
        
        # Combine them for the iTunes API
        combined_query = f"{channel_name} {search_term}"
        
        # Send to your existing search function
        await update.message.reply_text(f"Searching in '{channel_name}' for '{search_term}'...")
        await send_podcast_results(update, context, combined_query, offset=0)
        
    except IndexError:
        await update.message.reply_text("Please provide a search term. Example: /podchannel Ted | space")
