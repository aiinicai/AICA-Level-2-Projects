var repositoryRoot = FindRepositoryRoot(AppContext.BaseDirectory);
var failures = new List<string>();

RequireFile("docs/architecture-blueprint.md");
RequireFile("docs/glossary.md");
RequireFile("docs/security/threat-model.md");
RequireFile("docs/phases/phase-02-identity-access.md");
RequireFile("docs/phases/phase-03-client-registry.md");
RequireFile("docs/phases/phase-04-service-catalogue.md");
RequireFile("docs/phases/phase-05-task-lifecycle.md");
RequireFile("docs/phases/phase-06-recurrence-calendar.md");
RequireFile("docs/phases/phase-07-billing-configuration.md");
RequireFile("docs/phases/phase-08-billing-projection.md");
RequireFile("docs/phases/phase-09-dashboards-reports.md");
RequireFile("docs/phases/phase-11-production-release.md");
RequireFile("docs/phases/phase-13-bulk-client-import.md");
RequireFile("deploy/compose/compose.yml");
RequireFile("deploy/windows-server/Publish-Release.ps1");
RequireFile("deploy/windows-server/Install-PracticeManagement.ps1");
RequireFile("src/Practice.Database/AppDbContext.cs");
RequireFile("src/Practice.Database/Migrations/AppDbContextModelSnapshot.cs");
RequireFile("src/Practice.Billing/BillingRules.cs");
RequireFile("src/Practice.Billing/BillingProjectionCalculator.cs");
RequireFile("src/Practice.Api/Billing/BillingProjectionEndpoints.cs");
RequireFile("src/Practice.Reporting/ReportingRules.cs");
RequireFile("src/Practice.Reporting/TabularExport.cs");
RequireFile("src/Practice.Api/Reporting/ReportingEndpoints.cs");
RequireFile("src/Practice.Api/Audit/AuditEndpoints.cs");
RequireFile("tests/Practice.Api.IntegrationTests/Program.cs");
RequireFile("src/Practice.Api/Import/ImportMappingEndpoints.cs");
RequireFile("tools/Practice.ClientImporter/ImportPlan.cs");
RequireFile("tools/Practice.WorkbookProfiler/WorkbookProfilerService.cs");
RequireFile("tools/Practice.WorkbookProfiler/ClientDryRunService.cs");
RequireFile("tools/Practice.WorkbookProfiler/ServiceDryRunService.cs");

var sourceRoot = Path.Combine(repositoryRoot, "src");
foreach (var sourceFile in Directory.EnumerateFiles(sourceRoot, "*.cs", SearchOption.AllDirectories))
{
    var source = File.ReadAllText(sourceFile);
    if (source.Contains("../Modules/", StringComparison.OrdinalIgnoreCase))
    {
        failures.Add($"Forbidden path-based module dependency in {sourceFile}");
    }
}

foreach (var hostProject in new[] { "src/Practice.Api", "src/Practice.Worker" })
{
    foreach (var sourceFile in Directory.EnumerateFiles(Path.Combine(repositoryRoot, hostProject), "*.cs", SearchOption.AllDirectories))
    {
        if (File.ReadAllText(sourceFile).Contains(".Migrate(", StringComparison.Ordinal))
        {
            failures.Add($"Application host must not perform schema migration at startup: {sourceFile}");
        }
    }
}

var programSource = File.ReadAllText(Path.Combine(repositoryRoot, "src/Practice.Api/Program.cs"));
var diagnosticsMappingIndex = programSource.IndexOf("\"/api/v1/system/diagnostics\"", StringComparison.Ordinal);
if (diagnosticsMappingIndex < 0)
{
    failures.Add("The diagnostics endpoint mapping was not found in Program.cs.");
}
else
{
    var nextMappingIndex = programSource.IndexOf("app.Map", diagnosticsMappingIndex + 1, StringComparison.Ordinal);
    var diagnosticsMappingBlock = nextMappingIndex < 0
        ? programSource[diagnosticsMappingIndex..]
        : programSource[diagnosticsMappingIndex..nextMappingIndex];
    if (!diagnosticsMappingBlock.Contains(".RequireAuthorization(", StringComparison.Ordinal))
    {
        failures.Add("The diagnostics endpoint must require authorization; it must not be reachable anonymously.");
    }
}

var auditSource = File.ReadAllText(Path.Combine(repositoryRoot, "src/Practice.Api/Audit/AuditEndpoints.cs"));
if (!auditSource.Contains("RequireAuthorization(\"password-current\", PermissionCodes.AuditView)", StringComparison.Ordinal))
{
    failures.Add("Audit history endpoints must require the audit.view permission.");
}

// audit.view is seeded without scope support, so the endpoints must not silently filter rows.
// If scope is ever introduced it has to start from the permission seed, not from query code.
if (auditSource.Contains("ApplyClientScope", StringComparison.Ordinal) ||
    auditSource.Contains("ApplyTaskScope", StringComparison.Ordinal))
{
    failures.Add("Audit history must stay unscoped unless audit.view becomes scope-capable in the permission seed.");
}

if (!programSource.Contains("PermissionCodes.AuditView", StringComparison.Ordinal))
{
    failures.Add("The audit.view permission must be registered as an authorization policy in Program.cs.");
}

// UseAntiforgery alone does not reject JSON mutations; the recorded validation failure must
// still be acted on, otherwise every non-form mutation accepts a missing token.
if (!programSource.Contains("IAntiforgeryValidationFeature", StringComparison.Ordinal))
{
    failures.Add("Mutations must reject an invalid antiforgery token for non-form requests.");
}

// Employees created while mapping workbook names must not silently gain a login: employment and
// credential identity are separate, and these people only need to own work.
var importMappingSource = File.ReadAllText(Path.Combine(repositoryRoot, "src/Practice.Api/Import/ImportMappingEndpoints.cs"));
if (importMappingSource.Contains("new LoginUser", StringComparison.Ordinal))
{
    failures.Add("Import mapping must not create login accounts.");
}
if (!importMappingSource.Contains("RequireAuthorization(\"password-current\", PermissionCodes.EmployeesManage)", StringComparison.Ordinal))
{
    failures.Add("Import mapping endpoints must require employees.manage.");
}

var identitySource = File.ReadAllText(Path.Combine(repositoryRoot, "src/Practice.Identity/IdentityService.cs"));
foreach (var action in new[] { "identity.login_failed", "identity.account_locked", "identity.session_revoked" })
{
    if (!identitySource.Contains(action, StringComparison.Ordinal))
    {
        failures.Add($"Significant identity action {action} must be written to the audit trail.");
    }
}

if (failures.Count > 0)
{
    Console.Error.WriteLine("Architecture checks failed:");
    failures.ForEach(failure => Console.Error.WriteLine($"- {failure}"));
    return 1;
}

Console.WriteLine("Architecture foundation checks passed.");
return 0;

void RequireFile(string relativePath)
{
    if (!File.Exists(Path.Combine(repositoryRoot, relativePath)))
    {
        failures.Add($"Required foundation file is missing: {relativePath}");
    }
}

static string FindRepositoryRoot(string startPath)
{
    var directory = new DirectoryInfo(startPath);
    while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "global.json")))
    {
        directory = directory.Parent;
    }

    return directory?.FullName
        ?? throw new InvalidOperationException("Could not locate repository root containing global.json.");
}
