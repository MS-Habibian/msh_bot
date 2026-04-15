from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
from utils.pinterest_helper import search_pinterest_async

async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ لطفاً عبارت مورد نظر خود را وارد کنید!\n*مثال:* `/pin cat wallpapers`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    status_msg = await update.message.reply_text("🔍 در حال جستجو در پینترست...")

    try:
        results = await search_pinterest_async(query, limit=10)
        
        if not results:
            await status_msg.edit_text("❌ نتیجه‌ای یافت نشد.")
            return

        # Save results in user_data so we can retrieve the original URL later
        if 'pin_results' not in context.user_data:
            context.user_data['pin_results'] = {}
        
        # Create an album (Media Group) for previews
        media_group = []
        keyboard = []
        row = []

        for res in results:
            # Add to media group (using thumbnails to save bandwidth/time)
            media_group.append(InputMediaPhoto(media=res['thumbnail'], caption=f"گزینه #{res['id']}"))
            
            # Store original URL in context
            unique_key = f"pin_{update.effective_chat.id}_{res['id']}"
            context.user_data['pin_results'][unique_key] = res['original']

            # Build keyboard buttons (Row of 5 buttons)
            row.append(InlineKeyboardButton(text=f"🖼 {res['id']}", callback_data=f"pindl:{unique_key}"))
            if len(row) == 5:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)

        await status_msg.delete()
        
        # 1. Send the previews as an album
        await update.message.reply_media_group(media=media_group)
        
        # 2. Send the selection keyboard
        await update.message.reply_text(
            text="🎯 *تصاویر یافت شدند!*\nشماره تصویر مورد نظر را برای دریافت کیفیت اصلی (فایل) انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در جستجو:\n`{str(e)}`", parse_mode="Markdown")


async def handle_pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    _, unique_key = query.data.split(":")
    
    # Retrieve the original URL from user_data
    original_url = context.user_data.get('pin_results', {}).get(unique_key)

    if not original_url:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="❌ لینک تصویر منقضی شده است. لطفاً دوباره جستجو کنید."
        )
        return

    status_msg = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text="⏳ در حال دریافت کیفیت اصلی...",
        reply_to_message_id=query.message.message_id
    )

    try:
        # Send as a document to preserve original uncompressed quality
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=original_url,
            caption="✅ کیفیت اصلی تصویر دانلود شد.",
            reply_to_message_id=query.message.message_id
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا در ارسال تصویر اصلی:\n`{str(e)}`")
