# import os
# import uuid
# import shutil
# import re
# from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
# from telegram.ext import ContextTypes

# from utils.youtube_helper import search_youtube_async, get_youtube_qualities_async, download_youtube_video_async
# from utils.download_helper import format_size, split_media_playable, split_file_rar
# from handlers.downloader import cleanup_folder_job

# def extract_yt_video_id(url: str) -> str | None:
#     pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
#     match = re.search(pattern, url)
#     return match.group(1) if match else None

# def _build_quality_keyboard(video_id: str, resolutions: list) -> InlineKeyboardMarkup:
#     keyboard = []
#     row = []
#     for res in resolutions:
#         row.append(InlineKeyboardButton(f"🎬 {res}p", callback_data=f"ytdl:{video_id}:{res}"))
#         if len(row) == 2:
#             keyboard.append(row)
#             row = []
#     if row:
#         keyboard.append(row)
        
#     keyboard.append([
#         InlineKeyboardButton("🌟 بهترین کیفیت", callback_data=f"ytdl:{video_id}:best"),
#         InlineKeyboardButton("🎵 فقط صدا", callback_data=f"ytdl:{video_id}:audio")
#     ])
#     return InlineKeyboardMarkup(keyboard)


# async def send_search_results(context: ContextTypes.DEFAULT_TYPE, chat_id: int, results: list, query: str, offset: int):
#     """Helper function to send search results as individual messages"""
#     for i, vid in enumerate(results):
#         # Build Caption
#         caption = f"🎥 *{vid['title']}*\n⏱ مدت زمان: `{vid['duration']}`"
        
#         # Build Keyboard
#         keyboard = [[InlineKeyboardButton(f"🎬 انتخاب و دانلود", callback_data=f"ytfmt:{vid['id']}")]]
        
#         # If it's the last item, add the "Next 5 results" button at the bottom
#         if i == len(results) - 1:
#             short_query = query[:40]
#             keyboard.append([InlineKeyboardButton("⬇️ 5 نتیجه ی بعدی", callback_data=f"ytmore:{offset + 5}:{short_query}")])

#         reply_markup = InlineKeyboardMarkup(keyboard)

#         try:
#             if vid['thumbnail']:
#                 await context.bot.send_photo(
#                     chat_id=chat_id,
#                     photo=vid['thumbnail'],
#                     caption=caption,
#                     parse_mode="Markdown",
#                     reply_markup=reply_markup
#                 )
#             else:
#                 await context.bot.send_message(
#                     chat_id=chat_id,
#                     text=caption,
#                     parse_mode="Markdown",
#                     reply_markup=reply_markup
#                 )
#         except Exception as e:
#             # Fallback if photo sending fails
#             await context.bot.send_message(
#                 chat_id=chat_id,
#                 text=caption + f"\n[لینک تصویر]({vid['thumbnail']})",
#                 parse_mode="Markdown",
#                 reply_markup=reply_markup
#             )


# async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     if not context.args:
#         await update.message.reply_text("⚠️ لطفاً نام ویدیو را وارد کنید!\n*نحوه استفاده:* `/yt <نام ویدیو>`", parse_mode="Markdown")
#         return

#     query = " ".join(context.args)
#     status_msg = await update.message.reply_text("🔍 در حال جستجو در یوتیوب...")

#     try:
#         results = await search_youtube_async(query, limit=5, offset=0)
#         if not results:
#             await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
#             return

#         await status_msg.delete() # Remove status message before sending photos
#         await send_search_results(context, update.message.chat_id, results, query, 0)
        
#     except Exception as e:
#         await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")


# async def handle_yt_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query_cb = update.callback_query
#     await query_cb.answer()

#     _, offset_str, query = query_cb.data.split(":", 2)
#     offset = int(offset_str)

#     # 1. Remove the "Next 5 results" button from the last message
#     old_keyboard = query_cb.message.reply_markup.inline_keyboard
#     new_keyboard = [row for row in old_keyboard if not (row and row[0].callback_data and row[0].callback_data.startswith("ytmore:"))]
#     await query_cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))

#     # 2. Status message
#     status_msg = await context.bot.send_message(
#         chat_id=query_cb.message.chat_id,
#         text="🔍 در حال دریافت نتایج بعدی..."
#     )

#     try:
#         results = await search_youtube_async(query, limit=5, offset=offset)
#         if not results:
#             await status_msg.edit_text("❌ نتیجه دیگری یافت نشد.")
#             return

#         await status_msg.delete()
#         await send_search_results(context, query_cb.message.chat_id, results, query, offset)
        
#     except Exception as e:
#         await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")


# async def ytdl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     if not context.args:
#         await update.message.reply_text("⚠️ لطفاً لینک یوتیوب را وارد کنید!\n*نحوه استفاده:* `/ytdl <لینک یوتیوب>`", parse_mode="Markdown")
#         return

#     video_url = context.args[0]
#     video_id = extract_yt_video_id(video_url)
    
#     if not video_id:
#         await update.message.reply_text("❌ لینک وارد شده نامعتبر است یا آیدی ویدیو یافت نشد.")
#         return

#     status_msg = await update.message.reply_text("⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.")

#     try:
#         resolutions = await get_youtube_qualities_async(video_url)
#         if not resolutions:
#             await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
#             return

#         reply_markup = _build_quality_keyboard(video_id, resolutions)
#         await status_msg.edit_text(
#             text=f"🎥 ویدیو پیدا شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`https://www.youtube.com/watch?v={video_id}`",
#             reply_markup=reply_markup,
#             parse_mode="Markdown"
#         )
#     except Exception as e:
#         await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


# async def handle_yt_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()

#     _, video_id = query.data.split(":")
#     video_url = f"https://www.youtube.com/watch?v={video_id}"
    
#     status_msg = await context.bot.send_message(
#         chat_id=query.message.chat_id,
#         text="⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.",
#         reply_to_message_id=query.message.message_id
#     )

#     try:
#         resolutions = await get_youtube_qualities_async(video_url)
#         if not resolutions:
#             await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
#             return

#         reply_markup = _build_quality_keyboard(video_id, resolutions)
#         await status_msg.edit_text(
#             text=f"🎥 ویدیو انتخاب شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`{video_url}`",
#             reply_markup=reply_markup,
#             parse_mode="Markdown"
#         )
#     except Exception as e:
#         await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


# async def handle_yt_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     query = update.callback_query
#     await query.answer()

#     _, video_id, quality = query.data.split(":")
#     video_url = f"https://www.youtube.com/watch?v={video_id}"

#     if quality == 'best':
#         format_str = 'b'
#     elif quality == 'audio':
#         format_str = 'bestaudio[ext=m4a]/bestaudio/best'
#     else:
#         format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

#     file_id = str(uuid.uuid4())
#     download_folder = os.path.join("downloads", file_id)
#     quality_text = "صدا 🎵" if quality == 'audio' else f"ویدیو {quality}p" if quality != 'best' else "بهترین کیفیت"
    
#     await query.edit_message_text(text=f"⏳ در حال دانلود از یوتیوب ({quality_text})...\n`{video_url}`", parse_mode="Markdown")

#     async def update_progress(downloaded, total):
#         try:
#             if total > 0:
#                 percent = (downloaded / total) * 100
#                 text = f"⬇️ *در حال دانلود از یوتیوب...*\nپیشرفت: `{percent:.1f}%`\nحجم: `{format_size(downloaded)} / {format_size(total)}`"
#             else:
#                 text = f"⬇️ *در حال دانلود از یوتیوب...*\nدانلود شده: `{format_size(downloaded)}`"
#             await query.edit_message_text(text=text, parse_mode="Markdown")
#         except Exception:
#             pass 

#     try:
#         filepath = await download_youtube_video_async(video_url, download_folder, format_str, progress_callback=update_progress)
#         await query.edit_message_text("✂️ در حال پردازش و تقسیم فایل به تکه‌های زیر ۲۰ مگابایت...")
        
#         part_files = split_media_playable(filepath) if quality == 'audio' else split_file_rar(filepath)

#         context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

#         buttons = [InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}") for i in range(len(part_files))]
#         keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        
#         await query.edit_message_text(
#             text=f"✅ *پردازش کامل شد!*\n\n📂 تعداد بخش‌ها: `{len(part_files)}`\n☁️ *در حال آپلود بخش‌ها...*",
#             reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
#         )

#         for i, part_path in enumerate(part_files):
#             try:
#                 with open(part_path, "rb") as f:
#                     send_kwargs = {
#                         "chat_id": update.effective_chat.id,
#                         "caption": f"{'🎵' if quality == 'audio' else '🎥'} بخش {i+1} از {len(part_files)}",
#                         "read_timeout": 120, "write_timeout": 300, "connect_timeout": 120,
#                         "reply_to_message_id": query.message.message_id
#                     }
#                     if quality == 'audio':
#                         await context.bot.send_audio(audio=f, **send_kwargs)
#                     else:
#                         await context.bot.send_document(document=f, **send_kwargs)
#             except Exception:
#                 await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ آپلود بخش {i+1} ناموفق بود.")

#     except Exception as e:
#         error_text = f"❌ *خطا در دانلود ویدیو:*\n`{str(e)}`"
#         try:
#             await query.edit_message_text(text=error_text, parse_mode="Markdown")
#         except:
#             await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text, parse_mode="Markdown")
import os
import uuid
import shutil
import re
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.youtube_helper import search_youtube_async, get_youtube_qualities_async, download_youtube_video_async, get_channel_videos_async
from utils.download_helper import format_size, split_media_playable, split_file_rar
from handlers.downloader import cleanup_folder_job

def extract_yt_video_id(url: str) -> str | None:
    pattern = r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def _build_quality_keyboard(video_id: str, resolutions: list) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for res in resolutions:
        row.append(InlineKeyboardButton(f"🎬 {res}p", callback_data=f"ytdl:{video_id}:{res}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    keyboard.append([
        InlineKeyboardButton("🌟 بهترین کیفیت", callback_data=f"ytdl:{video_id}:best"),
        InlineKeyboardButton("🎵 فقط صدا", callback_data=f"ytdl:{video_id}:audio")
    ])
    return InlineKeyboardMarkup(keyboard)


async def send_search_results(context: ContextTypes.DEFAULT_TYPE, chat_id: int, results: list, query: str, offset: int, is_channel: bool = False):
    """Helper function to send search results as individual messages"""
    for i, vid in enumerate(results):
        caption = f"🎥 *{vid['title']}*\n⏱ مدت زمان: `{vid['duration']}`"
        keyboard = [[InlineKeyboardButton(f"🎬 انتخاب و دانلود", callback_data=f"ytfmt:{vid['id']}")]]
        
        if i == len(results) - 1:
            short_query = query[:40]
            cb_data = f"ytcmore:{offset + 5}:{short_query}" if is_channel else f"ytmore:{offset + 5}:{short_query}"
            keyboard.append([InlineKeyboardButton("⬇️ 5 نتیجه ی بعدی", callback_data=cb_data)])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if vid['thumbnail']:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=vid['thumbnail'],
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
        except Exception as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption + f"\n[لینک تصویر]({vid['thumbnail']})",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )


async def yt_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً نام ویدیو را وارد کنید!\n*نحوه استفاده:* `/yt <نام ویدیو>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text("🔍 در حال جستجو در یوتیوب...")

    try:
        results = await search_youtube_async(query, limit=5, offset=0)
        if not results:
            await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
            return

        await status_msg.delete() 
        await send_search_results(context, update.message.chat_id, results, query, 0)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در جستجو: `{str(e)}`", parse_mode="Markdown")

async def ytc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً آیدی یا لینک کانال را وارد کنید!\n*نحوه استفاده:* `/ytc @channelname`", parse_mode="Markdown")
        return

    channel_id = context.args[0]
    status_msg = await update.message.reply_text("🔍 در حال بررسی کانال و دریافت ویدیوها...")

    try:
        results = await get_channel_videos_async(channel_id, limit=5, offset=0)
        if not results:
            await status_msg.edit_text("❌ ویدیویی در این کانال یافت نشد.")
            return

        await status_msg.delete()
        await send_search_results(context, update.message.chat_id, results, channel_id, 0, is_channel=True)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در دریافت ویدیوهای کانال: `{str(e)}`", parse_mode="Markdown")


async def handle_yt_more_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query_cb = update.callback_query
    await query_cb.answer()

    is_channel = query_cb.data.startswith("ytcmore:")
    prefix = "ytcmore:" if is_channel else "ytmore:"
    
    _, offset_str, query = query_cb.data.split(":", 2)
    offset = int(offset_str)

    old_keyboard = query_cb.message.reply_markup.inline_keyboard
    new_keyboard = [row for row in old_keyboard if not (row and row[0].callback_data and row[0].callback_data.startswith(prefix))]
    await query_cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))

    status_msg = await context.bot.send_message(
        chat_id=query_cb.message.chat_id,
        text="🔍 در حال دریافت نتایج بعدی..."
    )

    try:
        if is_channel:
            results = await get_channel_videos_async(query, limit=5, offset=offset)
        else:
            results = await search_youtube_async(query, limit=5, offset=offset)
            
        if not results:
            await status_msg.edit_text("❌ نتیجه دیگری یافت نشد.")
            return

        await status_msg.delete()
        await send_search_results(context, query_cb.message.chat_id, results, query, offset, is_channel)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: `{str(e)}`", parse_mode="Markdown")


async def ytdl_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً لینک یوتیوب را وارد کنید!\n*نحوه استفاده:* `/ytdl <لینک یوتیوب>`", parse_mode="Markdown")
        return

    video_url = context.args[0]
    video_id = extract_yt_video_id(video_url)
    
    if not video_id:
        await update.message.reply_text("❌ لینک وارد شده نامعتبر است یا آیدی ویدیو یافت نشد.")
        return

    status_msg = await update.message.reply_text("⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.")

    try:
        resolutions = await get_youtube_qualities_async(video_url)
        if not resolutions:
            await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
            return

        reply_markup = _build_quality_keyboard(video_id, resolutions)
        await status_msg.edit_text(
            text=f"🎥 ویدیو پیدا شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`https://www.youtube.com/watch?v={video_id}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


async def handle_yt_format_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, video_id = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    status_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏳ در حال استخراج کیفیت‌های موجود...\nاین عملیات ممکن است کمی طول بکشد.",
        reply_to_message_id=query.message.message_id
    )

    try:
        resolutions = await get_youtube_qualities_async(video_url)
        if not resolutions:
            await status_msg.edit_text("❌ کیفیت قابل دانلودی یافت نشد یا ویدیو در دسترس نیست.")
            return

        reply_markup = _build_quality_keyboard(video_id, resolutions)
        await status_msg.edit_text(
            text=f"🎥 ویدیو انتخاب شد!\nلطفاً کیفیت مورد نظر خود را انتخاب کنید:\n`{video_url}`",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(text=f"❌ خطا در دریافت کیفیت‌ها:\n`{str(e)}`")


async def handle_yt_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, video_id, quality = query.data.split(":")
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    if quality == 'best':
        format_str = 'b'
    elif quality == 'audio':
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        format_str = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"

    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    quality_text = "صدا 🎵" if quality == 'audio' else f"ویدیو {quality}p" if quality != 'best' else "بهترین کیفیت"
    
    await query.edit_message_text(text=f"⏳ در حال شروع دانلود از یوتیوب ({quality_text})...\n`{video_url}`", parse_mode="Markdown")

    async def update_progress(downloaded, total, speed):
        try:
            speed_mb = speed / (1024 * 1024) if speed else 0
            if total > 0:
                percentage = (downloaded / total) * 100
                text = (f"⬇️ **در حال دانلود فایل از یوتیوب...**\n\n"
                        f"📈 پیشرفت: `{percentage:.1f}%`\n"
                        f"📥 مقدار دانلود شده: `{format_size(downloaded)}` از `{format_size(total)}`\n"
                        f"🚀 سرعت: `{speed_mb:.2f} MB/s`")
            else:
                text = (f"⬇️ **در حال دانلود فایل از یوتیوب...**\n\n"
                        f"📥 مقدار دانلود شده: `{format_size(downloaded)}`\n"
                        f"🚀 سرعت: `{speed_mb:.2f} MB/s`")
            await query.edit_message_text(text=text, parse_mode="Markdown")
        except Exception:
            pass 

    try:
        filepath = await download_youtube_video_async(video_url, download_folder, format_str, progress_callback=update_progress)
        await query.edit_message_text("✂️ در حال پردازش و تقسیم فایل به تکه‌های زیر ۲۰ مگابایت...")
        
        part_files = split_media_playable(filepath) if quality == 'audio' else split_file_rar(filepath)

        context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

        buttons = [InlineKeyboardButton(f"Part {i+1}", callback_data=f"reup:{file_id}:{i}") for i in range(len(part_files))]
        keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        
        await query.edit_message_text(
            text=f"✅ *پردازش کامل شد!*\n\n📂 تعداد بخش‌ها: `{len(part_files)}`\n☁️ *در حال آپلود بخش‌ها...*",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

        for i, part_path in enumerate(part_files):
            try:
                with open(part_path, "rb") as f:
                    send_kwargs = {
                        "chat_id": update.effective_chat.id,
                        "caption": f"{'🎵' if quality == 'audio' else '🎥'} بخش {i+1} از {len(part_files)}",
                        "read_timeout": 120, "write_timeout": 300, "connect_timeout": 120,
                        "reply_to_message_id": query.message.message_id
                    }
                    if quality == 'audio':
                        await context.bot.send_audio(audio=f, **send_kwargs)
                    else:
                        await context.bot.send_document(document=f, **send_kwargs)
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ آپلود بخش {i+1} ناموفق بود.")

    except Exception as e:
        error_text = f"❌ *خطا در دانلود ویدیو:*\n`{str(e)}`"
        try:
            await query.edit_message_text(text=error_text, parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=error_text, parse_mode="Markdown")
