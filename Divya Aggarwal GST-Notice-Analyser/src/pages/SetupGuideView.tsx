import React from 'react';
import { BookOpen, ShieldCheck, FileText, FileSpreadsheet, Scale, KeyRound } from 'lucide-react';

export const SetupGuideView: React.FC = () => {
  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full bg-[#F8FAFC]">
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-2xs flex items-center gap-3">
        <div className="p-3 bg-indigo-50 text-[#4338CA] rounded-xl border border-indigo-200">
          <BookOpen className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-base font-bold text-slate-900">How this workstation works</h1>
          <p className="text-xs text-slate-500">
            Extraction options, data privacy, and the GST defence references built in.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <FileText className="w-5 h-5 text-[#4338CA]" />
            <span>Extract a notice using Claude.ai (free)</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            No API key or credits needed — this uses your existing Claude.ai subscription:
          </p>
          <ol className="text-xs text-slate-700 space-y-1.5 list-decimal list-inside bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
            <li>Click <strong>Add Notice</strong>, choose <strong>Use Claude.ai</strong>, upload the PDF or paste the text.</li>
            <li>Click <strong>Copy prompt for Claude.ai</strong>.</li>
            <li>Open claude.ai, attach the same notice PDF, paste the prompt, send.</li>
            <li>Copy Claude's whole reply and paste it back into the app.</li>
            <li>Review, then <strong>Save to client record</strong>.</li>
          </ol>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <KeyRound className="w-5 h-5 text-[#4338CA]" />
            <span>Extract automatically with a Claude API key</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Optional. One click per notice, but billed against prepaid Anthropic API credits
            (a Claude.ai subscription does not fund the API).
          </p>
          <ul className="text-xs text-slate-700 space-y-1.5 list-disc list-inside bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
            <li>Add credits and create a key at console.anthropic.com.</li>
            <li>Paste it in <strong>Settings &rarr; Claude API Key</strong> and click <strong>Test key</strong>.</li>
            <li>If it reports <em>&ldquo;anthropic-workspace-id is required&rdquo;</em>, also paste your Workspace ID.</li>
          </ul>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            <span>Where your data lives</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            Every client, notice, reconciliation and document record is stored in your firm's private
            database. Only signed-in members of your firm can see it.
          </p>
          <ul className="text-xs text-slate-700 space-y-1.5 list-disc list-inside bg-emerald-50/50 p-3 rounded-xl border border-emerald-200 text-emerald-950">
            <li>Access is scoped per firm — one firm can never see another's data.</li>
            <li>Word and Excel files are generated in your browser, not on a server.</li>
            <li>Notice content is sent to Claude only when you choose to extract a notice.</li>
            <li>Sign out on shared machines; the session stays on the device otherwise.</li>
          </ul>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-3">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <Scale className="w-5 h-5 text-blue-700" />
            <span>Circular 183/2022 &amp; 193/2023 — ITC mismatch defence</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            For notices on differences between <strong>GSTR-3B Table 4(A)(5)</strong> and <strong>GSTR-2A/2B</strong>
            for FY 2017-18 to FY 2022-23:
          </p>
          <div className="text-xs text-slate-700 space-y-1.5 bg-blue-50/50 p-3 rounded-xl border border-blue-200 leading-relaxed">
            <div><strong>Difference up to &#8377;5,00,000:</strong> supplier certificate / self-declaration certifying payment of tax to the exchequer.</div>
            <div><strong>Difference above &#8377;5,00,000:</strong> CA / Cost Accountant certificate with UDIN from the supplier's CA.</div>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs space-y-3 col-span-2">
          <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
            <FileSpreadsheet className="w-5 h-5 text-amber-700" />
            <span>Importing your firm's own tracker spreadsheets</span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            The <strong>Import Firm Excel/CSV</strong> button in Document Tracker reads any layout — it auto-detects
            columns for document name, category, period, due date, remarks and status, and lets you confirm the
            mapping before importing the rows.
          </p>
        </div>
      </div>
    </div>
  );
};
