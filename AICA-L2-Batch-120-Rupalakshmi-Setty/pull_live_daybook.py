"""
Ledger Sentinel - LIVE PULL via the actual MCP tool logic (read-only)
----------------------------------------------------------------------
This calls the exact same export_daybook_to_excel() function defined in
tally_mcp_server.py - the real project deliverable - directly as a plain
Python function (same logic an MCP client such as Claude Desktop would
trigger when calling the tool over the protocol; this just skips the
stdio/MCP handshake so we can see the result immediately in a terminal).

Strictly read-only: only ever sends an Export Data request to Tally.

Run with:
    C:\\Python314\\python.exe pull_live_daybook.py
"""

import tally_mcp_server as mcp_tools

FROM_DATE = "20260101"
TO_DATE = "20261231"
COMPANY_NAME = "Gulf Emirates Trading & Distribution LLC"
OUTPUT_PATH = "live_daybook_export.xlsx"

print(f"Pulling Day Book live from Tally ({FROM_DATE} to {TO_DATE}) ...")
result = mcp_tools.export_daybook_to_excel.__wrapped__(
    FROM_DATE, TO_DATE, OUTPUT_PATH, COMPANY_NAME
) if hasattr(mcp_tools.export_daybook_to_excel, "__wrapped__") else mcp_tools.export_daybook_to_excel(
    FROM_DATE, TO_DATE, OUTPUT_PATH, COMPANY_NAME
)

print(result)
