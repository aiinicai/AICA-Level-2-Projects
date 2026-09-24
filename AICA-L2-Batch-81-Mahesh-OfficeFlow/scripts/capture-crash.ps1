# Captures the real crash stack trace from a connected Android phone.
#
# Beats guessing: it prints the exact exception and line, which is usually enough to fix the
# problem in one pass instead of several.
#
# On the phone first:  Settings > About phone > tap "Build number" 7 times, then
#                      Settings > Developer options > USB debugging = ON.
# Plug it in by USB, accept the "Allow USB debugging?" prompt, then run:
#
#   powershell -ExecutionPolicy Bypass -File scripts\capture-crash.ps1

$ErrorActionPreference = "Continue"
$adb = "C:\Users\Admin\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$pkg = "com.aistudio.officeflow.tkxjmp"

if (-not (Test-Path $adb)) { Write-Host "adb not found at $adb"; exit 1 }

Write-Host "Waiting for a device (plug the phone in, unlock it, accept the USB debugging prompt)..."
& $adb wait-for-device
& $adb devices

Write-Host "`nClearing old logs and launching OfficeFlow..."
& $adb logcat -c
& $adb shell monkey -p $pkg -c android.intent.category.LAUNCHER 1 | Out-Null

Write-Host "Reproduce the crash now. Capturing for 25 seconds...`n"
$out = Join-Path $PSScriptRoot "crash-log.txt"
$job = Start-Job -ScriptBlock { param($adb,$out) & $adb logcat -v time *:E | Out-File -FilePath $out -Encoding utf8 } -ArgumentList $adb,$out
Start-Sleep -Seconds 25
Stop-Job $job -ErrorAction SilentlyContinue | Out-Null
Remove-Job $job -Force -ErrorAction SilentlyContinue | Out-Null

Write-Host "--- the interesting part ---`n"
if (Test-Path $out) {
  $lines = Get-Content $out
  $hit = $lines | Select-String -Pattern 'FATAL EXCEPTION|AndroidRuntime|com\.example|officeflow' -Context 0,25 | Select-Object -First 3
  if ($hit) { $hit | ForEach-Object { $_.Line; $_.Context.PostContext } } else { $lines | Select-Object -Last 40 }
  Write-Host "`nFull log saved to: $out"
} else {
  Write-Host "No log captured. Is USB debugging enabled and the phone unlocked?"
}
