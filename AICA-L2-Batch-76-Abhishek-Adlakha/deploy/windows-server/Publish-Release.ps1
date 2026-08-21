[CmdletBinding()]
param(
    [string] $OutputRoot = "artifacts/windows-server",
    [string] $Runtime = "win-x64",
    [switch] $NoArchive
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $OutputRoot))
$artifactsRoot = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot "artifacts"))
if (-not $outputPath.StartsWith($artifactsRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputRoot must resolve inside the repository artifacts directory."
}

function Assert-LastCommandSucceeded([string] $Description) {
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit code $LASTEXITCODE." }
}

Set-Location $repositoryRoot
if (Test-Path $outputPath) { Remove-Item $outputPath -Recurse -Force }
$packagePath = Join-Path $outputPath "package"
$appPath = Join-Path $packagePath "app"
New-Item -ItemType Directory -Path $appPath -Force | Out-Null

Push-Location "web"
try {
    & pnpm install --frozen-lockfile
    Assert-LastCommandSucceeded "Frontend dependency installation"
    & pnpm build
    Assert-LastCommandSucceeded "Frontend release build"
}
finally { Pop-Location }

& dotnet publish "src/Practice.Api/Practice.Api.csproj" --configuration Release --runtime $Runtime --self-contained false --output $appPath
Assert-LastCommandSucceeded "API publish"
New-Item -ItemType Directory -Path (Join-Path $appPath "wwwroot") -Force | Out-Null
Copy-Item "web/dist/*" (Join-Path $appPath "wwwroot") -Recurse -Force

foreach ($project in @("Practice.Migrator", "Practice.AdminCli", "Practice.Worker")) {
    $destination = Join-Path $packagePath $project
    & dotnet publish "src/$project/$project.csproj" --configuration Release --runtime $Runtime --self-contained false --output $destination
    Assert-LastCommandSucceeded "$project publish"
}

Copy-Item "deploy/windows-server/Install-PracticeManagement.ps1" $packagePath
Copy-Item "deploy/windows-server/README.md" $packagePath
Set-Content -Path (Join-Path $packagePath "RELEASE.txt") -Encoding UTF8 -Value @(
    "CA Firm Practice Management"
    "Runtime: $Runtime"
    "Built UTC: $([DateTimeOffset]::UtcNow.ToString('O'))"
)

if (-not $NoArchive) {
    $archive = Join-Path $outputPath "PracticeManagement-$Runtime.zip"
    Compress-Archive -Path "$packagePath/*" -DestinationPath $archive -CompressionLevel Optimal
    Write-Host "Windows Server release archive: $archive"
}
Write-Host "Windows Server release package: $packagePath"
