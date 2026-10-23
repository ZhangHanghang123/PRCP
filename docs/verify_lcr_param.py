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
        print(f"登录后 URL: {page.url}")
        # 进入 LCR 参数补录
        await page.goto("https://wxfzhh.online/prcp/lcr-param", wait_until="networkidle", timeout=60000)
        print(f"LCR URL: {page.url}")
        await page.wait_for_timeout(5000)
        # 截图
        await page.screenshot(path="C:/银行经营/PRCP/docs/lcr_param_page.png", full_page=False)
        # 统计 KPI
        stats = await page.query_selector_all(".ant-statistic")
        print(f"\nKPI 统计数: {len(stats)}")
        for s in stats:
            txt = await s.inner_text()
            print(f"  {txt}")
        # 表格行数
        rows = await page.query_selector_all("tr.ant-table-row")
        print(f"\n表格行数: {len(rows)}")
        # 前 5 行编码
        codes = await page.eval_on_selector_all(
            "tr.ant-table-row td:nth-child(2)",
            "els => els.map(e => e.textContent.trim())"
        )
        print(f"\n前 5 行账户册编码:")
        for c in codes[:5]:
            print(f"  {c}")
        # 验证菜单显示
        menus = await page.query_selector_all(".ant-menu-item")
        menu_texts = []
        for m in menus:
            t = await m.inner_text()
            if "LCR" in t or "计量" in t or "指标" in t:
                menu_texts.append(t)
        print(f"\n菜单相关项:")
        for m in menu_texts:
            print(f"  {m}")
        await browser.close()

asyncio.run(main())