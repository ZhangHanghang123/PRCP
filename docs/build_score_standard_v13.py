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

PS = r'''$ErrorActionPreference = "Stop"
$SRC = "C:\银行经营\PRCP\docs\v2\评分标准_v12c.xlsx"
$DST = "C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
Copy-Item $SRC $DST -Force

$CAR = ConvertFrom-Json @'
__CAR__
'@
$ROE = ConvertFrom-Json @'
__ROE__
'@

function To2D($rows, $cols) {
    $arr = New-Object 'object[,]' $rows.Count, $cols
    for ($i = 0; $i -lt $rows.Count; $i++) {
        for ($j = 0; $j -lt $cols; $j++) {
            $v = $rows[$i][$j]
            if ($null -eq $v) { $arr[$i, $j] = $null } else { $arr[$i, $j] = $v }
        }
    }
    return $arr
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
    $data = To2D $CAR 13
    $sc.Range("A97:M119").Value2 = $data
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
    $rdata = To2D $ROE 13
    $sc.Range("A137:M142").Value2 = $rdata
    foreach ($a in @("A120:A136","L120:L136","M120:M136")) { try { $sc.Range($a).UnMerge() } catch {} }
    $sc.Range("A120:A142").Merge()
    $sc.Range("L120:L142").Merge()
    $sc.Range("M120:M142").Merge()
    Write-Output "ROE segment 18-23 appended at rows 137-142"

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
    # 权重改数值 + 加权改公式
    $w = @(0.16, 0.13, 0.12, 0.16, 0.1, 0.12, 0.11, 0.1)
    for ($i = 0; $i -lt 8; $i++) {
        $r = 5 + $i
        $sd.Cells.Item($r, 6).Value2 = $w[$i]
        $sd.Cells.Item($r, 6).NumberFormat = "0%"
        $sd.Cells.Item($r, 7).Formula = "=E" + $r + "/500*F" + $r
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

PS = PS.replace("__CAR__", json.dumps(CAR, ensure_ascii=False))
PS = PS.replace("__ROE__", json.dumps(ROE, ensure_ascii=False))
out = r"C:\银行经营\PRCP\docs\build_score_standard_v13.ps1"
open(out, "w", encoding="utf-8-sig").write(PS)
print("已生成:", out)
print("CAR 段数:", len(CAR), " ROE 补段:", len(ROE))
