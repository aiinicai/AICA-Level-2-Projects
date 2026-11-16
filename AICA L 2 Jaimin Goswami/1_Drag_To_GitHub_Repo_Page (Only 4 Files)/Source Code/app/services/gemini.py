"""Google Gemini AI Service for Finstock EventScope.
Provides real-time institutional financial analysis, market impact evaluations,
and regulatory summarization for Indian and global financial events.
"""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
import urllib.request
import urllib.error

logger = logging.getLogger("finstock.gemini")

DEFAULT_MODEL = "gemini-1.5-flash"


def find_api_txt() -> Path | None:
    """Find API.txt in common application and workspace locations."""
    candidates = [
        Path.cwd() / "API.txt",
        Path.cwd().parent / "API.txt",
        Path(__file__).resolve().parents[2] / "API.txt",
        Path(__file__).resolve().parents[3] / "API.txt",
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates.insert(0, exe_dir / "API.txt")
        candidates.insert(1, exe_dir.parent / "API.txt")
    
    for cand in candidates:
        try:
            if cand and cand.exists():
                return cand
        except Exception:
            continue
    return None


def get_gemini_api_key(db=None) -> str:
    """Retrieve Gemini API key from database setting, environment, or API.txt."""
    # 1. Database user_settings
    if db is not None:
        try:
            saved = db.setting("gemini_api_key")
            if saved and str(saved).strip():
                return str(saved).strip().strip('"\'')
        except Exception:
            pass

    # 2. Environment variable
    import os
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip().strip('"\'')

    # 3. Parse API.txt
    api_file = find_api_txt()
    if api_file:
        try:
            content = api_file.read_text(encoding="utf-8").strip()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                lower = line.lower()
                if "gemini" in lower and "=" in line:
                    return line.split("=", 1)[1].strip().strip('"\'')
                # Check for Google API key prefix
                if line.startswith("AIzaSy"):
                    return line.strip().strip('"\'')
        except Exception as exc:
            logger.debug("Could not read API.txt for Gemini key: %s", exc)

    return ""


def set_gemini_api_key(db, api_key: str):
    """Save Gemini API key to user_settings and sync to API.txt."""
    clean_key = api_key.strip().strip('"\'')
    if db is not None:
        db.set_setting("gemini_api_key", clean_key)
    
    api_file = find_api_txt()
    if api_file and clean_key:
        try:
            lines = []
            replaced = False
            if api_file.exists():
                for line in api_file.read_text(encoding="utf-8").splitlines():
                    if "gemini" in line.lower() or line.strip().startswith("AIzaSy"):
                        lines.append(f"GEMINI_API_KEY={clean_key}")
                        replaced = True
                    else:
                        lines.append(line)
            if not replaced:
                lines.append(f"GEMINI_API_KEY={clean_key}")
            api_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not update API.txt with Gemini key: %s", exc)


def get_cached_analysis(db, event_id: str) -> dict | None:
    """Retrieve previously generated Gemini analysis from SQLite cache."""
    try:
        rows = db.rows(
            "SELECT analysis_text, model, created_at FROM event_ai_cache WHERE event_id=?",
            (event_id,)
        )
        if rows:
            return {
                "text": rows[0]["analysis_text"],
                "model": rows[0]["model"],
                "created_at": rows[0]["created_at"]
            }
    except Exception as exc:
        logger.debug("Failed checking AI cache for %s: %s", event_id, exc)
    return None


def save_cached_analysis(db, event_id: str, analysis_text: str, model: str = DEFAULT_MODEL):
    """Store generated Gemini analysis in SQLite cache."""
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        db.execute(
            """INSERT OR REPLACE INTO event_ai_cache (event_id, analysis_text, model, created_at)
               VALUES (?, ?, ?, ?)""",
            (event_id, analysis_text, model, now_iso)
        )
    except Exception as exc:
        logger.warning("Failed saving AI cache for %s: %s", event_id, exc)


def delete_cached_analysis(db, event_id: str):
    """Clear cached analysis for re-generation."""
    try:
        db.execute("DELETE FROM event_ai_cache WHERE event_id=?", (event_id,))
    except Exception:
        pass


def analyze_event_impact(event: dict, db=None, api_key: str = None, force: bool = False) -> dict:
    """Call Google Gemini API to produce an institutional market impact report.
    Returns dict: {'success': bool, 'text': str, 'error': str, 'cached': bool}
    """
    event_id = event.get("id") or event.get("external_id")
    
    # 1. Check cache if not forcing refresh
    if db and event_id and not force:
        cached = get_cached_analysis(db, event_id)
        if cached:
            return {
                "success": True,
                "text": cached["text"],
                "model": cached["model"],
                "created_at": cached["created_at"],
                "cached": True,
                "error": ""
            }

    # 2. Resolve API key
    key = (api_key or get_gemini_api_key(db)).strip()
    if not key:
        return {
            "success": False,
            "text": "",
            "cached": False,
            "error": "Gemini API key is not configured. Add your free key in Settings or API.txt."
        }

    # 3. Construct structured prompt
    title = event.get("title", "Financial Event")
    authority = event.get("authority") or event.get("company") or "Official Authority"
    category = event.get("category", "General")
    country = event.get("country", "India")
    scheduled_at = event.get("scheduled_at", "Scheduled")
    summary = event.get("summary", "")
    importance = event.get("importance", "Medium")

    prompt = f"""You are an elite Institutional Equity & Derivatives Research Strategist covering Indian financial markets (NSE, BSE, SEBI, RBI) and global macro transmission.

Analyze this upcoming financial event for an Indian market participant:
- Event: {title}
- Issuer / Authority: {authority}
- Category: {category}
- Country: {country}
- Scheduled: {scheduled_at}
- Significance / Importance: {importance}
- Baseline Context: {summary}

Provide a structured, high-value institutional intelligence report in clear, concise markdown with the following 4 sections:

### 1. 💡 FINANCIAL CONCEPT & CORE TRANSMISSION
Explain the core mechanism in clear institutional language. What does this indicator/filing measure, and why is the market tracking it right now?

### 2. 📊 IMPACT ON NIFTY 50 & INDIAN SECTORS
- **Nifty 50 & Bank Nifty**: Expected directional bias and sensitivity (High / Moderate / Low).
- **Key Affected Sectors**: Detail specific sectors (e.g. Private/PSU Banks, IT Services, Auto, FMCG, Real Estate, Metals, Pharma) and how they typically react.
- **Yields & Rupee (INR)**: 10-year G-Sec yield and USD/INR impact.

### 3. 🎯 INSTITUTIONAL TRADER & INVESTOR PLAYBOOK
- **Volatility Window**: Anticipated timeframe of peak market reaction (Pre-event positioning vs Post-release volatility).
- **Actionable Watchlist**: Exact metrics to watch (Surprise factor, guidance, RBI stance, revision).
- **Risk Mitigation**: What options/derivatives hedgers and long-term equity investors should be aware of.

### 4. ⚡ SUMMARY SCORECARD
Give a quick 1-line verdict with expected market sentiment: [BULLISH / NEUTRAL / BEARISH / VOLATILITY SPIKE] with a 1-sentence rationale.
"""

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "topK": 40,
            "maxOutputTokens": 950
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{DEFAULT_MODEL}:generateContent?key={key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "FinstockEventScope/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=18) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))
            candidates = raw_data.get("candidates", [])
            if not candidates:
                return {
                    "success": False,
                    "text": "",
                    "cached": False,
                    "error": "Gemini API returned an empty response. Check token permissions."
                }
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not text:
                return {
                    "success": False,
                    "text": "",
                    "cached": False,
                    "error": "Gemini API response did not contain text content."
                }

            # Save in SQLite cache
            if db and event_id:
                save_cached_analysis(db, event_id, text, DEFAULT_MODEL)

            return {
                "success": True,
                "text": text,
                "model": DEFAULT_MODEL,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "cached": False,
                "error": ""
            }

    except urllib.error.HTTPError as http_err:
        err_msg = ""
        try:
            err_body = json.loads(http_err.read().decode("utf-8"))
            err_msg = err_body.get("error", {}).get("message", "")
        except Exception:
            err_msg = str(http_err)
        logger.error("Gemini HTTP Error %s: %s", http_err.code, err_msg)
        return {
            "success": False,
            "text": "",
            "cached": False,
            "error": f"Gemini API Error (HTTP {http_err.code}): {err_msg or http_err.reason}"
        }
    except Exception as exc:
        logger.error("Gemini API Network Exception: %s", exc)
        return {
            "success": False,
            "text": "",
            "cached": False,
            "error": f"Network connection to Gemini API failed: {type(exc).__name__}. Ensure internet access is available."
        }


def format_ai_analysis_html(ai_result: dict, theme: str = "Dark Navy") -> str:
    """Format raw markdown from Gemini into beautiful TradingView-styled HTML."""
    is_dark = str(theme).lower() not in ("clean light", "light", "white")
    card_bg = "#0B192E" if is_dark else "#F1F5F9"
    card_border = "#1E3A63" if is_dark else "#CBD5E1"
    badge_bg = "#1E40AF" if is_dark else "#DBEAFE"
    badge_fg = "#93C5FD" if is_dark else "#1E40AF"
    text_color = "#E2E8F0" if is_dark else "#1E293B"
    header_color = "#38BDF8" if is_dark else "#0284C7"
    accent_green = "#22C55E" if is_dark else "#16A34A"

    if not ai_result.get("success"):
        err = ai_result.get("error", "Unable to generate AI analysis.")
        return f"""
        <div style="background:{card_bg}; border:1px solid #DC2626; border-radius:8px; padding:14px; margin-top:12px;">
            <div style="font-weight:700; color:#EF4444; font-size:13px; margin-bottom:4px;">
                ⚠️ Gemini AI Analysis Unavailable
            </div>
            <div style="font-size:12px; color:{text_color}; line-height:1.5;">
                {err}
            </div>
            <div style="margin-top:10px; font-size:11px; color:#94A3B8;">
                💡 To configure your Gemini key, enter it in <b>Sources & Settings</b> or paste <code>GEMINI_API_KEY=your_key</code> into <b>API.txt</b>.
            </div>
        </div>
        """

    raw_text = ai_result.get("text", "")
    model = ai_result.get("model", "gemini-1.5-flash")
    created = ai_result.get("created_at", "")[:19].replace("T", " ") + " UTC"
    cached_badge = "<span style='background:#10B981; color:#064E3B; font-size:9px; padding:2px 6px; border-radius:4px; font-weight:700;'>CACHED</span>" if ai_result.get("cached") else "<span style='background:#3B82F6; color:#EFF6FF; font-size:9px; padding:2px 6px; border-radius:4px; font-weight:700;'>LIVE GENERATED</span>"

    # Convert basic markdown headers and bolding into HTML
    html_content = raw_text
    # Escape HTML special chars first (except we format headers)
    html_content = html_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Headers
    html_content = re.sub(r'###\s*(.*?)\n', rf'<h4 style="color:{header_color}; margin-top:14px; margin-bottom:6px; font-size:13px; font-weight:700; border-bottom:1px solid {card_border}; padding-bottom:3px;">\1</h4>', html_content)
    html_content = re.sub(r'##\s*(.*?)\n', rf'<h3 style="color:{header_color}; margin-top:16px; margin-bottom:8px; font-size:14px; font-weight:700;">\1</h3>', html_content)
    
    # Bold
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_content)
    
    # List items
    html_content = re.sub(r'^\s*[\-\*]\s+(.*)$', r'<div style="margin:3px 0 3px 12px;">• \1</div>', html_content, flags=re.MULTILINE)
    
    # Line breaks
    html_content = html_content.replace("\n\n", "<div style='height:8px;'></div>")

    return f"""
    <div style="background:{card_bg}; border:1px solid {card_border}; border-radius:8px; padding:16px; margin-top:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <div style="font-weight:700; color:{header_color}; font-size:13px;">
                ✨ GEMINI AI REAL-TIME MARKET INTELLIGENCE
            </div>
            <div>
                {cached_badge}
                <span style="font-size:10px; color:#64748B; margin-left:6px;">Model: {model}</span>
            </div>
        </div>
        <div style="font-size:12px; line-height:1.6; color:{text_color};">
            {html_content}
        </div>
        <div style="margin-top:12px; padding-top:8px; border-top:1px dashed {card_border}; font-size:10px; color:#64748B; display:flex; justify-content:space-between;">
            <span>Generated via Google Gemini API · Institutional Research Engine</span>
            <span>{created}</span>
        </div>
    </div>
    """
