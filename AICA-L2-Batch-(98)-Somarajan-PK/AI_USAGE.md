# AI Usage Log

| Area | AI tool | What AI did | What the human did |
|---|---|---|---|
| Design and code | Claude | Drafted the Python code, web UI and tests from my requirements | Defined requirements, ran and tested the tool, directed redesigns (app-first flow, Tally pull, bank selection, approval gate) |
| Test data | Claude (code) | Wrote a generator for fictional bank data with 19 planted issues | Reviewed that the data is entirely fictional |
| Commentary (optional) | Claude | Drafts an audit memo from the tool's numeric summary | Reviews and edits; AI never calculates |
| Presentation | Claude | Drafted the slide deck | Reviewed content and figures |

## Data protection
- Only synthetic data was used with AI tools.
- No client, personal or confidential information was entered into any AI platform.
- The tool itself runs locally; no data is sent to any AI service by the application.

## Verification
- All numbers come from the Python engine and are checked by the test scripts.
- The Excel BRS uses formulas that recalculate with zero errors.
- Professional judgement and approval stay with the reviewer.
