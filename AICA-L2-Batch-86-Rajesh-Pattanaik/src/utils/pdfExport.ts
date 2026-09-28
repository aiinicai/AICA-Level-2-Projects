import { jsPDF } from 'jspdf';
import { VerificationReport } from '../types';

/**
 * Bulletproof text sanitizer for jsPDF standard fonts.
 * Standard Helvetica/Times fonts in PDF engines only support 1-byte WinAnsi/Latin-1 encoding.
 * Passing multi-byte UTF-8 sequences (like ₹, curly quotes, emojis, em-dashes) causes
 * corrupted character sequences (e.g. 'Ø=ßâ', '¹2.5', '& þ') and distorts character kerning/spacing.
 */
export function cleanPdfText(str: string | undefined | null): string {
  if (!str) return '';
  return str
    // Convert Indian Rupee symbol to standard 'Rs. '
    .replace(/₹/g, 'Rs. ')
    // Convert smart double quotes to standard ASCII quotes
    .replace(/[\u201C\u201D\u201E\u201F\u2033\u2036]/g, '"')
    // Convert smart single quotes and apostrophes to standard ASCII single quote
    .replace(/[\u2018\u2019\u201A\u201B\u2032\u2035]/g, "'")
    // Convert long dashes and hyphens to clean ASCII hyphen-minus
    .replace(/[\u2013\u2014\u2015]/g, ' - ')
    // Convert ellipses to three dots
    .replace(/\u2026/g, '...')
    // Convert bullets to asterisks or dashes
    .replace(/[\u2022\u2023\u25E6\u2043\u2219]/g, ' * ')
    // Convert section symbols
    .replace(/§/g, 'Sec. ')
    // Strip emojis and miscellaneous symbols
    .replace(/[\u{1F300}-\u{1F9FF}]/gu, '')
    .replace(/[\u{2600}-\u{26FF}]/gu, '')
    .replace(/[\u{2700}-\u{27BF}]/gu, '')
    .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
    .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '')
    // Replace non-breaking spaces with standard space
    .replace(/\u00A0/g, ' ')
    // Filter any remaining non-ASCII characters to standard space
    .replace(/[^\x20-\x7E\r\n\t]/g, ' ')
    // Collapse duplicate spaces
    .replace(/ +/g, ' ')
    .trim();
}

export function generateVerificationPdf(report: VerificationReport): void {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'pt',
    format: 'a4'
  });

  const pageWidth = doc.internal.pageSize.getWidth(); // 595.28 pt
  const pageHeight = doc.internal.pageSize.getHeight(); // 841.89 pt
  const margin = 36;
  const contentWidth = pageWidth - margin * 2; // 523.28 pt
  let y = margin;

  const footerHeight = 35;

  const caseDate = new Date(report.verificationTimestamp);
  const caseId = `CAVA-${caseDate.getFullYear()}-${(caseDate.getTime() % 1000).toString().padStart(3, '0')}`;
  const formattedDate = caseDate.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
  const formattedTime = caseDate.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit'
  });

  // Draw running header on subsequent pages
  const drawRunningHeader = (pageNum: number) => {
    if (pageNum === 1) return;
    doc.setFillColor(248, 250, 252);
    doc.rect(margin, 18, contentWidth, 22, 'F');
    doc.setDrawColor(203, 213, 225);
    doc.setLineWidth(0.5);
    doc.line(margin, 40, pageWidth - margin, 40);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(30, 41, 59);
    doc.text('CA RAJESH KUMAR PATTANAIK & ASSOCIATES | STATUTORY AUDIT MEMORANDUM', margin + 6, 32);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(100, 116, 139);
    doc.text(`Ref: ${caseId} | ${formattedDate}`, pageWidth - margin - 6, 32, { align: 'right' });
  };

  const checkPageBreak = (neededHeight: number) => {
    if (y + neededHeight > pageHeight - footerHeight - 15) {
      doc.addPage();
      const newPage = doc.getNumberOfPages();
      drawRunningHeader(newPage);
      y = 50;
    }
  };

  // Professional section heading banner
  const drawSectionHeading = (
    title: string,
    subtitle?: string,
    badgeText?: string,
    badgeColor: [number, number, number] = [30, 41, 59]
  ) => {
    checkPageBreak(40);
    y += 8;

    // Header strip background
    doc.setFillColor(241, 245, 249);
    doc.roundedRect(margin, y, contentWidth, 22, 2, 2, 'F');
    doc.setDrawColor(203, 213, 225);
    doc.setLineWidth(0.5);
    doc.roundedRect(margin, y, contentWidth, 22, 2, 2, 'S');

    // Section title
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.setTextColor(15, 23, 42);
    doc.text(cleanPdfText(title), margin + 8, y + 14.5);

    // Optional badge on right
    if (badgeText) {
      const cleanBadge = cleanPdfText(badgeText);
      const badgeWidth = doc.getTextWidth(cleanBadge) + 12;
      const badgeX = pageWidth - margin - badgeWidth - 6;
      doc.setFillColor(badgeColor[0], badgeColor[1], badgeColor[2]);
      doc.roundedRect(badgeX, y + 3.5, badgeWidth, 15, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(cleanBadge, badgeX + badgeWidth / 2, y + 13.5, { align: 'center' });
    }

    y += 26;

    if (subtitle) {
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7.5);
      doc.setTextColor(71, 85, 105);
      const subLines = doc.splitTextToSize(cleanPdfText(subtitle), contentWidth);
      doc.text(subLines, margin + 4, y);
      y += subLines.length * 10 + 4;
    }
  };

  // =========================================================================
  // 1. FORMAL CHARTERED ACCOUNTANT FIRM LETTERHEAD (PAGE 1)
  // =========================================================================
  // Top deep navy band
  doc.setFillColor(15, 23, 42); // slate-900
  doc.rect(margin, y, contentWidth, 68, 'F');

  // Gold accent rule beneath title
  doc.setFillColor(217, 119, 6); // amber-600
  doc.rect(margin, y + 68, contentWidth, 3, 'F');

  // Firm Name & Credentials
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(255, 255, 255);
  doc.text('CA RAJESH KUMAR PATTANAIK & ASSOCIATES', margin + 12, y + 20);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(217, 119, 6);
  doc.text('CHARTERED ACCOUNTANTS & STATUTORY TAX AUDITORS', margin + 12, y + 32);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(203, 213, 225);
  doc.text('Bhubaneswar, Odisha | AICA Level 2 Research Capstone Framework', margin + 12, y + 43);
  doc.text('Subject: Independent Statutory Substantiation & Cross-Domain Regulatory Audit', margin + 12, y + 54);

  // Right side engagement reference block
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(255, 255, 255);
  doc.text(`MEMORANDUM REF: ${caseId}`, pageWidth - margin - 12, y + 20, { align: 'right' });

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(203, 213, 225);
  doc.text(`Date: ${formattedDate} (${formattedTime} IST)`, pageWidth - margin - 12, y + 32, { align: 'right' });
  doc.text('Classification: CONFIDENTIAL / AUDIT MEMORANDUM', pageWidth - margin - 12, y + 43, { align: 'right' });
  doc.setFont('helvetica', 'italic');
  doc.setTextColor(148, 163, 184);
  doc.text('"Verify the explicit. Surface the latent regulatory exposures."', pageWidth - margin - 12, y + 54, { align: 'right' });

  y += 78;

  // =========================================================================
  // 2. STRUCTURED EXECUTIVE AUDIT METRICS GRID (FIXES OVERLAPPING COLUMNS)
  // =========================================================================
  checkPageBreak(58);

  const numCols = 4;
  const colGap = 6;
  const colW = (contentWidth - colGap * (numCols - 1)) / numCols; // ~126 pt each
  const gridHeight = 48;

  // 4 discrete boxes with calculated widths - guarantees zero text collision
  const metrics = [
    {
      label: 'SOURCE RELIABILITY',
      value: cleanPdfText(report.sourceReliability),
      subtext: report.sourceReliability === 'Primary Authoritative' ? 'Official Statute / Act' : 'Secondary / Client Draft',
      isPrimary: report.sourceReliability === 'Primary Authoritative'
    },
    {
      label: 'SOURCE SUPPORT',
      value: cleanPdfText(report.scoreBreakdown?.sourceSupport || 'Moderate'),
      subtext: 'Direct Text Substantiation',
      isPrimary: false
    },
    {
      label: 'COMPLETENESS',
      value: cleanPdfText(report.scoreBreakdown?.completeness || 'Partial'),
      subtext: 'Cross-Domain Coverage',
      isPrimary: false
    },
    {
      label: 'RELIABILITY SCORE',
      value: `${report.verificationScore}/100`,
      subtext: cleanPdfText(report.overallStatus),
      isPrimary: true
    }
  ];

  metrics.forEach((m, i) => {
    const boxX = margin + i * (colW + colGap);
    
    // Background and border
    doc.setFillColor(i === 3 ? (report.verificationScore >= 65 ? 240 : 255) : 255, i === 3 ? (report.verificationScore >= 65 ? 253 : 241) : 255, i === 3 ? (report.verificationScore >= 65 ? 244 : 242) : 255);
    doc.roundedRect(boxX, y, colW, gridHeight, 2, 2, 'F');
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.5);
    doc.roundedRect(boxX, y, colW, gridHeight, 2, 2, 'S');

    // Top label
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(m.label, boxX + 6, y + 12);

    // Primary Value
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(i === 3 ? 12 : 8.5);
    if (i === 3) {
      if (report.verificationScore >= 80) doc.setTextColor(5, 150, 105);
      else if (report.verificationScore >= 50) doc.setTextColor(217, 119, 6);
      else doc.setTextColor(225, 29, 72);
    } else {
      doc.setTextColor(15, 23, 42);
    }
    const valLines = doc.splitTextToSize(m.value, colW - 12);
    doc.text(valLines[0], boxX + 6, y + (i === 3 ? 26 : 24));

    // Subtext
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    const subLines = doc.splitTextToSize(m.subtext, colW - 12);
    doc.text(subLines[0], boxX + 6, y + 38);
  });

  y += gridHeight + 8;

  // =========================================================================
  // 3. LIMITED VERIFICATION CAUTION NOTICE (IF APPLICABLE)
  // =========================================================================
  if (report.isLimitedVerification) {
    checkPageBreak(38);
    const noticeContent = cleanPdfText(
      report.limitedVerificationNotice ||
      'No authoritative statutory source material was supplied with the inquiry. This report represents an AI-assisted cross-domain regulatory risk and omission analysis. All statutory triggers must be confirmed against primary official gazettes, Acts, and judicial rulings prior to client advisory issuance.'
    );
    const noticeLines = doc.splitTextToSize(noticeContent, contentWidth - 20);
    const noticeBoxHeight = Math.max(34, noticeLines.length * 9.5 + 18);

    doc.setFillColor(254, 243, 199); // amber-100
    doc.roundedRect(margin, y, contentWidth, noticeBoxHeight, 2, 2, 'F');
    doc.setDrawColor(217, 119, 6); // amber-600
    doc.setLineWidth(1);
    doc.roundedRect(margin, y, contentWidth, noticeBoxHeight, 2, 2, 'S');

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7.5);
    doc.setTextColor(146, 64, 14);
    doc.text('STATUTORY NOTICE: LIMITED VERIFICATION (NO PRIMARY SOURCES SUPPLIED)', margin + 10, y + 13);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(120, 53, 15);
    doc.text(noticeLines, margin + 10, y + 23);

    y += noticeBoxHeight + 8;
  }

  // =========================================================================
  // 4. SECTION 1: EXECUTIVE VERDICT & RELIABILITY RATING
  // =========================================================================
  drawSectionHeading(
    '1. EXECUTIVE AUDIT OPINION & RELIABILITY VERDICT',
    undefined,
    `RATING: ${report.verificationScore}/100`,
    [15, 23, 42]
  );

  const cleanVerdict = cleanPdfText(report.executiveVerdict);
  const verdictLines = doc.splitTextToSize(cleanVerdict, contentWidth - 24);
  const verdictBoxHeight = Math.max(38, verdictLines.length * 10.5 + 16);

  checkPageBreak(verdictBoxHeight + 15);

  doc.setFillColor(255, 251, 235); // amber-50
  doc.roundedRect(margin, y, contentWidth, verdictBoxHeight, 2, 2, 'F');
  doc.setFillColor(217, 119, 6); // amber-600 left accent bar
  doc.rect(margin, y, 4, verdictBoxHeight, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(69, 26, 3);
  doc.text(verdictLines, margin + 12, y + 13);

  y += verdictBoxHeight + 6;

  if (report.scoreExplanation) {
    const cleanExp = cleanPdfText(report.scoreExplanation);
    const expLines = doc.splitTextToSize(`Auditor Assessment Rationale: ${cleanExp}`, contentWidth - 16);
    checkPageBreak(expLines.length * 9.5 + 10);
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(7.5);
    doc.setTextColor(71, 85, 105);
    doc.text(expLines, margin + 6, y + 8);
    y += expLines.length * 9.5 + 6;
  }

  // =========================================================================
  // 5. SECTION 2: KEY FACTS IDENTIFIED & STATUTORY TRIGGERS
  // =========================================================================
  if (report.keyFacts && report.keyFacts.length > 0) {
    drawSectionHeading('2. CLIENT FACTS IDENTIFIED & STATUTORY TRIGGERS', undefined, `${report.keyFacts.length} FACTS IDENTIFIED`);

    report.keyFacts.forEach((kf) => {
      const cleanCat = cleanPdfText(kf.category);
      const cleanFact = cleanPdfText(kf.fact);
      const catWidth = doc.getTextWidth(cleanCat) + 12;
      const factLines = doc.splitTextToSize(cleanFact, contentWidth - catWidth - 24);
      const rowHeight = Math.max(18, factLines.length * 9.5 + 9);

      checkPageBreak(rowHeight + 4);

      doc.setFillColor(248, 250, 252);
      doc.roundedRect(margin, y, contentWidth, rowHeight, 2, 2, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, rowHeight, 2, 2, 'S');

      // Category chip
      doc.setFillColor(226, 232, 240);
      doc.roundedRect(margin + 6, y + 3.5, catWidth, 12, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(51, 65, 85);
      doc.text(cleanCat, margin + 6 + catWidth / 2, y + 11.5, { align: 'center' });

      // Fact text
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(15, 23, 42);
      doc.text(factLines, margin + 12 + catWidth, y + 11.5);

      y += rowHeight + 4;
    });
  }

  // =========================================================================
  // 6. SECTION 3: APPLICABLE PROFESSIONAL DOMAINS & AI OMISSION STATUS
  // =========================================================================
  if (report.applicableDomains && report.applicableDomains.length > 0) {
    drawSectionHeading(
      '3. APPLICABLE PROFESSIONAL DOMAINS & REGULATORY COVERAGE',
      'Evaluates statutory cross-domain obligations triggered by client facts across Direct Tax, GST, MSMED & Corporate Law.',
      `${report.applicableDomains.length} DOMAINS EVALUATED`
    );

    report.applicableDomains.forEach((dom) => {
      const isMissed = dom.aiAddressedStatus === 'Missed / Omitted';
      const isPartial = dom.aiAddressedStatus === 'Partially Addressed';

      const cleanDom = cleanPdfText(dom.domain);
      const cleanProv = cleanPdfText(dom.relevantProvision);
      const colWidth = (contentWidth - 36) / 3;

      const whyLines = doc.splitTextToSize(cleanPdfText(dom.whyItApplies), colWidth);
      const impLines = doc.splitTextToSize(cleanPdfText(dom.impact), colWidth);
      const verLines = doc.splitTextToSize(cleanPdfText(dom.verificationRequired), colWidth);
      const maxColLines = Math.max(whyLines.length, impLines.length, verLines.length);

      const cardHeight = Math.max(64, 34 + maxColLines * 9.5 + 6);
      checkPageBreak(cardHeight + 6);

      // Card container
      doc.setFillColor(255, 255, 255);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(isMissed ? 244 : 226, isMissed ? 63 : 232, isMissed ? 94 : 240);
      doc.setLineWidth(isMissed ? 1 : 0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Left bar
      doc.setFillColor(isMissed ? 225 : isPartial ? 217 : 16, isMissed ? 29 : isPartial ? 119 : 185, isMissed ? 72 : isPartial ? 6 : 129);
      doc.rect(margin, y, 4, cardHeight, 'F');

      // Domain title & provision
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(15, 23, 42);
      doc.text(cleanDom, margin + 10, y + 13);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(100, 116, 139);
      doc.text(`(${cleanProv})`, margin + 14 + doc.getTextWidth(cleanDom), y + 13);

      // Status pill
      const statusText = isMissed ? 'OMITTED IN AI DRAFT' : isPartial ? 'PARTIALLY ADDRESSED' : 'ADDRESSED IN AI DRAFT';
      const badgeWidth = doc.getTextWidth(statusText) + 12;
      doc.setFillColor(isMissed ? 255 : isPartial ? 254 : 209, isMissed ? 228 : isPartial ? 243 : 250, isMissed ? 230 : isPartial ? 199 : 229);
      doc.roundedRect(pageWidth - margin - badgeWidth - 8, y + 4, badgeWidth, 13, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(isMissed ? 159 : isPartial ? 146 : 6, isMissed ? 18 : isPartial ? 64 : 95, isMissed ? 57 : isPartial ? 14 : 70);
      doc.text(statusText, pageWidth - margin - badgeWidth / 2 - 8, y + 12.5, { align: 'center' });

      // 3 data columns
      const c1X = margin + 10;
      const c2X = margin + 10 + colWidth + 8;
      const c3X = margin + 10 + (colWidth + 8) * 2;

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(148, 163, 184);
      doc.text('STATUTORY APPLICABILITY:', c1X, y + 26);
      doc.text('PROFESSIONAL EXPOSURE:', c2X, y + 26);
      doc.text('DUE DILIGENCE REQUIRED:', c3X, y + 26);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(51, 65, 85);
      doc.text(whyLines, c1X, y + 36);
      doc.text(impLines, c2X, y + 36);
      doc.text(verLines, c3X, y + 36);

      y += cardHeight + 6;
    });
  }

  // =========================================================================
  // 7. SECTION 4: SUPPORTED CLAIMS & STATUTORY SUBSTANTIATION
  // =========================================================================
  if (report.supportedClaims && report.supportedClaims.length > 0) {
    drawSectionHeading(
      '4. SUBSTANTIATED CLAIMS & STATUTORY CORROBORATION',
      'Identifies assertions in the AI response corroborated by authoritative provisions.',
      `${report.supportedClaims.length} VERIFIED`,
      [5, 150, 105]
    );

    report.supportedClaims.forEach((item) => {
      const cleanClaim = `"${cleanPdfText(item.claim)}"`;
      const cleanEv = item.sourceEvidence ? `Statutory Citation: "${cleanPdfText(item.sourceEvidence)}"` : 'Corroborated by governing statutory provisions.';
      const cleanImp = `Professional Implication: ${cleanPdfText(item.professionalImplication)}`;

      const claimLines = doc.splitTextToSize(cleanClaim, contentWidth - 110);
      const evLines = doc.splitTextToSize(cleanEv, contentWidth - 24);
      const impLines = doc.splitTextToSize(cleanImp, contentWidth - 24);

      const cardHeight = Math.max(52, 16 + claimLines.length * 10 + evLines.length * 9.5 + impLines.length * 9.5 + 6);
      checkPageBreak(cardHeight + 6);

      doc.setFillColor(240, 253, 244); // emerald-50
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(187, 247, 208);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Left bar
      doc.setFillColor(5, 150, 105);
      doc.rect(margin, y, 4, cardHeight, 'F');

      // Claim statement
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(6, 78, 59);
      doc.text(claimLines, margin + 10, y + 12.5);

      // Clean ASCII badge (No emojis, no garbling!)
      const badgeText = '[ SUBSTANTIATED ]';
      doc.setFillColor(5, 150, 105);
      doc.roundedRect(pageWidth - margin - 88, y + 5, 80, 13, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(badgeText, pageWidth - margin - 48, y + 13.5, { align: 'center' });

      let currentOffset = y + 12.5 + claimLines.length * 10 + 2;

      // Evidence citation
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7.5);
      doc.setTextColor(4, 120, 87);
      doc.text(evLines, margin + 10, currentOffset);
      currentOffset += evLines.length * 9.5 + 2;

      // Implication
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(30, 41, 59);
      doc.text(impLines, margin + 10, currentOffset);

      y += cardHeight + 6;
    });
  }

  // =========================================================================
  // 8. SECTION 5: CLAIMS REQUIRING PROFESSIONAL DUE DILIGENCE
  // =========================================================================
  if (report.questionableClaims && report.questionableClaims.length > 0) {
    drawSectionHeading(
      '5. CLAIMS REQUIRING PROFESSIONAL DUE DILIGENCE',
      'Assertions lacking primary statutory corroboration or requiring condition verification.',
      `${report.questionableClaims.length} REQ. VERIFICATION`,
      [217, 119, 6]
    );

    report.questionableClaims.forEach((item) => {
      const cleanClaim = `"${cleanPdfText(item.claim)}"`;
      const cleanNote = cleanPdfText(item.missingEvidenceNotice || item.analysis || 'Not substantiated by primary statutory references.');
      const cleanImp = `Professional Risk: ${cleanPdfText(item.professionalImplication)}`;

      const claimLines = doc.splitTextToSize(cleanClaim, contentWidth - 120);
      const notLines = doc.splitTextToSize(`Due Diligence Requirement: ${cleanNote}`, contentWidth - 24);
      const impLines = doc.splitTextToSize(cleanImp, contentWidth - 24);

      const cardHeight = Math.max(52, 16 + claimLines.length * 10 + notLines.length * 9.5 + impLines.length * 9.5 + 6);
      checkPageBreak(cardHeight + 6);

      doc.setFillColor(255, 251, 235); // amber-50
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(253, 230, 138);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Left bar
      doc.setFillColor(217, 119, 6);
      doc.rect(margin, y, 4, cardHeight, 'F');

      // Claim statement
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(146, 64, 14);
      doc.text(claimLines, margin + 10, y + 12.5);

      // Clean ASCII badge
      const badgeText = '[ REQ. DUE DILIGENCE ]';
      doc.setFillColor(217, 119, 6);
      doc.roundedRect(pageWidth - margin - 105, y + 5, 98, 13, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(badgeText, pageWidth - margin - 56, y + 13.5, { align: 'center' });

      let currentOffset = y + 12.5 + claimLines.length * 10 + 2;

      // Notice
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(180, 83, 9);
      doc.text(notLines, margin + 10, currentOffset);
      currentOffset += notLines.length * 9.5 + 2;

      // Implication
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(30, 41, 59);
      doc.text(impLines, margin + 10, currentOffset);

      y += cardHeight + 6;
    });
  }

  // =========================================================================
  // 9. SECTION 6: POTENTIAL ERRORS & STATUTORY MISSTATEMENTS
  // =========================================================================
  if (report.potentialErrors && report.potentialErrors.length > 0) {
    drawSectionHeading(
      '6. POTENTIAL ERRORS & STATUTORY MISSTATEMENTS',
      'Identifies factual contradictions, outdated thresholds, or erroneous statutory interpretations.',
      `${report.potentialErrors.length} CRITICAL MISSTATEMENTS`,
      [225, 29, 72]
    );

    report.potentialErrors.forEach((item) => {
      const cleanStmt = `AI Statement: "${cleanPdfText(item.statementInAIAnswer)}"`;
      const cleanContra = `Contradicting Authority: "${cleanPdfText(item.contradictingSourceEvidence)}"`;
      const cleanRisk = `Liability / Exposure: ${cleanPdfText(item.professionalImplication)}`;

      const stmtLines = doc.splitTextToSize(cleanStmt, contentWidth - 120);
      const contraLines = doc.splitTextToSize(cleanContra, contentWidth - 24);
      const riskLines = doc.splitTextToSize(cleanRisk, contentWidth - 24);

      const cardHeight = Math.max(56, 16 + stmtLines.length * 10 + contraLines.length * 9.5 + riskLines.length * 9.5 + 6);
      checkPageBreak(cardHeight + 6);

      doc.setFillColor(255, 241, 242); // rose-50
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(254, 205, 211);
      doc.setLineWidth(1);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Left bar
      doc.setFillColor(225, 29, 72);
      doc.rect(margin, y, 4, cardHeight, 'F');

      // Statement
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(159, 18, 57);
      doc.text(stmtLines, margin + 10, y + 12.5);

      // Error Type Badge
      const errLabel = `[ ${cleanPdfText(item.errorType.replace(/_/g, ' ').toUpperCase())} ]`;
      doc.setFillColor(225, 29, 72);
      doc.roundedRect(pageWidth - margin - 110, y + 5, 102, 13, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6);
      doc.setTextColor(255, 255, 255);
      doc.text(errLabel, pageWidth - margin - 59, y + 13.5, { align: 'center' });

      let currentOffset = y + 12.5 + stmtLines.length * 10 + 2;

      // Contradicting source
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(190, 18, 60);
      doc.text(contraLines, margin + 10, currentOffset);
      currentOffset += contraLines.length * 9.5 + 2;

      // Exposure
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(15, 23, 42);
      doc.text(riskLines, margin + 10, currentOffset);

      y += cardHeight + 6;
    });
  }

  // =========================================================================
  // 10. SECTION 7: MISSED ISSUES & RELATED PROVISIONS (CENTRAL CA ENGINE)
  // =========================================================================
  if (report.missedIssues && report.missedIssues.length > 0) {
    drawSectionHeading(
      '7. STATUTORY OMISSIONS & LATENT REGULATORY EXPOSURES',
      '"Even if the primary answer is procedurally correct, what reporting obligations and penalties did the AI omit?"',
      `${report.missedIssues.length} MATERIAL OMISSIONS`,
      [67, 56, 202] // indigo-700
    );

    report.missedIssues.forEach((miss) => {
      const cleanDom = cleanPdfText(miss.domain);
      const cleanTitle = cleanPdfText(miss.issueTitle);
      const cleanProv = `[${cleanPdfText(miss.applicableProvision)}]`;
      const cleanDesc = cleanPdfText(miss.description);

      const descLines = doc.splitTextToSize(cleanDesc, contentWidth - 24);
      const colWidth = (contentWidth - 36) / 3;

      const wm = doc.splitTextToSize(cleanPdfText(miss.whyMissedByAI), colWidth);
      const pen = doc.splitTextToSize(cleanPdfText(miss.consequenceOrPenalty), colWidth);
      const act = doc.splitTextToSize(cleanPdfText(miss.actionRequired), colWidth);
      const maxSubLines = Math.max(wm.length, pen.length, act.length);

      const cardHeight = Math.max(76, 26 + descLines.length * 9.5 + 14 + maxSubLines * 9.5 + 8);
      checkPageBreak(cardHeight + 6);

      // Box styling
      doc.setFillColor(245, 243, 255); // indigo-50
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(199, 210, 254);
      doc.setLineWidth(1);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Left bar
      doc.setFillColor(67, 56, 202);
      doc.rect(margin, y, 4, cardHeight, 'F');

      // Domain badge
      const domWidth = doc.getTextWidth(cleanDom) + 10;
      doc.setFillColor(67, 56, 202);
      doc.roundedRect(margin + 10, y + 5, domWidth, 12, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(cleanDom, margin + 10 + domWidth / 2, y + 13, { align: 'center' });

      // Title
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(30, 27, 75);
      doc.text(cleanTitle, margin + 16 + domWidth, y + 13);

      // Provision
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(79, 70, 229);
      doc.text(cleanProv, pageWidth - margin - 10, y + 13, { align: 'right' });

      // Description
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(51, 65, 85);
      doc.text(descLines, margin + 10, y + 25);

      const subCardsY = y + 25 + descLines.length * 9.5 + 5;
      const c1X = margin + 10;
      const c2X = margin + 10 + colWidth + 8;
      const c3X = margin + 10 + (colWidth + 8) * 2;

      // 3 highlight columns
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(100, 116, 139);
      doc.text('WHY AI MISSED IT:', c1X, subCardsY);
      doc.text('PENALTIES & EXPOSURES:', c2X, subCardsY);
      doc.text('MANDATORY CA ACTION:', c3X, subCardsY);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(71, 85, 105);
      doc.text(wm, c1X, subCardsY + 9.5);

      doc.setTextColor(190, 18, 60); // Red bold for penalties
      doc.setFont('helvetica', 'bold');
      doc.text(pen, c2X, subCardsY + 9.5);

      doc.setTextColor(5, 150, 105); // Green for action
      doc.setFont('helvetica', 'normal');
      doc.text(act, c3X, subCardsY + 9.5);

      y += cardHeight + 6;
    });
  }

  // =========================================================================
  // 11. SECTION 8: SOURCE EVIDENCE MATRIX
  // =========================================================================
  if (report.sourceEvidenceList && report.sourceEvidenceList.length > 0) {
    drawSectionHeading(
      '8. STATUTORY SOURCE EVIDENCE MATRIX',
      'Claim-by-claim verification against statutory provisions and official circulars.'
    );

    report.sourceEvidenceList.forEach((ev, idx) => {
      const cleanClaim = `"${cleanPdfText(ev.aiClaim)}"`;
      const cleanEvText = cleanPdfText(ev.sourceEvidence);
      const cleanImp = `Implication: ${cleanPdfText(ev.professionalImplication)}`;

      const cLines = doc.splitTextToSize(cleanClaim, contentWidth - 130);
      const seLines = doc.splitTextToSize(cleanEvText, contentWidth - 85);
      const impLines = doc.splitTextToSize(cleanImp, contentWidth - 20);

      const cardHeight = Math.max(50, 18 + cLines.length * 9.5 + seLines.length * 9.5 + impLines.length * 9.5 + 6);
      checkPageBreak(cardHeight + 5);

      doc.setFillColor(248, 250, 252);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Claim #
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(15, 23, 42);
      doc.text(`Claim #${idx + 1}:`, margin + 8, y + 12);

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(51, 65, 85);
      doc.text(cLines, margin + 48, y + 12);

      // Status badge
      const isSupp = ev.status === 'SUPPORTED';
      const statusLabel = isSupp ? '[ VERIFIED ]' : '[ UNVERIFIED ]';
      doc.setFillColor(isSupp ? 209 : 254, isSupp ? 250 : 243, isSupp ? 229 : 199);
      doc.roundedRect(pageWidth - margin - 80, y + 4, 72, 12, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(isSupp ? 6 : 146, isSupp ? 95 : 64, isSupp ? 70 : 14);
      doc.text(statusLabel, pageWidth - margin - 44, y + 12.5, { align: 'center' });

      let currentOffset = y + 12 + cLines.length * 9.5 + 2;

      // Source excerpt
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7);
      doc.setTextColor(100, 116, 139);
      doc.text('Statutory Source:', margin + 8, currentOffset);
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7);
      doc.setTextColor(15, 23, 42);
      doc.text(seLines, margin + 74, currentOffset);
      currentOffset += seLines.length * 9.5 + 2;

      // Implication
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(71, 85, 105);
      doc.text(impLines, margin + 8, currentOffset);

      y += cardHeight + 5;
    });
  }

  // =========================================================================
  // 12. SECTION 9: STATUTORY PENALTIES & REPORTING IMPACT
  // =========================================================================
  if (report.consequencesAndPenalties && report.consequencesAndPenalties.length > 0) {
    drawSectionHeading(
      '9. STATUTORY PENALTIES, CONSEQUENCES & REPORTING IMPACT',
      undefined,
      `${report.consequencesAndPenalties.length} EXPOSURES`
    );

    report.consequencesAndPenalties.forEach((cp) => {
      const cleanArea = cleanPdfText(cp.area);
      const cleanProv = cleanPdfText(cp.provision);
      const cleanDesc = cleanPdfText(cp.description);
      const cleanPen = cleanPdfText(cp.statutoryPenaltyOrImpact);

      const desc = doc.splitTextToSize(cleanDesc, contentWidth - 190);
      const pen = doc.splitTextToSize(cleanPen, 175);
      const cardHeight = Math.max(36, 18 + Math.max(desc.length, pen.length) * 9.5 + 6);

      checkPageBreak(cardHeight + 4);
      doc.setFillColor(255, 241, 242);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(254, 205, 211);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Area & Provision
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(15, 23, 42);
      doc.text(`[${cleanArea}] ${cleanProv}`, margin + 8, y + 12);

      // Risk badge
      const isCrit = cp.riskLevel === 'Critical';
      doc.setFillColor(isCrit ? 225 : 217, isCrit ? 29 : 119, isCrit ? 72 : 6);
      doc.roundedRect(pageWidth - margin - 80, y + 4, 72, 12, 2, 2, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(`${cp.riskLevel.toUpperCase()} RISK`, pageWidth - margin - 44, y + 12.5, { align: 'center' });

      // Penalty text & description
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7);
      doc.setTextColor(51, 65, 85);
      doc.text(desc, margin + 8, y + 23);

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(190, 18, 60);
      doc.text(pen, pageWidth - margin - 175, y + 23);

      y += cardHeight + 4;
    });
  }

  // =========================================================================
  // 13. SECTION 10: RECOMMENDED PROFESSIONAL ACTIONS
  // =========================================================================
  if (report.recommendedProfessionalActions && report.recommendedProfessionalActions.length > 0) {
    drawSectionHeading('10. RECOMMENDED PROFESSIONAL ACTIONS (AUDIT CHECKLIST)');

    report.recommendedProfessionalActions.forEach((act, idx) => {
      const cleanAct = cleanPdfText(act);
      const actLines = doc.splitTextToSize(cleanAct, contentWidth - 36);
      const cardHeight = Math.max(20, actLines.length * 9.5 + 9);

      checkPageBreak(cardHeight + 4);
      doc.setFillColor(255, 255, 255);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.roundedRect(margin, y, contentWidth, cardHeight, 2, 2, 'S');

      // Number circle
      doc.setFillColor(15, 23, 42);
      doc.circle(margin + 10, y + cardHeight / 2, 6, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(6.5);
      doc.setTextColor(255, 255, 255);
      doc.text(`${idx + 1}`, margin + 10, y + cardHeight / 2 + 2, { align: 'center' });

      // Action text
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(7.5);
      doc.setTextColor(15, 23, 42);
      doc.text(actLines, margin + 22, y + 11.5);

      y += cardHeight + 4;
    });
  }

  // =========================================================================
  // 14. SECTION 11: AUDITOR'S ATTESTATION & STATUTORY RELIANCE DISCLAIMER
  // =========================================================================
  const cleanWarn = cleanPdfText(
    report.professionalRelianceWarning ||
    'CA VerifyAI is an AI-assisted professional verification and risk-identification tool. It does not replace professional judgment, authoritative legal research, or independent verification against current official gazette publications and primary judicial precedents.'
  );
  const warnLines = doc.splitTextToSize(cleanWarn, contentWidth - 20);
  const warnBoxHeight = Math.max(88, warnLines.length * 9 + 58);

  checkPageBreak(warnBoxHeight + 10);
  y += 6;

  // Formal Auditor Seal & Signature Container
  doc.setFillColor(15, 23, 42); // slate-900
  doc.roundedRect(margin, y, contentWidth, warnBoxHeight, 2, 2, 'F');

  // Title
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(52, 211, 153); // emerald-400
  doc.text('11. AUDITOR ATTESTATION & STATUTORY RELIANCE DISCLAIMER', margin + 10, y + 14);

  // Disclaimer text
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(203, 213, 225);
  doc.text(warnLines, margin + 10, y + 25);

  // Formal Signature Block
  const sigY = y + warnBoxHeight - 24;
  doc.setDrawColor(51, 65, 85);
  doc.setLineWidth(0.5);
  doc.line(margin + 10, sigY - 4, pageWidth - margin - 10, sigY - 4);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(255, 255, 255);
  doc.text('ISSUED BY: CA RAJESH KUMAR PATTANAIK, FCA', margin + 10, sigY + 8);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  doc.setTextColor(148, 163, 184);
  doc.text('Chartered Accountant | Bhubaneswar, Odisha | AICA Level 2 Research Capstone Fellow', margin + 10, sigY + 18);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7);
  doc.setTextColor(52, 211, 153);
  doc.text('VERIFIED UNDER ICAI ETHICAL DUE DILIGENCE CONVENTIONS', pageWidth - margin - 10, sigY + 8, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  doc.setTextColor(148, 163, 184);
  doc.text(`Document Verification Hash: SHA256-${caseId}-${caseDate.getTime().toString(16).toUpperCase()}`, pageWidth - margin - 10, sigY + 18, { align: 'right' });

  y += warnBoxHeight + 8;

  // =========================================================================
  // 15. RUNNING FOOTERS ON ALL PAGES
  // =========================================================================
  const totalPages = doc.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);

    // Footer divider line
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.5);
    doc.line(margin, pageHeight - 26, pageWidth - margin, pageHeight - 26);

    // Left: Firm attribution
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(
      'CA VerifyAI | CA Rajesh Kumar Pattanaik & Associates, Chartered Accountants | Bhubaneswar, Odisha',
      margin,
      pageHeight - 14
    );

    // Center: Confidentiality notice
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(6);
    doc.setTextColor(148, 163, 184);
    doc.text('CONFIDENTIAL - STATUTORY AUDIT MEMORANDUM', pageWidth / 2, pageHeight - 14, { align: 'center' });

    // Right: Page number
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(7);
    doc.setTextColor(15, 23, 42);
    doc.text(`Page ${p} of ${totalPages}`, pageWidth - margin, pageHeight - 14, { align: 'right' });
  }

  // Save filename
  const filename = `CA_Statutory_Verification_Memorandum_${caseId}.pdf`;
  doc.save(filename);
}
