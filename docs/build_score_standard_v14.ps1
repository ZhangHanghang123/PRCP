$ErrorActionPreference = "Stop"
$SRC = "C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
$DST = "C:\银行经营\PRCP\docs\v2\评分标准_v14_锚点重标定.xlsx"

$TSV_SEG  = "C:\银行经营\PRCP\docs\_v14_segments.tsv"
$TSV_PAGE = "C:\银行经营\PRCP\docs\_v14_scorepage.tsv"
$TSV_RULE = "C:\银行经营\PRCP\docs\_v14_rule.tsv"
$TSV_TOTAL = "C:\银行经营\PRCP\docs\_v14_total.tsv"

# Backup existing target
if (Test-Path $DST) {
    $bak = ($DST -replace "\.xlsx$", "") + ".bak-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".xlsx"
    Copy-Item $DST $bak -Force
    Write-Output "backup -> $bak"
}
Copy-Item $SRC $DST -Force

function Read-Tsv($path) {
    $lines = @(Get-Content -Path $path -Encoding UTF8 | Where-Object { $_ -ne "" })
    $out = @()
    foreach ($line in $lines) {
        $parts = @($line -split "`t")
        $out += ,$parts
    }
    return $out
}

function Write-TsvRows($ws, $path, $firstRow, $lastColumnLetter, $ncols) {
    $rows = Read-Tsv $path
    $r = $firstRow
    foreach ($parts in $rows) {
        $vals = @($parts)
        while ($vals.Count -lt $ncols) { $vals += "" }
        $ws.Range("A" + $r + ":" + $lastColumnLetter + $r).Value2 = $vals
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
    $sc = $wb.Worksheets.Item(1)
    $sd = $wb.Worksheets.Item(2)
    $sr = $wb.Worksheets.Item(3)

    # ---- 1. Segment table: unmerge, clear, rewrite 184 rows ----
    $blocks = @("5:27","28:50","51:73","74:96","97:119","120:142","143:165","166:188")
    foreach ($b in $blocks) {
        $p = $b -split ":"
        $s = [int]$p[0]; $e = [int]$p[1]
        foreach ($col in @("A","L","M")) {
            try { $sc.Range($col + $s + ":" + $col + $e).UnMerge() } catch {}
        }
    }
    $sc.Range("A5:M188").ClearContents()
    $sc.Range("D5:E188").NumberFormat = "0.0000%"
    $sc.Range("F5:F188").NumberFormat = "@"
    $sc.Range("K5:K188").NumberFormat = "@"
    $last = Write-TsvRows $sc $TSV_SEG 5 "M" 13
    Write-Output "segment table rows 5..$last"
    if ($last -ne 188) { throw "segment row count mismatch: expect 188 got $last" }

    foreach ($b in $blocks) {
        $p = $b -split ":"
        $s = [int]$p[0]; $e = [int]$p[1]
        $sc.Range("A" + $s + ":A" + $e).Merge()
        $sc.Range("L" + $s + ":L" + $e).Merge()
        $sc.Range("M" + $s + ":M" + $e).Merge()
    }

    # ---- 2. Titles (from rule tsv) ----
    $rule = Read-Tsv $TSV_RULE
    $gr = @()
    foreach ($row in $rule) {
        $tag = $row[0]
        if ($tag -eq "__TITLE__") { $sr.Range("A1").Value2 = $row[1] }
        if ($tag -eq "__T1__") { $sc.Range("A1").Value2 = $row[1] }
        if ($tag -eq "__T2__") { $sc.Range("A2").Value2 = $row[1] }
        if ($tag -eq "__T3__") { $sd.Range("A1").Value2 = $row[1] }
        if ($tag -eq "__T4__") { $sd.Range("A2").Value2 = $row[1] }
        if ($tag -eq "__GRADE__") { $gr = @($row[1], $row[2], $row[3], $row[4], $row[5], $row[6]) }
    }

    # ---- 3. Score page rows 5-12 ----
    $sd.Rows("5:12").ClearContents()
    $sd.Range("C5:C12").NumberFormat = "0.00%"
    $sd.Range("E5:E12").NumberFormat = "0.00"
    $sd.Range("F5:F12").NumberFormat = "0%"
    $lastP = Write-TsvRows $sd $TSV_PAGE 5 "H" 8
    Write-Output "score page rows 5..$lastP"
    for ($r = 5; $r -le 12; $r++) {
        $sd.Cells.Item($r,7).Formula = "=E" + $r + "/500*F" + $r + "*100"
        $sd.Cells.Item($r,7).NumberFormat = "0.00"
    }
    $tot = Read-Tsv $TSV_TOTAL
    $sd.Range("A13").Value2 = $tot[0][0]
    $sd.Range("G13").Formula = "=SUM(G5:G12)"
    $sd.Range("G13").NumberFormat = '0.00"/100"'
    $sd.Range("H13").Formula = "=SUMPRODUCT(E5:E12,F5:F12)"
    $sd.Range("H13").NumberFormat = '0.00"/500"'
    $sd.Range("A14").Value2 = $tot[1][0]
    $sd.Range("G14").Formula = '=IF(G13>=90,"' + $gr[0] + '",IF(G13>=85,"' + $gr[1] + '",IF(G13>=80,"' + $gr[2] + '",IF(G13>=70,"' + $gr[3] + '",IF(G13>=60,"' + $gr[4] + '","' + $gr[5] + '")))))'
    $sd.Range("H14").Value2 = $tot[2][0]

    # ---- 4. Rule sheet ----
    foreach ($row in $rule) {
        $tag = $row[0]
        switch ($tag) {
            "__D6__" { $sr.Range("A6").Value2 = $row[1]; $sr.Range("B6").Value2 = $row[2]; $sr.Range("C6").Value2 = $row[3]; $sr.Range("D6").Value2 = $row[4] }
            "__D7__" { $sr.Range("A7").Value2 = $row[1]; $sr.Range("B7").Value2 = $row[2]; $sr.Range("C7").Value2 = $row[3]; $sr.Range("D7").Value2 = $row[4] }
            "__D8__" { $sr.Range("A8").Value2 = $row[1]; $sr.Range("B8").Value2 = $row[2]; $sr.Range("C8").Value2 = $row[3]; $sr.Range("D8").Value2 = $row[4] }
            "__D9__" { $sr.Range("A9").Value2 = $row[1]; $sr.Range("B9").Value2 = $row[2]; $sr.Range("C9").Value2 = $row[3]; $sr.Range("D9").Value2 = $row[4] }
            "__A21__" { $sr.Range("A21").Value2 = $row[1] }
            "__INDHDR__" { $sr.Range("A23").Value2 = $row[1]; $sr.Range("B23").Value2 = $row[2]; $sr.Range("C23").Value2 = $row[3]; $sr.Range("D23").Value2 = $row[4] }
            "__IND__" {
                $n = [int]$row[1]
                $r = 24 + $n
                $sr.Cells.Item($r,1).Value2 = $row[2]
                $sr.Cells.Item($r,2).Value2 = $row[3]
                $sr.Cells.Item($r,3).Value2 = $row[4]
                $sr.Cells.Item($r,4).Value2 = $row[5]
            }
            "__X__" { }
            "__A33__" { $sr.Range("A33").Value2 = $row[1] }
            "__NOTE__" {
                $r = [int]$row[1]
                $sr.Range("A" + $r).Value2 = $row[2]
                $sr.Range("A" + $r).Font.Size = 9
                $sr.Range("A" + $r).HorizontalAlignment = -4131
            }
        }
    }
    Write-Output "rule sheet updated"

    $xl.CalculateFullRebuild()
    $wb.Save()
    Write-Output "saved: $DST"

    # ---- 5. Read-back verification ----
    Write-Output ""
    Write-Output "===== score sheet rows 5-14 ====="
    for ($r = 5; $r -le 14; $r++) {
        Write-Output ("  {0,-10} {1,-9} {2,-10} {3,-8} {4,-6} {5,-8} {6}" -f `
            $sd.Cells.Item($r,1).Text, $sd.Cells.Item($r,3).Text, $sd.Cells.Item($r,4).Text, `
            $sd.Cells.Item($r,5).Text, $sd.Cells.Item($r,6).Text, $sd.Cells.Item($r,7).Text, $sd.Cells.Item($r,8).Text)
    }
    Write-Output ""
    Write-Output "===== segment spot-check ====="
    foreach ($r in 5, 6, 16, 21, 22, 27, 28, 44, 50, 51, 67, 73, 74, 90, 96, 97, 113, 119, 120, 136, 142, 143, 159, 165, 166, 182, 188) {
        Write-Output ("  r{0,-4} seg={1,-3} {2,-10} {3,-11} {4,-11} score={5,-7} I={6,-6} J={7,-6} {8}" -f `
            $r, $sc.Cells.Item($r,3).Text, $sc.Cells.Item($r,2).Text, $sc.Cells.Item($r,4).Text, `
            $sc.Cells.Item($r,5).Text, $sc.Cells.Item($r,7).Text, $sc.Cells.Item($r,9).Text, `
            $sc.Cells.Item($r,10).Text, $sc.Cells.Item($r,8).Text)
    }
    Write-Output ""
    Write-Output "===== KPI block boundaries ====="
    $prev = ""
    for ($r = 5; $r -le 188; $r++) {
        $v = $sc.Cells.Item($r,1).Value2
        if ($v -is [string] -and $v -ne "" -and $v -ne $prev) {
            Write-Output ("  {0,-6} @ row {1}" -f $v, $r); $prev = $v
        }
    }
    Write-Output ""
    Write-Output "===== error scan ====="
    $errCnt = 0
    foreach ($ws in @($sc, $sd, $sr)) {
        $ur = $ws.UsedRange
        $f = 0
        foreach ($e in @("#VALUE!","#REF!","#DIV/0!","#N/A","#NAME?","#NULL!")) {
            $f += $ws.Application.WorksheetFunction.CountIf($ur, $e)
        }
        Write-Output ("  {0}: {1}" -f $ws.Name, $f)
        $errCnt += $f
    }
    Write-Output ("  TOTAL ERRORS: {0}" -f $errCnt)

    $wb.Close($false)
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
