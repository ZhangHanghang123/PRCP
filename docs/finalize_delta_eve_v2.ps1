$ErrorActionPreference = "Stop"
$path = (Get-ChildItem -Path "C:\*\PRCP\docs\v2\DeltaEVE_*v2_*.xlsx" | Select-Object -First 1).FullName
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFullRebuild()
    $s6 = $wb.Worksheets.Item(6)
    $s5 = $wb.Worksheets.Item(5)

    Write-Output ("s6 col B width BEFORE = {0}" -f $s6.Columns.Item("B").ColumnWidth)
    Write-Output ("s6 B11 text = {0} | numberFormat = {1}" -f $s6.Range("B11").Text, $s6.Range("B11").NumberFormat)
    Write-Output ("s5 row11 health = {0}" -f $s5.Range("B11").Text)

    # 修列宽
    $s6.Columns.Item("B").ColumnWidth = 24
    $s6.Columns.Item("A").ColumnWidth = 32
    $s6.Columns.Item("D").ColumnWidth = 62
    $s5.Columns.Item("A").ColumnWidth = 16
    $s5.Columns.Item("B").ColumnWidth = 14
    foreach ($c in 3..15) { $s5.Columns.Item($c).ColumnWidth = 15 }

    $xl.CalculateFullRebuild()
    Write-Output ("s6 B11 text AFTER = {0}" -f $s6.Range("B11").Text)

    # 全表错误复扫
    $errCount = 0
    foreach ($sh in $wb.Worksheets) {
        $ur = $sh.UsedRange; $vals = $ur.Value2; $r0 = $ur.Row; $c0 = $ur.Column
        for ($i = 1; $i -le $ur.Rows.Count; $i++) {
            for ($j = 1; $j -le $ur.Columns.Count; $j++) {
                $v = $vals[$i, $j]
                if ($v -is [int] -and $v -lt -2000000000) { $errCount++ }
            }
        }
    }
    Write-Output "total error cells = $errCount"
    $wb.Save()
    Write-Output "saved."
    $wb.Close($false)
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }

# ---------- WPS 复核 ----------
Write-Output ""
Write-Output "########## WPS re-check ##########"
$app = New-Object -ComObject Ket.Application
$app.Visible = $false; $app.DisplayAlerts = $false
try {
    $wb2 = $app.Workbooks.Open($path)
    $w5 = $wb2.Worksheets.Item(5); $w6 = $wb2.Worksheets.Item(6)
    $line = "WPS s5 worst=" + $w5.Range("B13").Text + " dEVE=" + $w5.Range("F13").Text + " AST=" + $w5.Range("I13").Text + " DEP=" + $w5.Range("J13").Text + " IAR=" + $w5.Range("K13").Text
    Write-Output $line
    Write-Output ("WPS s5 health = " + $w5.Range("B11").Text)
    $l2 = "WPS s6 D_A=" + $w6.Range("B8").Text + " D_L=" + $w6.Range("B9").Text + " DGAP=" + $w6.Range("B10").Text + " NII=" + $w6.Range("B14").Text
    Write-Output $l2
    $wb2.Close($false)
} finally { $app.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null }
