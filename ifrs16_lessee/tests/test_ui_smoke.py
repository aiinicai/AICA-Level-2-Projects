"""UI logic smoke test with a fake Qt (real PySide6 is not required). It does NOT replace manual testing of the real UI."""
import datetime as dt
import unittest
from decimal import Decimal as D

from tests import fake_qt


class UISmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import PySide6.QtWidgets as w   # noqa: F401
            cls.real = hasattr(w, 'QApplication') and w.__file__ is not None
        except ImportError:
            cls.real = False
        if not cls.real:
            fake_qt.install()

    def test_pages_construct_refresh_and_events(self):
        if self.real:
            self.skipTest('real PySide6 present; smoke test is for headless fake Qt only')
        from ifrs16lessee.store import Store
        from ifrs16lessee.ui import pages, workspaces
        from ifrs16lessee.sample import load_sample

        class Win:
            def __init__(self):
                self.store = Store(); self.ref = None; self.went = []
            def set_lease(self, r): self.ref = r
            def refresh_all(self): pass
            def goto(self, n): self.went.append(n)
            def new_lease(self): pass
        w = Win()
        load_sample(w.store)
        w.ref = 'SAMPLE-001'
        dash, form, sched = pages.Dashboard(w), pages.LeaseForm(w), pages.Schedule(w)
        ev, term = workspaces.EventWorkspace(w, 'reassess'), workspaces.EventWorkspace(w, 'termination')
        jr, ta, rp = workspaces.JournalsPage(w), workspaces.TallyPage(w), workspaces.ReportsPage(w)
        for p in (dash, form, sched, ev, term, jr, ta, rp):
            p.refresh()
        self.assertEqual(form.ref.text(), 'SAMPLE-001')
        t = form.build()
        orig = w.store.get_terms('SAMPLE-001')
        self.assertEqual((t.payment_amount, t.discount_rate, t.commencement, t.end_date), (orig.payment_amount, orig.discount_rate, orig.commencement, orig.end_date))
        # new lease via the form
        form.ref.setText('UI-1'); form.lessor.setText('L'); form.asset.setText('Car'); form.amount.setText('500')
        form.save()
        self.assertIn('UI-1', [l['ref'] for l in w.store.list_leases()])
        # termination preview + commit through the workspace
        w.ref = 'UI-1'
        term.scope.setText('50'); term.cash.setText('0')
        term.preview()
        self.assertIsNotNone(term.pending)
        # reassessment preview needs a revised rate: expect a friendly warning, not an exception
        from tests.fake_qt import QMessageBox
        QMessageBox.shown.clear()
        ev.type.i = ev.type.findData('term_reassessment')
        ev.new_end_on._c = True
        ev.preview()
        self.assertTrue(any(k == 'warn' for k, _ in QMessageBox.shown))
        # tally page save round trip
        ta.company.setText('Demo Co'); ta.save()
        self.assertEqual(w.store.get_setting('tally')['company'], 'Demo Co')
        # bad input handled gracefully
        form.amount.setText('abc')
        QMessageBox.shown.clear()
        form.save()
        self.assertTrue(any(k == 'warn' for k, _ in QMessageBox.shown))


if __name__ == '__main__':
    unittest.main()
