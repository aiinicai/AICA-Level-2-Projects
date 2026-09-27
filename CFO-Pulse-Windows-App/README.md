# CFO Pulse Windows release

Run `CFOPulse-Verified.exe` on Windows. The first launch starts the local CFO Pulse service and prints its URL and a one-time Admin password. Sign in and change the password. The application stores its database, credentials, and uploaded reports in a `data` folder next to the executable.

Use **Import workbook** to upload either sample from the `samples/` folder. The files contain synthetic demonstration data. The executable is a self-contained PyInstaller one-file build; Python does not need to be installed.

This executable is unsigned. Review `../docs/RELEASE_REPORT.md` before redistribution.
