#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $PackagePath,
    [string] $InstallPath = "C:\Program Files\PracticeManagement",
    [string] $DataPath = "C:\ProgramData\PracticeManagement",
    [string] $SiteName = "PracticeManagement",
    [string] $HostName = "practice.firm.lan",
    [int] $HttpsPort = 443,
    [Parameter(Mandatory)] [string] $CertificateThumbprint
)

$ErrorActionPreference = "Stop"
$resolvedPackage = (Resolve-Path $PackagePath).Path
if (-not (Test-Path (Join-Path $resolvedPackage "app/Practice.Api.dll"))) {
    throw "The selected directory is not a valid Practice Management release package."
}
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw "Install the .NET 10 Hosting Bundle before running this installer."
}
if (-not (Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue)) {
    throw "A supported native PostgreSQL Windows service must be installed and running first."
}
$certificate = Get-Item "Cert:\LocalMachine\My\$CertificateThumbprint" -ErrorAction Stop

function Read-PlainSecret([string] $Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
}

$migrationConnection = Read-PlainSecret "PostgreSQL migration-owner connection string"
$applicationConnection = Read-PlainSecret "PostgreSQL application-role connection string"

Import-Module ServerManager
Install-WindowsFeature Web-Server, Web-WebSockets, Web-Mgmt-Console -IncludeManagementTools | Out-Null
Import-Module WebAdministration

$stagingPath = "$InstallPath.new"
if (Test-Path $stagingPath) { Remove-Item $stagingPath -Recurse -Force }
New-Item -ItemType Directory -Path $stagingPath -Force | Out-Null
Copy-Item (Join-Path $resolvedPackage "app/*") $stagingPath -Recurse -Force
New-Item -ItemType Directory -Path (Join-Path $stagingPath "worker") -Force | Out-Null
Copy-Item (Join-Path $resolvedPackage "Practice.Worker/*") (Join-Path $stagingPath "worker") -Recurse -Force

$env:ConnectionStrings__PracticeDatabase = $migrationConnection
try {
    & dotnet (Join-Path $resolvedPackage "Practice.Migrator/Practice.Migrator.dll")
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed with exit code $LASTEXITCODE." }
}
finally {
    Remove-Item Env:\ConnectionStrings__PracticeDatabase -ErrorAction SilentlyContinue
    $migrationConnection = $null
}

New-Item -ItemType Directory -Path $DataPath -Force | Out-Null
$configPath = Join-Path $DataPath "appsettings.Production.json"
@{
    ConnectionStrings = @{ PracticeDatabase = $applicationConnection }
    Security = @{ DataProtectionKeyPath = (Join-Path $DataPath "keys") }
} | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8
$applicationConnection = $null
New-Item -ItemType Directory -Path (Join-Path $DataPath "keys") -Force | Out-Null

if (-not (Test-Path "IIS:\AppPools\$SiteName")) { New-WebAppPool -Name $SiteName | Out-Null }
Set-ItemProperty "IIS:\AppPools\$SiteName" -Name managedRuntimeVersion -Value ""
Set-ItemProperty "IIS:\AppPools\$SiteName" -Name processModel.identityType -Value ApplicationPoolIdentity

if (Test-Path $InstallPath) {
    $previousPath = "$InstallPath.previous"
    if (Test-Path $previousPath) { Remove-Item $previousPath -Recurse -Force }
    Move-Item $InstallPath $previousPath
}
Move-Item $stagingPath $InstallPath

$identity = "IIS AppPool\$SiteName"
& icacls $InstallPath /inheritance:r /grant:r "${identity}:(OI)(CI)RX" "Administrators:(OI)(CI)F" /T | Out-Null
& icacls $DataPath /inheritance:r /grant:r "${identity}:(OI)(CI)M" "Administrators:(OI)(CI)F" /T | Out-Null

if (Test-Path "IIS:\Sites\$SiteName") { Remove-Website -Name $SiteName }
New-Website -Name $SiteName -ApplicationPool $SiteName -PhysicalPath $InstallPath -Port $HttpsPort -HostHeader $HostName -Ssl | Out-Null
New-Item "IIS:\SslBindings\0.0.0.0!$HttpsPort!$HostName" -Value $certificate -SSLFlags 1 -Force | Out-Null

Add-WebConfigurationProperty -PSPath "IIS:\Sites\$SiteName" -Filter "system.webServer/aspNetCore/environmentVariables" -Name "." -Value @{ name = "ASPNETCORE_ENVIRONMENT"; value = "Production" }
Add-WebConfigurationProperty -PSPath "IIS:\Sites\$SiteName" -Filter "system.webServer/aspNetCore/environmentVariables" -Name "." -Value @{ name = "PRACTICE_CONFIG_FILE"; value = $configPath }

if (-not (Get-NetFirewallRule -DisplayName "Practice Management HTTPS" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Practice Management HTTPS" -Direction Inbound -Protocol TCP -LocalPort $HttpsPort -Action Allow | Out-Null
}
Restart-WebAppPool -Name $SiteName
if (Get-ScheduledTask -TaskName "Practice Management Task Generator" -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName "Practice Management Task Generator" -Confirm:$false
}
$workerAction = New-ScheduledTaskAction -Execute "dotnet.exe" -Argument "`"$InstallPath\worker\Practice.Worker.dll`" --once" -WorkingDirectory (Join-Path $InstallPath "worker")
$workerTriggers = @(
    (New-ScheduledTaskTrigger -AtStartup),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 3650))
)
$workerSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName "Practice Management Task Generator" -Action $workerAction -Trigger $workerTriggers -Settings $workerSettings -User "SYSTEM" -RunLevel Highest | Out-Null
Start-ScheduledTask -TaskName "Practice Management Task Generator"
Write-Host "Installed. Configure internal DNS for https://$HostName and verify /health/ready from an authorized LAN computer."
