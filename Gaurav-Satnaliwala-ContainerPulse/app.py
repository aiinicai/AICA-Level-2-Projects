from __future__ import annotations

from datetime import datetime
import hashlib
import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from services.connector_setup import discover_and_retest
from services.excel_service import REQUIRED_COLUMNS, read_container_file, results_to_excel
from services.registry_service import ShippingLineRegistry
from services.status_service import classify_container_state
from services.tracking_service import run_tracking_batch

APP_TITLE = "ContainerPulse – Automated Container Tracking & ETA Intelligence"
APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
MASTER_PATH = DATA_DIR / "master_containers.xlsx"
REGISTRY_PATH = DATA_DIR / "shipping_line_registry.json"


def configure_logging() -> None:
    logger = logging.getLogger("containerpulse")
    logger.setLevel(logging.INFO)
    if not any(getattr(handler, "_containerpulse_console", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler._containerpulse_console = True
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)


configure_logging()
registry = ShippingLineRegistry(REGISTRY_PATH)

st.set_page_config(page_title="ContainerPulse", page_icon="🚢", layout="wide")
st.markdown("""
<style>
.block-container {padding-top:1.6rem; padding-bottom:2rem; max-width:1500px;}
.cp-title {font-size:2rem; font-weight:750; color:#0B2848; margin-bottom:.15rem;}
.cp-subtitle {color:#5B6B7A; margin-bottom:1.3rem;}
div[data-testid="stMetric"] {background:#F7FAFC; border:1px solid #DDE6EE; border-radius:12px; padding:14px 16px;}
div[data-testid="stFileUploader"] {border:1px dashed #AFC2D4; border-radius:12px; padding:.3rem .8rem;}
.cp-note {background:#F3F8FC; border-left:4px solid #1677A8; padding:.8rem 1rem; border-radius:6px; color:#29465B;}
.cp-statusbar {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:.75rem; margin:.35rem 0 1rem;}
.cp-statusitem {background:#F7FAFC; border:1px solid #DDE6EE; border-radius:10px; padding:.65rem .85rem; color:#29465B;}
.cp-statuslabel {display:block; color:#6B7C8D; font-size:.78rem; margin-bottom:.15rem;}
.cp-statusvalue {font-weight:700; color:#16324F;}
@media (max-width:800px) {.cp-statusbar {grid-template-columns:1fr;}}
.stButton > button {border-radius:8px; font-weight:650;}
</style>
""", unsafe_allow_html=True)


def activate_source(source, label: str) -> None:
    frame = read_container_file(source)
    st.session_state["input_df"] = frame
    st.session_state["current_source"] = label
    st.session_state.pop("source_error", None)


if "source_initialized" not in st.session_state:
    st.session_state["source_initialized"] = True
    if MASTER_PATH.exists():
        try:
            activate_source(MASTER_PATH, "Master Excel")
        except Exception as exc:
            st.session_state["source_error"] = f"Could not read the Master Excel file: {exc}"

ready_carriers = registry.ready_names()
with st.sidebar:
    page_name = st.radio("Navigation", ["Tracking Dashboard", "Admin / Shipping Line Registry"])
    st.divider()
    visible_browser = st.toggle(
        "Show carrier browser",
        value=True,
        help="Recommended locally and required while setting up a new carrier.",
    )
    st.caption(f"Ready carriers: {' | '.join(ready_carriers) if ready_carriers else 'None'}")
    st.divider()
    st.markdown("**Required Excel columns**")
    for column in REQUIRED_COLUMNS:
        st.caption(f"• {column}")
    sample_path = APP_ROOT / "sample_containerpulse_template.xlsx"
    if sample_path.exists():
        st.download_button(
            "Download sample template",
            data=sample_path.read_bytes(),
            file_name=sample_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def render_header(subtitle: str) -> None:
    st.markdown(f'<div class="cp-title">{APP_TITLE}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="cp-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def format_datetime(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    timestamp = pd.Timestamp(value)
    return timestamp.strftime("%d-%b-%Y") if timestamp.hour == 0 and timestamp.minute == 0 else timestamp.strftime("%d-%b-%Y %H:%M")


def tracking_dashboard() -> None:
    render_header("Retrieve the latest live container status—without carrier APIs.")
    st.subheader("Container source")
    source_controls = st.columns([1, 2])
    with source_controls[0]:
        reload_master = st.button("Reload Master Excel", use_container_width=True, disabled=not MASTER_PATH.exists())
    with source_controls[1]:
        uploaded = st.file_uploader("Optional: use another Excel file", type=["xlsx", "xls"], accept_multiple_files=False)

    if reload_master:
        try:
            activate_source(MASTER_PATH, "Master Excel")
            if uploaded is not None:
                st.session_state["processed_upload_hash"] = hashlib.sha256(uploaded.getvalue()).hexdigest()
            st.success("Reloaded the latest saved rows from master_containers.xlsx.")
        except Exception as exc:
            st.session_state["source_error"] = f"Could not reload the Master Excel file: {exc}"
    elif uploaded is not None:
        upload_hash = hashlib.sha256(uploaded.getvalue()).hexdigest()
        if upload_hash != st.session_state.get("processed_upload_hash"):
            try:
                activate_source(uploaded, "Uploaded Excel")
                st.session_state["processed_upload_hash"] = upload_hash
            except Exception as exc:
                st.session_state["source_error"] = f"Could not read the uploaded Excel file: {exc}"

    input_df = st.session_state.get("input_df")
    current_source = st.session_state.get("current_source")
    source_label = current_source or "No valid source loaded"
    run_label = st.session_state.get("last_tracking_run", "Not run in this session")
    current_ready = registry.ready_names()
    st.markdown(
        f'<div class="cp-statusbar">'
        f'<div class="cp-statusitem"><span class="cp-statuslabel">Current Source</span><span class="cp-statusvalue">{source_label}</span></div>'
        f'<div class="cp-statusitem"><span class="cp-statuslabel">Last Tracking Run</span><span class="cp-statusvalue">{run_label}</span></div>'
        f'<div class="cp-statusitem"><span class="cp-statuslabel">Ready Carriers</span><span class="cp-statusvalue">{" | ".join(current_ready)}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.get("source_error"):
        st.error(st.session_state["source_error"])
    if not isinstance(input_df, pd.DataFrame):
        st.markdown('<div class="cp-note">Upload an Excel file containing <b>Container Number</b> and <b>Shipping Line</b>.</div>', unsafe_allow_html=True)
        return

    st.subheader("Containers to track")
    st.caption(f"Loaded {len(input_df)} container{'s' if len(input_df) != 1 else ''} from {current_source}.")
    st.dataframe(input_df, use_container_width=True, hide_index=True)
    input_carriers = set(input_df["Shipping Line"])
    known = {entry["shipping_line_name"]: entry for entry in registry.list_entries()}
    unsupported = sorted(input_carriers - set(known))
    not_ready = sorted(name for name in input_carriers & set(known) if known[name]["connector_status"] != "Ready")
    if unsupported:
        st.warning(f"Shipping line not currently supported: {', '.join(unsupported)}.")
    if not_ready:
        st.warning(f"Connector not Ready: {', '.join(not_ready)}. Complete setup on the Admin page.")

    if st.button("Track All Containers", type="primary", disabled=input_df.empty):
        progress = st.progress(0, text="Starting tracking run…")
        status_area = st.empty()

        def on_progress(done: int, total: int, container: str, carrier: str) -> None:
            progress.progress(done / total, text=f"Tracked {done} of {total}")
            status_area.info(f"Checking {container} on {carrier}…")

        with st.spinner("Opening carrier tracking pages…"):
            results = run_tracking_batch(
                input_df,
                headless=not visible_browser,
                progress_callback=on_progress,
                registry_path=REGISTRY_PATH,
            )
        st.session_state["tracking_results"] = results
        st.session_state["last_tracking_run"] = datetime.now().astimezone().strftime("%d-%b-%Y %H:%M:%S")
        progress.progress(1.0, text="Tracking run complete")
        status_area.success("All containers processed.")

    render_results(st.session_state.get("tracking_results"))


def render_results(results_df) -> None:
    if not isinstance(results_df, pd.DataFrame) or results_df.empty:
        return
    states = results_df.apply(classify_container_state, axis=1)
    total = len(results_df)
    st.divider()
    st.subheader("Tracking overview")
    for card, label, value in zip(
        st.columns(4),
        ["Total Containers", "In Transit", "Arrived / Completed", "Tracking Errors"],
        [total, int(states.eq("In Transit").sum()), int(states.eq("Arrived / Completed").sum()), int(states.eq("Tracking Error").sum())],
    ):
        card.metric(label, value)

    def row_style(row: pd.Series) -> list[str]:
        color = "background-color:#FFF3CD;color:#664D03" if results_df.loc[row.name, "Tracking Result"] != "Success" else ""
        return [color] * len(row)

    display_results = pd.DataFrame({
        "Container Number": results_df["Container Number"],
        "Shipping Line": results_df["Shipping Line"],
        "Current Status": results_df["Current Status"].replace("", "—").fillna("—"),
        "Current Location": results_df["Current Location"].replace("", "—").fillna("—"),
        "Vessel": results_df["Vessel"].replace("", "—").fillna("—"),
        "Latest ETA": results_df["Latest ETA"].map(format_datetime),
        "Last Tracking Event": results_df["Last Tracking Event"].replace("", "—").fillna("—"),
        "Checked At": results_df["Checked At"].map(format_datetime),
    })
    st.subheader("Latest tracking results")
    st.dataframe(display_results.style.apply(row_style, axis=1), use_container_width=True, hide_index=True, height=min(520, 80 + 36 * len(results_df)))
    failed = results_df[results_df["Tracking Result"] != "Success"]
    if not failed.empty:
        st.subheader("Tracking Errors")
        for _, row in failed.iterrows():
            st.warning(f'{row["Container Number"]} ({row["Shipping Line"]}): {row["Error"] or "Tracking failed"}')
    st.download_button(
        "Download updated results (Excel)",
        data=results_to_excel(results_df),
        file_name=f"ContainerPulse_Results_{datetime.now():%Y%m%d_%H%M}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def registry_admin() -> None:
    render_header("Manage carrier tracking URLs and prototype configurable connectors.")
    st.subheader("Shipping Line Registry")
    entries = registry.list_entries()
    registry_table = pd.DataFrame([{
        "Shipping Line Name": entry["shipping_line_name"],
        "Tracking URL": entry["tracking_url"],
        "Connector Status": entry["connector_status"],
    } for entry in entries])
    st.dataframe(registry_table, use_container_width=True, hide_index=True)

    notice = st.session_state.pop("registry_notice", None)
    if notice:
        (st.success if notice[0] == "success" else st.error)(notice[1])

    with st.expander("Add a new shipping line", expanded=False):
        with st.form("add_carrier_form", clear_on_submit=True):
            new_name = st.text_input("Shipping Line Name")
            new_url = st.text_input("Tracking URL", placeholder="https://carrier.example/track")
            if st.form_submit_button("Add Shipping Line", type="primary"):
                try:
                    registry.add(new_name, new_url)
                    st.session_state["registry_notice"] = ("success", f"{new_name.strip().upper()} added as Not Configured.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    st.subheader("Edit, delete or configure")
    selected_name = st.selectbox("Select Shipping Line", [entry["shipping_line_name"] for entry in entries])
    selected = registry.get(selected_name)
    if not selected:
        return
    built_in = bool(selected.get("built_in"))
    edited_name = st.text_input("Shipping Line Name", value=selected["shipping_line_name"], disabled=built_in)
    edited_url = st.text_input("Tracking URL", value=selected["tracking_url"])
    st.caption(f'Connector Status: **{selected["connector_status"]}**')
    if selected.get("setup_error"):
        st.error(selected["setup_error"])
    action_columns = st.columns(2)
    if action_columns[0].button("Save Changes", use_container_width=True):
        try:
            registry.update(selected_name, edited_name, edited_url)
            st.session_state["registry_notice"] = ("success", "Registry entry updated.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if action_columns[1].button("Delete Entry", use_container_width=True, disabled=built_in):
        try:
            registry.delete(selected_name)
            st.session_state["registry_notice"] = ("success", f"{selected_name} deleted.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Setup Connector")
    if built_in:
        st.info("MSC and MAERSK use protected built-in connectors and are already Ready.")
        return

    input_df = st.session_state.get("input_df")
    test_from_excel = ""
    if isinstance(input_df, pd.DataFrame):
        matching = input_df[input_df["Shipping Line"].eq(selected_name)]
        if not matching.empty:
            test_from_excel = str(matching.iloc[0]["Container Number"])
    if test_from_excel:
        st.success(f"Test container found in the current Excel: {test_from_excel}")
        test_container = test_from_excel
    else:
        st.info("No container for this shipping line exists in the current Excel. Enter one test container number.")
        test_container = st.text_input("Test Container Number", key=f"test_container_{selected_name}")

    st.caption("Setup opens the public tracking page in the installed Chrome/Edge browser. CAPTCHA, login and access controls are never bypassed.")
    if st.button("Setup Connector", type="primary", disabled=not bool(test_container.strip())):
        with st.spinner("Inspecting the carrier page and automatically retesting…"):
            outcome = discover_and_retest(
                selected_name,
                selected["tracking_url"],
                test_container,
                headless=not visible_browser,
            )
        registry.save_setup_result(selected_name, outcome.success, outcome.config, outcome.reason)
        if outcome.success:
            st.session_state["registry_notice"] = ("success", f"{selected_name} connector setup and retest succeeded. Status: Ready.")
        else:
            st.session_state["registry_notice"] = ("error", f"{selected_name} setup failed: {outcome.reason}")
        st.rerun()


if page_name == "Tracking Dashboard":
    tracking_dashboard()
else:
    registry_admin()
