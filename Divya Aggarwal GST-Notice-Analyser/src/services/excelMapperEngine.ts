import * as XLSX from 'xlsx';
import { saveAs } from 'file-saver';
import { DocumentItem, DocumentMapping, DocumentStatus } from '../types';

export interface ColumnDetectionResult {
  headers: string[];
  docNameIndex: number;
  categoryIndex: number;
  statusIndex: number;
  dueDateIndex: number;
  remarksIndex: number;
  periodIndex: number;
  previewRows: string[][];
}

export function detectHeadersFromWorkbook(data: ArrayBuffer): ColumnDetectionResult {
  const workbook = XLSX.read(data, { type: 'array' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const rawRows: any[][] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

  if (rawRows.length === 0) {
    return {
      headers: [],
      docNameIndex: -1,
      categoryIndex: -1,
      statusIndex: -1,
      dueDateIndex: -1,
      remarksIndex: -1,
      periodIndex: -1,
      previewRows: [],
    };
  }

  let headerRowIndex = 0;
  for (let i = 0; i < Math.min(5, rawRows.length); i++) {
    const stringCount = rawRows[i].filter((c) => typeof c === 'string' && c.trim().length > 1).length;
    if (stringCount >= 2) {
      headerRowIndex = i;
      break;
    }
  }

  const headers = rawRows[headerRowIndex].map((h) => String(h || '').trim());
  const previewRows = rawRows
    .slice(headerRowIndex + 1, headerRowIndex + 6)
    .map((row) => row.map((cell) => String(cell ?? '').trim()));

  let docNameIndex = -1;
  let categoryIndex = -1;
  let statusIndex = -1;
  let dueDateIndex = -1;
  let remarksIndex = -1;
  let periodIndex = -1;

  headers.forEach((h, idx) => {
    const lower = h.toLowerCase();
    if (lower.includes('doc') || lower.includes('item') || lower.includes('requirement') || lower.includes('particular') || lower.includes('name')) {
      if (docNameIndex === -1) docNameIndex = idx;
    } else if (lower.includes('cat') || lower.includes('type') || lower.includes('head') || lower.includes('group')) {
      if (categoryIndex === -1) categoryIndex = idx;
    } else if (lower.includes('status') || lower.includes('stage') || lower.includes('state') || lower.includes('progress')) {
      if (statusIndex === -1) statusIndex = idx;
    } else if (lower.includes('due') || lower.includes('target') || lower.includes('date') || lower.includes('deadline')) {
      if (dueDateIndex === -1) dueDateIndex = idx;
    } else if (lower.includes('remark') || lower.includes('note') || lower.includes('comment') || lower.includes('action')) {
      if (remarksIndex === -1) remarksIndex = idx;
    } else if (lower.includes('period') || lower.includes('fy') || lower.includes('year') || lower.includes('month')) {
      if (periodIndex === -1) periodIndex = idx;
    }
  });

  if (docNameIndex === -1 && headers.length > 0) docNameIndex = 0;
  if (statusIndex === -1 && headers.length > 1) statusIndex = 1;
  if (dueDateIndex === -1 && headers.length > 2) dueDateIndex = 2;
  if (remarksIndex === -1 && headers.length > 3) remarksIndex = 3;

  return {
    headers,
    docNameIndex,
    categoryIndex,
    statusIndex,
    dueDateIndex,
    remarksIndex,
    periodIndex,
    previewRows,
  };
}

export function parseRowsWithMapping(
  caseId: string,
  workbookData: ArrayBuffer,
  mapping: DocumentMapping,
  defaultPeriod = 'FY 2022-23'
): DocumentItem[] {
  const workbook = XLSX.read(workbookData, { type: 'array' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const rawRows: any[][] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

  if (rawRows.length <= 1) return [];

  const headerRow = rawRows[0].map((h) => String(h || '').trim());
  const docIdx = headerRow.indexOf(mapping.docNameCol);
  const catIdx = headerRow.indexOf(mapping.categoryCol);
  const statIdx = headerRow.indexOf(mapping.statusCol);
  const dueIdx = headerRow.indexOf(mapping.dueDateCol);
  const remIdx = headerRow.indexOf(mapping.remarksCol);
  const perIdx = headerRow.indexOf(mapping.periodCol);

  const items: DocumentItem[] = [];

  for (let r = 1; r < rawRows.length; r++) {
    const row = rawRows[r];
    if (!row || row.length === 0) continue;

    const docName = String(row[docIdx] ?? row[0] ?? '').trim();
    if (!docName) continue;

    const category = catIdx >= 0 && row[catIdx] ? String(row[catIdx]).trim() : 'Client Data';
    const statusRaw = statIdx >= 0 && row[statIdx] ? String(row[statIdx]).trim() : 'Pending';
    const dueDate = dueIdx >= 0 && row[dueIdx] ? String(row[dueIdx]).trim() : '';
    const remarks = remIdx >= 0 && row[remIdx] ? String(row[remIdx]).trim() : '';
    const period = perIdx >= 0 && row[perIdx] ? String(row[perIdx]).trim() : defaultPeriod;

    let normalizedStatus: DocumentStatus = 'Pending';
    const lowerStat = statusRaw.toLowerCase();
    if (lowerStat.includes('received') || lowerStat.includes('done') || lowerStat.includes('complete')) {
      normalizedStatus = 'Received';
    } else if (lowerStat.includes('part')) {
      normalizedStatus = 'Partly Received';
    } else if (lowerStat.includes('clarif') || lowerStat.includes('query')) {
      normalizedStatus = 'Clarification Required';
    }

    items.push({
      id: 'doc_' + Date.now() + '_' + Math.random().toString(36).substring(2, 6),
      caseId,
      docName,
      category,
      status: normalizedStatus,
      requestedDate: new Date().toISOString().split('T')[0],
      dueDate: dueDate || '—',
      receivedDate: normalizedStatus === 'Received' ? new Date().toISOString().split('T')[0] : undefined,
      remarks,
      period,
    });
  }

  return items;
}

export function exportDocumentTrackerToExcel(
  clientName: string,
  gstin: string,
  noticeNumber: string,
  items: DocumentItem[]
): void {
  const wb = XLSX.utils.book_new();

  const headerRows = [
    ['CA FIRM DOCUMENT & CLIENT DATA TRACKER', '', '', '', '', ''],
    ['Client / Taxpayer:', clientName, '', 'GSTIN:', gstin, ''],
    ['Notice No:', noticeNumber, '', 'Export Date:', new Date().toLocaleDateString('en-IN'), ''],
    [],
    ['Sr No', 'Document / Information Required', 'Category', 'Period / FY', 'Current Status', 'Requested Date', 'Target Due Date', 'Received Date', 'CA Follow-up Remarks'],
  ];

  const dataRows = items.map((item, idx) => [
    idx + 1,
    item.docName,
    item.category,
    item.period || '-',
    item.status,
    item.requestedDate,
    item.dueDate,
    item.receivedDate || '-',
    item.remarks || '',
  ]);

  const ws = XLSX.utils.aoa_to_sheet([...headerRows, ...dataRows]);

  ws['!cols'] = [
    { wch: 6 },
    { wch: 40 },
    { wch: 18 },
    { wch: 14 },
    { wch: 16 },
    { wch: 14 },
    { wch: 14 },
    { wch: 14 },
    { wch: 45 },
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Document Tracker');

  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const blob = new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  saveAs(blob, 'GST_Document_Tracker_' + gstin + '.xlsx');
}
