import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(r"C:/银行经营/PRCP/docs")
OUT.mkdir(parents=True, exist_ok=True)

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

        await page.goto("https://wxfzhh.online/prcp/lcr-param", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUT / "lcr_param_factor_zero.png"), full_page=False)
        print("LCR 截图完成")

        await page.goto("https://wxfzhh.online/prcp/nsfr-param", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        await page.screenshot(path=str(OUT / "nsfr_param_factor_zero.png"), full_page=False)
        print("NSFR 截图完成")

        await browser.close()

asyncio.run(main())