#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按 Visio 的几何规则模拟渲染连接线，验证线实际画在哪、是否连到卡片上。

Visio 渲染规则（从原生样本反推）：
  形状的局部坐标原点 = 形状的 LocPin 点。
  该点在页面上的绝对位置 = Pin - LocPin（沿形状局部 X/Y 轴）。
  Geometry 的局部点 (lx, ly) → 页面绝对坐标 = Pin + (lx - LocPinX, ly - LocPinY)
  （Angle=0 时局部轴与页面轴平行）

据此算出每条线的实际端点，检查是否落在卡片包围盒上。
"""
import math
import os
import re
import sys
import zipfile

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}   {detail}")
        FAILS.append(name)


def shape_cells(shape_xml):
    """提取 Cell 的 N/V。兼容双引号（我们生成）与单引号（Visio 原生）两种属性风格。"""
    out = {}
    for m in re.finditer(r'<Cell N=["\']([A-Za-z0-9]+)["\'] V=["\']([^"\']*)["\']', shape_xml):
        out[m.group(1)] = m.group(2)
    return out


def local_to_page(lx, ly, pin_x, pin_y, loc_x, loc_y, angle_deg):
    """局部坐标 → 页面绝对坐标（Angle=0 为主，带角度时也支持）"""
    ox = lx - loc_x
    oy = ly - loc_y
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    return (pin_x + ox * ca - oy * sa, pin_y + ox * sa + oy * ca)


def analyse(path):
    z = zipfile.ZipFile(path)
    pg = z.read("visio/pages/page1.xml").decode("utf-8")
    shapes = re.findall(r"<Shape\b[^>]*>.*?</Shape>", pg, re.S)

    cards = []
    conns = []
    for s in shapes:
        nm = re.search(r'NameU=["\']([^"\']*)["\']', s)
        nm = nm.group(1) if nm else ""
        c = shape_cells(s)
        if "TaskCard" in nm:
            cards.append(s)
        elif "Connector" in nm or ("BeginX" in c and "EndX" in c and "EndArrow" in c):
            # Visio 原生样本的线名是 "Line.N"，靠 Begin/End + EndArrow 特征识别
            conns.append(s)

    # 卡片包围盒
    boxes = []
    for s in cards:
        c = shape_cells(s)
        px, py = float(c["PinX"]), float(c["PinY"])
        w, h = float(c["Width"]), float(c["Height"])
        boxes.append((px - w / 2, px + w / 2, py - h / 2, py + h / 2))

    print("=" * 70)
    print(f"{os.path.basename(path)}")
    print("=" * 70)
    print(f"  卡片 {len(cards)} 个 / 连接线 {len(conns)} 条")

    off_page = 0
    not_on_card = 0
    junction_bad = 0
    samples = []
    seg_data = []
    for s in conns:
        c = shape_cells(s)
        px, py = float(c["PinX"]), float(c["PinY"])
        lx, ly = float(c["LocPinX"]), float(c["LocPinY"])
        ang = float(c.get("Angle", 0))
        geo = re.search(r'<Section N=["\']Geometry["\'].*?</Section>', s, re.S)
        rows = re.findall(
            r'<Row T=["\'](\w+)["\'][^>]*><Cell N=["\']X["\'] V=["\']([^"\']*)["\']/>'
            r'<Cell N=["\']Y["\'] V=["\']([^"\']*)["\']/>', geo.group(0))
        if not rows:
            continue
        pts = [local_to_page(float(x), float(y), px, py, lx, ly, ang)
               for _t, x, y in rows]
        seg_data.append((pts[0], pts[-1]))

    def near(a, b, tol=0.002):
        return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol

    # 拐点：既是某段终点又是某段起点（浮点容差）
    junctions = []
    for (p, _q) in seg_data:
        for (_p2, q2) in seg_data:
            if near(p, q2):
                junctions.append(p)
                break

    # 列区间的 x 边界 → 判断某点是否在「列间空隙」
    xs = sorted({round(b[0], 4) for b in boxes} | {round(b[1], 4) for b in boxes})
    gaps = []
    for i in range(len(xs) - 1):
        if xs[i + 1] - xs[i] > 0.05:
            gaps.append((xs[i], xs[i + 1]))

    def in_gap(qx):
        return any(g0 - 0.02 <= qx <= g1 + 0.02 for (g0, g1) in gaps)

    for (p_start, p_end) in seg_data:
        for (qx, qy) in (p_start, p_end):
            if not (-1 <= qx <= 18 and -1 <= qy <= 12):
                off_page += 1
                continue
            is_junction = any(near((qx, qy), j) for j in junctions)
            on_card = any(x0 - 0.05 <= qx <= x1 + 0.05 and y0 - 0.05 <= qy <= y1 + 0.05
                          for (x0, x1, y0, y1) in boxes)
            if is_junction:
                # 拐点：必须在列间空隙里，且不能压卡片
                if on_card:
                    junction_bad += 1
                elif not in_gap(qx):
                    junction_bad += 1
            elif not on_card:
                not_on_card += 1
        if len(samples) < 4:
            samples.append((p_start, p_end))

    for (a, b) in samples:
        print(f"    渲染端点: ({a[0]:.3f},{a[1]:.3f}) → ({b[0]:.3f},{b[1]:.3f})")
    print(f"    折线拐点 {len(junctions)} 个 / 列间空隙 {len(gaps)} 处")

    # 自洽性：模拟渲染出的端点必须等于文件声明的 Begin/End
    # （这条同时验证了 Geometry 与 Pin/LocPin 是否自洽）
    self_ok = 0
    self_tot = 0
    for s in conns:
        c = shape_cells(s)
        if "BeginX" not in c:
            continue
        px, py = float(c["PinX"]), float(c["PinY"])
        lx, ly = float(c["LocPinX"]), float(c["LocPinY"])
        ang = float(c.get("Angle", 0))
        geo = re.search(r'<Section N=["\']Geometry["\'].*?</Section>', s, re.S)
        rows = re.findall(
            r'<Row T=["\'](\w+)["\'][^>]*><Cell N=["\']X["\'] V=["\']([^"\']*)["\']/>'
            r'<Cell N=["\']Y["\'] V=["\']([^"\']*)["\']/>', geo.group(0))
        if not rows:
            continue
        pts = [local_to_page(float(x), float(y), px, py, lx, ly, ang) for _t, x, y in rows]
        b1 = (float(c["BeginX"]), float(c["BeginY"]))
        b2 = (float(c["EndX"]), float(c["EndY"]))
        self_tot += 1
        if (abs(pts[0][0] - b1[0]) < 0.02 and abs(pts[0][1] - b1[1]) < 0.02 and
                abs(pts[-1][0] - b2[0]) < 0.02 and abs(pts[-1][1] - b2[1]) < 0.02):
            self_ok += 1

    check("所有连接线端点都在页面范围内", off_page == 0, f"{off_page} 个端点跑出页面")
    check("所有连接点都落在卡片上", not_on_card == 0, f"{not_on_card} 个连接点未命中卡片")
    check("折线拐点都在列间空隙且不压卡片", junction_bad == 0, f"{junction_bad} 个拐点异常")
    check(f"Geometry 与 Begin/End 自洽（{self_ok}/{self_tot}）", self_ok == self_tot and self_tot > 0,
          f"{self_tot - self_ok} 条不自洽")

    # 箭头方向：Geometry 路径末端切线必须与 Begin→End 同向
    # （Visio 按路径末端方向画箭头，切线歪了箭头就歪）
    arrow_bad = []
    for s in conns:
        c = shape_cells(s)
        if c.get("EndArrow", "0") in ("0", ""):
            continue
        geo = re.search(r'<Section N=["\']Geometry["\'].*?</Section>', s, re.S)
        rows = re.findall(
            r'<Row T="(\w+)"[^>]*><Cell N="X" V="([^"]*)"/><Cell N="Y" V="([^"]*)"/>', geo.group(0))
        if len(rows) < 2:
            continue
        p2 = (float(rows[-2][1]), float(rows[-2][2]))
        p1 = (float(rows[-1][1]), float(rows[-1][2]))
        tan = (p1[0] - p2[0], p1[1] - p2[1])
        beg = (float(c["BeginX"]), float(c["BeginY"]))
        end = (float(c["EndX"]), float(c["EndY"]))
        dirv = (end[0] - beg[0], end[1] - beg[1])
        # 切线与连线方向是否同向（允许反向前进，即同一直线）
        cross = tan[0] * dirv[1] - tan[1] * dirv[0]
        dot = tan[0] * dirv[0] + tan[1] * dirv[1]
        if abs(cross) > 1e-6 or dot < 0:
            arrow_bad.append((tan, dirv))

    check("箭头方向与连线方向一致（末端切线不歪）", not arrow_bad,
          f"{len(arrow_bad)} 条箭头方向错，例: {arrow_bad[0] if arrow_bad else ''}")
    return len(conns)


def main():
    paths = sys.argv[1:]
    if not paths:
        paths = [r"C:\银行经营\PRCP\docs\deliverables_model\single\模型反算主链路.vsdx"]
    for p in paths:
        analyse(p)
        print()
    print("=" * 70)
    if FAILS:
        print(f"结果：{len(FAILS)} 条未通过")
        for f in FAILS:
            print("  -", f)
        return 1
    print("结果：全部通过 —— 线实际渲染在卡片上")
    return 0


if __name__ == "__main__":
    sys.exit(main())
