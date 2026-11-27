"""
Rules for T-form statements where one line carries an inner and an outer
amount (the firm's own layout):

  Less: Drawings      2,80,000   19,39,300   -> drawings 2,80,000 + closing capital 19,39,300
  Furniture & Fixture 20,162
  Less: Depreciation   2,016     18,146      -> Furniture & Fixture (net) 18,146; the gross line is ignored
"""
import re

from core.models import SourceLine

_DRAW = re.compile(r"^(less\W*)?drawings?\b", re.I)
_DEP = re.compile(r"^(less\W*)?depreciation\b", re.I)


class TState:
    def __init__(self):
        self.last = {}          # side -> last SourceLine created on that side


def emit(state, side, label, nums, year, statement, src):
    """Return the SourceLines for one T-form segment."""
    lab = label.strip()
    out = []
    if not nums:
        return out
    if _DRAW.match(lab) and len(nums) >= 2:
        out.append(SourceLine(year=year, statement="BS", label="Less: Drawings", amount=nums[0], source=src,
                              head="drawings", confidence=95, note="T-form capital account"))
        out.append(SourceLine(year=year, statement="BS", label="Capital Account", amount=nums[-1], source=src,
                              head="capital", confidence=95, note="closing capital (outer column)"))
    elif _DEP.match(lab) and statement == "BS":
        prev = state.last.get(side)
        if prev is not None and len(nums) >= 2:
            prev.head, prev.confidence, prev.note = "ignore", 95, "gross value before depreciation"
            out.append(SourceLine(year=year, statement="BS", label=prev.label, amount=nums[-1], source=src,
                                  note="net of depreciation", gross=prev.amount))
        # a single depreciation amount under an asset is not a balance-sheet item
    else:
        out.append(SourceLine(year=year, statement=statement, label=lab, amount=nums[-1], source=src))
    for o in out:
        o.side = side
    if out:
        state.last[side] = out[-1]
    return out


def orphan(state, side, nums, year, statement, src):
    """A number with no label on the row after 'Less: Drawings' is the closing capital."""
    last = state.last.get(side)
    if statement == "BS" and last is not None and (last.head == "drawings" or _DRAW.match(last.label or "")) and nums:
        ln = SourceLine(year=year, statement="BS", label="Capital Account", amount=nums[-1], source=src,
                        head="capital", confidence=95, note="closing capital (row below drawings)", side=side)
        state.last[side] = ln
        return [ln]
    return []
