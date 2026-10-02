# Prompt files

These are the prompts the product itself uses. Each one keeps the model on figures produced by code and makes its output checkable.

| File | Used by | Purpose |
|---|---|---|
| [ic_note_prompt.md](ic_note_prompt.md) | MCP server (`ic_note` prompt) | Investment-committee note with FACT / CALC / ASSUMPTION / VIEW tags; must pass `verify_note` |
| [mcp_server_instructions.md](mcp_server_instructions.md) | MCP server (server instructions sent to every client) | Standing rules: quote tool figures exactly, tag statements, no buy/sell advice |
| [financial_extraction_prompt.md](financial_extraction_prompt.md) | App → *AI data extraction* screen | Pulls statement figures out of an annual report into schema-checked JSON, with the source line for every figure |
| [example_session.md](example_session.md) | Demo | The questions used in the demo video and the tools each one calls |

## Design choices

1. **The model never produces a figure of its own.** Numbers come from tools, which use the reconciled engine. The model's job is to select, explain and flag.
2. **Every statement is tagged.** The reader can tell a fact from a calculation, an assumption or the model's interpretation.
3. **The model's output is checked by code, not by another model.** `verify_note` rejects a note unless every figure is bound to the tool field it came from (value, unit, cited tool and wording). The extraction prompt requires the source line for every figure, and the app checks the JSON against its schema.
4. **Decision support only.** Every prompt forbids recommendations. The committee decides.

## AI use during development

LookThrough was built with AI coding assistance (Claude Code). This follows AICA Level 2 Modules 6 and 7, AI-assisted application development. Every figure the product shows is covered by the automated reconciliation and test suites in `verify/`.
