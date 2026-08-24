namespace Practice.Billing;

public sealed record ProjectionSchedule(
    string FrequencyCode,
    DateOnly? AnchorDate,
    int? BillingDay,
    string BusinessDayAdjustment,
    DateOnly? OneTimeDate,
    IReadOnlyCollection<int> Months);

public sealed record ProjectionTerm(
    Guid TermId,
    int TermVersion,
    decimal Amount,
    string CurrencyCode,
    DateOnly EffectiveFrom,
    DateOnly? EffectiveTo,
    ProjectionSchedule Schedule);

public sealed record ProjectionOccurrence(
    Guid TermId,
    int TermVersion,
    DateOnly NominalDate,
    DateOnly ProjectionDate,
    DateOnly ServicePeriodStart,
    DateOnly ServicePeriodEnd,
    decimal Amount,
    string CurrencyCode,
    string Explanation);

public static class BillingProjectionCalculator
{
    private const int MaximumMonthsToInspect = 1_200;

    public static IReadOnlyList<ProjectionOccurrence> Calculate(
        ProjectionTerm term,
        DateOnly windowFrom,
        DateOnly windowTo,
        IReadOnlyDictionary<DateOnly, bool>? holidayOverrides = null)
    {
        ArgumentNullException.ThrowIfNull(term);
        if (windowTo < windowFrom)
        {
            throw new ArgumentOutOfRangeException(nameof(windowTo), "Projection end date must be on or after its start date.");
        }

        if (term.Amount < 0 || term.CurrencyCode.Length != 3)
        {
            throw new ArgumentException("Projection terms require a non-negative amount and three-letter currency.", nameof(term));
        }

        holidayOverrides ??= new Dictionary<DateOnly, bool>();
        var results = new List<ProjectionOccurrence>();
        var latestNominalDate = term.EffectiveTo is { } effectiveTo && effectiveTo <= DateOnly.MaxValue.AddDays(-7)
            ? effectiveTo.AddDays(7)
            : DateOnly.MaxValue;
        foreach (var cycle in EnumerateCycles(term.Schedule))
        {
            var windowStop = windowTo <= DateOnly.MaxValue.AddDays(-7) ? windowTo.AddDays(7) : DateOnly.MaxValue;
            if (cycle.NominalDate > windowStop || cycle.NominalDate > latestNominalDate)
            {
                break;
            }

            var projectionDate = AdjustBusinessDay(cycle.NominalDate, term.Schedule.BusinessDayAdjustment, holidayOverrides);
            if (projectionDate < windowFrom || projectionDate > windowTo || projectionDate < term.EffectiveFrom || projectionDate > term.EffectiveTo.GetValueOrDefault(DateOnly.MaxValue))
            {
                continue;
            }

            results.Add(new ProjectionOccurrence(
                term.TermId,
                term.TermVersion,
                cycle.NominalDate,
                projectionDate,
                cycle.PeriodStart,
                cycle.PeriodEnd,
                decimal.Round(term.Amount, 2, MidpointRounding.AwayFromZero),
                term.CurrencyCode.ToUpperInvariant(),
                $"Term v{term.TermVersion} · {term.Schedule.FrequencyCode} · nominal {cycle.NominalDate:yyyy-MM-dd} · {term.Amount:0.00} {term.CurrencyCode.ToUpperInvariant()}"));
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
            "NEXT" => 1,
            "PREVIOUS" => -1,
            _ => throw new ArgumentOutOfRangeException(nameof(adjustment), adjustment, "Unsupported billing business-day adjustment.")
        };

        var candidate = date;
        for (var inspected = 0; inspected < 370; inspected++)
        {
            if (IsWorkingDay(candidate, holidayOverrides)) return candidate;
            candidate = candidate.AddDays(direction);
        }

        throw new InvalidOperationException("No billing working day was found within the safety limit.");
    }

    private static bool IsWorkingDay(DateOnly date, IReadOnlyDictionary<DateOnly, bool> holidayOverrides)
    {
        if (holidayOverrides.TryGetValue(date, out var workingDayOverride)) return workingDayOverride;
        return date.DayOfWeek != DayOfWeek.Sunday;
    }

    private static IEnumerable<(DateOnly NominalDate, DateOnly PeriodStart, DateOnly PeriodEnd)> EnumerateCycles(ProjectionSchedule schedule)
    {
        if (schedule.FrequencyCode == "ONE_TIME")
        {
            if (schedule.OneTimeDate is { } oneTime)
            {
                yield return (oneTime, oneTime, oneTime);
            }
            yield break;
        }

        if (schedule.AnchorDate is not { } anchor || schedule.BillingDay is not { } billingDay)
        {
            yield break;
        }

        var anchorMonth = new DateOnly(anchor.Year, anchor.Month, 1);
        if (schedule.FrequencyCode is "SPECIFIC_MONTH" or "CUSTOM_MONTHS")
        {
            var months = schedule.Months.Distinct().Order().ToArray();
            for (var yearOffset = 0; yearOffset <= MaximumMonthsToInspect / 12; yearOffset++)
            {
                var year = anchor.Year + yearOffset;
                foreach (var month in months)
                {
                    var periodStart = new DateOnly(year, month, 1);
                    if (periodStart < anchorMonth) continue;
                    yield return (WithDay(periodStart, billingDay), periodStart, periodStart.AddMonths(1).AddDays(-1));
                }
            }
            yield break;
        }

        var intervalMonths = BillingRules.IntervalMonths(schedule.FrequencyCode)
            ?? throw new ArgumentOutOfRangeException(nameof(schedule), schedule.FrequencyCode, "Unsupported projection frequency.");
        for (var offset = 0; offset <= MaximumMonthsToInspect; offset += intervalMonths)
        {
            var periodStart = anchorMonth.AddMonths(offset);
            yield return (WithDay(periodStart, billingDay), periodStart, periodStart.AddMonths(intervalMonths).AddDays(-1));
        }
    }

    private static DateOnly WithDay(DateOnly month, int day) =>
        new(month.Year, month.Month, Math.Min(day, DateTime.DaysInMonth(month.Year, month.Month)));
}
