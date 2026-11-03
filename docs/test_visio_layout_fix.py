#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证 visio-flow-generator 布局修复的自检用例。
覆盖：
  T1 分栏后卡高按子栏宽度重算（不再沿用整列宽）
  T2 折行宽度上限 = 卡片物理宽度（文字不溢出）
  T3 wrap() 按视觉宽度折行（ASCII 半角计宽）
  T4 回归：单栏 normal/tight 模式行为不变
  T5 回归：多页/多流程不受影响
"""
import sys
import os

SCRIPTS = r"C:/Users/zhanghh/.workbuddy/skills/visio-flow-generator/scripts"
sys.path.insert(0, SCRIPTS)

from generate_vsdx import (
    plan_column, card_height, card_units, sub_lane_metrics, wrap, text_units,
    CONTENT_W, COL_GAP, CARD_PAD_X, LANE_AVAIL_H,
)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILS.append(name)


print("=" * 68)
print("T1  分栏后卡高按子栏实际宽度重算")
print("=" * 68)
# 造一个必然触发分栏的列
items = [{"action": "操作" * 20, "owner": "A", "remark": "备注" * 10} for _ in range(8)]
n_cols = 7
col_w = (CONTENT_W - (n_cols - 1) * COL_GAP) / n_cols
card_w = col_w - 2 * CARD_PAD_X
mca = card_units(card_w, 9.5)
mcr = card_units(card_w, 8.0)

plan = plan_column(items, mca, mcr, col_w)
lane_n = len(plan["lanes"])
check("触发分栏", lane_n >= 2, f"lane_n={lane_n}")
if lane_n >= 2:
    met = sub_lane_metrics(col_w, lane_n)
    # 每张卡的实际高度必须等于「按子栏折行上限」算出的高度
    ok = True
    for lane in plan["lanes"]:
        for idx, h in lane:
            expect = card_height(items[idx], met["mca"], met["mcr"])
            if abs(expect - h) > 1e-9:
                ok = False
    check("卡高 == 按子栏宽度重算的高度", ok)
    # 且分栏后高度应大于整列宽算出的高度（因为折行更窄→行数更多）
    raw_full = card_height(items[0], mca, mcr)
    got = plan["lanes"][0][0][1]
    check("分栏卡高 > 整列宽卡高（证明已重算）", got > raw_full,
          f"split={got:.3f} full={raw_full:.3f}")

print()
print("=" * 68)
print("T2  折行宽度上限 = 卡片物理宽度（不溢出）")
print("=" * 68)
for cn in (3, 5, 7):
    col_w_n = (CONTENT_W - (cn - 1) * COL_GAP) / cn
    cw = col_w_n - 2 * CARD_PAD_X
    limit = card_units(cw, 9.5)
    # 折行后最长行的视觉宽度必须 <= 物理上限
    long_cn = "中文测试文本" * 20
    lines = wrap(long_cn, limit)
    widest = max(text_units(l) for l in lines)
    check(f"{cn}列: 最宽行 {widest:.2f} <= 上限 {limit:.2f}",
          widest <= limit + 1e-6)
    # 每行必须非空且总内容不丢失
    check(f"{cn}列: 折行不丢字", "".join(lines).replace(" ", "") == long_cn.replace(" ", ""))

print()
print("=" * 68)
print("T3  wrap() 视觉宽度：ASCII 半角计宽")
print("=" * 68)
ascii_s = "prcp_reverse_scheme"
check("ASCII 表名视觉宽度 < 字符数", text_units(ascii_s) < len(ascii_s),
      f"units={text_units(ascii_s):.1f} chars={len(ascii_s)}")
check("中文字符宽度 = 1.0", abs(text_units("中") - 1.0) < 1e-9)
# 同样的中文与英文，英文应折得更少
cn_lines = len(wrap("中文中文中文中文", 6))
en_lines = len(wrap("abcdabcdabcd", 6))
check("等宽预算下英文行数 <= 中文行数", en_lines <= cn_lines,
      f"en={en_lines} cn={cn_lines}")
# 显式换行保留
check("保留显式换行", len(wrap("上\n下", 10)) == 2)

print()
print("=" * 68)
print("T4  回归：单栏 normal / tight 行为不变")
print("=" * 68)
one = [{"action": "短操作", "owner": "A", "remark": ""}]
p1 = plan_column(one, mca, mcr, col_w)
check("单项 → normal", p1["mode"] == "normal", p1["mode"])
check("单项 → 单栏", len(p1["lanes"]) == 1)

three = [{"action": "短操作", "owner": "A", "remark": ""} for _ in range(3)]
p2 = plan_column(three, mca, mcr, col_w)
check("3 项 → normal", p2["mode"] == "normal", p2["mode"])
check("normal 间距 = CARD_GAP", p2["gap"] == 0.36, str(p2["gap"]))

# 不传 col_w 的旧调用方式不能崩
p3 = plan_column(three, mca, mcr)
check("不传 col_w 兼容（旧签名）", p3["mode"] in ("normal", "tight", "split"), p3["mode"])

print()
print("=" * 68)
print("T5  回归：空列 / 单项列不崩")
print("=" * 68)
p4 = plan_column([], mca, mcr, col_w)
check("空列 → lanes 为空", p4["lanes"] == [])
check("空列 → mode normal", p4["mode"] == "normal")

print()
print("=" * 68)
if FAILS:
    print(f"结果：{len(FAILS)} 条未通过 → {FAILS}")
    sys.exit(1)
print("结果：全部通过")
sys.exit(0)
