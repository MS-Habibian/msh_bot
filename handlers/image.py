import os
import shutil
import uuid
import docker
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

# Import your existing helper
from utils.download_helper import split_file

# Initialize Docker client
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    print("Ensure Docker is running and the user has permissions.")


# --- Cleanup job (same as your downloader) ---
async def cleanup_folder_job(context: ContextTypes.DEFAULT_TYPE):
    folder_path = context.job.data
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"🗑️ Cleaned up: {folder_path}")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Please provide an image name. Usage: `/image alpine:latest`",
            parse_mode="Markdown",
        )
        return

    image_name = context.args[0]
    chat_id = update.effective_chat.id

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    os.makedirs(download_folder, exist_ok=True)

    safe_filename = image_name.replace("/", "_").replace(":", "_") + ".tar"
    tar_path = os.path.join(download_folder, safe_filename)

    status_msg = await update.message.reply_text(
        f"⏳ Pulling Docker image `{image_name}`...", parse_mode="Markdown"
    )

    try:
        loop = asyncio.get_running_loop()

        # 1. Pull the image
        image = await loop.run_in_executor(None, docker_client.images.pull, image_name)
        await status_msg.edit_text(f"✅ Image pulled! Saving to tar file...")

        # 2. Save image to tar
        def save_image():
            with open(tar_path, "wb") as f:
                for chunk in image.save(named=image_name):
                    f.write(chunk)

        await loop.run_in_executor(None, save_image)

        # 3. Remove image from host Docker (to free up server space immediately)
        try:
            await loop.run_in_executor(
                None, lambda: docker_client.images.remove(image.id, force=True)
            )
        except Exception as e:
            print(f"Failed to remove docker image from host: {e}")

        # 4. Process and split file
        await status_msg.edit_text("✂️ Processing and splitting file (if needed)...")
        part_files = split_file(tar_path)

        # 5. Schedule folder cleanup for 5 hours later
        context.job_queue.run_once(
            cleanup_folder_job,
            5 * 3600,
            data=download_folder,
            name=f"cleanup_docker_{file_id}",
        )

        # 6. Build Inline Keyboard for retries
        keyboard = []
        row = []
        for i, part in enumerate(part_files):
            # Using the same callback_data format as your downloader ('reup:file_id:index')
            # So your existing handle_reupload_callback will work for Docker images too!
            btn = InlineKeyboardButton(
                f"Part {i+1}", callback_data=f"reup:{file_id}:{i}"
            )
            row.append(btn)
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 7. Send summary message
        await status_msg.edit_text(
            f"✅ *Image processed successfully!*\n\n"
            f"🐳 Image: `{image_name}`\n"
            f"📂 Parts: `{len(part_files)}`\n"
            f"⏳ Files will be kept on server for 5 hours.\n"
            f"☁️ *Uploading parts automatically now...*\n"
            f"_(Use buttons below if any part fails)_",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        # 8. Upload all parts
        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        caption=f"{image_name} - Part {i+1} of {len(part_files)}",
                        read_timeout=120,
                        write_timeout=300,
                        connect_timeout=120,
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Auto-upload of part {i+1} failed. Please use the button above to retry."
                )

    except docker.errors.ImageNotFound:
        await status_msg.edit_text(
            f"❌ Error: Image `{image_name}` not found.", parse_mode="Markdown"
        )
        shutil.rmtree(download_folder, ignore_errors=True)
    except Exception as e:
        await status_msg.edit_text(f"❌ *Error:*\n`{str(e)}`", parse_mode="Markdown")
        shutil.rmtree(download_folder, ignore_errors=True)
