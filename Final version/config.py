"""
config.py — R K Muley & Co | Tax Notice Litigation Assistant v8.0
All constants, feature flags, section index, prompts, verified case laws.
No Streamlit imports here — pure Python, importable in tests.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

# ── App Identity ──────────────────────────────────────────────────────────────
APP_VERSION   = "9.0.0-beta"
APP_NAME      = "Tax Notice Litigation Assistant"
FIRM_NAME     = "R K Muley & Co"
FIRM_SUBTITLE = "Chartered Accountants | Tax & Litigation Practice"

# ── File Paths ────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
DB_PATH    = BASE_DIR / "rkmuley_v9.db"
LOG_PATH   = BASE_DIR / "rkmuley_v9.log"
EXPORT_DIR = BASE_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# ── Portal Limits ─────────────────────────────────────────────────────────────
PORTAL_TEXTBOX_LIMIT = 4_000   # e-Proceedings inline text field (chars)
PORTAL_PDF_SIZE_MB   = 5       # Portal PDF attachment limit
MAX_DRAFT_CHARS      = 38_000  # Auto-split threshold
MIN_WORDS_PER_ISSUE  = 150     # Minimum response words per issue

# ── Regex Patterns (defined ONCE — no duplicates) ────────────────────────────
DIN_PATTERN = re.compile(
    r"\bITBA/[A-Z0-9()/.-]+(?:/[A-Z0-9()/.-]+)*\b",
    re.IGNORECASE,
)
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# ── Feature Flags ─────────────────────────────────────────────────────────────
FEATURES: dict[str, bool] = {
    "RBAC_LOGIN":          True,
    "AUDIT_TRAIL":         True,
    "HALLUCINATION_GUARD": True,
    "PASS_E_REVIEW":       True,
    "VAULT_ANALYTICS":     True,
    "COVER_NOTE_GEN":      True,
    "PORTAL_SPLIT":        True,
    "WORD_EXPORT":         True,
    "NOTICE_STORE":        True,
    "SYSTEM_HEALTH_TAB":   True,
    "FACELESS_MODE":       True,   # NEW v8: Auto-detect Section 144B/NFAC
    "DEADLINE_CALENDAR":   True,
    "ICS_EXPORT":          True,
    "AIS_RECON":           True,
    "FORM_68_PATHWAY":     True,
    "PENALTY_WORKFLOW":    True,
    "FORM35_APPEALS":      True,
    "ITAT_NOTICE_HELPER":  True,
    "EVIDENCE_TRACKER":    True,
    "POSTGRES_OPTION":     True,
}

# ── RBAC Role Definitions ─────────────────────────────────────────────────────
ROLES: dict[str, dict] = {
    "admin": {
        "label": "Admin / Partner",
        "can_delete_vault": True,  "can_export": True,
        "can_see_scores": True,    "can_see_health": True,
        "can_risk_checker": True,  "can_vault": True,
        "can_notice_store": True,
    },
    "ca": {
        "label": "CA / Manager",
        "can_delete_vault": False, "can_export": True,
        "can_see_scores": True,    "can_see_health": False,
        "can_risk_checker": True,  "can_vault": True,
        "can_notice_store": True,
    },
    "article": {
        "label": "Article / Junior Staff",
        "can_delete_vault": False, "can_export": False,
        "can_see_scores": False,   "can_see_health": False,
        "can_risk_checker": False, "can_vault": False,
        "can_notice_store": False,
    },
    "readonly": {
        "label": "Read-Only / Client",
        "can_delete_vault": False, "can_export": False,
        "can_see_scores": False,   "can_see_health": False,
        "can_risk_checker": False, "can_vault": False,
        "can_notice_store": False,
    },
}

USER_PERSONAS: dict[str, dict] = {
    "admin":    {"label": "Partner / Admin",        "icon": ""},
    "ca":       {"label": "CA / Manager",            "icon": ""},
    "article":  {"label": "Article / Junior Staff",  "icon": ""},
    "readonly": {"label": "Read-Only / Client",      "icon": ""},
}

# ── App Navigation Steps ──────────────────────────────────────────────────────
APP_STEPS: list[dict] = [
    {"id": "upload",     "label": "Upload & Extract",       "min_role": "article"},
    {"id": "review",     "label": "Review Issues",          "min_role": "article"},
    {"id": "inputs",     "label": "Your Inputs",            "min_role": "article"},
    {"id": "draft",      "label": "Draft & Download",       "min_role": "article"},
    {"id": "procedural", "label": "Procedural Audit",       "min_role": "article"},
    {"id": "riskcheck",  "label": "Risk Checker & Scores",  "min_role": "ca"},
    {"id": "vault",      "label": "CA Knowledge Vault",     "min_role": "ca"},
    {"id": "syshealth",  "label": "System Health",          "min_role": "admin"},
]

# ── Session State Key Registry ────────────────────────────────────────────────
STATE_KEYS: list[str] = [
    "extraction_result", "notice_text_stored", "matched_laws",
    "procedural_flags", "npp_result", "rss_result",
    "assessee_name", "assessee_pan", "assessee_address",
    "credentials", "assessee_city", "ar_name",
    "user_inputs_text", "draft_response", "cover_note",
    "admission_findings", "pass_e_result", "notice_store_id",
    "auth_username", "auth_role", "auth_display", "auth_token",
    "faceless_mode", "response_deadline",
    "ais_tis_rows", "ais_recon_result", "evidence_tracker_rows",
    "form_68_enabled", "form_68_draft",
    "penalty_response_draft", "penalty_metadata",
    "form35_package", "form35_metadata", "itat_notice_response",
]

# ── Known IT Act Section Index (for hallucination detection) ──────────────────
# This is the FULL set used for validation — 297 sections.
KNOWN_IT_SECTIONS: set[str] = {
    "2", "4", "5", "6", "9", "10", "11", "12", "14A", "15", "16", "17",
    "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "35D", "36", "37", "40", "40A", "40B", "41", "43", "43B",
    "44", "44AA", "44AB", "44AD", "44ADA", "44AE", "45", "47", "48", "49",
    "50", "50C", "54", "54B", "54EC", "54F", "55", "56", "57", "58", "59",
    "68", "69", "69A", "69B", "69C", "69D", "70", "71", "72", "73", "74",
    "80C", "80CCC", "80CCD", "80CCD(1)", "80CCD(1B)", "80CCD(2)",
    "80D", "80DD", "80DDB", "80E", "80EE", "80EEA",
    "80G", "80GG", "80GGA", "80GGB", "80GGC", "80IAB", "80IB", "80IC",
    "80ID", "80IE", "80JJA", "80JJAA", "80LA", "80P", "80QQB", "80RRB", "80U",
    "87A", "89", "90", "91", "92", "92A", "92B", "92C", "92CA", "92CB",
    "92CC", "92CD", "92CE", "93", "94", "94A", "94B",
    "115A", "115AB", "115AC", "115AD", "115B", "115BA", "115BB", "115BBC",
    "115BBD", "115BBE", "115BBF", "115BBG", "115BBH", "115BBI", "115JB",
    "115JC", "115O",
    "131", "132", "133", "133A", "133B", "133C", "134", "135",
    "139", "139(1)", "139(4)", "139(5)", "139A", "139AA", "140", "140A", "142", "142A",
    "143", "143(1)", "143(2)", "143(3)", "144", "144B", "144C", "145", "145A", "145B",
    "147", "148", "148A", "149", "150", "151", "152", "153",
    "153A", "153B", "153C", "153D", "154", "155", "156",
    "192", "192A", "193", "194", "194A", "194B", "194BB", "194C", "194D",
    "194DA", "194E", "194EE", "194F", "194G", "194H", "194I", "194IA",
    "194IB", "194IC", "194J", "194K", "194LA", "194LB", "194LBA", "194LBB",
    "194LBC", "194LC", "194LD", "194M", "194N", "194O", "194P", "194Q",
    "194R", "194S", "194T",
    "195", "196", "196A", "196B", "196C", "196D", "197", "197A",
    "198", "199", "200", "200A", "201", "202", "203", "203A", "203AA",
    "204", "205", "206", "206A", "206AA", "206AB", "206B", "206C", "206CA",
    "206CB", "206CC",
    "220", "221", "222", "226", "234A", "234B", "234C", "234D", "234E",
    "234F", "234G", "237", "238", "239", "240", "241", "241A", "244A", "245",
    "246A", "249", "250", "251", "253", "254", "260A", "263", "264",
    "270A", "270AA", "271", "271(1)(c)", "271A", "271AA", "271AAA", "271AAB",
    "271AAC", "271AAD", "271B", "271C", "271D", "271DA", "271E", "271F",
    "271FA", "271FAA", "271FAB", "271G", "271H", "272A", "273A", "273AA",
    "273B", "274", "275", "276", "276B", "276BB", "276C", "276CC", "276CCC",
    "276D", "277", "277A", "278", "278AA", "278AB", "279",
    "281", "281B", "282", "282A", "285BA", "285BB", "285BC", "286",
    "288", "288A", "288B", "289", "292B", "292BB", "292C",
    # Subsection forms that appear in notices
    "2(22)(e)", "10(13A)", "56(2)(viib)", "56(2)(x)", "40A(3)", "115BAC(1A)",
}

# ── Gemini Model Options ──────────────────────────────────────────────────────
GEMINI_MODELS: list[dict] = [
    {"id": "gemini-2.5-flash", "label": "Gemini 2.5 Flash — Recommended (fast, accurate)"},
    {"id": "gemini-2.5-pro",   "label": "Gemini 2.5 Pro — Best for complex multi-issue notices"},
    {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash — Stable fallback"},
    {"id": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash Lite — Fastest, simple notices only"},
]

# ── Success Metric Targets ────────────────────────────────────────────────────
SUCCESS_METRICS: dict[str, Any] = {
    "target_reply_score":       75,
    "target_hallucination_risk": "Low",
    "portal_char_limit":        PORTAL_TEXTBOX_LIMIT,
    "pdf_attachment_mb":        PORTAL_PDF_SIZE_MB,
    "min_words_per_issue":      MIN_WORDS_PER_ISSUE,
    "max_draft_chars":          MAX_DRAFT_CHARS,
}
