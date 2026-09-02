"""
RACM Generator — the core engine.
Combines COSO framework (ALL 5 components at once) + RACM schema + client
SOP text into ONE prompt per process, sent to Qwen via LM Studio.

v3 updates:
- max_tokens increased to 6000 (more room to cover all 17 principles evenly)
- Hard requirement for balanced principle coverage (min. 2 rows per principle,
  or an explicit "Not applicable" row instead of silent omission)
- Standardized "Reference (COSO Principle)" formatting to avoid inconsistent
  values like "Principle 5" vs "Principle 5: Enforces Accountability"
"""

import json
import requests
from coso_framework import COSO_FRAMEWORK
from racm_schema import RACM_COLUMNS

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"


def trim_sop_text(sop_text, max_chars=6000):
    """
    Keeps the prompt a manageable size for a local 7B model.
    """
    if len(sop_text) > max_chars:
        return sop_text[:max_chars]
    return sop_text


def build_full_framework_text():
    """
    Converts the entire COSO framework (5 components, 17 principles)
    into one structured text block for the prompt.
    """
    lines = []
    for comp in COSO_FRAMEWORK:
        lines.append(f"\nCOSO COMPONENT: {comp['component']}")
        for p in comp["principles"]:
            lines.append(f"  Principle {p['number']}: {p['title']}")
    return "\n".join(lines)


def build_prompt(sop_text, process_name):
    column_list = "\n".join([f"  {i+1}. {col}" for i, col in enumerate(RACM_COLUMNS)])
    framework_text = build_full_framework_text()

    prompt = f"""You are an internal controls and audit expert. Build a complete Risk and Control Matrix (RACM) for ONE specific business process, covering ALL FIVE COSO components and ALL 17 principles below, by comparing the CLIENT SOP TEXT against COSO best-practice requirements.

BUSINESS PROCESS TO FOCUS ON: {process_name}

FULL COSO FRAMEWORK TO COVER (all 5 components, all 17 principles):
{framework_text}

CLIENT SOP TEXT (full document, focus only on parts relevant to "{process_name}"):
\"\"\"
{sop_text}
\"\"\"

INSTRUCTIONS:
1. Focus ONLY on the "{process_name}" process. Ignore SOP content belonging to other processes.
2. MANDATORY COVERAGE RULE: You MUST include AT LEAST 2 rows for EACH of the 17 principles listed above — no principle may be skipped. If a principle is genuinely not applicable to this process, still include exactly 1 row for it with "Control Activity" set to "Not applicable — no relevant activity identified in SOP for this process" and "Design Deficiency (Yes/No)" set to "No".
3. For principles where relevant risks/controls DO exist, identify ALL of them — there may be more than 2 rows per principle where warranted. Do not stop at the minimum if more genuine risks exist.
4. In addition to the 17 standard COSO principles, also include any PROCESS-SPECIFIC risks relevant to "{process_name}" that a best-practice control framework would expect (e.g., segregation of duties, authorization limits, reconciliation, system access controls) even if not explicitly tied to a single principle. Map each to the closest matching principle number.
5. If the SOP text clearly describes a control matching a risk, create a row documenting it. Set "Design Deficiency (Yes/No)" to "No".
6. If the SOP is silent, vague, or weak on a risk that COSO best practice requires, STILL create a row for that best-practice control. Set "Design Deficiency (Yes/No)" to "Yes", and explain exactly what is missing in "Design Deficiency Description".
7. Leave "Operating Effectiveness Deficiency (Yes/No)" and "Operating Deficiency Description" blank ("") for now.
8. Assign realistic values for Financial Statement Assertion, Control Type (Preventive/Detective), Manual / Automated, and Control Frequency.
9. Keep each text field CONCISE — one short sentence per field. This is essential to fit full, balanced coverage of all 17 principles into one response.
10. STRICT FORMAT RULE for "Reference (COSO Principle)": this field must ALWAYS contain ONLY the format "Principle N" where N is the number (e.g., "Principle 5"). NEVER include the principle title or any other text in this field.
11. Output ONLY a valid JSON array of row objects. No explanation, no markdown, no code fences.

Each row object must have EXACTLY these 17 keys, spelled exactly as shown:
{column_list}

Begin the JSON array now:"""
    return prompt


def call_qwen(prompt, max_tokens=6000):
    """
    Sends the prompt to LM Studio's local Qwen model and returns the raw text reply.
    max_tokens raised to 6000 to give enough room for balanced coverage
    of all 17 principles without truncation.
    """
    payload = {
        "model": "qwen2.5-7b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }

    response = requests.post(LM_STUDIO_URL, json=payload, timeout=900)
    result = response.json()

    if "choices" not in result:
        print("\n[ERROR] LM Studio did not return a normal response. Raw reply was:")
        print(result)
        print("\nThis usually means: the model isn't loaded, the server isn't running,")
        print("or LM Studio is still restarting after a settings change.")
        print("Fix: check LM Studio, ensure model is loaded and server shows 'running', then retry.\n")
        raise RuntimeError("LM Studio response missing 'choices' — see details above.")

    content = result["choices"][0]["message"]["content"]
    finish_reason = result["choices"][0].get("finish_reason", "unknown")
    return content, finish_reason


def repair_truncated_json(raw_text):
    """
    If the AI's output got cut off mid-way, this attempts to salvage all
    COMPLETE row objects and discard the incomplete trailing one.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objects.append(cleaned[start:i + 1])
                start = None

    rows = []
    for obj_text in objects:
        try:
            rows.append(json.loads(obj_text))
        except json.JSONDecodeError:
            continue
    return rows


def normalize_reference_field(rows):
    """
    Cleans up the 'Reference (COSO Principle)' field so every row uses the
    exact same format: "Principle N". Strips any trailing title text the
    model may have added despite instructions (e.g., "Principle 5: Enforces
    Accountability" -> "Principle 5").
    """
    import re
    for row in rows:
        ref = row.get("Reference (COSO Principle)", "")
        if ref:
            match = re.search(r"Principle\s*(\d+)", str(ref), re.IGNORECASE)
            if match:
                row["Reference (COSO Principle)"] = f"Principle {match.group(1)}"
    return rows


def check_principle_coverage(rows):
    """
    Reports which of the 17 principles are missing or under-covered (0 rows)
    in this process's output, so gaps are visible immediately in the terminal
    rather than discovered later during manual review.
    """
    import re
    covered = set()
    for row in rows:
        ref = str(row.get("Reference (COSO Principle)", ""))
        match = re.search(r"Principle\s*(\d+)", ref, re.IGNORECASE)
        if match:
            covered.add(int(match.group(1)))

    all_principles = set(range(1, 18))
    missing = sorted(all_principles - covered)
    if missing:
        print(f"  [Notice] Principles with NO rows in this process: {missing}")
    return missing


def clean_and_parse_json(raw_text):
    """
    Parses the AI's JSON output. Falls back to salvaging complete rows only
    if standard parsing fails (e.g., due to truncation).
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        rows = json.loads(cleaned)
    except json.JSONDecodeError:
        print("  [Notice] Output was incomplete or malformed — attempting to recover complete rows...")
        rows = repair_truncated_json(raw_text)
        if rows:
            print(f"  [Notice] Recovered {len(rows)} complete row(s) despite truncation.")
        else:
            print("\n--- RAW AI OUTPUT (for debugging) ---")
            print(raw_text)
            print("--- END RAW OUTPUT ---\n")
            raise ValueError("Could not parse or recover any valid rows from AI response.")

    rows = normalize_reference_field(rows)
    return rows


def generate_racm_for_process(sop_text, process_name):
    """
    Full pipeline for ONE process, covering ALL COSO components in a single call:
    build prompt -> call Qwen -> parse JSON rows -> normalize -> check coverage.
    """
    sop_text = trim_sop_text(sop_text)
    prompt = build_prompt(sop_text, process_name)
    raw_reply, finish_reason = call_qwen(prompt)

    if finish_reason == "length":
        print("  [Notice] Model hit its token limit before finishing naturally.")

    rows = clean_and_parse_json(raw_reply)
    check_principle_coverage(rows)
    return rows