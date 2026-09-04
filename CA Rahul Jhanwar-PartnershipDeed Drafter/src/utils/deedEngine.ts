import { DeedFormData, IndustryPreset } from '../types';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { 
  constructSupplementaryDeedBody, 
  constructDissolutionDeedBody, 
  DEFAULT_SUPPLEMENTARY_CONFIG, 
  DEFAULT_DISSOLUTION_CONFIG,
  getSupplementaryClauseList,
  getDissolutionClauseList 
} from './supplementaryAndDissolutionEngine';

export { 
  constructSupplementaryDeedBody, 
  constructDissolutionDeedBody, 
  DEFAULT_SUPPLEMENTARY_CONFIG, 
  DEFAULT_DISSOLUTION_CONFIG 
};

export function formatFormalDate(isoDateString: string): string {
  if (!isoDateString) return '';
  const parts = isoDateString.split('-');
  if (parts.length !== 3) return isoDateString;

  const day = parseInt(parts[2], 10);
  const year = parts[0];
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const monthName = months[parseInt(parts[1], 10) - 1] || '';

  let suffix = 'th';
  if (day % 10 === 1 && day !== 11) suffix = 'st';
  else if (day % 10 === 2 && day !== 12) suffix = 'nd';
  else if (day % 10 === 3 && day !== 13) suffix = 'rd';

  return `${day}${suffix} ${monthName} ${year}`;
}

export function calculateAge(dobString: string, baseDateString?: string): string {
  if (!dobString) return '';
  const dob = new Date(dobString);
  if (isNaN(dob.getTime())) return '';
  const baseDate = baseDateString ? new Date(baseDateString) : new Date();
  let age = baseDate.getFullYear() - dob.getFullYear();
  const m = baseDate.getMonth() - dob.getMonth();
  if (m < 0 || (m === 0 && baseDate.getDate() < dob.getDate())) {
    age--;
  }
  return age >= 0 ? age.toString() : '0';
}

export function getOrdinal(n: number): string {
  const ords = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH', 'NINTH', 'TENTH'];
  return ords[n - 1] || `${n}TH`;
}

export const INDUSTRY_PRESETS: IndustryPreset[] = [
  {
    id: 'craft_gifts',
    label: 'Art, Craft, Marriage Packing & Gifts',
    iconName: 'Gift',
    firmName: 'M/S. CREATIVE CRAFTS & GIFTING STUDIO',
    businessIdea: 'CREATIVE ART AND CRAFT, HANDMADE PRODUCTS, PACKING ITEMS, MARRIAGE TROUSSEAU PACKING, UNIQUE GIFT ITEMS',
    firmObjects: 'The business of the partnership shall be to carry on in India and abroad the business of designing, handcrafting, manufacturing, curating, assembling, packing, customization, wholesale and retail trading, importing, exporting, distributing, e-commerce retailing, and marketing of all kinds of creative art and craft items, handmade decorative products, novelty gifts, customized wedding and marriage trousseau packaging items, corporate gift hampers, festive packaging, paper and wooden craft goods, ribbons, embellishments, raw craft supplies, and allied materials. The firm shall also provide event packaging consultancy, personalized gift assembly services, creative design workshops, and undertake all incidental, auxiliary, and complementary commercial operations connected therewith as may be mutually determined by the partners from time to time.'
  },
  {
    id: 'salon',
    label: 'Unisex Salon & Beauty Care',
    iconName: 'Scissors',
    firmName: 'M/S. BOUNCE & BEAUTY UNISEX SALON',
    businessIdea: 'UNISEX SALON, BEAUTY CARE, HAIR STYLING, SPA & COSMETICS TRADING',
    firmObjects: 'The business of the partnership shall be to carry on the business of operating and managing a unisex beauty salon providing services including hair cutting, styling, coloring, hair treatments, skincare treatments, facials, makeup services, bridal grooming, manicure, pedicure, spa therapies, body treatments, and other personal grooming and wellness services for men and women. The firm shall also trade, retail, and deal in cosmetics, beauty products, haircare products, skincare products, salon equipment, and allied items, and undertake all incidental and allied activities connected with the beauty and personal care industry or any other business which the partners may deem fit from time to time.'
  },
  {
    id: 'it_services',
    label: 'IT, Software & Digital Solutions',
    iconName: 'Code',
    firmName: 'M/S. NEXUS CLOUD & SOFTWARE SOLUTIONS',
    businessIdea: 'SOFTWARE DEVELOPMENT, CLOUD COMPUTING, SAAS, MOBILE APPS & IT CONSULTING',
    firmObjects: 'The business of the partnership shall be to carry on the business of software development, digital application engineering, web development, mobile applications, cloud architecture, system integration, cyber security consulting, artificial intelligence implementation, IT infrastructure management, and technology advisory services. The firm shall also market, distribute, license, and trade in software products, computer hardware, digital assets, SaaS subscriptions, and all allied and ancillary technologies and services connected therewith.'
  },
  {
    id: 'real_estate',
    label: 'Real Estate & Construction',
    iconName: 'Building',
    firmName: 'M/S. VANGUARD INFRA & DEVELOPERS',
    businessIdea: 'REAL ESTATE DEVELOPMENT, RESIDENTIAL PROJECTS, CIVIL CONTRACTS & PROPERTY TRADING',
    firmObjects: 'The business of the partnership shall be to carry on the business of builders, developers, civil engineering contractors, infrastructure consultants, property redevelopment, construction of residential and commercial complexes, layout plotting, project management, and real estate advisory. The firm shall also acquire, lease, purchase, sell, develop, and deal in lands, plots, apartments, commercial offices, building materials, construction equipment, and allied property assets.'
  },
  {
    id: 'retail_trading',
    label: 'Retail & Wholesale Trading',
    iconName: 'ShoppingBag',
    firmName: 'M/S. ROYAL TRADING & DISTRIBUTION ENTERPRISES',
    businessIdea: 'WHOLESALE & RETAIL TRADING OF FMCG, CONSUMER GOODS, GENERAL MERCHANDISE',
    firmObjects: 'The business of the partnership shall be to carry on the business of wholesale and retail trading, importing, exporting, distributing, marketing, supplying, and acting as commission agents, C&F agents, stockists, and dealers in all kinds of fast-moving consumer goods (FMCG), commodities, packaged merchandise, consumer durables, lifestyle goods, and allied general merchandise in India and abroad.'
  },
  {
    id: 'ca_finance',
    label: 'Accounting & Tax Advisory',
    iconName: 'FileSpreadsheet',
    firmName: 'M/S. ACCURATE AUDIT & TAX CONSULTANCY',
    businessIdea: 'ACCOUNTING, TAX ADVISORY, GST COMPLIANCE, FINANCIAL CONSULTING & BOOKKEEPING',
    firmObjects: 'The business of the partnership shall be to carry on the business of accounting, bookkeeping, taxation advisory, GST and direct tax compliance, corporate secretarial consulting, financial planning, project report preparation, business evaluation, payroll management, and management consulting services to businesses, individuals, and institutions in accordance with applicable professional laws and standards.'
  },
  {
    id: 'restaurant',
    label: 'Restaurant, Cafe & Hospitality',
    iconName: 'Utensils',
    firmName: 'M/S. FLAVOURS & CO. RESTAURANT',
    businessIdea: 'FINE DINE RESTAURANT, CAFE, CLOUD KITCHEN, CATERING & FOOD SERVICES',
    firmObjects: 'The business of the partnership shall be to carry on the business of running, operating, and managing restaurants, cafes, food courts, cloud kitchens, bakeries, beverage outlets, and outdoor catering services; and to prepare, process, cook, pack, sell, and deliver culinary delicacies, gourmet beverages, and packaged confectionery.'
  }
];

export function generateLegalObjectsClause(rawInput: string): string {
  if (!rawInput || !rawInput.trim()) {
    return 'The business of the partnership shall be to carry on the business of commercial trading, manufacturing, servicing, consulting, and general commercial activities as may be mutually decided by the partners from time to time.';
  }

  // Clean and normalize terms
  let cleanInput = rawInput
    .replace(/\biteam\b/gi, 'items')
    .replace(/\biteams\b/gi, 'items')
    .replace(/\bproduck\b/gi, 'products')
    .replace(/\bpackings\b/gi, 'packaging')
    .trim();

  // Split into components
  const terms = cleanInput
    .split(/[,;\n]+/)
    .map(t => t.trim())
    .filter(Boolean);

  const mainActivities = terms.join(', ').toLowerCase();

  return `The business of the partnership shall be to carry on in India or elsewhere the business of designing, manufacturing, processing, creating, handcrafting, procuring, packing, packaging, customizing, assembling, curating, stocking, distributing, marketing, exporting, importing, and dealing in ${mainActivities}, through physical retail outlets, wholesale distribution networks, departmental stores, institutional supply, and e-commerce platforms; and to act as service providers, contractors, consultants, commercial agents, dealers, stockists, and representatives in respect of all allied items, raw materials, accessories, tools, equipment, and consumables connected therewith; and to undertake all incidental, auxiliary, and complementary commercial operations as may be deemed expedient or beneficial by the partners from time to time under the Indian Partnership Act, 1932.`;
}

export function formatFirmName(name: string): string {
  if (!name || !name.trim()) return '';
  let trimmed = name.trim();
  // Remove existing redundant variations of m/s or ms
  trimmed = trimmed.replace(/^M\/S\.?\s*/i, '').replace(/^MS\.?\s*/i, '').replace(/^M\/s\.?\s*/, '').trim();
  if (!trimmed) return '';
  return `M/S. ${trimmed.toUpperCase()}`;
}

export function formatPartnerNameWithPrefix(partner: { titlePrefix?: string; name: string }): string {
  const rawName = (partner.name || '').trim();
  if (!rawName) return '';
  
  // Clean off any redundant prefix typed directly in the name box
  let cleanName = rawName
    .replace(/^MR\.?\s+/i, '')
    .replace(/^MRS\.?\s+/i, '')
    .replace(/^MISS\.?\s+/i, '')
    .replace(/^SMT\.?\s+/i, '')
    .replace(/^DR\.?\s+/i, '')
    .trim();

  const prefix = (partner.titlePrefix || '').trim();
  if (prefix) {
    return `${prefix.toUpperCase()} ${cleanName.toUpperCase()}`.trim();
  }
  return cleanName.toUpperCase();
}

export const DEFAULT_INITIAL_DATA: DeedFormData = {
  deedType: 'original',
  get supplementaryConfig() {
    return DEFAULT_SUPPLEMENTARY_CONFIG;
  },
  get dissolutionConfig() {
    return DEFAULT_DISSOLUTION_CONFIG;
  },
  uploadedDeedFileName: '',
  uploadedDeedExtractionStatus: 'idle',
  execCity: '',
  execDate: '',
  firmName: '',
  firmPan: '',
  commDate: '',
  interestRate: '12%',
  firmAddress: '',
  rawBusinessIdea: '',
  firmObjects: '',
  remunType: 'it_act_2025',
  remunDistribution: 'ratio',
  nonCompete: true,
  clientOwnership: true,
  stampDutyAmount: '300',
  includeStampPlaceholder: false,
  includeCoverPage: true,
  coverPageTitle: 'DEED OF PARTNERSHIP',
  coverPagePreparedBy: 'ADVOCATE & LEGAL CONSULTANT',
  includeCoverRegistrationBox: false,
  includeKycAnnexure: false,
  showPageNumbers: true,
  pageNumberFormat: 'page_x_of_y',
  includeCoverInPageNumbering: false,
  customTotalPages: '',
  startPageNumber: 1,
  signaturePageBreak: 'continuous',
  pageBreakBeforeClauses: [],
  documentDensity: 'compact',
  fontSize: '12pt',
  customClauses: [],
  partners: [
    {
      id: 'p1',
      titlePrefix: 'MR.',
      name: '',
      relationType: 'FATHER',
      parentName: '',
      pan: '',
      dob: '',
      age: '',
      address: '',
      profitShare: '',
      isWorking: true
    },
    {
      id: 'p2',
      titlePrefix: 'MR.',
      name: '',
      relationType: 'FATHER',
      parentName: '',
      pan: '',
      dob: '',
      age: '',
      address: '',
      profitShare: '',
      isWorking: true
    }
  ],
  witnesses: [
    {
      id: 'w1',
      name: '',
      parentName: '',
      address: ''
    },
    {
      id: 'w2',
      name: '',
      parentName: '',
      address: ''
    }
  ]
};

export interface DeedClauseItem {
  id: string;
  title: string;
  category: 'intro' | 'clause' | 'signatures';
  hasPageBreak: boolean;
}

export function formatPageNumber(
  currentPage: number,
  data: DeedFormData,
  autoTotalPages: number = 2
): string {
  const totalPagesStr = data.customTotalPages?.trim() || String(autoTotalPages);
  const format = data.pageNumberFormat || 'page_x_of_y';

  if (format === 'page_x') {
    return `Page ${currentPage}`;
  }
  if (format === 'hyphen_x') {
    return `- ${currentPage} -`;
  }
  return `Page ${currentPage} of ${totalPagesStr}`;
}

export function constructCoverPage(data: DeedFormData, isForWord: boolean = false): string {
  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const execCity = (data.execCity || '_______________').toUpperCase();
  const execDateFormatted = data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026';
  const commDateFormatted = data.commDate ? formatFormalDate(data.commDate) : '____ DAY OF ____________, 2026';
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();
  const firmPan = (data.firmPan || '').toUpperCase();
  const coverTitle = (data.coverPageTitle || 'DEED OF PARTNERSHIP').toUpperCase();
  const preparedBy = (data.coverPagePreparedBy || 'ADVOCATE & LEGAL CONSULTANT').toUpperCase();

  const partnersRows = data.partners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '__________________';
    const address = p.address ? p.address.toUpperCase() : '__________________';
    const panStr = p.pan ? ` | PAN: ${p.pan.toUpperCase()}` : '';
    const shareStr = p.profitShare ? ` (${p.profitShare}% Share)` : '';

    return `
      <tr>
        <td width="36" style="padding: 6px 8px; vertical-align: top; font-weight: bold; width: 36px; text-align: center; border: 1px solid #94a3b8; font-size: 10pt;">${idx + 1}.</td>
        <td style="padding: 6px 10px; vertical-align: top; text-align: left; border: 1px solid #94a3b8;">
          <div style="font-weight: bold; font-size: 11pt; color: #000000;">${formattedName} <span style="font-weight: normal; font-size: 10pt; color: #475569;">${shareStr}</span></div>
          <div style="font-size: 9.5pt; color: #1e293b; margin-top: 2px;">
            ${relWord} Sh. ${parentName}${panStr}
          </div>
          <div style="font-size: 9pt; color: #334155; margin-top: 2px; line-height: 1.35;">
            Address: ${address}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  const registrationBoxHtml = data.includeCoverRegistrationBox ? `
    <!-- OPTIONAL REGISTRATION BOX -->
    <div style="border: 1px solid #000000; background-color: #f8fafc; padding: 8px 12px; font-size: 8.5pt; text-align: left; margin-top: 14px; margin-bottom: 10px;">
      <div style="font-weight: bold; color: #000000; margin-bottom: 4px; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;">
        ★ FOR OFFICIAL USE & REGISTRATION AT REGISTRAR OF FIRMS / SUB-REGISTRAR ★
      </div>
      <table width="100%" border="0" cellpadding="2" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 8.5pt; color: #334155; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr>
          <td width="33%"><b>REGISTRATION NO:</b> ____________</td>
          <td width="33%"><b>BOOK NO:</b> ____________</td>
          <td width="34%"><b>VOLUME / PAGE:</b> ____________</td>
        </tr>
        <tr>
          <td><b>DATE OF FILING:</b> ____________</td>
          <td colspan="2"><b>SEAL & SIGNATURE OF REGISTRAR:</b> ________________________</td>
        </tr>
      </table>
    </div>
  ` : '';

  if (isForWord) {
    return `
      <div style="border: 2.5pt double #000000; padding: 16pt 18pt; background-color: #ffffff; text-align: center; font-family: 'Times New Roman', Times, serif;">
        
        <!-- TOP BANNER / HEADER -->
        <div style="border-bottom: 2pt solid #000000; padding-bottom: 8pt; margin-bottom: 10pt;">
          <p style="font-size: 8.5pt; font-weight: bold; letter-spacing: 1.5pt; color: #334155; text-transform: uppercase; margin: 0 0 4pt 0; text-align: center;">
            INDIAN PARTNERSHIP ACT, 1932 • OFFICIAL COMMERCIAL RECORD
          </p>
          <p style="font-size: 18pt; font-weight: bold; letter-spacing: 1.5pt; text-decoration: underline; color: #000000; text-transform: uppercase; margin: 4pt 0; text-align: center;">
            ${coverTitle}
          </p>
          <p style="font-size: 11pt; font-weight: bold; letter-spacing: 2pt; color: #000000; margin: 3pt 0 2pt 0; text-align: center;">
            — OF —
          </p>
          <p style="font-size: 15pt; font-weight: bold; letter-spacing: 1pt; color: #000000; text-transform: uppercase; margin: 3pt 0; text-align: center;">
            ${firmName}
          </p>
          ${firmPan ? `<p style="font-size: 9.5pt; font-weight: bold; color: #0f172a; margin: 3pt 0 0 0; text-align: center;">PERMANENT ACCOUNT NUMBER (PAN): ${firmPan}</p>` : ''}
        </div>

        <!-- MIDDLE: PARTIES BOX -->
        <div style="margin-bottom: 10pt; text-align: left;">
          <p style="font-size: 10pt; font-weight: bold; letter-spacing: 0.5pt; text-decoration: underline; color: #000000; margin: 0 0 4pt 0; text-transform: uppercase; text-align: left;">
            BETWEEN THE PARTNERS:
          </p>
          <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1pt solid #94a3b8; font-family: 'Times New Roman', Times, serif; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
            <tbody>
              ${partnersRows}
            </tbody>
          </table>
        </div>

        <!-- PARTICULARS TABLE -->
        <div style="margin-bottom: 10pt; text-align: left;">
          <p style="font-size: 10pt; font-weight: bold; letter-spacing: 0.5pt; text-decoration: underline; color: #000000; margin: 0 0 4pt 0; text-transform: uppercase; text-align: left;">
            KEY PARTICULARS:
          </p>
          <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1pt solid #94a3b8; font-family: 'Times New Roman', Times, serif; font-size: 9pt; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
            <tr>
              <td width="36%" style="font-weight: bold; background-color: #f8fafc; border: 1pt solid #94a3b8; padding: 4pt 6pt;">PRINCIPAL PLACE OF BUSINESS:</td>
              <td width="64%" style="border: 1pt solid #94a3b8; padding: 4pt 6pt;">${firmAddress}</td>
            </tr>
            <tr>
              <td style="font-weight: bold; background-color: #f8fafc; border: 1pt solid #94a3b8; padding: 4pt 6pt;">EFFECTIVE COMMENCEMENT:</td>
              <td style="border: 1pt solid #94a3b8; padding: 4pt 6pt;"><b>${commDateFormatted}</b></td>
            </tr>
            <tr>
              <td style="font-weight: bold; background-color: #f8fafc; border: 1pt solid #94a3b8; padding: 4pt 6pt;">EXECUTION DATE & PLACE:</td>
              <td style="border: 1pt solid #94a3b8; padding: 4pt 6pt;"><b>${execDateFormatted}</b> AT <b>${execCity}</b></td>
            </tr>
            ${preparedBy ? `
            <tr>
              <td style="font-weight: bold; background-color: #f8fafc; border: 1pt solid #94a3b8; padding: 4pt 6pt;">DRAFTED & PREPARED BY:</td>
              <td style="border: 1pt solid #94a3b8; padding: 4pt 6pt; font-weight: 600;">${preparedBy}</td>
            </tr>` : ''}
          </table>
        </div>

        ${registrationBoxHtml}

      </div>
    `;
  }

  return `
    <div class="deed-cover-page deed-block page-break-after" data-clause-id="cover_page" style="page-break-after: always; break-after: page; box-sizing: border-box; border: 3px double #000000; padding: 26px 22px; background-color: #ffffff; text-align: center; font-family: 'Times New Roman', Times, serif; color: #000000; margin-bottom: 28px;">
      
      <!-- TOP BANNER / HEADER -->
      <div style="border-bottom: 2px solid #000000; padding-bottom: 14px; margin-bottom: 16px;">
        <div style="font-size: 9.5pt; font-weight: bold; letter-spacing: 2px; color: #334155; text-transform: uppercase; margin-bottom: 6px;">
          INDIAN PARTNERSHIP ACT, 1932 • OFFICIAL COMMERCIAL RECORD
        </div>
        <div style="font-size: 24pt; font-weight: 900; letter-spacing: 2px; text-decoration: underline; color: #000000; text-transform: uppercase; margin: 8px 0; line-height: 1.2;">
          ${coverTitle}
        </div>
        <div style="font-size: 14pt; font-weight: bold; letter-spacing: 4px; color: #000000; margin: 10px 0 6px 0;">
          — OF —
        </div>
        <div style="font-size: 20pt; font-weight: 900; letter-spacing: 1.5px; color: #000000; text-transform: uppercase; line-height: 1.3;">
          ${firmName}
        </div>
        ${firmPan ? `<div style="font-size: 10.5pt; font-weight: bold; color: #0f172a; margin-top: 4px;">PERMANENT ACCOUNT NUMBER (PAN): ${firmPan}</div>` : ''}
      </div>

      <!-- MIDDLE: PARTIES BOX -->
      <div style="margin-bottom: 16px; text-align: left;">
        <div style="font-size: 11pt; font-weight: bold; letter-spacing: 1px; text-decoration: underline; color: #000000; margin-bottom: 6px; text-transform: uppercase;">
          BETWEEN THE PARTNERS:
        </div>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1px solid #94a3b8; font-family: 'Times New Roman', Times, serif; table-layout: fixed;">
          <tbody>
            ${partnersRows}
          </tbody>
        </table>
      </div>

      <!-- PARTICULARS TABLE -->
      <div style="margin-bottom: 14px; text-align: left;">
        <div style="font-size: 10.5pt; font-weight: bold; letter-spacing: 1px; text-decoration: underline; color: #000000; margin-bottom: 6px; text-transform: uppercase;">
          KEY PARTICULARS:
        </div>
        <table width="100%" border="1" cellpadding="5" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1px solid #94a3b8; font-family: 'Times New Roman', Times, serif; font-size: 9.5pt; table-layout: fixed;">
          <tr>
            <td width="36%" style="font-weight: bold; background-color: #f8fafc; border: 1px solid #94a3b8; padding: 5px 8px;">PRINCIPAL PLACE OF BUSINESS:</td>
            <td width="64%" style="border: 1px solid #94a3b8; padding: 5px 8px;">${firmAddress}</td>
          </tr>
          <tr>
            <td style="font-weight: bold; background-color: #f8fafc; border: 1px solid #94a3b8; padding: 5px 8px;">EFFECTIVE COMMENCEMENT:</td>
            <td style="border: 1px solid #94a3b8; padding: 5px 8px;"><b>${commDateFormatted}</b></td>
          </tr>
          <tr>
            <td style="font-weight: bold; background-color: #f8fafc; border: 1px solid #94a3b8; padding: 5px 8px;">EXECUTION DATE & PLACE:</td>
            <td style="border: 1px solid #94a3b8; padding: 5px 8px;"><b>${execDateFormatted}</b> AT <b>${execCity}</b></td>
          </tr>
          ${preparedBy ? `
          <tr>
            <td style="font-weight: bold; background-color: #f8fafc; border: 1px solid #94a3b8; padding: 5px 8px;">DRAFTED & PREPARED BY:</td>
            <td style="border: 1px solid #94a3b8; padding: 5px 8px; font-weight: 600;">${preparedBy}</td>
          </tr>` : ''}
        </table>
      </div>

      ${registrationBoxHtml}

    </div>
  `;
}

/**
 * Constructs a single-page compiled annexure sheet containing ONLY the copies
 * of PAN Card and Aadhaar Card (front & back) for all partners, adjusted in size
 * so all photos fit cleanly onto ONE page without any notary attestation sheet.
 */
export function constructKycAnnexurePages(
  data: DeedFormData,
  isForWord: boolean = false
): string {
  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const allPartnersToDisplay = [
    ...(data.partners || []),
    ...(data.deedType === 'supplementary' && data.supplementaryConfig?.incomingPartners ? data.supplementaryConfig.incomingPartners : [])
  ];
  const partnerCount = allPartnersToDisplay.length;

  // Scale image height dynamically based on partner count so everything fits on ONE page
  const imgMaxHeight = partnerCount > 2 ? '62px' : '76px';
  const boxMinHeight = partnerCount > 2 ? '70px' : '84px';

  const partnerCardsHtml = allPartnersToDisplay.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const panNo = (p.pan || 'APPLIED FOR').toUpperCase();
    const aadhaarNo = (p.aadhaar || 'NOT PROVIDED').toUpperCase();

    // 1. PAN Card Front Slot
    const panFrontHtml = p.panCardFrontUrl ? `
      <div style="text-align: center; border: 1px solid #000000; padding: 2px; background-color: #ffffff; border-radius: 3px; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="font-size: 7pt; font-weight: bold; background-color: #f1f5f9; padding: 2px; border-bottom: 1px solid #cbd5e1; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">
          PAN CARD &bull; ${panNo}
        </div>
        <div style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 2px;">
          ${p.panCardFrontUrl.startsWith('data:image') ? `
            <img src="${p.panCardFrontUrl}" style="max-height: ${imgMaxHeight}; max-width: 100%; object-fit: contain;" alt="PAN Card Front" />
          ` : `
            <div style="font-size: 7.5pt; font-weight: bold; color: #1e293b; padding: 6px;">[ ATTACHED: ${p.panCardFileName || 'PAN_CARD.pdf'} ]</div>
          `}
        </div>
        <div style="font-size: 6.5pt; color: #475569; font-weight: 600; text-transform: uppercase; border-top: 1px dashed #cbd5e1; padding-top: 1px;">
          Income Tax Dept
        </div>
      </div>
    ` : `
      <div style="border: 1px dashed #64748b; padding: 4px 2px; text-align: center; background-color: #f8fafc; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: center; border-radius: 3px;">
        <div style="font-size: 7pt; font-weight: bold; text-transform: uppercase; color: #0f172a;">
          PAN CARD (FRONT)
        </div>
        <div style="font-size: 6.5pt; color: #64748b; margin-top: 2px; font-style: italic;">
          [ Affix Copy: ${panNo} ]
        </div>
      </div>
    `;

    // 2. Aadhaar Front Slot
    const aadhaarFrontHtml = p.aadhaarCardFrontUrl ? `
      <div style="text-align: center; border: 1px solid #000000; padding: 2px; background-color: #ffffff; border-radius: 3px; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="font-size: 7pt; font-weight: bold; background-color: #f1f5f9; padding: 2px; border-bottom: 1px solid #cbd5e1; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">
          AADHAAR FRONT &bull; ${aadhaarNo}
        </div>
        <div style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 2px;">
          ${p.aadhaarCardFrontUrl.startsWith('data:image') ? `
            <img src="${p.aadhaarCardFrontUrl}" style="max-height: ${imgMaxHeight}; max-width: 100%; object-fit: contain;" alt="Aadhaar Card Front" />
          ` : `
            <div style="font-size: 7.5pt; font-weight: bold; color: #1e293b; padding: 6px;">[ ATTACHED: ${p.aadhaarFrontFileName || 'AADHAAR_FRONT.pdf'} ]</div>
          `}
        </div>
        <div style="font-size: 6.5pt; color: #475569; font-weight: 600; text-transform: uppercase; border-top: 1px dashed #cbd5e1; padding-top: 1px;">
          UIDAI Proof
        </div>
      </div>
    ` : `
      <div style="border: 1px dashed #64748b; padding: 4px 2px; text-align: center; background-color: #f8fafc; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: center; border-radius: 3px;">
        <div style="font-size: 7pt; font-weight: bold; text-transform: uppercase; color: #0f172a;">
          AADHAAR (FRONT)
        </div>
        <div style="font-size: 6.5pt; color: #64748b; margin-top: 2px; font-style: italic;">
          [ Affix Copy: ${aadhaarNo} ]
        </div>
      </div>
    `;

    // 3. Aadhaar Back Slot
    const aadhaarBackHtml = p.aadhaarCardBackUrl ? `
      <div style="text-align: center; border: 1px solid #000000; padding: 2px; background-color: #ffffff; border-radius: 3px; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="font-size: 7pt; font-weight: bold; background-color: #f1f5f9; padding: 2px; border-bottom: 1px solid #cbd5e1; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">
          AADHAAR BACK (ADDRESS)
        </div>
        <div style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 2px;">
          ${p.aadhaarCardBackUrl.startsWith('data:image') ? `
            <img src="${p.aadhaarCardBackUrl}" style="max-height: ${imgMaxHeight}; max-width: 100%; object-fit: contain;" alt="Aadhaar Card Back" />
          ` : `
            <div style="font-size: 7.5pt; font-weight: bold; color: #1e293b; padding: 6px;">[ ATTACHED: ${p.aadhaarBackFileName || 'AADHAAR_BACK.pdf'} ]</div>
          `}
        </div>
        <div style="font-size: 6.5pt; color: #475569; font-weight: 600; text-transform: uppercase; border-top: 1px dashed #cbd5e1; padding-top: 1px;">
          Address Proof
        </div>
      </div>
    ` : `
      <div style="border: 1px dashed #64748b; padding: 4px 2px; text-align: center; background-color: #f8fafc; min-height: ${boxMinHeight}; display: flex; flex-direction: column; justify-content: center; border-radius: 3px;">
        <div style="font-size: 7pt; font-weight: bold; text-transform: uppercase; color: #0f172a;">
          AADHAAR (BACK)
        </div>
        <div style="font-size: 6.5pt; color: #64748b; margin-top: 2px; font-style: italic;">
          [ Affix Address Proof ]
        </div>
      </div>
    `;

    return `
      <!-- COMPACT ID PROOF ROW FOR PARTNER #${idx + 1} -->
      <div style="margin-bottom: 8px; border: 1px solid #000000; padding: 6px; background-color: #ffffff;">
        <div style="background-color: #f1f5f9; border-bottom: 1px solid #000000; padding: 2px 6px; margin: -6px -6px 6px -6px; display: flex; justify-content: space-between; align-items: center; font-size: 8pt; font-weight: bold;">
          <span>PARTNER ${idx + 1}: ${formattedName}</span>
          <span style="font-size: 7.5pt; color: #334155;">PAN: ${panNo} &nbsp;|&nbsp; AADHAAR: ${aadhaarNo}</span>
        </div>

        <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; table-layout: fixed;">
          <tr>
            <td width="33%" valign="top" style="width: 33%; padding-right: 4px; vertical-align: top;">
              ${panFrontHtml}
            </td>
            <td width="34%" valign="top" style="width: 34%; padding: 0 2px; vertical-align: top;">
              ${aadhaarFrontHtml}
            </td>
            <td width="33%" valign="top" style="width: 33%; padding-left: 4px; vertical-align: top;">
              ${aadhaarBackHtml}
            </td>
          </tr>
        </table>
      </div>
    `;
  }).join('');

  return `
    <!-- ALL PROOFS COMPILED ON A SINGLE PAGE (NO NOTARY ATTESTATION SHEET) -->
    <div class="deed-block kyc-proof-page page-break-before ${isForWord ? 'SectionKyc' : ''}" data-clause-id="kyc_annexure" style="page-break-before: always; break-before: page; page-break-inside: avoid; margin-top: 16px; padding: ${isForWord ? '10pt 0' : '14px 18px'}; background-color: #ffffff; border: ${isForWord ? 'none' : '1.5px solid #000000'}; font-family: 'Times New Roman', Times, serif; color: #000000; box-sizing: border-box;">
      
      <!-- COMPACT PAGE HEADER -->
      <div style="text-align: center; border-bottom: 1.5px solid #000000; padding-bottom: 4px; margin-bottom: 8px;">
        <div style="font-size: 11pt; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase; text-decoration: underline; margin-bottom: 2px;">
          ANNEXURE &bull; COPIES OF IDENTITY & ADDRESS PROOFS
        </div>
        <div style="font-size: 7.5pt; font-weight: bold; color: #334155; text-transform: uppercase;">
          ${firmName} &bull; COPIES OF PAN CARD AND AADHAAR CARD (FRONT & BACK) OF ALL PARTNERS
        </div>
      </div>

      <!-- COMPILED PARTNERS ID PROOFS (ALL ON ONE PAGE) -->
      ${partnerCardsHtml}

      <!-- MINIMAL FOOTER NOTE -->
      <div style="margin-top: 6px; border-top: 1px dashed #94a3b8; padding-top: 2px; text-align: center; font-size: 7pt; color: #64748b;">
        Self-attested copies of government identity and address proof documents attached with Partnership Deed.
      </div>
    </div>
  `;
}

export function getDeedClauseList(data: DeedFormData): DeedClauseItem[] {
  if (data.deedType === 'supplementary') {
    return getSupplementaryClauseList(data);
  }
  if (data.deedType === 'dissolution') {
    return getDissolutionClauseList(data);
  }

  const breaks = data.pageBreakBeforeClauses || [];
  const list: DeedClauseItem[] = [];

  if (data.includeCoverPage !== false) {
    list.push({
      id: 'cover_page',
      title: 'Front Cover Page: Title & Partners Summary',
      category: 'intro',
      hasPageBreak: false
    });
  }

  list.push(
    { id: 'intro_parties', title: 'Preamble & Parties Details', category: 'intro', hasPageBreak: breaks.includes('intro_parties') },
    { id: 'clause_1', title: '1. Name of the Firm', category: 'clause', hasPageBreak: breaks.includes('clause_1') },
    { id: 'clause_2', title: '2. Place of Business', category: 'clause', hasPageBreak: breaks.includes('clause_2') },
    { id: 'clause_3', title: '3. Objects of Business', category: 'clause', hasPageBreak: breaks.includes('clause_3') },
    { id: 'clause_4', title: '4. Commencement and Duration', category: 'clause', hasPageBreak: breaks.includes('clause_4') },
    { id: 'clause_5', title: '5. Capital Contribution and Interest', category: 'clause', hasPageBreak: breaks.includes('clause_5') },
    { id: 'clause_6', title: '6. Bank Accounts and Operation', category: 'clause', hasPageBreak: breaks.includes('clause_6') },
    { id: 'clause_7', title: '7. Profit and Loss Sharing Ratio', category: 'clause', hasPageBreak: breaks.includes('clause_7') },
    { id: 'clause_8', title: '8. Remuneration to Partners (IT Act 2025)', category: 'clause', hasPageBreak: breaks.includes('clause_8') },
    { id: 'clause_9', title: '9. Books of Account and Accounting Period', category: 'clause', hasPageBreak: breaks.includes('clause_9') },
    { id: 'clause_10', title: '10. Retirement and Succession', category: 'clause', hasPageBreak: breaks.includes('clause_10') },
    { id: 'clause_11', title: '11. Goodwill Valuation', category: 'clause', hasPageBreak: breaks.includes('clause_11') },
  );

  let c = 12;
  if (data.nonCompete) {
    list.push({ 
      id: 'clause_non_compete', 
      title: `${c++}. Non-Compete Restriction and NOC`, 
      category: 'clause',
      hasPageBreak: breaks.includes('clause_non_compete') 
    });
  }
  if (data.clientOwnership) {
    list.push({ 
      id: 'clause_clientele', 
      title: `${c++}. Proprietary Clientele and Firm Assets`, 
      category: 'clause',
      hasPageBreak: breaks.includes('clause_clientele') 
    });
  }
  if (data.customClauses && data.customClauses.length > 0) {
    data.customClauses.filter(cl => cl.enabled && cl.title.trim()).forEach(cl => {
      const cId = `clause_custom_${cl.id}`;
      list.push({ 
        id: cId, 
        title: `${c++}. ${cl.title}`, 
        category: 'clause',
        hasPageBreak: breaks.includes(cId) 
      });
    });
  }
  list.push({ 
    id: 'clause_dispute', 
    title: `${c++}. Arbitration and Dispute Resolution`, 
    category: 'clause',
    hasPageBreak: breaks.includes('clause_dispute') 
  });
  list.push({ 
    id: 'clause_jurisdiction', 
    title: `${c++}. Applicability of the Partnership Act`, 
    category: 'clause',
    hasPageBreak: breaks.includes('clause_jurisdiction') 
  });
  list.push({ 
    id: 'signatures', 
    title: 'Execution & Witness Signatures', 
    category: 'signatures',
    hasPageBreak: (data.signaturePageBreak === 'newPage') || breaks.includes('signatures')
  });

  if (data.includeKycAnnexure === true) {
    list.push({
      id: 'kyc_annexure',
      title: 'Annexure: ID Proof Copies (PAN & Aadhaar)',
      category: 'signatures',
      hasPageBreak: true
    });
  }

  return list;
}

export function constructDeedBody(
  data: DeedFormData, 
  isForWord: boolean = false, 
  includeCover: boolean = true,
  includeKyc: boolean = true
): string {
  if (data.deedType === 'supplementary') {
    return constructSupplementaryDeedBody(data, isForWord, includeCover, includeKyc);
  }
  if (data.deedType === 'dissolution') {
    return constructDissolutionDeedBody(data, isForWord, includeCover, includeKyc);
  }

  const execCity = (data.execCity || '_______________').toUpperCase();
  const execDateFormatted = data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026';
  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const firmPan = (data.firmPan || '').toUpperCase();
  const commDateFormatted = data.commDate ? formatFormalDate(data.commDate) : '____ DAY OF ____________, 2026';
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();
  const firmObjects = (data.firmObjects || 'The business of the partnership shall be to carry on the business as may be mutually agreed upon by the partners from time to time.').trim();
  const interestRate = (data.interestRate || '12%').trim();
  const remunType = data.remunType;
  const remunDist = data.remunDistribution;
  const nonCompete = data.nonCompete;
  const clientOwnership = data.clientOwnership;

  const pageBreaks = data.pageBreakBeforeClauses || [];
  const breakClass = (id: string) => {
    if (isForWord) {
      return pageBreaks.includes(id) ? '<p class="MsoNormal" style="page-break-before:always;mso-break-type:section-break;margin:0;padding:0;font-size:1pt;line-height:1pt;">&nbsp;</p>' : '';
    }
    return pageBreaks.includes(id) ? ' page-break-before' : '';
  };
  const isSigBreak = data.signaturePageBreak === 'newPage' || pageBreaks.includes('signatures');
  const sigBreakTag = isForWord
    ? (isSigBreak ? '<p class="MsoNormal" style="page-break-before:always;mso-break-type:section-break;margin:0;padding:0;font-size:1pt;line-height:1pt;">&nbsp;</p>' : '')
    : '';
  const sigBreakClass = (!isForWord && isSigBreak) ? ' page-break-before' : '';

  const partnersIntro = data.partners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'Wife of' : 'Son of / Daughter of';
    return `<div style="margin-bottom: 10px; text-align: justify; line-height: 1.65;"><b>${formattedName}</b>, ${relWord} <b>${p.parentName || '________________'}</b>, aged <b>${p.age || '___'} YEARS</b>, having Permanent Account Number (PAN) <b>${p.pan || 'APPLIED FOR'}</b>, residing at <b>${p.address || '________________'}</b> (hereinafter referred to as the party of the <b>${getOrdinal(idx + 1)} PART</b>)</div>`;
  }).join('<div style="text-align: center; font-weight: bold; margin: 10px 0;">AND</div>');

  const profitTableRows = data.partners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    return `
    <tr>
      <td style="border: 1px solid #000; padding: 6px 8px; width: 12%; text-align: center;">${idx + 1}</td>
      <td style="border: 1px solid #000; padding: 6px 8px; width: 63%; text-align: left;"><b>${formattedName}</b></td>
      <td style="border: 1px solid #000; padding: 6px 8px; width: 25%; text-align: center;"><b>${p.profitShare || '0'}%</b></td>
    </tr>
  `;
  }).join('');

  let c = 1;

  const clause1 = `<div class="clause-heading">${c++}. NAME OF THE FIRM :-</div>
    <p class="deed-p">The business of the partnership firm shall be carried on under the name and style of <b>${firmName}</b>, or such other name as the partners may mutually decide in writing from time to time.</p>`;

  const clause2 = `<div class="clause-heading">${c++}. PLACE OF BUSINESS :-</div>
    <p class="deed-p">The principal place of business of the firm shall be situated at <b>${firmAddress}</b>, with full liberty to establish branches, regional offices, depots, showrooms, administrative offices, or manufacturing units at such other locations as the partners may mutually agree upon from time to time.</p>`;

  const clause3 = `<div class="clause-heading">${c++}. OBJECTS OF BUSINESS :-</div>
    <p class="deed-p">${firmObjects}</p>`;

  const clause4 = `<div class="clause-heading">${c++}. COMMENCEMENT AND DURATION :-</div>
    <p class="deed-p">The partnership shall be deemed to have commenced with effect from <b>${commDateFormatted}</b>, and the duration of the partnership shall be <b>PARTNERSHIP AT WILL</b>.</p>`;

  const clause5 = `<div class="clause-heading">${c++}. CAPITAL CONTRIBUTION AND INTEREST :-</div>
    <p class="deed-p">The capital required for the purpose of the partnership business shall be contributed and maintained by the partners in such manner and proportion as may be mutually agreed upon from time to time. The firm shall pay simple interest at a rate not exceeding <b>${interestRate}</b> per annum on the credit balances standing in the capital accounts of the partners in accordance with the statutory ceiling prescribed under Section 35(e) of the Income-tax Act, 2025. Interest on drawings shall be charged or adjusted as mutually agreed.</p>`;

  const clause6 = `<div class="clause-heading">${c++}. BANK ACCOUNTS AND OPERATION :-</div>
    <p class="deed-p">The bank accounts of the partnership firm shall be opened and maintained with any scheduled, nationalised, or co-operative bank(s) and such banking account(s) shall be operated under the joint or individual signatures of the partners as mutually resolved by the firm from time to time.</p>`;

  const clause7 = `<div class="clause-heading">${c++}. PROFIT AND LOSS SHARING RATIO :-</div>
    <p class="deed-p">The net profit or net loss of the firm, after charging and deducting all working expenses, administrative outgoings, interest on partner capital, and statutory remuneration payable to the working partners, shall be divided between and borne by the partners in the following agreed proportions:</p>
    <table class="deed-table" width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin: 10px 0;">
      <thead>
        <tr style="background-color: #f1f5f9;">
          <th style="width: 12%; text-align: center; border: 1px solid #000; padding: 6px 8px;">SR. NO.</th>
          <th style="width: 63%; text-align: left; border: 1px solid #000; padding: 6px 8px;">NAME OF THE PARTNER</th>
          <th style="width: 25%; text-align: center; border: 1px solid #000; padding: 6px 8px;">SHARE (%)</th>
        </tr>
      </thead>
      <tbody>
        ${profitTableRows}
      </tbody>
    </table>`;

  const distDesc = remunDist === 'ratio' ? 'in their mutual profit sharing ratio' : 'in equal proportion among all working partners';
  let remunerationBody = '';

  const workingPartners = data.partners?.filter(p => p.isWorking) || [];
  const partnersWithSalary = data.partners?.filter(p => p.isWorking && p.salaryMonthly && parseInt(p.salaryMonthly, 10) > 0) || [];

  if (remunType === 'fixed_salary' || (partnersWithSalary.length > 0 && remunType !== 'it_act_2025')) {
    const salaryRowsHtml = (partnersWithSalary.length > 0 ? partnersWithSalary : workingPartners).map((p, idx) => {
      const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
      const mSal = parseInt(p.salaryMonthly || '0', 10);
      const aSal = mSal * 12;
      return `
        <tr>
          <td style="border: 1px solid #000000; padding: 6px 10px; text-align: center; vertical-align: middle; font-size: 10pt;">${idx + 1}</td>
          <td style="border: 1px solid #000000; padding: 6px 10px; font-weight: bold; vertical-align: middle; font-size: 10pt;">${formattedName}</td>
          <td style="border: 1px solid #000000; padding: 6px 10px; text-align: right; font-weight: bold; vertical-align: middle; font-size: 10pt;">
            ${mSal > 0 ? `Rs. ${mSal.toLocaleString('en-IN')}/- per month` : 'As mutually agreed'}
          </td>
          <td style="border: 1px solid #000000; padding: 6px 10px; text-align: right; vertical-align: middle; font-size: 10pt;">
            ${aSal > 0 ? `Rs. ${aSal.toLocaleString('en-IN')}/- p.a.` : '—'}
          </td>
        </tr>
      `;
    }).join('');

    remunerationBody = `
      <p class="deed-p">All the partners have agreed to actively participate in the conduct and affairs of the partnership business as working partners. It is hereby mutually resolved, agreed, and covenanted that in consideration of the working partners actively devoting their time, professional attention, expertise, and personal efforts to the business of the firm, the following working partners shall be entitled to draw fixed monthly remuneration / salary as set forth hereunder: -</p>

      <table style="width: 100%; border-collapse: collapse; margin: 12px 0; border: 1.5px solid #000000; font-size: 10pt;">
        <thead>
          <tr style="background-color: #f1f5f9;">
            <th style="border: 1px solid #000000; padding: 6px 8px; text-align: center; width: 8%;">SR.</th>
            <th style="border: 1px solid #000000; padding: 6px 10px; text-align: left; width: 44%;">NAME OF WORKING PARTNER</th>
            <th style="border: 1px solid #000000; padding: 6px 10px; text-align: right; width: 24%;">MONTHLY SALARY</th>
            <th style="border: 1px solid #000000; padding: 6px 10px; text-align: right; width: 24%;">ANNUAL AMOUNT</th>
          </tr>
        </thead>
        <tbody>
          ${salaryRowsHtml}
        </tbody>
      </table>

      <p class="deed-p" style="margin-top: 6px; font-weight: bold;">Statutory Conditions & Special Covenants:</p>
      <div style="padding-left: 12px; margin-top: 4px;">
        <p class="deed-p" style="margin-bottom: 6px;">1. The aggregate remuneration payable to all working partners shall remain strictly subject to the maximum ceiling limits allowable under Section 40(b) / Section 35(e) of the Income-tax Act, as applicable for each financial year.</p>
        <p class="deed-p" style="margin-bottom: 6px;">2. In the event of commercial loss, inadequacy of book profits, or cash flow constraints, the working partners may unanimously resolve to proportionately scale down, postpone, or waive the remuneration payable for any financial year or period.</p>
        <p class="deed-p" style="margin-bottom: 6px;">3. The partners may, by mutual written resolution passed at the beginning of any financial year, increase or re-align the monthly salary of any working partner commensurate with their business responsibilities.</p>
        <p class="deed-p" style="margin-bottom: 6px;">4. All salary payments shall remain subject to applicable statutory Tax Deduction at Source (TDS) under the Income-tax Act.</p>
      </div>
    `;
  } else if (remunType === 'it_act_2025') {
    let interimSalaryNote = '';
    if (partnersWithSalary.length > 0) {
      const salDetails = partnersWithSalary.map(p => `${formatPartnerNameWithPrefix(p) || p.name}: Rs. ${parseInt(p.salaryMonthly!, 10).toLocaleString('en-IN')}/- per month`).join('; ');
      interimSalaryNote = `<p class="deed-p" style="margin-top: 6px;"><b>Interim Monthly Drawing:</b> Without prejudice to the aforesaid annual statutory book-profit ceilings, the working partner(s) shall be entitled to draw interim monthly remuneration (${salDetails}), adjustable against their final eligible annual remuneration entitlement at the close of the financial year.</p>`;
    }

    remunerationBody = `
      <p class="deed-p">All the partners have agreed to work in the partnership firm as working partners. It is hereby agreed that in consideration of the partners devoting their time and personal attention to the business of the partnership firm, all the working partners shall be entitled to draw yearly remuneration ${distDesc} on the basis of income of the firm in accordance with Section 35(e) of the Income-tax Act, 2025, in the following manner: -</p>
      
      <table style="width: 100%; border: none; border-collapse: collapse; margin: 10px 0; table-layout: fixed;">
        <tr>
          <td style="border: none; padding: 5px 10px 5px 0; width: 50%; vertical-align: top; text-align: left; font-size: 11pt;">
            a)&nbsp;&nbsp;On the first Rs. 6,00,000/- of the Book Profit, or in case of a Loss.
          </td>
          <td style="border: none; padding: 5px 0 5px 10px; width: 50%; vertical-align: top; text-align: left; font-size: 11pt;">
            Rs. 3,00,000/- or at the rate of 90% of the Book Profit, whichever is more.
          </td>
        </tr>
        <tr>
          <td style="border: none; padding: 5px 10px 5px 0; width: 50%; vertical-align: top; text-align: left; font-size: 11pt;">
            b)&nbsp;&nbsp;On the balance of the Book Profit.
          </td>
          <td style="border: none; padding: 5px 0 5px 10px; width: 50%; vertical-align: top; text-align: left; font-size: 11pt;">
            At the rate of 60% of the Book profit.
          </td>
        </tr>
      </table>
      ${interimSalaryNote}
      <p class="deed-p" style="margin-top: 6px; font-weight: bold;">Further it is hereby mutually clarified that:</p>
      <div style="padding-left: 12px; margin-top: 4px;">
        <p class="deed-p" style="margin-bottom: 6px;">1. The partners may unanimously decide to reduce, defer, or forgo remuneration in the interest of the business liquidity.</p>
        <p class="deed-p" style="margin-bottom: 6px;">2. All payments of salary, bonus, commission, remuneration, or interest to partners shall remain subject to applicable statutory Tax Deduction at Source (TDS) under the Income-tax Act, 2025.</p>
        <p class="deed-p" style="margin-bottom: 6px;">3. In case of any subsequent statutory amendment of Section 35(e) of the Income-tax Act, 2025, the limits and conditions herein shall automatically stand modified to conform with such amended provisions without requiring a separate supplementary deed.</p>
      </div>
    `;
  } else {
    remunerationBody = `<p class="deed-p">The working partners shall be entitled to draw remuneration as mutually decided in writing from time to time subject strictly to the limits and conditions under the Income-tax law.</p>`;
  }

  const clause8 = `<div class="clause-heading">${c++}. REMUNERATION TO PARTNERS :-</div>${remunerationBody}`;

  const clause9 = `<div class="clause-heading">${c++}. BOOKS OF ACCOUNT AND ACCOUNTING PERIOD :-</div>
    <p class="deed-p">The accounting year of the partnership firm shall commence on the 1st day of April and close on the 31st day of March of each financial year. Proper books of accounts shall be regularly maintained at the principal place of business and shall remain open to inspection and examination by all the partners at all reasonable times.</p>`;

  const clause10 = `<div class="clause-heading">${c++}. RETIREMENT AND SUCCESSION :-</div>
    <p class="deed-p">(A) Any partner may retire from the partnership by giving reasonable advance written notice to the other partners.</p>
    <p class="deed-p">(B) In the event of death or retirement of any partner, the firm shall not dissolve automatically and shall continue among the surviving partners. The legal heirs or representatives of a deceased partner shall only be entitled to the settlement of capital balances and accumulated profits standing to the credit of the deceased partner, without any right to interfere in the management or conduct of the firm.</p>`;

  const clause11 = `<div class="clause-heading">${c++}. GOODWILL :-</div>
    <p class="deed-p">In the event of retirement, death, or permanent incapacitation of any Partner, or upon the dissolution of the Firm, the valuation of the Goodwill of the Firm and the entitlement, if any, of the outgoing Partner, deceased Partner’s legal representatives, or the continuing Partners shall be determined on such terms and conditions as may be mutually agreed upon in writing between the continuing Partners and the outgoing Partner (or their legal heirs/representatives) at the relevant time.</p>
    <p class="deed-p">In the absence of such mutual agreement within 180 days from the effective date of retirement, demise, or decision to dissolve, the valuation of Goodwill shall be referred to an independent Chartered Accountant / registered valuer mutually appointed by the parties, whose valuation and determined mode of settlement shall be final and binding on all Partners and their legal representatives.</p>`;

  let optionalClausesHTML = '';

  if (nonCompete) {
    if (isForWord) {
      optionalClausesHTML += `${breakClass('clause_non_compete')}<div class="clause-heading">${c++}. NON-COMPETE RESTRICTION AND NOC :-</div>
        <p class="deed-p">No partner shall, directly or indirectly, engage in, operate, assist, finance, advise, or carry on any business similar to or competing with the business of this partnership firm either during the subsistence of this partnership or in the future, without first obtaining a formal written <b>'NO OBJECTION CERTIFICATE' (NOC)</b> executed by all other partners. In the event any partner commits a breach of this covenant without prior written NOC, all profits, revenues, and gains derived from such competing transaction or enterprise shall be deemed to have accrued exclusively to this partnership firm, and the defaulting partner shall indemnify the firm accordingly.</p>`;
    } else {
      optionalClausesHTML += `<div class="deed-block${breakClass('clause_non_compete')}" data-clause-id="clause_non_compete"><div class="clause-heading">${c++}. NON-COMPETE RESTRICTION AND NOC :-</div>
        <p class="deed-p">No partner shall, directly or indirectly, engage in, operate, assist, finance, advise, or carry on any business similar to or competing with the business of this partnership firm either during the subsistence of this partnership or in the future, without first obtaining a formal written <b>'NO OBJECTION CERTIFICATE' (NOC)</b> executed by all other partners. In the event any partner commits a breach of this covenant without prior written NOC, all profits, revenues, and gains derived from such competing transaction or enterprise shall be deemed to have accrued exclusively to this partnership firm, and the defaulting partner shall indemnify the firm accordingly.</p></div>`;
    }
  }

  if (clientOwnership) {
    if (isForWord) {
      optionalClausesHTML += `${breakClass('clause_clientele')}<div class="clause-heading">${c++}. PROPRIETARY CLIENTELE AND FIRM ASSETS :-</div>
        <p class="deed-p">All clients, patrons, contracts, inquiries, mandates, business goodwill, intellectual property, formulas, records, and client databases generated, served, or developed in connection with the business shall solely vest in and belong to the partnership firm as an entity, and not to any individual partner. No retiring or expelled partner shall have any right to solicit, divert, or claim proprietary control over the firm's clientele or proprietary assets.</p>`;
    } else {
      optionalClausesHTML += `<div class="deed-block${breakClass('clause_clientele')}" data-clause-id="clause_clientele"><div class="clause-heading">${c++}. PROPRIETARY CLIENTELE AND FIRM ASSETS :-</div>
        <p class="deed-p">All clients, patrons, contracts, inquiries, mandates, business goodwill, intellectual property, formulas, records, and client databases generated, served, or developed in connection with the business shall solely vest in and belong to the partnership firm as an entity, and not to any individual partner. No retiring or expelled partner shall have any right to solicit, divert, or claim proprietary control over the firm's clientele or proprietary assets.</p></div>`;
    }
  }

  // Custom user clauses
  if (data.customClauses && data.customClauses.length > 0) {
    data.customClauses.filter(cl => cl.enabled && cl.title.trim()).forEach(cl => {
      const customKey = `clause_custom_${cl.id}`;
      if (isForWord) {
        optionalClausesHTML += `${breakClass(customKey)}<div class="clause-heading">${c++}. ${cl.title.toUpperCase()} :-</div><p class="deed-p">${cl.content}</p>`;
      } else {
        optionalClausesHTML += `<div class="deed-block${breakClass(customKey)}" data-clause-id="${customKey}"><div class="clause-heading">${c++}. ${cl.title.toUpperCase()} :-</div><p class="deed-p">${cl.content}</p></div>`;
      }
    });
  }

  const disputeClause = `<div class="clause-heading">${c++}. ARBITRATION AND DISPUTE RESOLUTION :-</div>
    <p class="deed-p">All disputes, differences, or questions whatsoever which may arise either during the subsistence of the partnership or upon dissolution between the partners touching these presents or the construction or application thereof shall be referred to a mutually agreed sole arbitrator in accordance with the provisions of the Arbitration and Conciliation Act, 1996 or any statutory amendment thereof. The seat and venue of arbitration shall be at <b>${execCity}</b>.</p>`;

  const jurisdictionClause = `<div class="clause-heading">${c++}. APPLICABILITY OF THE PARTNERSHIP ACT :-</div>
    <p class="deed-p">In respect of all matters not expressly provided for herein, the rights, duties, and liabilities of the partners shall be governed by the provisions of the Indian Partnership Act, 1932.</p>`;

  // Execution Blocks - Left Side (Witnesses) and Right Side (Partners)
  const partnersExecutionBoxes = data.partners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '';

    if (isForWord) {
      return `
      <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr style="background-color: #f1f5f9;">
          <td colspan="3" style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 10.5pt; text-transform: uppercase; text-align: left; letter-spacing: 0.3pt; color: #0f172a; font-family: 'Times New Roman', Times, serif;">
            PARTNER #${idx + 1} — PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART
          </td>
        </tr>
        <tr>
          <!-- PARTNER PARTICULARS -->
          <td width="46%" valign="top" style="border: 1pt solid #000000; padding: 6pt; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 3pt 0; text-align: left; font-size: 10pt;"><b>NAME:</b> <span>${formattedName}</span></p>
            ${parentName ? `<p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</p>` : ''}
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PAN:</b> <b>${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</b></p>
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</p>
            ${p.profitShare ? `<p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${p.profitShare}%</b></p>` : ''}
            <p style="margin: 4pt 0 0 0; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
              <b>STATUS:</b> EXECUTANT / CONTINUING PARTNER
            </p>
          </td>

          <!-- PASSPORT SIZE PHOTOGRAPH BOX (STANDARD 3.5cm x 4.5cm / 35mm x 45mm) -->
          <td width="27%" align="center" valign="middle" style="border: 1pt solid #000000; padding: 4pt; width: 27%; text-align: center; vertical-align: middle; background-color: #fafafa;">
            <table border="1" cellpadding="0" cellspacing="0" align="center" width="98" height="126" style="width: 98pt; height: 126pt; border: 1.5pt dashed #334155; border-collapse: collapse; margin-left: auto; margin-right: auto; background-color: #ffffff; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr>
                <td align="center" valign="middle" width="98" height="126" style="border: 1.5pt dashed #334155; text-align: center; vertical-align: middle; padding: 4pt; background-color: #f8fafc; font-family: 'Times New Roman', Times, serif;">
                  <p style="font-size: 8pt; font-weight: bold; text-transform: uppercase; color: #1e293b; line-height: 1.25; margin: 0; text-align: center;">
                    AFFIX PASSPORT SIZE PHOTO
                  </p>
                  <p style="font-size: 7.5pt; font-weight: bold; color: #475569; margin: 4pt 0 0 0; letter-spacing: 0.3pt; text-align: center;">
                    3.5 cm × 4.5 cm
                  </p>
                  <p style="font-size: 6.5pt; color: #94a3b8; margin: 3pt 0 0 0; text-align: center;">
                    (Cross Sign over Photo)
                  </p>
                </td>
              </tr>
            </table>
          </td>

          <!-- LEFT THUMB IMPRESSION BOX (STANDARD SIZE) -->
          <td width="27%" align="center" valign="middle" style="border: 1pt solid #000000; padding: 4pt; width: 27%; text-align: center; vertical-align: middle; background-color: #fafafa;">
            <table border="1" cellpadding="0" cellspacing="0" align="center" width="98" height="126" style="width: 98pt; height: 126pt; border: 1.5pt dashed #334155; border-collapse: collapse; margin-left: auto; margin-right: auto; background-color: #ffffff; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr>
                <td align="center" valign="middle" width="98" height="126" style="border: 1.5pt dashed #334155; text-align: center; vertical-align: middle; padding: 4pt; background-color: #f8fafc; font-family: 'Times New Roman', Times, serif;">
                  <p style="font-size: 8pt; font-weight: bold; text-transform: uppercase; color: #1e293b; line-height: 1.25; margin: 0; text-align: center;">
                    LEFT THUMB IMPRESSION
                  </p>
                  <p style="font-size: 7.5pt; font-weight: bold; color: #475569; margin: 4pt 0 0 0; letter-spacing: 0.3pt; text-align: center;">
                    (L.T.I.)
                  </p>
                  <p style="font-size: 6.5pt; color: #94a3b8; margin: 3pt 0 0 0; text-align: center;">
                    (Clear Blue/Black Ink)
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- EXPANDED SPACIOUS PARTNER SIGNATURE BOX -->
        <tr>
          <td colspan="3" align="center" valign="bottom" style="border: 1pt solid #000000; padding: 18pt 8pt 8pt 8pt; text-align: center; vertical-align: bottom; background-color: #ffffff; font-family: 'Times New Roman', Times, serif;">
            <div style="height: 48pt; line-height: 48pt;">&nbsp;</div>
            <p style="width: 85%; border-bottom: 1.5pt solid #000000; margin: 0 auto 6pt auto; text-align: center;">&nbsp;</p>
            <p style="font-size: 10.5pt; font-weight: bold; text-transform: uppercase; color: #000000; letter-spacing: 0.5pt; text-align: center; margin: 0;">
              SIGNATURE OF PARTNER: ${formattedName}
            </p>
            <p style="font-size: 8.5pt; color: #475569; text-transform: uppercase; margin: 2pt 0 0 0; text-align: center;">
              (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
            </p>
          </td>
        </tr>
      </table>
      `;
    }

    return `
    <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 16px; border: 1.5px solid #000000; table-layout: fixed; page-break-inside: avoid; break-inside: avoid;">
      <tr style="background-color: #f1f5f9;">
        <td colspan="3" style="border: 1px solid #000000; padding: 6px 8px; font-weight: bold; font-size: 10.5pt; text-transform: uppercase; text-align: left; letter-spacing: 0.3px; color: #0f172a;">
          PARTNER #${idx + 1} — PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART
        </td>
      </tr>
      <tr>
        <!-- PARTNER PARTICULARS -->
        <td width="46%" valign="top" style="border: 1px solid #000000; padding: 8px 7px; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left;">
          <div style="margin-bottom: 4px; text-align: left; font-size: 10pt;"><b>NAME:</b> <span style="color: #000000;">${formattedName}</span></div>
          ${parentName ? `<div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</div>` : ''}
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PAN:</b> <span style="font-weight: bold; color: #000000;">${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</span></div>
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</div>
          ${p.profitShare ? `<div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${p.profitShare}%</b></div>` : ''}
          <div style="margin-top: 5px; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
            <b>STATUS:</b> EXECUTANT / CONTINUING PARTNER
          </div>
        </td>

        <!-- PASSPORT SIZE PHOTOGRAPH BOX (STANDARD 3.5cm x 4.5cm / 35mm x 45mm) -->
        <td width="27%" align="center" valign="middle" style="border: 1px solid #000000; padding: 6px 4px; width: 27%; text-align: center; vertical-align: middle; background-color: #fafafa;">
          <table border="1" cellpadding="0" cellspacing="0" align="center" width="105" height="135" style="width: 105px; height: 135px; min-width: 35mm; min-height: 45mm; border: 1.5px dashed #334155; border-collapse: collapse; margin-left: auto; margin-right: auto; background-color: #ffffff;">
            <tr>
              <td align="center" valign="middle" width="105" height="135" style="border: 1.5px dashed #334155; text-align: center; vertical-align: middle; padding: 6px 4px; background-color: #f8fafc;">
                <div style="font-size: 8pt; font-weight: bold; text-transform: uppercase; color: #1e293b; line-height: 1.25;">
                  AFFIX PASSPORT SIZE PHOTO
                </div>
                <div style="font-size: 7.5pt; font-weight: 600; color: #475569; margin-top: 6px; letter-spacing: 0.3px;">
                  3.5 cm × 4.5 cm
                </div>
                <div style="font-size: 6.5pt; color: #94a3b8; margin-top: 4px;">
                  (Cross Sign over Photo)
                </div>
              </td>
            </tr>
          </table>
        </td>

        <!-- LEFT THUMB IMPRESSION BOX (STANDARD SIZE) -->
        <td width="27%" align="center" valign="middle" style="border: 1px solid #000000; padding: 6px 4px; width: 27%; text-align: center; vertical-align: middle; background-color: #fafafa;">
          <table border="1" cellpadding="0" cellspacing="0" align="center" width="105" height="135" style="width: 105px; height: 135px; min-width: 35mm; min-height: 45mm; border: 1.5px dashed #334155; border-collapse: collapse; margin-left: auto; margin-right: auto; background-color: #ffffff;">
            <tr>
              <td align="center" valign="middle" width="105" height="135" style="border: 1.5px dashed #334155; text-align: center; vertical-align: middle; padding: 6px 4px; background-color: #f8fafc;">
                <div style="font-size: 8pt; font-weight: bold; text-transform: uppercase; color: #1e293b; line-height: 1.25;">
                  LEFT THUMB IMPRESSION
                </div>
                <div style="font-size: 7.5pt; font-weight: 600; color: #475569; margin-top: 6px; letter-spacing: 0.3px;">
                  (L.T.I.)
                </div>
                <div style="font-size: 6.5pt; color: #94a3b8; margin-top: 4px;">
                  (Clear Blue/Black Ink)
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- EXPANDED SPACIOUS PARTNER SIGNATURE BOX -->
      <tr>
        <td colspan="3" align="center" valign="bottom" style="border: 1px solid #000000; padding: 18px 10px 10px 10px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
          <div style="min-height: 52px; height: 55px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 6px;">
            <!-- Spacious blank signing room above line -->
            <div style="width: 88%; max-width: 440px; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
          </div>
          <div style="font-size: 10.5pt; font-weight: bold; text-transform: uppercase; color: #000000; letter-spacing: 0.5px; text-align: center;">
            SIGNATURE OF PARTNER: ${formattedName}
          </div>
          <div style="font-size: 8.5pt; color: #475569; text-transform: uppercase; margin-top: 2px; text-align: center;">
            (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
          </div>
        </td>
      </tr>
    </table>
  `;
  }).join('');

  // Witnesses
  const witness1 = data.witnesses[0] || { name: '', parentName: '', address: '' };
  const witness2 = data.witnesses[1] || { name: '', parentName: '', address: '' };

  const witness1Content = witness1.name.trim() ? `
    <div style="margin-bottom: 3px; text-align: left;"><b>NAME:</b> ${witness1.name.toUpperCase()}</div>
    <div style="margin-bottom: 3px; text-align: left;"><b>FATHER'S/HUSBAND'S NAME:</b> ${witness1.parentName.toUpperCase()}</div>
    <div style="margin-bottom: 3px; text-align: left;"><b>ADDRESS:</b> ${witness1.address.toUpperCase()}</div>
  ` : `
    <div style="margin-bottom: 6px; text-align: left;"><b>NAME:</b> ___________________________</div>
    <div style="margin-bottom: 6px; text-align: left;"><b>FATHER'S/HUSBAND'S NAME:</b> __________</div>
    <div style="margin-bottom: 6px; text-align: left;"><b>ADDRESS:</b> _________________________</div>
    <div style="margin-bottom: 2px; text-align: left;">_____________________________________</div>
  `;

  const witness2Content = witness2.name.trim() ? `
    <div style="margin-bottom: 3px; text-align: left;"><b>NAME:</b> ${witness2.name.toUpperCase()}</div>
    <div style="margin-bottom: 3px; text-align: left;"><b>FATHER'S/HUSBAND'S NAME:</b> ${witness2.parentName.toUpperCase()}</div>
    <div style="margin-bottom: 3px; text-align: left;"><b>ADDRESS:</b> ${witness2.address.toUpperCase()}</div>
  ` : `
    <div style="margin-bottom: 6px; text-align: left;"><b>NAME:</b> ___________________________</div>
    <div style="margin-bottom: 6px; text-align: left;"><b>FATHER'S/HUSBAND'S NAME:</b> __________</div>
    <div style="margin-bottom: 6px; text-align: left;"><b>ADDRESS:</b> _________________________</div>
    <div style="margin-bottom: 2px; text-align: left;">_____________________________________</div>
  `;

  const coverPageHtml = (includeCover && data.includeCoverPage !== false) ? constructCoverPage(data, isForWord) : '';

  const startPageNum = data.startPageNumber || 1;
  const autoTotal = 2;

  const page1Num = startPageNum;
  const page2Num = startPageNum + 1;

  // In Word mode, omit inline footers because Word generates native footers using mso-element:footer
  const page1Footer = isForWord ? '' : `
    <!-- CLAUSES PAGE BOTTOM NUMBERING -->
    <div class="deed-page-footer" style="margin-top: 24px; padding-top: 10px; border-top: 1.5px solid #000000; display: flex; justify-content: space-between; align-items: center; font-size: 10pt; font-family: 'Times New Roman', Times, serif; color: #1e293b;">
      <span style="font-size: 9pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">${firmName}</span>
      <span style="font-weight: bold; font-size: 10.5pt; color: #000000;">${formatPageNumber(page1Num, data, autoTotal)}</span>
    </div>
  `;

  const page2Footer = isForWord ? '' : `
    <!-- SIGNATURES PAGE BOTTOM NUMBERING -->
    <div class="deed-page-footer" style="margin-top: 24px; padding-top: 10px; border-top: 1.5px solid #000000; display: flex; justify-content: space-between; align-items: center; font-size: 10pt; font-family: 'Times New Roman', Times, serif; color: #1e293b;">
      <span style="font-size: 9pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; color: #475569;">${firmName}</span>
      <span style="font-weight: bold; font-size: 10.5pt; color: #000000;">${formatPageNumber(page2Num, data, autoTotal)}</span>
    </div>
  `;

  if (isForWord) {
    return `
      ${coverPageHtml}
      ${breakClass('intro')}
      <div class="deed-title">DEED OF PARTNERSHIP</div>
      <p class="deed-p">This Deed of Partnership is executed at <b>${execCity}</b> on this <b>${execDateFormatted}</b> by and between:</p>

      ${breakClass('intro_parties')}
      <div style="margin: 10pt 0;">
        ${partnersIntro}
      </div>

      ${breakClass('recitals')}
      <p class="deed-p">Whereas both the parties hereto have mutually agreed to constitute a partnership firm commencing from <b>${commDateFormatted}</b> to carry on the business under the name and style of <b>${firmName}</b> ${firmPan ? `(having PAN: <b>${firmPan}</b>)` : ''} having its principal place of business at <b>${firmAddress}</b> on the terms and conditions hereinafter set forth.</p>
      <p class="deed-p">Now this Deed Witnesseth and it is hereby mutually agreed by and between the parties hereto as follows:</p>

      ${breakClass('clause_1')}${clause1}
      ${breakClass('clause_2')}${clause2}
      ${breakClass('clause_3')}${clause3}
      ${breakClass('clause_4')}${clause4}
      ${breakClass('clause_5')}${clause5}
      ${breakClass('clause_6')}${clause6}
      ${breakClass('clause_7')}${clause7}
      ${breakClass('clause_8')}${clause8}
      ${breakClass('clause_9')}${clause9}
      ${breakClass('clause_10')}${clause10}
      ${breakClass('clause_11')}${clause11}
      ${optionalClausesHTML}
      ${breakClass('clause_dispute')}${disputeClause}
      ${breakClass('clause_jurisdiction')}${jurisdictionClause}

      <!-- FORMAL EXECUTION & SIGNATURE PAGE (SIDE-BY-SIDE DUAL COLUMN LAYOUT) -->
      ${sigBreakTag}
      <div style="margin-top: 14pt;">
        <p class="deed-p" style="font-weight: bold; margin-bottom: 12pt;">
          IN WITNESS WHEREOF THE PARTIES HERETO HAVE SET AND SUBSCRIBED THEIR RESPECTIVE HANDS, THUMB IMPRESSIONS, AND PHOTOGRAPHS ON THIS DEED OF PARTNERSHIP ON THE DAY, MONTH, AND YEAR FIRST HEREINABOVE WRITTEN.
        </p>

        <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; border: none; margin-top: 10pt; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
          <tr>
            <!-- LEFT COLUMN: WITNESSES DETAILS & SIGNATURES -->
            <td width="35%" valign="top" style="width: 35%; vertical-align: top; padding-right: 12pt; border: none; border-right: 1.5pt dashed #94a3b8;">
              <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase; text-align: left; letter-spacing: 0.3pt; font-family: 'Times New Roman', Times, serif;">
                SIGNED IN THE PRESENCE OF WITNESSES:
              </p>

              <!-- Witness 1 Card -->
              <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
                <tr style="background-color: #f1f5f9;">
                  <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 10pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">
                    WITNESS #1
                  </td>
                </tr>
                <tr>
                  <td style="border: 1pt solid #000000; padding: 7pt; vertical-align: top; font-size: 9.5pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">
                    ${witness1Content}
                  </td>
                </tr>
                <tr>
                  <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; background-color: #ffffff; font-family: 'Times New Roman', Times, serif;">
                    <div style="height: 32pt; line-height: 32pt;">&nbsp;</div>
                    <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                    <p style="font-size: 9.5pt; text-align: center; font-weight: bold; color: #000000; text-transform: uppercase; margin: 0;">
                      SIGNATURE OF WITNESS 1
                    </p>
                  </td>
                </tr>
              </table>

              <!-- Witness 2 Card -->
              <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
                <tr style="background-color: #f1f5f9;">
                  <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 10pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">
                    WITNESS #2
                  </td>
                </tr>
                <tr>
                  <td style="border: 1pt solid #000000; padding: 7pt; vertical-align: top; font-size: 9.5pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">
                    ${witness2Content}
                  </td>
                </tr>
                <tr>
                  <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; background-color: #ffffff; font-family: 'Times New Roman', Times, serif;">
                    <div style="height: 32pt; line-height: 32pt;">&nbsp;</div>
                    <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                    <p style="font-size: 9.5pt; text-align: center; font-weight: bold; color: #000000; text-transform: uppercase; margin: 0;">
                      SIGNATURE OF WITNESS 2
                    </p>
                  </td>
                </tr>
              </table>

            </td>

            <!-- RIGHT COLUMN: PARTNERS DETAILS & SIGNATURES -->
            <td width="65%" valign="top" style="width: 65%; vertical-align: top; padding-left: 12pt; border: none;">
              <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase; text-align: left; letter-spacing: 0.3pt; font-family: 'Times New Roman', Times, serif;">
                DETAILS AND EXECUTION BY PARTNERS:
              </p>
              ${partnersExecutionBoxes}
            </td>
          </tr>
        </table>
      </div>
    `;
  }

  return `
    ${coverPageHtml}
    <div class="deed-block${breakClass('intro')}">
      <div class="deed-title">DEED OF PARTNERSHIP</div>
      <p class="deed-p">This Deed of Partnership is executed at <b>${execCity}</b> on this <b>${execDateFormatted}</b> by and between:</p>
    </div>

    <div class="deed-block${breakClass('intro_parties')}" style="margin: 12px 0;">
      ${partnersIntro}
    </div>

    <div class="deed-block${breakClass('recitals')}">
      <p class="deed-p">Whereas both the parties hereto have mutually agreed to constitute a partnership firm commencing from <b>${commDateFormatted}</b> to carry on the business under the name and style of <b>${firmName}</b> ${firmPan ? `(having PAN: <b>${firmPan}</b>)` : ''} having its principal place of business at <b>${firmAddress}</b> on the terms and conditions hereinafter set forth.</p>
      <p class="deed-p">Now this Deed Witnesseth and it is hereby mutually agreed by and between the parties hereto as follows:</p>
    </div>

    <div class="deed-block${breakClass('clause_1')}" data-clause-id="clause_1">${clause1}</div>
    <div class="deed-block${breakClass('clause_2')}" data-clause-id="clause_2">${clause2}</div>
    <div class="deed-block${breakClass('clause_3')}" data-clause-id="clause_3">${clause3}</div>
    <div class="deed-block${breakClass('clause_4')}" data-clause-id="clause_4">${clause4}</div>
    <div class="deed-block${breakClass('clause_5')}" data-clause-id="clause_5">${clause5}</div>
    <div class="deed-block${breakClass('clause_6')}" data-clause-id="clause_6">${clause6}</div>
    <div class="deed-block${breakClass('clause_7')}" data-clause-id="clause_7">${clause7}</div>
    <div class="deed-block${breakClass('clause_8')}" data-clause-id="clause_8">${clause8}</div>
    <div class="deed-block${breakClass('clause_9')}" data-clause-id="clause_9">${clause9}</div>
    <div class="deed-block${breakClass('clause_10')}" data-clause-id="clause_10">${clause10}</div>
    <div class="deed-block${breakClass('clause_11')}" data-clause-id="clause_11">${clause11}</div>
    ${optionalClausesHTML}
    <div class="deed-block${breakClass('clause_dispute')}" data-clause-id="clause_dispute">${disputeClause}</div>
    <div class="deed-block${breakClass('clause_jurisdiction')}" data-clause-id="clause_jurisdiction">${jurisdictionClause}</div>

    ${page1Footer}

    <!-- FORMAL EXECUTION & SIGNATURE PAGE (SIDE-BY-SIDE DUAL COLUMN LAYOUT) -->
    <div class="deed-block${sigBreakClass}" data-clause-id="signatures">
      <p style="margin-top: 14px; margin-bottom: 14px; font-weight: bold; text-align: justify; font-size: 12.5px; line-height: 1.55;">
        IN WITNESS WHEREOF THE PARTIES HERETO HAVE SET AND SUBSCRIBED THEIR RESPECTIVE HANDS, THUMB IMPRESSIONS, AND PHOTOGRAPHS ON THIS DEED OF PARTNERSHIP ON THE DAY, MONTH, AND YEAR FIRST HEREINABOVE WRITTEN.
      </p>

      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; border: none; margin-top: 14px; table-layout: fixed;">
        <tr>
          <!-- LEFT COLUMN: WITNESSES DETAILS & SIGNATURES -->
          <td width="34%" valign="top" style="width: 34%; vertical-align: top; padding-right: 14px; border: none; border-right: 1.5px dashed #94a3b8;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase; text-align: left; letter-spacing: 0.3px;">
              SIGNED IN THE PRESENCE OF WITNESSES:
            </p>

            <!-- Witness 1 Card -->
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 16px; border: 1.5px solid #000000; table-layout: fixed; page-break-inside: avoid; break-inside: avoid;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 10pt; text-align: left; text-transform: uppercase;">
                  WITNESS #1
                </td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; vertical-align: top; font-size: 9.5pt; line-height: 1.45; text-align: left;">
                  ${witness1Content}
                </td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 38px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9.5pt; text-align: center; font-weight: bold; color: #000000; text-transform: uppercase;">
                    SIGNATURE OF WITNESS 1
                  </div>
                </td>
              </tr>
            </table>

            <!-- Witness 2 Card -->
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 16px; border: 1.5px solid #000000; table-layout: fixed; page-break-inside: avoid; break-inside: avoid;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 10pt; text-align: left; text-transform: uppercase;">
                  WITNESS #2
                </td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; vertical-align: top; font-size: 9.5pt; line-height: 1.45; text-align: left;">
                  ${witness2Content}
                </td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 38px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9.5pt; text-align: center; font-weight: bold; color: #000000; text-transform: uppercase;">
                    SIGNATURE OF WITNESS 2
                  </div>
                </td>
              </tr>
            </table>

          </td>

          <!-- RIGHT COLUMN: PARTNERS DETAILS & SIGNATURES -->
          <td width="66%" valign="top" style="width: 66%; vertical-align: top; padding-left: 14px; border: none;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase; text-align: left; letter-spacing: 0.3px;">
              DETAILS AND EXECUTION BY PARTNERS:
            </p>
            ${partnersExecutionBoxes}
          </td>
        </tr>
      </table>

      ${page2Footer}
    </div>
    ${(includeKyc && data.includeKycAnnexure === true) ? constructKycAnnexurePages(data, isForWord) : ''}
  `;
}

export function constructDeedHtmlDocument(data: DeedFormData, forPrint: boolean = false): string {
  const content = constructDeedBody(data);
  const firmName = formatFirmName(data.firmName) || 'Partnership Deed';
  return `
<!DOCTYPE html>
<html lang="EN">
<head>
  <meta charset="UTF-8">
  <title>${firmName} - Partnership Deed</title>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      font-family: 'Times New Roman', Times, serif;
      margin: 0;
      padding: ${forPrint ? '0' : '20px'};
      background-color: ${forPrint ? '#ffffff' : '#f8fafc'};
      color: #000000;
      line-height: 1.68;
      font-size: 13.5px;
      text-align: justify;
    }
    .deed-container {
      max-width: 820px;
      margin: auto;
      background: #ffffff;
      padding: ${forPrint ? '0' : '40px 50px'};
      ${forPrint ? '' : 'box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #cbd5e1; border-radius: 4px;'}
    }
    .deed-block {
      break-inside: avoid;
      page-break-inside: avoid;
      margin-bottom: 14px;
    }
    .deed-title {
      text-align: center;
      font-size: 18px;
      font-weight: bold;
      letter-spacing: 1.5px;
      text-decoration: underline;
      margin-bottom: 24px;
      text-transform: uppercase;
    }
    .clause-heading {
      font-weight: bold;
      text-align: left;
      margin-top: 10px;
      margin-bottom: 4px;
      text-transform: uppercase;
    }
    p, .deed-p {
      margin-top: 0;
      margin-bottom: 12px;
      line-height: 1.72;
      text-align: justify;
    }
    .deed-table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      table-layout: fixed;
      break-inside: avoid;
      page-break-inside: avoid;
    }
    .deed-table th, .deed-table td {
      border: 1px solid #000;
      padding: 8px 10px;
      text-align: left;
      word-wrap: break-word;
      font-size: 12.5px;
    }
    .exec-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      margin-bottom: 22px;
      table-layout: fixed;
      break-inside: avoid;
      page-break-inside: avoid;
    }
    .exec-table th, .exec-table td {
      border: 1px solid #000;
      padding: 8px;
      word-wrap: break-word;
      font-size: 12px;
    }
    .page-break-before {
      break-before: page;
      page-break-before: always;
      margin-top: 24px;
      padding-top: 12px;
    }
    @page {
      size: A4 portrait;
      margin: 18mm 15mm 18mm 15mm;
    }
    @media print {
      body {
        padding: 0 !important;
        background: #ffffff !important;
        font-size: 12pt !important;
      }
      .deed-container {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        max-width: 100% !important;
      }
    }
  </style>
</head>
<body>
  <div class="deed-container">
    ${content}
  </div>
</body>
</html>
  `;
}

export function downloadWordDocument(data: DeedFormData) {
  const hasCoverPage = data.includeCoverPage !== false;
  const coverHtml = hasCoverPage ? constructCoverPage(data, true) : '';
  const deedBodyHtml = constructDeedBody(data, true, false, false);
  const hasKycAnnexure = data.includeKycAnnexure === true;
  const kycHtml = hasKycAnnexure ? constructKycAnnexurePages(data, true) : '';
  const firmName = (data.firmName || '').trim() || 'PARTNERSHIP_DEED';
  const cleanName = firmName.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
  const prefix = data.deedType === 'supplementary' ? 'Supplementary_Deed_' : data.deedType === 'dissolution' ? 'Dissolution_Deed_' : 'Deed_';
  const fileName = `${prefix}${cleanName}.doc`;
  const deedTypeTitle = data.deedType === 'supplementary' ? 'Supplementary Deed of Partnership' : data.deedType === 'dissolution' ? 'Deed of Dissolution of Partnership' : 'Partnership Deed';

  const startPageNum = data.startPageNumber || 1;
  const format = data.pageNumberFormat || 'page_x_of_y';

  let pageNumField = `<b>Page <span style='mso-field-code:" PAGE "'></span> of <span style='mso-field-code:" SECTIONPAGES "'></span></b>`;
  if (format === 'page_x') {
    pageNumField = `<b>Page <span style='mso-field-code:" PAGE "'></span></b>`;
  } else if (format === 'hyphen_x') {
    pageNumField = `<b>- <span style='mso-field-code:" PAGE "'></span> -</b>`;
  } else if (data.customTotalPages?.trim()) {
    pageNumField = `<b>Page <span style='mso-field-code:" PAGE "'></span> of ${data.customTotalPages.trim()}</b>`;
  }

  const wordHeader = `
<html xmlns:o='urn:schemas-microsoft-com:office:office' 
      xmlns:w='urn:schemas-microsoft-com:office:word' 
      xmlns='http://www.w3.org/TR/REC-html40'>
<head>
  <meta charset='utf-8'>
  <title>${firmName} - ${deedTypeTitle}</title>
  <!--[if gte mso 9]>
  <xml>
    <w:WordDocument>
      <w:View>Print</w:View>
      <w:Zoom>100</w:Zoom>
      <w:DoNotOptimizeForBrowser/>
    </w:WordDocument>
  </xml>
  <![endif]-->
  <style>
    @page SectionCover {
      size: 595.3pt 841.9pt;
      margin: 36.0pt 42.0pt 36.0pt 42.0pt;
      mso-header-margin: 0pt;
      mso-footer-margin: 0pt;
      mso-paper-source: 0;
    }
    div.SectionCover {
      page: SectionCover;
    }
    @page SectionDeed {
      size: 595.3pt 841.9pt;
      margin: 54.0pt 54.0pt 54.0pt 54.0pt;
      mso-header-margin: 36.0pt;
      mso-footer-margin: 36.0pt;
      mso-footer: f1;
      mso-page-numbers-start: ${startPageNum};
    }
    div.SectionDeed {
      page: SectionDeed;
    }
    @page SectionKyc {
      size: 595.3pt 841.9pt;
      margin: 36.0pt 36.0pt 36.0pt 36.0pt;
      mso-header-margin: 0pt;
      mso-footer-margin: 0pt;
    }
    div.SectionKyc {
      page: SectionKyc;
    }
    p.MsoFooter, div.MsoFooter {
      margin: 0pt;
      font-family: 'Times New Roman', Times, serif;
      font-size: 10.0pt;
      color: #333333;
    }
    body {
      font-family: 'Times New Roman', Times, serif;
      font-size: 12.0pt;
      line-height: 1.45;
      text-align: justify;
      color: #000000;
    }
    .deed-title {
      text-align: center;
      font-size: 16.0pt;
      font-weight: bold;
      text-decoration: underline;
      letter-spacing: 1.5pt;
      margin-bottom: 18.0pt;
      text-transform: uppercase;
      font-family: 'Times New Roman', Times, serif;
    }
    .clause-heading {
      font-family: 'Times New Roman', Times, serif;
      font-size: 12.0pt;
      font-weight: bold;
      text-align: left !important;
      margin-top: 10.0pt;
      margin-bottom: 2.0pt;
      page-break-after: avoid;
    }
    p, .deed-p {
      font-family: 'Times New Roman', Times, serif;
      font-size: 12.0pt;
      margin-top: 0pt;
      margin-bottom: 8.0pt;
      line-height: 1.45;
      text-align: justify;
      text-justify: inter-ideograph;
      text-align-last: left;
    }
    table {
      border-collapse: collapse;
      mso-table-lspace: 0pt;
      mso-table-rspace: 0pt;
    }
    td, th {
      font-family: 'Times New Roman', Times, serif;
      font-size: 10.0pt;
      vertical-align: top;
    }
    .page-break-before {
      page-break-before: always;
      mso-break-type: section-break;
    }
    .page-break-after {
      page-break-after: always;
      mso-break-type: section-break;
    }
  </style>
</head>
<body lang="EN-US">
`;

  let bodyContent = '';
  if (hasCoverPage) {
    bodyContent += `
  <div class="SectionCover">
    ${coverHtml}
    <br clear="all" style="page-break-before:always;mso-break-type:section-break" />
  </div>
    `;
  }

  bodyContent += `
  <div class="SectionDeed">
    ${deedBodyHtml}
  </div>
  `;

  if (hasKycAnnexure) {
    bodyContent += `
  <br clear="all" style="page-break-before:always;mso-break-type:section-break" />
  <div class="SectionKyc">
    ${kycHtml}
  </div>
    `;
  }

  const wordFooter = `
    ${data.showPageNumbers !== false ? `
    <div style='mso-element:footer' id='f1'>
      <p class='MsoFooter' style='text-align:right; font-family:"Times New Roman", Times, serif; font-size:10pt; border-top: 1pt solid #000000; padding-top: 4pt;'>
        <span style='float:left; font-size:9pt; text-transform:uppercase; color:#475569; font-weight:bold;'>${formatFirmName(data.firmName) || 'PARTNERSHIP DEED'}</span>
        ${pageNumField}
      </p>
    </div>` : ''}
</body>
</html>
  `;
  const fullHtml = wordHeader + bodyContent + wordFooter;

  const blob = new Blob(['\ufeff' + fullHtml], { type: 'application/msword;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function printDeedDocument(data: DeedFormData) {
  const html = constructDeedHtmlDocument(data, true);
  
  // Create an invisible iframe specifically for printing the clean deed
  const printIframe = document.createElement('iframe');
  printIframe.setAttribute('title', 'Partnership Deed Print Window');
  printIframe.style.position = 'fixed';
  printIframe.style.right = '0';
  printIframe.style.bottom = '0';
  printIframe.style.width = '0';
  printIframe.style.height = '0';
  printIframe.style.border = '0';
  document.body.appendChild(printIframe);

  try {
    const iframeDoc = printIframe.contentWindow?.document || printIframe.contentDocument;
    if (iframeDoc) {
      iframeDoc.open();
      iframeDoc.write(html);
      iframeDoc.close();

      setTimeout(() => {
        try {
          printIframe.contentWindow?.focus();
          printIframe.contentWindow?.print();
        } catch (iframeErr) {
          console.warn('Iframe print restricted, trying popup fallback:', iframeErr);
          const printWindow = window.open('', '_blank');
          if (printWindow) {
            printWindow.document.write(html);
            printWindow.document.close();
            printWindow.focus();
            printWindow.print();
          }
        }
        setTimeout(() => {
          if (document.body.contains(printIframe)) {
            document.body.removeChild(printIframe);
          }
        }, 5000);
      }, 400);
    }
  } catch (err) {
    console.error('Print iframe error, fallback to new window:', err);
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    }
  }
}

export async function exportDeedToPDF(data: DeedFormData): Promise<boolean> {
  const firmName = (data.firmName || '').trim() || 'PARTNERSHIP_DEED';
  const cleanName = firmName.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
  const fileName = `Deed_${cleanName}.pdf`;

  const density = data.documentDensity || 'compact';
  const fontSize = data.fontSize || '12pt';

  let baseFontSize = '12.5px';
  let lineHeight = '1.60';
  let blockMargin = '10px';
  let paraMargin = '8px';

  if (density === 'tight') {
    baseFontSize = fontSize === '13pt' ? '12.8px' : fontSize === '11pt' ? '11.5px' : '12px';
    lineHeight = '1.45';
    blockMargin = '6px';
    paraMargin = '5px';
  } else if (density === 'standard') {
    baseFontSize = fontSize === '13pt' ? '14px' : fontSize === '11pt' ? '12.5px' : '13.5px';
    lineHeight = '1.72';
    blockMargin = '14px';
    paraMargin = '12px';
  } else {
    // compact
    baseFontSize = fontSize === '13pt' ? '13.5px' : fontSize === '11pt' ? '11.8px' : '12.5px';
    lineHeight = '1.58';
    blockMargin = '9px';
    paraMargin = '7px';
  }

  // Create an isolated iframe free from any application-level Tailwind stylesheets containing oklch
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.left = '-9999px';
  iframe.style.top = '-9999px';
  iframe.style.width = '794px';
  iframe.style.height = '1123px';
  iframe.style.border = 'none';
  document.body.appendChild(iframe);

  try {
    const iframeDoc = iframe.contentWindow?.document || iframe.contentDocument;
    if (!iframeDoc) {
      throw new Error('Could not access iframe document');
    }

    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * {
      box-sizing: border-box;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: geometricPrecision;
    }
    body {
      margin: 0;
      padding: 0;
      background-color: #ffffff;
      color: #000000;
      font-family: 'Times New Roman', Times, serif;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: geometricPrecision;
    }
    .pdf-page {
      width: 794px;
      height: 1123px;
      max-height: 1123px;
      box-sizing: border-box;
      padding: 44px 50px 38px 50px;
      background-color: #ffffff;
      color: #000000;
      font-family: 'Times New Roman', Times, serif;
      font-size: ${baseFontSize};
      line-height: ${lineHeight};
      text-align: justify;
      position: relative;
      overflow: hidden;
    }
    .deed-block {
      margin-bottom: ${blockMargin};
    }
    .deed-title {
      text-align: center;
      font-size: 17px;
      font-weight: bold;
      letter-spacing: 1.5px;
      text-decoration: underline;
      margin-bottom: 18px;
      text-transform: uppercase;
      font-family: 'Times New Roman', Times, serif;
    }
    .clause-heading {
      font-weight: bold;
      text-align: left;
      margin-top: 8px;
      margin-bottom: 4px;
      text-transform: uppercase;
      font-family: 'Times New Roman', Times, serif;
    }
    p, .deed-p {
      margin-top: 0;
      margin-bottom: ${paraMargin};
      line-height: ${lineHeight};
      text-align: justify;
    }
    .deed-table {
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0;
      table-layout: fixed;
    }
    .deed-table th, .deed-table td {
      border: 1px solid #000000;
      padding: 6px 8px;
      text-align: left;
      word-wrap: break-word;
      font-size: 12px;
    }
    .exec-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      margin-bottom: 16px;
      table-layout: fixed;
    }
    .exec-table th, .exec-table td {
      border: 1px solid #000000;
      padding: 6px;
      word-wrap: break-word;
      font-size: 11.5px;
    }
  </style>
</head>
<body>
  <div id="scratch-source" style="display: none;">
    ${constructDeedBody(data)}
  </div>
  <div id="pages-container"></div>
</body>
</html>
    `;

    iframeDoc.open();
    iframeDoc.write(htmlContent);
    iframeDoc.close();

    // Settle scratch source content
    await new Promise((resolve) => setTimeout(resolve, 200));

    const scratchSource = iframeDoc.getElementById('scratch-source');
    const pagesContainer = iframeDoc.getElementById('pages-container');

    if (!scratchSource || !pagesContainer) {
      throw new Error('Rendering containers not found');
    }

    const rawBlocks = Array.from(scratchSource.querySelectorAll('.deed-block')) as HTMLElement[];
    const blocksToPaginate = rawBlocks.length > 0 ? rawBlocks : (Array.from(scratchSource.children) as HTMLElement[]);

    // Expand iframe initial height so it doesn't restrict rendering
    iframe.style.height = `${Math.max(2500, (blocksToPaginate.length + 8) * 1150)}px`;

    const createPage = (): HTMLElement => {
      const p = iframeDoc.createElement('div');
      p.className = 'pdf-page';
      pagesContainer.appendChild(p);
      return p;
    };

    let currentPage = createPage();
    // Usable printable height inside A4:
    // Total 1123px - 44px top padding - 38px bottom padding - 35px footer reserve = ~1006px
    const USABLE_PAGE_HEIGHT = 1010;

    const getPageContentHeight = (page: HTMLElement): number => {
      let total = 0;
      const children = Array.from(page.children) as HTMLElement[];
      for (const child of children) {
        if (child.classList.contains('pdf-page-footer')) continue;
        const h = child.offsetHeight || child.getBoundingClientRect().height || 0;
        total += h;
        const style = iframeDoc.defaultView?.getComputedStyle(child);
        if (style) {
          total += (parseFloat(style.marginTop) || 0) + (parseFloat(style.marginBottom) || 0);
        }
      }
      return total;
    };

    for (let i = 0; i < blocksToPaginate.length; i++) {
      const block = blocksToPaginate[i].cloneNode(true) as HTMLElement;
      const isForceNewPage = block.classList.contains('page-break-before');
      const isCoverPage = block.classList.contains('deed-cover-page');

      if (isCoverPage) {
        if (currentPage.children.length > 0) {
          currentPage = createPage();
        }
        currentPage.appendChild(block);
        currentPage = createPage();
        continue;
      }

      if (isForceNewPage && currentPage.children.length > 0) {
        currentPage = createPage();
      }

      currentPage.appendChild(block);

      if (getPageContentHeight(currentPage) > USABLE_PAGE_HEIGHT) {
        if (currentPage.children.length > 1) {
          currentPage.removeChild(block);
          currentPage = createPage();
          currentPage.appendChild(block);
        }

        // If the block is on a fresh page but exceeds USABLE_PAGE_HEIGHT (e.g. multi-partner signatures or long clauses)
        if (getPageContentHeight(currentPage) > USABLE_PAGE_HEIGHT) {
          const directChildren = Array.from(block.children) as HTMLElement[];
          if (directChildren.length > 1) {
            currentPage.removeChild(block);

            let splitContainer = block.cloneNode(false) as HTMLElement;
            currentPage.appendChild(splitContainer);

            for (const child of directChildren) {
              const childClone = child.cloneNode(true) as HTMLElement;
              splitContainer.appendChild(childClone);

              if (getPageContentHeight(currentPage) > USABLE_PAGE_HEIGHT && splitContainer.children.length > 1) {
                splitContainer.removeChild(childClone);
                currentPage = createPage();
                splitContainer = block.cloneNode(false) as HTMLElement;
                currentPage.appendChild(splitContainer);
                splitContainer.appendChild(childClone);
              }
            }
          }
        }
      }
    }

    // Clean up empty trailing page if any
    while (pagesContainer.children.length > 1) {
      const last = pagesContainer.lastElementChild as HTMLElement;
      if (last && last.children.length === 0) {
        pagesContainer.removeChild(last);
      } else {
        break;
      }
    }

    // Adjust iframe height to ensure ALL generated pages are completely inside the viewport
    const pages = Array.from(pagesContainer.children) as HTMLElement[];
    if (pages.length === 0) {
      throw new Error('No pages generated');
    }
    iframe.style.height = `${Math.max(1500, (pages.length + 2) * 1150)}px`;

    // Wait for DOM layout to settle and ensure all image resources are loaded
    await new Promise((resolve) => setTimeout(resolve, 250));
    const allImgs = Array.from(iframeDoc.querySelectorAll('img')) as HTMLImageElement[];
    if (allImgs.length > 0) {
      await Promise.all(
        allImgs.map(img => {
          if (img.complete && img.naturalHeight !== 0) return Promise.resolve(null);
          return new Promise((resolve) => {
            img.onload = () => resolve(null);
            img.onerror = () => resolve(null);
            setTimeout(() => resolve(null), 2500);
          });
        })
      );
    }

    const hasCoverPage = pages.some(p => p.querySelector('.deed-cover-page') || p.classList.contains('deed-cover-page'));
    const actualDeedPagesCount = Math.max(1, pages.length - (hasCoverPage ? 1 : 0));
    
    // Check if user specified front cover to be included in page numbering
    const isCoverNumbered = data.includeCoverInPageNumbering === true;
    const baseTotalCount = isCoverNumbered ? pages.length : actualDeedPagesCount;

    // Never let total pages in footer be fewer than actual generated pages
    let totalPagesCount = baseTotalCount;
    if (data.customTotalPages && data.customTotalPages.trim() !== '' && data.customTotalPages.trim() !== '2') {
      const parsed = parseInt(data.customTotalPages, 10);
      if (!isNaN(parsed) && parsed >= baseTotalCount) {
        totalPagesCount = parsed;
      }
    }
    const startPage = data.startPageNumber || 1;

    let deedPageIndex = 0;
    for (let i = 0; i < pages.length; i++) {
      const pageEl = pages[i];
      const isCover = pageEl.querySelector('.deed-cover-page') || pageEl.classList.contains('deed-cover-page');

      // Remove existing footers from cloned content
      const existingFooters = pageEl.querySelectorAll('.deed-page-footer, .pdf-page-footer');
      existingFooters.forEach(f => f.remove());

      if (isCover && !isCoverNumbered) {
        // Front cover title page is unnumbered
        continue;
      }

      deedPageIndex++;
      const currentPageNum = startPage + (deedPageIndex - 1);

      const footer = iframeDoc.createElement('div');
      footer.className = 'pdf-page-footer';
      footer.style.position = 'absolute';
      footer.style.bottom = '18px';
      footer.style.left = '50px';
      footer.style.right = '50px';
      footer.style.display = 'flex';
      footer.style.justifyContent = 'space-between';
      footer.style.alignItems = 'center';
      footer.style.fontSize = '9.5pt';
      footer.style.fontFamily = "'Times New Roman', Times, serif";
      footer.style.color = '#1e293b';
      footer.style.borderTop = '1px solid #000000';
      footer.style.paddingTop = '6px';

      let pageText = `Page ${currentPageNum} of ${totalPagesCount}`;
      if (data.pageNumberFormat === 'page_x') {
        pageText = `Page ${currentPageNum}`;
      } else if (data.pageNumberFormat === 'hyphen_x') {
        pageText = `- ${currentPageNum} -`;
      }

      footer.innerHTML = `
        <span style="font-size: 8.5pt; font-weight: bold; color: #475569; text-transform: uppercase; letter-spacing: 0.5px;">${formatFirmName(data.firmName) || 'PARTNERSHIP DEED'}</span>
        <span style="font-weight: bold; font-size: 10pt; color: #000000;">${pageText}</span>
      `;
      pageEl.appendChild(footer);
    }

    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
      compress: false
    });

    const pdfWidth = 210;
    const pdfHeight = 297;

    for (let i = 0; i < pages.length; i++) {
      const pageEl = pages[i];

      const canvas = await html2canvas(pageEl, {
        scale: 2.5,
        useCORS: true,
        allowTaint: true,
        logging: false,
        backgroundColor: '#ffffff',
        width: 794,
        height: 1123,
        windowWidth: 794,
        imageTimeout: 10000
      });

      const imgData = canvas.toDataURL('image/png');
      if (i > 0) {
        pdf.addPage();
      }
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight, undefined, 'NONE');
    }

    pdf.save(fileName);
    return true;
  } catch (err) {
    console.warn('Direct PDF export error, triggering print fallback:', err);
    printDeedDocument(data);
    return false;
  } finally {
    if (document.body.contains(iframe)) {
      document.body.removeChild(iframe);
    }
  }
}

export function downloadStandaloneHtml(data: DeedFormData) {
  const fullHtml = constructDeedHtmlDocument(data, false);
  const firmName = data.firmName.trim() || 'PARTNERSHIP_DEED';
  const cleanName = firmName.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 40);
  const fileName = `Partnership_Deed_${cleanName}.html`;

  const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function downloadDesktopLauncherBat(appName: string = 'Partnership Deed Drafter') {
  const batContent = `@echo off
title ${appName} Desktop Launcher
color 1F
echo ======================================================
echo    Starting ${appName} Desktop Environment...
echo ======================================================
echo.
echo Launching local application server...
echo.

if exist dist\\server.cjs (
    start "Deed Drafter Server" /B node dist\\server.cjs
) else (
    echo Note: Building production bundle if required...
    call npm run build
    start "Deed Drafter Server" /B node dist\\server.cjs
)

echo Waiting for server on http://localhost:3000...
timeout /t 2 /nobreak >nul

echo Opening Desktop App Window...
start msedge --app="http://localhost:3000" || start chrome --app="http://localhost:3000" || start http://localhost:3000

echo Application successfully launched on desktop!
exit
`;

  const blob = new Blob([batContent], { type: 'application/x-bat;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'Launch_Partnership_Deed_Desktop.bat';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
