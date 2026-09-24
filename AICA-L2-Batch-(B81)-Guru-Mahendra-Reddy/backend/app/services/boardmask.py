"""Apply the board's visibility policy to an API response.

One rule governs every line of this module: **hide detail, never contradict.**

If the board's runway reads 7.7 months and the CFO's reads 5.2, the tool has
destroyed the only thing it was built for. So masking may remove a name, a
per-person figure, an account number or a drill-down. It may never change an
amount, a date, a status or a total. Nothing here writes a number.

Where something is withheld, the response says so — `_restricted` travels back
with the payload and the screen renders "detail restricted by the CFO" in place
of the value. A board member who can see that a thing was withheld is being
governed; one who cannot is being misled.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import BoardVisibility, Pseudonym, Role, User, VisibilityRule

# Keys whose *values* are a counterparty's name.
CLIENT_KEYS = {"customer", "customer_name", "client", "client_name", "party_name"}
VENDOR_KEYS = {"vendor", "vendor_name", "supplier", "supplier_name"}
PARTY_KEYS = {"party", "counterparty"}          # could be either; decided by context
PERSON_KEYS = {"employee", "employee_name", "person", "person_name"}

# Keys removed outright when a rule is off.
ACCOUNT_NUMBER_KEYS = {"account_number", "account_no", "acct_no", "ifsc", "iban"}
SALARY_KEYS = {"salary", "ctc", "loaded_cost", "cost_per_head", "monthly_cost",
               "annual_cost", "gross_pay", "employee_cost"}
HEADROOM_KEYS = {"headroom", "headroom_pct", "headroom_percent", "cushion"}
ROUTING_KEYS = {"recipients", "escalation", "escalate_to", "quiet_hours",
                "channel_config", "phone", "whatsapp", "email_to"}

WITHHELD = "Restricted"


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------
def load_policy(db: Session, entity_ids: list[int] | None = None) -> dict[str, bool]:
    """Effective policy: stored rows over catalogue defaults."""
    policy = dict(VisibilityRule.DEFAULTS)
    q = db.query(BoardVisibility)
    if entity_ids:
        q = q.filter(BoardVisibility.entity_id.in_(list(entity_ids) + [None]))
    for row in q.all():
        if row.rule_key in policy:
            policy[row.rule_key] = bool(row.visible)
    return policy


def applies_to(user: User | None) -> bool:
    """Only the board role is masked. Everyone else sees the whole thing."""
    return bool(user) and user.role == Role.BOARD


# ---------------------------------------------------------------------------
# Stable pseudonyms
# ---------------------------------------------------------------------------
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _label_for(seq: int, kind: str) -> str:
    noun = {"client": "Client", "vendor": "Vendor", "person": "Employee"}.get(kind, "Party")
    if seq < 26:
        return f"{noun} {_LETTERS[seq]}"
    return f"{noun} {seq + 1}"


class Pseudonymiser:
    """Allocates a stand-in name once and reuses it everywhere.

    Consistency is the whole point: "Client A" has to be the same company on
    Money Coming In, in the board pack, and in an alert. So the mapping is
    persisted rather than derived per request.
    """

    def __init__(self, db: Session, entity_id: int | None):
        self.db = db
        self.entity_id = entity_id
        self._cache: dict[tuple[str, str], str] = {}
        self._counts: dict[str, int] = {}
        self._dirty = False
        for p in db.query(Pseudonym).filter(
                Pseudonym.entity_id.in_([entity_id, None])).all():
            self._cache[(p.kind, p.real_name)] = p.label
            self._counts[p.kind] = max(self._counts.get(p.kind, 0), p.seq + 1)

    def label(self, kind: str, real_name: str) -> str:
        if not real_name or not isinstance(real_name, str):
            return real_name
        key = (kind, real_name)
        if key in self._cache:
            return self._cache[key]
        seq = self._counts.get(kind, 0)
        self._counts[kind] = seq + 1
        label = _label_for(seq, kind)
        self._cache[key] = label
        self.db.add(Pseudonym(entity_id=self.entity_id, kind=kind,
                              real_name=real_name, label=label, seq=seq))
        self._dirty = True
        return label

    def commit(self) -> None:
        if self._dirty:
            try:
                self.db.commit()
            except Exception:            # a label is a convenience, never load-bearing
                self.db.rollback()


# ---------------------------------------------------------------------------
# Free text
# ---------------------------------------------------------------------------
# Masking a `customer` field is the easy half. The engine also *writes
# sentences* — "If Bharat Metro Rail Corporation paid 45 days late, the
# cash-out date moves…" — and an alert title, a narrative paragraph and an
# action note all carry names in prose. Masking the structured fields while
# leaving those intact would be worse than not masking at all: it would look
# like the policy was working.
#
# So every string in the payload is scrubbed too.

# Dropped when deriving a short form, because "Bharat Metro" is how a person
# refers to "Bharat Metro Rail Corporation" and the prose does exactly that.
_GENERIC_TAIL = {
    "pvt", "private", "ltd", "limited", "llp", "inc", "corp", "corporation",
    "company", "co", "plc", "pte", "gmbh", "sa", "solutions", "services",
    "technologies", "systems", "industries", "enterprises", "and", "&",
    "authority", "projects", "park", "group", "holdings", "ventures",
}


def _aliases(name: str) -> list[str]:
    """The name, plus the shorter forms prose actually uses."""
    out = [name]
    words = name.replace(",", " ").split()
    for n in range(len(words) - 1, 1, -1):
        prefix = words[:n]
        if prefix[-1].strip(".").lower() in _GENERIC_TAIL:
            continue
        short = " ".join(prefix)
        if len(short) >= 6 and short != name:
            out.append(short)
    return out


class TextScrubber:
    """Replaces every known counterparty name found in free text.

    Longest first, so "Bharat Metro Rail Corporation" is replaced before the
    shorter "Bharat Metro" can leave a fragment behind.
    """

    def __init__(self, db: Session, entity_ids: list[int] | None,
                 pseudo: Pseudonymiser, mask_clients: bool, mask_vendors: bool):
        from app.models import Customer, Vendor

        self.pseudo = pseudo
        self.pairs: list[tuple[str, str, str]] = []      # (needle, kind, real)
        if not (mask_clients or mask_vendors):
            return

        def add(names, kind):
            for (real,) in names:
                if not real:
                    continue
                for alias in _aliases(real):
                    self.pairs.append((alias, kind, real))

        q = lambda M: (db.query(M.name).filter(M.entity_id.in_(entity_ids))   # noqa: E731
                       if entity_ids else db.query(M.name))
        if mask_clients:
            add(q(Customer).all(), "client")
        if mask_vendors:
            add(q(Vendor).all(), "vendor")
        self.pairs.sort(key=lambda p: len(p[0]), reverse=True)

    def __call__(self, text: str) -> tuple[str, bool]:
        if not self.pairs or len(text) < 4:
            return text, False
        hit = False
        for needle, kind, real in self.pairs:
            if needle in text:
                text = text.replace(needle, self.pseudo.label(kind, real))
                hit = True
        return text, hit


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------
class _Masker:
    def __init__(self, policy: dict[str, bool], pseudo: Pseudonymiser,
                 scrub: "TextScrubber | None" = None):
        self.p = policy
        self.pseudo = pseudo
        self.scrub = scrub
        self.restricted: set[str] = set()

    def _note(self, rule: str) -> None:
        self.restricted.add(rule)

    def walk(self, node: Any, context: str = "") -> Any:
        if isinstance(node, list):
            return [self.walk(v, context) for v in node]
        if isinstance(node, str):
            # Free text: the sentences the engine writes carry names too.
            if self.scrub:
                out, hit = self.scrub(node)
                if hit:
                    self._note(VisibilityRule.CLIENT_NAMES
                               if not self.p[VisibilityRule.CLIENT_NAMES]
                               else VisibilityRule.VENDOR_NAMES)
                return out
            return node
        if not isinstance(node, dict):
            return node

        out: dict[str, Any] = {}
        for k, v in node.items():
            lk = k.lower()

            # --- names ------------------------------------------------------
            if lk in CLIENT_KEYS and isinstance(v, str):
                if not self.p[VisibilityRule.CLIENT_NAMES]:
                    self._note(VisibilityRule.CLIENT_NAMES)
                    out[k] = self.pseudo.label("client", v)
                    continue
            elif lk in VENDOR_KEYS and isinstance(v, str):
                if not self.p[VisibilityRule.VENDOR_NAMES]:
                    self._note(VisibilityRule.VENDOR_NAMES)
                    out[k] = self.pseudo.label("vendor", v)
                    continue
            elif lk in PARTY_KEYS and isinstance(v, str):
                # A bare "party" is a client on a receivable and a vendor on a
                # payable. The surrounding context says which; when it does not,
                # mask if either rule is off — the safer reading.
                kind = "vendor" if context in ("payable", "bill", "commitment") else "client"
                rule = (VisibilityRule.VENDOR_NAMES if kind == "vendor"
                        else VisibilityRule.CLIENT_NAMES)
                if not self.p[rule]:
                    self._note(rule)
                    out[k] = self.pseudo.label(kind, v)
                    continue
            elif lk in PERSON_KEYS and isinstance(v, str):
                if not self.p[VisibilityRule.INDIVIDUAL_SALARIES]:
                    self._note(VisibilityRule.INDIVIDUAL_SALARIES)
                    out[k] = self.pseudo.label("person", v)
                    continue

            # --- withheld values -------------------------------------------
            if lk in ACCOUNT_NUMBER_KEYS and not self.p[VisibilityRule.BANK_ACCOUNT_NUMBERS]:
                self._note(VisibilityRule.BANK_ACCOUNT_NUMBERS)
                out[k] = WITHHELD
                continue
            if lk in SALARY_KEYS and not self.p[VisibilityRule.INDIVIDUAL_SALARIES]:
                self._note(VisibilityRule.INDIVIDUAL_SALARIES)
                out[k] = None
                continue
            if lk in HEADROOM_KEYS and not self.p[VisibilityRule.COVENANT_HEADROOM]:
                self._note(VisibilityRule.COVENANT_HEADROOM)
                out[k] = None
                continue
            if lk in ROUTING_KEYS and not self.p[VisibilityRule.ALERT_ROUTING]:
                self._note(VisibilityRule.ALERT_ROUTING)
                out[k] = None
                continue
            if lk == "trace" and not self.p[VisibilityRule.DRILLDOWNS]:
                self._note(VisibilityRule.DRILLDOWNS)
                out[k] = None
                continue

            # --- recurse, carrying context ---------------------------------
            nxt = context
            if lk in ("payables", "bills", "due_now", "commitments", "money_out"):
                nxt = "payable"
            elif lk in ("receivables", "invoices", "money_in", "collections"):
                nxt = "receivable"
            out[k] = self.walk(v, nxt)

        return out


def mask_payload(db: Session, user: User, payload: Any,
                 entity_id: int | None = None) -> Any:
    """Mask one API response for a board user. A no-op for every other role."""
    if not applies_to(user):
        return payload
    policy = load_policy(db, [entity_id] if entity_id else None)
    pseudo = Pseudonymiser(db, entity_id)
    scrub = TextScrubber(db, [entity_id] if entity_id else None, pseudo,
                         mask_clients=not policy[VisibilityRule.CLIENT_NAMES],
                         mask_vendors=not policy[VisibilityRule.VENDOR_NAMES])
    masker = _Masker(policy, pseudo, scrub)
    masked = masker.walk(payload)
    pseudo.commit()

    if isinstance(masked, dict) and masker.restricted:
        masked["_restricted"] = sorted(masker.restricted)
        masked["_restricted_labels"] = [VisibilityRule.LABELS.get(r, r)
                                        for r in sorted(masker.restricted)]
    return masked


def blocked_endpoints(policy: dict[str, bool]) -> dict[str, str]:
    """Whole screens a board user is kept off, and the sentence explaining it.

    A blocked screen returns 403 with this text rather than an empty page, so
    the board member knows a decision was made rather than that the tool broke.
    """
    out: dict[str, str] = {}
    if not policy[VisibilityRule.ACTIVITY_LOG]:
        out["/api/activity"] = ("The activity log is not part of the board view. "
                                "The CFO can turn it on in Setup › Board visibility.")
    if not policy[VisibilityRule.MANUAL_REGISTER]:
        out["/api/registers/manual"] = (
            "The manual entries register is not part of the board view. Figures "
            "that are maintained by hand are still flagged on every screen.")
    if not policy[VisibilityRule.SCENARIOS]:
        out["/api/scenarios/run"] = (
            "Scenario levers are not part of the board view. The scenarios the "
            "CFO has saved are still shown.")
    return out
