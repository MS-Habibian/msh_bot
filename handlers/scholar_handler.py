from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.scholar_utils import user_search_cache, get_scholar_results, download_direct_pdf

async def scholar_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    query = " ".join(context.args)
    
    if not query:
        await update.message.reply_text("لطفا نام مقاله را وارد کنید.\nمثال: `/scholar machine learning`")
        return
        
    message = await update.message.reply_text("⏳ در حال جستجو در گوگل اسکولار...")
    
    results = get_scholar_results(query, limit=10)
    
    if not results:
        await message.edit_text("❌ مقاله‌ای یافت نشد.")
        return
        
    # ذخیره در کش
    user_search_cache[chat_id] = results
    
    text = "📚 **نتایج جستجو:**\n\n"
    keyboard = []
    row = []
    
    for idx, paper in enumerate(results):
        text += f"*{idx+1}. {paper['title']}*\n"
        text += f"👤 {paper['author']} ({paper['pub_year']})\n\n"
        
        # فقط اگر eprint_url وجود داشت، نام دکمه را تغییر می‌دهیم تا کاربر بداند PDF موجود است
        btn_text = f"دانلود {idx+1}" if paper['eprint_url'] else f"بدون PDF {idx+1}"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"dl_{idx}"))
        
        if len(row) == 5:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_scholar_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    data = query.data
    
    if not data.startswith("dl_"):
        return
        
    index = int(data.split("_")[1])
    
    if chat_id not in user_search_cache or index >= len(user_search_cache[chat_id]):
        await query.message.reply_text("❌ نشست شما منقضی شده است. لطفا دوباره جستجو کنید.")
        return
        
    paper = user_search_cache[chat_id][index]
    eprint_url = paper.get('eprint_url')
    
    if not eprint_url:
        await query.message.reply_text(f"❌ متاسفانه گوگل اسکولار لینک مستقیم (eprint) برای مقاله '{paper['title']}' ارائه نداده است.")
        return
        
    # ارسال پیام وضعیت
    status_msg = await query.message.reply_text("⏳ در حال دانلود مستقیم PDF...")
    
    # دانلود PDF
    pdf_bytes = download_direct_pdf(eprint_url)
    
    if pdf_bytes:
        # نام فایل از روی عنوان ساخته می‌شود (حذف کاراکترهای غیرمجاز)
        safe_title = "".join([c for c in paper['title'] if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        filename = f"{safe_title[:40]}.pdf"
        
        await query.message.reply_document(
            document=pdf_bytes, 
            filename=filename,
            caption=f"📄 {paper['title']}"
        )
        await status_msg.delete()
    else:
        await status_msg.edit_text("❌ دانلود فایل با خطا مواجه شد یا لینک خراب بود.")
