import React, { useState } from 'react';
import {
  Smartphone,
  Sparkles,
  Download,
  Copy,
  Check,
  Globe,
  Palette,
  ChevronRight,
  Share2,
  ShieldCheck,
  Building,
  Calendar,
  PhoneCall,
} from 'lucide-react';
import { RegulatoryUpdate, BrandSettings } from '../types';

interface WhatsAppStudioViewProps {
  updates: RegulatoryUpdate[];
  selectedUpdate: RegulatoryUpdate | null;
  setSelectedUpdate: (update: RegulatoryUpdate | null) => void;
  brandSettings: BrandSettings;
}

export const WhatsAppStudioView: React.FC<WhatsAppStudioViewProps> = ({
  updates,
  selectedUpdate,
  setSelectedUpdate,
  brandSettings,
}) => {
  const activeUpdate = selectedUpdate || (updates.length > 0 ? updates[0] : null);
  const [selectedTheme, setSelectedTheme] = useState<'navy' | 'emerald' | 'slate' | 'amber'>('navy');
  const [selectedLanguage, setSelectedLanguage] = useState<'English' | 'Malayalam' | 'Hindi' | 'Tamil'>('English');
  const [copiedCardIndex, setCopiedCardIndex] = useState<number | null>(null);

  // Sanitize internal verification messages
  const sanitizeInternalText = (str: string | undefined | null): string => {
    if (!str) return '';
    return str
      .replace(/verification required/gi, '')
      .replace(/not specified in source email/gi, '')
      .replace(/reference verification pending/gi, '')
      .replace(/data verification required/gi, '')
      .replace(/not specified/gi, '')
      .replace(/pending verification/gi, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Generate 5 9:16 Cards based on Active Update according to Capstone Content Safety Rules
  const generateCards = (update: RegulatoryUpdate) => {
    const isMalayalam = selectedLanguage === 'Malayalam';
    const isHindi = selectedLanguage === 'Hindi';
    const isTamil = selectedLanguage === 'Tamil';

    const isTdsTcs =
      update.title.toLowerCase().includes('tds') ||
      update.title.toLowerCase().includes('tcs') ||
      update.category.toLowerCase().includes('tds') ||
      update.category.toLowerCase().includes('tcs') ||
      update.keyDevelopment.toLowerCase().includes('tds') ||
      update.keyDevelopment.toLowerCase().includes('tcs');

    if (isTdsTcs) {
      return [
        {
          cardNo: 1,
          title: 'CARD 1 — WHAT CHANGED',
          headerText: 'REGULATORY UPDATE',
          mainHeadline: 'TDS/TCS DEPOSIT DUE DATE — 7 AUGUST 2026',
          subHeadline:
            'The statutory due date for deposit of applicable TDS/TCS deducted or collected during July 2026 is 7 August 2026 for applicable non-government deductors and collectors.',
          footerText: 'Statutory Compliance Update',
        },
        {
          cardNo: 2,
          title: 'CARD 2 — WHO SHOULD REVIEW THIS?',
          headerText: 'WHO SHOULD REVIEW THIS?',
          mainHeadline: 'Applicable Deductors & Collectors',
          subHeadline: isMalayalam
            ? 'ജൂലൈ 2026-ലെ ബാധകമായ TDS/TCS ബാധ്യതകളുള്ള ബിസിനസ്സുകളും സ്ഥാപനങ്ങളും തങ്ങളുടെ അനുസരണ നില പരിശോധിക്കേണ്ടതാണ്.'
            : isHindi
            ? 'जुलाई 2026 के लिए लागू TDS/TCS देनदारियों वाले व्यवसायों और संस्थाओं को अपनी अनुपालन स्थिति की समीक्षा करनी चाहिए।'
            : isTamil
            ? 'ஜூலை 2026 க்கான பொருந்தக்கூடிய TDS/TCS பொறுப்புகளைக் கொண்ட வணிகங்களும் நிறுவனங்களும் தங்கள் இணக்க நிலையை மதிப்பாய்வு செய்ய வேண்டும்.'
            : 'Businesses and other entities having applicable TDS/TCS deduction or collection obligations for July 2026 should review their compliance position.',
          footerText: 'Applicability depends on statutory provisions',
        },
        {
          cardNo: 3,
          title: 'CARD 3 — WHY DOES IT MATTER?',
          headerText: 'WHY DOES IT MATTER?',
          mainHeadline: 'Deadline: 7 August 2026',
          subHeadline:
            'Delay in depositing applicable TDS/TCS may result in statutory consequences, including applicable interest and related compliance issues.\n\nDeadline: 7 August 2026.',
          footerText: 'Statutory Timeline Compliance',
        },
        {
          cardNo: 4,
          title: 'CARD 4 — RECOMMENDED ACTION',
          headerText: 'RECOMMENDED ACTION',
          mainHeadline: 'Verify Liability & Ensure Statutory Deposit',
          subHeadline:
            'Applicable deductors/collectors should verify their July 2026 TDS/TCS liability and ensure deposit within the applicable statutory timeline.\n\nWhere payment has already been completed, retain the relevant challan/payment evidence for compliance records.',
          footerText: 'Compliance Verification Guidance',
        },
        {
          cardNo: 5,
          title: 'CARD 5 — PROFESSIONAL INFORMATION',
          headerText: 'PROFESSIONAL INFORMATION',
          mainHeadline: 'PROFESSIONAL INFORMATION',
          subHeadline: isMalayalam
            ? 'ഈ റഗുലേറ്ററി അപ്‌ഡേറ്റ് പൊതുവായ വിവരങ്ങൾക്കായി പങ്കിടുന്നതാണ്.\n\nഓരോ സ്ഥാപനത്തിന്റെയും സാഹചര്യങ്ങൾക്കനുസരിച്ച് ഇതിന്റെ ബാധകത വ്യത്യാസപ്പെടാം.\n\nദയവായി പ്രസക്തമായ നിയമ വ്യവസ്ഥകൾ പരിശോധിച്ച് ആവശ്യമുള്ളിടത്ത് നിങ്ങളുടെ ചാർട്ടേഡ് അക്കൗണ്ടന്റെയോ ടാക്സ് ഉപദേഷ്ടാവിനെയോ സമീപിക്കുക.'
            : isHindi
            ? 'यह नियामक अपडेट सामान्य पेशेवर जानकारी के लिए साझा किया गया है।\n\nप्रत्येक संस्था की परिस्थितियों के आधार पर इसकी प्रयोज्यता भिन्न हो सकती है।\n\nकृपया लागू वैधानिक प्रावधानों का सत्यापन करें और आवश्यकतानुसार अपने चार्टर्ड अकाउंटेंट / कर सलाहकार से परामर्श लें।'
            : isTamil
            ? 'இந்த ஒழுங்குமுறை புதுப்பிப்பு பொதுவான தொழில்முறை தகவல்களுக்காகப் பகிரப்படுகிறது.\n\nஒவ்வொரு நிறுவனத்தின் சூழலைப் பொறுத்து இதன் பயன்பாடு வேறுபடலாம்.\n\nதயவுசெய்து பொருந்தக்கூடிய சட்டப் பிரிவுகளைச் சரிபார்த்து, தேவைப்படும்போது உங்கள் சார்ட்டர்டு அக்கவுண்டன்ட் / வரி ஆலோசகரைக் கலந்தாலோசிக்கவும்.'
            : 'This regulatory update is shared for general professional information.\n\nApplicability may vary based on the facts and circumstances of each entity.\n\nPlease verify the applicable statutory provisions and consult your Chartered Accountant / tax advisor where required.',
          footerText: 'General Professional Information Notice',
        },
      ];
    }

    // General Regulatory Update Cards Generator
    const cleanTitle = sanitizeInternalText(update.title);
    const cleanDevelopment = sanitizeInternalText(update.keyDevelopment || update.originalSummary);
    const cleanRef = sanitizeInternalText(update.referenceNo);
    const cleanAuthority = sanitizeInternalText(update.issuingAuthority);
    const cleanCategory = sanitizeInternalText(update.category);
    const cleanSubCategory = sanitizeInternalText(update.subCategory);
    const cleanDeadline = sanitizeInternalText(update.dates?.statutoryDeadline);
    const cleanAction = sanitizeInternalText(update.caRecommendedAction || update.impactAnalysis?.recommendedAction);
    const cleanImpact = sanitizeInternalText(update.impactAnalysis?.financialImpact || update.impactAnalysis?.whatChanged);
    const cleanComplianceImpact = sanitizeInternalText(update.impactAnalysis?.complianceImpact || update.impactAnalysis?.whoIsAffected);

    return [
      {
        cardNo: 1,
        title: 'CARD 1 — WHAT CHANGED',
        headerText: 'REGULATORY UPDATE',
        mainHeadline: cleanTitle,
        subHeadline: cleanDevelopment,
        footerText: cleanRef
          ? `Ref: ${cleanRef} • Statutory Update`
          : cleanAuthority
          ? `Source referenced: ${cleanAuthority}`
          : 'Statutory Compliance Update',
      },
      {
        cardNo: 2,
        title: 'CARD 2 — WHO SHOULD REVIEW THIS?',
        headerText: 'WHO SHOULD REVIEW THIS?',
        mainHeadline: `Applicable Category: ${cleanCategory}`,
        subHeadline: isMalayalam
          ? `ശ്രദ്ധിക്കുക: ${cleanCategory} മേഖലയിൽ പ്രവർത്തിക്കുന്ന ബിസിനസ്സുകൾ തങ്ങളുടെ അനുസരണ നില പരിശോധിക്കേണ്ടതാണ്.`
          : isHindi
          ? `ध्यान दें: ${cleanCategory} क्षेत्र में काम करने वाले व्यवसायों को अपनी अनुपालन स्थिति की समीक्षा करनी चाहिए।`
          : isTamil
          ? `கவனத்திற்கு: ${cleanCategory} துறையில் செயல்படும் வணிகங்கள் தங்கள் இணக்க நிலையை மதிப்பாய்வு செய்ய வேண்டும்.`
          : `Businesses and entities falling under ${cleanCategory} & ${cleanSubCategory} should review their compliance position.\n\n${cleanComplianceImpact}`,
        footerText: 'Applicability depends on statutory provisions',
      },
      {
        cardNo: 3,
        title: 'CARD 3 — WHY DOES IT MATTER?',
        headerText: 'WHY DOES IT MATTER?',
        mainHeadline: `Statutory Deadline: ${cleanDeadline || 'Immediate Action'}`,
        subHeadline: `Compliance Exposure & Consequence:\n${cleanImpact}\n\nApplicable Deadline: ${cleanDeadline || 'As per Statutory Schedule'}`,
        footerText: 'Statutory Compliance Timeline',
      },
      {
        cardNo: 4,
        title: 'CARD 4 — RECOMMENDED ACTION',
        headerText: 'RECOMMENDED ACTION',
        mainHeadline: 'Recommended Compliance Action',
        subHeadline: `Applicable businesses should:\n${cleanAction || 'Verify relevant statutory provisions and ensure timely compliance.'}`,
        footerText: 'Compliance Verification Guidance',
      },
      {
        cardNo: 5,
        title: 'CARD 5 — PROFESSIONAL INFORMATION',
        headerText: 'PROFESSIONAL INFORMATION',
        mainHeadline: 'PROFESSIONAL INFORMATION',
        subHeadline: isMalayalam
          ? 'ഈ റഗുലേറ്ററി അപ്‌ഡേറ്റ് പൊതുവായ വിവരങ്ങൾക്കായി പങ്കിടുന്നതാണ്.\n\nഓരോ സ്ഥാപനത്തിന്റെയും സാഹചര്യങ്ങൾക്കനുസരിച്ച് ഇതിന്റെ ബാധകത വ്യത്യാസപ്പെടാം.\n\nദയവായി പ്രസക്തമായ നിയമ വ്യവസ്ഥകൾ പരിശോധിച്ച് ആവശ്യമുള്ളിടത്ത് നിങ്ങളുടെ ചാർട്ടേഡ് അക്കൗണ്ടന്റെയോ ടാക്സ് ഉപദേഷ്ടാവിനെയോ സമീപിക്കുക.'
          : isHindi
          ? 'यह नियामक अपडेट सामान्य पेशेवर जानकारी के लिए साझा किया गया है।\n\nप्रत्येक संस्था की परिस्थितियों के आधार पर इसकी प्रयोज्यता भिन्न हो सकती है।\n\nकृपया लागू वैधानिक प्रावधानों का सत्यापन करें और आवश्यकतानुसार अपने चार्टर्ड अकाउंटेंट / कर सलाहकार से परामर्श लें।'
          : isTamil
          ? 'இந்த ஒழுங்குமுறை புதுப்பிப்பு பொதுவான தொழில்முறை தகவல்களுக்காகப் பகிரப்படுகிறது.\n\nஒவ்வொரு நிறுவனத்தின் சூழலைப் பொறுத்து இதன் பயன்பாடு வேறுபடலாம்.\n\nதயவுசெய்து பொருந்தக்கூடிய சட்டப் பிரிவுகளைச் சரிபார்த்து, தேவைப்படும்போது உங்கள் சார்ட்டர்டு அக்கவுண்டன்ட் / வரி ஆலோசகரைக் கலந்தாலோசிக்கவும்.'
          : 'This regulatory update is shared for general professional information.\n\nApplicability may vary based on the facts and circumstances of each entity.\n\nPlease verify the applicable statutory provisions and consult your Chartered Accountant / tax advisor where required.',
        footerText: 'General Professional Information Notice',
      },
    ];
  };

  const cards = activeUpdate ? generateCards(activeUpdate) : [];

  const handleCopyCard = (cardText: string, index: number) => {
    navigator.clipboard.writeText(cardText);
    setCopiedCardIndex(index);
    setTimeout(() => setCopiedCardIndex(null), 2000);
  };

  const getThemeClasses = () => {
    switch (selectedTheme) {
      case 'navy':
        return {
          bg: 'bg-slate-900 border-slate-800 text-white',
          accent: 'text-teal-400',
          badge: 'bg-teal-500/20 text-teal-300 border border-teal-500/30',
          footer: 'border-slate-800 bg-slate-950/80 text-slate-400',
        };
      case 'emerald':
        return {
          bg: 'bg-emerald-950 border-emerald-800 text-white',
          accent: 'text-emerald-300',
          badge: 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/30',
          footer: 'border-emerald-900 bg-emerald-950 text-emerald-300',
        };
      case 'amber':
        return {
          bg: 'bg-amber-950 border-amber-800 text-white',
          accent: 'text-amber-300',
          badge: 'bg-amber-500/20 text-amber-200 border border-amber-500/30',
          footer: 'border-amber-900 bg-amber-950 text-amber-300',
        };
      default:
        return {
          bg: 'bg-slate-800 border-slate-700 text-white',
          accent: 'text-sky-300',
          badge: 'bg-sky-500/20 text-sky-200 border border-sky-500/30',
          footer: 'border-slate-700 bg-slate-900 text-slate-400',
        };
    }
  };

  const themeStyle = getThemeClasses();

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <Smartphone className="w-4 h-4" />
            <span>MODULE 9 — WHATSAPP STATUS STUDIO V2 (9:16 CARDS)</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">WhatsApp Status 5-Card Series Studio</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Generates 5 vertical 9:16 status cards for client broadcasting & social engagement.
          </p>
        </div>
      </div>

      {/* Control Panel: Update Selection, Theme & Language */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Select Update */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Select Update:</label>
            <select
              value={activeUpdate?.id || ''}
              onChange={(e) => {
                const found = updates.find((u) => u.id === e.target.value);
                if (found) setSelectedUpdate(found);
              }}
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold"
            >
              {updates.map((u) => (
                <option key={u.id} value={u.id}>
                  [{u.category}] {u.title}
                </option>
              ))}
            </select>
          </div>

          {/* Theme Switcher */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Color Palette:</label>
            <div className="grid grid-cols-4 gap-1.5">
              {[
                { id: 'navy', label: 'Navy' },
                { id: 'emerald', label: 'Emerald' },
                { id: 'amber', label: 'Amber' },
                { id: 'slate', label: 'Slate' },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedTheme(t.id as any)}
                  className={`py-2 text-[10px] font-bold rounded-lg border transition-all cursor-pointer ${
                    selectedTheme === t.id
                      ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Language Switcher */}
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Broadcasting Language:</label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value as any)}
              className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-bold"
            >
              <option value="English">English</option>
              <option value="Malayalam">Malayalam (മലയാളം)</option>
              <option value="Hindi">Hindi (हिंदी)</option>
              <option value="Tamil">Tamil (தமிழ்)</option>
            </select>
          </div>
        </div>
      </div>

      {/* 5-Card 9:16 Studio Grid */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
          <Share2 className="w-4 h-4 text-teal-600" />
          <span>5-Card WhatsApp Broadcast Sequence (9:16 Vertical Cards)</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {cards.map((c, idx) => {
            const cardFullText = `*${c.headerText}*\n\n*${c.mainHeadline}*\n\n${c.subHeadline}\n\n_${c.footerText}_`;

            return (
              <div
                key={c.cardNo}
                className={`rounded-2xl border p-4 flex flex-col justify-between shadow-lg h-[460px] relative transition-all hover:scale-[1.02] ${themeStyle.bg}`}
              >
                {/* Header Badge */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${themeStyle.badge}`}>
                      {c.headerText}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">{c.cardNo}/5</span>
                  </div>

                  <h3 className={`text-sm font-black leading-tight mt-3 ${themeStyle.accent}`}>
                    {c.mainHeadline}
                  </h3>

                  <p className="text-xs font-medium opacity-90 whitespace-pre-wrap leading-relaxed mt-2">
                    {c.subHeadline}
                  </p>
                </div>

                {/* Footer Brand Info */}
                <div className="pt-3 border-t border-slate-700/60 space-y-2">
                  <div className="text-[10px] font-bold opacity-75">{c.footerText}</div>

                  <button
                    onClick={() => handleCopyCard(cardFullText, idx)}
                    className="w-full flex items-center justify-center space-x-1.5 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-bold transition-all cursor-pointer border border-white/20"
                  >
                    {copiedCardIndex === idx ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                        <span>COPIED!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span>COPY CARD #{c.cardNo}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
