"""Orchestrates the full analysis from a Project. Deterministic - no network, no AI."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import engine, risk, statements, validate
from .extract import align_gl_to_tb
from .fx import FXSettings, translate_tb, validate_settings
from .mapping import map_all
from .project import Project
from .questionnaire import prefill


@dataclass
class Analysis:
    project: Project
    mapped: list
    tr: object
    st: object
    review: object
    ctx: dict
    answers: dict
    adjs: list
    open_items: list
    comp: engine.Computation
    checks: list
    scenarios: list
    applic: dict
    warnings: list = field(default_factory=list)
    fx_issues: list = field(default_factory=list)

    @property
    def entity(self) -> str:
        return engine.ans(self.answers, "entity_name", "Company Name")

    @property
    def period_start(self) -> str:
        return engine.ans(self.answers, "period_start", self.project.fx.period_start or "")

    @property
    def period_end(self) -> str:
        return engine.ans(self.answers, "period_end", self.project.fx.period_end or "")

    def pending_impact(self) -> dict:
        """Effect on taxable income if every PROPOSED (non-rejected, unconfirmed) adjustment were confirmed."""
        c2 = engine.compute(self.tr, self.st, self.adjs, self.answers, include_status=("Confirmed", "Proposed"))
        return {"taxable_income": c2.E, "tax_payable": c2.payable, "delta_taxable": c2.E - self.comp.E, "delta_tax": c2.payable - self.comp.payable,
                "count": sum(1 for a in self.adjs if a.status == "Proposed")}


def run_analysis(p: Project) -> Analysis:
    if p.tb is None:
        raise ValueError("No trial balance loaded.")
    fx_issues = validate_settings(p.fx, p.gl)
    errs = [m for s, m in fx_issues if s == "ERROR"]
    if errs:
        raise ValueError("Currency settings incomplete: " + " ".join(errs))
    p.tb.currency = p.fx.tb_currency            # the label always follows the confirmed currency settings
    if p.prior_tb:
        p.prior_tb.currency = p.fx.tb_currency
    if p.gl:
        align_gl_to_tb(p.gl, p.tb)
    mapped = map_all(p.tb.accounts, p.mapping_overrides)
    tr = translate_tb(mapped, p.fx, p.gl)
    st = statements.build_statements(tr)

    # first pass context to prefill the questionnaire
    ctx = engine.questionnaire_context(tr, st, p.tb, p.gl, p.fx, p.answers)
    answers = prefill(p.answers, ctx)
    ctx = engine.questionnaire_context(tr, st, p.tb, p.gl, p.fx, answers)
    ps = engine.ans(answers, "period_start", p.fx.period_start or "")
    pe = engine.ans(answers, "period_end", p.fx.period_end or "")
    rp = [r.get("name", "") for r in (answers.get("related_parties") or []) if isinstance(r, dict)]
    review = risk.analyse(tr, p.gl, ps, pe, rp, p.prior_tb, p.settings.thresholds)
    for f in review.flags:
        r = p.flag_responses.get(f.flag_id)
        if r:
            f.mgmt_response = r.get("mgmt_response", "")
            f.reviewer_conclusion = r.get("reviewer_conclusion", "")
    adjs, oi = engine.build_adjustments(tr, review, answers)
    warns = engine.apply_decisions(adjs, p.decisions)
    comp = engine.compute(tr, st, adjs, answers)
    items = engine.open_items_from_state(answers, ctx, oi, comp, st, tr)
    checks = []
    checks += validate.check_tb(p.tb)
    checks += validate.check_mapping(mapped)
    checks += validate.check_statements(st, tr)
    if p.gl:
        checks += validate.check_gl(p.gl, p.tb, ps or None, pe or None)
        if p.tb and p.gl:
            checks.append(validate.Check("SCOPE-01", "TB and GL cover the same entity and period", "WARN",
                                         "The tool cannot prove this from the files alone: confirm that both come from the same entity and period."))
    # computation cross-check
    checks.append(validate.Check("CALC-01", "Computation starts from P&L profit", "PASS" if abs(comp.A - st.profit_for_year) < 0.01 else "FAIL",
                                 f"Accounting profit used: AED {comp.A:,.2f}; P&L profit: AED {st.profit_for_year:,.2f}"))
    scen = engine.scenarios(tr, st, review, answers)
    applic = engine.applicability(tr, st, adjs, comp, answers, p.settings.include_dta)
    return Analysis(p, mapped, tr, st, review, ctx, answers, adjs, items, comp, checks, scen, applic, warns, fx_issues)
