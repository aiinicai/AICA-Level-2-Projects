"""Streamlit UI for importing vendor statements / software exports (uses importer.py)."""
from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

import importer as I
from engine import fmt_inr

KINDS = ["Bill", "Payment", "Skip", "Review"]
STATEMENT, EXPORT = "Vendor statement (one vendor)", "Export from our software"


@st.cache_data(show_spinner="Reading file…")
def _read(data: bytes, name: str):
    return [(s.name, s.df) for s in I.read_raw(data, name)]


def staged_for(slug: str) -> dict:
    return st.session_state.setdefault("staged", {}).setdefault(slug, {})


def staged_totals(slug: str):
    """(bills_raw, pays_raw, n_files) combined across all accepted files for the company."""
    items = list(staged_for(slug).values())
    if not items:
        return None
    return (pd.concat([i["bills"] for i in items], ignore_index=True), pd.concat([i["pays"] for i in items], ignore_index=True), len(items))


def render(slug: str, master: pd.DataFrame) -> None:
    names = master["Vendor Name"].dropna().tolist() if len(master) else []
    st.caption("Upload vendor statements, or reports exported from your accounting software (Excel / CSV / text-based PDF). "
               "The layout is detected automatically; check the result, fix anything wrong, then add it to the run.")
    ups = st.file_uploader("Statements / exports", type=["xlsx", "xls", "csv", "pdf"], accept_multiple_files=True, key=f"imp_{slug}")
    for up in ups or []:
        fkey = hashlib.md5(f"{up.name}:{up.size}".encode()).hexdigest()[:10]
        with st.expander(f"📄 {up.name}", expanded=fkey not in staged_for(slug)):
            _one_file(slug, fkey, up, names)


def _one_file(slug: str, fkey: str, up, names: list[str]) -> None:
    try:
        sheets = _read(up.getvalue(), up.name)
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
        return

    kind = st.radio("This file is", [STATEMENT, EXPORT], horizontal=True, key=f"k_{fkey}")
    scored = sorted(range(len(sheets)), key=lambda i: (I.analyse(sheets[i][1]).score, len(sheets[i][1])), reverse=True)
    if len(sheets) > 1:
        si = st.selectbox("Sheet / table", scored, format_func=lambda i: sheets[i][0], key=f"sh_{fkey}")
    else:
        si = 0
    raw = sheets[si][1]
    det = I.analyse(raw)

    hdr_default = (det.header_idx or 0) + 1
    c1, c2 = st.columns([1, 3])
    hdr = int(c1.number_input("Header row", 1, max(len(raw), 1), hdr_default, key=f"hr_{fkey}_{si}",
                              help="Row number (in the file) that holds the column headings."))
    mapping_auto = I.map_header_row(raw, hdr - 1)
    c2.caption(f"Detected layout: **{I.layout_label(mapping_auto)}**" if mapping_auto else "⚠️ Could not recognise the columns – map them below.")

    labels = [f"{j + 1}: {str(v)[:25]}" for j, v in enumerate(raw.iloc[hdr - 1].tolist())]
    with st.expander("Column mapping (auto-detected – change if wrong)", expanded=not mapping_auto):
        cols = st.columns(5)
        mapping = {}
        for n, f in enumerate(I.FIELDS):
            default = mapping_auto.get(f)
            opts = [None] + list(range(len(labels)))
            choice = cols[n % 5].selectbox(f, opts, index=0 if default is None else default + 1,
                                           format_func=lambda j: "(none)" if j is None else labels[j],
                                           key=f"map_{fkey}_{si}_{hdr}_{f}")
            if choice is not None:
                mapping[f] = choice
    if not ({"Debit", "Credit", "Amount"} & set(mapping)) or "Date" not in mapping:
        st.error("Map at least a Date column and an Amount (or Debit/Credit) column.")
        return
    rows = I.build_rows(raw, hdr - 1, mapping)

    # direction convention
    inferred = I.infer_perspective(rows)
    default_persp = inferred or ("vendor" if kind == STATEMENT else "ours")
    persp_opts = {"vendor": "Vendor's own statement – Debit = invoices raised, Credit = receipts",
                  "ours": "Our ledger of the vendor – Credit = bills booked, Debit = payments made"}
    persp = st.radio("Debit / Credit convention", list(persp_opts), format_func=persp_opts.get, index=list(persp_opts).index(default_persp),
                     key=f"p_{fkey}", horizontal=False,
                     help="Auto-detected from invoice/payment wording." if inferred else "Could not be inferred from the wording – please confirm.")
    if inferred:
        st.caption(f"Auto-detected from the wording: {'vendor statement' if inferred == 'vendor' else 'our ledger'} convention.")

    # vendor
    vendor = None
    if "Vendor" in mapping:
        st.caption("Vendor taken from the Vendor column (matched to the vendor master).")
    else:
        guess = I.guess_vendor(det.preamble, names) if names else None
        opts = names + ["Other (not in master)"]
        vi = st.selectbox("Vendor this file belongs to", opts, index=opts.index(guess) if guess in opts else None,
                          placeholder="Choose vendor…", key=f"v_{fkey}")
        vendor = vi
        if vi == "Other (not in master)" or (not names):
            vendor = st.text_input("Vendor name", key=f"vn_{fkey}") or None
        if guess:
            st.caption(f"Vendor name found in the file header: {guess}")

    dk = st.radio("Rows with no clear Bill/Payment signal are treated as", ["Ask me (Review)", "Bills", "Payments"], horizontal=True,
                  key=f"dk_{fkey}")
    default_kind = {"Ask me (Review)": None, "Bills": "Bill", "Payments": "Payment"}[dk]

    cl = I.classify(rows, persp, default_kind)
    n = cl["Kind"].value_counts()
    m = st.columns(4)
    m[0].metric("Bills", int(n.get("Bill", 0)))
    m[1].metric("Payments", int(n.get("Payment", 0)))
    m[2].metric("Skipped (totals, opening bal.)", int(n.get("Skip", 0)))
    m[3].metric("Need review", int(n.get("Review", 0)))
    if (cl["Check"] != "").any():
        st.warning(f"{int((cl['Check'] != '').sum())} row(s) are flagged in the Check column – the wording disagrees with the Debit/Credit side. "
                   "If many rows are flagged, switch the convention above.")

    view = cl[["Kind", "Date", "Vendor", "Ref", "Description", "Amt", "Basis", "Check"]].copy()
    view["Amt"] = view["Amt"].map(fmt_inr)
    sig = hashlib.md5(f"{persp}{default_kind}{sorted(mapping.items())}{hdr}{si}".encode()).hexdigest()[:8]
    edited = st.data_editor(
        view, hide_index=True, width="stretch", height=300, key=f"ed_{fkey}_{sig}",
        disabled=[c for c in view.columns if c != "Kind"],
        column_config={"Kind": st.column_config.SelectboxColumn(options=KINDS, required=True, help="Change a row's classification if needed."),
                       "Date": st.column_config.DateColumn(format="DD-MM-YYYY"),
                       "Amt": st.column_config.TextColumn("Amount")})
    cl["Kind"] = edited["Kind"].values

    staged = staged_for(slug)
    c1, c2 = st.columns([1, 3])
    if fkey in staged:
        s = staged[fkey]
        c2.success(f"Added to this run: {len(s['bills'])} bills, {len(s['pays'])} payments.")
        for note in s["notes"]:
            c2.caption("• " + note)
        if c1.button("Remove", key=f"rm_{fkey}"):
            staged.pop(fkey, None)
            st.rerun()
    else:
        if c1.button("✅ Add to this run", type="primary", key=f"add_{fkey}", disabled=vendor is None and "Vendor" not in mapping):
            if (cl["Kind"] == "Review").any():
                st.warning("Rows still marked 'Review' were left out.")
            bills, pays, notes = I.to_inputs(cl, vendor, names)
            staged[fkey] = {"bills": bills, "pays": pays, "notes": notes, "name": up.name}
            st.rerun()
