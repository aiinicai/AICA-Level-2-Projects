/**
 * Indian INR currency, Lak/Crore formatting, and IST market session helpers.
 */

const inrCurrencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const inrWholeFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const indianNumberFormatter = new Intl.NumberFormat('en-IN', {
  maximumFractionDigits: 2,
});

export function formatINR(value: number, decimals = 2): string {
  if (!Number.isFinite(value)) return '₹0.00';
  if (decimals === 0) return inrWholeFormatter.format(value);
  return inrCurrencyFormatter.format(value);
}

export function formatINRCompact(value: number): string {
  if (!Number.isFinite(value)) return '₹0';
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1e7) {
    return `${sign}₹${(abs / 1e7).toFixed(2)} Cr`;
  }
  if (abs >= 1e5) {
    return `${sign}₹${(abs / 1e5).toFixed(2)} L`;
  }
  return `${sign}${inrWholeFormatter.format(abs)}`;
}

export function formatCr(crores: number): string {
  if (!Number.isFinite(crores)) return '₹0 Cr';
  return `₹${indianNumberFormatter.format(Math.round(crores))} Cr`;
}

export function formatNum(value: number, decimals = 2): string {
  if (!Number.isFinite(value)) return '0';
  return value.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPct(value: number, withSign = true): string {
  if (!Number.isFinite(value)) return '0.00%';
  const sign = withSign && value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

export interface NseHoliday {
  date: string;
  occasion: string;
  day: string;
}

export const NSE_HOLIDAYS_2026: NseHoliday[] = [
  { date: '2026-01-26', occasion: 'Republic Day', day: 'Monday' },
  { date: '2026-03-03', occasion: 'Holi', day: 'Tuesday' },
  { date: '2026-03-26', occasion: 'Shri Ram Navami', day: 'Thursday' },
  { date: '2026-03-31', occasion: 'Mahavir Jayanti', day: 'Tuesday' },
  { date: '2026-04-03', occasion: 'Good Friday', day: 'Friday' },
  { date: '2026-04-14', occasion: 'Dr. Baba Saheb Ambedkar Jayanti', day: 'Tuesday' },
  { date: '2026-05-01', occasion: 'Maharashtra Day', day: 'Friday' },
  { date: '2026-05-28', occasion: 'Bakri Id', day: 'Thursday' },
  { date: '2026-06-26', occasion: 'Muharram', day: 'Friday' },
  { date: '2026-09-14', occasion: 'Ganesh Chaturthi', day: 'Monday' },
  { date: '2026-10-02', occasion: 'Mahatma Gandhi Jayanti', day: 'Friday' },
  { date: '2026-10-20', occasion: 'Dussehra', day: 'Tuesday' },
  { date: '2026-11-08', occasion: 'Diwali (Laxmi Pujan — Muhurat Session)', day: 'Sunday' },
  { date: '2026-11-10', occasion: 'Diwali-Balipratipada', day: 'Tuesday' },
  { date: '2026-11-24', occasion: 'Prakash Gurpurb Sri Guru Nanak Dev', day: 'Tuesday' },
  { date: '2026-12-25', occasion: 'Christmas', day: 'Friday' },
];

export interface IstMarketStatus {
  istTimeStr: string;
  istDateStr: string;
  sessionLabel: string;
  isOpen: boolean;
  nextSessionNote: string;
}

export function getIndianMarketStatus(now = new Date()): IstMarketStatus {
  const istFormatter = new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const dateFormatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const dayFormatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Kolkata',
    weekday: 'short',
  });

  const istTimeStr = istFormatter.format(now);
  const istDateStr = dateFormatter.format(now);
  const weekday = dayFormatter.format(now);
  const [hStr, mStr] = istTimeStr.split(':');
  const mins = Number(hStr) * 60 + Number(mStr);

  const holiday = NSE_HOLIDAYS_2026.find((h) => h.date === istDateStr);
  if (holiday) {
    return {
      istTimeStr,
      istDateStr,
      sessionLabel: `NSE Holiday (${holiday.occasion})`,
      isOpen: false,
      nextSessionNote: 'Next regular session 09:15 IST',
    };
  }

  if (weekday === 'Sat' || weekday === 'Sun') {
    return {
      istTimeStr,
      istDateStr,
      sessionLabel: 'Weekend Closed',
      isOpen: false,
      nextSessionNote: 'Opens Monday 09:15 IST',
    };
  }

  if (mins >= 540 && mins < 555) {
    return {
      istTimeStr,
      istDateStr,
      sessionLabel: 'Pre-Open (09:00–09:15 IST)',
      isOpen: true,
      nextSessionNote: 'Continuous trading at 09:15 IST',
    };
  }
  if (mins >= 555 && mins <= 930) {
    return {
      istTimeStr,
      istDateStr,
      sessionLabel: 'Normal Market Open',
      isOpen: true,
      nextSessionNote: 'Closes at 15:30 IST',
    };
  }
  if (mins >= 940 && mins <= 960) {
    return {
      istTimeStr,
      istDateStr,
      sessionLabel: 'Post-Close (15:40–16:00 IST)',
      isOpen: false,
      nextSessionNote: 'EOD Bhavcopy settlement',
    };
  }
  return {
    istTimeStr,
    istDateStr,
    sessionLabel: 'After Hours Closed',
    isOpen: false,
    nextSessionNote: 'Pre-Open at 09:00 IST',
  };
}
