"""
run.py
------
Entry point. Run with:

    python run.py

Then open http://localhost:5000 in your browser.

AICA Level 2 Capstone Project — Author: Shrey Chopra
ICAI AICA capstone submission only — see LICENSE_NOTICE.md.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
