"""验证 PRCP 基础数据表 17 桶改造的 UI 效果"""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={'width': 1920, 'height': 900})
        page = await ctx.new_page()
        await page.goto('https://wxfzhh.online/prcp/login')
        await page.wait_for_load_state('networkidle')
        await page.fill('input[placeholder*="用户名"]', 'admin')
        await page.fill('input[type="password"]', 'admin123')
        await page.click('button[type="submit"]')
        try:
            await page.wait_for_url('**/dashboard', timeout=10000)
        except Exception:
            pass
        await page.goto('https://wxfzhh.online/prcp/basic')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path='C:/银行经营/PRCP/docs/term_buckets_basic.png',
            full_page=True,
        )
        print('basic 截图已保存')
        await page.goto('https://wxfzhh.online/prcp/data-reverse')
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path='C:/银行经营/PRCP/docs/term_buckets_reverse.png',
            full_page=True,
        )
        print('reverse 截图已保存')
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())