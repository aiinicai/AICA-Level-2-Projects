import { daysBetween } from './formatters';

export interface CashFlow {
  date: string; // YYYY-MM-DD
  amount: number; // Negative for outflows (purchases), positive for inflows (terminal resale value)
}

export interface XirrResult {
  xirr: number | null; // e.g. 0.1425 for 14.25%
  status: 'SUCCESS' | 'ZERO_DAYS' | 'NO_SIGN_CHANGE' | 'MISSING_DATA' | 'DID_NOT_CONVERGE';
  reason: string;
  daysHeld?: number;
  absoluteReturnPct?: number;
}

/**
 * Robust numerical XIRR solver matching Excel XIRR specifications.
 * Uses exact calendar-day differences divided by 365.
 * Uses Newton-Raphson with bounded step size, with fallback to Bisection / Brent.
 */
export function calculateXIRR(rawFlows: CashFlow[]): XirrResult {
  if (!rawFlows || rawFlows.length === 0) {
    return { xirr: null, status: 'MISSING_DATA', reason: 'No cash flows provided' };
  }

  // Aggregate cash flows occurring on the same calendar day
  const aggregatedMap = new Map<string, number>();
  for (const flow of rawFlows) {
    if (!flow.date || isNaN(flow.amount)) continue;
    const current = aggregatedMap.get(flow.date) || 0;
    aggregatedMap.set(flow.date, current + flow.amount);
  }

  // Filter out exact net 0 days and sort chronologically
  const sortedFlows: CashFlow[] = Array.from(aggregatedMap.entries())
    .map(([date, amount]) => ({ date, amount }))
    .filter(f => Math.abs(f.amount) > 1e-9)
    .sort((a, b) => a.date.localeCompare(b.date));

  if (sortedFlows.length < 2) {
    return {
      xirr: null,
      status: 'ZERO_DAYS',
      reason: 'At least two distinct cash flow dates are required'
    };
  }

  const startDate = sortedFlows[0].date;
  const endDate = sortedFlows[sortedFlows.length - 1].date;
  const totalDays = daysBetween(startDate, endDate);

  if (totalDays <= 0) {
    return {
      xirr: null,
      status: 'ZERO_DAYS',
      reason: 'Holding period is 0 days (transactions on same date)'
    };
  }

  let hasPositive = false;
  let hasNegative = false;
  let totalInflows = 0;
  let totalOutflows = 0;

  for (const f of sortedFlows) {
    if (f.amount > 0) {
      hasPositive = true;
      totalInflows += f.amount;
    } else if (f.amount < 0) {
      hasNegative = true;
      totalOutflows += Math.abs(f.amount);
    }
  }

  if (!hasPositive || !hasNegative) {
    return {
      xirr: null,
      status: 'NO_SIGN_CHANGE',
      reason: 'Requires both invested outflow and positive terminal value'
    };
  }

  const absoluteReturnPct = totalOutflows > 0 ? ((totalInflows - totalOutflows) / totalOutflows) * 100 : 0;

  // For a single purchase lot with single terminal value:
  if (sortedFlows.length === 2 && sortedFlows[0].amount < 0 && sortedFlows[1].amount > 0) {
    const cost = Math.abs(sortedFlows[0].amount);
    const terminal = sortedFlows[1].amount;
    const days = totalDays;
    // Closed-form XIRR: (terminal / cost) ^ (365 / days) - 1
    const exactXirr = Math.pow(terminal / cost, 365.0 / days) - 1.0;
    if (!isNaN(exactXirr) && isFinite(exactXirr)) {
      return {
        xirr: exactXirr,
        status: 'SUCCESS',
        reason: 'Single-lot exact formula verified',
        daysHeld: days,
        absoluteReturnPct
      };
    }
  }

  // Days from inception date
  const dayFractions = sortedFlows.map(f => daysBetween(startDate, f.date) / 365.0);
  const amounts = sortedFlows.map(f => f.amount);

  // XNPV function: sum(C_i / (1 + r)^t_i)
  function xnpv(r: number): number {
    let sum = 0;
    for (let i = 0; i < amounts.length; i++) {
      const t = dayFractions[i];
      const denom = Math.pow(1.0 + r, t);
      if (!isFinite(denom) || denom === 0) return NaN;
      sum += amounts[i] / denom;
    }
    return sum;
  }

  // Derivative XNPV'(r): sum(-t_i * C_i / (1 + r)^(t_i + 1))
  function dxnpv(r: number): number {
    let sum = 0;
    for (let i = 0; i < amounts.length; i++) {
      const t = dayFractions[i];
      const denom = Math.pow(1.0 + r, t + 1.0);
      if (!isFinite(denom) || denom === 0) return NaN;
      sum += (-t * amounts[i]) / denom;
    }
    return sum;
  }

  // Heuristic initial guess
  let guess = 0.1;
  if (totalOutflows > 0 && totalDays > 0) {
    const rawRatio = totalInflows / totalOutflows;
    const est = Math.pow(rawRatio, 365.0 / totalDays) - 1.0;
    if (est > -0.9 && est < 10.0) {
      guess = est;
    }
  }

  // 1. Newton-Raphson iteration
  let r = guess;
  const maxNewtonIter = 60;
  let newtonConverged = false;

  for (let iter = 0; iter < maxNewtonIter; iter++) {
    const val = xnpv(r);
    if (isNaN(val)) break;
    if (Math.abs(val) < 1e-7) {
      newtonConverged = true;
      break;
    }

    const deriv = dxnpv(r);
    if (isNaN(deriv) || Math.abs(deriv) < 1e-12) {
      break; // Derivative too flat
    }

    const step = val / deriv;
    let nextR = r - step;

    // Prevent jumping below -1 (boundary where (1+r) <= 0)
    if (nextR <= -0.999) {
      nextR = (r - 0.999) / 2.0;
    } else if (nextR > 50.0) {
      nextR = 25.0;
    }

    if (Math.abs(nextR - r) < 1e-8) {
      r = nextR;
      newtonConverged = true;
      break;
    }

    r = nextR;
  }

  if (newtonConverged && r > -0.999 && isFinite(r)) {
    return {
      xirr: r,
      status: 'SUCCESS',
      reason: 'Newton-Raphson converged',
      daysHeld: totalDays,
      absoluteReturnPct
    };
  }

  // 2. Bisection Fallback
  // Bracket search over interval [-0.999, 10.0]
  let low = -0.999;
  let high = 10.0;
  let fLow = xnpv(low);
  let fHigh = xnpv(high);

  if (isNaN(fLow) || isNaN(fHigh) || fLow * fHigh > 0) {
    // Try expanding search bracket up to 100.0
    high = 100.0;
    fHigh = xnpv(high);
  }

  if (!isNaN(fLow) && !isNaN(fHigh) && fLow * fHigh <= 0) {
    for (let iter = 0; iter < 100; iter++) {
      const mid = (low + high) / 2.0;
      const fMid = xnpv(mid);

      if (Math.abs(fMid) < 1e-6 || (high - low) < 1e-7) {
        return {
          xirr: mid,
          status: 'SUCCESS',
          reason: 'Bisection converged',
          daysHeld: totalDays,
          absoluteReturnPct
        };
      }

      if (fLow * fMid < 0) {
        high = mid;
        fHigh = fMid;
      } else {
        low = mid;
        fLow = fMid;
      }
    }
  }

  return {
    xirr: null,
    status: 'DID_NOT_CONVERGE',
    reason: 'Numerical solver failed to converge (XNPV root not found)',
    daysHeld: totalDays,
    absoluteReturnPct
  };
}

/**
 * Closed-form single lot XIRR: (Terminal Value / Invested Cost)^(365 / daysHeld) - 1
 */
export function calculateSingleLotXIRR(cost: number, terminalValue: number, daysHeld: number): number | null {
  if (daysHeld <= 0 || cost <= 0 || terminalValue < 0) return null;
  return Math.pow(terminalValue / cost, 365.0 / daysHeld) - 1.0;
}

