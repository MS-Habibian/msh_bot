import os
import shutil

from telegram.ext import ContextTypes


async def cleanup_folder_job(
    context: ContextTypes.DEFAULT_TYPE,
):
    folder_path = context.job.data
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"🗑️ پاک شد: {folder_path}")
