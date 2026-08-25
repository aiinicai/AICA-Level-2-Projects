using Practice.Database.Entities;

namespace Practice.Scheduling;

public sealed record ScheduledOccurrence(
    DateOnly PeriodStart,
    DateOnly PeriodEnd,
    DateOnly NominalDueDate,
    DateOnly DueDate,
    DateOnly GenerateOnDate,
    string OccurrenceKey);

public static class RecurrenceCalculator
{
    private const int MaximumMonthsToInspect = 600;

    public static IReadOnlyList<ScheduledOccurrence> Calculate(
        RecurrenceRule rule,
        DateOnly windowFrom,
        DateOnly windowTo,
        IReadOnlyDictionary<DateOnly, bool>? holidayOverrides = null)
    {
        ArgumentNullException.ThrowIfNull(rule);
        if (windowTo < windowFrom)
        {
            throw new ArgumentOutOfRangeException(nameof(windowTo), "The scheduling window must end on or after it starts.");
        }

        holidayOverrides ??= new Dictionary<DateOnly, bool>();
        var results = new List<ScheduledOccurrence>();
        foreach (var period in EnumeratePeriods(rule))
        {
            if (period.Start > rule.EffectiveTo.GetValueOrDefault(DateOnly.MaxValue)) break;
            if (period.End < rule.EffectiveFrom) continue;

            var nominalDueDate = FixedDueDate(rule, period.End);
            var dueDate = AdjustBusinessDay(nominalDueDate, rule.BusinessDayAdjustment, holidayOverrides);
            if (dueDate < windowFrom || dueDate > windowTo) continue;

            results.Add(new ScheduledOccurrence(
                period.Start,
                period.End,
                nominalDueDate,
                dueDate,
                dueDate.AddDays(-rule.GenerateLeadDays),
                OccurrenceKey(rule, period.Start, period.End)));
        }

        return results;
    }

    public static DateOnly AdjustBusinessDay(
        DateOnly date,
        string adjustment,
        IReadOnlyDictionary<DateOnly, bool> holidayOverrides)
    {
        if (adjustment == "NONE") return date;
        var direction = adjustment switch
        {
            "NEXT_BUSINESS_DAY" => 1,
            "PREVIOUS_BUSINESS_DAY" => -1,
            _ => throw new ArgumentOutOfRangeException(nameof(adjustment), adjustment, "Unsupported business-day adjustment.")
        };

        var candidate = date;
        for (var inspected = 0; inspected < 370; inspected++)
        {
            if (IsWorkingDay(candidate, holidayOverrides)) return candidate;
            candidate = candidate.AddDays(direction);
        }

        throw new InvalidOperationException("No working day was found within the safety limit.");
    }

    public static bool IsWorkingDay(DateOnly date, IReadOnlyDictionary<DateOnly, bool> holidayOverrides)
    {
        if (holidayOverrides.TryGetValue(date, out var workingDayOverride)) return workingDayOverride;
        return date.DayOfWeek != DayOfWeek.Sunday;
    }

    public static string OccurrenceKey(RecurrenceRule rule, DateOnly start, DateOnly end) =>
        $"{rule.Id:N}:{rule.RuleVersion}:{start:yyyyMMdd}:{end:yyyyMMdd}";

    private static DateOnly FixedDueDate(RecurrenceRule rule, DateOnly periodEnd)
    {
        if (rule.DueRuleCode != "FIXED_DAY_OF_OFFSET_MONTH")
        {
            throw new InvalidOperationException($"Unsupported due rule '{rule.DueRuleCode}'.");
        }

        var dueMonth = new DateOnly(periodEnd.Year, periodEnd.Month, 1).AddMonths(rule.DueMonthOffset);
        var day = Math.Min(rule.DueDay, (short)DateTime.DaysInMonth(dueMonth.Year, dueMonth.Month));
        return new DateOnly(dueMonth.Year, dueMonth.Month, day).AddDays(rule.DueDayOffset);
    }

    private static IEnumerable<(DateOnly Start, DateOnly End)> EnumeratePeriods(RecurrenceRule rule)
    {
        var anchorMonth = new DateOnly(rule.AnchorDate.Year, rule.AnchorDate.Month, 1);
        if (rule.FrequencyCode == "CUSTOM_MONTHS")
        {
            var selectedMonths = rule.Months.Select(item => (int)item.MonthNumber).Distinct().Order().ToArray();
            if (selectedMonths.Length == 0) yield break;
            for (var yearOffset = 0; yearOffset <= MaximumMonthsToInspect / 12; yearOffset++)
            {
                var year = anchorMonth.Year + yearOffset;
                foreach (var month in selectedMonths)
                {
                    var start = new DateOnly(year, month, 1);
                    if (start < anchorMonth) continue;
                    yield return (start, start.AddMonths(1).AddDays(-1));
                }
            }
            yield break;
        }

        var baseMonths = rule.FrequencyCode switch
        {
            "MONTHLY" => 1,
            "QUARTERLY" => 3,
            "HALF_YEARLY" => 6,
            "YEARLY" => 12,
            _ => throw new InvalidOperationException($"Unsupported frequency '{rule.FrequencyCode}'.")
        };
        var spanMonths = baseMonths;
        var stepMonths = checked(baseMonths * rule.IntervalCount);
        for (var monthOffset = 0; monthOffset <= MaximumMonthsToInspect; monthOffset += stepMonths)
        {
            var start = anchorMonth.AddMonths(monthOffset);
            yield return (start, start.AddMonths(spanMonths).AddDays(-1));
        }
    }
}
