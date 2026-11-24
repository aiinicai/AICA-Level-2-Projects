STATUSES = ["To Do", "In Progress", "Under Review", "Done"]
CATEGORIES = ["GST", "Income Tax", "TDS", "Audit", "Other"]
DOC_CATEGORIES = ["KYC", "GST", "Income Tax", "TDS", "Audit", "Bank statements", "Financials", "Other"]
ENTITY_TYPES = ["Individual", "HUF", "Proprietorship", "Partnership Firm", "LLP", "Company", "Trust / Society", "AOP / BOI"]
PRIORITIES = ["High", "Medium", "Low"]
GST_FREQ = ["None", "Monthly", "Quarterly"]

# QRMP GSTR-3B: 22nd for these states/UTs ...
QRMP_22 = ["Chhattisgarh", "Madhya Pradesh", "Gujarat", "Maharashtra", "Karnataka", "Goa", "Kerala",
           "Tamil Nadu", "Telangana", "Andhra Pradesh", "Dadra and Nagar Haveli and Daman and Diu",
           "Puducherry", "Andaman and Nicobar Islands", "Lakshadweep"]
# ... and 24th for these
QRMP_24 = ["Himachal Pradesh", "Punjab", "Uttarakhand", "Haryana", "Rajasthan", "Uttar Pradesh", "Bihar",
           "Sikkim", "Arunachal Pradesh", "Nagaland", "Manipur", "Mizoram", "Tripura", "Meghalaya", "Assam",
           "West Bengal", "Jharkhand", "Odisha", "Jammu and Kashmir", "Ladakh", "Chandigarh", "Delhi"]
STATES = sorted(QRMP_22 + QRMP_24)

STATUS_TONE = {"To Do": "slate", "In Progress": "blue", "Under Review": "amber", "Done": "green"}
CATEGORY_TONE = {"GST": "teal", "Income Tax": "indigo", "TDS": "violet", "Audit": "rose", "Other": "slate"}
