using Practice.ClientImporter;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using Practice.WorkbookProfiler;

var fixturePath = Path.Combine(Path.GetTempPath(), $"practice-profiler-{Guid.NewGuid():N}.xlsx");
try
{
    CreateSanitizedFixture(fixturePath);
    var before = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(fixturePath)));
    var report = WorkbookProfilerService.Profile(fixturePath, ["Alice"]);
    var after = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(fixturePath)));

    Require(before == after, "Profiler modified its source workbook.");
    Require(report.Sheets.Count == 1, "Expected one worksheet.");
    Require(report.TotalDataRows == 3, "Expected three data rows.");
    Require(report.Sheets[0].Issues.Any(issue => issue.Code == "DuplicateValue" && issue.ColumnName == "Code"),
        "Expected duplicate code detection.");
    Require(report.Sheets[0].Issues.Any(issue => issue.Code == "UnmatchedReferenceValue" && issue.Value == "Bob"),
        "Expected unmatched employee detection.");
    var dryRun = ClientDryRunService.Analyze(fixturePath);
    Require(dryRun.SourceRows == 3, "Client dry-run row reconciliation is incorrect.");
    Require(dryRun.Rows.Any(row => row.Issues.Any(issue => issue.Code == "AMBIGUOUS_FIRM")),
        "Ambiguous Firm category must remain an exception.");
    Require(dryRun.DuplicateClientCodeSets == 1, "Client dry-run should detect the normalized duplicate code.");
    Require(before == Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(fixturePath))), "Client dry-run modified its source workbook.");
    var serviceDryRun = ServiceDryRunService.Analyze(fixturePath);
    Require(serviceDryRun.ProposedAgreementCount == 3 && serviceDryRun.ReadyAgreementCount == 3,
        "Service dry-run should stage Monthly/Yearly Accounts and GST flags as three ready agreements.");
    Require(serviceDryRun.UnknownServiceFlagCount == 0, "Approved service flag values should not be reported as unknown.");
    Require(before == Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(fixturePath))), "Service dry-run modified its source workbook.");
    RequireImportRules();
Console.WriteLine("Workbook profiler, dry-run and client import rule checks passed.");
    return 0;
}
finally
{
    File.Delete(fixturePath);
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}

static void CreateSanitizedFixture(string path)
{
    using var archive = ZipFile.Open(path, ZipArchiveMode.Create);
    Add(archive, "[Content_Types].xml", """
        <?xml version="1.0" encoding="UTF-8"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
          <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
        </Types>
        """);
    Add(archive, "_rels/.rels", """
        <?xml version="1.0" encoding="UTF-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
        </Relationships>
        """);
    Add(archive, "xl/workbook.xml", """
        <?xml version="1.0" encoding="UTF-8"?>
        <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
          <sheets><sheet name="Master Data" sheetId="1" r:id="rId1"/></sheets>
        </workbook>
        """);
    Add(archive, "xl/_rels/workbook.xml.rels", """
        <?xml version="1.0" encoding="UTF-8"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
        </Relationships>
        """);
    Add(archive, "xl/worksheets/sheet1.xml", """
        <?xml version="1.0" encoding="UTF-8"?>
        <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
          <row r="1"><c r="A1" t="inlineStr"><is><t>Code</t></is></c><c r="B1" t="inlineStr"><is><t>Accountant</t></is></c><c r="C1" t="inlineStr"><is><t>Category</t></is></c><c r="D1" t="inlineStr"><is><t>Client name</t></is></c><c r="E1" t="inlineStr"><is><t>A/c</t></is></c><c r="F1" t="inlineStr"><is><t>GST</t></is></c><c r="G1" t="inlineStr"><is><t>GSTIN</t></is></c></row>
          <row r="2"><c r="A2" t="inlineStr"><is><t>C001</t></is></c><c r="B2" t="inlineStr"><is><t>Alice</t></is></c><c r="C2" t="inlineStr"><is><t>Firm</t></is></c><c r="D2" t="inlineStr"><is><t>Alpha</t></is></c><c r="E2" t="inlineStr"><is><t>Monthly</t></is></c><c r="F2" t="inlineStr"><is><t>Yes</t></is></c><c r="G2" t="inlineStr"><is><t>27AAPFU0939F1ZV</t></is></c></row>
          <row r="3"><c r="A3" t="inlineStr"><is><t> c001 </t></is></c><c r="B3" t="inlineStr"><is><t>Bob</t></is></c><c r="C3" t="inlineStr"><is><t>Individual</t></is></c><c r="D3" t="inlineStr"><is><t>Beta</t></is></c><c r="E3" t="inlineStr"><is><t>No</t></is></c><c r="F3" t="inlineStr"><is><t>No</t></is></c></row>
          <row r="4"><c r="A4" t="inlineStr"><is><t>C002</t></is></c><c r="B4" t="inlineStr"><is><t>Alice</t></is></c><c r="C4" t="inlineStr"><is><t>Individual</t></is></c><c r="D4" t="inlineStr"><is><t>Gamma</t></is></c><c r="E4" t="inlineStr"><is><t>Yearly</t></is></c><c r="F4" t="inlineStr"><is><t>No</t></is></c></row>
        </sheetData></worksheet>
        """);
}

// The owner's import decisions of 2026-08-21. These encode business rules, not implementation
// detail, so they must fail loudly if anyone changes what a workbook category means.
static void RequireImportRules()
{
    Require(ImportPlan.CategoryCodeFor("FIRM", "Sharma And Company") == "PARTNERSHIP",
        "Workbook category FIRM means a Partnership Firm.");
    Require(ImportPlan.CategoryCodeFor("FIRM", "Sharma Trading LLP") == "LLP",
        "A name containing LLP means a Limited Liability Partnership.");
    Require(ImportPlan.CategoryCodeFor("FIRM", "Sharma Ventures OPC") == "OPC",
        "A name containing OPC means a One Person Company.");
    Require(ImportPlan.CategoryCodeFor(null, "Ramesh Kumar") == "INDIVIDUAL",
        "A row with no category becomes an Individual.");
    Require(ImportPlan.CategoryCodeFor("PVT LTD", "Acme Industries Private Limited") == "PRIVATE_LIMITED",
        "An explicit private limited category is preserved.");
    Require(ImportPlan.CategoryCodeFor("INDIVIDUAL", "Gopal Llpsingh") == "INDIVIDUAL",
        "LLP inside a longer word must not reclassify an individual.");

    var report = new ClientDryRunReport("book.xlsm", "hash", DateTimeOffset.UtcNow, "Master Data", 4, 4, 0, 0, 0, 0,
    [
        Row(10, "C-1", "Old Trading Name", "AAAAA1111A", "27AAAAA1111A1Z5"),
        Row(20, "C-2", "New Trading Name", "AAAAA1111A", "07AAAAA1111A1Z9"),
        Row(30, "C-3", "Separate Business", "BBBBB2222B", null)
    ]);
    var plan = ImportPlan.Build(report);

    Require(plan.Clients.Count == 2, "Rows sharing a PAN merge into one client; a different PAN stays separate.");
    var merged = plan.Clients.Single(item => item.SourceRowNumbers.Count > 1);
    Require(merged.DisplayName == "New Trading Name", "The later row supplies the surviving name.");
    Require(merged.PreviousNames.Contains("Old Trading Name"), "The earlier name is preserved, not discarded.");
    Require(merged.Gstins.Count == 2, "Every state registration follows the merged client.");
    Require(plan.MergedRowCount == 1, "One row was absorbed by the merge.");
    Require(merged.BuildNotes()!.Contains("Merged from workbook rows 10, 20", StringComparison.Ordinal),
        "The merge is explained in the client notes.");
}

static ClientImportRow Row(int number, string code, string name, string pan, string? gstin) =>
    new(number, code, null, name, "INDIVIDUAL", null, null, null, null, null, null, pan, null, gstin, "READY", []);

static void Add(ZipArchive archive, string name, string contents)
{
    var entry = archive.CreateEntry(name);
    using var writer = new StreamWriter(entry.Open(), new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
    writer.Write(contents);
}
