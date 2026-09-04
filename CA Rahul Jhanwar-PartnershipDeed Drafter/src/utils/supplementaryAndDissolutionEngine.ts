import { DeedFormData, SupplementaryConfig, DissolutionConfig, Partner, Witness } from '../types';
import { 
  formatFormalDate, 
  formatFirmName, 
  formatPartnerNameWithPrefix, 
  getOrdinal,
  formatPageNumber,
  constructKycAnnexurePages,
  DeedClauseItem
} from './deedEngine';

export const DEFAULT_SUPPLEMENTARY_CONFIG: SupplementaryConfig = {
  originalDeedDate: '',
  originalDeedCity: '',
  originalRegistrationNumber: '',
  effectiveDate: '',
  priorDeeds: [],
  changePartners: true,
  changeClauses: false,
  changeRemuneration: false,
  changeOtherConditions: false,
  retiringPartnerIds: [],
  retirementEffectiveDate: '',
  retirementSettlementTerms: 'The accounts of the Retiring Partner have been fully settled, and the Retiring Partner has received all dues on account of capital, accumulated profits, and goodwill and has no further claim against the firm or its continuing partners.',
  incomingPartners: [],
  admissionEffectiveDate: '',
  admissionTerms: 'The Incoming Partner has contributed capital as mutually resolved and agreed, and shall share in all assets, liabilities, business, and profits of the firm in accordance with the amended terms.',
  revisedProfitShares: {},
  changeFirmName: false,
  newFirmName: '',
  changeAddress: false,
  newFirmAddress: '',
  changeObjects: false,
  newObjects: '',
  customAmendedClauses: [],
  remunType: 'it_act_2025',
  remunDistribution: 'ratio',
  revisedRemunText: '',
  changeInterestRate: false,
  revisedInterestRate: '12%',
  changeBankOperation: false,
  newBankOperationTerms: 'The banking accounts of the firm shall be operated jointly / severally as mutually resolved by the active partners.',
  additionalClauses: [],
  ratificationClause: 'Save and except the alterations, modifications, additions and amendments specifically contained herein, all other terms, conditions, covenants and agreements contained in the Principal Partnership Deed dated [DATE] shall remain unaltered, in full legal force and binding effect upon all the partners.'
};

export const DEFAULT_DISSOLUTION_CONFIG: DissolutionConfig = {
  originalDeedDate: '',
  originalDeedCity: '',
  originalRegistrationNumber: '',
  dissolutionDate: '',
  priorDeeds: [],
  dissolutionReason: 'mutual_consent',
  customReasonText: '',
  cessationOfBusiness: 'That the partnership firm M/S. [FIRM_NAME] stands dissolved by mutual consent with effect from the close of business on [DISSOLUTION_DATE], and no partner shall carry on any commercial business under the said firm name thereafter.',
  realizationOfAssets: 'All outstanding book debts, receivables, assets, stock, securities and bank balances of the firm shall be realized and collected by the partners and applied towards liquidation of statutory and third-party liabilities.',
  dischargeOfLiabilities: 'All debts, liabilities, loans, trade creditors and statutory tax dues (including Goods & Services Tax and Income Tax) shall be paid off and discharged in full out of the realized assets of the firm.',
  divisionOfSurplus: 'After the discharge of all debts, liabilities and expenses of winding up, the surplus assets and capital balance shall be divided and distributed among the partners strictly in proportion to their respective capital accounts and profit-sharing ratios.',
  custodianPartnerId: '',
  custodianPartnerName: '',
  recordsRetentionYears: '8',
  publicNoticeNewspapers: 'one English national daily and one vernacular daily newspaper circulating in the district',
  registrarNotification: true,
  mutualIndemnityTerms: 'Each partner hereby releases, acquits and discharges the other partners from all actions, claims and demands in respect of the partnership; provided that each partner shall indemnify the other partners against any undisclosed private debt or liability incurred without the authorization of the firm.',
  bankAccountSettlement: 'All existing current accounts, credit facilities and bank operations in the name of the firm shall be formally closed after settlement of all cheques and liabilities, and the mandate given to bankers shall stand revoked.'
};

/**
 * Constructs the specialized Cover Page for Supplementary Deed of Partnership
 * explicitly highlighting:
 * 1. "THIS IS A SUPPLEMENTARY DEED OF PARTNERSHIP"
 * 2. Particular points of amendment and reconstitution
 * 3. Principal deed reference and status of continuing, incoming, and retiring partners
 */
export function constructSupplementaryCoverPage(data: DeedFormData, isForWord: boolean = false): string {
  const supp = data.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const newFirmName = supp.changeFirmName && supp.newFirmName.trim() ? formatFirmName(supp.newFirmName) : firmName;
  const execCity = (data.execCity || supp.originalDeedCity || '_______________').toUpperCase();
  const execDateFormatted = data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026';
  const effectiveDateFormatted = supp.effectiveDate ? formatFormalDate(supp.effectiveDate) : execDateFormatted;
  const originalDeedDateFormatted = supp.originalDeedDate ? formatFormalDate(supp.originalDeedDate) : '____ DAY OF ____________, 20__';
  const originalDeedCity = (supp.originalDeedCity || execCity).toUpperCase();
  const regNumber = (supp.originalRegistrationNumber || '').trim().toUpperCase();
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();
  const newFirmAddress = supp.changeAddress && supp.newFirmAddress.trim() ? supp.newFirmAddress.toUpperCase() : firmAddress;
  const firmPan = (data.firmPan || '').toUpperCase();
  const coverTitle = (data.coverPageTitle || 'SUPPLEMENTARY DEED OF PARTNERSHIP').toUpperCase();
  const preparedBy = (data.coverPagePreparedBy || 'ADVOCATE & LEGAL CONSULTANT / CHARTERED ACCOUNTANT').toUpperCase();

  const retiringIds = supp.retiringPartnerIds || [];
  const existingPartners = data.partners || [];
  const retiringPartners = existingPartners.filter(p => retiringIds.includes(p.id));
  const continuingPartners = existingPartners.filter(p => !retiringIds.includes(p.id));
  const incomingPartners = supp.incomingPartners || [];
  const allPartnersInvolved = [...continuingPartners, ...incomingPartners, ...retiringPartners];

  // Specific particular points of amendment
  const points: string[] = [];
  points.push(`<b>PRINCIPAL PARTNERSHIP DEED:</b> Modification & Reconstitution of original Partnership Deed dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Registration No. <b>${regNumber}</b>)` : ''}.`);

  if (supp.priorDeeds && supp.priorDeeds.length > 0) {
    const priorDeedsList = supp.priorDeeds.map((d, idx) => {
      const dDate = d.executionDate ? formatFormalDate(d.executionDate) : 'Date Unspecified';
      const dReg = d.rofRegistrationNumber ? ` (Reg. No: <b>${d.rofRegistrationNumber}</b>)` : '';
      const dCity = d.executionCity ? ` at <b>${d.executionCity}</b>` : '';
      const dChanges = d.keyChangesSummary ? ` - <i>${d.keyChangesSummary}</i>` : '';
      return `<li style="margin-bottom: 4px;"><b>${d.deedLabel || `${getOrdinal(idx + 1)} Deed`}:</b> Dated <b>${dDate}</b>${dCity}${dReg}${dChanges}</li>`;
    }).join('');
    points.push(`<b>CHRONOLOGICAL CHAIN OF PRIOR DEEDS (${supp.priorDeeds.length} DEEDS RECORDED):</b><ul style="margin: 4px 0 2px 18px; padding: 0; font-size: 0.95em;">${priorDeedsList}</ul>`);
  }

  if (supp.changePartners && incomingPartners.length > 0) {
    const names = incomingPartners.map(p => formatPartnerNameWithPrefix(p)).join(', ');
    points.push(`<b>ADMISSION OF INCOMING PARTNER(S):</b> Induction and admission of <b>${names}</b> into the partnership w.e.f. <b>${effectiveDateFormatted}</b>.`);
  }

  if (supp.changePartners && retiringPartners.length > 0) {
    const names = retiringPartners.map(p => formatPartnerNameWithPrefix(p)).join(', ');
    points.push(`<b>RETIREMENT OF PARTNER(S):</b> Formal retirement of <b>${names}</b> from the partnership w.e.f. <b>${effectiveDateFormatted}</b> upon full and final settlement of capital, profits & goodwill.`);
  }

  points.push(`<b>REVISED PROFIT & LOSS SHARING:</b> Realignment and reconstitution of profit/loss sharing ratios among all continuing and incoming partners.`);

  if (supp.changeFirmName && supp.newFirmName.trim()) {
    points.push(`<b>AMENDMENT OF FIRM NAME:</b> Name of firm amended from <b>${firmName}</b> to <b>${newFirmName}</b>.`);
  }

  if (supp.changeAddress && supp.newFirmAddress.trim()) {
    points.push(`<b>CHANGE OF PLACE OF BUSINESS:</b> Principal place of business shifted and relocated to <b>${newFirmAddress}</b>.`);
  }

  if (supp.changeObjects && supp.newObjects.trim()) {
    points.push(`<b>ALTERATION OF BUSINESS ACTIVITIES:</b> Expansion and amendment of business objects and commercial operations.`);
  }

  if (supp.changeRemuneration) {
    points.push(`<b>WORKING PARTNERS' REMUNERATION & INTEREST:</b> Revised in accordance with Section 40(b) of the Income-tax Act, 2025.`);
  }

  if (supp.changeOtherConditions) {
    points.push(`<b>BANKING OPERATIONS & MANDATES:</b> Reconstitution of bank operating instructions and authorized signatories.`);
  }

  points.push(`<b>RATIFICATION & CONTINUANCE:</b> Save as amended herein, all covenants, clauses, and terms of the Principal Deed dated ${originalDeedDateFormatted} remain unaltered, valid, and in full legal force.`);

  if (isForWord) {
    const wordPointsHtml = points.map(pt => `
      <p style="margin: 0 0 4pt 0; line-height: 1.35; text-align: left; font-size: 9.0pt; font-family: 'Times New Roman', Times, serif;">
        <span style="font-weight: bold; color: #000000;">■</span> ${pt}
      </p>
    `).join('');

    const wordPartnersRows = allPartnersInvolved.map((p, idx) => {
      const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
      const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
      const parentName = p.parentName ? p.parentName.toUpperCase() : '__________________';
      const panStr = p.pan ? ` | PAN: ${p.pan.toUpperCase()}` : '';

      let roleBadge = 'CONTINUING PARTNER';
      let shareText = '';

      if (incomingPartners.some(ip => ip.id === p.id)) {
        roleBadge = 'INCOMING PARTNER (ADMITTED)';
        const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
        shareText = ` (${rev || '0'}% Revised Share)`;
      } else if (retiringPartners.some(rp => rp.id === p.id)) {
        roleBadge = 'RETIRING PARTNER (RETIRED)';
        shareText = ` (Former ${p.profitShare || '0'}% Share - Retired)`;
      } else {
        const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
        shareText = ` (${rev || '0'}% Revised Share)`;
      }

      return `
        <tr>
          <td width="30" align="center" valign="top" style="border: 1pt solid #000000; padding: 4pt; font-weight: bold; font-size: 9pt; font-family: 'Times New Roman', Times, serif;">${idx + 1}.</td>
          <td valign="top" style="border: 1pt solid #000000; padding: 4pt 6pt; text-align: left; font-size: 9pt; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 2pt 0;"><b>${formattedName}</b>${shareText} &mdash; <b>[${roleBadge}]</b></p>
            <p style="margin: 0; color: #333333; font-size: 8.5pt;">${relWord} Sh. ${parentName}${panStr}</p>
          </td>
        </tr>
      `;
    }).join('');

    const registrationBoxWord = data.includeCoverRegistrationBox ? `
      <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 10pt; border: 1pt solid #000000; font-family: 'Times New Roman', Times, serif;">
        <tr style="background-color: #f1f5f9;">
          <td colspan="3" align="center" style="border: 1pt solid #000000; font-weight: bold; font-size: 8.5pt; text-transform: uppercase;">
            FOR OFFICIAL USE & REGISTRATION AT REGISTRAR OF FIRMS / SUB-REGISTRAR
          </td>
        </tr>
        <tr>
          <td width="33%" style="border: 1pt solid #000000; font-size: 8pt;"><b>REGISTRATION NO:</b> ____________</td>
          <td width="33%" style="border: 1pt solid #000000; font-size: 8pt;"><b>BOOK NO:</b> ____________</td>
          <td width="34%" style="border: 1pt solid #000000; font-size: 8pt;"><b>VOLUME / PAGE:</b> ____________</td>
        </tr>
        <tr>
          <td style="border: 1pt solid #000000; font-size: 8pt;"><b>DATE OF FILING:</b> ____________</td>
          <td colspan="2" style="border: 1pt solid #000000; font-size: 8pt;"><b>SEAL & SIGNATURE:</b> ________________________</td>
        </tr>
      </table>
    ` : '';

    return `
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; height: 100%; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
      <tr>
        <td align="center" valign="middle" style="padding: 10pt 8pt;">
          <table width="100%" border="1" cellpadding="14" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 2.25pt double #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
            <tr>
              <td align="center" valign="top" style="padding: 18pt 16pt; font-family: 'Times New Roman', Times, serif;">
                
                <!-- TOP EMBLEM & PROMINENT NOTICE -->
                <p style="font-size: 8.5pt; font-weight: bold; letter-spacing: 1.5pt; text-transform: uppercase; color: #1e293b; margin: 0 0 2pt 0; text-align: center;">
                  ★ THIS IS A FORMAL SUPPLEMENTARY DEED OF PARTNERSHIP ★
                </p>
                <p style="font-size: 8pt; color: #475569; letter-spacing: 0.5pt; text-transform: uppercase; margin: 0 0 10pt 0; text-align: center;">
                  (DEED OF RECONSTITUTION, AMENDMENT & MODIFICATION OF PARTNERSHIP FIRM)
                </p>

                <!-- ORNAMENTAL DIVIDER -->
                <p style="font-size: 10pt; letter-spacing: 4pt; color: #000000; margin: 0 0 10pt 0; text-align: center;">
                  ═══════════════════════════════════════
                </p>

                <!-- PRIMARY DOCUMENT TITLE -->
                <h1 style="font-size: 20pt; font-weight: bold; letter-spacing: 1.5pt; text-transform: uppercase; margin: 0 0 4pt 0; text-align: center; color: #000000; line-height: 1.2;">
                  ${coverTitle}
                </h1>
                <p style="font-size: 10.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 1pt; margin: 0 0 14pt 0; text-align: center; color: #334155;">
                  UNDER SECTION 31, 32 & CHAPTER VI OF THE INDIAN PARTNERSHIP ACT, 1932
                </p>

                <!-- FIRM NAME BLOCK -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin: 0 0 12pt 0;">
                  <tr>
                    <td align="center" style="padding: 6pt 10pt; background-color: #f8fafc; border: 1.5pt solid #000000;">
                      <p style="font-size: 8.5pt; letter-spacing: 1.5pt; text-transform: uppercase; color: #475569; margin: 0 0 2pt 0; text-align: center; font-weight: bold;">
                        IN RESPECT OF THE PARTNERSHIP FIRM
                      </p>
                      <p style="font-size: 16pt; font-weight: bold; letter-spacing: 1.2pt; text-transform: uppercase; margin: 0; text-align: center; color: #000000;">
                        ${supp.changeFirmName && supp.newFirmName.trim() ? newFirmName : firmName}
                      </p>
                      ${supp.changeFirmName && supp.newFirmName.trim() ? `<p style="font-size: 8pt; color: #64748b; margin: 2pt 0 0 0; text-align: center;">(FORMERLY KNOWN AS: ${firmName})</p>` : ''}
                      <p style="font-size: 8.5pt; color: #334155; margin: 3pt 0 0 0; text-align: center;">
                        <b>PAN:</b> ${firmPan || 'APPLIED FOR'}&nbsp;&nbsp;|&nbsp;&nbsp;<b>PRINCIPAL PLACE:</b> ${newFirmAddress}
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- PARTICULAR POINTS OF SUPPLEMENTARY DEED -->
                <table width="100%" border="1" cellpadding="8" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 12pt; border: 1.5pt solid #000000;">
                  <tr style="background-color: #f1f5f9;">
                    <td align="center" style="border: 1pt solid #000000; padding: 4pt 8pt; font-weight: bold; font-size: 9.5pt; text-transform: uppercase; letter-spacing: 0.5pt; color: #0f172a;">
                      ★ NATURE & PARTICULAR POINTS OF AMENDMENT / RECONSTITUTION ★
                    </td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; padding: 7pt 10pt; background-color: #ffffff;">
                      ${wordPointsHtml}
                    </td>
                  </tr>
                </table>

                <!-- PARTNERS SUMMARY TABLE -->
                <p style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8pt; margin: 0 0 4pt 0; text-align: left; color: #000000;">
                  PARTNERS CONCERNED & RECONSTITUTED:
                </p>
                <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 10pt; border: 1pt solid #000000;">
                  ${wordPartnersRows}
                </table>

                <!-- KEY METADATA PARTICULARS -->
                <table width="100%" border="1" cellpadding="5" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 8pt; border: 1pt solid #000000; font-size: 8.5pt;">
                  <tr>
                    <td width="30%" style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">DOCUMENT NATURE:</td>
                    <td width="70%" style="border: 1pt solid #000000;"><b>SUPPLEMENTARY DEED OF PARTNERSHIP</b> (AMENDMENT & RECONSTITUTION)</td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">PRINCIPAL DEED REFERENCE:</td>
                    <td style="border: 1pt solid #000000;">Dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Reg. No. ${regNumber})` : ''}</td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">EFFECTIVE DATE:</td>
                    <td style="border: 1pt solid #000000;"><b>${effectiveDateFormatted}</b></td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">EXECUTION DATE & PLACE:</td>
                    <td style="border: 1pt solid #000000;"><b>${execDateFormatted}</b> at <b>${execCity}</b></td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">PREPARED & DRAFTED BY:</td>
                    <td style="border: 1pt solid #000000; font-weight: bold;">${preparedBy}</td>
                  </tr>
                </table>

                ${registrationBoxWord}

              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    `;
  }

  // HTML / Preview Mode
  const htmlPoints = points.map(pt => `
    <div style="margin-bottom: 5px; line-height: 1.42; text-align: left; font-size: 9.5pt;">
      <span style="color: #0f172a; font-weight: bold; margin-right: 4px;">■</span> ${pt}
    </div>
  `).join('');

  const htmlPartnersRows = allPartnersInvolved.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '__________________';
    const panStr = p.pan ? ` | PAN: ${p.pan.toUpperCase()}` : '';

    let roleBadge = 'CONTINUING PARTNER';
    let roleBg = '#eff6ff';
    let roleColor = '#1d4ed8';
    let shareText = '';

    if (incomingPartners.some(ip => ip.id === p.id)) {
      roleBadge = 'INCOMING PARTNER (ADMITTED)';
      roleBg = '#ecfdf5';
      roleColor = '#047857';
      const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
      shareText = ` (${rev || '0'}% Revised Share)`;
    } else if (retiringPartners.some(rp => rp.id === p.id)) {
      roleBadge = 'RETIRING PARTNER (RETIRED)';
      roleBg = '#fef2f2';
      roleColor = '#b91c1c';
      shareText = ` (Former ${p.profitShare || '0'}% Share - Retired)`;
    } else {
      const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
      shareText = ` (${rev || '0'}% Revised Share)`;
    }

    return `
      <tr>
        <td width="36" style="padding: 6px 8px; vertical-align: top; font-weight: bold; width: 36px; text-align: center; border: 1px solid #94a3b8; font-size: 9.5pt;">${idx + 1}.</td>
        <td style="padding: 6px 10px; vertical-align: top; text-align: left; border: 1px solid #94a3b8;">
          <div style="font-weight: bold; font-size: 10.5pt; color: #000000; display: flex; align-items: center; justify-content: space-between;">
            <span>${formattedName} <span style="font-weight: normal; font-size: 9.5pt; color: #475569;">${shareText}</span></span>
            <span style="font-size: 8pt; font-weight: bold; padding: 2px 6px; background-color: ${roleBg}; color: ${roleColor}; border: 1px solid ${roleColor}; border-radius: 3px; text-transform: uppercase;">
              ${roleBadge}
            </span>
          </div>
          <div style="font-size: 9pt; color: #1e293b; margin-top: 2px;">
            ${relWord} Sh. ${parentName}${panStr}
          </div>
          <div style="font-size: 8.5pt; color: #475569; margin-top: 2px; line-height: 1.35;">
            Address: ${p.address ? p.address.toUpperCase() : '__________________'}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  const registrationBoxHtml = data.includeCoverRegistrationBox ? `
    <div style="border: 1.5px solid #000000; background-color: #f8fafc; padding: 8px 12px; font-size: 8.5pt; text-align: left; margin-top: 14px; margin-bottom: 8px;">
      <div style="font-weight: bold; color: #000000; margin-bottom: 5px; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;">
        ★ FOR OFFICIAL USE & REGISTRATION AT REGISTRAR OF FIRMS / SUB-REGISTRAR ★
      </div>
      <table width="100%" border="0" cellpadding="2" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 8.5pt; color: #334155;">
        <tr>
          <td width="33%"><b>REGISTRATION NO:</b> ____________</td>
          <td width="33%"><b>BOOK NO:</b> ____________</td>
          <td width="34%"><b>VOLUME / PAGE:</b> ____________</td>
        </tr>
        <tr>
          <td><b>DATE OF FILING:</b> ____________</td>
          <td colspan="2"><b>SEAL & SIGNATURE:</b> ________________________</td>
        </tr>
      </table>
    </div>
  ` : '';

  return `
  <div class="deed-block deed-cover-page" style="break-after: page; page-break-after: always; padding: 8px 0 20px 0;">
    <div style="border: 3.5px double #000000; padding: 28px 24px; background-color: #ffffff; min-height: 980px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between;">
      
      <div>
        <!-- TOP PROMINENT HEADER -->
        <div style="text-align: center; margin-bottom: 8px;">
          <div style="font-size: 9pt; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; color: #0f172a;">
            ★ THIS IS A FORMAL SUPPLEMENTARY DEED OF PARTNERSHIP ★
          </div>
          <div style="font-size: 8pt; color: #475569; letter-spacing: 0.5px; text-transform: uppercase; margin-top: 2px;">
            (DEED OF RECONSTITUTION, AMENDMENT & MODIFICATION OF PARTNERSHIP FIRM)
          </div>
        </div>

        <div style="text-align: center; font-size: 11pt; letter-spacing: 6px; color: #000000; margin-bottom: 12px;">
          ❖ ❖ ❖
        </div>

        <!-- MAIN TITLE -->
        <div style="text-align: center; margin-bottom: 14px;">
          <h1 style="font-size: 20pt; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; margin: 0 0 4px 0; line-height: 1.25; color: #000000;">
            ${coverTitle}
          </h1>
          <p style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8px; margin: 0; color: #334155;">
            UNDER THE INDIAN PARTNERSHIP ACT, 1932
          </p>
        </div>

        <!-- FIRM NAME BOX -->
        <div style="background-color: #f8fafc; border: 1.5px solid #000000; padding: 10px 14px; text-align: center; margin-bottom: 14px;">
          <div style="font-size: 8.5pt; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: #475569; margin-bottom: 2px;">
            IN RESPECT OF THE PARTNERSHIP FIRM
          </div>
          <div style="font-size: 16pt; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: #000000;">
            ${supp.changeFirmName && supp.newFirmName.trim() ? newFirmName : firmName}
          </div>
          ${supp.changeFirmName && supp.newFirmName.trim() ? `<div style="font-size: 8.5pt; color: #64748b; margin-top: 2px;">(FORMERLY KNOWN AS: ${firmName})</div>` : ''}
          <div style="font-size: 9pt; color: #334155; margin-top: 4px;">
            <b>PAN:</b> ${firmPan || 'APPLIED FOR'}&nbsp;&nbsp;|&nbsp;&nbsp;<b>PRINCIPAL PLACE:</b> ${newFirmAddress}
          </div>
        </div>

        <!-- NATURE & PARTICULAR POINTS OF AMENDMENT / RECONSTITUTION -->
        <div style="border: 1.5px solid #000000; background-color: #ffffff; padding: 10px 12px; margin-bottom: 14px; text-align: left;">
          <div style="font-weight: bold; font-size: 9.5pt; color: #0f172a; text-transform: uppercase; text-decoration: underline; margin-bottom: 6px; text-align: center; letter-spacing: 0.5px;">
            ★ NATURE & PARTICULAR POINTS OF AMENDMENT / RECONSTITUTION ★
          </div>
          ${htmlPoints}
        </div>

        <!-- PARTNERS SUMMARY -->
        <div style="margin-bottom: 14px;">
          <div style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 5px; color: #000000; text-align: left;">
            PARTNERS CONCERNED & RECONSTITUTED:
          </div>
          <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1px solid #94a3b8;">
            ${htmlPartnersRows}
          </table>
        </div>

        <!-- KEY METADATA PARTICULARS TABLE -->
        <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1.5px solid #000000; font-size: 9pt; margin-top: 10px;">
          <tr>
            <td width="32%" style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">DOCUMENT NATURE:</td>
            <td width="68%" style="border: 1px solid #000000; text-align: left;"><b>SUPPLEMENTARY DEED OF PARTNERSHIP</b> (AMENDMENT & RECONSTITUTION)</td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">PRINCIPAL DEED REFERENCE:</td>
            <td style="border: 1px solid #000000; text-align: left;">Dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Reg. No. ${regNumber})` : ''}</td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">EFFECTIVE DATE:</td>
            <td style="border: 1px solid #000000; text-align: left;"><b>${effectiveDateFormatted}</b></td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">EXECUTION DATE & PLACE:</td>
            <td style="border: 1px solid #000000; text-align: left;"><b>${execDateFormatted}</b> at <b>${execCity}</b></td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">PREPARED & DRAFTED BY:</td>
            <td style="border: 1px solid #000000; text-align: left; font-weight: bold;">${preparedBy}</td>
          </tr>
        </table>

        ${registrationBoxHtml}

      </div>

      <div style="text-align: center; font-size: 8pt; color: #64748b; margin-top: 14px; text-transform: uppercase; letter-spacing: 1px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
        Executed under the Provisions of the Indian Partnership Act, 1932 & Applicable Laws
      </div>

    </div>
  </div>
  `;
}

/**
 * Constructs the specialized Cover Page for Deed of Dissolution of Partnership
 * explicitly highlighting:
 * 1. "THIS IS A FORMAL DEED OF DISSOLUTION OF PARTNERSHIP"
 * 2. Particular points of dissolution, winding up, accounts settlement & custodian
 * 3. Principal deed reference and status of all dissolving partners
 */
export function constructDissolutionCoverPage(data: DeedFormData, isForWord: boolean = false): string {
  const diss = data.dissolutionConfig || DEFAULT_DISSOLUTION_CONFIG;
  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const execCity = (data.execCity || diss.originalDeedCity || '_______________').toUpperCase();
  const execDateFormatted = data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026';
  const dissolutionDateFormatted = diss.dissolutionDate ? formatFormalDate(diss.dissolutionDate) : execDateFormatted;
  const originalDeedDateFormatted = diss.originalDeedDate ? formatFormalDate(diss.originalDeedDate) : '____ DAY OF ____________, 20__';
  const originalDeedCity = (diss.originalDeedCity || execCity).toUpperCase();
  const regNumber = (diss.originalRegistrationNumber || '').trim().toUpperCase();
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();
  const firmPan = (data.firmPan || '').toUpperCase();
  const coverTitle = (data.coverPageTitle || 'DEED OF DISSOLUTION OF PARTNERSHIP FIRM').toUpperCase();
  const preparedBy = (data.coverPagePreparedBy || 'ADVOCATE & LEGAL CONSULTANT / CHARTERED ACCOUNTANT').toUpperCase();

  const allPartners = data.partners || [];

  let custodianName = diss.custodianPartnerName;
  if (!custodianName && diss.custodianPartnerId) {
    const matched = allPartners.find(p => p.id === diss.custodianPartnerId);
    if (matched) custodianName = formatPartnerNameWithPrefix(matched);
  }
  if (!custodianName && allPartners.length > 0) {
    custodianName = formatPartnerNameWithPrefix(allPartners[0]);
  }
  custodianName = (custodianName || 'DESIGNATED CUSTODIAN PARTNER').toUpperCase();

  let reasonSummary = 'Mutual consent and commercial agreement of all the partners';
  if (diss.dissolutionReason === 'completion_of_venture') {
    reasonSummary = 'Completion and fulfillment of the commercial project and venture';
  } else if (diss.dissolutionReason === 'retirement_no_substitute') {
    reasonSummary = 'Retirement of partner and mutual decision not to induct new partners';
  } else if (diss.dissolutionReason === 'custom' && diss.customReasonText.trim()) {
    reasonSummary = diss.customReasonText.trim();
  }

  const retentionYears = diss.recordsRetentionYears || '8';

  const points: string[] = [
    `<b>FORMAL DISSOLUTION OF FIRM:</b> Complete, formal dissolution and total cessation of business operations of <b>${firmName}</b> under Section 40 & 43 of the Indian Partnership Act, 1932.`,
    `<b>EFFECTIVE DATE OF DISSOLUTION:</b> Commercial business stands dissolved with effect from close of business hours on <b>${dissolutionDateFormatted}</b>.`,
    `<b>GROUNDS / CAUSE OF DISSOLUTION:</b> <b>${reasonSummary}</b>.`,
    `<b>REALIZATION OF ASSETS & DISCHARGE OF DEBTS:</b> Collection of receivables, realization of assets, and complete discharge of third-party debts and statutory dues (GST & Income Tax).`,
    `<b>DISTRIBUTION OF NET SURPLUS:</b> Division of remaining surplus strictly in proportion to partners' capital accounts as per finalized balance sheet.`,
    `<b>SAFE CUSTODY OF RECORDS:</b> Books of accounts, tax returns, and statutory records entrusted to Partner <b>${custodianName}</b> for mandatory statutory preservation of <b>${retentionYears} YEARS</b>.`,
    `<b>STATUTORY NOTICES & FILING:</b> Filing statutory notice of dissolution in Form E / Form 5 with Registrar of Firms, publication in Official Gazette and daily newspapers, and closing of bank accounts.`,
    `<b>PRINCIPAL PARTNERSHIP DEED:</b> Originally constituted vide Partnership Deed dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Registration No. <b>${regNumber}</b>)` : ''}.`
  ];

  if (diss.priorDeeds && diss.priorDeeds.length > 0) {
    const priorDeedsList = diss.priorDeeds.map((d, idx) => {
      const dDate = d.executionDate ? formatFormalDate(d.executionDate) : 'Date Unspecified';
      const dReg = d.rofRegistrationNumber ? ` (Reg. No: <b>${d.rofRegistrationNumber}</b>)` : '';
      const dCity = d.executionCity ? ` at <b>${d.executionCity}</b>` : '';
      const dChanges = d.keyChangesSummary ? ` - <i>${d.keyChangesSummary}</i>` : '';
      return `<li style="margin-bottom: 4px;"><b>${d.deedLabel || `${getOrdinal(idx + 1)} Deed`}:</b> Dated <b>${dDate}</b>${dCity}${dReg}${dChanges}</li>`;
    }).join('');
    points.push(`<b>CHRONOLOGICAL CHAIN OF PRIOR DEEDS (${diss.priorDeeds.length} DEEDS RECORDED):</b><ul style="margin: 4px 0 2px 18px; padding: 0; font-size: 0.95em;">${priorDeedsList}</ul>`);
  }

  if (isForWord) {
    const wordPointsHtml = points.map(pt => `
      <p style="margin: 0 0 4pt 0; line-height: 1.35; text-align: left; font-size: 9.0pt; font-family: 'Times New Roman', Times, serif;">
        <span style="font-weight: bold; color: #000000;">■</span> ${pt}
      </p>
    `).join('');

    const wordPartnersRows = allPartners.map((p, idx) => {
      const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
      const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
      const parentName = p.parentName ? p.parentName.toUpperCase() : '__________________';
      const panStr = p.pan ? ` | PAN: ${p.pan.toUpperCase()}` : '';

      return `
        <tr>
          <td width="30" align="center" valign="top" style="border: 1pt solid #000000; padding: 4pt; font-weight: bold; font-size: 9pt; font-family: 'Times New Roman', Times, serif;">${idx + 1}.</td>
          <td valign="top" style="border: 1pt solid #000000; padding: 4pt 6pt; text-align: left; font-size: 9pt; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 2pt 0;"><b>${formattedName}</b> (${p.profitShare || '0'}% Share) &mdash; <b>[DISSOLVING PARTNER]</b></p>
            <p style="margin: 0; color: #333333; font-size: 8.5pt;">${relWord} Sh. ${parentName}${panStr}</p>
          </td>
        </tr>
      `;
    }).join('');

    const registrationBoxWord = data.includeCoverRegistrationBox ? `
      <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 10pt; border: 1pt solid #000000; font-family: 'Times New Roman', Times, serif;">
        <tr style="background-color: #f1f5f9;">
          <td colspan="3" align="center" style="border: 1pt solid #000000; font-weight: bold; font-size: 8.5pt; text-transform: uppercase;">
            FOR OFFICIAL USE & REGISTRATION AT REGISTRAR OF FIRMS / SUB-REGISTRAR
          </td>
        </tr>
        <tr>
          <td width="33%" style="border: 1pt solid #000000; font-size: 8pt;"><b>REGISTRATION NO:</b> ____________</td>
          <td width="33%" style="border: 1pt solid #000000; font-size: 8pt;"><b>BOOK NO:</b> ____________</td>
          <td width="34%" style="border: 1pt solid #000000; font-size: 8pt;"><b>VOLUME / PAGE:</b> ____________</td>
        </tr>
        <tr>
          <td style="border: 1pt solid #000000; font-size: 8pt;"><b>DATE OF FILING:</b> ____________</td>
          <td colspan="2" style="border: 1pt solid #000000; font-size: 8pt;"><b>SEAL & SIGNATURE:</b> ________________________</td>
        </tr>
      </table>
    ` : '';

    return `
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; height: 100%; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
      <tr>
        <td align="center" valign="middle" style="padding: 10pt 8pt;">
          <table width="100%" border="1" cellpadding="14" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 2.25pt double #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
            <tr>
              <td align="center" valign="top" style="padding: 18pt 16pt; font-family: 'Times New Roman', Times, serif;">
                
                <!-- TOP EMBLEM & PROMINENT NOTICE -->
                <p style="font-size: 8.5pt; font-weight: bold; letter-spacing: 1.5pt; text-transform: uppercase; color: #1e293b; margin: 0 0 2pt 0; text-align: center;">
                  ★ THIS IS A FORMAL DEED OF DISSOLUTION OF PARTNERSHIP ★
                </p>
                <p style="font-size: 8pt; color: #475569; letter-spacing: 0.5pt; text-transform: uppercase; margin: 0 0 10pt 0; text-align: center;">
                  (UNDER SECTION 40 & 43 OF THE INDIAN PARTNERSHIP ACT, 1932)
                </p>

                <!-- ORNAMENTAL DIVIDER -->
                <p style="font-size: 10pt; letter-spacing: 4pt; color: #000000; margin: 0 0 10pt 0; text-align: center;">
                  ═══════════════════════════════════════
                </p>

                <!-- PRIMARY DOCUMENT TITLE -->
                <h1 style="font-size: 20pt; font-weight: bold; letter-spacing: 1.5pt; text-transform: uppercase; margin: 0 0 4pt 0; text-align: center; color: #000000; line-height: 1.2;">
                  ${coverTitle}
                </h1>
                <p style="font-size: 10.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 1pt; margin: 0 0 14pt 0; text-align: center; color: #334155;">
                  WINDING UP, DISCHARGE OF LIABILITIES & FINAL SETTLEMENT
                </p>

                <!-- FIRM NAME BLOCK -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin: 0 0 12pt 0;">
                  <tr>
                    <td align="center" style="padding: 6pt 10pt; background-color: #f8fafc; border: 1.5pt solid #000000;">
                      <p style="font-size: 8.5pt; letter-spacing: 1.5pt; text-transform: uppercase; color: #475569; margin: 0 0 2pt 0; text-align: center; font-weight: bold;">
                        NAME OF DISSOLVED FIRM
                      </p>
                      <p style="font-size: 16pt; font-weight: bold; letter-spacing: 1.2pt; text-transform: uppercase; margin: 0; text-align: center; color: #000000;">
                        ${firmName}
                      </p>
                      <p style="font-size: 8.5pt; color: #334155; margin: 3pt 0 0 0; text-align: center;">
                        <b>PAN:</b> ${firmPan || 'APPLIED FOR'}&nbsp;&nbsp;|&nbsp;&nbsp;<b>PRINCIPAL PLACE:</b> ${firmAddress}
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- PARTICULAR POINTS OF DISSOLUTION DEED -->
                <table width="100%" border="1" cellpadding="8" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 12pt; border: 1.5pt solid #000000;">
                  <tr style="background-color: #f1f5f9;">
                    <td align="center" style="border: 1pt solid #000000; padding: 4pt 8pt; font-weight: bold; font-size: 9.5pt; text-transform: uppercase; letter-spacing: 0.5pt; color: #0f172a;">
                      ★ PARTICULARS & GROUNDS OF DISSOLUTION OF FIRM ★
                    </td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; padding: 7pt 10pt; background-color: #ffffff;">
                      ${wordPointsHtml}
                    </td>
                  </tr>
                </table>

                <!-- PARTNERS SUMMARY TABLE -->
                <p style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8pt; margin: 0 0 4pt 0; text-align: left; color: #000000;">
                  DISSOLVING PARTNERS:
                </p>
                <table width="100%" border="1" cellpadding="4" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 10pt; border: 1pt solid #000000;">
                  ${wordPartnersRows}
                </table>

                <!-- KEY METADATA PARTICULARS -->
                <table width="100%" border="1" cellpadding="5" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 8pt; border: 1pt solid #000000; font-size: 8.5pt;">
                  <tr>
                    <td width="30%" style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">DOCUMENT NATURE:</td>
                    <td width="70%" style="border: 1pt solid #000000;"><b>DEED OF DISSOLUTION OF PARTNERSHIP FIRM</b></td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">PRINCIPAL DEED REFERENCE:</td>
                    <td style="border: 1pt solid #000000;">Dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Reg. No. ${regNumber})` : ''}</td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">DISSOLUTION EFFECTIVE DATE:</td>
                    <td style="border: 1pt solid #000000;"><b>${dissolutionDateFormatted}</b></td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">CUSTODIAN OF RECORDS:</td>
                    <td style="border: 1pt solid #000000; font-weight: bold;">${custodianName} (PRESERVATION FOR ${retentionYears} YEARS)</td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">EXECUTION DATE & PLACE:</td>
                    <td style="border: 1pt solid #000000;"><b>${execDateFormatted}</b> at <b>${execCity}</b></td>
                  </tr>
                  <tr>
                    <td style="border: 1pt solid #000000; background-color: #f8fafc; font-weight: bold;">PREPARED & DRAFTED BY:</td>
                    <td style="border: 1pt solid #000000; font-weight: bold;">${preparedBy}</td>
                  </tr>
                </table>

                ${registrationBoxWord}

              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    `;
  }

  // HTML / Preview Mode
  const htmlPoints = points.map(pt => `
    <div style="margin-bottom: 5px; line-height: 1.42; text-align: left; font-size: 9.5pt;">
      <span style="color: #0f172a; font-weight: bold; margin-right: 4px;">■</span> ${pt}
    </div>
  `).join('');

  const htmlPartnersRows = allPartners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '__________________';
    const panStr = p.pan ? ` | PAN: ${p.pan.toUpperCase()}` : '';

    return `
      <tr>
        <td width="36" style="padding: 6px 8px; vertical-align: top; font-weight: bold; width: 36px; text-align: center; border: 1px solid #94a3b8; font-size: 9.5pt;">${idx + 1}.</td>
        <td style="padding: 6px 10px; vertical-align: top; text-align: left; border: 1px solid #94a3b8;">
          <div style="font-weight: bold; font-size: 10.5pt; color: #000000; display: flex; align-items: center; justify-content: space-between;">
            <span>${formattedName} <span style="font-weight: normal; font-size: 9.5pt; color: #475569;">(${p.profitShare || '0'}% Share)</span></span>
            <span style="font-size: 8pt; font-weight: bold; padding: 2px 6px; background-color: #fef2f2; color: #b91c1c; border: 1px solid #b91c1c; border-radius: 3px; text-transform: uppercase;">
              DISSOLVING PARTNER
            </span>
          </div>
          <div style="font-size: 9pt; color: #1e293b; margin-top: 2px;">
            ${relWord} Sh. ${parentName}${panStr}
          </div>
          <div style="font-size: 8.5pt; color: #475569; margin-top: 2px; line-height: 1.35;">
            Address: ${p.address ? p.address.toUpperCase() : '__________________'}
          </div>
        </td>
      </tr>
    `;
  }).join('');

  const registrationBoxHtml = data.includeCoverRegistrationBox ? `
    <div style="border: 1.5px solid #000000; background-color: #f8fafc; padding: 8px 12px; font-size: 8.5pt; text-align: left; margin-top: 14px; margin-bottom: 8px;">
      <div style="font-weight: bold; color: #000000; margin-bottom: 5px; text-align: center; text-transform: uppercase; letter-spacing: 0.5px;">
        ★ FOR OFFICIAL USE & REGISTRATION AT REGISTRAR OF FIRMS / SUB-REGISTRAR ★
      </div>
      <table width="100%" border="0" cellpadding="2" cellspacing="0" style="width: 100%; border-collapse: collapse; font-size: 8.5pt; color: #334155;">
        <tr>
          <td width="33%"><b>REGISTRATION NO:</b> ____________</td>
          <td width="33%"><b>BOOK NO:</b> ____________</td>
          <td width="34%"><b>VOLUME / PAGE:</b> ____________</td>
        </tr>
        <tr>
          <td><b>DATE OF FILING:</b> ____________</td>
          <td colspan="2"><b>SEAL & SIGNATURE:</b> ________________________</td>
        </tr>
      </table>
    </div>
  ` : '';

  return `
  <div class="deed-block deed-cover-page" style="break-after: page; page-break-after: always; padding: 8px 0 20px 0;">
    <div style="border: 3.5px double #000000; padding: 28px 24px; background-color: #ffffff; min-height: 980px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between;">
      
      <div>
        <!-- TOP PROMINENT HEADER -->
        <div style="text-align: center; margin-bottom: 8px;">
          <div style="font-size: 9pt; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; color: #0f172a;">
            ★ THIS IS A FORMAL DEED OF DISSOLUTION OF PARTNERSHIP ★
          </div>
          <div style="font-size: 8pt; color: #475569; letter-spacing: 0.5px; text-transform: uppercase; margin-top: 2px;">
            (UNDER SECTION 40 & 43 OF THE INDIAN PARTNERSHIP ACT, 1932)
          </div>
        </div>

        <div style="text-align: center; font-size: 11pt; letter-spacing: 6px; color: #000000; margin-bottom: 12px;">
          ❖ ❖ ❖
        </div>

        <!-- MAIN TITLE -->
        <div style="text-align: center; margin-bottom: 14px;">
          <h1 style="font-size: 20pt; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; margin: 0 0 4px 0; line-height: 1.25; color: #000000;">
            ${coverTitle}
          </h1>
          <p style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8px; margin: 0; color: #334155;">
            WINDING UP & FINAL SETTLEMENT OF PARTNERSHIP
          </p>
        </div>

        <!-- FIRM NAME BOX -->
        <div style="background-color: #f8fafc; border: 1.5px solid #000000; padding: 10px 14px; text-align: center; margin-bottom: 14px;">
          <div style="font-size: 8.5pt; font-weight: bold; letter-spacing: 1.5px; text-transform: uppercase; color: #475569; margin-bottom: 2px;">
            NAME OF DISSOLVED PARTNERSHIP FIRM
          </div>
          <div style="font-size: 16pt; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: #000000;">
            ${firmName}
          </div>
          <div style="font-size: 9pt; color: #334155; margin-top: 4px;">
            <b>PAN:</b> ${firmPan || 'APPLIED FOR'}&nbsp;&nbsp;|&nbsp;&nbsp;<b>PRINCIPAL PLACE:</b> ${firmAddress}
          </div>
        </div>

        <!-- PARTICULARS & GROUNDS OF DISSOLUTION OF FIRM -->
        <div style="border: 1.5px solid #000000; background-color: #ffffff; padding: 10px 12px; margin-bottom: 14px; text-align: left;">
          <div style="font-weight: bold; font-size: 9.5pt; color: #0f172a; text-transform: uppercase; text-decoration: underline; margin-bottom: 6px; text-align: center; letter-spacing: 0.5px;">
            ★ PARTICULARS & GROUNDS OF DISSOLUTION OF FIRM ★
          </div>
          ${htmlPoints}
        </div>

        <!-- PARTNERS SUMMARY -->
        <div style="margin-bottom: 14px;">
          <div style="font-size: 9.5pt; font-weight: bold; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 5px; color: #000000; text-align: left;">
            DISSOLVING PARTNERS:
          </div>
          <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1px solid #94a3b8;">
            ${htmlPartnersRows}
          </table>
        </div>

        <!-- KEY METADATA PARTICULARS TABLE -->
        <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; border: 1.5px solid #000000; font-size: 9pt; margin-top: 10px;">
          <tr>
            <td width="32%" style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">DOCUMENT NATURE:</td>
            <td width="68%" style="border: 1px solid #000000; text-align: left;"><b>DEED OF DISSOLUTION OF PARTNERSHIP FIRM</b></td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">PRINCIPAL DEED REFERENCE:</td>
            <td style="border: 1px solid #000000; text-align: left;">Dated <b>${originalDeedDateFormatted}</b> executed at <b>${originalDeedCity}</b>${regNumber ? ` (Reg. No. ${regNumber})` : ''}</td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">DISSOLUTION EFFECTIVE DATE:</td>
            <td style="border: 1px solid #000000; text-align: left;"><b>${dissolutionDateFormatted}</b></td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">CUSTODIAN OF RECORDS:</td>
            <td style="border: 1px solid #000000; text-align: left; font-weight: bold;">${custodianName} (PRESERVATION FOR ${retentionYears} YEARS)</td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">EXECUTION DATE & PLACE:</td>
            <td style="border: 1px solid #000000; text-align: left;"><b>${execDateFormatted}</b> at <b>${execCity}</b></td>
          </tr>
          <tr>
            <td style="border: 1px solid #000000; background-color: #f8fafc; font-weight: bold; text-align: left;">PREPARED & DRAFTED BY:</td>
            <td style="border: 1px solid #000000; text-align: left; font-weight: bold;">${preparedBy}</td>
          </tr>
        </table>

        ${registrationBoxHtml}

      </div>

      <div style="text-align: center; font-size: 8pt; color: #64748b; margin-top: 14px; text-transform: uppercase; letter-spacing: 1px; border-top: 1px solid #e2e8f0; padding-top: 8px;">
        Executed under Section 40 & 43 of the Indian Partnership Act, 1932 & Applicable Indian Laws
      </div>

    </div>
  </div>
  `;
}

// Construct Supplementary Deed Body
export function constructSupplementaryDeedBody(
  data: DeedFormData,
  isForWord: boolean = false,
  includeCover: boolean = true,
  includeKyc: boolean = true
): string {
  const supp = data.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
  const execCity = (data.execCity || supp.originalDeedCity || '_______________').toUpperCase();
  const execDateFormatted = data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026';
  const effectiveDateFormatted = supp.effectiveDate ? formatFormalDate(supp.effectiveDate) : execDateFormatted;
  const originalDeedDateFormatted = supp.originalDeedDate ? formatFormalDate(supp.originalDeedDate) : '____ DAY OF ____________, 20__';
  const originalDeedCity = (supp.originalDeedCity || execCity).toUpperCase();
  const regNumber = (supp.originalRegistrationNumber || '').trim().toUpperCase();

  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const newFirmName = supp.changeFirmName && supp.newFirmName.trim() ? formatFirmName(supp.newFirmName) : firmName;
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();
  const newFirmAddress = supp.changeAddress && supp.newFirmAddress.trim() ? supp.newFirmAddress.toUpperCase() : firmAddress;

  const pageBreaks = data.pageBreakBeforeClauses || [];
  const isSigBreak = data.signaturePageBreak === 'newPage' || pageBreaks.includes('signatures');
  const sigBreakTag = isForWord
    ? (isSigBreak ? '<p class="MsoNormal" style="page-break-before:always;mso-break-type:section-break;margin:0;padding:0;font-size:1pt;line-height:1pt;">&nbsp;</p>' : '')
    : '';
  const sigBreakClass = (!isForWord && isSigBreak) ? ' page-break-before' : '';

  // Segregate Partners: Continuing, Retiring, Incoming
  const retiringIds = supp.retiringPartnerIds || [];
  const existingPartners = data.partners || [];
  const retiringPartners = existingPartners.filter(p => retiringIds.includes(p.id));
  const continuingPartners = existingPartners.filter(p => !retiringIds.includes(p.id));
  const incomingPartners = supp.incomingPartners || [];
  const activePartners = [...continuingPartners, ...incomingPartners];

  // Party Introduction
  let partyIndex = 1;
  const partiesIntroList: string[] = [];

  continuingPartners.forEach((p) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${partyIndex}`;
    const relWord = p.relationType === 'HUSBAND' ? 'Wife of' : 'Son of / Daughter of';
    partiesIntroList.push(
      `<div style="margin-bottom: 10px; text-align: justify; line-height: 1.65;"><b>${formattedName}</b>, ${relWord} <b>${p.parentName || '________________'}</b>, aged <b>${p.age || '___'} YEARS</b>, having PAN <b>${p.pan || 'APPLIED FOR'}</b>, residing at <b>${p.address || '________________'}</b> (hereinafter referred to as the party of the <b>${getOrdinal(partyIndex++)} PART</b> / <b>CONTINUING PARTNER</b>)</div>`
    );
  });

  incomingPartners.forEach((p) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `NEW PARTNER ${partyIndex}`;
    const relWord = p.relationType === 'HUSBAND' ? 'Wife of' : 'Son of / Daughter of';
    partiesIntroList.push(
      `<div style="margin-bottom: 10px; text-align: justify; line-height: 1.65;"><b>${formattedName}</b>, ${relWord} <b>${p.parentName || '________________'}</b>, aged <b>${p.age || '___'} YEARS</b>, having PAN <b>${p.pan || 'APPLIED FOR'}</b>, residing at <b>${p.address || '________________'}</b> (hereinafter referred to as the party of the <b>${getOrdinal(partyIndex++)} PART</b> / <b>INCOMING PARTNER</b>)</div>`
    );
  });

  retiringPartners.forEach((p) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `RETIRING PARTNER ${partyIndex}`;
    const relWord = p.relationType === 'HUSBAND' ? 'Wife of' : 'Son of / Daughter of';
    partiesIntroList.push(
      `<div style="margin-bottom: 10px; text-align: justify; line-height: 1.65;"><b>${formattedName}</b>, ${relWord} <b>${p.parentName || '________________'}</b>, aged <b>${p.age || '___'} YEARS</b>, having PAN <b>${p.pan || 'APPLIED FOR'}</b>, residing at <b>${p.address || '________________'}</b> (hereinafter referred to as the party of the <b>${getOrdinal(partyIndex++)} PART</b> / <b>RETIRING PARTNER</b>)</div>`
    );
  });

  const partiesIntroHtml = partiesIntroList.join('<div style="text-align: center; font-weight: bold; margin: 10px 0;">AND</div>');

  // Recitals (WHEREAS clauses)
  const recitalsList: string[] = [];

  const priorDeeds = (supp.priorDeeds && supp.priorDeeds.length > 0) ? supp.priorDeeds : null;

  if (priorDeeds && priorDeeds.length > 0) {
    // 1. Original Deed Recital
    const originalDeed = priorDeeds.find(d => d.deedType === 'original') || priorDeeds[0];
    const origDateStr = originalDeed.executionDate ? formatFormalDate(originalDeed.executionDate) : originalDeedDateFormatted;
    const origCityStr = (originalDeed.executionCity || originalDeedCity).toUpperCase();
    const origRegStr = originalDeed.rofRegistrationNumber || regNumber;

    recitalsList.push(
      `WHEREAS the partnership business under the firm name and style of <b>${firmName}</b> having its principal place of business at <b>${firmAddress}</b> was originally constituted under and by virtue of a Deed of Partnership executed on <b>${origDateStr}</b> at <b>${origCityStr}</b>${origRegStr ? ` (registered with the Registrar of Firms having Registration / Diary No. <b>${origRegStr}</b>)` : ''} (hereinafter referred to as the <b>"ORIGINAL PARTNERSHIP DEED"</b>).`
    );

    // 2. Subsequent Prior Deeds Recitals
    const subsequentDeeds = priorDeeds.filter(d => d !== originalDeed);
    subsequentDeeds.forEach((d, idx) => {
      const dDateStr = d.executionDate ? formatFormalDate(d.executionDate) : '____ DAY OF ____________, 20__';
      const dEffDateStr = d.effectiveDate ? ` with effect from <b>${formatFormalDate(d.effectiveDate)}</b>` : '';
      const dCityStr = d.executionCity ? ` executed at <b>${d.executionCity.toUpperCase()}</b>` : '';
      const dRegStr = d.rofRegistrationNumber ? ` (Registration No. <b>${d.rofRegistrationNumber}</b>)` : '';
      const dChangesStr = d.keyChangesSummary || 'the terms and covenants of the partnership were altered and reconstituted';

      recitalsList.push(
        `AND WHEREAS subsequently vide ${d.deedLabel || `${getOrdinal(idx + 1)} Supplementary Deed of Partnership`} dated <b>${dDateStr}</b>${dCityStr}${dEffDateStr}${dRegStr}, the partnership firm was reconstituted and amended whereby <b>${dChangesStr}</b>.`
      );
    });

    recitalsList.push(
      `AND WHEREAS pursuant to the said Original Partnership Deed and the subsequent Supplementary Deeds aforesaid, the business of the partnership firm has been continuously and lawfully carried on up to the date hereof under the said terms and covenants.`
    );
  } else {
    // Single / Default original deed recital
    recitalsList.push(
      `WHEREAS the parties hereto (or the Continuing and Retiring Partners) have been carrying on the business of partnership under the firm name and style of <b>${firmName}</b> having its principal place of business at <b>${firmAddress}</b> under and by virtue of a Deed of Partnership executed on <b>${originalDeedDateFormatted}</b> at <b>${originalDeedCity}</b> (hereinafter referred to as the <b>"PRINCIPAL DEED"</b>).`
    );

    if (regNumber) {
      recitalsList.push(
        `AND WHEREAS the said partnership firm was duly registered with the Registrar of Firms having Registration / Acknowledgement / Diary No. <b>${regNumber}</b>.`
      );
    }
  }

  if (supp.changePartners) {
    if (retiringPartners.length > 0) {
      const retiringNames = retiringPartners.map(p => `<b>${formatPartnerNameWithPrefix(p)}</b>`).join(', ');
      const retDate = supp.retirementEffectiveDate ? formatFormalDate(supp.retirementEffectiveDate) : effectiveDateFormatted;
      recitalsList.push(
        `AND WHEREAS ${retiringNames} has / have expressed the desire to retire from the partnership firm with effect from <b>${retDate}</b> owing to personal preoccupations, and the Continuing Partners have mutually consented and agreed to accept the said retirement and to continue the business of the firm.`
      );
    }
    if (incomingPartners.length > 0) {
      const incomingNames = incomingPartners.map(p => `<b>${formatPartnerNameWithPrefix(p)}</b>`).join(', ');
      const admDate = supp.admissionEffectiveDate ? formatFormalDate(supp.admissionEffectiveDate) : effectiveDateFormatted;
      recitalsList.push(
        `AND WHEREAS the existing partners have mutually decided, in the best commercial interest and expansion of the business of the firm, to admit ${incomingNames} as new partner(s) in the firm with effect from <b>${admDate}</b>, and the Incoming Partner(s) has / have consented to be admitted as partner(s) and to contribute agreed capital and skills.`
      );
    }
  }

  if (supp.changeClauses) {
    const clauseModSummary: string[] = [];
    if (supp.changeFirmName) clauseModSummary.push(`change of firm name to <b>${newFirmName}</b>`);
    if (supp.changeAddress) clauseModSummary.push(`change of principal place of business to <b>${newFirmAddress}</b>`);
    if (supp.changeObjects) clauseModSummary.push(`alteration and addition to the business objects`);
    if (clauseModSummary.length > 0) {
      recitalsList.push(
        `AND WHEREAS the partners have mutually agreed and resolved to effect certain alterations in the covenants of the Principal Deed, including ${clauseModSummary.join(', ')}.`
      );
    }
  }

  if (supp.changeRemuneration) {
    recitalsList.push(
      `AND WHEREAS the partners have mutually agreed to revise the terms of working partners' remuneration and interest on capital in accordance with Section 35(e) of the Income-tax Act, 2025.`
    );
  }

  if (supp.changeOtherConditions) {
    recitalsList.push(
      `AND WHEREAS the partners have mutually agreed to amend the operational banking covenants and special terms of the partnership.`
    );
  }

  recitalsList.push(
    `AND WHEREAS all the parties hereto are desirous of reducing into writing the agreed terms, conditions, modifications, admissions, and retirements by executing this Supplementary Deed of Partnership.`
  );

  const recitalsHtml = recitalsList.map(r => `<p class="deed-p" style="margin-bottom: 12px; text-align: justify; line-height: 1.65;">${r}</p>`).join('');

  // Operative Clauses
  let c = 1;
  const operativeClauses: string[] = [];

  // Clause 1: Effective Date
  operativeClauses.push(`
    <div class="clause-heading">${c++}. EFFECTIVE DATE OF MODIFICATION :-</div>
    <p class="deed-p">This Supplementary Deed of Partnership shall come into legal force and effect from <b>${effectiveDateFormatted}</b>, and all alterations, amendments, admissions, and retirements herein contained shall be deemed to be effective and binding as and from the said date.</p>
  `);

  // Clause 2: Retirement (if any)
  if (supp.changePartners && retiringPartners.length > 0) {
    const retiringNames = retiringPartners.map(p => `<b>${formatPartnerNameWithPrefix(p)}</b>`).join(' and ');
    const retDate = supp.retirementEffectiveDate ? formatFormalDate(supp.retirementEffectiveDate) : effectiveDateFormatted;
    operativeClauses.push(`
      <div class="clause-heading">${c++}. RETIREMENT OF PARTNER(S) AND DISCHARGE :-</div>
      <p class="deed-p">With effect from the close of business on <b>${retDate}</b>, ${retiringNames} ceases to be a partner in the firm M/S. ${firmName}.</p>
      <p class="deed-p">${supp.retirementSettlementTerms || 'The accounts of the Retiring Partner have been verified, settled and paid in full satisfaction of capital, profits, and goodwill. The Retiring Partner has no surviving right, title, interest or claim in the firm assets, contracts, or name.'}</p>
      <p class="deed-p">The Continuing Partners hereby jointly and severally indemnify and hold harmless the Retiring Partner against all debts, liabilities, contracts, and proceedings incurred or arising out of the firm after the effective date of retirement.</p>
    `);
  }

  // Clause 3: Admission (if any)
  if (supp.changePartners && incomingPartners.length > 0) {
    const incomingNames = incomingPartners.map(p => `<b>${formatPartnerNameWithPrefix(p)}</b>`).join(' and ');
    const admDate = supp.admissionEffectiveDate ? formatFormalDate(supp.admissionEffectiveDate) : effectiveDateFormatted;
    operativeClauses.push(`
      <div class="clause-heading">${c++}. ADMISSION OF INCOMING PARTNER(S) :-</div>
      <p class="deed-p">With effect from <b>${admDate}</b>, ${incomingNames} is / are hereby admitted as partner(s) in the firm with all statutory rights, duties, powers, and liabilities under the Indian Partnership Act, 1932.</p>
      <p class="deed-p">${supp.admissionTerms || 'The Incoming Partner has contributed capital as mutually agreed upon and agrees to be bound by the covenants, conditions, and provisions of the Principal Deed as modified by this Supplementary Deed.'}</p>
    `);
  }

  // Clause 4: Profit and Loss Sharing Ratio
  const profitTableRows = activePartners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const customShare = supp.revisedProfitShares?.[p.id];
    const share = customShare !== undefined && customShare !== '' ? customShare : (p.profitShare || '0');
    return `
      <tr>
        <td style="border: 1px solid #000; padding: 6px 8px; width: 12%; text-align: center;">${idx + 1}</td>
        <td style="border: 1px solid #000; padding: 6px 8px; width: 63%; text-align: left;"><b>${formattedName}</b></td>
        <td style="border: 1px solid #000; padding: 6px 8px; width: 25%; text-align: center;"><b>${share}%</b></td>
      </tr>
    `;
  }).join('');

  operativeClauses.push(`
    <div class="clause-heading">${c++}. REVISED PROFIT AND LOSS SHARING RATIO :-</div>
    <p class="deed-p">Clause relating to profit and loss sharing in the Principal Deed stands substituted and superseded. The net profit or loss of the firm after deducting all business expenses, interest on partner capital, and working partners' remuneration shall be shared and borne by the continuing and admitted partners in the following proportions:</p>
    <table class="deed-table" width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin: 10px 0;">
      <thead>
        <tr style="background-color: #f1f5f9;">
          <th style="border: 1px solid #000; padding: 6px 8px; text-align: center; width: 12%;">Sr. No.</th>
          <th style="border: 1px solid #000; padding: 6px 8px; text-align: left; width: 63%;">Name of Partner</th>
          <th style="border: 1px solid #000; padding: 6px 8px; text-align: center; width: 25%;">Revised Share (%)</th>
        </tr>
      </thead>
      <tbody>
        ${profitTableRows}
      </tbody>
    </table>
  `);

  // Clause 5: Remuneration (if enabled or default IT Act)
  if (supp.changeRemuneration) {
    const interestRate = supp.changeInterestRate && supp.revisedInterestRate ? supp.revisedInterestRate : (data.interestRate || '12%');
    const partnersWithSalary = (data.partners || []).filter(p => p.isWorking && p.salaryMonthly && parseInt(p.salaryMonthly, 10) > 0);

    let specificSalaryHtml = '';
    if (partnersWithSalary.length > 0) {
      const rows = partnersWithSalary.map((p, idx) => {
        const mSal = parseInt(p.salaryMonthly!, 10);
        const aSal = mSal * 12;
        const pName = `${p.titlePrefix || ''} ${p.name}`.trim();
        return `
          <tr>
            <td style="border: 1px solid #000000; padding: 5px 8px; text-align: center; vertical-align: middle;">${idx + 1}</td>
            <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; vertical-align: middle;">${pName}</td>
            <td style="border: 1px solid #000000; padding: 5px 8px; text-align: right; font-weight: bold; vertical-align: middle;">Rs. ${mSal.toLocaleString('en-IN')}/- per month</td>
            <td style="border: 1px solid #000000; padding: 5px 8px; text-align: right; vertical-align: middle;">Rs. ${aSal.toLocaleString('en-IN')}/- p.a.</td>
          </tr>
        `;
      }).join('');

      specificSalaryHtml = `
        <p class="deed-p" style="margin-top: 8px;"><b>(C) Specific Monthly Salary / Remuneration Entitlement:</b> Without prejudice to the aforesaid annual statutory ceilings, the following working partner(s) shall be entitled to draw fixed monthly remuneration / salary with effect from the effective date of this deed as follows: -</p>
        <table style="width: 100%; border-collapse: collapse; margin: 8px 0; border: 1.5px solid #000000; font-size: 10pt;">
          <thead>
            <tr style="background-color: #f1f5f9;">
              <th style="border: 1px solid #000000; padding: 5px 8px; text-align: center; width: 8%;">SR.</th>
              <th style="border: 1px solid #000000; padding: 5px 8px; text-align: left; width: 44%;">NAME OF WORKING PARTNER</th>
              <th style="border: 1px solid #000000; padding: 5px 8px; text-align: right; width: 24%;">MONTHLY SALARY</th>
              <th style="border: 1px solid #000000; padding: 5px 8px; text-align: right; width: 24%;">ANNUAL AMOUNT</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
        <p class="deed-p" style="margin-top: 4px; font-size: 10pt; color: #334155;">The aforesaid monthly payments shall remain adjustable against each partner's respective annual allowable remuneration entitlement at the close of each financial year.</p>
      `;
    }

    operativeClauses.push(`
      <div class="clause-heading">${c++}. REVISED REMUNERATION AND INTEREST ON CAPITAL :-</div>
      <p class="deed-p">The clause relating to remuneration and interest in the Principal Deed is hereby amended and substituted as follows:</p>
      <p class="deed-p"><b>(A) Interest on Capital:</b> The firm shall pay simple interest at a rate not exceeding <b>${interestRate}</b> per annum on the credit balances in the capital accounts of the partners in conformity with Section 35(e) of the Income-tax Act, 2025.</p>
      <p class="deed-p"><b>(B) Statutory Book Profit Framework:</b> All working partners who actively devote their time and attention to the conduct of the affairs of the firm shall be entitled to receive remuneration calculated in accordance with the statutory ceiling prescribed under Section 35(e) of the Income-tax Act, 2025 (or Section 40(b) of the Income-tax Act, 1961), computed as follows:</p>
      <ul style="margin: 6px 0 10px 20px; line-height: 1.6;">
        <li>On the first ₹6,00,000 of book profit or in case of loss: <b>₹3,00,000 or 90% of book profit</b>, whichever is higher.</li>
        <li>On the balance of book profit: <b>60% of book profit</b>.</li>
      </ul>
      <p class="deed-p">The total remuneration so computed shall be distributed among the working partners ${supp.remunDistribution === 'equal' ? 'equally' : 'in proportion to their profit-sharing ratio'}.</p>
      ${specificSalaryHtml}
    `);
  }

  // Clause 6: Clause Amendments (Firm Name, Address, Objects)
  if (supp.changeClauses) {
    if (supp.changeFirmName && supp.newFirmName.trim()) {
      operativeClauses.push(`
        <div class="clause-heading">${c++}. CHANGE OF FIRM NAME :-</div>
        <p class="deed-p">The business of the partnership firm shall henceforth be carried on under the amended name and style of <b>${newFirmName}</b>.</p>
      `);
    }
    if (supp.changeAddress && supp.newFirmAddress.trim()) {
      operativeClauses.push(`
        <div class="clause-heading">${c++}. CHANGE OF PRINCIPAL PLACE OF BUSINESS :-</div>
        <p class="deed-p">The principal place of business of the firm is hereby shifted and shall henceforth be situated at <b>${newFirmAddress}</b>.</p>
      `);
    }
    if (supp.changeObjects && supp.newObjects.trim()) {
      operativeClauses.push(`
        <div class="clause-heading">${c++}. AMENDMENT TO OBJECTS CLAUSE :-</div>
        <p class="deed-p">The business objects clause of the Principal Deed is hereby amended and substituted as follows:</p>
        <p class="deed-p"><b>"${supp.newObjects.trim()}"</b></p>
      `);
    }
    if (supp.customAmendedClauses && supp.customAmendedClauses.length > 0) {
      supp.customAmendedClauses.forEach(cac => {
        if (cac.amendedText?.trim()) {
          operativeClauses.push(`
            <div class="clause-heading">${c++}. AMENDMENT TO ${cac.clauseNumberOrTitle.toUpperCase()} :-</div>
            <p class="deed-p">${cac.amendedText.trim()}</p>
          `);
        }
      });
    }
  }

  // Clause 7: Other Conditions / Banking
  if (supp.changeOtherConditions) {
    if (supp.changeBankOperation && supp.newBankOperationTerms.trim()) {
      operativeClauses.push(`
        <div class="clause-heading">${c++}. BANK ACCOUNTS AND OPERATION MANDATE :-</div>
        <p class="deed-p">${supp.newBankOperationTerms.trim()}</p>
      `);
    }
    if (supp.additionalClauses && supp.additionalClauses.length > 0) {
      supp.additionalClauses.filter(cl => cl.enabled && cl.title.trim()).forEach(cl => {
        operativeClauses.push(`
          <div class="clause-heading">${c++}. ${cl.title.toUpperCase()} :-</div>
          <p class="deed-p">${cl.content.trim()}</p>
        `);
      });
    }
  }

  // Final Clause: Ratification & Continuance of Principal Deed
  const ratificationText = (supp.ratificationClause || DEFAULT_SUPPLEMENTARY_CONFIG.ratificationClause).replace('[DATE]', originalDeedDateFormatted);
  operativeClauses.push(`
    <div class="clause-heading">${c++}. RATIFICATION AND CONTINUANCE OF PRINCIPAL DEED :-</div>
    <p class="deed-p">${ratificationText}</p>
  `);

  // Execution Tables & Signatures matching Gold Standard layout
  const allInvolvedPartners = [...continuingPartners, ...incomingPartners, ...retiringPartners];
  
  const partnersExecutionBoxes = allInvolvedPartners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '';
    
    let roleLabel = 'CONTINUING PARTNER';
    let shareText = '';
    if (incomingPartners.some(ip => ip.id === p.id)) {
      roleLabel = 'INCOMING PARTNER';
      const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
      shareText = `${rev || '0'}% (REVISED)`;
    } else if (retiringPartners.some(rp => rp.id === p.id)) {
      roleLabel = 'RETIRING PARTNER';
      shareText = `FORMER ${p.profitShare || '0'}% (RETIRED)`;
    } else {
      const rev = supp.revisedProfitShares?.[p.id] || p.profitShare;
      shareText = `${rev || '0'}% (REVISED)`;
    }

    if (isForWord) {
      return `
      <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr style="background-color: #f1f5f9;">
          <td colspan="3" style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 10.5pt; text-transform: uppercase; text-align: left; letter-spacing: 0.3pt; color: #0f172a; font-family: 'Times New Roman', Times, serif;">
            PARTNER #${idx + 1} &mdash; ${roleLabel.toUpperCase()} (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
          </td>
        </tr>
        <tr>
          <!-- PARTNER PARTICULARS -->
          <td width="46%" valign="top" style="border: 1pt solid #000000; padding: 6pt; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 3pt 0; text-align: left; font-size: 10pt;"><b>NAME:</b> <span>${formattedName}</span></p>
            ${parentName ? `<p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</p>` : ''}
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PAN:</b> <b>${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</b></p>
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</p>
            ${shareText ? `<p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${shareText}</b></p>` : ''}
            <p style="margin: 4pt 0 0 0; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
              <b>STATUS:</b> ${roleLabel.toUpperCase()}
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
                    3.5 cm &times; 4.5 cm
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
              SIGNATURE OF ${roleLabel.toUpperCase()}: ${formattedName}
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
          PARTNER #${idx + 1} &mdash; ${roleLabel.toUpperCase()} (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
        </td>
      </tr>
      <tr>
        <!-- PARTNER PARTICULARS -->
        <td width="46%" valign="top" style="border: 1px solid #000000; padding: 8px 7px; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left;">
          <div style="margin-bottom: 4px; text-align: left; font-size: 10pt;"><b>NAME:</b> <span style="color: #000000;">${formattedName}</span></div>
          ${parentName ? `<div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</div>` : ''}
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PAN:</b> <span style="font-weight: bold; color: #000000;">${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</span></div>
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</div>
          ${shareText ? `<div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${shareText}</b></div>` : ''}
          <div style="margin-top: 5px; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
            <b>STATUS:</b> ${roleLabel.toUpperCase()}
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
                  3.5 cm &times; 4.5 cm
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
            SIGNATURE OF ${roleLabel.toUpperCase()}: ${formattedName}
          </div>
          <div style="font-size: 8.5pt; color: #475569; text-transform: uppercase; margin-top: 2px; text-align: center;">
            (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
          </div>
        </td>
      </tr>
    </table>
    `;
  }).join('');

  const witnesses = data.witnesses && data.witnesses.length >= 2 ? data.witnesses : [
    { id: 'w1', name: '', parentName: '', address: '' },
    { id: 'w2', name: '', parentName: '', address: '' }
  ];

  const witness1 = witnesses[0];
  const witness2 = witnesses[1];

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

  // USE SPECIALIZED SUPPLEMENTARY COVER PAGE
  const coverHtml = (includeCover && data.includeCoverPage !== false) ? constructSupplementaryCoverPage(data, isForWord) : '';

  // Stamp paper space (only if explicitly requested for legacy physical stamp paper)
  const stampPaperHeader = data.includeStampPlaceholder ? `
    <div class="deed-block" style="height: 180px; border: 1.5px dashed #64748b; margin-bottom: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #f8fafc; border-radius: 4px;">
      <span style="font-size: 11pt; font-weight: bold; color: #475569; letter-spacing: 1px;">
        [ SPACE RESERVED FOR NON-JUDICIAL STAMP PAPER (RS. ${data.stampDutyAmount || '300'}) / E-STAMP CERTIFICATE ]
      </span>
      <span style="font-size: 8.5pt; color: #64748b; margin-top: 4px;">
        (Deed of Modification / Supplementary Partnership under Indian Partnership Act, 1932)
      </span>
    </div>
  ` : '';

  return `
    ${coverHtml}
    
    ${stampPaperHeader}

    <div class="deed-block" data-clause-id="intro">
      <div style="text-align: center; margin-bottom: 18px;">
        <h1 style="font-size: 15pt; font-weight: bold; text-decoration: underline; margin: 0 0 4px 0; letter-spacing: 0.5px;">
          SUPPLEMENTARY DEED OF PARTNERSHIP
        </h1>
        <p style="font-size: 10.5pt; font-weight: bold; color: #334155; margin: 0;">
          (DEED OF MODIFICATION, RECTIFICATION & AMENDMENT OF PARTNERSHIP)
        </p>
        <p style="font-size: 9.5pt; color: #64748b; margin: 2px 0 0 0;">
          IN RESPECT OF M/S. ${firmName}
        </p>
      </div>

      <p class="deed-p" style="margin-bottom: 14px; text-align: justify; line-height: 1.65;">
        THIS SUPPLEMENTARY DEED OF PARTNERSHIP is made and executed at <b>${execCity}</b> on this <b>${execDateFormatted}</b>, by and between:
      </p>
    </div>

    <div class="deed-block" data-clause-id="intro_parties" style="margin: 12px 0;">
      ${partiesIntroHtml}
    </div>

    <div class="deed-block" data-clause-id="recitals">
      <div style="font-weight: bold; text-align: center; margin-bottom: 12px; font-size: 11.5pt; text-decoration: underline; letter-spacing: 0.5px;">
        RECITALS & STATEMENT OF FACTS:
      </div>
      ${recitalsHtml}
    </div>

    <div class="deed-block" data-clause-id="witnesseth">
      <div style="font-weight: bold; text-align: center; margin-bottom: 14px; font-size: 11.5pt; letter-spacing: 0.5px;">
        NOW THIS SUPPLEMENTARY DEED WITNESSETH AND IT IS HEREBY MUTUALLY AGREED BY AND BETWEEN ALL PARTIES HERETO AS FOLLOWS:
      </div>
    </div>

    ${operativeClauses.map((clauseHtml, idx) => `
      <div class="deed-block" data-clause-id="clause_${idx + 1}">${clauseHtml}</div>
    `).join('')}

    ${sigBreakTag}
    <div class="deed-block ${sigBreakClass}" data-clause-id="signatures" style="margin-top: 24px; page-break-inside: avoid;">
      <p class="deed-p" style="text-align: justify; margin-bottom: 18px; font-weight: 500;">
        IN WITNESS WHEREOF, the Continuing Partners, Incoming Partner(s) (if any), and Retiring Partner(s) (if any) have set their respective hands and seals unto this Supplementary Deed on the day, month, and year first above written.
      </p>

      ${isForWord ? `
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 14pt; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr>
          <!-- LEFT: WITNESSES -->
          <td width="35%" valign="top" style="width: 35%; vertical-align: top; padding-right: 12pt; border: none; border-right: 1.5pt dashed #94a3b8; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              SIGNED IN THE PRESENCE OF WITNESSES:
            </p>
            
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">WITNESS #1</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 8pt; font-size: 9pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">${witness1Content}</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; font-family: 'Times New Roman', Times, serif;">
                  <div style="height: 36pt; line-height: 36pt;">&nbsp;</div>
                  <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                  <p style="font-size: 9pt; font-weight: bold; text-transform: uppercase; margin: 0; text-align: center;">SIGNATURE OF WITNESS 1</p>
                </td>
              </tr>
            </table>

            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">WITNESS #2</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 8pt; font-size: 9pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">${witness2Content}</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; font-family: 'Times New Roman', Times, serif;">
                  <div style="height: 36pt; line-height: 36pt;">&nbsp;</div>
                  <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                  <p style="font-size: 9pt; font-weight: bold; text-transform: uppercase; margin: 0; text-align: center;">SIGNATURE OF WITNESS 2</p>
                </td>
              </tr>
            </table>
          </td>

          <!-- RIGHT: ALL PARTNERS SIGNATURE BOXES -->
          <td width="65%" valign="top" style="width: 65%; vertical-align: top; padding-left: 12pt; border: none; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              DETAILS AND EXECUTION BY PARTNERS:
            </p>
            ${partnersExecutionBoxes}
          </td>
        </tr>
      </table>
      ` : `
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 10px;">
        <tr>
          <!-- LEFT: WITNESSES -->
          <td width="34%" valign="top" style="width: 34%; vertical-align: top; padding-right: 14px; border: none; border-right: 1.5px dashed #cbd5e1;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              SIGNED IN THE PRESENCE OF:
            </p>
            
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14px; border: 1.5px solid #000000; table-layout: fixed;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase;">WITNESS #1</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; font-size: 9pt; line-height: 1.45;">${witness1Content}</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 48px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9pt; font-weight: bold; text-transform: uppercase; color: #000000;">SIGNATURE OF WITNESS 1</div>
                </td>
              </tr>
            </table>

            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14px; border: 1.5px solid #000000; table-layout: fixed;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase;">WITNESS #2</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; font-size: 9pt; line-height: 1.45;">${witness2Content}</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 48px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9pt; font-weight: bold; text-transform: uppercase; color: #000000;">SIGNATURE OF WITNESS 2</div>
                </td>
              </tr>
            </table>
          </td>

          <!-- RIGHT: ALL PARTNERS SIGNATURE BOXES -->
          <td width="66%" valign="top" style="width: 66%; vertical-align: top; padding-left: 14px; border: none;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              DETAILS AND EXECUTION BY PARTNERS:
            </p>
            ${partnersExecutionBoxes}
          </td>
        </tr>
      </table>
      `}
    </div>

    ${(includeKyc && data.includeKycAnnexure === true) ? constructKycAnnexurePages(data, isForWord) : ''}
  `;
}

// Construct Dissolution Deed Body
export function constructDissolutionDeedBody(
  data: DeedFormData,
  isForWord: boolean = false,
  includeCover: boolean = true,
  includeKyc: boolean = true
): string {
  const diss = data.dissolutionConfig || DEFAULT_DISSOLUTION_CONFIG;
  const execCity = (data.execCity || diss.originalDeedCity || '_______________').toUpperCase();
  const dissolutionDateFormatted = diss.dissolutionDate 
    ? formatFormalDate(diss.dissolutionDate) 
    : (data.execDate ? formatFormalDate(data.execDate) : '____ DAY OF ____________, 2026');
  const originalDeedDateFormatted = diss.originalDeedDate ? formatFormalDate(diss.originalDeedDate) : '____ DAY OF ____________, 20__';
  const originalDeedCity = (diss.originalDeedCity || execCity).toUpperCase();
  const regNumber = (diss.originalRegistrationNumber || '').trim().toUpperCase();

  const firmName = formatFirmName(data.firmName) || 'M/S. _________________________________';
  const firmAddress = (data.firmAddress || '___________________________________________________').toUpperCase();

  const pageBreaks = data.pageBreakBeforeClauses || [];
  const isSigBreak = data.signaturePageBreak === 'newPage' || pageBreaks.includes('signatures');
  const sigBreakTag = isForWord
    ? (isSigBreak ? '<p class="MsoNormal" style="page-break-before:always;mso-break-type:section-break;margin:0;padding:0;font-size:1pt;line-height:1pt;">&nbsp;</p>' : '')
    : '';
  const sigBreakClass = (!isForWord && isSigBreak) ? ' page-break-before' : '';

  const allPartners = data.partners || [];

  // Party Introduction
  const partiesIntroHtml = allPartners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'Wife of' : 'Son of / Daughter of';
    return `<div style="margin-bottom: 10px; text-align: justify; line-height: 1.65;"><b>${formattedName}</b>, ${relWord} <b>${p.parentName || '________________'}</b>, aged <b>${p.age || '___'} YEARS</b>, having PAN <b>${p.pan || 'APPLIED FOR'}</b>, residing at <b>${p.address || '________________'}</b> (hereinafter referred to as the party of the <b>${getOrdinal(idx + 1)} PART</b>)</div>`;
  }).join('<div style="text-align: center; font-weight: bold; margin: 10px 0;">AND</div>');

  // Reason Summary
  let reasonSummary = 'mutual consent and commercial exigencies of the partners';
  if (diss.dissolutionReason === 'completion_of_venture') {
    reasonSummary = 'completion and fulfillment of the commercial project and venture';
  } else if (diss.dissolutionReason === 'retirement_no_substitute') {
    reasonSummary = 'retirement of partner and mutual decision not to induct new partners';
  } else if (diss.dissolutionReason === 'custom' && diss.customReasonText.trim()) {
    reasonSummary = diss.customReasonText.trim();
  }

  // Custodian Partner Name
  let custodianName = diss.custodianPartnerName;
  if (!custodianName && diss.custodianPartnerId) {
    const matched = allPartners.find(p => p.id === diss.custodianPartnerId);
    if (matched) custodianName = formatPartnerNameWithPrefix(matched);
  }
  if (!custodianName && allPartners.length > 0) {
    custodianName = formatPartnerNameWithPrefix(allPartners[0]);
  }
  custodianName = (custodianName || 'THE DESIGNATED MANAGING PARTNER').toUpperCase();

  const retentionYears = diss.recordsRetentionYears || '8';
  const publicNoticeNewspapers = diss.publicNoticeNewspapers || 'one English daily and one vernacular newspaper circulating in the district';

  // Recitals
  const recitalsList: string[] = [];

  const priorDeeds = (diss.priorDeeds && diss.priorDeeds.length > 0) ? diss.priorDeeds : null;

  if (priorDeeds && priorDeeds.length > 0) {
    // 1. Original Deed Recital
    const originalDeed = priorDeeds.find(d => d.deedType === 'original') || priorDeeds[0];
    const origDateStr = originalDeed.executionDate ? formatFormalDate(originalDeed.executionDate) : originalDeedDateFormatted;
    const origCityStr = (originalDeed.executionCity || originalDeedCity).toUpperCase();
    const origRegStr = originalDeed.rofRegistrationNumber || regNumber;

    recitalsList.push(
      `WHEREAS the partnership firm under the name and style of <b>${firmName}</b> having its place of business at <b>${firmAddress}</b> was originally constituted under and by virtue of the Original Deed of Partnership executed on <b>${origDateStr}</b> at <b>${origCityStr}</b>${origRegStr ? ` (having Registration / Diary No. <b>${origRegStr}</b>)` : ''} (hereinafter referred to as the <b>"ORIGINAL PARTNERSHIP DEED"</b>).`
    );

    // 2. Subsequent Prior Deeds Recitals
    const subsequentDeeds = priorDeeds.filter(d => d !== originalDeed);
    subsequentDeeds.forEach((d, idx) => {
      const dDateStr = d.executionDate ? formatFormalDate(d.executionDate) : '____ DAY OF ____________, 20__';
      const dEffDateStr = d.effectiveDate ? ` with effect from <b>${formatFormalDate(d.effectiveDate)}</b>` : '';
      const dCityStr = d.executionCity ? ` executed at <b>${d.executionCity.toUpperCase()}</b>` : '';
      const dRegStr = d.rofRegistrationNumber ? ` (Registration No. <b>${d.rofRegistrationNumber}</b>)` : '';
      const dChangesStr = d.keyChangesSummary || 'the constitution and covenants of the partnership were modified and amended';

      recitalsList.push(
        `AND WHEREAS subsequently vide ${d.deedLabel || `${getOrdinal(idx + 1)} Supplementary Deed of Partnership`} dated <b>${dDateStr}</b>${dCityStr}${dEffDateStr}${dRegStr}, the partnership firm was reconstituted and amended whereby <b>${dChangesStr}</b>.`
      );
    });

    recitalsList.push(
      `AND WHEREAS pursuant to the said Original Deed of Partnership and the subsequent Supplementary Deeds aforesaid, the partners have been continuously carrying on the business of the firm and sharing all profits and losses in the ratios and on the terms set forth therein.`
    );
  } else {
    recitalsList.push(
      `WHEREAS the parties hereto have been carrying on the business of partnership under the firm name and style of <b>${firmName}</b> at <b>${firmAddress}</b> under and by virtue of the Partnership Deed executed on <b>${originalDeedDateFormatted}</b> at <b>${originalDeedCity}</b> (hereinafter referred to as the <b>"PARTNERSHIP DEED"</b>).`
    );

    if (regNumber) {
      recitalsList.push(
        `AND WHEREAS the said partnership firm was duly registered with the Registrar of Firms having Registration / Diary No. <b>${regNumber}</b>.`
      );
    }

    recitalsList.push(
      `AND WHEREAS the partners have been sharing all profits and losses of the firm in the ratios set forth in the said Partnership Deed.`
    );
  }

  recitalsList.push(
    `AND WHEREAS on account of ${reasonSummary}, the parties hereto have mutually resolved and agreed to dissolve the said partnership firm with effect from the close of business hours on <b>${dissolutionDateFormatted}</b> under Section 40 of the Indian Partnership Act, 1932.`,
    `AND WHEREAS the books of accounts of the firm have been reconciled, balanced and audited up to the date of dissolution, and a final Balance Sheet and Profit & Loss Statement have been inspected and confirmed by all partners.`,
    `AND WHEREAS the parties have mutually agreed to reduce into writing the terms and covenants governing the dissolution, realization of assets, settlement of liabilities, and distribution of surplus by executing this Deed of Dissolution.`
  );

  const recitalsHtml = recitalsList.map(r => `<p class="deed-p" style="margin-bottom: 12px; text-align: justify; line-height: 1.65;">${r}</p>`).join('');

  // Operative Clauses
  let c = 1;
  const operativeClauses: string[] = [
    `
      <div class="clause-heading">${c++}. DISSOLUTION OF PARTNERSHIP FIRM :-</div>
      <p class="deed-p">The partnership firm carried on under the name and style of <b>${firmName}</b> stands formally, completely and irrevocably dissolved by mutual consent with effect from the close of business hours on <b>${dissolutionDateFormatted}</b> (hereinafter referred to as the <b>"EFFECTIVE DATE OF DISSOLUTION"</b>).</p>
    `,
    `
      <div class="clause-heading">${c++}. CESSATION OF COMMERCIAL BUSINESS :-</div>
      <p class="deed-p">From and after the effective date of dissolution, none of the partners shall carry on any trade or commercial business in the name or on behalf of the dissolved firm M/S. ${firmName}, nor use the firm name, trade logo, stationery, intellectual property, or credit, except for the sole and limited purpose of realizing assets, completing pending statutory commitments, and winding up the affairs of the firm.</p>
    `,
    `
      <div class="clause-heading">${c++}. REALIZATION OF ASSETS AND DEBTS :-</div>
      <p class="deed-p">${(diss.realizationOfAssets || DEFAULT_DISSOLUTION_CONFIG.realizationOfAssets).replace('[FIRM_NAME]', firmName)}</p>
    `,
    `
      <div class="clause-heading">${c++}. DISCHARGE OF LIABILITIES AND STATUTORY TAXES :-</div>
      <p class="deed-p">${(diss.dischargeOfLiabilities || DEFAULT_DISSOLUTION_CONFIG.dischargeOfLiabilities)} All third-party debts, bank loans, trade liabilities, supplier dues, and government taxes including Goods and Services Tax (GST), Income Tax, Tax Deducted at Source (TDS), and local levies shall be cleared and discharged in full without default.</p>
    `,
    `
      <div class="clause-heading">${c++}. DIVISION OF SURPLUS AND CAPITAL ACCOUNTS :-</div>
      <p class="deed-p">${(diss.divisionOfSurplus || DEFAULT_DISSOLUTION_CONFIG.divisionOfSurplus)}</p>
    `,
    `
      <div class="clause-heading">${c++}. CUSTODY AND PRESERVATION OF BOOKS OF ACCOUNTS :-</div>
      <p class="deed-p">The books of accounts, ledgers, vouchers, contracts, assessment records, GST and Income Tax files of the firm shall be entrusted to and preserved in the safe custody of Partner <b>${custodianName}</b> for a statutory period of not less than <b>${retentionYears} YEARS</b> from the date of dissolution. The said custodian partner undertakes to produce and make the records available for inspection to any erstwhile partner or judicial/tax authority as required by law.</p>
    `,
    `
      <div class="clause-heading">${c++}. STATUTORY PUBLIC NOTICE AND REGISTRAR FILING :-</div>
      <p class="deed-p">Public notice of dissolution as required under Section 72 of the Indian Partnership Act, 1932, shall be published in the Official Gazette and in <b>${publicNoticeNewspapers}</b>. Necessary notice of dissolution in statutory Form E / Form 5 shall be signed and submitted to the Registrar of Firms having jurisdiction, as well as to the Income Tax Department and GST Department for formal cancellation of registrations.</p>
    `,
    `
      <div class="clause-heading">${c++}. CLOSING OF BANK ACCOUNTS :-</div>
      <p class="deed-p">${(diss.bankAccountSettlement || DEFAULT_DISSOLUTION_CONFIG.bankAccountSettlement)} All current accounts and credit facilities with banks shall be closed, and all mandates issued to banks shall stand revoked.</p>
    `,
    `
      <div class="clause-heading">${c++}. MUTUAL RELEASE AND INDEMNITY :-</div>
      <p class="deed-p">${(diss.mutualIndemnityTerms || DEFAULT_DISSOLUTION_CONFIG.mutualIndemnityTerms)}</p>
    `,
    `
      <div class="clause-heading">${c++}. DISPUTE RESOLUTION AND JURISDICTION :-</div>
      <p class="deed-p">Any dispute arising in connection with the winding up of the firm or interpretation of this Deed shall be referred to arbitration in accordance with the Arbitration and Conciliation Act, 1996, and the competent Civil Courts at <b>${execCity}</b> shall have exclusive jurisdiction.</p>
    `
  ];

  // Execution Boxes matching Gold Standard layout with Passport Photo & Thumb Impression
  const partnersExecutionBoxes = allPartners.map((p, idx) => {
    const formattedName = formatPartnerNameWithPrefix(p) || `PARTNER ${idx + 1}`;
    const relWord = p.relationType === 'HUSBAND' ? 'W/o' : 'S/o / D/o';
    const parentName = p.parentName ? p.parentName.toUpperCase() : '';
    const roleLabel = 'ERSTWHILE / DISSOLVING PARTNER';

    if (isForWord) {
      return `
      <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr style="background-color: #f1f5f9;">
          <td colspan="3" style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 10.5pt; text-transform: uppercase; text-align: left; letter-spacing: 0.3pt; color: #0f172a; font-family: 'Times New Roman', Times, serif;">
            PARTNER #${idx + 1} &mdash; ${roleLabel} (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
          </td>
        </tr>
        <tr>
          <!-- PARTNER PARTICULARS -->
          <td width="46%" valign="top" style="border: 1pt solid #000000; padding: 6pt; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 3pt 0; text-align: left; font-size: 10pt;"><b>NAME:</b> <span>${formattedName}</span></p>
            ${parentName ? `<p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</p>` : ''}
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PAN:</b> <b>${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</b></p>
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</p>
            <p style="margin: 0 0 3pt 0; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${p.profitShare || '0'}%</b></p>
            <p style="margin: 4pt 0 0 0; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
              <b>STATUS:</b> DISSOLVING PARTNER
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
                    3.5 cm &times; 4.5 cm
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
              SIGNATURE OF DISSOLVING PARTNER: ${formattedName}
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
          PARTNER #${idx + 1} &mdash; ${roleLabel} (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
        </td>
      </tr>
      <tr>
        <!-- PARTNER PARTICULARS -->
        <td width="46%" valign="top" style="border: 1px solid #000000; padding: 8px 7px; vertical-align: top; width: 46%; font-size: 9.5pt; line-height: 1.45; text-align: left;">
          <div style="margin-bottom: 4px; text-align: left; font-size: 10pt;"><b>NAME:</b> <span style="color: #000000;">${formattedName}</span></div>
          ${parentName ? `<div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>${relWord}:</b> Sh. ${parentName}</div>` : ''}
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PAN:</b> <span style="font-weight: bold; color: #000000;">${p.pan ? p.pan.toUpperCase() : 'APPLIED FOR'}</span></div>
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>AGE:</b> ${p.age || '___'} YEARS</div>
          <div style="margin-bottom: 4px; text-align: left; color: #334155;"><b>PROFIT SHARE:</b> <b>${p.profitShare || '0'}%</b></div>
          <div style="margin-top: 5px; font-size: 8.5pt; color: #475569; line-height: 1.35; text-align: left;">
            <b>STATUS:</b> DISSOLVING PARTNER
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
                  3.5 cm &times; 4.5 cm
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
            SIGNATURE OF DISSOLVING PARTNER: ${formattedName}
          </div>
          <div style="font-size: 8.5pt; color: #475569; text-transform: uppercase; margin-top: 2px; text-align: center;">
            (PARTY OF THE ${getOrdinal(idx + 1).toUpperCase()} PART)
          </div>
        </td>
      </tr>
    </table>
    `;
  }).join('');

  const witnesses = data.witnesses && data.witnesses.length >= 2 ? data.witnesses : [
    { id: 'w1', name: '', parentName: '', address: '' },
    { id: 'w2', name: '', parentName: '', address: '' }
  ];

  const witness1 = witnesses[0];
  const witness2 = witnesses[1];

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

  // USE SPECIALIZED DISSOLUTION COVER PAGE
  const coverHtml = (includeCover && data.includeCoverPage !== false) ? constructDissolutionCoverPage(data, isForWord) : '';

  // Stamp paper space (only if explicitly requested for legacy physical stamp paper)
  const stampPaperHeader = data.includeStampPlaceholder ? `
    <div class="deed-block" style="height: 180px; border: 1.5px dashed #64748b; margin-bottom: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #f8fafc; border-radius: 4px;">
      <span style="font-size: 11pt; font-weight: bold; color: #475569; letter-spacing: 1px;">
        [ SPACE RESERVED FOR NON-JUDICIAL STAMP PAPER (RS. ${data.stampDutyAmount || '300'}) / E-STAMP CERTIFICATE ]
      </span>
      <span style="font-size: 8.5pt; color: #64748b; margin-top: 4px;">
        (Deed of Dissolution under Section 40/43 of the Indian Partnership Act, 1932)
      </span>
    </div>
  ` : '';

  return `
    ${coverHtml}
    
    ${stampPaperHeader}

    <div class="deed-block" data-clause-id="intro">
      <div style="text-align: center; margin-bottom: 18px;">
        <h1 style="font-size: 15pt; font-weight: bold; text-decoration: underline; margin: 0 0 4px 0; letter-spacing: 0.5px;">
          DEED OF DISSOLUTION OF PARTNERSHIP FIRM
        </h1>
        <p style="font-size: 10.5pt; font-weight: bold; color: #334155; margin: 0;">
          (UNDER SECTION 40 & 43 OF THE INDIAN PARTNERSHIP ACT, 1932)
        </p>
        <p style="font-size: 9.5pt; color: #64748b; margin: 2px 0 0 0;">
          IN RESPECT OF M/S. ${firmName}
        </p>
      </div>

      <p class="deed-p" style="margin-bottom: 14px; text-align: justify; line-height: 1.65;">
        THIS DEED OF DISSOLUTION OF PARTNERSHIP is made and executed at <b>${execCity}</b> on this <b>${dissolutionDateFormatted}</b>, by and between:
      </p>
    </div>

    <div class="deed-block" data-clause-id="intro_parties" style="margin: 12px 0;">
      ${partiesIntroHtml}
    </div>

    <div class="deed-block" data-clause-id="recitals">
      <div style="font-weight: bold; text-align: center; margin-bottom: 12px; font-size: 11.5pt; text-decoration: underline; letter-spacing: 0.5px;">
        RECITALS & STATEMENT OF FACTS:
      </div>
      ${recitalsHtml}
    </div>

    <div class="deed-block" data-clause-id="witnesseth">
      <div style="font-weight: bold; text-align: center; margin-bottom: 14px; font-size: 11.5pt; letter-spacing: 0.5px;">
        NOW THIS DEED OF DISSOLUTION WITNESSETH AND IT IS HEREBY MUTUALLY AGREED BY AND BETWEEN ALL PARTIES HERETO AS FOLLOWS:
      </div>
    </div>

    ${operativeClauses.map((clauseHtml, idx) => `
      <div class="deed-block" data-clause-id="clause_${idx + 1}">${clauseHtml}</div>
    `).join('')}

    ${sigBreakTag}
    <div class="deed-block ${sigBreakClass}" data-clause-id="signatures" style="margin-top: 24px; page-break-inside: avoid;">
      <p class="deed-p" style="text-align: justify; margin-bottom: 18px; font-weight: 500;">
        IN WITNESS WHEREOF, the parties hereto have set and subscribed their respective hands and seals unto this Deed of Dissolution on the day, month, and year first above written.
      </p>

      ${isForWord ? `
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 14pt; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
        <tr>
          <!-- LEFT: WITNESSES -->
          <td width="35%" valign="top" style="width: 35%; vertical-align: top; padding-right: 12pt; border: none; border-right: 1.5pt dashed #94a3b8; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              SIGNED IN THE PRESENCE OF WITNESSES:
            </p>
            
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">WITNESS #1</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 8pt; font-size: 9pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">${witness1Content}</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; font-family: 'Times New Roman', Times, serif;">
                  <div style="height: 36pt; line-height: 36pt;">&nbsp;</div>
                  <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                  <p style="font-size: 9pt; font-weight: bold; text-transform: uppercase; margin: 0; text-align: center;">SIGNATURE OF WITNESS 1</p>
                </td>
              </tr>
            </table>

            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14pt; border: 1.5pt solid #000000; mso-table-lspace: 0pt; mso-table-rspace: 0pt;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1pt solid #000000; padding: 5pt 8pt; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase; font-family: 'Times New Roman', Times, serif;">WITNESS #2</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 8pt; font-size: 9pt; line-height: 1.45; text-align: left; font-family: 'Times New Roman', Times, serif;">${witness2Content}</td>
              </tr>
              <tr>
                <td style="border: 1pt solid #000000; padding: 16pt 6pt 6pt 6pt; text-align: center; vertical-align: bottom; font-family: 'Times New Roman', Times, serif;">
                  <div style="height: 36pt; line-height: 36pt;">&nbsp;</div>
                  <p style="width: 90%; border-bottom: 1.5pt solid #000000; margin: 0 auto 4pt auto; text-align: center;">&nbsp;</p>
                  <p style="font-size: 9pt; font-weight: bold; text-transform: uppercase; margin: 0; text-align: center;">SIGNATURE OF WITNESS 2</p>
                </td>
              </tr>
            </table>
          </td>

          <!-- RIGHT: ALL PARTNERS SIGNATURE BOXES -->
          <td width="65%" valign="top" style="width: 65%; vertical-align: top; padding-left: 12pt; border: none; font-family: 'Times New Roman', Times, serif;">
            <p style="margin: 0 0 10pt 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              DETAILS AND EXECUTION BY PARTNERS:
            </p>
            ${partnersExecutionBoxes}
          </td>
        </tr>
      </table>
      ` : `
      <table width="100%" border="0" cellpadding="0" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-top: 10px;">
        <tr>
          <!-- LEFT: WITNESSES -->
          <td width="34%" valign="top" style="width: 34%; vertical-align: top; padding-right: 14px; border: none; border-right: 1.5px dashed #cbd5e1;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              SIGNED IN THE PRESENCE OF:
            </p>
            
            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14px; border: 1.5px solid #000000; table-layout: fixed;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase;">WITNESS #1</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; font-size: 9pt; line-height: 1.45;">${witness1Content}</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 48px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9pt; font-weight: bold; text-transform: uppercase; color: #000000;">SIGNATURE OF WITNESS 1</div>
                </td>
              </tr>
            </table>

            <table width="100%" border="1" cellpadding="6" cellspacing="0" style="width: 100%; border-collapse: collapse; margin-bottom: 14px; border: 1.5px solid #000000; table-layout: fixed;">
              <tr style="background-color: #f1f5f9;">
                <td style="border: 1px solid #000000; padding: 5px 8px; font-weight: bold; font-size: 9.5pt; text-align: left; text-transform: uppercase;">WITNESS #2</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 8px; font-size: 9pt; line-height: 1.45;">${witness2Content}</td>
              </tr>
              <tr>
                <td style="border: 1px solid #000000; padding: 14px 6px 8px 6px; text-align: center; vertical-align: bottom; background-color: #ffffff;">
                  <div style="min-height: 48px; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; margin-bottom: 4px;">
                    <div style="width: 90%; border-bottom: 1.5px solid #000000; margin: 0 auto;"></div>
                  </div>
                  <div style="font-size: 9pt; font-weight: bold; text-transform: uppercase; color: #000000;">SIGNATURE OF WITNESS 2</div>
                </td>
              </tr>
            </table>
          </td>

          <!-- RIGHT: ALL PARTNERS SIGNATURE BOXES -->
          <td width="66%" valign="top" style="width: 66%; vertical-align: top; padding-left: 14px; border: none;">
            <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 11pt; text-decoration: underline; text-transform: uppercase;">
              DETAILS AND EXECUTION BY PARTNERS:
            </p>
            ${partnersExecutionBoxes}
          </td>
        </tr>
      </table>
      `}
    </div>

    ${(includeKyc && data.includeKycAnnexure === true) ? constructKycAnnexurePages(data, isForWord) : ''}
  `;
}

// Clauses list for Supplementary Deed
export function getSupplementaryClauseList(data: DeedFormData): DeedClauseItem[] {
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
    { id: 'intro_parties', title: 'Preamble, Parties & Recitals', category: 'intro', hasPageBreak: breaks.includes('intro_parties') },
    { id: 'clause_1', title: '1. Effective Date of Modification', category: 'clause', hasPageBreak: breaks.includes('clause_1') }
  );

  const supp = data.supplementaryConfig || DEFAULT_SUPPLEMENTARY_CONFIG;
  let c = 2;
  if (supp.changePartners) {
    if (supp.retiringPartnerIds && supp.retiringPartnerIds.length > 0) {
      list.push({ id: 'clause_retire', title: `${c++}. Retirement of Partner(s)`, category: 'clause', hasPageBreak: breaks.includes('clause_retire') });
    }
    if (supp.incomingPartners && supp.incomingPartners.length > 0) {
      list.push({ id: 'clause_admit', title: `${c++}. Admission of Incoming Partner(s)`, category: 'clause', hasPageBreak: breaks.includes('clause_admit') });
    }
  }

  list.push({ id: 'clause_profit', title: `${c++}. Revised Profit & Loss Sharing Ratio`, category: 'clause', hasPageBreak: breaks.includes('clause_profit') });

  if (supp.changeRemuneration) {
    list.push({ id: 'clause_remun', title: `${c++}. Revised Remuneration & Interest (IT Act 2025)`, category: 'clause', hasPageBreak: breaks.includes('clause_remun') });
  }

  if (supp.changeClauses) {
    list.push({ id: 'clause_amendments', title: `${c++}. Clause Amendments (Name/Address/Objects)`, category: 'clause', hasPageBreak: breaks.includes('clause_amendments') });
  }

  if (supp.changeOtherConditions) {
    list.push({ id: 'clause_other', title: `${c++}. Banking Operations & Special Covenants`, category: 'clause', hasPageBreak: breaks.includes('clause_other') });
  }

  list.push(
    { id: 'clause_ratify', title: `${c++}. Ratification & Continuance of Principal Deed`, category: 'clause', hasPageBreak: breaks.includes('clause_ratify') },
    { id: 'signatures', title: 'Execution & Witness Signatures', category: 'signatures', hasPageBreak: (data.signaturePageBreak === 'newPage') || breaks.includes('signatures') }
  );

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

// Clauses list for Dissolution Deed
export function getDissolutionClauseList(data: DeedFormData): DeedClauseItem[] {
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
    { id: 'intro_parties', title: 'Preamble, Partners & Recitals', category: 'intro', hasPageBreak: breaks.includes('intro_parties') },
    { id: 'clause_1', title: '1. Dissolution of Partnership Firm', category: 'clause', hasPageBreak: breaks.includes('clause_1') },
    { id: 'clause_2', title: '2. Cessation of Commercial Business', category: 'clause', hasPageBreak: breaks.includes('clause_2') },
    { id: 'clause_3', title: '3. Realization of Assets and Debts', category: 'clause', hasPageBreak: breaks.includes('clause_3') },
    { id: 'clause_4', title: '4. Discharge of Liabilities & Statutory Taxes', category: 'clause', hasPageBreak: breaks.includes('clause_4') },
    { id: 'clause_5', title: '5. Division of Surplus & Capital Accounts', category: 'clause', hasPageBreak: breaks.includes('clause_5') },
    { id: 'clause_6', title: '6. Custody & Preservation of Books (8 Years)', category: 'clause', hasPageBreak: breaks.includes('clause_6') },
    { id: 'clause_7', title: '7. Statutory Public Notice & RoF Filing', category: 'clause', hasPageBreak: breaks.includes('clause_7') },
    { id: 'clause_8', title: '8. Closing of Bank Accounts', category: 'clause', hasPageBreak: breaks.includes('clause_8') },
    { id: 'clause_9', title: '9. Mutual Release and Indemnity', category: 'clause', hasPageBreak: breaks.includes('clause_9') },
    { id: 'clause_10', title: '10. Dispute Resolution & Jurisdiction', category: 'clause', hasPageBreak: breaks.includes('clause_10') },
    { id: 'signatures', title: 'Execution & Witness Signatures', category: 'signatures', hasPageBreak: (data.signaturePageBreak === 'newPage') || breaks.includes('signatures') }
  );

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
