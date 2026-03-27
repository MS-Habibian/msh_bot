# handlers/downloader.py
import os
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from utils.download_helper import download_file_async, format_size


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide a link!\n*Usage:* `/dl <link>`", parse_mode="Markdown"
        )
        return

    url = context.args[0]
    status_message = await update.message.reply_text(
        "🔍 Analyzing link and checking size..."
    )

    async def update_progress(downloaded: int, total: int):
        try:
            if total > 0:
                percent = (downloaded / total) * 100
                text = f"⬇️ *Downloading...*\nProgress: `{percent:.1f}%`\nSize: `{format_size(downloaded)} / {format_size(total)}`"
            else:
                text = f"⬇️ *Downloading...*\nDownloaded: `{format_size(downloaded)}` (Unknown total size)"

            await status_message.edit_text(text, parse_mode="Markdown")
        except BadRequest:
            pass

    try:
        # Download phase
        filepath = await download_file_async(url, progress_callback=update_progress)

        # Upload phase prep
        await status_message.edit_text(
            "✅ Download complete!\n\n☁️ *Uploading to Telegram...*\n_(This might take a minute depending on file size)_",
            parse_mode="Markdown",
        )

        # Tell Telegram to show the native "uploading document..." action at the top of the screen
        # await context.bot.send_chat_action(
        #     chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_DOCUMENT
        # )

        # Send the file WITH increased timeouts (e.g., 120 seconds = 2 minutes)
        with open(filepath, "rb") as file_to_send:
            await update.message.reply_document(
                document=file_to_send,
                read_timeout=180,  # Max time to wait for a response from Telegram
                write_timeout=3600,  # Max time allowed to upload the data to Telegram
                connect_timeout=180,
            )

        # Clean up
        os.remove(filepath)
        await status_message.delete()

    except ValueError as ve:
        await status_message.edit_text(f"🛑 *Error:* {str(ve)}", parse_mode="Markdown")
    except Exception as e:
        await status_message.edit_text(
            f"❌ *Failed:*\n`{str(e)}`", parse_mode="Markdown"
        )
        # Ensure we delete the temp file even if the upload crashes
        if "filepath" in locals() and os.path.exists(filepath):
            os.remove(filepath)
