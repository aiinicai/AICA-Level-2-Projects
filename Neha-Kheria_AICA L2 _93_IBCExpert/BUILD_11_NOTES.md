# Build 11 Notes — Windows Customer Packaging Source

Build 11 continues from Build 10 without redesigning completed modules.

Added:
- PyInstaller onedir customer specification at `packaging/IBCExpert.spec`.
- Mandatory build-time injection and validation of the owner PUBLIC licence verification key.
- Explicit exclusion of `owner_tools`, tests and development-only packages from the customer bundle.
- Windows PowerShell and batch reproducible customer build scripts.
- Post-build scanner that rejects owner tools, owner private-key filenames/markers, a missing or invalid public key, and a missing packaged executable.
- Release ZIP + SHA-256 manifest generation in the Windows build script.
- Platform-independent packaging-security regression tests.

Not claimed in this build:
- An actual Windows executable was not built in the Linux development sandbox.
- Windows clean-machine launch/installer acceptance remains pending.
- The owner private signing key was not created, copied, or embedded.
