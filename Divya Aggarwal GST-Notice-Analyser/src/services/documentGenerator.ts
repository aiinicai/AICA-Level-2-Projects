import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx';
import { saveAs } from 'file-saver';
import { Client, NoticeCase, NoticeIssue, DocumentItem, FirmSettings, ReconciliationItem } from '../types';

export function generateClientEmail(
  type: 'REQUEST' | 'FOLLOWUP',
  client: Client,
  noticeCase: NoticeCase,
  issues: NoticeIssue[],
  pendingDocs: DocumentItem[],
  targetDate = noticeCase.replyDeadline || 'the earliest'
): { subject: string; body: string; mailtoUrl: string } {
  if (type === 'REQUEST') {
    const subject = `URGENT: GST Notice ${noticeCase.formType} (${noticeCase.noticeNumber}) - Data and Documents Required`;
    const docList = pendingDocs.length > 0
      ? pendingDocs.map((d, i) => `${i + 1}. ${d.docName} [Period: ${d.period || noticeCase.period}] - Status: ${d.status}\n   Note: ${d.remarks || 'Please share Excel/PDF copy'}`).join('\n\n')
      : '1. Monthly GSTR-2B Excel Reports\n2. Purchase and Sales Registers with HSN\n3. Bank payment statements and Transport Lorry Receipts';

    const issueList = issues.map((iss, i) => `${i + 1}. ${iss.title} (Disputed Tax: Rs ${iss.taxAmount.toLocaleString('en-IN')})\n   - Department Allegation: ${iss.allegation}\n   - Questions for you: ${iss.clientQuestions}`).join('\n\n');

    const body = `Dear ${client.legalName},\n\n` +
      `We have received and analyzed the GST Notice (${noticeCase.formType}) issued by ${noticeCase.issuingAuthority} for the period ${noticeCase.period} (FY ${noticeCase.financialYear}).\n\n` +
      `NOTICE REFERENCE SUMMARY:\n` +
      `- Notice No: ${noticeCase.noticeNumber}\n` +
      `- Notice Date: ${noticeCase.noticeDate}\n` +
      `- Reply Deadline: ${noticeCase.replyDeadline}\n` +
      `- Total Disputed Demand: Rs ${noticeCase.totalDemand.toLocaleString('en-IN')} (Tax: Rs ${noticeCase.principalTax.toLocaleString('en-IN')}, Interest: Rs ${noticeCase.interest.toLocaleString('en-IN')}, Penalty: Rs ${noticeCase.penalty.toLocaleString('en-IN')})\n\n` +
      `KEY ISSUES RAISED BY THE DEPARTMENT:\n` +
      `${issueList}\n\n` +
      `DOCUMENTS AND DATA REQUIRED FROM YOUR SIDE BY ${targetDate}:\n` +
      `${docList}\n\n` +
      `Kindly furnish the above documents and clarifications at the earliest to enable us to finalize and submit a comprehensive legal reply before the statutory deadline of ${noticeCase.replyDeadline}.\n\n` +
      `Best regards,\n` +
      `Tax Advisory and GST Practice Team`;

    const mailtoUrl = `mailto:${client.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    return { subject, body, mailtoUrl };
  } else {
    const subject = `REMINDER: Pending Documents for GST Notice ${noticeCase.noticeNumber} (Reply Deadline: ${noticeCase.replyDeadline})`;
    const docList = pendingDocs.filter((d) => d.status !== 'Completed' && d.status !== 'Received').map((d, i) => `${i + 1}. ${d.docName} (${d.period || noticeCase.period}) - Current Status: ${d.status}`).join('\n');

    const body = `Dear ${client.legalName},\n\n` +
      `This is a gentle follow-up reminder regarding the pending documents required for preparing our response to GST Notice ${noticeCase.formType} (${noticeCase.noticeNumber}).\n\n` +
      `STATUTORY REPLY DEADLINE: ${noticeCase.replyDeadline}\n\n` +
      `PENDING DOCUMENTS LIST:\n` +
      `${docList}\n\n` +
      `To ensure timely submission on the GST portal and avoid any ex-parte assessment or penal consequences, please send the pending files immediately.\n\n` +
      `Warm regards,\n` +
      `CA Office`;

    const mailtoUrl = `mailto:${client.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    return { subject, body, mailtoUrl };
  }
}

export async function generateWordReplyDocument(
  client: Client,
  noticeCase: NoticeCase,
  issues: NoticeIssue[],
  reconciliations: ReconciliationItem[],
  firm: FirmSettings
): Promise<void> {
  const reconLine = (issueNumber: number): Paragraph[] => {
    const recs = reconciliations.filter((r) => r.issueNumber === issueNumber && (r.portalValue > 0 || r.status !== 'MISSING_DATA'));
    if (recs.length === 0) return [];
    return recs.map((r) =>
      new Paragraph({
        children: [
          new TextRun({ text: 'Reconciliation: ', bold: true }),
          new TextRun({
            text: `${r.reconType} — notice/demand Rs ${r.noticeValue.toLocaleString('en-IN')}, ` +
              `as per return Rs ${r.portalValue.toLocaleString('en-IN')}, as per books Rs ${r.booksValue.toLocaleString('en-IN')}, ` +
              `variance Rs ${r.variance.toLocaleString('en-IN')} (${r.status}). ${r.varianceReason}`,
          }),
        ],
        spacing: { after: 80 },
      }),
    );
  };

  const issueParagraphs = issues.flatMap((issue, idx) => [
    new Paragraph({
      children: [
        new TextRun({ text: `2.${idx + 1} Issue ${issue.issueNumber}: ${issue.title} (Disputed Tax: Rs ${issue.taxAmount.toLocaleString('en-IN')})`, bold: true }),
      ],
      spacing: { before: 150, after: 80 },
    }),
    new Paragraph({
      children: [
        new TextRun({ text: 'Department Allegation: ', bold: true }),
        new TextRun({ text: issue.allegation }),
      ],
      spacing: { after: 80 },
    }),
    ...reconLine(issue.issueNumber),
    new Paragraph({
      children: [
        new TextRun({ text: 'Factual and Legal Submissions: ', bold: true }),
        new TextRun({ text: issue.defensePoints }),
      ],
      spacing: { after: 80 },
    }),
    new Paragraph({
      children: [
        new TextRun({ text: 'Statutory Reliance and Judicial Precedents: ', bold: true }),
        new TextRun({ text: issue.legalPosition }),
      ],
      spacing: { after: 150 },
    }),
  ]);

  const reconciledRows = reconciliations.filter((r) => r.status !== 'MISSING_DATA');
  const reconSection: Paragraph[] = reconciledRows.length
    ? [
        new Paragraph({ text: '2A. RECONCILIATION OF FIGURES', heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 } }),
        ...reconciledRows.map((r) =>
          new Paragraph({
            children: [
              new TextRun({ text: `• ${r.reconType}: `, bold: true }),
              new TextRun({
                text: `demand Rs ${r.noticeValue.toLocaleString('en-IN')} vs return Rs ${r.portalValue.toLocaleString('en-IN')} vs books Rs ${r.booksValue.toLocaleString('en-IN')} — variance Rs ${r.variance.toLocaleString('en-IN')} (${r.status}). ${r.varianceReason}`,
              }),
            ],
            spacing: { after: 80 },
          }),
        ),
      ]
    : [];

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: [
          new Paragraph({
            text: firm.letterheadHeader || firm.caFirmName.toUpperCase(),
            heading: HeadingLevel.HEADING_1,
            alignment: AlignmentType.CENTER,
            spacing: { after: 100 },
          }),
          new Paragraph({
            text: `${firm.firmAddress} | Email: ${firm.contactEmail} | Phone: ${firm.contactPhone}`,
            alignment: AlignmentType.CENTER,
            spacing: { after: 300 },
          }),
          new Paragraph({
            text: `Date: ${new Date().toLocaleDateString('en-IN')}`,
            alignment: AlignmentType.RIGHT,
            spacing: { after: 200 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: 'To,\n', bold: true }),
              new TextRun({ text: `${noticeCase.issuingAuthority}\n` }),
              new TextRun({ text: 'Goods and Services Tax Department\n' }),
            ],
            spacing: { after: 200 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: 'SUBJECT: ', bold: true }),
              new TextRun({
                text: `WRITTEN SUBMISSION / REPLY TO SHOW CAUSE NOTICE ${noticeCase.formType} (REF NO: ${noticeCase.noticeNumber} DATED ${noticeCase.noticeDate}) FOR THE FINANCIAL YEAR ${noticeCase.financialYear}.`,
                bold: true,
                underline: {},
              }),
            ],
            spacing: { after: 200 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: 'Taxpayer Name: ', bold: true }),
              new TextRun({ text: `${client.legalName} (${client.tradeName})\n` }),
              new TextRun({ text: 'GSTIN: ', bold: true }),
              new TextRun({ text: `${client.gstin}\n` }),
              new TextRun({ text: 'Principal Place of Business: ', bold: true }),
              new TextRun({ text: `${client.address || 'As per GST Registration Records'}\n` }),
            ],
            spacing: { after: 300 },
          }),
          new Paragraph({
            text: 'Respected Sir / Madam,',
            spacing: { after: 150 },
          }),
          new Paragraph({
            text: `The taxpayer M/s ${client.legalName} ("the Assessee") hereby submits this preliminary reply and detailed factual submissions against the impugned Notice ${noticeCase.formType} Ref No. ${noticeCase.noticeNumber} issued under ${noticeCase.sectionsMentioned}.`,
            spacing: { after: 200 },
          }),
          new Paragraph({
            text: '1. PRELIMINARY SUBMISSIONS AND BRIEF BACKGROUND',
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 200, after: 100 },
          }),
          new Paragraph({
            text: '1.1 The Assessee is a law-abiding taxpayer holding valid GST registration and has diligently discharged all outward tax liabilities and filed statutory monthly returns within statutory time limits.',
            spacing: { after: 150 },
          }),
          new Paragraph({
            text: `1.2 The total proposed demand of Rs ${noticeCase.totalDemand.toLocaleString('en-IN')} is devoid of merits and founded on mechanical system reconciliations without considering actual transactional facts.`,
            spacing: { after: 200 },
          }),
          new Paragraph({
            text: '2. ISSUE-WISE POINTED SUBMISSIONS ON MERITS',
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 200, after: 100 },
          }),
          ...issueParagraphs,
          ...reconSection,
          new Paragraph({
            text: '3. PRAYER AND RELIEF SOUGHT',
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 200, after: 100 },
          }),
          new Paragraph({
            text: 'In view of the detailed submissions, reconciliations, and documentary evidences placed on record, the Assessee most respectfully prays that the Learned Authority be pleased to accept this written explanation and drop the proposed demand of Tax, Interest, and Penalty in its entirety.',
            spacing: { after: 300 },
          }),
          new Paragraph({
            text: 'VERIFICATION',
            heading: HeadingLevel.HEADING_3,
            alignment: AlignmentType.CENTER,
            spacing: { before: 200, after: 100 },
          }),
          new Paragraph({
            text: `I, the Authorized Representative of M/s ${client.legalName}, do hereby verify that the contents of paragraphs 1 to 3 above are true and correct to the best of my knowledge and records.`,
            spacing: { after: 300 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: `For ${client.legalName}\n\n\n\n`, bold: true }),
              new TextRun({ text: 'Authorized Signatory / Managing Director\n' }),
            ],
            alignment: AlignmentType.RIGHT,
          }),
        ],
      },
    ],
  });

  const blob = await Packer.toBlob(doc);
  const filename = `GST_Reply_${noticeCase.formType}_${client.gstin}_${noticeCase.noticeNumber}.docx`;
  saveAs(blob, filename);
}
