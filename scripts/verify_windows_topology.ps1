# Blou — Phase 0 Verification Script: Windows Display Topology Auditor
# Run this inside the RDP session to verify that Windows created 3 virtual monitors.

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Blou Phase 0: Windows Display Topology Verifier" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Add-Type -AssemblyName System.Windows.Forms

$screens = [System.Windows.Forms.Screen]::AllScreens
$count = $screens.Count

Write-Host "`n[+] Detected Active Displays: $count" -ForegroundColor $(if ($count -ge 3) { "Green" } else { "Yellow" })

for ($i = 0; $i -lt $count; $i++) {
    $s = $screens[$i]
    $isPrimary = if ($s.Primary) { "[PRIMARY]" } else { "         " }
    Write-Host ("  Display {0} {1}: Bounds={2} WorkingArea={3}" -f $i, $isPrimary, $s.Bounds, $s.WorkingArea)
}

# Check virtual screen bounding rectangle
$vsLeft   = [System.Windows.Forms.SystemInformation]::VirtualScreen.Left
$vsTop    = [System.Windows.Forms.SystemInformation]::VirtualScreen.Top
$vsWidth  = [System.Windows.Forms.SystemInformation]::VirtualScreen.Width
$vsHeight = [System.Windows.Forms.SystemInformation]::VirtualScreen.Height

Write-Host "`n[+] Combined Virtual Desktop Geometry:" -ForegroundColor Cyan
Write-Host "    Origin : ($vsLeft, $vsTop)"
Write-Host "    Width  : $vsWidth px"
Write-Host "    Height : $vsHeight px"

# Verdict
Write-Host "`n----------------------------------------------------------"
if ($count -ge 3 -and $vsWidth -ge 5760) {
    Write-Host ">>> PHASE 0 SUCCESS: The layout lie is accepted by Windows! <<<" -ForegroundColor Green
    Write-Host "Windows initialized 3 distinct monitors with 5760px desktop." -ForegroundColor Green
} elseif ($count -ge 3) {
    Write-Host ">>> PHASE 0 PASS: Windows reports 3 displays ($count total)." -ForegroundColor Green
} else {
    Write-Host ">>> PHASE 0 INCOMPLETE: Expected >= 3 displays, found $count. <<<" -ForegroundColor Red
}
Write-Host "----------------------------------------------------------`n"
