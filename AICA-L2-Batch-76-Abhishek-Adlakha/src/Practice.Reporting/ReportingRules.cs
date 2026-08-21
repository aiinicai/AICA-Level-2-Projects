namespace Practice.Reporting;

public sealed record TaskMetricInput(
    string StatusCode,
    bool IsTerminal,
    DateOnly DueDate,
    DateTimeOffset? CompletedAtUtc,
    DateTimeOffset? CancelledAtUtc);

public static class ReportingRules
{
    public static IReadOnlySet<string> Buckets(
        TaskMetricInput task,
        DateOnly today,
        DateOnly selectedFrom,
        DateOnly selectedTo,
        TimeSpan localOffset)
    {
        var buckets = new HashSet<string>(StringComparer.Ordinal);
        if (!task.IsTerminal && task.DueDate < today) buckets.Add("OVERDUE");
        if (!task.IsTerminal && task.DueDate == today) buckets.Add("DUE_TODAY");
        if (!task.IsTerminal && task.DueDate > today) buckets.Add("UPCOMING");
        if (task.StatusCode == "IN_PROCESS") buckets.Add("IN_PROCESS");
        if (task.StatusCode == "COMPLETED" && InLocalDateRange(task.CompletedAtUtc, selectedFrom, selectedTo, localOffset)) buckets.Add("COMPLETED");
        if (task.StatusCode == "CANCELLED" && InLocalDateRange(task.CancelledAtUtc, selectedFrom, selectedTo, localOffset)) buckets.Add("CANCELLED");
        return buckets;
    }

    public static bool InLocalDateRange(DateTimeOffset? timestamp, DateOnly from, DateOnly to, TimeSpan localOffset)
    {
        if (timestamp is null || to < from) return false;
        var localDate = DateOnly.FromDateTime(timestamp.Value.ToOffset(localOffset).DateTime);
        return localDate >= from && localDate <= to;
    }

    // The Indian financial year runs 1 April to 31 March and is written "FY 2025-26". A CA firm
    // files most statutory work against a year rather than a date, so this is the single
    // definition used by tasks, billing and reporting alike.
    public const int FinancialYearStartMonth = 4;

    public static int FinancialYearStartYear(DateOnly date) =>
        date.Month >= FinancialYearStartMonth ? date.Year : date.Year - 1;

    public static string FinancialYearLabel(int startYear) =>
        string.Create(System.Globalization.CultureInfo.InvariantCulture, $"FY {startYear}-{(startYear + 1) % 100:00}");

    public static string FinancialYearLabel(DateOnly date) => FinancialYearLabel(FinancialYearStartYear(date));

    public static (DateOnly From, DateOnly To) FinancialYearRange(int startYear) =>
        (new DateOnly(startYear, FinancialYearStartMonth, 1), new DateOnly(startYear + 1, FinancialYearStartMonth, 1).AddDays(-1));

    // Offered oldest first so the list reads naturally in a dropdown. Past years matter most: a
    // return filed today is usually for a year that has already closed.
    public static IReadOnlyList<int> FinancialYearChoices(DateOnly today, int yearsBack = 5, int yearsForward = 1)
    {
        var current = FinancialYearStartYear(today);
        return Enumerable.Range(current - yearsBack, yearsBack + yearsForward + 1).ToArray();
    }

    public static (DateTimeOffset StartUtc, DateTimeOffset EndExclusiveUtc) UtcRange(
        DateOnly from,
        DateOnly to,
        TimeSpan localOffset)
    {
        if (to < from) throw new ArgumentOutOfRangeException(nameof(to), "Report end date cannot precede its start date.");
        var start = new DateTimeOffset(from.ToDateTime(TimeOnly.MinValue), localOffset).ToUniversalTime();
        var end = new DateTimeOffset(to.AddDays(1).ToDateTime(TimeOnly.MinValue), localOffset).ToUniversalTime();
        return (start, end);
    }
}
