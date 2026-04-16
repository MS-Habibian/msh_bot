# import os
# from telegram import Update
# from telegram.ext import ContextTypes
# from utils.download_helper import format_size, split_file_rar
# from utils.tg_client import tg_app


# async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     # 1. Parse the command arguments
#     args = context.args
#     if not args:
#         await update.message.reply_text("📌 *راهنمای استفاده:*\n`/tgposts @channelname`\n`/tgposts 5 @channelname`\n(عدد بین ۱ تا ۲۰)", parse_mode="Markdown")
#         return

#     limit = 20
#     channel_username = ""

#     if len(args) == 1:
#         channel_username = args[0]
#     elif len(args) >= 2:
#         try:
#             limit = int(args[0])
#             channel_username = args[1]
#         except ValueError:
#             await update.message.reply_text("❌ اولین مقدار باید یک عدد باشد! مثال:\n`/tgposts 5 @channelname`", parse_mode="Markdown")
#             return

#     # Keep limit strictly between $1$ and $20$
#     limit = max(1, min(limit, 20))

#     if not channel_username.startswith("@"):
#         channel_username = f"@{channel_username}"

#     status_msg = await update.message.reply_text(f"⏳ در حال دریافت {limit} پست آخر از کانال {channel_username}...")

#     try:
#         posts = []
#         # 2. Fetch history using Pyrogram (Telegram API)
#         async for msg in tg_app.get_chat_history(channel_username, limit=limit):
#             posts.append(msg)

#         if not posts:
#             await status_msg.edit_text("❌ هیچ پستی یافت نشد یا کانال خصوصی/خالی است.")
#             return

#         posts.reverse() # Sort oldest to newest
#         await status_msg.edit_text(f"✅ تعداد `{len(posts)}` پست یافت شد. در حال آماده‌سازی و ارسال...", parse_mode="Markdown")

#         # 3. Process and send to Bale
#         for post_idx, post in enumerate(posts, 1):
#             try:
#                 if post.text:
#                     await update.message.reply_text(post.text)
                
#                 elif post.media:
#                     progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود از تلگرام سرور...", parse_mode="Markdown")
                    
#                     # Download the media to your French server
#                     file_path = await tg_app.download_media(post)
#                     caption = post.caption if post.caption else ""
                    
#                     if not file_path:
#                         await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}.")
#                         continue

#                     file_size = os.path.getsize(file_path)

#                     # Check if file is smaller than 19.5 MB
#                     if file_size <= 19.5 * 1024 * 1024:
#                         await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود در ربات بله...", parse_mode="Markdown")
#                         with open(file_path, 'rb') as f:
#                             # Standard upload to Bale based on media type
#                             if post.photo:
#                                 await update.message.reply_photo(photo=f, caption=caption)
#                             elif post.video:
#                                 await update.message.reply_video(video=f, caption=caption)
#                             elif post.document:
#                                 await update.message.reply_document(document=f, caption=caption)
#                             elif post.audio or post.voice:
#                                 await update.message.reply_audio(audio=f, caption=caption)
                        
#                         # Delete the original file
#                         os.remove(file_path)
#                         await progress_msg.delete()

#                     else:
#                         # File is too large, split it using your helper function
#                         await progress_msg.edit_text(f"✂️ *پست {post_idx}:* حجم فایل بزرگتر از ۲۰ مگابایت است (`{format_size(file_size)}`). در حال ساخت فایل‌های فشرده RAR...", parse_mode="Markdown")
                        
#                         part_files = split_file_rar(file_path, max_size_mb=19.5)
                        
#                         await progress_msg.edit_text(f"☁️ *پست {post_idx}:* فایل به `{len(part_files)}` بخش تقسیم شد. در حال آپلود بخش‌ها...", parse_mode="Markdown")

#                         for i, part_path in enumerate(part_files):
#                             try:
#                                 part_caption = caption + f"\n\n📦 بخش {i+1} از {len(part_files)}"
#                                 with open(part_path, "rb") as f:
#                                     await update.message.reply_document(
#                                         document=f, 
#                                         caption=part_caption,
#                                         read_timeout=120, write_timeout=300, connect_timeout=120
#                                     )
#                             except Exception as e:
#                                 await update.message.reply_text(f"❌ آپلود بخش {i+1} از پست {post_idx} ناموفق بود.")
#                             finally:
#                                 # Clean up the part file immediately after sending
#                                 if os.path.exists(part_path):
#                                     os.remove(part_path)

#                         # Check and remove the original file if your helper function didn't delete it
#                         if os.path.exists(file_path):
#                             os.remove(file_path)
                            
#                         await progress_msg.delete()

#             except Exception as e:
#                 print(f"Failed to send a post to Bale: {e}")
#                 await update.message.reply_text(f"❌ خطا در پردازش و ارسال پست {post_idx}.")

#         await update.message.reply_text("✅ تمامی پست‌ها با موفقیت دریافت و ارسال شدند!")

#     except Exception as e:
#         await status_msg.edit_text(f"❌ خطا در ارتباط با تلگرام: `{e}`", parse_mode="Markdown")


import os
import asyncio
from telegram import Update
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
    # 1. Parse the command arguments smartly
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
        posts = []
        async for msg in tg_app.get_chat_history(channel_username, limit=limit):
            posts.append(msg)

        if not posts:
            await status_msg.edit_text("❌ هیچ پستی یافت نشد یا کانال خصوصی/خالی است.")
            return

        posts.reverse()
        await status_msg.edit_text(f"✅ تعداد `{len(posts)}` پست یافت شد. در حال آماده‌سازی و ارسال...", parse_mode="Markdown")

        # زمان تاخیر برای حذف فایل‌ها به ثانیه ($5 \times 3600$ ثانیه)
        DELETE_DELAY = 5 * 3600 

        for post_idx, post in enumerate(posts, 1):
            try:
                if post.text:
                    await update.message.reply_text(post.text)
                
                elif post.media:
                    progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود از تلگرام سرور...", parse_mode="Markdown")
                    
                    file_path = await tg_app.download_media(post)
                    caption = post.caption if post.caption else ""
                    
                    if not file_path:
                        await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}.")
                        continue

                    file_size = os.path.getsize(file_path)
                    
                    # بررسی اینکه آیا فایل دانلودی پسوند apk دارد یا خیر
                    is_apk = file_path.lower().endswith('.apk')

                    # اگر فایل کوچکتر از 19.5 مگابایت بود و APK نبود
                    if file_size <= 19.5 * 1024 * 1024 and not is_apk:
                        await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود در ربات بله...", parse_mode="Markdown")
                        with open(file_path, 'rb') as f:
                            if post.photo:
                                await update.message.reply_photo(photo=f, caption=caption)
                            elif post.video:
                                await update.message.reply_video(video=f, caption=caption)
                            elif post.document:
                                await update.message.reply_document(document=f, caption=caption)
                            elif post.audio or post.voice:
                                await update.message.reply_audio(audio=f, caption=caption)
                        
                        # زمان‌بندی حذف فایل اصلی بعد از ۵ ساعت
                        context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=file_path)
                        await progress_msg.delete()

                    else:
                        reason = "فایل نصبی (APK) است" if is_apk else f"حجم فایل بزرگتر از ۲۰ مگابایت است (`{format_size(file_size)}`)"
                        await progress_msg.edit_text(f"✂️ *پست {post_idx}:* {reason}. در حال ساخت فایل‌های فشرده RAR...", parse_mode="Markdown")
                        
                        # فایل‌های APK یا فایل‌های بزرگ به RAR تبدیل/تقسیم می‌شوند
                        part_files = split_file_rar(file_path, max_size_mb=19.5)
                        
                        await progress_msg.edit_text(f"☁️ *پست {post_idx}:* فایل به صورت RAR آماده شد (`{len(part_files)}` بخش). در حال آپلود...", parse_mode="Markdown")

                        for i, part_path in enumerate(part_files):
                            try:
                                part_caption = caption + (f"\n\n📦 بخش {i+1} از {len(part_files)}" if len(part_files) > 1 else "\n\n📦 فایل فشرده شده")
                                
                                # ساخت یک نام فایل امن و تصادفی برای دور زدن فیلتر بله
                                safe_filename = f"file_post{post_idx}_part{i+1}.rar"
                                
                                with open(part_path, "rb") as f:
                                    await update.message.reply_document(
                                        document=f, 
                                        filename=safe_filename,  # اضافه شدن این خط مهم است!
                                        caption=part_caption,
                                        read_timeout=120, write_timeout=300, connect_timeout=120
                                    )
                            except Exception as e:
                                print(f"Upload error: {e}") # برای دیدن متن دقیق ارور در لاگ سرور
                                await update.message.reply_text(f"❌ آپلود بخش {i+1} از پست {post_idx} ناموفق بود.")
                            finally:
                                # زمان‌بندی حذف پارت‌های RAR بعد از ۵ ساعت
                                context.job_queue.run_once(delete_file_job, DELETE_DELAY, data=part_path)

            except Exception as e:
                print(f"Failed to send a post to Bale: {e}")
                await update.message.reply_text(f"❌ خطا در پردازش و ارسال پست {post_idx}.")

        await update.message.reply_text("✅ تمامی پست‌ها با موفقیت دریافت و ارسال شدند! فایل‌ها تا ۵ ساعت آینده روی سرور باقی می‌مانند.")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در ارتباط با تلگرام: `{e}`", parse_mode="Markdown")
