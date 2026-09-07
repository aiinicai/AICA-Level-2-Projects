package com.example.data.model

enum class AssetCategory(val displayName: String) {
    BANK("Bank Account"),
    CASH("Cash"),
    FIXED_DEPOSIT("Fixed Deposit"),
    MUTUAL_FUNDS("Mutual Funds"),
    SHARES("Shares & Equity"),
    BONDS("Bonds"),
    PPF("PPF / Govt"),
    EPF("EPF / Gratuity"),
    NPS("NPS / Pension"),
    GOLD("Gold & Precious Metals"),
    REAL_ESTATE("Real Estate"),
    VEHICLES("Vehicles")
}

enum class LiabilityCategory(val displayName: String) {
    HOME_LOAN("Home Loan"),
    PERSONAL_LOAN("Personal Loan"),
    EDUCATION_LOAN("Education Loan"),
    VEHICLE_LOAN("Vehicle Loan"),
    CREDIT_CARD("Credit Card Outstanding")
}

enum class TransactionType {
    INCOME, EXPENSE
}

enum class ExpenseCategory(val displayName: String) {
    HOUSEHOLD("Household & Living"),
    EDUCATION("Education"),
    HEALTHCARE("Healthcare"),
    TRAVEL("Travel & Commute"),
    UTILITIES("Utilities & Bills"),
    EMI("Loan EMI"),
    INSURANCE("Insurance Premium"),
    INVESTMENTS("Investments & SIP"),
    ENTERTAINMENT("Lifestyle & Dining")
}

enum class IncomeCategory(val displayName: String) {
    SALARY("Salary"),
    BUSINESS("Business Income"),
    RENTAL("Rental Income"),
    INTEREST("Interest & Dividends"),
    OTHER("Other Income")
}

enum class RiskProfile(val displayName: String) {
    CONSERVATIVE("Conservative (Capital Preservation)"),
    MODERATE("Moderate (Balanced Growth)"),
    AGGRESSIVE("Aggressive (Wealth Maximization)")
}

enum class GoalCategory(val displayName: String) {
    HOUSE("House Purchase"),
    RETIREMENT("Retirement"),
    EDUCATION("Child Education"),
    VACATION("Dream Vacation"),
    WEALTH("Wealth Creation")
}

enum class InsuranceType(val displayName: String) {
    TERM_LIFE("Term Life Insurance"),
    HEALTH("Health Insurance"),
    ACCIDENT("Personal Accident & Critical Illness")
}

enum class ReminderType(val displayName: String) {
    SIP_DUE("SIP Due"),
    EMI_DUE("EMI Due"),
    INSURANCE_RENEWAL("Insurance Renewal"),
    GOAL_REVIEW("Goal Review"),
    BUDGET_ALERT("Budget Alert"),
    TAX_DEADLINE("Advance Tax & ITR")
}
