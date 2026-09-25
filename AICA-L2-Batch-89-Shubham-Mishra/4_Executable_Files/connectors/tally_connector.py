"""
TallyConnector — connects via the ICAI Tally Prime MCP Server (the module the
L2 syllabus covers: https://ai.icai.org/usecases_details.php?id=200).

Architecture reality this connector is honest about (see connector_setup.md):
the Tally MCP Server is a local Node.js process that only works when it and
Tally Prime run on the same machine as the MCP client. A backend deployed to
Render/Railway cannot reach a user's local Tally Prime instance over the
public internet without a network tunnel. So this connector:

  1. Tries a real MCP stdio connection when TALLY_MCP_COMMAND is configured
     (works when the backend itself runs locally, alongside Tally Prime and
     the extracted MCP server -- e.g. during a live demo).
  2. Falls back to the cached sample pull in
     examples/outputs/sample_tally_pull.json otherwise, exactly as CLAUDE.md
     Section 6 recommends, with every result clearly marked "source":
     "live" or "source": "cached_fallback" so nothing is silently faked.

Tool names below (list-master, set-company, ledger-account, bills-outstanding)
are the real tool names exposed by this MCP server, confirmed by calling them
directly during development on 2026-09-16 and 2026-09-20.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_connector import BaseConnector

load_dotenv()

FALLBACK_PATH = (
    Path(__file__).resolve().parent.parent / "examples" / "outputs" / "sample_tally_pull.json"
)


def _load_fallback() -> dict:
    return json.loads(FALLBACK_PATH.read_text())


class TallyConnector(BaseConnector):
    def __init__(self):
        self.company: str | None = None
        self._mcp_command = os.getenv("TALLY_MCP_COMMAND", "").strip()
        self._mcp_args = os.getenv("TALLY_MCP_ARGS", "").split() if os.getenv("TALLY_MCP_ARGS") else []

    # ---- internal: real MCP stdio client -----------------------------------
    def _mcp_configured(self) -> bool:
        return bool(self._mcp_command)

    async def _call_tool_async(self, tool_name: str, arguments: dict) -> dict:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self._mcp_command, args=self._mcp_args)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                text = "".join(block.text for block in result.content if hasattr(block, "text"))
                return json.loads(text)

    def _call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Raises on any failure -- callers decide whether to fall back."""
        if not self._mcp_configured():
            raise RuntimeError("TALLY_MCP_COMMAND not configured; live Tally MCP connection unavailable")
        return asyncio.run(self._call_tool_async(tool_name, arguments))

    # ---- BaseConnector interface --------------------------------------------
    def authenticate(self, credentials: dict) -> None:
        """Tally's XML gateway (F1 > Settings > Connectivity, port 9000) has no
        login of its own; 'authenticate' here just records which company/client
        to target for subsequent calls."""
        self.company = credentials.get("company")

    def fetch_clients(self) -> list[dict]:
        try:
            data = self._call_tool("list-master", {"collection": "company"})
            return [{"client_id": name, "name": name, "source": "live"} for name in data.get("list", [])]
        except Exception:
            fallback = _load_fallback()
            return [{**c, "source": "cached_fallback"} for c in fallback["clients"]]

    def fetch_ledgers(self, client_id: str) -> list[dict]:
        try:
            self._call_tool("set-company", {"companyName": client_id})
            data = self._call_tool("list-master", {"collection": "ledger"})
            return [{"ledger_name": name, "source": "live"} for name in data.get("list", [])]
        except Exception:
            fallback = _load_fallback()
            return [{"ledger_name": name, "source": "cached_fallback"} for name in fallback["ledgers"]]

    def fetch_vouchers(self, client_id: str, date_range: tuple) -> list[dict]:
        from_date, to_date = date_range
        try:
            data = self._call_tool(
                "ledger-account",
                {"ledgerName": client_id, "fromDate": from_date, "toDate": to_date},
            )
            rows = data if isinstance(data, list) else data.get("rows", [])
            return [{**row, "source": "live"} for row in rows]
        except Exception:
            fallback = _load_fallback()
            return [{**row, "source": "cached_fallback"} for row in fallback["vouchers_sample"]["rows"]]

    def fetch_invoices(self, client_id: str) -> list[dict]:
        try:
            data = self._call_tool("bills-outstanding", {"nature": "receivable", "toDate": "2026-03-31"})
            rows = data if isinstance(data, list) else data.get("rows", [])
            return [{**row, "source": "live"} for row in rows]
        except Exception:
            fallback = _load_fallback()
            return [{**row, "source": "cached_fallback"} for row in fallback["invoices_sample"]["rows"]]


if __name__ == "__main__":
    connector = TallyConnector()
    connector.authenticate({"company": "Techno Traders Ltd"})
    print("Clients:", json.dumps(connector.fetch_clients(), indent=2))
    print("Invoices:", json.dumps(connector.fetch_invoices("Techno Traders Ltd")[:2], indent=2))
