import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Search, Download, RotateCcw } from 'lucide-react';

const DetailedView = ({ category, data, onBack, onStartOver }) => {
  const gstr2Type = '2B';
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOption, setSortOption] = useState('date-desc'); // default: newest first

  // A robust date parser to handle DD-MM-YYYY or DD/MM/YYYY formats
  const parseDate = (dateString) => {
    if (!dateString || typeof dateString !== 'string') return null;
    const parts = dateString.split(/[/-]/);
    if (parts.length === 3) {
      const [day, month, year] = parts;
      // Handles both YYYY-MM-DD and DD-MM-YYYY by checking string length
      if (year.length === 4) {
        return new Date(`${year}-${month}-${day}`);
      }
      if (day.length === 4) {
        return new Date(`${day}-${month}-${parts[2]}`);
      }
    }
    const parsedDate = new Date(dateString);
    return isNaN(parsedDate) ? null : parsedDate;
  };
const sortOptions = [
  { value: 'value-desc', label: 'Invoice Value: High to Low' },
  { value: 'value-asc', label: 'Invoice Value: Low to High' },
  { value: 'date-desc', label: 'Date: Newest First' },
  { value: 'date-asc', label: 'Date: Oldest First' },
  { value: 'gstin-asc', label: 'GSTIN: A-Z' },
  { value: 'gstin-desc', label: 'GSTIN: Z-A' },
  { value: 'invoiceNumber-asc', label: 'Invoice No: A-Z' },
  { value: 'invoiceNumber-desc', label: 'Invoice No: Z-A' },
];
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  if (!data) return null;

  // Special config for zero tax bills
  const isZeroTax = data.id === 'zeroTaxBills';
  const zeroTaxDescription = 'These are invoices where Invoice Value equals Taxable Value (no tax charged). They are shown separately for your reference.';

  const handleFilterChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
    setCurrentPage(1); // Reset to first page on filter change
  };

  const filteredData = data.data.filter(invoice => {
  // Common search across all fields
  const search = searchTerm.toLowerCase();
  if (!search) return true;
  if (data.id === 'mismatched') {
    return (
      Object.values(invoice.gstr1).some(val => val?.toString().toLowerCase().includes(search)) ||
      Object.values(invoice.gstr2).some(val => val?.toString().toLowerCase().includes(search))
    );
  }
  return Object.values(invoice).some(val => val?.toString().toLowerCase().includes(search));
});

// Sorting logic (Your GSTR-2B vs Government Provided GSTR-2B)
const getSortValue = (inv, field) => {
  if (!inv) return '';
  if (data.id === 'mismatched') {
    // Prefer Your GSTR-2B for sorting, fallback to Government Provided GSTR-2B
    return inv.gstr1?.[field] ?? inv.gstr2?.[field] ?? '';
  }
  return inv[field] ?? '';
};

const sortedData = [...filteredData].sort((a, b) => {
  switch (sortOption) {
    case 'value-desc':
      return (parseFloat(getSortValue(b, 'invoiceValue')) || 0) - (parseFloat(getSortValue(a, 'invoiceValue')) || 0);
    case 'value-asc':
      return (parseFloat(getSortValue(a, 'invoiceValue')) || 0) - (parseFloat(getSortValue(b, 'invoiceValue')) || 0);
    case 'date-desc': {
      const dateB = parseDate(getSortValue(b, 'invoiceDate'));
      const dateA = parseDate(getSortValue(a, 'invoiceDate'));
      if (!dateA) return 1;
      if (!dateB) return -1;
      return dateB - dateA;
    }
    case 'date-asc': {
      const dateA = parseDate(getSortValue(a, 'invoiceDate'));
      const dateB = parseDate(getSortValue(b, 'invoiceDate'));
      if (!dateA) return 1;
      if (!dateB) return -1;
      return dateA - dateB;
    }
    case 'gstin-asc':
      return getSortValue(a, 'gstin').localeCompare(getSortValue(b, 'gstin'));
    case 'gstin-desc':
      return getSortValue(b, 'gstin').localeCompare(getSortValue(a, 'gstin'));
    case 'invoiceNumber-asc':
      return getSortValue(a, 'invoiceNumber').localeCompare(getSortValue(b, 'invoiceNumber'));
    case 'invoiceNumber-desc':
      return getSortValue(b, 'invoiceNumber').localeCompare(getSortValue(a, 'invoiceNumber'));
    default:
      return 0;
  }
});

  const totalPages = Math.ceil(sortedData.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = sortedData.slice(startIndex, startIndex + itemsPerPage);

  const exportCategoryData = () => {
    let csv = 'Invoice Date,Invoice Value,GSTIN,Taxable Value,Status\n';
    
    data.data.forEach(invoice => {
      csv += `"${invoice.invoiceDate || ''}","${invoice.invoiceValue || ''}","${invoice.gstin || ''}","${invoice.taxableValue || ''}","${data.title}"\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.id}-invoices-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const renderMismatchedCell = (gstr1Value, gstr2Value) => (
    <div className="bg-red-900/30 p-2 rounded-md ring-1 ring-red-500/50">
      <p className="text-xs text-red-300 line-through">Your GSTR-2B: {gstr1Value}</p>
      <p className="text-sm font-semibold text-red-200">Government Provided GSTR-2B: {gstr2Value}</p>
    </div>
  );

  const renderCell = (invoice, field) => {
    const isMismatched = data.id === 'mismatched' && invoice.differences && invoice.differences[field];
    const value = invoice[field];

    const formatValue = (val) => {
      if (typeof val === 'number') return `₹${val.toLocaleString()}`;
      return val || 'N/A';
    };

    if (isMismatched) {
      return renderMismatchedCell(
        formatValue(invoice.differences[field].gstr1),
        formatValue(invoice.differences[field].gstr2)
      );
    }

    return formatValue(value);
  };

  const renderInvoiceRow = (invoice, index) => {
    const isEven = index % 2 === 0;
    const isMismatchedRow = data.id === 'mismatched' && invoice.differences;

    return (
      <motion.tr
        key={index}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: index * 0.05 }}
        className={`${isEven ? 'bg-dark-card' : 'bg-dark-bg'} ${isMismatchedRow ? '' : 'hover:bg-dark-border'} transition-colors`}
      >
        
        <td className="px-4 py-3 text-sm text-text-secondary">{renderCell(invoice, 'invoiceDate')}</td>
        <td className={`px-4 py-3 text-sm font-semibold ${invoice.differences?.invoiceValue ? 'text-red-200' : 'text-text-primary'}`}>{renderCell(invoice, 'invoiceValue')}</td>
        <td className={`px-4 py-3 text-sm font-mono ${invoice.differences?.gstin ? 'text-red-200' : 'text-text-secondary'}`}>{renderCell(invoice, 'gstin')}</td>
        <td className={`px-4 py-3 text-sm ${invoice.differences?.taxableValue ? 'text-red-200' : 'text-text-secondary'}`}>{renderCell(invoice, 'taxableValue')}</td>
      </motion.tr>
    );
  };

  return (
    <div className="min-h-screen px-4 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className={`mb-8 flex items-center gap-4 ${isZeroTax ? 'border-l-8 border-yellow-400 bg-yellow-50/10' : ''}`}
      >
        <button
          onClick={onBack}
          className={`neumorphic-card p-2 rounded-full text-text-primary hover:shadow-glow-blue transition-all duration-300 ${isZeroTax ? 'border-yellow-300' : ''}`}
        >
          <ArrowLeft size={22} />
        </button>
        <div>
          <h1 className={`text-2xl md:text-3xl font-bold mb-1 ${isZeroTax ? 'text-white' : 'text-text-primary'}`}>
            {data.title}
          </h1>
          <p className={`text-text-secondary text-base`}>
            {isZeroTax ? zeroTaxDescription : data.description}
          </p>
        </div>
      </motion.div>
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="text-text-secondary">
          Showing {filteredData.length} of {data.count} invoices
        </div>
        <div className="flex gap-2">
          <button
            onClick={exportCategoryData}
            className="flex items-center gap-2 bg-gradient-to-r from-accent-green to-accent-blue text-dark-bg font-medium py-2 px-4 rounded-lg transition-all duration-300 hover:shadow-glow-green text-sm"
          >
            <Download size={16} />
            Export
          </button>
          <button
            onClick={onStartOver}
            className="flex items-center gap-2 neumorphic-card text-text-primary font-medium py-2 px-4 rounded-lg transition-all duration-300 hover:shadow-glow-blue text-sm"
          >
            <RotateCcw size={16} />
            Start Over
          </button>
        </div>
      </div>



      {/* Search & Sort UI */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="flex flex-col md:flex-row gap-4 mb-6 items-center"
      >
        <div className="relative w-full md:w-2/3">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-secondary" size={20} />
          <input
            type="text"
            placeholder="Search invoices by any field..."
            value={searchTerm}
            onChange={e => { setSearchTerm(e.target.value); setCurrentPage(1); }}
            className="w-full bg-black text-white placeholder-gray-400 pl-12 pr-4 py-3 rounded-xl border border-dark-border focus:outline-none focus:border-accent-blue focus:shadow-glow-blue transition-all duration-300"
            style={{ color: 'white', backgroundColor: 'black' }}
          />
        </div>
        <div className="w-full md:w-1/3">
          <select
            value={sortOption}
            onChange={e => setSortOption(e.target.value)}
            className="w-full neumorphic-input-inset py-3 px-4 bg-dark-card text-text-primary rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-blue"
          >
            {sortOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </motion.div>

      {/* Table */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="neumorphic-card overflow-hidden mb-6"
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-dark-border">
              <tr>
                
<th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
  Date
</th>
<th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
  Invoice Value
</th>
<th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
  GSTIN
</th>
<th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
  Taxable Value
</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.length > 0 ? (
                paginatedData.map((invoice, index) => renderInvoiceRow(invoice, index))
              ) : (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-text-secondary">
                    {searchTerm ? 'No invoices match your search' : 'No invoices found'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* Pagination */}
      {totalPages > 1 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6 }}
          className="flex justify-center items-center gap-2"
        >
          <button
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="neumorphic-card px-4 py-2 rounded-lg text-text-primary disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-glow-blue transition-all duration-300"
          >
            Previous
          </button>
          
          <div className="flex gap-1">
            {[...Array(totalPages)].map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrentPage(i + 1)}
                className={`px-3 py-2 rounded-lg transition-all duration-300 ${
                  currentPage === i + 1
                    ? 'bg-accent-blue text-dark-bg shadow-glow-blue'
                    : 'neumorphic-card text-text-primary hover:shadow-glow-blue'
                }`}
              >
                {i + 1}
              </button>
            ))}
          </div>
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="neumorphic-card px-4 py-2 rounded-lg text-text-primary disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-glow-blue transition-all duration-300"
          >
            Next
          </button>
        </motion.div>
      )}
    </div>
  );
};

export default DetailedView;
