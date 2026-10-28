/**
 * MediCore Connect - Unified Table Filter Hook & Engine
 * Section 4: Consistent, multi-attribute filtering across all modules
 */

import { useState, useMemo, useEffect, useCallback } from 'react';

export interface FilterConfig<T> {
  searchFields?: (keyof T | string)[];
  dateField?: keyof T | string;
  amountField?: keyof T | string;
  statusField?: keyof T | string;
  buField?: keyof T | string;
  counterpartyField?: keyof T | string;
  makerField?: keyof T | string;
  approverField?: keyof T | string;
  customFilterFn?: (item: T, filters: Record<string, any>) => boolean;
}

export interface ActiveFilterChip {
  id: string;
  key: string;
  label: string;
  displayValue: string;
  onRemove: () => void;
}

export function useTableFilters<T extends Record<string, any>>(
  data: T[],
  config: FilterConfig<T> = {}
) {
  // Read initial filters from URL query string if present
  const getInitialUrlState = () => {
    try {
      const hash = window.location.hash || '';
      const queryIdx = hash.indexOf('?');
      if (queryIdx >= 0) {
        const params = new URLSearchParams(hash.slice(queryIdx + 1));
        return {
          search: params.get('q') || '',
          status: params.get('status') || '',
          bu: params.get('bu') || 'All',
          dateFrom: params.get('from') || '',
          dateTo: params.get('to') || '',
          counterparty: params.get('party') || '',
          maker: params.get('maker') || '',
          approver: params.get('approver') || '',
        };
      }
    } catch {
      // fallback
    }
    return {
      search: '',
      status: '',
      bu: 'All',
      dateFrom: '',
      dateTo: '',
      counterparty: '',
      maker: '',
      approver: '',
    };
  };

  const initial = getInitialUrlState();

  const [searchQuery, setSearchQuery] = useState<string>(initial.search);
  const [selectedStatus, setSelectedStatus] = useState<string>(initial.status);
  const [selectedBU, setSelectedBU] = useState<string>(initial.bu);
  const [dateFrom, setDateFrom] = useState<string>(initial.dateFrom);
  const [dateTo, setDateTo] = useState<string>(initial.dateTo);
  const [amountFrom, setAmountFrom] = useState<number | ''>('');
  const [amountTo, setAmountTo] = useState<number | ''>('');
  const [selectedCounterparty, setSelectedCounterparty] = useState<string>(initial.counterparty);
  const [selectedMaker, setSelectedMaker] = useState<string>(initial.maker);
  const [selectedApprover, setSelectedApprover] = useState<string>(initial.approver);
  const [customFilters, setCustomFilters] = useState<Record<string, any>>({});

  // Unique options extracted dynamically from dataset
  const uniqueStatuses = useMemo(() => {
    const field = config.statusField || 'status';
    const set = new Set<string>();
    data.forEach((item) => {
      if (item[field]) set.add(String(item[field]));
    });
    return Array.from(set).sort();
  }, [data, config.statusField]);

  const uniqueBUs = useMemo(() => {
    const field = config.buField || 'businessUnit';
    const set = new Set<string>();
    data.forEach((item) => {
      if (item[field]) set.add(String(item[field]));
    });
    return Array.from(set).sort();
  }, [data, config.buField]);

  const uniqueCounterparties = useMemo(() => {
    const field = config.counterpartyField || 'supplierName' || 'customerName';
    const set = new Set<string>();
    data.forEach((item) => {
      const val = item[field] || item['supplierName'] || item['customerName'] || item['payee'];
      if (val) set.add(String(val));
    });
    return Array.from(set).sort();
  }, [data, config.counterpartyField]);

  const uniqueMakers = useMemo(() => {
    const field = config.makerField || 'createdBy';
    const set = new Set<string>();
    data.forEach((item) => {
      if (item[field]) set.add(String(item[field]));
    });
    return Array.from(set).sort();
  }, [data, config.makerField]);

  const uniqueApprovers = useMemo(() => {
    const field = config.approverField || 'approvedBy';
    const set = new Set<string>();
    data.forEach((item) => {
      if (item[field]) set.add(String(item[field]));
    });
    return Array.from(set).sort();
  }, [data, config.approverField]);

  // Main Filter Evaluation Logic
  const filteredData = useMemo(() => {
    return data.filter((item) => {
      // 1. BU Filter
      if (selectedBU && selectedBU !== 'All') {
        const buVal = String(item[config.buField || 'businessUnit'] || '');
        if (buVal !== selectedBU && !buVal.includes(selectedBU)) return false;
      }

      // 2. Status Filter
      if (selectedStatus && selectedStatus !== 'All') {
        const statusVal = String(item[config.statusField || 'status'] || '');
        if (statusVal.toLowerCase() !== selectedStatus.toLowerCase()) return false;
      }

      // 3. Counterparty Filter
      if (selectedCounterparty && selectedCounterparty !== 'All') {
        const partyVal = String(
          item[config.counterpartyField || 'supplierName'] ||
          item['supplierName'] ||
          item['customerName'] ||
          item['payee'] ||
          ''
        );
        if (partyVal !== selectedCounterparty) return false;
      }

      // 4. Maker Filter
      if (selectedMaker && selectedMaker !== 'All') {
        const makerVal = String(item[config.makerField || 'createdBy'] || '');
        if (makerVal.toLowerCase() !== selectedMaker.toLowerCase()) return false;
      }

      // 5. Approver Filter
      if (selectedApprover && selectedApprover !== 'All') {
        const appVal = String(item[config.approverField || 'approvedBy'] || '');
        if (appVal.toLowerCase() !== selectedApprover.toLowerCase()) return false;
      }

      // 6. Date Range (Day-level ISO comparison)
      if (dateFrom || dateTo) {
        const dateRaw = String(item[config.dateField || 'date'] || item['invoiceDate'] || item['transactionDate'] || item['receiptDate'] || item['journalDate'] || item['createdAt'] || '');
        if (dateRaw) {
          // Normalize to YYYY-MM-DD
          const itemIso = dateRaw.split('T')[0];
          if (dateFrom && itemIso < dateFrom) return false;
          if (dateTo && itemIso > dateTo) return false;
        }
      }

      // 7. Amount Range
      if (amountFrom !== '' || amountTo !== '') {
        const amt = Number(item[config.amountField || 'totalAmount'] ?? item['amount'] ?? 0);
        if (amountFrom !== '' && amt < Number(amountFrom)) return false;
        if (amountTo !== '' && amt > Number(amountTo)) return false;
      }

      // 8. Free-text Search
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const searchFields = config.searchFields || ['number', 'description', 'supplierName', 'customerName', 'payee', 'reference'];
        const matched = searchFields.some((f) => {
          const val = item[f as keyof T];
          return val !== undefined && val !== null && String(val).toLowerCase().includes(q);
        });
        if (!matched) return false;
      }

      // 9. Custom filter callback
      if (config.customFilterFn) {
        if (!config.customFilterFn(item, customFilters)) return false;
      }

      return true;
    });
  }, [
    data,
    config,
    searchQuery,
    selectedStatus,
    selectedBU,
    dateFrom,
    dateTo,
    amountFrom,
    amountTo,
    selectedCounterparty,
    selectedMaker,
    selectedApprover,
    customFilters,
  ]);

  // Active filter chips list
  const activeFilterChips = useMemo(() => {
    const chips: ActiveFilterChip[] = [];

    if (searchQuery) {
      chips.push({
        id: 'search',
        key: 'search',
        label: 'Search',
        displayValue: `"${searchQuery}"`,
        onRemove: () => setSearchQuery(''),
      });
    }

    if (selectedBU && selectedBU !== 'All') {
      chips.push({
        id: 'bu',
        key: 'bu',
        label: 'Business Unit',
        displayValue: selectedBU,
        onRemove: () => setSelectedBU('All'),
      });
    }

    if (selectedStatus && selectedStatus !== 'All') {
      chips.push({
        id: 'status',
        key: 'status',
        label: 'Status',
        displayValue: selectedStatus,
        onRemove: () => setSelectedStatus(''),
      });
    }

    if (selectedCounterparty && selectedCounterparty !== 'All') {
      chips.push({
        id: 'counterparty',
        key: 'counterparty',
        label: 'Party',
        displayValue: selectedCounterparty,
        onRemove: () => setSelectedCounterparty(''),
      });
    }

    if (selectedMaker && selectedMaker !== 'All') {
      chips.push({
        id: 'maker',
        key: 'maker',
        label: 'Maker',
        displayValue: selectedMaker,
        onRemove: () => setSelectedMaker(''),
      });
    }

    if (selectedApprover && selectedApprover !== 'All') {
      chips.push({
        id: 'approver',
        key: 'approver',
        label: 'Approver',
        displayValue: selectedApprover,
        onRemove: () => setSelectedApprover(''),
      });
    }

    if (dateFrom || dateTo) {
      chips.push({
        id: 'date',
        key: 'date',
        label: 'Date Range',
        displayValue: `${dateFrom || 'Start'} → ${dateTo || 'End'}`,
        onRemove: () => {
          setDateFrom('');
          setDateTo('');
        },
      });
    }

    if (amountFrom !== '' || amountTo !== '') {
      chips.push({
        id: 'amount',
        key: 'amount',
        label: 'Amount Range',
        displayValue: `AED ${amountFrom || '0'} – ${amountTo || '∞'}`,
        onRemove: () => {
          setAmountFrom('');
          setAmountTo('');
        },
      });
    }

    return chips;
  }, [
    searchQuery,
    selectedBU,
    selectedStatus,
    selectedCounterparty,
    selectedMaker,
    selectedApprover,
    dateFrom,
    dateTo,
    amountFrom,
    amountTo,
  ]);

  const clearAllFilters = useCallback(() => {
    setSearchQuery('');
    setSelectedStatus('');
    setSelectedBU('All');
    setDateFrom('');
    setDateTo('');
    setAmountFrom('');
    setAmountTo('');
    setSelectedCounterparty('');
    setSelectedMaker('');
    setSelectedApprover('');
    setCustomFilters({});
  }, []);

  return {
    filteredData,
    totalCount: data.length,
    filteredCount: filteredData.length,
    searchQuery,
    setSearchQuery,
    selectedStatus,
    setSelectedStatus,
    selectedBU,
    setSelectedBU,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    amountFrom,
    setAmountFrom,
    amountTo,
    setAmountTo,
    selectedCounterparty,
    setSelectedCounterparty,
    selectedMaker,
    setSelectedMaker,
    selectedApprover,
    setSelectedApprover,
    customFilters,
    setCustomFilters,
    activeFilterChips,
    clearAllFilters,
    uniqueStatuses,
    uniqueBUs,
    uniqueCounterparties,
    uniqueMakers,
    uniqueApprovers,
  };
}
