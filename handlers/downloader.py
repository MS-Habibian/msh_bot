# handlers/downloader.py
import os
import shutil
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from utils.download_helper import download_file_async, format_size, split_file


# --- تابع پاکسازی صف کار ---
async def cleanup_folder_job(context: ContextTypes.DEFAULT_TYPE):
    folder_path = context.job.data
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"🗑️ پاک شد: {folder_path}")


# --- دستور اصلی دانلود ---
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً یک لینک وارد کنید!\n*نحوه استفاده:* `/dl <link>`",
            parse_mode="Markdown",
        )
        return

    url = context.args[0]
    file_id = str(uuid.uuid4())  # یک شناسه یکتا برای این دانلود تولید می‌کند
    download_folder = os.path.join("downloads", file_id)

    # status_msg = await update.message.reply_text("🔍 در حال بررسی و دانلود...")
    status_msg = await update.message.reply_text("🔍 در حال بررسی و دانلود...")

    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *در حال دانلود...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *در حال دانلود...*\nدانلود شده: `{format_size(downloaded)}` (حجم کل نامشخص است)"

            await status_msg.edit_text(text, parse_mode="Markdown")
        except BadRequest:
            pass

    try:
        # 1. فایل را در پوشه یکتای مربوطه دانلود کن
        filepath = await download_file_async(
            url, download_folder, progress_callback=update_progress
        )
        # آماده‌سازی مرحله آپلود

        # 2. اگر فایل بیشتر از 49 مگابایت بود آن را تقسیم کن
        await status_msg.edit_text("✂️ در حال پردازش و تقسیم فایل (در صورت نیاز)...")
        part_files = split_file(filepath)

        # 3. حذف پوشه را برای 1 ساعت بعد زمان‌بندی کن (3600 ثانیه)
        context.job_queue.run_once(
            cleanup_folder_job,
            5 * 3600,
            data=download_folder,
            name=f"cleanup_{file_id}",
        )

        # 4. ساخت کیبورد شیشه‌ای برای تلاش مجدد
        keyboard = []
        row = []
        for i, part in enumerate(part_files):
            # فرمت callback_data: reupload:file_id:index
            btn = InlineKeyboardButton(
                f"Part {i+1}", callback_data=f"reup:{file_id}:{i}"
            )
            row.append(btn)
            if len(row) == 3:  # 3 دکمه در هر ردیف
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 5. ارسال پیام خلاصه
        await status_msg.edit_text(
            f"✅ *دانلود کامل شد!*\n\n"
            f"📂 تعداد بخش‌ها: `{len(part_files)}`\n"
            f"⏳ فایل‌ها به مدت ۵ ساعت روی سرور نگه‌داری می‌شوند.\n"
            f"☁️ *اکنون بخش‌ها به‌صورت خودکار در حال آپلود هستند...*\n"
            f"_(اگر آپلود بخشی ناموفق بود، از دکمه‌های زیر برای تلاش مجدد استفاده کنید)_",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # 6. آپلود خودکار تمام بخش‌ها
        for i, part_path in enumerate(part_files):
            try:
                # await context.bot.send_chat_action(
                #     chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
                # )
                with open(part_path, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        caption=f"بخش {i+1} از {len(part_files)}",
                        read_timeout=120,
                        write_timeout=120,
                        connect_timeout=120,
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ آپلود خودکار بخش {i+1} ناموفق بود. لطفاً از دکمه بالا برای تلاش مجدد استفاده کنید."
                )
    except Exception as e:
        await status_msg.edit_text(f"❌ *خطا:*\n`{str(e)}`", parse_mode="Markdown")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)


# --- هندلر callback query برای تلاش مجدد ---
async def handle_reupload_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass # کلیک روی دکمه را تأیید می‌کند

    # callback_data را تجزیه می‌کند (مثلاً "reup:UUID:0")
    _, file_id, part_index_str = query.data.split(":")
    part_index = int(part_index_str)

    download_folder = os.path.join("downloads", file_id)

    # بررسی می‌کند که پوشه هنوز وجود دارد (توسط JobQueue حذف نشده باشد)
    if not os.path.exists(download_folder):
        await query.message.reply_text("⚠️ این فایل منقضی شده و از سرور حذف شده است.")
        return

    # فایل بخش موردنظر را در پوشه پیدا می‌کند
    files_in_dir = sorted(os.listdir(download_folder))
    if part_index >= len(files_in_dir):
        await query.message.reply_text("⚠️ در پیدا کردن این بخش از فایل خطایی رخ داد.")
        return

    part_filename = files_in_dir[part_index]
    part_path = os.path.join(download_folder, part_filename)

    # آپلود بخش درخواستی
    msg = await query.message.reply_text(f"☁️ در حال آپلود مجدد بخش {part_index + 1}...")
    try:
        # await context.bot.send_chat_action(
        #     chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
        # )
        with open(part_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                caption=f"تلاش مجدد دستی: بخش {part_index + 1}",
                read_timeout=120,
                write_timeout=300,
                connect_timeout=120,
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(
            f"❌ آپلود دوباره ناموفق بود: `{str(e)}`", parse_mode="Markdown"
        )
