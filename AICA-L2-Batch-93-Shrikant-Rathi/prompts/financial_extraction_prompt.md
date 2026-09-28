# Financial-statement extraction prompt (app → AI data extraction)

The user pastes an annual report's statement pages into any LLM (ChatGPT, Claude, Gemini, or an offline model in LM Studio) together with this prompt, then pastes the JSON reply back into the app. The app checks it against the schema, shows each figure next to its evidence line, and nothing is saved until a person approves it (maker-checker).

```
You are assisting a Chartered Accountant. Extract figures from the financial results pasted below for {company}, {fy}.

Rules:
1. Use only numbers that appear in the text. Do not estimate or compute missing values; return null instead.
2. Convert every amount to INR crore. State the unit you found in "source_unit".
3. Use the current-year column only. Ignore note references such as "(Note 3)".
4. "revenue" is revenue from operations, not total income.
5. For each field, quote the exact source line in "<field>_evidence".
6. Return valid JSON only, matching this schema:

{
  "company": "string",
  "fy": "{fy}",
  "source_unit": "crore | lakh | million",
  "revenue": number|null,     "revenue_evidence": "string",
  "ebitda": number|null,      "ebitda_evidence": "string",
  "pat": number|null,         "pat_evidence": "string",
  "net_worth": number|null,   "net_worth_evidence": "string",
  "total_debt": number|null,  "total_debt_evidence": "string",
  "cfo": number|null,         "cfo_evidence": "string"
}
```

Why the rules: rule 1 stops made-up numbers; rules 2 and 3 prevent unit and column mix-ups (lakh versus crore, prior year versus current year); rule 4 prevents a common definition error; rule 5 lets a person check each figure against its source line.
