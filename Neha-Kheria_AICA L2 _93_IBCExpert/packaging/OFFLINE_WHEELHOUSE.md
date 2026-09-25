# IBC Expert — Offline Wheelhouse

The wheelhouse is used only when running IBC Expert from source or preparing a build on a computer
that must install Python dependencies without internet access. The packaged PyInstaller customer
application does not download Python packages at runtime.

## Prepare on a trusted Windows build computer

Use 64-bit CPython 3.14.x, matching the Build 15 Windows release target:

```powershell
.\scripts\prepare_wheelhouse.ps1 -Clean
```

The script:
1. downloads every pinned requirement and transitive dependency as a wheel only;
2. refuses source distributions;
3. writes `wheelhouse\SHA256SUMS.txt`;
4. performs an offline `pip --dry-run` resolution using only that wheelhouse.

Do not hand-edit the wheelhouse after verification. If one wheel changes, regenerate the manifest
and repeat verification.

## Verify again without downloading

```powershell
python scripts\verify_wheelhouse.py wheelhouse --requirements requirements.txt
```

## Offline source bootstrap

Keep `requirements.txt` and the complete `wheelhouse` directory beside `bootstrap.py`, then run:

```powershell
python bootstrap.py
```

The bootstrap automatically selects `--no-index --find-links wheelhouse` when wheels are present.
It never falls back to the internet if a non-empty wheelhouse is selected and a required compatible
wheel is missing; it fails with a clear error instead.

## Security boundary

The wheelhouse contains third-party Python packages only. It must never contain the owner private
licence signing key, customer/client documents, database files, backups, or legal data.
