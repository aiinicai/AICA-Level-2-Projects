param([ValidateRange(1024,65535)][int]$Port = 8080)
$env:NW_BIND = '0.0.0.0'
$env:NW_PORT = [string]$Port
$env:NW_SECURE = '0'
$env:NW_DB = Join-Path $PSScriptRoot 'networth.sqlite3'
$env:GEMINI_API_KEY = [Environment]::GetEnvironmentVariable('GEMINI_API_KEY','Machine')
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -u (Join-Path $PSScriptRoot 'networth.py') *> (Join-Path $PSScriptRoot 'networth-server.log')
exit $LASTEXITCODE
