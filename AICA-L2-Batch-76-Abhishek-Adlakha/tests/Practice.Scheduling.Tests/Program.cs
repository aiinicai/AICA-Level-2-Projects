using Practice.Database.Entities;
using Practice.Scheduling;

var gst = Rule(anchor: new DateOnly(2026, 7, 1));
var july = RecurrenceCalculator.Calculate(gst, new DateOnly(2026, 8, 1), new DateOnly(2026, 8, 31)).Single();
Require(july.PeriodStart == new DateOnly(2026, 7, 1) && july.PeriodEnd == new DateOnly(2026, 7, 31), "Monthly GST period is incorrect.");
Require(july.DueDate == new DateOnly(2026, 8, 20), "Monthly GST due date must be 20 August 2026.");
Require(july.GenerateOnDate == new DateOnly(2026, 7, 30), "The 21-day lead date is incorrect.");

var holiday = new Dictionary<DateOnly, bool> { [new DateOnly(2026, 8, 20)] = false };
var moved = RecurrenceCalculator.Calculate(gst, new DateOnly(2026, 8, 1), new DateOnly(2026, 8, 31), holiday).Single();
Require(moved.DueDate == new DateOnly(2026, 8, 21), "A holiday must move a next-business-day deadline.");

Require(RecurrenceCalculator.IsWorkingDay(new DateOnly(2026, 8, 22), new Dictionary<DateOnly, bool>()), "Saturday must remain working until the firm confirms another policy.");
Require(!RecurrenceCalculator.IsWorkingDay(new DateOnly(2026, 8, 23), new Dictionary<DateOnly, bool>()), "Sunday must be non-working.");
Require(RecurrenceCalculator.AdjustBusinessDay(new DateOnly(2026, 8, 23), "NEXT_BUSINESS_DAY", new Dictionary<DateOnly, bool>()) == new DateOnly(2026, 8, 24), "Sunday must roll to Monday.");

var leap = Rule(anchor: new DateOnly(2028, 1, 1), dueDay: 31, dueMonthOffset: 1);
var february = RecurrenceCalculator.Calculate(leap, new DateOnly(2028, 2, 1), new DateOnly(2028, 2, 29)).Single();
Require(february.NominalDueDate == new DateOnly(2028, 2, 29), "Due day must clamp to leap-month end.");

var stable = RecurrenceCalculator.OccurrenceKey(gst, july.PeriodStart, july.PeriodEnd);
Require(stable == RecurrenceCalculator.OccurrenceKey(gst, july.PeriodStart, july.PeriodEnd), "Occurrence keys must be deterministic.");
gst.RuleVersion++;
Require(stable != RecurrenceCalculator.OccurrenceKey(gst, july.PeriodStart, july.PeriodEnd), "Rule versions must produce distinct occurrence keys.");

// The enrolment form states a yearly deadline as a date and converts it to a month offset. These
// pin the conversion, because getting it wrong moves a statutory deadline by months without
// anything looking broken: entering "7" for July would in fact schedule 31 October.
Require(YearlyOffset(4, 7) == 4, "A year starting in April ends in March, so a July deadline is four months later.");
Require(YearlyOffset(4, 4) == 1, "An April deadline falls the month after a March period end.");
Require(YearlyOffset(4, 3) == 0, "A March deadline falls in the same month the period ends.");
Require(YearlyOffset(1, 12) == 0, "A calendar year ends in December, so a December deadline is the same month.");
Require(YearlyOffset(1, 3) == 3, "A calendar year with a March deadline is three months later.");

Console.WriteLine("Phase 6 recurrence and due-date matrix passed.");
return 0;

static RecurrenceRule Rule(DateOnly anchor, short dueDay = 20, short dueMonthOffset = 1) => new()
{
    Id = new Guid("60000000-0000-0000-0000-000000000001"), ClientServiceId = Guid.NewGuid(),
    HolidayCalendarId = Guid.NewGuid(), FrequencyCode = "MONTHLY", IntervalCount = 1,
    AnchorDate = anchor, DueRuleCode = "FIXED_DAY_OF_OFFSET_MONTH", DueDay = dueDay,
    DueMonthOffset = dueMonthOffset, BusinessDayAdjustment = "NEXT_BUSINESS_DAY",
    GenerateLeadDays = 21, TimeZoneId = "Asia/Kolkata", EffectiveFrom = anchor,
    RuleVersion = 1, CreatedByUserId = Guid.NewGuid(), UpdatedByUserId = Guid.NewGuid()
};

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

// Mirrors yearlyOffsetFrom in the web client: the period ends the month before it starts.
static int YearlyOffset(int startMonth, int deadlineMonth)
{
    var periodEndMonth = startMonth == 1 ? 12 : startMonth - 1;
    return (deadlineMonth - periodEndMonth + 12) % 12;
}
