import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Department, LineItem, Priority, SubmissionStatus } from '../types';
import {
  formatINR,
  formatAUD,
  convertInrToAud,
  formatVariance,
  formatIST,
  formatDate,
} from '../utils/formatters';
import {
  Plus,
  Trash2,
  Save,
  Send,
  RotateCcw,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Lock,
  TrendingUp,
  Info,
  Calendar,
  Layers,
  Sparkles,
  HelpCircle,
  FileCheck,
} from 'lucide-react';

interface DepartmentFormProps {
  departmentOverride?: Department;
}

export const DepartmentForm: React.FC<DepartmentFormProps> = ({ departmentOverride }) => {
  const {
    currentUser,
    activeMonth,
    activeMonthId,
    submissions,
    categories,
    currencyMode,
    saveDepartmentDraft,
    submitDepartmentRequirements,
    recallDepartmentSubmission,
    getPriorMonthSubmission,
    months,
  } = useApp();

  // Department being edited
  const targetDept: Department = departmentOverride || currentUser.department || 'HR';

  // Current month's submission for this department
  const currentMonthSubs = submissions[activeMonthId] || [];
  const existingSubmission = currentMonthSubs.find((s) => s.department === targetDept);

  // Local state for line items & notes
  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const [submissionComments, setSubmissionComments] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [customCategoryInput, setCustomCategoryInput] = useState<string>('');
  const [isAddingCustomCategory, setIsAddingCustomCategory] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  // Load existing submission data when activeMonth or department changes
  useEffect(() => {
    if (existingSubmission && existingSubmission.lineItems.length > 0) {
      setLineItems(existingSubmission.lineItems);
      setSubmissionComments(existingSubmission.comments || '');
    } else {
      // Initialize with default category suggestions for this department
      const deptCats = categories.filter((c) => c.department === targetDept);
      const defaults: LineItem[] = deptCats.slice(0, 4).map((cat, idx) => ({
        id: `li-draft-${Date.now()}-${idx}`,
        submissionId: existingSubmission?.id || `sub-${activeMonthId}-${targetDept.toLowerCase()}`,
        department: targetDept,
        category: cat.name,
        description: '',
        amountInr: 0,
        priority: 'Important',
        notes: '',
      }));
      setLineItems(defaults);
      setSubmissionComments('');
    }
  }, [activeMonthId, targetDept, existingSubmission]);

  // Prior month comparison
  const priorSubmission = getPriorMonthSubmission(activeMonthId, targetDept);
  const priorTotalInr = priorSubmission
    ? priorSubmission.lineItems.reduce((acc, i) => acc + (i.approvedAmountInr ?? i.amountInr), 0)
    : 0;

  // Department categories
  const deptCategories = categories.filter((c) => c.department === targetDept);

  // Calculations
  const totalInr = lineItems.reduce((sum, item) => sum + (Number(item.amountInr) || 0), 0);
  const totalAud = convertInrToAud(totalInr, activeMonth.exchangeRate);
  
  const criticalInr = lineItems
    .filter((i) => i.priority === 'Critical')
    .reduce((sum, i) => sum + (Number(i.amountInr) || 0), 0);
  const criticalAud = convertInrToAud(criticalInr, activeMonth.exchangeRate);

  const importantInr = lineItems
    .filter((i) => i.priority === 'Important')
    .reduce((sum, i) => sum + (Number(i.amountInr) || 0), 0);
  
  const optionalInr = lineItems
    .filter((i) => i.priority === 'Optional')
    .reduce((sum, i) => sum + (Number(i.amountInr) || 0), 0);

  const variance = formatVariance(totalInr, priorTotalInr);

  // Lock status
  const isMonthLocked = activeMonth.status === 'Ready for Approval' || activeMonth.status === 'Approved' || activeMonth.status === 'Closed';
  const isSubmissionLocked = existingSubmission?.status === 'Submitted' || existingSubmission?.status === 'Locked' || existingSubmission?.status === 'Approved';
  const isReadOnly = isMonthLocked || (isSubmissionLocked && currentUser.role === 'department_submitter');

  const canRecall = existingSubmission?.status === 'Submitted' && activeMonth.status === 'Open';

  // Add a new empty line item
  const handleAddLineItem = (categoryName?: string) => {
    const cat = categoryName || (deptCategories[0]?.name || 'General Operations');
    const newItem: LineItem = {
      id: `li-item-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      submissionId: existingSubmission?.id || `sub-${activeMonthId}-${targetDept.toLowerCase()}`,
      department: targetDept,
      category: cat,
      description: '',
      amountInr: 0,
      priority: 'Important',
      notes: '',
    };
    setLineItems([...lineItems, newItem]);
  };

  // Remove line item
  const handleRemoveLineItem = (id: string) => {
    if (lineItems.length <= 1) {
      alert('You must keep at least one line item.');
      return;
    }
    setLineItems(lineItems.filter((i) => i.id !== id));
  };

  // Update line item property
  const handleUpdateLineItem = (id: string, field: keyof LineItem, value: any) => {
    setLineItems(
      lineItems.map((item) => {
        if (item.id === id) {
          return { ...item, [field]: value };
        }
        return item;
      })
    );
  };

  // Validation before submission
  const validateForm = (): boolean => {
    if (lineItems.length === 0) {
      alert('Please add at least one line item.');
      return false;
    }

    for (let i = 0; i < lineItems.length; i++) {
      const item = lineItems[i];
      if (!item.description || item.description.trim() === '') {
        alert(`Line item #${i + 1} has an empty description. Please describe the expense.`);
        return false;
      }
      if (item.amountInr === undefined || item.amountInr === null || item.amountInr < 0) {
        alert(`Line item #${i + 1} has an invalid or negative amount.`);
        return false;
      }
      if (item.amountInr === 0) {
        const confirmZero = confirm(`Line item #${i + 1} ("${item.description}") has an amount of ₹0. Do you still want to proceed?`);
        if (!confirmZero) return false;
      }
    }

    if (totalInr <= 0) {
      alert('Total submission amount must be greater than zero.');
      return false;
    }

    return true;
  };

  // Save Draft
  const handleSaveDraft = () => {
    saveDepartmentDraft(activeMonthId, targetDept, lineItems, submissionComments);
    setSaveSuccessMsg('Draft saved successfully!');
    setTimeout(() => setSaveSuccessMsg(null), 3000);
  };

  // Submit
  const handleSubmit = () => {
    if (!validateForm()) return;
    submitDepartmentRequirements(activeMonthId, targetDept, lineItems, submissionComments);
    setSaveSuccessMsg('Requirements submitted for consolidation!');
    setTimeout(() => setSaveSuccessMsg(null), 3500);
  };

  // Recall
  const handleRecall = () => {
    if (confirm(`Recall ${targetDept} submission back to Draft? You will be able to edit and re-submit.`)) {
      recallDepartmentSubmission(activeMonthId, targetDept);
    }
  };

  const getPriorityBadge = (priority: Priority) => {
    switch (priority) {
      case 'Critical':
        return 'bg-red-50 text-red-700 border-red-200 font-semibold';
      case 'Important':
        return 'bg-amber-50 text-amber-700 border-amber-200 font-medium';
      case 'Optional':
        return 'bg-slate-100 text-slate-700 border-slate-200 font-normal';
    }
  };

  // Historical Submissions for this department
  const historicalSubmissionsForDept = months
    .map((m) => {
      const subs = submissions[m.id] || [];
      const sub = subs.find((s) => s.department === targetDept);
      return {
        month: m,
        submission: sub,
      };
    })
    .filter((h) => h.submission);

  return (
    <div id="department-input-container" className="space-y-6">
      
      {/* Header and Status Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="px-2.5 py-1 rounded-md text-xs font-bold bg-blue-100 text-blue-800 border border-blue-200 uppercase tracking-wider">
                {targetDept} Department
              </span>
              <h2 className="text-xl font-bold text-slate-900">
                Monthly Cash Requirements Submission
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1 flex items-center gap-2">
              <span>Target Period: <strong className="text-slate-800">{activeMonth.label}</strong></span>
              <span>•</span>
              <span>Submission Deadline: <strong className="text-slate-800">{formatDate(activeMonth.submissionDeadline)}</strong></span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Status Indicator */}
            <div className="text-right">
              <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                Status
              </div>
              <div className="text-xs font-bold mt-0.5">
                {existingSubmission?.status === 'Submitted' ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Submitted
                  </span>
                ) : existingSubmission?.status === 'Locked' ? (
                  <span className="inline-flex items-center gap-1 text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                    <Lock className="w-3.5 h-3.5" /> Locked in Pack
                  </span>
                ) : existingSubmission?.status === 'Approved' ? (
                  <span className="inline-flex items-center gap-1 text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded border border-emerald-300">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Approved by Mgmt
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                    <Clock className="w-3.5 h-3.5" /> Draft / In Progress
                  </span>
                )}
              </div>
            </div>

            {/* Quick Action Button for Recall */}
            {canRecall && (
              <button
                id="btn-recall-submission"
                onClick={handleRecall}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-300 rounded-lg shadow-xs transition-colors"
                title="Recall submission back to draft to make changes"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Recall for Edit</span>
              </button>
            )}
          </div>
        </div>

        {/* Lock message alert if read-only */}
        {isReadOnly && (
          <div className="mt-4 p-3 bg-blue-50/70 border border-blue-200 rounded-lg flex items-start gap-2.5 text-xs text-blue-800">
            <Lock className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">
                {activeMonth.status === 'Ready for Approval'
                  ? 'Monthly pack is under Management Review.'
                  : activeMonth.status === 'Approved'
                  ? 'Monthly pack has been Approved by Management.'
                  : 'Submission is locked.'}
              </p>
              <p className="text-blue-700/80 mt-0.5">
                Submitted on {formatIST(existingSubmission?.submittedAt)} by {existingSubmission?.submittedBy || 'Department Head'}.
                {canRecall && ' You can recall this submission if edits are needed before final approval.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Metrics & Quick Reference Panel */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Total Department Requirement Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1">
            Total {targetDept} Request
          </div>
          <div className="mt-1 text-2xl font-black text-slate-900 font-mono">
            {formatINR(totalInr)}
          </div>
          <div className="mt-2 text-xs text-emerald-700 font-bold font-mono flex items-center justify-between pt-2 border-t border-slate-100">
            <span>{formatAUD(totalAud)}</span>
            <span className="text-[11px] text-slate-400 font-normal">FX: {activeMonth.exchangeRate}</span>
          </div>
        </div>

        {/* Prior Month Actual Reference & Variance Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 flex items-center justify-between">
            <span>Prior Month Variance</span>
            <span className="text-[10px] text-slate-400">MoM</span>
          </div>
          <div className="mt-1 flex items-baseline justify-between">
            <div className="text-xl font-bold text-slate-900 font-mono">
              {formatINR(priorTotalInr)}
            </div>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                variance.isNeutral
                  ? 'bg-slate-100 text-slate-700'
                  : variance.isPositive
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              }`}
            >
              {variance.formatted}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2 pt-2 border-t border-slate-100 font-mono">
            Prior approved: {formatAUD(convertInrToAud(priorTotalInr, activeMonth.exchangeRate))}
          </p>
        </div>

        {/* Critical Priority Ratio Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm border-l-4 border-l-red-500">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1 flex items-center justify-between">
            <span>Critical Must-Fund</span>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold">Priority</span>
          </div>
          <div className="mt-1 text-2xl font-black text-red-600 font-mono">
            {formatINR(criticalInr)}
          </div>
          <div className="mt-2 text-xs text-slate-500 flex items-center justify-between pt-2 border-t border-slate-100">
            <span className="font-mono text-emerald-700 font-bold">{formatAUD(criticalAud)}</span>
            <span className="font-bold text-slate-700">
              {totalInr > 0 ? `${((criticalInr / totalInr) * 100).toFixed(0)}% of total` : '0%'}
            </span>
          </div>
        </div>

        {/* Important & Optional Breakdown */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500 mb-1">
            Important vs Optional
          </div>
          <div className="mt-2 space-y-1.5 text-xs">
            <div className="flex justify-between items-center text-slate-700 font-medium">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500"></span> Important:
              </span>
              <span className="font-mono font-bold">{formatINR(importantInr)}</span>
            </div>
            <div className="flex justify-between items-center text-slate-600">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-slate-400"></span> Optional:
              </span>
              <span className="font-mono font-bold">{formatINR(optionalInr)}</span>
            </div>
          </div>
        </div>

      </div>

      {/* Main Line Items Table Form */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        
        {/* Table Header Controls */}
        <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-slate-800 text-sm">
              Expense Line Items ({lineItems.length})
            </h3>
            <span className="text-xs text-slate-500 font-normal">
              Enter amounts in INR (₹). AUD (A$) converts automatically.
            </span>
          </div>

          {!isReadOnly && (
            <div className="flex items-center gap-2">
              {/* Add standard category quick button */}
              <select
                id="select-quick-category"
                value={selectedCategory}
                onChange={(e) => {
                  if (e.target.value) {
                    handleAddLineItem(e.target.value);
                    setSelectedCategory('');
                  }
                }}
                className="text-xs bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-700 font-medium focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">+ Add Standard Category...</option>
                {deptCategories.map((cat) => (
                  <option key={cat.id} value={cat.name}>
                    {cat.name}
                  </option>
                ))}
              </select>

              <button
                id="btn-add-custom-line"
                onClick={() => handleAddLineItem('Custom Expense')}
                className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors shadow-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Custom Line</span>
              </button>
            </div>
          )}
        </div>

        {/* Line Items Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/70 border-b border-slate-200 text-slate-600 font-semibold">
                <th className="py-2.5 px-3 w-10 text-center">#</th>
                <th className="py-2.5 px-3 w-48">Category</th>
                <th className="py-2.5 px-3 min-w-[200px]">Description</th>
                <th className="py-2.5 px-3 w-36 text-right">Amount (₹ INR)</th>
                <th className="py-2.5 px-3 w-32 text-right">Amount (A$ AUD)</th>
                <th className="py-2.5 px-3 w-28 text-center">Priority</th>
                <th className="py-2.5 px-3 min-w-[180px]">Justification / Notes</th>
                {!isReadOnly && <th className="py-2.5 px-3 w-12 text-center"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lineItems.map((item, index) => {
                const audAmount = convertInrToAud(item.amountInr || 0, activeMonth.exchangeRate);
                return (
                  <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                    
                    {/* Index */}
                    <td className="py-2.5 px-3 text-center text-slate-400 font-mono">
                      {index + 1}
                    </td>

                    {/* Category */}
                    <td className="py-2.5 px-3">
                      {isReadOnly ? (
                        <span className="font-semibold text-slate-800">
                          {item.category}
                        </span>
                      ) : (
                        <select
                          value={item.category}
                          onChange={(e) => handleUpdateLineItem(item.id, 'category', e.target.value)}
                          className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 font-medium text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        >
                          {deptCategories.map((c) => (
                            <option key={c.id} value={c.name}>
                              {c.name}
                            </option>
                          ))}
                          {!deptCategories.some((c) => c.name === item.category) && (
                            <option value={item.category}>{item.category}</option>
                          )}
                        </select>
                      )}
                    </td>

                    {/* Description */}
                    <td className="py-2.5 px-3">
                      {isReadOnly ? (
                        <span className="text-slate-800 font-normal">
                          {item.description || '—'}
                        </span>
                      ) : (
                        <input
                          type="text"
                          value={item.description}
                          placeholder="e.g. 4 new engineer workstations..."
                          onChange={(e) => handleUpdateLineItem(item.id, 'description', e.target.value)}
                          className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-slate-800 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      )}
                    </td>

                    {/* Amount in INR */}
                    <td className="py-2.5 px-3 text-right">
                      {isReadOnly ? (
                        <span className="font-bold text-slate-900 font-mono">
                          {formatINR(item.amountInr)}
                        </span>
                      ) : (
                        <div className="relative">
                          <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 font-mono">
                            ₹
                          </span>
                          <input
                            type="number"
                            min="0"
                            step="1000"
                            value={item.amountInr === 0 ? '' : item.amountInr}
                            placeholder="0"
                            onChange={(e) => {
                              const val = e.target.value === '' ? 0 : Math.max(0, parseFloat(e.target.value) || 0);
                              handleUpdateLineItem(item.id, 'amountInr', val);
                            }}
                            className="w-full text-right bg-white border border-slate-300 rounded pl-5 pr-2 py-1 font-mono font-bold text-slate-900 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                          />
                        </div>
                      )}
                    </td>

                    {/* Amount in AUD */}
                    <td className="py-2.5 px-3 text-right font-mono font-semibold text-emerald-700 bg-emerald-50/30">
                      {formatAUD(audAmount)}
                    </td>

                    {/* Priority */}
                    <td className="py-2.5 px-3 text-center">
                      {isReadOnly ? (
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] border ${getPriorityBadge(item.priority)}`}>
                          {item.priority}
                        </span>
                      ) : (
                        <select
                          value={item.priority}
                          onChange={(e) => handleUpdateLineItem(item.id, 'priority', e.target.value as Priority)}
                          className={`w-full text-center text-[11px] rounded px-1.5 py-1 border focus:outline-none ${getPriorityBadge(item.priority)}`}
                        >
                          <option value="Critical">Critical</option>
                          <option value="Important">Important</option>
                          <option value="Optional">Optional</option>
                        </select>
                      )}
                    </td>

                    {/* Justification & Notes */}
                    <td className="py-2.5 px-3">
                      {isReadOnly ? (
                        <span className="text-slate-600 text-[11px] italic">
                          {item.notes || 'No note'}
                        </span>
                      ) : (
                        <input
                          type="text"
                          value={item.notes}
                          placeholder="Business justification / due date..."
                          onChange={(e) => handleUpdateLineItem(item.id, 'notes', e.target.value)}
                          className="w-full bg-white border border-slate-300 rounded px-2 py-1 text-slate-700 text-xs focus:ring-1 focus:ring-blue-500 focus:outline-none"
                        />
                      )}
                    </td>

                    {/* Actions */}
                    {!isReadOnly && (
                      <td className="py-2.5 px-3 text-center">
                        <button
                          type="button"
                          onClick={() => handleRemoveLineItem(item.id)}
                          className="text-slate-400 hover:text-red-600 p-1 rounded transition-colors"
                          title="Delete line item"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    )}

                  </tr>
                );
              })}
            </tbody>

            {/* Table Footer Totals */}
            <tfoot>
              <tr className="bg-slate-100 border-t-2 border-slate-300 font-bold text-slate-900 text-xs">
                <td colSpan={3} className="py-3 px-4 text-right">
                  {targetDept} Department Subtotal:
                </td>
                <td className="py-3 px-3 text-right text-base text-blue-900 font-mono">
                  {formatINR(totalInr)}
                </td>
                <td className="py-3 px-3 text-right text-sm text-emerald-800 font-mono bg-emerald-100/50">
                  {formatAUD(totalAud)}
                </td>
                <td colSpan={isReadOnly ? 2 : 3} className="py-3 px-3 text-xs text-slate-500 font-normal">
                  Calculated using locked/current rate (1 INR = {activeMonth.exchangeRate} AUD)
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {/* Overall Department Comments / Context */}
        <div className="p-4 bg-slate-50 border-t border-slate-200">
          <label className="block text-xs font-semibold text-slate-700 mb-1">
            Department Narrative & Executive Context for Management:
          </label>
          {isReadOnly ? (
            <div className="bg-white p-3 rounded-lg border border-slate-200 text-xs text-slate-700 italic">
              {submissionComments || 'No overall narrative provided.'}
            </div>
          ) : (
            <textarea
              rows={2}
              value={submissionComments}
              onChange={(e) => setSubmissionComments(e.target.value)}
              placeholder="Highlight any major headcount increases, annual contracts, or emergency replacements for Management..."
              className="w-full bg-white border border-slate-300 rounded-lg p-2.5 text-xs text-slate-800 focus:ring-1 focus:ring-blue-500 focus:outline-none"
            />
          )}
        </div>

        {/* Action Bar */}
        {!isReadOnly && (
          <div className="p-4 bg-white border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">
                Ensure all critical invoices and payroll projections are verified before formal submission.
              </span>
              {saveSuccessMsg && (
                <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200 animate-fade-in flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {saveSuccessMsg}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                id="btn-save-draft"
                onClick={handleSaveDraft}
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-xs transition-colors"
              >
                <Save className="w-3.5 h-3.5 text-slate-600" />
                <span>Save Draft</span>
              </button>

              <button
                type="button"
                id="btn-submit-department"
                onClick={handleSubmit}
                className="flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm hover:shadow transition-all"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Submit for Consolidation</span>
              </button>
            </div>
          </div>
        )}

      </div>

      {/* Historical Submissions Table for this Department */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-blue-600" />
          {targetDept} Historical Submission Log
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 font-semibold bg-slate-50">
                <th className="py-2 px-3">Month Cycle</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3 text-right">Requested (₹ INR)</th>
                <th className="py-2 px-3 text-right">Requested (A$ AUD)</th>
                <th className="py-2 px-3">Submitted By</th>
                <th className="py-2 px-3">Timestamp (IST)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {historicalSubmissionsForDept.map(({ month, submission }) => {
                const subTotalInr = submission?.lineItems.reduce((acc, i) => acc + i.amountInr, 0) || 0;
                const subTotalAud = convertInrToAud(subTotalInr, month.exchangeRate);
                return (
                  <tr key={month.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-semibold text-slate-800">
                      {month.label}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-700">
                        {submission?.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                      {formatINR(subTotalInr)}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-emerald-700">
                      {formatAUD(subTotalAud)}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">
                      {submission?.submittedBy || '—'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-500 font-mono text-[11px]">
                      {formatIST(submission?.submittedAt || submission?.lastUpdatedAt)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
