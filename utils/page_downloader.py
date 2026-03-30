# handlers/webpage.py
import os
import time
from urllib.parse import urlparse
from playwright.async_api import async_playwright


async def download_webpage_as_mhtml(url: str, download_dir: str = "downloads") -> str:
    """
    Downloads a webpage with rendered JavaScript and all assets as a single MHTML file.
    """
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)

    # Create a safe filename based on the domain and timestamp
    domain = urlparse(url).netloc.replace("www.", "")
    timestamp = int(time.time())
    filename = f"{domain}_{timestamp}.mhtml"
    filepath = os.path.join(download_dir, filename)

    async with async_playwright() as p:
        # Launch headless chromium
        ## chromium for server side
        browser = await p.chromium.launch(headless=True)
        ## use local chrome browser,
        # browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Go to the URL and wait for the network to be idle (ensures JS finishes loading)
            await page.goto(url, wait_until="networkidle", timeout=300000)

            # Optionally scroll to the bottom to trigger lazy-loaded images
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)  # wait 2 seconds for lazy loads

            # Create a Chrome DevTools Protocol (CDP) session to capture MHTML
            client = await context.new_cdp_session(page)

            # Capture the snapshot as MHTML
            snapshot = await client.send("Page.captureSnapshot", {"format": "mhtml"})
            mhtml_data = snapshot.get("data")

            # Save the data to a file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(mhtml_data)

            return filepath

        except Exception as e:
            print(f"Error downloading webpage: {e}")
            return None
        finally:
            await browser.close()
