param(
    [string]$EvidencePath = "$PSScriptRoot\windows_release_evidence.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
if ($env:OS -ne "Windows_NT") { throw "Clean-machine acceptance must run on Windows." }
if (-not (Test-Path $EvidencePath)) { throw "Evidence file not found: $EvidencePath" }

function Record-Gate {
    param([string]$Gate, [string]$Prompt)
    while ($true) {
        $answer = (Read-Host "$Prompt [P=pass / F=fail / B=blocked]").Trim().ToUpperInvariant()
        if ($answer -in @("P","F","B")) { break }
    }
    $status = @{P="PASS";F="FAIL";B="BLOCKED"}[$answer]
    $note = Read-Host "Short note for $Gate"
    $data = Get-Content -Raw -Encoding UTF8 $EvidencePath | ConvertFrom-Json
    if (-not $data.gates.PSObject.Properties[$Gate]) { throw "Unknown gate in evidence file: $Gate" }
    $data.gates.$Gate.status = $status
    $data.gates.$Gate.note = $note
    $data.gates.$Gate.updated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $data.updated_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $data | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $EvidencePath
}

Write-Host "IBC Expert clean-Windows acceptance"
Write-Host "Use SYNTHETIC TEST DATA ONLY. Do not use real client/legal confidential data."
Write-Host "This recorder requires only Windows PowerShell; Python is not required."
Write-Host "Do not mark a gate PASS unless you actually performed the described action."

$Installer = Get-ChildItem -Path $PSScriptRoot -Filter "IBCExpert-Setup-*.exe" | Select-Object -First 1
if (-not $Installer) { throw "IBCExpert installer was not found beside this script." }
Write-Host "Installer under test: $($Installer.FullName)"

Record-Gate clean_install "Install IBC Expert normally on this clean Windows machine/VM. Did installation complete without error?"
Record-Gate packaged_launch "Launch the installed application. Did it open normally?"
Record-Gate clean_core_workflow "Using synthetic data, complete first-run master setup; create/edit a client and matter; import a safe document/image; run available local OCR; search; instantiate/update workflow; generate and export a form. Did the sequence work?"
Record-Gate clean_backup_restore "Create an encrypted backup, alter/delete synthetic test information, restore the backup, and verify the original synthetic information returns. Did this work?"
Record-Gate clean_restart_persistence "Close the application, restart Windows/application, and verify synthetic data persists. Did persistence work?"
Record-Gate clean_trial_activation "Using a controlled test licence and owner-generated credentials, verify trial-expiry restriction, offline activation, restart and licence persistence. Did the sequence work?"

Write-Host "Acceptance recording complete: $EvidencePath"
Write-Host "Copy this evidence JSON back to the trusted release workstation for hash/evidence validation."
