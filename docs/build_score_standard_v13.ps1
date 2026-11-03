$ErrorActionPreference = "Stop"
$SRC = "C:\银行经营\PRCP\docs\v2\评分标准_v12c.xlsx"
$DST = "C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
Copy-Item $SRC $DST -Force

$CAR = ConvertFrom-Json @'
[[null, "🔴 不达标", 1, "0.00%", "11.90%", "11.90pp", 0, "不达标 (≤红线)", 0, 0, "6.85pp"], [null, "🟠 危险", 2, "11.9000%", "11.9200%", "0.0200pp", 15, "危险 0-150 分 (插值)", 0, 15, "0.89pp"], [null, "🟠 危险", 3, "11.9200%", "11.9400%", "0.0200pp", 45, "危险 0-150 分 (插值)", 15, 45, "0.87pp"], [null, "🟠 危险", 4, "11.9400%", "11.9600%", "0.0200pp", 75, "危险 0-150 分 (插值)", 45, 75, "0.85pp"], [null, "🟠 危险", 5, "11.9600%", "11.9800%", "0.0200pp", 105, "危险 0-150 分 (插值)", 75, 105, "0.83pp"], [null, "🟠 危险", 6, "11.9800%", "12.0000%", "0.0200pp", 135, "危险 0-150 分 (插值)", 105, 135, "0.81pp"], [null, "🟡 预警", 7, "12.0000%", "12.0400%", "0.0400pp", 165, "预警 150-300 分 (插值)", 135, 165, "0.78pp"], [null, "🟡 预警", 8, "12.0400%", "12.0800%", "0.0400pp", 195, "预警 150-300 分 (插值)", 165, 195, "0.74pp"], [null, "🟡 预警", 9, "12.0800%", "12.1200%", "0.0400pp", 225, "预警 150-300 分 (插值)", 195, 225, "0.70pp"], [null, "🟡 预警", 10, "12.1200%", "12.1600%", "0.0400pp", 255, "预警 150-300 分 (插值)", 225, 255, "0.66pp"], [null, "🟡 预警", 11, "12.1600%", "12.2000%", "0.0400pp", 285, "预警 150-300 分 (插值)", 255, 285, "0.62pp"], [null, "🟢 安全", 12, "12.2000%", "12.4000%", "0.2000pp", 320, "安全 300-500 分 (插值)", 285, 320, "0.50pp"], [null, "🟢 安全", 13, "12.4000%", "12.6000%", "0.2000pp", 360, "安全 300-500 分 (插值)", 320, 360, "0.30pp"], [null, "🟢 安全", 14, "12.6000%", "12.8000%", "0.2000pp", 400, "安全 300-500 分 (插值)", 360, 400, "0.10pp"], [null, "🟢 安全", 15, "12.8000%", "13.0000%", "0.2000pp", 440, "安全 300-500 分 (插值)", 400, 440, "0.10pp"], [null, "🟢 安全", 16, "13.0000%", "13.2000%", "0.2000pp", 480, "安全 300-500 分 (插值)", 440, 480, "0.30pp"], [null, "🟢🟢 满分", 17, "13.2000%", "13.2000%", "0.0000pp", 500, "⭐适度最优 500 分", 500, 500, "0.40pp"], [null, "🟢 安全", 18, "13.2000%", "13.8000%", "0.6000pp", 480, "过优 500→减分 (插值)", 500, 480, "0.70pp"], [null, "🟢 安全", 19, "13.8000%", "14.4000%", "0.6000pp", 440, "过优 500→减分 (插值)", 480, 440, "1.30pp"], [null, "🟢 安全", 20, "14.4000%", "15.0000%", "0.6000pp", 400, "过优 500→减分 (插值)", 440, 400, "1.90pp"], [null, "🟢 安全", 21, "15.0000%", "15.6000%", "0.6000pp", 360, "过优 500→减分 (插值)", 400, 360, "2.50pp"], [null, "🟢 安全", 22, "15.6000%", "16.2000%", "0.6000pp", 320, "过优 500→减分 (插值)", 360, 320, "3.10pp"], [null, "🟢 安全", 23, "16.20%", "999.00%", "982.80pp", 300, "极度过剩 300 分", 320, 300, "494.80pp"]]
'@
$ROE = ConvertFrom-Json @'
[[null, "🟢 安全", 18, "12.0000%", "12.8000%", "0.8000pp", 480, "过优 500→减分 (插值)", 500, 480, "2.79pp"], [null, "🟢 安全", 19, "12.8000%", "13.6000%", "0.8000pp", 440, "过优 500→减分 (插值)", 480, 440, "3.59pp"], [null, "🟢 安全", 20, "13.6000%", "14.4000%", "0.8000pp", 400, "过优 500→减分 (插值)", 440, 400, "4.39pp"], [null, "🟢 安全", 21, "14.4000%", "15.2000%", "0.8000pp", 360, "过优 500→减分 (插值)", 400, 360, "5.19pp"], [null, "🟢 安全", 22, "15.2000%", "16.0000%", "0.8000pp", 320, "过优 500→减分 (插值)", 360, 320, "5.99pp"], [null, "🟢 安全", 23, "16.00%", "999.00%", "983.00pp", 300, "极度过剩 300 分", 320, 300, "497.89pp"]]
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
    $sd.Range("D9").Value2 = [char]0x1F7E2 + " 安全"
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
