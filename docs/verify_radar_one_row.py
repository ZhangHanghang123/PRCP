"""Take screenshot to verify radar is just 1 row tall"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        await page.goto("https://wxfzhh.online/prcp/login")
        await page.wait_for_timeout(1500)
        try:
            await page.fill('input[placeholder*="账号"], input[placeholder*="用户"], input#username, input[type="text"]', "admin")
            await page.fill('input[type="password"], input#password', "admin123")
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(2000)
        except Exception as e:
            print("login err:", e)

        await page.goto("https://wxfzhh.online/prcp/reverse-dashboard")
        await page.wait_for_timeout(4000)

        await page.screenshot(path="C:/银行经营/PRCP/docs/kpi_one_row.png", full_page=False)
        print("screenshot saved")
        await browser.close()

asyncio.run(main())