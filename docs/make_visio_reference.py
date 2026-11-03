#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
让本机 Visio 自己画线并另存，产出「黄金参照样本」。
关键：每个可能失败的 COM 调用都单独 try/except，避免一处失败中断整段。
"""
import os
import re
import time
import zipfile

import win32com.client

OUT = r"C:\Users\zhanghh\AppData\Local\Temp\visio_ref"
os.makedirs(OUT, exist_ok=True)


def build():
    app = win32com.client.DispatchEx("Visio.Application")
    app.Visible = False
    doc = None
    try:
        doc = app.Documents.Add("")
        page = doc.Pages.Item(1)

        # 1) 水平线
        h = page.DrawLine(2.0, 8.0, 5.0, 8.0)
        # 2) 垂直线（向下）
        v = page.DrawLine(2.0, 6.0, 2.0, 4.0)
        # 3) 斜线
        d = page.DrawLine(6.0, 8.0, 8.0, 5.0)

        for s, label in ((h, "水平"), (v, "垂直"), (d, "斜线")):
            for cell, val in (("EndArrow", "4"), ("ObjType", "2"), ("1D", "1")):
                try:
                    s.CellsU(cell).FormulaU = val
                except Exception as e:
                    print(f"  {label} 设 {cell}={val} 失败: {str(e)[:50]}")

        path = os.path.join(OUT, "ref.vsdx")
        if os.path.exists(path):
            os.remove(path)
        doc.SaveAs(path)
        doc.Close()
        doc = None
        return path
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


path = None
for i in range(5):
    try:
        path = build()
        break
    except Exception as e:
        print(f"第{i+1}次失败: {str(e)[:90]}")
        time.sleep(4)

if not path or not os.path.exists(path):
    print("参照样本生成失败（Visio 激活限制）")
    raise SystemExit(1)

print("参照样本:", path, os.path.getsize(path), "bytes")
z = zipfile.ZipFile(path)
pg = z.read("visio/pages/page1.xml").decode("utf-8")

print()
print("=" * 70)
print("Visio 自己画的线 —— Shape XML")
print("=" * 70)
for m in re.finditer(r"<Shape\b[^>]*>.*?</Shape>", pg, re.S):
    body = m.group(0)
    if "Line" not in body[:200] and "Connector" not in body[:200]:
        continue
    attrs = re.search(r"<Shape ([^>]*)>", body).group(1)
    print("ATTRS:", attrs[:220])
    cells = re.findall(r"<Cell N='([A-Za-z0-9]+)' V='([^']*)'", body)
    print("CELLS:", cells)
    geo = re.search(r"<Section N='Geometry'.*?</Section>", body, re.S)
    print("GEOM:", geo.group(0) if geo else "NONE")
    print()
