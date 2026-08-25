namespace Practice.Database.Entities;

public sealed class RecurrenceRule
{
    public Guid Id { get; set; }
    public Guid ClientServiceId { get; set; }
    public ClientService ClientService { get; set; } = null!;
    public Guid HolidayCalendarId { get; set; }
    public HolidayCalendar HolidayCalendar { get; set; } = null!;
    public Guid? DefaultPrimaryAssigneeId { get; set; }
    public Employee? DefaultPrimaryAssignee { get; set; }
    public required string FrequencyCode { get; set; }
    public short IntervalCount { get; set; } = 1;
    public DateOnly AnchorDate { get; set; }
    public required string DueRuleCode { get; set; } = "FIXED_DAY_OF_OFFSET_MONTH";
    public short DueDay { get; set; }
    public short DueMonthOffset { get; set; } = 1;
    public short DueDayOffset { get; set; }
    public required string BusinessDayAdjustment { get; set; } = "NONE";
    public short GenerateLeadDays { get; set; } = 21;
    public required string TimeZoneId { get; set; } = "Asia/Kolkata";
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public int RuleVersion { get; set; } = 1;
    public bool IsActive { get; set; } = true;
    public Guid CreatedByUserId { get; set; }
    public LoginUser CreatedByUser { get; set; } = null!;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public Guid UpdatedByUserId { get; set; }
    public LoginUser UpdatedByUser { get; set; } = null!;
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public long RowVersion { get; set; } = 1;
    public ICollection<RecurrenceRuleMonth> Months { get; } = new List<RecurrenceRuleMonth>();
    public ICollection<RecurrenceAdjustment> Exceptions { get; } = new List<RecurrenceAdjustment>();
}

public sealed class RecurrenceRuleMonth
{
    public Guid RecurrenceRuleId { get; set; }
    public RecurrenceRule RecurrenceRule { get; set; } = null!;
    public short MonthNumber { get; set; }
    public short DisplayOrder { get; set; }
}

public sealed class RecurrenceAdjustment
{
    public Guid Id { get; set; }
    public Guid RecurrenceRuleId { get; set; }
    public RecurrenceRule RecurrenceRule { get; set; } = null!;
    public DateOnly PeriodStart { get; set; }
    public DateOnly PeriodEnd { get; set; }
    public required string Action { get; set; }
    public DateOnly? OverrideDueDate { get; set; }
    public string? OverrideTitle { get; set; }
    public Guid? OverridePrimaryAssigneeId { get; set; }
    public Employee? OverridePrimaryAssignee { get; set; }
    public string? OverridePriority { get; set; }
    public required string Reason { get; set; }
    public Guid CreatedByUserId { get; set; }
    public LoginUser CreatedByUser { get; set; } = null!;
    public DateTimeOffset CreatedAtUtc { get; set; }
}

public sealed class TaskGenerationRun
{
    public Guid Id { get; set; }
    public DateOnly WindowFrom { get; set; }
    public DateOnly WindowTo { get; set; }
    public required string Trigger { get; set; }
    public required string Status { get; set; }
    public required string WorkerId { get; set; }
    public Guid? TriggeredByUserId { get; set; }
    public LoginUser? TriggeredByUser { get; set; }
    public DateTimeOffset StartedAtUtc { get; set; }
    public DateTimeOffset? FinishedAtUtc { get; set; }
    public int CreatedCount { get; set; }
    public int ExistingCount { get; set; }
    public int SkippedCount { get; set; }
    public int ErrorCount { get; set; }
    public string? ErrorSummary { get; set; }
    public ICollection<TaskGenerationRunItem> Items { get; } = new List<TaskGenerationRunItem>();
}

public sealed class TaskGenerationRunItem
{
    public long Id { get; set; }
    public Guid RunId { get; set; }
    public TaskGenerationRun Run { get; set; } = null!;
    public Guid RecurrenceRuleId { get; set; }
    public RecurrenceRule RecurrenceRule { get; set; } = null!;
    public required string OccurrenceKey { get; set; }
    public required string Outcome { get; set; }
    public Guid? TaskId { get; set; }
    public PracticeTask? Task { get; set; }
    public DateOnly PeriodStart { get; set; }
    public DateOnly PeriodEnd { get; set; }
    public DateOnly? DueDate { get; set; }
    public string? Message { get; set; }
}
