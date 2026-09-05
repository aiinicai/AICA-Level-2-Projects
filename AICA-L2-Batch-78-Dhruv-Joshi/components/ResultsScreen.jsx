import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, AlertTriangle, XCircle, Download, RotateCcw, ChevronRight } from 'lucide-react';
import ResultCard from './ResultCard';
import DetailedView from './DetailedView';

const ResultsScreen = ({ results, onStartOver }) => {
  const gstr2Type = '2B';
  const [selectedCategory, setSelectedCategory] = useState(null);

  if (!results) {
    return <div>No results available</div>;
  }

  const { matched, missingInGstr2, missingInGstr1, mismatched, zeroTaxBills = [], summary } = results;

  // Flatten matched invoices to merge GSTR-1 and GSTR-2 values for display/export
  const matchedFlat = matched.map(({ gstr1, gstr2 }) => ({ ...gstr1, ...gstr2 }));
  const zeroTaxFlat = zeroTaxBills.map(inv => ({ ...inv }));

  const categories = [
    {
      id: 'zeroTaxBills',
      title: 'Zero Tax Bills',
      count: zeroTaxFlat.length,
      icon: CheckCircle,
      color: 'accent-yellow',
      description: 'Invoices where Invoice Value equals Taxable Value (no tax charged)',
      data: zeroTaxFlat
    },
    {
      id: 'matched',
      title: 'Matched Invoices',
      count: matchedFlat.length,
      icon: CheckCircle,
      color: 'accent-green',
      description: 'Invoices found in both files with identical details',
      data: matchedFlat
    },
    {
      id: 'missingInGstr2',
      title: `Missing in Government Provided GSTR-${gstr2Type}`,
      count: missingInGstr2.length,
      icon: AlertTriangle,
      color: 'accent-blue',
      description: `Invoices in Your GSTR-2B but not found in Government Provided GSTR-${gstr2Type}`,
      data: missingInGstr2
    },
    {
      id: 'missingInGstr1',
      title: 'Missing in Your GSTR-2B',
      count: missingInGstr1.length,
      icon: AlertTriangle,
      color: 'accent-purple',
      description: `Invoices in Government Provided GSTR-${gstr2Type} but not in Your GSTR-2B`,
      data: missingInGstr1
    },
    {
      id: 'mismatched',
      title: 'Mismatched Invoices',
      count: mismatched.length,
      icon: XCircle,
      color: 'red-400',
      description: 'Invoices with same number but different values',
      data: mismatched
    }
  ];

  const exportResults = () => {
    const csvContent = generateCSVReport(results);
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `GSTMitra-gst-reconciliation-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const generateCSVReport = (results) => {
    let csv = 'Category,Invoice Date,Invoice Value,GSTIN,Taxable Value,Status,Differences\n';
    
    // Add zero tax bills
    zeroTaxFlat.forEach(invoice => {
      csv += `Zero Tax Bill,"${invoice.invoiceDate}","${invoice.invoiceValue}","${invoice.gstin}","${invoice.taxableValue}",Zero Tax,Invoice Value equals Taxable Value\n`;
    });
    // Add matched invoices
    matchedFlat.forEach(invoice => {
      csv += `Matched,"${invoice.invoiceDate}","${invoice.invoiceValue}","${invoice.gstin}","${invoice.taxableValue}",Perfect Match,None\n`;
    });
    
    // Add missing invoices
    results.missingInGstr2.forEach(invoice => {
      csv += `Missing in Government Provided GSTR-${gstr2Type},"${invoice.invoiceDate}","${invoice.invoiceValue}","${invoice.gstin}","${invoice.taxableValue}",Not Found,Missing from government records\n`;
    });
    
    results.missingInGstr1.forEach(invoice => {
      csv += `Missing in Your GSTR-2B,"${invoice.invoiceDate}","${invoice.invoiceValue}","${invoice.gstin}","${invoice.taxableValue}",Not Found,Not in your records\n`;
    });
    
    // Add mismatched invoices
    results.mismatched.forEach(invoice => {
      const differences = Array.isArray(invoice.differences)
  ? invoice.differences.join('; ')
  : invoice.differences && typeof invoice.differences === 'object'
    ? Object.values(invoice.differences).join('; ')
    : 'Value mismatch';
      csv += `Mismatched,"${invoice.invoiceDate}","${invoice.invoiceValue}","${invoice.gstin}","${invoice.taxableValue}",Discrepancy,"${differences}"\n`;
    });
    
    return csv;
  };


  if (selectedCategory) {
    return (
      <DetailedView
        category={selectedCategory}
        data={categories.find(c => c.id === selectedCategory)}
        gstr2Type={gstr2Type}
        onBack={() => setSelectedCategory(null)}
        onStartOver={onStartOver}
      />
    );
  }

  return (
    <div className="min-h-screen px-4 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <h1 className="text-3xl md:text-4xl font-bold mb-4 text-text-primary">
          Reconciliation Complete
        </h1>
        <p className="text-text-secondary text-lg">
          Analysis of {summary.totalInvoices} invoices completed
        </p>
      </motion.div>

      {/* Summary Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="max-w-5xl mx-auto grid grid-rows-3 grid-cols-2 gap-8 py-12"
        style={{gridTemplateRows: 'repeat(3, minmax(0, 1fr))', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))'}}
      >
        {categories.map((category, index) => (
          <motion.div
            key={category.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 * index }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex"
          >
            <ResultCard
              {...category}
              onClick={() => setSelectedCategory(category.id)}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Quick Stats */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="max-w-4xl mx-auto neumorphic-card p-8 mb-12"
      >
        <h3 className="text-xl font-semibold text-text-primary mb-6 text-center">
          Quick Summary
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
          <div>
            <div className="text-2xl font-bold text-accent-green mb-2">
              {((matchedFlat.length / summary.totalInvoices) * 100).toFixed(1)}%
            </div>
            <div className="text-text-secondary">Match Rate</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-accent-blue mb-2">
              ₹{summary.totalValue?.toLocaleString() || '0'}
            </div>
            <div className="text-text-secondary">Total Value</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-400 mb-2">
              {mismatched.length + missingInGstr1.length + missingInGstr2.length}
            </div>
            <div className="text-text-secondary">Issues Found</div>
          </div>
        </div>
      </motion.div>

      {/* Zero Tax Bills Section */}
      {zeroTaxFlat.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="max-w-4xl mx-auto neumorphic-card p-8 mb-12 border-l-8 border-yellow-400"
        >
          <h3 className="text-xl font-semibold text-yellow-500 mb-2 flex items-center gap-2">
            <CheckCircle className="text-yellow-400" size={22} />
            Zero Tax Bills
          </h3>
          <div className="text-text-secondary mb-4">
            {zeroTaxFlat.length} invoice{zeroTaxFlat.length > 1 ? 's' : ''} where Invoice Value equals Taxable Value (no tax charged).<br/>
            These are shown separately for your reference and excluded from other categories.
          </div>
          <div className="overflow-x-auto">
            <table className="w-full mb-4">
              <thead>
                <tr className="bg-dark-border">
                  <th className="px-3 py-2 text-xs font-medium text-text-secondary uppercase">Invoice Number</th>
                  <th className="px-3 py-2 text-xs font-medium text-text-secondary uppercase">Date</th>
                  <th className="px-3 py-2 text-xs font-medium text-text-secondary uppercase">Invoice Value</th>
                  <th className="px-3 py-2 text-xs font-medium text-text-secondary uppercase">GSTIN</th>
                  <th className="px-3 py-2 text-xs font-medium text-text-secondary uppercase">Taxable Value</th>
                </tr>
              </thead>
              <tbody>
                {zeroTaxFlat.slice(0, 5).map((inv, i) => (
                  <tr key={i} className="border-b border-dark-border">
                    <td className="px-3 py-2">{inv.invoiceNumber}</td>
                    <td className="px-3 py-2">{inv.invoiceDate}</td>
                    <td className="px-3 py-2">₹{inv.invoiceValue}</td>
                    <td className="px-3 py-2">{inv.gstin}</td>
                    <td className="px-3 py-2">₹{inv.taxableValue}</td>
                  </tr>
                ))}
                {zeroTaxFlat.length > 5 && (
                  <tr>
                    <td colSpan={5} className="text-center text-xs text-text-secondary py-2">
                      ...and {zeroTaxFlat.length - 5} more
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <button
            className="mt-2 px-6 py-2 bg-yellow-400 text-dark-bg font-semibold rounded-lg hover:shadow-glow-yellow transition-all duration-300"
            onClick={() => setSelectedCategory('zeroTaxBills')}
          >
            View All Zero Tax Bills
          </button>
        </motion.div>
      )}

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
        className="flex flex-col sm:flex-row gap-4 justify-center items-center"
      >
        <button
          onClick={exportResults}
          className="flex items-center gap-2 bg-gradient-to-r from-accent-green to-accent-blue text-dark-bg font-semibold py-3 px-8 rounded-xl transition-all duration-300 hover:shadow-glow-green hover:scale-105"
        >
          <Download size={20} />
          Export Results
        </button>
        <button
          onClick={onStartOver}
          className="flex items-center gap-2 neumorphic-card text-text-primary font-medium py-3 px-8 rounded-xl transition-all duration-300 hover:shadow-glow-blue"
        >
          <RotateCcw size={20} />
          Start Over
        </button>
      </motion.div>

      {/* Footer */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.8 }}
        className="text-center mt-16 text-text-secondary text-sm"
      >
        <p>Click on any category above to view detailed invoice information</p>
      </motion.div>
    </div>
  );
};

export default ResultsScreen;
