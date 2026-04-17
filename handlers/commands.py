# handlers/commands.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

START_MESSAGE = """
🌟 *به ربات دستیار و دانلودر جامع خوش آمدید!* 🚀

من یک ربات همه‌کاره هستم و می‌تونم در زمینه‌های زیر بهت کمک کنم:

🌐 **دانلود از وب:** دانلود فایل از لینک مستقیم با سرعت بالا
📺 **یوتیوب:** جستجو و دانلود ویدیوها با کیفیت‌های مختلف
📌 **پینترست:** جستجو و دانلود عکس و ویدیو از پینترست
✈️ **تلگرام:** دریافت پست‌های کانال‌ها و تکه‌تکه کردن فایل‌های حجیم
🔍 **گوگل:** جستجو در وب و دریافت نتایج
🖼 **تصویر:** ابزارهای کاربردی برای کار با تصاویر

👇 برای مشاهده راهنمای استفاده از هر بخش، روی دکمه زیر کلیک کن:
"""

# متون راهنمای اختصاصی هر بخش
HELP_TEXTS = {
    "help_dl": (
        "🌐 *راهنمای دانلود مستقیم*\n\n"
        "با این دستور می‌توانید فایل‌ها را از لینک‌های مستقیم دانلود کنید.\n\n"
        "🔸 *دستور:* `/dl <لینک>`\n"
        "🔹 *مثال:* `/dl https://example.com/file.zip`\n\n"
        "_(همچنین دستورات `/dlp` و `/dlp2` برای دانلودهای پیشرفته‌تر در دسترس هستند)_"
    ),
    "help_yt": (
        "📺 *راهنمای یوتیوب*\n\n"
        "🔸 *جستجو:* `/yt <کلمه کلیدی>`\n"
        "🔹 *مثال:* `/yt آموزش پایتون`\n"
        "با این دستور ویدیوها جستجو شده و می‌توانید کیفیت مورد نظر را برای دانلود انتخاب کنید.\n\n"
        "🔸 *دانلود با لینک:* `/ytdl <لینک یوتیوب>`\n"
        "🔹 *مثال:* `/ytdl https://youtube.com/watch?v=...`"
    ),
    "help_pin": (
        "📌 *راهنمای پینترست*\n\n"
        "با این قابلیت می‌توانید در پینترست جستجو کنید و تصاویر یا ویدیوها را دانلود کنید.\n\n"
        "🔸 *دستور:* `/pin <موضوع جستجو>`\n"
        "🔹 *مثال:* `/pin nature wallpapers`"
    ),
    "help_tg": (
        "✈️ *راهنمای دانلود از تلگرام*\n\n"
        "با این دستور می‌توانید پست‌های اخیر یک کانال عمومی تلگرام را دریافت کنید. اگر فایلی بزرگتر از حجم مجاز باشد، قابلیت تکه‌تکه کردن (RAR) فعال می‌شود.\n\n"
        "🔸 *دستور:* `/tgposts <تعداد> @<آیدی_کانال>`\n"
        "🔹 *مثال:* `/tgposts 5 @varzesh3` (دریافت ۵ پست آخر)"
    ),
    "help_google": (
        "🔍 *راهنمای جستجوی گوگل*\n\n"
        "می‌توانید مستقیماً از طریق ربات در گوگل جستجو کنید.\n\n"
        "🔸 *دستور:* `/google <عبارت جستجو>`\n"
        "🔹 *مثال:* `/google اخبار تکنولوژی`"
    ),
    "help_image": (
        "🖼 *راهنمای تصویر*\n\n"
        "ابزاری برای پردازش و کار با تصاویر.\n\n"
        "🔸 *دستور:* `/image <پارامترها>`\n"
        "_(برای جزئیات بیشتر دستور را بدون پارامتر ارسال کنید)_"
    )
}

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📺 یوتیوب", callback_data="help_yt"),
            InlineKeyboardButton("🌐 دانلود مستقیم", callback_data="help_dl")
        ],
        [
            InlineKeyboardButton("✈️ تلگرام", callback_data="help_tg"),
            InlineKeyboardButton("📌 پینترست", callback_data="help_pin")
        ],
        [
            InlineKeyboardButton("🖼 تصویر", callback_data="help_image"),
            InlineKeyboardButton("🔍 گوگل", callback_data="help_google")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی راهنما", callback_data="help_main")]]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ارسال پیام خوش‌آمدگویی با یک دکمه برای باز کردن منو
    keyboard = [[InlineKeyboardButton("📚 دریافت راهنمای ربات", callback_data="help_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=START_MESSAGE,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # دستور /help هم مستقیماً منوی شیشه‌ای را باز می‌کند
    await update.message.reply_text(
        text="👇 *لطفاً برای مشاهده راهنما، یک بخش را انتخاب کنید:*",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

# این تابع برای مدیریت کلیک روی دکمه‌های راهنما است
async def help_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help_main":
        await query.edit_message_text(
            text="👇 *لطفاً برای مشاهده راهنما، یک بخش را انتخاب کنید:*",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    elif data in HELP_TEXTS:
        await query.edit_message_text(
            text=HELP_TEXTS[data],
            reply_markup=get_back_keyboard(),
            parse_mode="Markdown"
        )
