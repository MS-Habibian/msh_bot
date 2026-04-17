import os
import time
import uuid
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
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

# تابع پروگرس برای نمایش درصد پیشرفت دانلود از تلگرام
async def download_progress(current, total, query, start_time_list, last_update_time_list):
    now = time.time()
    # آپدیت پیام هر 3 ثانیه یکبار برای جلوگیری از محدودیت‌های تلگرام
    if now - last_update_time_list[0] > 3:
        last_update_time_list[0] = now
        percentage = current * 100 / total if total else 0
        speed = current / (now - start_time_list[0]) if (now - start_time_list[0]) > 0 else 0
        speed_mb = speed / (1024 * 1024)
        
        text = (f"⬇️ **در حال دانلود فایل بزرگ از تلگرام...**\n\n"
                f"📈 پیشرفت: `{percentage:.1f}%`\n"
                f"📥 مقدار دانلود شده: `{format_size(current)}` از `{format_size(total)}`\n"
                f"🚀 سرعت: `{speed_mb:.2f} MB/s`")
        
        try:
            await query.edit_message_text(text, parse_mode="Markdown")
        except:
            pass

def get_media_info(post):
    file_size, file_name = 0, ""
    if post.document:
        file_size, file_name = post.document.file_size, post.document.file_name or ""
    elif post.video:
        file_size, file_name = post.video.file_size, post.video.file_name or ""
    elif post.audio:
        file_size, file_name = post.audio.file_size, post.audio.file_name or ""
    elif post.voice:
        file_size = post.voice.file_size
    elif post.photo:
        file_size = post.photo.file_size
    return file_size, file_name

async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("📌 *راهنمای استفاده:*\n`/tgposts @channelname`\n`/tgposts 5 @channelname`\n(عدد بین ۱ تا ۲۰)", parse_mode="Markdown")
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

        await status_msg.edit_text(f"✅ تعداد `{len(grouped_posts)}` پست/آلبوم یافت شد. در حال پردازش...", parse_mode="Markdown")
        DELETE_DELAY = 5 * 3600 

        for post_idx, post_group in enumerate(grouped_posts, 1):
            try:
                # بررسی می‌کنیم آیا داخل آلبوم فایل بزرگی وجود دارد؟
                large_files = []
                normal_files = []
                
                for post in post_group:
                    if post.media:
                        file_size, file_name = get_media_info(post)
                        is_apk = file_name.lower().endswith('.apk')
                        if file_size > 19.5 * 1024 * 1024 or is_apk:
                            large_files.append((post, file_size, is_apk))
                        else:
                            normal_files.append(post)
                    else:
                        normal_files.append(post)

                # اول فایل‌های بزرگ (نیازمند تکه تکه شدن) را با دکمه ارسال می‌کنیم
                for l_post, size, is_apk in large_files:
                    reason = "فایل نصبی (APK) است" if is_apk else f"حجم فایل بزرگ است (`{format_size(size)}`)"
                    keyboard = [[InlineKeyboardButton("📥 دانلود و تکه‌تکه کردن (RAR)", callback_data=f"dlrar:{channel_username}:{l_post.id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    text = f"⚠️ *پست {post_idx} (فایل حجیم آلبوم/تکی):* این {reason}.\nبرای دانلود روی دکمه زیر کلیک کنید:"
                    msg_text = l_post.text or l_post.caption
                    if msg_text:
                        text += f"\n\n📝 کپشن:\n{msg_text}"
                        
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

                if not normal_files:
                    continue

                # پردازش فایل‌های کوچک و متن‌های معمولی
                if len(normal_files) == 1:
                    post = normal_files[0]
                    message_text = post.text or post.caption
                    
                    if post.media:
                        progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود فایل کوچک...", parse_mode="Markdown")
                        file_path = await tg_app.download_media(post)
                        
                        if not file_path:
                            await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}. (احتمالا مدیا قابل دانلود نیست)")
                            continue

                        await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود...", parse_mode="Markdown")
                        with open(file_path, 'rb') as f:
                            if post.photo: await update.message.reply_photo(photo=f, caption=message_text)
                            elif post.video: await update.message.reply_video(video=f, caption=message_text)
                            elif post.document: await update.message.reply_document(document=f, caption=message_text)
                            elif post.audio or post.voice: await update.message.reply_audio(audio=f, caption=message_text)
                        
                        context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=file_path)
                        await progress_msg.delete()

                    elif message_text:
                        await update.message.reply_text(message_text)
                        
                else: # ارسال به عنوان آلبوم برای فایل‌های کوچک باقیمانده
                    progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx} (آلبوم با {len(normal_files)} فایل کوچک):* در حال دانلود...", parse_mode="Markdown")
                    
                    downloaded_paths = []
                    album_caption = next((m.caption for m in normal_files if m.caption), "")

                    for m in normal_files:
                        if m.media:
                            path = await tg_app.download_media(m)
                            if path: downloaded_paths.append((m, path))

                    if not downloaded_paths:
                        await progress_msg.delete()
                        continue

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
                            await update.message.reply_text(f"❌ خطا در ارسال آلبوم: `{e}`", parse_mode="Markdown")
                    
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
    
    await query.edit_message_text("⬇️ در حال اتصال برای دانلود فایل بزرگ از تلگرام...")
    
    try:
        post = await tg_app.get_messages(channel_username, msg_id)
        
        # زمان شروع برای محاسبه سرعت و درصد
        start_time_list = [time.time()]
        last_update_time_list = [time.time()]
        
        file_path = await tg_app.download_media(
            post, 
            file_name=f"{download_folder}/",
            progress=download_progress,
            progress_args=(query, start_time_list, last_update_time_list)
        )
        
        if not file_path:
            await query.edit_message_text("❌ خطا در دانلود فایل از تلگرام (ممکن است مدیا قابل دانلود نباشد).")
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

        for i in range(len(part_files)):
            await reupload_tg_part(file_id, i, update, context, from_button=False)

    except Exception as e:
        await query.edit_message_text(f"❌ خطا در پردازش فایل:\n`{e}`", parse_mode="Markdown")

async def reupload_tg_part(file_id: str, part_index: int, update: Update, context: ContextTypes.DEFAULT_TYPE, from_button: bool = True):
    if from_button:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(f"☁️ در حال ارسال مجدد بخش {part_index+1} ...")

    download_folder = os.path.join("downloads", file_id)
    if not os.path.exists(download_folder):
        if from_button: await update.callback_query.edit_message_text("❌ پوشه فایل‌ها پیدا نشد.")
        return

    part_files = sorted([f for f in os.listdir(download_folder) if f.endswith(".rar")])
    if part_index < 0 or part_index >= len(part_files):
        if from_button: await update.callback_query.edit_message_text("❌ شماره بخش نامعتبر است.")
        return

    part_path = os.path.join(download_folder, part_files[part_index])
    try:
        with open(part_path, "rb") as f:
            await update.effective_chat.send_document(f, filename=part_files[part_index], write_timeout=300)
        if from_button:
            await update.callback_query.edit_message_text(f"✅ بخش {part_index+1} با موفقیت ارسال شد.")
    except Exception as e:
        if from_button:
            await update.callback_query.edit_message_text(f"❌ خطا در ارسال بخش:\n`{e}`", parse_mode="Markdown")


async def handle_reupload_tg_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    _, file_id, part_str = data.split(":")
    part_index = int(part_str)
    await reupload_tg_part(file_id, part_index, update, context, from_button=True)

def register_tgposts_handlers(app):
    app.add_handler(("tgposts", tgposts_command))
    app.add_handler(("dlrar", handle_download_rar_button))
    app.add_handler(("reuptg", handle_reupload_tg_button))

__all__ = ["tgposts_command", "handle_download_rar_button", "handle_reupload_tg_button", "register_tgposts_handlers"]
