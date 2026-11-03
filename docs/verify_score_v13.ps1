$ErrorActionPreference = "Stop"
$path = "C:\银行经营\PRCP\docs\v2\评分标准_v13_8指标_含CAR.xlsx"
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Open($path)
    $xl.CalculateFullRebuild()
    Write-Output "===== full-workbook error scan ====="
    $err = 0
    foreach ($sh in $wb.Worksheets) {
        $ur = $sh.UsedRange; $vals = $ur.Value2; $r0 = $ur.Row; $c0 = $ur.Column
        for ($i = 1; $i -le $ur.Rows.Count; $i++) {
            for ($j = 1; $j -le $ur.Columns.Count; $j++) {
                $v = $vals[$i, $j]
                if ($v -is [int] -and $v -lt -2000000000) {
                    $err++
                    if ($err -le 10) { Write-Output ("  ERR {0}!{1}" -f $sh.Name, $sh.Cells.Item($r0+$i-1,$c0+$j-1).Address()) }
                }
            }
        }
    }
    Write-Output "total error cells = $err"
    $sd = $wb.Worksheets.Item(2)
    Write-Output ""
    Write-Output "===== score sheet ====="
    for ($r = 5; $r -le 14; $r++) {
        $a = $sd.Cells.Item($r,1).Text; $c = $sd.Cells.Item($r,3).Text; $d = $sd.Cells.Item($r,4).Text
        $e = $sd.Cells.Item($r,5).Text; $f = $sd.Cells.Item($r,6).Text; $g = $sd.Cells.Item($r,7).Text
        $h = $sd.Cells.Item($r,8).Text
        Write-Output ("  {0,-10} {1,-9} {2,-9} {3,-8} {4,-7} {5,-8} {6}" -f $a,$c,$d,$e,$f,$g,$h)
    }
    Write-Output ("  G13 formula = " + $sd.Range("G13").Formula)
    Write-Output ("  H13 formula = " + $sd.Range("H13").Formula)
    Write-Output ("  G14 formula = " + $sd.Range("G14").Formula)
    $wb.Close($false)
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }

Write-Output ""
Write-Output "########## WPS re-check ##########"
$app = New-Object -ComObject Ket.Application
$app.Visible = $false; $app.DisplayAlerts = $false
try {
    $wb2 = $app.Workbooks.Open($path)
    $w2 = $wb2.Worksheets.Item(2)
    Write-Output ("WPS CAR row: " + $w2.Range("A9").Text + " | " + $w2.Range("C9").Text + " | " + $w2.Range("D9").Text + " | score=" + $w2.Range("E9").Text + " | w=" + $w2.Range("F9").Text + " | wtd=" + $w2.Range("G9").Text)
    Write-Output ("WPS total: " + $w2.Range("G13").Text + "  " + $w2.Range("H13").Text + "  rating=" + $w2.Range("G14").Text)
    $wb2.Close($false)
} finally { $app.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null }
