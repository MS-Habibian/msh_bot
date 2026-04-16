# handlers/tgposts.py
import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.tg_client import tg_app

async def tgposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # 1. Parse the command arguments
    args = context.args
    if not args:
        await update.message.reply_text("Usage:\n/tgposts @channelname\n/tgposts 5 @channelname")
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
            await update.message.reply_text("The first argument must be a number! Example: /tgposts 5 @channelname")
            return

    # Keep limit strictly between $1$ and $20$
    limit = max(1, min(limit, 20))

    if not channel_username.startswith("@"):
        channel_username = f"@{channel_username}"

    status_msg = await update.message.reply_text(f"Fetching the last {limit} posts from {channel_username} (This might take a moment if there are large videos)...")

    try:
        posts = []
        # 2. Fetch history using Pyrogram (Telegram API)
        async for msg in tg_app.get_chat_history(channel_username, limit=limit):
            posts.append(msg)

        if not posts:
            await status_msg.edit_text("No posts found or channel is empty/private.")
            return

        posts.reverse() # Sort oldest to newest

        # 3. Process and send to Bale
        for post in posts:
            try:
                if post.text:
                    await update.message.reply_text(post.text)
                
                elif post.media:
                    # Download the media to your French server
                    file_path = await tg_app.download_media(post)
                    caption = post.caption if post.caption else ""
                    
                    if not file_path:
                        continue

                    # Upload to Bale based on media type
                    if post.photo:
                        with open(file_path, 'rb') as f:
                            await update.message.reply_photo(photo=f, caption=caption)
                    elif post.video:
                        with open(file_path, 'rb') as f:
                            await update.message.reply_video(video=f, caption=caption)
                    elif post.document:
                        with open(file_path, 'rb') as f:
                            await update.message.reply_document(document=f, caption=caption)
                    elif post.audio or post.voice:
                        with open(file_path, 'rb') as f:
                            await update.message.reply_audio(audio=f, caption=caption)
                    
                    # Delete the file from the server to save space
                    if os.path.exists(file_path):
                        os.remove(file_path)

            except Exception as e:
                print(f"Failed to send a post to Bale: {e}")

        await status_msg.edit_text("✅ All posts fetched and sent successfully!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Error fetching from Telegram: {e}")
