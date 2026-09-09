import React, { useState, useRef } from 'react';
import { 
  X, 
  UploadCloud, 
  FileSpreadsheet, 
  Download, 
  CheckCircle2, 
  AlertCircle, 
  AlertTriangle, 
  Trash2, 
  Briefcase,
  HelpCircle,
  ArrowRight
} from 'lucide-react';
import { AuditType, Engagement, ParsedEngagementRow, FirmProfile } from '../../types/audit';
import { TemplateService } from '../../services/templateService';

interface BulkEngagementUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  auditTypes: AuditType[];
  firmProfile: FirmProfile;
  onImportEngagements: (engagements: Engagement[]) => void;
}

export const BulkEngagementUploadModal: React.FC<BulkEngagementUploadModalProps> = ({
  isOpen,
  onClose,
  auditTypes,
  firmProfile,
  onImportEngagements,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedRows, setParsedRows] = useState<ParsedEngagementRow[]>([]);
  const [validEngagements, setValidEngagements] = useState<Engagement[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDownloadSample = () => {
    TemplateService.downloadAssignmentsSampleTemplate(auditTypes);
  };

  const handleFileProcess = async (file: File) => {
    if (!file) return;
    
    // Check file extension
    const name = file.name.toLowerCase();
    if (!name.endsWith('.xlsx') && !name.endsWith('.xls') && !name.endsWith('.csv')) {
      setParseError('Please upload a valid Excel spreadsheet (.xlsx, .xls) or CSV file.');
      return;
    }

    setSelectedFile(file);
    setIsParsing(true);
    setParseError(null);

    try {
      const result = await TemplateService.parseAssignmentsExcel(
        file, 
        auditTypes, 
        firmProfile.partnerName || 'CA Ritesh Garg, FCA'
      );

      if (result.parsedRows.length === 0) {
        setParseError('The uploaded file contains no data rows or valid header columns. Please use our sample template.');
        setParsedRows([]);
        setValidEngagements([]);
      } else {
        setParsedRows(result.parsedRows);
        setValidEngagements(result.validEngagements);
      }
    } catch (err: any) {
      console.error('Failed to parse assignments excel:', err);
      setParseError(err.message || 'Error parsing Excel file. Please ensure proper spreadsheet format.');
      setParsedRows([]);
      setValidEngagements([]);
    } finally {
      setIsParsing(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileProcess(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileProcess(e.target.files[0]);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setParsedRows([]);
    setValidEngagements([]);
    setParseError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleConfirmImport = () => {
    if (validEngagements.length === 0) return;
    onImportEngagements(validEngagements);
    handleReset();
    onClose();
  };

  const validCount = parsedRows.filter(r => r.isValid).length;
  const invalidCount = parsedRows.filter(r => !r.isValid).length;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div 
        className="bg-white w-full max-w-4xl rounded-2xl shadow-2xl border border-stone-200 flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-200 bg-[#F5F2ED]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#5A5A40] text-white flex items-center justify-center shadow-xs">
              <FileSpreadsheet className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="text-base font-bold text-stone-800">Bulk Upload Audit Assignments (Excel)</h2>
              <p className="text-xs text-stone-600">
                Import multiple client audit engagements at once with instant validation & error checking.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-600 hover:bg-stone-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Sample Template Download Bar */}
          <div className="p-4 bg-amber-50/60 rounded-xl border border-amber-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <HelpCircle className="w-4 h-4 text-amber-800 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-amber-950">Download Pre-Formatted Excel Template</h4>
                <p className="text-[11px] text-amber-900 leading-relaxed mt-0.5">
                  Get our official sample file with pre-set columns (Client Name, Code, Audit Type, FY, Partner, Dates, Status) and realistic sample rows.
                </p>
              </div>
            </div>
            <button
              onClick={handleDownloadSample}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs transition-colors shrink-0 self-start sm:self-center"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Sample (.xlsx)</span>
            </button>
          </div>

          {/* File Upload Area */}
          {!selectedFile ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                isDragging 
                  ? 'border-[#5A5A40] bg-[#F5F2ED]' 
                  : 'border-stone-300 hover:border-[#5A5A40] hover:bg-stone-50/50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx, .xls, .csv"
                onChange={handleFileInputChange}
                className="hidden"
              />
              <div className="w-12 h-12 rounded-2xl bg-[#F5F2ED] text-[#5A5A40] flex items-center justify-center mx-auto mb-3 shadow-xs">
                <UploadCloud className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-stone-800">
                Click to browse or drag & drop your Excel file here
              </h3>
              <p className="text-xs text-stone-500 mt-1">
                Supports Microsoft Excel (.xlsx, .xls) and CSV (.csv)
              </p>
            </div>
          ) : (
            <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-lg bg-[#5A5A40] text-amber-300 flex items-center justify-center shrink-0">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <div className="truncate">
                  <p className="text-xs font-bold text-stone-800 truncate">{selectedFile.name}</p>
                  <p className="text-[11px] text-stone-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB • {parsedRows.length} total assignment row(s) found
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-2.5 py-1 text-xs font-semibold text-stone-600 hover:text-stone-900 border border-stone-300 rounded-lg hover:bg-white transition-colors"
                >
                  Change File
                </button>
                <button
                  onClick={handleReset}
                  className="p-1 text-stone-400 hover:text-rose-600 rounded-lg transition-colors"
                  title="Remove file"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx, .xls, .csv"
                onChange={handleFileInputChange}
                className="hidden"
              />
            </div>
          )}

          {/* Parse Error */}
          {parseError && (
            <div className="p-3.5 bg-rose-50 rounded-xl border border-rose-200 text-xs text-rose-700 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-bold">Excel Parsing Issue</p>
                <p className="mt-0.5 text-rose-600">{parseError}</p>
              </div>
            </div>
          )}

          {/* Parsing Spinner */}
          {isParsing && (
            <div className="p-8 text-center space-y-2">
              <div className="w-8 h-8 border-3 border-[#5A5A40] border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-xs text-stone-600 font-medium">Validating audit assignments and mapping fields...</p>
            </div>
          )}

          {/* Validation & Preview Table */}
          {parsedRows.length > 0 && (
            <div className="space-y-3">
              {/* Summary Stats */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#F5F2ED] rounded-xl border border-[#DED9D0] text-xs">
                <div className="flex items-center gap-4">
                  <span className="text-stone-700">
                    Total Rows: <strong className="text-stone-900">{parsedRows.length}</strong>
                  </span>
                  <span className="text-emerald-700 flex items-center gap-1 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {validCount} Ready to Import
                  </span>
                  {invalidCount > 0 && (
                    <span className="text-rose-700 flex items-center gap-1 font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      {invalidCount} Invalid (Will be skipped)
                    </span>
                  )}
                </div>
              </div>

              {/* Table */}
              <div className="border border-stone-200 rounded-xl overflow-hidden shadow-2xs">
                <div className="max-h-72 overflow-y-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-stone-100 text-stone-700 sticky top-0 border-b border-stone-200 font-semibold">
                      <tr>
                        <th className="py-2.5 px-3 w-12 text-center">#</th>
                        <th className="py-2.5 px-3 w-16 text-center">Status</th>
                        <th className="py-2.5 px-3">Client Name</th>
                        <th className="py-2.5 px-3">Code</th>
                        <th className="py-2.5 px-3">Audit Type</th>
                        <th className="py-2.5 px-3">FY</th>
                        <th className="py-2.5 px-3">Partner / Dates</th>
                        <th className="py-2.5 px-3">Stage</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 bg-white">
                      {parsedRows.map((row, idx) => (
                        <tr key={idx} className={row.isValid ? 'hover:bg-stone-50/60' : 'bg-rose-50/40 hover:bg-rose-50/70'}>
                          <td className="py-2 px-3 text-center text-stone-400 font-mono text-[11px]">{idx + 1}</td>
                          <td className="py-2 px-3 text-center">
                            {row.isValid ? (
                              <span className="inline-flex items-center text-emerald-600" title="Valid assignment">
                                <CheckCircle2 className="w-4 h-4" />
                              </span>
                            ) : (
                              <span className="inline-flex items-center text-rose-600" title={row.validationError}>
                                <AlertCircle className="w-4 h-4" />
                              </span>
                            )}
                          </td>
                          <td className="py-2 px-3 font-semibold text-stone-800">
                            <div>{row.clientName || <span className="text-rose-500 italic">Missing Client Name</span>}</div>
                            {row.clientPanGstin && (
                              <div className="text-[10px] text-stone-400 font-mono mt-0.5">{row.clientPanGstin}</div>
                            )}
                            {row.validationError && (
                              <div className="text-[10px] text-rose-600 font-normal mt-0.5">{row.validationError}</div>
                            )}
                          </td>
                          <td className="py-2 px-3 font-mono text-[11px] text-stone-700">
                            {row.clientCode}
                          </td>
                          <td className="py-2 px-3">
                            <span className="inline-block px-2 py-0.5 rounded-md bg-[#F5F2ED] text-stone-800 font-medium text-[11px] border border-[#DED9D0]">
                              {row.matchedAuditTypeName || row.auditTypeCodeOrName}
                            </span>
                          </td>
                          <td className="py-2 px-3 font-mono text-stone-600 text-[11px]">
                            {row.financialYear}
                          </td>
                          <td className="py-2 px-3 text-[11px] text-stone-600">
                            <div>{row.engagementPartner}</div>
                            <div className="text-[10px] text-stone-400 mt-0.5">{row.startDate} to {row.endDate}</div>
                          </td>
                          <td className="py-2 px-3">
                            <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold bg-stone-100 text-stone-700 border border-stone-200">
                              {row.overallStatus}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-stone-200 bg-stone-50 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg border border-stone-300 text-stone-700 text-xs font-semibold hover:bg-white transition-colors"
          >
            Cancel
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownloadSample}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-stone-300 bg-white text-stone-700 text-xs font-semibold hover:bg-stone-100 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Sample Template (.xlsx)</span>
            </button>

            <button
              type="button"
              onClick={handleConfirmImport}
              disabled={validCount === 0}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition-colors ${
                validCount > 0
                  ? 'bg-[#5A5A40] hover:bg-[#4A4A34] text-white'
                  : 'bg-stone-200 text-stone-400 cursor-not-allowed'
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-amber-300" />
              <span>Import {validCount} Valid Assignment{validCount !== 1 ? 's' : ''}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
