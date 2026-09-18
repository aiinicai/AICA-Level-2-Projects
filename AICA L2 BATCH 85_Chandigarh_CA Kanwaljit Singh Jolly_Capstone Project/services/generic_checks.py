"""
Generic deterministic checks.

For deterministic/hybrid criteria whose structure can be inferred, compute an
authoritative PASS/FAIL without an LLM. The most broadly useful structure is
table reconciliation: input record(s) must appear, correctly, in the output.
We auto-detect a shared key column between input and output tables and compute:

- coverage:   every input key present in the output
- value match: shared columns agree for keys present on both sides
- row count:  input vs output row counts
- required:   no empty cells in the output's compared columns

Each computed fact is mapped to matching deterministic criteria by keywords in the
criterion statement / how_to_verify. Criteria we can't map are left to the AI
validator. Results are returned as {criterion_id: {status, detail}} and are treated
as ground truth by services/generic_validator.py.
"""

import difflib
import re
from typing import Any, Dict, List, Optional

from models.check_spec import CheckSpec

# A pair of tables is only treated as a real input->output reconciliation when the
# chosen key column genuinely overlaps. Below this, the tables are unrelated (they
# merely share a column name) and must NOT yield a deterministic FAIL.
_MIN_KEY_OVERLAP = 0.5   # fraction of input keys that must appear in the output
_MIN_OVERLAP_KEYS = 1    # and at least one key must actually match (fraction gate does the work)

# keyword sets for mapping criteria to computed facts
_COVERAGE_WORDS = ("every", "all ", "each", "present", "appear", "missing", "coverage",
                   "included", "no input", "every input", "transferred", "carried over")
_VALUE_WORDS = ("match", "matches", "equal", "same", "correct", "consistent", "agree",
                "value", "amount", "accurate", "unchanged", "identical")
_COUNT_WORDS = ("count", "number of", "same number", "row count", "as many", "totals match")
_REQUIRED_WORDS = ("required", "non-empty", "not blank", "not empty", "mandatory", "filled", "populated")

# A criterion about STRUCTURE / NAMING / FORMAT / LAYOUT is not a row-level
# reconciliation: a coverage/value/count fact computed over data rows says nothing
# about it, so the row-reconcile checks must NOT decide it (it goes to the AI). This
# is what stops a "rows missing/mismatch" fact from being sprayed onto a filename,
# sheet-name, metadata-cell, column-presence, ordering, or grouping criterion.
_STRUCTURAL_WORDS = (
    "file name", "filename", "file is named", "named", "naming", "pattern",
    "sheet", "tab ", "worksheet", "workbook",
    "column", "header", "cell", "row 8", "row 9", "starts on row", "start on row",
    "b1:b6", "metadata", "first sheet", "second sheet", "sequence number",
    "format", "formatted", "layout", "order", "ordering", "sorted", "position",
    "grouped", "grouping", "timestamp", "title", "label", "section", "heading",
)

# A criterion about the output's own DERIVED / COMPUTED logic — values the output
# calculates (differences, totals), selection logic (which rows it chose to include),
# or generated explanations — is NOT verifiable by an input->output record carryover
# reconcile (which only checks that input values appear correctly in the output). The
# raw reconcile fact says nothing about whether a computed difference, a Matched/
# Mismatched flag, an exception-report selection, or a written reason is *correct*,
# so these must go to the AI rather than get a confident (and bogus) deterministic FAIL.
_DERIVED_LOGIC_WORDS = (
    "exception", "remark", "reason", "explanation", "explain",
    "only include", "only contain", "only show", "only list", "only the",
    "flagged", "indicate", "matched", "mismatched", "discrepanc",
    "derived", "computed", "calculate", "difference", "differ",
)

# text/prose checks
_PRESENCE_WORDS = ("include", "contain", "present", "section", "heading", "mention",
                   "state", "list", "show", "display", "appear", "header", "field", "label")
_NONEMPTY_WORDS = ("non-empty", "not empty", "not blank", "must exist", "is present",
                   "must be present", "provided", "populated", "must not be empty")


def _norm(v: Any) -> str:
    """Normalize a cell value for comparison (numeric-aware)."""
    if v is None:
        return ""
    s = str(v).strip()
    if s == "":
        return ""
    cleaned = s.replace(",", "").replace("₹", "").replace("$", "").strip()
    try:
        f = float(cleaned)
        return f"{f:.4f}".rstrip("0").rstrip(".")
    except (ValueError, TypeError):
        return s.casefold()


def _collect_tables(normalized_data: Dict[str, Any], side: str) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for art in (normalized_data or {}).get(side, []):
        for t in art.get("tables", []) or []:
            if t.get("headers") and t.get("rows"):
                tables.append({"file": art.get("file"), **t})
    return tables


def _rows_as_dicts(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    headers = table["headers"]
    out = []
    for row in table["rows"]:
        out.append({headers[i]: row[i] for i in range(min(len(headers), len(row)))})
    return out


def _norm_header(h: Any) -> str:
    """Normalize a column header so renamed/reformatted columns still match."""
    return re.sub(r'[^a-z0-9]', '', str(h).lower())


# Headers that name a within-sheet row counter, not a real entity identifier.
_SERIAL_HEADERS = {"sno", "srno", "srnno", "sr", "sl", "slno", "serial", "serialno",
                   "index", "idx", "rowno", "row", "no", "num", "number", "sequence", "seq"}


def _is_serial_header(header: Any) -> bool:
    return _norm_header(header) in _SERIAL_HEADERS


# Header fragments that signal a genuine entity identifier (preferred as the key).
_IDENTIFIER_HINTS = ("id", "regno", "registrationno", "admno", "admissionno", "rollno",
                     "roll", "code", "pan", "refno", "reference", "empno", "employeeno",
                     "studentid", "accountno", "acno", "uid", "gstin", "invoiceno")


def _is_identifier_header(header: Any) -> bool:
    h = _norm_header(header)
    return any(hint == h or h.endswith(hint) or h.startswith(hint) for hint in _IDENTIFIER_HINTS)


def _is_serial_values(values: List[str]) -> bool:
    """True when the values are a contiguous row counter (1,2,3,…), not real IDs.

    Serial/index columns are unique and overlap across sheets by coincidence (every
    sheet has 1..N), so they sneak past the uniqueness + overlap gates and fabricate
    bogus 'missing'/'mismatch' findings. Real identifiers (Reg No 1081, 1123, …) are
    unique but NOT a dense 1..N run, so this rejects only true serials.
    """
    nums: List[int] = []
    for v in values:
        try:
            f = float(v)
        except (ValueError, TypeError):
            return False  # any non-numeric value -> not a serial counter
        if f != int(f):
            return False
        nums.append(int(f))
    uniq = sorted(set(nums))
    if len(uniq) < 5:
        return False  # too few to judge; don't over-reject
    # Dense run starting near the top (covers its own range with few gaps).
    span = uniq[-1] - uniq[0] + 1
    return uniq[0] <= 2 and span <= len(uniq) * 1.2


def _map_columns(in_headers: List[Any], out_headers: List[Any]) -> Dict[Any, Any]:
    """
    Best-effort input->output column correspondence that survives renames
    (case, spaces, punctuation, minor wording). Each output column is used once.
    """
    norm_out = [(oh, _norm_header(oh)) for oh in out_headers]
    mapping: Dict[Any, Any] = {}
    used = set()
    for ih in in_headers:
        nih = _norm_header(ih)
        if not nih:
            continue
        best, best_score = None, 0.0
        for oh, noh in norm_out:
            if oh in used or not noh:
                continue
            if nih == noh:
                score = 1.0
            elif nih in noh or noh in nih:
                score = 0.92
            else:
                score = difflib.SequenceMatcher(None, nih, noh).ratio()
            if score > best_score:
                best, best_score = oh, score
        if best is not None and best_score >= 0.85:
            mapping[ih] = best
            used.add(best)
    return mapping


def _reconcile_pair(it: Dict[str, Any], ot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Reconcile one input table against one output table. None if no usable key."""
    col_map = _map_columns(it["headers"], ot["headers"])
    if not col_map:
        return None

    in_rows = _rows_as_dicts(it)
    out_rows = _rows_as_dicts(ot)

    # Choose the key. A candidate must be ~unique and genuinely overlap the output
    # (overlap gate: an unrelated table sharing a column name has ~0 overlap and is
    # rejected, so we never fabricate an "everything missing" FAIL). Among valid
    # candidates we rank by a tiered priority so a real identifier wins over a
    # coincidental one:
    #   1. header looks like an identifier (id / regNo / code …)  — strongest signal
    #   2. values are NOT a 1..N row counter (serials rank lower)
    #   3. higher uniqueness*overlap score
    best_key = best_outcol = None
    best_priority = None
    for ih, oh in col_map.items():
        # A within-sheet row counter named like one (S.No / Sr / index) is never a key.
        if _is_serial_header(ih) or _is_serial_header(oh):
            continue
        in_vals = [_norm(r.get(ih)) for r in in_rows if _norm(r.get(ih))]
        if not in_vals:
            continue
        out_vals = {_norm(r.get(oh)) for r in out_rows if _norm(r.get(oh))}
        in_set = set(in_vals)
        overlap_n = len(in_set & out_vals)
        uniqueness = len(in_set) / len(in_vals)
        overlap = overlap_n / len(in_set)
        if uniqueness < 0.9:
            continue
        # Overlap gate before a candidate is even considered.
        if overlap < _MIN_KEY_OVERLAP or overlap_n < _MIN_OVERLAP_KEYS:
            continue
        score = uniqueness * (0.5 + 0.5 * overlap)
        priority = (_is_identifier_header(ih), not _is_serial_values(in_vals), score)
        if best_priority is None or priority > best_priority:
            best_priority = priority
            best_key, best_outcol = ih, oh
    if best_key is None:
        return None

    out_by_key: Dict[str, Dict[str, Any]] = {}
    for r in out_rows:
        k = _norm(r.get(best_outcol))
        if k and k not in out_by_key:
            out_by_key[k] = r
    in_keys = {_norm(r.get(best_key)) for r in in_rows if _norm(r.get(best_key))}
    missing = sorted(k for k in in_keys if k not in out_by_key)

    compare = {ih: oh for ih, oh in col_map.items() if ih != best_key}
    mismatches: List[Dict[str, Any]] = []
    empty_cells = 0
    for r in in_rows:
        k = _norm(r.get(best_key))
        if not k or k not in out_by_key:
            continue
        orow = out_by_key[k]
        for ih, oh in compare.items():
            iv, ov = _norm(r.get(ih)), _norm(orow.get(oh))
            if ov == "":
                empty_cells += 1
            if iv != ov:
                mismatches.append({"key": k, "column": ih, "input": r.get(ih), "output": orow.get(oh)})

    return {
        "in_file": it.get("file"),
        "out_file": ot.get("file"),
        "key_column": best_key,
        "out_key_column": best_outcol,
        "input_count": len(in_rows),
        "output_count": len(out_rows),
        "missing_keys": missing,
        "compared_columns": list(compare.keys()),
        "value_mismatches": mismatches,
        "empty_cells": empty_cells,
    }


def _compute_facts(normalized_data: Dict[str, Any]) -> Dict[str, Any]:
    """Reconcile EVERY plausible input/output table pair on full data."""
    in_tables = _collect_tables(normalized_data, "normalized_inputs")
    out_tables = _collect_tables(normalized_data, "normalized_outputs")
    if not in_tables or not out_tables:
        return {"has_tables": bool(in_tables or out_tables), "pairs": [],
                "input_table_count": len(in_tables), "unreconciled_input_tables": len(in_tables),
                "total_input_rows": sum(len(t["rows"]) for t in in_tables),
                "total_output_rows": sum(len(t["rows"]) for t in out_tables)}

    # Greedy: each input table claims its best-reconciling unused output table.
    pairs: List[Dict[str, Any]] = []
    used_out = set()
    for it in in_tables:
        best_pair, best_quality, best_idx = None, -1, None
        for idx, ot in enumerate(out_tables):
            if idx in used_out:
                continue
            rec = _reconcile_pair(it, ot)
            if rec is None:
                continue
            quality = len(rec["compared_columns"]) + (rec["input_count"] - len(rec["missing_keys"]))
            if quality > best_quality:
                best_pair, best_quality, best_idx = rec, quality, idx
        if best_pair is not None:
            pairs.append(best_pair)
            used_out.add(best_idx)

    return {
        "has_tables": True,
        "pairs": pairs,
        "input_table_count": len(in_tables),
        "unreconciled_input_tables": len(in_tables) - len(pairs),
        "total_input_rows": sum(len(t["rows"]) for t in in_tables),
        "total_output_rows": sum(len(t["rows"]) for t in out_tables),
    }


def _matches(text: str, words) -> bool:
    return any(w in text for w in words)


def _output_text(normalized_data: Dict[str, Any]) -> str:
    """Concatenate the uniform text view of all output artifacts."""
    parts = []
    for art in (normalized_data or {}).get("normalized_outputs", []):
        t = (art.get("text") or "").strip()
        if t:
            parts.append(t)
    return "\n".join(parts)


def _output_has_tables(normalized_data: Dict[str, Any]) -> bool:
    """True when any output artifact is tabular (a spreadsheet), not prose."""
    for art in (normalized_data or {}).get("normalized_outputs", []):
        for t in art.get("tables", []) or []:
            if t.get("headers") and t.get("rows"):
                return True
    return False


def _quoted_phrases(text: str) -> List[str]:
    """Extract concrete literal phrases from a criterion (quoted or `code` spans)."""
    phrases = re.findall(r'"([^"]{2,80})"', text)
    # Opening single-quote must be at a word boundary, so an apostrophe inside a word
    # (class's, student's) does NOT start a bogus span like "s student list ...".
    phrases += re.findall(r"(?<![A-Za-z])'([^']{2,80})'", text)
    phrases += re.findall(r"`([^`]{2,80})`", text)
    seen, out = set(), []
    for p in phrases:
        key = p.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            out.append(p.strip())
    return out


def _apply_table_checks(check_spec, facts, results) -> None:
    pairs = facts.get("pairs", [])
    reconciled = len(pairs) > 0
    # Only assert a deterministic PASS for coverage/value/required when EVERY input
    # table was reconciled — otherwise unseen tables could hide problems (no false PASS).
    fully_reconciled = reconciled and facts.get("unreconciled_input_tables", 0) == 0

    all_missing = [(p["key_column"], k) for p in pairs for k in p["missing_keys"]]
    all_mismatches = [
        {**m, "in_file": p["in_file"], "out_file": p["out_file"]}
        for p in pairs for m in p["value_mismatches"]
    ]
    total_empty = sum(p["empty_cells"] for p in pairs)
    bad_counts = [(p["in_file"], p["input_count"], p["output_count"])
                  for p in pairs if p["input_count"] != p["output_count"]]
    total_in = facts.get("total_input_rows")
    total_out = facts.get("total_output_rows")

    def emit(cid, fail, pass_detail, fail_detail, pass_allowed):
        if fail:
            results[cid] = {"status": "FAIL", "detail": fail_detail}
        elif pass_allowed:
            results[cid] = {"status": "PASS", "detail": pass_detail}
        # else: leave undecided -> AI validator handles it

    for c in check_spec.deterministic_criteria:
        text = f"{c.statement} {c.how_to_verify}".casefold()

        # Structural/naming/format criteria, and criteria about the output's own
        # derived/computed logic, are NOT row-carryover reconciliation: a
        # rows-missing/mismatch fact is irrelevant to them, so defer to the AI
        # rather than stamp it (prevents confident-but-irrelevant FAILs).
        if _matches(text, _STRUCTURAL_WORDS) or _matches(text, _DERIVED_LOGIC_WORDS):
            continue

        # Order: coverage -> count -> value -> required (count before value because
        # "same number of rows" contains value-ish words but is about counts).
        if reconciled and _matches(text, _COVERAGE_WORDS):
            emit(c.id, bool(all_missing),
                 f"All input keys present across {len(pairs)} reconciled table(s).",
                 f"{len(all_missing)} input value(s) missing from output, e.g. {all_missing[:10]}",
                 fully_reconciled)
        elif _matches(text, _COUNT_WORDS):
            if reconciled:
                emit(c.id, bool(bad_counts),
                     f"Row counts match across {len(pairs)} reconciled table(s).",
                     f"Row count mismatch: {bad_counts[:5]}",
                     fully_reconciled)
            else:
                emit(c.id, total_in != total_out,
                     f"input rows={total_in}, output rows={total_out}",
                     f"input rows={total_in}, output rows={total_out}",
                     True)
        elif reconciled and _matches(text, _VALUE_WORDS):
            emit(c.id, bool(all_mismatches),
                 "All compared columns agree for shared keys.",
                 f"{len(all_mismatches)} value mismatch(es), e.g. {all_mismatches[:3]}",
                 fully_reconciled)
        elif reconciled and _matches(text, _REQUIRED_WORDS):
            emit(c.id, total_empty > 0,
                 "No empty cells in compared output columns.",
                 f"{total_empty} empty cell(s) in compared output columns",
                 fully_reconciled)


def _apply_text_checks(check_spec, normalized_data, results) -> None:
    """Document/prose checks: required literal phrases present, output non-empty.

    Phrase-presence matching is only reliable for PROSE outputs. Over a flattened
    spreadsheet a label may sit in any sheet/cell and the file name isn't in the
    content at all, which yields both false fails (a header it can't find, a filename)
    and weak "found a word somewhere" passes. So for tabular outputs we skip phrase
    matching and defer those criteria to the AI; the non-empty floor still applies.
    """
    out_text = _output_text(normalized_data)
    if not out_text.strip():
        return
    haystack = out_text.casefold()
    tabular = _output_has_tables(normalized_data)

    for c in check_spec.deterministic_criteria:
        if c.id in results:
            continue
        combined = f"{c.statement} {c.how_to_verify} {c.evidence_hint}"
        text = combined.casefold()

        phrases = _quoted_phrases(combined)
        if phrases and not tabular and _matches(text, _PRESENCE_WORDS):
            missing = [p for p in phrases if p.casefold() not in haystack]
            results[c.id] = {
                "status": "PASS" if not missing else "FAIL",
                "detail": (f"Output contains required text: {phrases}."
                           if not missing else f"Output is missing required text: {missing}"),
            }
        elif _matches(text, _NONEMPTY_WORDS):
            results[c.id] = {
                "status": "PASS",
                "detail": f"Output is non-empty ({len(out_text)} chars).",
            }


def run_generic_checks(check_spec: CheckSpec, normalized_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Return authoritative deterministic results: {criterion_id: {status, detail}}."""
    results: Dict[str, Dict[str, Any]] = {}

    facts = _compute_facts(normalized_data)
    if facts.get("has_tables"):
        _apply_table_checks(check_spec, facts, results)

    # Prose/document checks for any deterministic criterion not decided by tables.
    _apply_text_checks(check_spec, normalized_data, results)

    return results
