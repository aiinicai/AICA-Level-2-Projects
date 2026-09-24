# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Dashboard: KPI cards and charts for the logged-in user's leases, ONE currency at a time.

Amounts are never added across currencies: pick a currency and every money figure below is for
that currency only. Counts of leases (by status / classification) are plain counts.

The page comes in three layouts (Classic, Modern, Pro), each in a light and a dark theme; the user
chooses in Settings or in the 'Appearance' menu at the top of this page.
"""
from datetime import date, datetime

import pandas as pd
import streamlit as st

from auth_ui import require_login, set_flash, show_flash
from core import dashboard as dash
from core.branding import TAGLINE
from core.bulk import build_template_bytes
from core.dashboard_pdf import build_pdf
from core.dashboard_report import build_report, file_stem
from core.dashboard_xlsx import build_excel
from core.formatting import NUMBER_FORMATS, currency_label, format_money
from core.themes import LAYOUTS, THEMES, palette
from core.workflow import (
    get_dashboard_leases,
    get_dashboard_schedule_rows,
    get_dashboard_stamp,
    save_user_preferences,
)
from dashboard_views import (
    CLASSIFICATION_COLORS,
    STATUS_COLORS,
    donut_figure,
    greeting,
    interest_principal_figure,
    kpi_card_html,
    local_now,
    maturity_figure,
    ring_svg_html,
    stat_values,
    trend_sub,
)
from db.database import get_session
from lease_ui import amount_table

st.set_page_config(page_title="LeaseIQ Pro - Dashboard", page_icon="📊", layout="wide")
user = require_login()
tokens = palette(user.get("dashboard_layout", "classic"), user.get("theme", "light"))
layout = tokens["layout"]
number_style = user.get("number_format", "indian")

INCLUDE_CHOICES = {
    "All calculated leases (pending review, approved, active)": dash.INCLUDE_VALIDATED,
    "Approved and active leases only": dash.INCLUDE_APPROVED,
}
FRAMEWORK_CHOICES = {"ASC 842 view": "ASC_842", "Ind AS 116 view": "IND_AS_116"}


# ------------------------------- cached data -------------------------------- #
@st.cache_data(show_spinner=False)
def load_leases(user_id: int, stamp: tuple) -> list:
    """All of this user's leases (cached; ``stamp`` changes whenever their data does)."""
    with get_session() as session:
        return get_dashboard_leases(session, user_id)


@st.cache_data(show_spinner=False)
def load_schedule(user_id: int, framework: str, stamp: tuple):
    """The saved schedule rows for one framework, prepared for the dashboard (cached)."""
    with get_session() as session:
        rows = get_dashboard_schedule_rows(session, user_id, framework)
    return dash.prepare_schedule(rows)


@st.cache_data(show_spinner=False)
def portfolio_monthly(user_id: int, framework: str, currency: str, statuses: tuple, today_iso: str, stamp: tuple):
    """Interest / principal / cash by month for the next 60 months, ONE currency (cached)."""
    scope_ids = [lease["case_id"] for lease in dash.money_scope(load_leases(user_id, stamp), currency, statuses)]
    return dash.monthly_portfolio(load_schedule(user_id, framework, stamp), scope_ids, date.fromisoformat(today_iso), 60)


@st.cache_data(show_spinner=False)
def template_bytes() -> bytes:
    return build_template_bytes()


@st.cache_data(show_spinner=False)
def export_files(
    user_id: int, framework: str, currency: str, statuses: tuple, include_label: str, framework_label: str,
    number_style: str, today_iso: str, stamp: tuple, prepared_by: str, minute: str,
) -> dict:
    """The dashboard as an Excel workbook and a PDF, for the current filters (cached; ``minute`` keeps the timestamp honest)."""
    report = build_report(
        load_leases(user_id, stamp), load_schedule(user_id, framework, stamp), currency, statuses, include_label,
        framework_label, number_style, date.fromisoformat(today_iso), prepared_by, datetime.now(),
    )
    return {"excel": build_excel(report), "pdf": build_pdf(report), "stem": file_stem(report)}


def _save_appearance() -> None:
    """Callback of the 'Appearance' menu: remember the theme and layout, the page then redraws in them."""
    current = st.session_state["user"]
    try:
        with get_session() as session:
            save_user_preferences(
                session,
                current["user_id"],
                current["number_format"],
                current["default_currency"],
                st.session_state.get("dash_theme"),
                st.session_state.get("dash_layout"),
            )
    except ValueError as exc:
        set_flash("error", str(exc))


with get_session() as session:
    stamp = get_dashboard_stamp(session, user["user_id"])
leases = load_leases(user["user_id"], stamp)
show_flash()


def _appearance_menu() -> None:
    with st.popover("Appearance", icon=":material/palette:"):
        themes_list, layouts_list = list(THEMES), list(LAYOUTS)
        st.radio(
            "Theme", themes_list, index=themes_list.index(tokens["theme"]), format_func=THEMES.get,
            horizontal=True, key="dash_theme", on_change=_save_appearance,
        )
        st.radio(
            "Layout", layouts_list, index=layouts_list.index(layout), format_func=lambda key: LAYOUTS[key]["label"],
            key="dash_layout", on_change=_save_appearance,
        )
        st.caption("More about each layout, with previews, on the Settings page.")


# ------------------------------- header row -------------------------------- #
head_left, head_search, head_right = st.columns([4, 3, 2])
if layout != "modern":  # the top bar of the Modern layout already carries the brand
    head_left.markdown("## LeaseIQ Pro")
head_left.caption(TAGLINE)
search_text = head_search.text_input(
    "Search leases", key="dash_search", placeholder="Search by lease ID, lessor or lessee", label_visibility="collapsed"
)
with head_right:
    if layout != "modern":
        st.markdown("**{}**  \n{}".format(user["name"], user["role"]))
    appearance_column, export_column = st.columns(2)
    with appearance_column:
        _appearance_menu()
    export_slot = export_column.container()  # filled in below, once the filters are known

if search_text.strip():
    found = dash.search_leases(leases, search_text)
    if not found:
        st.info("No lease matches '{}'.".format(search_text.strip()))
    for lease in found:
        label = "Open {} - {} / {}".format(lease["lease_ref"], lease["lessor"] or "-", lease["lessee"] or "-")
        if st.button(label, key="dash_open_{}".format(lease["case_id"])):
            st.session_state["lease_view"] = {
                "mode": "results" if lease["has_results"] else "review",
                "case_id": lease["case_id"],
            }
            st.switch_page("pages/2_Leases.py")


# ------------------------------ greeting row ------------------------------- #
def _greeting_row() -> None:
    st.markdown("### {}".format(greeting(local_now(getattr(st.context, "timezone", None)), user["name"])))
    st.caption("Here is where your lease portfolio stands today.")


if layout == "modern":
    with st.container(key="hero"):
        _greeting_row()
else:
    _greeting_row()

# ------------------------------- empty state ------------------------------- #
if not leases:
    st.info(
        "You have no leases yet. Upload a contract, add one manually, or import many at once with Bulk Upload - "
        "your numbers and charts will appear here as soon as you do."
    )
    st.stop()

# -------------------------------- filters ---------------------------------- #
options = dash.currency_options(leases)
codes = [code for code, _ in options]
counts = dict(options)
if st.session_state.get("dash_currency") not in codes:  # e.g. a currency that no longer has any lease
    st.session_state.pop("dash_currency", None)
default_index = codes.index(dash.default_currency(options, user.get("default_currency", "INR")))
filter_currency, filter_include, filter_framework = st.columns(3)
currency = filter_currency.selectbox(
    "Currency",
    codes,
    index=default_index,
    format_func=lambda code: "{}  ({} lease{})".format(currency_label(code), counts[code], "" if counts[code] == 1 else "s"),
    key="dash_currency",
)
include_label = filter_include.radio("Leases included in the amounts", list(INCLUDE_CHOICES), key="dash_include")
framework_label = filter_framework.radio("Reporting view", list(FRAMEWORK_CHOICES), horizontal=True, key="dash_framework")
statuses = INCLUDE_CHOICES[include_label]

schedule = load_schedule(user["user_id"], FRAMEWORK_CHOICES[framework_label], stamp)
in_currency = dash.leases_in_currency(leases, currency)
scope = dash.money_scope(leases, currency, statuses)
case_ids = [lease["case_id"] for lease in scope]
today = date.today()
metrics = dash.kpis(leases, currency, statuses, schedule, today)
monthly = portfolio_monthly(
    user["user_id"], FRAMEWORK_CHOICES[framework_label], currency, tuple(statuses), today.isoformat(), stamp
)


def money(value: float) -> str:
    return format_money(value, currency, number_style)


with export_slot:
    with st.popover("Export", icon=":material/download:"):
        files = export_files(
            user["user_id"], FRAMEWORK_CHOICES[framework_label], currency, tuple(statuses), include_label, framework_label,
            number_style, today.isoformat(), stamp, user["name"], datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        st.download_button(
            "Excel workbook (.xlsx)", data=files["excel"], file_name=files["stem"] + ".xlsx", key="export_excel",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/table_view:",
        )
        st.download_button(
            "PDF report (.pdf)", data=files["pdf"], file_name=files["stem"] + ".pdf", key="export_pdf",
            mime="application/pdf", icon=":material/picture_as_pdf:",
        )
        st.caption(
            "Everything on this dashboard for {} with the filters you have chosen: key figures, status and classification, "
            "liability maturity, interest vs principal and future payments.".format(currency)
        )


# ------------------------------- KPI cards --------------------------------- #
def kpi_row() -> None:
    total_sub = []
    if metrics["new_this_month"]:
        total_sub.append("{} new this month".format(metrics["new_this_month"]))
    if metrics["leases_in_other_currencies"]:
        total_sub.append("{} more in other currencies".format(metrics["leases_in_other_currencies"]))
    cards = st.columns(4)
    cards[0].markdown(
        kpi_card_html(
            "Total Leases", str(metrics["total_leases"]), " | ".join(total_sub), tokens["kpi_blue"], variant=layout, icon="file"
        ),
        unsafe_allow_html=True,
    )
    for column, key, label, accent, icon in (
        (cards[1], "liability", "Total Lease Liability", tokens["kpi_green"], "coins"),
        (cards[2], "rou_net", "ROU Asset (Net)", tokens["kpi_purple"], "layers"),
        (cards[3], "expense", "Monthly Lease Expense", tokens["kpi_orange"], "wallet"),
    ):
        item = metrics[key]
        text = money(item["value"])
        column.markdown(
            kpi_card_html(
                label, text, trend_sub(item["trend"]), accent, item["trend"]["direction"],
                variant=layout, icon=icon, compact=len(text) > 15,
            ),
            unsafe_allow_html=True,
        )
    st.caption(
        "Amounts are for {} (month-end balances), in {}, from {} calculated lease{}. Amounts in other currencies are never "
        "added to these figures.  Number format: {}.".format(
            metrics["month"].strftime("%B %Y"),
            currency_label(currency),
            metrics["leases_counted"],
            "" if metrics["leases_counted"] == 1 else "s",
            NUMBER_FORMATS.get(number_style, number_style),
        )
    )
    if not scope:
        st.info("No calculated leases in {} match the selected status yet, so the amounts are zero.".format(currency))


def charts_row() -> None:
    status_column, classification_column, maturity_column = st.columns(3)
    with status_column, st.container(border=True):
        st.markdown("#### Leases by Status")
        st.plotly_chart(donut_figure(dash.status_counts(in_currency), STATUS_COLORS, palette=tokens), key="chart_status")
    with classification_column, st.container(border=True):
        st.markdown("#### Leases by Classification (ASC 842)")
        classified = dash.classification_counts(in_currency)
        st.plotly_chart(donut_figure(classified, CLASSIFICATION_COLORS, palette=tokens), key="chart_classification")
        if not classified:
            st.caption("Leases appear here once they have been calculated.")
    with maturity_column, st.container(border=True):
        st.markdown("#### Total Lease Liability Maturity (Next 5 Years)")
        buckets = dash.maturity_by_year(schedule, case_ids, today)
        st.plotly_chart(maturity_figure(buckets, currency, number_style, palette=tokens), key="chart_maturity")
        st.caption("Undiscounted payments due in each 12-month window from next month, in {}.".format(currency))


# ----------------------- interest vs principal, payments -------------------- #
def line_chart_card(height: int) -> None:
    with st.container(border=True):
        st.markdown("#### Interest vs. Principal - Next 60 Months (Portfolio)")
        crossover = dash.crossover_summary(monthly)
        st.plotly_chart(
            interest_principal_figure(monthly, currency, number_style, crossover.get("month"), palette=tokens, height=height),
            key="chart_interest_principal",
        )
        st.caption(dash.crossover_text(crossover))


def payments_card(rings: bool) -> None:
    with st.container(border=True):
        st.markdown("#### Future Payments Overview")
        window = st.radio(
            "Period", dash.PAYMENT_WINDOWS, format_func=lambda months: "{} months".format(months), horizontal=True, key="dash_window"
        )
        overview = dash.future_payments(monthly, window)
        if rings:  # how the payments split into interest and principal
            total = overview["interest"] + overview["principal"]
            interest_share = overview["interest"] / total * 100 if total else 0
            st.markdown(
                '<div class="ring-row">{}{}</div>'.format(
                    ring_svg_html(interest_share, tokens["interest"], tokens["surface_alt"], "Interest", tokens["text"]),
                    ring_svg_html(100 - interest_share if total else 0, tokens["principal"], tokens["surface_alt"], "Principal", tokens["text"]),
                ),
                unsafe_allow_html=True,
            )
        for column, label, key, accent in zip(
            st.columns(3),
            ("Total Payments", "Interest", "Principal"),
            ("total", "interest", "principal"),
            (tokens["kpi_blue"], tokens["kpi_orange"], tokens["kpi_green"]),
        ):
            compact, exact = stat_values(overview[key], currency, number_style)
            column.markdown(kpi_card_html(label, compact, "", accent, variant=layout, compact=True, full=exact), unsafe_allow_html=True)
        table = pd.DataFrame(
            {
                "Month": [month.strftime("%b %Y") for month in overview["table"]["month"]],
                "Total Payment": overview["table"]["total"],
                "Interest": overview["table"]["interest"],
                "Principal": overview["table"]["principal"],
            }
        )
        st.dataframe(amount_table(table, currency, number_style), hide_index=True, height=190)


# ------------------------------- quick actions ------------------------------ #
def quick_actions_card() -> None:
    """Shortcuts: one ribbon of five buttons across the page, in every layout."""
    with st.container(border=True):
        st.markdown("#### Quick Actions")
        latest = dash.latest_calculated_lease(in_currency)

        def open_latest() -> None:
            st.session_state["lease_view"] = {"mode": "results", "case_id": latest["case_id"]}
            st.switch_page("pages/2_Leases.py")

        upload, bulk, template, disclosures, memo = st.columns(5)
        can_edit = "edit" in user["rights"]
        if upload.button("Upload Lease Agreement", key="qa_upload", disabled=not can_edit):
            st.session_state["add_mode"] = "Upload contract"
            st.switch_page("pages/2_Leases.py")
        if bulk.button("Bulk Upload Leases", key="qa_bulk", disabled=not can_edit):
            st.switch_page("pages/3_Bulk_Upload.py")
        template.download_button(
            "Download Template", key="qa_template", data=template_bytes(),
            file_name="leaseiq_bulk_upload_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        if disclosures.button("Generate Disclosure Notes", key="qa_disclosures", disabled=latest is None, help=None if latest else "Calculate a lease first"):
            open_latest()
        if memo.button("Generate Memo AI Draft", key="qa_memo", disabled=latest is None, help=None if latest else "Calculate a lease first"):
            open_latest()
        if latest is not None:
            st.caption(
                "Disclosure notes and the memo open on your latest lease, {} (use its Disclosures / Technical memo tab).".format(
                    latest["lease_ref"]
                )
            )


# ------------------------------- the layouts -------------------------------- #
# Classic, Modern and Pro all end with the Quick Actions ribbon; Modern and Pro add ring gauges to the payments card.
kpi_row()
charts_row()
line_column, payments_column = st.columns([6, 4])
with line_column:
    line_chart_card(height=380)
with payments_column:
    payments_card(rings=layout in ("modern", "pro"))
quick_actions_card()
