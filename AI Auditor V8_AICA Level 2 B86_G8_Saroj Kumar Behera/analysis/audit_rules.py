"""
AI Auditor V8 - Chartered Accountant Audit Rules & Knowledge Base
Deterministic expert audit intelligence containing:
- Possible Non-Conclusive Reasons
- Audit Verification Document Requirements with 'WHY' justification
- Potential Risk & Attention Area Classification
"""

from typing import Dict, List, Any, Optional

AUDIT_RULES_KNOWLEDGE_BASE = {
    "revenue_operations": {
        "increase": {
            "possible_reasons": [
                "Expansion of business operations, customer base, or geographic territories.",
                "Increase in sales volume or units dispatched.",
                "Upward revision in selling prices or product pricing realization.",
                "Favorable change in product / sales mix towards higher-margin items.",
                "Recognition of deferred or unbilled revenue in the current period.",
                "Possible aggressive revenue recognition near period-end (e.g., channel stuffing or early cutoff)."
            ],
            "audit_verification": [
                {"doc": "Sales Register & Monthly GST (GSTR-1 / GSTR-3B) Reconciliation", "why": "To verify that recorded revenue reconciles strictly with statutory tax returns and outward supply ledgers."},
                {"doc": "Customer Contracts, Purchase Orders & Sales Invoices", "why": "To verify authorization, pricing terms, delivery milestones, and correct revenue recognition under Ind AS 115 / AS 9."},
                {"doc": "Goods Outward / Delivery Challans / Transporter LRs", "why": "To corroborate actual physical dispatch of goods and transfer of risks and rewards prior to period end."},
                {"doc": "Cut-off Testing Documentation (5 days before & after year-end)", "why": "To ensure sales and returns are recorded in the appropriate accounting period and avoid early cutoff inflation."},
                {"doc": "Subsequent Period Credit Notes & Sales Returns Register", "why": "To verify whether significant sales booked before year-end were reversed post balance sheet date."}
            ],
            "risk_level": "Medium",
            "risk_note": "Significant revenue surge requires cut-off verification and reconciliation with GST & e-way bills."
        },
        "decrease": {
            "possible_reasons": [
                "General economic downturn, industry slowdown, or reduced demand for core products.",
                "Loss of key customer accounts or loss of competitive market share.",
                "Downward pressure on unit selling prices or discounting to clear obsolete stock.",
                "Supply chain bottlenecks or raw material shortages curtailing output.",
                "Discontinuation of specific unprofitable business lines or product segments."
            ],
            "audit_verification": [
                {"doc": "Customer-wise / Segment-wise Sales Comparative Analysis", "why": "To isolate which specific product lines, customers, or branches experienced the decline."},
                {"doc": "Capacity Utilization Reports & Production Logs", "why": "To ascertain whether the decline was driven by operational shutdowns or lack of customer orders."},
                {"doc": "Customer Correspondence & Contract Cancellation Files", "why": "To document valid business reasons for loss of major accounts."},
                {"doc": "Management Commentary & Industry Benchmark Reports", "why": "To evaluate going concern assumptions and viability of future revenue streams."}
            ],
            "risk_level": "High",
            "risk_note": "Persistent revenue decline may impair fixed assets and jeopardize going-concern viability."
        }
    },
    "trade_receivables": {
        "increase": {
            "possible_reasons": [
                "Growth in credit sales volume during the latter part of the financial year.",
                "Relaxation or extension of customer credit terms to drive revenue.",
                "Slower collection cycles or liquidity distress among key customers.",
                "Concentration of unpaid balances among a few major debtors.",
                "Accumulation of disputed, overdue, or potentially doubtful debts without adequate provisioning."
            ],
            "audit_verification": [
                {"doc": "Debtors Ageing Schedule (> 6 months vs < 6 months, disputed vs undisputed)", "why": "To evaluate debt quality, recoverability, and adequacy of Expected Credit Loss (ECL) / bad debt provision."},
                {"doc": "Direct External Balance Confirmations (SA 505)", "why": "To obtain independent third-party confirmation of balances from top customers."},
                {"doc": "Subsequent Realisation / Bank Statements after Year-End", "why": "To confirm whether outstanding receivables were actually collected in cash post balance sheet date."},
                {"doc": "Credit Approval Files & Customer Limits", "why": "To ensure receivables were extended within authorized credit limits."},
                {"doc": "Litigation & Dispute Files for Overdue Balances", "why": "To assess need for specific provisioning on contested balances."}
            ],
            "risk_level": "High",
            "risk_note": "Rapid growth in debtors exceeding sales growth indicates potential working capital lockup and recovery risk."
        },
        "decrease": {
            "possible_reasons": [
                "Aggressive cash collection drives and disciplined credit control.",
                "Shift in business model towards cash sales, advances, or shorter credit cycles.",
                "Factoring or discounting of trade bills without recourse.",
                "Significant write-off of unrecoverable or bad debts during the year."
            ],
            "audit_verification": [
                {"doc": "Bad Debts Written Off Ledger & Board Approvals", "why": "To verify that write-offs are genuine, legally authorized, and not masking unrecorded cash collections."},
                {"doc": "Bank Statements & Daily Collection Summaries", "why": "To corroborate actual cash inflow receipts."},
                {"doc": "Bill Discounting Agreements & Bank Sanction Letters", "why": "To ensure factored debts are appropriately derecognized and contingent liabilities disclosed."}
            ],
            "risk_level": "Low",
            "risk_note": "Ensure debtor reductions represent actual collections rather than unapproved bad debt write-offs."
        }
    },
    "inventories": {
        "increase": {
            "possible_reasons": [
                "Strategic procurement / stockpiling ahead of anticipated raw material price surges or shortages.",
                "Unanticipated drop in sales demand leading to finished goods accumulation.",
                "Production bottlenecks or incomplete batches accumulating in Work-in-Progress (WIP).",
                "Accumulation of obsolete, slow-moving, or damaged stock.",
                "Change in inventory valuation methodology or overhead absorption rates."
            ],
            "audit_verification": [
                {"doc": "Physical Inventory Verification Report & Auditor Attendance Sheets", "why": "To confirm physical existence, condition, and count accuracy at year-end (SA 501)."},
                {"doc": "Inventory Valuation Working Sheets (Lower of Cost and Net Realizable Value - AS 2 / Ind AS 2)", "why": "To test mathematical accuracy and verify that carrying value does not exceed market net realizable value."},
                {"doc": "Slow-Moving, Non-Moving, and Obsolete Stock Analysis (> 180 / 365 days)", "why": "To verify adequacy of provision for inventory obsolescence."},
                {"doc": "Purchase Invoices & Bill of Entry (Imports)", "why": "To verify landing costs, freight, and custom duties included in raw material valuation."},
                {"doc": "Cost Accounting Records & Overhead Absorption Model", "why": "To ensure overhead allocation to WIP and Finished Goods reflects normal operating capacity."}
            ],
            "risk_level": "High",
            "risk_note": "Stock accumulation ties up liquidity and increases inventory holding costs and obsolescence risk."
        },
        "decrease": {
            "possible_reasons": [
                "Improved supply chain efficiency and implementation of Just-in-Time (JIT) replenishment.",
                "Heavy clearance of old inventory stock through discounts or promotions.",
                "Disruptions in vendor deliveries or shortage of working capital to purchase supplies.",
                "Higher sales volume outstripping replenishment rate."
            ],
            "audit_verification": [
                {"doc": "Year-end Stock Count Sheets & Discrepancy Adjustments", "why": "To verify that stock reduction is not due to unrecorded stock losses or inventory shrinkage."},
                {"doc": "Subsequent Purchase Orders & Raw Material Consumption Logs", "why": "To verify production continuity without risk of stock-outs."},
                {"doc": "Scrap / Wastage Disposal Records", "why": "To verify authorization and recovery of scrap proceeds."}
            ],
            "risk_level": "Medium",
            "risk_note": "Verify inventory reduction is operational and not masking unrecorded stock shortages or shrinkage."
        }
    },
    "long_term_borrowings": {
        "increase": {
            "possible_reasons": [
                "Availment of new term loans or debt instruments to fund capital expenditure (CapEx) / plant expansion.",
                "Restructuring or refinancing of high-cost short-term obligations into long-term facilities.",
                "Funding long-term strategic investments, acquisitions, or debt servicing.",
                "Issuance of debentures or external commercial borrowings (ECBs)."
            ],
            "audit_verification": [
                {"doc": "Loan Sanction Letters, Loan Agreements & Board Resolutions", "why": "To verify borrowing terms, interest rate covenants, tenure, and borrowing authority under Sec 180 of Companies Act."},
                {"doc": "Direct Bank / Lender Balance Confirmations (SA 505)", "why": "To confirm outstanding principal, accrued interest, and compliance with financial covenants."},
                {"doc": "Charge Creation / ROC Form CHG-1 & Register of Charges", "why": "To verify that hypothecation / mortgage of company assets is duly registered with ROC."},
                {"doc": "End-Use of Funds Certificate & Bank Statement Tracing", "why": "To ensure borrowed funds were utilized strictly for sanctioned capital purposes and not diverted."}
            ],
            "risk_level": "High",
            "risk_note": "Increased leverage raises fixed financial debt burden and interest commitment."
        },
        "decrease": {
            "possible_reasons": [
                "Scheduled contractual repayment of term loan installments.",
                "Early prepayment or redemption of debt out of operating cash surpluses or equity infusions.",
                "Debt reclassification from long-term to current maturities of long-term debt."
            ],
            "audit_verification": [
                {"doc": "Bank Repayment Vouchers, Bank Statements & NOC / Satisfaction of Charge (CHG-4)", "why": "To confirm full repayment and release of legal charges on pledged assets."},
                {"doc": "Current Maturities Reclassification Schedule", "why": "To ensure portions due within 12 months are properly presented under Current Liabilities."}
            ],
            "risk_level": "Low",
            "risk_note": "Ensure current maturities falling due within 12 months are correctly classified."
        }
    },
    "short_term_borrowings": {
        "increase": {
            "possible_reasons": [
                "Higher utilization of Cash Credit (CC) / Overdraft (OD) limits due to working capital expansion.",
                "Slower cash recovery from debtors necessitating short-term bridge financing.",
                "Funding seasonal inventory buildup before peak demand periods.",
                "Issuance of commercial paper or short-term unsecured inter-corporate deposits."
            ],
            "audit_verification": [
                {"doc": "Bank Overdraft / CC Sanction Letters & Limit Renewal Documents", "why": "To verify sanctioned limit, interest rates, margin requirements, and validity of drawing power."},
                {"doc": "Monthly Stock & Book Debt Statements submitted to Banks", "why": "To reconcile stock and debtor values reported to lending banks against books of accounts."},
                {"doc": "Drawing Power (DP) Calculation Sheets & Bank Statements", "why": "To ensure borrowings remained within sanctioned drawing power without penal interest."},
                {"doc": "Bank Confirmation Letters", "why": "To confirm end-of-year overdraft balances, interest charges, and unpaid dues."}
            ],
            "risk_level": "High",
            "risk_note": "High short-term bank borrowings indicate reliance on credit limits for everyday operations."
        },
        "decrease": {
            "possible_reasons": [
                "Repayment of short-term facilities from internal operational cash flows.",
                "Infusion of equity or long-term debt replacing short-term facilities.",
                "Reduction in working capital requirements."
            ],
            "audit_verification": [
                {"doc": "Bank Statements & Closure Letters", "why": "To verify authentic settlement of credit facilities."},
                {"doc": "Reconciliation of Bank Accounts", "why": "To ensure no unrecorded overdraft liability or outstanding cheques."}
            ],
            "risk_level": "Low",
            "risk_note": "Confirm debt reduction was settled via genuine funds rather than rollover into trade payables."
        }
    },
    "property_plant_equipment": {
        "increase": {
            "possible_reasons": [
                "Acquisition of new plant, machinery, land, building, or technological equipment.",
                "Capitalization of ongoing Capital Work-in-Progress (CWIP) projects upon commissioning.",
                "Upward revaluation of tangible fixed assets as per applicable accounting standards.",
                "Inclusion of right-of-use (ROU) assets under Ind AS 116 lease accounting."
            ],
            "audit_verification": [
                {"doc": "Fixed Asset Register (FAR) & Asset Capitalization Vouchers", "why": "To confirm quantitative details, cost components, installation date, and asset location."},
                {"doc": "Vendor Invoices, Purchase Orders & Installation Certificates", "why": "To verify cost elements and ensure operational readiness before capitalization."},
                {"doc": "Physical Verification of Fixed Assets Report", "why": "To confirm physical existence, condition, and reconciliation with FAR."},
                {"doc": "Title Deeds / Sale Deeds / Municipal Tax Receipts", "why": "To verify legal title and ownership of immovable properties."},
                {"doc": "Depreciation Working Sheets", "why": "To verify calculation as per useful lives prescribed in Schedule II of Companies Act, 2013."}
            ],
            "risk_level": "Medium",
            "risk_note": "Verify that revenue repairs and maintenance are not wrongly capitalized to inflate assets."
        },
        "decrease": {
            "possible_reasons": [
                "Annual depreciation and amortisation charges.",
                "Sale, transfer, or retirement of plant and machinery.",
                "Scrapping of damaged or obsolete fixed assets.",
                "Impairment loss recognition under Ind AS 36 / AS 28."
            ],
            "audit_verification": [
                {"doc": "Fixed Asset Disposal Register, Invoices & Board Approvals", "why": "To verify authorization, sale consideration, and calculation of profit/loss on disposal."},
                {"doc": "Bank Statements Tracing Sale Consideration", "why": "To confirm receipt of disposal proceeds."},
                {"doc": "Impairment Assessment Working", "why": "To evaluate recoverable amount calculation and impairment testing assumptions."}
            ],
            "risk_level": "Medium",
            "risk_note": "Verify profit or loss on disposal and removal of asset from gross block and accumulated depreciation."
        }
    },
    "trade_payables": {
        "increase": {
            "possible_reasons": [
                "Higher procurement volume of raw materials / merchandise in line with business expansion.",
                "Negotiation of more favorable / extended credit terms with suppliers.",
                "Delayed vendor payments due to tight working capital or dispute.",
                "Accumulation of MSME dues requiring statutory interest disclosure."
            ],
            "audit_verification": [
                {"doc": "Trade Payables Ageing Schedule & MSME Classification Breakdown", "why": "To verify overdue payables, vendor ageing, and compliance with Section 16 of MSMED Act (interest on delayed payments)."},
                {"doc": "Direct Vendor Balance Confirmations (SA 505)", "why": "To obtain independent confirmation of balances from top raw material suppliers."},
                {"doc": "Vendor Statement Reconciliations (Books vs Supplier Ledger)", "why": "To identify unrecorded purchase invoices, disputed debit notes, or timing differences."},
                {"doc": "Subsequent Period Payments & Bank Clearance", "why": "To confirm genuine settlement of payables post year-end."}
            ],
            "risk_level": "Medium",
            "risk_note": "Dues to MSME vendors exceeding 45 days attract mandatory compound interest and disclosure under Schedule III."
        },
        "decrease": {
            "possible_reasons": [
                "Faster payment turnaround to secure early-payment cash discounts.",
                "Reduction in raw material purchases due to production cutbacks.",
                "Settlement of past outstanding vendor dues out of debt or cash surpluses."
            ],
            "audit_verification": [
                {"doc": "Vendor Payment Vouchers & Bank Statements", "why": "To verify that payments were made to authorized vendor bank accounts."},
                {"doc": "Purchase Cut-Off Testing", "why": "To ensure unbilled purchases received prior to year-end are not omitted from liabilities."}
            ],
            "risk_level": "Low",
            "risk_note": "Perform search for unrecorded liabilities to ensure goods received before year-end are fully accounted."
        }
    },
    "employee_benefits": {
        "increase": {
            "possible_reasons": [
                "Increase in employee headcount to support business growth.",
                "Annual wage increments, salary revisions, bonuses, or incentives.",
                "Higher provision for employee retirement benefits (gratuity, leave encashment) based on actuarial valuation.",
                "Statutory minimum wage revisions or overtime payments."
            ],
            "audit_verification": [
                {"doc": "Monthly Payroll Sheets, Salary Registers & Bank Transfer Schedules", "why": "To verify net salary disbursements against authorized payroll."},
                {"doc": "Statutory PF, ESI, and Professional Tax Challans & Monthly Returns (ECR)", "why": "To verify statutory deduction compliance, timely deposit, and reconciliation with books."},
                {"doc": "Actuarial Valuation Report for Gratuity & Leave Encashment (Ind AS 19 / AS 15)", "why": "To verify actuarial assumptions (discount rate, salary escalation) and balance sheet provisioning."},
                {"doc": "Directors' Remuneration Approvals & Board / AGM Resolutions", "why": "To verify compliance with Section 197 / Schedule V limits of Companies Act, 2013."}
            ],
            "risk_level": "Medium",
            "risk_note": "Ensure non-deposit of PF/ESI within due dates is flagged under Tax Audit Form 3CD."
        },
        "decrease": {
            "possible_reasons": [
                "Reduction in workforce headcount, downsizing, or rationalization.",
                "Reduction in performance bonuses or incentives due to lower profits.",
                "Outsourcing of operational manpower to third-party contractors (shifted to other expenses)."
            ],
            "audit_verification": [
                {"doc": "Headcount Reconciliation & HR Resignation / Termination Logs", "why": "To corroborate reduction in staff numbers against payroll reductions."},
                {"doc": "Contract Labor Ledgers", "why": "To verify if employee costs were reclassified to subcontract charges."}
            ],
            "risk_level": "Low",
            "risk_note": "Verify full and final settlement computation for exited personnel."
        }
    },
    "finance_costs": {
        "increase": {
            "possible_reasons": [
                "Increase in total debt portfolio (term loans, working capital overdrafts).",
                "Upward revision in benchmark lending interest rates (e.g. RBI Repo Rate / SOFR).",
                "Payment of penal interest, loan processing fees, or bank guarantee commission charges.",
                "Cessation of interest capitalization upon commissioning of capital projects."
            ],
            "audit_verification": [
                {"doc": "Bank Interest Computation Sheets & Loan Amortization Schedules", "why": "To recalculate and verify interest charges independently against applied interest rates."},
                {"doc": "Bank Statements & Debit Advices", "why": "To verify actual interest debited by lenders."},
                {"doc": "Interest Capitalization Workings (Ind AS 23 / AS 16)", "why": "To verify eligible borrowing costs capitalized to qualifying assets and amounts expensed in P&L."},
                {"doc": "TDS Returns (Form 26Q) on Interest Payments (Sec 194A / 195)", "why": "To ensure tax is duly deducted at source on non-bank interest."}
            ],
            "risk_level": "High",
            "risk_note": "Rising interest expense lowers debt coverage ratios and restricts free cash flow."
        },
        "decrease": {
            "possible_reasons": [
                "Reduction in outstanding borrowings through debt retirement.",
                "Negotiation of lower interest rate spreads with lenders.",
                "Higher capitalization of borrowing costs to ongoing CWIP assets."
            ],
            "audit_verification": [
                {"doc": "Debt Repayment Tracing & Rate Revision Letters", "why": "To verify that interest savings correspond to debt reduction or approved rate cuts."},
                {"doc": "Borrowing Cost Capitalization Schedule", "why": "To ensure interest is not aggressively capitalized to hide operational financing costs."}
            ],
            "risk_level": "Medium",
            "risk_note": "Verify interest capitalization complies strictly with qualifying asset definitions."
        }
    },
    "other_expenses": {
        "increase": {
            "possible_reasons": [
                "Increase in scale of business operations driving proportional administrative and selling overheads.",
                "Escalation in utility, fuel, rent, legal, or freight costs.",
                "One-off or non-recurring expenses such as major repairs, consulting fees, or litigation costs.",
                "Write-off of old advances, bad debts, or provisions for contingencies."
            ],
            "audit_verification": [
                {"doc": "Detailed General Ledger for Major Expense Heads", "why": "To review underlying transaction details and identify abnormal or non-business items."},
                {"doc": "Vendor Invoices, Service Agreements & Approval Notes", "why": "To verify authorization, business purpose, and compliance with internal delegation of powers."},
                {"doc": "TDS Compliance Matrix & Challans (Form 26Q)", "why": "To check compliance with withholding tax provisions (Sec 194C, 194J, 194I) to prevent 30% disallowance under Sec 40(a)(ia)."},
                {"doc": "Related Party Expense Workings (Sec 188 / AS 18)", "why": "To verify that transactions with related parties are at arm's length and approved by Audit Committee."}
            ],
            "risk_level": "Medium",
            "risk_note": "Scrutinize high legal & professional fees and miscellaneous write-offs for potential tax disallowances."
        },
        "decrease": {
            "possible_reasons": [
                "Strict cost-rationalization and overhead curtailment measures.",
                "Absence of one-off non-recurring expenses incurred in the previous year.",
                "Deferral of discretionary administrative or marketing expenditures."
            ],
            "audit_verification": [
                {"doc": "Expense Ledger Scrutiny & Outstanding Expense Provisions", "why": "To verify that all accrued expenses for the year are fully provided for and not omitted."},
                {"doc": "Subsequent Period Expense Ledger Scrutiny", "why": "To ensure expenses pertaining to the current year were not postponed to the next financial period."}
            ],
            "risk_level": "Medium",
            "risk_note": "Perform search for unrecorded expenses and verify completeness of year-end accruals."
        }
    }
}

class AuditRulesEngine:
    
    @classmethod
    def get_rules_for_item(cls, standard_key: Optional[str], is_increase: bool) -> Dict[str, Any]:
        """Retrieves CA possible reasons and audit verification guidelines for a line item movement."""
        direction = "increase" if is_increase else "decrease"
        
        if standard_key and standard_key in AUDIT_RULES_KNOWLEDGE_BASE:
            data = AUDIT_RULES_KNOWLEDGE_BASE[standard_key].get(direction)
            if data:
                return data

        # Generic fallback rules
        if is_increase:
            return {
                "possible_reasons": [
                    "Expansion or increase in operational volume during the current accounting period.",
                    "General inflationary price adjustments or revised vendor/customer terms.",
                    "Reclassification or inclusion of additional sub-accounts.",
                    "Change in accounting estimation or timing of recognition."
                ],
                "audit_verification": [
                    {"doc": "Detailed General Ledger Extract & Sub-Ledger Schedules", "why": "To inspect transaction-level entries and verify mathematical aggregation."},
                    {"doc": "Primary Invoices, Vouchers & Supporting Documents", "why": "To verify transaction authenticity, authorization, and business purpose."},
                    {"doc": "Management Representation Letter & Explanatory Working Notes", "why": "To document management rationale for the significant variance."}
                ],
                "risk_level": "Low",
                "risk_note": "Review line item ledger for unusual spikes or round-sum entries."
            }
        else:
            return {
                "possible_reasons": [
                    "Reduction in operational activity or downsizing in the respective area.",
                    "Cost rationalization or settlement/utilization of balance.",
                    "Accounting reclassification to other heads of accounts.",
                    "Omission of period-end accruals or adjustments."
                ],
                "audit_verification": [
                    {"doc": "Detailed General Ledger Extract & Prior Period Comparative", "why": "To identify specific sub-items that caused the reduction."},
                    {"doc": "Period-end Accrual & Provision Working Sheets", "why": "To verify that all legitimate liabilities and expenses are fully accounted."},
                    {"doc": "Management Representation Letter", "why": "To obtain written confirmation of completeness and accuracy."}
                ],
                "risk_level": "Low",
                "risk_note": "Ensure completeness and verify that expenses or liabilities have not been understated."
            }
