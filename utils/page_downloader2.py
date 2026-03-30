import os
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright


async def download_as_pdf(
    url: str, format_type: str = "pdf", download_dir: str = "downloads"
) -> str:
    print("\n\n!@#$!@$!@#$", url)
    """
    format_type can be 'pdf' or 'png'
    """
    os.makedirs(download_dir, exist_ok=True)
    domain = urlparse(url).netloc.replace("www.", "")
    timestamp = int(time.time())

    ext = ".pdf" if format_type == "pdf" else ".png"
    filename = f"{domain}_{timestamp}{ext}"
    filepath = os.path.join(download_dir, filename)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ## use local chrome browser,
        # browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800}  # Set a good desktop width
        )
        page = await context.new_page()
        print("page:", page)
        try:
            # Load page
            print("a")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print("b")
            # Smoothly scroll to the bottom to force all lazy-loaded images to render
            await page.evaluate(
                """
                async () => {
                    await new Promise((resolve) => {
                        let totalHeight = 0;
                        const distance = 200;
                        const timer = setInterval(() => {
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            if (totalHeight >= scrollHeight - window.innerHeight) {
                                clearInterval(timer);
                                resolve();
                            }
                        }, 100);
                    });
                }
            """
            )
            print("c")
            # Wait a moment for final images/fonts to pop in after scrolling
            await page.wait_for_timeout(3000)
            print("d")

            # Scroll back to top just in case
            await page.evaluate("window.scrollTo(0, 0)")
            print("e")
            if format_type == "pdf":
                # Generate PDF
                print("f")
                await page.pdf(path=filepath, format="A4", print_background=True)
            else:
                # Generate Full-Page PNG
                await page.screenshot(path=filepath, full_page=True)

            return filepath

        except Exception as e:
            print(f"Error downloading webpage: {e}")
            return None
        finally:
            await browser.close()
