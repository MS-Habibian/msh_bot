import os
import uuid
import shutil
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# توابع ایمپورت شده بر اساس ساختار شما
from utils.youtube_helper import search_youtube_async, get_youtube_qualities_async, download_youtube_video_async
from utils.download_helper import format_size, split_file, split_media_playable
from handlers.downloader import cleanup_folder_job


def extract_yt_video_id(url: str):
    pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

# --- 1. دستور جستجوی یوتیوب ---
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

        keyboard = []
        text = "🎥 *نتایج جستجوی یوتیوب:*\n\n"
        for index, video in enumerate(results, start=1):
            text += f"{index}. {video['title']}\n"
            # انتقال به مرحله انتخاب کیفیت با ytfmt
            btn = InlineKeyboardButton(f"انتخاب کیفیت #{index}", callback_data=f"ytfmt:{video['id']}")
            keyboard.append([btn])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

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
        # دریافت کیفیت‌ها همانند سرچ
        resolutions = await get_youtube_qualities_async(video_url)
        
        if not resolutions:
            await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
            return

        keyboard = []
        row = []
        for res in resolutions:
            btn = InlineKeyboardButton(f"🎬 {res}p", callback_data=f"ytdl:{video_id}:{res}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        keyboard.append([
            InlineKeyboardButton("🌟 بهترین کیفیت", callback_data=f"ytdl:{video_id}:best"),
            InlineKeyboardButton("🎵 فقط صدا", callback_data=f"ytdl:{video_id}:audio")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(
            text=f"🎥 ویدیو پیدا شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`https://www.youtube.com/watch?v={video_id}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


# --- 2. هندلر نمایش کیفیت‌ها ---
async def handle_yt_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, video_id = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    chat_id = update.effective_chat.id
    message_id = query.message.message_id

    await context.bot.edit_message_text(
        chat_id=chat_id, message_id=message_id,
        text="⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.",
    )

    try:
        resolutions = await get_youtube_qualities_async(video_url)
        
        if not resolutions:
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id,
                text="❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست."
            )
            return

        keyboard = []
        row = []
        # ساخت دکمه برای هر رزولوشن (مثلا 360, 720, 1080)
        for res in resolutions:
            btn = InlineKeyboardButton(f"🎬 {res}p", callback_data=f"ytdl:{video_id}:{res}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        # دکمه دانلود بهترین کیفیت (ادغام شده پیش‌فرض)
        keyboard.append([InlineKeyboardButton("🌟 بهترین کیفیت (Best)", callback_data=f"ytdl:{video_id}:best")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"🎥 ویدیو پیدا شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`{video_url}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


# --- 3. هندلر دانلود و اسپلیت (تکه کردن) ---
async def handle_yt_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # استخراج آیدی و کیفیت
    _, video_id, quality = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # تبدیل کیفیت انتخابی به فرمت استاندارد yt-dlp
    if quality == 'best':
        format_str = 'b'
    elif quality == 'audio':
        # اولویت با فرمت m4a است که در تلگرام بهترین پشتیبانی را برای پخش مستقیم دارد
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        # فرمول: بهترین ویدیوی کوچکتر یا مساوی این رزولوشن + بهترین صدا / یا بهترین کیفیت تکی این رزولوشن
        format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    chat_id = update.effective_chat.id
    message_id = query.message.message_id
    
    quality_text = "صدا 🎵" if quality == 'audio' else f"ویدیو {quality}p" if quality != 'best' else "بهترین کیفیت"
    
    await context.bot.edit_message_text(
        chat_id=chat_id, message_id=message_id,
        text=f"⏳ در حال دانلود از یوتیوب ({quality_text})...\n`{video_url}`", 
        parse_mode="Markdown"
    )

    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nدانلود شده: `{format_size(downloaded)}`"
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, parse_mode="Markdown")
        except Exception:
            pass # نادیده گرفتن خطای بله

    try:
        # دانلود با کیفیت مشخص شده
        filepath = await download_youtube_video_async(video_url, download_folder, format_str, progress_callback=update_progress)

        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text="✂️ در حال پردازش و تقسیم فایل به تکه‌های زیر ۲۰ مگابایت..."
        )
        
        # ------------------ تغییر اصلی در این قسمت است ------------------
        if quality == 'audio':
            part_files = split_media_playable(filepath)
        else:
            part_files = split_file(filepath)
        # ----------------------------------------------------------------

        context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

        keyboard = []
        row = []
        for i, part in enumerate(part_files):
            btn = InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}")
            row.append(btn)
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.edit_message_text(
            chat_id=chat_id, message_id=message_id,
            text=f"✅ *پردازش کامل شد!*\n\n📂 تعداد بخش‌ها: `{len(part_files)}`\n☁️ *در حال آپلود بخش‌ها...*",
            reply_markup=reply_markup, parse_mode="Markdown"
        )

        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    # ------------------ تغییر برای ارسال فایل صوتی ------------------
                    if quality == 'audio':
                        await context.bot.send_audio(
                            chat_id=chat_id,
                            audio=f,
                            caption=f"🎵 بخش {i+1} از {len(part_files)}",
                            read_timeout=120, write_timeout=300, connect_timeout=120,
                            reply_to_message_id=message_id 
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=chat_id,
                            document=f,
                            caption=f"🎥 بخش {i+1} از {len(part_files)}",
                            read_timeout=120, write_timeout=300, connect_timeout=120,
                            reply_to_message_id=message_id 
                        )
                    # ----------------------------------------------------------------
            except Exception:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ آپلود بخش {i+1} ناموفق بود.")

    except Exception as e:
        error_text = f"❌ *خطا در دانلود ویدیو:*\n`{str(e)}`"
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=error_text, parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=chat_id, text=error_text, parse_mode="Markdown")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)

