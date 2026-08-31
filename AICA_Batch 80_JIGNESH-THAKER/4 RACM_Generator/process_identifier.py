"""
Process Identifier — detects distinct business sub-processes described
within a single SOP document (e.g., "Accounts Payable", "Payroll").
This ensures the final RACM covers EVERY process in the document,
not just the first one.
"""

import json
import requests

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"


def identify_processes(sop_text, max_chars=8000):
    excerpt = sop_text[:max_chars]

    prompt = f"""You are reviewing a company's Standard Operating Procedures (SOP) document, which may describe MULTIPLE distinct business processes.

SOP TEXT:
\"\"\"
{excerpt}
\"\"\"

TASK: Identify every distinct business process described in this document (e.g., "Procure-to-Pay", "Order-to-Cash", "Payroll", "Fixed Assets", "Treasury", "Inventory Management", "Financial Close").

Output ONLY a valid JSON array of short process name strings. No explanation, no markdown, no code fences. Example:
["Procure-to-Pay", "Payroll", "Fixed Assets"]

If you cannot clearly identify distinct processes, return exactly: ["General"]

Begin the JSON array now:"""

    payload = {
        "model": "qwen2.5-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 300
    }

    response = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
    result = response.json()

    if "choices" not in result:
        print("\n[ERROR] LM Studio did not return a normal response. Raw reply was:")
        print(result)
        print("\nThis usually means: the model isn't loaded, the server isn't running,")
        print("or LM Studio is still restarting after a settings change.")
        print("Fix: check LM Studio, ensure model is loaded and server shows 'running', then retry.\n")
        raise RuntimeError("LM Studio response missing 'choices' — see details above.")

    raw = result["choices"][0]["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        processes = json.loads(raw)
        if isinstance(processes, list) and len(processes) > 0:
            return processes
    except json.JSONDecodeError:
        pass

    return ["General"]