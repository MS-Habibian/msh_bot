# handlers/commands.py
from telegram import Update
from telegram.ext import ContextTypes

START_MESSAGE = """
*Welcome to the Universal Downloader Bot!* 🚀

I can help you download files from the web.

*Commands:*
/start - Restart the bot
/help - Show this help message
/dl <link> - Download a file from the given URL

*Example:*
`/dl https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf`

_Note: I can only send files up to 50MB due to Telegram limits._
"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(text=START_MESSAGE, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        text="To download a file, type `/dl` followed by your link.\n\nExample: `/dl https://example.com/file.zip`",
        parse_mode="Markdown",
    )
