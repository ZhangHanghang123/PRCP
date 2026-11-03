$ErrorActionPreference = "Stop"
$path = (Get-ChildItem -Path "C:\*\PRCP\docs\v2\DeltaEVE_*v2_*.xlsx" | Select-Object -First 1).FullName
Write-Output "FILE: $path"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFullRebuild()
    Write-Output ("SHEETS: " + (($wb.Worksheets | ForEach-Object { $_.Name }) -join " | "))

    Write-Output ""
    Write-Output "===== full-workbook error scan ====="
    $errCount = 0
    foreach ($sh in $wb.Worksheets) {
        $ur = $sh.UsedRange
        $vals = $ur.Value2
        $r0 = $ur.Row; $c0 = $ur.Column
        for ($i = 1; $i -le $ur.Rows.Count; $i++) {
            for ($j = 1; $j -le $ur.Columns.Count; $j++) {
                $v = $vals[$i, $j]
                if ($v -is [int] -and $v -lt -2000000000) {
                    $errCount++
                    if ($errCount -le 15) {
                        $addr = $sh.Cells.Item($r0 + $i - 1, $c0 + $j - 1)
                        Write-Output ("  ERR {0}!{1}  formula={2}" -f $sh.Name, $addr.Address(), $addr.Formula)
                    }
                }
            }
        }
    }
    Write-Output "total error cells = $errCount"

    Write-Output ""
    Write-Output "===== sheet3 (PV matrix) totals ====="
    $s4 = $wb.Worksheets.Item(4)
    foreach ($a in @("E28","E29","E30","D28")) {
        Write-Output ("  s4!{0,-5} text={1,-22} value={2}" -f $a, $s4.Range($a).Text, $s4.Range($a).Value2)
    }

    Write-Output ""
    Write-Output "===== sheet5 (multi-basis summary) ====="
    $s5 = $wb.Worksheets.Item(5)
    Write-Output "  row : code | assetPV | liabPV | EVE | dEVE | EVE_PCT | EVE_ABS | AST | DEP | IAR | dNII | dNII%"
    for ($r = 4; $r -le 10; $r++) {
        $a = $s5.Cells.Item($r, 1).Value2
        $c = $s5.Cells.Item($r, 3).Value2
        $d = $s5.Cells.Item($r, 4).Value2
        $e = $s5.Cells.Item($r, 5).Value2
        $f = $s5.Cells.Item($r, 6).Value2
        $g = $s5.Cells.Item($r, 7).Value2
        $h = $s5.Cells.Item($r, 8).Value2
        $ii = $s5.Cells.Item($r, 9).Value2
        $jj = $s5.Cells.Item($r, 10).Value2
        $kk = $s5.Cells.Item($r, 11).Value2
        $ll = $s5.Cells.Item($r, 12).Value2
        $mm = $s5.Cells.Item($r, 13).Value2
        Write-Output ("  {0,-16} {1,12:N2} {2,12:N2} {3,12:N2} {4,12:N2} {5,10:P2} {6,10:P2} {7,9:P2} {8,9:P2} {9,9:P2} {10,10:N2} {11,9:P2}" -f $a, $c, $d, $e, $f, $g, $h, $ii, $jj, $kk, $ll, $mm)
    }
    Write-Output "  worst-case row 13:"
    foreach ($col in @("B","F","G","H","I","J","K","L")) {
        Write-Output ("    {0}13 = {1}" -f $col, $s5.Range($col + "13").Text)
    }

    Write-Output ""
    Write-Output "===== sheet6 (NII & duration) ====="
    $s6 = $wb.Worksheets.Item(6)
    foreach ($a in @("B5","B6","B7","B8","B9","B10","B11","B14")) {
        Write-Output ("  s6!{0,-5} text={1,-22} value={2}" -f $a, $s6.Range($a).Text, $s6.Range($a).Value2)
    }
    Write-Output "  dNII rows:"
    for ($r = 17; $r -le 23; $r++) {
        Write-Output ("    {0,-16} dNII={1,12:N2}  pct={2,10:P2}  dr1Y={3,8:N1}" -f $s6.Cells.Item($r,1).Value2, $s6.Cells.Item($r,3).Value2, $s6.Cells.Item($r,4).Value2, $s6.Cells.Item($r,5).Value2)
    }

    Write-Output ""
    Write-Output "===== save (embed cached values) ====="
    $wb.Save()
    Write-Output "saved."
    $wb.Close($false)
} finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
