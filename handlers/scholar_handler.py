import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.scholar_utils import user_search_cache, get_scholar_results, get_scihub_pdf

async def scholar_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.replace('/scholar', '').strip()
    
    if not query:
        await update.message.reply_text(
            "لطفاً موضوع یا نام مقاله خود را بعد از دستور وارد کنید.\nمثال:\n`/scholar machine learning`"
        )
        return

    msg = await update.message.reply_text("🔍 در حال جستجو در گوگل اسکولار... لطفاً چند لحظه صبر کنید.")
    
    try:
        # جستجو در اسکولار
        results = get_scholar_results(query)
                
        if not results:
            await msg.edit_text("❌ هیچ نتیجه‌ای در گوگل اسکولار یافت نشد.")
            return

        urls_for_scihub = []
        # استفاده از HTML به جای Markdown برای جلوگیری از خطای فرمت‌بندی
        response_text = f"📚 <b>نتایج جستجو برای:</b> {query}\n\n"
        
        buttons = []

        for index, pub in enumerate(results):
            title = pub['bib'].get('title', 'بدون عنوان')
            
            # استخراج امن نام نویسنده (پشتیبانی از فرمت لیست یا رشته)
            authors = pub['bib'].get('author', 'نویسنده نامشخص')
            if isinstance(authors, list) and len(authors) > 0:
                author_str = str(authors[0])
            else:
                author_str = str(authors)
            author = author_str.split(' ')[0] + " et al."
            
            pub_year = pub['bib'].get('pub_year', 'سال نامشخص')
            
            pub_url = pub.get('pub_url', title)
            urls_for_scihub.append(pub_url)
            
            # تمیز کردن تگ‌های HTML احتمالی درون متن
            title = title.replace('<', '').replace('>', '')
            
            response_text += f"{index + 1}️⃣ <b>{title}</b>\n👤 {author} | 📅 {pub_year}\n\n"
            buttons.append(InlineKeyboardButton(text=str(index + 1), callback_data=f"dl_{index}"))

        user_search_cache[update.message.chat_id] = urls_for_scihub
        response_text += "👇 برای دانلود مقاله، روی شماره مربوطه در زیر کلیک کنید:"
        
        # چیدمان دکمه‌ها (۵ تا در هر ردیف)
        keyboard = [buttons[i:i + 5] for i in range(0, len(buttons), 5)]
        markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال با parse_mode="HTML"
        await msg.edit_text(response_text, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        # چاپ خطای دقیق در کنسول برای عیب‌یابی
        logging.error(f"Scholar Error: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطایی رخ داد. متن خطا در سرور ثبت شد.")


async def handle_scholar_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    index = int(query.data.split('_')[1])
    
    if chat_id not in user_search_cache or index >= len(user_search_cache[chat_id]):
        await query.answer("❌ نتایج جستجو منقضی شده است. لطفاً دوباره جستجو کنید.", show_alert=True)
        return
        
    identifier = user_search_cache[chat_id][index]
    
    await query.answer("⏳ در حال دریافت از Sci-Hub...")
    status_msg = await query.message.reply_text("⏳ در حال برقراری ارتباط با Sci-Hub و استخراج PDF...")
    
    try:
        pdf_content = get_scihub_pdf(identifier)
        
        if not pdf_content:
            await status_msg.edit_text("❌ متاسفانه فایل PDF این مقاله در Sci-Hub یافت نشد.")
            return
            
        await status_msg.edit_text("⬇️ فایل با موفقیت دریافت شد، در حال آپلود...")
        
        await context.bot.send_document(
            chat_id=chat_id, 
            document=pdf_content, 
            filename=f"Paper_Result_{index+1}.pdf",
            caption="📄 بفرمایید، این هم مقاله شما!"
        )
        await status_msg.delete()
            
    except Exception as e:
        await status_msg.edit_text("❌ خطا در ارتباط با شبکه یا سرور Sci-Hub.")
