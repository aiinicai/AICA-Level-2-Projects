namespace Practice.Database.Entities;

public sealed class BillingEntity
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string LegalName { get; set; }
    public string? TradeName { get; set; }
    public string? Pan { get; set; }
    public string? Gstin { get; set; }
    public string? Address { get; set; }
    public string? Email { get; set; }
    public string? Phone { get; set; }
    public required string CurrencyCode { get; set; } = "INR";
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public long RowVersion { get; set; } = 1;
    public ICollection<BillingTerm> Terms { get; } = new List<BillingTerm>();
}

public sealed class BillingTerm
{
    public Guid Id { get; set; }
    public Guid ClientServiceId { get; set; }
    public ClientService ClientService { get; set; } = null!;
    public Guid? BillingEntityId { get; set; }
    public BillingEntity? BillingEntity { get; set; }
    public bool IsBillable { get; set; }
    public required string PricingModel { get; set; } = "FIXED";
    public decimal? Amount { get; set; }
    public required string CurrencyCode { get; set; } = "INR";
    public bool TaxInclusive { get; set; }
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public int Version { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public Guid CreatedByUserId { get; set; }
    public LoginUser CreatedByUser { get; set; } = null!;
    public BillingSchedule? Schedule { get; set; }
}

public sealed class BillingSchedule
{
    public Guid BillingTermId { get; set; }
    public BillingTerm BillingTerm { get; set; } = null!;
    public required string FrequencyCode { get; set; }
    public int? IntervalMonths { get; set; }
    public DateOnly? AnchorDate { get; set; }
    public int? BillingDay { get; set; }
    public required string BusinessDayAdjustment { get; set; } = "NONE";
    public required string ProjectionTiming { get; set; } = "PER_BILLING_EVENT";
    public DateOnly? OneTimeDate { get; set; }
    public ICollection<BillingScheduleMonth> Months { get; } = new List<BillingScheduleMonth>();
}

public sealed class BillingScheduleMonth
{
    public Guid BillingTermId { get; set; }
    public BillingSchedule BillingSchedule { get; set; } = null!;
    public int Month { get; set; }
}

public sealed class BillingImportProposal
{
    public long Id { get; set; }
    public Guid ImportRunId { get; set; }
    public ImportRun ImportRun { get; set; } = null!;
    public int SourceRowNumber { get; set; }
    public string? SourceClientCode { get; set; }
    public string? SourceService { get; set; }
    public string? SourceBillingEntity { get; set; }
    public decimal? SourceAmount { get; set; }
    public string? SourceFrequency { get; set; }
    public Guid? ClientServiceId { get; set; }
    public ClientService? ClientService { get; set; }
    public Guid? BillingEntityId { get; set; }
    public BillingEntity? BillingEntity { get; set; }
    public required string Outcome { get; set; }
    public string? IssueCode { get; set; }
    public required string DataJson { get; set; }
}
