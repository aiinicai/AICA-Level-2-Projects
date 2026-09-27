import {
  Billing,
  BudgetRecord,
  BudgetVarianceSummary,
  HospitalDepartment,
  Service,
} from '../types';
import { mapRevenueCentreToDepartment, extractUniqueDepartments } from '../utils/departmentMapping';

export interface BudgetExecutiveSummary {
  month: string;
  availableMonths: string[];
  totalRevenueBudget: number;
  totalRevenueActual: number;
  totalRevenueVariance: number;
  totalRevenueVariancePercent: number;
  totalExpenseBudget: number;
  totalExpenseActual: number | null;
  totalExpenseVariance: number | null;
  totalExpenseVariancePercent: number | null;
  hasExpenseActuals: boolean;
  significantVariancesCount: number;
  ytdRevenueBudget: number;
  ytdRevenueActual: number;
  ytdRevenueVariance: number;
  ytdRevenueVariancePercent: number;
  departmentSummaries: BudgetVarianceSummary[];
}

export interface ActualExpenseRecord {
  Month: string; // 'YYYY-MM'
  Department: string;
  Expense_Amount: number;
}

export function executeBudgetEngine(
  budgets: BudgetRecord[],
  services: Service[],
  billings: Billing[],
  activeMonth?: string,
  actualExpenses: ActualExpenseRecord[] = []
): BudgetExecutiveSummary {
  // Collect all months present in budget records and billing records
  const monthSet = new Set<string>();
  budgets.forEach((b) => {
    if (b.Month) monthSet.add(b.Month);
  });
  billings.forEach((b) => {
    const m = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
    if (m && m.length === 7) monthSet.add(m);
  });

  const availableMonths = Array.from(monthSet).sort().reverse();
  const selectedMonth =
    activeMonth && monthSet.has(activeMonth)
      ? activeMonth
      : availableMonths[0] || '2026-09';

  // Build service lookup map
  const serviceMap = new Map<string, Service>();
  services.forEach((s) => serviceMap.set(s.Service_ID, s));

  // Dynamic department discovery
  const knownDepartments = extractUniqueDepartments(undefined, budgets);

  // Aggregate actual billing by Department for selected month
  const actualRevenueByDept = new Map<string, number>();
  // Also track all-month actual billing for YTD calculation
  const allMonthsRevenueByDept = new Map<string, Map<string, number>>();

  billings.forEach((b) => {
    const bMonth = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
    if (!bMonth) return;

    const svc = serviceMap.get(b.Service_ID);
    const revCentre = svc?.Revenue_Centre || 'General';
    const dept = mapRevenueCentreToDepartment(revCentre, knownDepartments);

    // Track monthly
    if (bMonth === selectedMonth) {
      const cur = actualRevenueByDept.get(dept) || 0;
      actualRevenueByDept.set(dept, cur + (Number(b.Billed_Amount) || 0));
    }

    // Track YTD by month and dept
    if (!allMonthsRevenueByDept.has(bMonth)) {
      allMonthsRevenueByDept.set(bMonth, new Map<string, number>());
    }
    const deptMapForMonth = allMonthsRevenueByDept.get(bMonth)!;
    deptMapForMonth.set(dept, (deptMapForMonth.get(dept) || 0) + (Number(b.Billed_Amount) || 0));
  });

  // Track actual expenses if provided
  const hasExpenseActuals = actualExpenses.length > 0;
  const actualExpenseByDept = new Map<string, number>();
  if (hasExpenseActuals) {
    actualExpenses.forEach((exp) => {
      if (exp.Month === selectedMonth) {
        const cur = actualExpenseByDept.get(exp.Department) || 0;
        actualExpenseByDept.set(exp.Department, cur + (Number(exp.Expense_Amount) || 0));
      }
    });
  }

  // Filter budgets for the active month
  const monthBudgets = budgets.filter((b) => b.Month === selectedMonth);

  // Determine actual YTD months that exist in the dataset up to selectedMonth
  const selectedYear = selectedMonth.slice(0, 4);
  const ytdHistoricalMonths = availableMonths.filter(
    (m) => m <= selectedMonth && m.startsWith(selectedYear)
  );

  const departmentSummaries: BudgetVarianceSummary[] = monthBudgets.map((bm) => {
    const revActual = Number((actualRevenueByDept.get(bm.Department) || 0).toFixed(2));
    const revVariance = Number((revActual - bm.Revenue_Budget).toFixed(2));
    const revVariancePct =
      bm.Revenue_Budget > 0 ? Number(((revVariance / bm.Revenue_Budget) * 100).toFixed(1)) : 0;

    // Actual expense: only compute if real expense data exists; NEVER estimate
    let expActual: number | null = null;
    let expVariance: number | null = null;
    let expVariancePct: number | null = null;

    if (hasExpenseActuals && actualExpenseByDept.has(bm.Department)) {
      expActual = Number((actualExpenseByDept.get(bm.Department) || 0).toFixed(2));
      expVariance = Number((expActual - bm.Expense_Budget).toFixed(2));
      expVariancePct =
        bm.Expense_Budget > 0 ? Number(((expVariance / bm.Expense_Budget) * 100).toFixed(1)) : 0;
    }

    const isSignificant =
      Math.abs(revVariancePct) >= 10.0 ||
      (expVariancePct !== null && Math.abs(expVariancePct) >= 10.0);

    // Deterministic YTD calculation based strictly on actual periods present in uploaded data
    const ytdBudgetSum = budgets
      .filter((b) => b.Department === bm.Department && ytdHistoricalMonths.includes(b.Month))
      .reduce((s, b) => s + b.Revenue_Budget, 0);

    let ytdActualSum = 0;
    ytdHistoricalMonths.forEach((m) => {
      const monthMap = allMonthsRevenueByDept.get(m);
      if (monthMap) {
        ytdActualSum += monthMap.get(bm.Department) || 0;
      }
    });

    const ytdBudget = ytdBudgetSum > 0 ? ytdBudgetSum : bm.Revenue_Budget;
    const ytdActual = Number((ytdActualSum > 0 ? ytdActualSum : revActual).toFixed(2));
    const ytdVariance = Number((ytdActual - ytdBudget).toFixed(2));

    return {
      month: selectedMonth,
      department: bm.Department,
      revenueBudget: bm.Revenue_Budget,
      revenueActual: revActual,
      revenueVariance: revVariance,
      revenueVariancePercent: revVariancePct,
      expenseBudget: bm.Expense_Budget,
      expenseActual: expActual,
      expenseVariance: expVariance,
      expenseVariancePercent: expVariancePct,
      isSignificant,
      ytdRevenueBudget: ytdBudget,
      ytdRevenueActual: ytdActual,
      ytdRevenueVariance: ytdVariance,
    };
  });

  const totalRevBudget = departmentSummaries.reduce((s, d) => s + d.revenueBudget, 0);
  const totalRevActual = departmentSummaries.reduce((s, d) => s + d.revenueActual, 0);
  const totalRevVariance = Number((totalRevActual - totalRevBudget).toFixed(2));
  const totalRevVariancePct =
    totalRevBudget > 0 ? Number(((totalRevVariance / totalRevBudget) * 100).toFixed(1)) : 0;

  const totalExpBudget = departmentSummaries.reduce((s, d) => s + d.expenseBudget, 0);
  const totalExpActual = hasExpenseActuals
    ? departmentSummaries.reduce((s, d) => s + (d.expenseActual || 0), 0)
    : null;
  const totalExpVariance = totalExpActual !== null ? Number((totalExpActual - totalExpBudget).toFixed(2)) : null;
  const totalExpVariancePct =
    totalExpActual !== null && totalExpBudget > 0
      ? Number(((totalExpVariance! / totalExpBudget) * 100).toFixed(1))
      : null;

  const sigCount = departmentSummaries.filter((d) => d.isSignificant).length;

  const ytdRevBudget = departmentSummaries.reduce((s, d) => s + d.ytdRevenueBudget, 0);
  const ytdRevActual = departmentSummaries.reduce((s, d) => s + d.ytdRevenueActual, 0);
  const ytdRevVariance = Number((ytdRevActual - ytdRevBudget).toFixed(2));
  const ytdRevVariancePct =
    ytdRevBudget > 0 ? Number(((ytdRevVariance / ytdRevBudget) * 100).toFixed(1)) : 0;

  return {
    month: selectedMonth,
    availableMonths,
    totalRevenueBudget: totalRevBudget,
    totalRevenueActual: totalRevActual,
    totalRevenueVariance: totalRevVariance,
    totalRevenueVariancePercent: totalRevVariancePct,
    totalExpenseBudget: totalExpBudget,
    totalExpenseActual: totalExpActual,
    totalExpenseVariance: totalExpVariance,
    totalExpenseVariancePercent: totalExpVariancePct,
    hasExpenseActuals,
    significantVariancesCount: sigCount,
    ytdRevenueBudget: ytdRevBudget,
    ytdRevenueActual: ytdRevActual,
    ytdRevenueVariance: ytdRevVariance,
    ytdRevenueVariancePercent: ytdRevVariancePct,
    departmentSummaries,
  };
}
