export const ORDINARY_COURSE = [
  "Sale of goods",
  "Purchase of goods",
  "Availing of services",
  "Rendering of services",
];
export const NATURES = [
  ...ORDINARY_COURSE,
  "Leasing of property",
  "Sale of property",
  "Purchase of property",
  "Office or place of profit",
];
export const MARKET_TOLERANCE = 0.1;
export const RULE15_PCT = 0.1;
export const RULE15_OFFICE_MONTHLY = 250000;
export const CRORE = 10000000;
export const RULE15_SOURCE =
  "Rule 15(3)(a)(i), (iii), (iv) read with Sec 188(1)(a), (c), (d); preceding year's audited accounts; individually or together with earlier transactions in the year";
export const RULE15_PROPERTY_SOURCE = "Rule 15(3)(a)(ii) read with Sec 188(1)(b)";
export const RULE15_OFFICE_SOURCE = "Rule 15(3)(b) read with Sec 188(1)(f)";
export const SEBI_SOURCE =
  "Reg 23(1) and Schedule XII, SEBI LODR (Fifth Amendment) Regulations, 2025, effective 19 December 2025";
export const VERIFICATION_STATUS = "Verified by the author, 20 Nov 2026";
export function sebiThreshold(t: number): number {
  if (t <= 20000 * CRORE) return t * 0.1;
  if (t <= 40000 * CRORE) return 2000 * CRORE + 0.05 * (t - 20000 * CRORE);
  return Math.min(3000 * CRORE + 0.025 * (t - 40000 * CRORE), 5000 * CRORE);
}
export const CHECKS: Record<string, { name: string; meaning: string }> = {
  C2: {
    name: "Audit committee approval",
    meaning: "Every RPT voucher needs a prior, valid audit committee approval.",
  },
  C3: {
    name: "Approved limit exceeded",
    meaning: "Transactions within an approval period must not exceed its approved limit.",
  },
  C4: {
    name: "Market price deviation",
    meaning:
      "Weighted average related-party prices are screened against unrelated-party prices at a 10% tolerance.",
  },
  C5: {
    name: "Board approval",
    meaning:
      "Transactions outside ordinary course or flagged by the market screen need Board approval.",
  },
  C6: {
    name: "Shareholder approval",
    meaning: "Section 188 groups crossing the Rule 15 limits need prior shareholder approval.",
  },
  C7: {
    name: "Interested director participation",
    meaning: "An interested director must stay out of the Board decision.",
  },
  L2: {
    name: "Material transaction",
    meaning:
      "Listed-company RPTs exceeding the party-level SEBI threshold need prior shareholder approval.",
  },
};
