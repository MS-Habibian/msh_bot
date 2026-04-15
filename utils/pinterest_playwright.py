from playwright.async_api import async_playwright
import urllib.parse

async def search_pinterest_playwright(query: str, limit: int = 10) -> list:
    """
    استفاده از مرورگر واقعی Playwright برای دور زدن خطای 403 DuckDuckGo
    """
    clean_query = query.replace('/pin', '').strip()
    search_query = f"{clean_query} site:pinterest.com"
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://duckduckgo.com/?q={encoded_query}&iax=images&ia=images"

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # باز کردن صفحه جستجوی عکس
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # صبر کردن تا عکس‌ها لود شوند
            await page.wait_for_selector("img.tile--img__img", timeout=10000)

            # استخراج اطلاعات عکس‌ها
            elements = await page.query_selector_all("div.tile--img")
            
            for i, el in enumerate(elements[:limit], start=1):
                img_element = await el.query_selector("img.tile--img__img")
                link_element = await el.query_selector("a.tile--img__sub")
                
                if img_element:
                    thumbnail = await img_element.get_attribute("src")
                    # برای دریافت عکس اصلی از داک داک گو معمولا لینک در href تگ a قرار دارد
                    # یا می‌توانیم از همان نسخه با کیفیت پیش‌نمایش استفاده کنیم
                    original_url = thumbnail
                    if original_url and original_url.startswith("//"):
                        original_url = "https:" + original_url

                    results.append({
                        'id': str(i),
                        'title': f"Pinterest Image {i}",
                        'thumbnail': original_url,
                        'original': original_url # نسخه اصلی
                    })

        except Exception as e:
            print(f"Playwright Pinterest Search Error: {e}")
        finally:
            await browser.close()

    return results
