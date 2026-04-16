# # handlers/tgposts.py
# import os
# from telegram import Update
# from telegram.ext import ContextTypes
# from utils.tg_client import tg_app

# async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     # 1. Parse the command arguments
#     args = context.args
#     if not args:
#         await update.message.reply_text("Usage:\n/tgposts @channelname\n/tgposts 5 @channelname")
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
#             await update.message.reply_text("The first argument must be a number! Example: /tgposts 5 @channelname")
#             return

#     # Keep limit strictly between $1$ and $20$
#     limit = max(1, min(limit, 20))

#     if not channel_username.startswith("@"):
#         channel_username = f"@{channel_username}"

#     status_msg = await update.message.reply_text(f"Fetching the last {limit} posts from {channel_username} (This might take a moment if there are large videos)...")

#     try:
#         posts = []
#         # 2. Fetch history using Pyrogram (Telegram API)
#         async for msg in tg_app.get_chat_history(channel_username, limit=limit):
#             posts.append(msg)

#         if not posts:
#             await status_msg.edit_text("No posts found or channel is empty/private.")
#             return

#         posts.reverse() # Sort oldest to newest

#         # 3. Process and send to Bale
#         for post in posts:
#             try:
#                 if post.text:
#                     await update.message.reply_text(post.text)
                
#                 elif post.media:
#                     # Download the media to your French server
#                     file_path = await tg_app.download_media(post)
#                     caption = post.caption if post.caption else ""
                    
#                     if not file_path:
#                         continue

#                     # Upload to Bale based on media type
#                     if post.photo:
#                         with open(file_path, 'rb') as f:
#                             await update.message.reply_photo(photo=f, caption=caption)
#                     elif post.video:
#                         with open(file_path, 'rb') as f:
#                             await update.message.reply_video(video=f, caption=caption)
#                     elif post.document:
#                         with open(file_path, 'rb') as f:
#                             await update.message.reply_document(document=f, caption=caption)
#                     elif post.audio or post.voice:
#                         with open(file_path, 'rb') as f:
#                             await update.message.reply_audio(audio=f, caption=caption)
                    
#                     # Delete the file from the server to save space
#                     if os.path.exists(file_path):
#                         os.remove(file_path)

#             except Exception as e:
#                 print(f"Failed to send a post to Bale: {e}")

#         await status_msg.edit_text("✅ All posts fetched and sent successfully!")

#     except Exception as e:
#         await status_msg.edit_text(f"❌ Error fetching from Telegram: {e}")
import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.download_helper import format_size, split_file_rar
from utils.tg_client import tg_app


async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 1. Parse the command arguments
    args = context.args
    if not args:
        await update.message.reply_text("📌 *راهنمای استفاده:*\n`/tgposts @channelname`\n`/tgposts 5 @channelname`\n(عدد بین ۱ تا ۲۰)", parse_mode="Markdown")
        return

    limit = 20
    channel_username = ""

    if len(args) == 1:
        channel_username = args[0]
    elif len(args) >= 2:
        try:
            limit = int(args[0])
            channel_username = args[1]
        except ValueError:
            await update.message.reply_text("❌ اولین مقدار باید یک عدد باشد! مثال:\n`/tgposts 5 @channelname`", parse_mode="Markdown")
            return

    # Keep limit strictly between $1$ and $20$
    limit = max(1, min(limit, 20))

    if not channel_username.startswith("@"):
        channel_username = f"@{channel_username}"

    status_msg = await update.message.reply_text(f"⏳ در حال دریافت {limit} پست آخر از کانال {channel_username}...")

    try:
        posts = []
        # 2. Fetch history using Pyrogram (Telegram API)
        async for msg in tg_app.get_chat_history(channel_username, limit=limit):
            posts.append(msg)

        if not posts:
            await status_msg.edit_text("❌ هیچ پستی یافت نشد یا کانال خصوصی/خالی است.")
            return

        posts.reverse() # Sort oldest to newest
        await status_msg.edit_text(f"✅ تعداد `{len(posts)}` پست یافت شد. در حال آماده‌سازی و ارسال...", parse_mode="Markdown")

        # 3. Process and send to Bale
        for post_idx, post in enumerate(posts, 1):
            try:
                if post.text:
                    await update.message.reply_text(post.text)
                
                elif post.media:
                    progress_msg = await update.message.reply_text(f"⬇️ *پست {post_idx}:* در حال دانلود از تلگرام سرور...", parse_mode="Markdown")
                    
                    # Download the media to your French server
                    file_path = await tg_app.download_media(post)
                    caption = post.caption if post.caption else ""
                    
                    if not file_path:
                        await progress_msg.edit_text(f"❌ خطا در دانلود مدیا برای پست {post_idx}.")
                        continue

                    file_size = os.path.getsize(file_path)

                    # Check if file is smaller than 19.5 MB
                    if file_size <= 19.5 * 1024 * 1024:
                        await progress_msg.edit_text(f"☁️ *پست {post_idx}:* در حال آپلود در ربات بله...", parse_mode="Markdown")
                        with open(file_path, 'rb') as f:
                            # Standard upload to Bale based on media type
                            if post.photo:
                                await update.message.reply_photo(photo=f, caption=caption)
                            elif post.video:
                                await update.message.reply_video(video=f, caption=caption)
                            elif post.document:
                                await update.message.reply_document(document=f, caption=caption)
                            elif post.audio or post.voice:
                                await update.message.reply_audio(audio=f, caption=caption)
                        
                        # Delete the original file
                        os.remove(file_path)
                        await progress_msg.delete()

                    else:
                        # File is too large, split it using your helper function
                        await progress_msg.edit_text(f"✂️ *پست {post_idx}:* حجم فایل بزرگتر از ۲۰ مگابایت است (`{format_size(file_size)}`). در حال ساخت فایل‌های فشرده RAR...", parse_mode="Markdown")
                        
                        part_files = split_file_rar(file_path, max_size_mb=19.5)
                        
                        await progress_msg.edit_text(f"☁️ *پست {post_idx}:* فایل به `{len(part_files)}` بخش تقسیم شد. در حال آپلود بخش‌ها...", parse_mode="Markdown")

                        for i, part_path in enumerate(part_files):
                            try:
                                part_caption = caption + f"\n\n📦 بخش {i+1} از {len(part_files)}"
                                with open(part_path, "rb") as f:
                                    await update.message.reply_document(
                                        document=f, 
                                        caption=part_caption,
                                        read_timeout=120, write_timeout=300, connect_timeout=120
                                    )
                            except Exception as e:
                                await update.message.reply_text(f"❌ آپلود بخش {i+1} از پست {post_idx} ناموفق بود.")
                            finally:
                                # Clean up the part file immediately after sending
                                if os.path.exists(part_path):
                                    os.remove(part_path)

                        # Check and remove the original file if your helper function didn't delete it
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            
                        await progress_msg.delete()

            except Exception as e:
                print(f"Failed to send a post to Bale: {e}")
                await update.message.reply_text(f"❌ خطا در پردازش و ارسال پست {post_idx}.")

        await update.message.reply_text("✅ تمامی پست‌ها با موفقیت دریافت و ارسال شدند!")

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در ارتباط با تلگرام: `{e}`", parse_mode="Markdown")
