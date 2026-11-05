#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按 **Visio 的几何规则**渲染 vsdx 预览图。

与 skill 自带的 SVG/PIL 渲染不同，这里严格按 Visio 的规则计算：
  局部坐标原点 = 形状 LocPin 点
  页面坐标 = Pin + (局部点 − LocPin)
所以预览图里的连线落点 = Visio 实际渲染的落点（已用 Visio 原生样本交叉验证）。

用法: python render_by_visio_rules.py <vsdx> <out.png>
"""
import math
import os
import re
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("需要 Pillow: python -m pip install pillow")
    sys.exit(1)

DPI = 110
PAGE_W, PAGE_H = 17.0, 11.0


def cells_of(s):
    out = {}
    for m in re.finditer(r'<Cell N=["\']([A-Za-z0-9]+)["\'] V=["\']([^"\']*)["\']', s):
        out[m.group(1)] = m.group(2)
    return out


def font(sz, bold=False):
    for p in (r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
              r"C:\Windows\Fonts\simhei.ttf",
              r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def local_to_page(lx, ly, c):
    px, py = float(c["PinX"]), float(c["PinY"])
    lcx, lcy = float(c["LocPinX"]), float(c["LocPinY"])
    ang = math.radians(float(c.get("Angle", 0)))
    ox, oy = lx - lcx, ly - lcy
    ca, sa = math.cos(ang), math.sin(ang)
    return (px + ox * ca - oy * sa, py + ox * sa + oy * ca)


def rect(dr, x0, y0, x1, y1, **kw):
    """画矩形（自动归一化 y0/y1 顺序）。"""
    if y1 < y0:
        y0, y1 = y1, y0
    dr.rectangle([x0, y0, x1, y1], **kw)


def render(vsdx_path, out_png, page_index=1):
    import zipfile
    z = zipfile.ZipFile(vsdx_path)
    pg_path = f"visio/pages/page{page_index}.xml"
    pg = z.read(pg_path).decode("utf-8")
    shapes = re.findall(r"<Shape\b[^>]*>.*?</Shape>", pg, re.S)

    W, H = int(PAGE_W * DPI), int(PAGE_H * DPI)

    def X(v):
        return v * DPI

    def Y(v):
        return (PAGE_H - v) * DPI          # SVG/Canvas: y 向下

    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)

    # ── 标题栏 / 图例 / 页脚（按页面尺寸定位，与 Visio 一致）──
    all_shapes = re.findall(r"<Shape\b[^>]*>.*?</Shape>", pg, re.S)

    def by_name(key):
        for sh in all_shapes:
            nm2 = re.search(r'NameU=["\']([^"\']*)["\']', sh)
            if nm2 and key in nm2.group(1):
                return sh
        return None

    s = by_name("TitleBar")
    if s:
        c = cells_of(s)
        px, py = float(c["PinX"]), float(c["PinY"])
        w, h = float(c["Width"]), float(c["Height"])
        rect(dr, X(px - w / 2), Y(py + h / 2), X(px + w / 2), Y(py - h / 2),
             fill=c.get("FillForegnd", "#1E3A8A"))
        tm = re.search(r"<Text>(.*?)</Text>", s, re.S)
        if tm:
            txt = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
            dr.text((X(px), Y(py)), txt, font=font(20, True), fill="#FFFFFF", anchor="mm")

    # 图例 chip（横向排布在标题下方）
    chips = [sh for sh in all_shapes
             if re.search(r'NameU=["\']([^"\']*)["\']', sh)
             and "LegendChip" in re.search(r'NameU=["\']([^"\']*)["\']', sh).group(1)]
    if chips:
        for s in chips:
            c = cells_of(s)
            px, py = float(c["PinX"]), float(c["PinY"])
            w, h = float(c["Width"]), float(c["Height"])
            rect(dr, X(px - w / 2), Y(py + h / 2), X(px + w / 2), Y(py - h / 2),
                 fill=c.get("FillForegnd", "#2563EB"))
            tm = re.search(r"<Text>(.*?)</Text>", s, re.S)
            if tm:
                txt = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
                dr.text((X(px), Y(py)), txt, font=font(11, True), fill="#FFFFFF", anchor="mm")

    # 泳道背景
    lane_fill = "#F8FAFC"
    lane_border = "#E2E8F0"
    for s in shapes:
        c = cells_of(s)
        if "Width" not in c:
            continue
        px, py = float(c["PinX"]), float(c["PinY"])
        w, h = float(c["Width"]), float(c["Height"])
        if w < 1:                     # 跳过连接线
            continue
        rect(dr, X(px - w / 2), Y(py + h / 2), X(px + w / 2), Y(py - h / 2),
             fill=lane_fill, outline=lane_border, width=1)

    # 卡片
    for s in shapes:
        nm = re.search(r'NameU=["\']([^"\']*)["\']', s)
        nm = nm.group(1) if nm else ""
        c = cells_of(s)
        if "TaskCard" not in nm or "Width" not in c:
            continue
        px, py = float(c["PinX"]), float(c["PinY"])
        w, h = float(c["Width"]), float(c["Height"])
        fill = c.get("FillForegnd", "#FFFFFF")
        border = c.get("LineColor", "#94A3B8")
        rect(dr, X(px - w / 2), Y(py + h / 2), X(px + w / 2), Y(py - h / 2),
             fill=fill, outline=border, width=2)
        # 文字
        tm = re.search(r"<Text>(.*?)</Text>", s, re.S)
        if tm:
            body = tm.group(1)
            segs = []
            for m in re.finditer(r'<cp IX=["\']\d+["\']/>|<pp IX=["\']\d+["\']/>|([^<]+)', body):
                if m.group(0).startswith("<pp"):
                    segs.append(("\n", None))
                elif m.group(0).startswith("<cp"):
                    pass
                elif m.group(1):
                    segs.append((m.group(1), None))
            # 合并成行
            lines, cur = [], ""
            for t, _ in segs:
                if t == "\n":
                    lines.append(cur)
                    cur = ""
                else:
                    cur += t
            if cur:
                lines.append(cur)
            f = font(11)
            ty = Y(py + h / 2) + 7
            for li, ln in enumerate(lines):
                col = "#1F2937"
                if li == 0:
                    col, fnt = "#1F2937", font(11, True)
                elif li == 1:
                    col, fnt = "#334155", font(10)
                else:
                    col, fnt = "#64748B", font(10)
                dr.text((X(px), ty), ln, font=fnt, fill=col, anchor="ma")
                ty += 15

    # 连接线（严格按 Visio 几何规则）
    for s in shapes:
        nm = re.search(r'NameU=["\']([^"\']*)["\']', s)
        nm = nm.group(1) if nm else ""
        c = cells_of(s)
        if "Connector" not in nm and not ("BeginX" in c and "EndX" in c):
            continue
        if "Width" not in c:
            continue
        geo = re.search(r'<Section N=["\']Geometry["\'].*?</Section>', s, re.S)
        if not geo:
            continue
        rows = re.findall(
            r'<Row T=["\'](\w+)["\'][^>]*><Cell N=["\']X["\'] V=["\']([^"\']*)["\']/>'
            r'<Cell N=["\']Y["\'] V=["\']([^"\']*)["\']/>', geo.group(0))
        if not rows:
            continue
        pts = [local_to_page(float(x), float(y), c) for _t, x, y in rows]
        color = c.get("LineColor", "#64748B")
        dr.line([(X(px), Y(py)) for px, py in pts], fill=color, width=2)
        # 箭头
        if c.get("EndArrow", "0") not in ("0", "") and len(pts) >= 2:
            # 方向 = 路径末端切线（与 Visio 一致）；2 点路径时即整条线方向
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            a = math.atan2(Y(y2) - Y(y1), X(x2) - X(x1))
            L = 11
            dr.polygon([
                (X(x2), Y(y2)),
                (X(x2) - L * math.cos(a - math.pi / 6), Y(y2) - L * math.sin(a - math.pi / 6)),
                (X(x2) - L * math.cos(a + math.pi / 6), Y(y2) - L * math.sin(a + math.pi / 6)),
            ], fill=color)

    im.save(out_png)
    return out_png


if __name__ == "__main__":
    src = sys.argv[1]
    dst = sys.argv[2]
    pg = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    import zipfile
    z = zipfile.ZipFile(src)
    pages = sorted([n for n in z.namelist()
                    if re.match(r"visio/pages/page\d+\.xml$", n)],
                   key=lambda n: int(re.search(r"page(\d+)", n).group(1)))
    if len(pages) > 1:
        # 多页：逐页渲染后纵向拼接
        from PIL import Image
        imgs = []
        for i, _p in enumerate(pages, 1):
            tmp = dst.replace(".png", f"_p{i}.png")
            render(src, tmp, i)
            imgs.append(Image.open(tmp))
        W = max(im.width for im in imgs)
        H = sum(im.height for im in imgs)
        out = Image.new("RGB", (W, H), "white")
        y = 0
        for im in imgs:
            out.paste(im, (0, y))
            y += im.height
        out.save(dst)
        for i in range(1, len(pages) + 1):
            p = dst.replace(".png", f"_p{i}.png")
            if os.path.exists(p):
                os.remove(p)
        print("按 Visio 规则渲染(多页):", dst, os.path.getsize(dst), "bytes")
    else:
        r = render(src, dst, pg)
        print("按 Visio 规则渲染:", r, os.path.getsize(r), "bytes")
