import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telegram.ext import ContextTypes
# from utils.pinterest_helper import search_pinterest_async
from utils.pinterest_helper import debug_pinterest, search_pinterest_rss


async def pin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفاً یک عبارت برای جستجو وارد کنید.\nمثال: `/pin cats`", parse_mode="Markdown")
        return

    query = " ".join(context.args)
    processing_msg = await update.message.reply_text(f"🔍 در حال جستجوی تصاویر برای '{query}'...")

    results = await search_pinterest_rss(query, limit=10)

    if not results:
        await processing_msg.edit_text("❌ نتیجه‌ای یافت نشد. لطفاً دوباره تلاش کنید.")
        return

    context.user_data['pin_results'] = results

    # دانلود تصاویر به صورت bytes
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Referer': 'https://www.pinterest.com/',
    }

    media_group = []
    keyboard = []
    row = []

    async with aiohttp.ClientSession() as session:
        for item in results:
            try:
                async with session.get(item['thumbnail'], headers=headers, timeout=10) as img_response:
                    if img_response.status == 200:
                        img_bytes = await img_response.read()
                        media_group.append(InputMediaPhoto(media=img_bytes))
                        
                        btn = InlineKeyboardButton(text=item['id'], callback_data=f"pindl_{item['id']}")
                        row.append(btn)
                        if len(row) == 5:
                            keyboard.append(row)
                            row = []
                        
                        print(f"[Pinterest] Downloaded image {item['id']} ({len(img_bytes)} bytes)")
                    else:
                        print(f"[Pinterest] Failed to download image {item['id']}: {img_response.status}")
            except Exception as e:
                print(f"[Pinterest] Error downloading image {item['id']}: {e}")
                continue

    if row:
        keyboard.append(row)

    if not media_group:
        await processing_msg.edit_text("❌ خطا در بارگذاری تصاویر.")
        return

    await processing_msg.delete()
    await update.message.reply_media_group(media=media_group)

    reply_markup = InlineKeyboardMarkup(keyboard)
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
