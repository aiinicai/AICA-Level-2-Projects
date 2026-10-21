import React, { useState, useMemo } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Maximize2,
  Minimize2,
  Download,
  Filter,
  FileSpreadsheet,
  FileText,
  Printer,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertTriangle,
  Eye,
  CheckCircle2,
  Clock,
  XCircle,
  HelpCircle,
} from 'lucide-react';
import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { TransactionStatus } from '../core/types';

export interface ColumnDef<T> {
  key: string;
  header: string;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render?: (item: T) => React.ReactNode;
  sortable?: boolean;
  exportValue?: (item: T) => string | number;
}

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  keyField: keyof T;
  title?: string;
  onRowClick?: (item: T) => void;
  selectedId?: string;
  onNewClick?: () => void;
  newButtonLabel?: string;
  onViewAccounting?: (item: T) => void;
  filterPlaceholder?: string;
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  keyField,
  title,
  onRowClick,
  selectedId,
  onNewClick,
  newButtonLabel = 'Create',
  onViewAccounting,
  filterPlaceholder = 'Filter records...',
  emptyMessage = 'No matching records found',
}: DataTableProps<T>) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [isDetached, setIsDetached] = useState(false);
  const [isWrap, setIsWrap] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(columns.map((c) => c.key));
  const [showColMenu, setShowColMenu] = useState(false);
  const [showActionsMenu, setShowActionsMenu] = useState(false);

  // Filter
  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return data;
    const q = searchQuery.toLowerCase();
    return data.filter((row) =>
      columns.some((col) => {
        const val = row[col.key];
        if (val === undefined || val === null) return false;
        return String(val).toLowerCase().includes(q);
      })
    );
  }, [data, searchQuery, columns]);

  // Sort
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];
      if (valA === valB) return 0;
      if (valA === undefined || valA === null) return 1;
      if (valB === undefined || valB === null) return -1;
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
      return sortOrder === 'asc' ? 1 : -1;
    });
  }, [filteredData, sortKey, sortOrder]);

  // Paginate
  const totalPages = Math.max(1, Math.ceil(sortedData.length / pageSize));
  const pagedData = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, page, pageSize]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortOrder === 'asc') setSortOrder('desc');
      else {
        setSortKey(null);
        setSortOrder('asc');
      }
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  // Export to Excel
  const handleExportExcel = () => {
    const exportRows = sortedData.map((row) => {
      const obj: Record<string, any> = {};
      columns.forEach((col) => {
        if (visibleColumns.includes(col.key)) {
          obj[col.header] = col.exportValue ? col.exportValue(row) : row[col.key];
        }
      });
      return obj;
    });

    const worksheet = XLSX.utils.json_to_sheet(exportRows);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, title || 'Data');
    XLSX.writeFile(workbook, `${title || 'Export'}_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  // Export to CSV
  const handleExportCSV = () => {
    const exportRows = sortedData.map((row) => {
      const obj: Record<string, any> = {};
      columns.forEach((col) => {
        if (visibleColumns.includes(col.key)) {
          obj[col.header] = col.exportValue ? col.exportValue(row) : row[col.key];
        }
      });
      return obj;
    });

    const worksheet = XLSX.utils.json_to_sheet(exportRows);
    const csv = XLSX.utils.sheet_to_csv(worksheet);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${title || 'Export'}_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
  };

  // Export to PDF
  const handleExportPDF = () => {
    const doc = new jsPDF({ orientation: 'landscape' });
    doc.setFontSize(14);
    doc.setTextColor(91, 44, 131); // Plum
    doc.text(title || 'MediCore Connect Report', 14, 15);
    doc.setFontSize(9);
    doc.setTextColor(100);
    doc.text(`Generated on 19/Oct/2026 | Total Records: ${sortedData.length}`, 14, 22);

    const activeCols = columns.filter((c) => visibleColumns.includes(c.key));
    const headers = [activeCols.map((c) => c.header)];
    const rows = sortedData.map((r) =>
      activeCols.map((c) => (c.exportValue ? String(c.exportValue(r)) : String(r[c.key] ?? '')))
    );

    autoTable(doc, {
      head: headers,
      body: rows,
      startY: 26,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [91, 44, 131], textColor: [255, 255, 255] },
      alternateRowStyles: { fillColor: [248, 245, 250] },
    });

    doc.save(`${title || 'Export'}_${new Date().toISOString().slice(0, 10)}.pdf`);
  };

  const renderStatusBadge = (status: TransactionStatus) => {
    let bg = 'bg-gray-100 text-gray-800 border-gray-300';
    let icon = <Clock className="w-3 h-3 mr-1 inline" />;

    if (status === 'Posted' || status === 'Approved') {
      bg = 'bg-emerald-50 text-emerald-800 border-emerald-300';
      icon = <CheckCircle2 className="w-3 h-3 mr-1 inline text-emerald-600" />;
    } else if (status === 'Pending Approval' || status === 'Pending Higher Approval') {
      bg = 'bg-amber-50 text-amber-800 border-amber-300';
      icon = <Clock className="w-3 h-3 mr-1 inline text-amber-600" />;
    } else if (status === 'Draft') {
      bg = 'bg-gray-50 text-gray-700 border-gray-300';
      icon = <Clock className="w-3 h-3 mr-1 inline text-gray-500" />;
    } else if (status === 'Rejected') {
      bg = 'bg-rose-50 text-rose-800 border-rose-300';
      icon = <XCircle className="w-3 h-3 mr-1 inline text-rose-600" />;
    } else if (status === 'Approved - Accounting Error') {
      bg = 'bg-rose-100 text-rose-900 border-rose-400';
      icon = <AlertTriangle className="w-3 h-3 mr-1 inline text-rose-600" />;
    }

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${bg}`}>
        {icon}
        {status}
      </span>
    );
  };

  const tableBody = (
    <div className="overflow-x-auto border border-gray-200 rounded-b-md bg-white">
      <table className="w-full text-left text-xs border-collapse">
        <thead className="bg-[#EDE4F5] text-[#3F1D5C] font-semibold uppercase tracking-wider sticky top-0 z-10 border-b border-plum-200">
          <tr>
            {columns
              .filter((col) => visibleColumns.includes(col.key))
              .map((col) => {
                const isSorted = sortKey === col.key;
                const alignClass =
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left';
                return (
                  <th
                    key={col.key}
                    onClick={() => col.sortable !== false && handleSort(col.key)}
                    style={{ width: col.width }}
                    className={`py-2.5 px-3 select-none cursor-pointer hover:bg-plum-200/80 transition-colors ${alignClass}`}
                  >
                    <div
                      className={`flex items-center space-x-1 ${
                        col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : 'justify-start'
                      }`}
                    >
                      <span>{col.header}</span>
                      {col.sortable !== false && (
                        <span>
                          {isSorted ? (
                            sortOrder === 'asc' ? (
                              <ArrowUp className="w-3.5 h-3.5 text-[#5B2C83]" />
                            ) : (
                              <ArrowDown className="w-3.5 h-3.5 text-[#5B2C83]" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 text-plum-400 opacity-60 hover:opacity-100" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            {onViewAccounting && (
              <th className="py-2.5 px-3 text-center w-24">Accounting</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {pagedData.length === 0 ? (
            <tr>
              <td
                colSpan={columns.filter((c) => visibleColumns.includes(c.key)).length + (onViewAccounting ? 1 : 0)}
                className="py-12 text-center text-gray-400 text-sm italic"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            pagedData.map((row, rowIdx) => {
              const isSelected = selectedId && String(row[keyField]) === selectedId;
              const hasHoldOrException = row.holds?.length > 0 || row.status === 'Exception' || row.status === 'Approved - Accounting Error';

              return (
                <tr
                  key={String(row[keyField]) || rowIdx}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={`transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-plum-100/70 border-l-4 border-l-[#5B2C83]'
                      : rowIdx % 2 === 0
                      ? 'bg-white hover:bg-plum-50/50'
                      : 'bg-gray-50/60 hover:bg-plum-50/50'
                  }`}
                >
                  {columns
                    .filter((col) => visibleColumns.includes(col.key))
                    .map((col) => {
                      const alignClass =
                        col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left';
                      const isStatusCol = col.key === 'status';

                      return (
                        <td
                          key={col.key}
                          className={`py-2 px-3 text-gray-700 ${alignClass} ${
                            isWrap ? 'break-words' : 'truncate max-w-xs'
                          }`}
                        >
                          {isStatusCol ? (
                            renderStatusBadge(row[col.key])
                          ) : col.render ? (
                            col.render(row)
                          ) : (
                            <span className="flex items-center space-x-1.5">
                              {col.key === 'number' && hasHoldOrException && (
                                <span title={row.holds?.[0]?.reason || row.exceptionReason || 'Exception required action'}>
                                  <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0 inline" />
                                </span>
                              )}
                              <span>{String(row[col.key] ?? '—')}</span>
                            </span>
                          )}
                        </td>
                      );
                    })}

                  {onViewAccounting && (
                    <td className="py-2 px-3 text-center">
                      {(row.status === 'Posted' || row.status === 'Approved' || row.status === 'Approved - Accounting Error') ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onViewAccounting(row);
                          }}
                          className="px-2 py-0.5 text-[11px] rounded bg-plum-100 text-[#5B2C83] hover:bg-[#5B2C83] hover:text-white font-medium transition-colors border border-plum-300"
                        >
                          View Accounting
                        </button>
                      ) : (
                        <span className="text-gray-400 text-[10px]">—</span>
                      )}
                    </td>
                  )}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div
      className={`flex flex-col select-none ${
        isDetached
          ? 'fixed inset-4 z-50 bg-white rounded-xl shadow-2xl p-6 border border-gray-300 overflow-hidden'
          : 'w-full'
      }`}
    >
      {/* Detached Modal Backdrop */}
      {isDetached && (
        <div
          className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs -z-10"
          onClick={() => setIsDetached(false)}
        />
      )}

      {/* Toolbar */}
      <div className="bg-gray-100 border border-gray-200 rounded-t-md p-2 flex flex-wrap items-center justify-between gap-2">
        {/* Left Toolbar controls */}
        <div className="flex items-center space-x-2">
          {onNewClick && (
            <button
              onClick={onNewClick}
              className="bg-[#5B2C83] hover:bg-[#3F1D5C] text-white px-3 py-1.5 rounded text-xs font-semibold shadow-xs flex items-center space-x-1 transition-colors"
            >
              <span>+ {newButtonLabel}</span>
            </button>
          )}

          {/* Actions Menu */}
          <div className="relative">
            <button
              onClick={() => {
                setShowActionsMenu(!showActionsMenu);
                setShowColMenu(false);
              }}
              className="bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 px-2.5 py-1.5 rounded text-xs font-medium flex items-center space-x-1"
            >
              <span>Actions</span>
            </button>
            {showActionsMenu && (
              <div className="absolute left-0 mt-1 w-44 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-30 text-xs">
                {onNewClick && (
                  <button
                    onClick={() => { onNewClick(); setShowActionsMenu(false); }}
                    className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 font-medium"
                  >
                    + {newButtonLabel}
                  </button>
                )}
                <button
                  onClick={() => { handleExportExcel(); setShowActionsMenu(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 flex items-center space-x-2"
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Export to Excel (.xlsx)</span>
                </button>
                <button
                  onClick={() => { handleExportCSV(); setShowActionsMenu(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 flex items-center space-x-2"
                >
                  <FileText className="w-3.5 h-3.5 text-gray-600" />
                  <span>Export to CSV</span>
                </button>
                <button
                  onClick={() => { handleExportPDF(); setShowActionsMenu(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 flex items-center space-x-2"
                >
                  <Download className="w-3.5 h-3.5 text-rose-600" />
                  <span>Download PDF Report</span>
                </button>
                <button
                  onClick={() => { window.print(); setShowActionsMenu(false); }}
                  className="w-full text-left px-3 py-1.5 hover:bg-plum-50 text-gray-700 flex items-center space-x-2"
                >
                  <Printer className="w-3.5 h-3.5 text-gray-600" />
                  <span>Print View</span>
                </button>
              </div>
            )}
          </div>

          {/* View Menu */}
          <div className="relative">
            <button
              onClick={() => {
                setShowColMenu(!showColMenu);
                setShowActionsMenu(false);
              }}
              className="bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 px-2.5 py-1.5 rounded text-xs font-medium flex items-center space-x-1"
            >
              <span>View</span>
            </button>
            {showColMenu && (
              <div className="absolute left-0 mt-1 w-52 bg-white rounded-md shadow-lg border border-gray-200 p-2 z-30 text-xs">
                <div className="font-semibold text-gray-500 uppercase text-[10px] mb-1.5">
                  Columns Display
                </div>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {columns.map((c) => (
                    <label
                      key={c.key}
                      className="flex items-center space-x-2 px-1 py-0.5 hover:bg-gray-50 rounded cursor-pointer text-gray-700"
                    >
                      <input
                        type="checkbox"
                        checked={visibleColumns.includes(c.key)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setVisibleColumns([...visibleColumns, c.key]);
                          } else {
                            if (visibleColumns.length > 2) {
                              setVisibleColumns(visibleColumns.filter((k) => k !== c.key));
                            }
                          }
                        }}
                        className="rounded text-[#5B2C83] focus:ring-[#5B2C83]"
                      />
                      <span>{c.header}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Wrap Toggle */}
          <button
            onClick={() => setIsWrap(!isWrap)}
            title="Toggle Text Wrap"
            className={`px-2 py-1.5 rounded border text-xs font-medium ${
              isWrap ? 'bg-[#5B2C83] text-white border-[#5B2C83]' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            Wrap
          </button>

          {/* Detach */}
          <button
            onClick={() => setIsDetached(!isDetached)}
            title={isDetached ? 'Attach View' : 'Detach View into Full Dialog'}
            className="px-2 py-1.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 rounded text-xs font-medium flex items-center space-x-1"
          >
            {isDetached ? (
              <>
                <Minimize2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Attach</span>
              </>
            ) : (
              <>
                <Maximize2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Detach</span>
              </>
            )}
          </button>
        </div>

        {/* Right Toolbar: Search & Export quick buttons */}
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder={filterPlaceholder}
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="pl-8 pr-3 py-1 bg-white border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-[#5B2C83] focus:border-[#5B2C83] w-48 sm:w-64"
            />
          </div>

          <button
            onClick={handleExportExcel}
            title="Download Excel Spreadsheet (.xlsx)"
            className="p-1.5 bg-white hover:bg-gray-50 border border-gray-300 rounded text-emerald-700"
          >
            <FileSpreadsheet className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportPDF}
            title="Export PDF Document"
            className="p-1.5 bg-white hover:bg-gray-50 border border-gray-300 rounded text-rose-700"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Table Body */}
      {tableBody}

      {/* Pagination Footer */}
      <div className="bg-gray-100 border-x border-b border-gray-200 rounded-b-md px-3 py-2 flex items-center justify-between text-xs text-gray-600">
        <div>
          Showing{' '}
          <strong className="text-gray-900">
            {sortedData.length > 0 ? (page - 1) * pageSize + 1 : 0}
          </strong>{' '}
          to{' '}
          <strong className="text-gray-900">
            {Math.min(page * pageSize, sortedData.length)}
          </strong>{' '}
          of <strong className="text-gray-900">{sortedData.length}</strong> records
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
            className="bg-white border border-gray-300 rounded px-2 py-0.5 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-[#5B2C83]"
          >
            <option value={10}>10 per page</option>
            <option value={15}>15 per page</option>
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
          </select>

          <div className="flex items-center space-x-1">
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1}
              className="p-1 rounded bg-white border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              <ChevronsLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded bg-white border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="px-2">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded bg-white border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages}
              className="p-1 rounded bg-white border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
            >
              <ChevronsRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
