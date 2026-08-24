using Microsoft.EntityFrameworkCore;
using Practice.Database;
using Practice.Database.Entities;
using Practice.WorkbookProfiler;

namespace Practice.ClientImporter;

// The workbook names people as "Accountant", "Leader" or "ITR Data" free text. Those names have to
// become real employees before agreements can carry an owner, but the API must not read the
// confidential workbook, so the names are staged into import.client_import_mappings here and the
// application only ever edits the staged rows.
public static class PeopleSeeder
{
    public const string SourceField = "EMPLOYEE_NAME";
    public const string TargetType = "EMPLOYEE";

    public static async Task<(int Added, int Existing)> SeedAsync(
        AppDbContext database, ServiceDryRunReport report, CancellationToken cancellationToken)
    {
        var distinct = report.UnresolvedOwnershipReferences
            .GroupBy(item => item.SourceValue.Trim(), StringComparer.OrdinalIgnoreCase)
            .Select(group => new
            {
                Name = group.First().SourceValue.Trim(),
                Columns = group.GroupBy(item => item.SourceColumn, StringComparer.Ordinal)
                    .OrderByDescending(column => column.Count())
                    .Select(column => $"{column.Key} ({column.Count()})")
                    .ToArray()
            })
            .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
            .ToArray();

        var known = await database.ClientImportMappings
            .Where(item => item.SourceField == SourceField)
            .Select(item => item.NormalizedSourceValue)
            .ToListAsync(cancellationToken);
        var seen = new HashSet<string>(known, StringComparer.Ordinal);

        var added = 0;
        foreach (var person in distinct)
        {
            var normalized = person.Name.ToUpperInvariant();
            if (!seen.Add(normalized))
            {
                continue;
            }

            database.ClientImportMappings.Add(new ClientImportMapping
            {
                Id = Guid.NewGuid(),
                SourceField = SourceField,
                SourceValue = person.Name,
                NormalizedSourceValue = normalized,
                TargetType = TargetType,
                TargetId = null,
                IsApproved = false,
                Notes = string.Join(", ", person.Columns),
                UpdatedAtUtc = DateTimeOffset.UtcNow
            });
            added++;
        }

        await database.SaveChangesAsync(cancellationToken);
        return (added, distinct.Length - added);
    }
}
