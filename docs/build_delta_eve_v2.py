# -*- coding: utf-8 -*-
"""
ΔEVE 计量模版 v2 —— 无资本口径版（多口径活公式）

相对 v1 的改造：
1. 指标口径全部改为「不使用一级资本」：
   ΔEVE/EVE基准%、|ΔEVE|/|EVE基准|%、ΔEVE/总资产%、ΔEVE/存款总额%、
   ΔEVE/生息资产%、ΔNII/NII基准%
2. 冲击情景由 4 个补到 7 个（基准 + 巴塞尔 SRP31.90-93 六情景），
   补入 short_rate_up / short_rate_down（v1 缺失）
3. 新增存款利率传导系数 β（负债端贴现曲线按 β 向基准传导）
4. 全部计算改为活公式（v1 主表与汇总页均为硬编码值）：
   ②现金流底稿 → ③曲线与折现因子 → ④账户PV矩阵 → ⑤多口径汇总 → ⑥ΔNII与久期缺口
5. 保留 v1 视觉风格（CITIC 红 #C7000B / 微软雅黑）

数据源：prcp_basic_20251231_v5.xlsx 基础数据页
  账户册 R4-R43（末级 24 个）｜剩余期限 64 桶 BX~EI(76~139)
  当前余额 EJ(140)｜加权平均利率 EL(142)｜月利息 EM(143)｜现值 K(11)
  国债收益率曲线 R48-R111（64 段）
"""
import openpyxl
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as GL

SRC = r"C:/银行经营/PRCP/docs/v2/prcp_basic_20251231_v5.xlsx"
OUT = r"C:/银行经营/PRCP/docs/v2/DeltaEVE_计量模版_v2_无资本口径.xlsx"

RED = "C7000B"
F_TITLE = Font(name="微软雅黑", size=15, bold=True, color="FFFFFF")
F_HDR = Font(name="微软雅黑", size=9, bold=True, color="FFFFFF")
F_SUB = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
F_BODY = Font(name="微软雅黑", size=9)
F_SMALL = Font(name="微软雅黑", size=9, color="555555")
F_NOTE = Font(name="微软雅黑", size=8, color="666666")
F_BOLD = Font(name="微软雅黑", size=10, bold=True)
FILL_RED = PatternFill("solid", fgColor=RED)
FILL_LIGHT = PatternFill("solid", fgColor="FFF3E0")
FILL_ASSET = PatternFill("solid", fgColor="E8F5E9")
FILL_LIAB = PatternFill("solid", fgColor="FFEBEE")
FILL_EQUITY = PatternFill("solid", fgColor="FFF9C4")
FILL_GREY = PatternFill("solid", fgColor="F2F2F2")
FILL_INPUT = PatternFill("solid", fgColor="FFF9C4")
FILL_FORMULA = PatternFill("solid", fgColor="E3F2FD")
_thin = Side(style="thin", color="BDBDBD")
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
AL_L = Alignment(horizontal="left", vertical="center")
AL_C = Alignment(horizontal="center", vertical="center")
AL_R = Alignment(horizontal="right", vertical="center")
AL_CW = Alignment(horizontal="center", vertical="center", wrap_text=True)
AL_LW = Alignment(horizontal="left", vertical="center", wrap_text=True)
NUM = "#,##0.00"
NUM4 = "0.0000"
PCT = "0.00%"

# ===================== 1. 读取源数据 =====================
src = openpyxl.load_workbook(SRC, data_only=True)["基础数据"]

accounts = []
for r in range(4, 44):
    if src.cell(r, 7).value != 1:
        continue
    accounts.append({
        "sid": src.cell(r, 3).value,
        "name": str(src.cell(r, 4).value).strip(),
        "kind": src.cell(r, 8).value,
        "pv": src.cell(r, 11).value or 0,
        "bal": src.cell(r, 140).value or 0,
        "rate": src.cell(r, 142).value or 0,
        "mint": src.cell(r, 143).value or 0,
        "cf": [src.cell(r, c).value or 0 for c in range(76, 140)],
    })

labels = [str(src.cell(r, 1).value).strip() for r in range(48, 112)]
years = [round((i + 1) / 12, 4) for i in range(60)] + [10, 15, 20, 30]
curve = [src.cell(r, 2).value or 0 for r in range(48, 112)]

n_acc = len(accounts)
n_bucket = 64
print("账户 %d 个（资产 %d / 负债 %d / 权益 %d），期限桶 %d"
      % (n_acc, sum(a["kind"] == "ASSET" for a in accounts),
         sum(a["kind"] == "LIAB" for a in accounts),
         sum(a["kind"] == "EQUITY" for a in accounts), n_bucket))

# 资产/负债列分组（②页 C 起）
COL_C = 3                                    # ②页首个账户列 = C
ACC_COL = {a["sid"]: COL_C + i for i, a in enumerate(accounts)}
asset_cols = [ACC_COL[a["sid"]] for a in accounts if a["kind"] == "ASSET"]
liab_cols = [ACC_COL[a["sid"]] for a in accounts if a["kind"] == "LIAB"]
first_asset, last_asset = min(asset_cols), max(asset_cols)
first_liab, last_liab = min(liab_cols), max(liab_cols)

# 细分标记
def asset_sub(a):
    if a["kind"] != "ASSET":
        return "NON_ASSET"
    return "NON_EARNING" if ("非生息" in a["name"]) else "EARNING"


def liab_sub(a):
    if a["kind"] != "LIAB":
        return "NON_LIAB"
    return "DEPOSIT" if ("存款" in a["name"] and "市场化" not in a["name"]) else "WHOLESALE"


# ===================== 2. 情景定义 =====================
SC = [
    ("baseline", "基准情景", 1, 0, "当前收益率曲线", "当前收益率曲线", "巴塞尔 SRP31.90 基准"),
    ("parallel_up", "平行上移", 1, 250, "全期限 +幅度", "全期限 +幅度", "巴塞尔 SRP31.90 平行上移"),
    ("parallel_down", "平行下移", 1, 250, "全期限 −幅度", "全期限 −幅度", "巴塞尔 SRP31.90 平行下移"),
    ("steepener", "变陡峭", 1, 100, "不变", "每年 +幅度，上限 +100bp", "巴塞尔 SRP31.92 陡峭化"),
    ("flattener", "变平坦", 1, 100, "−幅度", "不变", "巴塞尔 SRP31.91 平坦化"),
    ("short_up", "短端上移", 1, 250, "全期限 +幅度", "不变", "★ 巴塞尔 SRP31.90 短端上移（v1 缺失）"),
    ("short_down", "短端下移", 1, 250, "全期限 −幅度", "不变", "★ 巴塞尔 SRP31.90 短端下移（v1 缺失）"),
]
SC_ROW = {s[0]: 6 + i for i, s in enumerate(SC)}          # ①页情景表行号
N_SC = len(SC)

# ===================== 3. 建簿 =====================
wb = Workbook()
wb.remove(wb.active)


def sheet(title, sub, last_col, sub_last=None):
    ws = wb.create_sheet(title)
    ws.merge_cells("A1:%s1" % last_col)
    ws["A1"] = title
    ws["A1"].font = F_TITLE
    ws["A1"].fill = FILL_RED
    ws["A1"].alignment = AL_C
    ws.row_dimensions[1].height = 28
    ws.merge_cells("A2:%s2" % (sub_last or last_col))
    ws["A2"] = sub
    ws["A2"].font = F_SMALL
    ws["A2"].fill = FILL_LIGHT
    ws["A2"].alignment = AL_C
    ws.row_dimensions[2].height = 18
    return ws


def hdr(ws, row, labels_, widths=None, height=28):
    for i, h in enumerate(labels_, start=1):
        c = ws.cell(row, i, h)
        c.font = F_HDR
        c.fill = FILL_RED
        c.alignment = AL_CW
        c.border = BORDER
    ws.row_dimensions[row].height = height
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[GL(i)].width = w


def band(ws, row, text, span):
    ws.merge_cells("A%d:%s%d" % (row, GL(span), row))
    c = ws.cell(row, 1, text)
    c.font = F_SUB
    c.fill = FILL_RED
    c.alignment = AL_L
    ws.row_dimensions[row].height = 20


def put(ws, r, c, v, fmt=None, font=None, fill=None, align=None, border=True):
    cell = ws.cell(r, c, v)
    if fmt:
        cell.number_format = fmt
    cell.font = font or F_BODY
    if fill:
        cell.fill = fill
    cell.alignment = align or AL_R
    if border:
        cell.border = BORDER
    return cell


# ===================== ① 参数与口径 =====================
ws1 = sheet("①参数与口径", "参数区（黄色为可调输入）｜蓝色为公式计算｜数据日期 2025-12-31｜"
                            "本版全部指标口径均不使用一级资本", "H")
band(ws1, 4, "一、利率冲击情景定义（巴塞尔 IRRBB SRP31.90-93 六个规定情景 + 基准）", 9)
hdr(ws1, 5, ["序号", "情景代码", "情景名称", "启用(1/0)", "冲击幅度(bp)",
             "短端(≤1Y)处理", "长端(>1Y)处理", "监管依据", "1Y点位实际变动(bp)"],
    [6, 16, 12, 11, 12, 20, 26, 34, 20])
for i, (code, name, on, bp, sh, lo, note) in enumerate(SC):
    r = 6 + i
    put(ws1, r, 1, i, "0", align=AL_C)
    put(ws1, r, 2, code, align=AL_L)
    put(ws1, r, 3, name, align=AL_C)
    put(ws1, r, 4, on, "0", fill=FILL_INPUT, align=AL_C)
    put(ws1, r, 5, bp, "0", fill=FILL_INPUT, align=AL_C)
    put(ws1, r, 6, sh, align=AL_L)
    put(ws1, r, 7, lo, align=AL_L)
    put(ws1, r, 8, note, align=AL_L)
    if code == "baseline":
        put(ws1, r, 9, 0, "+0;-0", align=AL_C, fill=FILL_FORMULA)
    else:
        k = i - 1
        put(ws1, r, 9, "=(③曲线与折现因子!%s$15-③曲线与折现因子!$C$15)*100"
            % GL(5 + k), "+0.0;-0.0", align=AL_C, fill=FILL_FORMULA)
put(ws1, 13, 1, "★「1Y点位实际变动(bp)」= 该情景在 12M 期限上相对基准曲线的真实变动（自动读取③页），"
                "与「冲击幅度(bp)」的差额即利率下限/封顶造成的截断，例：平行下移设定 −250bp，"
                "因 1Y 基准利率仅 1.3372% 且下限为 0，实际只下行 133.7bp。",
    align=AL_LW, font=F_NOTE)
ws1.merge_cells("A13:I13")
ws1.row_dimensions[13].height = 26

band(ws1, 14, "二、模型假设参数", 8)
assum = [
    ("存款利率传导系数 β（负债端）", 0.5, "0.000",
     "负债端贴现曲线 = 基准 + (情景 − 基准) × β。β=0 存款利率固定；β=1 完全跟随市场。"
     "FSI Brief 19：多数银行 NMD 假设主导 IRRBB 结果"),
    ("长期利率下限", 0, "0.00", "冲击后利率不低于该值（%），防止负利率导致折现因子异常"),
    ("短端判定年限", 1, "0", "短端/长端分界年限，1 表示 ≤1Y 为短端"),
]
for i, (k, v, f, d) in enumerate(assum):
    r = 15 + i
    put(ws1, r, 1, k, align=AL_L)
    put(ws1, r, 2, v, f, fill=FILL_INPUT, align=AL_C)
    ws1.merge_cells("C%d:H%d" % (r, r))
    put(ws1, r, 3, d, align=AL_L)
    for c in range(4, 9):
        ws1.cell(r, c).border = BORDER
BETA = "①参数与口径!$B$15"

band(ws1, 19, "三、指标口径定义（全部不使用一级资本）", 8)
hdr(ws1, 20, ["口径代码", "口径名称", "计算公式", "分母基数", "预警阈值(%)", "监管/管理定位", "数据依赖", "备注"],
    [14, 20, 34, 20, 12, 22, 22, 30])
met_def = [
    ("EVE_PCT", "ΔEVE / EVE基准", "(EVE_冲击 − EVE_基准) / EVE_基准", "净资产现值(资产PV−负债PV)", "",
     "经济价值相对变化率", "④⑤页", "巴塞尔 EVE 早期预警指标之一；EVE基准为负时符号自动翻转"),
    ("EVE_ABS", "|ΔEVE| / |EVE基准|", "ABS(ΔEVE) / ABS(EVE_基准)", "净资产现值", "",
     "经济价值变化幅度", "④⑤页", "口径更直观，恒为正"),
    ("AST", "ΔEVE / 总资产", "ΔEVE / 资产现值合计", "总资产现值", "", "规模归一化", "④⑤页",
     "剔除资本规模影响，跨行可比"),
    ("DEP", "ΔEVE / 存款总额", "ΔEVE / 存款类负债现值合计", "存款类负债现值", "",
     "负债端规模归一化", "④⑤页", "衡量存款对经济价值的杠杆"),
    ("IAR", "ΔEVE / 生息资产", "ΔEVE / 生息资产现值合计", "生息资产现值", "", "规模归一化", "④⑤页",
     "与 NIM 口径的资产端分母一致"),
    ("NII", "ΔNII / NII基准", "(NII_冲击 − NII_基准) / NII_基准", "NII 基准(年化)", "",
     "相对盈利口径", "⑥页", "巴塞尔 SRP31.87「相对盈利」异常银行测试"),
]
for i, row in enumerate(met_def):
    r = 21 + i
    for c, v in enumerate(row, start=1):
        put(ws1, r, c, v, align=AL_C if c in (1, 5) else AL_L,
            fill=FILL_INPUT if c == 5 else None)
band(ws1, 28, "四、说明", 8)
notes1 = [
    "1）v1 模版主指标为 |ΔEVE| / 一级资本 ≤ 15%（银保监《商业银行银行账户利率风险计量》）。"
    "本版按需求改为不使用一级资本的口径组合，v1 口径仍可作为监管报送口径单独保留。",
    "2）巴塞尔 SRP31.83 明确允许监管增设「不同资本口径（CET1、超额资本）或相对盈利」的附加异常测试，"
    "且阈值不得低于 Tier 1 的 15%——本版的 AST/DEP/IAR/NII 口径即属此类管理口径。",
    "3）★ 重要提示：本模版以「资产合同现金流 × 市场贴现率 − 负债合同现金流 × 传导后贴现率」计量经济价值，"
    "未做商业利差（商业 margin）剥离，且 EVE 基准可能为负。EVE 基准为负时 EVE_PCT 口径的符号会翻转，"
    "此时应以 EVE_ABS / AST / DEP 口径为准。",
    "4）6 个冲击情景较 v1 补入 short_rate_up / short_rate_down（短端冲击），是巴塞尔 SRP31.90-93 规定的完整集合。",
]
for i, t in enumerate(notes1):
    r = 29 + i
    ws1.merge_cells("A%d:H%d" % (r, r))
    put(ws1, r, 1, t, align=AL_LW, font=F_NOTE)
    ws1.row_dimensions[r].height = 30

# ===================== ② 现金流底稿 =====================
ws2 = sheet("②现金流底稿", "数据来源：prcp_basic_20251231_v5.xlsx 基础数据页 剩余期限分布 BX~EI（64 桶）｜"
                            "本表为唯一静态数据源，其余各页均为公式", GL(COL_C + n_acc - 1))
hdr(ws2, 3, ["期限", "年数"] + [a["name"][:14] for a in accounts],
    [10, 8] + [21] * n_acc)
# 账户元信息行（编码 / 大类 / 余额 / 利率 / 月利息）
for i, a in enumerate(accounts):
    c = COL_C + i
    ws2.cell(4, c, a["sid"]).font = Font(name="微软雅黑", size=7, color="888888")
    ws2.cell(5, c, a["kind"]).font = Font(name="微软雅黑", size=7, color="888888")
    ws2.cell(6, c, a["bal"]).number_format = "#,##0"
    ws2.cell(6, c).font = Font(name="微软雅黑", size=8, color="555555")
    ws2.cell(7, c, a["rate"]).number_format = "0.00"
    ws2.cell(7, c).font = Font(name="微软雅黑", size=8, color="555555")
    ws2.cell(8, c, a["mint"]).number_format = "#,##0"
    ws2.cell(8, c).font = Font(name="微软雅黑", size=8, color="555555")
for r, lab in ((4, "账户编码"), (5, "大类"), (6, "当前余额(元)"), (7, "加权平均利率(%)"), (8, "月利息(元)")):
    put(ws2, r, 1, lab, align=AL_L, font=Font(name="微软雅黑", size=7, color="888888"))
put(ws2, 4, 2, "", align=AL_C)
# 桶数据行 10..73
B0 = 10
for t in range(n_bucket):
    r = B0 + t
    put(ws2, r, 1, labels[t], align=AL_C)
    put(ws2, r, 2, years[t], "0.0000", align=AL_R)
    for i, a in enumerate(accounts):
        put(ws2, r, COL_C + i, a["cf"][t], NUM, align=AL_R)
put(ws2, 74, 1, "合计", align=AL_C, font=F_BOLD, fill=FILL_GREY)
put(ws2, 74, 2, "", fill=FILL_GREY)
for i in range(n_acc):
    c = COL_C + i
    put(ws2, 74, c, "=SUM(%s%d:%s%d)" % (GL(c), B0, GL(c), B0 + n_bucket - 1),
        NUM, font=F_BOLD, fill=FILL_GREY)
ws2.freeze_panes = "C%d" % B0

# ===================== ③ 曲线与折现因子 =====================
# 列: A期限 B年数 C基准利率 D基准DF | E..J 资产端6情景利率 | K..P 负债端6情景利率
#     Q..V 资产端6情景DF | W..AB 负债端6情景DF
ws3 = sheet("③曲线与折现因子", "利率单位＝百分数(%)；冲击幅度参数单位＝bp（1bp = 0.01%，即 ÷100 换算）｜"
                              "资产端＝情景曲线；负债端＝基准 +(情景−基准)×β｜"
                              "折现因子 DF = 1/(1+r/100)^年数｜右侧 AC 列起为「相对基准的真实变动(bp)」", "AN")
hr = 3
heads3 = ["期限", "年数", "基准利率(%)", "基准DF"]
for _, nm, *_ in SC[1:]:
    heads3.append("资产:%s(%%)" % nm)
for _, nm, *_ in SC[1:]:
    heads3.append("负债:%s(%%)" % nm)
for _, nm, *_ in SC[1:]:
    heads3.append("资产DF:%s" % nm)
for _, nm, *_ in SC[1:]:
    heads3.append("负债DF:%s" % nm)
for _, nm, *_ in SC[1:]:
    heads3.append("Δ(bp)资产:%s" % nm)
for _, nm, *_ in SC[1:]:
    heads3.append("Δ(bp)负债:%s" % nm)
hdr(ws3, hr, heads3, [10, 8] + [13] * 26 + [14] * 12, height=42)

# 行 4..67
R0 = 4
for t in range(n_bucket):
    r = R0 + t
    put(ws3, r, 1, "=②现金流底稿!A%d" % (B0 + t), align=AL_C)
    put(ws3, r, 2, "=②现金流底稿!B%d" % (B0 + t), "0.0000")
    put(ws3, r, 3, curve[t], "0.0000", align=AL_R)
    put(ws3, r, 4, "=1/(1+C%d/100)^B%d" % (r, r), "0.000000", fill=FILL_FORMULA)
    for k, (code, name, on, bp, sh, lo, note) in enumerate(SC[1:]):
        sr = SC_ROW[code]
        col = 5 + k                                    # E..J 资产端利率
        if code == "parallel_up":
            f = "=IF(①参数与口径!$D$%d=0,$C%d,MAX(①参数与口径!$B$16,$C%d+①参数与口径!$E$%d/100))" % (sr, r, r, sr)
        elif code == "parallel_down":
            f = "=IF(①参数与口径!$D$%d=0,$C%d,MAX(①参数与口径!$B$16,$C%d-①参数与口径!$E$%d/100))" % (sr, r, r, sr)
        elif code == "steepener":
            f = ("=IF(①参数与口径!$D$%d=0,$C%d,IF($B%d<=①参数与口径!$B$17,$C%d,"
                 "MIN($C%d+①参数与口径!$E$%d/100,$C%d+($B%d-①参数与口径!$B$17)*①参数与口径!$E$%d/100)))"
                 % (sr, r, r, r, r, sr, r, r, sr))
        elif code == "flattener":
            f = ("=IF(①参数与口径!$D$%d=0,$C%d,IF($B%d<=①参数与口径!$B$17,"
                 "MAX(①参数与口径!$B$16,$C%d-①参数与口径!$E$%d/100),$C%d))"
                 % (sr, r, r, r, sr, r))
        elif code == "short_up":
            f = ("=IF(①参数与口径!$D$%d=0,$C%d,IF($B%d<=①参数与口径!$B$17,"
                 "MAX(①参数与口径!$B$16,$C%d+①参数与口径!$E$%d/100),$C%d))"
                 % (sr, r, r, r, sr, r))
        else:  # short_down
            f = ("=IF(①参数与口径!$D$%d=0,$C%d,IF($B%d<=①参数与口径!$B$17,"
                 "MAX(①参数与口径!$B$16,$C%d-①参数与口径!$E$%d/100),$C%d))"
                 % (sr, r, r, r, sr, r))
        put(ws3, r, col, f, "0.0000", fill=FILL_FORMULA)
        # 负债端：基准 + (资产情景 − 基准) × β
        put(ws3, r, 11 + k,
            "=$C%d+(%s%d-$C%d)*%s" % (r, GL(col), r, r, BETA), "0.0000", fill=FILL_FORMULA)
    for k in range(6):
        put(ws3, r, 17 + k, "=1/(1+%s%d/100)^$B%d" % (GL(5 + k), r, r), "0.000000", fill=FILL_FORMULA)
        put(ws3, r, 23 + k, "=1/(1+%s%d/100)^$B%d" % (GL(11 + k), r, r), "0.000000", fill=FILL_FORMULA)
    # 相对基准的真实变动（bp）—— 1bp = 0.01%，故 (情景% − 基准%) × 100
    for k in range(6):
        put(ws3, r, 29 + k, "=(%s%d-$C%d)*100" % (GL(5 + k), r, r), "+0.0;-0.0",
            fill=FILL_FORMULA, align=AL_R)
        put(ws3, r, 35 + k, "=(%s%d-$C%d)*100" % (GL(11 + k), r, r), "+0.0;-0.0",
            fill=FILL_FORMULA, align=AL_R)
ws3.freeze_panes = "C4"

# ===================== ④ 账户PV矩阵 =====================
# 列: A编码 B名称 C大类 D当前余额(亿) E..K 基准+6情景PV(亿) | L资产细分 M负债细分 N现值×久期 O久期(年)
ws4 = sheet("④账户PV矩阵", "账户现值 PV = SUMPRODUCT(②账户64桶现金流, ③对应情景折现因子) ÷ 1e8｜"
                            "资产端用资产DF，负债端用负债DF", "O")
hdr(ws4, 3, ["账户编码", "账户名称", "大类", "当前余额(亿)", "基准PV(亿)"] +
    ["%sPV(亿)" % s[1] for s in SC[1:]] + ["资产细分", "负债细分", "PV×久期", "Macaulay久期(年)"],
    [18, 26, 8, 14] + [15] * 7 + [13, 13, 16, 16])
P0 = 4
for i, a in enumerate(accounts):
    r = P0 + i
    put(ws4, r, 1, a["sid"], align=AL_L)
    put(ws4, r, 2, a["name"], align=AL_L)
    put(ws4, r, 3, a["kind"], align=AL_C,
        fill=FILL_ASSET if a["kind"] == "ASSET" else (FILL_LIAB if a["kind"] == "LIAB" else FILL_EQUITY))
    put(ws4, r, 4, "=②现金流底稿!%s6/100000000" % GL(COL_C + i), NUM, align=AL_R)
    cf_range = "②现金流底稿!%s%d:%s%d" % (GL(COL_C + i), B0, GL(COL_C + i), B0 + n_bucket - 1)
    # 基准 PV
    put(ws4, r, 5, "=SUMPRODUCT(%s,③曲线与折现因子!$D$%d:$D$%d)/100000000"
        % (cf_range, R0, R0 + n_bucket - 1), NUM, fill=FILL_FORMULA)
    for k in range(6):
        dcol = GL(17 + k) if a["kind"] != "LIAB" else GL(23 + k)
        put(ws4, r, 6 + k, "=SUMPRODUCT(%s,③曲线与折现因子!$%s$%d:$%s$%d)/100000000"
            % (cf_range, dcol, R0, dcol, R0 + n_bucket - 1), NUM, fill=FILL_FORMULA)
    put(ws4, r, 12, asset_sub(a), align=AL_C)
    put(ws4, r, 13, liab_sub(a), align=AL_C)
    put(ws4, r, 15, "=IFERROR(SUMPRODUCT(%s,③曲线与折现因子!$B$%d:$B$%d,③曲线与折现因子!$D$%d:$D$%d)"
                      "/SUMPRODUCT(%s,③曲线与折现因子!$D$%d:$D$%d),0)"
        % (cf_range, R0, R0 + n_bucket - 1, R0, R0 + n_bucket - 1,
           cf_range, R0, R0 + n_bucket - 1), NUM4, fill=FILL_FORMULA)
    put(ws4, r, 14, "=E%d*O%d" % (r, r), NUM, fill=FILL_FORMULA)
LAST = P0 + n_acc - 1
R_A = LAST + 1
R_L = LAST + 2
R_E = LAST + 3
put(ws4, R_A, 1, "资产合计", align=AL_L, font=F_BOLD, fill=FILL_GREY)
put(ws4, R_L, 1, "负债合计", align=AL_L, font=F_BOLD, fill=FILL_GREY)
put(ws4, R_E, 1, "EVE（资产PV−负债PV）", align=AL_L, font=F_BOLD, fill=FILL_GREY)
for c in range(2, 16):
    ws4.cell(R_A, c).border = BORDER
    ws4.cell(R_L, c).border = BORDER
    ws4.cell(R_E, c).border = BORDER
    ws4.cell(R_A, c).fill = FILL_GREY
    ws4.cell(R_L, c).fill = FILL_GREY
    ws4.cell(R_E, c).fill = FILL_GREY
for c in range(4, 12):
    put(ws4, R_A, c, "=SUMIF($C$%d:$C$%d,\"ASSET\",%s$%d:%s$%d)"
        % (P0, LAST, GL(c), P0, GL(c), LAST), NUM, font=F_BOLD, fill=FILL_GREY)
    put(ws4, R_L, c, "=SUMIF($C$%d:$C$%d,\"LIAB\",%s$%d:%s$%d)"
        % (P0, LAST, GL(c), P0, GL(c), LAST), NUM, font=F_BOLD, fill=FILL_GREY)
    put(ws4, R_E, c, "=%s%d-%s%d" % (GL(c), R_A, GL(c), R_L), NUM, font=F_BOLD, fill=FILL_GREY)
put(ws4, R_A, 14, "=SUMIF($C$%d:$C$%d,\"ASSET\",$N$%d:$N$%d)" % (P0, LAST, P0, LAST), NUM,
    font=F_BOLD, fill=FILL_GREY)
put(ws4, R_L, 14, "=SUMIF($C$%d:$C$%d,\"LIAB\",$N$%d:$N$%d)" % (P0, LAST, P0, LAST), NUM,
    font=F_BOLD, fill=FILL_GREY)
for r in (R_A, R_L, R_E):
    ws4.cell(r, 12).border = BORDER
    ws4.cell(r, 13).border = BORDER
    ws4.cell(r, 15).border = BORDER

# ===================== ⑤ ΔEVE 多口径汇总 =====================
ws5 = sheet("⑤ΔEVE多口径汇总", "★ 本页所有指标口径均不使用一级资本｜"
                                "口径：EVE_PCT / EVE_ABS / AST / DEP / IAR / NII", "O")
hdr(ws5, 3, ["情景代码", "情景名称", "资产PV(亿)", "负债PV(亿)", "EVE(亿)", "ΔEVE(亿)",
             "ΔEVE/EVE基准%", "|ΔEVE|/|EVE基准|%", "ΔEVE/总资产%", "ΔEVE/存款总额%",
             "ΔEVE/生息资产%", "ΔNII(亿)", "ΔNII%", "|ΔEVE|(辅助)", "启用"],
    [15, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 14, 12, 14, 8])
S0 = 4
for i, (code, name, on, bp, sh, lo, note) in enumerate(SC):
    r = S0 + i
    put(ws5, r, 1, code, align=AL_L)
    put(ws5, r, 2, name, align=AL_C)
    vcol = GL(5 + i)                                   # ④页情景 PV 列
    put(ws5, r, 3, "=④账户PV矩阵!%s%d" % (vcol, R_A), NUM, fill=FILL_FORMULA)
    put(ws5, r, 4, "=④账户PV矩阵!%s%d" % (vcol, R_L), NUM, fill=FILL_FORMULA)
    put(ws5, r, 5, "=④账户PV矩阵!%s%d" % (vcol, R_E), NUM, fill=FILL_FORMULA)
    put(ws5, r, 6, "=E%d-$E$%d" % (r, S0), NUM, fill=FILL_FORMULA)
    put(ws5, r, 7, "=IFERROR(F%d/$E$%d,\"n/a\")" % (r, S0), PCT, fill=FILL_FORMULA)
    put(ws5, r, 8, "=IFERROR(ABS(F%d)/ABS($E$%d),\"n/a\")" % (r, S0), PCT, fill=FILL_FORMULA)
    put(ws5, r, 9, "=IFERROR(F%d/$C$%d,\"n/a\")" % (r, S0), PCT, fill=FILL_FORMULA)
    put(ws5, r, 10, "=IFERROR(F%d/SUMIF(④账户PV矩阵!$M$%d:$M$%d,\"DEPOSIT\",④账户PV矩阵!$E$%d:$E$%d),\"n/a\")"
        % (r, P0, LAST, P0, LAST), PCT, fill=FILL_FORMULA)
    put(ws5, r, 11, "=IFERROR(F%d/SUMIF(④账户PV矩阵!$L$%d:$L$%d,\"EARNING\",④账户PV矩阵!$E$%d:$E$%d),\"n/a\")"
        % (r, P0, LAST, P0, LAST), PCT, fill=FILL_FORMULA)
    put(ws5, r, 12, "=⑥ΔNII与久期缺口!$C$%d" % (17 + i), NUM, fill=FILL_FORMULA)
    put(ws5, r, 13, "=IFERROR(L%d/⑥ΔNII与久期缺口!$B$14,\"n/a\")" % r, PCT, fill=FILL_FORMULA)
    put(ws5, r, 14, "=ABS(F%d)" % r, NUM, fill=FILL_FORMULA)
    put(ws5, r, 15, "=①参数与口径!$D$%d" % SC_ROW[code], "0", align=AL_C, fill=FILL_FORMULA)
S_LAST = S0 + N_SC - 1
# EVE 基准健康度提示
put(ws5, S_LAST + 1, 1, "EVE 基准健康度", align=AL_L, font=F_BOLD, fill=FILL_GREY)
ws5.merge_cells("B%d:O%d" % (S_LAST + 1, S_LAST + 1))
put(ws5, S_LAST + 1, 2,
    "=IF($E$%d<0,"
    "\"⚠ EVE 基准为负（当前 \"&TEXT($E$%d,\"#,##0.00\")&\" 亿元）：经济价值为负，"
    "EVE_PCT / EVE_ABS 口径分母过小、结果失真，建议以 AST / DEP / IAR 规模归一化口径判读；\","
    "IF(ABS($E$%d)<$C$%d*0.01,"
    "\"⚠ EVE 基准绝对值不足总资产 1%%，相对口径失真，建议改用规模归一化口径；\","
    "\"EVE 基准绝对值 ≥ 总资产 1%%，EVE_PCT / EVE_ABS 口径可用\"))"
    % (S0, S0, S0, S0),
    align=AL_L, font=F_NOTE, fill=FILL_GREY)
ws5.row_dimensions[S_LAST + 1].height = 26
band(ws5, S_LAST + 2, "最坏情景（按 |ΔEVE| 最大；★ 巴塞尔原文为 maximum ΔEVE，方向口径以 F 列为准）", 15)
BW = S_LAST + 3
put(ws5, BW, 1, "最坏情景", align=AL_L, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 2, "=INDEX($B$%d:$B$%d,MATCH(MAX($N$%d:$N$%d),$N$%d:$N$%d,0))"
    % (S0 + 1, S_LAST, S0 + 1, S_LAST, S0 + 1, S_LAST), align=AL_C, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 6, "=INDEX($F$%d:$F$%d,MATCH(MAX($N$%d:$N$%d),$N$%d:$N$%d,0))"
    % (S0 + 1, S_LAST, S0 + 1, S_LAST, S0 + 1, S_LAST), NUM, font=F_BOLD, fill=FILL_GREY)
for c, f in ((7, "=IFERROR(F%d/$E$%d,\"n/a\")"), (8, "=IFERROR(ABS(F%d)/ABS($E$%d),\"n/a\")"),
             (9, "=IFERROR(F%d/$C$%d,\"n/a\")")):
    put(ws5, BW, c, f % (BW, S0), PCT, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 10, "=IFERROR(F%d/SUMIF(④账户PV矩阵!$M$%d:$M$%d,\"DEPOSIT\",④账户PV矩阵!$E$%d:$E$%d),\"n/a\")"
    % (BW, P0, LAST, P0, LAST), PCT, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 11, "=IFERROR(F%d/SUMIF(④账户PV矩阵!$L$%d:$L$%d,\"EARNING\",④账户PV矩阵!$E$%d:$E$%d),\"n/a\")"
    % (BW, P0, LAST, P0, LAST), PCT, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 12, "=INDEX($L$%d:$L$%d,MATCH(MAX($N$%d:$N$%d),$N$%d:$N$%d,0))"
    % (S0 + 1, S_LAST, S0 + 1, S_LAST, S0 + 1, S_LAST), NUM, font=F_BOLD, fill=FILL_GREY)
put(ws5, BW, 13, "=IFERROR(L%d/⑥ΔNII与久期缺口!$B$14,\"n/a\")" % BW, PCT, font=F_BOLD, fill=FILL_GREY)
for c in range(3, 16):
    ws5.cell(BW, c).border = BORDER
    ws5.cell(BW, c).fill = FILL_GREY
put(ws5, BW + 2, 1, "口径速查", font=F_BOLD, align=AL_L)
legend = [
    "EVE_PCT = (EVE_冲击 − EVE_基准) / EVE_基准　　带符号；EVE 基准为负时符号翻转，须结合 EVE_ABS 判读",
    "EVE_ABS = |ΔEVE| / |EVE_基准|　　经济价值变化幅度口径，恒为正",
    "AST = ΔEVE / 资产现值合计　　规模归一化，剔除资本规模影响",
    "DEP = ΔEVE / 存款类负债现值合计　　衡量存款对经济价值的杠杆",
    "IAR = ΔEVE / 生息资产现值合计　　与 NIM 资产端分母一致",
    "NII = ΔNII / NII 基准　　巴塞尔 SRP31.87 相对盈利异常测试口径",
]
for i, t in enumerate(legend):
    ws5.merge_cells("A%d:O%d" % (BW + 3 + i, BW + 3 + i))
    put(ws5, BW + 3 + i, 1, t, align=AL_L, font=F_NOTE)

# ===================== ⑥ ΔNII 与久期缺口 =====================
ws6 = sheet("⑥ΔNII与久期缺口", "久期缺口：DGAP = D_A − (L/A) × D_L｜"
                                "ΔNII：首年（12 个月内）重定价缺口近似，负债端按 β 传导", "AB")
band(ws6, 3, "一、久期与久期缺口（基于基准现金流与基准曲线）", 8)
hdr(ws6, 4, ["项目", "数值", "单位", "说明"], [24, 18, 16, 46])
dur = [
    ("资产现值合计", "=④账户PV矩阵!$E$%d" % R_A, "亿元", "基准情景下资产端 PV 合计"),
    ("负债现值合计", "=④账户PV矩阵!$E$%d" % R_L, "亿元", "基准情景下负债端 PV 合计"),
    ("EVE 基准（资产−负债）", "=④账户PV矩阵!$E$%d" % R_E, "亿元", "★ 为负时 EVE_PCT 口径符号翻转，须改用其他口径"),
    ("资产加权久期 D_A", "=IFERROR(④账户PV矩阵!$N$%d/④账户PV矩阵!$E$%d,0)" % (R_A, R_A), "年",
     "Σ(PV×久期)/ΣPV，资产端"),
    ("负债加权久期 D_L", "=IFERROR(④账户PV矩阵!$N$%d/④账户PV矩阵!$E$%d,0)" % (R_L, R_L), "年",
     "Σ(PV×久期)/ΣPV，负债端"),
    ("久期缺口 DGAP", "=B8-(B6/B5)*B9", "年", "D_A − (L/A) × D_L；正=资产久期长于负债"),
    ("久期缺口×资产规模", "=B10*B5", "亿元", "近似 ΔEVE = −Δi × DGAP × A 的规模口径（一阶近似，仅供事前估算）"),
]
for i, (k, f, u, d) in enumerate(dur):
    r = 5 + i
    put(ws6, r, 1, k, align=AL_L)
    put(ws6, r, 2, f, NUM4 if "久期" in k and "规模" not in k else NUM, fill=FILL_FORMULA)
    put(ws6, r, 3, u, align=AL_C)
    ws6.merge_cells("D%d:H%d" % (r, r))
    put(ws6, r, 4, d, align=AL_LW, font=F_NOTE)
    for c in range(5, 9):
        ws6.cell(r, c).border = BORDER

band(ws6, 13, "二、NII 基准", 8)
put(ws6, 14, 1, "NII 基准（年化）", align=AL_L)
put(ws6, 14, 2, "=(SUMIF(②现金流底稿!$C$5:%s$5,\"ASSET\",②现金流底稿!$C$8:%s$8)"
                "-SUMIF(②现金流底稿!$C$5:%s$5,\"LIAB\",②现金流底稿!$C$8:%s$8))*12/100000000"
    % (GL(COL_C + n_acc - 1), GL(COL_C + n_acc - 1), GL(COL_C + n_acc - 1), GL(COL_C + n_acc - 1)),
    NUM, fill=FILL_FORMULA)
put(ws6, 14, 3, "亿元", align=AL_C)
ws6.merge_cells("D14:H14")
put(ws6, 14, 4, "资产月利息合计 − 负债月利息合计，再 ×12 年化（取自②页第8行元数据）", align=AL_LW, font=F_NOTE)

band(ws6, 15, "三、ΔNII（首年重定价缺口近似，敞口明细见「⑦首年重定价敞口」）", 8)
hdr(ws6, 16, ["情景代码", "情景名称", "ΔNII(亿)", "ΔNII%"], [24, 18, 16, 46])
for i, (code, name, on, bp, sh, lo, note) in enumerate(SC):
    r = 17 + i
    put(ws6, r, 1, code, align=AL_L)
    put(ws6, r, 2, name, align=AL_C)
    if code == "baseline":
        put(ws6, r, 3, 0, NUM, fill=FILL_FORMULA)
        put(ws6, r, 5, 0, "0", fill=FILL_FORMULA)
    else:
        k = i - 1
        acol = GL(5 + k)
        put(ws6, r, 5, "=(③曲线与折现因子!%s$%d-③曲线与折现因子!$C$%d)*100" % (acol, R0 + 11, R0 + 11),
            "0.0", fill=FILL_FORMULA)
        put(ws6, r, 3, "=0", NUM, fill=FILL_FORMULA)
    put(ws6, r, 4, "=IFERROR(C%d/$B$14,\"n/a\")" % r, PCT, fill=FILL_FORMULA)

# ===================== ⑦ 首年重定价敞口 =====================
ws7 = sheet("⑦首年重定价敞口", "ΔNII 计算底稿：12 个月内现金流 × 各情景利率变化向量｜"
                              "资产端不传导，负债端按 β 传导", "K")
hdr(ws7, 3, ["期限", "年数", "基准利率(%)"] +
    ["%s利率" % s[1] for s in SC[1:]] +
    ["资产现金流(元)", "负债现金流(元)"], [12, 10, 13] + [13] * 6 + [20, 20])
for t in range(12):
    r = 4 + t
    put(ws7, r, 1, "=②现金流底稿!A%d" % (B0 + t), align=AL_C)
    put(ws7, r, 2, "=②现金流底稿!B%d" % (B0 + t), "0.0000")
    put(ws7, r, 3, "=③曲线与折现因子!C%d" % (R0 + t), "0.0000")
    for k in range(6):
        put(ws7, r, 4 + k, "=③曲线与折现因子!%s%d" % (GL(5 + k), R0 + t), "0.0000")
    put(ws7, r, 10, "=SUM(②现金流底稿!%s%d:%s%d)" % (GL(first_asset), B0 + t, GL(last_asset), B0 + t), NUM)
    put(ws7, r, 11, "=SUM(②现金流底稿!%s%d:%s%d)" % (GL(first_liab), B0 + t, GL(last_liab), B0 + t), NUM)
put(ws7, 16, 1, "合计", align=AL_C, font=F_BOLD, fill=FILL_GREY)
put(ws7, 16, 2, "", fill=FILL_GREY)
put(ws7, 16, 3, "", fill=FILL_GREY)
for k in range(6):
    put(ws7, 16, 4 + k, "", fill=FILL_GREY)
put(ws7, 16, 10, "=SUM(J4:J15)", NUM, font=F_BOLD, fill=FILL_GREY)
put(ws7, 16, 11, "=SUM(K4:K15)", NUM, font=F_BOLD, fill=FILL_GREY)
band(ws7, 18, "说明", 11)
for i, t in enumerate([
    "1）ΔNII（⑥页）= Σ_资产(RCF₁₂M × Δr) − Σ_负债(RCF₁₂M × Δr × β)，其中 Δr 由本表「情景利率 − 基准利率」逐桶给出。",
    "2）变陡峭情景下 1 年内利率不变，故 ΔNII = 0；这是口径的正常结果，非计算错误。",
    "3）利率下限保护：情景利率不低于 0，故下移情景的实际冲击幅度可能小于设定幅度（如 1Y 由 −250bp 截断为 −133.7bp）。",
]):
    ws7.merge_cells("A%d:K%d" % (19 + i, 19 + i))
    put(ws7, 19 + i, 1, t, align=AL_LW, font=F_NOTE)
    ws7.row_dimensions[19 + i].height = 26

# 各情景 ΔNII（用⑦页辅助表）
for i, (code, name, on, bp, sh, lo, note) in enumerate(SC):
    r = 17 + i
    if code == "baseline":
        continue
    k = i - 1
    dcol = GL(4 + k)
    f = ("=(SUMPRODUCT('⑦首年重定价敞口'!$J$4:$J$15,('⑦首年重定价敞口'!$%s$4:$%s$15-'⑦首年重定价敞口'!$C$4:$C$15)/100)"
         "-SUMPRODUCT('⑦首年重定价敞口'!$K$4:$K$15,('⑦首年重定价敞口'!$%s$4:$%s$15-'⑦首年重定价敞口'!$C$4:$C$15)/100)*%s)/100000000"
         % (dcol, dcol, dcol, dcol, BETA))
    put(ws6, r, 3, f, NUM, fill=FILL_FORMULA)

band(ws6, 40, "四、ΔNII 口径说明", 8)
notes6 = [
    "1）ΔNII 采用「首年重定价缺口近似」：仅 12 个月内到期的现金流受利率重定价影响，"
    "ΔNII ≈ Σ_资产(RCF₁₂M × Δr) − Σ_负债(RCF₁₂M × Δr × β)，可解释、可审计。",
    "2）完整口径（逐月重定价 + 新业务投放）需接入 NII 逐月推演模版（NII计量模版_v4），本表为轻量版本。",
    "3）负债端按 β 传导：β=0 表示存款利率固定（如活期存款），β=1 表示完全跟随市场（如市场化负债）。"
    "本表统一用同一 β，精细化可在②页按账户拆分。",
]
for i, t in enumerate(notes6):
    ws6.merge_cells("A%d:H%d" % (41 + i, 41 + i))
    put(ws6, 41 + i, 1, t, align=AL_LW, font=F_NOTE)
    ws6.row_dimensions[41 + i].height = 26

# ===================== ⑧ 计算逻辑说明 =====================
ws8 = sheet("⑧计算逻辑说明", "ΔEVE 计量模版 v2（无资本口径版）", "D")
ws8.column_dimensions["A"].width = 26
ws8.column_dimensions["B"].width = 96
ws8.column_dimensions["C"].width = 16
ws8.column_dimensions["D"].width = 30
logic = [
    ("版本", "v2 —— 由 v1 改造：指标口径全部改为不使用一级资本；情景 4→7 个；全部改为活公式", "", ""),
    ("数据源", "prcp_basic_20251231_v5.xlsx 基础数据页：账户册 R4-R43（末级 24 个）、剩余期限 64 桶 BX~EI、"
               "当前余额 EJ、加权平均利率 EL、月利息 EM、现值 K、国债曲线 R48-R111", "", ""),
    ("①参数与口径", "情景启用/幅度、存款传导 β、长期利率下限、短端判定年限、6 个指标口径定义与阈值", "", ""),
    ("②现金流底稿", "唯一静态数据页：64 期限桶 × 24 账户剩余现金流；元数据区（编码/大类/余额/利率/月利息）", "", ""),
    ("③曲线与折现因子", "基准利率（静态）→ 6 情景资产端利率（公式，含启用开关与下限）→ 负债端利率 = 基准 +(情景−基准)×β → "
                        "折现因子 DF = 1/(1+r/100)^年数（资产端 7 列、负债端 7 列）", "", ""),
    ("④账户PV矩阵", "账户现值 PV = SUMPRODUCT(②该账户 64 桶现金流, ③对应情景折现因子) ÷ 1e8；"
                    "Macaulay 久期 = Σ(t×CF)/Σ(CF×DF)；末级账户 PV×久期 用于加权久期", "", ""),
    ("⑤ΔEVE多口径汇总", "EVE = 资产PV − 负债PV；ΔEVE = EVE_冲击 − EVE_基准；"
                        "6 个口径公式全部引用④⑥页，无任何一级资本输入", "", ""),
    ("⑥ΔNII与久期缺口", "DGAP = D_A − (L/A)×D_L；NII 基准 = (资产月利息−负债月利息)×12；"
                        "ΔNII 用 12 个月重定价敞口 × 利率变化向量计算，负债端乘 β", "", ""),
    ("公式链", "② → ③ → ④ → ⑤ / ⑥ → ⑦", "", ""),
    ("监管依据", "巴塞尔 III IRRBB 补充指引 SRP31.82（最大 ΔEVE vs Tier 1 15%）、SRP31.83（允许不同资本口径或相对盈利的附加测试）、"
               "SRP31.85（关键假设）、SRP31.87（ΔNII 相对盈利）、SRP31.90-93（六个规定冲击情景）；"
               "中国银保监《商业银行银行账户利率风险计量》", "", ""),
    ("口径说明", "本版未做商业利差（commercial margin）剥离；EVE 基准为负时 EVE_PCT 符号翻转，"
               "应以 EVE_ABS / AST / DEP 判读；负债端 β 为全行统一值，未做账户级差异化", "", ""),
    ("已知局限", "① 合同现金流未剥离商业利差，资产端 EVE 可能被系统性低估；② 权益账户现金流为 0，"
               "EVE 以「资产−负债」近似；③ 短端/长端分界为 1Y 固定，非巴塞尔的逐期限桶口径；"
               "④ ΔNII 为轻量近似，未含新业务投放与滚动续作", "", ""),
    ("久期口径 vs 全量重估", "⑥页久期缺口是一阶近似（ΔEVE ≈ −Δi×DGAP×A），用于事前估算与限额分配，"
                "不能替代⑤页的全量现金流重估；本模版中 DGAP 与隐含久期（由全量重估反算）存在差异，"
                "以⑤页结果为准", "", ""),
]
for i, (k, v, c, d) in enumerate(logic):
    r = 4 + i
    put(ws8, r, 1, k, align=AL_L, font=F_BOLD)
    ws8.merge_cells("B%d:D%d" % (r, r))
    put(ws8, r, 2, v, align=AL_LW, font=F_BODY)
    ws8.row_dimensions[r].height = 34

wb.save(OUT)
print("已生成:", OUT)
print("账户列 C~%s（资产 %s~%s，负债 %s~%s）"
      % (GL(COL_C + n_acc - 1), GL(first_asset), GL(last_asset), GL(first_liab), GL(last_liab)))
print("④页: 明细 R%d~%d，资产合计 R%d，负债合计 R%d，EVE R%d" % (P0, LAST, R_A, R_L, R_E))
print("⑤页: 情景行 R%d~%d，最坏情景 R%d" % (S0, S_LAST, BW))
