"""Smart Revision Engine: topic content, interactive preview and PDF downloads.

Content is original faculty-style commentary (formulas are standard textbook relationships).
Faculty should review before circulation; verify against the latest ICAI Study Material.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import streamlit as st

from config.icai_resources import module_by_id
from modules.pdf_generator import DiagramKind, PdfMode, build_pdf


@dataclass(frozen=True)
class Topic:
    key: str
    title: str
    module_id: str
    formulas: list[tuple[str, str]]
    diagram_kind: DiagramKind
    diagram_steps: list[str]
    traps: list[str]
    working_paper_title: str
    working_paper: list[list[str]]       # first row = header
    mastery_steps: list[str]
    faculty_note: str

    @property
    def module_name(self) -> str:
        return module_by_id(self.module_id).name

    @property
    def badge(self) -> str:
        return module_by_id(self.module_id).weightage_label


TOPICS: dict[str, Topic] = {t.key: t for t in (
    Topic(
        key="coc", title="Cost of Capital", module_id="M2",
        formulas=[
            ("Kd irredeemable (post-tax)", "I x (1 - t) / NP, where NP = issue price less flotation cost"),
            ("Kd redeemable (approx.)", "[I(1 - t) + (RV - NP)/n] / [(RV + NP)/2]"),
            ("Ke (CAPM)", "Rf + Beta x (Rm - Rf)"),
            ("Ke (dividend growth)", "D1 / P0 + g, where D1 = D0 x (1 + g)"),
            ("Kp (irredeemable)", "Preference dividend / NP"),
            ("Ke (retained earnings)", "Same as Ke; no flotation cost on retained earnings"),
            ("WACC", "Sum of (weight x cost); use target or market weights if stated"),
        ],
        diagram_kind="tradeoff", diagram_steps=[],
        traps=[
            "Use net proceeds (after flotation cost) in the denominator, not face value.",
            "Interest is tax-adjusted; preference and equity dividends are NOT.",
            "Use D1, not D0, in the dividend growth model.",
            "Read the weights instruction: book, market or target. Do not assume.",
            "Flotation cost on debt: state clearly whether it is on issue price or face value.",
        ],
        working_paper_title="WACC working paper (illustrative layout)",
        working_paper=[
            ["Source", "Amount", "Weight", "Cost (%)", "Weight x Cost"],
            ["Equity", "A", "A / Total", "Ke", "Product"],
            ["Preference", "B", "B / Total", "Kp", "Product"],
            ["Debt (post-tax)", "C", "C / Total", "Kd (1 - t)", "Product"],
            ["Total", "A + B + C", "1.00", "", "WACC (%)"],
        ],
        mastery_steps=[
            "Compute net proceeds for every security first; marks are usually allotted to this step.",
            "Calculate each component cost separately with the formula written out.",
            "Decide the weighting basis from the question wording and state it.",
            "Present the table, then write the final WACC with the % label.",
        ],
        faculty_note="When Ke is asked 'using CAPM and dividend model', show both and state which one you finally use and why.",
    ),
    Topic(
        key="lev", title="Leverages", module_id="M2",
        formulas=[
            ("Contribution", "Sales - Variable cost"),
            ("EBIT", "Contribution - Fixed operating cost"),
            ("Operating leverage (DOL)", "Contribution / EBIT"),
            ("Financial leverage (DFL)", "EBIT / EBT (EBIT less interest)"),
            ("Combined leverage (DCL)", "DOL x DFL = Contribution / EBT"),
            ("Margin of safety effect", "A % change in sales changes EBIT by DOL x % and EPS by DCL x %"),
        ],
        diagram_kind="flow",
        diagram_steps=["Sales", "Contribution\n(less VC)", "EBIT\n(less FC)", "EBT\n(less interest)", "EPS\n(PAT / shares)"],
        traps=[
            "DFL uses EBIT / EBT; with preference dividends the denominator is EBT less pref. dividend grossed up for tax.",
            "Do not confuse fixed operating cost with interest.",
            "DCL = DOL x DFL; check the product equals Contribution / EBT.",
            "Comment on risk: high DOL and high DFL together is a risky structure.",
        ],
        working_paper_title="Income-statement walk for leverages",
        working_paper=[
            ["Line item", "Working", "Leverage link"],
            ["Sales", "Given", "Start point"],
            ["Less: Variable cost", "Given", ""],
            ["Contribution", "Sales - VC", "Numerator of DOL and DCL"],
            ["Less: Fixed cost", "Given", ""],
            ["EBIT", "Contribution - FC", "Denominator of DOL; numerator of DFL"],
            ["Less: Interest", "Given", ""],
            ["EBT", "EBIT - Interest", "Denominator of DFL and DCL"],
        ],
        mastery_steps=[
            "Build the income-statement walk before any ratio.",
            "Compute DOL, DFL, DCL in that order and cross-check DCL.",
            "Use the percentage-change shortcut for 'what if sales change' questions.",
            "Close with one line of business-risk interpretation.",
        ],
        faculty_note="Examiners reward the interpretation sentence. Never end on a bare number.",
    ),
    Topic(
        key="cb", title="Capital Budgeting", module_id="M3",
        formulas=[
            ("NPV", "Sum of PV of cash inflows - Initial outlay (PV of cash outflows)"),
            ("Profitability index", "PV of inflows / PV of outflows"),
            ("IRR (interpolation)", "Lower rate + [NPV at lower / (NPV at lower - NPV at higher)] x rate gap"),
            ("Payback", "Years until cumulative cash flow turns positive"),
            ("Discounted payback", "Same, using discounted cash flows"),
            ("Annual cash flow", "EBIT x (1 - t) + Depreciation (or PAT + Dep + other non-cash)"),
            ("EAA / EAC", "NPV (or PV of cost) / Annuity factor, for unequal-life projects"),
        ],
        diagram_kind="flow",
        diagram_steps=["Initial outlay\n+ working capital", "Annual\nafter-tax CFAT", "Discount at\ncost of capital", "Add terminal\nrecoveries", "NPV / IRR\ndecision"],
        traps=[
            "Depreciation is not a cash flow; it only enters through the tax shield.",
            "Include working-capital investment at start and release at the end.",
            "Sunk cost and allocated overhead are irrelevant; opportunity cost is relevant.",
            "Choose between mutually exclusive projects by NPV when NPV and IRR conflict.",
            "Salvage value: check tax on profit or loss on sale.",
        ],
        working_paper_title="NPV working paper (illustrative layout)",
        working_paper=[
            ["Year", "Cash flow", "PV factor", "Present value"],
            ["0", "(Outlay + WC)", "1.000", "(Amount)"],
            ["1 to n", "CFAT", "From table", "Product"],
            ["n", "Salvage + WC release", "From table", "Product"],
            ["Result", "", "", "NPV"],
        ],
        mastery_steps=[
            "Set out the cash-flow table by year with clear headings.",
            "Compute tax shield on depreciation separately where methods differ.",
            "Use the PV table values given in the question paper only.",
            "State the accept/reject rule against zero NPV, with units.",
        ],
        faculty_note="IRR interpolation: pick two rates that give NPVs of opposite sign. Show both NPVs.",
    ),
    Topic(
        key="div", title="Dividend Decisions", module_id="M4",
        formulas=[
            ("Walter", "P = [D + (r/Ke)(E - D)] / Ke"),
            ("Gordon", "P0 = E1 (1 - b) / (Ke - b x r)"),
            ("MM (no taxes)", "P0 = (D1 + P1) / (1 + Ke)"),
            ("Growth rate", "g = b x r (retention x return on equity)"),
            ("Payout ratio", "Dividend / Earnings"),
        ],
        diagram_kind="flow",
        diagram_steps=["Earnings", "Retention\n(b)", "Reinvest at r", "Growth\ng = b x r", "Share price"],
        traps=[
            "Walter: r > Ke means zero payout is optimal; r < Ke means 100% payout.",
            "Gordon uses E1 and retention b; keep the sign convention straight.",
            "MM: dividend policy is irrelevant under perfect markets.",
            "State the assumptions behind each model if a theory comment is asked.",
        ],
        working_paper_title="Walter model comparison at different payouts",
        working_paper=[
            ["Payout", "D per share", "Price (Walter)", "Comment"],
            ["0%", "0", "Compute", "Best if r > Ke"],
            ["50%", "E x 0.5", "Compute", "Neutral if r = Ke"],
            ["100%", "E", "Compute", "Best if r < Ke"],
        ],
        mastery_steps=[
            "Identify the model named in the question before computing.",
            "Compute E and D per share explicitly.",
            "Substitute with intermediate values visible.",
            "Compare r with Ke and conclude on optimum payout.",
        ],
        faculty_note="Link to Sections 123 (dividend) of the Companies Act 2013 for the legal angle in Paper 2.",
    ),
    Topic(
        key="wc", title="Working Capital Management", module_id="M5",
        formulas=[
            ("Operating cycle", "RMCP + WIPCP + FGCP + DCP"),
            ("Cash conversion cycle", "Operating cycle - Creditors' payment period"),
            ("RMCP", "Average RM stock / Daily RM consumption"),
            ("WIPCP", "Average WIP / Daily cost of production"),
            ("FGCP", "Average FG / Daily cost of goods sold"),
            ("DCP", "Average debtors / Daily credit sales"),
            ("Gross working capital", "Total current assets"),
            ("Net working capital", "Current assets - Current liabilities"),
            ("Add cash buffer", "Many questions ask for a 10% to 20% contingency; read the instruction"),
        ],
        diagram_kind="ccc", diagram_steps=[],
        traps=[
            "Use cost basis (not sales) for stocks and WIP; sales basis only for debtors unless told otherwise.",
            "Days in year (360 or 365) is given in the question; use that value.",
            "Do not include depreciation in cost for cash-cost based estimates.",
            "WIP carrying cost: apply the stated completion percentage for each cost element.",
            "Creditors' period is deducted only in the cash conversion cycle, not in the operating cycle.",
        ],
        working_paper_title="Working capital estimate (illustrative layout)",
        working_paper=[
            ["Item", "Working", "Amount"],
            ["Raw material stock", "Annual RM / 12 x months", "Amount"],
            ["WIP", "Cost elements x completion %", "Amount"],
            ["Finished goods", "Cost of goods sold basis", "Amount"],
            ["Debtors", "Cost of sales or sales as stated", "Amount"],
            ["Cash balance", "Given", "Amount"],
            ["Less: Creditors", "Purchases / 12 x months", "(Amount)"],
            ["Net working capital", "", "Total"],
        ],
        mastery_steps=[
            "Set out the cost sheet for one unit or one year first.",
            "Compute each current asset and liability on the stated basis.",
            "Add the contingency only at the end if asked.",
            "Label the final answer clearly (Rs. and basis).",
        ],
        faculty_note="D-Mart style retailers run a negative cycle because they collect cash at once and pay suppliers later. Contrast with a capital-goods manufacturer.",
    ),
    Topic(
        key="sm", title="Strategic Analysis: Porter's Five Forces and SWOT", module_id="SM",
        formulas=[
            ("Five forces", "Entry threat, Supplier power, Buyer power, Substitutes, Rivalry"),
            ("SWOT", "Internal: Strengths, Weaknesses | External: Opportunities, Threats"),
            ("BCG matrix", "Stars, Cash cows, Question marks, Dogs (market growth vs relative share)"),
            ("Value chain", "Primary activities + Support activities = Margin"),
            ("Ansoff", "Market penetration, Market development, Product development, Diversification"),
        ],
        diagram_kind="flow",
        diagram_steps=["Environment\nscan", "Internal\nappraisal", "Strategic\nchoice", "Implementation", "Evaluation\n& control"],
        traps=[
            "Always apply the framework to the case facts; a textbook definition alone earns few marks.",
            "Separate internal factors (SW) from external factors (OT) in SWOT.",
            "Link every recommendation to a named strategy level: corporate, business or functional.",
            "Keep answers structured: heading, point, case evidence.",
        ],
        working_paper_title="Case-answer skeleton for Paper 6B",
        working_paper=[
            ["Step", "What to write", "Marks logic"],
            ["1. Identify", "Name the concept or framework", "Direct credit"],
            ["2. Define", "One-line definition", "Direct credit"],
            ["3. Apply", "Use facts from the case", "Most marks"],
            ["4. Conclude", "Recommendation or implication", "Value addition"],
        ],
        mastery_steps=[
            "Underline the verb in the question (discuss, evaluate, advise).",
            "Write the framework heading before the points.",
            "Quote at least two facts from the case in the application step.",
            "End with a one-line recommendation.",
        ],
        faculty_note="Paper 6B is half the paper. Practise two case-based answers every week in the exam time limit.",
    ),
)}

TOPIC_KEYS: list[str] = list(TOPICS)


def render_revision() -> None:
    st.subheader("Smart Revision Engine and Cue Cards")
    candidate = st.session_state.get("candidate_name", "Candidate")

    c1, c2 = st.columns([2, 2])
    topic_key = c1.selectbox("Topic", TOPIC_KEYS, format_func=lambda k: TOPICS[k].title)
    mode_label = c2.radio("Format", ["1-Pager Exam Morning Blitz", "2-Pager Practical Mastery"], horizontal=True)
    mode: PdfMode = "blitz" if mode_label.startswith("1") else "mastery"
    topic = TOPICS[topic_key]

    st.markdown(f"<span class='badge'>ICAI BOS WEIGHTAGE: {topic.badge}</span> &nbsp; {topic.module_name}",
                unsafe_allow_html=True)

    st.markdown("#### Formula matrix")
    st.table({"Concept": [a for a, _ in topic.formulas], "Formula / Rule": [b for _, b in topic.formulas]})

    st.markdown("#### Examiner warnings")
    limit = 4 if mode == "blitz" else len(topic.traps)
    st.markdown("<div class='sticky'><b>Examiner warnings</b><ul>" +
                "".join(f"<li>{t}</li>" for t in topic.traps[:limit]) + "</ul></div>", unsafe_allow_html=True)

    if mode == "mastery":
        st.markdown(f"#### Working paper: {topic.working_paper_title}")
        hdr, *rows = topic.working_paper
        st.table({h: [r[i] for r in rows] for i, h in enumerate(hdr)})
        st.markdown("#### Practical mastery steps")
        for i, s in enumerate(topic.mastery_steps, 1):
            st.markdown(f"{i}. {s}")
        st.info(topic.faculty_note)

    st.markdown("#### Download printable cue cards")
    d1, d2 = st.columns(2)
    d1.download_button("Download 1-Pager Blitz PDF", build_pdf(topic, "blitz", candidate),
                       file_name=f"{topic.key}_blitz_1pager.pdf", mime="application/pdf", key=f"dl1_{topic.key}")
    d2.download_button("Download 2-Pager Mastery PDF", build_pdf(topic, "mastery", candidate),
                       file_name=f"{topic.key}_mastery_2pager.pdf", mime="application/pdf", key=f"dl2_{topic.key}")
