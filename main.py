# main.py
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from config import BOT_TOKEN, BASE_URL
from handlers.commands import start_command, help_command
from handlers.status_command import status_command
from handlers.dlp_command import dlp_command
from handlers.dlp2_command import dlp2_command
from handlers.download_command import download_command, handle_reupload_callback
from handlers.google_command import google_command
from handlers.image_command import image_command
from database.session import init_db


# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# TODO: delete
async def post_init(application):
    """Runs after the bot initializes but before it starts polling."""
    # Initialize the database tables
    await init_db()
    logging.info("Database initialized.")


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("No BOT_TOKEN provided in .env file!")
    """Build the bot and attach handlers."""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url(BASE_URL)
        # .post_init(post_init)
        .build()
    )

    # Register Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(CommandHandler("dl", download_command))
    application.add_handler(
        CallbackQueryHandler(handle_reupload_callback, pattern="^reup:")
    )

    application.add_handler(CommandHandler("google", google_command))

    application.add_handler(CommandHandler("dlp", dlp_command))
    application.add_handler(CommandHandler("dlp2", dlp2_command))

    application.add_handler(CommandHandler("image", image_command))

    application.add_handler(CommandHandler("status", status_command))

    # Start the bot
    print("Bot is starting with clean architecture...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
