"""
CARO 2020 clause checklist.

The Companies (Auditor's Report) Order, 2020 was issued by the Ministry
of Corporate Affairs on 25 February 2020 and applies to statutory audits
for financial years commencing on or after 1 April 2021.  Paragraph 3
carries twenty-one clauses.

The engine does two things and stops.  It determines whether the Order
applies at all, and it pre-populates each clause with whatever the
trial balance and general ledger can actually evidence.  Every clause is
returned for the auditor to complete; nothing here is a conclusion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .formatting import inr

# Applicability thresholds under paragraph 1(2) of the Order and the
# definition of a small company in section 2(85) of the Companies Act.
SMALL_COMPANY_PAIDUP_LIMIT = 4_00_00_000       # Rs 4 crore
SMALL_COMPANY_TURNOVER_LIMIT = 40_00_00_000    # Rs 40 crore
PRIVATE_EXEMPT_CAPITAL_RESERVES = 1_00_00_000  # Rs 1 crore
PRIVATE_EXEMPT_BORROWINGS = 1_00_00_000        # Rs 1 crore
PRIVATE_EXEMPT_REVENUE = 10_00_00_000          # Rs 10 crore


@dataclass
class ApplicabilityResult:
    applies: bool
    reasons: list[str] = field(default_factory=list)
    reference: str = "CARO 2020, paragraph 1(2)"


def check_applicability(
    *,
    company_class: str,               # "private" | "public"
    is_one_person_company: bool = False,
    is_banking_or_insurance: bool = False,
    is_section_8: bool = False,
    paid_up_capital: float = 0.0,
    reserves_and_surplus: float = 0.0,
    turnover: float = 0.0,
    total_borrowings: float = 0.0,
    total_revenue: float = 0.0,
    is_holding_or_subsidiary_of_public: bool = False,
) -> ApplicabilityResult:
    """Determine whether CARO 2020 applies to the company under audit."""
    reasons: list[str] = []

    if is_one_person_company:
        return ApplicabilityResult(False, ["One person company - exempt under paragraph 1(2)(ii)."])
    if is_banking_or_insurance:
        return ApplicabilityResult(
            False, ["Banking or insurance company - exempt under paragraph 1(2)(i) and (iii)."]
        )
    if is_section_8:
        return ApplicabilityResult(
            False, ["Company licensed under section 8 - exempt under paragraph 1(2)(iii)."]
        )

    if (
        paid_up_capital <= SMALL_COMPANY_PAIDUP_LIMIT
        and turnover <= SMALL_COMPANY_TURNOVER_LIMIT
        and company_class == "private"
        and not is_holding_or_subsidiary_of_public
    ):
        reasons.append(
            f"Paid-up capital of Rs {inr(paid_up_capital, decimals=0)} and turnover of "
            f"Rs {inr(turnover, decimals=0)} are within the small company thresholds; confirm "
            "the company is not a holding or subsidiary of a public company."
        )

    if company_class == "private" and not is_holding_or_subsidiary_of_public:
        within = (
            (paid_up_capital + reserves_and_surplus) <= PRIVATE_EXEMPT_CAPITAL_RESERVES
            and total_borrowings <= PRIVATE_EXEMPT_BORROWINGS
            and total_revenue <= PRIVATE_EXEMPT_REVENUE
        )
        if within:
            return ApplicabilityResult(
                False,
                reasons
                + [
                    "Private company within all three limits in paragraph 1(2)(iv) - "
                    "capital plus reserves, borrowings and revenue. CARO 2020 does not apply."
                ],
            )

    reasons.append("None of the exemptions in paragraph 1(2) are satisfied.")
    return ApplicabilityResult(True, reasons)


@dataclass
class Clause:
    number: str
    title: str
    requirement: str
    data_available: bool = False
    evidence: str = ""
    suggested_status: str = "Auditor input required"
    auditor_response: str = ""

    @property
    def is_prefilled(self) -> bool:
        return self.data_available


# The twenty-one clauses of paragraph 3.
CLAUSES: tuple[tuple[str, str, str], ...] = (
    ("(i)", "Property, plant and equipment and intangible assets",
     "Maintenance of records, physical verification, title deeds held in the company's name, "
     "revaluation, and proceedings under the Benami Transactions (Prohibition) Act, 1988."),
    ("(ii)", "Inventory and working capital limits",
     "Physical verification of inventory and its coverage and discrepancies; and, where working "
     "capital limits above Rs 5 crore are sanctioned against current assets, agreement of the "
     "quarterly returns filed with banks to the books of account."),
    ("(iii)", "Investments, guarantees, security and loans or advances",
     "Particulars of investments made, guarantees or security given, and loans or advances in the "
     "nature of loans granted, with terms, repayment schedule and overdue amounts."),
    ("(iv)", "Loans to directors and investments under sections 185 and 186",
     "Compliance with sections 185 and 186 of the Companies Act, 2013 in respect of loans, "
     "investments, guarantees and security."),
    ("(v)", "Deposits",
     "Compliance with sections 73 to 76, the deposit rules, and any directions of the Reserve "
     "Bank of India in respect of deposits or amounts deemed to be deposits."),
    ("(vi)", "Cost records",
     "Maintenance of cost records prescribed under section 148(1) where applicable."),
    ("(vii)", "Statutory dues",
     "Regularity in depositing undisputed statutory dues, arrears outstanding for more than six "
     "months, and particulars of dues not deposited on account of a dispute."),
    ("(viii)", "Unrecorded income surrendered in tax assessments",
     "Transactions not recorded in the books that have been surrendered or disclosed as income "
     "in assessments under the Income-tax Act, 1961."),
    ("(ix)", "Default in repayment of borrowings",
     "Default in repayment of loans or borrowings or interest; declaration as a wilful defaulter; "
     "end use of term loans; short-term funds used for long-term purposes; and funds raised on "
     "the pledge of securities of subsidiaries, joint ventures or associates."),
    ("(x)", "Money raised by public offer or private placement",
     "Application of money raised by initial or further public offer, and compliance with section "
     "42 and section 62 for preferential allotments or private placements."),
    ("(xi)", "Fraud and whistle-blower complaints",
     "Fraud by or on the company noticed or reported; filing of Form ADT-4; and whistle-blower "
     "complaints received during the year."),
    ("(xii)", "Nidhi company",
     "Net owned funds to deposits ratio, maintenance of ten per cent unencumbered term deposits, "
     "and default in payment of interest or repayment of deposits."),
    ("(xiii)", "Related party transactions",
     "Compliance with sections 177 and 188 and disclosure of related party transactions in the "
     "financial statements as required by the applicable accounting standards."),
    ("(xiv)", "Internal audit system",
     "Existence of an internal audit system commensurate with the size and nature of the business, "
     "and consideration of the internal auditor's reports by the statutory auditor."),
    ("(xv)", "Non-cash transactions with directors",
     "Non-cash transactions with directors or persons connected with them, and compliance with "
     "section 192."),
    ("(xvi)", "Registration under section 45-IA of the RBI Act",
     "Requirement for and status of registration as a non-banking financial company or housing "
     "finance company, and whether the group has any core investment company."),
    ("(xvii)", "Cash losses",
     "Cash losses incurred in the financial year and in the immediately preceding financial year."),
    ("(xviii)", "Resignation of statutory auditors",
     "Resignation of the statutory auditors during the year and consideration of the issues, "
     "objections or concerns raised by the outgoing auditors."),
    ("(xix)", "Material uncertainty over meeting liabilities",
     "On the basis of the financial ratios, ageing and expected dates of realisation of financial "
     "assets and payment of financial liabilities, whether any material uncertainty exists as to "
     "the company meeting its liabilities existing at the balance sheet date as and when they "
     "fall due within one year."),
    ("(xx)", "Corporate social responsibility",
     "Transfer of unspent corporate social responsibility amounts in accordance with section 135."),
    ("(xxi)", "Qualifications in group companies",
     "Qualifications or adverse remarks by the respective auditors in the CARO reports of the "
     "companies included in the consolidated financial statements."),
)


@dataclass
class CAROChecklist:
    applicability: ApplicabilityResult
    clauses: list[Clause] = field(default_factory=list)
    reference: str = "CARO 2020 (issued 25 February 2020), paragraph 3"

    @property
    def prefilled_count(self) -> int:
        return sum(1 for c in self.clauses if c.is_prefilled)

    def as_rows(self) -> list[dict]:
        return [
            {
                "Clause": c.number,
                "Subject": c.title,
                "Requirement": c.requirement,
                "Data available": "Yes" if c.data_available else "No",
                "Evidence from the books": c.evidence,
                "Status": c.suggested_status,
                "Auditor response": c.auditor_response,
            }
            for c in self.clauses
        ]


def build_checklist(
    applicability: ApplicabilityResult,
    *,
    facts: dict | None = None,
) -> CAROChecklist:
    """Build the twenty-one clause checklist, pre-populating the clauses the
    accounting records can evidence.

    `facts` accepts keys the engine derives elsewhere: has_ppe, has_inventory,
    working_capital_limit, statutory_dues_outstanding, cash_loss_current,
    cash_loss_prior, has_borrowings, current_ratio, csr_applicable,
    related_party_balances, has_investments.
    """
    facts = facts or {}
    checklist = CAROChecklist(applicability=applicability)

    for number, title, requirement in CLAUSES:
        clause = Clause(number=number, title=title, requirement=requirement)

        if number == "(i)" and "has_ppe" in facts:
            clause.data_available = True
            has = facts["has_ppe"]
            clause.evidence = (
                f"Property, plant and equipment of Rs {inr(facts.get('ppe_value', 0))} "
                "appears in the trial balance." if has
                else "No property, plant and equipment balance in the trial balance."
            )
            clause.suggested_status = (
                "Obtain the fixed asset register, physical verification report and title deeds."
                if has else "Confirm the company holds no such assets."
            )

        elif number == "(ii)" and "has_inventory" in facts:
            clause.data_available = True
            has = facts["has_inventory"]
            clause.evidence = (
                f"Inventory of Rs {inr(facts.get('inventory_value', 0))} at the year end." if has
                else "No inventory balance in the trial balance."
            )
            wc = facts.get("working_capital_limit", 0)
            clause.suggested_status = (
                "Obtain the physical verification report. "
                + (
                    "Working capital limits exceed Rs 5 crore - agree the quarterly returns filed "
                    "with the bank to the books."
                    if wc > 5_00_00_000
                    else "Confirm whether working capital limits above Rs 5 crore are sanctioned."
                )
            ) if has else "Confirm the company carries no inventory."

        elif number == "(vii)" and "statutory_dues_outstanding" in facts:
            clause.data_available = True
            amount = facts["statutory_dues_outstanding"]
            clause.evidence = f"Statutory dues of Rs {inr(amount)} outstanding at the year end."
            clause.suggested_status = (
                "Age the balance and confirm nothing is outstanding beyond six months from the "
                "date it became payable; obtain the disputed dues schedule."
            )

        elif number == "(ix)" and "has_borrowings" in facts:
            clause.data_available = True
            has = facts["has_borrowings"]
            clause.evidence = (
                f"Borrowings of Rs {inr(facts.get('borrowings_value', 0))} at the year end." if has
                else "No borrowings in the trial balance."
            )
            clause.suggested_status = (
                "Obtain the repayment schedule, bank confirmations and the wilful defaulter "
                "declaration." if has else "Report that the clause is not applicable."
            )

        elif number == "(xiii)" and "related_party_balances" in facts:
            clause.data_available = True
            clause.evidence = (
                f"{facts['related_party_balances']} ledger(s) tagged as related party in the "
                "chart of accounts."
            )
            clause.suggested_status = (
                "Obtain the section 188 approvals and agree the disclosure to AS 18."
            )

        elif number == "(xvii)" and "cash_loss_current" in facts:
            clause.data_available = True
            cur = facts["cash_loss_current"]
            pri = facts.get("cash_loss_prior")
            clause.evidence = (
                f"Cash {'loss' if cur < 0 else 'profit'} of Rs {inr(abs(cur))} in the current year"
                + (
                    f"; Rs {inr(abs(pri))} {'loss' if pri < 0 else 'profit'} in the preceding year."
                    if pri is not None else "; no comparative supplied."
                )
            )
            clause.suggested_status = (
                "Report the cash loss." if cur < 0 else "Report that no cash loss was incurred."
            )

        elif number == "(xix)" and "current_ratio" in facts:
            cr = facts["current_ratio"]
            # The current ratio is not computable where there are no current
            # liabilities. That is a fact about the company, not an error, and
            # the clause still has to be answered.
            if cr is None:
                clause.data_available = False
                clause.evidence = (
                    "The current ratio could not be computed - the company has no "
                    "current liabilities at the year end."
                )
                clause.suggested_status = (
                    "Assess the material uncertainty from the ageing and expected dates of "
                    "realisation of financial assets and payment of financial liabilities, "
                    "without relying on the current ratio."
                )
            else:
                clause.data_available = True
                clause.evidence = f"Current ratio of {cr:.2f} at the year end."
                clause.suggested_status = (
                    "Current ratio is below 1; evaluate the ageing of financial assets and "
                    "liabilities and consider whether a material uncertainty exists."
                    if cr < 1
                    else "Corroborate with the ageing schedules and management's cash flow forecast."
                )

        elif number == "(xx)" and "csr_applicable" in facts:
            clause.data_available = True
            clause.evidence = (
                "Corporate social responsibility expenditure appears in the trial balance."
                if facts["csr_applicable"] else
                "No corporate social responsibility expenditure in the trial balance."
            )
            clause.suggested_status = (
                "Verify the section 135 computation and the transfer of any unspent amount."
                if facts["csr_applicable"]
                else "Confirm whether section 135 applies on the basis of net worth, turnover "
                     "and net profit."
            )

        checklist.clauses.append(clause)

    return checklist
