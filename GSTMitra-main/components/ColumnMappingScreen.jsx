import React, { useState, useEffect } from 'react';
import { logReconciliationUsage } from '../src/utils/logReconciliationUsage';
import { getAuth } from 'firebase/auth';
import { motion } from 'framer-motion';
import { ArrowRight, RefreshCw } from 'lucide-react';

const ALL_FIELDS = [
  { id: 'invoiceNumber', label: 'Invoice Number', keywords: ['invoice', 'inv', 'bill', 'invoice_no'] },
  { id: 'invoiceDate', label: 'Invoice Date', keywords: ['date', 'dt', 'invoice_date', 'invoicedate', 'inv_date', 'bill_date', 'document_date', 'doc_date'] },
  { id: 'invoiceValue', label: 'Invoice Value', keywords: ['value', 'val', 'amount', 'amt', 'total', 'invoice_value', 'invoicevalue', 'total_value'] },
  { id: 'gstin', label: 'GSTIN', keywords: ['gstin', 'gst', 'tin', 'supplier_gstin', 'ctin'] },
  { id: 'taxableValue', label: 'Taxable Value', keywords: ['taxable'] },
];

const USER_REQUIRED_FIELDS = [
  { id: 'gstin', label: 'GSTIN' },
  { id: 'invoiceValue', label: 'Invoice Value' },
  { id: 'taxableValue', label: 'Taxable Value' },
  { id: 'invoiceDate', label: 'Invoice Date' },
]; // Invoice Number, IGST, CGST, SGST removed as per user request

const ColumnMappingScreen = ({ gstr1, gstr2, onMappingComplete, onCancel }) => {
  const gstr2Type = '2B';
  const [gstr1Mapping, setGstr1Mapping] = useState({});
  const [gstr2Mapping, setGstr2Mapping] = useState({});
  const [gstr1StartRow, setGstr1StartRow] = useState(2); // Default to 2 assuming one header row
  const [gstr2StartRow, setGstr2StartRow] = useState(2);

  const getColumnLetter = (index) => String.fromCharCode(65 + index);

  // Generate preview data based on current selections
  const getPreviewData = (fileData, mapping, startRow) => {
    if (!fileData.preview || !fileData.preview.length) return [];
    
    // Get all available data for proper filtering
    let allData = fileData.preview;
    
    // Apply start row filtering - startRow is 1-indexed, array is 0-indexed
    // If startRow is 2, we want to skip the first row (index 0)
    const filteredData = allData.slice(Math.max(0, startRow - 1));
    
    // Take first 3 rows for preview
    return filteredData.slice(0, 3).map(row => {
      const previewRow = {};
      USER_REQUIRED_FIELDS.forEach(field => {
        const columnHeader = mapping[field.id];
        if (columnHeader && row[columnHeader] !== undefined) {
          previewRow[field.label] = row[columnHeader];
        } else {
          previewRow[field.label] = '-';
        }
      });
      return previewRow;
    });
  };

  useEffect(() => {
    const autoMap = (headers) => {
      const initialMapping = {};
      const gstinPatterns = ['gstin', 'gst', 'tin', 'supplier_gstin', 'ctin'];
      const invoiceValuePatterns = ['invoice_value', 'invoicevalue', 'total', 'amount', 'value', 'invoice_amount', 'total_value'];
      const invoiceDatePatterns = ['invoice_date', 'invoicedate', 'date', 'inv_date', 'bill_date', 'document_date', 'doc_date'];
      const invoiceNumberPatterns = ['invoice_number', 'invoicenumber', 'inv_no', 'invoice_no', 'document_number', 'doc_no'];
      headers.forEach(header => {
        const lowerHeader = header.toLowerCase();
        
        if (gstinPatterns.some(pattern => lowerHeader.includes(pattern))) {
          initialMapping.gstin = header;
        } else if (invoiceValuePatterns.some(pattern => lowerHeader.includes(pattern))) {
          initialMapping.invoiceValue = header;
        } else if (invoiceDatePatterns.some(pattern => lowerHeader.includes(pattern))) {
          initialMapping.invoiceDate = header;
        } else if (invoiceNumberPatterns.some(pattern => lowerHeader.includes(pattern))) {
          initialMapping.invoiceNumber = header;
        }
      });
      return initialMapping;
    };

    if (gstr1?.headers) setGstr1Mapping(autoMap(gstr1.headers));
    if (gstr2?.headers) setGstr2Mapping(autoMap(gstr2.headers));
  }, [gstr1, gstr2]);

  const handleMappingChange = (fileType, fieldId, header) => {
    // Convert placeholder value back to empty string if needed
    const actualHeader = header.startsWith('__EMPTY_') ? '' : header;
    if (fileType === 'gstr1') {
      setGstr1Mapping(prev => ({ ...prev, [fieldId]: actualHeader }));
    } else {
      setGstr2Mapping(prev => ({ ...prev, [fieldId]: actualHeader }));
    }
  };

  const isGstr1MappingComplete = !gstr1?.headers || USER_REQUIRED_FIELDS.every(field => gstr1Mapping[field.id]);
  const isGstr2MappingComplete = !gstr2?.headers || USER_REQUIRED_FIELDS.every(field => gstr2Mapping[field.id]);
  const isMappingComplete = isGstr1MappingComplete && isGstr2MappingComplete;

  const handleSubmit = async () => {
    if (isMappingComplete) {
      // Track reconciliation usage
      try {
        const auth = getAuth();
        const user = auth.currentUser;
        if (user) {
          await logReconciliationUsage(user.uid);
        }
      } catch (e) {
        console.error('Failed to log reconciliation usage:', e);
      }
      onMappingComplete(gstr1Mapping, gstr2Mapping, gstr1StartRow, gstr2StartRow);
    }
  };

  // Debug: Log headers to see what is available
  console.log('Your GSTR-2B headers:', gstr1.headers);
  console.log('GSTR-2 headers:', gstr2.headers);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
        className="w-full max-w-4xl"
      >
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-text-primary mb-2">Map Your Columns</h1>
          <p className="text-text-secondary">Match your CSV columns to the required fields for reconciliation.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Your GSTR-2B Mapping */}
          <div className="neumorphic-card p-6">
            <h2 className="text-2xl font-bold text-center text-accent-blue mb-6">Your GSTR-2B</h2>
            {gstr1?.headers ? (
              <>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-text-secondary mb-2">Data Starts From Row</label>
                  <input
                    type="number"
                    min="1"
                    value={gstr1StartRow}
                    onChange={(e) => setGstr1StartRow(Math.max(1, parseInt(e.target.value, 10) || 1))}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 text-text-primary focus:outline-none focus:border-accent-blue"
                  />
                </div>
                {USER_REQUIRED_FIELDS.map(field => (
                  <div key={`gstr1-${field.id}`} className="mb-4">
                    <label className="block text-sm font-medium text-text-secondary mb-2">{field.label}</label>
                    <select
                      value={gstr1Mapping[field.id] || ''}
                      onChange={(e) => handleMappingChange('gstr1', field.id, e.target.value)}
                      className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 text-text-primary focus:outline-none focus:border-accent-blue"
                    >
                      <option value="" disabled>Select column...</option>
                      {gstr1.headers.map((header, index) => {
                        const optValue = header === '' ? `__EMPTY_${index}` : header;
                        const display = header === '' ? `(blank)` : '';
                        return (
                          <option key={`${optValue}`} value={optValue}>Column {getColumnLetter(index)} {display}</option>
                        );
                      })}
                    </select>
                  </div>
                ))}
              </>
            ) : <p className="text-center text-text-secondary">JSON file uploaded. No mapping needed.</p>}
          </div>

          {/* GSTR-2 Mapping */}
          <div className="neumorphic-card p-6">
            <h2 className="text-2xl font-bold text-center text-accent-green mb-6">Government Provided GSTR-{gstr2Type}</h2>
            {gstr2?.headers ? (
              <>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-text-secondary mb-2">Data Starts From Row</label>
                  <input
                    type="number"
                    min="1"
                    value={gstr2StartRow}
                    onChange={(e) => setGstr2StartRow(Math.max(1, parseInt(e.target.value, 10) || 1))}
                    className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 text-text-primary focus:outline-none focus:border-accent-blue"
                  />
                </div>
                {USER_REQUIRED_FIELDS.map(field => (
                  <div key={`gstr2-${field.id}`} className="mb-4">
                    <label className="block text-sm font-medium text-text-secondary mb-2">{field.label}</label>
                    <select
                      value={gstr2Mapping[field.id] || ''}
                      onChange={(e) => handleMappingChange('gstr2', field.id, e.target.value)}
                      className="w-full bg-dark-bg border border-dark-border rounded-lg p-2 text-text-primary focus:outline-none focus:border-accent-blue"
                    >
                      <option value="" disabled>Select column...</option>
                      {gstr2.headers.map((header, index) => {
                        const optValue = header === '' ? `__EMPTY_${index}` : header;
                        const display = header === '' ? `(blank)` : '';
                        return (
                          <option key={`${optValue}`} value={optValue}>Column {getColumnLetter(index)} {display}</option>
                        );
                      })}
                    </select>
                  </div>
                ))}
              </>
            ) : <p className="text-center text-text-secondary">JSON file uploaded. No mapping needed.</p>}
          </div>
        </div>
        
        <div className="text-center mb-8">
          <motion.button
            onClick={handleSubmit}
            disabled={!isMappingComplete}
            className={`bg-white text-black font-bold text-lg px-12 py-4 rounded-xl shadow-md transition-colors duration-300 ${
              isMappingComplete
                ? 'hover:bg-gray-200'
                : 'opacity-50 cursor-not-allowed'
            }`}
            whileTap={{ scale: 0.95 }}
          >
            {isMappingComplete ? 'Confirm & Reconcile' : 'Complete Mapping to Continue'}
            <ArrowRight className="inline-block ml-2" />
          </motion.button>
          <button onClick={onCancel} className="mt-4 bg-gray-100 text-gray-700 font-bold rounded-lg shadow hover:bg-gray-200 transition-colors flex items-center gap-2 mx-auto">
            <RefreshCw size={14} /> Start Over
          </button>
        </div>

        {/* Data Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          {/* Your GSTR-2B Preview */}
          {gstr1?.headers && (
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-accent-blue mb-4">Your GSTR-2B Comparison Preview</h3>
              <p className="text-sm text-text-secondary mb-3">
                Data starting from row {gstr1StartRow} (after headers) - showing what will be compared:
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-border">
                      {USER_REQUIRED_FIELDS.map(field => (
                        <th key={field.id} className="text-left p-2 text-text-secondary">
                          {field.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {getPreviewData(gstr1, gstr1Mapping, gstr1StartRow).map((row, index) => (
                      <tr key={index} className="border-b border-dark-border/50">
                        {USER_REQUIRED_FIELDS.map(field => (
                          <td key={field.id} className="p-2 text-text-primary">
                            {row[field.label] || '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* GSTR-2 Preview */}
          {gstr2?.headers && (
            <div className="neumorphic-card p-6">
              <h3 className="text-lg font-semibold text-accent-green mb-4">Government Provided GSTR-{gstr2Type} Comparison Preview</h3>
              <p className="text-sm text-text-secondary mb-3">
                Data starting from row {gstr2StartRow} (after headers) - showing what will be compared:
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-dark-border">
                      {USER_REQUIRED_FIELDS.map(field => (
                        <th key={field.id} className="text-left p-2 text-text-secondary">
                          {field.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {getPreviewData(gstr2, gstr2Mapping, gstr2StartRow).map((row, index) => (
                      <tr key={index} className="border-b border-dark-border/50">
                        {USER_REQUIRED_FIELDS.map(field => (
                          <td key={field.id} className="p-2 text-text-primary">
                            {row[field.label] || '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default ColumnMappingScreen;
  