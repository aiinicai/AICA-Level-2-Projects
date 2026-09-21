param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
$appUrl = 'http://127.0.0.1:8501'
$runtimePath = Join-Path $projectPath '.runtime'

function Test-AppReady {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "$appUrl/_stcore/health" -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content.Trim() -eq 'ok'
    } catch { return $false }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'The Python environment is missing. Follow the setup instructions in README.md.'
}

if (-not (Test-AppReady)) {
    New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
    $appProcess = Start-Process -FilePath $pythonPath `
        -ArgumentList @('-m', 'streamlit', 'run', 'app.py', '--server.address=127.0.0.1', '--server.port=8501') `
        -WorkingDirectory $projectPath -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $runtimePath 'server.log') `
        -RedirectStandardError (Join-Path $runtimePath 'server-error.log')
    $appProcess.Id | Set-Content -LiteralPath (Join-Path $runtimePath 'server.pid')
    $ready = $false
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        if (Test-AppReady) { $ready = $true; break }
        if ($appProcess.HasExited) {
            throw 'The app could not start. Check .runtime/server-error.log in the project folder.'
        }
        Start-Sleep -Milliseconds 300
    }
    if (-not $ready) {
        throw 'The app did not become ready. Check .runtime/server-error.log in the project folder.'
    }
}

Write-Output "Tax Notice Decoder is ready at $appUrl"
if (-not $NoBrowser) { Start-Process $appUrl }
