import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging so you can see errors in the terminal
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# 1. Define the /start command handler
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(f"Hello {user.first_name}! I am your new bot. Send me a message!")

# 2. Define a message handler that echoes the user's message
async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    user_text = update.message.text
    # The bot replies with the exact same text
    await update.message.reply_text(f"You said: {user_text}")

# 3. Main function to set up and run the bot
def main() -> None:
    # Replace 'YOUR_TOKEN_HERE' with your actual bot token
    BOT_TOKEN = "1421133829:AgGZYsLFZIh3BDcJ6zoY4TWRRa5eYorP_9c"
    
    # Create the application
    application = Application.builder().token(BOT_TOKEN).base_url("https://tapi.bale.ai/bot").build()

    # Add handlers to the application
    application.add_handler(CommandHandler("start", start_command))
    
    # This handler listens for standard text messages (not commands)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    # Run the bot until you press Ctrl-C
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
