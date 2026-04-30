# main.py
import logging
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.commands import start_command, help_command
from handlers.dlp import dlp_callback, dlp_command
from handlers.dlp2 import dlp2_command
from handlers.downloader import download_command, handle_reupload_callback
from handlers.google import google_command
from handlers.image import image_command
# from handlers.instagram import instagram_command
from handlers.linkedin import linkedin_command
from handlers.paper_handler import paper_download_callback, paper_paginate_callback, paper_search_command
from handlers.youtube import handle_yt_format_callback, yt_command, handle_yt_download_callback, ytdl_command
from handlers.pinterest import pin_command, pin_download_callback
from handlers.tgposts import handle_download_rar_button, handle_reupload_tg_button, tgposts_command
from handlers.commands import start_command, help_command, help_callback_handler
from handlers.podcast import handle_pod_callback, pod_command, podchannel_command 
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import Update, BotCommand

# Import Scholar Handlers

from utils.tg_client import tg_app # Import the Pyrogram ap

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


# --- Lifecycle Hooks to run Telegram Scraper alongside Bale Bot ---
async def on_startup(application: Application):
    print("Starting Telegram MTProto Client...")
    await tg_app.start()
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Get help"),
        BotCommand("dl", "Download a file"),
        BotCommand("google", "Search on Google"),
        BotCommand("dlp", "DLP handler"),
        BotCommand("dlp2", "DLP2 handler"),
        BotCommand("image", "Image tool"),
        BotCommand("yt", "Search YouTube"),
        BotCommand("ytdl", "Download from YouTube"),
        BotCommand("pin", "Pinterest tools"),
        BotCommand("tgposts", "Telegram posts downloader"),
        BotCommand("scholar", "Search Google Scholar papers"),
        BotCommand("podcast", "Podcast tools"),
        BotCommand("podchannel", "Podcast channel tools")
    ]
    # Push the commands to Telegram (or Bale) servers
    await application.bot.set_my_commands(commands)
    print("Bot commands menu updated!")

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

    application.add_handler(CommandHandler("dl", download_command))
    application.add_handler(CallbackQueryHandler(handle_reupload_callback, pattern="^reup:"))

    application.add_handler(CommandHandler("google", google_command))

    application.add_handler(CommandHandler("dlp", dlp_command))
    application.add_handler(CommandHandler("dlp2", dlp2_command))

    application.add_handler(CommandHandler("image", image_command))
    application.add_handler(CallbackQueryHandler(dlp_callback, pattern="^dlp:"))

    # هندلر جستجوی یوتیوب
    application.add_handler(CommandHandler("yt", yt_command))
    application.add_handler(CommandHandler("ytdl", ytdl_command))
    application.add_handler(CallbackQueryHandler(handle_yt_download_callback, pattern="^ytdl:"))
    application.add_handler(CallbackQueryHandler(handle_yt_format_callback, pattern=r"^ytfmt:"))

    # پینترست
    application.add_handler(CommandHandler("pin", pin_command))
    application.add_handler(CallbackQueryHandler(pin_download_callback, pattern='^(pindl_|pinmore_)'))
    # application.add_handler(CallbackQueryHandler(pin_page_callback, pattern=r"^pin_page\|"))

    application.add_handler(CommandHandler("tgposts", tgposts_command))
    application.add_handler(CallbackQueryHandler(handle_download_rar_button, pattern="^dlrar:"))
    application.add_handler(CallbackQueryHandler(handle_reupload_tg_button, pattern="^reuptg:"))

    application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="^help_"))

    # Scholar handlers
    application.add_handler(CommandHandler("scholar", paper_search_command))
    application.add_handler(CallbackQueryHandler(paper_download_callback, pattern=r"^paper_pdf\|"))
    application.add_handler(CallbackQueryHandler(paper_paginate_callback, pattern=r"^scholar_page\|"))
    # در بخشی که هندلرهای یوتیوب را Add می‌کنید، این خطوط را اضافه کنید:
    application.add_handler(CommandHandler("podcast", pod_command))
    # application.add_handler(CallbackQueryHandler(handle_pod_download_callback, pattern='^poddl:'))
    # تغییر پترن به گونه‌ای که هر دو poddl و podmore را بگیرد
    application.add_handler(CallbackQueryHandler(handle_pod_callback, pattern='^pod(dl|more):'))
    application.add_handler(CommandHandler("podchannel", podchannel_command)) # Add this line
    # application.add_handler(CallbackQueryHandler(paper_download_callback, pattern="^arxiv_pdf\|"))


    # application.add_handler(CommandHandler("linkedin", linkedin_command))



    # Start the bot
    print("Bot is starting with clean architecture...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
