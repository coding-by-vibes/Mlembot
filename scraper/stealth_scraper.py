import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

def fetch_with_googlebot(url: str) -> str:
    print(f"[Fallback] Fetching with Googlebot headers: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.encoding = response.apparent_encoding
    return response.text

async def fetch_content(url: str) -> str:
    # 🔍 Try using requests + Googlebot to get around light anti-bot walls
    if not urlparse(url).scheme:
     url = "https://" + url
    try:
        html = await asyncio.to_thread(fetch_with_googlebot, url)
        soup = BeautifulSoup(html, "html.parser")

        if soup.find("script", {"id": "__NEXT_DATA__"}):
            print("[Smart Fetch] Found __NEXT_DATA__ in requests version, skipping Playwright.")
            return html
        else:
            print("[Smart Fetch] No __NEXT_DATA__ found in initial requests response.")
    except Exception as e:
        print(f"[Smart Fetch] Initial requests check failed: {e}")

    # ⏳ Fallback to Playwright for dynamic content or heavy JS sites
    print(f"[Playwright] Navigating to {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)

        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        content = await page.content()
        await browser.close()
        return content
