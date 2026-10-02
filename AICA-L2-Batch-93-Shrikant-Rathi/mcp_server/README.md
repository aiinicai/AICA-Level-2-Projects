# LookThrough MCP server

This server gives Claude read-only access to the LookThrough portfolio engine, so a committee member can ask questions in plain language and get answers built from verified figures. It covers AICA Level 2 Module 10 (Agentic AI and MCP).

```
Claude (Desktop or any MCP client)
   │  MCP over stdio
   ▼
mcp_server/lookthrough_mcp.py ── 11 read-only tools + 1 prompt
   │  import
   ▼
verify/recompute.py ── independent pandas engine, reconciled with the app on every value
   │
   ▼
data/live/dataset.json ── AMFI NAVs, AMC disclosures, NSE/Yahoo prices; dummy family
```

## Tools

| Tool | Returns |
|---|---|
| `list_entities` | Entity and scheme identifiers, policy limits and valuation date |
| `portfolio_summary` | Value, cost, gain, XIRR and asset split, for the family or one entity |
| `look_through_exposure` | Stock exposure held directly and through funds, HHI, top-10 share and sector weights |
| `policy_check` | Each investment-policy test with its value, limit and status |
| `fund_report` | A scheme's returns, risk metrics, expense ratio and top holdings |
| `fund_overlap` | Overlap and largest common holdings of two schemes |
| `company_report` | A company's ratios, five years of statements and the family's exposure to it |
| `tax_position` | An entity's indicative capital-gains position (Income-tax Act, 2025, ss. 196 and 198) |
| `stress_test` | Beta-scaled effect of a market move on equity |
| `data_provenance` | Data sources, AMC files (URL and SHA-256), missing disclosures and warnings |
| `verify_note` | **QC gate**: binds every figure in a draft note to the tool field it came from, and lists any it cannot bind, with the reason |

Prompt: `ic_note(question, member)` produces an investment-committee note. Each statement is tagged FACT, CALC, ASSUMPTION or VIEW, and the note has to pass `verify_note` before it is presented.

## Controls

- **Read-only.** Every tool is annotated `readOnlyHint`. No tool writes data, places an order or goes to the network.
- **No new financial arithmetic.** Every figure comes from the reference engine. The server only converts units and compares figures with policy limits.
- **Deterministic check on the model.** The server records every number it returns in a session with its unit and the words that identify it (field name, company, test, sector). `verify_note` accepts a figure only when it binds to one of those numbers: each figure must be bound to one field a tool returned: same value, same unit (crore/lakh, % or ratio), from the tool cited on that line, and described by words that name that field and not a sibling field of the same record. The check is done in code, not by another model.
- **Audit trail.** `logs/mcp_audit.jsonl` gets one line per call, with the time, tool, arguments and a SHA-256 of the result.
- **Decision support only.** The server instructions and the prompt forbid buy/sell recommendations.

## Verification

```
python verify/mcp_check.py
```

31 checks, in four groups:

- **Tie-out:** every tool is compared with `reference_metrics.json`. This covers 1,073 company ratios, 132 fund metrics, all 66 overlap pairs and tax for 5 entities.
- **`verify_note` tests:** changing one figure must fail the note; an invented figure, a coincidental value, a wrong citation, a wrong unit and a swapped field must each be refused; the published sample note must pass. Each of the six binding rules is mutation-tested (removing it turns a test red).
- **Input validation.**
- **A live stdio session:** the tools are listed, all read-only, and errors come back as tool errors with a usable message.

## Connect to Claude Desktop

1. Copy the `lookthrough` entry from `claude_desktop_config.example.json` into `%APPDATA%\Claude\claude_desktop_config.json`. Change the paths if the project lives somewhere else.
2. Restart Claude Desktop. The tools appear under the connectors (plug) icon.
3. Try: *"Use the ic_note prompt: is the family over-exposed to HDFC Bank?"*

Uses the `mcp` Python SDK 2.x (`MCPServer`). In the 1.x SDK the class was called `FastMCP`, and its API is not compatible.
