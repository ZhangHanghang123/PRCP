# -*- coding: utf-8 -*-
"""生成 build_score_standard_v13.ps1：评分标准 v13（增加 CAR 指标 + 修 ROE 覆盖漏洞）"""
import json

CAR = []          # 23 段
def row(tier, seg, lo, hi, w, score, desc, ilo, ihi, dist, lo_txt=None, hi_txt=None):
    CAR.append([None, tier, seg, lo_txt or lo, hi_txt or hi, w, score, desc, ilo, ihi, dist])

def pct(x, d=4):
    return ("%.*f%%" % (d, x * 100))

def pp(x, d=2):
    return ("%.*fpp" % (d, x))

CAR_ACT = 12.80 / 100
RED = 0.119          # 红线 11.9%
# 1 红线
mid = (0 + RED) / 2
row("🔴 不达标", 1, 0, RED, pp(RED * 100), 0, "不达标 (≤红线)", 0, 0, pp(abs(CAR_ACT - mid) * 100),
    "0.00%", pct(RED, 2))
# 2-6 危险 11.90~12.00 宽 0.02pp
danger = [(0.1190, 0.1192, 15, 0, 15), (0.1192, 0.1194, 45, 15, 45), (0.1194, 0.1196, 75, 45, 75),
          (0.1196, 0.1198, 105, 75, 105), (0.1198, 0.1200, 135, 105, 135)]
for i, (lo, hi, sc, ilo, ihi) in enumerate(danger):
    mid = (lo + hi) / 2
    row("🟠 危险", 2 + i, lo, hi, pp((hi - lo) * 100, 4), sc, "危险 0-150 分 (插值)", ilo, ihi,
        pp(abs(CAR_ACT - mid) * 100), pct(lo), pct(hi))
# 7-11 预警 12.00~12.20 宽 0.04pp
warn = [(0.1200, 0.1204, 165, 135, 165), (0.1204, 0.1208, 195, 165, 195), (0.1208, 0.1212, 225, 195, 225),
        (0.1212, 0.1216, 255, 225, 255), (0.1216, 0.1220, 285, 255, 285)]
for i, (lo, hi, sc, ilo, ihi) in enumerate(warn):
    mid = (lo + hi) / 2
    row("🟡 预警", 7 + i, lo, hi, pp((hi - lo) * 100, 4), sc, "预警 150-300 分 (插值)", ilo, ihi,
        pp(abs(CAR_ACT - mid) * 100), pct(lo), pct(hi))
# 12-16 安全 12.20~13.20 宽 0.20pp
safe = [(0.1220, 0.1240, 320, 285, 320), (0.1240, 0.1260, 360, 320, 360), (0.1260, 0.1280, 400, 360, 400),
        (0.1280, 0.1300, 440, 400, 440), (0.1300, 0.1320, 480, 440, 480)]
for i, (lo, hi, sc, ilo, ihi) in enumerate(safe):
    mid = (lo + hi) / 2
    row("🟢 安全", 12 + i, lo, hi, pp((hi - lo) * 100, 4), sc, "安全 300-500 分 (插值)", ilo, ihi,
        pp(abs(CAR_ACT - mid) * 100), pct(lo), pct(hi))
# 17 满分 13.20%
row("🟢🟢 满分", 17, 0.1320, 0.1320, pp(0, 4), 500, "⭐适度最优 500 分", 500, 500,
    pp(abs(CAR_ACT - 0.1320) * 100), pct(0.1320), pct(0.1320))
# 18-22 过优 13.20~16.20 宽 0.60pp
over = [(0.1320, 0.1380, 480, 500, 480), (0.1380, 0.1440, 440, 480, 440), (0.1440, 0.1500, 400, 440, 400),
        (0.1500, 0.1560, 360, 400, 360), (0.1560, 0.1620, 320, 360, 320)]
for i, (lo, hi, sc, ilo, ihi) in enumerate(over):
    mid = (lo + hi) / 2
    row("🟢 安全", 18 + i, lo, hi, pp((hi - lo) * 100, 4), sc, "过优 500→减分 (插值)", ilo, ihi,
        pp(abs(CAR_ACT - mid) * 100), pct(lo), pct(hi))
# 23 极度过剩
mid = (0.1620 + 9.99) / 2
row("🟢 安全", 23, 0.1620, 9.99, pp((9.99 - 0.1620) * 100, 2), 300, "极度过剩 300 分", 320, 300,
    pp(abs(CAR_ACT - mid) * 100), "16.20%", "999.00%")

# ---------- ROE 补 18-23 段（原表只有 17 段，ROE>12% 无匹配会抛异常）----------
ROE_ACT = 9.61 / 100
ROE = []
def rrow(tier, seg, lo, hi, w, score, desc, ilo, ihi, dist, lo_txt=None, hi_txt=None):
    ROE.append([None, tier, seg, lo_txt or lo, hi_txt or hi, w, score, desc, ilo, ihi, dist])

rover = [(0.1200, 0.1280, 480, 500, 480), (0.1280, 0.1360, 440, 480, 440), (0.1360, 0.1440, 400, 440, 400),
         (0.1440, 0.1520, 360, 400, 360), (0.1520, 0.1600, 320, 360, 320)]
for i, (lo, hi, sc, ilo, ihi) in enumerate(rover):
    mid = (lo + hi) / 2
    rrow("🟢 安全", 18 + i, lo, hi, pp((hi - lo) * 100, 4), sc, "过优 500→减分 (插值)", ilo, ihi,
         pp(abs(ROE_ACT - mid) * 100), pct(lo), pct(hi))
mid = (0.1600 + 9.99) / 2
rrow("🟢 安全", 23, 0.1600, 9.99, pp((9.99 - 0.1600) * 100, 2), 300, "极度过剩 300 分", 320, 300,
     pp(abs(ROE_ACT - mid) * 100), "16.00%", "999.00%")


# ===================== 得分重算 + 峰值修正 =====================
import openpyxl as _ox

_v12 = r"C://银行经营//PRCP//docs//v2//评分标准_v12c.xlsx"
_wb = _ox.load_workbook(_v12, data_only=True)
_ws = _wb["0-500分评分标准"]
_sdp = _wb["中信银行得分"]


def _pct(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t) / 100 if abs(t) > 1.5 else float(t)
    t = str(t).strip()
    if t.endswith("%"):
        return float(t[:-1]) / 100
    if t.endswith("pp"):
        return float(t[:-2]) / 100
    try:
        return float(t) / 100
    except Exception:
        return None


def _num(t):
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    try:
        return float(str(t).strip())
    except Exception:
        return None


# 得分页实测值（文本百分比）-> 小数
ACT = {}
for _r in range(5, 12):
    _nm = _sdp.cell(_r, 1).value
    _v = _sdp.cell(_r, 3).value
    if _nm and _v:
        ACT[str(_nm).strip()] = _pct(_v)

# 指标块起点
_blocks = {}
for _r in range(5, 200):
    _v = _ws.cell(_r, 1).value
    if isinstance(_v, str) and _v.strip() in ACT:
        _blocks[_v.strip()] = _r

SCORES = []
for _nm in ["LCR", "NSFR", "EVE", "CET1", "ROE", "IBL", "LR"]:
    _act = ACT[_nm]
    _s = _blocks[_nm]
    _hit = None
    for _r in range(_s, _s + 30):
        _lo, _hi = _pct(_ws.cell(_r, 4).value), _pct(_ws.cell(_r, 5).value)
        if _lo is None or _hi is None:
            break
        if _lo - 1e-12 <= _act <= _hi + 1e-12:
            _hit = (_r, _lo, _hi, _num(_ws.cell(_r, 9).value), _num(_ws.cell(_r, 10).value))
            break
    if not _hit:
        raise SystemExit("no segment for " + _nm)
    _r, _lo, _hi, _ilo, _ihi = _hit
    _sc = _ilo if _hi == _lo else _ilo + (_act - _lo) / (_hi - _lo) * (_ihi - _ilo)
    SCORES.append((_nm, round(_sc, 2)))
SCORES.append(("CAR", 400.0))
SCORES_ORDER = ["LCR", "NSFR", "EVE", "CET1", "CAR", "ROE", "IBL", "LR"]
SCORES = sorted(SCORES, key=lambda x: SCORES_ORDER.index(x[0]))

# 峰值修正：EVE 子段12 的 I（r62）与 IBL 子段12 的 I（v13 中 r154）-> 500
PEAK_FIX = [("EVE_I", 62, 500), ("IBL_I", 154, 500)]

PS = r'''$ErrorActionPreference = "Stop"
$SRC = "C:\银行经营\PRCP\docs\v2\评分标准_v12c.xlsx"
$DST = "C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
Copy-Item $SRC $DST -Force

function Read-Tsv2D($path, $cols) {
    $lines = @(Get-Content -Path $path -Encoding UTF8 | Where-Object { $_ -ne "" })
    $arr = [object[,]]::new($lines.Count, $cols)
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $parts = @($lines[$i] -split "`t")
        for ($j = 0; $j -lt $cols; $j++) {
            $v = $parts[$j]
            if ($v -eq "") { $arr[$i, $j] = $null } else { $arr[$i, $j] = $v }
        }
    }
    return $arr
}

function Write-TsvRows($ws, $path, $firstRow, $lastCol) {
    $lines = @(Get-Content -Path $path -Encoding UTF8 | Where-Object { $_ -ne "" })
    $r = $firstRow
    foreach ($line in $lines) {
        $parts = @($line -split "`t")
        $ws.Range("A" + $r + ":" + $lastCol + $r).Value2 = $parts
        $r++
    }
    return $r - 1
}

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($DST)
    $xl.CalculateFullRebuild()
    $sc = $wb.Worksheets.Item(1)      # 0-500分评分标准
    $sd = $wb.Worksheets.Item(2)      # 中信银行得分
    $sr = $wb.Worksheets.Item(3)      # 评分规则说明

    # ================= 1. 评分页：CET1 之后插入 CAR 23 行 =================
    $sc.Rows("97:119").Insert(-4121) | Out-Null        # xlDown
    foreach ($rng in @("D97:E119","F97:F119","K97:K119")) { $sc.Range($rng).NumberFormat = "@" }
    $last = Write-TsvRows $sc $TSVCAR 97 "M"
    Write-Output "  CAR rows written: 97..$last"
    $sc.Range("A97").Value2 = "CAR"
    $sc.Range("L97").Value2 = "越高越好"
    $sc.Range("M97").Value2 = "< 11.9% (10.5 监管 + 0.5 附加 + 0.9 本行)"
    # 合并区重建
    foreach ($a in @("A96:A119","L96:L119","M96:M119")) { try { $sc.Range($a).UnMerge() } catch {} }
    $sc.Range("A97:A119").Merge()
    $sc.Range("L97:L119").Merge()
    $sc.Range("M97:M119").Merge()
    Write-Output "CAR block inserted at rows 97-119"

    # ================= 2. 评分页：ROE 补 18-23 段（ROE 原 120-136，插入 6 行）=================
    $sc.Rows("137:142").Insert(-4121) | Out-Null
    foreach ($rng in @("D137:E142","F137:F142","K137:K142")) { $sc.Range($rng).NumberFormat = "@" }
    $last2 = Write-TsvRows $sc $TSVROE 137 "M"
    Write-Output "  ROE rows written: 137..$last2"
    foreach ($a in @("A120:A136","L120:L136","M120:M136")) { try { $sc.Range($a).UnMerge() } catch {} }
    $sc.Range("A120:A142").Merge()
    $sc.Range("L120:L142").Merge()
    $sc.Range("M120:M142").Merge()
    Write-Output "ROE segment 18-23 appended at rows 137-142"

    # ================= 2b. 峰值修正 + 得分重算 =================
    $sc.Range("I62").Value2 = 500        # EVE 子段12 下限分 = 峰值 500（消除 8.00% 处凹陷）
    $sc.Range("I154").Value2 = 500       # IBL 子段12 下限分 = 峰值 500（消除 20.00% 处凹陷）
    # 越高越好型指标：子段16 的上限分 480 -> 500，使「适度最优 500 分」真正可达
    foreach ($r in 20, 43, 89, 112, 135, 181) { $sc.Range("J" + $r).Value2 = 500 }

    # ================= 3. 标题 =================
    $sc.Range("A1").Value2 = "中信银行 8 指标 0-500 分评分规则 v13 (LCR / NSFR / EVE / CET1 / CAR / ROE / IBL / LR)"
    $sc.Range("A2").Value2 = "LCR 16% + NSFR 13% + EVE 12% + CET1 16% + CAR 10% + ROE 12% + IBL 11% + LR 10% = 100% | 0-500 分制 | 监管不达标 = 0 分"

    # ================= 4. 得分页：插入 CAR 行 =================
    $sd.Rows("9:9").Insert(-4121) | Out-Null
    $sd.Range("A9").Value2 = "CAR"
    $sd.Range("B9").Value2 = "< 11.9% (10.5 监管 + 0.5 附加 + 0.9 本行)"
    $sd.Range("C9").Value2 = "12.80%"
    $sd.Range("D9").Value2 = "🟢 安全"
    $sd.Range("E9").Value2 = 400
    $sd.Range("F9").Value2 = 0.1
    $sd.Range("H9").Value2 = "资本充足率 实测 12.80%"
    # 得分按 v13 档位表重算后写入（必须在插入 CAR 行之后，否则行序错位）
    $sclines = @(Get-Content -Path $TSVSCORE -Encoding UTF8 | Where-Object { $_ -ne "" })
    $i = 0
    for ($r = 5; $r -le 12; $r++) {
        $sp = @($sclines[$i] -split "`t")
        $sd.Cells.Item($r, 5).Value2 = [double]$sp[1]
        $i++
    }
    Write-Output "scores rewritten (8 indicators)"
    # 权重改数值 + 加权改公式
    $w = @(0.16, 0.13, 0.12, 0.16, 0.1, 0.12, 0.11, 0.1)
    for ($i = 0; $i -lt 8; $i++) {
        $r = 5 + $i
        $sd.Cells.Item($r, 6).Value2 = $w[$i]
        $sd.Cells.Item($r, 6).NumberFormat = "0%"
        $sd.Cells.Item($r, 7).Formula = "=E" + $r + "/500*F" + $r + "*100"
        $sd.Cells.Item($r, 7).NumberFormat = "0.00"
    }
    $sd.Range("A1").Value2 = "中信银行 8 指标 0-500 分实测得分 v13"
    $sd.Range("A2").Value2 = "LCR 16% + NSFR 13% + EVE 12% + CET1 16% + CAR 10% + ROE 12% + IBL 11% + LR 10% = 100% | 0-500 分制 | 监管不达标 = 0 分"
    # 综合得分 / 评级改真公式
    $sd.Range("A13").Value2 = "综合得分"
    $sd.Range("G13").Formula = "=SUM(G5:G12)"
    $sd.Range("G13").NumberFormat = '0.00"/100"'
    $sd.Range("H13").Formula = "=SUMPRODUCT(E5:E12,F5:F12)"
    $sd.Range("H13").NumberFormat = '0.00"/500"'
    $sd.Range("A14").Value2 = "综合评级"
    $sd.Range("G14").Formula = '=IF(G13>=90,"A+ 卓越",IF(G13>=85,"A 优秀",IF(G13>=80,"B+ 良好",IF(G13>=70,"B 中等",IF(G13>=60,"C 较弱","D 差")))))'
    $sd.Range("H14").Value2 = "满分 100 (500/500)"
    Write-Output "score sheet updated"

    # ================= 5. 规则说明页 =================
    $sr.Range("A1").Value2 = "v13 0-500 分评分规则 + 平滑性约束 + 8 指标说明"
    $sr.Range("A21").Value2 = "三、8 指标说明"
    $sr.Range("A33").Value2 = "五、v13 修正说明"
    $sr.Range("A34").Value2 = "1）得分页原沿用 v12b 档位表结果，与 v12c 档位表已不一致（如 LCR 得分 445.8 实际对应实测 148.29%，而实测值列为 147.29%），v13 已按档位表统一重算，全部指标得分下调 15~20 分"
    $sr.Range("A35").Value2 = "2）ROE 原仅 17 个档位（子段 1-17），实测值 >12% 时无任何区间匹配，打分引擎会抛「值不在任何段位区间内」异常；v13 补齐子段 18-23（12%-16% 过优减分 + ≥16% 极度过剩 300 分）"
    $sr.Range("A36").Value2 = "3）EVE / IBL 的适度最优单点（8.00% / 20.00%）原被子段 12 区间下界覆盖，引擎首个匹配规则下取不到 500 分且在峰值处形成 20 分凹陷；v13 将子段 12 的「区间下限分数」改为 500，峰值连续"
    $sr.Range("A37").Value2 = "4）新增 CAR 指标，权重 10%，红线 11.9%（10.5 监管 + 0.5 附加 + 0.9 本行），中信实测 12.80% 落在安全区，得 400 分，加权贡献 8.00 分"
    $sr.Range("A38").Value2 = "5）8 指标权重重新分配：LCR 16 / NSFR 13 / EVE 12 / CET1 16 / CAR 10 / ROE 12 / IBL 11 / LR 10 = 100%；资本类合计 26%（CET1 16 + CAR 10）"
    $sr.Range("A39").Value2 = "6）得分页 G 列（加权）、综合得分、评级改为活公式，改动实测值或得分后自动刷新"
    $sr.Range("A40").Value2 = "7）所有指标的「适度最优 500 分」单点（子段17）原被子段16 区间上界抢先匹配，引擎规则下永远取不到 500 分；v13 将子段16 的「区间上限分数」由 480 改为 500，峰值真正可达且曲线连续"
    foreach ($r in 33..40) {
        $sr.Range("A" + $r).Font.Size = 9
        $sr.Range("A" + $r).HorizontalAlignment = -4131
    }
    $sr.Range("A29:M29").Copy() | Out-Null
    $sr.Range("A31:M31").PasteSpecial(-4104) | Out-Null     # xlPasteFormats
    $sr.Range("A31").Value2 = "CAR 资本充足率"
    $sr.Range("B31").Value2 = "适度最优"
    $sr.Range("C31").Value2 = "< 11.9% (10.5 监管 + 0.5 附加 + 0.9 本行)"
    $sr.Range("D31").Value2 = "13-16%"
    $sr.Range("A6").Value2 = "不达标"
    $sr.Range("D6").Value2 = "LCR<120% / NSFR<100% / EVE>15% / CET1<8.7% / CAR<11.9%"
    $sr.Range("D7").Value2 = "LCR 120-128% / CET1 8.7-8.84% / EVE 12-15% / CAR 11.9-12.0%"
    $sr.Range("D8").Value2 = "LCR 128-140% / CET1 8.84-9% / NSFR 103-105% / CAR 12.0-12.2%"
    $sr.Range("D9").Value2 = "LCR 140-150% / CET1 9-10% / NSFR 105-107% / CAR 12.2-13.2%"
    Write-Output "rule sheet updated"

    $xl.CalculateFullRebuild()
    $wb.Save()
    Write-Output "saved: $DST"

    # ================= 6. 回读校验 =================
    Write-Output ""
    Write-Output "===== score sheet (rows 5-14) ====="
    for ($r = 5; $r -le 14; $r++) {
        $a = $sd.Cells.Item($r,1).Text
        $c = $sd.Cells.Item($r,3).Text
        $d = $sd.Cells.Item($r,4).Text
        $e = $sd.Cells.Item($r,5).Text
        $f = $sd.Cells.Item($r,6).Text
        $g = $sd.Cells.Item($r,7).Text
        $h = $sd.Cells.Item($r,8).Text
        Write-Output ("  {0,-10} {1,-9} {2,-8} {3,-8} {4,-6} {5,-8} {6}" -f $a,$c,$d,$e,$f,$g,$h)
    }
    Write-Output ""
    Write-Output "===== CAR block spot-check ====="
    foreach ($r in 97, 103, 110, 113, 119) {
        Write-Output ("  r{0}: {1} | seg={2} | {3}~{4} | {5} | score={6} | I={7} J={8} | {9}" -f `
            $r, $sc.Cells.Item($r,1).Text, $sc.Cells.Item($r,3).Text, $sc.Cells.Item($r,4).Text, $sc.Cells.Item($r,5).Text, `
            $sc.Cells.Item($r,6).Text, $sc.Cells.Item($r,7).Text, $sc.Cells.Item($r,9).Text, $sc.Cells.Item($r,10).Text, $sc.Cells.Item($r,2).Text)
    }
    Write-Output ""
    Write-Output "===== ROE block tail ====="
    foreach ($r in 136, 137, 138, 142) {
        Write-Output ("  r{0}: seg={1} | {2}~{3} | {4} | score={5} | I={6} J={7} | {8}" -f `
            $r, $sc.Cells.Item($r,3).Text, $sc.Cells.Item($r,4).Text, $sc.Cells.Item($r,5).Text, `
            $sc.Cells.Item($r,6).Text, $sc.Cells.Item($r,7).Text, $sc.Cells.Item($r,9).Text, $sc.Cells.Item($r,10).Text, $sc.Cells.Item($r,2).Text)
    }
    Write-Output ""
    Write-Output "===== block boundaries ====="
    for ($r = 5; $r -le 190; $r++) {
        $v = $sc.Cells.Item($r,1).Value2
        if ($v -is [string] -and $v -ne "" -and $v -ne $prev) { Write-Output ("  {0} @ row {1}" -f $v, $r); $prev = $v }
    }

    $wb.Close($false)
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
'''

def write_tsv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        for r in rows:
            f.write("\t".join("" if v is None else str(v) for v in r) + "\n")


tsv_car = r"C:\银行经营\PRCP\docs\_v13_car.tsv"
tsv_roe = r"C:\银行经营\PRCP\docs\_v13_roe.tsv"
write_tsv(tsv_car, CAR)
write_tsv(tsv_roe, ROE)
tsv_score = r"C://银行经营//PRCP//docs//_v13_score.tsv"
write_tsv(tsv_score, [[n, s] for n, s in SCORES])

assert "$TSVCAR" in PS and "$TSVROE" in PS and "$TSVSCORE" in PS, "TSV placeholder missing"
PS = PS.replace("$TSVCAR", tsv_car).replace("$TSVROE", tsv_roe).replace("$TSVSCORE", tsv_score)
assert "$TSVCAR" not in PS and "$TSVROE" not in PS and "$TSVSCORE" not in PS, "TSV placeholder not replaced"
out = r"C:\银行经营\PRCP\docs\build_score_standard_v13.ps1"
open(out, "w", encoding="utf-8-sig").write(PS)
print("已生成:", out)
print("CAR 段数:", len(CAR), " ROE 补段:", len(ROE))
