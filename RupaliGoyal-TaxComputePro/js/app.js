/**
 * TaxCompute Pro - Application Controller & UI View Binder
 */

import { MASTER_RATES } from './masterRates.js';
import { TaxEngine } from './taxEngine.js';
import { AdvanceTaxEngine } from './advanceTaxEngine.js';
import { AIAdvisoryEngine } from './aiAdvisoryEngine.js';
import { AppState, PRESET_PROFILES } from './state.js';

// Format currency in Indian numbering system
export function formatINR(amount) {
  if (isNaN(amount) || amount === null || amount === undefined) return '₹0';
  const num = Math.round(amount);
  const isNegative = num < 0;
  const absNum = Math.abs(num);
  const formatted = absNum.toLocaleString('en-IN');
  return isNegative ? `- ₹${formatted}` : `₹${formatted}`;
}

export function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'success' ? '✅' : (type === 'error' ? '⚠️' : 'ℹ️');
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

class AppController {
  constructor() {
    this.appState = new AppState();
    this.currentMasterTab = 'mtab-slabs';
    this.init();
  }

  init() {
    this.bindNavigation();
    this.bindDirectSheetInputs();
    this.bindAssesseeControls();
    this.bindSalaryInputs();
    this.bindHpInputs();
    this.bindPgbpInputs();
    this.bindCgInputs();
    this.bindOsInputs();
    this.bindDeductionsInputs();
    this.bindAdvanceTaxInputs();
    this.bindMasterRatesTabs();
    this.bindHeaderActions();

    // Subscribe to state changes
    this.appState.subscribe((state) => {
      this.syncInputsFromState(state);
      this.render();
    });

    // Initial render
    this.syncInputsFromState(this.appState.getState());
    this.render();
  }

  bindNavigation() {
    // Main Tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const targetTabId = btn.getAttribute('data-tab');
        document.querySelectorAll('.tab-content').forEach(pane => pane.classList.remove('active'));
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) targetPane.classList.add('active');
      });
    });

    // 5 Heads Sub-tabs
    const subtabBtns = document.querySelectorAll('.subtab-btn');
    subtabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const subtabId = btn.getAttribute('data-subtab');
        if (!subtabId) return;
        subtabBtns.forEach(b => {
          if (b.hasAttribute('data-subtab')) b.classList.remove('active');
        });
        btn.classList.add('active');
        document.querySelectorAll('.subtab-pane').forEach(p => p.classList.remove('active'));
        const target = document.getElementById(subtabId);
        if (target) target.classList.add('active');
      });
    });
  }

  bindDirectSheetInputs() {
    // Direct Sheet 1: Salary
    const dsSalaryBasicDa = document.getElementById('ds_salaryBasicDa');
    const dsSalaryHra = document.getElementById('ds_salaryHra');
    const dsSalaryRentPaid = document.getElementById('ds_salaryRentPaid');
    const dsSalaryIsMetro = document.getElementById('ds_salaryIsMetro');
    const dsSalaryOtherAllowances = document.getElementById('ds_salaryOtherAllowances');

    const updateSalaryFromDirect = () => {
      const state = this.appState.getState();
      state.salary = state.salary || {};
      const totalBasicDa = Number(dsSalaryBasicDa?.value || 0);
      state.salary.basicSalary = Math.round(totalBasicDa * 0.8333); // split basic
      state.salary.da = totalBasicDa - state.salary.basicSalary;
      state.salary.hraReceived = Number(dsSalaryHra?.value || 0);
      state.salary.rentPaid = Number(dsSalaryRentPaid?.value || 0);
      state.salary.isMetro = Boolean(dsSalaryIsMetro?.checked);
      state.salary.specialAllowance = Number(dsSalaryOtherAllowances?.value || 0);
      this.appState.setState(state);
    };

    [dsSalaryBasicDa, dsSalaryHra, dsSalaryRentPaid, dsSalaryOtherAllowances].forEach(el => {
      if (el) el.addEventListener('input', updateSalaryFromDirect);
    });
    if (dsSalaryIsMetro) dsSalaryIsMetro.addEventListener('change', updateSalaryFromDirect);

    // Direct Sheet 2: House Property
    const dsHpSelfInterest = document.getElementById('ds_hpSelfInterest');
    const dsHpLetoutRent = document.getElementById('ds_hpLetoutRent');
    const dsHpLetoutExpenses = document.getElementById('ds_hpLetoutExpenses');

    const updateHpFromDirect = () => {
      const state = this.appState.getState();
      state.houseProperty = { properties: [] };
      const selfInt = Number(dsHpSelfInterest?.value || 0);
      const letoutRent = Number(dsHpLetoutRent?.value || 0);
      const letoutExp = Number(dsHpLetoutExpenses?.value || 0);

      if (selfInt > 0 || letoutRent === 0) {
        state.houseProperty.properties.push({
          id: 1,
          propertyName: 'Primary Residence (Self-Occupied)',
          type: 'self',
          grossRent: 0,
          municipalTaxes: 0,
          loanInterest: selfInt,
          preConstructionInterest: 0
        });
      }
      if (letoutRent > 0) {
        state.houseProperty.properties.push({
          id: 2,
          propertyName: 'Let-out Property',
          type: 'letout',
          grossRent: letoutRent,
          municipalTaxes: Math.round(letoutExp * 0.1),
          loanInterest: Math.round(letoutExp * 0.9),
          preConstructionInterest: 0
        });
      }
      this.appState.setState(state);
    };

    [dsHpSelfInterest, dsHpLetoutRent, dsHpLetoutExpenses].forEach(el => {
      if (el) el.addEventListener('input', updateHpFromDirect);
    });

    // Direct Sheet 3: PGBP
    const dsPgbpModeSelect = document.getElementById('ds_pgbpModeSelect');
    const dsPgbpGrossInput = document.getElementById('ds_pgbpGrossInput');

    const updatePgbpFromDirect = () => {
      const state = this.appState.getState();
      state.pgbp = state.pgbp || {};
      const modeVal = dsPgbpModeSelect?.value || 'presumptive_44ad';
      const grossVal = Number(dsPgbpGrossInput?.value || 0);

      if (modeVal === 'presumptive_44ad') {
        state.pgbp.mode = 'presumptive';
        state.pgbp.presumptiveScheme = '44AD';
        state.pgbp.sec44ad_digitalTurnover = grossVal;
        state.pgbp.sec44ad_cashTurnover = 0;
        state.pgbp.sec44ad_declaredDigitalProfit = Math.round(grossVal * 0.06);
        state.pgbp.sec44ad_declaredCashProfit = 0;
      } else if (modeVal === 'presumptive_44ada') {
        state.pgbp.mode = 'presumptive';
        state.pgbp.presumptiveScheme = '44ADA';
        state.pgbp.sec44ada_grossReceipts = grossVal;
        state.pgbp.sec44ada_cashReceipts = 0;
        state.pgbp.sec44ada_declaredProfit = Math.round(grossVal * 0.50);
      } else {
        state.pgbp.mode = 'books';
        state.pgbp.netProfitAsPerPL = grossVal;
        state.pgbp.disallowanceSec40a = 0;
        state.pgbp.disallowanceSec43B = 0;
        state.pgbp.disallowanceSec40A3 = 0;
        state.pgbp.otherInadmissibleExpenses = 0;
        state.pgbp.bookDepreciation = 0;
        state.pgbp.itDepreciationSec32 = 0;
      }
      this.appState.setState(state);
    };

    if (dsPgbpModeSelect) dsPgbpModeSelect.addEventListener('change', updatePgbpFromDirect);
    if (dsPgbpGrossInput) dsPgbpGrossInput.addEventListener('input', updatePgbpFromDirect);

    // Direct Sheet 4: Capital Gains
    const dsCgStcg111a = document.getElementById('ds_cgStcg111a');
    const dsCgLtcg112a = document.getElementById('ds_cgLtcg112a');
    const dsCgLtcg112 = document.getElementById('ds_cgLtcg112');
    const dsCgStcgNormal = document.getElementById('ds_cgStcgNormal');

    const updateCgFromDirect = () => {
      const state = this.appState.getState();
      state.capitalGains = state.capitalGains || {};
      state.capitalGains.stcg111a_gross = Number(dsCgStcg111a?.value || 0);
      state.capitalGains.ltcg112a_gross = Number(dsCgLtcg112a?.value || 0);
      state.capitalGains.ltcg112_gross = Number(dsCgLtcg112?.value || 0);
      state.capitalGains.stcgNormal_gross = Number(dsCgStcgNormal?.value || 0);
      this.appState.setState(state);
    };

    [dsCgStcg111a, dsCgLtcg112a, dsCgLtcg112, dsCgStcgNormal].forEach(el => {
      if (el) el.addEventListener('input', updateCgFromDirect);
    });

    // Direct Sheet 5: Other Sources
    const dsOsInterest = document.getElementById('ds_osInterest');
    const dsOsDividend = document.getElementById('ds_osDividend');
    const dsOsSpecial = document.getElementById('ds_osSpecial');

    const updateOsFromDirect = () => {
      const state = this.appState.getState();
      state.otherSources = state.otherSources || {};
      const intVal = Number(dsOsInterest?.value || 0);
      state.otherSources.savingsInterest = Math.round(intVal * 0.3);
      state.otherSources.termDepositInterest = intVal - state.otherSources.savingsInterest;
      state.otherSources.dividendIncome = Number(dsOsDividend?.value || 0);
      state.otherSources.cryptoVdaIncome115BBH = Number(dsOsSpecial?.value || 0);
      this.appState.setState(state);
    };

    [dsOsInterest, dsOsDividend, dsOsSpecial].forEach(el => {
      if (el) el.addEventListener('input', updateOsFromDirect);
    });

    // Direct Sheet 6: Deductions & Taxes
    const dsDed80C = document.getElementById('ds_ded80C');
    const dsDed80CCD1B = document.getElementById('ds_ded80CCD1B');
    const dsDed80CCD2 = document.getElementById('ds_ded80CCD2');
    const dsDed80D = document.getElementById('ds_ded80D');
    const dsDedOther = document.getElementById('ds_dedOther');
    const dsPreTdsTcs = document.getElementById('ds_preTdsTcs');
    const dsPreAdvanceTax = document.getElementById('ds_preAdvanceTax');

    const updateDedFromDirect = () => {
      const state = this.appState.getState();
      state.deductions = state.deductions || {};
      state.deductions.sec80C_ppf = Number(dsDed80C?.value || 0);
      state.deductions.sec80CCD1B = Number(dsDed80CCD1B?.value || 0);
      state.deductions.sec80CCD2_employerNps = Number(dsDed80CCD2?.value || 0);
      state.deductions.sec80D_selfInsurance = Number(dsDed80D?.value || 0);
      state.deductions.otherDeductions = Number(dsDedOther?.value || 0);

      state.prepaidTaxes = state.prepaidTaxes || {};
      state.prepaidTaxes.tdsClaimed = Number(dsPreTdsTcs?.value || 0);
      state.prepaidTaxes.advanceTaxPaid = Number(dsPreAdvanceTax?.value || 0);
      this.appState.setState(state);
    };

    [dsDed80C, dsDed80CCD1B, dsDed80CCD2, dsDed80D, dsDedOther, dsPreTdsTcs, dsPreAdvanceTax].forEach(el => {
      if (el) el.addEventListener('input', updateDedFromDirect);
    });
  }

  bindAssesseeControls() {
    const presetSelect = document.getElementById('presetProfileSelect');
    if (presetSelect) {
      presetSelect.addEventListener('change', (e) => {
        this.appState.loadProfile(e.target.value);
        showToast(`Loaded preset profile: ${e.target.selectedOptions[0].text}`, 'success');
      });
    }

    const assesseeSelect = document.getElementById('assesseeTypeSelect');
    if (assesseeSelect) {
      assesseeSelect.addEventListener('change', (e) => {
        this.appState.setState({ assesseeType: e.target.value });
      });
    }

    const aySelect = document.getElementById('assessmentYear');
    if (aySelect) {
      aySelect.addEventListener('change', (e) => {
        this.appState.setState({ assessmentYear: e.target.value });
      });
    }

    // Text inputs in Assessee Master
    ['assesseeName', 'assesseePan', 'assesseeDob', 'residentialStatus', 'caName', 'caMembership', 'firmRegNo', 'udin'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.assesseeDetails = state.assesseeDetails || {};
          if (id === 'assesseeName') state.assesseeDetails.name = el.value;
          else if (id === 'assesseePan') state.assesseeDetails.pan = el.value.toUpperCase();
          else if (id === 'assesseeDob') state.assesseeDetails.dob = el.value;
          else if (id === 'residentialStatus') state.assesseeDetails.residentialStatus = el.value;
          else if (id === 'caName') state.assesseeDetails.caName = el.value;
          else if (id === 'caMembership') state.assesseeDetails.caMembership = el.value;
          else if (id === 'firmRegNo') state.assesseeDetails.firmRegNo = el.value;
          else if (id === 'udin') state.assesseeDetails.udin = el.value;
          this.appState.setState(state);
        });
      }
    });

    // Prepaid taxes
    ['tdsClaimed', 'tcsClaimed', 'advanceTaxPaidTotal', 'reliefSec89'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.prepaidTaxes = state.prepaidTaxes || {};
          if (id === 'tdsClaimed') state.prepaidTaxes.tdsClaimed = Number(el.value || 0);
          else if (id === 'tcsClaimed') state.prepaidTaxes.tcsClaimed = Number(el.value || 0);
          else if (id === 'advanceTaxPaidTotal') state.prepaidTaxes.advanceTaxPaid = Number(el.value || 0);
          else if (id === 'reliefSec89') state.reliefSec89_90 = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });
  }

  bindSalaryInputs() {
    const salaryFields = [
      'salaryBasic', 'salaryDa', 'salaryHra', 'salaryRentPaid', 'salaryLta',
      'salaryLtaExempt', 'salarySpecialAllowance', 'salaryBonus', 'salaryPerquisites',
      'salaryProfTax', 'salaryEntertainment'
    ];

    salaryFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.salary = state.salary || {};
          const keyMap = {
            salaryBasic: 'basicSalary', salaryDa: 'da', salaryHra: 'hraReceived',
            salaryRentPaid: 'rentPaid', salaryLta: 'ltaReceived', salaryLtaExempt: 'ltaExempt',
            salarySpecialAllowance: 'specialAllowance', salaryBonus: 'bonusCommission',
            salaryPerquisites: 'perquisites', salaryProfTax: 'professionalTax',
            salaryEntertainment: 'entertainmentAllowance'
          };
          state.salary[keyMap[id]] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });

    const isMetroEl = document.getElementById('salaryIsMetro');
    if (isMetroEl) {
      isMetroEl.addEventListener('change', () => {
        const state = this.appState.getState();
        state.salary = state.salary || {};
        state.salary.isMetro = isMetroEl.checked;
        this.appState.setState(state);
      });
    }
  }

  bindHpInputs() {
    const addBtn = document.getElementById('btnAddHpProperty');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        const state = this.appState.getState();
        state.houseProperty = state.houseProperty || { properties: [] };
        const newId = (state.houseProperty.properties.length + 1);
        state.houseProperty.properties.push({
          id: newId,
          propertyName: `Property ${newId} (Let-out)`,
          type: 'letout',
          grossRent: 240000,
          municipalTaxes: 12000,
          loanInterest: 100000,
          preConstructionInterest: 0
        });
        this.appState.setState(state);
        showToast('Added new House Property', 'info');
      });
    }
  }

  renderHpProperties(properties = []) {
    const container = document.getElementById('hpPropertiesContainer');
    if (!container) return;

    if (properties.length === 0) {
      container.innerHTML = `
        <div style="padding: 1.5rem; text-align: center; border: 1px dashed var(--border-subtle); border-radius: var(--radius-md); color: var(--text-muted);">
          No properties configured. Click "Add Property" above to add a Self-Occupied or Let-Out property.
        </div>
      `;
      return;
    }

    container.innerHTML = properties.map((prop, idx) => `
      <div class="card" style="background: var(--bg-secondary); border: 1px solid var(--border-subtle); padding: 1.25rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <input type="text" class="input-control hp-prop-name" data-idx="${idx}" value="${prop.propertyName || `Property ${idx + 1}`}" style="font-weight: 700; width: 300px;">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <select class="select-control hp-prop-type" data-idx="${idx}">
              <option value="self" ${prop.type === 'self' ? 'selected' : ''}>Self-Occupied</option>
              <option value="letout" ${prop.type === 'letout' ? 'selected' : ''}>Let-Out Property</option>
              <option value="deemed" ${prop.type === 'deemed' ? 'selected' : ''}>Deemed Let-Out</option>
            </select>
            <button class="btn btn-secondary btn-icon-only hp-prop-delete" data-idx="${idx}" style="color: var(--accent-crimson);" title="Delete Property">🗑️</button>
          </div>
        </div>

        <div class="grid-4">
          <div class="form-group" style="${prop.type === 'self' ? 'opacity: 0.5; pointer-events: none;' : ''}">
            <label class="form-label">Gross Rent Received / Receivable (GAV)</label>
            <div class="input-with-currency">
              <span class="currency-prefix">₹</span>
              <input type="number" class="input-control hp-prop-rent" data-idx="${idx}" value="${prop.grossRent || 0}">
            </div>
          </div>

          <div class="form-group" style="${prop.type === 'self' ? 'opacity: 0.5; pointer-events: none;' : ''}">
            <label class="form-label">Municipal Taxes Paid by Owner</label>
            <div class="input-with-currency">
              <span class="currency-prefix">₹</span>
              <input type="number" class="input-control hp-prop-taxes" data-idx="${idx}" value="${prop.municipalTaxes || 0}">
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Interest on Housing Loan u/s 24(b)</label>
            <div class="input-with-currency">
              <span class="currency-prefix">₹</span>
              <input type="number" class="input-control hp-prop-interest" data-idx="${idx}" value="${prop.loanInterest || 0}">
            </div>
            <span class="form-hint">${prop.type === 'self' ? 'Max ₹2,00,000 in Old Regime / Nil in New' : 'Actual interest deductible'}</span>
          </div>

          <div class="form-group">
            <label class="form-label">Pre-construction Interest (1/5th)</label>
            <div class="input-with-currency">
              <span class="currency-prefix">₹</span>
              <input type="number" class="input-control hp-prop-pre-interest" data-idx="${idx}" value="${prop.preConstructionInterest || 0}">
            </div>
          </div>
        </div>
      </div>
    `).join('');

    // Attach dynamic listeners
    container.querySelectorAll('.hp-prop-name').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].propertyName = e.target.value;
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-type').forEach(el => {
      el.addEventListener('change', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].type = e.target.value;
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-rent').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].grossRent = Number(e.target.value || 0);
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-taxes').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].municipalTaxes = Number(e.target.value || 0);
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-interest').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].loanInterest = Number(e.target.value || 0);
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-pre-interest').forEach(el => {
      el.addEventListener('input', (e) => {
        const i = e.target.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties[i].preConstructionInterest = Number(e.target.value || 0);
        this.appState.setState(state);
      });
    });

    container.querySelectorAll('.hp-prop-delete').forEach(el => {
      el.addEventListener('click', (e) => {
        const i = el.getAttribute('data-idx');
        const state = this.appState.getState();
        state.houseProperty.properties.splice(i, 1);
        this.appState.setState(state);
        showToast('Property deleted', 'info');
      });
    });
  }

  bindPgbpInputs() {
    const btnPresumptive = document.getElementById('btnPgbpPresumptive');
    const btnBooks = document.getElementById('btnPgbpBooks');
    const secPresumptive = document.getElementById('pgbpPresumptiveSection');
    const secBooks = document.getElementById('pgbpBooksSection');
    const schemeSelect = document.getElementById('pgbpSchemeSelect');

    const sec44ad = document.getElementById('sec44adInputs');
    const sec44ada = document.getElementById('sec44adaInputs');
    const sec44ae = document.getElementById('sec44aeInputs');

    if (btnPresumptive && btnBooks) {
      btnPresumptive.addEventListener('click', () => {
        btnPresumptive.className = 'btn btn-primary';
        btnBooks.className = 'btn btn-secondary';
        secPresumptive.style.display = 'flex';
        secBooks.style.display = 'none';
        const state = this.appState.getState();
        state.pgbp = state.pgbp || {};
        state.pgbp.mode = 'presumptive';
        this.appState.setState(state);
      });

      btnBooks.addEventListener('click', () => {
        btnBooks.className = 'btn btn-primary';
        btnPresumptive.className = 'btn btn-secondary';
        secBooks.style.display = 'flex';
        secPresumptive.style.display = 'none';
        const state = this.appState.getState();
        state.pgbp = state.pgbp || {};
        state.pgbp.mode = 'books';
        this.appState.setState(state);
      });
    }

    if (schemeSelect) {
      schemeSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        sec44ad.style.display = val === '44AD' ? 'grid' : 'none';
        sec44ada.style.display = val === '44ADA' ? 'grid' : 'none';
        sec44ae.style.display = val === '44AE' ? 'grid' : 'none';
        const state = this.appState.getState();
        state.pgbp = state.pgbp || {};
        state.pgbp.presumptiveScheme = val;
        this.appState.setState(state);
      });
    }

    const pgbpFields = [
      'sec44ad_digitalTurnover', 'sec44ad_cashTurnover', 'sec44ad_declaredDigitalProfit', 'sec44ad_declaredCashProfit',
      'sec44ada_grossReceipts', 'sec44ada_cashReceipts', 'sec44ada_declaredProfit',
      'sec44ae_heavyVehicleTons', 'sec44ae_heavyVehicleMonths', 'sec44ae_otherVehiclesCount', 'sec44ae_otherVehicleMonths',
      'netProfitAsPerPL', 'disallowanceSec40a', 'disallowanceSec43B', 'disallowanceSec40A3', 'otherInadmissibleExpenses',
      'bookDepreciation', 'itDepreciationSec32', 'incomeCreditedNotTaxableInPgbp'
    ];

    pgbpFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.pgbp = state.pgbp || {};
          state.pgbp[id] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });
  }

  bindCgInputs() {
    const cgFields = [
      'stcg111a_gross', 'stcgNormal_gross', 'ltcg112a_gross', 'ltcg112_gross', 'rollover54'
    ];
    cgFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.capitalGains = state.capitalGains || {};
          state.capitalGains[id] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });
  }

  bindOsInputs() {
    const osFields = [
      'savingsInterest', 'termDepositInterest', 'dividendIncome', 'familyPension',
      'otherRegularIncome', 'allowableExpensesSec57', 'lotteryIncome115BB', 'onlineGaming115BBJ', 'cryptoVdaIncome115BBH'
    ];
    osFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.otherSources = state.otherSources || {};
          state.otherSources[id] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });
  }

  bindDeductionsInputs() {
    const dedFields = [
      'sec80C_ppf', 'sec80C_epf', 'sec80C_elss', 'sec80C_lic', 'sec80C_homeLoanPrincipal', 'sec80C_tuitionFees',
      'sec80CCD1B', 'sec80CCD2_employerNps', 'sec80JJAA', 'sec80D_selfInsurance', 'sec80D_preventiveCheckup',
      'sec80D_parentsInsurance', 'sec80E_educationInterest', 'sec80EEA_housingInterest', 'sec80G_donations', 'otherDeductions'
    ];

    dedFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.deductions = state.deductions || {};
          state.deductions[id] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });

    const isParentsSeniorEl = document.getElementById('isParentsSenior');
    if (isParentsSeniorEl) {
      isParentsSeniorEl.addEventListener('change', () => {
        const state = this.appState.getState();
        state.deductions = state.deductions || {};
        state.deductions.isParentsSenior = isParentsSeniorEl.checked;
        this.appState.setState(state);
      });
    }
  }

  bindAdvanceTaxInputs() {
    const advFields = ['advPaidQ1', 'advPaidQ2', 'advPaidQ3', 'advPaidQ4'];
    advFields.forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', () => {
          const state = this.appState.getState();
          state.advanceTaxInstallments = state.advanceTaxInstallments || {};
          const keyMap = { advPaidQ1: 'q1_june15', advPaidQ2: 'q2_sept15', advPaidQ3: 'q3_dec15', advPaidQ4: 'q4_mar15' };
          state.advanceTaxInstallments[keyMap[id]] = Number(el.value || 0);
          this.appState.setState(state);
        });
      }
    });

    const dueDateSelect = document.getElementById('advanceTaxDueDateSelect');
    if (dueDateSelect) {
      dueDateSelect.addEventListener('change', (e) => {
        const state = this.appState.getState();
        state.advanceTaxInstallments = state.advanceTaxInstallments || {};
        state.advanceTaxInstallments.filingDueDate = e.target.value;
        this.appState.setState(state);
      });
    }

    const actualDateInput = document.getElementById('advanceTaxActualFilingDate');
    if (actualDateInput) {
      actualDateInput.addEventListener('input', (e) => {
        const state = this.appState.getState();
        state.advanceTaxInstallments = state.advanceTaxInstallments || {};
        state.advanceTaxInstallments.actualFilingDate = e.target.value;
        this.appState.setState(state);
      });
    }
  }

  bindMasterRatesTabs() {
    const mtabBtns = document.querySelectorAll('[data-mastertab]');
    mtabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        mtabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentMasterTab = btn.getAttribute('data-mastertab');
        this.renderMasterRates();
      });
    });
  }

  bindHeaderActions() {
    // Clear all figures to 0
    const clearBtn = document.getElementById('btnClearAllFigures');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        const emptyState = {
          assesseeType: 'individual_general',
          assessmentYear: '2026-27',
          financialYear: '2025-26',
          assesseeDetails: {
            name: '',
            pan: '',
            dob: '',
            residentialStatus: 'Resident',
            caName: 'Chartered Accountant',
            caMembership: '',
            firmRegNo: '',
            udin: ''
          },
          salary: { basicSalary: 0, da: 0, hraReceived: 0, rentPaid: 0, isMetro: true, ltaReceived: 0, ltaExempt: 0, specialAllowance: 0, bonusCommission: 0, perquisites: 0, professionalTax: 0 },
          houseProperty: { properties: [] },
          pgbp: { mode: 'presumptive', presumptiveScheme: '44AD', sec44ad_digitalTurnover: 0, sec44ad_cashTurnover: 0, sec44ad_declaredDigitalProfit: 0, sec44ad_declaredCashProfit: 0 },
          capitalGains: { stcg111a_gross: 0, stcgNormal_gross: 0, ltcg112a_gross: 0, ltcg112_gross: 0, rollover54: 0 },
          otherSources: { savingsInterest: 0, termDepositInterest: 0, dividendIncome: 0, familyPension: 0, otherRegularIncome: 0, allowableExpensesSec57: 0, lotteryIncome115BB: 0, onlineGaming115BBJ: 0, cryptoVdaIncome115BBH: 0 },
          deductions: { sec80C_ppf: 0, sec80C_epf: 0, sec80C_elss: 0, sec80C_lic: 0, sec80C_homeLoanPrincipal: 0, sec80C_tuitionFees: 0, sec80CCD1B: 0, sec80CCD2_employerNps: 0, sec80D_selfInsurance: 0, sec80D_preventiveCheckup: 0, sec80D_parentsInsurance: 0, sec80E_educationInterest: 0, sec80EEA_housingInterest: 0, sec80G_donations: 0, otherDeductions: 0 },
          prepaidTaxes: { tdsClaimed: 0, tcsClaimed: 0, advanceTaxPaid: 0 },
          advanceTaxInstallments: { q1_june15: 0, q2_sept15: 0, q3_dec15: 0, q4_mar15: 0, q4_mar31: 0, filingDueDate: '2026-07-31', actualFilingDate: '2026-07-25' }
        };
        this.appState.setState(emptyState);
        showToast('Worksheet cleared. Ready for fresh computation.', 'info');
      });
    }

    // Theme toggle
    const themeBtn = document.getElementById('btnThemeToggle');
    const themeIcon = document.getElementById('themeIcon');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        const html = document.documentElement;
        const isDark = html.getAttribute('data-theme') === 'dark';
        const newTheme = isDark ? 'light' : 'dark';
        html.setAttribute('data-theme', newTheme);
        themeIcon.textContent = isDark ? '🌙' : '☀️';
        showToast(`Switched to ${newTheme.toUpperCase()} theme`, 'info');
      });
    }

    // Export JSON
    const exportBtn = document.getElementById('btnExportJson');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        const jsonStr = this.appState.exportJson();
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const pan = this.appState.getState().assesseeDetails?.pan || 'CLIENT';
        a.download = `TaxComputePro_${pan}_FY2025-26.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Assessee computation data exported successfully', 'success');
      });
    }

    // Import JSON
    const importBtn = document.getElementById('btnImportJson');
    const fileInput = document.getElementById('jsonFileInput');
    if (importBtn && fileInput) {
      importBtn.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
          const res = this.appState.importJson(event.target.result);
          if (res.success) {
            showToast('Assessee data loaded successfully', 'success');
          } else {
            showToast(`Import error: ${res.error}`, 'error');
          }
        };
        reader.readAsText(file);
      });
    }

    // Print button
    const printBtn = document.getElementById('btnPrintStatement');
    if (printBtn) {
      printBtn.addEventListener('click', () => {
        // Switch to certified statement tab first
        const stmtTabBtn = document.querySelector('[data-tab="tab-certified-statement"]');
        if (stmtTabBtn) stmtTabBtn.click();
        setTimeout(() => window.print(), 300);
      });
    }

    // Copy memo
    const copyMemoBtn = document.getElementById('btnCopyMemo');
    if (copyMemoBtn) {
      copyMemoBtn.addEventListener('click', () => {
        const memoEl = document.getElementById('aiAdvisoryContainer');
        if (memoEl) {
          navigator.clipboard.writeText(memoEl.innerText).then(() => {
            showToast('AI Advisory Memorandum copied to clipboard', 'success');
          });
        }
      });
    }
  }

  syncInputsFromState(state) {
    if (state.assesseeType) {
      const el = document.getElementById('assesseeTypeSelect');
      if (el && el.value !== state.assesseeType) el.value = state.assesseeType;
    }

    const details = state.assesseeDetails || {};
    if (document.getElementById('assesseeName')) document.getElementById('assesseeName').value = details.name || '';
    if (document.getElementById('assesseePan')) document.getElementById('assesseePan').value = details.pan || '';
    if (document.getElementById('assesseeDob')) document.getElementById('assesseeDob').value = details.dob || '';
    if (document.getElementById('residentialStatus')) document.getElementById('residentialStatus').value = details.residentialStatus || 'Resident';
    if (document.getElementById('caName')) document.getElementById('caName').value = details.caName || '';
    if (document.getElementById('caMembership')) document.getElementById('caMembership').value = details.caMembership || '';
    if (document.getElementById('firmRegNo')) document.getElementById('firmRegNo').value = details.firmRegNo || '';
    if (document.getElementById('udin')) document.getElementById('udin').value = details.udin || '';

    // Prepaid taxes
    const prep = state.prepaidTaxes || {};
    if (document.getElementById('tdsClaimed')) document.getElementById('tdsClaimed').value = prep.tdsClaimed || 0;
    if (document.getElementById('tcsClaimed')) document.getElementById('tcsClaimed').value = prep.tcsClaimed || 0;
    if (document.getElementById('advanceTaxPaidTotal')) document.getElementById('advanceTaxPaidTotal').value = prep.advanceTaxPaid || 0;
    if (document.getElementById('reliefSec89')) document.getElementById('reliefSec89').value = state.reliefSec89_90 || 0;

    // Salary inputs
    const sal = state.salary || {};
    const totalBasicDa = (sal.basicSalary || 0) + (sal.da || 0);
    if (document.getElementById('salaryBasic')) document.getElementById('salaryBasic').value = sal.basicSalary || 0;
    if (document.getElementById('salaryDa')) document.getElementById('salaryDa').value = sal.da || 0;
    if (document.getElementById('salaryHra')) document.getElementById('salaryHra').value = sal.hraReceived || 0;
    if (document.getElementById('salaryRentPaid')) document.getElementById('salaryRentPaid').value = sal.rentPaid || 0;
    if (document.getElementById('salaryIsMetro')) document.getElementById('salaryIsMetro').checked = Boolean(sal.isMetro);
    if (document.getElementById('salaryLta')) document.getElementById('salaryLta').value = sal.ltaReceived || 0;
    if (document.getElementById('salaryLtaExempt')) document.getElementById('salaryLtaExempt').value = sal.ltaExempt || 0;
    if (document.getElementById('salarySpecialAllowance')) document.getElementById('salarySpecialAllowance').value = sal.specialAllowance || 0;
    if (document.getElementById('salaryBonus')) document.getElementById('salaryBonus').value = sal.bonusCommission || 0;
    if (document.getElementById('salaryPerquisites')) document.getElementById('salaryPerquisites').value = sal.perquisites || 0;
    if (document.getElementById('salaryProfTax')) document.getElementById('salaryProfTax').value = sal.professionalTax || 0;

    // Direct Sheet Salary
    if (document.getElementById('ds_salaryBasicDa')) document.getElementById('ds_salaryBasicDa').value = totalBasicDa;
    if (document.getElementById('ds_salaryHra')) document.getElementById('ds_salaryHra').value = sal.hraReceived || 0;
    if (document.getElementById('ds_salaryRentPaid')) document.getElementById('ds_salaryRentPaid').value = sal.rentPaid || 0;
    if (document.getElementById('ds_salaryIsMetro')) document.getElementById('ds_salaryIsMetro').checked = Boolean(sal.isMetro);
    const otherAllow = (sal.specialAllowance || 0) + (sal.bonusCommission || 0) + (sal.perquisites || 0);
    if (document.getElementById('ds_salaryOtherAllowances')) document.getElementById('ds_salaryOtherAllowances').value = otherAllow;

    // Render HP list & Direct Sheet HP
    const hpList = state.houseProperty?.properties || [];
    this.renderHpProperties(hpList);
    const selfProp = hpList.find(p => p.type === 'self');
    const letoutProp = hpList.find(p => p.type === 'letout' || p.type === 'deemed');
    if (document.getElementById('ds_hpSelfInterest')) document.getElementById('ds_hpSelfInterest').value = selfProp ? (selfProp.loanInterest || 0) : 0;
    if (document.getElementById('ds_hpLetoutRent')) document.getElementById('ds_hpLetoutRent').value = letoutProp ? (letoutProp.grossRent || 0) : 0;
    if (document.getElementById('ds_hpLetoutExpenses')) document.getElementById('ds_hpLetoutExpenses').value = letoutProp ? ((letoutProp.municipalTaxes || 0) + (letoutProp.loanInterest || 0)) : 0;

    // PGBP inputs
    const pgbp = state.pgbp || {};
    if (document.getElementById('sec44ad_digitalTurnover')) document.getElementById('sec44ad_digitalTurnover').value = pgbp.sec44ad_digitalTurnover || 0;
    if (document.getElementById('sec44ad_cashTurnover')) document.getElementById('sec44ad_cashTurnover').value = pgbp.sec44ad_cashTurnover || 0;
    if (document.getElementById('sec44ad_declaredDigitalProfit')) document.getElementById('sec44ad_declaredDigitalProfit').value = pgbp.sec44ad_declaredDigitalProfit || 0;
    if (document.getElementById('sec44ad_declaredCashProfit')) document.getElementById('sec44ad_declaredCashProfit').value = pgbp.sec44ad_declaredCashProfit || 0;
    if (document.getElementById('sec44ada_grossReceipts')) document.getElementById('sec44ada_grossReceipts').value = pgbp.sec44ada_grossReceipts || 0;
    if (document.getElementById('sec44ada_cashReceipts')) document.getElementById('sec44ada_cashReceipts').value = pgbp.sec44ada_cashReceipts || 0;
    if (document.getElementById('sec44ada_declaredProfit')) document.getElementById('sec44ada_declaredProfit').value = pgbp.sec44ada_declaredProfit || 0;
    if (document.getElementById('netProfitAsPerPL')) document.getElementById('netProfitAsPerPL').value = pgbp.netProfitAsPerPL || 0;
    if (document.getElementById('disallowanceSec40a')) document.getElementById('disallowanceSec40a').value = pgbp.disallowanceSec40a || 0;
    if (document.getElementById('disallowanceSec43B')) document.getElementById('disallowanceSec43B').value = pgbp.disallowanceSec43B || 0;
    if (document.getElementById('disallowanceSec40A3')) document.getElementById('disallowanceSec40A3').value = pgbp.disallowanceSec40A3 || 0;
    if (document.getElementById('otherInadmissibleExpenses')) document.getElementById('otherInadmissibleExpenses').value = pgbp.otherInadmissibleExpenses || 0;
    if (document.getElementById('bookDepreciation')) document.getElementById('bookDepreciation').value = pgbp.bookDepreciation || 0;
    if (document.getElementById('itDepreciationSec32')) document.getElementById('itDepreciationSec32').value = pgbp.itDepreciationSec32 || 0;
    if (document.getElementById('incomeCreditedNotTaxableInPgbp')) document.getElementById('incomeCreditedNotTaxableInPgbp').value = pgbp.incomeCreditedNotTaxableInPgbp || 0;

    // Direct Sheet PGBP
    if (document.getElementById('ds_pgbpGrossInput')) {
      if (pgbp.mode === 'books') {
        document.getElementById('ds_pgbpGrossInput').value = pgbp.netProfitAsPerPL || 0;
        if (document.getElementById('ds_pgbpModeSelect')) document.getElementById('ds_pgbpModeSelect').value = 'regular_books';
      } else if (pgbp.presumptiveScheme === '44ADA') {
        document.getElementById('ds_pgbpGrossInput').value = pgbp.sec44ada_grossReceipts || 0;
        if (document.getElementById('ds_pgbpModeSelect')) document.getElementById('ds_pgbpModeSelect').value = 'presumptive_44ada';
      } else {
        document.getElementById('ds_pgbpGrossInput').value = (pgbp.sec44ad_digitalTurnover || 0) + (pgbp.sec44ad_cashTurnover || 0);
        if (document.getElementById('ds_pgbpModeSelect')) document.getElementById('ds_pgbpModeSelect').value = 'presumptive_44ad';
      }
    }

    // Capital Gains inputs
    const cg = state.capitalGains || {};
    if (document.getElementById('stcg111a_gross')) document.getElementById('stcg111a_gross').value = cg.stcg111a_gross || 0;
    if (document.getElementById('stcgNormal_gross')) document.getElementById('stcgNormal_gross').value = cg.stcgNormal_gross || 0;
    if (document.getElementById('ltcg112a_gross')) document.getElementById('ltcg112a_gross').value = cg.ltcg112a_gross || 0;
    if (document.getElementById('ltcg112_gross')) document.getElementById('ltcg112_gross').value = cg.ltcg112_gross || 0;
    if (document.getElementById('rollover54')) document.getElementById('rollover54').value = cg.rollover54 || 0;

    // Direct Sheet CG
    if (document.getElementById('ds_cgStcg111a')) document.getElementById('ds_cgStcg111a').value = cg.stcg111a_gross || 0;
    if (document.getElementById('ds_cgLtcg112a')) document.getElementById('ds_cgLtcg112a').value = cg.ltcg112a_gross || 0;
    if (document.getElementById('ds_cgLtcg112')) document.getElementById('ds_cgLtcg112').value = cg.ltcg112_gross || 0;
    if (document.getElementById('ds_cgStcgNormal')) document.getElementById('ds_cgStcgNormal').value = cg.stcgNormal_gross || 0;

    // Other Sources inputs
    const os = state.otherSources || {};
    if (document.getElementById('savingsInterest')) document.getElementById('savingsInterest').value = os.savingsInterest || 0;
    if (document.getElementById('termDepositInterest')) document.getElementById('termDepositInterest').value = os.termDepositInterest || 0;
    if (document.getElementById('dividendIncome')) document.getElementById('dividendIncome').value = os.dividendIncome || 0;
    if (document.getElementById('familyPension')) document.getElementById('familyPension').value = os.familyPension || 0;
    if (document.getElementById('otherRegularIncome')) document.getElementById('otherRegularIncome').value = os.otherRegularIncome || 0;
    if (document.getElementById('allowableExpensesSec57')) document.getElementById('allowableExpensesSec57').value = os.allowableExpensesSec57 || 0;
    if (document.getElementById('lotteryIncome115BB')) document.getElementById('lotteryIncome115BB').value = os.lotteryIncome115BB || 0;
    if (document.getElementById('onlineGaming115BBJ')) document.getElementById('onlineGaming115BBJ').value = os.onlineGaming115BBJ || 0;
    if (document.getElementById('cryptoVdaIncome115BBH')) document.getElementById('cryptoVdaIncome115BBH').value = os.cryptoVdaIncome115BBH || 0;

    // Direct Sheet OS
    if (document.getElementById('ds_osInterest')) document.getElementById('ds_osInterest').value = (os.savingsInterest || 0) + (os.termDepositInterest || 0);
    if (document.getElementById('ds_osDividend')) document.getElementById('ds_osDividend').value = (os.dividendIncome || 0) + (os.familyPension || 0) + (os.otherRegularIncome || 0);
    if (document.getElementById('ds_osSpecial')) document.getElementById('ds_osSpecial').value = (os.cryptoVdaIncome115BBH || 0) + (os.lotteryIncome115BB || 0) + (os.onlineGaming115BBJ || 0);

    // Deductions inputs
    const ded = state.deductions || {};
    const total80C = (ded.sec80C_ppf || 0) + (ded.sec80C_epf || 0) + (ded.sec80C_elss || 0) + (ded.sec80C_lic || 0) + (ded.sec80C_homeLoanPrincipal || 0) + (ded.sec80C_tuitionFees || 0);
    const total80D = (ded.sec80D_selfInsurance || 0) + (ded.sec80D_preventiveCheckup || 0) + (ded.sec80D_parentsInsurance || 0);

    if (document.getElementById('sec80C_ppf')) document.getElementById('sec80C_ppf').value = ded.sec80C_ppf || 0;
    if (document.getElementById('sec80C_epf')) document.getElementById('sec80C_epf').value = ded.sec80C_epf || 0;
    if (document.getElementById('sec80C_elss')) document.getElementById('sec80C_elss').value = ded.sec80C_elss || 0;
    if (document.getElementById('sec80C_lic')) document.getElementById('sec80C_lic').value = ded.sec80C_lic || 0;
    if (document.getElementById('sec80C_homeLoanPrincipal')) document.getElementById('sec80C_homeLoanPrincipal').value = ded.sec80C_homeLoanPrincipal || 0;
    if (document.getElementById('sec80C_tuitionFees')) document.getElementById('sec80C_tuitionFees').value = ded.sec80C_tuitionFees || 0;
    if (document.getElementById('sec80CCD1B')) document.getElementById('sec80CCD1B').value = ded.sec80CCD1B || 0;
    if (document.getElementById('sec80CCD2_employerNps')) document.getElementById('sec80CCD2_employerNps').value = ded.sec80CCD2_employerNps || 0;
    if (document.getElementById('sec80JJAA')) document.getElementById('sec80JJAA').value = ded.sec80JJAA || 0;
    if (document.getElementById('sec80D_selfInsurance')) document.getElementById('sec80D_selfInsurance').value = ded.sec80D_selfInsurance || 0;
    if (document.getElementById('sec80D_preventiveCheckup')) document.getElementById('sec80D_preventiveCheckup').value = ded.sec80D_preventiveCheckup || 0;
    if (document.getElementById('sec80D_parentsInsurance')) document.getElementById('sec80D_parentsInsurance').value = ded.sec80D_parentsInsurance || 0;
    if (document.getElementById('isParentsSenior')) document.getElementById('isParentsSenior').checked = Boolean(ded.isParentsSenior);
    if (document.getElementById('sec80E_educationInterest')) document.getElementById('sec80E_educationInterest').value = ded.sec80E_educationInterest || 0;
    if (document.getElementById('sec80EEA_housingInterest')) document.getElementById('sec80EEA_housingInterest').value = ded.sec80EEA_housingInterest || 0;
    if (document.getElementById('sec80G_donations')) document.getElementById('sec80G_donations').value = ded.sec80G_donations || 0;
    if (document.getElementById('otherDeductions')) document.getElementById('otherDeductions').value = ded.otherDeductions || 0;

    // Direct Sheet Deductions & Taxes
    if (document.getElementById('ds_ded80C')) document.getElementById('ds_ded80C').value = total80C;
    if (document.getElementById('ds_ded80CCD1B')) document.getElementById('ds_ded80CCD1B').value = ded.sec80CCD1B || 0;
    if (document.getElementById('ds_ded80CCD2')) document.getElementById('ds_ded80CCD2').value = ded.sec80CCD2_employerNps || 0;
    if (document.getElementById('ds_ded80D')) document.getElementById('ds_ded80D').value = total80D;
    if (document.getElementById('ds_dedOther')) document.getElementById('ds_dedOther').value = (ded.sec80G_donations || 0) + (ded.sec80E_educationInterest || 0) + (ded.otherDeductions || 0);

    if (document.getElementById('ds_preTdsTcs')) document.getElementById('ds_preTdsTcs').value = (prep.tdsClaimed || 0) + (prep.tcsClaimed || 0);
    if (document.getElementById('ds_preAdvanceTax')) document.getElementById('ds_preAdvanceTax').value = prep.advanceTaxPaid || 0;

    // Advance tax inputs
    const adv = state.advanceTaxInstallments || {};
    if (document.getElementById('advPaidQ1')) document.getElementById('advPaidQ1').value = adv.q1_june15 || 0;
    if (document.getElementById('advPaidQ2')) document.getElementById('advPaidQ2').value = adv.q2_sept15 || 0;
    if (document.getElementById('advPaidQ3')) document.getElementById('advPaidQ3').value = adv.q3_dec15 || 0;
    if (document.getElementById('advPaidQ4')) document.getElementById('advPaidQ4').value = adv.q4_mar15 || 0;
    if (document.getElementById('advanceTaxDueDateSelect')) document.getElementById('advanceTaxDueDateSelect').value = adv.filingDueDate || '2026-07-31';
    if (document.getElementById('advanceTaxActualFilingDate')) document.getElementById('advanceTaxActualFilingDate').value = adv.actualFilingDate || '2026-07-25';
  }

  render() {
    const state = this.appState.getState();
    const comparison = TaxEngine.compareRegimes(state);
    const isNew = comparison.recommendedRegime === 'NEW';
    const activeResult = isNew ? comparison.newRegime : comparison.oldRegime;

    // Compute advance tax
    const advParams = {
      totalTaxLiability: activeResult.taxComputation.totalTaxLiability,
      tdsTcsClaimed: (state.prepaidTaxes?.tdsClaimed || 0) + (state.prepaidTaxes?.tcsClaimed || 0),
      reliefSec89_90: state.reliefSec89_90 || 0,
      assesseeType: state.assesseeType,
      isPresumptive44AD_ADA: (state.pgbp?.mode === 'presumptive' && (state.pgbp?.presumptiveScheme === '44AD' || state.pgbp?.presumptiveScheme === '44ADA')),
      installmentsPaid: state.advanceTaxInstallments || {},
      filingDueDate: state.advanceTaxInstallments?.filingDueDate || '2026-07-31',
      actualFilingDate: state.advanceTaxInstallments?.actualFilingDate || '2026-07-25',
      assessmentYear: state.assessmentYear || '2026-27'
    };
    const advTaxResult = AdvanceTaxEngine.computeAdvanceTaxAndInterest(advParams);

    // AI Advisory
    const advisory = AIAdvisoryEngine.generateAdvisory(comparison, advTaxResult, state);

    // 0. Render Direct Sheet Outputs
    this.renderDirectSheetOutputs(comparison, advTaxResult);

    // 1. Render KPI Ribbon
    this.renderKpiRibbon(comparison, activeResult, advTaxResult);

    // 2. Render Salary Live Breakdown
    this.renderSalarySummary(comparison);

    // 3. Render HP Summary
    this.renderHpSummary(comparison);

    // 4. Render PGBP Summary
    this.renderPgbpSummary(activeResult);

    // 5. Render CG Breakdown
    this.renderCgSummary(activeResult);

    // 6. Render Deductions Live Status
    this.renderDeductionsSummary(comparison);

    // 7. Render Regime Comparison Matrix & Chart
    this.renderComparisonMatrix(comparison);

    // 8. Render Advance Tax Schedule & 234 Interest
    this.renderAdvanceTaxView(advTaxResult);

    // 9. Render Master Rates Tab
    this.renderMasterRates();

    // 10. Render Certified Statement & AI Memo
    this.renderCertifiedStatement(comparison, advTaxResult, advisory, state);
  }

  renderDirectSheetOutputs(comparison, advTaxResult) {
    const { newRegime, oldRegime, recommendedRegime } = comparison;
    const isNew = recommendedRegime === 'NEW';
    const active = isNew ? newRegime : oldRegime;

    if (document.getElementById('ds_netSalaryOutput')) {
      document.getElementById('ds_netSalaryOutput').textContent = formatINR(active.heads.salary.netSalaryIncome);
    }
    if (document.getElementById('ds_netHpOutput')) {
      document.getElementById('ds_netHpOutput').textContent = formatINR(active.heads.houseProperty.allowableLossAgainstOtherHeads);
    }
    if (document.getElementById('ds_netPgbpOutput')) {
      document.getElementById('ds_netPgbpOutput').textContent = formatINR(active.heads.pgbp.netPgbpIncome);
    }
    if (document.getElementById('ds_netCgOutput')) {
      document.getElementById('ds_netCgOutput').textContent = formatINR(active.heads.capitalGains.totalTaxableCapitalGains);
    }
    if (document.getElementById('ds_netOsOutput')) {
      document.getElementById('ds_netOsOutput').textContent = formatINR(active.heads.otherSources.totalOtherSources);
    }
    if (document.getElementById('ds_gtiOutput')) {
      document.getElementById('ds_gtiOutput').textContent = formatINR(active.grossTotalIncome);
    }

    // New Regime card
    if (document.getElementById('ds_newTaxableIncome')) {
      document.getElementById('ds_newTaxableIncome').textContent = formatINR(newRegime.totalTaxableIncome);
    }
    if (document.getElementById('ds_newTaxLiability')) {
      document.getElementById('ds_newTaxLiability').textContent = formatINR(newRegime.taxComputation.totalTaxLiability);
    }
    if (document.getElementById('ds_newNetPayable')) {
      const netNew = newRegime.taxComputation.netTaxPayableOrRefundable;
      document.getElementById('ds_newNetPayable').textContent = netNew >= 0 ? `${formatINR(netNew)} (Payable)` : `${formatINR(Math.abs(netNew))} (Refund)`;
      document.getElementById('ds_newNetPayable').style.color = netNew >= 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)';
    }

    // Old Regime card
    if (document.getElementById('ds_oldTaxableIncome')) {
      document.getElementById('ds_oldTaxableIncome').textContent = formatINR(oldRegime.totalTaxableIncome);
    }
    if (document.getElementById('ds_oldTaxLiability')) {
      document.getElementById('ds_oldTaxLiability').textContent = formatINR(oldRegime.taxComputation.totalTaxLiability);
    }
    if (document.getElementById('ds_oldNetPayable')) {
      const netOld = oldRegime.taxComputation.netTaxPayableOrRefundable;
      document.getElementById('ds_oldNetPayable').textContent = netOld >= 0 ? `${formatINR(netOld)} (Payable)` : `${formatINR(Math.abs(netOld))} (Refund)`;
      document.getElementById('ds_oldNetPayable').style.color = netOld >= 0 ? 'var(--accent-crimson)' : 'var(--accent-emerald)';
    }
  }

  renderKpiRibbon(comparison, activeResult, advTaxResult) {
    const { newRegime, oldRegime, recommendedRegime, absoluteSavings } = comparison;

    document.getElementById('kpiGti').textContent = formatINR(activeResult.grossTotalIncome);
    document.getElementById('kpiDeductions').textContent = formatINR(oldRegime.totalDeductionsAllowed);
    document.getElementById('kpiDeductionsSubtext').textContent = `New: ${formatINR(newRegime.totalDeductionsAllowed)} | Old: ${formatINR(oldRegime.totalDeductionsAllowed)}`;

    document.getElementById('kpiNewRegimeTax').textContent = formatINR(newRegime.taxComputation.totalTaxLiability);
    document.getElementById('kpiOldRegimeTax').textContent = formatINR(oldRegime.taxComputation.totalTaxLiability);

    const badge = document.getElementById('kpiRecommendationBadge');
    if (recommendedRegime === 'NEW') {
      badge.className = 'badge-tag badge-new';
      badge.textContent = 'New Regime Better';
      document.getElementById('kpiSavings').textContent = formatINR(absoluteSavings);
      document.getElementById('kpiSavingsSubtext').textContent = 'Net Savings in New Regime';
    } else if (recommendedRegime === 'OLD') {
      badge.className = 'badge-tag badge-old';
      badge.textContent = 'Old Regime Better';
      document.getElementById('kpiSavings').textContent = formatINR(absoluteSavings);
      document.getElementById('kpiSavingsSubtext').textContent = 'Net Savings in Old Regime';
    } else {
      badge.className = 'badge-tag';
      badge.textContent = 'Neutral';
      document.getElementById('kpiSavings').textContent = '₹0';
      document.getElementById('kpiSavingsSubtext').textContent = 'Both Regimes Equal';
    }

    const netPayable = activeResult.taxComputation.netTaxPayableOrRefundable + advTaxResult.totalStatutoryInterest;
    const payableEl = document.getElementById('kpiNetPayable');
    if (netPayable > 0) {
      payableEl.textContent = formatINR(netPayable);
      payableEl.style.color = 'var(--accent-crimson)';
      document.getElementById('kpiPrepaidSubtext').textContent = `Net Payable (Incl. Int: ${formatINR(advTaxResult.totalStatutoryInterest)})`;
    } else {
      payableEl.textContent = formatINR(Math.abs(netPayable));
      payableEl.style.color = 'var(--accent-emerald)';
      document.getElementById('kpiPrepaidSubtext').textContent = 'Statutory Refund Receivable';
    }
  }

  renderSalarySummary(comparison) {
    const oldSal = comparison.oldRegime.heads.salary;
    const newSal = comparison.newRegime.heads.salary;

    document.getElementById('salSummaryGrossOld').textContent = formatINR(oldSal.grossSalary);
    document.getElementById('salSummaryGrossNew').textContent = formatINR(newSal.grossSalary);

    document.getElementById('salSummaryExemptionsOld').textContent = `- ${formatINR(oldSal.totalSec10Exemptions)}`;
    document.getElementById('salSummaryProfTaxOld').textContent = `- ${formatINR(oldSal.profTaxDeduction)}`;

    document.getElementById('salSummaryNetOld').textContent = formatINR(oldSal.netSalaryIncome);
    document.getElementById('salSummaryNetNew').textContent = formatINR(newSal.netSalaryIncome);
  }

  renderHpSummary(comparison) {
    const oldHp = comparison.oldRegime.heads.houseProperty;
    const newHp = comparison.newRegime.heads.houseProperty;

    document.getElementById('hpSummaryGrossOld').textContent = formatINR(oldHp.totalHpIncome);
    document.getElementById('hpSummaryAllowedOld').textContent = formatINR(oldHp.allowableLossAgainstOtherHeads);
    document.getElementById('hpSummaryCfOld').textContent = formatINR(oldHp.carryForwardHpLoss);

    document.getElementById('hpSummaryGrossNew').textContent = formatINR(newHp.totalHpIncome);
    document.getElementById('hpSummaryAllowedNew').textContent = formatINR(newHp.allowableLossAgainstOtherHeads);
    document.getElementById('hpSummaryCfNew').textContent = formatINR(newHp.carryForwardHpLoss);
  }

  renderPgbpSummary(activeResult) {
    const pgbp = activeResult.heads.pgbp;
    document.getElementById('pgbpComputedNet').textContent = formatINR(pgbp.netPgbpIncome);

    const badge = document.getElementById('pgbpAuditBadge');
    if (pgbp.details?.auditRequired) {
      badge.innerHTML = `<span class="badge-tag" style="background: rgba(244, 63, 94, 0.15); color: var(--accent-crimson); border: 1px solid rgba(244, 63, 94, 0.3);">⚠️ Tax Audit u/s 44AB Mandatory</span>`;
    } else {
      badge.innerHTML = `<span class="badge-tag" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald);">Audit Not Required</span>`;
    }
  }

  renderCgSummary(activeResult) {
    const cg = activeResult.heads.capitalGains;
    document.getElementById('cgBreakdownStcg111aGross').textContent = formatINR(cg.netStcg111a);
    document.getElementById('cgBreakdownStcg111aNet').textContent = formatINR(cg.netStcg111a);

    document.getElementById('cgBreakdownStcgNormalGross').textContent = formatINR(cg.netStcgNormal);
    document.getElementById('cgBreakdownStcgNormalNet').textContent = formatINR(cg.netStcgNormal);

    document.getElementById('cgBreakdownLtcg112aGross').textContent = formatINR(cg.netLtcg112aBeforeExemption);
    document.getElementById('cgBreakdownLtcg112aExempt').textContent = `- ${formatINR(cg.exemption112A)}`;
    document.getElementById('cgBreakdownLtcg112aNet').textContent = formatINR(cg.taxableLtcg112a);

    document.getElementById('cgBreakdownLtcg112Gross').textContent = formatINR(cg.netLtcg112 + cg.rollover54Exemptions);
    document.getElementById('cgBreakdownLtcg112Rollover').textContent = `- ${formatINR(cg.rollover54Exemptions)}`;
    document.getElementById('cgBreakdownLtcg112Net').textContent = formatINR(cg.netLtcg112);

    document.getElementById('cgBreakdownTotal').textContent = formatINR(cg.totalTaxableCapitalGains);
  }

  renderDeductionsSummary(comparison) {
    const oldDed = comparison.oldRegime.chapterVIA;
    document.getElementById('sec80CTotalClaimed').textContent = formatINR(oldDed.sec80C_gross || 0);
    document.getElementById('sec80CTotalAllowed').textContent = formatINR(oldDed.sec80C_allowed || 0);
  }

  renderComparisonMatrix(comparison) {
    const { newRegime, oldRegime, recommendedRegime, absoluteSavings, breakevenAnalytics } = comparison;

    // Recommendation badge in card header
    const compBadge = document.getElementById('comparisonRecommendationBadge');
    if (recommendedRegime === 'NEW') {
      compBadge.innerHTML = `<span class="badge-tag badge-new" style="font-size: 0.85rem; padding: 0.35rem 0.85rem;">🎉 New Regime Saves ${formatINR(absoluteSavings)}</span>`;
    } else if (recommendedRegime === 'OLD') {
      compBadge.innerHTML = `<span class="badge-tag badge-old" style="font-size: 0.85rem; padding: 0.35rem 0.85rem;">🎉 Old Regime Saves ${formatINR(absoluteSavings)}</span>`;
    } else {
      compBadge.innerHTML = `<span class="badge-tag" style="font-size: 0.85rem; padding: 0.35rem 0.85rem;">Regimes are Tax Neutral</span>`;
    }

    // Breakeven Banner
    document.getElementById('breakevenInsight').textContent = breakevenAnalytics.insight;
    document.getElementById('breakevenTarget').textContent = formatINR(breakevenAnalytics.breakevenDeductionsNeeded);

    // Matrix Table Rows
    const tbody = document.getElementById('regimeComparisonTableBody');
    if (!tbody) return;

    const rows = [
      { label: 'Income from Salaries (Sec 15-17)', oldVal: oldRegime.heads.salary.netSalaryIncome, newVal: newRegime.heads.salary.netSalaryIncome },
      { label: 'Income from House Property (Sec 22-27)', oldVal: oldRegime.heads.houseProperty.allowableLossAgainstOtherHeads, newVal: newRegime.heads.houseProperty.allowableLossAgainstOtherHeads },
      { label: 'Profits & Gains of Business / Profession (Sec 28-44)', oldVal: oldRegime.heads.pgbp.netPgbpIncome, newVal: newRegime.heads.pgbp.netPgbpIncome },
      { label: 'Capital Gains (Sec 45-55A)', oldVal: oldRegime.heads.capitalGains.totalTaxableCapitalGains, newVal: newRegime.heads.capitalGains.totalTaxableCapitalGains },
      { label: 'Income from Other Sources (Sec 56-59)', oldVal: oldRegime.heads.otherSources.totalOtherSources, newVal: newRegime.heads.otherSources.totalOtherSources },
      { label: 'Gross Total Income (GTI)', oldVal: oldRegime.grossTotalIncome, newVal: newRegime.grossTotalIncome, isHighlight: true },
      { label: 'Less: Chapter VI-A Deductions (80C, 80D, 80CCD, etc.)', oldVal: -oldRegime.totalDeductionsAllowed, newVal: -newRegime.totalDeductionsAllowed },
      { label: 'Total Taxable Income (Round off u/s 288A)', oldVal: oldRegime.totalTaxableIncome, newVal: newRegime.totalTaxableIncome, isHighlight: true },
      { label: 'Tax on Normal Income (Progressive Slabs)', oldVal: oldRegime.taxComputation.taxOnNormalIncome, newVal: newRegime.taxComputation.taxOnNormalIncome },
      { label: 'Tax on Special Rate Incomes (111A, 112A, 112, 115BB)', oldVal: oldRegime.taxComputation.taxOnSpecialIncome, newVal: newRegime.taxComputation.taxOnSpecialIncome },
      { label: 'Gross Tax Payable before Rebate', oldVal: oldRegime.taxComputation.baseTaxBeforeRebate, newVal: newRegime.taxComputation.baseTaxBeforeRebate },
      { label: 'Less: Rebate u/s 87A (incl. Marginal Relief)', oldVal: -oldRegime.taxComputation.rebate87A, newVal: -newRegime.taxComputation.rebate87A },
      { label: 'Tax Payable after Section 87A Rebate', oldVal: oldRegime.taxComputation.netTaxAfterRebate, newVal: newRegime.taxComputation.netTaxAfterRebate },
      { label: 'Add: Surcharge (after Marginal Relief)', oldVal: oldRegime.taxComputation.surcharge.netSurcharge, newVal: newRegime.taxComputation.surcharge.netSurcharge },
      { label: 'Add: Health & Education Cess @ 4%', oldVal: oldRegime.taxComputation.cess, newVal: newRegime.taxComputation.cess },
      { label: 'Total Tax Liability', oldVal: oldRegime.taxComputation.totalTaxLiability, newVal: newRegime.taxComputation.totalTaxLiability, isTotal: true }
    ];

    tbody.innerHTML = rows.map(r => {
      const diff = r.oldVal - r.newVal;
      let diffHtml = '<span style="color: var(--text-muted);">-</span>';
      if (diff > 0) diffHtml = `<span style="color: var(--accent-emerald); font-weight: 600;">+ ${formatINR(diff)}</span>`;
      else if (diff < 0) diffHtml = `<span style="color: var(--accent-crimson); font-weight: 600;">- ${formatINR(Math.abs(diff))}</span>`;

      return `
        <tr class="${r.isTotal ? 'total-row' : (r.isHighlight ? 'highlight-row' : '')}">
          <td>${r.label}</td>
          <td class="amount-cell">${formatINR(r.oldVal)}</td>
          <td class="amount-cell">${formatINR(r.newVal)}</td>
          <td style="text-align: center;">${diffHtml}</td>
        </tr>
      `;
    }).join('');

    // Render SVG Bar Chart
    this.renderComparisonChart(oldRegime, newRegime);
  }

  renderComparisonChart(oldRegime, newRegime) {
    const container = document.getElementById('regimeComparisonChartContainer');
    if (!container) return;

    const oldTax = oldRegime.taxComputation.totalTaxLiability;
    const newTax = newRegime.taxComputation.totalTaxLiability;
    const maxVal = Math.max(oldTax, newTax, 100000) * 1.2;

    const oldBarHeight = Math.round((oldTax / maxVal) * 180);
    const newBarHeight = Math.round((newTax / maxVal) * 180);

    const svg = `
      <svg class="chart-svg" width="600" height="260" viewBox="0 0 600 260" xmlns="http://www.w3.org/2000/svg">
        <!-- Grid lines -->
        <line x1="60" y1="210" x2="540" y2="210" stroke="var(--border-color)" stroke-width="2" />
        <line x1="60" y1="120" x2="540" y2="120" stroke="var(--border-subtle)" stroke-dasharray="4" />
        <line x1="60" y1="30" x2="540" y2="30" stroke="var(--border-subtle)" stroke-dasharray="4" />

        <!-- Old Regime Bar -->
        <rect x="140" y="${210 - oldBarHeight}" width="100" height="${oldBarHeight}" rx="6" fill="#f59e0b" opacity="0.9">
          <animate attributeName="height" from="0" to="${oldBarHeight}" dur="0.5s" fill="freeze" />
          <animate attributeName="y" from="210" to="${210 - oldBarHeight}" dur="0.5s" fill="freeze" />
        </rect>
        <text x="190" y="${Math.max(25, 200 - oldBarHeight)}" text-anchor="middle" fill="var(--text-primary)" font-size="13" font-weight="700" font-family="monospace">
          ${formatINR(oldTax)}
        </text>
        <text x="190" y="232" text-anchor="middle" fill="var(--text-secondary)" font-size="12" font-weight="600">
          Old Tax Regime
        </text>

        <!-- New Regime Bar -->
        <rect x="360" y="${210 - newBarHeight}" width="100" height="${newBarHeight}" rx="6" fill="#10b981" opacity="0.9">
          <animate attributeName="height" from="0" to="${newBarHeight}" dur="0.5s" fill="freeze" />
          <animate attributeName="y" from="210" to="${210 - newBarHeight}" dur="0.5s" fill="freeze" />
        </rect>
        <text x="410" y="${Math.max(25, 200 - newBarHeight)}" text-anchor="middle" fill="var(--text-primary)" font-size="13" font-weight="700" font-family="monospace">
          ${formatINR(newTax)}
        </text>
        <text x="410" y="232" text-anchor="middle" fill="var(--text-secondary)" font-size="12" font-weight="600">
          New Regime u/s 115BAC
        </text>
      </svg>
    `;

    container.innerHTML = svg;
  }

  renderAdvanceTaxView(advTaxResult) {
    document.getElementById('advTaxAssessedAmount').textContent = formatINR(advTaxResult.assessedTax);

    const appBadge = document.getElementById('advanceTaxApplicabilityBadge');
    if (advTaxResult.isAdvanceTaxApplicable) {
      appBadge.className = 'badge-tag badge-new';
      appBadge.textContent = 'Section 208 Applicable (Assessed Tax ≥ ₹10k)';
    } else {
      appBadge.className = 'badge-tag';
      appBadge.textContent = advTaxResult.isExemptSenior ? 'Exempt Senior Citizen u/s 207(2)' : 'Tax < ₹10k (Exempt from Advance Tax)';
    }

    // Schedule items
    if (advTaxResult.schedule && advTaxResult.schedule.length > 0) {
      const s = advTaxResult.schedule;
      if (s[0]) {
        document.getElementById('advReqQ1').textContent = formatINR(s[0].requiredCumulativeAmount);
        document.getElementById('advCumPaidQ1').textContent = formatINR(s[0].actualCumulativePaid);
        document.getElementById('advShortfallQ1').textContent = formatINR(s[0].shortfall);
        document.getElementById('advIntQ1').textContent = formatINR(s[0].interest234C);
        document.getElementById('advStatusQ1').innerHTML = s[0].status === 'Compliant'
          ? `<span style="color: var(--accent-emerald);">✅ Paid</span>`
          : `<span style="color: var(--accent-crimson);">⚠️ Shortfall</span>`;
      }
      if (s[1]) {
        document.getElementById('advReqQ2').textContent = formatINR(s[1].requiredCumulativeAmount);
        document.getElementById('advCumPaidQ2').textContent = formatINR(s[1].actualCumulativePaid);
        document.getElementById('advShortfallQ2').textContent = formatINR(s[1].shortfall);
        document.getElementById('advIntQ2').textContent = formatINR(s[1].interest234C);
        document.getElementById('advStatusQ2').innerHTML = s[1].status === 'Compliant'
          ? `<span style="color: var(--accent-emerald);">✅ Paid</span>`
          : `<span style="color: var(--accent-crimson);">⚠️ Shortfall</span>`;
      }
      if (s[2]) {
        document.getElementById('advReqQ3').textContent = formatINR(s[2].requiredCumulativeAmount);
        document.getElementById('advCumPaidQ3').textContent = formatINR(s[2].actualCumulativePaid);
        document.getElementById('advShortfallQ3').textContent = formatINR(s[2].shortfall);
        document.getElementById('advIntQ3').textContent = formatINR(s[2].interest234C);
        document.getElementById('advStatusQ3').innerHTML = s[2].status === 'Compliant'
          ? `<span style="color: var(--accent-emerald);">✅ Paid</span>`
          : `<span style="color: var(--accent-crimson);">⚠️ Shortfall</span>`;
      }
      if (s[3]) {
        document.getElementById('advReqQ4').textContent = formatINR(s[3].requiredCumulativeAmount);
        document.getElementById('advCumPaidQ4').textContent = formatINR(s[3].actualCumulativePaid);
        document.getElementById('advShortfallQ4').textContent = formatINR(s[3].shortfall);
        document.getElementById('advIntQ4').textContent = formatINR(s[3].interest234C);
        document.getElementById('advStatusQ4').innerHTML = s[3].status === 'Compliant'
          ? `<span style="color: var(--accent-emerald);">✅ Paid</span>`
          : `<span style="color: var(--accent-crimson);">⚠️ Shortfall</span>`;
      }
    }

    document.getElementById('totalInt234C').textContent = formatINR(advTaxResult.interest234C.amount);
    document.getElementById('totalInt234B').textContent = formatINR(advTaxResult.interest234B.amount);
    document.getElementById('totalInt234A').textContent = formatINR(advTaxResult.interest234A.amount);
  }

  renderMasterRates() {
    const container = document.getElementById('masterRatesContentContainer');
    if (!container) return;

    if (this.currentMasterTab === 'mtab-slabs') {
      container.innerHTML = `
        <div class="grid-2">
          <div>
            <h4 style="color: var(--accent-emerald); margin-bottom: 0.75rem;">New Tax Regime Slabs u/s 115BAC(1A) [FY 2025-26 & 2026-27]</h4>
            <table class="master-table">
              <thead><tr><th>Income Slab</th><th>Tax Rate</th></tr></thead>
              <tbody>
                ${MASTER_RATES.SLABS.NEW_REGIME.map(s => `<tr><td>${s.label}</td><td><strong>${(s.rate * 100).toFixed(0)}%</strong></td></tr>`).join('')}
              </tbody>
            </table>
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">*Section 87A rebate applies up to ₹7,00,000 taxable income (with marginal relief up to ₹7,27,777).</p>
          </div>

          <div>
            <h4 style="color: var(--accent-gold); margin-bottom: 0.75rem;">Old Tax Regime Slabs (Individual < 60 Yrs & HUF)</h4>
            <table class="master-table">
              <thead><tr><th>Income Slab</th><th>Tax Rate</th></tr></thead>
              <tbody>
                ${MASTER_RATES.SLABS.OLD_REGIME_GENERAL.map(s => `<tr><td>${s.label}</td><td><strong>${(s.rate * 100).toFixed(0)}%</strong></td></tr>`).join('')}
              </tbody>
            </table>
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.5rem;">*Senior Citizens (60-80 Yrs): Basic limit ₹3,00,000 | Super Senior (80+ Yrs): Basic limit ₹5,00,000.</p>
          </div>
        </div>
      `;
    } else if (this.currentMasterTab === 'mtab-surcharge') {
      container.innerHTML = `
        <div class="grid-2">
          <div>
            <h4 style="color: var(--accent-emerald); margin-bottom: 0.75rem;">New Regime Surcharge Tiers (Max 25%)</h4>
            <table class="master-table">
              <thead><tr><th>Taxable Income Threshold</th><th>Surcharge Rate</th></tr></thead>
              <tbody>
                ${MASTER_RATES.SURCHARGE_INDIVIDUAL.NEW_REGIME.map(s => `<tr><td>${s.label}</td><td><strong>${(s.rate * 100).toFixed(0)}%</strong></td></tr>`).join('')}
              </tbody>
            </table>
          </div>

          <div>
            <h4 style="color: var(--accent-gold); margin-bottom: 0.75rem;">Old Regime Surcharge Tiers (Max 37%)</h4>
            <table class="master-table">
              <thead><tr><th>Taxable Income Threshold</th><th>Surcharge Rate</th></tr></thead>
              <tbody>
                ${MASTER_RATES.SURCHARGE_INDIVIDUAL.OLD_REGIME.map(s => `<tr><td>${s.label}</td><td><strong>${(s.rate * 100).toFixed(0)}%</strong></td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    } else if (this.currentMasterTab === 'mtab-tds') {
      container.innerHTML = `
        <div class="matrix-table-wrapper">
          <table class="master-table">
            <thead>
              <tr>
                <th>Section</th>
                <th>Nature of Payment</th>
                <th>Threshold Limit</th>
                <th>TDS / TCS Rate</th>
                <th>Statutory Remarks</th>
              </tr>
            </thead>
            <tbody>
              ${MASTER_RATES.TDS_TCS_MASTER.map(t => `
                <tr>
                  <td><span class="section-code">Sec ${t.section}</span></td>
                  <td><strong>${t.nature}</strong></td>
                  <td>${t.threshold}</td>
                  <td style="font-weight: 700; color: var(--accent-primary);">${t.rate}</td>
                  <td style="font-size: 0.78rem; color: var(--text-secondary);">${t.remarks}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    } else if (this.currentMasterTab === 'mtab-depr') {
      container.innerHTML = `
        <div class="matrix-table-wrapper">
          <table class="master-table">
            <thead>
              <tr>
                <th>Asset Block</th>
                <th>Description / Nature of Asset</th>
                <th>Income Tax Depreciation Rate u/s 32</th>
              </tr>
            </thead>
            <tbody>
              ${MASTER_RATES.DEPRECIATION_BLOCKS.map(d => `
                <tr>
                  <td><span class="section-code">${d.block}</span></td>
                  <td>${d.asset}</td>
                  <td style="font-weight: 700; color: var(--accent-emerald);">${(d.rate * 100).toFixed(0)}%</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }
  }

  renderCertifiedStatement(comparison, advTaxResult, advisory, state) {
    const isNew = comparison.recommendedRegime === 'NEW';
    const active = isNew ? comparison.newRegime : comparison.oldRegime;
    const details = state.assesseeDetails || {};

    // Fill headers
    document.getElementById('stmtAy').textContent = state.assessmentYear || '2026-27';
    document.getElementById('stmtFy').textContent = (state.assessmentYear === '2027-28' ? '2026-27' : '2025-26');
    document.getElementById('stmtName').textContent = details.name || 'Assessee';
    document.getElementById('stmtPan').textContent = details.pan || 'ABCPS1234F';
    document.getElementById('stmtStatus').textContent = `${details.residentialStatus || 'Resident'} (${state.assesseeType || 'Individual'})`;
    document.getElementById('stmtRegime').textContent = isNew ? 'New Tax Regime u/s 115BAC(1A)' : 'Old Tax Regime';

    document.getElementById('stmtVerifyName').textContent = details.name || 'Assessee';
    document.getElementById('stmtVerifyPan').textContent = details.pan || 'ABCPS1234F';
    document.getElementById('stmtDate').textContent = new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    document.getElementById('stmtCaFirm').textContent = details.caName || 'R. K. Agrawal & Co.';
    document.getElementById('stmtCaMno').textContent = details.caMembership || '054321';
    document.getElementById('stmtCaFrn').textContent = details.firmRegNo || '001234N';
    document.getElementById('stmtUdin').textContent = details.udin || '26054321AAAAAA1122';

    // Statement Table Rows
    const tbody = document.getElementById('stmtTableBody');
    if (!tbody) return;

    const netTaxWithInterest = active.taxComputation.netTaxPayableOrRefundable + advTaxResult.totalStatutoryInterest;

    tbody.innerHTML = `
      <tr>
        <td><strong>Sch S</strong></td>
        <td>Income from Salaries (Sec 15 to 17)</td>
        <td class="amount">${formatINR(active.heads.salary.netSalaryIncome)}</td>
      </tr>
      <tr>
        <td><strong>Sch HP</strong></td>
        <td>Income / (Loss) from House Property (Sec 22 to 27)</td>
        <td class="amount">${formatINR(active.heads.houseProperty.allowableLossAgainstOtherHeads)}</td>
      </tr>
      <tr>
        <td><strong>Sch PGBP</strong></td>
        <td>Profits & Gains of Business or Profession (Sec 28 to 44)</td>
        <td class="amount">${formatINR(active.heads.pgbp.netPgbpIncome)}</td>
      </tr>
      <tr>
        <td><strong>Sch CG</strong></td>
        <td>Capital Gains (Sec 45 to 55A)</td>
        <td class="amount">${formatINR(active.heads.capitalGains.totalTaxableCapitalGains)}</td>
      </tr>
      <tr>
        <td><strong>Sch OS</strong></td>
        <td>Income from Other Sources (Sec 56 to 59)</td>
        <td class="amount">${formatINR(active.heads.otherSources.totalOtherSources)}</td>
      </tr>
      <tr class="total-row">
        <td><strong>GTI</strong></td>
        <td><strong>GROSS TOTAL INCOME (Total of all 5 Heads)</strong></td>
        <td class="amount"><strong>${formatINR(active.grossTotalIncome)}</strong></td>
      </tr>
      <tr>
        <td><strong>Sch VIA</strong></td>
        <td>Less: Deductions under Chapter VI-A (80C, 80D, 80CCD, etc.)</td>
        <td class="amount">- ${formatINR(active.totalDeductionsAllowed)}</td>
      </tr>
      <tr class="total-row">
        <td><strong>NTI</strong></td>
        <td><strong>TOTAL TAXABLE INCOME (Rounded off u/s 288A)</strong></td>
        <td class="amount"><strong>${formatINR(active.totalTaxableIncome)}</strong></td>
      </tr>
      <tr>
        <td><strong>TAX-1</strong></td>
        <td>Tax on Normal Income at Applicable Slabs</td>
        <td class="amount">${formatINR(active.taxComputation.taxOnNormalIncome)}</td>
      </tr>
      <tr>
        <td><strong>TAX-2</strong></td>
        <td>Tax on Special Rate Incomes (111A, 112A, 112, 115BB, 115BBH)</td>
        <td class="amount">${formatINR(active.taxComputation.taxOnSpecialIncome)}</td>
      </tr>
      <tr>
        <td><strong>SEC 87A</strong></td>
        <td>Less: Rebate under Section 87A (including Marginal Relief)</td>
        <td class="amount">- ${formatINR(active.taxComputation.rebate87A)}</td>
      </tr>
      <tr>
        <td><strong>SC</strong></td>
        <td>Add: Surcharge on Income Tax</td>
        <td class="amount">${formatINR(active.taxComputation.surcharge.netSurcharge)}</td>
      </tr>
      <tr>
        <td><strong>CESS</strong></td>
        <td>Add: Health & Education Cess @ 4%</td>
        <td class="amount">${formatINR(active.taxComputation.cess)}</td>
      </tr>
      <tr class="total-row">
        <td><strong>TTL</strong></td>
        <td><strong>TOTAL TAX LIABILITY</strong></td>
        <td class="amount"><strong>${formatINR(active.taxComputation.totalTaxLiability)}</strong></td>
      </tr>
      <tr>
        <td><strong>INT</strong></td>
        <td>Add: Penal Interest under Sections 234A, 234B & 234C</td>
        <td class="amount">${formatINR(advTaxResult.totalStatutoryInterest)}</td>
      </tr>
      <tr>
        <td><strong>PRE</strong></td>
        <td>Less: Prepaid Taxes (TDS + TCS + Advance Tax Paid)</td>
        <td class="amount">- ${formatINR(active.taxComputation.prepaidTaxes.totalPrepaidTaxes)}</td>
      </tr>
      <tr class="total-row" style="font-size: 11pt; background: #e6f4ea !important;">
        <td><strong>NET</strong></td>
        <td><strong>${netTaxWithInterest >= 0 ? 'NET TAX PAYABLE / (SELF-ASSESSMENT TAX U/S 140A)' : 'NET REFUND DUE TO ASSESSEE U/S 237'}</strong></td>
        <td class="amount" style="color: ${netTaxWithInterest >= 0 ? '#b91c1c' : '#047857'}; font-weight: bold;">
          <strong>${formatINR(Math.abs(netTaxWithInterest))}</strong>
        </td>
      </tr>
    `;

    // Render AI Advisory Cards
    this.renderAIAdvisoryMemorandum(advisory);
  }

  renderAIAdvisoryMemorandum(advisory) {
    const container = document.getElementById('aiAdvisoryContainer');
    if (!container) return;

    let html = '';

    // Observations
    advisory.observations.forEach(obs => {
      html += `
        <div class="memo-alert ${obs.type}">
          <div class="memo-alert-title">
            <span>${obs.title}</span>
            <span class="badge-tag">${obs.impact}</span>
          </div>
          <p class="memo-alert-body">${obs.detail}</p>
        </div>
      `;
    });

    // Tax Saving Tips
    if (advisory.taxSavingTips.length > 0) {
      html += `<h4 style="font-size: 0.92rem; font-weight: 700; color: var(--accent-primary); margin: 1.25rem 0 0.75rem 0;">💡 Tax Optimization & Structuring Opportunities</h4>`;
      advisory.taxSavingTips.forEach(tip => {
        html += `
          <div class="memo-alert info">
            <div class="memo-alert-title">
              <span><strong>[${tip.section}]</strong> ${tip.opportunity}</span>
              <span class="badge-tag" style="background: rgba(56, 189, 248, 0.2); color: var(--accent-primary);">${tip.potentialSaving}</span>
            </div>
            <p class="memo-alert-body">${tip.detail}</p>
          </div>
        `;
      });
    }

    // Compliance & Audit Warnings
    if (advisory.complianceWarnings.length > 0) {
      html += `<h4 style="font-size: 0.92rem; font-weight: 700; color: var(--accent-crimson); margin: 1.25rem 0 0.75rem 0;">⚠️ Statutory Compliance & Audit Alerts</h4>`;
      advisory.complianceWarnings.forEach(warn => {
        html += `
          <div class="memo-alert danger">
            <div class="memo-alert-title">
              <span><strong>${warn.category}</strong></span>
              <span class="badge-tag" style="background: rgba(244, 63, 94, 0.2); color: var(--accent-crimson);">${warn.severity.toUpperCase()} RISK</span>
            </div>
            <p class="memo-alert-body">${warn.detail}</p>
          </div>
        `;
      });
    }

    // Corporate / PGBP Notes
    if (advisory.corporatePgbpAdvisories.length > 0) {
      html += `<h4 style="font-size: 0.92rem; font-weight: 700; color: var(--accent-gold); margin: 1.25rem 0 0.75rem 0;">🏢 Business & Corporate Advisory Notes</h4>`;
      advisory.corporatePgbpAdvisories.forEach(corp => {
        html += `
          <div class="memo-alert warning">
            <div class="memo-alert-title"><span>${corp.title}</span></div>
            <p class="memo-alert-body">${corp.detail}</p>
          </div>
        `;
      });
    }

    container.innerHTML = html;
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.taxComputeApp = new AppController();
});
