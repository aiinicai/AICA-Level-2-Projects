"""Text, filenames, deadline presentation and safe clipboard markup."""
import base64
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines())).strip()


def comparable(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def escape_markdown(text: str) -> str:
    """Treat model/upload strings as text in widgets that interpret Markdown."""
    return re.sub(r"([\\`*_{}\[\]()#+.!|<>~-])", r"\\\1", text)


def safe_filename(assessment_year: str | None) -> str:
    year = re.sub(r"[^A-Za-z0-9_-]", "-", assessment_year or "").strip("-_")[:30]
    return f"Tax_Notice_Reply{'_AY_' + year if year else ''}.docx"


def deadline_label(exact_date: date, today: date | None = None) -> tuple[str, str]:
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    days = (exact_date - today).days
    if days < 0:
        return f"{abs(days)} day{'s' if days != -1 else ''} overdue", "error"
    if days == 0:
        return "Due today", "warning"
    return f"{days} day{'s' if days != 1 else ''} remaining", "warning"


def explicit_date_in_quote(value: date, quote: str) -> bool:
    """Only recognize explicit, unambiguous date strings; never derive relative dates."""
    text = comparable(quote).replace(",", "")
    patterns = [
        rf"{value.year}-{value.month:02}-{value.day:02}",
        rf"0?{value.day}[/.-]0?{value.month}[/.-]{value.year}",
        rf"0?{value.day}\s+{value.strftime('%B').lower()}\s+{value.year}",
        rf"0?{value.day}\s+{value.strftime('%b').lower()}\s+{value.year}",
        rf"{value.strftime('%B').lower()}\s+0?{value.day}\s+{value.year}",
    ]
    return any(re.search(r"(?<!\w)" + p + r"(?!\w)", text) for p in patterns)


def clipboard_html(text: str) -> str:
    """Base64 prevents document content from being interpreted as HTML or JS."""
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return '''<style>body{margin:0;font:14px sans-serif;color:#0F2744}
button{background:white;border:1px solid #CBD4DC;border-radius:8px;padding:10px 18px;
font:600 14px sans-serif;color:#0F2744;cursor:pointer} #message{margin-left:12px}</style>
<button id="copy" type="button">Copy Reply</button><span id="message" role="status"></span>
<script>
const reply = new TextDecoder().decode(Uint8Array.from(atob("''' + payload + '''"), c => c.charCodeAt(0)));
document.getElementById('copy').addEventListener('click', async () => {
  const message = document.getElementById('message');
  try { await navigator.clipboard.writeText(reply); message.textContent = 'Copied'; }
  catch { message.textContent = 'Select the reply above and press Ctrl+C (or Cmd+C).'; }
});
</script>'''
