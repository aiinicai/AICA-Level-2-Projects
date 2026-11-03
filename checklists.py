"""
BOI Account Opening Audit & Document Scrutiny System
Checklist Definitions for Saving and Current Accounts
"""

SAVING_ACCOUNT_CHECKS = [
    {
        "id": "SB_CHK_01",
        "title": "Aadhaar Card Verification",
        "category": "Customer Identification (OVD)",
        "description": "Masked synthetic Aadhaar copy with first 8 digits hidden. Online UIDAI QR/XML verification or biometric verification status verified with demographic details match.",
        "guideline": "RBI KYC Master Direction § 16. Masked Aadhaar must be collected. First 8 digits must be redacted/masked.",
        "severity": "High",
        "default_pass_criteria": "Aadhaar copy is properly masked; name, DoB, and address match Account Opening Form exactly."
    },
    {
        "id": "SB_CHK_02",
        "title": "PAN Card / Finacle Verification",
        "category": "Tax & Regulatory Identification",
        "description": "Verification of PAN card copy against NSDL/ITD portal or Finacle PAN validation flag. If PAN is unavailable, valid Form 60 with agricultural/non-taxable income declaration.",
        "guideline": "Income Tax Rule 114B & Finacle PAN Validation norms. Form 60 must be properly witnessed.",
        "severity": "High",
        "default_pass_criteria": "Valid PAN linked in Finacle and verified against ITD database or complete Form 60 with declaration."
    },
    {
        "id": "SB_CHK_03",
        "title": "CKYC Record Status",
        "category": "Central KYC Registry",
        "description": "14-digit CKYC Identifier search or upload confirmation in CKYCR portal. Verification of KYC identifier match with customer master.",
        "guideline": "PMLA (Maintenance of Records) Rules § 9(1A). CKYC identifier must be linked within 3 days of account opening.",
        "severity": "Medium",
        "default_pass_criteria": "CKYC search performed; 14-digit CKYC number generated or existing CKYC matched with verified status."
    },
    {
        "id": "SB_CHK_04",
        "title": "Customer Photograph",
        "category": "Biometric & Visual Verification",
        "description": "Recent colored passport-size photograph affixed on AOF and cross-signed by the applicant or captured live via BOI DigiKYC portal.",
        "guideline": "BOI SOP on Account Opening § 4.2. Clear face visibility; photo must not be faded or mutilated.",
        "severity": "Medium",
        "default_pass_criteria": "Recent clear passport-size photo affixed, cross-signed by customer, and matches identity documents."
    },
    {
        "id": "SB_CHK_05",
        "title": "Officer Signature with PF Number",
        "category": "Branch Scrutiny & Accountability",
        "description": "Verifying officer's signature, full name, designation, branch code, and 6-digit Provident Fund (PF) Employee Number on all KYC copies and AOF.",
        "guideline": "BOI Internal Audit Norms. Every KYC document must bear OSV (Original Seen & Verified) stamp with PF Number.",
        "severity": "High",
        "default_pass_criteria": "OSV stamp affixed on all OVD copies with Branch Official's signature, name stamp, and valid PF Number."
    },
    {
        "id": "SB_CHK_06",
        "title": "Customer Profile Sheet (CPS)",
        "category": "AML Risk Profiling",
        "description": "Customer Profile Sheet completely filled including Occupation, Annual Income, Source of Funds, Expected Annual Turnover, and AML Risk Categorization (Low/Medium/High).",
        "guideline": "RBI Master Direction on KYC § 22. Risk categorization must be assigned based on occupation and turnover.",
        "severity": "Medium",
        "default_pass_criteria": "CPS filled completely, risk categorized (Low/Medium/High) with clear source of funds indicated."
    },
    {
        "id": "SB_CHK_07",
        "title": "AOF Dual Officer Verification",
        "category": "Maker-Checker Controls",
        "description": "Account Opening Form (AOF) completed in full, verified by Maker (Clerk/Officer) and authenticated by Checker (Branch Manager/Assistant Manager) with dual signature.",
        "guideline": "BOI Four-Eye Principle. No account can be activated without Maker-Checker dual authorization.",
        "severity": "High",
        "default_pass_criteria": "AOF carries legible Maker and Checker signatures with official branch seal and date stamps."
    },
    {
        "id": "SB_CHK_08",
        "title": "Customer Signature / Thumb Impression",
        "category": "Specimen Signature Record",
        "description": "Customer's specimen signature or left thumb impression (LTI) captured on specimen card/AOF and successfully scanned & uploaded into Finacle Signature Module.",
        "guideline": "Negotiable Instruments Act & Finacle Mandate norms. Thumb impression must be attested by an independent witness.",
        "severity": "High",
        "default_pass_criteria": "Specimen signature properly signed in ink, matches OVD signature, and uploaded into Finacle signature viewer."
    }
]

CURRENT_ACCOUNT_CHECKS = [
    {
        "id": "CA_CHK_01",
        "title": "Certificate of Incorporation / Partnership Deed / Registration Certificate",
        "category": "Legal Entity Existence Proof",
        "description": "Certified copy of Certificate of Incorporation & MoA/AoA (for Companies), registered Partnership Deed (for Firms), Trust Deed (for Trusts), or Registration Certificate.",
        "guideline": "Companies Act 2013 / Indian Partnership Act 1932 & RBI KYC Master Direction § 29.",
        "severity": "Critical",
        "default_pass_criteria": "Certified true copy of constitutional documents verified against MCA21/Registrar records."
    },
    {
        "id": "CA_CHK_02",
        "title": "PAN of Entity",
        "category": "Entity Tax Identification",
        "description": "PAN card copy of the business entity verified against ITD database / Finacle entity master records with status 'Active'.",
        "guideline": "Section 139A of Income Tax Act 1961. Business entity PAN is strictly mandatory.",
        "severity": "Critical",
        "default_pass_criteria": "Entity PAN card verified on NSDL/ITD portal and matched with entity name on certificate of incorporation."
    },
    {
        "id": "CA_CHK_03",
        "title": "GSTIN Registration / Udhyam Certificate / Trade License",
        "category": "Proof of Business Activity (Two OVDs)",
        "description": "At least two independent documents certifying the name, address, and activity of the entity (e.g., GSTIN certificate, Udhyam Registration, Shop & Establishment License, IEC code).",
        "guideline": "RBI Master Direction on KYC § 28 (Sole Proprietorship / Entity 2-Document Rule).",
        "severity": "High",
        "default_pass_criteria": "Two valid government-issued registrations/licenses verifying active business operations at the declared address."
    },
    {
        "id": "CA_CHK_04",
        "title": "Beneficial Ownership (BO) Declaration",
        "category": "PMLA Compliance",
        "description": "Beneficial Owner declaration identifying natural persons holding >10% controlling ownership (Companies/Partnerships) or >15% (Unincorporated entities/Trusts) with supporting KYC.",
        "guideline": "Prevention of Money Laundering (Maintenance of Records) Rules § 9(3) and RBI Master Direction § 33.",
        "severity": "Critical",
        "default_pass_criteria": "Completed Annexure for Beneficial Ownership identification signed by authorized official with full shareholding table."
    },
    {
        "id": "CA_CHK_05",
        "title": "Resolution / Power of Attorney / Mandate",
        "category": "Account Operation Authority",
        "description": "Certified true copy of Board Resolution (for Companies) or Mandate Letter / Power of Attorney (for Partnerships/Trusts) specifying authorized persons and operational instructions.",
        "guideline": "Section 179 of Companies Act 2013 & BOI Commercial Banking Manual § 3.4.",
        "severity": "Critical",
        "default_pass_criteria": "Valid Board Resolution on company letterhead signed by Chairman/Company Secretary with specimen signatures."
    },
    {
        "id": "CA_CHK_06",
        "title": "KYC of All Authorized Signatories / Directors / Partners",
        "category": "Key Managerial Personnel KYC",
        "description": "PAN, Aadhaar/Passport, photograph, and address proof for all authorized signatories, key directors, active partners, and beneficial owners.",
        "guideline": "RBI Master Direction on KYC § 30. Full OVD verification required for every individual operating the account.",
        "severity": "High",
        "default_pass_criteria": "OSV-verified KYC documents and specimen signatures obtained for all authorized signatories."
    },
    {
        "id": "CA_CHK_07",
        "title": "CKYC Search & Download for Entity & Promoters",
        "category": "Central KYC Registry (Legal Entity)",
        "description": "CKYC search and CKYC Legal Entity Identifier (LEI/CKYC-LE) record creation or linkage for the corporate entity as well as all authorized signatories.",
        "guideline": "CERSAI Central KYC Registry guidelines for non-individual entities.",
        "severity": "Medium",
        "default_pass_criteria": "CKYC portal search records printed, entity CKYC template completed, and promoter CKYC matched."
    },
    {
        "id": "CA_CHK_08",
        "title": "Pre-Opening Site / Business Inspection Report",
        "category": "Physical Verification & Due Diligence",
        "description": "Physical site inspection of the business premises conducted by a BOI branch officer prior to account opening, accompanied by geo-tagged photos and inspection checklist.",
        "guideline": "BOI Circular on Fraud Prevention & Current Account Opening Guidelines § 5.1.",
        "severity": "Critical",
        "default_pass_criteria": "Detailed site visit report signed by inspecting officer with date, premises photograph, and sign board verification."
    },
    {
        "id": "CA_CHK_09",
        "title": "Credit Facility Undertaking / NOC from Existing Bankers",
        "category": "RBI Current Account Regulations",
        "description": "Declaration from customer confirming non-availment of credit facilities from any bank, or NOC from lending banks / Escrow agreement compliant with RBI Current Account circulars.",
        "guideline": "RBI Circular RBI/2020-21/20 on Opening of Current Accounts by Banks & subsequent amendments.",
        "severity": "Critical",
        "default_pass_criteria": "Written undertaking obtained and CRILC/CIBIL Commercial bureau check confirms no unauthorized CC/OD facility elsewhere."
    },
    {
        "id": "CA_CHK_10",
        "title": "Customer Profile Sheet & AML Risk Profiling",
        "category": "Corporate AML & Risk Assessment",
        "description": "Comprehensive business profile covering nature of industry, expected annual turnover, major suppliers/buyers, international trade exposure, and High/Medium/Low AML risk rating.",
        "guideline": "RBI KYC Master Direction § 22 & BOI AML Policy. Annual review frequency tied to risk rating.",
        "severity": "High",
        "default_pass_criteria": "Detailed CPS signed by branch head with AML risk grading and expected monthly transaction limits."
    },
    {
        "id": "CA_CHK_11",
        "title": "Dual Officer Verification & PF Signatures",
        "category": "Maker-Checker Controls",
        "description": "Dual officer verification on all account opening forms, inspection reports, and legal documents with clear Officer Signatures, Name Stamps, and PF Numbers.",
        "guideline": "BOI Standard Operating Procedure on Account Opening Audit § 7.",
        "severity": "High",
        "default_pass_criteria": "All AOF pages and document attachments verified and signed with PF Numbers by both Maker and Checker."
    }
]

# Quick lookup helper by account type
def get_checklist_for_type(account_type: str):
    if "Saving" in account_type:
        return SAVING_ACCOUNT_CHECKS
    return CURRENT_ACCOUNT_CHECKS
