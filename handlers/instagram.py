import instaloader
from telegram import Update
from telegram.ext import ContextTypes
import time

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /instagram <username>")
        return
    
    username = context.args[0].replace('@', '')
    status_msg = await update.message.reply_text(f"🔍 Fetching posts from @{username}...")
    
    try:
        L = instaloader.Instaloader()
        L.load_session_from_file('your_instagram_username')  # Replace with your actual Instagram username
        
        profile = instaloader.Profile.from_username(L.context, username)
        posts = list(profile.get_posts())[:3]
        
        if not posts:
            await status_msg.edit_text("No posts found.")
            return
        
        await status_msg.edit_text(f"📥 Sending {len(posts)} latest posts...")
        
        for post in posts:
            time.sleep(2)
            caption = post.caption if post.caption else "No caption"
            
            if post.is_video:
                await update.message.reply_video(
                    video=post.video_url,
                    caption=caption[:1024]
                )
            else:
                await update.message.reply_photo(
                    photo=post.url,
                    caption=caption[:1024]
                )
        
        await status_msg.edit_text("✅ Done!")
        
    except instaloader.exceptions.ProfileNotExistsException:
        await status_msg.edit_text(f"❌ Profile @{username} not found.")
    except instaloader.exceptions.ConnectionException:
        await status_msg.edit_text("❌ Instagram blocked the request. Session may have expired.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
