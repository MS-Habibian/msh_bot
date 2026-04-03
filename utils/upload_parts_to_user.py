from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from config import HOURS_TO_KEEP_FILES


async def upload_parts_to_user(update: Update, file_id:str, part_files: list[str], status_msg=None):
    # create keyboard for reuploading parts
    keyboard = []
    row = []
    for i, part in enumerate(part_files):
        # فرمت callback_data: reupload:file_id:index
        btn = InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}")
        row.append(btn)
        if len(row) == 3:  # 3 دکمه در هر ردیف
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    reply_markup = InlineKeyboardMarkup(keyboard)

    # send the summary message
    if status_msg:
        await status_msg.edit_text(
          f"✅ *دانلود کامل شد!*\n\n"
          f"📂 تعداد بخش‌ها: `{len(part_files)}`\n"
          f"⏳ فایل‌ها به مدت {HOURS_TO_KEEP_FILES} ساعت روی سرور نگه‌داری می‌شوند.\n"
          f"☁️ *اکنون بخش‌ها به‌صورت خودکار در حال آپلود هستند...*\n"
          f"_(اگر آپلود بخشی ناموفق بود، از دکمه‌های زیر برای تلاش مجدد استفاده کنید)_",
          reply_markup=reply_markup,
          parse_mode="Markdown",
        )
    else:
        update.message.reply_text(
            f"✅ *دانلود کامل شد!*\n\n"
            f"📂 تعداد بخش‌ها: `{len(part_files)}`\n"
            f"⏳ فایل‌ها به مدت {HOURS_TO_KEEP_FILES} ساعت روی سرور نگه‌داری می‌شوند.\n"
            f"☁️ *اکنون بخش‌ها به‌صورت خودکار در حال آپلود هستند...*\n"
            f"_(اگر آپلود بخشی ناموفق بود، از دکمه‌های زیر برای تلاش مجدد استفاده کنید)_",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    # 6. آپلود خودکار تمام بخش‌ها
    for i, part_path in enumerate(part_files):
        try:
            with open(part_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"بخش {i+1} از {len(part_files)}",
                    read_timeout=120,
                    write_timeout=180,
                    connect_timeout=120,
                )
        except Exception as e:
            await update.message.reply_text(
                f"❌ آپلود خودکار بخش {i+1} ناموفق بود. لطفاً از دکمه بالا برای تلاش مجدد استفاده کنید."
            )
