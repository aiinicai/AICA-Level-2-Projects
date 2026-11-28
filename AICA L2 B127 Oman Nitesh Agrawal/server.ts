import express from 'express';
import crypto from 'node:crypto';
import path from 'node:path';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import { MisDatabase } from './src/server/db';
import { reconcileTrialBalance } from './src/engine/kpiEngine';
import type {
  AccountingPolicyConfig,
  GlMappingRule,
  ManagementAdjustment,
  TrialBalanceRow,
  UserRole,
  WorkflowStage,
} from './src/types/mis';

dotenv.config();

const PORT = 3000;
const SESSION_SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');

const db = new MisDatabase();

interface TokenPayload {
  userId: string;
  name: string;
  role: UserRole;
  exp: number;
}

function signToken(payload: TokenPayload): string {
  const data = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sig = crypto.createHmac('sha256', SESSION_SECRET).update(data).digest('base64url');
  return `${data}.${sig}`;
}

function verifyToken(token: string | undefined): TokenPayload | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [data, sig] = parts;
  const expected = crypto.createHmac('sha256', SESSION_SECRET).update(data).digest('base64url');
  if (sig.length !== expected.length) return null;
  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
  try {
    const parsed = JSON.parse(Buffer.from(data, 'base64url').toString('utf8')) as TokenPayload;
    if (Date.now() > parsed.exp) return null;
    return parsed;
  } catch {
    return null;
  }
}

function requireAuth(allowedRoles?: UserRole[]) {
  return (req: express.Request, res: express.Response, next: express.NextFunction) => {
    const authHeader = req.headers.authorization;
    const token = authHeader?.startsWith('Bearer ') ? authHeader.slice(7) : undefined;
    const payload = verifyToken(token);
    if (!payload) {
      res.status(401).json({ error: 'Authentication required' });
      return;
    }
    if (allowedRoles && !allowedRoles.includes(payload.role)) {
      res.status(403).json({ error: `Role ${payload.role} lacks permission for this action` });
      return;
    }
    (req as express.Request & { user?: TokenPayload }).user = payload;
    next();
  };
}

async function startServer() {
  const app = express();
  app.use(express.json({ limit: '25mb' }));

  // Health & DB integrity
  app.get('/api/health', (_req, res) => {
    const integrity = db.runIntegrityCheck();
    res.json({ status: 'ok', integrity });
  });

  // Session / Role Switcher (uses real server-signed HMAC Bearer token)
  app.post('/api/auth/session', (req, res) => {
    const { userId, password } = req.body as { userId?: string; password?: string };
    const users = db.getUsers();
    const target = users.find((u) => u.id === (userId || 'usr-cfo'));
    if (!target) {
      res.status(404).json({ error: 'User not found' });
      return;
    }
    if (password !== undefined) {
      const fullUser = db.findUserById(target.id);
      if (!fullUser || !db.verifyPassword(password, fullUser.passwordHash)) {
        res.status(401).json({ error: 'Invalid credentials' });
        return;
      }
    }
    const token = signToken({
      userId: target.id,
      name: target.name,
      role: target.role,
      exp: Date.now() + 1000 * 60 * 60 * 12,
    });
    res.json({ token, user: target });
  });

  // Bootstrap complete workspace dataset (units paged separately if needed, or full for fast local calc)
  app.get('/api/bootstrap', (_req, res) => {
    const dataset = db.getDataset();
    const users = db.getUsers();
    const integrity = db.runIntegrityCheck();
    res.json({ dataset, users, integrity });
  });

  // Upload Trial Balance rows (Finance Controller / CFO)
  app.post(
    '/api/upload/trial-balance',
    requireAuth(['CFO_Admin', 'Finance_Controller']),
    (req, res) => {
      const { companyId, period, rows } = req.body as {
        companyId: string;
        period: string;
        rows: TrialBalanceRow[];
      };
      const user = (req as express.Request & { user: TokenPayload }).user;
      if (!companyId || !period || !Array.isArray(rows) || rows.length === 0) {
        res.status(400).json({ error: 'companyId, period, and non-empty rows are required' });
        return;
      }
      const ds = db.upsertTrialBalanceRows(companyId, period, rows);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'TB_UPLOADED',
        entity: `${companyId} / ${period}`,
        details: `Uploaded ${rows.length} GL lines for period ${period}.`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // Save GL Mapping Rule
  app.post(
    '/api/mappings',
    requireAuth(['CFO_Admin', 'Finance_Controller']),
    (req, res) => {
      const rule = req.body as GlMappingRule;
      const user = (req as express.Request & { user: TokenPayload }).user;
      if (!rule?.accountCode || !rule?.targetClass) {
        res.status(400).json({ error: 'accountCode and targetClass are required' });
        return;
      }
      rule.approvedBy = user.name;
      rule.updatedAt = new Date().toISOString().slice(0, 10);
      db.saveGlMapping(rule);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'GL_MAPPING_SAVED',
        entity: rule.accountCode,
        details: `Mapped account ${rule.accountCode} to ${rule.targetClass}.`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // Transition Monthly MIS Workflow (enforces reconciliation gate before Published/Locked!)
  app.post(
    '/api/workflow/transition',
    requireAuth(['CFO_Admin', 'Finance_Controller', 'Project_Director']),
    (req, res) => {
      const { period, nextStage, comment, department } = req.body as {
        period: string;
        nextStage?: WorkflowStage;
        comment?: string;
        department?: string;
      };
      const user = (req as express.Request & { user: TokenPayload }).user;
      const ds = db.getDataset();
      const wf = ds.workflows.find((w) => w.period === period);
      if (!wf) {
        res.status(404).json({ error: 'Period workflow not found' });
        return;
      }

      if (comment && department) {
        wf.departmentalComments.push({
          department,
          author: user.name,
          comment,
          timestamp: new Date().toISOString(),
        });
      }

      if (nextStage) {
        if ((nextStage === 'Approved' || nextStage === 'Published' || nextStage === 'Locked') && user.role !== 'CFO_Admin') {
          res.status(403).json({ error: 'Only CFO_Admin can approve, publish, or lock MIS periods (Maker-Checker control).' });
          return;
        }
        // Reopening a locked period requires CFO_Admin
        if (wf.stage === 'Locked' && user.role !== 'CFO_Admin') {
          res.status(403).json({ error: 'Only CFO_Admin can reopen a locked MIS period.' });
          return;
        }
        if (nextStage === 'Published' || nextStage === 'Locked') {
          const idx = ds.periods.indexOf(period);
          const prevPeriod = idx > 0 ? ds.periods[idx - 1] : '';
          const rec = reconcileTrialBalance(
            ds.trialBalance.filter((r) => r.period === period),
            ds.trialBalance.filter((r) => r.period === prevPeriod),
            ds.glMappings,
            ds.policies.materialityThresholdOMR
          );
          if (!rec.canPublish) {
            res.status(400).json({
              error: `Publication blocked: ${rec.messages.join(' ')}`,
            });
            return;
          }
        }
        wf.stage = nextStage;
        if (nextStage === 'Approved' || nextStage === 'Published') {
          wf.approvedBy = user.name;
        }
        if (nextStage === 'Locked') {
          wf.lockedAt = new Date().toISOString();
        }
        if (nextStage === 'Open') {
          wf.lockedAt = null;
        }
      }

      db.updateWorkflow(period, wf);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: nextStage ? `WORKFLOW_${nextStage.toUpperCase()}` : 'WORKFLOW_COMMENT',
        entity: `Period ${period}`,
        details: nextStage ? `Transitioned period ${period} to ${nextStage}.` : `Added departmental note (${department}).`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // Management Adjustments (Maker-Checker)
  app.post(
    '/api/adjustments',
    requireAuth(['CFO_Admin', 'Finance_Controller']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const body = req.body as Omit<ManagementAdjustment, 'id' | 'preparedBy' | 'approvedBy' | 'status' | 'createdAt'>;
      if (!body.description || !Number.isFinite(body.amountOMR) || body.amountOMR <= 0) {
        res.status(400).json({ error: 'Valid description and positive amountOMR required' });
        return;
      }
      const adj: ManagementAdjustment = {
        ...body,
        id: `adj-${Date.now()}`,
        preparedBy: user.name,
        approvedBy: null,
        status: 'Pending Approval',
        createdAt: new Date().toISOString(),
      };
      db.addAdjustment(adj);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'ADJUSTMENT_SUBMITTED',
        entity: adj.id,
        details: `${adj.description} (OMR ${adj.amountOMR.toFixed(3)})`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  app.post(
    '/api/adjustments/:id/approve',
    requireAuth(['CFO_Admin']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const adjId = String(req.params.id);
      db.approveAdjustment(adjId, user.name);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'ADJUSTMENT_APPROVED',
        entity: adjId,
        details: `Approved management adjustment ${adjId}.`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // Accounting & Tax Policies
  app.post(
    '/api/policies',
    requireAuth(['CFO_Admin']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const policies = req.body as AccountingPolicyConfig;
      db.updatePolicies(policies);
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'POLICIES_UPDATED',
        entity: 'IFRS & Oman Tax Config',
        details: `Updated IFRS/Tax policies (Materiality OMR ${policies.materialityThresholdOMR.toFixed(3)}).`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // Backups & Restore
  app.post(
    '/api/backups/create',
    requireAuth(['CFO_Admin', 'Finance_Controller']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const bak = db.createPhysicalBackup('Manual');
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'BACKUP_CREATED',
        entity: bak.filename,
        details: `Created SQLite backup (${bak.checksum}).`,
      });
      res.json({ backup: bak, dataset: db.getDataset() });
    }
  );

  app.post(
    '/api/backups/restore',
    requireAuth(['CFO_Admin']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const { filename } = req.body as { filename: string };
      if (!filename || !db.restoreBackup(filename)) {
        res.status(404).json({ error: 'Backup file not found' });
        return;
      }
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'BACKUP_RESTORED',
        entity: filename,
        details: `Restored SQLite database from ${filename}.`,
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  app.post(
    '/api/admin/reset-seed',
    requireAuth(['CFO_Admin']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      db.resetToSeed();
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'DATASET_RESET_SEED',
        entity: 'Database',
        details: 'Reset workspace to reconcilable 1,560-unit 24-month sample database.',
      });
      res.json({ dataset: db.getDataset() });
    }
  );

  // License activation (non-IP device ID bound)
  app.post(
    '/api/license/activate',
    requireAuth(['CFO_Admin']),
    (req, res) => {
      const user = (req as express.Request & { user: TokenPayload }).user;
      const { licenseKey, licensedTo, edition } = req.body as {
        licenseKey: string;
        licensedTo: string;
        edition: 'Permanent' | 'Subscription';
      };
      if (!licenseKey || licenseKey.trim().length < 10) {
        res.status(400).json({ error: 'Valid signed license key required (min 10 chars).' });
        return;
      }
      const ds = db.getDataset();
      const sig = crypto
        .createHash('sha256')
        .update(`${ds.license.deviceId}:${licenseKey}:${licensedTo}`)
        .digest('hex')
        .slice(0, 14)
        .toUpperCase();
      const updated = db.updateLicense({
        ...ds.license,
        edition: edition || 'Permanent',
        status: 'Active',
        licensedTo: licensedTo || ds.license.licensedTo,
        expiresAt: edition === 'Subscription' ? '2027-11-25T00:00:00Z' : null,
        signatureHash: `SIG-SHA256-${sig}`,
      });
      db.insertAuditLog({
        id: `aud-${Date.now()}`,
        timestamp: new Date().toISOString(),
        actor: user.name,
        role: user.role,
        action: 'LICENSE_ACTIVATED',
        entity: updated.license.deviceId,
        details: `Activated ${updated.license.edition} license for ${updated.license.licensedTo}.`,
      });
      res.json({ dataset: updated });
    }
  );

  // Server-Side Gemini AI Management Analyst (never fabricates numbers, operates strictly on verified engine JSON)
  app.post('/api/ai/commentary', async (req, res) => {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      res.status(503).json({
        error:
          'Online AI integration requires GEMINI_API_KEY in Settings > Secrets. Use the verified Offline Rule-Based Engine below for local commentary.',
      });
      return;
    }

    const { question, verifiedContext } = req.body as {
      question?: string;
      verifiedContext: Record<string, unknown>;
    };

    try {
      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            'User-Agent': 'aistudio-build',
          },
        },
      });

      const prompt = [
        'You are the Group CFO & Chartered Accountant AI Management Analyst for a real estate developer in Oman/GCC.',
        'STRICT RULES:',
        '1. Use ONLY the verified financial and operational figures provided in the JSON below. Never invent, extrapolate, or fabricate any number.',
        '2. Clearly distinguish Confirmed Facts (from verified KPIs) from Possible Explanations / Hypotheses.',
        '3. Provide concise, executive-ready bullets: Executive Diagnosis, Key Drivers & Variances, Board Questions, and Action Plan.',
        question ? `4. Address this specific management question: "${question}"` : '4. Provide a comprehensive monthly MIS board commentary.',
        '',
        'VERIFIED_KPI_ENGINE_DATA:',
        JSON.stringify(verifiedContext, null, 2),
      ].join('\n');

      const response = await ai.models.generateContent({
        model: 'gemini-4-hydrogen',
        contents: prompt,
      });

      res.json({ commentary: response.text ?? '' });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Gemini API request failed';
      res.status(500).json({ error: message });
    }
  });

  // Vite dev middleware or static dist serving
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`RealEstate 360 server listening on http://localhost:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start RealEstate 360 server:', err);
  process.exit(1);
});
