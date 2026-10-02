# Uploads a Sample Advisory skill folder to your Anthropic workspace as a custom skill
# and prints its skill ID for Sample Advisory Config in n8n.
# Usage (from this folder):  .\upload-skill.ps1 strategic-advisory-mandate-letter
# The API key is typed at the prompt, used once, and never saved.
param([Parameter(Mandatory = $true)][string]$SkillFolder)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dir = Join-Path $root $SkillFolder
if (-not (Test-Path (Join-Path $dir 'SKILL.md'))) { throw "No SKILL.md found in $dir" }

$key = ''
for ($try = 1; $try -le 3; $try++) {
  $secure = Read-Host 'Paste your Anthropic API key (it will not be shown)' -AsSecureString
  $key = ([Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))).Trim()
  # a full key starts with sk-ant- and is roughly 100 characters; catch partial pastes before calling the API
  if ($key.StartsWith('sk-ant-') -and $key.Length -ge 80) { break }
  $start = if ($key.Length -ge 7) { $key.Substring(0, 7) } else { $key }
  Write-Host ("That is not a complete API key: got {0} characters starting with '{1}'. A key starts with sk-ant-api03- and is about 108 characters. Copy it again from console.anthropic.com." -f $key.Length, $start) -ForegroundColor Yellow
  $key = ''
}
if (-not $key) { Write-Host 'No valid key entered.' -ForegroundColor Red; exit 1 }

# every file goes in as files[] with its path inside one top-level folder, as the Skills API expects
$curlArgs = @('-sS', '-X', 'POST', 'https://api.anthropic.com/v1/skills', '-H', "x-api-key: $key", '-H', 'anthropic-version: 2023-06-01')
Get-ChildItem $dir -Recurse -File | ForEach-Object {
  $rel = $SkillFolder + '/' + $_.FullName.Substring($dir.Length + 1).Replace('\', '/')
  $curlArgs += @('-F', "files[]=@$($_.FullName);filename=$rel")
}

$raw = & curl.exe @curlArgs
$key = $null
try { $res = $raw | ConvertFrom-Json } catch { Write-Host $raw; throw 'Unexpected answer from the API' }
if ($res.error) { Write-Host ('Upload failed: ' + $res.error.message) -ForegroundColor Red; exit 1 }

Write-Host ''
Write-Host 'Uploaded.' -ForegroundColor Green
Write-Host ('Skill ID:    ' + $res.id)
Write-Host ('Version:     ' + $res.latest_version_id)
Write-Host ''
Write-Host 'Paste the Skill ID into n8n, Data tables, Sample Advisory Config (skillMandate for the mandate skill, skillMOU for the MOU skill).'

