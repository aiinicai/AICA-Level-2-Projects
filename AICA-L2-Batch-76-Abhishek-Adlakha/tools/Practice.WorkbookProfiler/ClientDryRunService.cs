using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Practice.WorkbookProfiler;

public static partial class ClientDryRunService
{
    private const string Base36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";

    public static ClientDryRunReport Analyze(string workbookPath)
    {
        var sourceHash = Sha(workbookPath);
        var table = WorkbookProfilerService.ReadTable(workbookPath, "Master Data");
        var transformed = table.Rows.Select(Transform).ToArray();
        var duplicateCodes = transformed.Where(x => x.ProposedClientCode is not null).GroupBy(x => x.ProposedClientCode!, StringComparer.Ordinal)
            .Where(x => x.Count() > 1).ToDictionary(x => x.Key, x => x.Select(r => r.RowNumber).ToArray(), StringComparer.Ordinal);
        var duplicateLegacyCodes = transformed.Where(x => x.LegacyCode is not null).GroupBy(x => NormalizeCode(x.LegacyCode!), StringComparer.Ordinal)
            .Where(x => x.Count() > 1).ToDictionary(x => x.Key, x => x.Select(r => r.RowNumber).ToArray(), StringComparer.Ordinal);
        var duplicateTaxIds = transformed.SelectMany(x => new[] { (Kind: "PAN", Value: x.Pan, x.RowNumber), (Kind: "GSTIN", Value: x.Gstin, x.RowNumber) })
            .Where(x => x.Value is not null).GroupBy(x => $"{x.Kind}:{x.Value}", StringComparer.Ordinal)
            .Where(x => x.Count() > 1).ToDictionary(x => x.Key, x => x.Select(r => r.RowNumber).ToArray(), StringComparer.Ordinal);
        var rows = transformed.Select(row =>
        {
            var issues = row.Issues.ToList();
            if (row.ProposedClientCode is not null && duplicateCodes.TryGetValue(row.ProposedClientCode, out var codeRows)) issues.Add(new("DUPLICATE_CLIENT_CODE", $"Client code occurs in rows {string.Join(", ", codeRows)}."));
            if (row.LegacyCode is not null && duplicateLegacyCodes.TryGetValue(NormalizeCode(row.LegacyCode), out var legacyRows)) issues.Add(new("DUPLICATE_LEGACY_CODE", $"Legacy code occurs in rows {string.Join(", ", legacyRows)} and must be reconciled."));
            foreach (var tax in new[] { ("PAN", row.Pan), ("GSTIN", row.Gstin) }) if (tax.Item2 is not null && duplicateTaxIds.TryGetValue($"{tax.Item1}:{tax.Item2}", out var taxRows)) issues.Add(new("DUPLICATE_TAX_ID", $"{tax.Item1} occurs in rows {string.Join(", ", taxRows)}; no uniqueness decision was made."));
            return row with { Outcome = issues.Count == 0 ? "READY" : "EXCEPTION", Issues = issues.ToArray() };
        }).ToArray();
        if (Sha(workbookPath) != sourceHash) throw new InvalidOperationException("Source workbook changed during the dry-run.");
        return new ClientDryRunReport(Path.GetFileName(workbookPath), sourceHash, DateTimeOffset.UtcNow, table.SheetName, rows.Length,
            rows.Count(x => x.Outcome == "READY"), rows.Count(x => x.Outcome == "EXCEPTION"), duplicateCodes.Count, duplicateLegacyCodes.Count, duplicateTaxIds.Count, rows);
    }

    private static ClientImportRow Transform(WorkbookTableRow row)
    {
        string? V(string key) => row.Values.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value) ? value.Trim() : null;
        var legacyCode = V("Code"); var proposed = V("New code") ?? legacyCode; var category = V("Category")?.ToUpperInvariant();
        var mapped = category switch { "INDIVIDUAL" => "INDIVIDUAL", "HUF" => "HUF", "LLP" => "LLP", "PVT LTD" or "PRIVATE LIMITED" => "PRIVATE_LIMITED", "TRUST" => "TRUST", "SOCIETY" => "SOCIETY", "PROPRIETORSHIP" => "PROPRIETORSHIP", "PARTNERSHIP" => "PARTNERSHIP", _ => null };
        var pan = Tax(V("PAN")); var tan = Tax(V("TAN")); var gstin = Tax(V("GSTIN")); var issues = new List<ImportIssueDetail>();
        if (proposed is null) issues.Add(new("MISSING_CLIENT_CODE", "Both New code and Code are blank."));
        if (V("Client name") is null) issues.Add(new("MISSING_CLIENT_NAME", "Client name is blank."));
        if (category == "FIRM") issues.Add(new("AMBIGUOUS_FIRM", "Firm must be classified as Partnership, Proprietorship, or Other by an administrator."));
        else if (category is not null && mapped is null) issues.Add(new("UNMAPPED_CATEGORY", $"Category '{category}' has no approved mapping."));
        if (pan is not null && !PanPattern().IsMatch(pan)) issues.Add(new("INVALID_PAN", "PAN shape is invalid."));
        if (tan is not null && !TanPattern().IsMatch(tan)) issues.Add(new("INVALID_TAN", "TAN shape is invalid."));
        if (gstin is not null && !ValidGstin(gstin)) issues.Add(new("INVALID_GSTIN", "GSTIN shape or checksum is invalid."));
        return new(row.RowNumber, proposed is null ? null : NormalizeCode(proposed), legacyCode, V("Client name"), category, mapped, V("Group"), V("Mobile"), V("Email Id *"), V("Authorized Person"), V("Address"), pan, tan, gstin, issues.Count == 0 ? "READY" : "EXCEPTION", issues);
    }

    private static bool ValidGstin(string value)
    {
        if (!GstinPattern().IsMatch(value)) return false; var factor = 1; var sum = 0;
        for (var i = 0; i < 14; i++) { var product = Base36.IndexOf(value[i]) * factor; sum += product / 36 + product % 36; factor = factor == 2 ? 1 : 2; }
        return value[14] == Base36[(36 - sum % 36) % 36];
    }
    private static string NormalizeCode(string value) => Whitespace().Replace(value.Trim(), "-").ToUpperInvariant();
    private static string? Tax(string? value)
    {
        if (string.IsNullOrWhiteSpace(value)) return null;
        var normalized = value.Trim().ToUpperInvariant();
        return normalized is "NA" or "N/A" or "NONE" or "-" or "0" ? null : normalized;
    }
    private static string Sha(string path) { using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
    [GeneratedRegex(@"\s+")] private static partial Regex Whitespace();
    [GeneratedRegex("^[A-Z]{5}[0-9]{4}[A-Z]$")] private static partial Regex PanPattern();
    [GeneratedRegex("^[A-Z]{4}[0-9]{5}[A-Z]$")] private static partial Regex TanPattern();
    [GeneratedRegex("^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")] private static partial Regex GstinPattern();
}

public sealed record ClientDryRunReport(string SourceFileName, string SourceSha256, DateTimeOffset GeneratedAtUtc, string SourceSheet, int SourceRows, int ReadyRows, int ExceptionRows, int DuplicateClientCodeSets, int DuplicateLegacyCodeSets, int DuplicateTaxIdSets, IReadOnlyList<ClientImportRow> Rows);
public sealed record ClientImportRow(int RowNumber, string? ProposedClientCode, string? LegacyCode, string? DisplayName, string? SourceCategory, string? ProposedCategoryCode, string? SourceGroup, string? Mobile, string? Email, string? AuthorizedPerson, string? Address, string? Pan, string? Tan, string? Gstin, string Outcome, IReadOnlyList<ImportIssueDetail> Issues);
public sealed record ImportIssueDetail(string Code, string Message);
