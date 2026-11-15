"""Industry profiles: they recommend KPIs and modules; they never force modules the data cannot support."""
PROFILES = [
    {"code": "trading", "label": "Trading", "modules": ["inventory", "products"],
     "kpis": ["revenue", "gross_margin_pct", "net_profit", "inventory_days", "receivable_days", "payable_days", "cash_conversion_cycle", "current_ratio"],
     "notes": ["Product margins, stock ageing and supplier concentration are the core analytics."]},
    {"code": "distribution", "label": "Distribution", "modules": ["inventory", "products", "cost_centres"],
     "kpis": ["revenue", "gross_margin_pct", "opex_ratio_pct", "inventory_days", "receivable_days", "cash_conversion_cycle", "overdue_receivables_pct", "interest_coverage"],
     "notes": ["Working capital (receivables + stock) typically drives cash needs."]},
    {"code": "wholesale", "label": "Wholesale", "modules": ["inventory", "products"],
     "kpis": ["revenue", "gross_margin_pct", "inventory_days", "receivable_days", "payable_days", "current_ratio", "debt_to_equity"],
     "notes": ["Volumes are high and margins thin: watch margin compression closely."]},
    {"code": "retail", "label": "Retail", "modules": ["inventory", "products", "cost_centres"],
     "kpis": ["revenue", "gross_margin_pct", "inventory_days", "opex_ratio_pct", "net_margin_pct", "cash_bank"],
     "notes": ["Store-wise analysis needs cost centres or godowns per store.", "Stock-outs can only be inferred where stock balances reach zero in the data."]},
    {"code": "manufacturing", "label": "Manufacturing", "modules": ["inventory", "products", "cost_centres"],
     "kpis": ["revenue", "gross_margin_pct", "ebitda_margin_pct", "inventory_days", "fixed_asset_turnover", "interest_coverage", "roce_pct"],
     "notes": ["Raw material / WIP / finished goods split needs stock groups mapped accordingly.",
               "Yield and variance analysis requires manufacturing journals with standard costs, which many Tally setups do not maintain."]},
    {"code": "services", "label": "Services", "modules": ["cost_centres"],
     "kpis": ["revenue", "ebitda_margin_pct", "net_margin_pct", "receivable_days", "overdue_receivables_pct", "revenue_per_employee", "cash_runway_months"],
     "notes": ["Inventory analytics are disabled unless stock is tracked.", "Revenue per employee needs the head count in company settings."]},
    {"code": "professional", "label": "Professional firm", "modules": ["cost_centres"],
     "kpis": ["revenue", "net_margin_pct", "receivable_days", "overdue_receivables_pct", "revenue_per_employee", "opex_ratio_pct"],
     "notes": ["Service lines / partners can be analysed through cost centres."]},
    {"code": "contracting", "label": "Contractors & projects", "modules": ["cost_centres", "projects"],
     "kpis": ["revenue", "gross_margin_pct", "receivable_days", "overdue_receivables_pct", "current_ratio", "debt_to_equity"],
     "notes": ["Project profitability uses cost centres as projects.", "Retention money and mobilisation advances should be mapped to separate ledgers to be visible."]},
    {"code": "other", "label": "Other", "modules": ["cost_centres"],
     "kpis": ["revenue", "gross_profit", "net_profit", "cash_bank", "current_ratio", "debt_to_equity"], "notes": []},
]


def profile_of(code: str) -> dict:
    return next((p for p in PROFILES if p["code"] == code), PROFILES[-1])
