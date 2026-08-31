using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace Practice.WorkbookProfiler;

public static partial class ServiceDryRunService
{
    private const string Base36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    private static readonly ServiceColumn[] Columns =
    [
        new("A/c", "ACCOUNTS", false), new("ITR", "ITR", false), new("SFT", "SFT", false),
        new("Tax Audit", "TAX_AUDIT", false), new("TDS", "TDS", false), new("TDS Reconcilaiton", "TDS_RECONCILIATION", false),
        new("GST", "GST", true), new("GST Refund", "GST_REFUND", true), new("GSTR9", "GSTR9", true),
        new("Rodtep", "RODTEP", false), new("FLA Return", "FLA_RETURN", false), new("CFO/Internal Audit", "CFO_INTERNAL_AUDIT", false),
        new("LUT", "LUT", true), new("MSME", "MSME", false), new("IEC", "IEC", false), new("Company Tax", "COMPANY_TAX", false),
        new("Professional Tax", "PROFESSIONAL_TAX", false), new("Audit", "AUDIT", false), new("ROC Return", "ROC_RETURN", false),
        new("ROC Register", "ROC_REGISTER", false), new("Transfer Pricing", "TRANSFER_PRICING", false)
    ];
    private static readonly string[] OwnerColumns = ["Accountant", "Leader", "ITR Data"];

    public static ServiceDryRunReport Analyze(string workbookPath)
    {
        var sourceHash = Sha(workbookPath); var table = WorkbookProfilerService.ReadTable(workbookPath, "Master Data");
        var proposals = new List<ServiceAgreementProposal>(); var unknownCells = new List<ServiceTransformIssue>();
        var owners = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
        foreach (var ownerColumn in OwnerColumns) owners[ownerColumn] = new(StringComparer.Ordinal);
        foreach (var row in table.Rows)
        {
            string? V(string key) => row.Values.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value) ? value.Trim() : null;
            var clientCode = V("New code") ?? V("Code"); var gstin = Tax(V("GSTIN"));
            foreach (var ownerColumn in OwnerColumns) { var owner = Sentinel(V(ownerColumn)); if (owner is not null) owners[ownerColumn].Add(owner); }
            foreach (var column in Columns)
            {
                var raw = V(column.Header); var state = EnabledState(raw);
                if (state == CellState.Disabled) continue;
                if (state == CellState.Unknown) { unknownCells.Add(new(row.RowNumber, column.Header, raw, "UNKNOWN_SERVICE_FLAG", "Value is neither an approved enabled nor disabled token.")); continue; }
                var issues = new List<ServiceTransformIssue>();
                if (clientCode is null) issues.Add(new(row.RowNumber, column.Header, raw, "MISSING_CLIENT_CODE", "Client code is required before creating an agreement."));
                string? proposedGstin = null;
                if (column.GstinScoped)
                {
                    if (gstin is null) issues.Add(new(row.RowNumber, column.Header, raw, "GSTIN_SCOPE_REQUIRED", "GST-specific service requires an approved client GSTIN scope."));
                    else if (!ValidGstin(gstin)) issues.Add(new(row.RowNumber, column.Header, raw, "INVALID_GSTIN_SCOPE", "GSTIN must be reconciled before this service can be enrolled."));
                    else proposedGstin = gstin;
                }
                proposals.Add(new(row.RowNumber, clientCode is null ? null : NormalizeCode(clientCode), column.Header, raw, column.ServiceCode, proposedGstin,
                    issues.Count == 0 ? "READY" : "EXCEPTION", V("Accountant"), V("Leader"), V("ITR Data"), issues));
            }
        }
        if (Sha(workbookPath) != sourceHash) throw new InvalidOperationException("Source workbook changed during the service dry-run.");
        return new(Path.GetFileName(workbookPath), sourceHash, DateTimeOffset.UtcNow, table.SheetName, table.Rows.Count, proposals.Count,
            proposals.Count(x => x.Outcome == "READY"), proposals.Count(x => x.Outcome == "EXCEPTION"), unknownCells.Count,
            owners.SelectMany(pair => pair.Value.Select(value => new OwnershipReference(pair.Key, value))).OrderBy(x => x.SourceColumn).ThenBy(x => x.SourceValue).ToArray(),
            unknownCells, proposals);
    }

    private static CellState EnabledState(string? value)
    {
        var normalized = Sentinel(value)?.ToUpperInvariant();
        if (normalized is null || normalized is "NO" or "N" or "FALSE" or "0") return CellState.Disabled;
        if (normalized is "YES" or "Y" or "TRUE" or "1" or "APPLICABLE" or "ACTIVE" or "MONTHLY" or "YEARLY") return CellState.Enabled;
        return CellState.Unknown;
    }
    private static string? Sentinel(string? value) { if (string.IsNullOrWhiteSpace(value)) return null; var normalized = Whitespace().Replace(value.Trim(), " "); return normalized.ToUpperInvariant() is "NA" or "N/A" or "NONE" or "-" ? null : normalized; }
    private static string? Tax(string? value) => Sentinel(value)?.Replace(" ", string.Empty, StringComparison.Ordinal).ToUpperInvariant();
    private static string NormalizeCode(string value) => Whitespace().Replace(value.Trim(), "-").ToUpperInvariant();
    private static bool ValidGstin(string value)
    {
        if (!GstinPattern().IsMatch(value)) return false; var factor = 1; var sum = 0;
        for (var i = 0; i < 14; i++) { var product = Base36.IndexOf(value[i]) * factor; sum += product / 36 + product % 36; factor = factor == 2 ? 1 : 2; }
        return value[14] == Base36[(36 - sum % 36) % 36];
    }
    private static string Sha(string path) { using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
    [GeneratedRegex(@"\s+")] private static partial Regex Whitespace();
    [GeneratedRegex("^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")] private static partial Regex GstinPattern();
    private sealed record ServiceColumn(string Header, string ServiceCode, bool GstinScoped);
    private enum CellState { Disabled, Enabled, Unknown }
}

public sealed record ServiceDryRunReport(string SourceFileName, string SourceSha256, DateTimeOffset GeneratedAtUtc, string SourceSheet,
    int SourceRows, int ProposedAgreementCount, int ReadyAgreementCount, int ExceptionAgreementCount, int UnknownServiceFlagCount,
    IReadOnlyList<OwnershipReference> UnresolvedOwnershipReferences, IReadOnlyList<ServiceTransformIssue> UnknownServiceFlags,
    IReadOnlyList<ServiceAgreementProposal> Proposals);
public sealed record ServiceAgreementProposal(int RowNumber, string? ProposedClientCode, string SourceColumn, string? SourceValue, string ServiceCode, string? ProposedGstin,
    string Outcome, string? SourceAccountant, string? SourceLeader, string? SourceItrData, IReadOnlyList<ServiceTransformIssue> Issues);
public sealed record ServiceTransformIssue(int RowNumber, string ColumnName, string? RawValue, string Code, string Message);
public sealed record OwnershipReference(string SourceColumn, string SourceValue);
