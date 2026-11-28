import type { LanguageCode, ModuleId } from '../types/mis';

export const MODULE_META: {
  id: ModuleId;
  group: 'Core MIS' | 'Operations & Delivery' | 'Treasury & Risk' | 'Governance & Tools';
  labelEn: string;
  labelAr: string;
}[] = [
  { id: 'executive', group: 'Core MIS', labelEn: 'Executive Dashboard', labelAr: 'لوحة القيادة التنفيذية' },
  { id: 'financial-mis', group: 'Core MIS', labelEn: 'Financial MIS & IFRS', labelAr: 'التقارير المالية والمعايير' },
  { id: 'cashflow-treasury', group: 'Core MIS', labelEn: 'Cash Flow & Treasury', labelAr: 'التدفقات النقدية والخزينة' },
  { id: 'project-performance', group: 'Core MIS', labelEn: 'Project Performance', labelAr: 'أداء المشاريع' },
  { id: 'sales-inventory', group: 'Operations & Delivery', labelEn: 'Sales & Inventory', labelAr: 'المبيعات والمخزون' },
  { id: 'collections', group: 'Operations & Delivery', labelEn: 'Customer Collections', labelAr: 'تحصيلات العملاء' },
  { id: 'construction', group: 'Operations & Delivery', labelEn: 'Construction & Planning', labelAr: 'الإنشاءات والتخطيط' },
  { id: 'budget-cost', group: 'Operations & Delivery', labelEn: 'Budget & Cost Control', labelAr: 'الموازنة وضبط التكاليف' },
  { id: 'contracts', group: 'Operations & Delivery', labelEn: 'Contracts & Procurement', labelAr: 'العقود والمشتريات' },
  { id: 'financing', group: 'Treasury & Risk', labelEn: 'Financing & Covenants', labelAr: 'التمويل والتعهدات البنكية' },
  { id: 'feasibility', group: 'Treasury & Risk', labelEn: 'Feasibility & Scenarios', labelAr: 'الجدوى والسيناريوهات' },
  { id: 'risk-compliance', group: 'Treasury & Risk', labelEn: 'Risk & Compliance', labelAr: 'المخاطر والامتثال' },
  { id: 'handover-warranty', group: 'Treasury & Risk', labelEn: 'Handover & Warranty', labelAr: 'التسليم والضمان' },
  { id: 'rental-properties', group: 'Treasury & Risk', labelEn: 'Rental Properties', labelAr: 'العقارات المؤجرة' },
  { id: 'ai-analyst', group: 'Governance & Tools', labelEn: 'AI Management Analyst', labelAr: 'المحلل الإداري الذكي' },
  { id: 'data-upload', group: 'Governance & Tools', labelEn: 'Data Upload & GL Map', labelAr: 'رفع البيانات وربط الحسابات' },
  { id: 'workflow-controls', group: 'Governance & Tools', labelEn: 'MIS Workflow & Locks', labelAr: 'سير العمل والإغلاق الشهري' },
  { id: 'reports-exports', group: 'Governance & Tools', labelEn: 'Reports & Exports', labelAr: 'التقارير والتصدير' },
  { id: 'settings-admin', group: 'Governance & Tools', labelEn: 'Security, Backup & Admin', labelAr: 'الأمان والنسخ الاحتياطي' },
];

export const UI_TEXT: Record<LanguageCode, Record<string, string>> = {
  en: {
    brand: 'RealEstate 360',
    consolidated: 'Consolidated Group (3 Entities)',
    allProjects: 'All 5 Developments',
    searchPlaceholder: 'Search modules, projects, units, GL accounts...',
    maskOn: 'Mask Values',
    maskOff: 'Masked',
    present: 'Present',
    exitPresent: 'Exit Presentation',
    setupWizard: 'Setup Wizard',
    reconciled: 'Reconciled (0.000 OMR)',
    unreconciled: 'Unreconciled Variance',
    periodLabel: 'Period',
    basisLabel: 'Basis',
    currencyLabel: 'Currency',
    companyLabel: 'Entity',
    projectLabel: 'Project',
  },
  ar: {
    brand: 'عقار 360',
    consolidated: 'المجموعة الموحدة (3 شركات)',
    allProjects: 'جميع المشاريع (5)',
    searchPlaceholder: 'ابحث في الوحدات، المشاريع، الحسابات...',
    maskOn: 'إخفاء الأرقام',
    maskOff: 'الأرقام مخفية',
    present: 'وضع العرض',
    exitPresent: 'إنهاء العرض',
    setupWizard: 'معالج الإعداد',
    reconciled: 'مطابق (0.000 ر.ع)',
    unreconciled: 'فرق غير مطابق',
    periodLabel: 'الفترة',
    basisLabel: 'الأساس',
    currencyLabel: 'العملة',
    companyLabel: 'الشركة',
    projectLabel: 'المشروع',
  },
};

export function t(lang: LanguageCode, key: string): string {
  return UI_TEXT[lang][key] ?? UI_TEXT.en[key] ?? key;
}
