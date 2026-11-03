$ErrorActionPreference = "Stop"
$path = (Get-ChildItem -Path "C:\*\PRCP\docs\v2\DeltaEVE_*v3_*.xlsx" | Select-Object -First 1).FullName
Write-Output "FILE: $path"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFullRebuild()
    Write-Output ("SHEETS: " + (($wb.Worksheets | ForEach-Object { $_.Name }) -join " | "))

    Write-Output ""
    Write-Output "===== full-workbook error scan ====="
    $errCount = 0
    foreach ($sh in $wb.Worksheets) {
        $ur = $sh.UsedRange; $vals = $ur.Value2; $r0 = $ur.Row; $c0 = $ur.Column
        for ($i = 1; $i -le $ur.Rows.Count; $i++) {
            for ($j = 1; $j -le $ur.Columns.Count; $j++) {
                $v = $vals[$i, $j]
                if ($v -is [int] -and $v -lt -2000000000) {
                    $errCount++
                    if ($errCount -le 15) {
                        $addr = $sh.Cells.Item($r0 + $i - 1, $c0 + $j - 1)
                        Write-Output ("  ERR {0}!{1} formula={2}" -f $sh.Name, $addr.Address(), $addr.Formula)
                    }
                }
            }
        }
    }
    Write-Output "total error cells = $errCount"

    $s4 = $wb.Worksheets.Item(4)
    $s5 = $wb.Worksheets.Item(5)
    $s1 = $wb.Worksheets.Item(1)
    Write-Output ""
    Write-Output "===== sheet4 totals ====="
    Write-Output ("  E28(asset)=" + $s4.Range("E28").Text + "  E29(liab)=" + $s4.Range("E29").Text + "  E30(EVE)=" + $s4.Range("E30").Text)

    Write-Output ""
    Write-Output "===== sheet5 EVE_ABS ====="
    Write-Output "  code | assetPV | liabPV | EVE | dEVE | |dEVE| | EVE_ABS | judge"
    for ($r = 4; $r -le 10; $r++) {
        $a = $s5.Cells.Item($r, 1).Text
        $c = $s5.Cells.Item($r, 3).Text
        $d = $s5.Cells.Item($r, 4).Text
        $e = $s5.Cells.Item($r, 5).Text
        $f = $s5.Cells.Item($r, 6).Text
        $g = $s5.Cells.Item($r, 7).Text
        $h = $s5.Cells.Item($r, 8).Text
        $ii = $s5.Cells.Item($r, 9).Text
        Write-Output ("  {0,-15} {1,14} {2,14} {3,14} {4,14} {5,14} {6,12} {7}" -f $a,$c,$d,$e,$f,$g,$h,$ii)
    }
    Write-Output ("  worst: " + $s5.Range("B13").Text + " | dEVE=" + $s5.Range("F13").Text + " | |dEVE|=" + $s5.Range("G13").Text + " | EVE_ABS=" + $s5.Range("H13").Text + " | " + $s5.Range("I13").Text)
    Write-Output ("  health: " + $s5.Range("B11").Text)

    Write-Output ""
    Write-Output "===== threshold function test ====="
    $s1.Range("B23").Value2 = 100
    $xl.CalculateFullRebuild()
    Write-Output ("  threshold=100 -> judge(r5)=" + $s5.Range("I5").Text + "  judge(r13)=" + $s5.Range("I13").Text)
    $s1.Range("B23").Value2 = 1
    $xl.CalculateFullRebuild()
    Write-Output ("  threshold=1   -> judge(r5)=" + $s5.Range("I5").Text + "  judge(r13)=" + $s5.Range("I13").Text)
    $s1.Range("B23").ClearContents() | Out-Null
    $xl.CalculateFullRebuild()
    Write-Output ("  threshold=empty -> judge(r5)=" + $s5.Range("I5").Text + "  judge(r13)=" + $s5.Range("I13").Text)

    Write-Output ""
    Write-Output "===== save ====="
    $wb.Save()
    Write-Output "saved."
    $wb.Close($false)
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }

Write-Output ""
Write-Output "########## WPS re-check ##########"
$app = New-Object -ComObject Ket.Application
$app.Visible = $false; $app.DisplayAlerts = $false
try {
    $wb2 = $app.Workbooks.Open($path)
    $w5 = $wb2.Worksheets.Item(5)
    $line = "WPS worst=" + $w5.Range("B13").Text + " dEVE=" + $w5.Range("F13").Text + " EVE_ABS=" + $w5.Range("H13").Text + " judge=" + $w5.Range("I13").Text
    Write-Output $line
    Write-Output ("WPS health: " + $w5.Range("B11").Text)
    Write-Output ("WPS parallel_up row: dEVE=" + $w5.Range("F5").Text + " EVE_ABS=" + $w5.Range("H5").Text)
    $wb2.Close($false)
} finally { $app.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null }
