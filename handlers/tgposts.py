import os
import uuid
import shutil
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.downloader import cleanup_folder_job
from utils.download_helper import format_size, split_file_rar 
from utils.tg_client import tg_app

# تابع کمکی برای حذف فایل‌های تکی پس از گذشت زمان مشخص
async def delete_file_job(context: ContextTypes.DEFAULT_TYPE):
    file_path = context.job.data
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("📌 *راهنمای استفاده:*\n`/tgposts @channelname`\n`/tgposts 5 @channelname`\n`/tgposts @channelname 10`\n(عدد بین ۱ تا ۲۰)", parse_mode="Markdown")
        return

    limit = 20
    channel_username = None

    for arg in args:
        if arg.isdigit():
            limit = int(arg)
        else:
            channel_username = arg

    if not channel_username:
        await update.message.reply_text("❌ لطفا آیدی کانال را وارد کنید.", parse_mode="Markdown")
        return

    limit = max(1, min(limit, 20))

    if not channel_username.startswith("@") and not channel_username.startswith("http"):
        channel_username = f"@{channel_username}"

    status_msg = await update.message.reply_text(f"⏳ در حال دریافت {limit} پست آخر از کانال {channel_username}...")

    try:
        grouped_posts = []
        group_map = {}

        async for msg in tg_app.get_chat_history(channel_username):
            if msg.media_group_id:
                if msg.media_group_id in group_map:
                    group_map[msg.media_group_id].append(msg)
                else:
                    if len(grouped_posts) >= limit: break
                    group_map[msg.media_group_id] = [msg]
                    grouped_posts.append(group_map[msg.media_group_id])
            else:
                if len(grouped_posts) >= limit: break
                grouped_posts.append([msg])

        if not grouped_posts:
            await status_msg.edit_text("❌ هیچ پستی یافت نشد یا کانال خصوصی/خالی است.")
            return

        grouped_posts.reverse()
        for group in grouped_posts:
            group.reverse()

        await status_msg.edit_text(f"✅ تعداد `{len(grouped_posts)}` پست/آلبوم یافت شد. در حال آماده‌سازی و ارسال...", parse_mode="Markdown")

        DELETE_DELAY = 5 * 3600 

        for post_idx, post_group in enumerate(grouped_posts, 1):
            try:
                # ---------------- حالت اول: پیام تکی ----------------
                if len(post_group) == 1:
                    post = post_group[0]
                    message_text = post.text or post.caption
                    
                    if post.media:
                        # استخراج سایز و نام فایل بدون دانلود
                        file_size = 0
                        file_name = ""
                        if post.document:
                            file_size = post.document.file_size
                            file_name = post.document.file_name or ""
                        elif post.video:
                            file_size = post.video.file_size
                            file_name = post.video.file_name or ""
                        elif post.audio:
                            file_size = post.audio.file_size
                            file_name = post.audio.file_name or ""
                        elif post.voice:
                            file_size = post.voice.file_size
                        elif post.photo:
                            file_size = post.photo.file_size

                        is_apk = file_name.lower().endswith('.apk')

                        # اگر فایل بزرگ است یا APK است، دکمه نشان بده و دانلود نکن
                        if file_size > 19.5 * 1024 * 1024 or is_apk:
                            reason = "فایل نصبی (APK) است" if is_apk else f"حجم فایل بزرگ است (`{format_size(file_size)}`)"
                            keyboard = [[InlineKeyboardButton("📥 دانلود و تکه‌تکه کردن (RAR)", callback_data=f"dlrar:{channel_username}:{post.id}")]]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            
                            text = f"⚠️ *پست {post_idx}:* این {reason}.\nبرای دانلود و فشرده‌سازی روی دکمه زیر کلیک کنید:"
                            if message_text:
                                text += f"\n\n📝 کپشن:\n{message_text}"
                                
                            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
                        
                        # روال عادی برای فایل‌های کوچک
                        else:
                            progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود...", parse_mode="Markdown")
                            file_path = await tg_app.download_media(post)
                            caption = message_text if message_text else ""
                            
                            if not file_path:
                                await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}.")
                                continue

                            await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود در ربات...", parse_mode="Markdown")
                            with open(file_path, 'rb') as f:
                                if post.photo: await update.message.reply_photo(photo=f, caption=caption)
                                elif post.video: await update.message.reply_video(video=f, caption=caption)
                                elif post.document: await update.message.reply_document(document=f, caption=caption)
                                elif post.audio or post.voice: await update.message.reply_audio(audio=f, caption=caption)
                            
                            context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=file_path)
                            await progress_msg.delete()

                    elif message_text:
                        try:
                            await update.message.reply_text(message_text)
                        except Exception:
                            await update.message.reply_text(f"⚠️ فرمت متفاوت:\n\n{message_text}")
                    else:
                        await update.message.reply_text(f"⚠️ *پست {post_idx}:* محتوای پشتیبانی نشده.", parse_mode="Markdown")

                # ---------------- حالت دوم: آلبوم ----------------
                else:
                    progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx} (آلبوم با {len(post_group)} فایل):* در حال دانلود...", parse_mode="Markdown")
                    
                    downloaded_paths = []
                    album_caption = ""
                    for m in post_group:
                        if m.caption:
                            album_caption = m.caption
                            break

                    for m in post_group:
                        path = await tg_app.download_media(m)
                        if path: downloaded_paths.append((m, path))

                    await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود آلبوم...", parse_mode="Markdown")
                    
                    media_group_to_send = []
                    open_files = []

                    for idx, (m, path) in enumerate(downloaded_paths):
                        f = open(path, 'rb')
                        open_files.append(f)
                        cap = album_caption if idx == 0 else ""
                        
                        if m.photo: media_group_to_send.append(InputMediaPhoto(media=f, caption=cap))
                        elif m.video: media_group_to_send.append(InputMediaVideo(media=f, caption=cap))
                        elif m.document: media_group_to_send.append(InputMediaDocument(media=f, caption=cap))
                        elif m.audio: media_group_to_send.append(InputMediaAudio(media=f, caption=cap))

                    if media_group_to_send:
                        try:
                            await update.message.reply_media_group(media=media_group_to_send, read_timeout=120, write_timeout=300)
                        except Exception as e:
                            await update.message.reply_text(f"❌ خطا در ارسال آلبوم پست {post_idx}:\n`{e}`", parse_mode="Markdown")
                    
                    for f in open_files: f.close()
                    for _, path in downloaded_paths:
                        context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=path)

                    await progress_msg.delete()

            except Exception as e:
                await update.message.reply_text(f"❌ خطا در پردازش پست {post_idx}:\nارور: `{e}`", parse_mode="Markdown")

        await update.message.reply_text("✅ فرآیند دریافت پست‌ها به پایان رسید!")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در ارتباط با تلگرام:\n`{e}`", parse_mode="Markdown")


# =====================================================================
# هندلرهای مربوط به دکمه‌های شیشه‌ای برای فایل‌های حجیم تلگرام
# =====================================================================

async def handle_download_rar_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    _, channel_username, msg_id = data.split(":")
    msg_id = int(msg_id)
    
    file_id = str(uuid.uuid4())
    download_folder = os.path.join("downloads", file_id)
    os.makedirs(download_folder, exist_ok=True)
    
    await query.edit_message_text("⬇️ در حال دانلود فایل بزرگ از تلگرام... (لطفاً صبور باشید)")
    
    try:
        post = await tg_app.get_messages(channel_username, msg_id)
        file_path = await tg_app.download_media(post, file_name=f"{download_folder}/")
        
        if not file_path:
            await query.edit_message_text("❌ خطا در دانلود فایل از تلگرام.")
            return

        await query.edit_message_text("✂️ دانلود تمام شد. در حال ساخت فایل‌های فشرده RAR...")
        part_files = split_file_rar(file_path, max_size_mb=19.5)
        
        context.job_queue.run_once(cleanup_folder_job, 5 * 3600, data=download_folder, name=f"cleanup_{file_id}")

        keyboard = []
        row = []
        for i, part in enumerate(part_files):
            btn = InlineKeyboardButton(f"بخش {i+1}", callback_data=f"reuptg:{file_id}:{i}")
            row.append(btn)
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row: keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ *دانلود و فشرده‌سازی کامل شد!*\n\n"
            f"📂 تعداد بخش‌ها: `{len(part_files)}`\n"
            f"☁️ *اکنون بخش‌ها به‌صورت خودکار در حال آپلود هستند...*\n"
            f"_(اگر آپلودی ناموفق بود، از دکمه‌های زیر برای تلاش مجدد استفاده کنید)_",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        caption = post.text or post.caption or ""
        
        for i, part_path in enumerate(part_files):
            part_caption = caption + (f"\n\n📦 بخش {i+1} از {len(part_files)}" if len(part_files) > 1 else "\n\n📦 فایل فشرده شده")
            safe_filename = f"file_part{i+1}.rar"
            try:
                with open(part_path, "rb") as f:
                    await context.bot.send_document(
                        chat_id=query.message.chat_id, document=f, filename=safe_filename, caption=part_caption,
                        read_timeout=120, write_timeout=300, connect_timeout=120
                    )
            except Exception as e:
                await context.bot.send_message(
                    chat_id=query.message.chat_id, 
                    text=f"❌ آپلود خودکار بخش {i+1} ناموفق بود.\n`{e}`", 
                    parse_mode="Markdown"
                )

    except Exception as e:
        await query.edit_message_text(f"❌ خطای پیش‌بینی نشده:\n`{e}`")
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)

async def handle_tg_reupload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, file_id, part_index_str = query.data.split(":")
    part_index = int(part_index_str)
    download_folder = os.path.join("downloads", file_id)

    if not os.path.exists(download_folder):
        await query.message.reply_text("⚠️ این فایل منقضی شده و از سرور حذف شده است.")
        return

    files_in_dir = sorted([f for f in os.listdir(download_folder) if f.endswith('.rar')])
    if part_index >= len(files_in_dir):
        await query.message.reply_text("⚠️ در پیدا کردن این بخش از فایل خطایی رخ داد.")
        return

    part_filename = files_in_dir[part_index]
    part_path = os.path.join(download_folder, part_filename)

    msg = await query.message.reply_text(f"☁️ در حال آپلود مجدد بخش {part_index + 1}...")
    try:
        safe_filename = f"file_part{part_index+1}.rar"
        with open(part_path, "rb") as f:
            await query.message.reply_document(
                document=f, filename=safe_filename, caption=f"🔄 تلاش مجدد دستی: بخش {part_index + 1}",
                read_timeout=120, write_timeout=300, connect_timeout=120,
            )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ آپلود دوباره ناموفق بود: `{str(e)}`", parse_mode="Markdown")
