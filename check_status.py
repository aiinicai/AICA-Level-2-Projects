import socket
import sys

def get_host_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check():
    print("==================================================================")
    print("         GS STOCK AUDIT TRACKER - NETWORK SERVER STATUS           ")
    print("==================================================================")
    print()
    
    port = 8501
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_running = (sock.connect_ex(("127.0.0.1", port)) == 0)
    sock.close()
    
    ip = get_host_ip()
    
    if is_running:
        print("[STATUS: ONLINE & RUNNING IN BACKGROUND]")
        print()
        print(f"Local Access (Your PC):        http://localhost:{port}")
        print(f"Team Access (Office Network):  http://{ip}:{port}")
        print()
        print("Team members on the same office Wi-Fi / LAN can directly open:")
        print(f"  -> http://{ip}:{port}")
        print("in their browser to log in and update audit records in real-time.")
    else:
        print("[STATUS: STOPPED / NOT RUNNING]")
        print()
        print("To start the server silently in the background, double click:")
        print("  -> Start_Silent_Server.vbs")
        print()
        print("To start with a visible terminal window, double click:")
        print("  -> Start_Application.bat")

    print()
    print("==================================================================")

if __name__ == "__main__":
    check()
