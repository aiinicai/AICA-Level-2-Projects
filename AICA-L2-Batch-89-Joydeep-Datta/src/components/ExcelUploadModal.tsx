import React, { useState } from 'react';
import { X, Upload, FileSpreadsheet, CheckCircle2, AlertCircle, Download } from 'lucide-react';
import { EmployeeMaster, EmployeeDeclaration } from '../types/payroll';
import {
  parseEmployeeMasterExcel,
  parseEmployeeDeclarationExcel,
  exportEmployeeMasterExcel,
  exportEmployeeDeclarationExcel,
} from '../utils/excelHandler';

interface ExcelUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportMaster: (employees: EmployeeMaster[]) => void;
  onImportDeclarations: (declarations: EmployeeDeclaration[]) => void;
  currentEmployees: EmployeeMaster[];
  currentDeclarations: EmployeeDeclaration[];
}

export const ExcelUploadModal: React.FC<ExcelUploadModalProps> = ({
  isOpen,
  onClose,
  onImportMaster,
  onImportDeclarations,
  currentEmployees,
  currentDeclarations,
}) => {
  if (!isOpen) return null;

  const [importType, setImportType] = useState<'master' | 'declaration'>('master');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [parsedMaster, setParsedMaster] = useState<EmployeeMaster[] | null>(null);
  const [parsedDecl, setParsedDecl] = useState<EmployeeDeclaration[] | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedFile(file);
    setParseError(null);
    setLoading(true);

    try {
      if (importType === 'master') {
        const data = await parseEmployeeMasterExcel(file);
        if (data.length === 0) {
          setParseError('No employee records found in Excel file. Please check column headers.');
        } else {
          setParsedMaster(data);
        }
      } else {
        const data = await parseEmployeeDeclarationExcel(file);
        if (data.length === 0) {
          setParseError('No declaration records found in Excel file. Please check column headers.');
        } else {
          setParsedDecl(data);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to parse Excel file';
      setParseError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmImport = () => {
    if (importType === 'master' && parsedMaster) {
      onImportMaster(parsedMaster);
      onClose();
    } else if (importType === 'declaration' && parsedDecl) {
      onImportDeclarations(parsedDecl);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-bold text-slate-900">
              Bulk Data Ingestion via Excel (.xlsx)
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-5 text-xs">
          {/* Target Master Choice */}
          <div>
            <label className="block font-semibold text-slate-700 mb-2">Select Ingestion Category:</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => {
                  setImportType('master');
                  setSelectedFile(null);
                  setParsedMaster(null);
                  setParsedDecl(null);
                  setParseError(null);
                }}
                className={`p-3 rounded-xl border text-left transition-all ${
                  importType === 'master'
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-950 font-bold ring-1 ring-indigo-500'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="text-xs font-bold">01_Employee_Master</div>
                <div className="text-[11px] font-normal text-slate-500 mt-0.5">
                  Employees, CTC, Basic, DOJ, DOL, PAN, and Bank details
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  setImportType('declaration');
                  setSelectedFile(null);
                  setParsedMaster(null);
                  setParsedDecl(null);
                  setParseError(null);
                }}
                className={`p-3 rounded-xl border text-left transition-all ${
                  importType === 'declaration'
                    ? 'border-indigo-600 bg-indigo-50/50 text-indigo-950 font-bold ring-1 ring-indigo-500'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                }`}
              >
                <div className="text-xs font-bold">02_Employee_Declaration</div>
                <div className="text-[11px] font-normal text-slate-500 mt-0.5">
                  Tax Regimes, 80C, HRA Rent, 80D, 24(b), and Proof Status
                </div>
              </button>
            </div>
          </div>

          {/* Template Download Prompt */}
          <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-slate-600">
              Need the exact Excel template format with pre-filled sample headers?
            </span>
            <button
              type="button"
              onClick={() => {
                if (importType === 'master') {
                  exportEmployeeMasterExcel(currentEmployees);
                } else {
                  exportEmployeeDeclarationExcel(currentDeclarations);
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-semibold text-indigo-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition-colors shadow-2xs"
            >
              <Download className="h-3.5 w-3.5" />
              Download Template
            </button>
          </div>

          {/* File Upload Drop Area */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-indigo-500 transition-colors bg-slate-50/50">
            <input
              type="file"
              id="excel-file-input"
              accept=".xlsx, .xls"
              onChange={handleFileChange}
              className="hidden"
            />
            <label htmlFor="excel-file-input" className="cursor-pointer block">
              <Upload className="h-8 w-8 text-indigo-500 mx-auto mb-2" />
              <span className="font-semibold text-slate-800 block text-xs">
                {selectedFile ? selectedFile.name : 'Click to select an Excel spreadsheet (.xlsx)'}
              </span>
              <span className="text-[11px] text-slate-400 block mt-1">
                Supports Standard Microsoft Excel (.xlsx) format
              </span>
            </label>
          </div>

          {loading && (
            <div className="text-center py-4 text-slate-500 animate-pulse">
              Parsing Excel workbook sheets and validating rows...
            </div>
          )}

          {parseError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <div>
                <strong>Error importing file:</strong> {parseError}
              </div>
            </div>
          )}

          {/* Preview of Parsed Records */}
          {parsedMaster && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                Parsed {parsedMaster.length} employee records successfully.
              </div>
              <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 bg-slate-50">
                {parsedMaster.map((emp, i) => (
                  <div key={i} className="p-2 text-[11px] flex justify-between items-center">
                    <span className="font-mono font-bold text-slate-800">{emp.employeeCode}</span>
                    <span className="font-medium text-slate-900">{emp.employeeName}</span>
                    <span className="text-slate-500">{emp.department}</span>
                    <span className="font-mono">Basic: ₹{emp.basicMonthly.toLocaleString('en-IN')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsedDecl && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-emerald-700 font-semibold">
                <CheckCircle2 className="h-4 w-4" />
                Parsed {parsedDecl.length} tax declaration records successfully.
              </div>
              <div className="max-h-40 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100 bg-slate-50">
                {parsedDecl.map((d, i) => (
                  <div key={i} className="p-2 text-[11px] flex justify-between items-center">
                    <span className="font-mono font-bold text-slate-800">{d.employeeCode}</span>
                    <span className="font-semibold text-indigo-700">{d.regimeDeclared} Regime</span>
                    <span className="text-slate-500">Rent: ₹{d.rentPaidAnnual.toLocaleString('en-IN')}</span>
                    <span className="font-mono text-slate-600">Status: {d.proofStatus}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={(!parsedMaster && !parsedDecl) || loading}
            onClick={handleConfirmImport}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition-colors shadow-xs"
          >
            <CheckCircle2 className="h-4 w-4" />
            Merge & Ingest Data
          </button>
        </div>
      </div>
    </div>
  );
};
