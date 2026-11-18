"""Shared application state for all pages."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ..config import Settings, get_secret
from ..db.models import Company
from ..db.session import is_reachable, local_sessionmaker, make_local_engine, make_remote_engine
from ..engine import masters as masters_mod
from ..engine.posting import PostResult, post
from ..extract.pipeline import ExtractOptions
from ..gst_states import state_code
from ..tally.client import TallyClient


class AppState:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.actor = f"{settings.user_name}@{settings.host_name}"
        self.holder = f"{self.actor}#{settings.machine_id[:6]}"
        self.Local = local_sessionmaker(make_local_engine(settings.local_db_url), self.actor)
        self.session = self.Local()          # UI-thread session
        self._remote = None
        self.window = None
        self.company_id: str = ""
        self._listeners = []

    # ---- remote DB
    def reset_remote(self):
        self._remote = None

    def remote(self):
        if self._remote is None and self.settings.remote_db_url:
            eng = make_remote_engine(self.settings.remote_db_url, get_secret("remote_db_password"))
            self._remote = (eng, sessionmaker(bind=eng, expire_on_commit=False))
        return self._remote

    def lock_session(self):
        """Company lock lives on the office DB when reachable, else locally."""
        r = self.remote() if self.settings.remote_db_url else None
        if r and is_reachable(r[0]):
            return r[1]()
        return self.Local()

    # ---- companies
    def companies(self) -> list[Company]:
        return list(self.session.scalars(select(Company).order_by(Company.name)))

    def company(self) -> Company | None:
        return self.session.get(Company, self.company_id) if self.company_id else None

    def set_company(self, cid: str):
        if cid != self.company_id:
            self.company_id = cid
            for fn in self._listeners:
                fn()

    def on_company_change(self, fn):
        self._listeners.append(fn)

    def masters(self, company: Company | None = None):
        """Masters are read once and reused until Tally is synced or a ledger is created (cheap check)."""
        c = company or self.company()
        if not c:
            return masters_mod.Masters()
        from sqlalchemy import func, select
        from ..db.models import MasterCache
        stamp = self.session.execute(select(func.count(), func.max(MasterCache.id), func.max(MasterCache.synced_at))
                                     .where(MasterCache.company_id == c.id)).one()
        cache = getattr(self, "_masters_cache", {})
        hit = cache.get(c.id)
        if hit and hit[0] == tuple(stamp):
            return hit[1]
        m = masters_mod.load(self.session, c.id)
        cache[c.id] = (tuple(stamp), m)
        self._masters_cache = cache
        return m

    def client(self, company: Company | None = None) -> TallyClient:
        c = company or self.company()
        return TallyClient(c.tally_host if c else self.settings.default_tally_host,
                           c.tally_port if c else self.settings.default_tally_port, self.settings.tally_timeout_s)

    def extract_options(self, company: Company) -> ExtractOptions:
        s = self.settings
        return ExtractOptions(company_gstin=company.gstin, company_state=state_code(company.state),
                              company_name=company.name,
                              gemini_key=get_secret("gemini_api_key") or "", gemini_model=s.gemini_model,
                              gemini_threshold=s.gemini_threshold, allow_unredacted_image=s.allow_unredacted_image,
                              use_gemini=s.use_gemini, layouts=self._layouts(company))

    def _layouts(self, company) -> dict:
        from ..engine import layouts
        s = self.Local()
        try:
            return layouts.load_all(s, company.id)
        finally:
            s.close()

    def post(self, session, company, voucher, row=None, override_reason: str = "", remote_id: str = "") -> PostResult:
        from ..engine.entry import check_restrictions
        m = masters_mod.load(session, company.id)
        lock_s = self.lock_session()
        try:
            res = post(session, lock_s, self.client(company), company, voucher, self.holder, row,
                       set(m.ledgers), set(m.stock_items), self.settings.lock_stale_seconds,
                       override_reason, check_restrictions(voucher, m, company), remote_id)
        finally:
            lock_s.close()
        if res.ok:
            self.changed(company.id)
        return res

    # ---- one "data changed" signal for every screen
    def version(self, company_id: str | None = None) -> int:
        return getattr(self, "_versions", {}).get(company_id or (self.company().id if self.company() else ""), 0)

    def changed(self, company_id: str | None = None) -> None:
        """Something in Tally or the app's own data changed (posting, sync, import, invoice cleared).
        Drops every cache for the company; each page reloads the next time it is shown."""
        cid = company_id or (self.company().id if self.company() else "")
        v = getattr(self, "_versions", {})
        v[cid] = v.get(cid, 0) + 1
        self._versions = v
        from ..engine import history
        history.invalidate(cid)
        try:
            from . import reports_page, workbench
            for k in [k for k in reports_page._CACHE if k[0] == cid]:
                reports_page._CACHE.pop(k, None)
            for k in [k for k in workbench._BAL_CACHE if k[0] == cid]:
                workbench._BAL_CACHE.pop(k, None)
        except Exception:
            pass
