"""The firm's letterhead (logo + CA details) shared by every report, invoice and export."""
import base64
import io
import re
from pathlib import Path

from PIL import Image

from ..config import data_dir
from ..models import FirmSetting, db

ALLOWED = {"PNG": "png", "JPEG": "jpg"}
MAX_LOGO_BYTES = 1024 * 1024


class LogoError(ValueError):
    pass


def _logo_path() -> Path | None:
    name = FirmSetting.get("firm_logo")
    if not name:
        return None
    path = data_dir() / "uploads" / name
    return path if path.exists() else None


def logo_bytes() -> bytes | None:
    path = _logo_path()
    return path.read_bytes() if path else None


def logo_data_uri() -> str | None:
    path = _logo_path()
    if not path:
        return None
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def save_logo(raw: bytes) -> None:
    """Validate by actually decoding the image; the extension the user chose is never trusted."""
    if len(raw) > MAX_LOGO_BYTES:
        raise LogoError("The logo must be 1 MB or smaller.")
    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.verify()
    except Exception:
        raise LogoError("That file is not a valid PNG or JPG image.")
    if fmt not in ALLOWED:
        raise LogoError("The logo must be a PNG or JPG image.")
    remove_logo()
    folder = data_dir() / "uploads"
    folder.mkdir(exist_ok=True)
    name = f"logo.{ALLOWED[fmt]}"
    (folder / name).write_bytes(raw)
    FirmSetting.put("firm_logo", name)


def remove_logo() -> None:
    path = _logo_path()
    if path:
        path.unlink(missing_ok=True)
    FirmSetting.put("firm_logo", "")


def profile() -> dict:
    s = FirmSetting.all()
    return {
        "name": s.get("firm_name") or "Office Manager",
        "tagline": s.get("firm_tagline") or "",
        "address": s.get("firm_address") or "",
        "phone": s.get("firm_phone") or "",
        "email": s.get("firm_email") or "",
        "website": s.get("firm_website") or "",
        "pan": s.get("firm_pan") or "",
        "gstin": s.get("firm_gstin") or "",
        "frn": s.get("firm_frn") or "",
        "partner_name": s.get("firm_partner_name") or "",
        "membership_no": s.get("firm_membership_no") or "",
        "logo": logo_data_uri(),
    }


REPORT_FIELDS = {"logo": "Logo", "tagline": "Tagline", "address": "Office address", "phone": "Phone", "email": "Email",
                 "website": "Website", "frn": "Firm Reg. No. (FRN)", "pan": "Firm PAN", "gstin": "Firm GSTIN",
                 "partner_name": "Partner / Proprietor name", "membership_no": "Membership No."}


def hidden_fields() -> set[str]:
    return {k for k in REPORT_FIELDS if FirmSetting.get("lh_hide_" + k) == "1"}


def report_profile() -> dict:
    """The firm profile as it should appear on reports: anything unticked in Settings is left out. (Invoices always show everything.)"""
    p, hide = profile(), hidden_fields()
    for k in hide:
        p[k] = None if k == "logo" else ""
    p["hide_logo"] = "logo" in hide
    return p


def report_logo_bytes() -> bytes | None:
    return None if "logo" in hidden_fields() else logo_bytes()


PROFESSIONS = {
    "ca": {"name": "Chartered Accountant firm", "title": "Chartered Accountant", "reg": "Firm Reg. No. (FRN)", "reg_short": "FRN",
           "member": "Membership No.", "member_short": "M.No.", "head": "Partner / Proprietor name"},
    "advocate": {"name": "Advocate / Law office", "title": "Advocate", "reg": "Bar Council Enrolment No.", "reg_short": "Enrl. No.",
                 "member": "Bar Association / Chamber No.", "member_short": "Chamber", "head": "Advocate name"},
    "other": {"name": "Tax consultant / other professional", "title": "Consultant", "reg": "Registration No.", "reg_short": "Reg. No.",
              "member": "Membership No.", "member_short": "M.No.", "head": "Proprietor name"},
}


DEFAULT_DESIGNATIONS = ["Proprietor", "Partner", "Director", "Managing Director", "Karta", "Trustee", "Authorised Signatory", "Accountant",
                        "Manager", "Self"]


def designations() -> list[str]:
    """Designation master for client contact persons (kept in Settings, one per line)."""
    raw = FirmSetting.get("designations")
    if raw is None:
        return list(DEFAULT_DESIGNATIONS)
    seen, out = set(), []
    for line in raw.splitlines():
        name = line.strip()[:80]
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


def profession() -> dict:
    key = FirmSetting.get("profession", "ca")
    p = dict(PROFESSIONS.get(key, PROFESSIONS["ca"]))
    p["key"] = key if key in PROFESSIONS else "ca"
    custom = (FirmSetting.get("profession_title") or "").strip()
    if custom:
        p["title"] = custom
    return p


def contact_line(p: dict) -> str:
    parts = [("Phone: " + p["phone"]) if p["phone"] else "", ("Email: " + p["email"]) if p["email"] else "",
             ("Web: " + p["website"]) if p["website"] else ""]
    return "  |  ".join(x for x in parts if x)


def id_line(p: dict) -> str:
    parts = [(profession()["reg_short"] + ": " + p["frn"]) if p["frn"] else "", ("PAN: " + p["pan"]) if p["pan"] else "",
             ("GSTIN: " + p["gstin"]) if p["gstin"] else ""]
    return "  |  ".join(x for x in parts if x)


def signatory_line(p: dict) -> str:
    parts = [p["partner_name"], (profession()["member_short"] + " " + p["membership_no"]) if p["membership_no"] else ""]
    return ", ".join(x for x in parts if x)


def header_lines(p: dict | None = None) -> list[str]:
    """Plain-text letterhead used in CSV and Excel exports."""
    p = p or report_profile()
    lines = [p["name"], p["tagline"], re.sub(r"\s*[\r\n]+\s*", ", ", p["address"].strip()), contact_line(p), id_line(p)]
    if p["partner_name"] or p["membership_no"]:
        lines.append((profession()["title"] + ": " + p["partner_name"]).strip()
                     + ((", " + profession()["member_short"] + ": " + p["membership_no"]) if p["membership_no"] else ""))
    return [ln for ln in lines if ln]
