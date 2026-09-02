namespace Practice.Database;

// Retention rules for the audit trail, kept pure so the date boundaries can be tested without a
// database. Security-relevant history is kept four times longer than routine business history:
// those are the records an investigation actually needs, and they are cheap to keep.
public static class AuditRetention
{
    public const int GeneralRetentionMonths = 3;
    public const int SecurityRetentionMonths = 12;

    // Everything under identity.* is security history. These few extra actions are too, because
    // they change who can do what, or record confidential data leaving the system.
    private static readonly string[] AdditionalSecurityActions =
    [
        "reports.exported",
        "system.field_policy_changed",
        "employees.created",
        "employees.team_created"
    ];

    public static bool IsSecurityAction(string action) =>
        action.StartsWith("identity.", StringComparison.Ordinal)
        || AdditionalSecurityActions.Contains(action, StringComparer.Ordinal);

    public static DateTimeOffset CutoffFor(string action, DateTimeOffset now) =>
        now.AddMonths(-(IsSecurityAction(action) ? SecurityRetentionMonths : GeneralRetentionMonths));

    public static bool IsExpired(string action, DateTimeOffset occurredAtUtc, DateTimeOffset now) =>
        occurredAtUtc < CutoffFor(action, now);

    public static IReadOnlyList<string> SecurityActionList() => AdditionalSecurityActions;
}
