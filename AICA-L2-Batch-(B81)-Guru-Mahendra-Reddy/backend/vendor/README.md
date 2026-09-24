# Bundled Python packages

Every package the backend needs, as ready-built wheels, so the application
installs and runs on a machine with **no internet access** — a locked-down
corporate laptop, a machine behind a proxy that blocks PyPI, or an examiner's
environment with no network at all.

`run.bat` installs from here with:

```
pip install --no-index --find-links vendor -r requirements.txt
```

`--no-index` means pip never contacts PyPI.

## What is here

Wheels for **64-bit Windows, Python 3.12, 3.13 and 3.14**. Packages that are
pure Python (`py3-none-any`) work on any platform and version; the four with
compiled parts — `pydantic_core`, `sqlalchemy`, `greenlet`, `charset_normalizer`
— are present once per Python version, and `bcrypt` ships a single wheel that
covers all three.

## On macOS or Linux

These wheels will not match. Install normally instead — `run.sh` does this
automatically:

```
pip install --prefer-binary -r requirements.txt
```

## Refreshing the bundle

From a machine with internet access:

```
pip download -r requirements.txt -d vendor \
    --platform win_amd64 --python-version 3.12 --only-binary=:all:
pip download -r requirements.txt -d vendor \
    --platform win_amd64 --python-version 3.13 --only-binary=:all:
pip download -r requirements.txt -d vendor \
    --platform win_amd64 --python-version 3.14 --only-binary=:all:
```
