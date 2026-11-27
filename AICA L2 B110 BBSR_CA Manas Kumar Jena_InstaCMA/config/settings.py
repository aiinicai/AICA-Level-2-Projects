"""
Settings of InstaCMA, saved on this PC in %USERPROFILE%\\.cma_builder2\\settings.json
(firm details, AI providers, OCR path, default bank norms, admin password).
"""
import copy
import json
import os

SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".cma_builder2")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

FACTORY_SETTINGS = {
    # CA firm (printed on the covering letter and the assessment note)
    "firm_name": "", "firm_frn": "", "preparer_name": "", "preparer_membership": "",
    "preparer_designation": "Partner", "firm_address": "", "firm_phone": "", "firm_email": "", "firm_place": "",
    "letterhead_image": "",
    "audited_note": ("In our opinion and to the best of our information and according to the records and "
                     "explanations given to us, the accounts give a true and fair view in compliance with the "
                     "accounting principles and applicable laws & regulations."),
    # AI (any model) - provider: none / gemini / anthropic / openai / compatible / ollama
    "ai_main": {"provider": "none", "api_key": "", "model": "", "base_url": ""},
    "ai_backup": {"provider": "none", "api_key": "", "model": "", "base_url": ""},
    "use_ai_for_pdf": True,
    # OCR
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    # output
    "output_folder": os.path.join(os.path.expanduser("~"), "Documents", "CMA Builder Output"),
    "display_unit": "Actual",
    "admin_password": "admin",
    # defaults used when the user leaves a norm blank
    "defaults": {"dscr_min": 1.5, "dscr_max": 2.5, "turnover_fail_below": 4.0, "turnover_pass_from": 5.0,
                 "stock_margin": 0.25, "debtor_margin": 0.25, "default_growth": 0.20, "cc_rate": 0.10,
                 "tl_rate": 0.105, "debtor_days_cap": 90, "dp_buffer": 0.02},
}


def _merge(base, extra):
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings():
    data = {}
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    return _merge(FACTORY_SETTINGS, data)


def save_settings(settings):
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
        json.dump(settings, fh, indent=2, default=str)


def reset_settings():
    keep = load_settings()
    fresh = copy.deepcopy(FACTORY_SETTINGS)
    for k in ("firm_name", "firm_frn", "preparer_name", "preparer_membership", "admin_password"):
        fresh[k] = keep.get(k, fresh[k])
    save_settings(fresh)
    return load_settings()
