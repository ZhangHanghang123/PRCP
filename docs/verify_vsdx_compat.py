#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对照真实 Visio 文件（vsdx 库自带 media.vsdx）逐项核验我们生成的 .vsdx
是否满足 Visio / ProcessOn 的加载要求。

检查项：
  C1 ZIP 结构与必需部件
  C2 [Content_Types].xml 覆盖声明齐全
  C3 关系链闭合（每个 Target 存在，每个部件有 rels）
  C4 VisioDocument 子元素顺序
  C5 Shape 子元素顺序（Cell* → Section* → Text）
  C6 命名空间前缀正确（r:id / xmlns:r）
  C7 第三方库可解析
"""
import os
import re
import sys
import zipfile
import xml.dom.minidom as minidom

REAL = r"C:/Users/zhanghh/AppData/Local/Programs/Python/Python314/Lib/site-packages/vsdx/media/media.vsdx"
OURS = r"C:/银行经营/PRCP/docs/deliverables/PRCP组合反算主流程.vsdx"

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


zo = zipfile.ZipFile(OURS)
zr = zipfile.ZipFile(REAL)
names = zo.namelist()

print("=" * 70)
print("C1  ZIP 结构与必需部件")
print("=" * 70)
for n in ["[Content_Types].xml", "_rels/.rels", "visio/document.xml",
          "visio/_rels/document.xml.rels", "visio/pages/pages.xml",
          "visio/pages/_rels/pages.xml.rels", "visio/windows.xml",
          "docProps/core.xml", "docProps/app.xml"]:
    check(f"存在 {n}", n in names)
check("至少一个 pageN.xml", any(n.startswith("visio/pages/page") and
                               n.endswith(".xml") for n in names))
check("[Content_Types].xml 是首个条目（OPC 推荐）",
      names[0] == "[Content_Types].xml", names[0])
check("ZIP 可正常解压（testzip）", zo.testzip() is None)

print()
print("=" * 70)
print("C2  ContentTypes 覆盖声明")
print("=" * 70)
ct = zo.read("[Content_Types].xml").decode("utf-8")
for part, ctype in [
    ("/visio/document.xml", "application/vnd.ms-visio.drawing.main+xml"),
    ("/visio/pages/pages.xml", "application/vnd.ms-visio.pages+xml"),
    ("/visio/windows.xml", "application/vnd.ms-visio.windows+xml"),
    ("/visio/pages/page1.xml", "application/vnd.ms-visio.page+xml"),
]:
    m = re.search(r'<Override PartName="%s" ContentType="([^"]+)"' % re.escape(part), ct)
    check(f"{part} 声明为 {ctype}", m is not None and m.group(1) == ctype,
          m.group(1) if m else "缺失")
# 每个实际存在的部件都要有 Override 或 Default 兜底
for n in names:
    if n.endswith(".xml") and not n.startswith("_rels") and "_rels/" not in n \
            and n != "[Content_Types].xml":
        check(f"部件已声明: {n}", f'PartName="/{n}"' in ct)

print()
print("=" * 70)
print("C3  关系链闭合")
print("=" * 70)
for rels_part in [n for n in names if n.endswith(".rels")]:
    base = os.path.dirname(os.path.dirname(rels_part))
    xml = zo.read(rels_part).decode("utf-8")
    for m in re.finditer(r'Target="([^"]+)"(?![^>]*TargetMode="External")', xml):
        target = m.group(1)
        if target.startswith("http"):
            continue
        resolved = os.path.normpath(os.path.join(base, target)).replace("\\", "/")
        check(f"{rels_part} → {target} 存在", resolved in names, resolved)

print()
print("=" * 70)
print("C4  VisioDocument 子元素顺序")
print("=" * 70)
doc = zo.read("visio/document.xml").decode("utf-8")
seq = []
depth = 0
for m in re.finditer(r"<(/?)([A-Za-z0-9]+)([^>]*?)(/?)>", doc):
    close, tag, attrs, selfc = m.groups()
    if tag == "VisioDocument":
        continue
    if depth == 0:
        seq.append(tag)
    if not close and not selfc:
        depth += 1
    elif close:
        depth -= 1
print(f"  实际顺序: {seq}")
EXPECT_DOC = ["DocumentSettings", "Colors", "FaceNames", "StyleSheets", "DocumentSheet"]
check("子元素顺序符合 Visio 规范", seq == EXPECT_DOC, f"期望 {EXPECT_DOC}")

print()
print("=" * 70)
print("C5  Shape 子元素顺序（Cell* → Section* → Text）")
print("=" * 70)
pg = zo.read("visio/pages/page1.xml").decode("utf-8")
shapes = re.findall(r"<Shape .*?</Shape>", pg, re.S)
check(f"解析到 {len(shapes)} 个 Shape", len(shapes) > 0)
bad = []
for s in shapes:
    # 只看 Shape 的**直接**子元素：Section 内部的 Cell 不算
    depth = 0
    order = []
    for m in re.finditer(r"<(/?)(Section|Text|Cell)\b", s):
        close, tag = m.group(1), m.group(2)
        if tag == "Section":
            if not close:
                if depth == 0:
                    order.append("Section")
                depth += 1
            else:
                depth -= 1
        elif tag == "Cell":
            if depth == 0:
                order.append("Cell")
        else:  # Text
            if depth == 0:
                order.append("Text")
    merged = []
    for t in order:
        if merged and merged[-1] == t:
            continue
        merged.append(t)
    # 连接线等无文字的 Shape 只有 Cell→Section，是合法的
    if merged not in (["Cell", "Section"], ["Cell", "Section", "Text"]):
        bad.append(merged)
check("所有 Shape 顺序均为 Cell→Section(→Text)", not bad,
      f"异常 {len(bad)} 个，例: {bad[0] if bad else ''}")

# 统计两类 shape
with_text = sum(1 for s in shapes if "<Text>" in s)
without = len(shapes) - with_text
print(f"  含文字 Shape {with_text} 个 / 无文字（连接线等）{without} 个")

# 追加硬校验：Text 之后不得再有 Section/Cell
late = []
for s in shapes:
    ti = s.find("<Text>")
    if ti >= 0:
        tail = s[ti:]
        if "<Section" in tail or re.search(r"<Cell\b", tail):
            late.append(s[:60])
check("Text 之后无 Section/Cell", not late, f"{len(late)} 个异常")

print()
print("=" * 70)
print("C6  命名空间前缀")
print("=" * 70)
pages_xml = zo.read("visio/pages/pages.xml").decode("utf-8")
check("pages.xml 声明 xmlns:r", 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"' in pages_xml)
check("Rel 使用 r:id 前缀", "<Rel r:id=" in pages_xml)
check("Rel 不用裸 ID=", "<Rel ID=" not in pages_xml)
check("document.xml 声明 xmlns:r", 'xmlns:r=' in doc)
check("PageContents 声明 xmlns:r", 'xmlns:r=' in pg)

print()
print("=" * 70)
print("C7  XML 合法性 + 第三方库解析")
print("=" * 70)
errs = []
for n in names:
    if n.endswith((".xml", ".rels")):
        try:
            minidom.parseString(zo.read(n))
        except Exception as e:
            errs.append((n, str(e)))
check("全部 XML 可解析", not errs, str(errs[:2]))

try:
    from vsdx import VisioFile
    v = VisioFile(OURS)
    check("第三方 vsdx 库可打开", True)
    check(f"页数 = {len(v.pages)}", len(v.pages) >= 1)
    shapes_ok = len(v.pages[0].child_shapes)
    check(f"页面 shape 数 = {shapes_ok}", shapes_ok > 0)
except Exception as e:
    check("第三方 vsdx 库可打开", False, str(e))

print()
print("=" * 70)
print("对照真实 Visio 文件的部件清单")
print("=" * 70)
real_parts = set(zr.namelist())
our_parts = set(names)
print(f"  真实文件有、我们没有: {sorted(real_parts - our_parts)}")
print(f"  我们有、真实文件无: {sorted(our_parts - real_parts)}")
print("  （masters/thumbnail/custom 是可选部件，缺失不影响打开）")

print()
print("=" * 70)
if FAILS:
    print(f"结果：{len(FAILS)} 条未通过")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("结果：全部通过")
sys.exit(0)
