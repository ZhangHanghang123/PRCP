#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用本机 Microsoft Visio 2013 的 COM 接口真实打开 .vsdx，验证文件能否被 Visio 加载。
这是最权威的验证——ProcessOn 的 Visio 导入器同样基于 Visio 文件结构。

Visio COM 的 OpenEx 参数：
  visOpenHidden = 2（隐藏打开，不弹 UI）
"""
import os
import sys

import win32com.client
from win32com.client import constants

VS_PATH = r"C:\银行经营\PRCP\docs\deliverables\PRCP组合反算主流程.vsdx"

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


def main():
    vsdx_path = sys.argv[1] if len(sys.argv) > 1 else VS_PATH
    print("=" * 68)
    print("用 Visio 2013 COM 真实打开 .vsdx")
    print("=" * 68)
    print(f"文件: {vsdx_path}")
    print(f"存在: {os.path.exists(vsdx_path)}")
    print()

    app = win32com.client.Dispatch("Visio.Application")
    app.Visible = False
    doc = None
    try:
        # visOpenHidden = 2
        doc = app.Documents.OpenEx(vsdx_path, 2)
        print("=== Visio 打开成功 ===")
        print(f"  文档名: {doc.Name}")
        print(f"  页数:   {doc.Pages.Count}")

        # 多页文件：逐页检查
        if doc.Pages.Count > 1:
            print()
            print("  逐页检查:")
            all_ok = True
            for pi in range(1, doc.Pages.Count + 1):
                pg = doc.Pages.Item(pi)
                n_text = 0
                n_card = 0
                first_ok = 0
                for si in range(1, pg.Shapes.Count + 1):
                    sh = pg.Shapes.Item(si)
                    try:
                        tx = sh.Text
                    except Exception:
                        tx = ""
                    if tx.strip():
                        n_text += 1
                    if "TaskCard" in sh.Name:
                        n_card += 1
                        if tx.strip().split("\r")[0].split("\n")[0].strip():
                            first_ok += 1
                ok = (n_card > 0 and first_ok == n_card)
                all_ok = all_ok and ok
                print(f"    第{pi}页 「{pg.Name}」: shape={pg.Shapes.Count} "
                      f"卡片={n_card} 首行非空={first_ok} {'OK' if ok else '异常'}")
            check("所有页的卡片首行均非空", all_ok)
            doc.Close()
            print()
            print("=" * 68)
            if FAILS:
                print(f"结果：{len(FAILS)} 条未通过")
                for f in FAILS:
                    print("  -", f)
                return 1
            print("结果：全部通过 —— Visio 2013 可正常打开本文件")
            return 0

        page = doc.Pages.Item(1)
        print(f"  页名:   {page.Name}")
        ps = page.PageSheet
        print(f"  页面尺寸: {ps.CellsU('PageWidth').ResultIU:.2f} x "
              f"{ps.CellsU('PageHeight').ResultIU:.2f} in")
        print(f"  Shape 数: {page.Shapes.Count}")

        # 统计形状类型与文本
        n_text = 0
        n_conn = 0
        card_first_ok = 0
        card_total = 0
        samples = []
        for i in range(1, page.Shapes.Count + 1):
            s = page.Shapes.Item(i)
            try:
                txt = s.Text
            except Exception:
                txt = ""
            if txt.strip():
                n_text += 1
            # 1 = visShapeForeign? 连接线判定：OneD
            try:
                if s.OneD:
                    n_conn += 1
            except Exception:
                pass
            if "TaskCard" in s.Name:
                card_total += 1
                # 首行（操作名）不能为空 —— 这是「黑字不显示」的典型症状
                first = txt.split("\r")[0].split("\n")[0].strip()
                if first:
                    card_first_ok += 1
                if len(samples) < 5 and txt.strip():
                    samples.append((s.Name, txt.strip().replace("\r", " | ")
                                    .replace("\n", " | ")))

        print(f"  含文字 shape: {n_text}")
        print(f"  一维(连接线) shape: {n_conn}")
        print(f"  卡片首行非空: {card_first_ok}/{card_total}")
        print()
        print("  文本抽样:")
        for nm, t in samples:
            print(f"    · {nm}: {t[:64]}")

        check("Visio 能打开文件", True)
        check("页数 >= 1", doc.Pages.Count >= 1)
        check(f"Shape 数 > 50（实际 {page.Shapes.Count}）", page.Shapes.Count > 50)
        check(f"含文字 shape > 40（实际 {n_text}）", n_text > 40)
        check(f"连接线 > 20（实际 {n_conn}）", n_conn > 20)
        check(f"所有卡片首行（操作名）非空（{card_first_ok}/{card_total}）",
              card_total > 0 and card_first_ok == card_total)

        # 让 Visio 另存一份：若能保存，说明 Visio 完全认得并解析了内部结构
        out = r"C:\Users\zhanghh\AppData\Local\Temp\vsdx_resaved.vsdx"
        if os.path.exists(out):
            os.remove(out)
        try:
            doc.SaveAs(out)
            check("Visio 能另存（结构被完整解析）", os.path.exists(out),
                  f"{os.path.getsize(out) if os.path.exists(out) else 0} bytes")
        except Exception as e:
            check("Visio 能另存", False, str(e))

        # 导出 PNG 交叉验证渲染
        try:
            png = r"C:\Users\zhanghh\AppData\Local\Temp\vsdx_render.png"
            if os.path.exists(png):
                os.remove(png)
            page.Export(png)
            check("Visio 能渲染导出 PNG", os.path.exists(png),
                  f"{os.path.getsize(png) if os.path.exists(png) else 0} bytes")
        except Exception as e:
            check("Visio 能渲染导出 PNG", False, str(e))

    except Exception as e:
        print(f"\n!!! Visio 打开失败: {e}")
        check("Visio 能打开文件", False, str(e))
    finally:
        try:
            if doc is not None:
                doc.Close()
        except Exception:
            pass
        try:
            app.Quit()
        except Exception:
            pass

    print()
    print("=" * 68)
    if FAILS:
        print(f"结果：{len(FAILS)} 条未通过")
        for f in FAILS:
            print("  -", f)
        return 1
    print("结果：全部通过 —— Visio 2013 可正常打开本文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
