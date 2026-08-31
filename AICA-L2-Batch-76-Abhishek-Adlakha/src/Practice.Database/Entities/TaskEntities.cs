namespace Practice.Database.Entities;

public sealed class WorkTaskStatus
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Label { get; set; }
    public required string Color { get; set; }
    public int DisplayOrder { get; set; }
    public bool IsTerminal { get; set; }
    public bool CountsAsComplete { get; set; }
    public bool IsActive { get; set; } = true;
}

public sealed class TaskStatusTransition
{
    public Guid FromStatusId { get; set; }
    public WorkTaskStatus FromStatus { get; set; } = null!;
    public Guid ToStatusId { get; set; }
    public WorkTaskStatus ToStatus { get; set; } = null!;
    public required string RequiredPermission { get; set; }
    public bool ReasonRequired { get; set; }
    public bool CompletionDataRequired { get; set; }
}

public sealed class PracticeTask
{
    public Guid Id { get; set; }
    public long TaskNumber { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public Guid ServiceId { get; set; }
    public ServiceDefinition Service { get; set; } = null!;
    public Guid? ClientServiceId { get; set; }
    public ClientService? ClientService { get; set; }
    public Guid? GstRegistrationId { get; set; }
    public GstRegistration? GstRegistration { get; set; }
    public Guid? RecurrenceRuleId { get; set; }
    public RecurrenceRule? RecurrenceRule { get; set; }
    public string? OccurrenceKey { get; set; }
    public required string Title { get; set; }
    public string? Description { get; set; }
    public DateOnly? PeriodStart { get; set; }
    public DateOnly? PeriodEnd { get; set; }
    public DateOnly DueDate { get; set; }
    public Guid StatusId { get; set; }
    public WorkTaskStatus Status { get; set; } = null!;
    public required string Priority { get; set; } = "NORMAL";
    public bool BillableSnapshot { get; set; }
    public DateTimeOffset? CompletedAtUtc { get; set; }
    public Guid? CompletedByUserId { get; set; }
    public LoginUser? CompletedByUser { get; set; }
    public DateTimeOffset? CancelledAtUtc { get; set; }
    public Guid? CancelledByUserId { get; set; }
    public LoginUser? CancelledByUser { get; set; }
    public string? CancellationReason { get; set; }
    public int ReopenedCount { get; set; }
    public required string CreatedSource { get; set; } = "MANUAL";
    public Guid? CreatedByUserId { get; set; }
    public LoginUser? CreatedByUser { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public Guid? UpdatedByUserId { get; set; }
    public LoginUser? UpdatedByUser { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public long RowVersion { get; set; } = 1;
    public ICollection<TaskAssignment> Assignments { get; } = new List<TaskAssignment>();
    public ICollection<TaskStatusHistory> StatusHistory { get; } = new List<TaskStatusHistory>();
    public ICollection<TaskComment> Comments { get; } = new List<TaskComment>();
}

public sealed class TaskAssignment
{
    public Guid Id { get; set; }
    public Guid TaskId { get; set; }
    public PracticeTask Task { get; set; } = null!;
    public Guid EmployeeId { get; set; }
    public Employee Employee { get; set; } = null!;
    public required string AssignmentRole { get; set; }
    public DateTimeOffset AssignedAtUtc { get; set; }
    public Guid? AssignedByUserId { get; set; }
    public LoginUser? AssignedByUser { get; set; }
    public DateTimeOffset? UnassignedAtUtc { get; set; }
    public Guid? UnassignedByUserId { get; set; }
    public LoginUser? UnassignedByUser { get; set; }
    public string? Remarks { get; set; }
    public string? UnassignmentReason { get; set; }
}

public sealed class TaskStatusHistory
{
    public Guid Id { get; set; }
    public Guid TaskId { get; set; }
    public PracticeTask Task { get; set; } = null!;
    public Guid? FromStatusId { get; set; }
    public WorkTaskStatus? FromStatus { get; set; }
    public Guid ToStatusId { get; set; }
    public WorkTaskStatus ToStatus { get; set; } = null!;
    public Guid? ActorUserId { get; set; }
    public LoginUser? ActorUser { get; set; }
    public DateTimeOffset ChangedAtUtc { get; set; }
    public string? Reason { get; set; }
    public string? CompletionNote { get; set; }
    public required string MetadataJson { get; set; } = "{}";
}

public sealed class TaskComment
{
    public Guid Id { get; set; }
    public Guid TaskId { get; set; }
    public PracticeTask Task { get; set; } = null!;
    public Guid AuthorUserId { get; set; }
    public LoginUser AuthorUser { get; set; } = null!;
    public required string Body { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset? EditedAtUtc { get; set; }
    public bool IsRedacted { get; set; }
    public DateTimeOffset? RedactedAtUtc { get; set; }
    public Guid? RedactedByUserId { get; set; }
    public LoginUser? RedactedByUser { get; set; }
}
