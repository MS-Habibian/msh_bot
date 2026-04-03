# handlers/downloader.py
import os
import shutil
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from config import HOURS_TO_KEEP_FILES, SPLIT_CHUNK_SIZE
from database.models import User
from decorators.transactional_decorator import transactional_handler
from services.billing_service import BillingManager
from utils import split_file, upload_parts_to_user
from utils.clean_up_folder_job import cleanup_folder_job
from utils.download_helper import download_file_async, format_size, get_file_size_from_url
from sqlalchemy.ext.asyncio import AsyncSession


@transactional_handler()
async def download_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession,
    user: User,
    billing: BillingManager,
) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً یک لینک وارد کنید!\n*نحوه استفاده:* `/dl <link>`",
            parse_mode="Markdown",
        )
        return

    url = context.args[0]
    ### check for file size, user quota
    file_size = get_file_size_from_url()
    billing.charge(cost_bytes=file_size, action='/dl')

    # create a unique id for the file
    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)

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

    # try:
    # download the file
    filepath = await download_file_async(
        url, download_folder, progress_callback=update_progress
    )

    await status_msg.edit_text("✂️ در حال پردازش و تقسیم فایل (در صورت نیاز)...")
    
    # split the file into chunks with appropriate sizes
    part_files = split_file(filepath, SPLIT_CHUNK_SIZE)

    # schedule deletion in couple of hours
    context.job_queue.run_once(
        cleanup_folder_job,
        HOURS_TO_KEEP_FILES * 3600,
        data=download_folder,
        name=f"cleanup_{file_id}",
    )

    await upload_parts_to_user(update, file_id, part_files, status_msg)
    # except Exception as e:
    #     await status_msg.edit_text(f"❌ *خطا:*\n`{str(e)}`", parse_mode="Markdown")
    #     if os.path.exists(download_folder):
    #         shutil.rmtree(download_folder)


# --- هندلر callback query برای تلاش مجدد ---
async def handle_reupload_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()  # کلیک روی دکمه را تأیید می‌کند

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
