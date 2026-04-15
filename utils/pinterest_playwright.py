from playwright.async_api import async_playwright
import urllib.parse

async def search_pinterest_playwright(query: str, limit: int = 10) -> list:
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://duckduckgo.com/?q={encoded_query}&iax=images&ia=images"

    results = []

    async with async_playwright() as p:
        # اضافه کردن آرگومان برای مخفی کردن حالت اتوماسیون (جلوگیری از بلاک شدن)
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        try:
            # لود کردن صفحه
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # کمی صبر می‌کنیم تا اسکریپت‌های سایت عکس‌ها را رندر کنند
            await page.wait_for_timeout(3000) 

            # اجرای اسکریپت داخل مرورگر برای پیدا کردن تمام تگ‌های عکس که سایز مناسبی دارند
            images_data = await page.evaluate('''() => {
                let items = [];
                // پیدا کردن تمام عکس‌ها در صفحه
                let imgs = document.querySelectorAll('img');
                for (let img of imgs) {
                    let src = img.src;
                    // فیلتر کردن آیکون‌ها و لوگوها، فقط عکس‌های واقعی را می‌خواهیم
                    if (src && src.includes('external-content.duckduckgo.com')) {
                        items.push(src);
                    }
                }
                return items;
            }''')

            # حذف موارد تکراری و ساخت لیست نهایی
            unique_images = list(dict.fromkeys(images_data))
            
            for i, img_url in enumerate(unique_images[:limit], start=1):
                # تبدیل لینک پیش‌نمایش داک‌داک‌گو به لینک اصلی در صورت امکان
                original_url = img_url
                if "fui=" in img_url:
                    try:
                        extracted = urllib.parse.parse_qs(urllib.parse.urlparse(img_url).query).get('fui', [img_url])[0]
                        original_url = extracted
                    except:
                        pass

                results.append({
                    'id': str(i),
                    'title': f"Pinterest Image {i}",
                    'thumbnail': img_url,
                    'original': original_url
                })

        except Exception as e:
            print(f"Playwright Pinterest Search Error: {e}")
            # در صورت نیاز به دیباگ می‌توانید اسکرین‌شات بگیرید:
            # await page.screenshot(path="error_screenshot.png")
        finally:
            await browser.close()

    return results
