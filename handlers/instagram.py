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

        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        try:
            url = f"https://www.instagram.com/{username}/"
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait a bit for JS to render
            await asyncio.sleep(4)

            # Take a screenshot for debugging - REMOVE LATER
            await page.screenshot(path="/tmp/instagram_debug.png", full_page=False)

            # Get full page text for diagnosis
            page_text = await page.inner_text('body')
            page_html = await page.content()

            # --- Diagnosis ---
            if 'Log in' in page_text and ('loginForm' in page_html or 'Login' in page_text):
                await browser.close()
                return None, "Instagram is showing login wall."

            if 'Sorry, this page' in page_text or 'Page Not Found' in page_text:
                await browser.close()
                return None, f"Account @{username} not found."

            if 'This Account is Private' in page_text:
                await browser.close()
                return None, f"@{username} is a private account."

            # Debug: show what we actually got
            print(f"[DEBUG] Page title: {await page.title()}")
            print(f"[DEBUG] Page text preview: {page_text[:500]}")

            # Try multiple selectors for posts
            post_links = []

            # Selector strategy 1: standard article links
            try:
                post_links = await page.eval_on_selector_all(
                    'a[href*="/p/"]',
                    'links => [...new Set(links.map(l => l.href))].slice(0, 5)'
                )
                print(f"[DEBUG] Strategy 1 found: {len(post_links)} links")
            except:
                pass

            # Selector strategy 2: all links containing /p/
            if not post_links:
                try:
                    all_links = await page.eval_on_selector_all(
                        'a',
                        'links => links.map(l => l.href)'
                    )
                    post_links = list(dict.fromkeys([
                        l for l in all_links
                        if '/p/' in l and 'instagram.com' in l
                    ]))[:5]
                    print(f"[DEBUG] Strategy 2 found: {len(post_links)} links")
                except:
                    pass

            # Selector strategy 3: scroll and retry
            if not post_links:
                await page.evaluate("window.scrollTo(0, 300)")
                await asyncio.sleep(2)
                try:
                    post_links = await page.eval_on_selector_all(
                        'a[href*="/p/"]',
                        'links => [...new Set(links.map(l => l.href))].slice(0, 5)'
                    )
                    print(f"[DEBUG] Strategy 3 found: {len(post_links)} links")
                except:
                    pass

            if not post_links:
                # Show what HTML elements exist for debugging
                tags = await page.eval_on_selector_all(
                    '*',
                    'els => [...new Set(els.map(e => e.tagName))].join(", ")'
                )
                print(f"[DEBUG] Tags found on page: {tags[:300]}")
                await browser.close()
                return None, "No posts found. Instagram may have changed its layout."

            # Get profile name
            try:
                name_el = await page.query_selector('h1, h2')
                if name_el:
                    profile_name = (await name_el.inner_text()).strip() or username
            except:
                profile_name = username

            # Visit each post
            for link in post_links:
                try:
                    await page.goto(link, wait_until='domcontentloaded', timeout=20000)
                    await asyncio.sleep(2)

                    post = {'url': link}

                    # Get image
                    try:
                        img_el = await page.query_selector('article img[srcset], article img[src]')
                        if not img_el:
                            img_el = await page.query_selector('img[srcset], img[src]')
                        if img_el:
                            srcset = await img_el.get_attribute('srcset')
                            if srcset:
                                sources = []
                                for s in srcset.split(','):
                                    parts = s.strip().split(' ')
                                    if len(parts) == 2:
                                        try:
                                            sources.append((parts[0], int(parts[1].replace('w', ''))))
                                        except:
                                            pass
                                if sources:
                                    post['image'] = max(sources, key=lambda x: x[1])[0]
                            if not post.get('image'):
                                post['image'] = await img_el.get_attribute('src')
                    except:
                        pass

                    # Get video
                    try:
                        video_el = await page.query_selector('video')
                        if video_el:
                            post['video'] = await video_el.get_attribute('src')
                    except:
                        pass

                    # Get caption
                    try:
                        for selector in ['h1', 'article h1', 'div[data-testid="post-comment-root"] span', 'ul li span']:
                            caption_el = await page.query_selector(selector)
                            if caption_el:
                                text = (await caption_el.inner_text()).strip()
                                if text:
                                    post['caption'] = text
                                    break
                    except:
                        post['caption'] = ''

                    if post.get('image') or post.get('video'):
                        posts.append(post)

                except Exception as e:
                    print(f"[DEBUG] Failed to fetch post {link}: {e}")
                    continue

        except Exception as e:
            await browser.close()
            return None, f"Browser error: {str(e)[:300]}"

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
        error_msg = str(e)[:200]
        await status_msg.edit_text(f"❌ Unexpected error:\n`{error_msg}`", parse_mode='Markdown')
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
                f"⚠️ Could not send post {i+1}: `{str(e)[:100]}`",
                parse_mode='Markdown'
            )
            continue

    await status_msg.edit_text(
        f"✅ Done! Fetched {len(posts)} posts from *{profile_name}*",
        parse_mode='Markdown'
    )
