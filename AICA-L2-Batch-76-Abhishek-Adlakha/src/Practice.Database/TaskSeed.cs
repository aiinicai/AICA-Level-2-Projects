using Practice.Database.Entities;

namespace Practice.Database;

public static class TaskSeed
{
    public static readonly Guid NotStartedId = new("50000000-0000-0000-0000-000000000001");
    public static readonly Guid InProcessId = new("50000000-0000-0000-0000-000000000002");
    public static readonly Guid OnHoldId = new("50000000-0000-0000-0000-000000000003");
    public static readonly Guid CompletedId = new("50000000-0000-0000-0000-000000000004");
    public static readonly Guid CancelledId = new("50000000-0000-0000-0000-000000000005");

    public static readonly WorkTaskStatus[] Statuses =
    [
        Status(NotStartedId, "NOT_STARTED", "Not Started", "#64748b", 10, false, false),
        Status(InProcessId, "IN_PROCESS", "In Process", "#2563eb", 20, false, false),
        Status(OnHoldId, "ON_HOLD", "On Hold", "#d97706", 30, false, false),
        Status(CompletedId, "COMPLETED", "Completed", "#059669", 40, true, true),
        Status(CancelledId, "CANCELLED", "Cancelled", "#dc2626", 50, true, false)
    ];

    public static readonly TaskStatusTransition[] Transitions =
    [
        Transition(NotStartedId, InProcessId),
        Transition(NotStartedId, OnHoldId),
        Transition(InProcessId, OnHoldId),
        Transition(OnHoldId, InProcessId),
        Transition(NotStartedId, CancelledId, reason: true),
        Transition(InProcessId, CancelledId, reason: true),
        Transition(OnHoldId, CancelledId, reason: true),
        Transition(InProcessId, CompletedId, completion: true),
        Transition(NotStartedId, CompletedId, completion: true),
        Transition(CompletedId, InProcessId, "tasks.reopen", reason: true),
        Transition(CancelledId, NotStartedId, "tasks.reopen", reason: true)
    ];

    private static WorkTaskStatus Status(Guid id, string code, string label, string color, int order, bool terminal, bool complete) => new()
    {
        Id = id, Code = code, Label = label, Color = color, DisplayOrder = order,
        IsTerminal = terminal, CountsAsComplete = complete, IsActive = true
    };

    private static TaskStatusTransition Transition(Guid from, Guid to, string permission = "tasks.change_status", bool reason = false, bool completion = false) => new()
    {
        FromStatusId = from, ToStatusId = to, RequiredPermission = permission,
        ReasonRequired = reason, CompletionDataRequired = completion
    };
}
