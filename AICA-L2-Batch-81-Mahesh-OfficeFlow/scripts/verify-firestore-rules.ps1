# End-to-end check of the deployed Firestore security rules.
#
# Signs in with real Firebase Auth tokens over the REST API and asserts what each role can and
# cannot do, so the rules are verified against the live project rather than by reading them.
# Needs only the public API key — the same one that ships inside the apps.
#
# Creates temporary probe accounts and deletes them again. Any documents it writes are removed.
#
#   powershell -ExecutionPolicy Bypass -File scripts\verify-firestore-rules.ps1

$ErrorActionPreference = "Continue"

$ApiKey    = "AIzaSyBQxMe57oSTZkYFS_EyEbVTBe296yR0-cg"
$ProjectId = "office-flow-integration"
$Base      = "https://firestore.googleapis.com/v1/projects/$ProjectId/databases/(default)/documents"

$script:pass = 0
$script:fail = 0

function ErrBody($e) {
  try { return (New-Object System.IO.StreamReader($e.Exception.Response.GetResponseStream())).ReadToEnd() }
  catch { return $e.Exception.Message }
}

function Check([string]$name, [bool]$expectAllowed, [scriptblock]$call) {
  $allowed = $true
  $detail = ""
  try { & $call | Out-Null } catch { $allowed = $false; $detail = ((ErrBody $_) -replace '\s+', ' ') }
  if ($allowed -eq $expectAllowed) {
    $script:pass++
    "  PASS  $name  ({0})" -f $(if ($allowed) { "allowed" } else { "denied" })
  } else {
    $script:fail++
    "  FAIL  $name  (expected {0}, got {1})" -f `
      $(if ($expectAllowed) { "allowed" } else { "denied" }), $(if ($allowed) { "allowed" } else { "denied" })
    if ($detail) { "        $($detail.Substring(0, [Math]::Min(160, $detail.Length)))" }
  }
}

function NewProbe([string]$label) {
  $email = "probe-$label-delete-me@primeaccounting.in"
  $pass  = "Probe!" + (Get-Random -Minimum 100000 -Maximum 999999)
  $r = Invoke-RestMethod -Method Post -ContentType "application/json" -TimeoutSec 20 `
        -Uri "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=$ApiKey" `
        -Body (@{ email = $email; password = $pass; returnSecureToken = $true } | ConvertTo-Json)
  return @{ uid = $r.localId; token = $r.idToken; email = $r.email }
}

function RemoveProbe($probe) {
  try {
    Invoke-RestMethod -Method Post -ContentType "application/json" -TimeoutSec 20 `
      -Uri "https://identitytoolkit.googleapis.com/v1/accounts:delete?key=$ApiKey" `
      -Body (@{ idToken = $probe.token } | ConvertTo-Json) | Out-Null
  } catch { "  (could not delete probe account $($probe.email) - remove it in the console)" }
}

function Hdr($probe) { return @{ Authorization = "Bearer $($probe.token)" } }

Write-Host "Verifying Firestore rules for $ProjectId`n"

# ── does the database exist at all? ──────────────────────────────────────
try {
  Invoke-RestMethod -Method Get -Uri "$Base/teamMembers?pageSize=1" -TimeoutSec 20 | Out-Null
  Write-Host "WARNING: unauthenticated read succeeded - the database is wide open."
} catch {
  $b = ErrBody $_
  if ($b -match 'NOT_FOUND|does not exist') {
    Write-Host "STOP: no (default) Firestore database exists for $ProjectId."
    Write-Host "      Firebase console > Build > Firestore Database > Create database."
    exit 1
  }
}

$probe = NewProbe "member"
Write-Host "probe account: $($probe.email)`n"

Write-Host "Signed-in user (no profile document - i.e. not on the roster):"
Check "read teamMembers" $true  { Invoke-RestMethod -Method Get -Headers (Hdr $probe) -Uri "$Base/teamMembers?pageSize=5" -TimeoutSec 20 }
Check "read projects"    $true  { Invoke-RestMethod -Method Get -Headers (Hdr $probe) -Uri "$Base/projects?pageSize=5" -TimeoutSec 20 }

# A user with no roster entry has no role, so must not be able to create work or promote anyone.
$fakeTask = @{ fields = @{ title = @{ stringValue = "probe" }; assignedMemberId = @{ stringValue = $probe.uid } } } | ConvertTo-Json -Depth 6
Check "create a task (should be refused)" $false {
  Invoke-RestMethod -Method Post -ContentType "application/json" -Headers (Hdr $probe) -TimeoutSec 20 `
    -Uri "$Base/tasks?documentId=probe-task-delete-me" -Body $fakeTask
}

$fakeAdmin = @{ fields = @{ email = @{ stringValue = $probe.email }; userRole = @{ stringValue = "ADMIN" } } } | ConvertTo-Json -Depth 6
Check "self-create an ADMIN profile (should be refused)" $false {
  Invoke-RestMethod -Method Post -ContentType "application/json" -Headers (Hdr $probe) -TimeoutSec 20 `
    -Uri "$Base/teamMembers?documentId=$($probe.uid)" -Body $fakeAdmin
}

Write-Host "`nUnauthenticated:"
Check "read teamMembers without signing in (should be refused)" $false {
  Invoke-RestMethod -Method Get -Uri "$Base/teamMembers?pageSize=1" -TimeoutSec 20
}

# ── tidy up anything that slipped through ────────────────────────────────
foreach ($path in @("tasks/probe-task-delete-me", "teamMembers/$($probe.uid)")) {
  try { Invoke-RestMethod -Method Delete -Headers (Hdr $probe) -Uri "$Base/$path" -TimeoutSec 20 | Out-Null } catch { }
}
RemoveProbe $probe

Write-Host "`n$script:pass passed, $script:fail failed"
if ($script:fail -gt 0) {
  Write-Host "`nIf 'read teamMembers' was denied, the rules in firestore.rules have not been published yet."
  exit 1
}
Write-Host "Rules look correct."
