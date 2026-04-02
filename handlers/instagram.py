import instaloader
from telegram import Update
from telegram.ext import ContextTypes

L = instaloader.Instaloader()

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "⚠️ لطفاً یک نام کاربری اینستاگرام وارد کنید!\n*نحوه استفاده:* `/ig <username>`",
            parse_mode="Markdown"
        )
        return

    username = context.args[0].replace("@", "")
    status_msg = await update.message.reply_text(f"🔍 در حال دریافت پست‌های @{username}...")

    try:
        profile = instaloader.Profile.from_username(L.context, username)
        posts = list(profile.get_posts())[:5]  # آخرین 5 پست

        if not posts:
            await status_msg.edit_text("❌ پستی یافت نشد.")
            return

        await status_msg.edit_text(f"✅ {len(posts)} پست یافت شد. در حال ارسال...")

        for post in posts:
            caption = f"📸 @{username}\n\n{post.caption[:500] if post.caption else 'بدون توضیح'}"
            if post.is_video:
                await update.message.reply_video(
                    video=post.video_url,
                    caption=caption
                )
            else:
                await update.message.reply_photo(
                    photo=post.url,
                    caption=caption
                )

        await status_msg.delete()

    except instaloader.exceptions.ProfileNotExistsException:
        await status_msg.edit_text(f"❌ کاربر @{username} یافت نشد.")
    except Exception as e:
        await status_msg.edit_text(f"❌ خطا: `{str(e)}`", parse_mode="Markdown")
