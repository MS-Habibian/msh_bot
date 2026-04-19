import io
import requests
from bs4 import BeautifulSoup
from scholarly import scholarly
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, Application

# Define the Sci-Hub base URL (this changes occasionally, e.g., .se, .st, .ru)
SCIHUB_BASE_URL = "https://sci-hub.se/"

async def scholar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /scholar command."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query. Usage: /scholar <paper name>")
        return

    message = await update.message.reply_text("🔍 Searching Google Scholar...")

    try:
        # 1. Search Google Scholar
        # We fetch the first result from the generator
        search_query = scholarly.search_pubs(query)
        paper = next(search_query)
        
        title = paper['bib'].get('title', 'Unknown Title')
        pub_url = paper.get('pub_url', '')
        
        # Sci-hub works best with DOIs or direct Publisher URLs. 
        # If no URL is found, we fall back to searching the title on Sci-Hub.
        identifier = pub_url if pub_url else title

        await message.edit_text(f"📄 Found: *{title}*\n⏳ Attempting to download from Sci-Hub...", parse_mode='Markdown')

        # 2. Fetch the Sci-Hub page
        response = requests.post(SCIHUB_BASE_URL, data={'request': identifier}, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 3. Extract the PDF link from the Sci-Hub page
        # Sci-Hub usually embeds the PDF in an iframe or embed tag
        pdf_embed = soup.find('embed', type='application/pdf') or soup.find('iframe', id='pdf')
        
        if not pdf_embed or not pdf_embed.get('src'):
            await message.edit_text(f"❌ Could not find the PDF for *{title}* on Sci-Hub. It might not be available yet.", parse_mode='Markdown')
            return

        pdf_url = pdf_embed.get('src')
        
        # Handle relative URLs (e.g., //domain.com/path)
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = SCIHUB_BASE_URL.rstrip('/') + pdf_url

        # 4. Download the PDF into memory
        pdf_response = requests.get(pdf_url, timeout=20)
        pdf_response.raise_for_status() # Ensure the download was successful
        
        # Save to an in-memory bytes buffer
        pdf_file = io.BytesIO(pdf_response.content)
        
        # Clean up the filename (remove invalid characters)
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title[:40]}.pdf"

        # 5. Upload the document to Telegram
        await message.edit_text(f"📤 Uploading: *{title}*...", parse_mode='Markdown')
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_file,
            filename=filename,
            caption=f"Here is your paper:\n*{title}*",
            parse_mode='Markdown'
        )
        
        # Delete the "uploading" status message to keep chat clean
        await message.delete()

    except StopIteration:
        await message.edit_text("❌ No results found on Google Scholar for your query.")
    except requests.exceptions.RequestException as e:
        await message.edit_text("❌ Network error while trying to reach Sci-Hub or download the PDF.")
    except Exception as e:
        await message.edit_text(f"❌ An error occurred: {str(e)}")

# Example of how to add it to your bot application:
# app = Application.builder().token("YOUR_BOT_TOKEN").build()
# app.add_handler(CommandHandler("scholar", scholar_command))
# app.run_polling()
