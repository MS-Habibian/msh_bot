import os
import asyncio
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from telegram.ext import ContextTypes
from utils.download_helper import format_size, split_file_rar
from utils.tg_client import tg_app


# تابع کمکی برای حذف فایل‌ها پس از گذشت زمان مشخص
async def delete_file_job(context: ContextTypes.DEFAULT_TYPE):
    file_path = context.job.data
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file after 5 hours: {file_path}")
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

        # گرفتن تاریخچه بدون محدودیت عددی ثابت در API، خودمان دستی متوقفش می‌کنیم
        async for msg in tg_app.get_chat_history(channel_username):
            if msg.media_group_id:
                if msg.media_group_id in group_map:
                    # این پیام متعلق به آلبومی است که قبلا دیده‌ایم، پس فقط به آن اضافه‌اش می‌کنیم
                    group_map[msg.media_group_id].append(msg)
                else:
                    # یک آلبوم جدید پیدا کردیم. آیا به محدودیت رسیده‌ایم؟
                    if len(grouped_posts) >= limit:
                        break
                    
                    group_map[msg.media_group_id] = [msg]
                    grouped_posts.append(group_map[msg.media_group_id])
            else:
                # یک پیام تکی (متن یا فایل بدون آلبوم) پیدا کردیم. آیا به محدودیت رسیده‌ایم؟
                if len(grouped_posts) >= limit:
                    break
                
                grouped_posts.append([msg])

        if not grouped_posts:
            await status_msg.edit_text("❌ هیچ پستی یافت نشد یا کانال خصوصی/خالی است.")
            return

        # مرتب‌سازی کل پست‌ها از قدیمی‌ترین به جدیدترین (برای ارسال در ربات بله)
        grouped_posts.reverse()
        
        # مرتب‌سازی فایل‌های داخل خود آلبوم‌ها (چون تلگرام پیام‌ها را از آخر به اول می‌دهد)
        for group in grouped_posts:
            group.reverse()

        await status_msg.edit_text(f"✅ تعداد `{len(grouped_posts)}` پست/آلبوم یافت شد. در حال آماده‌سازی و ارسال...", parse_mode="Markdown")

        DELETE_DELAY = 5 * 3600 

        for post_idx, post_group in enumerate(grouped_posts, 1):
            try:
                # ---------------- حالت اول: پیام تکی ----------------
                if len(post_group) == 1:
                    post = post_group[0]
                    
                    if post.text:
                        await update.message.reply_text(post.text)
                    
                    elif post.media:
                        progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود از تلگرام...", parse_mode="Markdown")
                        
                        file_path = await tg_app.download_media(post)
                        caption = post.caption if post.caption else ""
                        
                        if not file_path:
                            await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}.")
                            continue

                        file_size = os.path.getsize(file_path)
                        is_apk = file_path.lower().endswith('.apk')

                        if file_size <= 19.5 * 1024 * 1024 and not is_apk:
                            await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود در ربات...", parse_mode="Markdown")
                            with open(file_path, 'rb') as f:
                                if post.photo:
                                    await update.message.reply_photo(photo=f, caption=caption)
                                elif post.video:
                                    await update.message.reply_video(video=f, caption=caption)
                                elif post.document:
                                    await update.message.reply_document(document=f, caption=caption)
                                elif post.audio or post.voice:
                                    await update.message.reply_audio(audio=f, caption=caption)
                            
                            context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=file_path)
                            await progress_msg.delete()

                        else:
                            reason = "فایل نصبی (APK) است" if is_apk else f"حجم فایل بزرگتر از ۲۰ مگابایت است (`{format_size(file_size)}`)"
                            await progress_msg.edit_text(f"✂️ *پست {post_idx}:* {reason}. در حال ساخت فایل‌های فشرده RAR...", parse_mode="Markdown")
                            
                            part_files = split_file_rar(file_path, max_size_mb=19.5)
                            await progress_msg.edit_text(f"☁️ *پست {post_idx}:* فایل آماده شد (`{len(part_files)}` بخش). در حال آپلود...", parse_mode="Markdown")

                            for i, part_path in enumerate(part_files):
                                try:
                                    part_caption = caption + (f"\n\n📦 بخش {i+1} از {len(part_files)}" if len(part_files) > 1 else "\n\n📦 فایل فشرده شده")
                                    safe_filename = f"file_post{post_idx}_part{i+1}.rar"
                                    
                                    with open(part_path, "rb") as f:
                                        await update.message.reply_document(
                                            document=f, filename=safe_filename, caption=part_caption,
                                            read_timeout=120, write_timeout=300, connect_timeout=120
                                        )
                                except Exception as e:
                                    # نمایش دلیل دقیق خطا به جای پیام کلی
                                    await update.message.reply_text(f"❌ خطا در آپلود بخش {i+1} از پست {post_idx}:\nدلیل ارور: `{e}`", parse_mode="Markdown")
                                finally:
                                    context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=part_path)

                            context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=file_path)
                            await progress_msg.delete()

                # ---------------- حالت دوم: آلبوم (چند مدیا با هم) ----------------
                else:
                    progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx} (آلبوم با {len(post_group)} فایل):* در حال دانلود از تلگرام...", parse_mode="Markdown")
                    
                    downloaded_paths = []
                    album_caption = ""
                    
                    # پیدا کردن کپشن در کل گروه (تلگرام کپشن را روی یکی از فایل‌ها می‌گذارد)
                    for m in post_group:
                        if m.caption:
                            album_caption = m.caption
                            break

                    for m in post_group:
                        path = await tg_app.download_media(m)
                        if path:
                            downloaded_paths.append((m, path))

                    await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود آلبوم در ربات...", parse_mode="Markdown")
                    
                    media_group_to_send = []
                    open_files = []

                    for idx, (m, path) in enumerate(downloaded_paths):
                        f = open(path, 'rb')
                        open_files.append(f)
                        
                        # کپشن فقط روی فایل اول قرار می‌گیرد (مثل تلگرام)
                        cap = album_caption if idx == 0 else ""
                        
                        if m.photo:
                            media_group_to_send.append(InputMediaPhoto(media=f, caption=cap))
                        elif m.video:
                            media_group_to_send.append(InputMediaVideo(media=f, caption=cap))
                        elif m.document:
                            media_group_to_send.append(InputMediaDocument(media=f, caption=cap))
                        elif m.audio:
                            media_group_to_send.append(InputMediaAudio(media=f, caption=cap))

                    if media_group_to_send:
                        try:
                            # ارسال گروهی به صورت آلبوم به بله
                            await update.message.reply_media_group(media=media_group_to_send, read_timeout=120, write_timeout=300)
                        except Exception as e:
                            await update.message.reply_text(f"❌ خطا در ارسال آلبوم پست {post_idx}:\nدلیل ارور: `{e}`", parse_mode="Markdown")
                    
                    # بستن فایل‌ها و زمان‌بندی برای حذف
                    for f in open_files:
                        f.close()
                    for _, path in downloaded_paths:
                        context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=path)

                    await progress_msg.delete()

            except Exception as e:
                print(f"Failed to send a post to Bale: {e}")
                await update.message.reply_text(f"❌ خطا در پردازش پست {post_idx}:\nارور: `{e}`", parse_mode="Markdown")

        await update.message.reply_text("✅ تمامی پست‌ها با موفقیت دریافت و ارسال شدند!")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در ارتباط با تلگرام:\n`{e}`", parse_mode="Markdown")
