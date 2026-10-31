# Build your own Windows installer

## 1. Prepare the build PC

Use Windows 10/11 x64, a normal writable folder such as `C:\Work\SALES360`, a stable internet connection for preparation, and several GB of disk space. Node modules, SDK, PostgreSQL, package caches and installer staging occupy far more space than the source archive.

Install these build prerequisites from the official publishers:

- [Node.js 24 x64](https://nodejs.org/en/download) (includes npm/npx).
- [Full Python 3.12.10 x64](https://www.python.org/ftp/python/3.12.10/) with pip; enable Add Python to PATH. The embedded ZIP alone does not include pip.

The preparation script provides local .NET SDK 10.0.403, embedded Python 3.12.10, PostgreSQL 17.6 binary distribution, NSIS 3.12 and Microsoft Visual C++ x64 runtime. These are compatibility pins, not a claim that they are the newest patched versions. Review/update dependency security policy before production distribution. It also restores exact frontend versions from the pnpm lockfile and the Python packages in `scripts/requirements-runtime.txt`.

## 2. Download source and prepare dependencies

Extract the source ZIP or clone your repository. Open CMD in its root (where README.md is located):

```bat
node --version
python --version
Prepare-BuildTools.bat
```

If `python` points to a different version:

```bat
Prepare-BuildTools.bat -BuildPython "C:\Path\To\Python312\python.exe"
```

The script downloads from official publisher/PyPI/npm sources. Fixed ZIP archives are checked against SHA256 values in `build-support/downloads.json`; the rolling Microsoft runtime must have a valid Microsoft Authenticode signature. `.NET` uses the included official Microsoft installer script. Dependency downloads are not shipped in the source archive. The build does not need any external business-service credentials.

If a proxy/firewall blocks a publisher, obtain the exact archive from that publisher and place it in `output/downloads/` using the manifest filename, then rerun. A checksum failure stops preparation: do not bypass it or silently replace a pinned version. Verify the new publisher download and update the manifest deliberately if changing a tool version.

## 3. Compile and package

```bat
Build-Windows.bat
```

The script restores locked .NET dependencies, publishes a self-contained Windows x64 host, runs domain tests, type-checks and builds the web application, generates the guide, stages the offline runtime and compiles the NSIS installers. Any failed step stops the build.

Outputs:

- `output/releases/SALES360-Offline-0.9.1-Complete-Setup-unsigned.exe` â€” normal client installation; bundles Microsoft prerequisite.
- `output/releases/SALES360-Offline-0.9.1-Setup-unsigned.exe` â€” inner installer; use the complete setup on client PCs.
- `output/releases/SALES360-Offline-0.9.1-Portable.zip` â€” extracted portable layout.
- `output/releases/SALES360-Offline-0.9.1/` â€” staged files used by the tests.

The script refuses to replace an existing staged release. Rename your previous `output/releases/SALES360-Offline-0.9.1` folder and previous versioned output EXE/ZIP files before rebuilding. Keep backups of builds you need. No source or company records need to be deleted.

## 4. Test before handing over

```bat
Test-Evaluation.bat
```

This creates a new disposable PostgreSQL data folder and private first Administrator, imports the two synthetic workbooks, checks 101 customers/projects/invoices, reconciles every customer balance and collection totals, and checks duplicate-commit protection. It stops its test database afterward. It does not use the default company database. Each run chooses a new test data folder.

The reduced package retains the domain tests and supported 101-customer integration test. Historical VAT/workbook/browser regression scripts and evidence remain in the earlier full source archive and are not required by this build.

## 5. Run without installing

```bat
Run-Source.bat --data-dir "C:\SALES360-Evaluation-Data" --port 5099
```

Choose a new empty folder for evaluation. `Run-Source.bat` uses the compiled/staged runtime, not a system PostgreSQL service. See the installation guide for stopping, backup and restore.

## Build troubleshooting

- Missing `node`, `npx` or Python: install prerequisites, check PATH and reopen CMD.
- PowerShell download fails: check publisher access, proxy and the exact pinned filenames. Do not add tokens to repository files.
- NuGet/pnpm/pip failure: restore network access and rerun preparation/build; never claim an incomplete build passed.
- Destination exists: rename old generated output first; build uses a new staging directory.
- Microsoft signature cannot validate: check Windows certificate/time/network configuration and obtain the runtime from Microsoft.
- PostgreSQL cannot start: use a writable local data directory, review protected local logs, and check port/security-product restrictions.
- Company mail delivery, ERP connectivity and FTA filing are separate external services; they do not become offline features by rebuilding.

## Reuse an already prepared local cache (optional)

A developer who already has the complete tools in another checkout may run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/prepare-build-tools.ps1 -ToolCacheRoot C:\ExistingPreparedSALES360
```

This copies tools and the Microsoft prerequisite, then restores web dependencies. It does not copy company data. `-SkipWebInstall` is intended only when you have independently prepared `apps/web/node_modules`. The public download path requires internet; cache reuse was also used for source-package build verification.

