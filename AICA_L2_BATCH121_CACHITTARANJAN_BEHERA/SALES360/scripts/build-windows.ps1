param([switch]$SkipCompile,[string]$NuGetCachePath)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$version=(Get-Content 'installer/windows/SALES360-release.dat' -Raw|ConvertFrom-Json).version
$dotnet=Join-Path $projectRoot '.tools/dotnet/dotnet.exe'
$python=Join-Path $projectRoot '.tools/python-embed/python.exe'
$compiler=Join-Path $projectRoot '.tools/nsis/nsis-3.12/makensis.exe'
foreach($required in @($dotnet,$python,$compiler,'.tools/postgres/pgsql/bin/pg_ctl.exe','output/releases/VC_redist.x64.exe','apps/web/node_modules/typescript/bin/tsc')){
 if(!(Test-Path -LiteralPath $required)){throw "Missing $required. Run Prepare-BuildTools.bat first."}
}
$env:DOTNET_CLI_HOME=Join-Path $projectRoot '.tools/dotnet-home'
$env:NUGET_PACKAGES=if($NuGetCachePath){(Resolve-Path -LiteralPath $NuGetCachePath).ProviderPath}else{Join-Path $projectRoot '.tools/nuget'}
$env:DOTNET_CLI_TELEMETRY_OPTOUT='1'
$hostBuild=Join-Path $projectRoot 'output/build/source/host'
$payload=Join-Path $projectRoot "output/releases/SALES360-Offline-$version"
if(Test-Path -LiteralPath $payload){throw 'Output already exists. Rename your previous output folder before rebuilding; no files were deleted.'}
& $dotnet restore apps/api -r win-x64 --configfile NuGet.Config --locked-mode -p:NuGetAudit=false
if($LASTEXITCODE -ne 0){throw 'Backend dependency restore failed'}
& $dotnet publish apps/api -c Release -r win-x64 --self-contained true --no-restore -o $hostBuild
if($LASTEXITCODE -ne 0){throw 'Backend publish failed'}
& $dotnet run --project tests/domain -c Release
if($LASTEXITCODE -ne 0){throw 'Domain tests failed'}
Push-Location apps/web
try{
 & node node_modules/typescript/bin/tsc -b
 if($LASTEXITCODE -ne 0){throw 'TypeScript check failed'}
 & node node_modules/vite/bin/vite.js build --configLoader runner
 if($LASTEXITCODE -ne 0){throw 'Frontend build failed'}
}finally{Pop-Location}
& $python scripts/build_user_guide.py
if($LASTEXITCODE -ne 0){throw 'User guide generation failed'}
New-Item -ItemType Directory -Force -Path $payload,"$payload/runtime","$payload/apps/web","$payload/scripts","$payload/licenses" | Out-Null
Copy-Item -LiteralPath $hostBuild -Destination $payload -Recurse
Copy-Item -LiteralPath '.tools/python-embed' -Destination "$payload/runtime/python" -Recurse
New-Item -ItemType Directory -Force -Path "$payload/runtime/postgres" | Out-Null
foreach($name in @('bin','lib','share')){Copy-Item -LiteralPath ".tools/postgres/pgsql/$name" -Destination "$payload/runtime/postgres" -Recurse}
Copy-Item -LiteralPath 'apps/web/dist' -Destination "$payload/apps/web" -Recurse
Copy-Item -LiteralPath 'templates','docs' -Destination $payload -Recurse
Copy-Item -LiteralPath 'examples' -Destination $payload -Recurse
Copy-Item -LiteralPath 'scripts/render_pdf.py','scripts/requirements-runtime.txt' -Destination "$payload/scripts"
foreach($name in @('SALES360.py','Start-SALES360.bat','Stop-SALES360.bat','Backup-SALES360.bat','Restore-SALES360.bat','Repair-SALES360.bat','Open-Outlook-Recovery.bat','SALES360-release.dat','OFFLINE-README.txt')){Copy-Item -LiteralPath "installer/windows/$name" -Destination $payload}
Copy-Item -LiteralPath 'scripts/NOTICE.md' -Destination "$payload/licenses/THIRD-PARTY.md"
Copy-Item -LiteralPath 'installer/windows/POSTGRESQL-LICENSE.txt' -Destination "$payload/licenses"
Copy-Item -LiteralPath 'output/releases/VC_redist.x64.exe' -Destination "$payload/runtime"
Copy-Item -LiteralPath 'assets/brand' -Destination "$payload/icons" -Recurse
Copy-Item -LiteralPath 'docs/INSTALLATION-AND-USAGE.html','output/guides/INSTALLATION-AND-USAGE.pdf' -Destination $payload
$inventory=Get-ChildItem -LiteralPath $payload -Recurse -File | Where-Object {$_.Extension -notin '.pyc','.pyo' -and $_.FullName -notlike '*\__pycache__\*'} | ForEach-Object{[ordered]@{path=$_.FullName.Substring($payload.Length+1);bytes=$_.Length;sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}}
@{version=$version;offline=$true;apiKeysRequired=$false;runtime='Windows x64';files=$inventory}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$payload/bundle-manifest.json"
if(!$SkipCompile){
 $inner=Join-Path $projectRoot "output/releases/SALES360-Offline-$version-Setup-unsigned.exe"
 & $compiler "/DPAYLOAD=$payload" "/DOUTPUT=$inner" 'installer/windows/offline-setup.nsi'
 if($LASTEXITCODE -ne 0){throw 'Application installer compilation failed'}
 $complete=Join-Path $projectRoot "output/releases/SALES360-Offline-$version-Complete-Setup-unsigned.exe"
 & $compiler "/DICONPATH=$projectRoot\assets\brand\sales360.ico" "/DAPPLICATION=$inner" "/DVCREDIST=$projectRoot\output\releases\VC_redist.x64.exe" "/DLICENSEPATH=$projectRoot\installer\windows\POSTGRESQL-LICENSE.txt" "/DOUTPUT=$complete" 'installer/windows/offline-bootstrap.nsi'
 if($LASTEXITCODE -ne 0){throw 'Complete installer compilation failed'}
 Get-FileHash -LiteralPath $complete -Algorithm SHA256
}
. "$PSScriptRoot/New-PortableZip.ps1"
New-PortableZip -Source $payload -Destination (Join-Path $projectRoot "output/releases/SALES360-Offline-$version-Portable.zip")
Write-Host "Built $version. Output: output/releases. These binaries must not be committed to the source repository."
