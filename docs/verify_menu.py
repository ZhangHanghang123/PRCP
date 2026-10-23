import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1600, "height": 900})
        page = await ctx.new_page()
        # 登录
        await page.goto("https://wxfzhh.online/prcp/login", wait_until="networkidle", timeout=60000)
        await page.fill('input[placeholder="用户名"]', "admin")
        await page.fill('input[placeholder="密码"]', "admin123")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard", timeout=60000)
        # 等待页面加载
        await page.wait_for_timeout(3000)
        # 点击所有菜单展开
        menus = await page.query_selector_all(".ant-menu-submenu-title")
        for m in menus:
            try:
                txt = await m.inner_text()
                # 展开"计量参数补录"和"反算决策"
                if "计量参数" in txt or "反算决策" in txt:
                    await m.click()
                    await page.wait_for_timeout(500)
            except: pass
        await page.wait_for_timeout(1000)
        await page.screenshot(path="C:/银行经营/PRCP/docs/menu_layout.png", full_page=False)
        # 列出所有菜单项
        items = await page.query_selector_all(".ant-menu-item, .ant-menu-submenu-title")
        print(f"\n菜单项:")
        for it in items:
            try:
                t = await it.inner_text()
                t = t.strip().replace("\n", " | ")
                if t and len(t) < 50:
                    print(f"  {t}")
            except: pass
        await browser.close()

asyncio.run(main())