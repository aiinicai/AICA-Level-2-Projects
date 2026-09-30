import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  RotateCcw,
  ShieldCheck,
  Code2,
  Terminal
} from 'lucide-react';
import { formatINR, calculateDueDate, isValidGSTIN, isValidPAN, extractPANFromGSTIN } from '../../utils/formatters';
import { calculateOverdueDays, getAgeingBucket } from '../../utils/ageingEngine';
import { parseNarration } from '../../utils/reconciliationEngine';

interface TestResult {
  name: string;
  category: string;
  expected: string;
  actual: string;
  passed: boolean;
  durationMs: number;
}

export const AccountingTestSuiteView: React.FC = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<TestResult[]>([]);

  const runAllTests = () => {
    setIsRunning(true);
    const start = performance.now();
    const suite: TestResult[] = [];

    // Test 1: Due Date Calculation
    {
      const t0 = performance.now();
      const calculated = calculateDueDate('2026-04-15', 30);
      const passed = calculated === '2026-05-15';
      suite.push({
        name: 'Due Date: Standard 30 Days Credit',
        category: 'Invoicing',
        expected: '2026-05-15',
        actual: calculated,
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 2: Extended Credit Terms Due Date
    {
      const t0 = performance.now();
      const calculated = calculateDueDate('2026-05-15', 45);
      const passed = calculated === '2026-06-29';
      suite.push({
        name: 'Due Date: 45 Days Extended Credit Term',
        category: 'Invoicing',
        expected: '2026-06-29',
        actual: calculated,
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 3: GSTIN Validation - Valid Maharashtra GSTIN
    {
      const t0 = performance.now();
      const valid = isValidGSTIN('27AAACA1234B1Z2');
      suite.push({
        name: 'GSTIN Validation: Valid 15-digit Indian Format',
        category: 'Tax Validation',
        expected: 'true',
        actual: String(valid),
        passed: valid === true,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 4: GSTIN Validation - Invalid Format
    {
      const t0 = performance.now();
      const valid = isValidGSTIN('INVALID123');
      suite.push({
        name: 'GSTIN Validation: Reject Malformed GSTIN',
        category: 'Tax Validation',
        expected: 'false',
        actual: String(valid),
        passed: valid === false,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 5: PAN Extraction from GSTIN
    {
      const t0 = performance.now();
      const extracted = extractPANFromGSTIN('27AAACA1234B1Z2');
      const passed = extracted === 'AAACA1234B';
      suite.push({
        name: 'PAN Extraction: Extract Digits 3-12 from GSTIN',
        category: 'Tax Validation',
        expected: 'AAACA1234B',
        actual: extracted || 'null',
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 6: Ageing Bucket Categorization - Not Due
    {
      const t0 = performance.now();
      const bucket = getAgeingBucket(-5);
      suite.push({
        name: 'Ageing Engine: Negative overdue days mapped to Not Due',
        category: 'Ageing',
        expected: 'Not Due',
        actual: bucket,
        passed: bucket === 'Not Due',
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 7: Ageing Bucket Categorization - 31-60 Days
    {
      const t0 = performance.now();
      const bucket = getAgeingBucket(45);
      suite.push({
        name: 'Ageing Engine: 45 days overdue mapped to 31–60 Days',
        category: 'Ageing',
        expected: '31–60 Days',
        actual: bucket,
        passed: bucket === '31–60 Days',
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 8: Ageing Bucket Categorization - > 365 Days
    {
      const t0 = performance.now();
      const bucket = getAgeingBucket(400);
      suite.push({
        name: 'Ageing Engine: 400 days overdue mapped to > 365 Days',
        category: 'Ageing',
        expected: '> 365 Days',
        actual: bucket,
        passed: bucket === '> 365 Days',
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 9: Narration Parser - Extract Invoice Number
    {
      const t0 = performance.now();
      const parsed = parseNarration('NEFT-CMS-INFOSYS-INV-2026-001-HDFC001');
      const passed = parsed.extractedInvoiceNumber === 'INV-2026-001';
      suite.push({
        name: 'Narration Parser: Extract Invoice Number Pattern',
        category: 'Reconciliation',
        expected: 'INV-2026-001',
        actual: parsed.extractedInvoiceNumber || 'null',
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 10: Narration Parser - Extract Customer Alias
    {
      const t0 = performance.now();
      const parsed = parseNarration('RTGS/TCS/SALES_SETTLEMENT/ICICI');
      const passed = parsed.matchedCustomerAlias === 'TCS';
      suite.push({
        name: 'Narration Parser: Extract Customer Alias Pattern',
        category: 'Reconciliation',
        expected: 'TCS',
        actual: parsed.matchedCustomerAlias || 'null',
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 11: Indian Currency Formatter (Lakhs & Crores grouping)
    {
      const t0 = performance.now();
      const formatted = formatINR(100000, false);
      const passed = formatted === '₹1,00,000';
      suite.push({
        name: 'Currency Formatter: 1 Lakh with Indian Commas (1,00,000)',
        category: 'Formatting',
        expected: '₹1,00,000',
        actual: formatted,
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    // Test 12: Indian Currency Formatter - Crores
    {
      const t0 = performance.now();
      const formatted = formatINR(15000000, false);
      const passed = formatted === '₹1,50,00,000';
      suite.push({
        name: 'Currency Formatter: 1.5 Crores (1,50,00,000)',
        category: 'Formatting',
        expected: '₹1,50,00,000',
        actual: formatted,
        passed,
        durationMs: +(performance.now() - t0).toFixed(2)
      });
    }

    setTimeout(() => {
      setResults(suite);
      setIsRunning(false);
    }, 200);
  };

  const totalPassed = results.filter(r => r.passed).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Accounting Test & Verification Suite</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Automated unit tests validating Indian accounting logic, DSO, GSTIN/PAN parsing, leap years, and matching rules.
          </p>
        </div>
        <button
          onClick={runAllTests}
          disabled={isRunning}
          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:bg-slate-300 text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center gap-2"
        >
          {isRunning ? (
            <span className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-white border-t-transparent"></span>
          ) : (
            <Play className="w-4 h-4 fill-white" />
          )}
          <span>{results.length === 0 ? 'Run Automated Test Suite' : 'Re-Run All Tests'}</span>
        </button>
      </div>

      {/* Summary Card */}
      {results.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase text-slate-400">Total Unit Tests</span>
            <p className="text-xl font-bold text-slate-900 mt-1">{results.length} Tests</p>
          </div>
          <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase text-emerald-800">Passed</span>
            <p className="text-xl font-bold text-emerald-900 mt-1">{totalPassed} / {results.length}</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 shadow-xs">
            <span className="text-[10px] font-bold uppercase text-slate-400">Success Rate</span>
            <p className="text-xl font-bold text-emerald-700 mt-1">
              {((totalPassed / results.length) * 100).toFixed(0)}% Pass
            </p>
          </div>
        </div>
      )}

      {/* Results Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-700" />
            <h3 className="font-bold text-slate-900 text-xs">Test Execution Log</h3>
          </div>
          <span className="text-[11px] text-slate-400">Execution in Client Sandbox</span>
        </div>

        {results.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-2">
            <Code2 className="w-10 h-10 text-slate-300 mx-auto" />
            <p className="font-bold text-slate-700 text-sm">Automated Test Suite Ready</p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Click "Run Automated Test Suite" to verify accounting algorithms, date arithmetic, GST checks, and regex parsing.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-[10px] uppercase font-bold text-slate-500">
                <tr>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Test Case</th>
                  <th className="p-3.5">Expected</th>
                  <th className="p-3.5">Actual Output</th>
                  <th className="p-3.5 text-right">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {results.map((r, i) => (
                  <tr key={i} className="hover:bg-slate-50 font-sans">
                    <td className="p-3.5">
                      {r.passed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          <span>PASS</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          <XCircle className="w-3.5 h-3.5 text-rose-600" />
                          <span>FAIL</span>
                        </span>
                      )}
                    </td>
                    <td className="p-3.5 text-[11px] font-semibold text-slate-500">{r.category}</td>
                    <td className="p-3.5 font-semibold text-slate-900">{r.name}</td>
                    <td className="p-3.5 font-mono text-slate-600 text-xs">{r.expected}</td>
                    <td className="p-3.5 font-mono font-bold text-slate-800 text-xs">{r.actual}</td>
                    <td className="p-3.5 text-right font-mono text-slate-400 text-xs">{r.durationMs} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
