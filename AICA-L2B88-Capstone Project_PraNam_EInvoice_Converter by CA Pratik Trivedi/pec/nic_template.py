"""Surgical handling of the NIC/GePP .xlsm package.

WHY NOT openpyxl FOR WRITING: the supplied NIC-GePP workbook contains ~295 ActiveX
controls (Validate / Generate JSON / Import buttons, Profile text boxes), VML drawings,
EMF control images and a VBA project. openpyxl does not round-trip ActiveX controls, so
saving the template through it damages the utility. This module therefore copies the
.xlsm package part-by-part, byte-for-byte, and rewrites ONLY the <sheetData> rows of the
'eInvoice' and 'Items' sheets. Macros, controls, validation lists, named ranges,
formatting, protection and every other sheet are left exactly as they were.

The NIC column for each value is located from the template's own hidden row 4 codes
(colDocno, colHsn, ...), not from fixed column letters.
"""
from __future__ import annotations

import hashlib
import html
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath

from .logsetup import get_logger
from .util import col_index, col_letter, xml_escape

log = get_logger()
REL_NS_TARGET = re.compile(r'<Relationship\b[^>]*?Id="([^"]+)"[^>]*?Target="([^"]+)"[^>]*/?>')
ROW_RE = re.compile(r"<row\b[^>]*?(?:/>|>.*?</row>)", re.S)
CELL_RE = re.compile(r'<c\b([^>]*?)(?:/>|>(.*?)</c>)', re.S)


class TemplateError(Exception):
    pass


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return m.group(1) if m else None


class TemplatePackage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise TemplateError(f"NIC template not found: {self.path}")
        if self.path.suffix.lower() != ".xlsm":
            raise TemplateError("The NIC/GePP template must be the macro-enabled .xlsm utility.")
        try:
            self.zf = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile:
            raise TemplateError("The NIC template is not a valid Excel .xlsm file.")
        self._ss: list[str] | None = None
        self.sheet_parts = self._map_sheets()

    def close(self):
        self.zf.close()

    def read(self, part: str) -> str:
        return self.zf.read(part).decode("utf-8")

    def _map_sheets(self) -> dict[str, str]:
        wb = self.read("xl/workbook.xml")
        rels = dict(REL_NS_TARGET.findall(self.read("xl/_rels/workbook.xml.rels")))
        out = {}
        for m in re.finditer(r'<sheet\b[^>]*?name="([^"]+)"[^>]*?r:id="([^"]+)"', wb):
            target = rels.get(m.group(2), "")
            out[html.unescape(m.group(1))] = "xl/" + target.lstrip("/").replace("xl/", "", 1) \
                if not target.startswith("/xl/") else target.lstrip("/")
        return out

    def sheet_names(self) -> list[str]:
        return list(self.sheet_parts)

    @property
    def shared_strings(self) -> list[str]:
        if self._ss is None:
            self._ss = []
            if "xl/sharedStrings.xml" in self.zf.namelist():
                x = self.read("xl/sharedStrings.xml")
                for si in re.findall(r"<si>(.*?)</si>", x, re.S):
                    self._ss.append(html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, re.S))))
        return self._ss

    def _cell_text(self, attrs: str, inner: str | None) -> str:
        if not inner:
            return ""
        t = _attr(attrs, "t")
        if t == "inlineStr":
            return html.unescape("".join(re.findall(r"<t[^>]*>(.*?)</t>", inner, re.S)))
        v = re.search(r"<v>(.*?)</v>", inner, re.S)
        if not v:
            return ""
        if t == "s":
            return self.shared_strings[int(v.group(1))]
        return html.unescape(v.group(1))

    def sheet_rows(self, sheet: str) -> dict[int, dict[str, str]]:
        part = self.sheet_parts.get(sheet)
        if not part:
            raise TemplateError(f"Sheet '{sheet}' not found in NIC template.")
        x = self.read(part)
        rows = {}
        for rx in ROW_RE.findall(x):
            r = int(_attr(rx[:rx.index(">")], "r"))
            cells = {}
            for attrs, inner in CELL_RE.findall(rx):
                ref = _attr(attrs, "r")
                txt = self._cell_text(attrs, inner)
                if ref and txt != "":
                    cells[re.match(r"[A-Z]+", ref).group(0)] = txt
            rows[r] = cells
        return rows

    def header_codes(self, sheet: str) -> tuple[dict[str, str], dict[str, str], int]:
        """Returns (code -> column letter, code -> visible label, first data row).
        The code row is the row whose cells mostly start with 'col' (row 4 in NIC-GePP V2.0)."""
        rows = self.sheet_rows(sheet)
        code_row = None
        for r in sorted(rows)[:15]:
            vals = list(rows[r].values())
            if vals and sum(v.startswith("col") for v in vals) >= max(5, len(vals) // 2):
                code_row = r
                break
        if code_row is None:
            raise TemplateError(f"Column-code row not found on NIC sheet '{sheet}'. "
                                "Is this the NIC-GePP utility?")
        codes = {v: k for k, v in rows[code_row].items() if v.startswith("col")}
        labels = {code: rows.get(code_row - 1, {}).get(col, code) for code, col in codes.items()}
        return codes, labels, code_row + 1

    def data_row_count(self, sheet: str, first_row: int) -> int:
        return sum(1 for r, c in self.sheet_rows(sheet).items() if r >= first_row and c)

    # ------------------------------------------------------------ Profile (ActiveX) - read only
    def profile_controls(self, sheet: str = "Profile") -> dict[str, str]:
        """Best-effort read of the text held in the Profile sheet's ActiveX text boxes
        (txtGstin, txtLegal, ...). Used only to pre-fill / cross-check supplier settings."""
        out: dict[str, str] = {}
        part = self.sheet_parts.get(sheet)
        if not part:
            return out
        base = PurePosixPath(part).parent
        relp = f"{base}/_rels/{PurePosixPath(part).name}.rels"
        if relp not in self.zf.namelist():
            return out
        rels = dict(REL_NS_TARGET.findall(self.read(relp)))
        x = self.read(part)
        for rid, name in re.findall(r'<control\b[^>]*?r:id="([^"]+)"[^>]*?name="([^"]+)"', x):
            if name in out or rid not in rels:
                continue
            try:
                ax = str(PurePosixPath(base, rels[rid])).replace("xl/worksheets/../", "xl/")
                ax = _norm(ax)
                axrel = f"{PurePosixPath(ax).parent}/_rels/{PurePosixPath(ax).name}.rels"
                bin_target = REL_NS_TARGET.findall(self.read(axrel))[0][1]
                data = self.zf.read(_norm(str(PurePosixPath(PurePosixPath(ax).parent, bin_target))))
                txt = _activex_text(data)
                if txt is not None:
                    out[name] = txt
            except Exception:
                continue
        return out


def _norm(p: str) -> str:
    parts = []
    for seg in p.split("/"):
        if seg == "..":
            parts and parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/".join(parts)


def _activex_text(data: bytes) -> str | None:
    """Forms 2.0 text/combo box persistence stores the value as a length DWORD with the
    'compressed' flag (0x80000000) followed later by the ASCII text. Heuristic, verified
    against NIC-GePP V2.0; anything that does not decode cleanly is ignored."""
    for p in range(20, min(len(data) - 16, 96)):
        if data[p + 3] == 0x80 and data[p + 2] == 0:
            n = data[p] | (data[p + 1] << 8)
            if 0 < n <= 2000 and p + 12 + n <= len(data):
                raw = data[p + 12:p + 12 + n]
                if all(32 <= b < 127 for b in raw):
                    return raw.decode("ascii").strip()
    return None


# ================================================================== writer
def _cols_styles(sheet_xml: str) -> dict[int, str]:
    styles = {}
    for m in re.finditer(r"<col\b([^>]*)/>", sheet_xml):
        a = m.group(1)
        st = _attr(a, "style")
        if st is None:
            continue
        for c in range(int(_attr(a, "min")), int(_attr(a, "max")) + 1):
            styles[c] = st
    return styles


def _build_rows(records, codes, start_row, col_styles) -> tuple[str, int]:
    parts, r = [], start_row
    for rec in records:
        cells = []
        for code, val in sorted(((c, v) for c, v in rec.items() if c in codes and v not in (None, "")),
                                key=lambda cv: col_index(codes[cv[0]])):
            col = codes[code]
            st = col_styles.get(col_index(col))
            s_attr = f' s="{st}"' if st else ""
            cells.append(f'<c r="{col}{r}"{s_attr} t="inlineStr"><is><t xml:space="preserve">'
                         f'{xml_escape(str(val))}</t></is></c>')
        parts.append(f'<row r="{r}">{"".join(cells)}</row>')
        r += 1
    return "".join(parts), r - 1


def _rewrite_sheet(xml: str, records, codes, first_row, mode) -> tuple[str, int]:
    m = re.search(r"<sheetData\s*/>|<sheetData\b[^>]*>(.*?)</sheetData>", xml, re.S)
    if not m:
        raise TemplateError("sheetData element missing in NIC sheet.")
    inner = m.group(1) or ""
    rows = ROW_RE.findall(inner)
    keep, last_used = [], first_row - 1
    for rx in rows:
        rn = int(_attr(rx[:rx.index(">")], "r"))
        has_cells = "<c " in rx or "<c>" in rx
        if rn < first_row:
            keep.append(rx)
        elif mode == "append":
            keep.append(rx)
            if has_cells:
                last_used = max(last_used, rn)
    start = first_row if mode == "replace" else last_used + 1
    new_rows, end_row = _build_rows(records, codes, start, _cols_styles(xml))
    new_inner = "".join(keep) + new_rows
    new_xml = xml[:m.start()] + f"<sheetData>{new_inner}</sheetData>" + xml[m.end():]
    dm = re.search(r'<dimension ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"\s*/>', new_xml)
    if dm:
        max_row = max(end_row, first_row - 1, *(int(_attr(rx[:rx.index(">")], "r")) for rx in keep)) \
            if keep else end_row
        new_xml = new_xml.replace(dm.group(0), f'<dimension ref="{dm.group(1)}{dm.group(2)}:{dm.group(3)}{max_row}"/>')
    return new_xml, start


def write_nic_file(template: str | Path, out_path: str | Path, header_records: list[dict],
                   item_records: list[dict], mode: str = "replace") -> dict:
    """Creates out_path as a copy of the template with eInvoice/Items rows populated.
    The template itself is opened read-only and never modified."""
    template, out_path = Path(template), Path(out_path)
    if template.resolve() == out_path.resolve():
        raise TemplateError("Output path must differ from the NIC template path.")
    before = sha256(template)
    pkg = TemplatePackage(template)
    try:
        targets = {}
        info = {}
        for sheet, recs in (("eInvoice", header_records), ("Items", item_records)):
            codes, _, first = pkg.header_codes(sheet)
            part = pkg.sheet_parts[sheet]
            new_xml, start = _rewrite_sheet(pkg.read(part), recs, codes, first, mode)
            targets[part] = new_xml.encode("utf-8")
            info[sheet] = {"first_row": start, "rows_written": len(recs), "part": part,
                           "pre_existing_rows": pkg.data_row_count(sheet, first)}
        tmp = out_path.with_suffix(".tmp")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp, "w") as zout:
            for zi in pkg.zf.infolist():
                data = targets.get(zi.filename)
                if data is None:
                    data = pkg.zf.read(zi.filename)
                ni = zipfile.ZipInfo(zi.filename, date_time=zi.date_time)
                ni.compress_type = zipfile.ZIP_DEFLATED
                ni.external_attr = zi.external_attr
                zout.writestr(ni, data)
        shutil.move(str(tmp), str(out_path))
    finally:
        pkg.close()
    if sha256(template) != before:          # defensive: should be impossible
        raise TemplateError("SAFETY STOP: the NIC template changed during conversion.")
    info["template_sha256"] = before
    log.info("NIC file written (%s rows eInvoice, %s rows Items)", len(header_records), len(item_records))
    return info


def verify_nic_file(template: str | Path, out_path: str | Path, header_records, item_records, info) -> list[str]:
    """Independent post-write checks. Returns a list of problems (empty = all good)."""
    problems = []
    import xml.dom.minidom
    t, o = zipfile.ZipFile(template), zipfile.ZipFile(out_path)
    try:
        tn, on = set(t.namelist()), set(o.namelist())
        if tn != on:
            problems.append(f"Package parts differ: missing {sorted(tn - on)[:5]}, extra {sorted(on - tn)[:5]}")
        changed = {info["eInvoice"]["part"], info["Items"]["part"]}
        for n in tn & on:
            if n in changed:
                try:
                    xml.dom.minidom.parseString(o.read(n))
                except Exception as e:
                    problems.append(f"{n} is not well-formed XML: {e}")
                continue
            if t.getinfo(n).CRC != o.getinfo(n).CRC:
                problems.append(f"Unexpected change in {n}")
    finally:
        t.close(); o.close()
    if sha256(template) != info["template_sha256"]:
        problems.append("Original NIC template hash changed")
    pkg = TemplatePackage(out_path)
    try:
        for sheet, recs in (("eInvoice", header_records), ("Items", item_records)):
            codes, _, _ = pkg.header_codes(sheet)
            rows = pkg.sheet_rows(sheet)
            start = info[sheet]["first_row"]
            for i, rec in enumerate(recs):
                got = rows.get(start + i, {})
                for code, val in rec.items():
                    if val in (None, "") or code not in codes:
                        continue
                    if got.get(codes[code], "") != str(val):
                        problems.append(f"{sheet} row {start + i} {code}: expected '{val}' got '{got.get(codes[code])}'")
            if info[sheet]["rows_written"] and (start + len(recs)) in rows and rows[start + len(recs)] \
                    and pkg is not None and info.get("mode", "replace") == "replace":
                problems.append(f"{sheet}: unexpected data after the written rows")
    finally:
        pkg.close()
    return problems
