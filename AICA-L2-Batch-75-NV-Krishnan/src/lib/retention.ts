import { EntityType, Service } from "../types";

export const SERVICES_CONFIG: Record<string, {
  name: string;
  basis: "from_date" | "contract_tenure";
  years: number | null;
  statute: string | null;
  entityDependent?: boolean;
}> = {
  "statutory-audit": {
    name: "Statutory Audit",
    basis: "from_date",
    years: 8,
    statute: "Companies Act 2013 s.128(5)"
  },
  "tax-audit": {
    name: "Tax Audit",
    basis: "from_date",
    years: 7,
    statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026"
  },
  "income-tax-services": {
    name: "Income Tax services",
    basis: "from_date",
    years: 7,
    statute: "Income-tax Act 2025, Section 62 read with Rule 46(9), Income-tax Rules 2026"
  },
  "gst-services": {
    name: "GST services",
    basis: "from_date",
    years: 6,
    statute: "CGST Act 2017 s.36"
  },
  "accounting-services": {
    name: "Accounting services",
    basis: "contract_tenure",
    years: null,
    statute: null
  },
  "finance-consulting-services": {
    name: "Finance-related consulting services",
    basis: "contract_tenure",
    years: null,
    statute: null
  },
  "internal-audit-services": {
    name: "Internal audit services",
    basis: "from_date",
    years: null,
    statute: "Companies Act 2013 s.138 (Mandatory company: 8 years) / Non-company: 7 years under Income-tax Act 2025, Section 62 read with Rule 46(9)",
    entityDependent: true
  }
};

/**
 * Calculates explicit Erasure Due Date
 * @param serviceId Service slug ID
 * @param entityType Client entity type ("company" | "non_company")
 * @param contractEndDateStr ISO date string (YYYY-MM-DD)
 */
export function calculateErasureDueDate(
  serviceId: string,
  entityType: EntityType,
  contractEndDateStr: string
): { erasureDueDate: string; basis: "from_date" | "contract_tenure"; yearsCalculated: number; statute: string | null } {
  const config = SERVICES_CONFIG[serviceId] || {
    name: serviceId,
    basis: "contract_tenure",
    statute: "Standard engagement contract terms"
  };

  const endDate = new Date(contractEndDateStr);
  if (isNaN(endDate.getTime())) {
    return {
      erasureDueDate: contractEndDateStr,
      basis: config.basis,
      yearsCalculated: 0,
      statute: config.statute ?? null
    };
  }

  if (config.basis === "contract_tenure") {
    // contractEndDate + 60 days
    const result = new Date(endDate);
    result.setDate(result.getDate() + 60);
    return {
      erasureDueDate: result.toISOString().split("T")[0],
      basis: "contract_tenure",
      yearsCalculated: 0,
      statute: config.statute ?? null
    };
  } else {
    // from_date basis
    let years = config.years || 7;
    if (serviceId === "internal-audit-services") {
      years = entityType === "company" ? 8 : 7;
    }

    const result = new Date(endDate);
    result.setFullYear(result.getFullYear() + years);
    result.setDate(result.getDate() + 60);

    return {
      erasureDueDate: result.toISOString().split("T")[0],
      basis: "from_date",
      yearsCalculated: years,
      statute: config.statute ?? null
    };
  }
}
