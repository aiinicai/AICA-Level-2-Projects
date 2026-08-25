[CmdletBinding()]
param(
    [ValidateSet("migrate", "backup", "verify-backup")]
    [string] $Action = "migrate",
    [string] $Path
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repositoryRoot

if (-not (Test-Path ".env")) {
    throw "Missing .env. Run .\deploy\scripts\practice.ps1 start first."
}

$composeArguments = @("compose", "--env-file", ".env", "-f", "deploy/compose/compose.yml")
function Invoke-Compose {
    & docker @composeArguments @args
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose command failed with exit code $LASTEXITCODE." }
}
switch ($Action) {
    "migrate" {
        Invoke-Compose run --rm --build migrate
    }
    "backup" {
        $databaseName = (& docker @composeArguments exec -T database printenv POSTGRES_DB).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $databaseName) { throw "Could not resolve the configured database name." }
        if (-not $Path) {
            $timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
            $Path = "backups/practice-management-$timestamp.dump"
        }
        $fullPath = [IO.Path]::GetFullPath($Path)
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($fullPath)) | Out-Null
        Invoke-Compose exec -T database pg_dump --username practice_migrator --dbname $databaseName --format=custom --file=/tmp/practice-management.dump
        $databaseContainer = (& docker @composeArguments ps -q database).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $databaseContainer) { throw "Could not resolve the database container." }
        & docker cp "${databaseContainer}:/tmp/practice-management.dump" $fullPath
        if ($LASTEXITCODE -ne 0) { throw "Copying the backup failed." }
        Invoke-Compose exec -T database rm -f /tmp/practice-management.dump
        Write-Host "Backup created: $fullPath"
    }
    "verify-backup" {
        if (-not $Path -or -not (Test-Path $Path)) { throw "A valid backup path is required." }
        $databaseContainer = (& docker @composeArguments ps -q database).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $databaseContainer) { throw "Could not resolve the database container." }
        & docker cp ([IO.Path]::GetFullPath($Path)) "${databaseContainer}:/tmp/practice-restore-verification.dump"
        if ($LASTEXITCODE -ne 0) { throw "Copying the backup into the database container failed." }
        Invoke-Compose exec -T database dropdb --username practice_migrator --if-exists practice_restore_verification
        Invoke-Compose exec -T database createdb --username practice_migrator practice_restore_verification
        Invoke-Compose exec -T database pg_restore --username practice_migrator --dbname practice_restore_verification --exit-on-error /tmp/practice-restore-verification.dump
        Invoke-Compose exec -T database psql --username practice_migrator --dbname practice_restore_verification --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('reference','system','audit','import');"
        Invoke-Compose exec -T database dropdb --username practice_migrator practice_restore_verification
        Invoke-Compose exec -T database rm -f /tmp/practice-restore-verification.dump
        Write-Host "Backup restore verification passed. The temporary verification database was removed."
    }
}
