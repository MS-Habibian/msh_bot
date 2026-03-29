import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.page_downloader import download_webpage_as_mhtml

# Inside your message handler function:
async def dlp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text # assuming the user sent a URL
    
    if url.startswith("http://") or url.startswith("https://"):
        await update.message.reply_text("Loading webpage, executing JS, and bundling assets... Please wait.")
        
        # Call our Playwright function
        filepath = await download_webpage_as_mhtml(url)
        
        if filepath and os.path.exists(filepath):
            # Send the file back to the user
            with open(filepath, 'rb') as doc:
                await update.message.reply_document(
                    document=doc, 
                    filename=os.path.basename(filepath),
                    caption="Here is your saved webpage. Open it in Chrome/Edge/Brave."
                )
            # Clean up the file after sending
            os.remove(filepath)
        else:
            await update.message.reply_text("Failed to download the webpage.")
