import { initializeApp } from "firebase/app";
import { getFirestore, doc, setDoc, deleteDoc, getDocs, collection } from "firebase/firestore";
import firebaseConfig from "../firebase-applet-config.json" with { type: "json" };

const app = initializeApp(firebaseConfig);
const db = getFirestore(app, firebaseConfig.firestoreDatabaseId);

const RESTRUCTURED_SERVICES = [
  {
    id: "statutory-audit",
    name: "Statutory Audit",
    consentTemplate: {
      body: "Consent for collection and processing of financial statements, books of account, and audit evidence pursuant to statutory audit obligations under the Companies Act 2013.",
      version: 1
    },
    retentionPolicy: {
      basis: "from_date",
      years: 8,
      statute: "Companies Act 2013 s.128(5)"
    }
  },
  {
    id: "tax-audit",
    name: "Tax Audit",
    consentTemplate: {
      body: "Consent for processing books of account, computational schedules, and tax audit documentation under the Income-tax framework.",
      version: 1
    },
    retentionPolicy: {
      basis: "from_date",
      years: 7,
      statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026"
    }
  },
  {
    id: "income-tax-services",
    name: "Income Tax services",
    consentTemplate: {
      body: "Consent for processing income computation, tax filings, representations, and statutory assessments under the Income-tax framework.",
      version: 1
    },
    retentionPolicy: {
      basis: "from_date",
      years: 7,
      statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026"
    }
  },
  {
    id: "gst-services",
    name: "GST services",
    consentTemplate: {
      body: "Consent for processing supply registers, input tax credit documentation, and periodic/annual GST returns.",
      version: 1
    },
    retentionPolicy: {
      basis: "from_date",
      years: 6,
      statute: "CGST Act 2017 s.36"
    }
  },
  {
    id: "accounting-services",
    name: "Accounting services",
    consentTemplate: {
      body: "Consent for processing invoices, bank statements, general ledgers, and periodic bookkeeping compilation.",
      version: 1
    },
    retentionPolicy: {
      basis: "contract_tenure",
      years: null,
      statute: null
    }
  },
  {
    id: "finance-consulting-services",
    name: "Finance-related consulting services",
    consentTemplate: {
      body: "Consent for processing advisory notes, financial models, valuation data, and strategic consulting documentation.",
      version: 1
    },
    retentionPolicy: {
      basis: "contract_tenure",
      years: null,
      statute: null
    }
  },
  {
    id: "internal-audit-services",
    name: "Internal audit services",
    consentTemplate: {
      body: "Consent for processing operational records, internal control reviews, process documentation, and management audit reports.",
      version: 1
    },
    retentionPolicy: {
      basis: "from_date",
      years: null,
      statute: "Companies Act 2013 s.138 (Mandatory company: 8 years) / Non-company or non-mandatory: 7 years under Income-tax Act 2025, Section 62 read with Rule 46(9)",
      entityDependent: true,
      conditionalRules: {
        companyMandatory: 8,
        nonCompanyOrNonMandatory: 7
      },
      note: "Entity-dependent retention: 8 years for mandatory Companies Act s.138 audits, 7 years for non-company or non-mandatory internal audits."
    }
  }
];

async function runRestructure() {
  console.log("Cleaning up old underscore docs and writing exact 7 restructured docs...");
  const oldIds = [
    "accounting_services",
    "finance_consulting",
    "gst_services",
    "income_tax_services",
    "internal_audit",
    "statutory_audit",
    "tax_audit"
  ];
  for (const oldId of oldIds) {
    try {
      await deleteDoc(doc(db, "services", oldId));
    } catch (e) {}
  }

  for (const item of RESTRUCTURED_SERVICES) {
    const { id, ...data } = item;
    await setDoc(doc(db, "services", id), data);
    console.log(`Updated service: ${id}`);
  }

  console.log("\nFETCHING FINAL FIRESTORE DATA:");
  const snap = await getDocs(collection(db, "services"));
  console.log(`TOTAL DOCUMENTS: ${snap.docs.length}`);
  snap.docs.forEach((d, idx) => {
    console.log(`\n--- [${idx + 1}] Document ID: "${d.id}" ---`);
    console.log(JSON.stringify(d.data(), null, 2));
  });
}

runRestructure()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
