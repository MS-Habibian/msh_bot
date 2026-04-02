import os
from telegram import Update
from telegram.ext import ContextTypes
from database.models import User
from decorators.transactional_decorator import transactional_handler
from services.billing_service import BillingManager
from utils.page_downloader import download_webpage_as_mhtml
from sqlalchemy.ext.asyncio import AsyncSession


@transactional_handler()
async def dlp_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    session: AsyncSession,
    user: User,
    billing: BillingManager,
) -> None:
    billing.charge(cost_requests=1, action="/dlp")
    url = context.args[0]
    if url.startswith("http://") or url.startswith("https://"):
        await update.message.reply_text(
            "Loading webpage, executing JS, and bundling assets... Please wait."
        )
        # Call our Playwright function
        filepath = await download_webpage_as_mhtml(url)

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
            await update.message.reply_text("Failed to download the webpage.")
    else:
        print("bad url:", url)
