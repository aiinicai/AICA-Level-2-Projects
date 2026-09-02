/**
 * Utility functions for Indian NGO Grant Management (GrantSetu)
 */

// Format numbers in Indian Standard Currency Notation (₹ Lakhs & Crores)
export const formatINR = (amount) => {
  if (amount === undefined || amount === null || isNaN(amount)) return '₹ 0';
  const val = Number(amount);
  const isNegative = val < 0;
  const absVal = Math.abs(val);
  
  // Convert to Indian number string format
  const parts = absVal.toFixed(0).toString().split('.');
  let lastThree = parts[0].substring(parts[0].length - 3);
  const otherNumbers = parts[0].substring(0, parts[0].length - 3);
  if (otherNumbers !== '') {
    lastThree = ',' + lastThree;
  }
  const formatted = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + lastThree;
  
  return `${isNegative ? '-' : ''}₹ ${formatted}`;
};

// Format concise Indian currency shorthand (e.g. ₹ 45.00 Lakhs, ₹ 1.20 Cr)
export const formatINRShorthand = (amount) => {
  if (!amount || isNaN(amount)) return '₹ 0';
  const num = Number(amount);
  if (num >= 10000000) {
    return `₹ ${(num / 10000000).toFixed(2)} Cr`;
  }
  if (num >= 100000) {
    return `₹ ${(num / 100000).toFixed(2)} Lakhs`;
  }
  return formatINR(num);
};

// Format Date string (e.g. 15 Aug 2025)
export const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return dateStr;
  }
};

// Get Days remaining from today to target date
export const getDaysRemaining = (targetDateStr) => {
  if (!targetDateStr) return null;
  const target = new Date(targetDateStr);
  const today = new Date();
  const diffTime = target - today;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
};

// Check if certificate/grant is expiring soon (within 90 days)
export const isExpiringSoon = (targetDateStr, thresholdDays = 90) => {
  const days = getDaysRemaining(targetDateStr);
  return days !== null && days >= 0 && days <= thresholdDays;
};

// Calculate financial year string (e.g. "FY 2025-26" for Indian April-March FY)
export const getIndianFinancialYear = (dateStr = new Date()) => {
  const d = new Date(dateStr);
  const month = d.getMonth() + 1; // 1-12
  const year = d.getFullYear();
  if (month >= 4) {
    return `FY ${year}-${(year + 1).toString().slice(2)}`;
  } else {
    return `FY ${year - 1}-${year.toString().slice(2)}`;
  }
};
