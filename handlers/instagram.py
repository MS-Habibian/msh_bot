# handlers/instagram.py
import httpx
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ContextTypes
import json
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

PROXY_SITES = [
    ("picuki", "https://www.picuki.com/profile/{username}"),
    ("instastories", "https://www.instastories.watch/user/{username}"),
]

async def fetch_via_picuki(client: httpx.AsyncClient, username: str):
    """Scrape via picuki.com"""
    posts = []
    url = f"https://www.picuki.com/profile/{username}"
    
    response = await client.get(url, timeout=20)
    if response.status_code != 200:
        return None, f"picuki returned {response.status_code}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Profile name
    name_tag = soup.find('div', class_='profile-name-top')
    profile_name = name_tag.text.strip() if name_tag else username
    
    # Posts
    boxes = soup.find_all('div', class_='box-photo')[:5]
    
    for box in boxes:
        post = {}
        
        img = box.find('img')
        if img:
            post['image'] = img.get('src') or img.get('data-src')
        
        caption_tag = box.find('div', class_='photo-description')
        post['caption'] = caption_tag.text.strip() if caption_tag else ''
        
        link = box.find('a', href=True)
        if link:
            post['url'] = link['href']
        
        if post.get('image'):
            posts.append(post)
    
    return posts, profile_name


async def fetch_via_instagramio(client: httpx.AsyncClient, username: str):
    """Scrape via instagram.io / bibliogram alternative"""
    posts = []
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    
    headers = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}
    response = await client.get(url, headers=headers, timeout=20)
    
    if response.status_code != 200:
        return None, f"instagram returned {response.status_code}"
    
    try:
        data = response.json()
        user = data.get('graphql', {}).get('user') or data.get('data', {}).get('user', {})
        
        if not user:
            return None, "Could not parse user data"
        
        profile_name = user.get('full_name', username)
        edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])[:5]
        
        for edge in edges:
            node = edge.get('node', {})
            post = {}
            
            # Image
            post['image'] = node.get('display_url') or node.get('thumbnail_src')
            
            # Caption
            caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
            if caption_edges:
                post['caption'] = caption_edges[0].get('node', {}).get('text', '')
            
            # Video
            if node.get('is_video'):
                post['video_url'] = node.get('video_url')
            
            # Link
            shortcode = node.get('shortcode')
            if shortcode:
                post['url'] = f"https://www.instagram.com/p/{shortcode}/"
            
            if post.get('image'):
                posts.append(post)
        
        return posts, profile_name
        
    except Exception as e:
        return None, f"JSON parse error: {e}"


async def fetch_via_storiesig(client: httpx.AsyncClient, username: str):
    """Use storiesig API"""
    posts = []
    url = f"https://storiesig.info/api/ig/posts?username={username}"
    
    response = await client.get(url, timeout=20)
    if response.status_code != 200:
        return None, f"storiesig returned {response.status_code}"
    
    try:
        data = response.json()
        items = data.get('items', data.get('posts', []))[:5]
        profile_name = data.get('username', username)
        
        for item in items:
            post = {}
            
            # Try different image keys
            post['image'] = (
                item.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
                or item.get('display_url')
                or item.get('thumbnail_url')
            )
            
            # Caption
            caption = item.get('caption') or {}
            if isinstance(caption, dict):
                post['caption'] = caption.get('text', '')
            else:
                post['caption'] = str(caption)
            
            # Link
            code = item.get('code') or item.get('shortcode')
            if code:
                post['url'] = f"https://www.instagram.com/p/{code}/"
            
            if post.get('image'):
                posts.append(post)
        
        return posts, profile_name
        
    except Exception as e:
        return None, f"JSON parse error: {e}"


async def fetch_instagram_posts(username: str):
    """Try multiple methods until one works"""
    
    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=20,
        verify=False  # Some proxies have SSL issues
    ) as client:
        
        # Method 1: Picuki
        try:
            posts, name = await fetch_via_picuki(client, username)
            if posts:
                return posts, name
        except Exception as e:
            pass
        
        # Method 2: Instagram JSON endpoint
        try:
            posts, name = await fetch_via_instagramio(client, username)
            if posts:
                return posts, name
        except Exception as e:
            pass
        
        # Method 3: StoriesIG API
        try:
            posts, name = await fetch_via_storiesig(client, username)
            if posts:
                return posts, name
        except Exception as e:
            pass
        
        return None, "❌ All methods failed. Instagram is heavily rate-limited without login."


async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📸 *Instagram Post Fetcher*\n\nUsage: `/instagram <username>`\nExample: `/instagram nasa`",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0].replace('@', '').strip()
    status_msg = await update.message.reply_text(f"🔍 Fetching posts from @{username}...")
    
    posts, profile_name = await fetch_instagram_posts(username)
    
    if posts is None:
        await status_msg.edit_text(
            f"❌ *Could not fetch posts*\n\n{profile_name}\n\n"
            f"Instagram aggressively blocks scrapers. Try again later.",
            parse_mode='Markdown'
        )
        return
    
    if not posts:
        await status_msg.edit_text(
            f"❌ No posts found for @{username}\n"
            f"Profile may be private or username incorrect."
        )
        return
    
    await status_msg.edit_text(
        f"📥 Sending {len(posts)} posts from *{profile_name}*...",
        parse_mode='Markdown'
    )
    
    for i, post in enumerate(posts):
        try:
            caption_text = f"📸 *{profile_name}*\n\n{post.get('caption', '')[:900]}"
            if post.get('url'):
                caption_text += f"\n\n🔗 [View Post]({post['url']})"
            
            if post.get('video_url'):
                await update.message.reply_video(
                    video=post['video_url'],
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
            await update.message.reply_text(f"⚠️ Could not send post {i+1}: `{e}`", parse_mode='Markdown')
            continue
    
    await status_msg.edit_text(
        f"✅ Done! Fetched posts from *{profile_name}*",
        parse_mode='Markdown'
    )
