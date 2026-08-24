using Practice.Billing;
using Practice.Api.Billing;
using System.IO.Compression;
using System.Text;

var anchor = new DateOnly(2026, 4, 1);
foreach (var (frequency, months) in new[]
{
    ("MONTHLY", Array.Empty<int>()), ("QUARTERLY", Array.Empty<int>()), ("HALF_YEARLY", Array.Empty<int>()),
    ("ANNUALLY", Array.Empty<int>()), ("SPECIFIC_MONTH", new[] { 4 }), ("CUSTOM_MONTHS", new[] { 4, 7, 10, 1 })
})
{
    Require(BillingRules.ValidateSchedule(frequency, anchor, 15, null, months, "NONE").Count == 0, $"{frequency} should be valid.");
}
Require(BillingRules.ValidateSchedule("ONE_TIME", null, null, new DateOnly(2026, 8, 20), [], "NEXT").Count == 0, "One-time schedule should be valid.");
Require(BillingRules.ValidateSchedule("SPECIFIC_MONTH", anchor, 15, null, [], "NONE").Count > 0, "Specific month must select one month.");
Require(BillingRules.ValidateSchedule("CUSTOM_MONTHS", anchor, 15, null, [4, 4], "NONE").Count > 0, "Duplicate custom months must fail.");
Require(BillingRules.IntervalMonths("QUARTERLY") == 3 && BillingRules.IntervalMonths("ONE_TIME") is null, "Frequency intervals are incorrect.");

var monthly = Projection("MONTHLY", new DateOnly(2026, 1, 1), 31, 2_000m);
var monthlyRows = BillingProjectionCalculator.Calculate(monthly, new DateOnly(2026, 1, 1), new DateOnly(2026, 12, 31));
Require(monthlyRows.Count == 12 && monthlyRows.Sum(item => item.Amount) == 24_000m, "Monthly annual projection must contain 12 full fee events.");
Require(monthlyRows[1].NominalDate == new DateOnly(2026, 2, 28), "Billing day must clip to the last calendar day.");

var quarterly = Projection("QUARTERLY", new DateOnly(2026, 4, 1), 15, 1_000m);
var quarterlyRows = BillingProjectionCalculator.Calculate(quarterly, new DateOnly(2026, 4, 1), new DateOnly(2027, 3, 31));
Require(quarterlyRows.Count == 4 && quarterlyRows.Sum(item => item.Amount) == 4_000m, "Quarterly fiscal-year projection must contain four events.");
Require(quarterlyRows[0].ServicePeriodEnd == new DateOnly(2026, 6, 30), "Quarterly explanation period is incorrect.");

var annual = Projection("ANNUALLY", new DateOnly(2026, 9, 1), 15, 25_000m);
var calendarQuarterly = Projection("QUARTERLY", new DateOnly(2026, 1, 1), 15, 1_000m);
var matrixTotal = monthlyRows.Sum(item => item.Amount) +
                  BillingProjectionCalculator.Calculate(calendarQuarterly, new DateOnly(2026, 1, 1), new DateOnly(2026, 12, 31)).Sum(item => item.Amount) +
                  BillingProjectionCalculator.Calculate(annual, new DateOnly(2026, 1, 1), new DateOnly(2026, 12, 31)).Sum(item => item.Amount);
Require(matrixTotal == 53_000m, "Hand-calculated billing matrix must reconcile to 53,000.");

var changedTerm = monthly with { EffectiveFrom = new DateOnly(2026, 7, 1), Amount = 2_500m, TermVersion = 2 };
Require(BillingProjectionCalculator.Calculate(changedTerm, new DateOnly(2026, 1, 1), new DateOnly(2026, 12, 31)).Sum(item => item.Amount) == 15_000m, "Mid-year term changes must respect effective boundaries.");

var selected = Projection("CUSTOM_MONTHS", new DateOnly(2026, 1, 1), 10, 500m, [1, 4, 7, 10]);
Require(BillingProjectionCalculator.Calculate(selected, new DateOnly(2026, 1, 1), new DateOnly(2026, 12, 31)).Count == 4, "Custom-month projection is incorrect.");

var oneTime = new ProjectionTerm(Guid.NewGuid(), 1, 10_000m, "INR", new DateOnly(2026, 1, 1), null,
    new ProjectionSchedule("ONE_TIME", null, null, "NONE", new DateOnly(2026, 8, 20), []));
Require(BillingProjectionCalculator.Calculate(oneTime, new DateOnly(2026, 8, 1), new DateOnly(2026, 8, 31)).Single().Amount == 10_000m, "One-time projection is incorrect.");

var sunday = Projection("MONTHLY", new DateOnly(2026, 8, 1), 23, 1m) with
{
    Schedule = new ProjectionSchedule("MONTHLY", new DateOnly(2026, 8, 1), 23, "NEXT", null, [])
};
Require(BillingProjectionCalculator.Calculate(sunday, new DateOnly(2026, 8, 1), new DateOnly(2026, 8, 31)).Single().ProjectionDate == new DateOnly(2026, 8, 24), "Sunday must move to Monday.");

var leap = Projection("MONTHLY", new DateOnly(2028, 1, 1), 31, 1m);
Require(BillingProjectionCalculator.Calculate(leap, new DateOnly(2028, 2, 1), new DateOnly(2028, 2, 29)).Single().NominalDate.Day == 29, "Leap-year billing day clipping is incorrect.");

var exportDetail = new ProjectionDetail(monthly.TermId, 1, Guid.NewGuid(), Guid.NewGuid(), "ABC", "ABC Private Limited", null, "Ungrouped",
    Guid.NewGuid(), "GST", "GST Return", Guid.NewGuid(), "FIRM-A", "Firm A", null, null, null, null,
    new DateOnly(2026, 1, 31), new DateOnly(2026, 1, 31), new DateOnly(2026, 1, 1), new DateOnly(2026, 1, 31),
    2_000m, "INR", false, "MONTHLY", "Term v1 · MONTHLY · nominal 2026-01-31 · 2000.00 INR");
var exportReport = new ProjectionReport(new DateOnly(2026, 1, 1), new DateOnly(2026, 1, 31), new DateOnly(2026, 1, 1), DateTimeOffset.UtcNow,
    "Expected fees only.", [], [], [], [], [], [], [], [], [], [], [], [exportDetail]);
var csv = Encoding.UTF8.GetString(ProjectionExport.CreateCsv(exportReport));
Require(csv.Contains("ABC Private Limited", StringComparison.Ordinal) && csv.Contains("2000.00", StringComparison.Ordinal), "CSV export must contain projection detail.");
using (var xlsxStream = new MemoryStream(ProjectionExport.CreateXlsx(exportReport)))
using (var xlsx = new ZipArchive(xlsxStream, ZipArchiveMode.Read))
{
    Require(xlsx.GetEntry("xl/workbook.xml") is not null && xlsx.GetEntry("xl/worksheets/sheet1.xml") is not null, "XLSX export must be a valid Open XML package.");
}
Console.WriteLine("Billing schedule and Phase 8 projection checks passed.");
return 0;

static ProjectionTerm Projection(string frequency, DateOnly anchorDate, int billingDay, decimal amount, int[]? months = null) =>
    new(Guid.NewGuid(), 1, amount, "INR", anchorDate, null,
        new ProjectionSchedule(frequency, anchorDate, billingDay, "NONE", null, months ?? []));

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}
