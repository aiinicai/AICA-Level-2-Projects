"""Chapter-wise self-evaluation sandbox with step-marking rubric."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


@dataclass(frozen=True)
class Problem:
    key: str
    chapter: str
    marks: int
    statement: str
    solution_lines: list[str]
    answer_label: str
    insights: list[str]
    rubric: list[tuple[str, int]]


def _kd_problem() -> Problem:
    # Rs.100 face value, 10% debentures, issued at Rs.95, flotation 5% of face value (Rs.5),
    # redeemable at 10% premium (Rs.110) after 5 years, tax 30%.
    interest, t = 10.0, 0.30
    np_ = 95.0 - 5.0
    rv, n = 110.0, 5
    num = interest * (1 - t) + (rv - np_) / n
    den = (rv + np_) / 2
    kd = num / den * 100
    return Problem(
        key="kd", chapter="Cost of Capital", marks=6,
        statement=("A company issues 10% debentures of Rs. 100 face value at Rs. 95 per debenture. Flotation cost is "
                   "5% of face value. Debentures are redeemable after 5 years at a 10% premium. Tax rate is 30%. "
                   "Compute the after-tax cost of debt using the approximation method."),
        solution_lines=[
            f"Net proceeds (NP) = 95 - 5 = Rs. {np_:.0f}",
            f"Redemption value (RV) = 100 x 1.10 = Rs. {rv:.0f}",
            f"Post-tax interest = 10 x (1 - 0.30) = Rs. {interest * (1 - t):.2f}",
            f"Kd = [7 + (110 - 90)/5] / [(110 + 90)/2] = {num:.2f} / {den:.0f}",
        ],
        answer_label=f"Kd = {kd:.2f}% (post-tax)",
        insights=["Students use Rs. 95 and forget flotation cost, giving a wrong NP.",
                  "Some apply tax on the redemption premium; the approximation method only tax-adjusts interest.",
                  "Writing '%' and 'post-tax' with the answer is part of the final-answer mark."],
        rubric=[("Net proceeds and flotation cost handled correctly", 2), ("Correct formula with substitution", 2),
                ("Final answer with % label", 2)],
    )


def _wacc_problem() -> Problem:
    e, p, d = 600.0, 100.0, 300.0
    ke, kp, kd_pre, t = 14.0, 11.0, 10.0, 0.30
    tot = e + p + d
    wacc = (e * ke + p * kp + d * kd_pre * (1 - t)) / tot
    return Problem(
        key="wacc", chapter="Cost of Capital", marks=6,
        statement=("Capital structure (book values): Equity Rs. 6,00,000 (Ke 14%), 11% Preference Rs. 1,00,000 "
                   "(Kp 11%), 10% Debentures Rs. 3,00,000. Tax rate 30%. Compute WACC on book-value weights."),
        solution_lines=[
            f"Total capital = Rs. {tot:,.0f}",
            f"Equity: 0.60 x 14 = {0.6 * ke:.2f}",
            f"Preference: 0.10 x 11 = {0.1 * kp:.2f}",
            f"Debt: 0.30 x 10 x 0.70 = {0.3 * kd_pre * 0.7:.2f}",
        ],
        answer_label=f"WACC = {wacc:.2f}%",
        insights=["Interest not tax-adjusted before weighting.", "Using market weights when book is instructed.",
                  "Missing the total row so the weights are not visibly 1.00."],
        rubric=[("Weights computed correctly", 2), ("Component costs and tax adjustment", 2),
                ("Final WACC with % label", 2)],
    )


def _npv_problem() -> Problem:
    outlay, cf, n, r = 500000.0, 150000.0, 5, 0.12
    af = (1 - (1 + r) ** -n) / r
    npv = cf * af - outlay
    return Problem(
        key="npv", chapter="Capital Budgeting", marks=8,
        statement=("A project needs Rs. 5,00,000 now and generates annual after-tax cash inflows of Rs. 1,50,000 "
                   "for 5 years. Cost of capital is 12%. Compute NPV and advise. (Use PVAF at 12% for 5 years = "
                   f"{af:.3f}.)"),
        solution_lines=[f"PV of inflows = 1,50,000 x {af:.3f} = Rs. {cf * af:,.0f}",
                        f"NPV = {cf * af:,.0f} - 5,00,000 = Rs. {npv:,.0f}"],
        answer_label=f"NPV = Rs. {npv:,.0f}; {'Accept' if npv > 0 else 'Reject'} the project",
        insights=["Using sum of inflows (7,50,000) without discounting.", "Forgetting to deduct the initial outlay.",
                  "No decision statement after computing NPV."],
        rubric=[("Initial outlay and inflows identified", 2), ("PVAF formula and substitution", 2),
                ("Final NPV in Rs. with decision", 2)],
    )


PROBLEMS: dict[str, Problem] = {p.key: p for p in (_kd_problem(), _wacc_problem(), _npv_problem())}


def render_sandbox() -> None:
    st.subheader("Chapter-wise Self-Evaluation Sandbox")
    key = st.selectbox("Problem", list(PROBLEMS),
                       format_func=lambda k: f"{PROBLEMS[k].chapter} ({PROBLEMS[k].marks} marks)")
    p = PROBLEMS[key]
    st.markdown(f"**Question ({p.marks} marks)**")
    st.write(p.statement)
    st.text_area("Write your working here", height=150, key=f"work_{p.key}")

    if st.toggle("Reveal model solution", key=f"rev_{p.key}"):
        for ln in p.solution_lines:
            st.write("- " + ln)
        st.success(p.answer_label)

        st.markdown("**Self-marking rubric**")
        total = 0
        for i, (label, mx) in enumerate(p.rubric):
            total += st.slider(f"{label} (max +{mx})", 0, mx, 0, key=f"rub_{p.key}_{i}")
        max_total = sum(m for _, m in p.rubric)
        st.metric("Self-assessed score", f"{total} / {max_total}")
        st.session_state.setdefault("sandbox_scores", {})[p.key] = (total, max_total)

    with st.expander("Examiner Insights: common student mistakes"):
        for i in p.insights:
            st.write("- " + i)
