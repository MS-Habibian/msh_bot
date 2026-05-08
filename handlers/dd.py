import os
import shutil
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Replace these imports with your actual project structure if needed
from config import SERVER_FILES_PATH, ENCRYPTION_PASSWORD
from utils.download_helper import split_file_rar

# For safety, ensure the path is set. If config doesn't have it, fallback to /var/files
# SERVER_FILES_PATH = getattr(config, 'SERVER_FILES_PATH', '/var/files')


async def list_server_files_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lists files in the server directory and creates an inline keyboard."""
    if not os.path.exists(SERVER_FILES_PATH):
        await update.message.reply_text("❌ پوشه فایل‌های سرور یافت نشد.")
        return

    # List only files (ignore folders like 'parts')
    try:
        files = [
            f
            for f in os.listdir(SERVER_FILES_PATH)
            if os.path.isfile(os.path.join(SERVER_FILES_PATH, f))
        ]
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در خواندن پوشه: {e}")
        return

    if not files:
        await update.message.reply_text("📂 هیچ فایلی در سرور موجود نیست.")
        return

    keyboard = []
    for filename in files:
        # Note: Callback data limit is 64 bytes. If filenames are very long, this might need truncation.
        keyboard.append(
            [InlineKeyboardButton(filename, callback_data=f"select_file:{filename}")]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📥 لطفاً فایل مورد نظر خود را برای دانلود انتخاب کنید:",
        reply_markup=reply_markup,
    )


async def dd_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles the file selection, splitting into a parts folder, and auto-uploading."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("select_file:"):
        return

    filename = query.data.split(":", 1)[1]
    source_filepath = os.path.join(SERVER_FILES_PATH, filename)

    if not os.path.exists(source_filepath):
        await query.message.reply_text(
            f"❌ خطا: فایل `{filename}` دیگر در سرور وجود ندارد.", parse_mode="Markdown"
        )
        return

    parts_base_dir = os.path.join(SERVER_FILES_PATH, "parts")
    parts_folder = os.path.join(parts_base_dir, f"{filename}_parts")

    status_message = await query.message.reply_text(
        f"🔍 در حال بررسی فایل `{filename}`...", parse_mode="Markdown"
    )

    try:
        # 1. Ensure the base parts folder and specific file parts folder exist
        os.makedirs(parts_folder, exist_ok=True)

        # Check if parts already exist to skip splitting
        existing_parts = sorted(
            [
                f
                for f in os.listdir(parts_folder)
                if os.path.isfile(os.path.join(parts_folder, f))
            ]
        )

        if not existing_parts:
            await status_message.edit_text("✂️ در حال پردازش و تقسیم فایل...")

            # Copy the file to the parts folder so it splits locally in that directory
            processing_filepath = os.path.join(parts_folder, filename)
            shutil.copy2(source_filepath, processing_filepath)

            # Split the file using your helper
            split_file_rar(processing_filepath, 19.5, ENCRYPTION_PASSWORD)

            # Remove the copied original file to save space, keeping only the split parts
            if os.path.exists(processing_filepath):
                os.remove(processing_filepath)

            # Reload the list of parts after splitting
            existing_parts = sorted(
                [
                    f
                    for f in os.listdir(parts_folder)
                    if os.path.isfile(os.path.join(parts_folder, f))
                ]
            )

        if not existing_parts:
            await status_message.edit_text(
                "❌ خطا: عملیات تقسیم فایل با شکست مواجه شد."
            )
            return

        # 2. Build the inline keyboard for manual retry (using dd_reup:filename:index)
        keyboard = []
        row = []
        for i in range(len(existing_parts)):
            row.append(
                InlineKeyboardButton(
                    f"Part {i+1}", callback_data=f"dd_reup:{filename}:{i}"
                )
            )
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await status_message.edit_text(
            f"✅ فایل `{filename}` به {len(existing_parts)} بخش تقسیم شد.\n"
            f"در حال آپلود خودکار قطعات...\n\n"
            f"در صورت عدم آپلود قطعه‌ای، می‌توانید از دکمه‌های زیر استفاده کنید:",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        # 3. Auto-upload all parts
        for i, part_filename in enumerate(existing_parts):
            part_path = os.path.join(parts_folder, part_filename)
            try:
                with open(part_path, "rb") as f:
                    await query.message.reply_document(
                        document=f,
                        caption=f"📦 بخش {i+1} از {len(existing_parts)} - `{filename}`",
                        parse_mode="Markdown",
                    )
            except Exception as upload_error:
                await query.message.reply_text(
                    f"⚠️ آپلود بخش {i+1} با خطا مواجه شد. برای تلاش مجدد از دکمه‌های بالا استفاده کنید."
                )

        await query.message.reply_text("🎉 آپلود خودکار به پایان رسید!")

    except Exception as e:
        await status_message.edit_text(
            f"❌ خطای غیرمنتظره رخ داد:\n`{e}`", parse_mode="Markdown"
        )


async def handle_dd_reupload_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles requests to re-upload a specific part from the persistent parts folder."""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("dd_reup:"):
        return

    # Data format: dd_reup:filename:index
    try:
        _, filename, part_index_str = query.data.split(":", 2)
        part_index = int(part_index_str)
    except ValueError:
        await query.message.reply_text("❌ داده‌های درخواست نامعتبر است.")
        return

    parts_folder = os.path.join(SERVER_FILES_PATH, "parts", f"{filename}_parts")

    if not os.path.exists(parts_folder):
        await query.message.reply_text("❌ پوشه قطعات این فایل حذف شده یا وجود ندارد.")
        return

    try:
        existing_parts = sorted(
            [
                f
                for f in os.listdir(parts_folder)
                if os.path.isfile(os.path.join(parts_folder, f))
            ]
        )

        if part_index >= len(existing_parts):
            await query.message.reply_text("❌ قطعه مورد نظر یافت نشد.")
            return

        part_filename = existing_parts[part_index]
        part_path = os.path.join(parts_folder, part_filename)

        with open(part_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                caption=f"🔄 تلاش مجدد دستی: بخش {part_index + 1} - `{filename}`",
                parse_mode="Markdown",
            )

    except Exception as e:
        await query.message.reply_text(
            f"❌ خطا در ارسال قطعه:\n`{e}`", parse_mode="Markdown"
        )
