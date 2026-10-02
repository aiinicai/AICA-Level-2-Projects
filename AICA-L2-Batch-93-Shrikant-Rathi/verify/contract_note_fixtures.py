"""Fictitious contract notes (a made-up broker and client) built as real PDFs at test time; nothing is committed.

Layout A: per-fill rows with order/trade numbers and times in positioned columns, ISIN printed, net rate including a
          per-unit brokerage (common for full-service brokers).
Layout B: one line per security, no ISIN, words Buy/Sell, gross value column (common for discount brokers).
Both carry a charges block and a net amount computed from the same figures, so a correct parser reconciles to Rs 0.
"""
import io

BROKER = "Demo Securities Ltd (fictitious)"
PASSWORD = "Demo1234"


def _pdf(pages):
    """pages: list of lists of (x, y, text). Minimal PDF 1.4 with Helvetica, one content stream per page."""
    objs = []

    def esc(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    n_pages = len(pages)
    # 1 catalog, 2 pages, 3 font, then (page, content) pairs
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for i, items in enumerate(pages):
        stream = "".join(f"BT /F1 7 Tf 1 0 0 1 {x} {y} Tm ({esc(t)}) Tj ET\n" for x, y, t in items)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>")
        objs.append(f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}endstream")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offs = []
    for k, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{k} 0 obj\n{o}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for o in offs:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def inr(v):
    """Indian digit grouping: 1,65,133.00"""
    neg, v = v < 0, abs(v)
    s = f"{v:.2f}"
    whole, frac = s.split(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return ("-" if neg else "") + whole + "." + frac


def _charges(buys, sells, brokerage):
    turnover = buys + sells
    exch = round(turnover * 0.0000297, 2)
    sebi = round(turnover * 0.000001, 2)
    stamp = round(buys * 0.00015, 2)
    cgst = round((brokerage + exch + sebi) * 0.09, 2)
    sgst = cgst
    stt = round(turnover * 0.001)
    ch = {"brokerage": brokerage, "exchange": exch, "sebi": sebi, "stamp": stamp, "cgst": cgst, "sgst": sgst, "stt": stt}
    return ch, round(buys - sells + sum(ch.values()), 2)


def _charge_block(ch, net, y0):
    rows = [("Brokerage", ch["brokerage"]), ("Exchange Transaction Charges", ch["exchange"]), ("SEBI Turnover Fees", ch["sebi"]),
            ("Stamp Duty", ch["stamp"]), ("CGST @ 9%", ch["cgst"]), ("SGST @ 9%", ch["sgst"]), ("Securities Transaction Tax", ch["stt"]),
            ("Net Amount Payable by Client" if net >= 0 else "Net Amount Receivable by Client", abs(net))]
    return [(60, y0 - 12 * i, lbl) for i, (lbl, _) in enumerate(rows)] + [(500, y0 - 12 * i, inr(v)) for i, (_, v) in enumerate(rows)]


# Layout A trades: (isin, name, side, qty, gross, brok_per_unit)
A_TRADES = [  # rates near the real month-end closes, so the plausibility check passes
    ("INE040A01034", "HDFC BANK LTD", "B", 60, 730.50, 0.37),
    ("INE040A01034", "HDFC BANK LTD", "B", 40, 731.00, 0.37),
    ("INE467B01029", "TATA CONSULTANCY SERVICES LTD", "B", 25, 2380.00, 1.19),
    ("INE090A01021", "ICICI BANK LTD", "B", 30, 1440.25, 0.72),
]
TRADE_DATE_A = "14/08/2026"


def layout_a():
    items = [(60, 560, BROKER), (60, 548, "CONTRACT NOTE CUM TAX INVOICE"), (60, 536, "Contract Note No: DSL/2026/004512"),
             (400, 536, f"Trade Date: {TRADE_DATE_A}"), (60, 524, "Client: DEMO CLIENT (fictitious)"),
             (60, 500, "Order No"), (130, 500, "Order Time"), (180, 500, "Trade No"), (230, 500, "Trade Time"), (280, 500, "Security / Contract Description"),
             (470, 500, "B/S"), (500, 500, "Quantity"), (545, 500, "Gross Rate"), (600, 500, "Brokerage/Unit"), (665, 500, "Net Rate"), (730, 500, "Net Total")]
    y, buys, brok = 486, 0.0, 0.0
    for k, (isin, name, side, q, g, b) in enumerate(A_TRADES):
        net_rate = round(g + b, 2)
        items += [(60, y, f"13000000{12345670 + k}"), (130, y, "10:15:02"), (180, y, f"5123456{k}"), (230, y, "10:15:03"),
                  (280, y, f"{name} {isin}"), (475, y, side), (505, y, str(q)), (545, y, inr(g)), (600, y, inr(b)), (665, y, inr(net_rate)),
                  (730, y, inr(q * net_rate))]
        buys += q * g; brok += q * b; y -= 12
    ch, net = _charges(round(buys, 2), 0.0, round(brok, 2))
    return _pdf([items + _charge_block(ch, net, y - 20)]), {"buys": round(buys, 2), "net": net, "charges": ch}


# Layout B trades: (name, side, qty, rate)
B_TRADES = [
    ("Reliance Industries Limited", "Buy", 20, 1290.00),
    ("ICICI Bank Limited", "Sell", 10, 1450.40),
]
TRADE_DATE_B = "21-Aug-2026"


def layout_b(trades=None, net_override=None, rate_first=False):
    items = [(60, 560, BROKER), (60, 548, f"Contract Note Number : CN-889201     Trade Date : {TRADE_DATE_B}"),
             (60, 520, "Security Name              Buy/Sell    Qty     Avg Rate     Gross Value")]
    y, buys, sells = 506, 0.0, 0.0
    for name, side, q, r in trades or B_TRADES:
        items.append((60, y, f"{name}   {side}   {inr(r)}   {q}   {inr(q * r)}" if rate_first else f"{name}   {side}   {q}   {inr(r)}   {inr(q * r)}"))
        if side == "Buy":
            buys += q * r
        else:
            sells += q * r
        y -= 12
    ch, net = _charges(round(buys, 2), round(sells, 2), 40.00)
    return _pdf([items + _charge_block(ch, net if net_override is None else net_override, y - 20)]), {"buys": round(buys, 2), "sells": round(sells, 2), "net": net, "charges": ch}


def encrypted(data, password=PASSWORD):
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(data)))
    w.encrypt(password, algorithm="AES-256")
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
