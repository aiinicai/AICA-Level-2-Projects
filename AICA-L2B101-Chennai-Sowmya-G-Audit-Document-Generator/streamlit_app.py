# ============================================================
#  Statutory Audit Document Generator - browser version (Streamlit)
#  Sowmya G & Associates
#
#  Run on your own computer (any OS):
#     py -m pip install -r requirements.txt
#     py -m streamlit run streamlit_app.py
#  It opens in your web browser at http://localhost:8501
#
#  Keep these files in one folder:
#     streamlit_app.py, audit_engine.py, ca_logo.jpeg, requirements.txt
# ============================================================

import io
import os
import re
import tempfile
import zipfile
from datetime import date

import pandas as pd
import streamlit as st

import audit_engine as eng


st.set_page_config(page_title="Audit Document Generator", page_icon="\U0001F4C4",
                   layout="wide")


# ------------------------------------------------------------
# 1. Optional password (used only when a password is set in secrets)
# ------------------------------------------------------------

def app_password():
    try:
        return st.secrets.get("app_password", "")
    except Exception:            # no secrets file at all - running locally
        return ""


def password_ok():
    password = app_password()
    if not password:
        return True
    if st.session_state.get("signed_in"):
        return True
    st.title("Audit Document Generator")
    entered = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if entered == password:
            st.session_state["signed_in"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    return False


if not password_ok():
    st.stop()


# ------------------------------------------------------------
# 2. Starting values (kept in session_state so the PDF can fill them)
# ------------------------------------------------------------

DIRECTOR_COLUMNS = ["Name", "DIN", "Designation"]


def empty_directors():
    return pd.DataFrame([{"Name": "", "DIN": "", "Designation": "Director"}
                         for _ in range(eng.NUMBER_OF_DIRECTORS)])


defaults = {
    "company": "", "cin": "", "address": "", "constitution": "", "private": True,
    "directors": empty_directors(), "editor_version": 0,
}
for key, value in eng.FIRM_DEFAULTS.items():
    defaults[key] = value
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def load_mca_pdf():
    """Runs when a master data PDF is uploaded: fill the company fields."""
    uploaded = st.session_state.get("mca_pdf")
    if uploaded is None:
        return
    try:
        found, line_count = eng.extract_master_data(io.BytesIO(uploaded.getvalue()))
    except Exception as error:
        st.session_state["pdf_message"] = ("error", "Could not read the PDF: " + str(error))
        return
    if line_count == 0:
        st.session_state["pdf_message"] = ("error", "This PDF has no readable text (it may "
                                           "be a scanned image). Please type the details.")
        return

    labels = {"company": "Company name", "cin": "CIN", "address": "Registered office",
              "constitution": "Constitution"}
    filled, missing = [], []
    for key, label in labels.items():
        if found[key]:
            st.session_state[key] = found[key]
            filled.append(label)
        else:
            missing.append(label)
    if found["constitution"]:
        text = found["constitution"].lower()
        st.session_state["private"] = "private" in text or "one person" in text

    directors = found["directors"][:eng.NUMBER_OF_DIRECTORS]
    table = empty_directors()
    for i, director in enumerate(directors):
        table.loc[i, "Name"] = director["name"]
        table.loc[i, "DIN"] = director["din"]
    st.session_state["directors"] = table
    st.session_state["editor_version"] += 1          # redraw the directors table
    if directors:
        filled.append(str(len(directors)) + " director(s)")
    else:
        missing.append("Directors")

    message = "Filled from PDF: " + ", ".join(filled) if filled else "Nothing could be read."
    if missing:
        message += ". Not found, please type in: " + ", ".join(missing)
    if found["cin"].startswith("L"):
        message += ". Note: the CIN shows this is a listed company."
    st.session_state["pdf_message"] = ("info", message + ". Please check before generating.")


# ------------------------------------------------------------
# 3. Sidebar: auditor and letterhead (rarely changes)
# ------------------------------------------------------------

with st.sidebar:
    st.header("Auditor")
    st.text_input("Firm name *", key="firm")
    st.text_input("Signing auditor *", key="auditor")
    st.selectbox("Designation", ["Proprietor", "Partner"], key="designation")
    st.text_input("FRN *", key="frn")
    st.text_input("Membership no. *", key="membership")
    st.text_input("UDIN (audit report)", key="udin")
    st.text_input("Place *", key="place")
    with st.expander("Letterhead"):
        st.text_input("Address line 1", key="firm_address1")
        st.text_input("Address line 2", key="firm_address2")
        st.text_input("Phone", key="phone")
        st.text_input("Email", key="email")
        st.text_input("Website", key="website")
        logo_upload = st.file_uploader("Logo (optional, replaces ca_logo.jpeg)",
                                       type=["png", "jpg", "jpeg"])


# ------------------------------------------------------------
# 4. Main page
# ------------------------------------------------------------

st.title("Statutory Audit Document Generator")
st.caption("Letter of Engagement • DSC Authorisation • Letter of Representation "
           "• Independent Auditor's Report with CARO 2020 / IFC annexures "
           "(Accounting Standards)")

tab1, tab2, tab3, tab4 = st.tabs(["1. Company & Directors", "2. Opinion & Reporting",
                                  "3. Company facts", "4. Dates"])

with tab1:
    st.file_uploader("MCA master data PDF (fills company name, CIN, registered office, "
                     "constitution and directors)", type=["pdf"], key="mca_pdf",
                     on_change=load_mca_pdf)
    if "pdf_message" in st.session_state:
        kind, text = st.session_state["pdf_message"]
        (st.error if kind == "error" else st.info)(text)

    left, right = st.columns(2)
    with left:
        st.text_input("Company name *", key="company")
        st.text_input("CIN *", key="cin")
        st.text_area("Registered office *", key="address", height=80)
    with right:
        st.text_input("Constitution", key="constitution")
        st.checkbox("Private company", key="private")
        st.selectbox("Financial year", eng.financial_year_choices(), key="fy")
        st.selectbox("Result for the year", ["profit", "loss"], key="result")
        st.checkbox("Cash Flow Statement prepared (not required for small companies / OPC)",
                    value=True, key="cash_flow")

    st.subheader("Directors")
    st.caption("The first two sign the engagement acknowledgement and the representation "
               "letter. Each director gets a DSC authorisation page.")
    directors_table = st.data_editor(
        st.session_state["directors"], num_rows="fixed", hide_index=True,
        width="stretch", key="directors_editor_" + str(st.session_state["editor_version"]),
        column_config={
            "Name": st.column_config.TextColumn("Name", width="large"),
            "DIN": st.column_config.TextColumn("DIN", max_chars=8),
            "Designation": st.column_config.SelectboxColumn(
                "Designation", options=eng.DIRECTOR_DESIGNATIONS, required=True),
        })

with tab2:
    opinion = st.selectbox("Type of opinion", eng.OPINIONS, key="opinion")
    basis_text = st.text_area("Matter giving rise to the modification",
                              disabled=opinion == "Unmodified", key="basis_text")
    eom = st.text_area("Emphasis of Matter (leave blank if none)",
                       disabled=opinion == "Disclaimer", key="eom")
    st.checkbox("CARO 2020 applies (adds Annexure)", value=True, key="caro")
    st.checkbox("Report on Internal Financial Controls required (adds Annexure)", key="ifc")
    st.checkbox("Company has pending litigations", key="litigation")
    st.markdown("**Audit trail (edit log) in accounting software**")
    trail = st.radio("Audit trail maintained?", eng.AUDIT_TRAIL_OPTIONS, key="audit_trail")
    trail_from = st.date_input("Enabled from", value=None, format="DD/MM/YYYY",
                               disabled=trail != eng.AUDIT_TRAIL_OPTIONS[1],
                               key="audit_trail_from")

with tab3:
    st.caption("Tick what applies. These drive the CARO 2020 annexure and the Letter of "
               "Representation. Unticked items are reported as 'not applicable' or 'nil'. "
               "Yellow highlights in the documents need your input.")
    columns = st.columns(2)
    for number, (key, label, default) in enumerate(eng.CARO_ITEMS):
        with columns[number % 2]:
            st.checkbox(label, value=default, key=key)

with tab4:
    a, b, c = st.columns(3)
    a.date_input("Engagement letter & DSC *", value=date.today(), format="DD/MM/YYYY",
                 key="engagement_date")
    b.date_input("Letter of representation *", value=date.today(), format="DD/MM/YYYY",
                 key="mrl_date")
    c.date_input("Signing of audit report *", value=date.today(), format="DD/MM/YYYY",
                 key="report_date")


# ------------------------------------------------------------
# 5. Collect, check and generate
# ------------------------------------------------------------

DOCUMENTS = [
    ("gen_eng", "Letter of Engagement", "1_Letter_of_Engagement", eng.make_engagement_letter),
    ("gen_dsc", "DSC Authorisation Letter", "2_DSC_Authorisation_Letter", eng.make_dsc_letters),
    ("gen_mrl", "Letter of Representation", "3_Letter_of_Representation", eng.make_mrl),
    ("gen_report", "Audit Report (with annexures)", "4_Independent_Auditors_Report",
     eng.make_audit_report),
]


def as_text(value):
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else ""


def collect_details():
    s = st.session_state
    keys = ["company", "cin", "address", "constitution", "private", "fy", "result",
            "cash_flow", "opinion", "caro", "ifc", "litigation", "audit_trail",
            "firm", "auditor", "designation", "frn", "membership", "udin", "place",
            "firm_address1", "firm_address2", "phone", "email", "website"]
    d = {key: (s[key].strip() if isinstance(s[key], str) else s[key]) for key in keys}
    d["address"] = " ".join(d["address"].split())
    d["basis_text"] = (s.get("basis_text") or "").strip() if d["opinion"] != "Unmodified" else ""
    d["eom"] = (s.get("eom") or "").strip() if d["opinion"] != "Disclaimer" else ""
    for key, _, default in eng.CARO_ITEMS:
        d[key] = s.get(key, default)
    for key in ("engagement_date", "mrl_date", "report_date", "audit_trail_from"):
        d[key] = as_text(s.get(key))
    d["directors"] = []
    for _, row in directors_table.iterrows():
        name = str(row["Name"] or "").strip()
        if name:
            d["directors"].append({"name": name, "din": str(row["DIN"] or "").strip(),
                                   "designation": row["Designation"] or "Director"})
    d.update(eng.fy_details(d["fy"]))
    if d["udin"] == "":
        d["udin"] = "____________________"
    d["logo"] = logo_path()
    for key, _, _, _ in DOCUMENTS:
        d[key] = s.get(key, True)
    return d


def logo_path():
    if logo_upload is not None:
        suffix = os.path.splitext(logo_upload.name)[1]
        handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        handle.write(logo_upload.getvalue())
        handle.close()
        return handle.name
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "ca_logo.jpeg")
    return path if os.path.exists(path) else ""


def check_details(d):
    problems = []
    required = {"company": "Company name", "cin": "CIN", "address": "Registered office",
                "firm": "Firm name", "auditor": "Signing auditor", "frn": "FRN",
                "membership": "Membership no.", "place": "Place"}
    for key, label in required.items():
        if not d[key]:
            problems.append(label + " is empty")
    for key, label in (("engagement_date", "Engagement date"), ("mrl_date", "MRL date"),
                       ("report_date", "Audit report date")):
        if not d[key]:
            problems.append(label + " is missing")
    if d["opinion"] != "Unmodified" and not d["basis_text"]:
        problems.append("Describe the matter giving rise to the modification (tab 2)")
    if d["audit_trail"] == eng.AUDIT_TRAIL_OPTIONS[1] and not d["audit_trail_from"]:
        problems.append("Enter the date from which audit trail was enabled (tab 2)")
    if (d["gen_eng"] or d["gen_dsc"] or d["gen_mrl"]) and not d["directors"]:
        problems.append("Enter at least one director (tab 1)")
    for director in d["directors"]:
        if not re.fullmatch(r"\d{8}", director["din"]):
            problems.append("DIN of " + director["name"] + " should be 8 digits")
    if not any(d[key] for key, _, _, _ in DOCUMENTS):
        problems.append("Tick at least one document")
    return problems


st.divider()
st.subheader("Generate")
picks = st.columns(4)
for column, (key, label, _, _) in zip(picks, DOCUMENTS):
    column.checkbox(label, value=True, key=key)

if st.button("Generate documents", type="primary"):
    details = collect_details()
    problems = check_details(details)
    if problems:
        st.error("Please check:\n\n- " + "\n- ".join(problems))
    else:
        if not re.fullmatch(eng.CIN_PATTERN, details["cin"]):
            st.warning("The CIN does not look like the usual 21-character format. "
                       "Documents were still created - please check.")
        folder = eng.safe_name(details["company"]) + "_FY_" + details["fy"]
        files = {}
        for key, label, file_name, maker in DOCUMENTS:
            if details[key]:
                buffer = io.BytesIO()
                maker(details, buffer)
                files[file_name + ".docx"] = buffer.getvalue()
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(folder + "/" + name, data)
        st.session_state["output"] = (folder, files, bundle.getvalue())

if "output" in st.session_state:
    folder, files, bundle = st.session_state["output"]
    st.success("Created " + str(len(files)) + " document(s). Review all wording and the "
               "yellow highlights before issuing.")
    st.download_button("Download all (" + folder + ".zip)", bundle, file_name=folder + ".zip",
                       mime="application/zip", type="primary")
    word = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    for column, (name, data) in zip(st.columns(len(files)), files.items()):
        column.download_button(name.replace("_", " ").replace(".docx", ""), data,
                               file_name=name, mime=word)
