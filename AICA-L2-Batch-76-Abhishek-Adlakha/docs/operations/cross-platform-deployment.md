# Cross-Platform Deployment

## Support contract

| Use | Windows | macOS |
|---|---|---|
| Staff access | Current managed Chrome or Edge | Current managed Chrome or Edge |
| Local development | Docker Desktop, .NET 10, Node 24, pnpm 11, PowerShell | Docker Desktop, .NET 10, Node 24, pnpm 11, POSIX shell |
| Development/pilot | Compose through PowerShell on a supported workstation | Compose through POSIX shell on Docker Desktop |
| Production server | Native Windows Server 2019: IIS/.NET 10 + PostgreSQL Windows service | Not a production host; browser client only |

There is one database and application deployment. Staff computers do not synchronize local databases or run client-specific copies.

## Shared lifecycle

| Action | Windows PowerShell | macOS terminal |
|---|---|---|
| Prepare | `.\deploy\scripts\practice.ps1 bootstrap` | `./deploy/scripts/practice.sh bootstrap` |
| Verify source | `.\deploy\scripts\practice.ps1 verify` | `./deploy/scripts/practice.sh verify` |
| Start/update local stack | `.\deploy\scripts\practice.ps1 start` | `./deploy/scripts/practice.sh start` |
| Stop stack | `.\deploy\scripts\practice.ps1 stop` | `./deploy/scripts/practice.sh stop` |

Both development wrappers use `deploy/compose/compose.yml`. They do not define the production runtime. Production release packaging and installation live in `deploy/windows-server` and are verified separately on Windows CI.

The start command runs services in the background. Use Docker Desktop’s Containers view for live logs, and use the stop command for a clean shutdown that retains database data.

## LAN access

1. Give the host a DHCP reservation/static LAN address and internal DNS name.
2. Use an internal TLS certificate trusted by every managed Windows and Mac computer.
3. Allow only the chosen HTTPS/web port from authorized LAN subnets. PostgreSQL remains bound to host loopback and is never exposed to staff computers.
4. IIS terminates TLS on production; port 8088 remains a development-only Compose default.
5. Users open the same URL from Windows or Mac. Application dates remain `Asia/Kolkata`; timestamps are stored as UTC once persistence begins.

## Development architecture compatibility

The development images support x64 and ARM64, so Docker selects the right image for Windows x64, Intel Mac or Apple silicon. The production package is built explicitly for `win-x64`, and IIS serves the compiled React assets from the ASP.NET Core application.

## Production contract

Docker Desktop is not used on Windows Server 2019. Follow [the native Windows Server runbook](../../deploy/windows-server/README.md). Production requires native PostgreSQL automatic startup, IIS HTTPS, persisted data-protection keys, restricted filesystem/database permissions, off-server backups and Windows-host release/rollback verification. Phase 11 completes production commissioning and recovery drills.
