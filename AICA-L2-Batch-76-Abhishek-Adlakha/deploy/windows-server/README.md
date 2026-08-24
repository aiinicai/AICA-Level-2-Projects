# Native Windows Server 2019 deployment

Production uses IIS, the .NET 10 Hosting Bundle and PostgreSQL as a native Windows service. Docker Desktop and Hyper-V are not required. Windows and macOS staff access one HTTPS address from current Edge, Chrome or Safari browsers over the office LAN.

## Server prerequisites

1. A fully patched Windows Server 2019 host with a static LAN address and UPS protection.
2. Native PostgreSQL 18 installed as an automatically started Windows service. Create separate `practice_migrator` and `practice_app` logins and restrict PostgreSQL/firewall access to the server itself.
3. The .NET 10 Hosting Bundle for IIS.
4. An internal DNS name such as `practice.firm.lan` and a trusted TLS certificate in `Local Computer > Personal`.
5. An encrypted, tested backup destination outside the server.

## Build the release

On a controlled Windows build computer at the repository root:

```powershell
.\deploy\windows-server\Publish-Release.ps1
```

Copy only the resulting ZIP to the server, extract it, verify its approved checksum, then run from elevated PowerShell:

```powershell
.\Install-PracticeManagement.ps1 `
  -PackagePath C:\Temp\PracticeManagement-package `
  -CertificateThumbprint YOUR_CERTIFICATE_THUMBPRINT
```

The installer prompts privately for the migration-owner and application-role PostgreSQL connection strings. It migrates before swapping the application directory, stores the runtime connection string and data-protection keys under `C:\ProgramData\PracticeManagement`, applies restricted ACLs, configures IIS HTTPS and opens only the selected HTTPS port. It also installs the Phase 6 task generator as a Windows Scheduled Task running at startup and every six hours; Hyper-V and Docker are not used in production.

Create the first administrator after installation from an elevated terminal on the server. The password is entered without echo:

```powershell
$env:PRACTICE_CONFIG_FILE = 'C:\ProgramData\PracticeManagement\appsettings.Production.json'
dotnet 'C:\path\to\package\Practice.AdminCli\Practice.AdminCli.dll' bootstrap-admin --mobile YOUR_10_DIGIT_MOBILE --name 'Abhishek Adlakha'
Remove-Item Env:\PRACTICE_CONFIG_FILE
```

Do not put passwords in scripts, chat, documentation, source control or ordinary command-line arguments. Phase 11 will add signed release approval, backup/restore, rollback and full production commissioning runbooks.

## Local password recovery

If an employee forgets a password, an authorized server administrator runs the recovery CLI locally. The new password is entered twice without echo; all existing sessions are revoked and the reset is audited:

```powershell
$env:PRACTICE_CONFIG_FILE = 'C:\ProgramData\PracticeManagement\appsettings.Production.json'
dotnet 'C:\path\to\package\Practice.AdminCli\Practice.AdminCli.dll' reset-password --mobile EMPLOYEE_10_DIGIT_MOBILE
Remove-Item Env:\PRACTICE_CONFIG_FILE
```
