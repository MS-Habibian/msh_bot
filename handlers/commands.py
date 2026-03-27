# handlers/commands.py
from telegram import Update
from telegram.ext import ContextTypes

START_MESSAGE = """
*به ربات دانلود کننده جهانی خوش آمدید!* 🚀

من می‌توانم به شما در دانلود فایل از وب کمک کنم.

*دستورات:*
/start - راه‌اندازی مجدد ربات
/help - نمایش این پیام راهنما
/dl <لینک> - دانلود یک فایل از آدرس URL داده شده

*مثال:*
`/dl https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf`

"""
# _توجه: به دلیل محدودیت‌های بله، من فقط می‌توانم فایل‌هایی تا حجم 50 مگابایت ارسال کنم._


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(text=START_MESSAGE, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        text="برای دانلود یک فایل، عبارت `/dl` را نوشته و سپس لینک خود را وارد کنید.\n\nمثال: `/dl https://example.com/file.zip`",
        parse_mode="Markdown",
    )
