# SALES360 — essential evaluation source (0.9.1)

This reduced package contains **95 files**, including its SHA256 inventory. Add one video and one presentation and the total becomes **97 files**. Historical release documents, duplicate prompt copies, old tests and optional workflow files have been removed. All application source and the supported local installer build remain included.

## Upload to GitHub

1. Extract the ZIP and open the SALES360 folder.
2. Create your GitHub repository, then choose **Add file > Upload files**.
3. Drag the **contents** of SALES360 into the upload area, preserving the folders. Include `.gitignore` and `.gitattributes`; if your browser hides them, add them explicitly or use GitHub Desktop.
4. Add your one video and one presentation. These two files are not supplied or modified by this package.
5. Commit the upload. A file uploaded through the browser must fit its individual size limit; the reduced source ZIP and every source file are below 25 MB. For a larger video, supply a video-hosting link or a separate release asset instead.

Upload extracted source for browsable evaluation, rather than uploading only the ZIP. The package has 95 source files; folders themselves are not source files.

## Build your own EXE

On Windows x64 install full **Node.js 24** (npm/npx) and full **Python 3.12** (pip), both on PATH. Open CMD in this folder and run each command after the previous one succeeds:

```bat
Prepare-BuildTools.bat
Build-Windows.bat
Test-Evaluation.bat
```

The first command downloads dependencies on the build PC. The complete installer is then generated at:

```text
output/releases/SALES360-Offline-0.9.1-Complete-Setup-unsigned.exe
```

The installed core runs offline without API keys. Python alone is not the full application: the included React/TypeScript, C#/.NET and PostgreSQL components are also required. The installer is unsigned and offers an optional desktop icon.

## Important files

| Location | Purpose |
|---|---|
| `installer/windows/SALES360.py` | Offline Python launcher |
| `installer/windows/*.bat` | Start, stop, backup, restore, repair and recovery helpers |
| `apps/web/` | React/TypeScript interface |
| `apps/api/` | .NET APIs, database schema, imports, billing, reports and VAT |
| `src/domain/` | Financial calculation rules |
| `scripts/` | Build, PDF rendering, runtime checks and dependencies |
| `installer/windows/*.nsi` | Windows installer definitions |
| `templates/import-formats/` | Customer master and SOA import layouts |
| `examples/` | Two workbooks covering 101 imaginary customers and their controls |
| `tests/` | Domain tests and supported 101-customer evaluation test |

## Guides and prompts

- [Build instructions](docs/BUILD-FROM-SOURCE.md)
- [Installation and usage](docs/INSTALLATION-AND-USAGE.md)
- [Development process](docs/DEVELOPMENT-PROCESS.md)
- [Implemented scope and limits](docs/EVALUATION-STATUS.md)
- [VAT sources and scope](docs/VAT-RULES-AND-SOURCES.md)
- [Original consolidated master prompt](SALES360_Codex_Master_Prompt.md)
- [Reconstructed requirement amendments](prompts/02-REQUIREMENT-AMENDMENTS.md)
- [Reusable rebuild/evaluation prompt](prompts/03-REBUILD-AND-EVALUATE-PROMPT.md)
- [Source ownership](LICENSE-NOTICE.md) and [dependency notices](scripts/NOTICE.md)

The amendment history is reconstructed from available user messages, not a complete authenticated raw chat export. The consolidated master prompt remains intact. No company database, passwords, recovery messages, keys, node_modules, runtime binaries or compiled EXE are included.

## Verification

The reduced package was rebuilt locally using prepared dependency caches: backend publication, frontend type checking/build, domain tests and both Windows installer compilations passed. The supported integration test then created 101 customers, 101 projects, 101 invoices and 67 collection records in a fresh disposable database, reconciled all 101 customer balances and checked duplicate-commit protection.

Fresh public dependency downloads were not tested end-to-end on another PC. This is not an independent security/performance certification or a claim that every original master-spec requirement is complete. The original full source remains available separately; this reduced package preserves all supported application/build inputs.
