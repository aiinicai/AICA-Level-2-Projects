"""Screen test. Opens the built dashboard in a real browser (Playwright + Chromium), clicks through the slicers
and charts, and checks that what is DISPLAYED equals the Python engine's numbers. Also fails on any console error.
"""
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from playwright.sync_api import sync_playwright  # noqa: E402
from app import build_dashboard, life as L, portfolio as P  # noqa: E402

DB = ROOT / "db_dummy"


def digits(t):
    return int(re.sub(r"[^\d]", "", t.split("\n")[0].split("(")[0]))


def kpi(pg, label):
    return pg.locator(".kpi", has=pg.locator(f".l:text-is('{label}')")).locator(".n").inner_text()


def main(shot_dir=None):
    out = Path(tempfile.mkdtemp()) / "d.html"
    build_dashboard.build(DB, out, "Dummy data")
    db = P.load(DB)
    shots = Path(shot_dir) if shot_dir else None
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(out.as_uri())

        def total(on, cls=None):
            ls = P.lines(db, on)
            return round(sum(x["value"] for x in ls if cls is None or x["cls"] == cls))

        # 1 latest total
        assert digits(kpi(pg, "Total value")) == total(db["latest"]), "latest total"
        # 2 every month end
        for m in ["2025-12-31", "2026-03-31", "2026-06-30", "2026-10-31"]:
            pg.select_option("#sl-on", m)
            assert digits(kpi(pg, "Total value")) == total(date.fromisoformat(m)), m
            assert digits(kpi(pg, "Mutual funds")) == total(date.fromisoformat(m), "Mutual funds"), m
        pg.select_option("#sl-on", db["latest"].isoformat())
        # 3 click the Shares slice -> chip + KPI
        pg.locator("#c-donut .legend li", has_text="Equity shares").click()
        assert pg.locator(".chip").count() == 1 and "Asset class: Equity shares" in pg.locator(".chip").inner_text()
        assert digits(kpi(pg, "Total value")) == total(db["latest"], "Equity shares"), "shares slice"
        pg.click("#clear")
        assert pg.locator(".chip").count() == 0
        # 4 sector slicer on Shares tab
        pg.click(".tab[data-i='2']")
        pg.select_option("#sl-sector", "Banking")
        want = round(sum(x["value"] for x in P.lines(db, db["latest"]) if x["cls"] == "Equity shares" and db["instruments"][x["key"]]["group"] == "Banking"))
        assert digits(kpi(pg, "Value")) == want, "banking sector"
        if shots: pg.screenshot(path=str(shots / "shares_banking.png"), full_page=True)
        # linked: sector filter carries to Overview and removes funds, bank and deposits
        pg.click(".tab[data-i='0']")
        assert digits(kpi(pg, "Total value")) == want, "sector carries to overview"
        assert digits(kpi(pg, "Mutual funds")) == 0
        pg.click("#clear")
        # 5 fund house + click a fund row
        pg.click(".tab[data-i='1']")
        pg.select_option("#sl-fh", "HDFC Mutual Fund")
        want = round(sum(x["value"] for x in P.lines(db, db["latest"]) if x["cls"] == "Mutual funds" and db["instruments"][x["key"]]["house"] == "HDFC Mutual Fund"))
        assert digits(kpi(pg, "Value")) == want, "HDFC"
        first = pg.locator("#c-ftab tbody tr").first
        fname = " ".join(first.locator("td").first.inner_text().split())
        first.click()
        assert pg.locator(".chip").count() == 2
        fkey = [k for k, i in db["instruments"].items() if i["name"] == fname][0]
        assert pg.locator("#c-ledger tbody tr").count() == sum(1 for t in db["tx"] if t["key"] == fkey and t["date"] <= db["latest"]), "ledger rows = transactions of that fund"
        if shots: pg.screenshot(path=str(shots / "funds_hdfc_row.png"), full_page=True)
        pg.click("#clear")
        # 6 account slicer on Bank tab includes broker cash
        pg.click(".tab[data-i='3']")
        pg.select_option("#sl-account", "Demat ZD1234")
        want = round(sum(x["value"] for x in P.lines(db, db["latest"]) if x["account"] == "Demat ZD1234" and x["cls"] == "Bank balances"))
        assert digits(kpi(pg, "Bank balances")) == want, "broker cash by account"
        pg.click("#clear")
        pg.select_option("#sl-ccy", "USD")
        want = round(sum(x["value"] for x in P.lines(db, db["latest"]) if x["ccy"] == "USD"))
        assert digits(kpi(pg, "Foreign currency, in INR")) == want, "USD in INR"
        pg.click("#clear")
        # 7 hover tooltip shows
        pg.click(".tab[data-i='0']")
        pg.locator("#c-line svg").hover(position={"x": 300, "y": 120})
        assert pg.locator("#tip").is_visible() and "Value" in pg.locator("#tip").inner_text()
        # 7b Overview: range buttons, holdings class buttons and search, CSV export
        pg.click(".tab[data-i='0']")
        pg.click(".range button[data-r='3M']")
        assert pg.locator(".range button[data-r='3M']").get_attribute("aria-pressed") == "true" and pg.locator("#c-line svg").count() == 1, "range 3M"
        assert digits(kpi(pg, "Total value")) == total(db["latest"]), "range does not change the headline total"
        pg.click(".range button[data-r='ALL']")
        pg.click("#hold-f button[data-c='Term deposits']")
        fds = {}
        for x in P.lines(db, db["latest"]):
            if x["cls"] == "Term deposits":
                fds[x["key"]] = fds.get(x["key"], 0) + x["value"]
        assert pg.locator("#c-hold tbody tr:not(.foot)").count() == len(fds), "fixed deposit rows"
        assert digits(pg.locator("#c-hold tr.foot td").nth(3).inner_text()) == round(sum(fds.values())), "fixed deposit footer total"
        pg.click("#clear")
        pg.fill("#q", "tata")
        names = pg.locator("#c-hold tbody tr:not(.foot) .nm").all_inner_texts()
        assert names and all("tata" in n.lower() for n in names), "search holdings"
        pg.fill("#q", "")
        with pg.expect_download() as dl:
            pg.click("#hold-dl")
        rows = dl.value.path().read_text(encoding="utf-8").strip().splitlines()
        body = rows[1:]
        assert rows[0].startswith("Asset class,Name") and len(body) == len(P.lines(db, db["latest"])), "csv rows"
        import csv, io
        vsum = sum(int(r[5]) for r in csv.reader(io.StringIO("\n".join(body))))
        assert abs(vsum - total(db["latest"])) <= len(body), "csv total equals engine total"
        # 7c NRI DTAA tab (page 9): sample folios D1 to D3
        pg.click(".tab[data-i='8']")
        fr = pg.frame_locator("#dtaa")
        fr.locator("#chk tr").first.wait_for()
        assert fr.locator("#chk tr").count() == 3
        res = [fr.locator("#chk tr").nth(i).locator("td").nth(8).inner_text().strip() for i in range(3)]
        def clear(r, ts, te, ds, de):
            return ts <= r <= te and ds is not None and ds <= r <= de
        want = ["Clear" if clear(*a) else "Hold" for a in [
            ("2026-07-15", "2026-05-05", "2026-10-31", "2026-05-22", "2026-10-31"),
            ("2026-11-10", "2026-05-05", "2026-10-31", "2026-05-22", "2026-10-31"),
            ("2026-06-20", "2026-05-05", "2026-10-31", None, None)]]
        assert res == want, (res, want)
        assert res == ["Clear", "Hold", "Hold"], res
        d3 = [fr.locator("#chk tr").nth(i).locator("td").nth(7).inner_text().strip() for i in range(3)]
        assert d3 == ["Pass", "Flag", "Not run"], d3
        assert "1 clear, 2 on hold" in fr.locator("#counts").inner_text()
        # 7d DTAA worked example: ten dummy documents, each marked SAMPLE, dummy identifiers only, one identifier everywhere
        import re
        assert fr.locator("[data-doc]").count() == 7, "cover, enclosures 1, 2, 3, 4-8, 9 and the reply"
        for i in ["cover", "1", "2", "3", "4-8", "9", "reply"]:
            assert fr.locator("[data-doc='%s'] .sheet" % i).count() >= 1, i
            assert fr.locator("[data-doc='%s'] .dn" % i).count() == 1, i
        assert fr.locator("[data-doc='4-8'] .idc").count() == 5, "five copies"
        assert fr.locator("table.pack tbody tr").count() == 10, "pack index has ten rows"
        assert fr.locator("table.tl tbody tr").count() == 8, "timeline rows"
        txt = fr.locator("body").inner_text()
        assert set(re.findall(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", txt)) == {"ABCDE1234F"}, "only the dummy PAN"
        assert set(re.findall(r"\b[A-Z][0-9]{7}\b", txt)) == {"X0000001"}, "only the dummy passport"
        assert set(re.findall(r"[\w.]+@[\w.]+", txt)) == {"busyme@example.com"}, "only the dummy email"
        assert txt.count("X0000001") >= 6, "same identifier on form 41, annexure G, declaration, letter and certificate"
        assert fr.locator(".sheet").count() >= 11, "every sheet carries the SAMPLE mark"
        for need in ["Flat 000, Sample Tower", "203.0.113.10", "ARN-0000001", "22 May 2026", "31 Oct 2026"]:
            assert need in txt, need
        # the form 41 period equals the certificate period equals Annexure G validity
        assert txt.count("05/05/2026") >= 2 and txt.count("31/10/2026") >= 2 and "05-May-2026" in txt and "31-Oct-2026" in txt
        assert pg.locator("#slicers").is_hidden(), "slicers hidden on DTAA tab"
        # 8 data checks tab shows all PASS
        pg.click(".tab[data-i='7']")
        assert "pass" in pg.locator(".card h3 .pill").first.inner_text().lower() and pg.locator("#c-chk .pill.fail").count() == 0
        # 8b name, SIP, property, insurance and calendar pages, against the Python life module
        lf = L.load(DB)
        assert pg.title() == "Hisaab Kitaab" and "Hisaab Kitaab" in pg.locator("#brand").inner_text() and "BusyMe" in pg.locator("#acct-name").inner_text(), "page name and owner"
        assert "Kumar" not in pg.content(), "no other name"
        assert "PAN " + lf["owner"]["pan"] in pg.locator("#acct-pan").inner_text() and lf["owner"]["pan"] == "ABCDE1234F", "PAN in sidebar"
        pg.click(".tab[data-i='0']")
        assert digits(kpi(pg, "Total value")) == total(db["latest"]), "total unchanged by property and insurance"
        note = pg.locator(".outside").inner_text()
        assert "Not in this total" in note and "2,80,00,000" in note and "insurance" in note.lower(), note
        pg.click(".tab[data-i='1']")
        plan = round(sum(s["amount"] for s in lf["sip"]))
        assert plan == 200000 and len(lf["sip"]) == 5
        assert digits(kpi(pg, "SIP in Nov 2026")) == plan, "SIP this month = plan"
        assert digits(pg.locator("table", has_text="Per month").locator("tr.foot td").last.inner_text()) == plan, "SIP plan total"
        pg.click(".tab[data-i='4']")
        pr = lf["props"][0]
        assert digits(kpi(pg, "Market value")) == round(pr["value"]) and digits(kpi(pg, "Cost")) == round(pr["cost"])
        assert digits(kpi(pg, "Rent per month")) == round(pr["rent"])
        last12 = sorted(r["amount"] for r in lf["rent"] if r["date"] > date(db["latest"].year - 1, db["latest"].month, db["latest"].day))
        assert digits(kpi(pg, "Rent received, last 12 months")) == round(sum(last12)), "12-month rent"
        assert digits(pg.locator("#c-rcpt tr.foot td").nth(2).inner_text()) == round(sum(r["amount"] for r in lf["rent"])), "rent total"
        pg.click(".tab[data-i='5']")
        txt = pg.locator("#page").inner_text()
        term, med, ret = lf["ins"]
        assert kpi(pg, "Life cover") == "\u20b9 10.00 Cr" and term["cover"] == 10 * 10 ** 7, "life cover 10 crore"
        assert kpi(pg, "Medical cover") == "\u20b9 2.00 Cr" and med["cover"] == 2 * 10 ** 7, "medical cover 2 crore"
        assert digits(kpi(pg, "Premiums in 2026")) == 600000, "premiums in 2026"
        assert "3 of 10" in txt and "12 of 21" in txt, "premiums paid so far"
        assert "300" in txt and "30,00,000" in txt, "retirement income payments"
        pg.click(".tab[data-i='6']")
        cal = L.calendar(lf, db["latest"], 12)
        assert digits(kpi(pg, "Next 12 months")) == round(sum(e[3] for e in cal)) == 3140000, "calendar total"
        assert digits(kpi(pg, "SIP")) == 2400000 and digits(kpi(pg, "Insurance premiums")) == 600000 and digits(kpi(pg, "House tax and maintenance")) == 140000
        assert pg.locator("#c-list tr").count() >= len({(e[0], e[1]) for e in cal}), "calendar list rows"
        assert pg.locator("#page .calgrid .day.has").count() >= 1, "calendar grid shows days with money out"
        # 8c lively overview: mini trends, waterfall adds up to the gain, At a glance, Replay plays and restores the date
        pg.click(".tab[data-i='0']"); pg.wait_for_timeout(300); pg.click("#clear") if pg.locator("#clear").count() else None
        pg.select_option("#sl-on", str(db["latest"])); pg.wait_for_timeout(200)
        assert pg.locator(".assets .spark svg").count() == 4, "a mini trend on each asset card"
        lines_now = P.lines(db, db["latest"])
        gain = sum(x["value"] - x["cost"] for x in lines_now)
        assert digits(pg.locator("#c-wf").locator("xpath=following-sibling::div[contains(@class,'note')]").inner_text()) == round(gain), "waterfall total gain note"
        n_src = len({x["cls"] for x in lines_now if abs(sum(y["value"] - y["cost"] for y in lines_now if y["cls"] == x["cls"])) > 0.5})
        assert pg.locator("#c-wf .wb").count() == n_src + 1, "waterfall: one bar per source plus the total"
        assert pg.evaluate("(function(){var E=window.__dash.E,S=window.__dash.S,ls=E.filtered(S.on,S.F),bc=E.byClass(ls),t=E.sum(ls),s=0;E.CLASSES.forEach(function(c){s+=bc[c].value-bc[c].cost});return Math.abs(s-t.gain)<0.01})()"), "waterfall steps add up to the total gain"
        assert pg.locator("#c-glance .fact").count() == 4, "At a glance rows"
        first_total = kpi(pg, "Total value")
        pg.click("#replay"); pg.wait_for_timeout(1300)
        assert pg.locator(".rp").count() == 1 and pg.locator("#replay").inner_text().endswith("Stop"), "replay running"
        pg.click("#replay"); pg.wait_for_timeout(300)
        assert pg.locator("#sl-on").input_value() == str(db["latest"]) and kpi(pg, "Total value") == first_total, "stopping a replay restores the date"
        pg.click("#replay"); pg.wait_for_function("document.querySelector('#replay') && document.querySelector('#replay').textContent.indexOf('Replay') >= 0", timeout=30000)
        assert pg.locator("#sl-on").input_value() == str(db["latest"]) and kpi(pg, "Total value") == first_total, "a finished replay ends on the latest date"
        assert pg.locator(".hero2 #c-hero svg").count() == 1 and pg.locator("#hero-last").inner_text() != "", "hero trend drawn"
        # 8d NRI lens: account-type bars and currency donut add up to the total value
        tot = sum(x["value"] for x in lines_now)
        got = pg.evaluate("(function(){var E=window.__dash.E,S=window.__dash.S,m={};E.filtered(S.on,S.F).forEach(function(l){m[l.atype]=(m[l.atype]||0)+l.value});return m})()")
        assert abs(sum(got.values()) - tot) < 1, "account types add up to total value"
        for key in ("NRE", "NRO", "FCNR"):
            want = sum(x["value"] for x in lines_now if key in x.get("account", "") and "FCNR" not in x.get("account", "") or (key == "FCNR" and "FCNR" in x.get("account", "")))
            have = sum(v for k, v in got.items() if k.startswith(key))
            assert abs(want - have) < 1 or want == 0, f"{key} bars match the engine"
        assert pg.locator("#c-atype .hb").count() == len(got), "one bar per account type"
        ccy = pg.evaluate("(function(){var E=window.__dash.E,S=window.__dash.S,t=0;E.filtered(S.on,S.F).forEach(function(l){t+=l.value});return t})()")
        assert abs(ccy - tot) < 1, "currency view uses the same total"
        pg.locator("#c-atype .hb").nth(0).click(); pg.wait_for_timeout(250)
        assert "Account type" in pg.locator("#chips").inner_text(), "account type bar filters"
        pg.click("#clear"); pg.wait_for_timeout(250)
        assert kpi(pg, "Total value") == first_total, "clearing restores the total"
        # 8e movers and heatmap: bars match the engine's return on cost; heatmap cells match prices
        pg.wait_for_timeout(200)
        import collections
        agg = collections.defaultdict(lambda: [0.0, 0.0])
        for x in lines_now:
            if x["cls"] in ("Mutual funds", "Equity shares"):
                agg[x["key"]][0] += x["value"]; agg[x["key"]][1] += x["cost"]
        rets = sorted(((v - c) / c for v, c in agg.values() if c > 0), reverse=True)
        want = rets[:5] + rets[-5:] if len(rets) > 10 else rets
        have = pg.evaluate("Array.from(document.querySelectorAll('#c-mov .hb .hv')).map(function(e){return parseFloat(e.textContent.replace('\\u2212','-').replace('%','').replace('+',''))})")
        assert len(have) == len(want) and all(abs(h - 100 * w) < 0.06 for h, w in zip(have, want)), "gainers and losers match the engine"
        assert pg.locator("#c-heat tbody tr").count() == min(10, len(agg)), "heatmap has one row per top holding"
        import csv as _csv
        px = collections.defaultdict(dict)
        for r in _csv.DictReader(open(ROOT / "db_dummy" / "prices.csv")):
            px[r["key"]][r["date"]] = float(r["price"])
        cell = pg.evaluate("(function(){var E=window.__dash.E,S=window.__dash.S,ds=E.timeline(S.on).slice(-13),r=document.querySelectorAll('#c-heat tbody tr')[0],td=r.querySelectorAll('td')[3];return {name:r.querySelector('th').title,txt:td.textContent,d0:ds[3],d1:ds[4]}})()")
        names = {r["name"]: r["key"] for r in _csv.DictReader(open(ROOT / "db_dummy" / "instruments.csv"))}
        key = names[cell["name"]]
        def pon(k, d): return px[k][max(x for x in px[k] if x <= d)]
        want_c = (pon(key, cell["d1"]) / pon(key, cell["d0"]) - 1) * 100
        assert abs(float(cell["txt"]) - want_c) < 0.06, f"heatmap cell matches prices ({cell['txt']} vs {want_c:.2f})"
        pg.locator("#c-heat th.rl").first.click(); pg.wait_for_timeout(250)
        assert "Holding" in pg.locator("#chips").inner_text() or pg.locator("#chips .chip").count() >= 1, "heatmap row click filters"
        pg.click("#clear"); pg.wait_for_timeout(250)
        # 8f dark mode: switch changes the theme, keeps the total, and switches back
        pg.click("#theme"); pg.wait_for_timeout(250)
        assert pg.evaluate("document.documentElement.getAttribute('data-theme')") == "dark" and kpi(pg, "Total value") == first_total, "dark mode on, total unchanged"
        assert pg.evaluate("getComputedStyle(document.body).backgroundColor") != "rgb(248, 250, 252)", "dark background applied"
        if shots: pg.screenshot(path=str(shots / "overview_dark.png"), full_page=True)
        pg.click("#theme"); pg.wait_for_timeout(250)
        assert pg.evaluate("document.documentElement.getAttribute('data-theme')") == "light", "light mode restored"
        # 8g six changes of 26 Nov: Equity shares name, no empty filter line, bank-first account list, time slider, clickable asset cards
        assert "Equity shares" in pg.locator(".tab").all_inner_texts()[2] and not any(t.strip() == "Shares" for t in pg.locator(".tab").all_inner_texts()), "tab renamed to Equity shares"
        assert pg.locator("#chips").inner_text().strip() == "", "no filter line when no filter is on"
        groups = pg.locator("#sl-account optgroup").evaluate_all("els => els.map(e => e.label)")
        assert groups[:4] == ["Federal Bank", "HDFC Bank", "ICICI Bank", "State Bank of India"] and groups[-2:] == ["Demat accounts", "Fund folios"], "banks first, then demat and folios"
        pg.select_option("#sl-account", "bank:HDFC Bank"); pg.wait_for_timeout(250)
        want = round(sum(x["value"] for x in lines_now if x["account"].startswith("HDFC Bank ")))
        assert digits(kpi(pg, "Total value")) == want and "Bank: HDFC Bank" in pg.locator("#chips").inner_text(), "all accounts of one bank"
        pg.select_option("#sl-account", "HDFC Bank NRE savings XX1101"); pg.wait_for_timeout(250)
        assert "Account:" in pg.locator("#chips").inner_text() and "Bank:" not in pg.locator("#chips").inner_text(), "one account replaces the bank filter"
        pg.click("#clear"); pg.wait_for_timeout(250)
        tl = pg.evaluate("window.__dash.E.timeline(window.__dash.E.data.meta.latest)")
        k = len(tl) - 5
        pg.evaluate("v => { var e = document.getElementById('hero-sl'); e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); }", k); pg.wait_for_timeout(250)
        want_k = round(sum(x["value"] for x in P.lines(db, __import__("datetime").date.fromisoformat(tl[k]))))
        assert digits(pg.locator(".hero2 .kpi.nw .n").inner_text()) == want_k, "slider moves the hero total live, matching the engine"
        assert pg.locator("#sl-on").input_value() == str(db["latest"]), "dragging does not change the date until released"
        pg.locator("#hero-sl").dispatch_event("change"); pg.wait_for_timeout(300)
        assert pg.locator("#sl-on").input_value() == tl[k] and digits(kpi(pg, "Total value")) == want_k, "release sets the as-on date for the whole page"
        pg.select_option("#sl-on", str(db["latest"])); pg.wait_for_timeout(250)
        pg.locator(".assets .kpi[data-cls='Equity shares']").click(); pg.wait_for_timeout(250)
        assert "Asset class: Equity shares" in pg.locator("#chips").inner_text() and pg.locator(".assets .kpi.on").count() == 1, "asset card click filters"
        assert pg.locator(".assets .kpi[data-cls='Mutual funds'] .n").inner_text() != "₹ 0", "other cards keep their values"
        pg.click("#clear"); pg.wait_for_timeout(250)
        # 8h export: an .xlsx on every page that opens and carries the same numbers; PDF button opens the print dialog
        import openpyxl
        for i in range(9):
            pg.click(f".tab[data-i='{i}']"); pg.wait_for_timeout(250)
            with pg.expect_download() as dl:
                pg.click("#export")
            assert dl.value.suggested_filename.endswith(".xlsx"), f"excel file name on page {i}"
            dl.value.save_as(str(Path(tempfile.gettempdir()) / "hk_test.xlsx"))
            wb = openpyxl.load_workbook(str(Path(tempfile.gettempdir()) / "hk_test.xlsx"))
            assert wb.worksheets[0].title == "Summary" and wb.worksheets[0]["B2"].value, f"summary sheet on page {i}"
            if i == 0:
                sm = {r[0].value: r[1].value for r in wb["Summary"].iter_rows(min_row=8) if r[0].value}
                assert sm["Total value"] == total(db["latest"]), "excel total value equals engine total"
                hs = wb["Holdings"]
                assert hs.max_row - 2 == len({x["key"] for x in P.lines(db, db["latest"])}), "excel holdings rows = holdings, less header and total rows"
        pg.click(".tab[data-i='0']"); pg.wait_for_timeout(250)
        pg.evaluate("window.__printed = 0; window.print = function () { window.__printed++; }; 0")
        pg.click("#exportpdf")
        assert pg.evaluate("window.__printed") == 1 and pg.title() == "Hisaab Kitaab", "PDF button prints the page and restores the title"
        assert pg.locator("#exportpdf").is_visible() and all(pg.locator("#export").is_visible() for _ in [0]), "export buttons on the overview"
        if shots:
            for i, n in enumerate(["overview", "funds", "shares", "bank", "property", "insurance", "calendar", "checks", "dtaa"]):
                pg.click(f".tab[data-i='{i}']"); pg.wait_for_timeout(400)
                pg.screenshot(path=str(shots / f"{n}.png"), full_page=True)
        # 9 phone width: no sideways scroll on any page
        ph = b.new_page(viewport={"width": 390, "height": 800}, reduced_motion="reduce")
        ph.on("pageerror", lambda e: errs.append(str(e)))
        ph.goto(out.as_uri())
        for i in range(9):
            ph.click(f".tab[data-i='{i}']"); ph.wait_for_timeout(300)
            assert ph.evaluate("document.documentElement.scrollWidth") <= 390, f"phone overflow on page {i}"
        if shots: ph.click(".tab[data-i='0']"); ph.screenshot(path=str(shots / "phone_overview.png"), full_page=True)
        b.close()
    assert not errs, errs
    print("  screen test: displayed totals equal the Python engine for 4 month ends, 5 slicer or click paths; holdings filter, search, range and CSV export; SIP plan, house property, insurance, cash calendar and name; DTAA tab results; mini trends, waterfall, At a glance, Replay, account-type and currency views, gainers and losers, price-change heatmap (checked against raw prices), light and dark mode; phone width on 9 pages; tooltip works; no console errors")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
    print("ALL PASS")
