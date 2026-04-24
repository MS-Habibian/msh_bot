import asyncio
import os
import time
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.podcast_helper import search_podcast_async, download_podcast_async
from utils.download_helper import format_size, split_media_playable
from handlers.downloader import cleanup_folder_job

async def podcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام پادکست را وارد کنید!\n*نحوه استفاده:* `/podcast <نام پادکست>`", parse_mode="Markdown")
        return

    query_str = " ".join(context.args)
    status_msg = await update.message.reply_text("🔍 در حال جستجوی پادکست...")

    try:
        # جستجو و دریافت ۵۰ نتیجه
        results = await search_podcast_async(query_str, limit=50)
        if not results:
            await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
            return

        # ذخیره نتایج در کش برای صفحه‌بندی
        if 'podcast_cache' not in context.bot_data:
            context.bot_data['podcast_cache'] = {}
        context.bot_data['podcast_cache'][query_str] = results

        await send_podcast_page(status_msg, query_str, 0, context)

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")

async def send_podcast_page(message, query_str: str, offset: int, context: ContextTypes.DEFAULT_TYPE):
    """تابع کمکی برای نمایش یک صفحه از نتایج (۵ تایی)"""
    results = context.bot_data['podcast_cache'].get(query_str, [])
    page_results = results[offset : offset + 5]

    if not page_results:
        await message.edit_text("❌ نتیجه بیشتری یافت نشد.")
        return

    # کیبورد شامل دکمه‌های دانلود
    keyboard = []
    text = f"🎙 *نتایج جستجوی پادکست:*\n`{query_str}`\n\n"
    
    for i, pod in enumerate(page_results, start=offset + 1):
        text += f"{i}. 🎧 {pod['title']} | 👤 {pod['artist']}\n"
        # ذخیره لینک در bot_data تا نیاز نباشد لینک طولانی را در callback_data بفرستیم
        context.bot_data[f"podlink_{pod['id']}"] = pod['url']
        keyboard.append([InlineKeyboardButton(f"📥 دانلود #{i}", callback_data=f"poddl:{pod['id']}")])

    # دکمه‌های ناوبری (صفحه قبل و بعد)
    nav_row = []
    if offset >= 5:
        nav_row.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"podmore:{offset - 5}:{query_str}"))
    if offset + 5 < len(results):
        nav_row.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"podmore:{offset + 5}:{query_str}"))
    
    if nav_row:
        keyboard.append(nav_row)

    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_pod_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split(":")

    if data[0] == "podmore":
        offset = int(data[1])
        query_str = data[2]
        await send_podcast_page(query.message, query_str, offset, context)
        return

    elif data[0] == "poddl":
        pod_id = data[1]
        pod_url = context.bot_data.get(f"podlink_{pod_id}")
        
        if not pod_url:
            await query.edit_message_text("❌ لینک این پادکست در سرور منقضی شده است. لطفاً دوباره جستجو کنید.")
            return

        file_id = str(uuid.uuid4())
        download_folder = os.path.join("downloads", file_id)
        
        await query.edit_message_text("⏳ در حال دانلود پادکست...\nاین کار ممکن است چند دقیقه زمان ببرد.")

        loop = asyncio.get_running_loop()
        
        # Use a list to store the last update time so we can modify it inside the inner function
        last_update_time = [0.0]

        def update_progress(downloaded, total):
            current_time = time.time()
            # Only update Telegram every 2 seconds, OR if the download is completely finished
            if current_time - last_update_time[0] < 2.0 and downloaded < total:
                return
            
            last_update_time[0] = current_time

            async def _do_update():
                try:
                    if total > 0:
                        percent = (downloaded / total) * 100
                        text = f"⬇️ *در حال دانلود پادکست...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
                    else:
                        text = f"⬇️ *در حال دانلود پادکست...*\nدانلود شده: `{format_size(downloaded)}`"
                    await query.edit_message_text(text=text, parse_mode="Markdown")
                except Exception:
                    pass 
            
            asyncio.run_coroutine_threadsafe(_do_update(), loop)

        try:
            # دانلود پادکست
            filepath = await download_podcast_async(pod_url, download_folder, progress_callback=update_progress)
            await query.edit_message_text("✂️ در حال پردازش فایل و آماده‌سازی برای ارسال...")
            
            part_files = split_media_playable(filepath)

            context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

            await query.edit_message_text(f"✅ *پردازش کامل شد!*\n\n📂 تعداد بخش‌ها: `{len(part_files)}`\n☁️ *در حال آپلود...*", parse_mode="Markdown")

            for i, part_path in enumerate(part_files):
                try:
                    with open(part_path, "rb") as f:
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=f,
                            caption=f"🎧 پادکست - بخش {i+1} از {len(part_files)}",
                            read_timeout=120, write_timeout=300, connect_timeout=120,
                            reply_to_message_id=query.message.message_id
                        )
                except Exception as e:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ آپلود بخش {i+1} ناموفق بود.\n{str(e)}")

        except Exception as e:
            error_text = f"❌ *خطا در دانلود پادکست:*\n`{str(e)}`"
            try:
                await query.edit_message_text(text=error_text, parse_mode="Markdown")
            except:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text, parse_mode="Markdown")