package com.example.core.model

enum class PartyRole(val label: String) {
    CUSTOMER("Customer"),
    SUPPLIER("Supplier"),
    EMPLOYEE("Staff"),
    LENDER("Lender"),
    BORROWER("Borrower"),
    OTHER("Other")
}

enum class TransactionType(val label: String, val isCreditToParty: Boolean) {
    GAVE("You Gave (Udhar / Sale)", true),                       // Customer owes more (+ balance / Debit)
    GOT("You Got (Payment / Receipt)", false),                   // Customer owes less (- balance / Credit)
    PURCHASE("Got Credit from Supplier (Purchase)", false),      // Business owes supplier more (- balance / Credit to Supplier)
    PAYMENT_TO_SUPPLIER("Paid to Supplier (Payment Made)", true),// Business owes supplier less (+ balance / Debit to Supplier)
    SALE("Sale Entry", true),                                    // Sale on credit (+ balance)
    EXPENSE("Business Expense", false),                          // Direct expense
    INCOME("Business Income", true),                             // Direct income
    TRANSFER("Account Transfer", false),                         // Transfer between internal accounts (Cash <-> Bank)
    OPENING_BALANCE("Opening Balance", true),
    ADJUSTMENT("Balance Adjustment", true)
}

enum class TransactionStatus {
    POSTED,
    VOIDED,
    REVERSED
}

enum class PaymentMode(val label: String) {
    CASH("Cash"),
    BANK_TRANSFER("Bank Transfer / NEFT / RTGS"),
    UPI("UPI / GPay / PhonePe / Paytm"),
    CHEQUE("Cheque"),
    CREDIT("On Credit / Udhar")
}

enum class AccountType(val label: String) {
    CASH("Cash in Hand"),
    BANK("Bank Account"),
    UPI("UPI Wallet"),
    OTHER("Other Account")
}

enum class AgeingBucket(val label: String) {
    CURRENT("0 - 30 Days"),
    DAYS_31_60("31 - 60 Days"),
    DAYS_61_90("61 - 90 Days"),
    OVER_90("90+ Days (Overdue)")
}

enum class PartyFilter(val label: String) {
    ALL("All Parties"),
    CUSTOMERS("Customers"),
    SUPPLIERS("Suppliers"),
    RECEIVABLE("You'll Receive (Lena)"),
    PAYABLE("You'll Pay (Dena)"),
    SETTLED("Settled (Zero Balance)"),
    ARCHIVED("Archived")
}

enum class ReportType(val label: String) {
    RECEIVABLES_AGEING("Receivables Ageing"),
    PAYABLES_AGEING("Payables Ageing"),
    DAYBOOK("Daily Daybook / Register"),
    CASHFLOW("Cash Flow (In/Out)"),
    EXPENSES("Category-wise Expenses"),
    ALL_TRANSACTIONS("All Transactions Register")
}
