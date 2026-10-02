/**
 * Generates a Sample Advisory "Scope of Work Mandate" docx, replicating the
 * approved Example Co (Example Industries Private Limited) layout, from a
 * content JSON file.
 *
 * Usage: node generate_mandate.js <content.json> <output.docx>
 */
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageBreak, PageNumber, HeightRule,
} = require("docx");

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  console.error("Usage: node generate_mandate.js <content.json> <output.docx>");
  process.exit(1);
}
const DATA = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const ASSETS = path.join(__dirname, "..", "assets");

// ---------- validation of mandatory inputs ----------
const get = (p) => p.split(".").reduce((o, k) => (o ? o[k] : undefined), DATA);
const REQUIRED = [
  "client.legal_name", "client.short_name", "client.registered_office",
  "background.business_description", "engagement.retainer_fee",
  "engagement.date_display", "signature.client_name",
  "signature.client_designation", "signature.advisor_name",
  "signature.advisor_designation",
];
const missing = REQUIRED.filter((k) => !get(k));
if (missing.length) {
  console.error("Missing mandatory fields: " + missing.join(", "));
  process.exit(1);
}

// ---------- palette + type sampled from the approved mandate ----------
const NAVY = "0B1F3A";
const NAVY_SUB = "1F3864";
const GOLD_TEXT = "9C7A2E";
const GOLD_RULE = "B8985A";
const CREAM = "F2EFE7";
const GRAY_ITALIC = "7F7F7F";
const FONT = "Book Antiqua";
const SIZE = 21; // 10.5pt in half points
const SIZE_SMALL = 16; // 8pt page number text

const C = DATA.client;
const E = DATA.engagement;
const S = DATA.signature;
const SHORT = C.short_name;
const LEGAL = C.legal_name;
const BRAND = C.brand_name || "";
const PLACE = S.place || "Mumbai";

const TERM_WORD = (E.term_years_words || "three").toLowerCase();
const TERM_NUM = E.term_years_number || 3;
const TERM_WORD_CAP = TERM_WORD.charAt(0).toUpperCase() + TERM_WORD.slice(1);

const clientLine = BRAND ? `${LEGAL}, operating under the brand ${BRAND}` : LEGAL;
const preparedFor = BRAND && BRAND !== LEGAL ? `${LEGAL} (${BRAND})` : LEGAL;
const Q = (s) => `\u201C${s}\u201D`;
const POSS = `${SHORT}\u2019s`;

function sub(str) {
  if (!str) return "";
  return String(str)
    .replace(/\{CLIENT_SHORT\}/g, SHORT)
    .replace(/\{CLIENT_LEGAL\}/g, LEGAL)
    .replace(/'/g, "\u2019");
}

function run(text, opts = {}) {
  return new TextRun({ text: sub(text), font: FONT, size: SIZE, ...opts });
}

// splits ordinals like 3rd / 16th so the suffix renders as superscript
function ordinalRuns(text, opts = {}) {
  const parts = sub(text).split(/(\d+)(st|nd|rd|th)\b/);
  const out = [];
  for (let i = 0; i < parts.length; i++) {
    if (!parts[i]) continue;
    const sup = i % 3 === 2;
    out.push(new TextRun({ text: parts[i], font: FONT, size: SIZE, superScript: sup, ...opts }));
  }
  return out;
}

function bodyPara(text, opts = {}, after = 200) {
  return new Paragraph({
    spacing: { after, line: 264 },
    alignment: AlignmentType.JUSTIFIED,
    children: [run(text, opts)],
  });
}

function bulletPara(text) {
  return new Paragraph({
    spacing: { after: 100, line: 264 },
    alignment: AlignmentType.JUSTIFIED,
    numbering: { reference: "bullets", level: 0 },
    children: [run(text)],
  });
}

function sectionHeading(number, title) {
  return new Paragraph({
    spacing: { before: 320, after: 200 },
    keepNext: true,
    border: { bottom: { color: GOLD_RULE, space: 4, style: BorderStyle.SINGLE, size: 8 } },
    children: [run(`${number}.  ${title}`, { bold: true, color: NAVY })],
  });
}

function subHeadingPara(text) {
  return new Paragraph({
    spacing: { before: 180, after: 80 },
    keepNext: true,
    children: [run(text, { bold: true, color: NAVY_SUB })],
  });
}

const NONE = { style: BorderStyle.NONE, size: 0, color: "auto" };
const noBorders = { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE };
function thin(color = "000000", size = 4) { return { style: BorderStyle.SINGLE, size, color }; }
function gridBorders(color = "000000") {
  const b = thin(color);
  return { top: b, bottom: b, left: b, right: b, insideHorizontal: b, insideVertical: b };
}

// navy full width bar with white bold text, used for scope pillars A to F.
// A shaded paragraph (not a table) so keepNext reliably holds it to its bullet.
function pillarBar(letter, title) {
  return new Paragraph({
    keepNext: true,
    keepLines: true,
    spacing: { before: 60, after: 60 },
    indent: { left: 60, right: 60 },
    shading: { type: ShadingType.CLEAR, fill: NAVY, color: "auto" },
    border: {
      top: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 1 },
      bottom: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 1 },
      left: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 },
      right: { style: BorderStyle.SINGLE, size: 6, color: NAVY, space: 4 },
    },
    children: [run(`${letter}. ${title}`, { bold: true, color: "FFFFFF" })],
  });
}

// two column label/value table with cream label cells
function infoTable(rows, superscriptOrdinals = true) {
  return new Table({
    width: { size: 9700, type: WidthType.DXA },
    columnWidths: [2800, 6900],
    borders: gridBorders(),
    rows: rows.map(([label, value]) => new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: 2800, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: CREAM, color: "auto" },
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 90, bottom: 90, left: 120, right: 120 },
          children: [new Paragraph({ children: [run(label, { bold: true, color: NAVY })] })],
        }),
        new TableCell({
          width: { size: 6900, type: WidthType.DXA },
          verticalAlign: VerticalAlign.CENTER,
          margins: { top: 90, bottom: 90, left: 120, right: 120 },
          children: [new Paragraph({ alignment: AlignmentType.JUSTIFIED, children: superscriptOrdinals ? ordinalRuns(value) : [run(value)] })],
        }),
      ],
    })),
  });
}

// numbered box: navy marker cell plus cream body cell (stages and phases)
function stageBox(marker, title, description) {
  return new Table({
    width: { size: 9700, type: WidthType.DXA },
    columnWidths: [1000, 8700],
    borders: gridBorders("404040"),
    rows: [new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: 1000, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: NAVY, color: "auto" },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(String(marker), { bold: true, color: "FFFFFF" })] })],
        }),
        new TableCell({
          width: { size: 8700, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: CREAM, color: "auto" },
          margins: { top: 140, bottom: 140, left: 150, right: 150 },
          children: [
            new Paragraph({ children: [run(title, { bold: true, color: NAVY })] }),
            new Paragraph({ alignment: AlignmentType.JUSTIFIED, children: [run(description)] }),
          ],
        }),
      ],
    })],
  });
}

function spacer(h = 200) { return new Paragraph({ spacing: { after: h }, children: [] }); }

// ---------- header / footer ----------
const headerLogo = fs.readFileSync(path.join(ASSETS, "logo.png"));
const footerStrip = fs.readFileSync(path.join(ASSETS, "footer_strip.png"));

const header = new Header({
  children: [new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new ImageRun({ data: headerLogo, transformation: { width: 90, height: 87 }, type: "png" })],
  })],
});

const footer = new Footer({
  children: [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new ImageRun({ data: footerStrip, transformation: { width: 540, height: 62 }, type: "png" })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 40 },
      children: [
        new TextRun({ text: "Page ", font: FONT, size: SIZE_SMALL, color: "808080" }),
        new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: SIZE_SMALL, color: "808080" }),
        new TextRun({ text: " of ", font: FONT, size: SIZE_SMALL, color: "808080" }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: SIZE_SMALL, color: "808080" }),
      ],
    }),
  ],
});

// ---------- page 1 : cover ----------
const cover = [
  spacer(300),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
    children: [run("STRICTLY PRIVATE AND CONFIDENTIAL", { bold: true, color: GOLD_TEXT, size: SIZE - 2 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 480 },
    children: [run("SCOPE OF WORK MANDATE", { bold: true, color: NAVY, size: SIZE + 13 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 40 },
    children: [run(E.title_line1 || "Strategic Advisory and Growth Partnership", { bold: true, color: NAVY_SUB, size: SIZE + 7 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 160 },
    children: [run(`Prepared for ${preparedFor}`, { italics: true, color: GRAY_ITALIC, size: SIZE + 1 })],
  }),
  infoTable([
    ["Advisor", "Sample Advisory Private Limited"],
    ["Client", clientLine],
    ["Nature of Engagement", E.nature || "Strategic Advisory and Growth Partner services, covering business advisory, fund raising and IPO readiness, on a retainer basis"],
    ["Billing Cycle", "Monthly retainer, plus a success fee on funds raised"],
    ["Fee", `${E.retainer_fee} plus applicable taxes, per month, together with a success fee as set out in Section 11`],
    ["Date", E.date_display],
  ], false),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- 1 : preamble ----------
const clientIntro = BRAND
  ? `${LEGAL}, operating under the brand ${BRAND}, having its registered office at ${C.registered_office} (${Q(SHORT)}, ${Q("the Company")}).`
  : `${LEGAL}, having its registered office at ${C.registered_office} (${Q(SHORT)}, ${Q("the Company")}).`;

const preamble = [
  sectionHeading(1, "Preamble"),
  bodyPara(`This Scope of Work Mandate (${Q("Mandate")}) is entered into between Sample Advisory Private Limited, a Mumbai based advisory firm, having its registered office at Registered office address, City 400001 (${Q("Sample Advisory")}, ${Q("the Advisor")}), and ${clientIntro}`),
  bodyPara(`This document sets out the objective, scope, engagement structure, process and terms under which Sample Advisory will act as Strategic Advisor and Growth Partner to ${SHORT}. This Mandate, once signed by both parties, constitutes the governing document for the engagement, with no separate engagement letter to follow.`),
];

// ---------- 2 : background and objective ----------
const bizDesc = sub(DATA.background.business_description).trim();
const background = [
  sectionHeading(2, "Background and Objective"),
  bodyPara(`${bizDesc} As the Company pursues its growth plans and expansion strategy, ${SHORT} wishes to bring on a dedicated Strategic Advisor and Growth Partner who can work closely with the promoters across business, financial and capital raising priorities.`),
  bodyPara("The objective of this Mandate is threefold:", {}, 100),
  bulletPara(`Support ${POSS} growth plans through structured business advisory, strategic input and access to Sample Advisory\u2019s network of investors, lenders and industry participants.`),
  bulletPara(`Assist the Company in raising growth capital through the most suitable structure, whether equity, strategic investment, debt, and any other route appropriate to ${POSS} requirements.`),
  bulletPara(`Build readiness across business, financial and regulatory dimensions so that ${SHORT} is well positioned to pursue a future listing, should the Company and its promoters choose to do so.`),
  bodyPara(`Sample Advisory will act as ${POSS} Strategic Advisor and Growth Partner on an exclusive basis for the scope set out in this Mandate, functioning as a close, ongoing partner to the promoters and management team across strategy, fund raising and growth.`),
];

// ---------- 3 : scope of services ----------
const PILLAR_TITLES = [
  ["A", "Business Strategy and Growth Advisory"],
  ["B", "Fund Raising and Investor Connect"],
  ["C", "Capital and Business Structuring"],
  ["D", "Governance and IPO Readiness"],
  ["E", "Transaction Coordination and Documentation"],
  ["F", "Institutional and Board Support"],
];
const DEFAULT_BULLETS = [
  `Understanding ${POSS} business model, industry positioning and expansion plans, and providing ongoing strategic input to the promoters.`,
  `Identifying and facilitating introductions with investors, lenders and strategic counterparties suited to ${POSS} funding requirements.`,
  `Advisory support on the most suitable capital structure and transaction structure for ${POSS} growth and fund raising plans.`,
  `A preliminary review of governance, secretarial and financial readiness, and advisory support in preparing ${SHORT} toward listing readiness.`,
  "Coordinating with legal counsel, statutory auditors and, once appointed, a SEBI registered Lead Manager, together with preparing investor facing materials.",
  "Periodic strategic updates to the promoters and board, and general availability as a strategic sounding board through the engagement.",
];
const overrides = DATA.pillar_bullets || [];

const scope = [
  sectionHeading(3, "Scope of Services"),
  bodyPara(`As Strategic Advisor and Growth Partner, Sample Advisory\u2019s mandate spans business strategy, fund raising and listing readiness together. The engagement will cover the following broad pillars, with the relative emphasis across each reviewed periodically and adjusted based on ${POSS} evolving priorities, as agreed between the parties.`),
];
PILLAR_TITLES.forEach(([letter, title], i) => {
  scope.push(pillarBar(letter, title));
  scope.push(bulletPara(overrides[i] ? sub(overrides[i]) : DEFAULT_BULLETS[i]));
});
scope.push(bodyPara(`The precise activities within each pillar, along with priorities and sequencing, will be jointly determined with ${POSS} promoters as the engagement progresses. Sample Advisory is not registered as a Merchant Banker under applicable SEBI regulations, and accordingly will not act as a lead manager, underwriter, and any other capacity requiring such registration. Services under this Mandate are limited to advisory, coordination and facilitation, with all regulated filings undertaken by the Company and its appointed, duly registered intermediaries.`));

// ---------- 4 : strategic approach ----------
const STAGES = [
  ["Diagnose", `Understand ${POSS} current business, financial position and readiness gaps through a structured internal review.`],
  ["Stabilise", "Bring order, accuracy and reliability to core business and financial information, closing known gaps ahead of investor engagement."],
  ["Systemise", `Institutionalise processes, governance and documentation so that ${SHORT} presents a consistent, credible profile to investors and lenders.`],
  ["Scale", `Support ${SHORT} in raising growth capital and building toward listing readiness, in step with the Company\u2019s expansion plans.`],
];
const approach = [
  sectionHeading(4, "Strategic Approach"),
  bodyPara(`Sample Advisory\u2019s engagement with ${SHORT} will follow a four stage strategic approach, moving the Company from a reactive posture to a protective, scalable one:`),
];
STAGES.forEach(([t, d], i) => { approach.push(stageBox(i + 1, t, d)); approach.push(spacer(200)); });

// ---------- 5 : engagement process ----------
const PHASES = [
  ["I", "Discovery and Alignment", "Understand the business, its operating model and promoter priorities, and design a detailed roadmap for the engagement."],
  ["II", "Control and Clarity", `Bring order, process, speed and reliability to business and financial information, so that ${POSS} numbers can be trusted by investors and lenders.`],
  ["III", "Intelligence and Insight", "Turn business and financial data into a credible investor narrative, giving management clear visibility into fund raising and readiness progress."],
  ["IV", "Scalability and Enablement", `Build an organisation and capital structure designed to scale with ${POSS} growth plans, rather than constrain them.`],
];
const processSec = [
  sectionHeading(5, "Engagement Process"),
  bodyPara("The mandate will be delivered through four connected phases of work, each building on the previous:"),
];
PHASES.forEach(([m, t, d]) => { processSec.push(stageBox(m, t, d)); processSec.push(spacer(200)); });

// ---------- 6 : engagement model ----------
const model = [
  sectionHeading(6, "Engagement Model and Structure"),
  bodyPara(`This Mandate is structured as an exclusive, retainer based Strategic Advisory and Growth Partner engagement, reflecting the close, ongoing nature of support ${SHORT} requires across business advisory, fund raising and readiness.`),
  infoTable([
    ["Engagement Type", "Exclusive, retainer based Strategic Advisory and Growth Partner mandate"],
    ["Duration", `${TERM_WORD_CAP} years (${TERM_NUM}) from the effective date, extendable by mutual written consent`],
    ["Exclusivity", "Sample Advisory is engaged on an exclusive basis for the scope set out in this Mandate during the Term"],
    ["Time Commitment", "An agreed proportion of time each month, as set out in this Mandate"],
    ["Billing Cycle", "Monthly retainer, payable in advance i.e. before 3rd of each month, plus a success fee on funds raised (as applicable) as set out in Section 11"],
    ["Review Cadence", `Scope and priorities to be reviewed periodically between Sample Advisory and ${POSS} promoters`],
  ]),
  spacer(120),
  bodyPara(`During the Term, ${SHORT} agrees to route discussions with investors, lenders and strategic counterparties introduced, identified and substantially connected by Sample Advisory through Sample Advisory, so that the Company and the Advisor can work as genuine partners through to a successful outcome. The decision to accept and proceed with any investor, lender and proposal introduced by Sample Advisory remains solely with ${POSS} promoters, at their sole discretion.`),
];

// ---------- 7 : deliverables ----------
const deliverables = [
  sectionHeading(7, "Deliverables and Reporting Cadence"),
  bulletPara("Periodic promoter and board level review meetings, at a frequency mutually agreed."),
  bulletPara("A monthly summary note covering business, fund raising and readiness progress."),
  bulletPara("Quarterly progress review across the scope areas set out in this Mandate."),
  bulletPara("Ad hoc analysis and support as required for investor meetings, negotiations and readiness decisions."),
];

// ---------- 8 : roles ----------
const roles = [
  sectionHeading(8, "Roles and Responsibilities"),
  subHeadingPara("Sample Advisory"),
  bulletPara("Provide a designated engagement lead supported by the Sample Advisory team, under the oversight of a Director."),
  bulletPara("Deliver the scope of services set out in this Mandate with professional diligence and confidentiality."),
  bulletPara(`Use its best efforts to secure the most favourable terms achievable for ${SHORT} in any transaction facilitated under this Mandate, while recognising that no particular outcome, valuation and investor commitment can be assured.`),
  subHeadingPara(SHORT),
  bulletPara("Provide timely access to business and financial records, systems and personnel required for the engagement."),
  bulletPara("Designate a point of contact within the Company to coordinate with the Sample Advisory engagement team."),
  bulletPara("Bear statutory costs, regulatory charges, legal expenses and other transaction related expenses directly and separately from the fees payable under Section 11."),
];

// ---------- 9 : confidentiality ----------
const confidentiality = [
  sectionHeading(9, "Confidentiality"),
  bodyPara("Both parties agree to treat all business, financial and investor related information exchanged in the course of this engagement as confidential, and to use such information solely for the purpose of this Mandate. This obligation will survive for two years beyond the completion, suspension and termination of the engagement."),
];

// ---------- 10 : term and termination ----------
const term = [
  sectionHeading(10, "Term and Termination"),
  subHeadingPara("Term"),
  bodyPara(`This Mandate shall be in force from the date of acceptance by both parties and continues for ${TERM_WORD} years from that date, unless extended by mutual written consent, and until brought to a close in accordance with this Section.`),
  subHeadingPara("Termination for Convenience"),
  bodyPara("Either party may bring the engagement to a close prior to expiry of the Term by providing thirty days written notice to the other party, together with a genuine reason for the closure. During the notice period, Sample Advisory will continue to deliver the agreed scope of services and will support an orderly transition of responsibilities."),
  subHeadingPara("Termination for Cause"),
  bodyPara("Either party may terminate this Mandate with immediate effect, by written notice, if the other party commits a material breach of its obligations under this Mandate and does not remedy that breach within fifteen days of being notified in writing, and equally if the other party undergoes insolvency, winding up, and any comparable event affecting its ability to continue the engagement."),
  subHeadingPara("Tail Period"),
  bodyPara("Where this Mandate is terminated and expires, any transaction that Sample Advisory originated and substantially progressed during the Term will continue to be covered under the success fee arrangement set out in Section 11, provided such transaction is completed within twelve months of the date of such termination and expiry."),
  subHeadingPara("Effect of Termination"),
  bulletPara("Sample Advisory will be entitled to the retainer fee for the month in which termination takes effect, computed on a pro rata basis up to the effective date of termination."),
  bulletPara(`${SHORT} will settle all outstanding invoices within fifteen days of the effective date of termination.`),
  bulletPara("Sample Advisory will hand over all work in progress, reports and Company records prepared during the engagement, in a reasonably usable format."),
  bulletPara("Each party will return, and cease using, any confidential information and materials belonging to the other party, save for copies required to be retained for legal and regulatory record keeping purposes."),
  bulletPara("The confidentiality obligations under Section 9, together with the Tail Period arrangement above, will continue to apply beyond the end of this Mandate."),
];

// ---------- 11 : fees and billing ----------
const pct = (E.success_fee_pct || "").trim();
const feeTail = `The success fee becomes payable upon successful completion of the relevant transaction and receipt of the corresponding funds by ${SHORT}, within five business days of such receipt. Where a transaction comprises multiple tranches, the success fee will be computed and become payable in respect of each tranche as funds are received.`;
const successFeeText = pct
  ? `In consideration of the fund raising services rendered, ${SHORT} will pay Sample Advisory a success fee of ${pct} of the total funds raised through any transaction sourced, facilitated and substantially assisted by Sample Advisory. ${feeTail}`
  : `In consideration of the fund raising services rendered, ${SHORT} will pay Sample Advisory a success fee equivalent to certain percentage of the total funds raised through any transaction sourced, facilitated and substantially assisted by Sample Advisory, of which the percentage of Success Fees shall be decided mutually as and when applicable. ${feeTail}`;

const fees = [
  sectionHeading(11, "Fees and Billing"),
  subHeadingPara("Retainer Fee"),
  bodyPara(`${SHORT} will pay Sample Advisory a monthly retainer fee of ${E.retainer_fee} plus applicable taxes, payable in advance each calendar month, in consideration of the ongoing business advisory, fund raising and readiness services rendered under this Mandate.`),
  subHeadingPara("Success Fee"),
  bodyPara(successFeeText),
  subHeadingPara("Statutory Costs and Expenses"),
  bodyPara(`All statutory costs, regulatory charges, legal expenses, due diligence expenses, valuation expenses and other transaction related expenses will be borne directly by ${SHORT}, separately from the fees set out above. Reasonable out of pocket expenses incurred by Sample Advisory in performing the services, including travel and documentation, will be reimbursed by ${SHORT} on an actual basis.`),
  bodyPara("This fee structure may be revised by mutual agreement between the parties, recorded in writing, as the scope of the engagement evolves."),
];

// ---------- 12 : governing law ----------
const law = [
  sectionHeading(12, "Governing Law and Dispute Resolution"),
  bodyPara("This Mandate is governed by the laws of India. Any dispute arising under this Mandate will first be addressed through good faith discussion between the parties, and, failing an amicable resolution, will be referred to and finally resolved through arbitration under the Arbitration and Conciliation Act, 1996, by a sole arbitrator mutually appointed by the parties. The seat and venue of arbitration will be Mumbai, Maharashtra, with proceedings conducted in English."),
];

// ---------- 13 : acceptance ----------
function sigCell(children, valign) {
  return new TableCell({
    width: { size: 4850, type: WidthType.DXA },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    verticalAlign: valign || VerticalAlign.CENTER,
    children,
  });
}
function sigRow(left, right, opts = {}) {
  const rowOpts = { cantSplit: true, children: [sigCell(left, opts.valign), sigCell(right, opts.valign)] };
  if (opts.height) rowOpts.height = { value: opts.height, rule: HeightRule.ATLEAST };
  return new TableRow(rowOpts);
}
const P = (runs, align) => new Paragraph({ alignment: align || AlignmentType.LEFT, children: runs });
const clientUpper = (BRAND && BRAND !== LEGAL ? `${LEGAL} (${BRAND})` : LEGAL).toUpperCase();

const acceptance = [
  sectionHeading(13, "Acceptance"),
  bodyPara(`This Mandate sets out the complete understanding of Sample Advisory Private Limited and ${LEGAL} regarding the scope, structure and fee of the Strategic Advisory and Growth Partner engagement described above. Upon signature by both parties below, this Mandate becomes effective and binding, with no separate engagement letter required.`),
  new Table({
    width: { size: 9700, type: WidthType.DXA },
    columnWidths: [4850, 4850],
    borders: gridBorders(),
    rows: [
      sigRow([P([run("For the Company", { bold: true })])], [P([run("For the Advisor", { bold: true })])]),
      sigRow([P([run(clientUpper, { bold: true })], AlignmentType.JUSTIFIED)], [P([run("ADVISOR CAPITAL ADVISORS PRIVATE LIMITED", { bold: true })], AlignmentType.JUSTIFIED)]),
      sigRow([P([run("Signature: ______________________")])], [P([run("Signature: ______________________")])], { height: 2600, valign: VerticalAlign.BOTTOM }),
      sigRow([P([run(`Name: ${S.client_name}`)])], [P([run(`Name: ${S.advisor_name}`)])]),
      sigRow([P([run(`Designation: ${S.client_designation}`)])], [P([run(`Designation: ${S.advisor_designation}`)])]),
      sigRow([P(ordinalRuns(`Date: ${E.date_display}`))], [P(ordinalRuns(`Date: ${E.date_display}`))]),
      sigRow([P([run(`Place: ${PLACE}`)])], [P([run(`Place: ${PLACE}`)])]),
    ],
  }),
];

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: SIZE } } } },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: "bullet", text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 220 } } } }],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 }, // A4
        margin: { top: 1900, bottom: 1700, left: 1100, right: 1100, header: 500, footer: 300 },
      },
    },
    headers: { default: header },
    footers: { default: footer },
    children: [
      ...cover, ...preamble, ...background, ...scope, ...approach, ...processSec,
      ...model, ...deliverables, ...roles, ...confidentiality, ...term, ...fees,
      ...law, ...acceptance,
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outputPath, buf);
  console.log("Written:", outputPath);
});
