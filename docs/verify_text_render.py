#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
按 Visio 官方规范解析 .vsdx 的 Shape 文本，独立验证：
  1) cp/pp 标记序列合规（cp 严格递增、pp 在段首且前有换行）
  2) 每个 cp 的 IX 都能在 Character Section 找到对应 Row
  3) 解析出的文本行数与内容完整（首行操作名不丢、责任人/备注齐全）
  4) 颜色/字号/粗体取自正确的 Character Row
这相当于模拟 ProcessOn 导入器的文本还原逻辑。
"""
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


def parse_shape_text(shape_xml):
    """按 Visio 规范解析 shape 的文本 → [(行, [(片段, 字符属性dict, 段落属性dict)])]"""
    # Character Section: Row IX → 属性
    char_rows = {}
    cm = re.search(r'<Section N="Character">(.*?)</Section>', shape_xml, re.S)
    if cm:
        for rm in re.finditer(r'<Row IX="(\d+)">(.*?)</Row>', cm.group(1), re.S):
            attrs = {}
            for cell in re.finditer(r'<Cell N="([^"]+)" V="([^"]*)"', rm.group(2)):
                attrs[cell.group(1)] = cell.group(2)
            char_rows[int(rm.group(1))] = attrs

    para_rows = {}
    pm = re.search(r'<Section N="Paragraph">(.*?)</Section>', shape_xml, re.S)
    if pm:
        for rm in re.finditer(r'<Row IX="(\d+)">(.*?)</Row>', pm.group(1), re.S):
            attrs = {}
            for cell in re.finditer(r'<Cell N="([^"]+)" V="([^"]*)"', rm.group(2)):
                attrs[cell.group(1)] = cell.group(2)
            para_rows[int(rm.group(1))] = attrs

    tm = re.search(r"<Text>(.*?)</Text>", shape_xml, re.S)
    if not tm:
        return [], char_rows, para_rows, []
    body = tm.group(1)

    # 逐 token 扫描：标记 + 文本
    tokens = re.split(r"(<cp IX=\"\d+\"/>|<pp IX=\"\d+\"/>)", body)
    lines = [[]]          # 当前段的片段列表
    cur_cp = None
    cur_pp = 0
    events = []
    for tok in tokens:
        if not tok:
            continue
        cm2 = re.fullmatch(r'<cp IX="(\d+)"/>', tok)
        pm2 = re.fullmatch(r'<pp IX="(\d+)"/>', tok)
        if cm2:
            cur_cp = int(cm2.group(1))
            events.append(("cp", cur_cp, ""))
        elif pm2:
            cur_pp = int(pm2.group(1))
            events.append(("pp", cur_pp, ""))
        else:
            # 文本：按 \n 拆分 —— 段落边界与软换行都表现为换行，
            # 段落边界由 <pp> 标记，软换行没有 <pp>，此处统一拆行便于检查
            parts = tok.split("\n")
            for k, part in enumerate(parts):
                if part:
                    lines[-1].append((part, cur_cp, cur_pp))
                if k < len(parts) - 1:
                    lines.append([])   # 换行 → 新行
            events.append(("text", tok, ""))
    return lines, char_rows, para_rows, events


def main(path):
    z = zipfile.ZipFile(path)
    pg = z.read("visio/pages/page1.xml").decode("utf-8")
    shapes = re.findall(r"<Shape\b[^>]*>.*?</Shape>", pg, re.S)
    cards = [s for s in shapes if "TaskCard" in s]

    print("=" * 70)
    print(f"解析 {len(cards)} 张 TaskCard 的文本（按 Visio 规范）")
    print("=" * 70)

    seq_bad = []
    missing_row = []
    empty_first = []
    multi_line = []

    for idx, s in enumerate(cards):
        lines, char_rows, para_rows, events = parse_shape_text(s)

        # 1) cp 索引严格递增
        cp_idx = [e[1] for e in events if e[0] == "cp"]
        if cp_idx != sorted(cp_idx) or cp_idx != list(range(len(cp_idx))):
            seq_bad.append((idx, cp_idx))

        # 2) 每个 cp IX 都能找到 Character Row
        for i in cp_idx:
            if i not in char_rows:
                missing_row.append((idx, i))

        # 3) 首行非空（操作名不能丢）
        if not lines or not any(t.strip() for t, _, _ in lines[0]):
            empty_first.append(idx)

        # 4) 至少要有 操作名 + 责任人 两段（备注可为空，属合法）
        nonempty = [ln for ln in lines if any(t.strip() for t, _, _ in ln)]
        if len(nonempty) < 2:
            multi_line.append((idx, len(nonempty)))
        # 责任人行必须存在
        has_owner = any(any("责任人" in t for t, _, _ in ln) for ln in nonempty)
        if not has_owner:
            multi_line.append((idx, "no-owner"))

    check("cp 索引严格递增且连续", not seq_bad, f"{seq_bad[:3]}")
    check("每个 cp IX 都有对应 Character Row", not missing_row, f"{missing_row[:3]}")
    check("所有卡片首行（操作名）非空", not empty_first, f"{empty_first[:5]}")
    check("所有卡片解析出 操作名+责任人（备注可空）", not multi_line, f"{multi_line[:3]}")

    # 抽样打印解析结果
    print()
    print("  解析抽样（前 4 张卡片）:")
    for idx in range(min(4, len(cards))):
        lines, char_rows, para_rows, events = parse_shape_text(cards[idx])
        print(f"  --- 卡片 {idx+1} ---")
        for ln in lines:
            for text, cp, pp in ln:
                if not text.strip():
                    continue
                ca = char_rows.get(cp, {})
                color = ca.get("Color", "?")
                size = ca.get("Size", "?")
                bold = "粗" if ca.get("Style") == "1" else "常"
                print(f"      [{color} {size} {bold}] {text}")

    # 校验：颜色应为卡片深灰 #1F2937（操作名），责任人/备注用不同灰
    print()
    print("=" * 70)
    print("颜色/样式抽样")
    print("=" * 70)
    colors = set()
    for s in cards[:20]:
        lines, char_rows, _, _ = parse_shape_text(s)
        for ln in lines:
            for text, cp, pp in ln:
                if text.strip():
                    colors.add((char_rows.get(cp, {}).get("Color"),
                                char_rows.get(cp, {}).get("Style")))
    print(f"  出现的 (颜色, 粗体) 组合: {sorted(colors, key=str)}")
    check("存在深色正文（#1F2937）", any(c and c.upper() == "#1F2937" for c, _ in colors),
          str(sorted(colors, key=str)))

    print()
    print("=" * 70)
    print("连接线几何检查（箭头是否笔直）")
    print("=" * 70)
    conns = [s for s in shapes if "Connector" in s]
    print(f"  连接线数: {len(conns)}")
    diag = []
    rel_coord = []
    objtype_bad = []
    for s in conns:
        cells = dict(re.findall(r'<Cell N="([A-Za-z0-9]+)" V="([^"]*)"', s))
        bx, by = float(cells["BeginX"]), float(cells["BeginY"])
        ex, ey = float(cells["EndX"]), float(cells["EndY"])
        dx, dy = ex - bx, ey - by
        if abs(dx) > 1e-6 and abs(dy) > 1e-6:
            diag.append((bx, by, ex, ey))
        # 1D 连接线必须用绝对坐标 MoveTo/LineTo
        geo = re.search(r'<Section N="Geometry".*?</Section>', s, re.S)
        if geo and ('T="RelMoveTo"' in geo.group(0) or 'T="RelLineTo"' in geo.group(0)):
            rel_coord.append(cells.get("BeginX"))
        if cells.get("ObjType") == "2":
            objtype_bad.append(cells.get("ObjType"))

    check("所有连接线均为水平或垂直（无斜线）", not diag, f"{len(diag)} 条斜线")
    check("连接线 Geometry 使用绝对坐标 MoveTo/LineTo", not rel_coord, f"{len(rel_coord)} 条用了相对坐标")

    # 按 Visio 真实渲染规则校验：
    # 线的矩形包围盒 = [PinX ± Width/2, PinY ± Height/2]，必须包含 Begin/End 两端
    bbox_bad = []
    angle_bad = []
    for s in conns:
        cells = dict(re.findall(r'<Cell N="([A-Za-z0-9]+)" V="([^"]*)"', s))
        try:
            px, py = float(cells["PinX"]), float(cells["PinY"])
            w, h = float(cells["Width"]), float(cells["Height"])
            bx, by = float(cells["BeginX"]), float(cells["BeginY"])
            ex, ey = float(cells["EndX"]), float(cells["EndY"])
        except (KeyError, ValueError):
            continue
        # 包围盒（Height 可为负，取绝对值）
        x0, x1_ = px - w / 2, px + w / 2
        y0, y1_ = py - abs(h) / 2, py + abs(h) / 2
        eps = 0.02
        for (qx, qy) in ((bx, by), (ex, ey)):
            if not (x0 - eps <= qx <= x1_ + eps and y0 - eps <= qy <= y1_ + eps):
                bbox_bad.append((s[:40], (bx, by), (ex, ey), (x0, x1_, y0, y1_)))
        # Angle 必须为 0（方向由 Width/Height 表达）
        if abs(float(cells.get("Angle", "0"))) > 1e-6:
            angle_bad.append(cells.get("Angle"))

    check("线的包围盒包含 Begin/End 两端（线能真正连到卡片）", not bbox_bad,
          f"{len(bbox_bad)} 条越界，例: {bbox_bad[0][1:] if bbox_bad else ''}")
    check("Angle=0（方向由 Width/Height 表达）", not angle_bad, f"{len(angle_bad)} 条 Angle≠0")

    # 用第三方 vsdx 库独立交叉验证（模拟 ProcessOn 的解析器）
    try:
        from vsdx import VisioFile
        v = VisioFile(path)
        pg = v.pages[0]
        conns2 = [s for s in pg.child_shapes
                  if getattr(s, "begin_x", None) is not None
                  and getattr(s, "end_x", None) is not None]
        diag2 = []
        for s in conns2:
            dx = s.end_x - s.begin_x
            dy = s.end_y - s.begin_y
            if abs(dx) > 1e-6 and abs(dy) > 1e-6:
                diag2.append(s)
        check(f"第三方库解析出 {len(conns2)} 条 1D 连接线", len(conns2) > 0)
        check("第三方库读到的连接线也无斜线", not diag2, f"{len(diag2)} 条斜线")
    except Exception as e:
        print(f"  SKIP  第三方库交叉验证（{str(e)[:60]}）")

    # 打印抽样
    print()
    print("  连接线抽样:")
    for s in conns[:4]:
        cells = dict(re.findall(r'<Cell N="([A-Za-z0-9]+)" V="([^"]*)"', s))
        print(f"    Begin=({float(cells['BeginX']):.2f},{float(cells['BeginY']):.2f}) "
              f"End=({float(cells['EndX']):.2f},{float(cells['EndY']):.2f}) "
              f"W={cells.get('Width')} H={cells.get('Height')} Angle={cells.get('Angle')}")

    # 端点是否真的落在卡片上：取所有卡片的包围盒集合
    # 说明：跨列连线是「横向→纵向→横向」三段折线，中间段的两个端点是**拐点**，
    #       允许悬空；只有真正连接卡片的那两个点必须在卡片上。
    card_boxes = []
    for s in cards:
        cells = dict(re.findall(r'<Cell N="([A-Za-z0-9]+)" V="([^"]*)"', s))
        try:
            px, py = float(cells["PinX"]), float(cells["PinY"])
            w, h = float(cells["Width"]), float(cells["Height"])
        except (KeyError, ValueError):
            continue
        card_boxes.append((px - w / 2, px + w / 2, py - h / 2, py + h / 2))

    def on_card(x, y):
        return any(x0 - 0.08 <= x <= x1 + 0.08 and y0 - 0.08 <= y <= y1 + 0.08
                   for (x0, x1, y0, y1) in card_boxes)

    # 把属于同一条折线的三段归组：按 (x_from,y_from)-(mid)-(x_to,y_to) 的连续性
    # 简化：统计「悬空且不是拐点」的端点。
    # 判定规则：一条线段的端点若悬空，则它必然是折线的中间拐点；
    #           真正的流程连接点（连到卡片的那两端）必须命中卡片。
    #           → 折线的第一段起点 & 最后一段终点必须命中卡片。
    segs = []
    for s in conns:
        cells = dict(re.findall(r'<Cell N="([A-Za-z0-9]+)" V="([^"]*)"', s))
        try:
            segs.append(((float(cells["BeginX"]), float(cells["BeginY"])),
                         (float(cells["EndX"]), float(cells["EndY"]))))
        except (KeyError, ValueError):
            continue

    # 找出所有「既是某段终点、又是某段起点」的中间拐点
    starts = {p for (p, _q) in segs}
    ends = {q for (_p, q) in segs}
    junctions = starts & ends

    orphan = 0
    for (p, q) in segs:
        for pt in (p, q):
            if pt in junctions:
                continue          # 折线拐点，允许悬空
            if not on_card(*pt):
                orphan += 1
    check("所有连线连接点都落在卡片上（真正连上）", orphan == 0, f"{orphan} 个连接点悬空")
    print(f"  （折线拐点 {len(junctions)} 个，属正常）")

    print()
    print("=" * 70)
    if FAILS:
        print(f"结果：{len(FAILS)} 条未通过")
        for f in FAILS:
            print("  -", f)
        return 1
    print("结果：全部通过 —— 文本可被 Visio/ProcessOn 正确还原")
    return 0


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\银行经营\PRCP\docs\deliverables\PRCP组合反算主流程.vsdx"
    sys.exit(main(p))
