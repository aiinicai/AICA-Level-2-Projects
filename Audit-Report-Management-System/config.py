from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent
TEMPLATE_DIR=BASE_DIR/"templates"
GENERATED_DIR=BASE_DIR/"generated"
DOCX_DIR=GENERATED_DIR/"docx"
DATABASE_DIR=BASE_DIR/"database"
REGISTER_PATH=DATABASE_DIR/"audit_reports.xlsx"
MASTER_PATH=DATABASE_DIR/"audit_master.xlsx"

TEMPLATE_RULES={
 ("private_ltd",False,"unmodified"):"AR_Private_Ltd_Co.docx",
 ("private_ltd",False,"qualified"):"AR_Private_Ltd_Co_Qualified.docx",
 ("private_ltd",True,"unmodified"):"AR_Private_Ltd_Small_Co.docx",
 ("private_ltd",True,"qualified"):"AR_Private_Ltd_Small_Co_Qualified.docx",
}
ENTITY_OPTIONS={"private_ltd":"Private Limited Company"}
OPINION_OPTIONS={"unmodified":"Unmodified Opinion","qualified":"Qualified Opinion"}

CANONICAL_VARIABLES=[
 ("CLIENT_NAME","Client legal name","Mandatory"),
 ("CIN","Corporate Identification Number","Mandatory"),
 ("CITY","Client city","Mandatory"),
 ("YEAR_ENDING","Financial year ending","Mandatory"),
 ("REPORT_DATE","Date of Auditor's Report","Mandatory"),
 ("UDIN","UDIN","Optional"),
 ("FIRM_NAME","CA Firm name","From Firm Master"),
 ("FRN","Firm Registration Number","From Firm Master"),
 ("PARTNER_NAME","Signing CA / Partner","From Partner Master"),
 ("MEMBERSHIP_NO","Partner Membership Number","From Partner Master"),
 ("PLACE","Place of signing","From Firm/Partner Master"),
]
PLACEHOLDER_ALIASES={
 "CLIENT_NAME":["{Name of Company}","{NAME OF COMPANY}"],
 "CIN":["{CIN}"],"CITY":["{City}"],"YEAR_ENDING":["{Year ending}"],
 "REPORT_DATE":["{Date of Report}"],"UDIN":["{UDIN}"],
 "FIRM_NAME":["{CA Firm Name}"],
 "PARTNER_NAME":["{Signing CA}"],
 "FRN":["{FRN}"],
 "MEMBERSHIP_NO":["{Membership No.}"],
 "PLACE":["{Place of Signing}"],
}
FIXED_SIGNATURE_ALIASES={
 "FIRM_NAME":["ABC & Co LLP"],
 "PARTNER_NAME":["CA ___________","CA ________________"],
 "MEMBERSHIP_NO":["Membership No.: 000000"],
 "FRN":["Firm Reg. no.: 000000W/W000000"],
 "PLACE":["Place:\tNashik","Place: \tNashik"],
}
REGISTER_HEADERS=[
 "ReportID","ClientID","EngagementID","ClientName","CIN","City","EntityType","SmallCompany","Opinion",
 "FinancialYear","YearEnding","TemplateName","TemplateVersion","PartnerName",
 "MembershipNo","FirmName","FRN","Place","ReportDate","UDIN","GeneratedAt",
 "Status","DOCXPath"
]
FIRM_HEADERS=["FirmID","FirmName","FRN","Address","DefaultPlace","Active"]
PARTNER_HEADERS=["PartnerID","FirmID","PartnerName","MembershipNo","DefaultPlace","Active"]
CLIENT_HEADERS=["ClientID","ClientName","CIN","PAN","City","Address","EntityType","SmallCompany","Active"]
ENGAGEMENT_HEADERS=["EngagementID","ClientID","FinancialYear","YearEnding","EntityType","SmallCompany","Opinion","FirmID","PartnerID","Place","Status","PreviousEngagementID","Notes"]
TEMPLATE_HEADERS=["TemplateID","FileName","EntityType","SmallCompany","Opinion","Version","EffectiveFrom","Status","Description"]
VARIABLE_HEADERS=["VariableCode","Description","Requirement","Aliases","Source","Active"]
WORDING_HEADERS=["WordingID","WordingCode","Title","ApplicableContext","StandardWording","Status","Version","Notes"]


# ---------------- Stage 5: Entity Classification & Applicability ----------------
# Corporate entity types are deliberately broader than the currently available
# Stage 3/4 Word templates. Applicability is independent of template availability.
ENTITY_FORM_OPTIONS = {
    "private_ltd": "Private Limited Company",
    "public_ltd_unlisted": "Unlisted Public Limited Company",
    "public_ltd_listed": "Listed Public Limited Company",
    "opc": "One Person Company (OPC)",
    "section8": "Section 8 Company",
    "producer_company": "Producer Company",
    "nidhi_company": "Nidhi Company",
    "government_company": "Government Company",
    "foreign_company": "Foreign Company",
    "other_company": "Other Company",
    "proprietorship": "Proprietorship",
    "partnership": "Partnership Firm",
    "llp": "Limited Liability Partnership (LLP)",
    "trust": "Trust / Society / Other Non-corporate",
    "other_noncorporate": "Other Non-corporate Entity",
}

CLASSIFICATION_HEADERS = [
    "EngagementID","AssessmentBasis","AssessmentDate","EntityForm",
    "Listed","InProcessListing","Bank","FinancialInstitution","Insurance",
    "Section8","OPC","SmallCompany","PrivateCompany","PublicCompany",
    "HoldingCompany","SubsidiaryCompany","HoldingSubsidiaryOfNonMSME","SpecialActEntity",
    "PaidUpCapital","ReservesSurplus","TurnoverPriorYear","RevenueCurrentYear",
    "BorrowingsMax","NetWorth","IndASRequired","AccountingFramework",
    "NonCompanyASCategory","LegacyLevel","CorporateSMCResult","CAROSystemResult","IFCSystemResult",
    "CashFlowSystemResult","ScheduleIIISystemResult","ProfessionalNotes",
    "UpdatedAt"
]

APPLICABILITY_HEADERS = [
    "EngagementID","RuleCode","Requirement","SystemResult","FinalResult",
    "Override","Rationale","Source","RuleVersion","UpdatedAt"
]

# Small company threshold changed by MCA notification G.S.R. 880(E), effective
# 1 December 2025. Keep the threshold effective-date driven rather than hard-coded.
SMALL_COMPANY_THRESHOLD_HISTORY = [
    ("2022-09-15","2025-11-30",4.0,40.0,"MCA G.S.R. 700(E)"),
    ("2025-12-01",None,10.0,100.0,"MCA G.S.R. 880(E)"),
]

# CARO 2020 private-company exemption thresholds are distinct from small-company
# thresholds and therefore are stored separately.
CARO_PRIVATE_THRESHOLD_PUC_RESERVES = 1.0
CARO_PRIVATE_THRESHOLD_BORROWINGS = 1.0
CARO_PRIVATE_THRESHOLD_REVENUE = 10.0
IFC_PRIVATE_TURNOVER_THRESHOLD = 50.0
IFC_PRIVATE_BORROWINGS_THRESHOLD = 25.0
