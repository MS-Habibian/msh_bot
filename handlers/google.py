# handlers/google.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from utils.google_scraper import search_google  # We will update this utility below


async def google_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user provided a search query
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
    # message_text = f"🔍 <b>نتایج جستجو برای:</b> <i>{safe_query}</i>\n\n"

    # for i, res in enumerate(results, 1):
    #     # Escape title and snippet to prevent Telegram Parse errors
    #     title = html.escape(res["title"])
    #     link = res["link"]
    #     snippet = html.escape(res["snippet"])

    #     # Format: 1. Title (Hyperlinked & Bold) \n Snippet \n\n
    #     message_text += f"{i}. <b><a href='{link}'>{title}</a></b>\n{snippet}\n\n"

    # # Telegram has a 4096 character limit per message. We need to truncate if it gets too long.
    # if len(message_text) > 4096:
    #     # Cut at 4080 and add closing tags just in case, though usually simple truncation is fine
    #     message_text = message_text[:4090] + "..."

    # # Send the final formatted message
    # await processing_message.edit_text(
    #     text=message_text,
    #     parse_mode="HTML",
    #     disable_web_page_preview=True,  # Disables link previews so the chat doesn't get cluttered
    # )
    # قالب‌بندی پیام خروجی
    message_text = f"🔍 <b>نتایج جستجو برای:</b> <i>{safe_query}</i>\n\n"

    for i, res in enumerate(results, 1):
        # ایمن‌سازی عنوان و توضیحات
        title = html.escape(res["title"])
        link = res["link"]
        snippet = html.escape(res["snippet"])

        # نمایش عنوان و توضیحات
        message_text += f"{i}. <b>{title}</b>\n"
        message_text += f"📝 {snippet}\n"

        # قراردادن دستور dlp به صورت Code Block (با یک کلیک کپی می‌شود)
        message_text += f"📥 برای دانلود روی دستور زیر کلیک کنید تا کپی شود:\n"
        message_text += f"<code>/dlp {link}</code>\n\n"
        message_text += (
            f"برای دانلود روی دستور زیر کلیک کنید تا کپی شود:\n`/dlp {link}`"
        )

    # مدیریت محدودیت طول پیام تلگرام (4096 کاراکتر)
    if len(message_text) > 4096:
        message_text = message_text[:4080] + "\n\n... (نتایج بیشتر حذف شدند)"

    # ارسال پیام نهایی
    await processing_message.edit_text(
        text=message_text,
        parse_mode="HTML",
        disable_web_page_preview=True,  # غیرفعال کردن پیش‌نمایش لینک‌ها برای جلوگیری از شلوغی
    )
