import React, { useState } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  FileText, 
  ShieldCheck, 
  Layers, 
  Plus, 
  Loader2,
  FileCheck2,
  Lock
} from 'lucide-react';
import { CapexItem, CapitalisationReviewResult } from '../types';
import { reviewCapitalisationWithAI } from '../services/aiService';
import { formatINR } from '../services/reliabilityScore';

interface AiCapitalisationReviewProps {
  capexQueue: CapexItem[];
  setCapexQueue: React.Dispatch<React.SetStateAction<CapexItem[]>>;
  currencyMode: 'Lakhs' | 'Crores' | 'Full';
  onAddCapitalisedAsset?: (newItem: CapexItem, review: CapitalisationReviewResult) => void;
}

export const AiCapitalisationReview: React.FC<AiCapitalisationReviewProps> = ({
  capexQueue,
  setCapexQueue,
  currencyMode,
  onAddCapitalisedAsset
}) => {
  const [selectedItem, setSelectedItem] = useState<CapexItem>(capexQueue[0] || null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [reviewResult, setReviewResult] = useState<CapitalisationReviewResult | null>(
    capexQueue[0]?.aiRecommendation || null
  );

  // Custom Test Modal
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customDescription, setCustomDescription] = useState(
    'Supply and erection of 250 kW Rooftop Solar PV System with 10-Year Inverter Warranty, bi-directional net metering panel & structural mounting frames'
  );
  const [customAmount, setCustomAmount] = useState('2450000');
  const [customVendor, setCustomVendor] = useState('Tata Power Solar Systems Ltd.');
  const [customPO, setCustomPO] = useState('PO-2024-SOLAR-091');

  // Human Decision State
  const [humanDecision, setHumanDecision] = useState<'Capitalise' | 'Expense' | 'Componentise' | 'Return to Vendor'>('Capitalise');
  const [approverName, setApproverName] = useState('Pooja Iyer (Lead Controller)');
  const [approverRemarks, setApproverRemarks] = useState('Reviewed technical installation report; approved capitalisation split under Ind AS 16.');
  const [isApprovedMessage, setIsApprovedMessage] = useState<string | null>(null);

  const handleSelectCapex = (item: CapexItem) => {
    setSelectedItem(item);
    setReviewResult(item.aiRecommendation || null);
    setIsApprovedMessage(null);
  };

  const handleRunAiAnalysis = async (itemToAnalyze: CapexItem = selectedItem) => {
    if (!itemToAnalyze) return;
    setIsAnalyzing(true);
    setIsApprovedMessage(null);
    try {
      const result = await reviewCapitalisationWithAI(itemToAnalyze);
      setReviewResult(result);
      // update state
      setCapexQueue((prev) =>
        prev.map((it) => (it.id === itemToAnalyze.id ? { ...it, aiRecommendation: result, status: 'Reviewed - Needs Approval' } : it))
      );
    } catch (err) {
      console.error('Error analyzing transaction:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApplyHumanApproval = () => {
    if (!selectedItem || !reviewResult) return;

    const updatedItem: CapexItem = {
      ...selectedItem,
      status: humanDecision === 'Expense' ? 'Expensed' : 'Approved & Capitalised',
      humanApproval: {
        approver: approverName,
        role: 'Lead Controller',
        decision: humanDecision,
        timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
        remarks: approverRemarks
      }
    };

    setCapexQueue((prev) => prev.map((it) => (it.id === selectedItem.id ? updatedItem : it)));
    setSelectedItem(updatedItem);
    setIsApprovedMessage(`Accounting treatment recorded: ${humanDecision} approved by ${approverName}.`);

    if (onAddCapitalisedAsset && (humanDecision === 'Capitalise' || humanDecision === 'Componentise')) {
      onAddCapitalisedAsset(updatedItem, reviewResult);
    }
  };

  const handleCreateCustomTest = () => {
    const newItem: CapexItem = {
      id: `CPX-TEST-${Date.now().toString().slice(-4)}`,
      poNumber: customPO,
      invoiceNumber: `INV-CUSTOM-${Math.floor(1000 + Math.random() * 9000)}`,
      vendor: customVendor,
      description: customDescription,
      amountINR: parseFloat(customAmount) || 1000000,
      invoiceDate: new Date().toISOString().split('T')[0],
      plant: 'Pune Plant - Chakan',
      department: 'Infrastructure Projects',
      grnStatus: 'Complete',
      technicalInspection: 'Passed',
      suggestedCategory: 'Plant & Machinery',
      status: 'Pending AI Review'
    };

    setCapexQueue((prev) => [newItem, ...prev]);
    setSelectedItem(newItem);
    setShowCustomModal(false);
    handleRunAiAnalysis(newItem);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-blue-600">
            <Sparkles className="w-4 h-4 text-blue-600" />
            <span>Ind AS 16 / Ind AS 38 / Schedule II Accounting Engine</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-1">
            AI Capitalisation Review & Policy Memo Engine
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Evaluate POs, invoices, and GRNs for Capitalise vs. Expense treatment, componentisation, useful life, and Section 17(5) GST ITC eligibility.
          </p>
        </div>

        <button
          onClick={() => setShowCustomModal(true)}
          className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-xs self-start md:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Test Custom Procurement Invoice</span>
        </button>
      </div>

      {/* Main Grid: Pending Queue (Left) & AI Review & Approval Workspace (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Capex Pending Queue (4 Cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Procurement Review Queue ({capexQueue.length})
            </span>
            <span className="text-[11px] text-slate-400">Click to evaluate</span>
          </div>

          <div className="space-y-2.5">
            {capexQueue.map((item) => {
              const isSelected = selectedItem?.id === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => handleSelectCapex(item)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-blue-50/70 border-blue-500 shadow-sm ring-1 ring-blue-500/20'
                      : 'bg-white border-slate-200 hover:border-slate-300 shadow-2xs'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-blue-700">
                      {item.poNumber}
                    </span>
                    <span className="font-mono text-xs font-bold text-slate-900">
                      {formatINR(item.amountINR, currencyMode)}
                    </span>
                  </div>

                  <h4 className="text-xs font-semibold text-slate-800 mt-1 line-clamp-2" title={item.description}>
                    {item.description}
                  </h4>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
                    <span className="truncate max-w-[150px]">{item.vendor}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.status === 'Approved & Capitalised'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : item.status === 'Expensed'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : item.status === 'Reviewed - Needs Approval'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-slate-100 text-slate-600 border border-slate-200'
                    }`}>
                      {item.status}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: AI Analysis Workspace (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          {selectedItem ? (
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
              
              {/* Selected Transaction Summary Card */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200 gap-2">
                  <div>
                    <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">Selected Procurement Transaction</span>
                    <h3 className="text-base font-bold text-slate-900">{selectedItem.vendor}</h3>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-slate-500 block">Invoice Value</span>
                    <span className="text-lg font-bold text-slate-900 font-mono">
                      {formatINR(selectedItem.amountINR, currencyMode)}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mt-3">
                  <div>
                    <span className="text-slate-500 text-[11px] block">PO Number:</span>
                    <span className="font-mono font-semibold text-slate-800">{selectedItem.poNumber}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Invoice No:</span>
                    <span className="font-mono font-semibold text-slate-800">{selectedItem.invoiceNumber}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Invoice Date:</span>
                    <span className="font-mono text-slate-800">{selectedItem.invoiceDate}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Plant Unit:</span>
                    <span className="text-slate-800 truncate block">{selectedItem.plant.split(' - ')[0]}</span>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-200 text-xs">
                  <span className="text-slate-500 block text-[11px] mb-0.5">PO Scope / Description:</span>
                  <p className="text-slate-800 font-medium">{selectedItem.description}</p>
                </div>

                {/* Run AI Button */}
                <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs text-slate-500">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>Evaluates Ind AS 16, Sch II, & CGST Sec 17(5)</span>
                  </div>
                  <button
                    onClick={() => handleRunAiAnalysis(selectedItem)}
                    disabled={isAnalyzing}
                    className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:bg-slate-300 text-white text-xs font-semibold flex items-center space-x-2 transition-all shadow-xs"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Evaluating Technical Standard...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 text-blue-400" />
                        <span>Run AI Capitalisation Review</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* AI Structured Review Output */}
              {reviewResult ? (
                <div className="space-y-4 animate-in fade-in duration-300">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                      <Sparkles className="w-4 h-4 text-blue-600" />
                      <span>AI Accounting Assessment & Recommendation</span>
                    </h3>
                    <span className="text-xs text-slate-500 font-mono">
                      Confidence: <strong className="text-emerald-700 font-bold">{Math.round(reviewResult.confidenceScore * 100)}%</strong>
                    </span>
                  </div>

                  {/* Top Recommendation Banner */}
                  <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    reviewResult.recommendation === 'Capitalise' || reviewResult.recommendation === 'Mixed / Componentise'
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                      : 'bg-rose-50 border-rose-200 text-rose-900'
                  }`}>
                    <div>
                      <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">
                        Recommended Accounting Treatment
                      </span>
                      <div className="text-lg font-bold mt-0.5">
                        {reviewResult.recommendation === 'Capitalise'
                          ? 'Capitalise as Fixed Asset (PPE)'
                          : reviewResult.recommendation === 'Mixed / Componentise'
                          ? 'Componentise & Capitalise (Ind AS 16)'
                          : 'Charge to Profit & Loss (Operating Expense)'}
                      </div>
                      <span className="text-xs opacity-90 block mt-0.5">
                        Policy Standard: <strong>{reviewResult.policyReference}</strong>
                      </span>
                    </div>

                    <div className="text-right sm:border-l sm:border-emerald-300 sm:pl-4">
                      <span className="text-[10px] uppercase font-semibold opacity-80 block">Recommended Life</span>
                      <span className="text-base font-bold font-mono text-slate-900">
                        {reviewResult.usefulLifeYears > 1 ? `${reviewResult.usefulLifeYears} Years` : 'Current Year P&L'}
                      </span>
                    </div>
                  </div>

                  {/* Technical Reasoning & Extracted Evidence */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                      <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                        Technical Accounting Reasoning
                      </span>
                      <p className="text-slate-700 leading-relaxed">
                        {reviewResult.reasoning}
                      </p>
                    </div>

                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                      <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] block">
                        Extracted Contractual Evidence
                      </span>
                      <ul className="space-y-1.5 text-slate-700">
                        {reviewResult.evidenceKeyPoints?.map((ev, i) => (
                          <li key={i} className="flex items-start space-x-1.5">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                            <span>{ev}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Componentisation Breakdown (If applicable) */}
                  {reviewResult.componentisationDetails && reviewResult.componentisationDetails.length > 0 && (
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                          <Layers className="w-3.5 h-3.5 text-blue-600" />
                          <span>Recommended Ind AS 16 Component Split</span>
                        </span>
                        <span className="text-[10px] text-slate-500">Para 43 Componentisation</span>
                      </div>

                      <div className="space-y-2">
                        {reviewResult.componentisationDetails.map((cmp, idx) => (
                          <div key={idx} className="bg-white border border-slate-200 p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs shadow-2xs">
                            <div>
                              <span className="font-bold text-slate-900">{cmp.name}</span>
                              <span className="text-slate-500 block text-[11px] mt-0.5">{cmp.justification}</span>
                            </div>
                            <div className="flex items-center space-x-4 shrink-0">
                              <span className="font-mono text-slate-600">Share: {cmp.costRatioPct}%</span>
                              <span className="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                                Life: {cmp.usefulLifeYears} Years
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* GST & Section 17(5) Assessment */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                        GST Input Tax Credit (ITC) & Tax Assessment
                      </span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                        reviewResult.gstItcEligibility === 'Eligible'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}>
                        {reviewResult.gstItcEligibility}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700">{reviewResult.gstAnalysis}</p>
                  </div>

                  {/* Mandatory Human-in-the-Loop Approval Decision */}
                  <div className="bg-slate-50 border border-amber-300 rounded-xl p-5 space-y-4 shadow-2xs">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Lock className="w-4 h-4 text-amber-600" />
                        <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                          Human Decision & Sign-Off (Mandatory Governance)
                        </h4>
                      </div>
                      <span className="text-[10px] text-slate-500">SOX / Internal Control Requirement</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                      <div>
                        <label className="text-slate-600 block mb-1 font-semibold">Accounting Decision:</label>
                        <select
                          value={humanDecision}
                          onChange={(e) => setHumanDecision(e.target.value as any)}
                          className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                        >
                          <option value="Capitalise">Approve Capitalisation (Full Asset)</option>
                          <option value="Componentise">Approve with Ind AS 16 Component Split</option>
                          <option value="Expense">Approve Expensing (Charge to P&L)</option>
                          <option value="Return to Vendor">Return for Documentation Revision</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-slate-600 block mb-1 font-semibold">Signing Controller / Authority:</label>
                        <input
                          type="text"
                          value={approverName}
                          onChange={(e) => setApproverName(e.target.value)}
                          className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="text-slate-600 block mb-1 text-xs font-semibold">Approval Justification & Memo Notes:</label>
                      <textarea
                        value={approverRemarks}
                        onChange={(e) => setApproverRemarks(e.target.value)}
                        rows={2}
                        className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 shadow-2xs"
                      />
                    </div>

                    <div className="flex items-center justify-between pt-2">
                      <span className="text-[11px] text-slate-500">
                        Creates an immutable audit trail entry in Fixed Asset Governance Log.
                      </span>
                      <button
                        onClick={handleApplyHumanApproval}
                        className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs flex items-center space-x-2 transition-all shadow-xs"
                      >
                        <FileCheck2 className="w-4 h-4" />
                        <span>Sign & Post Accounting Memo</span>
                      </button>
                    </div>

                    {isApprovedMessage && (
                      <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        <span>{isApprovedMessage}</span>
                      </div>
                    )}
                  </div>

                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-slate-500">
                  <Sparkles className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                  <p className="font-semibold text-slate-800">No Review Run Yet</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Click "Run AI Capitalisation Review" above to evaluate this procurement transaction.
                  </p>
                </div>
              )}

            </div>
          ) : (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 shadow-sm">
              <FileText className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <p className="font-bold text-slate-800">Select a Procurement Transaction</p>
              <p className="text-xs text-slate-500 mt-1">Select an item from the left queue to begin review.</p>
            </div>
          )}
        </div>

      </div>

      {/* Modal: Custom Invoice Test */}
      {showCustomModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-xl p-6 shadow-2xl space-y-4 text-slate-800 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-blue-600" />
                <span>Test Custom Procurement Transaction</span>
              </h3>
              <button
                onClick={() => setShowCustomModal(false)}
                className="text-slate-400 hover:text-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-700 block mb-1 font-semibold">Vendor Name:</label>
                <input
                  type="text"
                  value={customVendor}
                  onChange={(e) => setCustomVendor(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-700 block mb-1 font-semibold">PO Number:</label>
                  <input
                    type="text"
                    value={customPO}
                    onChange={(e) => setCustomPO(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 font-mono shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
                <div>
                  <label className="text-slate-700 block mb-1 font-semibold">Amount (INR):</label>
                  <input
                    type="number"
                    value={customAmount}
                    onChange={(e) => setCustomAmount(e.target.value)}
                    className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 font-mono shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-700 block mb-1 font-semibold">PO / Invoice Description:</label>
                <textarea
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  rows={3}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-slate-900 shadow-2xs focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-200">
              <button
                onClick={() => setShowCustomModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCustomTest}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold flex items-center space-x-2 shadow-xs"
              >
                <Sparkles className="w-4 h-4 text-blue-400" />
                <span>Evaluate with AI</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
