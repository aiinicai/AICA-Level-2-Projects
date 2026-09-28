# `ic_note` prompt (MCP server)

**Parameters:** `question` (text) and `member` (default `ALL`).

```
Prepare an investment-committee note on: {question}
Entity: {member}

Use the LookThrough tools for every figure (start with list_entities and data_provenance). Structure:
1. Question and scope (entity, valuation date from the tools).
2. Key facts - each line tagged [FACT] or [CALC] with the tool it came from.
3. Analysis - tag interpretations [VIEW] and inputs [ASSUMPTION].
4. Policy position - results of policy_check.
5. Risks and what would change the conclusion.
6. Options for the committee with trade-offs. Do not recommend buying or selling; the committee decides.
7. Data limitations - from the caveats and data_provenance.

Quote figures exactly as returned, with units, and end each line with every tool its figures came from, in
parentheses, e.g. (fund_overlap; policy_check). Then call verify_note with the complete note; if any figure is
untraced, correct or remove it and verify again. Present the note only when verify_note passes, and state that it passed.
```

The note this prompt produced is in [../examples/sample_ic_note.md](../examples/sample_ic_note.md): 32 figures, each bound to the tool field it came from.
