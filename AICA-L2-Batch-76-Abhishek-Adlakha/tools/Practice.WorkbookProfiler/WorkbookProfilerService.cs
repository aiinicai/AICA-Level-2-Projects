using System.Globalization;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Xml.Linq;

namespace Practice.WorkbookProfiler;

public sealed partial class WorkbookProfilerService
{
    private static readonly XNamespace SpreadsheetNamespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
    private static readonly XNamespace OfficeRelationshipNamespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
    private static readonly XNamespace PackageRelationshipNamespace = "http://schemas.openxmlformats.org/package/2006/relationships";
    private static readonly string[] AssignmentHeaderTerms = ["ACCOUNTANT", "LEADER", "ITR DATA", "EMPLOYEE", "ASSIGNED", "OWNER"];

    public static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true
    };

    public static WorkbookProfileReport Profile(string workbookPath, IEnumerable<string>? referenceValues = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(workbookPath);
        var extension = Path.GetExtension(workbookPath);
        if (!extension.Equals(".xlsx", StringComparison.OrdinalIgnoreCase) &&
            !extension.Equals(".xlsm", StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Only .xlsx and .xlsm Open XML workbooks are supported.", nameof(workbookPath));
        }

        var fileInfo = new FileInfo(workbookPath);
        if (!fileInfo.Exists)
        {
            throw new FileNotFoundException("Workbook was not found.", workbookPath);
        }

        using var stream = new FileStream(workbookPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        var sha256 = Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
        stream.Position = 0;
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read, leaveOpen: false);

        var sharedStrings = ReadSharedStrings(archive);
        var sheets = ReadSheetDefinitions(archive);
        var normalizedReferences = (referenceValues ?? [])
            .Select(Normalize)
            .Where(value => value.Length > 0)
            .ToHashSet(StringComparer.Ordinal);
        var sheetReports = sheets
            .Select(sheet => ProfileSheet(archive, sheet, sharedStrings, normalizedReferences))
            .ToArray();

        return new WorkbookProfileReport(
            fileInfo.Name,
            fileInfo.Length,
            sha256,
            DateTimeOffset.UtcNow,
            sheetReports,
            sheetReports.Sum(sheet => sheet.DataRowCount),
            sheetReports.Sum(sheet => sheet.Issues.Count));
    }

    public static WorkbookTable ReadTable(string workbookPath, string sheetName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(workbookPath);
        using var stream = new FileStream(workbookPath, FileMode.Open, FileAccess.Read, FileShare.Read);
        using var archive = new ZipArchive(stream, ZipArchiveMode.Read, leaveOpen: false);
        var sharedStrings = ReadSharedStrings(archive);
        var sheet = ReadSheetDefinitions(archive).SingleOrDefault(x => x.Name.Equals(sheetName, StringComparison.OrdinalIgnoreCase))
            ?? throw new InvalidDataException($"Sheet '{sheetName}' was not found.");
        var rows = LoadRequiredXml(archive, sheet.Path).Descendants(SpreadsheetNamespace + "row")
            .Select(row => ReadRow(row, sharedStrings)).Where(row => row.Count > 0).ToArray();
        if (rows.Length == 0) return new WorkbookTable(sheet.Name, [], []);
        var maxColumn = rows.SelectMany(row => row.Keys).DefaultIfEmpty(-1).Max();
        var headers = Enumerable.Range(0, maxColumn + 1).Select(index => rows[0].GetValueOrDefault(index)?.Trim() is { Length: > 0 } header ? header : $"Column {ColumnName(index)}").ToArray();
        var data = rows.Skip(1).Select((row, index) => new WorkbookTableRow(index + 2,
            headers.Select((header, column) => new { header, value = row.GetValueOrDefault(column) })
                .ToDictionary(x => x.header, x => x.value, StringComparer.OrdinalIgnoreCase))).ToArray();
        return new WorkbookTable(sheet.Name, headers, data);
    }

    private static string[] ReadSharedStrings(ZipArchive archive)
    {
        var entry = archive.GetEntry("xl/sharedStrings.xml");
        if (entry is null)
        {
            return [];
        }

        using var entryStream = entry.Open();
        var document = XDocument.Load(entryStream, LoadOptions.None);
        return document.Descendants(SpreadsheetNamespace + "si")
            .Select(item => string.Concat(item.Descendants(SpreadsheetNamespace + "t").Select(text => text.Value)))
            .ToArray();
    }

    private static SheetDefinition[] ReadSheetDefinitions(ZipArchive archive)
    {
        var workbook = LoadRequiredXml(archive, "xl/workbook.xml");
        var relationships = LoadRequiredXml(archive, "xl/_rels/workbook.xml.rels")
            .Descendants(PackageRelationshipNamespace + "Relationship")
            .Where(element => element.Attribute("Id") is not null && element.Attribute("Target") is not null)
            .ToDictionary(
                element => element.Attribute("Id")!.Value,
                element => NormalizeWorksheetPath(element.Attribute("Target")!.Value),
                StringComparer.Ordinal);

        return workbook.Descendants(SpreadsheetNamespace + "sheet")
            .Select(sheet =>
            {
                var name = sheet.Attribute("name")?.Value ?? "Unnamed";
                var relationshipId = sheet.Attribute(OfficeRelationshipNamespace + "id")?.Value
                    ?? throw new InvalidDataException($"Sheet '{name}' has no relationship identifier.");
                return new SheetDefinition(name, relationships[relationshipId]);
            })
            .ToArray();
    }

    private static SheetProfile ProfileSheet(
        ZipArchive archive,
        SheetDefinition sheet,
        IReadOnlyList<string> sharedStrings,
        HashSet<string> normalizedReferences)
    {
        var document = LoadRequiredXml(archive, sheet.Path);
        var rows = document.Descendants(SpreadsheetNamespace + "row")
            .Select(row => ReadRow(row, sharedStrings))
            .Where(row => row.Count > 0)
            .ToArray();

        if (rows.Length == 0)
        {
            return new SheetProfile(sheet.Name, 0, 0, [], []);
        }

        var headerRow = rows[0];
        var maxColumn = rows.SelectMany(row => row.Keys).DefaultIfEmpty(-1).Max();
        var headers = Enumerable.Range(0, maxColumn + 1)
            .Select(index => headerRow.GetValueOrDefault(index)?.Trim() is { Length: > 0 } header
                ? header
                : $"Column {ColumnName(index)}")
            .ToArray();
        var issues = new List<ProfileIssue>();

        for (var columnIndex = 0; columnIndex < headers.Length; columnIndex++)
        {
            if (!headerRow.TryGetValue(columnIndex, out var originalHeader) || string.IsNullOrWhiteSpace(originalHeader))
            {
                issues.Add(new ProfileIssue("Warning", "BlankHeader", sheet.Name, 1, headers[columnIndex], null,
                    "The header cell is blank; a generated column name was assigned."));
            }

            var values = rows.Skip(1)
                .Select((row, index) => new IndexedValue(index + 2, row.GetValueOrDefault(columnIndex)))
                .Where(item => !string.IsNullOrWhiteSpace(item.Value))
                .ToArray();

            foreach (var duplicate in values.GroupBy(item => Normalize(item.Value!), StringComparer.Ordinal)
                         .Where(group => group.Key.Length > 0 && group.Count() > 1)
                         .OrderByDescending(group => group.Count()).ThenBy(group => group.Key, StringComparer.Ordinal)
                         .Take(25))
            {
                issues.Add(new ProfileIssue("Info", "DuplicateValue", sheet.Name, null, headers[columnIndex], duplicate.Key,
                    $"Normalized value occurs {duplicate.Count().ToString(CultureInfo.InvariantCulture)} times (rows {string.Join(", ", duplicate.Take(10).Select(item => item.RowNumber))})."));
            }

            if (normalizedReferences.Count > 0 && IsAssignmentColumn(headers[columnIndex]))
            {
                foreach (var unmatched in values.GroupBy(item => Normalize(item.Value!), StringComparer.Ordinal)
                             .Where(group => group.Key.Length > 0 && !normalizedReferences.Contains(group.Key))
                             .OrderBy(group => group.Key, StringComparer.Ordinal))
                {
                    issues.Add(new ProfileIssue("Warning", "UnmatchedReferenceValue", sheet.Name,
                        unmatched.First().RowNumber, headers[columnIndex], unmatched.First().Value,
                        "Value does not match the supplied normalized reference list."));
                }
            }
        }

        return new SheetProfile(sheet.Name, Math.Max(0, rows.Length - 1), headers.Length, headers, issues);
    }

    private static Dictionary<int, string> ReadRow(XElement row, IReadOnlyList<string> sharedStrings)
    {
        var values = new Dictionary<int, string>();
        foreach (var cell in row.Elements(SpreadsheetNamespace + "c"))
        {
            var reference = cell.Attribute("r")?.Value;
            if (string.IsNullOrWhiteSpace(reference))
            {
                continue;
            }

            var columnIndex = ColumnIndex(reference);
            var cellType = cell.Attribute("t")?.Value;
            string? value;
            if (cellType == "inlineStr")
            {
                value = string.Concat(cell.Descendants(SpreadsheetNamespace + "t").Select(text => text.Value));
            }
            else
            {
                value = cell.Element(SpreadsheetNamespace + "v")?.Value;
                if (cellType == "s" && int.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var sharedIndex))
                {
                    value = sharedIndex >= 0 && sharedIndex < sharedStrings.Count ? sharedStrings[sharedIndex] : value;
                }
            }

            if (value is not null)
            {
                values[columnIndex] = value;
            }
        }

        return values;
    }

    private static XDocument LoadRequiredXml(ZipArchive archive, string path)
    {
        var entry = archive.GetEntry(path) ?? throw new InvalidDataException($"Workbook part '{path}' is missing.");
        using var entryStream = entry.Open();
        return XDocument.Load(entryStream, LoadOptions.None);
    }

    private static string NormalizeWorksheetPath(string target)
    {
        var normalized = target.Replace('\\', '/').TrimStart('/');
        return normalized.StartsWith("xl/", StringComparison.Ordinal) ? normalized : "xl/" + normalized;
    }

    private static bool IsAssignmentColumn(string header)
    {
        var normalized = Normalize(header);
        return AssignmentHeaderTerms.Any(term => normalized.Contains(term, StringComparison.Ordinal));
    }

    private static string Normalize(string value) => WhitespaceRegex().Replace(value.Trim(), " ").ToUpperInvariant();

    private static int ColumnIndex(string cellReference)
    {
        var result = 0;
        foreach (var character in cellReference)
        {
            if (!char.IsAsciiLetter(character))
            {
                break;
            }

            result = (result * 26) + (char.ToUpperInvariant(character) - 'A' + 1);
        }

        return result - 1;
    }

    private static string ColumnName(int index)
    {
        var name = string.Empty;
        for (var value = index + 1; value > 0; value = (value - 1) / 26)
        {
            name = (char)('A' + ((value - 1) % 26)) + name;
        }

        return name;
    }

    [GeneratedRegex(@"\s+")]
    private static partial Regex WhitespaceRegex();

    private sealed record SheetDefinition(string Name, string Path);
    private sealed record IndexedValue(int RowNumber, string? Value);
}

public sealed record WorkbookProfileReport(
    string SourceFileName,
    long SourceSizeBytes,
    string SourceSha256,
    DateTimeOffset ProfiledAtUtc,
    IReadOnlyList<SheetProfile> Sheets,
    int TotalDataRows,
    int TotalIssues);

public sealed record SheetProfile(
    string Name,
    int DataRowCount,
    int ColumnCount,
    IReadOnlyList<string> Headers,
    IReadOnlyList<ProfileIssue> Issues);

public sealed record ProfileIssue(
    string Severity,
    string Code,
    string SheetName,
    int? RowNumber,
    string? ColumnName,
    string? Value,
    string Message);

public sealed record WorkbookTable(string SheetName, IReadOnlyList<string> Headers, IReadOnlyList<WorkbookTableRow> Rows);
public sealed record WorkbookTableRow(int RowNumber, IReadOnlyDictionary<string, string?> Values);
