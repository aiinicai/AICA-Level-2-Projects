import React, { useState, useEffect } from 'react';
import { Sliders, Plus, CheckCircle2, Layout, Maximize2, Move, Sparkles, Layers, Check, Trash2, Edit3, Save, RotateCcw } from 'lucide-react';
import api from '../services/api';
import { TagTemplate, LabelSize } from '../types';
import { useCompany } from '../context/CompanyContext';
import { AssetTagPreview } from '../components/AssetTagPreview';

export const TagTemplatesPage: React.FC = () => {
  const { selectedCompany } = useCompany();
  const [templates, setTemplates] = useState<TagTemplate[]>([]);
  const [labelSizes, setLabelSizes] = useState<LabelSize[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Template Designer State
  const [templateName, setTemplateName] = useState('Standard Corporate');
  const [widthMm, setWidthMm] = useState(70);
  const [heightMm, setHeightMm] = useState(35);
  const [codeType, setCodeType] = useState<'BARCODE' | 'QR_CODE'>('BARCODE');
  const [showLogo, setShowLogo] = useState(true);
  const [showSap, setShowSap] = useState(true);
  const [showDesc, setShowDesc] = useState(true);
  const [showLoc, setShowLoc] = useState(true);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState('');

  const fetchTemplatesAndSizes = async () => {
    try {
      setLoading(true);
      const [resTmpl, resSizes] = await Promise.all([
        api.get<TagTemplate[]>('/templates'),
        api.get<LabelSize[]>('/printing/label-sizes'),
      ]);
      setTemplates(resTmpl.data);
      setLabelSizes(resSizes.data);
      if (resTmpl.data.length > 0) {
        applyTemplate(resTmpl.data[0]);
      }
    } catch (e) {
      console.error('Failed to load templates:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplatesAndSizes();
  }, []);

  const applyTemplate = (tmpl: TagTemplate) => {
    setSelectedTemplateId(tmpl.id);
    setTemplateName(tmpl.template_name);
    setWidthMm(tmpl.width_mm);
    setHeightMm(tmpl.height_mm);
    setCodeType(tmpl.code_type);
    setShowLogo(tmpl.show_logo);
    setShowSap(tmpl.field_visibility?.sap_number !== false);
    setShowDesc(tmpl.field_visibility?.description !== false);
    setShowLoc(tmpl.field_visibility?.location !== false);
  };

  const handleSaveNewTemplate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!templateName.trim()) {
      alert('Template name is required.');
      return;
    }
    try {
      const payload = {
        template_name: templateName,
        company_id: selectedCompany?.id,
        width_mm: widthMm,
        height_mm: heightMm,
        code_type: codeType,
        code_position: codeType === 'BARCODE' ? 'BOTTOM' : 'RIGHT',
        show_logo: showLogo,
        show_company_name: true,
        field_visibility: {
          sap_number: showSap,
          description: showDesc,
          location: showLoc,
        },
        font_settings: {},
        is_default: false,
      };

      const res = await api.post<TagTemplate>('/templates', payload);
      setSaveSuccessMsg(`New template "${res.data.template_name}" created successfully!`);
      setSelectedTemplateId(res.data.id);
      setTimeout(() => setSaveSuccessMsg(''), 3500);
      fetchTemplatesAndSizes();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create new template.');
    }
  };

  const handleUpdateTemplate = async () => {
    if (!selectedTemplateId) return;
    if (!templateName.trim()) {
      alert('Template name is required.');
      return;
    }
    try {
      const payload = {
        template_name: templateName,
        company_id: selectedCompany?.id,
        width_mm: widthMm,
        height_mm: heightMm,
        code_type: codeType,
        code_position: codeType === 'BARCODE' ? 'BOTTOM' : 'RIGHT',
        show_logo: showLogo,
        show_company_name: true,
        field_visibility: {
          sap_number: showSap,
          description: showDesc,
          location: showLoc,
        },
        font_settings: {},
        is_default: false,
      };

      const res = await api.put<TagTemplate>(`/templates/${selectedTemplateId}`, payload);
      setSaveSuccessMsg(`Template "${res.data.template_name}" updated successfully!`);
      setTimeout(() => setSaveSuccessMsg(''), 3500);
      fetchTemplatesAndSizes();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update template.');
    }
  };

  const handleDeleteTemplate = async (tmplId: number, tmplName: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete template "${tmplName}"?`)) {
      return;
    }
    try {
      await api.delete(`/templates/${tmplId}`);
      setSaveSuccessMsg(`Template "${tmplName}" deleted successfully!`);
      setTimeout(() => setSaveSuccessMsg(''), 3500);
      if (selectedTemplateId === tmplId) {
        setSelectedTemplateId(null);
        setTemplateName('New Custom Template');
      }
      fetchTemplatesAndSizes();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete template.');
    }
  };

  const handleResetForm = () => {
    setSelectedTemplateId(null);
    setTemplateName('New Custom Template');
    setWidthMm(70);
    setHeightMm(35);
    setCodeType('BARCODE');
    setShowLogo(true);
    setShowSap(true);
    setShowDesc(true);
    setShowLoc(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Tag Template Library & Designer</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Select from pre-configured corporate template presets or design custom physical tag specifications
          </p>
        </div>
        {saveSuccessMsg && (
          <div className="flex items-center gap-1.5 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded-lg font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {saveSuccessMsg}
          </div>
        )}
      </div>

      {/* System Saved Templates Gallery */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600" />
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              System Saved Template Presets ({templates.length})
            </h2>
          </div>
          <span className="text-[11px] text-slate-500">Click any preset to instantly apply and preview</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {templates.map((tmpl) => {
            const isSelected = selectedTemplateId === tmpl.id;
            return (
              <div
                key={tmpl.id}
                onClick={() => applyTemplate(tmpl)}
                className={`p-3.5 rounded-xl border text-left transition relative flex flex-col justify-between cursor-pointer group ${
                  isSelected
                    ? 'bg-blue-50/80 border-blue-500 shadow-sm ring-2 ring-blue-500/20'
                    : 'bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-slate-100/70'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-bold font-mono bg-slate-200 text-slate-800 px-1.5 py-0.5 rounded">
                      {tmpl.width_mm} × {tmpl.height_mm} mm
                    </span>
                    <div className="flex items-center gap-1">
                      {isSelected && (
                        <span className="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3" />
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={(e) => handleDeleteTemplate(tmpl.id, tmpl.template_name, e)}
                        className="p-1 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition"
                        title="Delete Template"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <h3 className="text-xs font-bold text-slate-900 line-clamp-1">{tmpl.template_name}</h3>
                  <p className="text-[10px] text-slate-500 mt-0.5 font-medium">
                    Symbology: {tmpl.code_type === 'BARCODE' ? '1D Code 128 (Bottom)' : '2D QR Code (Right)'}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px]">
                  <span className="text-blue-600 font-bold group-hover:underline flex items-center gap-1">
                    <Edit3 className="w-3 h-3" />
                    {isSelected ? 'Editing' : 'Load & Edit'}
                  </span>
                  {tmpl.is_default && (
                    <span className="text-[9px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded font-bold uppercase">
                      Default
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Designer & Real-time Live Scaled Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Designer Controls (6 Cols) */}
        <form onSubmit={handleSaveNewTemplate} className="lg:col-span-6 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                {selectedTemplateId ? `Edit Template (#${selectedTemplateId})` : 'Create Custom Template'}
              </h2>
              <p className="text-[11px] text-slate-500">
                {selectedTemplateId
                  ? `Modifying "${templateName}". Click Update to save changes.`
                  : 'Configure physical dimension and visibility properties'}
              </p>
            </div>
            {selectedTemplateId && (
              <button
                type="button"
                onClick={handleResetForm}
                className="text-[11px] text-slate-600 hover:text-slate-900 flex items-center gap-1 px-2 py-1 bg-slate-100 hover:bg-slate-200 rounded font-medium transition"
              >
                <RotateCcw className="w-3 h-3" />
                New Blank
              </button>
            )}
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Template Preset Name</label>
            <input
              type="text"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 font-medium"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Tag Width (mm)</label>
              <input
                type="number"
                value={widthMm}
                onChange={(e) => setWidthMm(Number(e.target.value))}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-mono font-bold"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Tag Height (mm)</label>
              <input
                type="number"
                value={heightMm}
                onChange={(e) => setHeightMm(Number(e.target.value))}
                className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 font-mono font-bold"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1.5">Symbology Placement</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setCodeType('BARCODE')}
                className={`p-2.5 rounded-lg border text-xs font-bold transition ${
                  codeType === 'BARCODE'
                    ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-2xs'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                1D Barcode (Bottom Section)
              </button>
              <button
                type="button"
                onClick={() => setCodeType('QR_CODE')}
                className={`p-2.5 rounded-lg border text-xs font-bold transition ${
                  codeType === 'QR_CODE'
                    ? 'bg-blue-50 border-blue-500 text-blue-700 shadow-2xs'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                2D QR Code (Right Side)
              </button>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <div className="text-xs font-bold text-slate-800">Field Visibility Toggles</div>
            <div className="space-y-2 text-xs">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showLogo}
                  onChange={(e) => setShowLogo(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="font-medium text-slate-700">Display Company Header / Logo</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showSap}
                  onChange={(e) => setShowSap(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="font-medium text-slate-700">Display SAP NO Key-Value</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showDesc}
                  onChange={(e) => setShowDesc(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="font-medium text-slate-700">Display DESCRIPTION Key-Value</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showLoc}
                  onChange={(e) => setShowLoc(e.target.checked)}
                  className="rounded text-blue-600"
                />
                <span className="font-medium text-slate-700">Display LOCATION Key-Value</span>
              </label>
            </div>
          </div>

          {/* Action Buttons: Update, Save As New, Delete */}
          <div className="space-y-2 pt-2">
            {selectedTemplateId ? (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleUpdateTemplate}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center justify-center gap-1.5"
                >
                  <Save className="w-4 h-4" />
                  Update Template #{selectedTemplateId}
                </button>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={handleSaveNewTemplate}
                    className="py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl transition flex items-center justify-center gap-1.5"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Save as New Copy
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDeleteTemplate(selectedTemplateId, templateName)}
                    className="py-2 bg-white hover:bg-red-50 text-red-600 border border-red-200 font-bold text-xs rounded-xl transition flex items-center justify-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Delete Template
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="submit"
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl shadow-md transition flex items-center justify-center gap-1.5"
              >
                <Plus className="w-4 h-4" />
                Save as Custom Template
              </button>
            )}
          </div>
        </form>

        {/* Live Scaled Preview (6 Cols) */}
        <div className="lg:col-span-6 bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col items-center justify-between">
          <div className="w-full flex items-center justify-between pb-3 mb-4 border-b border-slate-100">
            <div className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Real-Time Scaled Preview
            </div>
            <span className="text-xs font-mono text-slate-500 font-semibold">{widthMm} × {heightMm} mm</span>
          </div>

          <div className="my-6 p-6 bg-slate-50/70 border border-slate-200 rounded-xl flex justify-center w-full">
            <AssetTagPreview
              companyName={selectedCompany?.name || 'TATA CONSULTANCY SERVICES LIMITED'}
              logoUrl={showLogo ? selectedCompany?.logo_path : undefined}
              assetId="TATA-000001"
              sapNumber={showSap ? '41009821-0' : undefined}
              description={showDesc ? 'SERVER DELL POWEREDGE R750' : undefined}
              location={showLoc ? 'MUM-DC-BAY-12' : undefined}
              codeType={codeType}
              widthMm={widthMm}
              heightMm={heightMm}
              showActions={true}
              scale={1.1}
            />
          </div>

          <div className="w-full p-3 bg-blue-50/50 border border-blue-200/70 rounded-xl text-xs text-blue-900 font-medium text-center">
            Matches standard thermal transfer and sheet label printing substrates.
          </div>
        </div>
      </div>
    </div>
  );
};
