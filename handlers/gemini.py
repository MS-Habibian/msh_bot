# handlers/gemini.py
import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes
from config import GEMINI_API_KEY

# Configure the API
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash') # Using flash for faster responses

async def ask_gemini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /ask command."""
    if not context.args:
        await update.message.reply_text("Please ask a question! Usage: /ask What is Python?")
        return

    user_prompt = " ".join(context.args)
    
    # Optional: Send typing action (Wrap in try/except as Bale API sometimes handles actions differently)
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    except:
        pass
        
    try:
        response = gemini_model.generate_content(user_prompt)
        answer = response.text[:4090] # Keep under Bale/Telegram character limit
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Error communicating with AI: {str(e)}")
