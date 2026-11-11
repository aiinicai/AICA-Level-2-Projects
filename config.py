"""Default company profile and Kenyan statutory rates.

All rates are stored in the database on first run and can be edited from
Settings > Statutory Rates without touching code. Verify against KRA / NSSF /
SHA gazette notices whenever the Finance Act or a Legal Notice changes them.
"""

APP_NAME = "Lordship Africa Payroll"
APP_VERSION = "1.0.0"

DEFAULT_COMPANY = {
    "name": "Lordship Africa",
    "kra_pin": "",
    "nssf_no": "",
    "shif_no": "",
    "nita_no": "",
    "address": "Nairobi, Kenya",
    "phone": "",
    "email": "",
    "bank_name": "",
    "bank_account": "",
}

DEFAULT_RATES = {
    "rates_version": "Kenya 2026 (Finance Act 2023 bands, TLAA 2024, NSSF Year 4)",

    # PAYE monthly bands: [upper limit of band in KES (null = no limit), rate]
    "paye_bands": [
        [24000, 0.10],
        [32333, 0.25],
        [500000, 0.30],
        [800000, 0.325],
        [None, 0.35],
    ],
    "personal_relief": 2400.0,
    # Insurance relief: 15% of life/education/health premiums, capped monthly
    "insurance_relief_rate": 0.15,
    "insurance_relief_cap": 5000.0,
    # Secondary employment: no personal relief, flat top rate
    "secondary_employment_rate": 0.35,
    # Consultants / professional fees (resident) withholding tax
    "consultant_wht_rate": 0.05,

    # Allowable deductions before PAYE (Tax Laws (Amendment) Act 2024)
    "pension_deduction_cap": 30000.0,      # NSSF + registered pension, per month
    "mortgage_interest_cap": 30000.0,      # owner-occupied interest, per month
    "prmf_cap": 15000.0,                   # post-retirement medical fund, per month
    "disability_exemption": 150000.0,      # monthly exemption with KRA certificate
    "non_cash_benefit_threshold": 5000.0,  # non-cash benefits at/below this are exempt

    # Social Health Insurance Fund (replaced NHIF from 1 Oct 2024)
    "shif_rate": 0.0275,
    "shif_minimum": 300.0,

    # Affordable Housing Levy - employee and employer each
    "ahl_rate": 0.015,

    # NSSF Act 2013 - employee and employer each contribute this rate
    "nssf_rate": 0.06,
    "nssf_schedule": [
        {"effective": "2024-02-01", "lel": 7000, "uel": 36000},
        {"effective": "2025-02-01", "lel": 8000, "uel": 72000},
        {"effective": "2026-02-01", "lel": 9000, "uel": 108000},
    ],

    # NITA industrial training levy, employer only, per employee per month
    "nita_levy": 50.0,

    # Employment Act / Regulation of Wages
    "overtime_normal_multiplier": 1.5,
    "overtime_holiday_multiplier": 2.0,
    "standard_monthly_hours": 225.0,       # 52-hour week
    "days_per_month_for_absence": 30.0,
    "minimum_wage": 16113.75,              # Nairobi general labourer - verify latest Wage Order
    "max_deductions_fraction": 0.6667,     # Employment Act s.19(3): deductions <= 2/3 of wages
}

RATE_HELP = {
    "paye_bands": "Monthly PAYE bands as [upper limit, rate]. Use null for the top band.",
    "nssf_schedule": "NSSF Lower/Upper Earnings Limits by effective date (YYYY-MM-DD).",
    "minimum_wage": "Used only for warnings. Check the current Regulation of Wages Order.",
}

EMPLOYMENT_TYPES = ["Primary", "Secondary", "Consultant (WHT)"]
PAYMENT_MODES = ["Bank", "M-Pesa", "Cheque", "Cash"]
DEDUCTION_KINDS = ["Loan", "Salary Advance", "SACCO", "HELB", "Welfare", "Union Dues", "Other"]
