[CmdletBinding()]
param(
    [ValidateSet("bootstrap", "start", "stop", "verify")]
    [string] $Action = "start"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $repositoryRoot

function Assert-LastCommandSucceeded {
    param([string] $Description)

    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Assert-CommandExists {
    param([string] $Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command is not installed or not on PATH: $Name"
    }
}

function Initialize-EnvironmentFile {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Warning "Created .env from .env.example. Change its password before non-local use."
    }
}

switch ($Action) {
    "bootstrap" {
        Initialize-EnvironmentFile
        Assert-CommandExists "pnpm"
        Push-Location "web"
        try {
            & pnpm install --frozen-lockfile
            Assert-LastCommandSucceeded "Frontend dependency installation"
        }
        finally {
            Pop-Location
        }
    }
    "start" {
        Initialize-EnvironmentFile
        Assert-CommandExists "docker"
        & docker compose --env-file .env -f deploy/compose/compose.yml up --build --detach
        Assert-LastCommandSucceeded "Docker Compose startup"
    }
    "stop" {
        Initialize-EnvironmentFile
        Assert-CommandExists "docker"
        & docker compose --env-file .env -f deploy/compose/compose.yml down
        Assert-LastCommandSucceeded "Docker Compose shutdown"
    }
    "verify" {
        Assert-CommandExists "dotnet"
        Assert-CommandExists "pnpm"

        & dotnet restore PracticeManagement.slnx
        Assert-LastCommandSucceeded ".NET restore"
        & dotnet build PracticeManagement.slnx --configuration Release --no-restore
        Assert-LastCommandSucceeded ".NET build"
        & dotnet run --project tests/Practice.Architecture.Tests/Practice.Architecture.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Architecture checks"
        & dotnet run --project tests/Practice.Database.Tests/Practice.Database.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Database foundation checks"
        & dotnet run --project tests/Practice.Identity.Tests/Practice.Identity.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Identity checks"
        & dotnet run --project tests/Practice.Scheduling.Tests/Practice.Scheduling.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Scheduling checks"
        & dotnet run --project tests/Practice.Billing.Tests/Practice.Billing.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Billing checks"
        & dotnet run --project tests/Practice.Reporting.Tests/Practice.Reporting.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Reporting checks"
        & dotnet run --project tests/Practice.WorkbookProfiler.Tests/Practice.WorkbookProfiler.Tests.csproj --configuration Release --no-build
        Assert-LastCommandSucceeded "Workbook profiler checks"

        # The API integration suite needs a disposable PostgreSQL instance. It is started here
        # and always removed, and it never touches the development compose volume.
        $dockerAvailable = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)
        if ($dockerAvailable) { & docker info *> $null; $dockerAvailable = $LASTEXITCODE -eq 0 }
        if ($dockerAvailable) {
            $integrationContainer = "practice-verify-db-$PID"
            $integrationPassword = [System.Guid]::NewGuid().ToString("N")
            try {
                & docker run -d --name $integrationContainer -p 127.0.0.1:55432:5432 `
                    -e POSTGRES_DB=practice_verify -e POSTGRES_USER=practice_verify `
                    -e POSTGRES_PASSWORD=$integrationPassword `
                    --tmpfs /var/lib/postgresql postgres:18-alpine | Out-Null
                $integrationReady = $false
                foreach ($attempt in 1..40) {
                    & docker exec $integrationContainer pg_isready -U practice_verify -d practice_verify *> $null
                    if ($LASTEXITCODE -eq 0) { $integrationReady = $true; break }
                    Start-Sleep -Seconds 2
                }
                if ($integrationReady) {
                    $env:PRACTICE_TEST_DATABASE = "Host=127.0.0.1;Port=55432;Database=practice_verify;Username=practice_verify;Password=$integrationPassword"
                    try {
                        & dotnet run --project tests/Practice.Api.IntegrationTests/Practice.Api.IntegrationTests.csproj --configuration Release --no-build
                        Assert-LastCommandSucceeded "API integration checks"
                    }
                    finally {
                        Remove-Item Env:PRACTICE_TEST_DATABASE -ErrorAction SilentlyContinue
                    }
                }
                else {
                    Write-Warning "Disposable PostgreSQL did not become ready; API integration checks were skipped."
                }
            }
            finally {
                & docker rm -f $integrationContainer *> $null
            }
        }
        else {
            Write-Warning "Docker is unavailable; API integration checks were skipped."
        }

        Push-Location "web"
        try {
            & pnpm install --frozen-lockfile
            Assert-LastCommandSucceeded "Frontend dependency installation"
            & pnpm lint
            Assert-LastCommandSucceeded "Frontend static checks"
            & pnpm test
            Assert-LastCommandSucceeded "Frontend tests"
            & pnpm build
            Assert-LastCommandSucceeded "Frontend build"
        }
        finally {
            Pop-Location
        }
    }
}
