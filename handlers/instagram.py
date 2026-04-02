# handlers/instagram.py
import asyncio
import os
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ContextTypes


async def fetch_instagram_posts_playwright(username: str):
    """Fetch Instagram posts using Playwright (real browser)"""
    posts = []
    profile_name = username

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Block unnecessary resources to speed up loading
        await context.route("**/*.{woff,woff2,ttf,otf}", lambda route: route.abort())

        page = await context.new_page()

        # Hide automation flags
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        try:
            url = f"https://www.instagram.com/{username}/"
            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Check if login wall appeared
            page_content = await page.content()
            if 'Log in' in page_content and 'loginForm' in page_content:
                await browser.close()
                return None, "Instagram is showing login wall. Try again later."

            # Check if account exists
            if 'Sorry, this page' in page_content or 'Page Not Found' in page_content:
                await browser.close()
                return None, f"Account @{username} not found."

            # Check if private
            if 'This Account is Private' in page_content:
                await browser.close()
                return None, f"@{username} is a private account."

            # Wait for posts to load
            await page.wait_for_selector('article', timeout=15000)

            # Scroll down a bit to trigger lazy loading
            await page.evaluate("window.scrollBy(0, 500)")
            await asyncio.sleep(2)

            # Get profile name
            try:
                name_el = await page.query_selector('h1, h2')
                if name_el:
                    profile_name = await name_el.inner_text()
                    profile_name = profile_name.strip()
            except:
                profile_name = username

            # Get all post links (first 5)
            post_links = await page.eval_on_selector_all(
                'article a[href*="/p/"]',
                'links => [...new Set(links.map(l => l.href))].slice(0, 5)'
            )

            if not post_links:
                await browser.close()
                return None, "No posts found. Profile may be empty or Instagram blocked the request."

            # Visit each post and extract data
            for link in post_links:
                try:
                    await page.goto(link, wait_until='networkidle', timeout=20000)
                    await asyncio.sleep(1)

                    post = {'url': link}

                    # Get image(s)
                    try:
                        img_el = await page.query_selector('article img[srcset], article img[src]')
                        if img_el:
                            # Prefer srcset highest resolution
                            srcset = await img_el.get_attribute('srcset')
                            if srcset:
                                # Parse srcset and get highest resolution
                                sources = [s.strip().split(' ') for s in srcset.split(',')]
                                sources = [(s[0], int(s[1].replace('w', ''))) for s in sources if len(s) == 2]
                                if sources:
                                    best = max(sources, key=lambda x: x[1])
                                    post['image'] = best[0]
                            
                            if not post.get('image'):
                                post['image'] = await img_el.get_attribute('src')
                    except:
                        pass

                    # Get video
                    try:
                        video_el = await page.query_selector('article video')
                        if video_el:
                            post['video'] = await video_el.get_attribute('src')
                    except:
                        pass

                    # Get caption
                    try:
                        caption_el = await page.query_selector('article h1, div[data-testid="post-comment-root"] span')
                        if caption_el:
                            post['caption'] = await caption_el.inner_text()
                            post['caption'] = post['caption'].strip()
                    except:
                        post['caption'] = ''

                    # Get likes if available
                    try:
                        likes_el = await page.query_selector('section span[class*="like"], button span')
                        if likes_el:
                            post['likes'] = await likes_el.inner_text()
                    except:
                        post['likes'] = ''

                    if post.get('image') or post.get('video'):
                        posts.append(post)

                except Exception as e:
                    continue

        except Exception as e:
            await browser.close()
            return None, f"Browser error: {e}"

        await browser.close()

    return posts, profile_name


async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📸 *Instagram Post Fetcher*\n\n"
            "Usage: `/instagram <username>`\n"
            "Example: `/instagram nasa`\n\n"
            "⚠️ Only works for public accounts.",
            parse_mode='Markdown'
        )
        return

    username = context.args[0].replace('@', '').strip()
    status_msg = await update.message.reply_text(
        f"🌐 Opening Instagram profile for @{username}...\n"
        f"_(This may take 30-60 seconds)_",
        parse_mode='Markdown'
    )

    try:
        posts, profile_name = await fetch_instagram_posts_playwright(username)
    except Exception as e:
        await status_msg.edit_text(f"❌ Unexpected error: `{e}`", parse_mode='Markdown')
        return

    if posts is None:
        await status_msg.edit_text(
            f"❌ *Failed:* {profile_name}",
            parse_mode='Markdown'
        )
        return

    if not posts:
        await status_msg.edit_text(f"❌ No posts found for @{username}")
        return

    await status_msg.edit_text(
        f"📥 Sending {len(posts)} posts from *{profile_name}*...",
        parse_mode='Markdown'
    )

    for i, post in enumerate(posts):
        try:
            caption_text = f"📸 *{profile_name}*"
            if post.get('likes'):
                caption_text += f"  |  ❤️ {post['likes']}"
            if post.get('caption'):
                caption_text += f"\n\n{post['caption'][:900]}"
            if post.get('url'):
                caption_text += f"\n\n🔗 [View Post]({post['url']})"

            if post.get('video'):
                await update.message.reply_video(
                    video=post['video'],
                    caption=caption_text,
                    parse_mode='Markdown'
                )
            elif post.get('image'):
                await update.message.reply_photo(
                    photo=post['image'],
                    caption=caption_text,
                    parse_mode='Markdown'
                )

        except Exception as e:
            await update.message.reply_text(
                f"⚠️ Could not send post {i+1}: `{e}`",
                parse_mode='Markdown'
            )
            continue

    await status_msg.edit_text(
        f"✅ Done! Fetched {len(posts)} posts from *{profile_name}*",
        parse_mode='Markdown'
    )
