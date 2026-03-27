# handlers/downloader.py
import os
import shutil
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from utils.download_helper import download_file_async, format_size, split_file


# --- JOB QUEUE CLEANUP FUNCTION ---
async def cleanup_folder_job(context: ContextTypes.DEFAULT_TYPE):
    folder_path = context.job.data
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"🗑️ Cleaned up: {folder_path}")


# --- MAIN DOWNLOAD COMMAND ---
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a link!\n*Usage:* `/dl <link>`", parse_mode="Markdown"
        )
        return

    url = context.args[0]
    file_id = str(uuid.uuid4())  # Generate unique ID for this download
    download_folder = os.path.join("downloads", file_id)

    # status_msg = await update.message.reply_text("🔍 Analyzing and downloading...")
    status_msg = await update.message.reply_text("🔍 Analyzing and downloading...")

    async def update_progress(downloaded, total):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *Downloading...*\nProgress: `{percent:.1f}%`\nSize: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *Downloading...*\nDownloaded: `{format_size(downloaded)}` (Unknown total size)"

            await status_msg.edit_text(text, parse_mode="Markdown")
        except BadRequest:
            pass

    try:
        # 1. Download the file to the unique folder
        filepath = await download_file_async(
            url, download_folder, progress_callback=update_progress
        )
        # Upload phase prep

        # 2. Split the file if it's > 49 MB
        await status_msg.edit_text("✂️ Processing and splitting file (if necessary)...")
        part_files = split_file(filepath)

        # 3. Schedule folder deletion after 1 hour (3600 seconds)
        context.job_queue.run_once(
            cleanup_folder_job,
            5 * 3600,
            data=download_folder,
            name=f"cleanup_{file_id}",
        )

        # 4. Create the Inline Keyboard for retries
        keyboard = []
        row = []
        for i, part in enumerate(part_files):
            # callback_data format: reupload:file_id:index
            btn = InlineKeyboardButton(
                f"Part {i+1}", callback_data=f"reup:{file_id}:{i}"
            )
            row.append(btn)
            if len(row) == 3:  # 3 buttons per row
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 5. Send summary message
        await status_msg.edit_text(
            f"✅ *Download Complete!*\n\n"
            f"📂 Parts: `{len(part_files)}`\n"
            f"⏳ Files will be kept on the server for $1$ hour.\n"
            f"☁️ *Uploading parts automatically now...*\n"
            f"_(If a part fails, use the buttons below to retry)_",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # 6. Automatically upload all parts
        for i, part_path in enumerate(part_files):
            try:
                # await context.bot.send_chat_action(
                #     chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
                # )
                with open(part_path, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        caption=f"Part {i+1} of {len(part_files)}",
                        read_timeout=120,
                        write_timeout=120,
                        connect_timeout=120,
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Failed to auto-upload Part {i+1}. Please use the button above to retry."
                )
    except Exception as e:
        await status_msg.edit_text(f"❌ *Error:*\n`{str(e)}`", parse_mode="Markdown")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)


# --- CALLBACK QUERY HANDLER FOR RETRIES ---
async def handle_reupload_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the button click

    # Parse callback_data (e.g., "reup:UUID:0")
    _, file_id, part_index_str = query.data.split(":")
    part_index = int(part_index_str)

    download_folder = os.path.join("downloads", file_id)

    # Check if folder still exists (hasn't been deleted by JobQueue)
    if not os.path.exists(download_folder):
        await query.message.reply_text(
            "⚠️ This file has expired and was deleted from the server."
        )
        return

    # Find the specific part file in the folder
    files_in_dir = sorted(os.listdir(download_folder))
    if part_index >= len(files_in_dir):
        await query.message.reply_text("⚠️ Error finding that file part.")
        return

    part_filename = files_in_dir[part_index]
    part_path = os.path.join(download_folder, part_filename)

    # Upload the requested part
    msg = await query.message.reply_text(f"☁️ Re-uploading Part {part_index + 1}...")
    try:
        # await context.bot.send_chat_action(
        #     chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
        # )
        with open(part_path, "rb") as f:
            await query.message.reply_document(
                document=f,
                caption=f"Manual Retry: Part {part_index + 1}",
                read_timeout=120,
                write_timeout=300,
                connect_timeout=120,
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(
            f"❌ Upload failed again: `{str(e)}`", parse_mode="Markdown"
        )
