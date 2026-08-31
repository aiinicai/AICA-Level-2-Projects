using System.IO.Compression;
using System.Text;
using Practice.Reporting;

var today = new DateOnly(2026, 8, 21); var from = new DateOnly(2026, 8, 1); var to = new DateOnly(2026, 8, 31); var ist = TimeSpan.FromMinutes(330);
Require(ReportingRules.Buckets(new TaskMetricInput("NOT_STARTED", false, today.AddDays(-1), null, null), today, from, to, ist).SetEquals(["OVERDUE"]), "Overdue metric boundary is incorrect.");
Require(ReportingRules.Buckets(new TaskMetricInput("IN_PROCESS", false, today, null, null), today, from, to, ist).SetEquals(["DUE_TODAY", "IN_PROCESS"]), "Due-today/in-process overlap is incorrect.");
Require(ReportingRules.Buckets(new TaskMetricInput("NOT_STARTED", false, today.AddDays(1), null, null), today, from, to, ist).SetEquals(["UPCOMING"]), "Upcoming metric boundary is incorrect.");
Require(ReportingRules.Buckets(new TaskMetricInput("COMPLETED", true, today, new DateTimeOffset(2026, 7, 31, 19, 0, 0, TimeSpan.Zero), null), today, from, to, ist).Contains("COMPLETED"), "IST completion boundary must include 1 August local time.");
var utc = ReportingRules.UtcRange(from, to, ist);
Require(utc.StartUtc == new DateTimeOffset(2026, 7, 31, 18, 30, 0, TimeSpan.Zero) && utc.EndExclusiveUtc == new DateTimeOffset(2026, 8, 31, 18, 30, 0, TimeSpan.Zero), "IST report range conversion is incorrect.");

var columns = new[] { new ExportColumn("Client"), new ExportColumn("Count", true) };
var rows = new[] { (IReadOnlyList<string>)["=Unsafe", "12"] };
var csv = Encoding.UTF8.GetString(TabularExport.Csv(columns, rows));
Require(csv.Contains("'=Unsafe", StringComparison.Ordinal), "CSV formula protection is missing.");
using var stream = new MemoryStream(TabularExport.Xlsx("Task report", columns, rows));
using var archive = new ZipArchive(stream, ZipArchiveMode.Read);
Require(archive.GetEntry("xl/workbook.xml") is not null && archive.GetEntry("xl/worksheets/sheet1.xml") is not null, "XLSX report package is incomplete.");
// The Indian financial year drives most statutory work, so its boundaries are asserted rather
// than assumed: FY 2025-26 runs 1 April 2025 to 31 March 2026.
Require(ReportingRules.FinancialYearLabel(new DateOnly(2025, 4, 1)) == "FY 2025-26", "1 April starts the new financial year.");
Require(ReportingRules.FinancialYearLabel(new DateOnly(2026, 3, 31)) == "FY 2025-26", "31 March still belongs to the year that started the previous April.");
Require(ReportingRules.FinancialYearLabel(new DateOnly(2026, 4, 1)) == "FY 2026-27", "1 April rolls the financial year over.");
Require(ReportingRules.FinancialYearRange(2025) == (new DateOnly(2025, 4, 1), new DateOnly(2026, 3, 31)), "FY 2025-26 spans April to March.");
Require(ReportingRules.FinancialYearChoices(new DateOnly(2026, 8, 21), 5, 1).Contains(2025), "The year just closed must be offered, because returns are filed after it ends.");

Console.WriteLine("Phase 9 metric boundary and tabular export checks passed.");
return 0;

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}
