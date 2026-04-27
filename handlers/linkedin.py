# handlers/linkedin.py

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from linkedin_api import Linkedin
from config import LINKEDIN_LI_AT_COOKIE # Import your cookie from config

# Set up logging
logger = logging.getLogger(__name__)

# --- LinkedIn API Authentication ---
# It's better to initialize it once, but for simplicity in a serverless environment,
# we can do it inside the command. For better performance, consider initializing it once globally.
try:
    api = Linkedin(
        '', # username is not needed when using a cookie
        '', # password is not needed when using a cookie
        cookies=LINKEDIN_LI_AT_COOKIE,
        refresh_cookies=False, # We don't want the library to try and refresh it
        debug=False # Set to True to see detailed API calls
    )
except Exception as e:
    logger.error(f"Failed to initialize LinkedIn API: {e}")
    api = None

# Helper function to format a post for sending to Telegram
def format_linkedin_post(post):
    """Formats a LinkedIn post dictionary into a readable string."""
    actor = post.get('actor', {})
    actor_name = actor.get('name', 'Unknown')
    actor_urn = actor.get('urn', '').split(':')[-1]
    actor_url = f"https://www.linkedin.com/in/{actor_urn}"

    commentary = post.get('commentary', 'No text content.')
    urn = post.get('urn', '').split(':')[-1]
    post_url = f"https://www.linkedin.com/feed/update/urn:li:activity:{urn}"

    likes = post.get('likesCount', 0)
    comments = post.get('commentsCount', 0)

    # Media handling
    media_url = None
    media_type = "None"
    content = post.get('content')
    if content and content.get('images'):
        # Get the highest resolution image
        root_url = content['images'][0]['rootUrl']
        artifact = content['images'][0]['artifacts'][-1]
        media_url = f"{root_url}{artifact['fileIdentifyingUrlPathSegment']}"
        media_type = "Image"
    elif content and content.get('videos'):
        # Note: Getting direct video URLs is harder and might require more processing.
        # For now, we just indicate a video is present.
        media_type = "Video"

    message = (
        f"👤 **Author:** [{actor_name}]({actor_url})\n\n"
        f"📝 **Post:**\n{commentary}\n\n"
        f"❤️ Likes: `{likes}`\n"
        f"💬 Comments: `{comments}`"
    )

    return message, post_url, media_url, media_type


async def linkedin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not api:
        await update.message.reply_text("❌ سرویس لینکدین به درستی مقداردهی اولیه نشده است. لطفا با ادمین تماس بگیرید.")
        return

    args = context.args
    # /linkedin search <keyword> OR /linkedin profile <profile_urn>
    if not args or len(args) < 2:
        await update.message.reply_text(
            "📌 *راهنمای استفاده:*\n\n"
            "1️⃣ *جستجوی پست‌ها:*\n`/linkedin search KEYWORD`\n"
            "   *مثال:* `/linkedin search python developer`\n\n"
            "2️⃣ *دریافت پست‌های یک پروفایل:*\n`/linkedin profile PROFILE_URL`\n"
            "   *مثال:* `/linkedin profile https://www.linkedin.com/in/satyanadella/`",
            parse_mode="Markdown"
        )
        return

    mode = args[0].lower()
    query = " ".join(args[1:])
    limit = 5 # Let's fetch 5 posts by default

    status_msg = await update.message.reply_text(f"⏳ در حال جستجو در لینکدین برای: `{query}`...")

    try:
        posts = []
        if mode == "search":
            posts = api.search_posts(keywords=query, limit=limit)
        elif mode == "profile":
            # Extract the URN from the URL
            profile_urn = query.split('/in/')[1].split('/')[0]
            posts = api.get_profile_posts(urn_id=profile_urn, limit=limit)
        else:
            await status_msg.edit_text("❌ حالت نامعتبر است. از `search` یا `profile` استفاده کنید.")
            return

        if not posts:
            await status_msg.edit_text("❌ هیچ پستی یافت نشد.")
            return

        await status_msg.edit_text(f"✅ تعداد `{len(posts)}` پست یافت شد. در حال ارسال...")

        for post in posts:
            message, post_url, media_url, media_type = format_linkedin_post(post)

            keyboard = [[InlineKeyboardButton("View on LinkedIn 🔗", url=post_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                if media_type == "Image" and media_url:
                    await update.message.reply_photo(
                        photo=media_url,
                        caption=message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        message,
                        parse_mode="Markdown",
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
            except Exception as e:
                logger.error(f"Error sending LinkedIn post to Telegram: {e}")
                # Fallback to sending text if photo fails
                await update.message.reply_text(
                    f"{message}\n\n(خطا در ارسال مدیا: {e})",
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )

    except Exception as e:
        logger.error(f"An error occurred with LinkedIn API: {e}")
        await status_msg.edit_text(
            f"❌ خطا در ارتباط با لینکدین.\n"
            f"ممکن است کوکی شما منقضی شده باشد یا درخواست‌ها بیش از حد مجاز بوده است.\n\n"
            f"`Error: {e}`",
            parse_mode="Markdown"
        )
