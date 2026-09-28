# Exports every Sample Advisory workflow (names starting with "DF") from n8n into n8n\workflows
# as importable JSON. Needs an n8n API key: n8n > Settings > n8n API > Create an API key.
# Credentials are referenced by name only; no secrets are exported.
param([string]$N8nUrl = 'https://your-instance.app.n8n.cloud')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root 'n8n\workflows'
New-Item -ItemType Directory -Force $out | Out-Null

$secure = Read-Host 'Paste your n8n API key (not shown)' -AsSecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
$h = @{ 'X-N8N-API-KEY' = $key; 'Accept' = 'application/json' }
$base = $N8nUrl.TrimEnd('/') + '/api/v1'

$all = @(); $cursor = $null
do {
  $u = "$base/workflows?limit=250" + $(if ($cursor) { "&cursor=$cursor" } else { '' })
  $page = Invoke-RestMethod -Uri $u -Headers $h
  $all += $page.data; $cursor = $page.nextCursor
} while ($cursor)
$mine = $all | Where-Object { $_.name -like 'DF*' -and -not $_.isArchived }

foreach ($w in $mine) {
  $full = Invoke-RestMethod -Uri "$base/workflows/$($w.id)" -Headers $h
  $export = [ordered]@{ name = $full.name; nodes = $full.nodes; connections = $full.connections; settings = $full.settings; meta = @{ exportedFrom = 'Sample Advisory n8n'; originalId = $full.id } }
  $file = ($full.name -replace '[^A-Za-z0-9]+', '_').Trim('_') + '.json'
  ($export | ConvertTo-Json -Depth 100) | Set-Content -Path (Join-Path $out $file) -Encoding utf8
  Write-Host "Exported $($full.name)"
}
$key = $null
Write-Host ''
Write-Host "Done: $($mine.Count) workflows in $out" -ForegroundColor Green
