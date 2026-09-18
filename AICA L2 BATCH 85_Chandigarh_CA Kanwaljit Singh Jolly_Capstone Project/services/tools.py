"""
Full-data check tools — the "pre-written code the model calls."

A validation model has a finite, expensive context, so we don't ask it to *read*
all the rows. Instead it calls these tools, which run over 100% of the normalized
data and return a SMALL result (a count, a short list, a reconciliation summary).
The model spends tokens on deciding which tool to call and reasoning over the tiny
results — so coverage is complete and cost stays flat as files grow.

Each tool is pure Python over the normalized `{normalized_inputs, normalized_outputs}`
shape. `TOOL_SCHEMAS` are OpenAI/Anthropic-style function schemas; `dispatch()` runs
a tool by name. This module is the testable foundation under the (separate) model-
driven tool loop — nothing here calls an LLM.
"""

import math
import re
from typing import Any, Dict, List, Optional, Tuple

from services.generic_checks import (
    _collect_tables,
    _norm,
    _reconcile_pair,
    _rows_as_dicts,
)

# Cap list sizes in tool results so a tool can never blow the model's context.
_MAX_ITEMS = 50

# Tiny stopword set so BM25 doesn't rank on filler words (the corpus is often small).
_STOPWORDS = frozenset((
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are", "was",
    "were", "be", "by", "with", "as", "at", "it", "this", "that", "these", "those",
    "from", "but", "not", "no", "if", "then", "than", "so", "such", "can", "will",
))

_SIDES = {"input": "normalized_inputs", "output": "normalized_outputs"}


def _side_key(side: str) -> str:
    return _SIDES.get((side or "").strip().lower(), "")


def _find_table(normalized_data: Dict[str, Any], side: str, name: Optional[str]) -> Optional[Dict[str, Any]]:
    key = _side_key(side)
    if not key:
        return None
    tables = _collect_tables(normalized_data, key)
    if not tables:
        return None
    if name:
        for t in tables:
            if str(t.get("name", "")).casefold() == name.casefold():
                return t
        # fall back to a fuzzy contains-match on the name
        for t in tables:
            if name.casefold() in str(t.get("name", "")).casefold():
                return t
        return None
    return tables[0]


def _cap(items: List[Any]) -> Dict[str, Any]:
    return {"total": len(items), "shown": items[:_MAX_ITEMS], "truncated": len(items) > _MAX_ITEMS}


# ==================== tools ====================

def list_tables(normalized_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enumerate every input/output table with headers + row counts (no row data)."""
    def describe(side_key):
        return [
            {"side": side, "name": t.get("name"), "file": t.get("file"),
             "headers": t.get("headers"), "row_count": len(t.get("rows") or [])}
            for side, sk in _SIDES.items() if sk == side_key
            for t in _collect_tables(normalized_data, side_key)
        ]
    tables = describe("normalized_inputs") + describe("normalized_outputs")
    return {"tables": tables, "count": len(tables)}


def count_rows(normalized_data: Dict[str, Any], side: str, table: Optional[str] = None,
               column: Optional[str] = None, equals: Optional[str] = None,
               non_empty: bool = False) -> Dict[str, Any]:
    """Count rows in a table, optionally filtered by column==equals or column non-empty."""
    t = _find_table(normalized_data, side, table)
    if not t:
        return {"error": f"no {side} table found" + (f" named '{table}'" if table else "")}
    rows = _rows_as_dicts(t)
    if column is None:
        return {"count": len(rows)}
    if column not in t["headers"]:
        return {"error": f"column '{column}' not in {t['headers']}"}
    if equals is not None:
        target = _norm(equals)
        n = sum(1 for r in rows if _norm(r.get(column)) == target)
    elif non_empty:
        n = sum(1 for r in rows if _norm(r.get(column)) != "")
    else:
        n = len(rows)
    return {"count": n, "of_total": len(rows)}


def lookup(normalized_data: Dict[str, Any], side: str, column: str, value: str,
           table: Optional[str] = None) -> Dict[str, Any]:
    """Return rows on a side where `column` equals `value` (normalized compare)."""
    t = _find_table(normalized_data, side, table)
    if not t:
        return {"error": f"no {side} table found" + (f" named '{table}'" if table else "")}
    if column not in t["headers"]:
        return {"error": f"column '{column}' not in {t['headers']}"}
    target = _norm(value)
    matches = [r for r in _rows_as_dicts(t) if _norm(r.get(column)) == target]
    return {"matches": _cap(matches), "key_column": column, "value": value}


def get_rows(normalized_data: Dict[str, Any], side: str, start: int = 0, count: int = 20,
             table: Optional[str] = None) -> Dict[str, Any]:
    """Fetch a slice of rows [start, start+count) for targeted inspection."""
    t = _find_table(normalized_data, side, table)
    if not t:
        return {"error": f"no {side} table found" + (f" named '{table}'" if table else "")}
    start = max(0, int(start))
    count = max(1, min(int(count), _MAX_ITEMS))
    rows = _rows_as_dicts(t)
    return {"rows": rows[start:start + count], "start": start,
            "returned": len(rows[start:start + count]), "row_count": len(rows)}


def aggregate(normalized_data: Dict[str, Any], side: str, column: str, op: str = "sum",
              table: Optional[str] = None) -> Dict[str, Any]:
    """sum/avg/min/max/count of a numeric column over the FULL table."""
    t = _find_table(normalized_data, side, table)
    if not t:
        return {"error": f"no {side} table found" + (f" named '{table}'" if table else "")}
    if column not in t["headers"]:
        return {"error": f"column '{column}' not in {t['headers']}"}
    nums: List[float] = []
    for r in _rows_as_dicts(t):
        nv = _norm(r.get(column))
        try:
            nums.append(float(nv))
        except (ValueError, TypeError):
            continue
    if not nums:
        return {"error": f"column '{column}' has no numeric values"}
    op = (op or "sum").lower()
    result = {"sum": sum(nums), "avg": sum(nums) / len(nums), "min": min(nums),
              "max": max(nums), "count": len(nums)}.get(op)
    if result is None:
        return {"error": f"unknown op '{op}' (use sum/avg/min/max/count)"}
    return {"op": op, "column": column, "result": result, "n": len(nums)}


def _tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(t) > 1 and t not in _STOPWORDS]


def _passages(text: str, file: str) -> List[Tuple[str, str]]:
    """Split a document into passages (paragraphs, long ones windowed) for ranking."""
    out: List[Tuple[str, str]] = []
    for para in re.split(r"\n\s*\n", text or ""):
        para = para.strip()
        if not para:
            continue
        if len(para) <= 500:
            out.append((file, para))
        else:  # window long paragraphs so a snippet stays readable
            for i in range(0, len(para), 400):
                out.append((file, para[i:i + 400]))
    return out


def _bm25_rank(passages: List[Tuple[str, str]], query: str, top_k: int) -> List[Dict[str, Any]]:
    """Rank passages against the query with BM25 (Okapi, k1=1.5, b=0.75). Pure Python."""
    q_terms = _tokenize(query)
    if not passages or not q_terms:
        return []
    docs = [_tokenize(text) for _f, text in passages]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n if n else 0.0
    df: Dict[str, int] = {}
    for d in docs:
        for term in set(d):
            df[term] = df.get(term, 0) + 1
    k1, b = 1.5, 0.75
    scored = []
    for idx, d in enumerate(docs):
        if not d:
            continue
        dl = len(d)
        tf: Dict[str, int] = {}
        for term in d:
            tf[term] = tf.get(term, 0) + 1
        score = 0.0
        for term in q_terms:
            f = tf.get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        if score > 0:
            file, text = passages[idx]
            scored.append({"file": file, "where": "text", "score": round(score, 3),
                           "snippet": text[:300]})
    scored.sort(key=lambda h: h["score"], reverse=True)
    return scored[:top_k]


def search_text(normalized_data: Dict[str, Any], query: str, side: Optional[str] = None,
                top_k: int = 5) -> Dict[str, Any]:
    """Find content relevant to `query`.

    Prose is ranked by BM25 (lexical relevance — recall on term overlap, not just an
    exact substring), so a partial/paraphrased query still surfaces the right passage.
    Table cells use exact substring matching (you want precise value hits there).
    """
    if not (query or "").strip():
        return {"error": "empty query"}
    top_k = max(1, min(int(top_k or 5), _MAX_ITEMS))
    q_cf = query.casefold()
    sides = [_side_key(side)] if side else list(_SIDES.values())

    all_passages: List[Tuple[str, str]] = []
    table_hits: List[Dict[str, Any]] = []
    for sk in sides:
        if not sk:
            continue
        for art in (normalized_data or {}).get(sk, []):
            all_passages.extend(_passages(art.get("text") or "", art.get("file")))
            for t in art.get("tables", []) or []:
                for i, row in enumerate(t.get("rows") or []):
                    if any(q_cf in str(cell).casefold() for cell in row):
                        table_hits.append({"file": art.get("file"),
                                           "where": f"table '{t.get('name')}' row {i}", "row": row})

    ranked_prose = _bm25_rank(all_passages, query, top_k)
    hits = ranked_prose + table_hits
    return {"query": query, "matches": _cap(hits), "ranking": "bm25"}


def reconcile(normalized_data: Dict[str, Any], input_table: Optional[str] = None,
              output_table: Optional[str] = None) -> Dict[str, Any]:
    """Full input->output reconciliation (coverage, value match, empties) over all rows."""
    it = _find_table(normalized_data, "input", input_table)
    ot = _find_table(normalized_data, "output", output_table)
    if not it or not ot:
        return {"error": "need both an input and an output table to reconcile"}
    res = _reconcile_pair(it, ot)
    if res is None:
        return {"error": "no shared key column could be inferred between the tables"}
    # keep full counts, but bound the potentially large example lists
    res["missing_key_count"] = len(res["missing_keys"])
    res["value_mismatch_count"] = len(res["value_mismatches"])
    res["missing_keys"] = res["missing_keys"][:_MAX_ITEMS]
    res["value_mismatches"] = res["value_mismatches"][:_MAX_ITEMS]
    return res


# ==================== registry ====================

_TOOLS = {
    "list_tables": list_tables,
    "count_rows": count_rows,
    "lookup": lookup,
    "get_rows": get_rows,
    "aggregate": aggregate,
    "search_text": search_text,
    "reconcile": reconcile,
}


def dispatch(name: str, args: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
    """Run a tool by name with kwargs; never raises — returns {'error': ...} on failure."""
    fn = _TOOLS.get(name)
    if fn is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        return fn(normalized_data, **(args or {}))
    except TypeError as e:
        return {"error": f"bad arguments for '{name}': {e}"}
    except Exception as e:  # noqa: BLE001 - a tool failure must not crash the validator
        return {"error": f"tool '{name}' failed: {e}"}


def _s(props, required):
    return {"type": "object", "properties": props, "required": required}


# OpenAI/Anthropic-compatible function schemas (normalized_data is injected by the harness).
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {"name": "list_tables", "description": "List every input/output table with headers and row counts.",
     "parameters": _s({}, [])},
    {"name": "count_rows", "description": "Count rows in a table, optionally where column==equals or column is non-empty.",
     "parameters": _s({
         "side": {"type": "string", "enum": ["input", "output"]},
         "table": {"type": "string", "description": "table name (optional; defaults to first)"},
         "column": {"type": "string"}, "equals": {"type": "string"},
         "non_empty": {"type": "boolean"}}, ["side"])},
    {"name": "lookup", "description": "Return rows on a side where a column equals a value.",
     "parameters": _s({
         "side": {"type": "string", "enum": ["input", "output"]},
         "column": {"type": "string"}, "value": {"type": "string"},
         "table": {"type": "string"}}, ["side", "column", "value"])},
    {"name": "get_rows", "description": "Fetch a slice of rows [start, start+count) for inspection.",
     "parameters": _s({
         "side": {"type": "string", "enum": ["input", "output"]},
         "start": {"type": "integer"}, "count": {"type": "integer"},
         "table": {"type": "string"}}, ["side"])},
    {"name": "aggregate", "description": "sum/avg/min/max/count of a numeric column over the whole table.",
     "parameters": _s({
         "side": {"type": "string", "enum": ["input", "output"]},
         "column": {"type": "string"},
         "op": {"type": "string", "enum": ["sum", "avg", "min", "max", "count"]},
         "table": {"type": "string"}}, ["side", "column"])},
    {"name": "search_text",
     "description": "Find relevant content: prose ranked by BM25 lexical relevance (handles partial/"
                    "paraphrased queries), table cells by exact substring. Returns top passages + cell hits.",
     "parameters": _s({
         "query": {"type": "string"},
         "side": {"type": "string", "enum": ["input", "output"]},
         "top_k": {"type": "integer", "description": "max prose passages to return (default 5)"}}, ["query"])},
    {"name": "reconcile", "description": "Full input->output reconciliation: coverage, value matches, empties.",
     "parameters": _s({
         "input_table": {"type": "string"}, "output_table": {"type": "string"}}, [])},
]
