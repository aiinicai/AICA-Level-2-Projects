"""Reads the code lists from the supplied NIC/GePP workbook's own 'Master Codes' sheet,
via the workbook's named ranges (Units, look_units, States, look_state, country_code,
currency_code, port_code, Doctype, Supply). Nothing is hard-coded, so an updated NIC
utility with revised masters is picked up automatically. Read-only - the template is
never saved by this module."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, range_boundaries

from .logsetup import get_logger
from .util import clean_text

log = get_logger()


@dataclass
class Masters:
    units: list[tuple[str, str]] = field(default_factory=list)      # (description, code) e.g. ("CARTONS","CTN")
    states: dict[str, str] = field(default_factory=dict)            # NAME -> code
    countries: dict[str, str] = field(default_factory=dict)         # code -> name
    currencies: dict[str, str] = field(default_factory=dict)        # code -> name
    ports: dict[str, str] = field(default_factory=dict)             # code -> description
    doc_types: list[str] = field(default_factory=list)
    doc_type_codes: dict[str, str] = field(default_factory=dict)   # "Tax Invoice" -> "INV"
    supply_types: list[str] = field(default_factory=list)

    @property
    def unit_descriptions(self): return [d for d, _ in self.units]

    def unit_code(self, desc: str) -> str:
        return next((c for d, c in self.units if d.upper() == (desc or "").upper()), "")

    def unit_from_text(self, text: str) -> str:
        """'PCS', 'Pieces', 'KGS', 'Nos' printed on an invoice -> the NIC unit description."""
        t = re.sub(r"[^A-Z]", "", (text or "").upper())
        if not t:
            return ""
        extra = {"PIECE": "PCS", "PIECES": "PCS", "NOS": "NOS", "NO": "NOS", "KG": "KGS", "KILOGRAM": "KGS",
                 "KILOGRAMS": "KGS", "LTR": "LTR", "LITRE": "LTR", "LITRES": "LTR", "MT": "MTS", "TON": "TON",
                 "TONNE": "TON", "CTN": "CTN", "CARTON": "CTN", "CARTONS": "CTN", "BOXES": "BOX", "PKT": "PAC",
                 "PACKET": "PAC", "PACKETS": "PAC", "PACK": "PAC", "BAG": "BAG", "BAGS": "BAG", "SET": "SET",
                 "UNIT": "UNT", "UNITS": "UNT", "SQM": "SQM", "MTR": "MTR", "METER": "MTR", "METERS": "MTR"}
        for desc, code in self.units:
            if t == re.sub(r"[^A-Z]", "", desc.upper()) or t == re.sub(r"[^A-Z]", "", (code or "").upper()):
                return desc
        code = extra.get(t)
        if code:
            for desc, c in self.units:
                if (c or "").upper() == code:
                    return desc
        return ""

    def country_candidates(self, text: str) -> list[tuple[str, str]]:
        """Finds the country in free text such as 'ATLANTA , USA', 'CUMMING GA 30041 USA', 'NEWZEALAND',
        'P.O.BOX 51018, LIMBE, MALAWI'. Uses the NIC country master names (full name and the part before
        a comma/bracket) plus common trade spellings. Returns the distinct matches found (India ignored
        when another country is present)."""
        if not text:
            return []
        index = self._country_index()
        up = text.upper()
        norm = lambda x: re.sub(r"[^A-Z]", "", x)
        whole = norm(up)
        if whole in index:
            return [(index[whole], self.countries[index[whole]])]
        words = [w for w in re.split(r"[^A-Z.]+", up) if w]
        found: list[str] = []
        # longest phrases first so 'SOUTH AFRICA' wins over 'AFRICA', 'NEW ZEALAND' over 'ZEALAND'
        for size in (4, 3, 2, 1):
            for i in range(len(words) - size + 1):
                key = norm("".join(words[i:i + size]))
                if len(key) < 2 or key not in index:
                    continue
                code = index[key]
                if code not in found:
                    found.append(code)
            if found and size > 1:
                break
        if len(found) > 1 and "IN" in found:
            found.remove("IN")
        return [(c, self.countries[c]) for c in found]

    _ALIASES = {
        "USA": "US", "UNITEDSTATES": "US", "AMERICA": "US", "UK": "GB", "UNITEDKINGDOM": "GB", "ENGLAND": "GB",
        "GREATBRITAIN": "GB", "BRITAIN": "GB", "SCOTLAND": "GB", "WALES": "GB", "NORTHERNIRELAND": "GB",
        "UAE": "AE", "EMIRATES": "AE", "DUBAI": "AE", "ABUDHABI": "AE", "SHARJAH": "AE", "AJMAN": "AE",
        "KSA": "SA", "SAUDI": "SA", "SOUTHKOREA": "KR", "KOREA": "KR", "NORTHKOREA": "KP", "RUSSIA": "RU",
        "VIETNAM": "VN", "IRAN": "IR", "SYRIA": "SY", "LAOS": "LA", "MOLDOVA": "MD", "TANZANIA": "TZ",
        "BOLIVIA": "BO", "VENEZUELA": "VE", "CZECHREPUBLIC": "CZ", "CZECH": "CZ", "IVORYCOAST": "CI",
        "COTEDIVOIRE": "CI", "HOLLAND": "NL", "THENETHERLANDS": "NL", "TURKIYE": "TR", "SWAZILAND": "SZ",
        "BURMA": "MM", "MACEDONIA": "MK", "CAPEVERDE": "CV", "EASTTIMOR": "TL", "PALESTINE": "PS",
        "TAIWAN": "TW", "BRUNEI": "BN", "MACAU": "MO", "DRC": "CD", "DRCONGO": "CD", "REPUBLICOFCONGO": "CG",
        "HONGKONGSAR": "HK", "PRC": "CN", "PEOPLESREPUBLICOFCHINA": "CN", "MICRONESIA": "FM",
    }

    def _country_index(self) -> dict[str, str]:
        if getattr(self, "_cidx", None):
            return self._cidx
        idx, short = {}, {}
        for code, name in self.countries.items():
            idx[re.sub(r"[^A-Z]", "", name.upper())] = code                     # full official name
        for code, name in self.countries.items():
            k = re.sub(r"[^A-Z]", "", re.split(r"[,(]", name.upper())[0])
            if len(k) >= 4 and k not in idx:
                short.setdefault(k, set()).add(code)
        for k, codes in short.items():
            if len(codes) == 1:                                                 # ambiguous short names skipped
                idx[k] = next(iter(codes))
        for k, code in self._ALIASES.items():
            if code in self.countries:
                idx[k] = code
        self._cidx = idx
        return idx

    _CITY_ALIASES = {"DUBAI", "ABUDHABI", "SHARJAH", "AJMAN"}        # cities that also identify a country
    _PORT_ALIASES = {"NHAVASHEVA": "INNSA1", "JNPT": "INNSA1", "JAWAHARLALNEHRU": "INNSA1"}

    def is_exact_country(self, text: str) -> bool:
        """True only when the whole phrase is a country name ('UNITED ARAB EMIRATES'), not when it
        merely contains one ('CUMMING GA USA')."""
        k = re.sub(r"[^A-Z]", "", (text or "").upper())
        return bool(k) and k not in self._CITY_ALIASES and k in self._country_index()

    def is_country_name(self, text: str) -> bool:
        """True for a country name. City names that merely imply a country (Dubai) are not counted,
        so they can still be used as the buyer's location."""
        if re.sub(r"[^A-Z]", "", (text or "").upper()) in self._CITY_ALIASES:
            return False
        return bool(self.country_candidates(text))

    def port_candidates(self, text: str) -> list[tuple[str, str]]:
        key = re.sub(r"[^A-Z]", "", (text or "").upper().replace("PORT", "").replace("INDIA", ""))
        alias = self._PORT_ALIASES.get(key)
        if alias and alias in self.ports:
            return [(alias, self.ports[alias].strip())]
        words = [w for w in re.findall(r"[A-Z]{3,}", (text or "").upper())
                 if w not in {"PORT", "INDIA", "SEZ", "ICD", "CFS", "THE", "AND"}]
        if not words:
            return []
        return sorted([(c, d.strip()) for c, d in self.ports.items()
                       if all(w in d.upper() for w in words)])


def _named(wb, name):
    try:
        dn = wb.defined_names[name]
    except KeyError:
        return None
    for sheet, ref in dn.destinations:
        return wb[sheet], ref
    return None


def _col_values(ws, ref, offset=0):
    min_col, min_row, max_col, max_row = range_boundaries(ref.replace("$", ""))
    out = []
    for r in range(min_row, max_row + 1):
        v = ws.cell(r, min_col).value
        d = ws.cell(r, min_col + offset).value if offset else None
        out.append((v, d))
    return out


def load_masters(template: str | Path) -> Masters:
    wb = load_workbook(template, read_only=False, keep_vba=False, data_only=True)
    m = Masters()
    try:
        if (x := _named(wb, "look_units")):
            ws, ref = x
            m.units = [(clean_text(a), clean_text(b)) for a, b in _col_values(ws, ref, 1) if clean_text(a)]
        if (x := _named(wb, "look_state")):
            ws, ref = x
            for a, b in _col_values(ws, ref, 1):
                if clean_text(a):
                    m.states[clean_text(a).upper()] = str(b).zfill(2) if b is not None else ""
        for nm, target in (("country_code", m.countries), ("currency_code", m.currencies), ("port_code", m.ports)):
            if (x := _named(wb, nm)):
                ws, ref = x
                for a, b in _col_values(ws, ref, 1):
                    if clean_text(a):
                        target[clean_text(a).upper()] = clean_text(b)
        if (x := _named(wb, "look_type")):
            ws, ref = x
            m.doc_type_codes = {clean_text(a): clean_text(b) for a, b in _col_values(ws, ref, 1) if clean_text(a)}
        if (x := _named(wb, "Doctype")):
            m.doc_types = [clean_text(a) for a, _ in _col_values(*x) if clean_text(a)]
        if (x := _named(wb, "Supply")):
            m.supply_types = [clean_text(a) for a, _ in _col_values(*x) if clean_text(a)]
    finally:
        wb.close()
    log.info("Masters loaded: %d units, %d states, %d countries, %d currencies, %d ports",
             len(m.units), len(m.states), len(m.countries), len(m.currencies), len(m.ports))
    return m
