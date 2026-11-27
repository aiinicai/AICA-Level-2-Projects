import { CategoryBudget, ExpenseCategory, Transaction } from '../types/finance';

export interface SpendingInsight {
  id: string;
  type: 'tip' | 'warning' | 'achievement';
  title: string;
  description: string;
  savingsPotentialAED?: number;
  category?: ExpenseCategory;
}

export function generateSpendingInsights(
  transactions: Transaction[],
  budgets: CategoryBudget[],
  monthlyIncome: number
): SpendingInsight[] {
  const insights: SpendingInsight[] = [];
  const currentMonthExpenses = transactions.filter(t => t.type === 'expense');

  // 1. Calculate spending per category
  const categoryTotals: Record<string, number> = {};
  let totalExpense = 0;

  for (const tx of currentMonthExpenses) {
    categoryTotals[tx.category] = (categoryTotals[tx.category] || 0) + tx.amount;
    totalExpense += tx.amount;
  }

  // Savings rate analysis
  if (monthlyIncome > 0) {
    const savingsRate = ((monthlyIncome - totalExpense) / monthlyIncome) * 100;
    if (savingsRate >= 30) {
      insights.push({
        id: 'savings-good',
        type: 'achievement',
        title: 'Strong UAE Savings Rate',
        description: `You are saving ${savingsRate.toFixed(0)}% of your income this month (AED ${(monthlyIncome - totalExpense).toLocaleString('en-AE', { minimumFractionDigits: 0 })}). You are outperforming the typical 15% UAE benchmark.`
      });
    } else if (savingsRate < 10 && savingsRate >= 0) {
      insights.push({
        id: 'savings-low',
        type: 'warning',
        title: 'Low Savings Margin Alert',
        description: `Current savings rate is only ${savingsRate.toFixed(1)}%. Review dining and discretionary shopping to maintain a recommended 20% safety buffer.`
      });
    }
  }

  // Food & Dining Leak
  const foodSpend = categoryTotals['Food'] || 0;
  if (foodSpend > 1500) {
    insights.push({
      id: 'food-leak',
      type: 'tip',
      title: 'Food & Dining Optimization',
      description: `Dining & takeaway reached AED ${foodSpend.toLocaleString()} this month. Preparing meal prep for 2 office lunches per week can save approximately AED 480/month.`,
      savingsPotentialAED: 480,
      category: 'Food'
    });
  }

  // Petrol & Fuel Check
  const petrolSpend = categoryTotals['Petrol'] || 0;
  if (petrolSpend > 600) {
    insights.push({
      id: 'petrol-tip',
      type: 'tip',
      title: 'Fuel Cashback Tip',
      description: `Your fuel spend is AED ${petrolSpend.toLocaleString()}. Using a dedicated fuel credit card (like ENOC Yes Rewards or Citi Cashback) can yield 5-10% cashback (approx AED ${Math.round(petrolSpend * 0.08)} saved).`,
      savingsPotentialAED: Math.round(petrolSpend * 0.08),
      category: 'Petrol'
    });
  }

  // Check budget overruns (>80%)
  for (const b of budgets) {
    const spent = categoryTotals[b.category] || 0;
    const ratio = b.monthlyLimit > 0 ? spent / b.monthlyLimit : 0;
    if (ratio >= 1.0) {
      insights.push({
        id: `overbudget-${b.category}`,
        type: 'warning',
        title: `${b.category} Budget Exceeded`,
        description: `You spent AED ${spent.toLocaleString()} against your AED ${b.monthlyLimit.toLocaleString()} monthly target (over by AED ${(spent - b.monthlyLimit).toLocaleString()}).`,
        category: b.category
      });
    } else if (ratio >= 0.8) {
      insights.push({
        id: `caution-${b.category}`,
        type: 'warning',
        title: `${b.category} at ${(ratio * 100).toFixed(0)}% of Limit`,
        description: `Approaching monthly cap with AED ${(b.monthlyLimit - spent).toLocaleString()} remaining. Pace spending for the rest of the cycle.`,
        category: b.category
      });
    }
  }

  // Red flag transaction alerts
  const unverifiedRedFlags = transactions.filter(t => t.isRedFlag && !t.isVerifiedByUser);
  if (unverifiedRedFlags.length > 0) {
    insights.push({
      id: 'unverified-red-flags',
      type: 'warning',
      title: `${unverifiedRedFlags.length} Suspicious / International Transactions`,
      description: `You have foreign currency or high-value transactions pending your safety review. Check the Flagged tab to confirm or report them.`
    });
  }

  // Fallback tip if list is short
  if (insights.length === 0) {
    insights.push({
      id: 'general-tip',
      type: 'tip',
      title: 'Smart UAE Budgeting Tip',
      description: 'Keep track of Salik toll recharges and DEWA summer air-conditioning slabs to avoid unexpected monthly bill surges.',
      savingsPotentialAED: 200
    });
  }

  return insights;
}
