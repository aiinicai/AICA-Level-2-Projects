"""Catalogue of standard references used in explanations and judgment flags.

Descriptions are short paraphrases for navigation only; the notified Ind AS 116
text (ICAI 2025-26 edition / MCA notification) is authoritative.
"""
from __future__ import annotations

REFS: dict[str, tuple[str, str]] = {
    # key: (reference, short paraphrase)
    "EXEMPT": ("Ind AS 116.5–8, B3–B8", "Recognition exemptions — short-term leases (election by class) and leases of low-value assets (lease-by-lease)"),
    "SHORT_TERM_DEF": ("Ind AS 116 App. A", "Short-term lease: lease term of 12 months or less at commencement; a lease with a purchase option is not short-term"),
    "LOW_VALUE": ("Ind AS 116.B3–B8", "Low value assessed on the value of the asset when new, on an absolute basis; lessee must benefit from the asset on its own; not for head leases of subleases"),
    "IDENTIFY": ("Ind AS 116.9–11, B9–B31", "A contract contains a lease if it conveys the right to control the use of an identified asset for a period in exchange for consideration"),
    "SUBSTITUTION": ("Ind AS 116.B14–B19", "Supplier substitution right is substantive only if the supplier has the practical ability and would benefit economically"),
    "COMPONENTS": ("Ind AS 116.12–16", "Separate lease and non-lease components, allocating consideration on relative stand-alone prices"),
    "EXPEDIENT_15": ("Ind AS 116.15", "Practical expedient: by class of underlying asset, do not separate non-lease components"),
    "TERM": ("Ind AS 116.18–19, B34–B41", "Lease term = non-cancellable period + periods covered by options reasonably certain to be exercised (extension) or not exercised (termination)"),
    "ENFORCEABLE": ("Ind AS 116.B34", "A lease is no longer enforceable when both parties can terminate without permission with no more than an insignificant penalty; consider broader economics (IFRIC agenda decision, Nov 2019)"),
    "LESSOR_OPTION": ("Ind AS 116.B35", "A termination right held only by the lessor is not considered in determining the lease term"),
    "TERM_REASSESS": ("Ind AS 116.20–21", "Reassess on a significant event within the lessee's control; revise when the non-cancellable period changes"),
    "INITIAL_REC": ("Ind AS 116.22–23", "Recognise ROU asset and lease liability at commencement; ROU measured at cost"),
    "ROU_COST": ("Ind AS 116.24", "ROU cost = initial liability + payments at/before commencement − incentives received + initial direct costs + restoration estimate"),
    "RESTORATION_ROU": ("Ind AS 116.24(d), 25; Ind AS 37", "Estimated dismantling/restoration costs included in ROU when the obligation is incurred"),
    "LIAB_INITIAL": ("Ind AS 116.26", "Lease liability = PV of lease payments not paid at commencement, discounted at the implicit rate if readily determinable, otherwise the IBR"),
    "PAYMENTS": ("Ind AS 116.27–28", "Lease payments: fixed (less incentives receivable), index/rate-linked at commencement value, RVG amounts, purchase option if reasonably certain, termination penalties if term reflects termination"),
    "IN_SUBSTANCE": ("Ind AS 116.B42", "In-substance fixed payments are included as fixed payments"),
    "VARIABLE_EXCL": ("Ind AS 116.38(b)", "Variable payments not depending on an index or rate are recognised in profit or loss when incurred"),
    "ROU_SUBSEQ": ("Ind AS 116.29–30", "ROU measured at cost less accumulated depreciation and impairment, adjusted for remeasurements"),
    "DEPRECIATION": ("Ind AS 116.31–32", "Depreciate from commencement to the earlier of end of useful life and end of lease term; to end of useful life if ownership transfers or purchase option reasonably certain"),
    "IMPAIRMENT": ("Ind AS 116.33; Ind AS 36", "Apply Ind AS 36 to ROU assets"),
    "LIAB_SUBSEQ": ("Ind AS 116.36–38", "Liability increased by interest, reduced by payments, remeasured for reassessments/modifications; constant periodic rate"),
    "REMEASURE_ROU": ("Ind AS 116.39", "Remeasurement adjusts the ROU asset; any further reduction once ROU is nil goes to profit or loss"),
    "REVISED_RATE": ("Ind AS 116.40–41", "Revised discount rate for changes in lease term or purchase-option assessment"),
    "UNCHANGED_RATE": ("Ind AS 116.42–43", "Unchanged discount rate for RVG and index/rate changes, unless floating interest rates change"),
    "MOD_SEPARATE": ("Ind AS 116.44", "Modification is a separate lease if it adds the right to use additional assets at a price commensurate with stand-alone price"),
    "MOD_REMEASURE": ("Ind AS 116.45", "Other modifications: allocate consideration, determine term, remeasure liability at a revised rate at the effective date"),
    "MOD_ACCOUNTING": ("Ind AS 116.46", "Decrease in scope: reduce ROU for partial/full termination with gain/loss; other modifications: adjust ROU"),
    "PRESENTATION": ("Ind AS 116.47–50", "Present ROU and lease liabilities separately or disclose line items; interest separate from depreciation; cash-flow classification"),
    "CASHFLOW_INDAS": ("Ind AS 116.50; Appendix 1", "Ind AS: principal and interest portions of lease payments in financing activities; short-term, low-value and variable payments in operating activities"),
    "CASHFLOW_IFRS": ("IFRS 16.50; IAS 7", "IFRS: principal in financing; interest per the entity's IAS 7 policy for interest paid (subject to IFRS 18 from 2027)"),
    "DISCLOSURE_53": ("Ind AS 116.53–54", "Depreciation by class, interest, short-term, low-value and variable expense, sublease income, total cash outflow, additions, SLB gains/losses, carrying amount by class"),
    "MATURITY": ("Ind AS 116.58; Ind AS 107.39, B11", "Maturity analysis of lease liabilities (undiscounted contractual cash flows)"),
    "DISCLOSURE_59": ("Ind AS 116.59", "Additional qualitative/quantitative information: variable payments, options, RVG, leases not yet commenced, restrictions"),
    "DISCLOSURE_60": ("Ind AS 116.60", "Disclose that short-term / low-value exemptions are applied"),
    "LESSOR_CLASS": ("Ind AS 116.61–66", "Finance lease if substantially all risks and rewards incidental to ownership transfer; otherwise operating"),
    "LESSOR_FINANCE": ("Ind AS 116.67–80", "Recognise net investment; finance income at a constant periodic rate of return"),
    "LESSOR_OPERATING": ("Ind AS 116.81–88", "Operating lease income on a straight-line (or other systematic) basis"),
    "LESSOR_DISCLOSURE": ("Ind AS 116.89–97", "Lessor disclosures incl. maturity analysis of lease payments receivable"),
    "SUBLEASE": ("Ind AS 116.B58, 68", "Classify a sublease by reference to the ROU asset arising from the head lease"),
    "SLB": ("Ind AS 116.98–103", "Sale and leaseback: Ind AS 115 sale test; ROU at retained proportion of carrying amount; gain only on rights transferred; off-market adjustments"),
    "SLB_102A": ("Ind AS 116.102A, C1D, C20E", "Seller-lessee measures leaseback liability so that no gain/loss arises on the right of use retained (applicable from 1 April 2024)"),
    "DEPOSIT": ("Ind AS 109.5.1.1, B5.1.1", "Refundable deposit is a financial asset initially at fair value; difference from cash paid reflects another element (typically prepaid lease payment)"),
    "DEPOSIT_EIR": ("Ind AS 109.5.4.1", "Interest income by effective interest method on amortised cost"),
    "PROVISION": ("Ind AS 37.36–47, 60", "Best estimate discounted at a pre-tax rate; unwinding recognised as borrowing cost"),
    "DECOM_CHANGES": ("Ind AS 16 Appendix A (Changes in decommissioning, restoration and similar liabilities)", "Changes in estimate adjust the related asset under the cost model; deduction limited to carrying amount"),
    "FX_MONETARY": ("Ind AS 21.23(a), 28", "Monetary items (lease liability) retranslated at closing rate; exchange differences in profit or loss"),
    "FX_NONMONETARY": ("Ind AS 21.23(b)", "Non-monetary items at historical cost (ROU asset) remain at the transaction-date rate"),
    "DEFERRED_TAX": ("Ind AS 12.15, 24, 22A", "Deferred tax on ROU asset and lease liability; initial recognition exemption does not apply to equal taxable and deductible temporary differences (amendment effective 1 April 2023)"),
    "SCHEDULE_III": ("Schedule III (Division II) to the Companies Act, 2013", "Lease liabilities presented as separate line items under financial liabilities — current and non-current"),
    "FAIR_VALUE_IP": ("Ind AS 116 Appendix 1; Ind AS 40", "Fair value model for investment property not permitted under Ind AS 40 — ROU investment property at cost"),
}


def ref(key: str) -> str:
    r = REFS.get(key)
    return r[0] if r else key


def ref_text(key: str) -> str:
    r = REFS.get(key)
    return f"{r[0]} — {r[1]}" if r else key
