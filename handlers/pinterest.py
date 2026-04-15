from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
# from utils.pinterest_helper import search_pinterest_async
from utils.pinterest_playwright import search_pinterest_playwright


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفاً یک عبارت برای جستجو وارد کنید.\nمثال: `/pin cats`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    processing_msg = await update.message.reply_text(f"🔍 در حال جستجوی تصاویر برای '{query}'...")

    # فراخوانی تابع Playwright
    results = await search_pinterest_playwright(query, limit=10)

    if not results:
        await processing_msg.edit_text("❌ نتیجه‌ای یافت نشد یا در ارتباط با سرور مشکلی پیش آمد.")
        return

    # ذخیره نتایج در context.user_data برای استفاده در زمان دانلود
    context.user_data['pin_results'] = results

    # ساخت آلبوم تصاویر (MediaGroup) برای پیش‌نمایش
    media_group = []
    keyboard = []
    row = []

    for item in results:
        media_group.append(InputMediaPhoto(media=item['thumbnail']))
        
        # ساخت دکمه‌های شیشه‌ای (شماره‌گذاری شده)
        btn = InlineKeyboardButton(text=item['id'], callback_data=f"pindl_{item['id']}")
        row.append(btn)
        
        if len(row) == 5: # هر ۵ دکمه در یک ردیف
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)

    # ارسال آلبوم پیش‌نمایش
    await update.message.reply_media_group(media=media_group)
    
    # ارسال کیبورد برای انتخاب و دانلود عکس اصلی
    reply_markup = InlineKeyboardMarkup(keyboard)
    await processing_msg.delete() # حذف پیام "در حال جستجو..."
    await update.message.reply_text(
        "👇 برای دانلود عکس با کیفیت اصلی، شماره آن را انتخاب کنید:",
        reply_markup=reply_markup
    )


async def handle_pin_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # استخراج ID عکس انتخاب شده (مثلا pindl_3 -> 3)
    item_id = query.data.split('_')[1]
    
    # بازیابی اطلاعات از user_data
    results = context.user_data.get('pin_results', [])
    selected_item = next((item for item in results if item['id'] == item_id), None)

    if not selected_item:
        await query.message.reply_text("❌ اطلاعات این عکس منقضی شده است. لطفاً دوباره جستجو کنید.")
        return

    # ارسال عکس اصلی به صورت فایل (Document) برای حفظ کیفیت
    await query.message.reply_document(
        document=selected_item['original'],
        caption=f"✅ {selected_item['title']}"
    )
