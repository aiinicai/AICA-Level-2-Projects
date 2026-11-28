"""Production-style server (Waitress). Usage: python run_server.py [port]"""
import os
import sys

from waitress import serve

from app import create_app
from app.cli import bootstrap

app = create_app()
with app.app_context():
    bootstrap()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("CHALLAN_PORT", 8080))
    print(f"Manual Challan Register running on http://0.0.0.0:{port}  (Ctrl+C to stop)")
    serve(app, host="0.0.0.0", port=port, threads=8)
