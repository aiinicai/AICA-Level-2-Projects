param([string]$BuildPython='python',[string]$ToolCacheRoot,[switch]$SkipWebInstall)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
if(!$SkipWebInstall){
 if(!(Get-Command node -ErrorAction SilentlyContinue) -or !(Get-Command npx.cmd -ErrorAction SilentlyContinue)){throw 'Install the full Node.js 24 Windows distribution (with npm/npx), add it to PATH and reopen CMD.'}
}
if(!$ToolCacheRoot){
 & $BuildPython -c "import sys;assert sys.version_info[:2]==(3,12),'Full Python 3.12 with pip is required'"
 if($LASTEXITCODE -ne 0){throw 'Install full Python 3.12 or pass -BuildPython with its full path'}
}
New-Item -ItemType Directory -Force -Path '.tools','output/releases','output/downloads' | Out-Null
if($ToolCacheRoot){
 $cache=(Resolve-Path -LiteralPath $ToolCacheRoot).ProviderPath
 if($cache -eq $projectRoot){throw 'Tool cache must be a separate prepared checkout.'}
 foreach($name in @('dotnet','python-embed','postgres','nsis')){
  $source=Join-Path $cache ".tools/$name"
  if(!(Test-Path -LiteralPath $source)){throw "Missing prepared cache: $source"}
  if(!(Test-Path -LiteralPath ".tools/$name")){Copy-Item -LiteralPath $source -Destination '.tools' -Recurse}
 }
 Copy-Item -LiteralPath (Join-Path $cache 'output/releases/VC_redist.x64.exe') -Destination 'output/releases/VC_redist.x64.exe' -Force
}else{
 $manifest=Get-Content -LiteralPath 'build-support/downloads.json' -Raw | ConvertFrom-Json
 foreach($entry in $manifest.PSObject.Properties){
  $target=Join-Path $projectRoot ('output/downloads/'+$entry.Name)
  if(!(Test-Path -LiteralPath $target)){Invoke-WebRequest -UseBasicParsing -Uri $entry.Value.url -OutFile $target}
  if($entry.Value.sha256 -and (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.Value.sha256){throw "Checksum mismatch: $target. Do not use this download; obtain the pinned archive from the official publisher."}
 }
 if(!(Test-Path '.tools/python-embed/python.exe')){Expand-Archive -LiteralPath 'output/downloads/python-embed.zip' -DestinationPath '.tools/python-embed'}
 if(!(Test-Path '.tools/postgres/pgsql/bin/pg_ctl.exe')){Expand-Archive -LiteralPath 'output/downloads/postgres.zip' -DestinationPath '.tools/postgres'}
 if(!(Test-Path '.tools/nsis/nsis-3.12/makensis.exe')){Expand-Archive -LiteralPath 'output/downloads/nsis.zip' -DestinationPath '.tools/nsis'}
 Copy-Item -LiteralPath 'output/downloads/VC_redist.x64.exe' -Destination 'output/releases/VC_redist.x64.exe' -Force
 if(!(Test-Path '.tools/dotnet/dotnet.exe')){
  & 'build-support/dotnet-install.ps1' -Version '10.0.403' -Architecture x64 -InstallDir (Join-Path $projectRoot '.tools/dotnet') -NoPath
  if($LASTEXITCODE -ne 0){throw '.NET SDK preparation failed'}
 }
 & $BuildPython -c "import sys;assert sys.version_info[:2]==(3,12),'Install full Python 3.12 and put it on PATH or use -BuildPython with its full path'"
 if($LASTEXITCODE -ne 0){throw 'Full Python 3.12 with pip is required on the build PC'}
 New-Item -ItemType Directory -Force -Path 'output/wheelhouse','.tools/python-embed/Lib/site-packages' | Out-Null
 & $BuildPython -m pip download --index-url https://pypi.org/simple --only-binary=:all: --dest output/wheelhouse -r scripts/requirements-runtime.txt
 if($LASTEXITCODE -ne 0){throw 'Wheel download failed'}
 & $BuildPython -m pip install --no-index --find-links output/wheelhouse --target .tools/python-embed/Lib/site-packages --upgrade --no-compile -r scripts/requirements-runtime.txt
 if($LASTEXITCODE -ne 0){throw 'Python runtime library preparation failed'}
 @('python312.zip','.','Lib\site-packages','import site') | Set-Content -LiteralPath '.tools/python-embed/python312._pth' -Encoding ASCII
}
$signature=Get-AuthenticodeSignature -LiteralPath 'output/releases/VC_redist.x64.exe'
if($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft'){throw 'Microsoft runtime publisher signature must validate'}
& '.tools/python-embed/python.exe' 'scripts/check_offline_libraries.py'
if($LASTEXITCODE -ne 0){throw 'Bundled Python library check failed'}
if(!$SkipWebInstall){
 & node --version
 if($LASTEXITCODE -ne 0){throw 'Install Node.js 24 and reopen the terminal'}
 Push-Location 'apps/web'
 try{
  & npx.cmd --yes pnpm@10.20.0 install --frozen-lockfile
  if($LASTEXITCODE -ne 0){throw 'Frontend dependency installation failed'}
 }finally{Pop-Location}
}
Write-Host 'Build tools prepared. Run Build-Windows.bat next. Build tools/downloads are excluded from Git.'
