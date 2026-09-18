============================================================
  CMA PRO BUILDER - QUICK SETUP GUIDE
============================================================

WHAT THIS IS
  Bank CMA (Credit Monitoring Arrangement) report suite.
  Installed on ONE office PC (the "server"). Every other PC
  on the office network uses it through a web browser.

FIRST RUN
  1. Double-click the desktop icon "CMA Pro Builder".
     (It starts silently in the background - no black window.)
  2. Your browser opens to http://localhost:8080
  3. The Activation screen shows a HARDWARE ID like
        B7BA-EAC3-21DD-CBC5
     Send this ID to your software provider.
  4. You receive a key like  CMA-XXXX-XXXX-XXXX-XXXX
     Type it in and click Activate. Done - no internet needed.

OTHER OFFICE PCs
  1. On the server PC, run  add-firewall-rules.bat  once
     (right-click -> Run as administrator).
  2. Find the server PC's IP address (the server window shows it,
     e.g. http://192.168.1.10:8080).
  3. On every other PC, open that address in Chrome/Edge.
     All PCs share the same client data automatically.

DAILY USE
  - Desktop icon / start-hidden.vbs  start the server (silent, no window)
  - start.bat         start with a visible console (for troubleshooting)
  - stop.bat          stop the server
  - check-status.bat  is the server running?

DATA
  All data lives in the  data\  folder here. Back it up by
  copying that folder. The license is tied to THIS computer;
  moving to a new server PC needs a new key from the provider.

PORT
  Default is 8080. To change it, run:
      set PORT=9000 && CMA-Pro-Builder.exe
============================================================
