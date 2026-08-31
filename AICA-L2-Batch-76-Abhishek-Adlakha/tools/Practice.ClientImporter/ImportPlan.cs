using System.Text.RegularExpressions;
using Practice.WorkbookProfiler;

namespace Practice.ClientImporter;

// The owner's import decisions, kept as pure rules so the plan can be reviewed and tested without
// a database. Recorded 2026-08-21:
//   * Workbook category FIRM means Partnership Firm, unless the name says LLP or OPC.
//   * Rows sharing a PAN are the same client: either the name changed, or the business is
//     registered for GST in several states. They merge into one client carrying every GSTIN.
//   * Rows sharing only an old code, with different PANs, are different clients that were given
//     the same code by mistake. Both are kept.
//   * A row with no category at all becomes Individual.
//   * When a merged client has two names, the row further down the sheet wins; the earlier name
//     is preserved in the notes rather than discarded.
public static partial class ImportPlan
{
    public static ClientPlan Build(ClientDryRunReport report)
    {
        var groups = new List<PlannedClient>();
        var byPan = new Dictionary<string, PlannedClient>(StringComparer.Ordinal);

        foreach (var row in report.Rows.OrderBy(item => item.RowNumber))
        {
            var pan = Normalize(row.Pan);
            if (pan.Length > 0 && byPan.TryGetValue(pan, out var existing))
            {
                existing.Absorb(row);
                continue;
            }

            var planned = PlannedClient.From(row);
            groups.Add(planned);
            if (pan.Length > 0)
            {
                byPan[pan] = planned;
            }
        }

        return new ClientPlan(report.SourceFileName, report.SourceSha256, report.SourceRows, groups);
    }

    public static string CategoryCodeFor(string? sourceCategory, string? displayName)
    {
        var category = (sourceCategory ?? string.Empty).Trim().ToUpperInvariant();
        var name = (displayName ?? string.Empty).ToUpperInvariant();

        // The name overrides the category: a row labelled FIRM whose name says LLP is an LLP.
        if (LlpPattern().IsMatch(name)) return "LLP";
        if (OpcPattern().IsMatch(name)) return "OPC";

        return category switch
        {
            "INDIVIDUAL" => "INDIVIDUAL",
            "HUF" => "HUF",
            "LLP" => "LLP",
            "OPC" => "OPC",
            "TRUST" => "TRUST",
            "SOCIETY" => "SOCIETY",
            "PVT LTD" or "PRIVATE LIMITED" or "PVT. LTD." => "PRIVATE_LIMITED",
            "PUBLIC LTD" or "PUBLIC LIMITED" => "PUBLIC_LIMITED",
            "PROPRIETORSHIP" or "PROPRIETOR" => "PROPRIETORSHIP",
            "FIRM" => "PARTNERSHIP",
            "" => "INDIVIDUAL",
            _ => "OTHER"
        };
    }

    public static string Normalize(string? value) =>
        string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToUpperInvariant();

    [GeneratedRegex(@"\bLLP\b")]
    private static partial Regex LlpPattern();

    [GeneratedRegex(@"\bOPC\b")]
    private static partial Regex OpcPattern();
}

public sealed record ClientPlan(string SourceFileName, string SourceSha256, int SourceRows, IReadOnlyList<PlannedClient> Clients)
{
    public int MergedRowCount => Clients.Sum(item => item.SourceRowNumbers.Count) - Clients.Count;
    public int GstRegistrationCount => Clients.Sum(item => item.Gstins.Count);
}

public sealed class PlannedClient
{
    public required string ClientCode { get; set; }
    public required string DisplayName { get; set; }
    public string? LegacyCode { get; set; }
    public string? Pan { get; set; }
    public string? Tan { get; set; }
    public string? Email { get; set; }
    public string? Mobile { get; set; }
    public string? Address { get; set; }
    public string? AuthorizedPerson { get; set; }
    public string? SourceGroup { get; set; }
    public required string CategoryCode { get; set; }
    public List<int> SourceRowNumbers { get; } = [];
    public List<string> Gstins { get; } = [];
    public List<string> PreviousNames { get; } = [];

    public static PlannedClient From(ClientImportRow row)
    {
        var planned = new PlannedClient
        {
            ClientCode = row.ProposedClientCode ?? $"ROW-{row.RowNumber}",
            DisplayName = (row.DisplayName ?? $"Client {row.RowNumber}").Trim(),
            LegacyCode = Clean(row.LegacyCode),
            Pan = Clean(row.Pan),
            Tan = ImportPlan.Normalize(row.Tan) is { Length: > 0 } tan ? tan : null,
            Email = Clean(row.Email),
            Mobile = Clean(row.Mobile),
            Address = Clean(row.Address),
            AuthorizedPerson = Clean(row.AuthorizedPerson),
            SourceGroup = Clean(row.SourceGroup),
            CategoryCode = ImportPlan.CategoryCodeFor(row.SourceCategory, row.DisplayName)
        };
        planned.SourceRowNumbers.Add(row.RowNumber);
        planned.AddGstin(row.Gstin);
        return planned;
    }

    // A later row wins the name, because rows are appended over time; the earlier name is kept.
    public void Absorb(ClientImportRow row)
    {
        SourceRowNumbers.Add(row.RowNumber);
        AddGstin(row.Gstin);

        var incoming = (row.DisplayName ?? string.Empty).Trim();
        if (incoming.Length > 0 && !string.Equals(incoming, DisplayName, StringComparison.OrdinalIgnoreCase))
        {
            PreviousNames.Add(DisplayName);
            DisplayName = incoming;
            CategoryCode = ImportPlan.CategoryCodeFor(row.SourceCategory, incoming);
        }

        LegacyCode ??= Clean(row.LegacyCode);
        Tan ??= Clean(row.Tan);
        Email ??= Clean(row.Email);
        Mobile ??= Clean(row.Mobile);
        Address ??= Clean(row.Address);
        AuthorizedPerson ??= Clean(row.AuthorizedPerson);
        SourceGroup ??= Clean(row.SourceGroup);
    }

    public string? BuildNotes()
    {
        var parts = new List<string>();
        if (PreviousNames.Count > 0)
        {
            parts.Add("Previously recorded as: " + string.Join("; ", PreviousNames.Distinct(StringComparer.OrdinalIgnoreCase)));
        }
        if (SourceRowNumbers.Count > 1)
        {
            parts.Add("Merged from workbook rows " + string.Join(", ", SourceRowNumbers));
        }
        return parts.Count == 0 ? null : string.Join(". ", parts) + ".";
    }

    private void AddGstin(string? gstin)
    {
        var value = ImportPlan.Normalize(gstin);
        if (value.Length > 0 && !Gstins.Contains(value, StringComparer.Ordinal))
        {
            Gstins.Add(value);
        }
    }

    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
}
