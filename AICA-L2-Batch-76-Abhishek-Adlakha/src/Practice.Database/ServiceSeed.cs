using Practice.Database.Entities;

namespace Practice.Database;

public static class ServiceSeed
{
    public static readonly DateTimeOffset SeedTimestamp = new(2026, 8, 20, 0, 0, 0, TimeSpan.Zero);

    public static readonly ServiceCategory[] Categories =
    [
        Category("40000000-0000-0000-0000-000000000001", "ACCOUNTING", "Accounting", 10),
        Category("40000000-0000-0000-0000-000000000002", "INCOME_TAX", "Income Tax", 20),
        Category("40000000-0000-0000-0000-000000000003", "GST", "GST", 30),
        Category("40000000-0000-0000-0000-000000000004", "ASSURANCE", "Assurance and Advisory", 40),
        Category("40000000-0000-0000-0000-000000000005", "CORPORATE", "Corporate and Regulatory", 50)
    ];

    public static readonly ServiceDefinition[] Services =
    [
        Service("41000000-0000-0000-0000-000000000001", "ACCOUNTS", "Accounts", 1, true),
        Service("41000000-0000-0000-0000-000000000002", "ITR", "Income Tax Return", 2, true),
        Service("41000000-0000-0000-0000-000000000003", "SFT", "Statement of Financial Transactions", 2, true),
        Service("41000000-0000-0000-0000-000000000004", "TAX_AUDIT", "Tax Audit", 2, true),
        Service("41000000-0000-0000-0000-000000000005", "TDS", "TDS Compliance", 2, true),
        Service("41000000-0000-0000-0000-000000000006", "TDS_RECONCILIATION", "TDS Reconciliation", 2, true),
        Service("41000000-0000-0000-0000-000000000007", "GST", "GST Returns", 3, true, true),
        Service("41000000-0000-0000-0000-000000000008", "GST_REFUND", "GST Refund", 3, false, true),
        Service("41000000-0000-0000-0000-000000000009", "GSTR9", "GSTR-9 Annual Return", 3, true, true),
        Service("41000000-0000-0000-0000-000000000010", "RODTEP", "RoDTEP", 5, true),
        Service("41000000-0000-0000-0000-000000000011", "FLA_RETURN", "FLA Return", 5, true),
        Service("41000000-0000-0000-0000-000000000012", "CFO_INTERNAL_AUDIT", "CFO / Internal Audit", 4, false),
        Service("41000000-0000-0000-0000-000000000013", "LUT", "Letter of Undertaking", 3, true, true),
        Service("41000000-0000-0000-0000-000000000014", "MSME", "MSME Compliance", 5, true),
        Service("41000000-0000-0000-0000-000000000015", "IEC", "Import Export Code", 5, false),
        Service("41000000-0000-0000-0000-000000000016", "COMPANY_TAX", "Company Tax", 2, true),
        Service("41000000-0000-0000-0000-000000000017", "PROFESSIONAL_TAX", "Professional Tax", 5, true),
        Service("41000000-0000-0000-0000-000000000018", "AUDIT", "Audit", 4, true),
        Service("41000000-0000-0000-0000-000000000019", "ROC_RETURN", "ROC Return", 5, true),
        Service("41000000-0000-0000-0000-000000000020", "ROC_REGISTER", "ROC Register", 5, false),
        Service("41000000-0000-0000-0000-000000000021", "TRANSFER_PRICING", "Transfer Pricing", 2, true)
    ];

    private static ServiceCategory Category(string id, string code, string name, int order) => new()
    {
        Id = Guid.Parse(id), Code = code, Name = name, NormalizedName = name.ToUpperInvariant(), DisplayOrder = order, IsActive = true
    };

    private static ServiceDefinition Service(string id, string code, string name, int category, bool recurrence, bool gstin = false) => new()
    {
        Id = Guid.Parse(id), CategoryId = Categories[category - 1].Id, Code = code, Name = name,
        NormalizedName = name.ToUpperInvariant(), DefaultBillable = true, SupportsRecurrence = recurrence,
        SupportsGstinScope = gstin, IsActive = true, CreatedAtUtc = SeedTimestamp, UpdatedAtUtc = SeedTimestamp
    };
}
