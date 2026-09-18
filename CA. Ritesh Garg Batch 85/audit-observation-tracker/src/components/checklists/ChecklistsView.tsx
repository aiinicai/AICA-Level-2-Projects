import React, { useState } from 'react';
import { 
  CheckSquare, 
  Search, 
  PlusCircle, 
  Upload, 
  Download, 
  FileSpreadsheet, 
  Trash2, 
  Edit3, 
  Filter, 
  ShieldAlert, 
  CheckCircle2, 
  AlertCircle, 
  HelpCircle,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Tag,
  Save,
  X
} from 'lucide-react';
import { AuditType, AuditChecklistItem, SeverityLevel, FirmProfile } from '../../types/audit';
import { TemplateService } from '../../services/templateService';
import { ChecklistUploadModal } from './ChecklistUploadModal';

interface ChecklistsViewProps {
  auditTypes: AuditType[];
  checklistItems: AuditChecklistItem[];
  firmProfile: FirmProfile;
  onSaveChecklistItem: (item: Partial<AuditChecklistItem> & { checkPoint: string; auditTypeId: string }) => void;
  onDeleteChecklistItem: (id: string) => void;
  onImportChecklistItems: (items: AuditChecklistItem[], replace: boolean) => void;
}

export const ChecklistsView: React.FC<ChecklistsViewProps> = ({
  auditTypes,
  checklistItems = [],
  firmProfile,
  onSaveChecklistItem,
  onDeleteChecklistItem,
  onImportChecklistItems,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAuditType, setSelectedAuditType] = useState('ALL');
  const [selectedRisk, setSelectedRisk] = useState('ALL');
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<AuditChecklistItem | null>(null);

  // Item Form State
  const [formAuditTypeId, setFormAuditTypeId] = useState(auditTypes[0]?.id || 'at-1');
  const [formCategory, setFormCategory] = useState('');
  const [formItemNumber, setFormItemNumber] = useState('');
  const [formCheckPoint, setFormCheckPoint] = useState('');
  const [formGuidance, setFormGuidance] = useState('');
  const [formStatutoryRef, setFormStatutoryRef] = useState('');
  const [formRiskLevel, setFormRiskLevel] = useState<SeverityLevel>('High');
  const [formIsMandatory, setFormIsMandatory] = useState(true);
  const [formError, setFormError] = useState('');

  const auditTypeMap = new Map<string, AuditType>(auditTypes.map(at => [at.id, at]));

  // Filter items
  const filteredItems = checklistItems.filter(item => {
    if (selectedAuditType !== 'ALL' && item.auditTypeId !== selectedAuditType) return false;
    if (selectedRisk !== 'ALL' && item.riskLevel !== selectedRisk) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const atName = auditTypeMap.get(item.auditTypeId)?.name.toLowerCase() || '';
      return (
        item.checkPoint.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        (item.procedureGuidance && item.procedureGuidance.toLowerCase().includes(q)) ||
        (item.statutoryReference && item.statutoryReference.toLowerCase().includes(q)) ||
        (item.itemNumber && item.itemNumber.toLowerCase().includes(q)) ||
        atName.includes(q)
      );
    }
    return true;
  });

  // Group filtered items by category
  const groupedByCategory = filteredItems.reduce((acc, item) => {
    const at = auditTypeMap.get(item.auditTypeId);
    const typeLabel = at ? `${at.name} (${at.code})` : 'General';
    const key = `${typeLabel} — ${item.category}`;
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {} as Record<string, AuditChecklistItem[]>);

  // Statistics
  const totalCount = checklistItems.length;
  const criticalCount = checklistItems.filter(i => i.riskLevel === 'Critical').length;
  const highCount = checklistItems.filter(i => i.riskLevel === 'High').length;
  const coveredTypesCount = new Set(checklistItems.map(i => i.auditTypeId)).size;

  const handleDownloadSample = () => {
    TemplateService.downloadChecklistSampleTemplate(auditTypes);
  };

  const handleExportActive = () => {
    TemplateService.exportChecklistsToExcel(checklistItems, auditTypes);
  };

  const handleOpenNewItem = () => {
    setEditingItem(null);
    setFormAuditTypeId(selectedAuditType !== 'ALL' ? selectedAuditType : (auditTypes[0]?.id || 'at-1'));
    setFormCategory('');
    setFormItemNumber('');
    setFormCheckPoint('');
    setFormGuidance('');
    setFormStatutoryRef('');
    setFormRiskLevel('High');
    setFormIsMandatory(true);
    setFormError('');
    setIsItemModalOpen(true);
  };

  const handleOpenEditItem = (item: AuditChecklistItem) => {
    setEditingItem(item);
    setFormAuditTypeId(item.auditTypeId);
    setFormCategory(item.category);
    setFormItemNumber(item.itemNumber || '');
    setFormCheckPoint(item.checkPoint);
    setFormGuidance(item.procedureGuidance || '');
    setFormStatutoryRef(item.statutoryReference || '');
    setFormRiskLevel(item.riskLevel);
    setFormIsMandatory(item.isMandatory);
    setFormError('');
    setIsItemModalOpen(true);
  };

  const handleSaveItemSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formCheckPoint.trim()) {
      setFormError('Check Point / Audit Procedure is required');
      return;
    }
    if (!formCategory.trim()) {
      setFormError('Category / Area is required');
      return;
    }

    onSaveChecklistItem({
      id: editingItem?.id,
      auditTypeId: formAuditTypeId,
      category: formCategory.trim(),
      itemNumber: formItemNumber.trim() || undefined,
      checkPoint: formCheckPoint.trim(),
      procedureGuidance: formGuidance.trim() || undefined,
      statutoryReference: formStatutoryRef.trim() || undefined,
      riskLevel: formRiskLevel,
      isMandatory: formIsMandatory,
    });

    setIsItemModalOpen(false);
  };

  const handleDeleteItem = (item: AuditChecklistItem) => {
    if (window.confirm(`Delete check point "${item.itemNumber || ''} ${item.checkPoint.slice(0, 40)}..."?`)) {
      onDeleteChecklistItem(item.id);
    }
  };

  return (
    <div id="checklists-view-container" className="space-y-6">
      {/* Header */}
      <div className="bg-white p-5 rounded-2xl border border-stone-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-stone-800 tracking-tight">Audit Checklists & Templates Master</h1>
            <span className="bg-[#F5F2ED] text-stone-700 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-[#DED9D0]">
              {totalCount} Check Points
            </span>
          </div>
          <p className="text-sm text-stone-500 mt-0.5">
            Standardized CA audit test procedures and statutory compliance checklists by audit type.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleDownloadSample}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-100 transition-colors shadow-2xs"
            title="Download official sample Excel template"
          >
            <Download className="w-3.5 h-3.5 text-stone-600" />
            <span>Sample Template (.xlsx)</span>
          </button>

          <button
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-amber-300 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-semibold transition-colors shadow-2xs"
          >
            <Upload className="w-3.5 h-3.5 text-amber-800" />
            <span>Upload Template (Excel)</span>
          </button>

          <button
            onClick={handleExportActive}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-100 transition-colors shadow-2xs"
            title="Export all current active checklists to Excel"
          >
            <FileSpreadsheet className="w-3.5 h-3.5 text-stone-600" />
            <span>Export (.xlsx)</span>
          </button>

          <button
            onClick={handleOpenNewItem}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <PlusCircle className="w-3.5 h-3.5 text-amber-300" />
            <span>+ Add Check Point</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-2xs">
          <p className="text-xs font-medium text-stone-500">Total Checkpoints</p>
          <p className="text-2xl font-bold text-stone-800 mt-1">{totalCount}</p>
          <p className="text-[11px] text-stone-400 mt-0.5">Across {coveredTypesCount} audit types</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-rose-100 bg-rose-50/20 shadow-2xs">
          <p className="text-xs font-medium text-rose-700">Critical Risk Items</p>
          <p className="text-2xl font-bold text-rose-800 mt-1">{criticalCount}</p>
          <p className="text-[11px] text-rose-600 mt-0.5">High audit exposure checks</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-amber-100 bg-amber-50/20 shadow-2xs">
          <p className="text-xs font-medium text-amber-700">High Risk Items</p>
          <p className="text-2xl font-bold text-amber-800 mt-1">{highCount}</p>
          <p className="text-[11px] text-amber-600 mt-0.5">Mandatory verification steps</p>
        </div>

        <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-2xs">
          <p className="text-xs font-medium text-stone-500">Excel Templates</p>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              Instant Import Ready
            </span>
          </div>
          <p className="text-[11px] text-stone-400 mt-1.5">Editable & customizable</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-2xl border border-stone-200 shadow-sm flex flex-col md:flex-row items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search checklists by procedure, statutory reference (e.g. CARO, Sec 43B), category, or keyword..."
            className="w-full pl-9 pr-3.5 py-1.5 text-xs bg-stone-50 border border-stone-200 rounded-lg text-stone-800 placeholder-stone-400 focus:bg-white focus:outline-hidden focus:ring-2 focus:ring-[#5A5A40]/10 focus:border-[#5A5A40]"
          />
        </div>

        {/* Audit Type Filter */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          <select
            value={selectedAuditType}
            onChange={(e) => setSelectedAuditType(e.target.value)}
            className="text-xs bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 text-stone-700 font-medium focus:bg-white focus:outline-hidden"
          >
            <option value="ALL">All Audit Types</option>
            {auditTypes.map((at) => (
              <option key={at.id} value={at.id}>
                {at.name} ({at.code})
              </option>
            ))}
          </select>

          <select
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
            className="text-xs bg-stone-50 border border-stone-200 rounded-lg px-2.5 py-1.5 text-stone-700 font-medium focus:bg-white focus:outline-hidden"
          >
            <option value="ALL">All Risk Levels</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
      </div>

      {/* Checklists List Organized by Category */}
      {Object.keys(groupedByCategory).length === 0 ? (
        <div className="bg-white p-12 rounded-2xl border border-stone-200 text-center space-y-4 shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-stone-100 text-stone-400 flex items-center justify-center mx-auto">
            <CheckSquare className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-stone-800">No Checklist Procedures Found</h3>
            <p className="text-xs text-stone-500 mt-1 max-w-md mx-auto">
              {searchQuery || selectedAuditType !== 'ALL' || selectedRisk !== 'ALL'
                ? 'No check points matched your current search filters. Try clearing filters.'
                : 'Your checklist master is currently empty. You can download our sample template and upload your Excel checklist.'}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              onClick={handleDownloadSample}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-stone-300 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-50"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Sample (.xlsx)</span>
            </button>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#5A5A40] text-white text-xs font-semibold hover:bg-[#4A4A34]"
            >
              <Upload className="w-3.5 h-3.5 text-amber-300" />
              <span>Upload Template</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {(Object.entries(groupedByCategory) as [string, AuditChecklistItem[]][]).map(([groupTitle, items]) => (
            <div key={groupTitle} className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
              {/* Category Group Header */}
              <div className="bg-[#F5F2ED] px-5 py-3 border-b border-stone-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-[#5A5A40]" />
                  <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                    {groupTitle}
                  </h3>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-white text-stone-600 font-semibold border border-stone-200">
                    {items.length} procedure{items.length !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

              {/* Items List */}
              <div className="divide-y divide-stone-100">
                {items.map((item) => {
                  const at = auditTypeMap.get(item.auditTypeId);
                  return (
                    <div 
                      key={item.id}
                      className="p-4 hover:bg-stone-50/70 transition-colors flex flex-col sm:flex-row sm:items-start justify-between gap-4"
                    >
                      <div className="flex items-start gap-3 min-w-0 flex-1">
                        {/* Number badge */}
                        <span className="px-2 py-1 bg-stone-100 text-stone-700 font-mono font-bold text-xs rounded-lg shrink-0 border border-stone-200">
                          {item.itemNumber || 'CL'}
                        </span>

                        <div className="space-y-1.5 min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-stone-900 leading-snug">
                              {item.checkPoint}
                            </span>
                            {item.isMandatory && (
                              <span className="text-[10px] bg-emerald-50 text-emerald-800 font-bold px-1.5 py-0.5 rounded-md border border-emerald-200">
                                Mandatory
                              </span>
                            )}
                          </div>

                          {/* Verification Guidance */}
                          {item.procedureGuidance && (
                            <div className="text-xs text-stone-600 bg-stone-50/80 p-2.5 rounded-xl border border-stone-200/60 leading-relaxed">
                              <span className="font-semibold text-stone-700">Audit Guidance: </span>
                              {item.procedureGuidance}
                            </div>
                          )}

                          {/* Tags: Statutory reference & Audit Type */}
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            {item.statutoryReference && (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-stone-700 bg-amber-50/80 px-2 py-0.5 rounded-md border border-amber-200/80">
                                <Tag className="w-3 h-3 text-amber-700" />
                                {item.statutoryReference}
                              </span>
                            )}

                            <span className="text-[10px] text-stone-500">
                              Type: <strong>{at?.name || 'Audit'} ({at?.code || 'SA'})</strong>
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right: Risk Badge & Actions */}
                      <div className="flex sm:flex-col items-center sm:items-end justify-between gap-2 shrink-0">
                        <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold ${
                          item.riskLevel === 'Critical' ? 'bg-rose-100 text-rose-800 border border-rose-200' :
                          item.riskLevel === 'High' ? 'bg-amber-100 text-amber-900 border border-amber-200' :
                          item.riskLevel === 'Medium' ? 'bg-blue-100 text-blue-800 border border-blue-200' :
                          'bg-stone-100 text-stone-700 border border-stone-200'
                        }`}>
                          {item.riskLevel} Risk
                        </span>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleOpenEditItem(item)}
                            className="p-1.5 text-stone-400 hover:text-stone-700 hover:bg-stone-200/60 rounded-lg transition-colors"
                            title="Edit Check Point"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item)}
                            className="p-1.5 text-stone-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                            title="Delete Check Point"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload Checklist Template Modal */}
      <ChecklistUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        auditTypes={auditTypes}
        onImportChecklistItems={onImportChecklistItems}
      />

      {/* Add / Edit Check Point Modal */}
      {isItemModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div 
            className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-stone-200 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200 bg-[#F5F2ED]">
              <div className="flex items-center gap-2">
                <CheckSquare className="w-5 h-5 text-[#5A5A40]" />
                <h3 className="text-sm font-bold text-stone-800">
                  {editingItem ? 'Edit Audit Check Point' : '+ Add Audit Check Point'}
                </h3>
              </div>
              <button
                onClick={() => setIsItemModalOpen(false)}
                className="p-1 text-stone-400 hover:text-stone-600 rounded-lg"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveItemSubmit} className="p-5 space-y-4 overflow-y-auto max-h-[80vh]">
              {formError && (
                <div className="p-3 bg-rose-50 rounded-xl border border-rose-200 text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-stone-700 block mb-1">Audit Type *</label>
                  <select
                    value={formAuditTypeId}
                    onChange={(e) => setFormAuditTypeId(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                  >
                    {auditTypes.map((at) => (
                      <option key={at.id} value={at.id}>
                        {at.name} ({at.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-stone-700 block mb-1">Item Sequence / No.</label>
                  <input
                    type="text"
                    value={formItemNumber}
                    onChange={(e) => setFormItemNumber(e.target.value)}
                    placeholder="e.g. 1.1, CL-01"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">Category / Process Area *</label>
                <input
                  type="text"
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  placeholder="e.g. Physical Inventory Verification, MSME Compliance, Loan Sanction"
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">Check Point / Procedure Question *</label>
                <textarea
                  rows={3}
                  value={formCheckPoint}
                  onChange={(e) => setFormCheckPoint(e.target.value)}
                  placeholder="Describe the specific audit test or verification procedure..."
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">Verification Guidance (For Article/Staff)</label>
                <textarea
                  rows={2}
                  value={formGuidance}
                  onChange={(e) => setFormGuidance(e.target.value)}
                  placeholder="Sampling instructions, checking methodology, cut-off date instructions..."
                  className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-stone-700 block mb-1">Statutory / Regulatory Reference</label>
                  <input
                    type="text"
                    value={formStatutoryRef}
                    onChange={(e) => setFormStatutoryRef(e.target.value)}
                    placeholder="e.g. CARO 2020 3(ii), Sec 43B(h)"
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-stone-700 block mb-1">Risk Exposure Level</label>
                  <select
                    value={formRiskLevel}
                    onChange={(e) => setFormRiskLevel(e.target.value as SeverityLevel)}
                    className="w-full px-3 py-1.5 text-xs rounded-lg border border-stone-300 bg-white text-stone-800 focus:outline-hidden focus:border-[#5A5A40]"
                  >
                    <option value="Critical">Critical</option>
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="formIsMandatory"
                  checked={formIsMandatory}
                  onChange={(e) => setFormIsMandatory(e.target.checked)}
                  className="rounded text-[#5A5A40] focus:ring-[#5A5A40]"
                />
                <label htmlFor="formIsMandatory" className="text-xs font-semibold text-stone-700 cursor-pointer">
                  Mandatory Audit Procedure Checkpoint
                </label>
              </div>

              <div className="pt-4 border-t border-stone-200 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsItemModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-stone-300 text-stone-700 text-xs font-semibold hover:bg-stone-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-[#5A5A40] hover:bg-[#4A4A34] text-white text-xs font-semibold shadow-xs"
                >
                  <Save className="w-3.5 h-3.5 text-amber-300" />
                  <span>{editingItem ? 'Save Changes' : 'Add Check Point'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
