# handlers/youtube.py
import os
import uuid
import shutil
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from utils.youtube_helper import search_youtube_async, download_youtube_video_async
# فرض می‌کنیم توابع split_file و format_size را دارید
from utils.download_helper import format_size, split_file
from handlers.downloader import cleanup_folder_job

# --- 1. دستور جستجوی یوتیوب ---
async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً نام ویدیو را وارد کنید!\n*نحوه استفاده:* `/yt <نام ویدیو>`",
            parse_mode="Markdown",
        )
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
            # استفاده از شناسه ویدیو در callback_data
            btn = InlineKeyboardButton(f"⬇️ دانلود #{index}", callback_data=f"ytdl:{video['id']}")
            keyboard.append([btn])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")

# --- 2. هندلر دکمه دانلود یوتیوب ---
async def handle_yt_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # استخراج آیدی ویدیو
    _, video_id = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    
    status_msg = await query.edit_message_text(f"⏳ در حال آماده‌سازی برای دانلود از یوتیوب...\n`{video_url}`", parse_mode="Markdown")

    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *در حال دانلود از یوتیوب...*\nدانلود شده: `{format_size(downloaded)}`"
            await status_msg.edit_text(text, parse_mode="Markdown")
        except BadRequest:
            pass # نادیده گرفتن خطای آپدیت تکراری پیام تلگرام

    try:
        # 1. دانلود ویدیو با yt-dlp
        filepath = await download_youtube_video_async(
            video_url, download_folder, progress_callback=update_progress
        )

        # 2. تقسیم فایل در صورت نیاز (دقیقاً مشابه منطق قبلی شما)
        await status_msg.edit_text("✂️ در حال پردازش و تقسیم فایل ویدیو (در صورت نیاز)...")
        part_files = split_file(filepath)

        # 3. زمان‌بندی حذف پوشه
        context.job_queue.run_once(
            cleanup_folder_job,
            5 * 3600,
            data=download_folder,
            name=f"cleanup_{file_id}",
        )

        # 4. ساخت کیبورد شیشه‌ای برای تلاش مجدد (دقیقا با فرمت قبلی شما reup:file_id:index)
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

        # 5. پیام خلاصه
        await status_msg.edit_text(
            f"✅ *دانلود ویدیو کامل شد!*\n\n"
            f"📂 تعداد بخش‌ها: `{len(part_files)}`\n"
            f"⏳ فایل‌ها به مدت ۵ ساعت روی سرور نگه‌داری می‌شوند.\n"
            f"☁️ *اکنون بخش‌ها به‌صورت خودکار در حال آپلود هستند...*",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # 6. آپلود بخش‌ها
        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    # چون ویدیو است، اگر پسوند part. ندارد میتوانید از reply_video استفاده کنید
                    # اما reply_document برای فایل‌های تکه شده (split شده) امن‌تر است
                    await query.message.reply_document(
                        document=f,
                        caption=f"🎥 بخش {i+1} از {len(part_files)}",
                        read_timeout=120,
                        write_timeout=300,
                        connect_timeout=120,
                    )
            except Exception as e:
                await query.message.reply_text(
                    f"❌ آپلود بخش {i+1} ناموفق بود. از دکمه‌های بالا برای تلاش مجدد استفاده کنید."
                )

    except Exception as e:
        print(f"Error downloading YT video: {e}")
        error_text = f"❌ *خطا در دانلود ویدیو:*\n`{str(e)}`"
        try:
            # تلاش برای ویرایش پیام قبلی
            await status_msg.edit_text(error_text, parse_mode="Markdown")
        except Exception as edit_err:
            print(f"Could not edit message: {edit_err}")
            # اگر ویرایش ناموفق بود، یک پیام جدید ارسال کن
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_text,
                parse_mode="Markdown"
            )
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)
