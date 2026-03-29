# handlers/dlp_handler.py (یا هر فایلی که دستورات را مدیریت می‌کنید)
import os
from utils.web_downloader import download_single_html, cleanup_file

# این تابع باید به عنوان هندلر دستور /dlp تنظیم شود
async def dlp_command(message):
    # جدا کردن لینک از متن پیام (مثلاً: /dlp https://example.com)
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.reply_text(
            "⚠️ لطفاً لینک مورد نظر خود را همراه با دستور ارسال کنید.\n"
            "مثال:\n"
            "`/dlp https://example.com`",
            parse_mode="Markdown"
        )
        return
        
    url = parts[1]
    
    # پیام انتظار
    wait_msg = await message.reply_text("⏳ در حال دانلود صفحه و فایل‌های مرتبط، لطفاً کمی صبر کنید...")
    
    # فراخوانی تابع دانلود
    output_file = download_single_html(url, downloads_dir="downloads")
    
    if output_file and os.path.exists(output_file):
        try:
            # ارسال فایل به کاربر
            with open(output_file, 'rb') as file:
                await message.reply_document(
                    document=file,
                    caption="✅ صفحه مورد نظر شما با موفقیت دانلود شد!\n\nاین فایل شامل تمام تصاویر و استایل‌های صفحه است و به صورت آفلاین اجرا می‌شود."
                )
        except Exception as e:
            await message.reply_text("❌ مشکلی در ارسال فایل به وجود آمد.")
            print(f"Send error: {e}")
        finally:
            # پاک کردن فایل از روی سرور پس از ارسال
            cleanup_file(output_file)
            
            # پاک کردن پیام انتظار
            await wait_msg.delete()
    else:
        # در صورت شکست در دانلود
        await wait_msg.edit_text("❌ متاسفانه در دانلود این صفحه مشکلی پیش آمد. ممکن است سایت در دسترس نباشد یا دانلود آن مسدود شده باشد.")
        cleanup_file(output_file)
