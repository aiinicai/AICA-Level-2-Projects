import React from 'react';
import { Cpu, Check, X, Shield, Star } from 'lucide-react';

export const StackComparison: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-2 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-slate-900" />
          Technical Stack Comparison & Evaluation
        </h3>
        <p className="text-sm text-slate-500 mb-6">
          Evaluation of viable architectural foundations against GTD and OmniFocus requirements.
        </p>

        {/* Comparison Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-xs divide-y divide-slate-200">
            <thead className="bg-slate-50 text-slate-700 font-semibold">
              <tr>
                <th className="py-3 px-4">Evaluation Criteria</th>
                <th className="py-3 px-4 bg-emerald-50/70 border-x border-emerald-100 text-emerald-950 font-bold">
                  Recommended: TypeScript + React + Local Storage
                </th>
                <th className="py-3 px-4">Python 3.11+ / PyQt6 + SQLite</th>
                <th className="py-3 px-4">Tauri / Electron Desktop Wrapper</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-sans">
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">Instant AI Studio & Web Preview</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ Instant zero-install interactive preview in browser
                </td>
                <td className="py-3 px-4 text-slate-500">
                  ✗ Requires headless X11 / virtual display or local pip install
                </td>
                <td className="py-3 px-4 text-slate-500">
                  ✓ Web code runs in browser; desktop packaging in Phase 6
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">Local-First Offline Reliability</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ 100% offline via IndexedDB / Web SQL / WASM SQLite
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ Native SQLite database file
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ Native SQLite or local storage
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">Keyboard & Sub-3s Quick Entry</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ Global app hotkeys, modal entry dialog, quick-capture bar
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ OS-level global hotkey listener
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ OS-level hotkey via Tauri/Electron IPC
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">UI Calmness & Typography (Anti-Slop)</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ Tailwind CSS + Plus Jakarta Sans + clean zero-pill aesthetics
                </td>
                <td className="py-3 px-4 text-slate-500">
                  △ QSS styling can be brittle across OS versions
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ Same clean CSS as web
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">Cross-Device Portability</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ Desktop, tablet, mobile browser, PWA installable
                </td>
                <td className="py-3 px-4 text-slate-500">
                  ✗ Desktop only (no mobile/tablet companion)
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ Tauri mobile or desktop
                </td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-medium text-slate-900">Code Clarity for Beginner/Intermediate</td>
                <td className="py-3 px-4 bg-emerald-50/30 border-x border-emerald-100 text-emerald-700 font-medium">
                  ✓ Standard TypeScript interfaces, transparent hooks, no magic
                </td>
                <td className="py-3 px-4 text-slate-600">
                  ✓ Standard Python + SQLAlchemy models
                </td>
                <td className="py-3 px-4 text-slate-500">
                  △ Added build complexity (Rust or Node IPC)
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Final Recommendation Box */}
        <div className="mt-6 p-5 bg-slate-900 text-white rounded-xl space-y-3">
          <div className="flex items-center gap-2 font-bold text-sm text-emerald-400">
            <Star className="w-4 h-4 fill-emerald-400" />
            Architectural Recommendation: TypeScript + React + Local Storage
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            By building Phase 1–5 in <strong>TypeScript + React</strong> with a modular local storage adapter, you receive an immediate, tactile, interactive application right here in this environment. All data resides securely in your local browser storage with instant JSON/CSV export to prevent vendor lock-in. If you want a standalone native desktop executable in Phase 6, we can wrap the codebase into a <strong>Tauri</strong> app (lightweight Rust shell using the system webview) without rewriting a single line of business logic or UI.
          </p>
        </div>
      </div>
    </div>
  );
};
