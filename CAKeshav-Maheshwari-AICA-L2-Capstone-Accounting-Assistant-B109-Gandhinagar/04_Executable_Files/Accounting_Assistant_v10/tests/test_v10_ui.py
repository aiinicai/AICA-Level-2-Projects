"""v10 look: themes, 3D tiles, glass cards, sparklines."""
from datetime import date, datetime


def test_every_theme_builds_and_old_names_map(qapp):
    from PyQt6.QtGui import QColor
    from app.ui import theme
    assert theme.resolve("light") == "pearl" and theme.resolve("dark") == "midnight"
    assert theme.resolve("unknown") == theme.DEFAULT
    for key, label in theme.THEMES:
        q = theme.apply(key)
        assert label and "QPushButton#nav:checked" in q and "{" in q
        # values other screens hand to QColor() must stay plain colours
        for name in ("SURFACE", "ACCENT", "LINE", "INK", "MUTED", "OK_FG", "WARN_FG", "WARN_BG", "ERR_FG", "SUBTLE"):
            assert QColor(getattr(theme, name)).isValid(), (key, name)
        assert len(theme.TILES) == 3 and theme.MODULE["Bank"]
    theme.apply(theme.DEFAULT)


def test_tiles_cards_and_title_paint(qapp):
    from app.ui import fx, theme
    for key, _l in theme.THEMES:
        theme.apply(key)
        t = fx.GlowTile("Invoices waiting", "Open Workbench", 1)
        t.resize(360, 140)
        t.set_value(21, [1, 3, 2, 5, 4, 8])
        t._set_t(1.0)                                  # hovered: lifted, brighter glow
        assert not t.grab().isNull() and t.eff.blurRadius() > 40
        t.set_value(0, [0, 0, 0])                      # flat line, no crash
        assert not t.grab().isNull()
        c = fx.GlassCard("CASH & BANK", "#2DD4BF")
        c.resize(300, 120)
        c._set_t(0.6)
        assert not c.grab().isNull()
        g = fx.GradientLabel("Aarohan Infotech Private Limited", 26)
        assert g.sizeHint().width() > 200 and not g.grab().isNull()
    theme.apply(theme.DEFAULT)


def test_tile_click_emits(qapp):
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtTest import QTest
    from app.ui import fx
    t = fx.GlowTile("Bank lines to post", "Open Bank", 1)
    t.resize(300, 140)
    t.show()
    hits = []
    t.clicked.connect(lambda: hits.append(1))
    QTest.mouseClick(t, Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
    assert hits == [1]


def test_activity_series(db):  # noqa: F811
    from app.db.models import BankLine, VoucherHistory
    from app.engine import dashboard
    s, c = db
    today = date(2026, 11, 18)
    s.add_all([BankLine(company_id=c.id, bank_ledger="HDFC", line_hash=f"h{i}", date=d, narration="x")
               for i, d in enumerate(["20261118", "20261118", "20261110", "20261001"])])
    s.add(VoucherHistory(company_id=c.id, guid="v1", masterid="1", date="20261117", voucher_type="Journal",
                         number="1", party="", reference="", narration="", entries=[]))
    s.commit()
    a = dashboard.activity(s, c.id, 14, today)
    assert len(a["bank"]) == 14 and a["bank"][-1] == 2 and sum(a["bank"]) == 3   # October line is outside
    assert a["posted"][-2] == 1 and sum(a["invoices"]) == 0


from tests.test_engine import db  # noqa: E402,F401
