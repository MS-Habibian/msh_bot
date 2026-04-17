import os
import shutil
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.page_downloader import download_webpage_as_mhtml
from utils.page_downloader2 import download_as_pdf
from utils.download_helper import split_file


async def dlp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ *Usage:* `/dlp <url>`", parse_mode="Markdown")
        return

    url = context.args[0]
    
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("⚠️ URL must start with http:// or https://")
        return

    keyboard = [
        [
            InlineKeyboardButton("PDF", callback_data=f"dlp:pdf:{url}"),
            InlineKeyboardButton("MHTML", callback_data=f"dlp:mhtml:{url}"),
            InlineKeyboardButton("PNG", callback_data=f"dlp:png:{url}")
        ]
    ]
    
    await update.message.reply_text(
        "📥 *Choose download format:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def dlp_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    _, format_type, url = query.data.split(":", 2)
    
    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    os.makedirs(download_folder, exist_ok=True)

    await query.edit_message_text("🔍 Loading webpage...")

    try:
        if format_type == "mhtml":
            filepath = await download_webpage_as_mhtml(url)
        else:
            filepath = await download_as_pdf(url, format_type=format_type)
        
        if not filepath or not os.path.exists(filepath):
            await query.edit_message_text("❌ Failed to download the webpage.")
            return

        new_filepath = os.path.join(download_folder, os.path.basename(filepath))
        shutil.move(filepath, new_filepath)
        
        await query.edit_message_text("✂️ Processing file...")
        part_files = split_file(new_filepath)

        context.job_queue.run_once(
            lambda ctx: shutil.rmtree(download_folder) if os.path.exists(download_folder) else None,
            5 * 3600,
            data=download_folder,
            name=f"cleanup_{file_id}"
        )

        keyboard = []
        row = []
        for i in range(len(part_files)):
            row.append(InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        await query.edit_message_text(
            f"✅ *Download complete!*\n\n"
            f"📂 Parts: `{len(part_files)}`\n"
            f"⏳ Files kept for 5 hours\n"
            f"☁️ *Uploading...*",
            reply_markup=InlineKeyboardMarkup(keyboard) if len(part_files) > 1 else None,
            parse_mode="Markdown"
        )

        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    caption = f"Part {i+1} of {len(part_files)}" if len(part_files) > 1 else f"Webpage as {format_type.upper()}"
                    await query.message.reply_document(
                        document=f,
                        caption=caption,
                        read_timeout=120,
                        write_timeout=120,
                        connect_timeout=120
                    )
            except Exception as e:
                await query.message.reply_text(f"❌ Upload failed for part {i+1}. Use button to retry.")

        await query.edit_message_text(
            f"✅ *Download complete!*\n\n"
            f"📂 Parts: `{len(part_files)}`\n"
            f"⏳ Files kept for 5 hours\n"
            f"✅ *Uploaded!*",
            reply_markup=InlineKeyboardMarkup(keyboard) if len(part_files) > 1 else None,
            parse_mode="Markdown"
        )

    except Exception as e:
        try:
            await query.edit_message_text(f"❌ *Error:*\n`{str(e)}`", parse_mode="Markdown")
        except:
            await query.message.reply_text(f"❌ *Error:*\n`{str(e)}`", parse_mode="Markdown")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)