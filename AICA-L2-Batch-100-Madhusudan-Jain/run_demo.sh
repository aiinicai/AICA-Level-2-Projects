#!/bin/zsh
# Start the CHS Audit Assistant for a demo: keeps the Mac awake while it runs and prints the address to share.
cd "$(dirname "$0")"
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
echo "Share this address on the same Wi-Fi:  http://${IP:-<this Mac's IP>}:8501"
echo "Press Ctrl+C to stop."
exec caffeinate -dimsu .venv/bin/streamlit run app.py --server.port 8501 --server.headless true
