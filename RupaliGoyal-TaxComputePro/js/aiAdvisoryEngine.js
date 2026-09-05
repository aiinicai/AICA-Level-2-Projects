/**
 * TaxCompute Pro - AI Tax Planning, Audit & Advisory Engine
 * Generates CA-grade statutory audit memoranda, optimization roadmaps, and risk warnings.
 */

export class AIAdvisoryEngine {

  static generateAdvisory(taxComparisonResult, advanceTaxResult, state) {
    const { newRegime, oldRegime, recommendedRegime, absoluteSavings, breakevenAnalytics } = taxComparisonResult;
    const isNew = recommendedRegime === 'NEW';
    const activeAssessee = state.assesseeType || 'individual_general';
    const activeName = state.assesseeDetails?.name || 'Assessee';
    const activePan = state.assesseeDetails?.pan || 'PAN_NOT_SPECIFIED';

    const observations = [];
    const taxSavingTips = [];
    const complianceWarnings = [];
    const corporatePgbpAdvisories = [];

    const salary = state.salary || {};
    const hp = state.houseProperty || {};
    const pgbp = state.pgbp || {};
    const cg = state.capitalGains || {};
    const os = state.otherSources || {};
    const deductions = state.deductions || {};

    const basicSalary = Number(salary.basicSalary || 0);
    const da = Number(salary.da || 0);
    const salaryForNps = basicSalary + da;
    const grossTotalIncome = isNew ? newRegime.grossTotalIncome : oldRegime.grossTotalIncome;

    // 1. Regime Optimization Analysis
    if (recommendedRegime === 'NEW') {
      observations.push({
        title: 'New Tax Regime u/s 115BAC(1A) is Highly Favorable',
        type: 'success',
        impact: `Net Savings: ₹${absoluteSavings.toLocaleString('en-IN')}`,
        detail: `The New Tax Regime provides lower progressive slab rates and an enhanced Standard Deduction of ₹75,000. Under current deductions (₹${(oldRegime.totalDeductionsAllowed || 0).toLocaleString('en-IN')}), opting for New Regime saves ₹${absoluteSavings.toLocaleString('en-IN')} in total tax liability.`
      });

      if (breakevenAnalytics.deductionDeficit > 0) {
        observations.push({
          title: 'Breakeven Deduction Threshold',
          type: 'info',
          impact: `Gap: ₹${breakevenAnalytics.deductionDeficit.toLocaleString('en-IN')}`,
          detail: `To make the Old Tax Regime equal or better than the New Regime, the assessee must marshal additional Chapter VI-A deductions & exemptions of at least ₹${breakevenAnalytics.deductionDeficit.toLocaleString('en-IN')} (totaling ₹${breakevenAnalytics.breakevenDeductionsNeeded.toLocaleString('en-IN')}).`
        });
      }
    } else if (recommendedRegime === 'OLD') {
      observations.push({
        title: 'Old Tax Regime Yields Superior Net Savings',
        type: 'success',
        impact: `Net Savings: ₹${absoluteSavings.toLocaleString('en-IN')}`,
        detail: `Due to substantial deductions and exemptions claimed under HRA u/s 10(13A), Home Loan Interest u/s 24(b), and Chapter VI-A (80C, 80D, 80CCD(1B)), the Old Regime delivers a tax benefit of ₹${absoluteSavings.toLocaleString('en-IN')} over New Regime.`
      });
    } else {
      observations.push({
        title: 'Regimes are Tax Neutral',
        type: 'info',
        impact: 'Zero difference',
        detail: 'Both New and Old tax regimes yield identical tax liabilities. You may prefer New Regime for reduced compliance documentation and simplified filing.'
      });
    }

    // 2. Section 80CCD(2) - Employer NPS Optimization (Allowed in BOTH Regimes!)
    const claimed80CCD2 = Number(deductions.sec80CCD2_employerNps || 0);
    const maxPossible80CCD2 = salaryForNps * 0.14;

    if (salaryForNps > 0) {
      if (claimed80CCD2 < maxPossible80CCD2) {
        const unutilizedNps = maxPossible80CCD2 - claimed80CCD2;
        const potentialTaxSaved = Math.round(unutilizedNps * 0.312); // approx 30% + cess
        taxSavingTips.push({
          section: 'Sec 80CCD(2)',
          opportunity: 'Maximize Employer NPS Contribution up to 14%',
          potentialSaving: `Up to ₹${potentialTaxSaved.toLocaleString('en-IN')}`,
          detail: `Finance Act now allows employer NPS contributions up to 14% of (Basic + DA) under BOTH Old and New Tax Regimes. Currently you have claimed ₹${claimed80CCD2.toLocaleString('en-IN')} out of eligible ₹${maxPossible80CCD2.toLocaleString('en-IN')}. Restructuring compensation with the employer can unlock ₹${unutilizedNps.toLocaleString('en-IN')} in tax-free salary deductions.`
        });
      }
    }

    // 3. Capital Gains Harvesting & Budget 2024 Calibration
    const netLtcg112a = Number(cg.ltcg112a_gross || 0);
    if (netLtcg112a > 0 && netLtcg112a < 125000) {
      const unusedExemption = 125000 - netLtcg112a;
      taxSavingTips.push({
        section: 'Sec 112A',
        opportunity: 'Unused ₹1,25,000 Annual LTCG Exemption',
        potentialSaving: `₹${Math.round(unusedExemption * 0.125).toLocaleString('en-IN')}`,
        detail: `Budget 2024 increased the tax-free LTCG threshold on listed equity and equity mutual funds to ₹1,25,000 per financial year. You have ₹${unusedExemption.toLocaleString('en-IN')} of unutilized exemption. Consider tax-loss or gain harvesting before March 31 to step up asset cost basis tax-free.`
      });
    }

    if (Number(cg.stcg111a_gross || 0) > 0) {
      taxSavingTips.push({
        section: 'Sec 111A / 112A',
        opportunity: 'Budget 2024 Revised Rates Reminder',
        potentialSaving: 'Rate Compliance',
        detail: 'Note that Short-Term Capital Gains on listed equities u/s 111A are now taxed at 20% (up from 15%), while Long-Term Capital Gains u/s 112A are taxed at 12.5% (up from 10%). Holding equity investments beyond 12 months reduces the tax rate from 20% to 12.5% and unlocks the ₹1.25L annual exemption.'
      });
    }

    // 4. House Property Set-off & Home Loan Strategy
    const hpList = hp.properties || [];
    const selfOccupiedProps = hpList.filter(p => p.type === 'self');
    const totalSelfInterest = selfOccupiedProps.reduce((sum, p) => sum + Number(p.loanInterest || 0) + Number(p.preConstructionInterest || 0), 0);

    if (selfOccupiedProps.length > 0 && isNew) {
      complianceWarnings.push({
        category: 'House Property & Regime Limitation',
        severity: 'medium',
        detail: `You have ₹${totalSelfInterest.toLocaleString('en-IN')} in self-occupied home loan interest. Under the New Tax Regime u/s 115BAC, interest on self-occupied house property is NOT allowable and cannot be set off. Ensure you factor this into your regime selection.`
      });
    }

    if (totalSelfInterest > 200000 && !isNew) {
      taxSavingTips.push({
        section: 'Sec 24(b)',
        opportunity: 'Co-borrowing & Multi-Property Restructuring',
        potentialSaving: 'Additional ₹2,00,000 per co-owner',
        detail: `Home loan interest deduction on self-occupied property is capped at ₹2,00,000. If the property is co-owned and co-borrowed with a spouse or parent, each co-owner can independently claim up to ₹2,00,000 u/s 24(b) plus ₹1,50,000 principal u/s 80C.`
      });
    }

    // 5. Presumptive PGBP & Section 44AB Audit Triggers
    if (pgbp.mode === 'presumptive') {
      const scheme = pgbp.presumptiveScheme || '44AD';
      if (scheme === '44AD') {
        const totalTurnover = Number(pgbp.sec44ad_digitalTurnover || 0) + Number(pgbp.sec44ad_cashTurnover || 0);
        const digitalTurnover = Number(pgbp.sec44ad_digitalTurnover || 0);
        const digitalRatio = digitalTurnover / (totalTurnover || 1);

        if (totalTurnover > 20000000 && digitalRatio < 0.95) {
          complianceWarnings.push({
            category: 'Tax Audit Trigger u/s 44AB',
            severity: 'high',
            detail: `Total turnover is ₹${totalTurnover.toLocaleString('en-IN')} with cash receipts exceeding 5%. The enhanced ₹3 Crore threshold applies ONLY if 95%+ transactions are digital. A statutory Tax Audit under Section 44AB is mandatory.`
          });
        }
        corporatePgbpAdvisories.push({
          title: 'Presumptive Scheme 44AD Maintenance',
          detail: 'No requirement to maintain formal books of accounts u/s 44AA or get accounts audited u/s 44AB provided deemed profit (6% digital / 8% cash) is declared. Advance tax is payable in a single installment by 15th March.'
        });
      } else if (scheme === '44ADA') {
        const grossReceipts = Number(pgbp.sec44ada_grossReceipts || 0);
        const declaredProfit = Number(pgbp.sec44ada_declaredProfit || 0);
        const minProfit = grossReceipts * 0.50;

        if (declaredProfit < minProfit && grossTotalIncome > (isNew ? 300000 : 250000)) {
          complianceWarnings.push({
            category: 'Section 44ADA Audit Risk',
            severity: 'high',
            detail: `Declared professional profit (₹${declaredProfit.toLocaleString('en-IN')}) is below the statutory 50% deemed profit (₹${minProfit.toLocaleString('en-IN')}). Under Section 44ADA(4), maintenance of books u/s 44AA and tax audit u/s 44AB by a Chartered Accountant is required.`
          });
        }
      }
    } else if (pgbp.mode === 'books') {
      corporatePgbpAdvisories.push({
        title: 'Section 43B(h) Micro & Small Enterprises Compliance',
        detail: 'Statutory payments to registered MSME vendors must be settled within 15/45 days as per MSMED Act 2006. Any outstanding payables at year-end are strictly disallowed as income add-backs under Section 43B(h).'
      });
      corporatePgbpAdvisories.push({
        title: 'Section 32 Block Depreciation Reconciliation',
        detail: 'Ensure IT depreciation schedule complies with Appendix I block rates (e.g. Computers @ 40%, Plant & Machinery @ 15%) rather than Companies Act Schedule II straight-line rates.'
      });
    }

    // 6. Section 115BAA / Corporate Concession Advisory
    if (activeAssessee === 'company_reg_25' || activeAssessee === 'company_reg_30') {
      corporatePgbpAdvisories.push({
        title: 'Section 115BAA Migration Feasibility (22% Flat Tax)',
        detail: 'Opting for Section 115BAA provides an effective tax rate of 25.168% (inclusive of 10% surcharge & 4% cess) with complete exemption from Minimum Alternate Tax (MAT u/s 115JB). Check unutilized MAT credit before exercising Form 10-IC.'
      });
    }

    // 7. Advance Tax & Statutory Interest Advisory
    if (advanceTaxResult.isAdvanceTaxApplicable) {
      if (advanceTaxResult.totalStatutoryInterest > 0) {
        complianceWarnings.push({
          category: 'Penal Interest Liability u/s 234A/B/C',
          severity: 'high',
          detail: `Shortfall in advance tax has triggered ₹${advanceTaxResult.totalStatutoryInterest.toLocaleString('en-IN')} in mandatory penal interest (Sec 234C: ₹${advanceTaxResult.interest234C.amount.toLocaleString('en-IN')}, Sec 234B: ₹${advanceTaxResult.interest234B.amount.toLocaleString('en-IN')}, Sec 234A: ₹${advanceTaxResult.interest234A.amount.toLocaleString('en-IN')}). Pay the balance self-assessment tax immediately via e-Pay Tax on the Income Tax Portal (Challan 280) to arrest further monthly interest accretion.`
        });
      } else {
        observations.push({
          title: 'Advance Tax Compliance is on Track',
          type: 'success',
          impact: 'Zero penal interest',
          detail: 'Advance tax installments meet the statutory quarterly thresholds (15%, 45%, 75%, 100%), avoiding any Section 234C or 234B penal interest.'
        });
      }
    }

    return {
      executiveSummary: {
        assesseeName: activeName,
        pan: activePan,
        assesseeType: activeAssessee,
        assessmentYear: state.assessmentYear || '2026-27',
        financialYear: '2025-26',
        grossTotalIncome,
        recommendedRegime,
        totalTaxLiability: isNew ? newRegime.taxComputation.totalTaxLiability : oldRegime.taxComputation.totalTaxLiability,
        netPayableOrRefundable: isNew ? newRegime.taxComputation.netTaxPayableOrRefundable : oldRegime.taxComputation.netTaxPayableOrRefundable,
        statutoryInterest: advanceTaxResult.totalStatutoryInterest,
        dateGenerated: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
      },
      observations,
      taxSavingTips,
      complianceWarnings,
      corporatePgbpAdvisories
    };
  }
}
