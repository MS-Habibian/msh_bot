import os
import uuid
import shutil
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.youtube_helper import search_youtube_async, get_youtube_qualities_async, download_youtube_video_async
from utils.download_helper import format_size, split_media_playable, split_file_rar
from handlers.downloader import cleanup_folder_job

def extract_yt_video_id(url: str) -> str | None:
    pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def _build_quality_keyboard(video_id: str, resolutions: list) -> InlineKeyboardMarkup:
    """Helper function to build the resolution keyboard."""
    keyboard = []
    row = []
    for res in resolutions:
        row.append(InlineKeyboardButton(f"🎬 {res}p", callback_data=f"ytdl:{video_id}:{res}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([
        InlineKeyboardButton("🌟 بهترین کیفیت", callback_data=f"ytdl:{video_id}:best"),
        InlineKeyboardButton("🎵 فقط صدا", callback_data=f"ytdl:{video_id}:audio")
    ])
    return InlineKeyboardMarkup(keyboard)

async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام ویدیو را وارد کنید!\n*نحوه استفاده:* `/yt <نام ویدیو>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text("🔍 در حال جستجو در یوتیوب...")

    try:
        results = await search_youtube_async(query, limit=5)
        if not results:
            await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
            return

        # Added duration to both buttons and text list
        keyboard = [[InlineKeyboardButton(f"🎬 انتخاب #{i} (⏱ {vid['duration']})", callback_data=f"ytfmt:{vid['id']}")] 
                    for i, vid in enumerate(results, start=1)]
        
        text = "🎥 *نتایج جستجوی یوتیوب:*\n\n" + "\n".join([f"{i}. ⏱ `{vid['duration']}` | {vid['title']}" for i, vid in enumerate(results, start=1)])
        
        await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")


async def ytdl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً لینک یوتیوب را وارد کنید!\n*نحوه استفاده:* `/ytdl <لینک یوتیوب>`", parse_mode="Markdown")
        return

    video_url = context.args[0]
    video_id = extract_yt_video_id(video_url)
    
    if not video_id:
        await update.message.reply_text("❌ لینک وارد شده نامعتبر است یا آیدی ویدیو یافت نشد.")
        return

    status_msg = await update.message.reply_text("⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.")

    try:
        resolutions = await get_youtube_qualities_async(video_url)
        if not resolutions:
            await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
            return

        reply_markup = _build_quality_keyboard(video_id, resolutions)
        await status_msg.edit_text(
            text=f"🎥 ویدیو پیدا شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`https://www.youtube.com/watch?v={video_id}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


async def handle_yt_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, video_id = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # KEY CHANGE: Send a NEW message instead of editing the search results
    status_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.",
        reply_to_message_id=query.message.message_id
    )

    try:
        resolutions = await get_youtube_qualities_async(video_url)
        if not resolutions:
            await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
            return

        reply_markup = _build_quality_keyboard(video_id, resolutions)
        await status_msg.edit_text(
            text=f"🎥 ویدیو انتخاب شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`{video_url}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


async def handle_yt_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, video_id, quality = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    if quality == 'best':
        format_str = 'b'
    elif quality == 'audio':
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    quality_text = "صدا 🎵" if quality == 'audio' else f"ویدیو {quality}p" if quality != 'best' else "بهترین کیفیت"
    
    await query.edit_message_text(text=f"⏳ در حال دانلود از یوتیوب ({quality_text})...\n`{video_url}`", parse_mode="Markdown")

    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nدانلود شده: `{format_size(downloaded)}`"
            await query.edit_message_text(text=text, parse_mode="Markdown")
        except Exception:
            pass 

    try:
        filepath = await download_youtube_video_async(video_url, download_folder, format_str, progress_callback=update_progress)
        await query.edit_message_text("✂️ در حال پردازش و تقسیم فایل به تکه‌های زیر ۲۰ مگابایت...")
        
        part_files = split_media_playable(filepath) if quality == 'audio' else split_file_rar(filepath)

        context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

        buttons = [InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}") for i in range(len(part_files))]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        
        await query.edit_message_text(
            text=f"✅ *پردازش کامل شد!*\n\n📂 تعداد بخش‌ها: `{len(part_files)}`\n☁️ *در حال آپلود بخش‌ها...*",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    send_kwargs = {
                        "chat_id": update.effective_chat.id,
                        "caption": f"{'🎵' if quality == 'audio' else '🎥'} بخش {i+1} از {len(part_files)}",
                        "read_timeout": 120, "write_timeout": 300, "connect_timeout": 120,
                        "reply_to_message_id": query.message.message_id
                    }
                    if quality == 'audio':
                        await context.bot.send_audio(audio=f, **send_kwargs)
                    else:
                        await context.bot.send_document(document=f, **send_kwargs)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ آپلود بخش {i+1} ناموفق بود.")

    except Exception as e:
        error_text = f"❌ *خطا در دانلود ویدیو:*\n`{str(e)}`"
        try:
            await query.edit_message_text(text=error_text, parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text, parse_mode="Markdown")
