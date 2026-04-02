# handlers/instagram.py
import httpx
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ContextTypes

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

async def fetch_instagram_posts(username: str):
    posts = []
    
    try:
        # Try imginn.com as proxy
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            response = await client.get(f"https://imginn.com/{username}/")
            
            if response.status_code != 200:
                return None, f"Profile not found or blocked (status {response.status_code})"
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get profile info
            name_tag = soup.find('h1', class_='name')
            profile_name = name_tag.text.strip() if name_tag else username
            
            # Find posts
            items = soup.find_all('div', class_='item')[:5]
            
            for item in items:
                post = {}
                
                # Get image
                img = item.find('img')
                if img:
                    post['image'] = img.get('data-src') or img.get('src')
                
                # Get video
                video = item.find('video')
                if video:
                    source = video.find('source')
                    if source:
                        post['video'] = source.get('src')
                
                # Get caption
                caption = item.find('p')
                post['caption'] = caption.text.strip() if caption else ''
                
                # Get post link
                link = item.find('a', class_='img')
                if link:
                    post['url'] = "https://imginn.com" + link.get('href', '')
                
                if post.get('image') or post.get('video'):
                    posts.append(post)
            
            return posts, profile_name
            
    except Exception as e:
        return None, str(e)


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
        await status_msg.edit_text(f"❌ Error: {profile_name}")
        return
    
    if not posts:
        await status_msg.edit_text(f"❌ No posts found for @{username}. Profile may be private.")
        return
    
    await status_msg.edit_text(f"📥 Sending {len(posts)} latest posts from *{profile_name}*...", parse_mode='Markdown')
    
    for i, post in enumerate(posts):
        try:
            caption_text = f"📸 *{profile_name}*\n\n{post.get('caption', '')[:900]}"
            if post.get('url'):
                caption_text += f"\n\n🔗 [View on Instagram]({post['url']})"
            
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
            await update.message.reply_text(f"⚠️ Could not send post {i+1}: {str(e)}")
            continue
    
    await status_msg.edit_text(f"✅ Done! Fetched posts from *{profile_name}*", parse_mode='Markdown')
