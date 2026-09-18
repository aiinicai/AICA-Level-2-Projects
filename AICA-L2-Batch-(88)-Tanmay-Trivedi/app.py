"""
GST Blocked Credit Checker - Streamlit app
=============================================
Section 17(5), CGST Act, 2017. Three tabs:

    Quick Check  - describe one expense, answer a follow-up question or two
                   if the category needs it, get an instant verdict.
    Bulk Check   - upload an Excel of expense line items, get an annotated,
                   colour-coded verdict report back.
    Invoice Check - upload a photo/PDF invoice, read off a description, and
                   run it through the same engine as Quick Check.

Every tab also raises an independent Reverse Charge Mechanism (RCM) alert
(src/rcm.py, Section 9(3)/9(4)) alongside the Section 17(5) verdict, since
RCM liability and ITC eligibility are two separate questions about the same
expense.

Run with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.ai_explainer import explain
from src.bulk_check import CONDITION_COLUMNS, make_template_bytes, run_bulk_check, to_excel_bytes
from src.invoice_reader import METHOD_LABELS, read_invoice
from src.rcm import match_rcm
from src.rules import ELIGIBLE, NEEDS_INPUT, evaluate, match_categories

st.set_page_config(page_title="GST Blocked Credit Checker", page_icon="\U0001F9FE", layout="centered")

st.title("GST Blocked Credit Checker")
st.caption(
    "Section 17(5), CGST Act, 2017 - a first check on whether Input Tax Credit is blocked. "
    "Reflects the Finance Act 2025 amendment to clauses (c)/(d). Always verify manually before "
    "taking a filing position - this is a planning aid, not a substitute for reading the section."
)


def render_rcm_alert(description: str) -> None:
    """Shown on every tab, independently of the Section 17(5) verdict - RCM
    liability (who pays the GST) and ITC eligibility (can it be claimed) are
    two separate questions about the same expense."""
    rcm_matches = match_rcm(description)
    if not rcm_matches:
        return
    for rc in rcm_matches:
        st.warning(
            f"⚠️ **Possible Reverse Charge Mechanism (RCM) liability - Section {rc.section}** "
            f"({rc.title}). {rc.note} This is independent of the ITC verdict below - if RCM applies, "
            f"you (the recipient) self-invoice and pay the GST directly; verify the specific "
            f"conditions (recipient status, supplier's own charge, notification wording) before "
            f"concluding."
        )


tab1, tab2, tab3 = st.tabs(["Quick Check", "Bulk Check (Excel)", "Invoice Check (Upload)"])

# ============================================================ Tab 1: Quick Check

with tab1:
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "last_desc" not in st.session_state:
        st.session_state.last_desc = ""

    desc = st.text_input(
        "Describe the expense/purchase",
        placeholder="e.g. Car purchased for the managing director's use",
    )

    if desc != st.session_state.last_desc:
        st.session_state.answers = {}
        st.session_state.last_desc = desc

    if desc.strip():
        matches = match_categories(desc)
        render_rcm_alert(desc)

        if not matches:
            st.success(
                "No Section 17(5) block matched this description. It appears **ITC ELIGIBLE**, subject "
                "to the general Section 16 conditions (business use, valid tax invoice, tax actually "
                "paid by the supplier, return filed, etc.). If the description was brief, double-check "
                "manually - the matcher only looks for known keyword phrasing."
            )
        else:
            if len(matches) > 1:
                options = {f"{c.clause} - {c.title}": c for c in matches}
                choice = st.radio(
                    "More than one category matched - which best fits this expense?",
                    list(options.keys()),
                )
                category = options[choice]
            else:
                category = matches[0]
                st.info(f"Matched: **{category.clause} - {category.title}**")

            st.write(category.general_rule)
            if category.special_note:
                st.warning(category.special_note)

            for cond in category.conditions:
                widget_key = f"{category.id}_{cond.key}"
                ans = st.radio(
                    cond.question, ["Not answered yet", "Yes", "No"],
                    key=widget_key, horizontal=True,
                )
                st.session_state.answers[cond.key] = {"Yes": "Y", "No": "N"}.get(ans)

            result = evaluate(category, st.session_state.answers)

            if result["verdict"] == NEEDS_INPUT:
                st.info("Answer the question(s) above to get a verdict.")
            else:
                verdict = result["verdict"]
                if verdict == ELIGIBLE:
                    st.markdown(f"### :green[{verdict}]")
                else:
                    st.markdown(f"### :red[{verdict}]")
                st.write(f"**Clause:** {result['clause']}")
                st.write(result["reasoning"])

                with st.expander("Plain-language explanation (optional, uses Claude if configured)"):
                    if st.button("Generate explanation", key=f"explain_{category.id}"):
                        with st.spinner("Generating..."):
                            text = explain(desc, category.title, result["clause"], verdict, result["reasoning"])
                        st.write(text)
    else:
        st.caption("Type a description above to get started.")

# ============================================================ Tab 2: Bulk Check

with tab2:
    st.write(
        "Upload an Excel sheet with one expense per row under a **Description** column. The optional "
        "columns below let you answer the follow-up conditions in bulk - leave any of them blank and "
        "that row comes back flagged **NEEDS REVIEW** instead of being guessed at. Every row also gets "
        "an independent **RCM Alert** column flagging possible reverse-charge liability (Section "
        "9(3)/9(4)) - a separate question from the ITC verdict itself."
    )
    with st.expander("What are the optional columns for?"):
        for col in CONDITION_COLUMNS:
            st.write(f"- {col}")

    st.download_button(
        "Download blank template (with example rows)",
        data=make_template_bytes(),
        file_name="Blocked_Credit_Bulk_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    uploaded = st.file_uploader("Upload your filled-in Excel", type=["xlsx"])
    if uploaded is not None:
        try:
            df = pd.read_excel(uploaded)
            result_df = run_bulk_check(df)
        except Exception as exc:
            st.error(f"Could not process this file: {exc}")
        else:
            st.write(f"Checked {len(result_df)} row(s).")
            st.dataframe(result_df, use_container_width=True)
            st.download_button(
                "Download annotated report (Excel, colour-coded)",
                data=to_excel_bytes(result_df),
                file_name="Blocked_Credit_Bulk_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ============================================================ Tab 3: Invoice Check (Upload)

with tab3:
    st.write(
        "Upload a photo or PDF of a purchase invoice. The tool reads the goods/services "
        "description off it and matches it against Section 17(5) the same way Quick Check does - "
        "if the matched category needs a follow-up question (e.g. seating capacity, whether it's "
        "obligatory under law), you're asked that here too, since an invoice by itself usually "
        "can't answer that."
    )
    st.caption(
        "How it reads the file: if a Claude API key is configured (`ANTHROPIC_API_KEY`), it's read "
        "via Claude directly - more accurate on real invoice layouts, but the invoice content is "
        "sent to Anthropic's API for that one request. Otherwise it's read entirely offline: a "
        "PDF's own text layer if it has one, or Tesseract OCR (needs the Tesseract engine "
        "installed - see README) if it's a scan or photo. Either way, nothing is saved to disk by "
        "this tool."
    )

    invoice_file = st.file_uploader(
        "Upload invoice (JPG, PNG or PDF)", type=["jpg", "jpeg", "png", "pdf"], key="invoice_upload"
    )

    if invoice_file is not None:
        if st.session_state.get("invoice_last_name") != invoice_file.name:
            file_bytes = invoice_file.getvalue()
            with st.spinner("Reading invoice..."):
                read_result = read_invoice(file_bytes, invoice_file.name)
            st.session_state.invoice_result = read_result
            st.session_state.invoice_last_name = invoice_file.name
            st.session_state.invoice_text_edited = read_result.text
            st.session_state.invoice_answers = {}

        read_result = st.session_state.invoice_result

        if read_result.error:
            st.error(read_result.error)
        else:
            st.success(f"Read via: {METHOD_LABELS.get(read_result.method, read_result.method)}")
            inv_desc = st.text_area(
                "Extracted description (edit if the reading isn't quite right - it re-matches "
                "automatically below)",
                key="invoice_text_edited",
                height=130,
            )

            if inv_desc.strip():
                inv_matches = match_categories(inv_desc)
                render_rcm_alert(inv_desc)

                if not inv_matches:
                    st.success(
                        "No Section 17(5) block matched this description. It appears **ITC "
                        "ELIGIBLE**, subject to the general Section 16 conditions (business use, "
                        "valid tax invoice, tax actually paid by the supplier, return filed, etc.). "
                        "Double-check manually - the matcher only looks for known keyword phrasing, "
                        "and OCR/AI reading of a real invoice can occasionally miss the mark."
                    )
                else:
                    if len(inv_matches) > 1:
                        inv_options = {f"{c.clause} - {c.title}": c for c in inv_matches}
                        inv_choice = st.radio(
                            "More than one category matched - which best fits this expense?",
                            list(inv_options.keys()),
                            key="invoice_category_choice",
                        )
                        inv_category = inv_options[inv_choice]
                    else:
                        inv_category = inv_matches[0]
                        st.info(f"Matched: **{inv_category.clause} - {inv_category.title}**")

                    st.write(inv_category.general_rule)
                    if inv_category.special_note:
                        st.warning(inv_category.special_note)

                    for cond in inv_category.conditions:
                        widget_key = f"invoice_{inv_category.id}_{cond.key}"
                        ans = st.radio(
                            cond.question, ["Not answered yet", "Yes", "No"],
                            key=widget_key, horizontal=True,
                        )
                        st.session_state.invoice_answers[cond.key] = {"Yes": "Y", "No": "N"}.get(ans)

                    inv_result = evaluate(inv_category, st.session_state.invoice_answers)

                    if inv_result["verdict"] == NEEDS_INPUT:
                        st.info("Answer the question(s) above to get a verdict.")
                    else:
                        inv_verdict = inv_result["verdict"]
                        if inv_verdict == ELIGIBLE:
                            st.markdown(f"### :green[{inv_verdict}]")
                        else:
                            st.markdown(f"### :red[{inv_verdict}]")
                        st.write(f"**Clause:** {inv_result['clause']}")
                        st.write(inv_result["reasoning"])

                        with st.expander("Plain-language explanation (optional, uses Claude if configured)"):
                            if st.button("Generate explanation", key=f"invoice_explain_{inv_category.id}"):
                                with st.spinner("Generating..."):
                                    inv_text = explain(
                                        inv_desc, inv_category.title, inv_result["clause"],
                                        inv_verdict, inv_result["reasoning"],
                                    )
                                st.write(inv_text)
    else:
        st.caption("Upload an invoice above to get started.")
