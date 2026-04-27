import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from linkedin_api import Linkedin
from config import LINKEDIN_LI_AT_COOKIE

# 1. Setup logger
logger = logging.getLogger(__name__)

# Initialize LinkedIn API
api = None
try:
    if not LINKEDIN_LI_AT_COOKIE:
        logger.error("LINKEDIN_LI_AT_COOKIE is missing or empty in config.py!")
    else:
        logger.info("Attempting to initialize LinkedIn API...")
        # Passing dummy username/password strings along with the cookies
        api = Linkedin("", "", cookies={'li_at': LINKEDIN_LI_AT_COOKIE})
        logger.info("LinkedIn API initialized successfully!")
except Exception as e:
    # 2. This will log the full error and traceback to your server console
    logger.error("Failed to initialize LinkedIn API. See traceback below:", exc_info=True)

def format_linkedin_post(post_data: dict) -> str:
    # Basic formatting helper
    text = post_data.get('text', {}).get('text', 'No text content')
    author = post_data.get('author', {}).get('name', 'Unknown Author')
    return f"👤 **{author}**\n\n{text[:800]}..." # Truncate long posts

async def linkedin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not api:
        await update.message.reply_text("❌ سرویس لینکدین به درستی مقداردهی اولیه نشده است. لطفا لاگ سرور را بررسی کنید.")
        return

    if not context.args:
        await update.message.reply_text("❌ لطفا کلمه کلیدی یا لینک پروفایل را وارد کنید.\nمثال:\n/linkedin search python\n/linkedin profile <url>")
        return

    mode = context.args[0].lower()
    query = " ".join(context.args[1:])

    if not query:
        await update.message.reply_text("❌ لطفا کلمه کلیدی یا لینک پروفایل را وارد کنید.")
        return

    msg = await update.message.reply_text("⏳ در حال جستجو در لینکدین...")

    try:
        posts = []
        if mode == 'search':
            # Note: The actual method name depends on the linkedin-api version.
            posts = api.search_posts(query, limit=5) 
        elif mode == 'profile':
            # In a real scenario, you'd extract the public ID from the URL first
            public_id = query.strip('/').split('/')[-1]
            posts = api.get_profile_posts(public_id, post_count=5)
        else:
            await msg.edit_text("❌ دستور نامعتبر. از search یا profile استفاده کنید.")
            return

        if not posts:
            await msg.edit_text("❌ هیچ پستی یافت نشد.")
            return

        await msg.delete()
        for post in posts:
            formatted_text = format_linkedin_post(post)
            
            # Create a simple inline keyboard (Update URL logic based on actual post data)
            urn = post.get('urn', '')
            post_url = f"https://www.linkedin.com/feed/update/{urn}/" if urn else "https://www.linkedin.com"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("مشاهده در لینکدین", url=post_url)]])

            await update.message.reply_text(formatted_text, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error fetching LinkedIn posts: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطایی رخ داد: {e}\nممکن است کوکی منقضی شده باشد یا محدودیت API اعمال شده باشد.")
