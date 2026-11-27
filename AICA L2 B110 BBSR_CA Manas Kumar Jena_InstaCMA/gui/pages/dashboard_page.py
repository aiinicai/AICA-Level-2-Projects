"""Dashboard: the proposal at a glance."""
from PyQt5.QtWidgets import QGridLayout, QGroupBox, QVBoxLayout, QListWidget

from gui.pages.base_page import BasePage
from gui.pages.common import buttons, lakh
from gui.widgets.metric_card import MetricCard
from gui.widgets.table_view import DataTable


class DashboardPage(BasePage):
    title = "Dashboard"
    subtitle = "Start a new client, open a saved client file, or load a sample to see how the tool works."

    def build(self):
        self.body.addLayout(buttons(self, [
            ("New client", self.app.new_project, None), ("Open client file...", self.app.open_project, "Secondary"),
            ("Save client file", self.app.save_project, "Secondary"),
            ("Sample: trading proprietorship", lambda: self.app.load_sample("sm"), "Secondary"),
            ("Sample: manufacturing company", lambda: self.app.load_sample("kal"), "Secondary")]))
        grid = QGridLayout()
        self.cards = {}
        for i, (k, t) in enumerate([("client", "Client"), ("years", "Years"), ("facility", "Facility"),
                                    ("dp", "Drawing power"), ("turnover", "Turnover / CC limit"),
                                    ("dscr", "Average DSCR"), ("cash", "Lowest cash at bank"),
                                    ("checks", "Checks")]):
            self.cards[k] = MetricCard(t)
            grid.addWidget(self.cards[k], i // 4, i % 4)
        self.body.addLayout(grid)
        g = QGroupBox("Year-wise results (Rs lakh)")
        v = QVBoxLayout(g)
        self.table = DataTable()
        self.table.setMinimumHeight(220)
        v.addWidget(self.table)
        self.body.addWidget(g)
        g2 = QGroupBox("Warnings and decisions needed")
        v2 = QVBoxLayout(g2)
        self.warn = QListWidget()
        self.warn.setMinimumHeight(150)
        v2.addWidget(self.warn)
        self.body.addWidget(g2)
        self.body.addStretch()

    def refresh(self):
        p, r = self.project, self.result
        it = p.intake
        self.cards["client"].set(it.client_name or "-", "%s | %s" % (it.constitution, it.nature))
        if r is None or not r.years:
            for k in ("years", "facility", "dp", "turnover", "dscr", "cash", "checks"):
                self.cards[k].set("-", "Set the years and upload the statements")
            self.table.load([], [])
            self.warn.clear()
            return
        kinds = {}
        for y in p.year_list():
            kinds[y.kind] = kinds.get(y.kind, 0) + 1
        self.cards["years"].set(str(len(p.years)), ", ".join("%d %s" % (v, k) for k, v in kinds.items()))
        fac = []
        if it.has_cc:
            fac.append("CC %s L" % lakh(it.cc_limit))
        if it.has_tl:
            fac.append("TL %s L" % lakh(it.tl_amount))
        self.cards["facility"].set(" + ".join(fac) or "-", it.case_type)
        fut = r.future
        if fut:
            ok = all(y["dp_status"] == "PASS" for y in fut)
            self.cards["dp"].set("PASS" if ok else "FAIL", "every year" if ok else "shortfall in a year",
                                 "PASS" if ok else "FAIL")
            m = [y["turnover_multiple"] for y in fut if y["turnover_multiple"]]
            st = [y["turnover_status"] for y in fut]
            worst = "FAIL" if "FAIL" in st else ("AMBER" if "AMBER" in st else "PASS")
            self.cards["turnover"].set(("%.2fx" % min(m)) if m else "N/A", "lowest year", worst)
            avg = r.summary.get("dscr_avg")
            self.cards["dscr"].set(("%.2f" % avg) if avg is not None else "N/A",
                                   "drawings %sdeducted" % ("" if it.dscr_deduct_drawings else "not "),
                                   r.summary.get("dscr_status"))
            low = min(y["bank_balance"] for y in fut)
            self.cards["cash"].set("%s L" % lakh(low), "balancing figure", "PASS" if low >= 0 else "FAIL")
        errs = [c for c in self.app.checks if c[0] == "ERROR"]
        self.cards["checks"].set("OK" if not errs else "%d error(s)" % len(errs),
                                 "ready to export" if not errs else "see Checks", "PASS" if not errs else "FAIL")
        rows = []
        for y in r.years:
            rows.append(["%s %s" % (y["label"], y["kind"][:4] + "."), lakh(y["sales"]), lakh(y["pat"]),
                         lakh(y["drawing_power"]), lakh(y["cc_limit"]), y["dp_status"],
                         ("%.2fx" % y["turnover_multiple"]) if y["turnover_multiple"] else "-", y["turnover_status"],
                         ("%.2f" % y["dscr"]) if y.get("dscr") is not None else "-", y.get("dscr_status", "-"),
                         lakh(y["bank_balance"])])
        self.table.load(["Year", "Sales", "Net profit", "Drawing power", "CC limit", "DP", "Sales/limit",
                         "Turnover", "DSCR", "DSCR test", "Cash at bank"], rows)
        self.warn.clear()
        for w in r.warnings + r.decisions:
            self.warn.addItem(w)
        if not (r.warnings or r.decisions):
            self.warn.addItem("No warnings.")
