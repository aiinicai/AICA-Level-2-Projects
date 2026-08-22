"""
Tally MCP Multi-Source Import Tool -- standalone build.

Stages Bank Statement (Excel/CSV/PDF), Journal Entry, GSTR-2B, and GSTR-1
rows and posts them to Tally Prime as vouchers only after explicit approval
in the staging grid. Reads (ledger list, duplicate-check) and writes (voucher
posting) both go through Tally's XML/HTTP Gateway (default localhost:9000).

Run:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5050 with Tally Prime running locally and its
XML/HTTP server enabled (Gateway of Tally -> F12 -> Advanced Configuration).
"""
from flask import Flask, render_template

from tally_import.routes import tally_bp

app = Flask(__name__)
app.secret_key = "dev-only-not-for-multi-user-deployment"
app.register_blueprint(tally_bp)


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
