import {
  ClientMaster,
  RegulatoryUpdate,
  ClientMatch,
  ClientAdvisory,
  MatchStatus,
  FormalAdvisory,
  PlainLanguageClientCommunication,
  ShortWhatsAppAlert,
  ManagementNote,
  CAInternalAction,
  CommunicationLanguage,
  BrandSettings,
} from '../types';

/**
 * Deterministic Client Matching Engine V2.2 — Hard Exclusion Rules & Compliance Profile Criteria
 */
export function matchClientWithUpdate(client: ClientMaster, update: RegulatoryUpdate): ClientMatch {
  const matchReasons: string[] = [];
  const exclusionReasons: string[] = [];
  const missingInformation: string[] = [];

  // ==========================================
  // 1. SPECIALIZED TDS / TCS DETERMINISTIC LOGIC
  // ==========================================
  if (
    update.category === 'TDS / TCS' ||
    update.title.toLowerCase().includes('tds') ||
    update.title.toLowerCase().includes('tcs')
  ) {
    // A. Check Hard Exclusion
    if (
      client.tanAvailable === 'No' ||
      (client.tdsApplicableStatus === 'No' && client.tcsApplicableStatus === 'No')
    ) {
      exclusionReasons.push('Hard Exclusion: Client is positively identified as having no TAN or TDS/TCS deduction obligation.');
      return {
        id: `match_${update.id}_${client.id}`,
        updateId: update.id,
        clientId: client.id,
        clientName: client.clientName,
        relevanceStatus: 'NOT APPLICABLE',
        relevanceScore: 0,
        matchReasons: [],
        exclusionReasons,
        missingInformation: [],
        recommendedNextStep: 'No advisory required. Document exclusion in audit file.',
        needForProfessionalReview: 'No CA review required — client exempt from TDS/TCS.',
        canGenerateAdvisory: false,
      };
    }

    // B. Detect Missing Client Master Fields
    const missingFields: string[] = [];
    if (!client.tanAvailable || client.tanAvailable === 'Unknown') missingFields.push('• TAN Status');
    if ((!client.tdsApplicableStatus || client.tdsApplicableStatus === 'Unknown') && (!client.tcsApplicableStatus || client.tcsApplicableStatus === 'Unknown')) {
      missingFields.push('• TDS/TCS Applicability');
    }
    if (!client.activeDeductorCollector || client.activeDeductorCollector === 'Unknown') {
      missingFields.push('• Active Deductor/Collector Status');
    }
    if (!client.relevantPeriodActivity || client.relevantPeriodActivity === 'Unknown') {
      missingFields.push('• Relevant Period Deduction/Collection Status');
    }
    if (!client.tdsTcsAmountPayable || client.tdsTcsAmountPayable === 'Unknown') {
      missingFields.push('• Amount Payable');
    }
    if (!client.depositStatus || client.depositStatus === 'Unknown') {
      missingFields.push('• Deposit Status');
    }

    if (missingFields.length > 0) {
      missingInformation.push(...missingFields);
      matchReasons.push('Client Master Data Insufficient for Deterministic TDS/TCS Matching.');
      matchReasons.push('Tax Audit applicability under Sec 44AB alone is NOT sufficient evidence of TDS/TCS payable.');

      return {
        id: `match_${update.id}_${client.id}`,
        updateId: update.id,
        clientId: client.id,
        clientName: client.clientName,
        relevanceStatus: 'POSSIBLY RELEVANT — DATA VERIFICATION REQUIRED',
        relevanceScore: 30,
        matchReasons,
        exclusionReasons: [],
        missingInformation,
        recommendedNextStep: 'Update Client Master compliance profile before generating client advisory.',
        needForProfessionalReview: `CA must verify TAN & TDS/TCS ledger balances for ${client.clientName}.`,
        canGenerateAdvisory: false,
      };
    }

    // C. Deterministic Evaluation when fields are available
    if (client.depositStatus === 'Paid' || client.tdsTcsAmountPayable === 'Nil') {
      matchReasons.push('Client is an active TDS deductor with relevant period activity.');
      matchReasons.push(`Deposit status: Paid (${client.lastDepositDate ? 'Last deposited: ' + client.lastDepositDate : 'Nil outstanding balance'}).`);

      return {
        id: `match_${update.id}_${client.id}`,
        updateId: update.id,
        clientId: client.id,
        clientName: client.clientName,
        relevanceStatus: 'MATCHED / ALREADY COMPLIED',
        relevanceScore: 90,
        matchReasons,
        exclusionReasons: [],
        missingInformation: [],
        recommendedNextStep: 'Compliance already completed. Maintain deposit receipt in audit file. No urgent advisory required.',
        needForProfessionalReview: 'Record maintained for audit file. Urgent payment advisory generation disabled.',
        canGenerateAdvisory: false,
      };
    } else {
      matchReasons.push('Client has active TDS/TCS deduction obligation.');
      matchReasons.push(`Deposit status: Unpaid (${client.tdsTcsAmountPayable || 'Amount Outstanding'}). Statutory deadline applies today.`);

      return {
        id: `match_${update.id}_${client.id}`,
        updateId: update.id,
        clientId: client.id,
        clientName: client.clientName,
        relevanceStatus: 'MATCHED / ACTION REQUIRED',
        relevanceScore: 95,
        matchReasons,
        exclusionReasons: [],
        missingInformation: [],
        recommendedNextStep: `Generate formal Client Advisory & notify ${client.primaryContact || client.clientName} immediately regarding today's TDS/TCS deposit deadline.`,
        needForProfessionalReview: `CA must verify bank payment challan before issuing advisory.`,
        canGenerateAdvisory: true,
      };
    }
  }

  // ==========================================
  // 2. GENERALIZED REGULATORY APPLICABILITY FRAMEWORK
  // ==========================================
  let score = 0;

  // MCA / Companies Act
  if (update.category === 'MCA / Companies Act') {
    if (['Sole Proprietorship', 'Partnership', 'Individual', 'Trust/NGO'].includes(client.entityType)) {
      exclusionReasons.push(
        `Hard Exclusion: MCA Companies Act circulars apply strictly to Private/Public Limited Companies or LLPs, not ${client.entityType}.`
      );
    } else {
      score += 40;
      matchReasons.push(`Client is a ${client.entityType} subject to Ministry of Corporate Affairs jurisdiction.`);
    }

    if (update.title.toLowerCase().includes('demat') || update.keyDevelopment.toLowerCase().includes('pas-7')) {
      if (client.annualTurnoverRange.includes('50') || client.annualTurnoverRange.includes('100') || client.annualTurnoverRange.includes('250')) {
        score += 35;
        matchReasons.push(`Turnover bracket (${client.annualTurnoverRange}) indicates non-Small Company status requiring share dematerialisation.`);
      }
    }
  }

  // GST
  if (update.category === 'GST') {
    if (!client.gstRegistered) {
      exclusionReasons.push(`Hard Exclusion: Client is not registered under GST.`);
    } else {
      score += 45;
      matchReasons.push(`Client is GST registered (${client.gstin || 'Active GSTIN'}).`);
    }

    if (update.title.toLowerCase().includes('e-invoicing') || update.importantThresholds.includes('2 Crore')) {
      if (client.annualTurnoverRange !== '₹1 Cr - ₹5 Cr' && !client.annualTurnoverRange.includes('10 Cr')) {
        score += 35;
        matchReasons.push(`Annual turnover range (${client.annualTurnoverRange}) exceeds the ₹2 Crore e-invoicing threshold.`);
      }
    }
  }

  // Income Tax & Section 43B(h)
  if (update.category === 'Income Tax') {
    if (client.incomeTaxAssessee === false) {
      exclusionReasons.push(`Hard Exclusion: Client is exempt from Income Tax Audit provisions.`);
    } else {
      score += 30;
      matchReasons.push(`Client is an Income Tax assessee subject to Tax Audit under Sec 44AB.`);
    }

    if (update.title.includes('43B(h)') || update.keyDevelopment.toLowerCase().includes('msme')) {
      if (['Retail & Consumer Chains', 'Auto Components & Engineering', 'Travel, Tourism & Forex'].includes(client.industry)) {
        score += 45;
        matchReasons.push(`Industry sector (${client.industry}) involves high procurement from Micro/Small vendors subject to Sec 43B(h) payment limits.`);
      }
      if (!client.udyamRegNo && !client.udyamRegistration) {
        missingInformation.push('• Client vendor MSME Udyam classification data required.');
      }
    }
  }

  // RBI / Forex / FEMA
  if (
    update.category === 'RBI / Banking' ||
    update.category === 'FEMA / Foreign Exchange' ||
    update.category === 'Forex'
  ) {
    const hasForex = client.importer || client.exporter || client.femaExposure !== 'None' || client.forexExposure !== 'None' || client.hasFemaExposure || client.hasForeignCurrencyExposure;
    if (!hasForex) {
      exclusionReasons.push(`Hard Exclusion: Client has no cross-border trade, FDI/ODI, or foreign exchange exposure.`);
    } else {
      score += 45;
      matchReasons.push(
        `Client has active cross-border exposure (Importer: ${client.importer ? 'Yes' : 'No'}, Exporter: ${client.exporter ? 'Yes' : 'No'}, Forex Exposure: ${client.forexExposure}).`
      );
    }
  }

  // EPFO / PF / ESI / Labour Law
  if (update.category === 'Labour Law' || update.category === 'PF' || update.category === 'ESI') {
    if (!client.payroll || client.numberOfEmployees === 0) {
      exclusionReasons.push(`Hard Exclusion: Client has no payroll or active employee headcount.`);
    } else {
      if (update.category === 'PF' && !client.pfApplicable) {
        exclusionReasons.push(`Hard Exclusion: EPF Act is not applicable to client establishment.`);
      } else if (update.category === 'ESI' && !client.esiApplicable) {
        exclusionReasons.push(`Hard Exclusion: ESIC Act is not applicable to client establishment.`);
      } else {
        score += 45;
        matchReasons.push(`Client maintains active payroll with ${client.numberOfEmployees} employees.`);
      }
    }
  }

  // Market Items
  if (update.isMarketItem) {
    if (update.title.toLowerCase().includes('crude') && client.crudeSensitivity !== 'None') {
      score += 40;
      matchReasons.push(`Client has ${client.crudeSensitivity} operational sensitivity to fuel and crude oil logistics costs.`);
    }
    if ((update.title.toLowerCase().includes('usd') || update.title.toLowerCase().includes('forex')) && client.forexExposure !== 'None') {
      score += 45;
      matchReasons.push(`Client operating margin is exposed to USD exchange rate volatility.`);
    }
  }

  // Final Classification & Action Control
  if (exclusionReasons.length > 0) {
    return {
      id: `match_${update.id}_${client.id}`,
      updateId: update.id,
      clientId: client.id,
      clientName: client.clientName,
      relevanceStatus: 'NOT APPLICABLE',
      relevanceScore: 0,
      matchReasons: [],
      exclusionReasons,
      missingInformation: [],
      recommendedNextStep: 'No advisory required. Document exclusion in audit file.',
      needForProfessionalReview: `No CA review required — update excluded by statutory rule.`,
      canGenerateAdvisory: false,
    };
  }

  if (missingInformation.length > 0) {
    return {
      id: `match_${update.id}_${client.id}`,
      updateId: update.id,
      clientId: client.id,
      clientName: client.clientName,
      relevanceStatus: 'POSSIBLY RELEVANT — DATA VERIFICATION REQUIRED',
      relevanceScore: 35,
      matchReasons,
      exclusionReasons: [],
      missingInformation,
      recommendedNextStep: 'Update Client Master compliance profile before generating client advisory.',
      needForProfessionalReview: `CA must verify missing threshold information for ${client.clientName}.`,
      canGenerateAdvisory: false,
    };
  }

  if (score >= 70) {
    return {
      id: `match_${update.id}_${client.id}`,
      updateId: update.id,
      clientId: client.id,
      clientName: client.clientName,
      relevanceStatus: 'MATCHED / ACTION REQUIRED',
      relevanceScore: Math.min(score, 98),
      matchReasons,
      exclusionReasons: [],
      missingInformation: [],
      recommendedNextStep: `Generate formal Client Advisory & notify ${client.primaryContact || client.clientName} immediately.`,
      needForProfessionalReview: `Chartered Accountant must verify ${client.clientName}'s financial figures before sending advisory.`,
      canGenerateAdvisory: true,
    };
  }

  return {
    id: `match_${update.id}_${client.id}`,
    updateId: update.id,
    clientId: client.id,
    clientName: client.clientName,
    relevanceStatus: 'POSSIBLY RELEVANT — DATA VERIFICATION REQUIRED',
    relevanceScore: Math.max(score, 30),
    matchReasons,
    exclusionReasons: [],
    missingInformation: ['• Additional entity compliance metrics required'],
    recommendedNextStep: 'Verify client threshold metrics before generating advisory.',
    needForProfessionalReview: `Verify if requirement applies to ${client.clientName}.`,
    canGenerateAdvisory: false,
  };
}

/**
 * Helper to generate simple regional translation summary
 */
function generateRegionalLanguageText(
  lang: CommunicationLanguage | undefined,
  update: RegulatoryUpdate,
  client: ClientMaster
) {
  if (!lang) return undefined;
  if (lang.includes('Malayalam')) {
    return {
      language: 'Malayalam' as const,
      languageHeader: 'മലയാളത്തിൽ (Malayalam Summary)',
      summary: `ശ്രദ്ധിക്കുക: ${client.clientName} ബിസിനസ്സിന് ബാധകമായ പുതിയ ${update.category} നിയമ ഭേദഗതി. ${update.keyDevelopment} അടുത്ത മാസം മുതൽ പ്രാബല്യത്തിൽ വരുന്നു. നിങ്ങളുടെ ചാർട്ടേഡ് അക്കൗണ്ടൻ്റുമായി ചർച്ച ചെയ്ത് ആവശ്യമായ നടപടികൾ സ്വീകരിക്കുക.`,
    };
  }
  if (lang.includes('Hindi')) {
    return {
      language: 'Hindi' as const,
      languageHeader: 'हिंदी में (Hindi Summary)',
      summary: `ध्यान दें: ${client.clientName} के व्यवसाय के लिए महत्वपूर्ण ${update.category} संशोधन। ${update.keyDevelopment} लागू हो रहा है। अपने चार्टर्ड अकाउंटेंट से परामर्श करें और समय पर आवश्यक कार्यवाही पूर्ण करें।`,
    };
  }
  if (lang.includes('Tamil')) {
    return {
      language: 'Tamil' as const,
      languageHeader: 'தமிழில் (Tamil Summary)',
      summary: `கவனத்திற்கு: ${client.clientName} நிறுவனத்திற்குப் பொருந்தக்கூடிய புதிய ${update.category} விதிமுறை மாற்றம். ${update.keyDevelopment} உடனடியாகச் செயல்படத் தொடங்குகிறது. உங்கள் பட்டயக் கணக்காளருடன் ஆலோசிக்கவும்.`,
    };
  }
  return undefined;
}

/**
 * Generates structured professional output and plain language client advisory
 */
export function generateClientAdvisory(
  client: ClientMaster,
  update: RegulatoryUpdate,
  brandSettings?: BrandSettings
): ClientAdvisory {
  const firm = brandSettings?.firmName || 'M. R. & Co., Chartered Accountants';
  const ca = brandSettings?.caName || 'CA Rajesh Kumar, FCA';

  const formalAdvisory: FormalAdvisory = {
    subject: `PROFESSIONAL ADVISORY: ${update.title}`,
    development: update.sourceFacts || update.keyDevelopment,
    authoritativeSource: `${update.issuingAuthority} (${update.referenceNo || update.source})`,
    applicability: `Applicable to ${client.clientName} (${client.entityType}, ${client.industry}) based on statutory threshold (${update.importantThresholds || 'Standard Statutory Criteria'}).`,
    clientSpecificImpact: update.aiImpactAnalysisText || update.impactAnalysis.complianceImpact,
    financialImpact: update.impactAnalysis.financialImpact,
    operationalImpact: update.impactAnalysis.operationalImpact,
    requiredAction: update.caRecommendedAction || update.impactAnalysis.recommendedAction,
    statutoryDate: update.dates?.effectiveDate || update.dates?.statutoryDeadline || 'Statutory Date Pending Verification',
    recommendedInternalActionDate: update.dates?.recommendedInternalActionDate || 'Prior to statutory deadline',
    documentsRequired: `1. FY 2025-26 Financial Books & Trial Balance\n2. Active Vendor/Customer Master with GSTIN/Udyam details\n3. Accounting/ERP Software configuration logs`,
    verificationNotes: update.unconfirmedNotice || 'AI draft prepared for CA review. Verify turnover thresholds before dispatch.',
    disclaimer: brandSettings?.disclaimer || `Issued by ${firm} for general guidance of ${client.clientName}.`,
  };

  const plainLanguageCommunication: PlainLanguageClientCommunication = {
    whatHappened: `The ${update.issuingAuthority} has issued a new requirement regarding ${update.category}: ${update.keyDevelopment}`,
    doesThisAffectMyBusiness: `Yes, because your business operates as a ${client.entityType} in ${client.industry} with an annual turnover of ${client.annualTurnoverRange}.`,
    whyDoesItMatter: `${update.impactAnalysis.financialImpact} ${update.impactAnalysis.complianceImpact}`,
    whatShouldIDo: `Check your billing and accounting setup with your accounts team. Ensure suppliers/customers are updated with required tax/regulatory credentials.`,
    byWhen: `Statutory effective date is ${update.dates?.effectiveDate || update.dates?.statutoryDeadline}. We recommend completing preparation by ${update.dates?.recommendedInternalActionDate || '20 days prior'}.`,
    whatWillMyCaDo: `Our CA team at ${firm} will verify your financial thresholds, audit your software readiness, and ensure full compliance before filing.`,
    regionalLanguageText: generateRegionalLanguageText(client.preferredLanguage, update, client),
  };

  const shortAlert: ShortWhatsAppAlert = {
    title: `IMPORTANT BUSINESS UPDATE: ${update.category}`,
    whatChanged: update.keyDevelopment,
    businessImpact: update.impactAnalysis.financialImpact,
    action: update.impactAnalysis.recommendedAction.split('.')[0] + '.',
    importantDate: update.dates?.effectiveDate || update.dates?.statutoryDeadline,
    ourTeamAction: `Our advisory team at ${firm} will review your account records and assist in implementation.`,
    sourceNote: `Source: ${update.issuingAuthority} (${update.referenceNo || 'Official Notification'})`,
    fullFormattedText: `🚨 *IMPORTANT BUSINESS UPDATE*
*Client:* ${client.clientName}
*Subject:* ${update.title}

*What Changed:*
${update.keyDevelopment}

*Business Impact:*
${update.impactAnalysis.financialImpact}

*Action Required:*
${update.impactAnalysis.recommendedAction.split('.')[0]}.

*Important Date:* ${update.dates?.effectiveDate || update.dates?.statutoryDeadline}

*Advisor:* ${firm} (${ca})

_Source: ${update.issuingAuthority} (${update.referenceNo})_`,
  };

  const managementNote: ManagementNote = {
    issue: update.title,
    risk: update.riskLevel === 'Critical' ? 'High Statutory Penalty / Invalidation Risk' : 'Moderate Operational Compliance Risk',
    financialImplication: update.impactAnalysis.financialImpact,
    recommendedAction: update.impactAnalysis.recommendedAction,
    responsibleFunction: update.category === 'GST' ? 'Finance & Taxation' : update.category === 'MCA / Companies Act' ? 'Legal & Secretarial' : 'CFO & Managing Partner',
    timeline: update.dates?.recommendedInternalActionDate || update.dates?.statutoryDeadline,
  };

  const caInternalAction: CAInternalAction = {
    client: client.clientName,
    update: update.title,
    action: `Audit ${client.clientName}'s readiness for ${update.category} requirement.`,
    priority: update.riskLevel === 'Critical' ? 'High' : update.riskLevel === 'High' ? 'Medium' : 'Low',
    deadline: update.dates?.recommendedInternalActionDate || update.dates?.statutoryDeadline,
    status: 'Pending',
  };

  return {
    id: `adv_${update.id}_${client.id}`,
    updateId: update.id,
    clientId: client.id,
    clientName: client.clientName,
    originalFormalAdvisory: { ...formalAdvisory },
    formalAdvisory,
    plainLanguageCommunication,
    shortAlert,
    managementNote,
    caInternalAction,
    approvalStatus: 'Pending Review',
    dispatchStatus: 'Not Dispatched',
    createdAt: new Date().toISOString(),
  };
}
