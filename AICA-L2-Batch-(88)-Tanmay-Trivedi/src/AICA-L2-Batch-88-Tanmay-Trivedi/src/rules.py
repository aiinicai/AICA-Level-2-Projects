"""
rules.py
---------
The rule table for Section 17(5) of the CGST Act, 2017 ("Blocked Credits") and
the small engine that matches a free-text expense description against it.

Each Category is one sub-clause (or a natural sub-group of one) of Section
17(5). Most categories are a flat block with no exceptions; a few need one or
two follow-up Yes/No questions before a final verdict can be given, because
the Act itself carves out exceptions (e.g. a cab company can claim ITC on
cars, a restaurant can claim ITC on the food it buys to resell).

This reflects the law as amended by the Finance Act, 2025 (25th GST Council
recommendation), which replaced "plant or machinery" with "plant and
machinery" in clauses (c) and (d) with retrospective effect from 01-07-2017,
overriding the Supreme Court's Safari Retreats judgement. Verify against the
current text of the CGST Act before relying on this for a filing position -
this is a planning/first-check tool, not a substitute for reading the section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ELIGIBLE = "ITC ELIGIBLE"
BLOCKED = "ITC BLOCKED"
NEEDS_INPUT = "NEEDS_INPUT"


@dataclass
class Condition:
    key: str
    question: str
    yes_verdict: str | None
    no_verdict: str | None
    yes_note: str
    no_note: str


@dataclass
class Category:
    id: str
    clause: str
    title: str
    keywords: list[str]
    general_rule: str
    default_verdict: str
    conditions: list[Condition] = field(default_factory=list)
    special_note: str = ""
    # Lower priority = a broad catch-all clause that should only win when no
    # more specific clause also matches (specific provisions override general
    # ones - e.g. a car is governed by the motor-vehicle clause (a), not the
    # generic "personal consumption" clause (g), even if both phrases appear).
    priority: int = 0


CATEGORIES: list[Category] = [
    Category(
        id="motor_vehicle",
        clause="17(5)(a)",
        title="Motor Vehicles for Transport of Persons",
        keywords=["motor vehicle", "car", "cab", "sedan", "suv", "two wheeler",
                   "bike", "scooter", "passenger vehicle", "vehicle purchase", "hatchback"],
        general_rule="ITC on motor vehicles for transporting persons (seating capacity up to 13, including the driver) is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "seating_over_13",
                "Does the vehicle's seating capacity exceed 13 persons (including the driver)?",
                yes_verdict=ELIGIBLE, no_verdict=None,
                yes_note="Vehicles with seating capacity over 13 fall outside clause (a) entirely.",
                no_note="",
            ),
            Condition(
                "used_for_exception",
                "Is it used for further supply of such vehicles (dealer stock), transportation of "
                "passengers (cab/travel business), or imparting driver training?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the clause (a) exception for these specific uses.",
                no_note="No applicable exception - blocked under clause (a).",
            ),
        ],
    ),
    Category(
        id="vessel_aircraft",
        clause="17(5)(aa)",
        title="Vessels & Aircraft",
        keywords=["vessel", "aircraft", "ship", "yacht", "helicopter", "airplane", "boat"],
        general_rule="ITC on vessels and aircraft is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "used_for_exception",
                "Is it used for further supply, passenger transportation, navigation/flying "
                "training, or transportation of goods?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the clause (aa) exception for these specific uses.",
                no_note="No applicable exception - blocked under clause (aa).",
            ),
        ],
    ),
    Category(
        id="vehicle_insurance_repair",
        clause="17(5)(ab)",
        title="Insurance, Repair & Servicing of Restricted Vehicles/Vessels/Aircraft",
        keywords=["vehicle insurance", "car insurance", "motor insurance", "vehicle repair",
                   "vehicle servicing", "vehicle maintenance", "car servicing", "car repair"],
        general_rule="ITC on general insurance, servicing, repair and maintenance of the motor "
                      "vehicles/vessels/aircraft covered by clause (a)/(aa) is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "used_for_exception",
                "Does the underlying vehicle/vessel/aircraft itself qualify for ITC under the "
                "(a)/(aa) exceptions, OR are you a manufacturer of such vehicles/vessels/aircraft, "
                "OR a general insurance company insuring them?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the clause (ab) exception.",
                no_note="No applicable exception - blocked under clause (ab).",
            ),
        ],
    ),
    Category(
        id="food_catering_health",
        clause="17(5)(b)(i)",
        title="Food & Beverages, Outdoor Catering, Beauty Treatment, Cosmetic/Plastic Surgery, Health Services",
        keywords=["food", "beverages", "catering", "outdoor catering", "canteen", "refreshment",
                   "snacks", "beauty treatment", "cosmetic surgery", "plastic surgery",
                   "health service", "spa treatment"],
        general_rule="ITC on food & beverages, outdoor catering, beauty treatment, cosmetic/plastic "
                      "surgery and health services is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "same_category_outward_supply",
                "Is this used to make an outward taxable supply of the SAME category (e.g. a "
                "restaurant buying food to resell), or as part of a taxable composite/mixed supply?",
                yes_verdict=ELIGIBLE, no_verdict=None,
                yes_note="Falls within the same-category outward-supply exception.",
                no_note="",
            ),
            Condition(
                "obligatory_under_law",
                "Is providing this obligatory for the employer under any law currently in force?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the statutory-obligation exception.",
                no_note="No applicable exception - blocked under clause (b)(i).",
            ),
        ],
    ),
    Category(
        id="life_health_insurance",
        clause="17(5)(b)(i)",
        title="Life Insurance & Health Insurance",
        keywords=["life insurance", "health insurance", "mediclaim", "group insurance for employee"],
        general_rule="ITC on life insurance and health insurance is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "same_category_outward_supply",
                "Is this used to make an outward taxable supply of the SAME category, or as part "
                "of a taxable composite/mixed supply (e.g. an insurance company itself)?",
                yes_verdict=ELIGIBLE, no_verdict=None,
                yes_note="Falls within the same-category outward-supply exception.",
                no_note="",
            ),
            Condition(
                "obligatory_under_law",
                "Is providing this obligatory for the employer under any law currently in force "
                "(e.g. a specific statutory requirement to insure certain employees)?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the statutory-obligation exception.",
                no_note="No applicable exception - blocked under clause (b)(i).",
            ),
        ],
    ),
    Category(
        id="vehicle_leasing_renting",
        clause="17(5)(b)(i)",
        title="Leasing, Renting or Hiring of Motor Vehicles/Vessels/Aircraft",
        keywords=["vehicle rental", "car rental", "car lease", "vehicle hire", "cab rental",
                   "leasing of vehicle", "renting of vehicle", "vehicle on lease"],
        general_rule="ITC on leasing/renting/hiring of motor vehicles, vessels or aircraft is "
                      "blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "used_for_exception",
                "Is the underlying vehicle/vessel/aircraft used for further supply, passenger "
                "transportation, or training (i.e. within the (a)/(aa) exceptions)?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the clause (a)/(aa) exception carried through to leasing.",
                no_note="No applicable exception - blocked under clause (b)(i).",
            ),
        ],
    ),
    Category(
        id="club_membership",
        clause="17(5)(b)(iii)",
        title="Club, Health & Fitness Centre Membership",
        keywords=["club membership", "gym membership", "health club", "fitness centre",
                   "fitness center", "golf club membership", "membership of a club",
                   "membership of the club", "membership of a golf club", "membership of a gym",
                   "club subscription", "annual club fee"],
        general_rule="ITC on membership of a club, health or fitness centre is blocked, with no "
                      "statutory exception (unlike food/insurance under clause (b)(i)).",
        default_verdict=BLOCKED,
        conditions=[],
    ),
    Category(
        id="employee_travel_benefit",
        clause="17(5)(b)(iv)",
        title="Employee Travel Benefits (LTC/LTA)",
        keywords=["leave travel concession", "ltc", "lta", "home travel concession",
                   "employee vacation travel"],
        general_rule="ITC on travel benefits extended to employees on vacation (LTC/LTA) is "
                      "blocked, with no statutory exception.",
        default_verdict=BLOCKED,
        conditions=[],
    ),
    Category(
        id="works_contract",
        clause="17(5)(c)",
        title="Works Contract Services for Construction of Immovable Property",
        keywords=["works contract"],
        general_rule="ITC on works contract services for construction of an immovable property "
                      "is blocked by default (other than for 'plant and machinery').",
        default_verdict=BLOCKED,
        special_note="Finance Act 2025 changed 'plant or machinery' to 'plant and machinery' in "
                      "this clause, retrospectively from 01-07-2017, reversing the Safari Retreats "
                      "judgement's favourable reading.",
        conditions=[
            Condition(
                "for_plant_and_machinery",
                "Is this for construction of 'plant and machinery' (apparatus/equipment fixed to "
                "earth by foundation) rather than a building or other civil structure?",
                yes_verdict=ELIGIBLE, no_verdict=None,
                yes_note="Plant and machinery is expressly excluded from this block.",
                no_note="",
            ),
            Condition(
                "further_supply_of_works_contract",
                "Is this an input service for further supply of works contract service (you are "
                "passing the same works contract service on)?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Falls within the further-supply-of-works-contract exception.",
                no_note="No applicable exception - blocked under clause (c).",
            ),
        ],
    ),
    Category(
        id="construction_own_account",
        clause="17(5)(d)",
        title="Goods/Services for Construction of Immovable Property on Own Account",
        keywords=["building construction", "office construction", "factory construction",
                   "construction on own account", "capitalised construction", "capitalized construction",
                   "civil work", "construction of building"],
        general_rule="ITC on goods/services received for constructing an immovable property on "
                      "your own account is blocked by default (other than for 'plant and machinery'), "
                      "even if the property is used in the course of business.",
        default_verdict=BLOCKED,
        special_note="Finance Act 2025 changed 'plant or machinery' to 'plant and machinery' in "
                      "this clause, retrospectively from 01-07-2017, reversing the Safari Retreats "
                      "judgement's favourable reading.",
        conditions=[
            Condition(
                "for_plant_and_machinery",
                "Is this for 'plant and machinery' (apparatus/equipment fixed to earth by "
                "foundation) rather than a building or other civil structure?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Plant and machinery is expressly excluded from this block.",
                no_note="No applicable exception - blocked under clause (d).",
            ),
        ],
    ),
    Category(
        id="composition_scheme",
        clause="17(5)(e)",
        title="Tax Paid Under the Composition Scheme",
        keywords=["composition scheme", "composition dealer", "composition tax"],
        general_rule="ITC on tax paid by a supplier under the composition scheme (Section 10) is "
                      "blocked, with no exception.",
        default_verdict=BLOCKED,
        conditions=[],
    ),
    Category(
        id="nrtp",
        clause="17(5)(f)",
        title="Non-Resident Taxable Person - Domestic Purchases",
        keywords=["non-resident taxable person", "nrtp"],
        general_rule="ITC on domestic goods/services received by a non-resident taxable person "
                      "is blocked by default.",
        default_verdict=BLOCKED,
        conditions=[
            Condition(
                "imported_goods",
                "Is this for goods imported by the non-resident taxable person?",
                yes_verdict=ELIGIBLE, no_verdict=BLOCKED,
                yes_note="Imported goods are the sole exception under clause (f).",
                no_note="No applicable exception - blocked under clause (f).",
            ),
        ],
    ),
    Category(
        id="personal_consumption",
        clause="17(5)(g)",
        title="Goods/Services for Personal Consumption",
        keywords=["personal use", "personal consumption", "personal expense"],
        general_rule="ITC on goods/services used for personal consumption is blocked, with no "
                      "exception.",
        default_verdict=BLOCKED,
        special_note="If use is mixed business/personal, apportion under Section 17(1)/17(2) "
                      "rather than treating the whole amount as blocked - this tool doesn't compute "
                      "that apportionment.",
        conditions=[],
        priority=-1,
    ),
    Category(
        id="lost_stolen_written_off",
        clause="17(5)(h)",
        title="Goods Lost, Stolen, Destroyed, Written Off, or Disposed of as Gift/Free Sample",
        keywords=["lost goods", "goods lost", "stolen goods", "theft of goods", "destroyed goods",
                   "goods destroyed", "written off", "write-off", "free sample", "gift",
                   "damaged goods", "scrap disposal", "goods write-off", "loss by fire",
                   "loss of stock", "stock loss"],
        general_rule="ITC on goods lost, stolen, destroyed, written off, or disposed of as a gift "
                      "or free sample is blocked, with no exception. If ITC was already claimed, "
                      "it must be reversed.",
        default_verdict=BLOCKED,
        conditions=[],
    ),
    Category(
        id="fraud_demand",
        clause="17(5)(i)",
        title="Tax Paid Pursuant to Fraud/Suppression Demands (Sections 74, 129, 130)",
        keywords=["fraud", "suppression", "wilful misstatement", "willful misstatement",
                   "confiscation", "detention of goods"],
        general_rule="ITC on tax paid pursuant to demands confirmed under Sections 74, 129 or 130 "
                      "(fraud, suppression, confiscation/detention) is blocked, with no exception.",
        default_verdict=BLOCKED,
        conditions=[],
    ),
]


def match_categories(description: str) -> list[Category]:
    """Match a free-text description against each category's keyword phrases,
    using word boundaries so a short keyword (e.g. 'ship') can't false-match
    inside an unrelated word (e.g. 'membership').

    A description can trip more than one category's keywords at once (e.g.
    "motor insurance premium for the car" contains both "motor insurance"
    and "car"). When that happens, the MOST SPECIFIC match wins - ranked by
    the matched keyword's word count, then character length - rather than
    whichever category happens to be listed first. Otherwise a generic
    single-word hit (like "car") could out-rank the more specific phrase
    (like "motor insurance") that actually describes the expense."""
    text = description.lower()
    scored = []
    for cat in CATEGORIES:
        best_score = None
        for kw in cat.keywords:
            pattern = r"\b" + re.escape(kw.strip().lower()) + r"\b"
            if re.search(pattern, text):
                score = (len(kw.strip().split()), len(kw.strip()))
                if best_score is None or score > best_score:
                    best_score = score
        if best_score is not None:
            scored.append(((cat.priority,) + best_score, cat))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [cat for _score, cat in scored]


def get_category(cat_id: str) -> Category | None:
    for cat in CATEGORIES:
        if cat.id == cat_id:
            return cat
    return None


def evaluate(category: Category, answers: dict) -> dict:
    """Walk the category's conditions in order using the given answers
    (dict of condition-key -> 'Y'/'N'). Returns a dict with verdict, clause,
    reasoning, and (if applicable) the next unanswered question so an
    interactive caller can prompt for it."""
    reasoning_notes = [category.general_rule]

    for cond in category.conditions:
        ans = (answers.get(cond.key) or "").strip().upper()
        if ans not in ("Y", "N"):
            return {
                "verdict": NEEDS_INPUT,
                "clause": category.clause,
                "next_question_key": cond.key,
                "next_question": cond.question,
                "reasoning": " ".join(reasoning_notes),
            }
        if ans == "Y":
            if cond.yes_verdict is not None:
                reasoning_notes.append(cond.yes_note)
                return {
                    "verdict": cond.yes_verdict,
                    "clause": category.clause,
                    "next_question_key": None,
                    "next_question": None,
                    "reasoning": " ".join(reasoning_notes),
                }
            # yes_verdict is None -> continue to next condition
            reasoning_notes.append(cond.yes_note)
            continue
        else:  # 'N'
            if cond.no_verdict is not None:
                reasoning_notes.append(cond.no_note)
                return {
                    "verdict": cond.no_verdict,
                    "clause": category.clause,
                    "next_question_key": None,
                    "next_question": None,
                    "reasoning": " ".join(reasoning_notes),
                }
            reasoning_notes.append(cond.no_note)
            continue

    return {
        "verdict": category.default_verdict,
        "clause": category.clause,
        "next_question_key": None,
        "next_question": None,
        "reasoning": " ".join(reasoning_notes),
    }
