# handlers/google.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.google_scraper import search_google

async def google_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user provided a search query
    if not context.args:
        await update.message.reply_text("Please provide a search query. Example: `/google python programming`", parse_mode='Markdown')
        return

    query = " ".join(context.args)
    processing_message = await update.message.reply_text(f"🔍 Searching Google for '{query}'...")

    # Fetch results
    results = search_google(query, num_results=10)

    if results is None:
        await processing_message.edit_text("❌ Error communicating with Google. Please try again later.")
        return
        
    if not results:
        await processing_message.edit_text(f"No results found for '{query}'.")
        return

    # Format the message
    # We use <b> for bolding the linked title to make it stand out, followed by the snippet
    message_text = f"🔍 <b>Search results for:</b> <i>{query}</i>\n\n"
    
    for i, res in enumerate(results, 1):
        title = res['title']
        link = res['link']
        snippet = res['snippet']
        
        # Format: 1. Title (Hyperlinked & Bold) \n Snippet \n\n
        message_text += f"{i}. <b><a href='{link}'>{title}</a></b>\n{snippet}\n\n"

    # Telegram has a 4096 character limit per message. We need to truncate if it gets too long.
    if len(message_text) > 4096:
        message_text = message_text[:4090] + "..."

    # Send the final formatted message
    await processing_message.edit_text(
        text=message_text, 
        parse_mode='HTML', 
        disable_web_page_preview=True # Disables link previews so the chat doesn't get cluttered
    )
