/**
 * Comprehensive Sample Data for Indian NGO Grant Management (GrantSetu)
 * Realistic data based on Indian statutory rules (FCRA, CSR-1, 12A/80G, Darpan ID, GFR 12-A)
 */

export const initialNgoProfile = {
  name: "Seva Vikas Foundation",
  shortName: "SVF India",
  registrationType: "Public Charitable Trust",
  registrationNo: "E-18492/Pune",
  registrationDate: "2015-06-12",
  darpanId: "MH/2018/0198472",
  pan: "AAATS1234E",
  tan: "PUNE01928B",
  gstin: "27AAATS1234E1Z5",
  
  // Tax Exemption Certificates
  twelveARef: "AAATS1234E20214",
  twelveAValidTill: "2026-11-30",
  eightyGRef: "AAATS1234E20215",
  eightyGValidTill: "2026-11-30",
  
  // CSR Registration
  csr1RegNo: "CSR00018942",
  csr1RegDate: "2021-04-15",
  
  // FCRA Compliance
  fcraStatus: "Active",
  fcraRegNo: "083780512",
  fcraValidTill: "2028-03-31",
  fcraBankName: "State Bank of India (SBI)",
  fcraBranch: "Main Branch, 11 Sansad Marg, New Delhi 110001",
  fcraAccountNo: "40019283741",
  fcraIfsc: "SBIN0000691",
  
  // Domestic Operations Account
  domesticBankName: "HDFC Bank Ltd",
  domesticBranch: "Kothrud Branch, Pune",
  domesticAccountNo: "50100293847162",
  domesticIfsc: "HDFC0000149",
  
  // Address & Contact
  officeAddress: "Plot No. 42, Green Enclave, Karve Nagar, Pune, Maharashtra - 411052",
  contactPerson: "Dr. Anjali Deshmukh (Executive Director)",
  email: "contact@sevavikas.org.in",
  phone: "+91 98220 11234",
  website: "https://www.sevavikas.org.in"
};

export const initialGrants = [
  {
    id: "GRANT-2025-001",
    proposalId: "PROP-2024-008",
    title: "Rural Women Healthcare & Diagnostic Clinics",
    donorName: "HDFC Parivartan CSR Foundation",
    fundingType: "Domestic CSR", // Domestic CSR | FCRA Foreign | Govt Grant | HNI
    bankAccountType: "Domestic", // Domestic | FCRA
    sanctionOrderNo: "HDFC-CSR-2024-MH-94",
    sanctionDate: "2024-09-01",
    startDate: "2024-10-01",
    endDate: "2025-09-30",
    totalSanctionedAmount: 4500000,
    receivedAmount: 3000000, // Tranche 1 & 2
    spentAmount: 2450000,
    status: "Active", // Active | Pending UC | Proposal | Completed | Closed
    restrictedFund: true,
    fcraCompliant: true,
    
    tranches: [
      { id: "T1", trancheNo: 1, amount: 1500000, expectedDate: "2024-10-05", status: "Received", receivedDate: "2024-10-08", ucRequired: false, ucSubmitted: true },
      { id: "T2", trancheNo: 2, amount: 1500000, expectedDate: "2025-02-01", status: "Received", receivedDate: "2025-02-04", ucRequired: true, ucSubmitted: true },
      { id: "T3", trancheNo: 3, amount: 1500000, expectedDate: "2025-07-01", status: "Scheduled", receivedDate: null, ucRequired: true, ucSubmitted: false }
    ],

    budgetBreakdown: [
      { category: "Personnel & Staff Salaries", allocated: 1400000, spent: 1050000 },
      { category: "Mobile Diagnostic Van & Medical Equipment", allocated: 1600000, spent: 1550000 },
      { category: "Sub-Grants to Local Grassroots CBOs", allocated: 800000, spent: 400000 },
      { category: "Medicine & Health Camp Supplies", allocated: 480000, spent: 300000 },
      { category: "Admin & Operational Overheads (Max 5%)", allocated: 220000, spent: 150000 }
    ],

    kpis: [
      { name: "Mobile Health Camps Conducted", target: 48, achieved: 34, unit: "Camps" },
      { name: "Rural Women Screened & Treated", target: 12000, achieved: 8950, unit: "Women" },
      { name: "SHG Health Volunteers Trained", target: 150, achieved: 120, unit: "Volunteers" }
    ],

    logFrameSummary: {
      goal: "Reduce maternal anemia and reproductive health risks among rural women in Pune district.",
      outcome: "Improved access to preventative healthcare across 40 tribal & rural villages.",
      outputs: "Operating 2 mobile diagnostic vans with lady doctors and ultrasound facility."
    }
  },
  {
    id: "GRANT-2025-002",
    proposalId: "PROP-2024-004",
    title: "Clean Drinking Water & Sanitation in Marathwada",
    donorName: "Global Water Works Initiative (USAID Partner)",
    fundingType: "FCRA Foreign",
    bankAccountType: "FCRA",
    sanctionOrderNo: "GWWI-INT-2024-019",
    sanctionDate: "2024-06-15",
    startDate: "2024-07-01",
    endDate: "2026-06-30",
    totalSanctionedAmount: 8500000,
    receivedAmount: 4250000,
    spentAmount: 3890000,
    status: "Active",
    restrictedFund: true,
    fcraCompliant: true,

    tranches: [
      { id: "T1", trancheNo: 1, amount: 4250000, expectedDate: "2024-07-01", status: "Received", receivedDate: "2024-07-05", ucRequired: false, ucSubmitted: true },
      { id: "T2", trancheNo: 2, amount: 4250000, expectedDate: "2025-07-01", status: "Pending Approval", receivedDate: null, ucRequired: true, ucSubmitted: false }
    ],

    budgetBreakdown: [
      { category: "Solar RO Water Purification Plants", allocated: 4500000, spent: 2200000 },
      { category: "Community Wash Sanitation Block Construction", allocated: 2200000, spent: 1100000 },
      { category: "Hydrological Survey & Engineering Consultant", allocated: 800000, spent: 350000 },
      { category: "Community Water User Association Training", allocated: 600000, spent: 140000 },
      { category: "FCRA Admin Overheads (Max 20% Rule)", allocated: 400000, spent: 100000 }
    ],

    kpis: [
      { name: "Solar RO Plants Installed", target: 15, achieved: 8, unit: "Units" },
      { name: "Villagers Gaining Safe Drinking Water Access", target: 25000, achieved: 13500, unit: "People" },
      { name: "School Sanitation Blocks Operational", target: 10, achieved: 6, unit: "Blocks" }
    ],

    logFrameSummary: {
      goal: "Eradicate water-borne fluorosis and diarrheal illnesses in drought-prone Marathwada.",
      outcome: "24x7 community-owned clean drinking water hubs installed in 15 fluorosis-affected panchayats.",
      outputs: "Deep borewell recharge structures and community RO filtration systems built."
    }
  }
];

export const initialSubGrants = [
  {
    id: "SUBGRANT-2025-01",
    parentGrantId: "GRANT-2025-001",
    parentGrantTitle: "Rural Women Healthcare & Diagnostic Clinics",
    fundingType: "Domestic CSR", // Non-FCRA Grant
    subGranteeName: "Gramin Mahila Vikas Sanstha (GMVS)",
    subGranteeDarpanId: "MH/2019/0219481",
    subGranteePan: "AAATG9281F",
    subGrantee12A: "AAATG9281F20211",
    subGrantee80G: "AAATG9281F20212",
    contactPerson: "Smt. Sunita Patil (President)",
    email: "gmvs.pune@gmail.com",
    mouRefNo: "SVF/SUB-MOU/2024/04",
    mouDate: "2024-10-10",
    sanctionedAmount: 800000,
    disbursedAmount: 400000,
    status: "Active",
    purpose: "Mobilization of Self Help Groups (SHGs) & Village Health Nutrition Day (VHND) field drives across 20 tribal habitations.",
    
    tranches: [
      { id: "ST1", trancheNo: 1, amount: 400000, date: "2024-10-15", status: "Disbursed", ucSubmitted: true },
      { id: "ST2", trancheNo: 2, amount: 400000, date: "2025-04-10", status: "Scheduled", ucSubmitted: false }
    ],

    documents: [
      { id: "DOC-SUB-01", name: "GMVS_Sub_Grant_MoU_Signed.pdf", size: "1.4 MB", type: "application/pdf", category: "Sub-Grant MoU", uploadedAt: "2024-10-10" }
    ]
  }
];

export const initialProposals = [
  {
    id: "PROP-2025-015",
    title: "Digital Literacy & STEM Labs in Tribal Ashram Schools",
    donorName: "Tata Trusts CSR Division",
    fundingType: "Domestic CSR",
    targetDomain: "Education & Digital Inclusion",
    currency: "INR",
    durationMonths: 24,
    totalBudget: 6000000,
    status: "Under Internal Review",
    submissionDeadline: "2025-09-15",
    projectLocation: "Nandurbar & Palghar Districts, Maharashtra",

    problemStatement: "Over 85% of tribal ashram school students lack access to basic computer hardware and interactive science experiments, severely limiting their performance in secondary board examinations and higher vocational education admissions.",
    
    logFrame: {
      goal: "Bridge the rural-urban digital divide by empowering tribal students with computer literacy and hands-on STEM education.",
      outcome: "Improve STEM subject pass percentage from 48% to 80% across 20 government ashram schools.",
      outputs: [
        "20 solar-powered computer labs with 10 laptops each",
        "20 mini science experiment kits & smart projector displays",
        "40 ashram school teachers trained as master facilitators"
      ],
      activities: [
        "Infrastructure survey and solar installation at school premises",
        "Procurement and hardware deployment of ruggedized laptops",
        "Curriculum creation in local Marathi and English medium",
        "Conducting monthly coding and robotics workshops"
      ]
    },

    budgetItems: [
      { category: "Hardware & STEM Equipment", description: "200 Laptops + 20 Solar Systems + 20 Projectors", cost: 3400000 },
      { category: "Personnel & Facilitators", description: "2 Field Coordinators + 4 Master Trainers (2 yrs)", cost: 1400000 },
      { category: "Teacher Capacity Building", description: "Residential training workshops for 40 teachers", cost: 400000 },
      { category: "Monitoring, Evaluation & Learning", description: "Third-party baseline & endline evaluation study", cost: 500000 },
      { category: "Admin & Management Overhead", description: "Stationery, audit, reporting & project management (5% cap)", cost: 300000 }
    ],

    documents: [
      { id: "DOC-PROP-01", name: "Detailed_Project_Report_STEM_Tribal.pdf", size: "2.1 MB", type: "application/pdf", category: "Project Report (DPR)", uploadedAt: "2025-01-10" }
    ]
  }
];

export const initialExpenses = [
  {
    id: "VOUCH-2025-001",
    grantId: "GRANT-2025-001",
    grantTitle: "Rural Women Healthcare & Diagnostic Clinics",
    voucherNo: "SVF/24-25/104",
    date: "2024-10-15",
    payeeName: "Force Motors Ltd Pune",
    category: "Mobile Diagnostic Van & Medical Equipment",
    amount: 1450000,
    paymentMode: "Bank NEFT",
    bankAccountUsed: "Domestic HDFC Account",
    fcraTag: "Domestic",
    receiptAttached: true,
    description: "Purchase of customized Traveler Mobile Ambulance Van with generator backup",
    approvedBy: "Dr. Anjali Deshmukh",
    documents: [
      { id: "DOC-EXP-01", name: "Force_Motors_Ambulance_Invoice_Tax.pdf", size: "840 KB", type: "application/pdf", category: "Vendor Tax Invoice", uploadedAt: "2024-10-15" }
    ]
  },
  {
    id: "VOUCH-2025-002",
    grantId: "GRANT-2025-001",
    grantTitle: "Rural Women Healthcare & Diagnostic Clinics",
    voucherNo: "SVF/24-25/118",
    date: "2024-11-02",
    payeeName: "Dr. Sunita Kulkarni (Gynaecologist)",
    category: "Personnel & Staff Salaries",
    amount: 180000,
    paymentMode: "Bank Transfer",
    bankAccountUsed: "Domestic HDFC Account",
    fcraTag: "Domestic",
    receiptAttached: true,
    description: "Lady Doctor Honorarium for October 2024 field diagnostic camps",
    approvedBy: "Finance Officer",
    documents: []
  }
];

export const initialClosureRecords = [];
