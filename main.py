# main.py
import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.commands import start_command, help_command
from handlers.dlp import dlp_command
from handlers.dlp2 import dlp2_command
from handlers.downloader import download_command, handle_reupload_callback
from handlers.google import google_command
from handlers.image import image_command
# from handlers.instagram import instagram_command
from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers.youtube import handle_yt_format_callback, yt_command, handle_yt_download_callback, ytdl_command
from handlers.pinterest import pin_command, pin_download_callback
from telegram.ext import CommandHandler, CallbackQueryHandler
from handlers.tgposts import handle_download_rar_button, handle_tg_reupload_callback, tgposts_command
from utils.tg_client import tg_app # Import the Pyrogram ap

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# --- Lifecycle Hooks to run Telegram Scraper alongside Bale Bot ---
async def on_startup(application: Application):
    print("Starting Telegram MTProto Client...")
    await tg_app.start()

async def on_shutdown(application: Application):
    print("Stopping Telegram MTProto Client...")
    await tg_app.stop()

def main() -> None:
    """Build the bot and attach handlers."""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .base_url("https://tapi.bale.ai/bot")
        .post_init(on_startup)      # <--- ADD THIS
        .post_shutdown(on_shutdown) # <--- ADD THIS
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

    application.add_handler(CommandHandler("google", google_command))

    application.add_handler(CommandHandler("dlp", dlp_command))
    application.add_handler(CommandHandler("dlp2", dlp2_command))

    application.add_handler(CommandHandler("image", image_command))

    # application.add_handler(CommandHandler("ig", instagram_command))
        

    # ... your bot setup code ...

    # هندلر جستجوی یوتیوب
    application.add_handler(CommandHandler("yt", yt_command))
    # هندلر جدید برای دانلود مستقیم با لینک
    application.add_handler(CommandHandler("ytdl", ytdl_command))

    # هندلر کلیک روی نتایج
    application.add_handler(CallbackQueryHandler(handle_yt_download_callback, pattern="^ytdl:"))
    application.add_handler(CallbackQueryHandler(handle_yt_format_callback, pattern=r"^ytfmt:"))

    #پینترست
    application.add_handler(CommandHandler("pin", pin_command))
    application.add_handler(CallbackQueryHandler(pin_download_callback, pattern="^pindl_"))

    application.add_handler(CommandHandler("tgposts", tgposts_command))

    application.add_handler(CallbackQueryHandler(handle_download_rar_button, pattern="^dlrar:"))
    application.add_handler(CallbackQueryHandler(handle_tg_reupload_callback, pattern="^reuptg:"))




    # Start the bot
    print("Bot is starting with clean architecture...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
