using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Practice.ClientImporter;
using Practice.Database;
using Practice.Database.Entities;
using Practice.WorkbookProfiler;

// Importing client data is a privileged, one-off operation, so it lives in a command run
// deliberately rather than behind an HTTP endpoint. It defaults to a dry run: --apply is required
// before anything is written, and the whole write happens in one transaction.
if (args.Length == 0 || args.Contains("--help", StringComparer.Ordinal))
{
    Console.WriteLine("Usage: Practice.ClientImporter <workbook.xlsm> [--people] [--apply] [--connection <string>]");
    Console.WriteLine("  (default)  plan and import clients");
    Console.WriteLine("  --people   stage the unresolved owner names for mapping in the application");
    Console.WriteLine("Without --apply nothing is written.");
    return args.Length == 0 ? 2 : 0;
}

var workbookPath = Path.GetFullPath(args[0]);
var apply = args.Contains("--apply", StringComparer.Ordinal);
var connectionString = OptionValue(args, "--connection")
    ?? Environment.GetEnvironmentVariable("ConnectionStrings__PracticeDatabase");

var seedPeople = args.Contains("--people", StringComparer.Ordinal);

if (seedPeople)
{
    var people = ServiceDryRunService.Analyze(workbookPath);
    var distinctPeople = people.UnresolvedOwnershipReferences
        .Select(item => item.SourceValue.Trim())
        .Distinct(StringComparer.OrdinalIgnoreCase).Count();
    Console.WriteLine($"Unresolved owner references: {people.UnresolvedOwnershipReferences.Count}");
    Console.WriteLine($"Distinct people to map     : {distinctPeople}");

    if (!apply)
    {
        Console.WriteLine();
        Console.WriteLine("Dry run only. Nothing was written. Re-run with --apply to stage them.");
        return 0;
    }
    if (string.IsNullOrWhiteSpace(connectionString))
    {
        Console.Error.WriteLine("A connection string is required to apply. Pass --connection or set ConnectionStrings__PracticeDatabase.");
        return 1;
    }

    var peopleOptions = new DbContextOptionsBuilder<AppDbContext>().UseNpgsql(connectionString).Options;
    await using var peopleDatabase = new AppDbContext(peopleOptions);
    var (added, existing) = await PeopleSeeder.SeedAsync(peopleDatabase, people, CancellationToken.None);
    Console.WriteLine();
    Console.WriteLine($"Staged {added} name(s) for mapping; {existing} were already staged.");
    Console.WriteLine("Map them in Administration, then import the agreements.");
    return 0;
}

var GstinShape = new Regex("^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$", RegexOptions.Compiled);
var TanShape = new Regex("^[A-Z]{4}[0-9]{5}[A-Z]$", RegexOptions.Compiled);
var report = ClientDryRunService.Analyze(workbookPath);
var plan = ImportPlan.Build(report);

Console.WriteLine($"Source          : {plan.SourceFileName}");
Console.WriteLine($"Source SHA-256  : {plan.SourceSha256}");
Console.WriteLine($"Workbook rows   : {plan.SourceRows}");
Console.WriteLine($"Clients to load : {plan.Clients.Count}");
Console.WriteLine($"Rows merged away: {plan.MergedRowCount}");
Console.WriteLine($"GST registrations: {plan.GstRegistrationCount}");
Console.WriteLine();
Console.WriteLine("By category:");
foreach (var group in plan.Clients.GroupBy(item => item.CategoryCode).OrderByDescending(g => g.Count()))
{
    Console.WriteLine($"  {group.Count(),5}  {group.Key}");
}

if (!apply)
{
    Console.WriteLine();
    Console.WriteLine("Dry run only. Nothing was written. Re-run with --apply to import.");
    return 0;
}

if (string.IsNullOrWhiteSpace(connectionString))
{
    Console.Error.WriteLine("A connection string is required to apply. Pass --connection or set ConnectionStrings__PracticeDatabase.");
    return 1;
}

var options = new DbContextOptionsBuilder<AppDbContext>().UseNpgsql(connectionString).Options;
await using var database = new AppDbContext(options);

// Re-running the same workbook must not create a second copy of every client.
if (await database.ImportRuns.AnyAsync(item => item.SourceSha256 == plan.SourceSha256 && item.Status == "Completed"))
{
    Console.Error.WriteLine("This workbook has already been imported successfully. Refusing to import it twice.");
    return 1;
}

var categories = await database.ClientCategories.ToDictionaryAsync(item => item.Code, item => item.Id, StringComparer.Ordinal);
var missing = plan.Clients.Select(item => item.CategoryCode).Distinct(StringComparer.Ordinal)
    .Where(code => !categories.ContainsKey(code)).ToArray();
if (missing.Length > 0)
{
    Console.Error.WriteLine($"Unknown client categories: {string.Join(", ", missing)}");
    return 1;
}

var existingCodes = await database.Clients.Select(item => item.NormalizedClientCode).ToListAsync();
var usedCodes = new HashSet<string>(existingCodes, StringComparer.Ordinal);
var existingGstins = new HashSet<string>(
    await database.GstRegistrations.Select(item => item.Gstin).ToListAsync(), StringComparer.Ordinal);

var now = DateTimeOffset.UtcNow;
var today = DateOnly.FromDateTime(now.UtcDateTime);
var run = new ImportRun
{
    Id = Guid.NewGuid(), SourceFileName = plan.SourceFileName, SourceSha256 = plan.SourceSha256,
    Mode = "Import", Status = "Running", StartedAtUtc = now,
    SourceSizeBytes = new FileInfo(workbookPath).Length
};
database.ImportRuns.Add(run);

await using var transaction = await database.Database.BeginTransactionAsync();
var imported = 0;
var skippedGstins = 0;
var seenTans = new HashSet<string>(StringComparer.Ordinal);

foreach (var planned in plan.Clients)
{
    var code = UniqueCode(planned.ClientCode, usedCodes);
    var client = new Client
    {
        Id = Guid.NewGuid(),
        ClientCode = code,
        NormalizedClientCode = code,
        LegacyCode = planned.LegacyCode,
        DisplayName = planned.DisplayName,
        NormalizedDisplayName = planned.DisplayName.ToUpperInvariant(),
        CategoryId = categories[planned.CategoryCode],
        Pan = planned.Pan,
        Tan = planned.Tan,
        Status = "ACTIVE",
        Notes = planned.BuildNotes(),
        CreatedAtUtc = now,
        UpdatedAtUtc = now
    };
    database.Clients.Add(client);

    // GSTIN is unique across every client, so a value already present is recorded as an issue
    // rather than failing the whole import.
    var primaryAssigned = false;
    foreach (var gstin in planned.Gstins)
    {
        if (!GstinShape.IsMatch(gstin))
        {
            skippedGstins++;
            database.ImportIssues.Add(new ImportIssue
            {
                ImportRunId = run.Id, Severity = "Warning", IssueCode = "GSTIN_MALFORMED",
                Message = "GSTIN does not match the required format and was not attached.",
                RowNumber = planned.SourceRowNumbers[0], ColumnName = "GSTIN"
            });
            continue;
        }

        if (!existingGstins.Add(gstin))
        {
            skippedGstins++;
            database.ImportIssues.Add(new ImportIssue
            {
                ImportRunId = run.Id, Severity = "Warning", IssueCode = "GSTIN_ALREADY_PRESENT",
                Message = "GSTIN already exists on another client and was not attached again.",
                RowNumber = planned.SourceRowNumbers[0], ColumnName = "GSTIN"
            });
            continue;
        }

        database.GstRegistrations.Add(new GstRegistration
        {
            Id = Guid.NewGuid(), ClientId = client.Id, Gstin = gstin,
            StateCode = gstin[..2], RegistrationStatus = "ACTIVE",
            IsPrimary = !primaryAssigned, IsActive = true,
            CreatedAtUtc = now, UpdatedAtUtc = now
        });
        primaryAssigned = true;
    }

    // The workbook carries one TAN per client. Record it as a registration as well as on the
    // client, so a fresh import and a migrated database look the same on screen.
    if (!string.IsNullOrWhiteSpace(planned.Tan) && TanShape.IsMatch(planned.Tan))
    {
        // A TAN belongs to one deductor, so the same TAN against two different PANs is a data
        // problem worth surfacing. It is recorded rather than blocked, per BIZ-003.
        if (!seenTans.Add(planned.Tan))
        {
            database.ImportIssues.Add(new ImportIssue
            {
                ImportRunId = run.Id, Severity = "Warning", IssueCode = "TAN_USED_BY_ANOTHER_CLIENT",
                Message = "This TAN is already recorded against a different client. Confirm which one is correct.",
                RowNumber = planned.SourceRowNumbers[0], ColumnName = "TAN"
            });
        }

        database.TanRegistrations.Add(new TanRegistration
        {
            Id = Guid.NewGuid(), ClientId = client.Id, Tan = planned.Tan,
            IsPrimary = true, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        });
    }

    database.ClientImportResults.Add(new ClientImportResult
    {
        ImportRunId = run.Id,
        SourceRowNumber = planned.SourceRowNumbers[0],
        SourceClientCode = planned.LegacyCode,
        ProposedClientCode = code,
        ClientId = client.Id,
        Outcome = "IMPORTED",
        DataJson = JsonSerializer.Serialize(new
        {
            rows = planned.SourceRowNumbers,
            merged = planned.SourceRowNumbers.Count > 1,
            category = planned.CategoryCode,
            gstins = planned.Gstins.Count,
            previousNames = planned.PreviousNames
        })
    });
    imported++;
}

run.Status = "Completed";
run.CompletedAtUtc = DateTimeOffset.UtcNow;
run.ReportJson = JsonSerializer.Serialize(new
{
    clients = imported,
    mergedRows = plan.MergedRowCount,
    gstRegistrations = plan.GstRegistrationCount - skippedGstins,
    skippedGstins
});

await database.SaveChangesAsync();
await transaction.CommitAsync();

Console.WriteLine();
Console.WriteLine($"Imported {imported} clients from {plan.SourceRows} workbook rows.");
Console.WriteLine($"Import run {run.Id} recorded.");
if (skippedGstins > 0)
{
    Console.WriteLine($"{skippedGstins} GSTIN(s) were already present and were not attached again.");
}
return 0;

static string UniqueCode(string preferred, HashSet<string> used)
{
    var candidate = preferred.Trim().ToUpperInvariant();
    if (used.Add(candidate))
    {
        return candidate;
    }

    for (var suffix = 2; ; suffix++)
    {
        var next = $"{candidate}-{suffix}";
        if (used.Add(next))
        {
            return next;
        }
    }
}

static string? OptionValue(string[] arguments, string option)
{
    var index = Array.IndexOf(arguments, option);
    return index >= 0 && index + 1 < arguments.Length ? arguments[index + 1] : null;
}