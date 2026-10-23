"""Map each Tally ledger to a Schedule III line using the editable rulebook.

Order of precedence: user override > rule for the ledger's own group > rule for a parent group.
Within a rule, the first matching name pattern ("case") wins, otherwise the rule default applies.
Ledgers with no rule come out as UNMAPPED and are flagged for a person (or, later, AI) to decide.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .tb import TrialBalance

RULEBOOK_PATH = Path(__file__).with_name("rulebook_non_ind_as.json")
MAPPING_COLS = ["ledger", "group", "primary_group", "statement", "line", "line_label", "sub", "opening", "closing",
                "source", "rule_id", "review"]


@dataclass
class Rulebook:
    lines: dict
    rules: list
    framework: str

    @classmethod
    def load(cls, path=RULEBOOK_PATH) -> "Rulebook":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["lines"], data["rules"], data.get("framework", ""))

    def rules_for(self, group: str) -> list:
        return [r for r in self.rules if group in r["groups"]]


def _pick(rulebook: Rulebook, chain: list[str], name: str):
    """Return (rule, case_or_None) for the deepest group that has a matching rule."""
    for g in chain:
        for rule in rulebook.rules_for(g):
            for case in rule.get("cases", []):
                if re.search(case["name"], name, re.I):
                    return rule, case
            if rule.get("line"):
                return rule, None
    return None, None


def _sign_ok(closing: float, normal: str | None) -> bool:
    if not normal or abs(closing) < 0.005:
        return True
    return (closing > 0) == (normal == "Dr")


def map_ledgers(tb: TrialBalance, rulebook: Rulebook | None = None, overrides: dict | None = None) -> pd.DataFrame:
    rb = rulebook or Rulebook.load()
    overrides = overrides or {}
    rows = []
    for led in tb.ledgers.itertuples(index=False):
        chain = tb.chain(led.group)
        rule, case = _pick(rb, chain, led.name)
        item = {"ledger": led.name, "group": led.group, "primary_group": led.primary_group,
                "opening": led.opening, "closing": led.closing, "source": "rule", "rule_id": "", "review": [],
                "inventory_pl_line": None, "_net": None}
        if led.name in overrides:
            o = overrides[led.name]
            item.update(line=o["line"], sub=o.get("sub", ""), source="override", rule_id="OVERRIDE")
            if o.get("reason"):
                item["review"].append(f"Override: {o['reason']}")
        elif rule is None:
            item.update(line="UNMAPPED", sub="", source="unmapped", rule_id="")
            item["review"].append("No rule matched this ledger or its groups. Assign a Schedule III line "
                                  "(add an override or a rule).")
        else:
            src = case or rule
            item.update(line=src.get("line", rule.get("line")), sub=src.get("sub", rule.get("sub", "")), rule_id=rule["id"],
                        inventory_pl_line=src.get("inventory_pl_line", rule.get("inventory_pl_line")))
            note = (case or {}).get("review") or (None if case else rule.get("review"))
            if note:
                item["review"].append(note)
            ws = rule.get("wrong_sign")
            if ws and not _sign_ok(led.closing, rule.get("normal")):
                item.update(line=ws["line"], sub=ws["sub"], rule_id=rule["id"] + "/sign")
                item["review"] = [ws["review"]] if ws.get("review") else []
            if rule.get("net"):
                m = re.search(rule["net"]["key_regex"], led.name, re.I)
                item["_net"] = (rule["net"], m.group(1).upper() if m else led.name, case is not None)
        guess = tb.inferred.get(led.name)
        if guess and guess[1] == "low" and led.name not in overrides and (abs(led.opening) + abs(led.closing)) >= 0.005:
            item["review"].append(f"The file gives no ledger group; '{guess[0]}' was guessed from the balance side. "
                                  "Confirm what this ledger is.")
        rows.append(item)

    # Netting: GST input and output of the same tax head are one balance; a net debit becomes an asset.
    nets: dict = {}
    for r in rows:
        if r["_net"]:
            nets[r["_net"][1]] = nets.get(r["_net"][1], 0.0) + r["closing"]
    for r in rows:
        if r["_net"]:
            cfg, key, had_case = r["_net"]
            tgt = cfg["debit"] if nets[key] > 0.005 else (None if had_case else cfg["credit"])
            if tgt:
                r.update(line=tgt["line"], sub=tgt["sub"])
                r["review"] = [tgt["review"]] if tgt.get("review") else r["review"]

    out = pd.DataFrame(rows)
    out["review"] = out["review"].map(lambda x: " ".join(x))
    out["line_label"] = out["line"].map(lambda k: rb.lines.get(k, {}).get("label", "Unmapped"))
    out["statement"] = out["line"].map(lambda k: rb.lines.get(k, {}).get("statement", ""))
    unm = out["statement"] == ""
    out.loc[unm, "statement"] = tb.ledgers.set_index("name").loc[out.loc[unm, "ledger"], "nature"].map(
        lambda n: "PL" if n in ("Income", "Expenses") else "BS").values
    return out[MAPPING_COLS + ["inventory_pl_line"]]
