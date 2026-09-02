"""
Prints this computer's address on the local network, so run_far.bat can show
it to the person starting the app and so QR codes point somewhere other
devices can actually reach.

Deliberately does not send any real traffic: connecting a UDP socket just
asks the OS which local address it would use to reach that destination,
without transmitting anything. Falls back to printing nothing (and letting
run_far.bat fall back to 127.0.0.1) if this computer has no network route at
all, e.g. it isn't connected to any network.
"""

import socket

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        print(s.getsockname()[0])
    finally:
        s.close()
except OSError:
    pass
