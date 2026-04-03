# handlers/google.py
import html
from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database.models import User
from decorators.transactional_decorator import transactional_handler
from services.billing_service import BillingManager
from utils.google_scraper import search_google  # We will update this utility below
from sqlalchemy.ext.asyncio import AsyncSession


@transactional_handler()
async def google_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession,
    user: User,
    billing: BillingManager,
):
    # Check if the user provided a search query
    billing.charge(cost_requests=1, action="/google")
    if not context.args:
        await update.message.reply_text(
            "لطفاً یک عبارت برای جستجو وارد کنید. مثال:\n`/google python programming`",
            parse_mode="Markdown",
        )
        return

    query = " ".join(context.args)
    # Escape query to prevent HTML parsing errors in Telegram
    safe_query = html.escape(query)

    processing_message = await update.message.reply_text(
        f"🔍 در حال جستجو برای '<b>{safe_query}</b>'...", parse_mode="HTML"
    )

    # Fetch results (Using DuckDuckGo under the hood)
    results = search_google(query, num_results=10)

    if results is None:
        await processing_message.edit_text(
            "❌ خطا در دریافت اطلاعات. لطفاً بعداً دوباره تلاش کنید."
        )
        return

    if not results:
        await processing_message.edit_text(
            f"هیچ نتیجه‌ای برای '<b>{safe_query}</b>' یافت نشد.", parse_mode="HTML"
        )
        return

    # # Format the message in Persian
    message_text = f"🔍 <b>نتایج جستجو برای:</b> <i>{safe_query}</i>\n\n"
    keyboard = []

    for i, res in enumerate(results, 1):
        title = html.escape(res["title"])
        link = res["link"]
        snippet = html.escape(res["snippet"])

        message_text += f"{i}. <b>{title}</b>\n"
        message_text += f"📝 {snippet}\n\n"

        # استفاده از CopyTextButton
        # متن دستور دانلود که می‌خواهیم کپی شود
        command_to_copy = f"/dlp {link}"

        # ساخت دکمه کپی
        button = InlineKeyboardButton(
            text=f"📋 کپی دستور دانلود {i}",
            copy_text=CopyTextButton(text=command_to_copy),
        )
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await processing_message.edit_text(
        text=message_text,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )
