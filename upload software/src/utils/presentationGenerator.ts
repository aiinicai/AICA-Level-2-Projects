import pptxgen from 'pptxgenjs';
import { EntityDetails, ReconciliationReport } from '../types/accounting';

export const generateProjectPresentation = (
  entity?: EntityDetails,
  reconciliation?: ReconciliationReport
): pptxgen => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';

  const entityName = entity?.name || 'M/s ABC Enterprises';
  const entityType = entity?.entityType || 'Partnership Firm';
  const financialYear = entity?.financialYear || '2024-25';
  const pan = entity?.pan || 'AAAPF1234K';
  const gst = entity?.gstin || '27AAAPF1234K1Z5';

  // Theme Palette
  const C_DARK_BG = '0F172A'; // Slate 900
  const C_NAVY = '1E293B';    // Slate 800
  const C_ACCENT = '2563EB';  // Blue 600
  const C_GOLD = 'D97706';    // Amber 600
  const C_EMERALD = '059669'; // Emerald 600
  const C_LIGHT_BG = 'F8FAFC';// Slate 50
  const C_WHITE = 'FFFFFF';
  const C_MUTED = '64748B';   // Slate 500
  const C_BORDER = 'CBD5E1';  // Slate 300
  const C_TEXT = '1E293B';

  // =========================================================================
  // SLIDE 1: OVERVIEW & CLIENT PROFILE
  // =========================================================================
  const slide1 = pptx.addSlide();
  slide1.background = { color: C_DARK_BG };

  slide1.addText('ICAI STATUTORY COMPLIANCE SUITE', {
    x: 0.8,
    y: 0.6,
    w: 11.5,
    h: 0.3,
    fontSize: 11,
    fontFace: 'Arial',
    color: C_GOLD,
    bold: true,
    charSpacing: 2,
  });

  slide1.addText('Non-Corporate Financial Statements Automation', {
    x: 0.8,
    y: 0.95,
    w: 11.5,
    h: 0.6,
    fontSize: 26,
    fontFace: 'Arial',
    color: C_WHITE,
    bold: true,
  });

  slide1.addText(
    'Converts raw Trial Balance into standard Vertical Balance Sheet, P&L, and Schedules 1–14 in seconds.',
    {
      x: 0.8,
      y: 1.6,
      w: 11.5,
      h: 0.4,
      fontSize: 13,
      fontFace: 'Arial',
      color: '94A3B8',
    }
  );

  slide1.addShape(pptx.ShapeType.line, {
    x: 0.8,
    y: 2.15,
    w: 11.5,
    h: 0,
    line: { color: '334155', width: 1 },
  });

  // Left Card: Entity Profile
  slide1.addShape(pptx.ShapeType.roundRect, {
    x: 0.8,
    y: 2.4,
    w: 5.6,
    h: 4.1,
    fill: { color: C_NAVY },
    line: { color: '334155', width: 1 },
    rectRadius: 0.08,
  });

  slide1.addText('CLIENT PROFILE', {
    x: 1.1,
    y: 2.65,
    w: 5.0,
    h: 0.3,
    fontSize: 12,
    fontFace: 'Arial',
    color: C_GOLD,
    bold: true,
  });

  slide1.addText(
    `• Entity Name:   ${entityName}\n• Constitution:  ${entityType}\n• Financial Year: FY ${financialYear}\n• PAN:           ${pan}\n• GSTIN:         ${gst}\n• Framework:     ICAI Technical Guide`,
    {
      x: 1.1,
      y: 3.1,
      w: 5.0,
      h: 3.1,
      fontSize: 12,
      fontFace: 'Courier New',
      color: 'F1F5F9',
      lineSpacing: 22,
    }
  );

  // Right Card: Key Highlights
  slide1.addShape(pptx.ShapeType.roundRect, {
    x: 6.7,
    y: 2.4,
    w: 5.6,
    h: 4.1,
    fill: { color: C_NAVY },
    line: { color: '334155', width: 1 },
    rectRadius: 0.08,
  });

  slide1.addText('KEY HIGHLIGHTS', {
    x: 7.0,
    y: 2.65,
    w: 5.0,
    h: 0.3,
    fontSize: 12,
    fontFace: 'Arial',
    color: C_EMERALD,
    bold: true,
  });

  slide1.addText(
    '• Turnkey Speed: From raw TB to final accounts in <2 mins.\n• Universal ERP: Tally, Busy, SAP, Marg & Zoho (Excel/CSV).\n• Smart Ingestion: Auto-cleans headers, footers & totals.\n• ICAI Standard: Vertical Balance Sheet & Schedules 1–14.\n• Multi-Format Export: Linked Excel (.xlsx) & Print PDF.\n• Safe & Fast: In-browser processing with zero data loss.',
    {
      x: 7.0,
      y: 3.1,
      w: 5.0,
      h: 3.1,
      fontSize: 12,
      fontFace: 'Arial',
      color: 'CBD5E1',
      lineSpacing: 22,
    }
  );

  slide1.addText('Chartered Accountant Practice Tool  |  Non-Corporate Format (Proprietorship / Firm / LLP / Trust)', {
    x: 0.8,
    y: 6.8,
    w: 11.5,
    h: 0.3,
    fontSize: 10,
    fontFace: 'Arial',
    color: C_MUTED,
  });

  // =========================================================================
  // SLIDE 2: 7-STEP PROCESS FLOW
  // =========================================================================
  const slide2 = pptx.addSlide();
  slide2.background = { color: C_LIGHT_BG };

  slide2.addText('WORKFLOW IN 7 SIMPLE STEPS', {
    x: 0.8,
    y: 0.5,
    w: 10,
    h: 0.25,
    fontSize: 11,
    fontFace: 'Arial',
    color: C_ACCENT,
    bold: true,
  });

  slide2.addText('End-to-End Preparation Pipeline', {
    x: 0.8,
    y: 0.8,
    w: 11.5,
    h: 0.45,
    fontSize: 22,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  const steps = [
    { num: '01', title: 'Control Sheet', note: 'Set entity details, policies & schedule visibility.' },
    { num: '02', title: 'TB Upload', note: 'Drag & drop raw Excel/CSV from any ERP.' },
    { num: '03', title: 'Auto-Map', note: '100+ rules auto-assign ledgers to Sch 1–14.' },
    { num: '04', title: 'Trading & P&L', note: 'Auto Gross Profit, Operating Profit & Tax.' },
    { num: '05', title: 'Schedules 1-14', note: 'Auto Capital Fund & AS-10 Fixed Assets block.' },
    { num: '06', title: 'Balance Sheet', note: 'Vertical format with drill-down to ledgers.' },
    { num: '07', title: 'Audit & Export', note: 'Zero-variance check (₹0.00) + Excel & PDF.' },
    { num: '⚡', title: 'Speed', note: 'Completes in <2 mins with 100% accuracy.' },
  ];

  steps.forEach((st, idx) => {
    const cardX = 0.8 + (idx % 4) * 2.85;
    const cardY = idx < 4 ? 1.5 : 4.0;

    slide2.addShape(pptx.ShapeType.roundRect, {
      x: cardX,
      y: cardY,
      w: 2.7,
      h: 2.1,
      fill: { color: C_WHITE },
      line: { color: C_BORDER, width: 1 },
      rectRadius: 0.06,
    });

    slide2.addShape(pptx.ShapeType.rect, {
      x: cardX + 0.15,
      y: cardY + 0.15,
      w: 0.45,
      h: 0.3,
      fill: { color: idx === 7 ? C_EMERALD : C_NAVY },
    });

    slide2.addText(st.num, {
      x: cardX + 0.15,
      y: cardY + 0.15,
      w: 0.45,
      h: 0.3,
      fontSize: 11,
      fontFace: 'Arial',
      color: C_WHITE,
      bold: true,
      align: 'center',
    });

    slide2.addText(st.title, {
      x: cardX + 0.7,
      y: cardY + 0.15,
      w: 1.85,
      h: 0.3,
      fontSize: 12,
      fontFace: 'Arial',
      color: C_NAVY,
      bold: true,
    });

    slide2.addText(st.note, {
      x: cardX + 0.15,
      y: cardY + 0.6,
      w: 2.4,
      h: 1.35,
      fontSize: 10.5,
      fontFace: 'Arial',
      color: '475569',
      lineSpacing: 14,
    });
  });

  // =========================================================================
  // SLIDE 3: SMART INGESTION & AUTO-MAPPING
  // =========================================================================
  const slide3 = pptx.addSlide();
  slide3.background = { color: C_LIGHT_BG };

  slide3.addText('DATA PROCESSING & RULES', {
    x: 0.8,
    y: 0.5,
    w: 10,
    h: 0.25,
    fontSize: 11,
    fontFace: 'Arial',
    color: C_GOLD,
    bold: true,
  });

  slide3.addText('Smart Ingestion & Auto-Mapping Engine', {
    x: 0.8,
    y: 0.8,
    w: 11.5,
    h: 0.45,
    fontSize: 22,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  // Left Box: Smart Ingestion
  slide3.addShape(pptx.ShapeType.roundRect, {
    x: 0.8,
    y: 1.5,
    w: 5.6,
    h: 4.8,
    fill: { color: C_WHITE },
    line: { color: C_BORDER, width: 1 },
    rectRadius: 0.08,
  });

  slide3.addText('1. Smart Upload & Ingestion', {
    x: 1.1,
    y: 1.8,
    w: 5.0,
    h: 0.35,
    fontSize: 14,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  slide3.addText(
    '• Auto-detects column layout (Ledger, Op, Dr, Cr, Cl).\n• Skips multi-line company letterhead banners.\n• Auto-extracts Client Name, PAN, GSTIN & FY.\n• Removes "Total" & summary rows to prevent double counting.\n• Supports 4-column & 6-column reports from all major ERPs.',
    {
      x: 1.1,
      y: 2.3,
      w: 5.0,
      h: 3.7,
      fontSize: 11.5,
      fontFace: 'Arial',
      color: '334155',
      lineSpacing: 18,
    }
  );

  // Right Box: Auto-Mapping Rules
  slide3.addShape(pptx.ShapeType.roundRect, {
    x: 6.7,
    y: 1.5,
    w: 5.6,
    h: 4.8,
    fill: { color: C_WHITE },
    line: { color: C_BORDER, width: 1 },
    rectRadius: 0.08,
  });

  slide3.addText('2. Intelligent Auto-Mapping', {
    x: 7.0,
    y: 1.8,
    w: 5.0,
    h: 0.35,
    fontSize: 14,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  slide3.addText(
    '• 100+ ICAI keyword mapping rules.\n• Debit in Capital → Auto-routed as Drawings (Sch 1).\n• GST ITC (Dr) & TDS → Loans & Advances (Sch 13).\n• Bank OD (Cr) → Short-Term Borrowings (Sch 4).\n• Search & 1-click reclassification studio.\n• Built-in AI Assistant for ambiguous accounts.',
    {
      x: 7.0,
      y: 2.3,
      w: 5.0,
      h: 3.7,
      fontSize: 11.5,
      fontFace: 'Arial',
      color: '334155',
      lineSpacing: 18,
    }
  );

  // =========================================================================
  // SLIDE 4: STATUTORY COMPUTATIONS (SCH 1 & SCH 8)
  // =========================================================================
  const slide4 = pptx.addSlide();
  slide4.background = { color: C_LIGHT_BG };

  slide4.addText('STATUTORY ENGINES', {
    x: 0.8,
    y: 0.5,
    w: 10,
    h: 0.25,
    fontSize: 11,
    fontFace: 'Arial',
    color: C_EMERALD,
    bold: true,
  });

  slide4.addText('Capital Movement (Sch 1) & Fixed Assets (Sch 8)', {
    x: 0.8,
    y: 0.8,
    w: 11.5,
    h: 0.45,
    fontSize: 22,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  // Card 1: Schedule 1 Capital
  slide4.addShape(pptx.ShapeType.roundRect, {
    x: 0.8,
    y: 1.5,
    w: 5.6,
    h: 4.8,
    fill: { color: C_WHITE },
    line: { color: C_BORDER, width: 1 },
    rectRadius: 0.08,
  });

  slide4.addText('Schedule 1: Capital Fund Engine', {
    x: 1.1,
    y: 1.8,
    w: 5.0,
    h: 0.35,
    fontSize: 14,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  slide4.addText(
    '  Opening Capital Balance\n' +
    '  (+) Fresh Capital Introduced\n' +
    '  (+) Partner Remuneration & Interest\n' +
    '  (+) Net Profit for the Year (from P&L)\n' +
    '  (-) Drawings for the Year\n' +
    '  (-) Personal Taxes & LIC\n' +
    '  ─────────────────────────────────────\n' +
    '  (=) Closing Partner Fund / Net Worth\n\n' +
    '• Auto-splits profit/drawings across multiple partners by PSR.',
    {
      x: 1.1,
      y: 2.3,
      w: 5.0,
      h: 3.7,
      fontSize: 11,
      fontFace: 'Courier New',
      color: '1E293B',
      lineSpacing: 16,
    }
  );

  // Card 2: Schedule 8 AS-10 Fixed Assets
  slide4.addShape(pptx.ShapeType.roundRect, {
    x: 6.7,
    y: 1.5,
    w: 5.6,
    h: 4.8,
    fill: { color: C_WHITE },
    line: { color: C_BORDER, width: 1 },
    rectRadius: 0.08,
  });

  slide4.addText('Schedule 8: AS-10 Fixed Assets Block', {
    x: 7.0,
    y: 1.8,
    w: 5.0,
    h: 0.35,
    fontSize: 14,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  slide4.addText(
    '• Gross Block:\n  Opening + Additions (>180d / <180d) - Sales\n  = Closing Gross Block\n\n• Depreciation Block:\n  Opening + Depreciation for Year - Disposals\n  = Closing Depreciation\n\n• Net Block (Carrying Value):\n  Closing Gross - Closing Depreciation\n  = Net Book Value (Flows to Balance Sheet Assets)',
    {
      x: 7.0,
      y: 2.3,
      w: 5.0,
      h: 3.7,
      fontSize: 11.5,
      fontFace: 'Arial',
      color: '334155',
      lineSpacing: 17,
    }
  );

  // =========================================================================
  // SLIDE 5: AUDIT CHECKS & DELIVERABLES
  // =========================================================================
  const slide5 = pptx.addSlide();
  slide5.background = { color: C_LIGHT_BG };

  slide5.addText('INTEGRITY & EXPORTS', {
    x: 0.8,
    y: 0.5,
    w: 10,
    h: 0.25,
    fontSize: 11,
    fontFace: 'Arial',
    color: C_GOLD,
    bold: true,
  });

  slide5.addText('3-Way Audit Verification & Deliverables', {
    x: 0.8,
    y: 0.8,
    w: 11.5,
    h: 0.45,
    fontSize: 22,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  // Top 3 Cards
  const auditCards = [
    { title: '1. TRIAL BALANCE', note: 'Total Dr = Total Cr. All ledgers accounted for without dropping balances.' },
    { title: '2. P&L LINK', note: 'Gross Profit & Net Surplus link seamlessly to Capital Fund in Sch 1.' },
    { title: '3. BALANCE SHEET', note: 'Total Equity & Liab = Total Assets. Guaranteed zero difference (₹0.00).' },
  ];

  auditCards.forEach((cd, idx) => {
    const cardX = 0.8 + idx * 3.9;
    slide5.addShape(pptx.ShapeType.roundRect, {
      x: cardX,
      y: 1.5,
      w: 3.6,
      h: 1.6,
      fill: { color: C_WHITE },
      line: { color: C_BORDER, width: 1 },
      rectRadius: 0.06,
    });

    slide5.addText(cd.title, {
      x: cardX + 0.2,
      y: 1.7,
      w: 3.2,
      h: 0.25,
      fontSize: 11,
      fontFace: 'Arial',
      color: idx === 2 ? C_EMERALD : C_NAVY,
      bold: true,
    });

    slide5.addText(cd.note, {
      x: cardX + 0.2,
      y: 2.0,
      w: 3.2,
      h: 0.9,
      fontSize: 10.5,
      fontFace: 'Arial',
      color: '475569',
      lineSpacing: 14,
    });
  });

  // Bottom-Left Box: Deliverables
  slide5.addShape(pptx.ShapeType.roundRect, {
    x: 0.8,
    y: 3.3,
    w: 5.6,
    h: 3.0,
    fill: { color: C_WHITE },
    line: { color: C_BORDER, width: 1 },
    rectRadius: 0.08,
  });

  slide5.addText('Statutory Deliverables', {
    x: 1.1,
    y: 3.55,
    w: 5.0,
    h: 0.3,
    fontSize: 13,
    fontFace: 'Arial',
    color: C_NAVY,
    bold: true,
  });

  slide5.addText(
    '• Linked Excel Workbook (.xlsx):\n  Contains live formulas (=SUM, sheet links) across Control, TB, P&L, BS & Sch 1–14.\n\n• Audit-Ready PDF Report:\n  Formatted vertical statements with accounting notes and signature blocks.',
    {
      x: 1.1,
      y: 3.95,
      w: 5.0,
      h: 2.1,
      fontSize: 11,
      fontFace: 'Arial',
      color: '334155',
      lineSpacing: 16,
    }
  );

  // Bottom-Right Box: Practice Value
  slide5.addShape(pptx.ShapeType.roundRect, {
    x: 6.7,
    y: 3.3,
    w: 5.6,
    h: 3.0,
    fill: { color: C_NAVY },
    line: { color: '334155', width: 1 },
    rectRadius: 0.08,
  });

  slide5.addText('Practice Benefits', {
    x: 7.0,
    y: 3.55,
    w: 5.0,
    h: 0.3,
    fontSize: 13,
    fontFace: 'Arial',
    color: C_GOLD,
    bold: true,
  });

  slide5.addText(
    '✓ Saves 90% time during peak tax audit season.\n✓ Eliminates manual calculation & linking errors.\n✓ Instant bank loan & credit proposal readiness.\n✓ 100% private: In-browser processing with no cloud leaks.',
    {
      x: 7.0,
      y: 3.95,
      w: 5.0,
      h: 2.1,
      fontSize: 11.5,
      fontFace: 'Arial',
      color: C_WHITE,
      lineSpacing: 18,
    }
  );

  return pptx;
};

export const downloadPresentationFile = async (
  entity?: EntityDetails,
  reconciliation?: ReconciliationReport
): Promise<void> => {
  const pptx = generateProjectPresentation(entity, reconciliation);
  const safeName = (entity?.name || 'ICAI_Non_Corporate').replace(/[^a-zA-Z0-9]/g, '_');
  await pptx.writeFile({ fileName: `${safeName}_Financial_Statements_Presentation.pptx` });
};
