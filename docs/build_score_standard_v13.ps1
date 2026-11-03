$ErrorActionPreference = "Stop"
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
    $last = Write-TsvRows $sc C:\银行经营\PRCP\docs\_v13_car.tsv 97 "M"
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
    $last2 = Write-TsvRows $sc C:\银行经营\PRCP\docs\_v13_roe.tsv 137 "M"
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
    $sclines = @(Get-Content -Path C://银行经营//PRCP//docs//_v13_score.tsv -Encoding UTF8 | Where-Object { $_ -ne "" })
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
