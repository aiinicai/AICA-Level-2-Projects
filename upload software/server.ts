import express from "express";
import path from "path";
import fs from "fs";
import dotenv from "dotenv";

// Load .env or config.env (supports both dev and packaged EXE)
dotenv.config();
if (process.env.ACCUSHEET_CONFIG_PATH) {
  dotenv.config({ path: process.env.ACCUSHEET_CONFIG_PATH, override: false });
}

const app = express();
const PORT = parseInt(process.env.PORT || "3000", 10);

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ extended: true, limit: "50mb" }));

// =========================================================================
// DATA PERSISTENCE LAYER (USERS & ENTITY VAULT)
// =========================================================================
// In packaged Electron app, ACCUSHEET_DATA_DIR points to the user's AppData folder
// so data persists across app updates. Falls back to cwd/data in dev mode.
const DATA_DIR = process.env.ACCUSHEET_DATA_DIR || path.join(process.cwd(), "data");
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const USERS_FILE = path.join(DATA_DIR, "users.json");
const ENTITIES_FILE = path.join(DATA_DIR, "entities.json");

interface StoredUser {
  id: string;
  name: string;
  email: string;
  password: string; // Plain/hashed for this demo portal
  role: "ADMIN" | "AUDITOR" | "ACCOUNTANT" | "VIEWER";
  status: "APPROVED" | "PENDING" | "SUSPENDED";
  createdAt: string;
  approvedAt?: string;
  approvedBy?: string;
  lastLoginAt?: string;
}

function loadUsers(): StoredUser[] {
  try {
    if (fs.existsSync(USERS_FILE)) {
      const data = fs.readFileSync(USERS_FILE, "utf-8");
      return JSON.parse(data);
    }
  } catch (err) {
    console.error("Error reading users file:", err);
  }

  // Default seed users
  const defaultUsers: StoredUser[] = [
    {
      id: "admin",
      name: "Priyanka Garg (CA / Partner)",
      email: "capriyankagarg61@gmail.com",
      password: "Admin@123",
      role: "ADMIN",
      status: "APPROVED",
      createdAt: new Date().toISOString(),
      approvedAt: new Date().toISOString(),
      approvedBy: "SYSTEM",
    },
    {
      id: "auditor",
      name: "Senior Audit Reviewer",
      email: "audit.team@firm.in",
      password: "Audit@123",
      role: "AUDITOR",
      status: "APPROVED",
      createdAt: new Date().toISOString(),
      approvedAt: new Date().toISOString(),
      approvedBy: "admin",
    },
  ];

  saveUsers(defaultUsers);
  return defaultUsers;
}

function saveUsers(users: StoredUser[]) {
  try {
    fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2), "utf-8");
  } catch (err) {
    console.error("Error writing users file:", err);
  }
}

function loadEntities(): any[] {
  try {
    if (fs.existsSync(ENTITIES_FILE)) {
      const data = fs.readFileSync(ENTITIES_FILE, "utf-8");
      return JSON.parse(data);
    }
  } catch (err) {
    console.error("Error reading entities file:", err);
  }
  return [];
}

function saveEntities(entities: any[]) {
  try {
    fs.writeFileSync(ENTITIES_FILE, JSON.stringify(entities, null, 2), "utf-8");
  } catch (err) {
    console.error("Error writing entities file:", err);
  }
}

// Initialize on boot
loadUsers();
loadEntities();

// =========================================================================
// AUTHENTICATION & USER MANAGEMENT API
// =========================================================================

// POST /api/auth/login
app.post("/api/auth/login", (req, res) => {
  const { id, password } = req.body;
  if (!id || !password) {
    return res.status(400).json({ success: false, error: "User ID and Password are required." });
  }

  const users = loadUsers();
  const cleanId = id.trim().toLowerCase();
  const user = users.find((u) => u.id.toLowerCase() === cleanId);

  if (!user || user.password !== password) {
    return res.status(401).json({ success: false, error: "Invalid User ID or password." });
  }

  if (user.status === "PENDING") {
    return res.status(403).json({
      success: false,
      error: "Your User ID is pending approval by the Administrator. Please contact your Admin to grant access.",
      isPending: true,
    });
  }

  if (user.status === "SUSPENDED") {
    return res.status(403).json({
      success: false,
      error: "This User account has been deactivated or suspended by the Administrator.",
      isSuspended: true,
    });
  }

  // Update last login
  user.lastLoginAt = new Date().toISOString();
  saveUsers(users);

  const { password: _, ...safeUser } = user;
  return res.json({ success: true, user: safeUser });
});

// POST /api/auth/register (New User Request)
app.post("/api/auth/register", (req, res) => {
  const { id, name, email, password, role } = req.body;
  if (!id || !password || !name) {
    return res.status(400).json({ success: false, error: "User ID, Name, and Password are required." });
  }

  const users = loadUsers();
  const cleanId = id.trim().toLowerCase();

  if (users.some((u) => u.id.toLowerCase() === cleanId)) {
    return res.status(400).json({ success: false, error: "This User ID is already taken. Please choose another." });
  }

  const newUser: StoredUser = {
    id: cleanId,
    name: name.trim(),
    email: (email || "").trim(),
    password: password.trim(),
    role: role || "AUDITOR",
    status: "PENDING", // Requires Admin approval
    createdAt: new Date().toISOString(),
  };

  users.push(newUser);
  saveUsers(users);

  const { password: _, ...safeUser } = newUser;
  return res.json({
    success: true,
    user: safeUser,
    message: "Registration submitted successfully! Your account is pending Administrator approval before sign-in.",
  });
});

// GET /api/auth/users (List all users - for Admin management)
app.get("/api/auth/users", (req, res) => {
  const users = loadUsers();
  const safeUsers = users.map(({ password, ...u }) => u);
  return res.json({ success: true, users: safeUsers });
});

// POST /api/auth/users (Admin directly creates a pre-approved user)
app.post("/api/auth/users", (req, res) => {
  const { id, name, email, password, role, adminUserId } = req.body;
  if (!id || !password || !name) {
    return res.status(400).json({ success: false, error: "User ID, Name, and Password are required." });
  }

  const users = loadUsers();
  const cleanId = id.trim().toLowerCase();

  if (users.some((u) => u.id.toLowerCase() === cleanId)) {
    return res.status(400).json({ success: false, error: "This User ID already exists." });
  }

  const newUser: StoredUser = {
    id: cleanId,
    name: name.trim(),
    email: (email || "").trim(),
    password: password.trim(),
    role: role || "AUDITOR",
    status: "APPROVED",
    createdAt: new Date().toISOString(),
    approvedAt: new Date().toISOString(),
    approvedBy: adminUserId || "admin",
  };

  users.push(newUser);
  saveUsers(users);

  const { password: _, ...safeUser } = newUser;
  return res.json({ success: true, user: safeUser });
});

// PATCH /api/auth/users/:id/status (Admin approve, reject, suspend user)
app.patch("/api/auth/users/:id/status", (req, res) => {
  const userId = req.params.id.toLowerCase();
  const { status, role, adminUserId } = req.body;

  const users = loadUsers();
  const user = users.find((u) => u.id.toLowerCase() === userId);

  if (!user) {
    return res.status(404).json({ success: false, error: "User not found." });
  }

  if (status) {
    user.status = status;
    if (status === "APPROVED" && !user.approvedAt) {
      user.approvedAt = new Date().toISOString();
      user.approvedBy = adminUserId || "admin";
    }
  }

  if (role) {
    user.role = role;
  }

  saveUsers(users);

  const { password: _, ...safeUser } = user;
  return res.json({ success: true, user: safeUser });
});

// DELETE /api/auth/users/:id (Admin delete user)
app.delete("/api/auth/users/:id", (req, res) => {
  const userId = req.params.id.toLowerCase();
  const users = loadUsers();

  const userIdx = users.findIndex((u) => u.id.toLowerCase() === userId);
  if (userIdx === -1) {
    return res.status(404).json({ success: false, error: "User not found." });
  }

  // Prevent deleting last admin
  const adminCount = users.filter((u) => u.role === "ADMIN" && u.status === "APPROVED").length;
  if (users[userIdx].role === "ADMIN" && adminCount <= 1) {
    return res.status(400).json({ success: false, error: "Cannot delete the last remaining Administrator." });
  }

  users.splice(userIdx, 1);
  saveUsers(users);

  return res.json({ success: true, message: `User ${userId} deleted successfully.` });
});

// =========================================================================
// ENTITY DATA VAULT API (SAVE & FETCH ENTITY WORKSPACES)
// =========================================================================

// POST /api/entities/save
app.post("/api/entities/save", (req, res) => {
  try {
    const { workspace } = req.body;
    if (!workspace || !workspace.entityId) {
      return res.status(400).json({ success: false, error: "Invalid workspace payload." });
    }

    const entities = loadEntities();
    const existingIndex = entities.findIndex(
      (e) => e.entityId === workspace.entityId || e.id === workspace.id
    );

    const recordToSave = {
      ...workspace,
      id: workspace.id || `ws-${workspace.entityId}-${Date.now()}`,
      savedAt: new Date().toISOString(),
    };

    if (existingIndex >= 0) {
      entities[existingIndex] = recordToSave;
    } else {
      entities.unshift(recordToSave);
    }

    saveEntities(entities);

    return res.json({
      success: true,
      id: recordToSave.id,
      savedAt: recordToSave.savedAt,
      message: `Entity "${workspace.entityName}" saved successfully in Audit Vault.`,
    });
  } catch (err: any) {
    console.error("Save entity error:", err);
    return res.status(500).json({ success: false, error: err.message || "Failed to save entity." });
  }
});

// GET /api/entities/list (List all saved entities with summaries)
app.get("/api/entities/list", (req, res) => {
  try {
    const entities = loadEntities();
    const list = entities.map((e) => ({
      id: e.id,
      entityId: e.entityId,
      entityName: e.entityName,
      entityType: e.entityType,
      financialYear: e.financialYear,
      balanceSheetDate: e.balanceSheetDate,
      savedAt: e.savedAt,
      savedBy: e.savedBy || "Staff",
      versionTag: e.versionTag || "Default",
      notes: e.notes || "",
      summary: e.summary || {
        totalAssets: 0,
        totalLiabilities: 0,
        netProfit: 0,
        isBalanced: true,
        difference: 0,
        ledgersCount: e.data?.ledgers?.length || 0,
        adjustmentsCount: e.data?.adjustments?.length || 0,
        assetsCount: e.data?.depreciationAssets?.length || 0,
      },
    }));

    return res.json({ success: true, entities: list });
  } catch (err: any) {
    console.error("List entities error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// GET /api/entities/:id (Fetch complete entity data for review)
app.get("/api/entities/:id", (req, res) => {
  try {
    const id = req.params.id;
    const entities = loadEntities();
    const entityRecord = entities.find((e) => e.id === id || e.entityId === id);

    if (!entityRecord) {
      return res.status(404).json({ success: false, error: "Saved entity record not found." });
    }

    return res.json({ success: true, workspace: entityRecord });
  } catch (err: any) {
    console.error("Fetch entity error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// DELETE /api/entities/:id (Delete saved entity snapshot)
app.delete("/api/entities/:id", (req, res) => {
  try {
    const id = req.params.id;
    const entities = loadEntities();
    const filtered = entities.filter((e) => e.id !== id && e.entityId !== id);

    if (filtered.length === entities.length) {
      return res.status(404).json({ success: false, error: "Entity not found in vault." });
    }

    saveEntities(filtered);
    return res.json({ success: true, message: "Entity removed from vault." });
  } catch (err: any) {
    console.error("Delete entity error:", err);
    return res.status(500).json({ success: false, error: err.message });
  }
});

// =========================================================================
// BUILT-IN RULE ENGINE — No API key required
// =========================================================================

// ── Ledger Classification Rule Table (Indian GAAP / ICAI Non-Corporate) ──
const CLASSIFICATION_RULES: Array<{
  keywords: string[];
  headCode?: string;
  mainHead: string;
  subHead: string;
  scheduleNo: number | string;
  nature: string;
  confidence: string;
  reasoning: string;
}> = [
  // ── Capital & Liabilities ────────────────────────────────────────────────
  { keywords: ["capital", "partner capital", "proprietor capital", "owner capital", "capital a/c"], headCode: "CAP_01", mainHead: "Capital & Liabilities", subHead: "Capital Account", scheduleNo: 1, nature: "Liability", confidence: "High", reasoning: "Capital accounts represent the owner/partner's equity in a non-corporate entity per ICAI guidance." },
  { keywords: ["drawings", "drawing account", "proprietor drawings", "partner drawings"], headCode: "CAP_02", mainHead: "Capital & Liabilities", subHead: "Drawings (Deducted from Capital)", scheduleNo: 1, nature: "Liability", confidence: "High", reasoning: "Drawings reduce the capital balance of the proprietor/partner as per non-corporate accounting norms." },
  { keywords: ["loan from partner", "loan from proprietor", "partner loan", "unsecured loan from partner"], headCode: "LIB_03", mainHead: "Capital & Liabilities", subHead: "Unsecured Loans – Partners/Proprietor", scheduleNo: 3, nature: "Liability", confidence: "High", reasoning: "Loans introduced by partners/proprietors are classified as unsecured loans, separate from capital." },
  { keywords: ["bank loan", "term loan", "secured loan", "mortgage", "hypothecation", "vehicle loan", "cc limit", "cash credit"], headCode: "LIB_02", mainHead: "Capital & Liabilities", subHead: "Secured Loans", scheduleNo: 2, nature: "Liability", confidence: "High", reasoning: "Loans secured against assets are classified under Secured Loans in the Balance Sheet." },
  { keywords: ["unsecured loan", "loan from friends", "loan from relatives", "private loan", "personal loan"], headCode: "LIB_03", mainHead: "Capital & Liabilities", subHead: "Unsecured Loans", scheduleNo: 3, nature: "Liability", confidence: "High", reasoning: "Loans without collateral are classified as Unsecured Loans." },
  { keywords: ["sundry creditor", "trade creditor", "accounts payable", "creditors", "payable"], headCode: "LIB_04", mainHead: "Capital & Liabilities", subHead: "Current Liabilities – Sundry Creditors", scheduleNo: 4, nature: "Liability", confidence: "High", reasoning: "Trade creditors are current liabilities shown under Schedule 4 in a non-corporate balance sheet." },
  { keywords: ["outstanding expense", "accrued expense", "expense payable", "audit fee payable", "salary payable", "wages payable", "outstanding"], headCode: "LIB_05", mainHead: "Capital & Liabilities", subHead: "Current Liabilities – Outstanding Expenses", scheduleNo: 5, nature: "Liability", confidence: "High", reasoning: "Outstanding expenses are accrued liabilities to be disclosed under current liabilities." },
  { keywords: ["advance from customer", "advance received", "customer advance", "deposit received", "security deposit received"], headCode: "LIB_05", mainHead: "Capital & Liabilities", subHead: "Current Liabilities – Advance from Customers", scheduleNo: 5, nature: "Liability", confidence: "High", reasoning: "Advances received from customers are current liabilities until the obligation is fulfilled." },
  { keywords: ["tds payable", "tds liability", "tax deducted", "income tax payable", "gst payable", "gst liability", "vat payable"], headCode: "LIB_06", mainHead: "Capital & Liabilities", subHead: "Current Liabilities – Statutory Dues", scheduleNo: 6, nature: "Liability", confidence: "High", reasoning: "Statutory dues including TDS, GST and income tax are current liabilities per tax law requirements." },
  { keywords: ["provision", "provision for taxation", "provision for expenses", "provident fund payable", "pf payable", "esic payable"], headCode: "LIB_07", mainHead: "Capital & Liabilities", subHead: "Provisions", scheduleNo: 7, nature: "Liability", confidence: "Medium", reasoning: "Provisions for known obligations are classified as provisions in the balance sheet." },

  // ── Assets ───────────────────────────────────────────────────────────────
  { keywords: ["land", "building", "furniture", "fixture", "plant", "machinery", "equipment", "vehicle", "computer", "office equipment", "tools", "air conditioner", "ac", "fixed asset"], headCode: "AST_01", mainHead: "Assets", subHead: "Fixed Assets (Tangible)", scheduleNo: 8, nature: "Asset", confidence: "High", reasoning: "Tangible fixed assets are capitalised and shown at cost less accumulated depreciation per Schedule 8." },
  { keywords: ["goodwill", "trademark", "patent", "copyright", "software", "intangible", "brand", "franchise"], headCode: "AST_02", mainHead: "Assets", subHead: "Fixed Assets (Intangible)", scheduleNo: 8, nature: "Asset", confidence: "High", reasoning: "Intangible assets are recognised per AS-26 (Intangible Assets) and shown net of amortisation." },
  { keywords: ["investment", "mutual fund", "shares", "stocks", "debenture", "bonds", "fdr", "fixed deposit", "nsc", "ppf"], headCode: "AST_03", mainHead: "Assets", subHead: "Investments", scheduleNo: 9, nature: "Asset", confidence: "High", reasoning: "Investments are disclosed at cost or fair value as applicable under Indian GAAP." },
  { keywords: ["closing stock", "stock in trade", "inventory", "raw material", "work in progress", "wip", "finished goods"], headCode: "AST_04", mainHead: "Assets", subHead: "Current Assets – Stock / Inventory", scheduleNo: 10, nature: "Asset", confidence: "High", reasoning: "Closing stock is valued at cost or NRV, whichever is lower, per AS-2." },
  { keywords: ["sundry debtor", "trade debtor", "accounts receivable", "debtors", "receivable", "book debt"], headCode: "AST_05", mainHead: "Assets", subHead: "Current Assets – Sundry Debtors", scheduleNo: 11, nature: "Asset", confidence: "High", reasoning: "Trade debtors are current assets. Confirmation and ageing analysis is required for audit." },
  { keywords: ["cash in hand", "cash", "petty cash"], headCode: "AST_06", mainHead: "Assets", subHead: "Current Assets – Cash in Hand", scheduleNo: 12, nature: "Asset", confidence: "High", reasoning: "Cash in hand is a liquid current asset to be verified physically." },
  { keywords: ["bank", "bank account", "current account", "savings account", "bank balance", "hdfc", "sbi", "icici", "axis", "kotak", "pnb"], headCode: "AST_07", mainHead: "Assets", subHead: "Current Assets – Bank Balances", scheduleNo: 12, nature: "Asset", confidence: "High", reasoning: "Bank balances are verified through bank reconciliation statements." },
  { keywords: ["advance to supplier", "advance paid", "prepaid", "advance expense", "security deposit paid", "rent deposit", "loan given", "loan to"], headCode: "AST_08", mainHead: "Assets", subHead: "Loans & Advances", scheduleNo: 13, nature: "Asset", confidence: "Medium", reasoning: "Advances and security deposits recoverable are classified as Loans & Advances." },
  { keywords: ["tds receivable", "tds credit", "advance tax", "income tax refund", "gst refund", "input tax credit", "itc"], headCode: "AST_09", mainHead: "Assets", subHead: "Loans & Advances – Tax Credits", scheduleNo: 13, nature: "Asset", confidence: "High", reasoning: "Advance tax, TDS credit and GST ITC are recoverable from the government, classified as advances." },

  // ── Income ───────────────────────────────────────────────────────────────
  { keywords: ["sales", "turnover", "revenue", "gross sales", "net sales", "service income", "professional fees", "consultation fees", "consultancy", "fees received", "commission income", "contract revenue"], headCode: "PL_01", mainHead: "Income", subHead: "Direct Income / Turnover", scheduleNo: "P&L", nature: "Income", confidence: "High", reasoning: "Primary revenue from operations is classified as turnover/direct income in P&L." },
  { keywords: ["interest income", "interest received", "bank interest", "interest on fdr", "interest on loan given"], headCode: "PL_02", mainHead: "Income", subHead: "Indirect Income – Interest Income", scheduleNo: "P&L", nature: "Income", confidence: "High", reasoning: "Interest received on deposits or loans given is classified as indirect income." },
  { keywords: ["rental income", "rent received", "lease income", "house rent income"], headCode: "PL_03", mainHead: "Income", subHead: "Indirect Income – Rental Income", scheduleNo: "P&L", nature: "Income", confidence: "High", reasoning: "Rental income is indirect income unless letting is the core business activity." },
  { keywords: ["dividend", "dividend income", "dividend received"], headCode: "PL_04", mainHead: "Income", subHead: "Indirect Income – Dividend", scheduleNo: "P&L", nature: "Income", confidence: "High", reasoning: "Dividend income from investments is classified as indirect income." },
  { keywords: ["other income", "miscellaneous income", "profit on sale", "gain on sale", "insurance claim", "discount received"], headCode: "PL_05", mainHead: "Income", subHead: "Indirect Income – Others", scheduleNo: "P&L", nature: "Income", confidence: "Medium", reasoning: "Non-operational income items are grouped as other/indirect income." },

  // ── Expenses ─────────────────────────────────────────────────────────────
  { keywords: ["purchase", "goods purchased", "raw material consumed", "direct material", "cost of goods"], headCode: "PL_10", mainHead: "Expense", subHead: "Direct Expenses – Purchases", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Purchases of goods for resale or raw materials are direct trading expenses." },
  { keywords: ["opening stock", "opening inventory"], headCode: "PL_11", mainHead: "Expense", subHead: "Direct Expenses – Opening Stock", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Opening stock is included in cost of goods sold computation." },
  { keywords: ["freight", "carriage inward", "transport charges", "loading", "unloading", "packing charges"], headCode: "PL_12", mainHead: "Expense", subHead: "Direct Expenses – Freight / Carriage", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Direct costs related to procurement of goods are classified as direct expenses." },
  { keywords: ["salary", "wages", "staff salary", "employee salary", "labour", "manpower"], headCode: "PL_20", mainHead: "Expense", subHead: "Indirect Expenses – Salaries & Wages", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Staff salaries are indirect expenses; partner remuneration is separately disclosed per partnership deed." },
  { keywords: ["rent", "rent paid", "office rent", "shop rent", "lease rent"], headCode: "PL_21", mainHead: "Expense", subHead: "Indirect Expenses – Rent", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Rent paid for business premises is an indirect operating expense." },
  { keywords: ["electricity", "power", "water", "utility", "telephone", "internet", "broadband"], headCode: "PL_22", mainHead: "Expense", subHead: "Indirect Expenses – Utilities", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Utility expenses (electricity, telephone, water) are indirect overhead expenses." },
  { keywords: ["depreciation", "amortisation", "amortization", "dep"], headCode: "PL_23", mainHead: "Expense", subHead: "Indirect Expenses – Depreciation", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Depreciation on fixed assets is computed per IT Act or Companies Act rates for non-corporate entities." },
  { keywords: ["interest paid", "bank interest paid", "interest on loan", "interest on cc", "interest on od", "finance charges", "bank charges"], headCode: "PL_24", mainHead: "Expense", subHead: "Indirect Expenses – Interest & Finance Charges", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Interest on borrowings is a finance cost. Section 40(b) limits apply for partner interest in partnership firms." },
  { keywords: ["audit fee", "professional fee", "legal fee", "accounting charges", "consultancy charges paid", "ca fee"], headCode: "PL_25", mainHead: "Expense", subHead: "Indirect Expenses – Professional Fees", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Professional/audit fees are deductible indirect expenses." },
  { keywords: ["advertisement", "marketing", "promotion", "publicity", "printing", "stationery"], headCode: "PL_26", mainHead: "Expense", subHead: "Indirect Expenses – Selling & Distribution", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Advertising and selling expenses are classified as indirect selling overheads." },
  { keywords: ["repairs", "maintenance", "amc", "annual maintenance"], headCode: "PL_27", mainHead: "Expense", subHead: "Indirect Expenses – Repairs & Maintenance", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Repair and maintenance expenditure is revenue in nature and classified as indirect expense." },
  { keywords: ["travelling", "travel", "conveyance", "vehicle expense", "fuel", "petrol", "diesel", "tour expense"], headCode: "PL_28", mainHead: "Expense", subHead: "Indirect Expenses – Travelling & Conveyance", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Business travel and conveyance costs are deductible indirect expenses." },
  { keywords: ["insurance", "premium paid", "insurance premium"], headCode: "PL_29", mainHead: "Expense", subHead: "Indirect Expenses – Insurance", scheduleNo: "P&L", nature: "Expense", confidence: "High", reasoning: "Insurance premium is an indirect business expense." },
  { keywords: ["miscellaneous expense", "other expense", "sundry expense", "petty expense", "general expense"], headCode: "PL_30", mainHead: "Expense", subHead: "Indirect Expenses – Miscellaneous", scheduleNo: "P&L", nature: "Expense", confidence: "Low", reasoning: "Miscellaneous items should be reviewed and reclassified to specific heads where possible." },
];

function classifyLedgerByRules(ledger: any, heads: any[]): any | null {
  const name = (ledger.ledgerName || "").toLowerCase().trim();
  for (const rule of CLASSIFICATION_RULES) {
    if (rule.keywords.some((kw) => name.includes(kw))) {
      // Try to match to an actual head in the provided heads list
      const matchedHead = heads.find(
        (h) =>
          h.code === rule.headCode ||
          (h.subHead && h.subHead.toLowerCase().includes(rule.subHead.toLowerCase().split(" – ").pop()?.toLowerCase() || "")) ||
          (h.mainHead && h.mainHead.toLowerCase() === rule.mainHead.toLowerCase())
      );
      return {
        ledgerName: ledger.ledgerName,
        suggestedHeadCode: matchedHead?.code || rule.headCode || "",
        suggestedMainHead: rule.mainHead,
        suggestedSubHead: rule.subHead,
        suggestedScheduleNo: rule.scheduleNo,
        nature: rule.nature,
        confidence: rule.confidence,
        reasoning: rule.reasoning,
      };
    }
  }
  return null;
}

// ── Audit Notes Template Engine ──────────────────────────────────────────────
function generateAuditNotes(payload: any): any[] {
  const notes: any[] = [];
  const entity = payload.entityDetails || payload.entity || {};
  const recon = payload.reconciliation || {};
  const pl = payload.plStatement || {};
  const userQuestion = (payload.userQuestion || "").toLowerCase();

  // Handle free-form questions
  if (userQuestion) {
    if (userQuestion.includes("40a") || userQuestion.includes("cash") || userQuestion.includes("269st")) {
      return [{
        category: "Compliance",
        observation: "Section 40A(3) disallows cash payments exceeding ₹10,000 in a day to a single person. Review all cash vouchers above this threshold. Section 269ST prohibits receipt of ₹2 lakh or more in cash from a single person in a day. Verify cash receipts register against bank deposits.",
        recommendedDisclosure: "Disclose any 40A(3) disallowances in Tax Audit Report (Form 3CD – Clause 21). Verify compliance with 269ST and obtain declarations from cash payers above ₹2 lakh.",
        severity: "Critical"
      }];
    }
    if (userQuestion.includes("partner") || userQuestion.includes("salary") || userQuestion.includes("interest on capital")) {
      return [{
        category: "Capital",
        observation: "Partner remuneration and interest on capital are allowable only as per the partnership deed. Section 40(b) restricts the maximum deductible remuneration to the limits prescribed. Interest on capital is capped at 12% p.a. Ensure amounts paid are within deed provisions.",
        recommendedDisclosure: "Show partner interest on capital separately in Schedule 1. Disclose remuneration paid in Profit & Loss Account and reconcile with amounts claimed in ITR. Obtain the partnership deed and verify authorisation.",
        severity: "Caution"
      }];
    }
    if (userQuestion.includes("depreciation")) {
      return [{
        category: "Assets",
        observation: "Depreciation for non-corporate entities is generally computed under the Income Tax Act, 1961 (WDV method) for tax purposes. Verify the opening WDV, additions, deletions and rate applied for each asset block. Ensure depreciation schedule ties to Fixed Asset Register.",
        recommendedDisclosure: "Prepare a detailed depreciation schedule (Schedule 8) showing opening WDV, additions, deletions, rate, and closing WDV. Reconcile with IT Act block-wise depreciation.",
        severity: "Info"
      }];
    }
    // Generic response for other questions
    return [{
      category: "Compliance",
      observation: `Audit query — '${payload.userQuestion}': Review the relevant supporting documents, statutory books, and ICAI guidance notes applicable to non-corporate entities. Ensure proper disclosures are made in the working papers as per SA-230.`,
      recommendedDisclosure: "Document the audit evidence and workings in the permanent/current file as per SA-230 (Audit Documentation) requirements.",
      severity: "Info"
    }];
  }

  // Auto-generated observations based on entity data
  const entityType = (entity.entityType || entity.type || "Proprietorship");
  const entityName = entity.name || entity.entityName || "the entity";
  const fy = entity.financialYear || entity.fy || "the financial year";

  notes.push({
    category: "Capital",
    observation: `Verify the opening and closing capital accounts of ${entityName} for FY ${fy}. Ensure drawings, remuneration, interest on capital, and net profit additions are properly reconciled with the prior year balance sheet and partner/proprietor confirmation letters.`,
    recommendedDisclosure: "Disclose capital account movement in Schedule 1. Obtain signed confirmation from partners/proprietor of capital balances as at the balance sheet date.",
    severity: "Caution"
  });

  if (entityType.toLowerCase().includes("partnership") || entityType.toLowerCase().includes("llp")) {
    notes.push({
      category: "Compliance",
      observation: `For ${entityName} (${entityType}): Verify that partner remuneration and interest on capital are within the limits prescribed under Section 40(b) of the Income Tax Act. Check that the partnership deed is registered and authorises the amounts paid.`,
      recommendedDisclosure: "Attach a copy of the partnership deed. Disclose partners' remuneration and interest in Form 3CD (Clause 27) if Tax Audit is applicable. Show remuneration as a separate line in Profit & Loss Account.",
      severity: "Critical"
    });
  }

  if (recon && recon.isBalanced === false) {
    const diff = Math.abs(recon.difference || 0).toLocaleString("en-IN");
    notes.push({
      category: "P&L",
      observation: `The Balance Sheet of ${entityName} is NOT balanced — there is a difference of ₹${diff}. This must be investigated and resolved before finalisation. Common causes: omitted ledgers, wrong side entries, incorrect opening balances, or unbooked adjusting entries.`,
      recommendedDisclosure: "Do NOT finalise the balance sheet until the difference is resolved. Prepare a reconciliation statement explaining the difference and correcting journal entries.",
      severity: "Critical"
    });
  } else {
    notes.push({
      category: "P&L",
      observation: `The Balance Sheet of ${entityName} is balanced for FY ${fy}. Verify Sundry Debtors and Creditors by obtaining balance confirmation letters (as per SA-505). Check that all cut-off transactions near the year-end are booked in the correct period.`,
      recommendedDisclosure: "Attach debtors/creditors ageing analysis. Note any debtors outstanding beyond 6 months for doubtful debt assessment. Confirm balances with third parties where material.",
      severity: "Info"
    });
  }

  notes.push({
    category: "Assets",
    observation: `Verify physical existence and ownership of Fixed Assets of ${entityName}. Ensure additions during FY ${fy} are properly capitalised and not expensed. Check that depreciation is computed as per the applicable method (WDV under IT Act or SLM as per accounting policy).`,
    recommendedDisclosure: "Prepare Schedule 8 – Fixed Assets with gross block, depreciation, and net block. Obtain invoices for additions. Conduct physical verification of assets.",
    severity: "Info"
  });

  notes.push({
    category: "Compliance",
    observation: `Verify GST compliance of ${entityName} — GSTR-1 vs books sales reconciliation, GSTR-3B vs ITC availed, and GSTR-2A/2B matching. Ensure TDS obligations (Section 194A, 194C, 194H, 194J etc.) are met and TDS challans are reconciled with Form 26AS / AIS.`,
    recommendedDisclosure: "Prepare GST reconciliation statement. Disclose any GST demands or TDS defaults in notes to accounts. Check MSME payment compliance (Section 43B(h)) if applicable.",
    severity: "Caution"
  });

  notes.push({
    category: "Assets",
    observation: `Closing stock of ${entityName} should be valued at cost or net realisable value (NRV), whichever is lower, as per AS-2 (Valuation of Inventories). Obtain stock statements, verify stock registers, and assess the valuation method adopted for consistency.`,
    recommendedDisclosure: "Disclose stock valuation method (FIFO/Weighted Average) in Significant Accounting Policies. If stock value differs from prior year method, disclose the change and its impact.",
    severity: "Info"
  });

  return notes;
}

// Health check endpoint
app.get("/api/health", (req, res) => {
  res.json({ status: "ok", timestamp: new Date().toISOString() });
});

// Ledger classification endpoint — fully offline rule engine
app.post("/api/ai/classify-assistant", async (req, res) => {
  try {
    const { ledgers = [], heads = [] } = req.body;

    const suggestions = ledgers
      .map((ledger: any) => classifyLedgerByRules(ledger, heads))
      .filter(Boolean);

    return res.json({
      success: true,
      suggestions,
      engine: "built-in-rule-engine",
      message: `Classified ${suggestions.length} of ${ledgers.length} ledgers using Indian GAAP rule engine.`,
    });
  } catch (error: any) {
    console.error("Classification error:", error);
    return res.status(500).json({
      success: false,
      error: error.message || "Failed to classify ledgers",
    });
  }
});

// Audit notes endpoint — fully offline template engine
app.post("/api/ai/audit-notes", async (req, res) => {
  try {
    const notes = generateAuditNotes(req.body);

    // Build a formatted summary string for the AiAssistantModal
    const entityName = (req.body.entityDetails || req.body.entity || {}).name || "the entity";
    const summary = `Audit observations generated for **${entityName}** using AccuSheet Pro's built-in Indian GAAP / ICAI rule engine.`;
    const observations = notes.map((n) => `[${n.severity.toUpperCase()}] ${n.category}: ${n.observation}`);
    const complianceNotes = notes
      .filter((n) => n.category === "Compliance" || n.recommendedDisclosure)
      .map((n) => n.recommendedDisclosure);

    return res.json({
      success: true,
      notes,
      summary,
      observations,
      complianceNotes,
      answer: notes.map((n) => `**[${n.severity}] ${n.category}**\n${n.observation}\n→ ${n.recommendedDisclosure}`).join("\n\n"),
      engine: "built-in-rule-engine",
    });
  } catch (error: any) {
    console.error("Audit notes error:", error);
    return res.status(500).json({
      success: false,
      error: error.message || "Failed to generate audit notes",
    });
  }
});

// Vite middleware for development vs static build for production
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const { createServer: createViteServer } = await import("vite");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = fs.existsSync(path.join(__dirname, "index.html"))
      ? __dirname
      : path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://127.0.0.1:${PORT}`);
  });
}

startServer();
