EXECUTABLE FILES
==================

InsightFlow-Windows.zip
  Unzip, then double-click InsightFlow.exe (or "Launch InsightFlow.bat").
  No Node.js or internet connection required.
  Windows SmartScreen may show a warning on first launch because the app is
  not code-signed with a paid certificate — click "More info" -> "Run
  anyway". This is expected for an unsigned indie build, not a defect.

InsightFlow-macOS-AppleSilicon.zip
  For M1/M2/M3/M4 Macs. Unzip, then double-click InsightFlow.app.
  macOS Gatekeeper will likely block the first launch ("cannot be opened" or
  "is damaged"). To fix:
    1. Open Terminal, cd into the unzipped folder
    2. Run: xattr -cr InsightFlow.app
    3. Double-click InsightFlow.app again — it will now open normally.
  This is standard behavior for any unsigned macOS app downloaded from the
  internet, not a sign the file is actually corrupted.

Both builds are Electron desktop wrappers around the same React/Vite web
application found in 05_Supporting_Documents — they embed the built
dashboard directly, so no build step or dependency install is needed to run
them.
