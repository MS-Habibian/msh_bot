import os
import shutil
import uuid
import docker
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from database.models import User
from services.billing_service import BillingManager
from sqlalchemy.ext.asyncio import AsyncSession


# Import your existing helper
from utils import upload_parts_to_user
from utils.clean_up_folder_job import cleanup_folder_job
from utils.download_helper import split_file

# Initialize Docker client
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    print("Ensure Docker is running and the user has permissions.")


async def image_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession,
    user: User,
    billing: BillingManager,
):
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً نام ایمیج را وارد کنید!\n*نحوه استفاده:* `/image alpine:latest`",
            parse_mode="Markdown",
        )
        return

    image_name = context.args[0]

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    os.makedirs(download_folder, exist_ok=True)

    safe_filename = image_name.replace("/", "_").replace(":", "_") + ".tar"
    tar_path = os.path.join(download_folder, safe_filename)

    status_msg = await update.message.reply_text(
        f"⏳ در حال پول گرفتن ایمیج `{image_name}`...", parse_mode="Markdown"
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
        ### TODO: charge user as much as the file size

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

        await upload_parts_to_user(update, file_id, part_files, status_msg)

    except docker.errors.ImageNotFound:
        await status_msg.edit_text(
            f"❌ ایمیج مورد نظر یافت نشد.", parse_mode="Markdown"
        )
        raise
    except Exception as e:
        shutil.rmtree(download_folder, ignore_errors=True)
        raise
