import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.podcast_helper import search_podcast_async, get_podcast_url_async, download_podcast_async

DOWNLOAD_FOLDER = "downloads"

async def pod_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /podcast"""
    if not context.args:
        await update.message.reply_text("❌ لطفا نام پادکست را وارد کنید. مثال:\n`/podcast channel b`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text("🔎 در حال جستجوی پادکست...")

    results = await search_podcast_async(query, limit=5)
    if not results:
        await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
        return

    # ساخت کیبورد شیشه‌ای با فرمت poddl:ID
    keyboard = [
        [InlineKeyboardButton(f"🎧 انتخاب #{i} (⏱ {pod['duration']})", callback_data=f"poddl:{pod['id']}")]
        for i, pod in enumerate(results, start=1)
    ]

    text = "🎙 *نتایج جستجوی پادکست:* \n\n" + "\n".join(
        [f"{i}. ⏱ `{pod['duration']}` | {pod['title']}" for i, pod in enumerate(results, start=1)]
    )

    await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_pod_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دانلود پادکست هنگام کلیک کاربر روی نتایج"""
    query = update.callback_query
    await query.answer()

    # استخراج ID از Callback Data
    _, track_id = query.data.split(":")

    await query.edit_message_text("⏳ در حال دریافت اطلاعات پادکست...")

    # به دست آوردن لینک دانلود
    audio_url = await get_podcast_url_async(track_id)
    if not audio_url:
        await query.edit_message_text("❌ خطا در دریافت لینک پادکست.")
        return

    await query.edit_message_text("⏳ در حال دانلود پادکست (لطفا صبور باشید)...")

    # تابع محلی برای بروزرسانی درصد پیشرفت (دقیقا مشابه یوتیوب)
    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                text = f"⏳ در حال دانلود پادکست...\n\n📊 پیشرفت: {percent:.1f}%\n💾 {mb_downloaded:.1f}MB از {mb_total:.1f}MB"
                await query.edit_message_text(text)
        except Exception:
            pass

    try:
        # فراخوانی دانلودر
        filepath = await download_podcast_async(audio_url, DOWNLOAD_FOLDER, progress_callback=update_progress)

        await query.edit_message_text("✅ دانلود تمام شد. در حال ارسال فایل به تلگرام...")

        # ارسال فایل صوتی به صورت Native در تلگرام
        with open(filepath, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=audio_file,
                caption="🎧 پادکست شما آماده است!",
                read_timeout=120,
                write_timeout=120
            )

        # پاک کردن فایل و پیام وضعیت بعد از ارسال موفق
        os.remove(filepath)
        await query.delete_message()

    except Exception as e:
        await query.edit_message_text(f"❌ خطا در دانلود یا ارسال: {e}")
