import os
from telegram import Update
from telegram.ext import ContextTypes
from utils.page_downloader2 import download_as_pdf


# Inside your message handler function:
async def dlp2_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(11111111)
    # url = update.message.text  # assuming the user sent a URL
    url = context.args[0]
    print(2222222)
    if url.startswith("http://") or url.startswith("https://"):
        print(333333333333)
        await update.message.reply_text(
            "Loading webpage, executing JS, and bundling assets... Please wait."
        )

        # Call our Playwright function
        filepath = await download_as_pdf(url)

        if filepath and os.path.exists(filepath):
            # Send the file back to the user
            with open(filepath, "rb") as doc:
                await update.message.reply_document(
                    document=doc,
                    filename=os.path.basename(filepath),
                    caption="Here is your saved webpage. Open it in Chrome/Edge/Brave.",
                )
            # Clean up the file after sending
            os.remove(filepath)
        else:
            print(4444444)
            await update.message.reply_text("Failed to download the webpage.")
    else:
        print("bad url:", url)
