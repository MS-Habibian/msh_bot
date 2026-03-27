# main.py
import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.commands import start_command, help_command
from handlers.downloader import download_command, handle_reupload_callback

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main() -> None:
    """Build the bot and attach handlers."""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .build()
    )

    # Register Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Register URL Handler
    # filters.Entity("url") ensures this ONLY triggers if the user sends a web link
    # application.add_handler(MessageHandler(filters.Entity("url"), handle_url))
    application.add_handler(CommandHandler("dl", download_command))
     # Add the handler for the inline keyboard buttons. 
    # We filter for callback data starting with "reup:"
    application.add_handler(CallbackQueryHandler(handle_reupload_callback, pattern="^reup:"))


    # Start the bot
    print("Bot is starting with clean architecture...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
