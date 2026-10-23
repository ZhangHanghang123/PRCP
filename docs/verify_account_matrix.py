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
        # 进入"基础数据表"页面（路由：/data-maint/BASIC）
        await page.goto("https://wxfzhh.online/prcp/data-maint/BASIC", wait_until="networkidle", timeout=60000)
        print(f"页面 URL: {page.url}")
        await page.wait_for_timeout(6000)
        # 截图全图
        await page.screenshot(path="C:/银行经营/PRCP/docs/prcp_basic_data_full.png", full_page=False)
        # 找 Badge
        badges = await page.query_selector_all(".ant-badge-count")
        print(f"Badge 数量: {len(badges)}")
        for i, b in enumerate(badges):
            txt = await b.inner_text()
            print(f"  Badge {i}: {txt}")
        # 点击账户册矩阵 Tab
        tabs = await page.query_selector_all(".ant-tabs-tab")
        clicked = False
        for t in tabs:
            txt = await t.inner_text()
            if "账户册矩阵" in txt:
                await t.click()
                clicked = True
                print(f"点击 Tab: {txt}")
                break
        if not clicked:
            print("未找到账户册矩阵 Tab")
        await page.wait_for_timeout(4000)
        # 截图
        await page.screenshot(path="C:/银行经营/PRCP/docs/prcp_account_matrix.png", full_page=False)
        all_rows = await page.query_selector_all("tr.ant-table-row")
        print(f"\n账户册矩阵 表格行数: {len(all_rows)}")
        # 取编码列
        codes = await page.eval_on_selector_all(
            "tr.ant-table-row td:first-child code",
            "els => els.map(e => e.textContent)"
        )
        print(f"\n前 20 行账户册编码:")
        for c in codes[:20]:
            print(f"  {c}")
        print(f"...共 {len(codes)} 行编码")
        await browser.close()

asyncio.run(main())