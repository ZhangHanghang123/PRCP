import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:/银行经营/PRCP/docs")
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("cet1-param", "cet1_param_page.png", "CET1"),
    ("eve-param", "eve_param_page.png", "EVE"),
    ("nim-param", "nim_param_page.png", "NIM"),
    ("roe-param", "roe_param_page.png", "ROE"),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1800, "height": 1000})
        page = await ctx.new_page()

        await page.goto("https://wxfzhh.online/prcp/login", wait_until="domcontentloaded", timeout=30000)
        await page.fill('input[placeholder="用户名"]', "admin")
        await page.fill('input[placeholder="密码"]', "admin123")
        await page.click('button[type="submit"]')
        await page.wait_for_url(lambda url: "/login" not in url, timeout=20000)
        await page.wait_for_timeout(1500)

        for slug, fname, name in PAGES:
            print(f"--- {name} ---")
            await page.goto(f"https://wxfzhh.online/prcp/{slug}", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(OUT / fname), full_page=False)
            rows = await page.query_selector_all(".ant-table-row")
            print(f"  行数: {len(rows)}")

        await browser.close()

asyncio.run(main())