# FTA HSN Query — AI Workflow Automation Capstone

An n8n-based AI agent that answers Free Trade Agreement (FTA) compliance
questions — applicable customs duty rates, de minimis rules, cumulation,
Qualifying Value Content (QVC) build-up/build-down calculations — sourced
strictly from official CBIC notifications uploaded into a structured
document register, not from the model's general knowledge.

---

## Live links

| Item | Link |
|---|---|
| n8n workflow (editor) | https://baisakhi.app.n8n.cloud/workflow/U41XkqTj73dWOHsK |
| Public query form ("Check an HSN Code Against an FTA") | https://baisakhi.app.n8n.cloud/form/47b5eaa3-4070-4fbb-b4d6-6948f3221f10 |
| n8n instance (project home) | https://baisakhi.app.n8n.cloud |

---

## What it does

1. User fills a form: FTA name, importing/exporting/destination country,
   HSN code, question type, and a free-text question.
2. The workflow looks up:
   - An **exact HS-code rate** from a structured lookup table
     (`hs_rates_india_uk`, 11,116 rows — the full India-UK CETA tariff
     schedule, parsed from the source PDF; see `code/extract_and_parse_tariff_table.py`).
   - The **full text of every uploaded notification** for that FTA, stored
     in a second data table (`fta_documents`), including metadata on which
     notification amends/supersedes which (critical for FTAs like
     India-ASEAN AIFTA where the applicable rate table has been replaced
     five times since 2011).
   - A **direct text grep** of those full documents for the exact HSN code,
     as a second, independent confirmation alongside the structured lookup.
3. All of this is assembled into a single prompt (`code/n8n_node_2_build_agent_prompt.js`)
   and given to an AI agent (`code/n8n_node_3_fta_answer_agent_system_prompt.txt`)
   running on Google Gemini, with a live web-search tool available as a
   fallback for anything not covered by the uploaded documents.
4. The agent's HTML-formatted answer is styled (`code/n8n_node_4_format_html_response.js`)
   and shown back to the user on the form's completion page — with the
   statutory extract, a worked example where relevant, and a sources list.

A companion **Intake** workflow (not detailed in this package) lets a
compliance officer upload new PDF notifications, which get OCR'd, tagged
with FTA/notification metadata (date, amendment chain, change scope), and
added to the `fta_documents` register for future queries.

---

## Folder contents

```
code/
  n8n_node_2_build_agent_prompt.js          Core prompt-assembly logic (Code node)
  n8n_node_3_fta_answer_agent_system_prompt.txt  AI agent system prompt
  n8n_node_4_format_html_response.js        Answer HTML styling (Code node)
  extract_and_parse_tariff_table.py         PDF -> structured JSON tariff parser

data/
  hs_rates_india_uk.csv                     11,116-row India-UK CETA tariff
                                             schedule (HS code, BCD/AIDC/Health
                                             Cess rates), parsed from the
                                             official notification PDF

README.md                                   This file
```

---

## Architecture (n8n workflow: "FTA HSN Query")

```
HSN Query Form (trigger)
  -> Get HS Rate            [exact-match lookup against hs_rates_india_uk]
     -> Get Documents For FTA  [pulls all notifications for the selected FTA]
        -> Build Agent Prompt  [assembles lookup + grep + document excerpt]
           -> FTA Answer Agent [Gemini + Web Search tool]
              -> Format HTML Response
                 -> Show Answer [form completion page]
```

---

## Key engineering decisions

- **Structured lookup + full-text grep, in parallel.** A single 11,000-line
  tariff table can't fit in an LLM's context window alongside everything
  else, so exact rates are looked up two independent ways — a fast indexed
  table match, and a regex grep across the full source text — so either one
  can catch a code the other might miss, and they cross-verify each other.
- **Amendment-chain metadata.** Each stored notification records whether it
  fully replaces, partially amends, or merely adds to an earlier one, so the
  agent can correctly identify the *current* rate for an FTA like AIFTA that
  has been amended repeatedly since 2011, rather than citing a superseded
  rate.
- **Free-tier LLM constraints.** Google Gemini's free tier caps requests at
  250,000 tokens/minute and ~20 requests/day; the prompt-assembly logic
  budgets document text to stay well under the per-minute limit.
