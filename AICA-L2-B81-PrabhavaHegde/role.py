"""
Engagement role determination.

The single most misunderstood point in DPDP work for a CA practice. Published
guidance contradicts itself: some sources say a CA firm is always a Data
Fiduciary, others say it acts as a Data Processor. Both are describing different
engagements.

The test is who decides the purpose and means of processing, so the answer belongs
to the engagement, not to the firm. A firm can be Fiduciary on its own payroll and
Processor on an outsourced payroll mandate, in the same week.

This module asks five questions and returns a role plus written reasoning. The
reasoning is printed in the report, because an unexplained role determination is
the first thing an opposing view will attack.
"""

from __future__ import annotations

from dataclasses import dataclass

# Each question carries the weight it contributes toward a Fiduciary finding.
# Negative weight pulls toward Processor.
QUESTIONS = [
    {
        "id": "Q1",
        "text": "Does the entity decide WHY the personal data is collected, "
                "independently of any instruction from another organisation?",
        "weight": 3,
        "fiduciary_note": "decides the purpose of processing independently",
        "processor_note": "processes for a purpose set by another organisation",
    },
    {
        "id": "Q2",
        "text": "Does the entity decide HOW the data is processed - the systems, "
                "the retention, who has access?",
        "weight": 2,
        "fiduciary_note": "decides the means of processing",
        "processor_note": "follows means specified by the engaging organisation",
    },
    {
        "id": "Q3",
        "text": "Does the entity collect the personal data directly from the individual?",
        "weight": 2,
        "fiduciary_note": "collects directly from the Data Principal",
        "processor_note": "receives data from another organisation rather than the individual",
    },
    {
        "id": "Q4",
        "text": "Would the entity continue to hold and use this data if the engaging "
                "organisation terminated the relationship?",
        "weight": 2,
        "fiduciary_note": "retains and uses the data on its own account",
        "processor_note": "holds data only for the duration of the mandate",
    },
    {
        "id": "Q5",
        "text": "Is the entity bound by a written contract to process only on the "
                "documented instructions of another organisation?",
        "weight": -3,
        "fiduciary_note": "is not contractually confined to another party's instructions",
        "processor_note": "is contractually confined to documented instructions",
    },
]

FIDUCIARY_THRESHOLD = 3

# The note shown above the role questions.
ROLE_NOTE = ("The role is decided per engagement, not per firm. The same entity can "
             "be a Fiduciary on one mandate and a Processor on another.")


@dataclass
class RoleFinding:
    role: str                 # 'fiduciary' or 'processor'
    score: int
    reasoning: str
    borderline: bool          # True when the result is close enough to warrant partner review


def determine(answers: dict[str, bool]) -> RoleFinding:
    """Decide the engagement role from yes/no answers keyed by question id.

    Returns the role, the score, and reasoning written in report language.
    A borderline result is flagged rather than resolved silently - the tool
    should not pretend to certainty the facts do not support.
    """
    missing = [q["id"] for q in QUESTIONS if q["id"] not in answers]
    if missing:
        raise ValueError(f"role determination incomplete, missing: {missing}")

    total = 0
    fiduciary_points: list[str] = []
    processor_points: list[str] = []

    for q in QUESTIONS:
        said_yes = answers[q["id"]]
        if said_yes:
            total += q["weight"]
            # A 'yes' on a negatively weighted question is a Processor indicator.
            (fiduciary_points if q["weight"] > 0 else processor_points).append(
                q["fiduciary_note"] if q["weight"] > 0 else q["processor_note"]
            )
        else:
            (processor_points if q["weight"] > 0 else fiduciary_points).append(
                q["processor_note"] if q["weight"] > 0 else q["fiduciary_note"]
            )

    role = "fiduciary" if total >= FIDUCIARY_THRESHOLD else "processor"
    borderline = abs(total - FIDUCIARY_THRESHOLD) <= 2

    role_name = "Data Fiduciary" if role == "fiduciary" else "Data Processor"
    points, counter = ((fiduciary_points, processor_points) if role == "fiduciary"
                       else (processor_points, fiduciary_points))

    reasoning = f"The entity has been assessed as a {role_name} for this engagement. It {_join(points)}."
    if counter:
        reasoning += (" Factors pointing the other way were considered, namely that it "
                      + _join(counter) + ".")
    if borderline:
        reasoning += (" The determination is finely balanced on the facts stated and should "
                      "be confirmed by the engagement partner against the executed contract "
                      "before the report is issued.")

    return RoleFinding(role=role, score=total, reasoning=reasoning, borderline=borderline)


def _join(items: list[str]) -> str:
    """Join clauses into readable report prose."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


if __name__ == "__main__":
    # A CA firm assessing its own practice: decides purpose, collects directly, keeps data.
    own_practice = {"Q1": True, "Q2": True, "Q3": True, "Q4": True, "Q5": False}
    # An outsourced payroll mandate: client sets purpose, firm works to instruction.
    payroll_mandate = {"Q1": False, "Q2": False, "Q3": False, "Q4": False, "Q5": True}

    for label, ans in [("Own practice", own_practice), ("Payroll mandate", payroll_mandate)]:
        f = determine(ans)
        print(f"{label:<18} -> {f.role.upper():<10} score={f.score:<3} borderline={f.borderline}")
        print(f"                   {f.reasoning}\n")

    assert determine(own_practice).role == "fiduciary"
    assert determine(payroll_mandate).role == "processor"
    print("role self-check: ok")
