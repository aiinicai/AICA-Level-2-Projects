using System.Globalization;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Api.Clients;

// Client codes are a prefix plus a zero-padded serial, for example AKG0001. The prefix belongs to
// the firm and is configurable; the serial is allocated by reading the highest existing number for
// that prefix, so imported clients and clients created in the application share one sequence.
//
// Gaps are never reused. The import merged duplicate workbook rows, which left holes in the
// sequence, and reissuing a retired number would make two different clients share a code in
// anyone's older paperwork.
public static class ClientCodeSequence
{
    public const string SettingKey = "clients.code_prefix";
    public const string DefaultPrefix = "AKG";
    private const int SerialDigits = 4;

    public static async Task<string> GetPrefixAsync(AppDbContext database, CancellationToken cancellationToken)
    {
        var setting = await database.AppSettings.AsNoTracking()
            .SingleOrDefaultAsync(item => item.Key == SettingKey, cancellationToken);
        if (setting is null) return DefaultPrefix;
        try
        {
            return JsonSerializer.Deserialize<string>(setting.ValueJson) ?? DefaultPrefix;
        }
        catch (JsonException)
        {
            return DefaultPrefix;
        }
    }

    public static async Task SetPrefixAsync(
        AppDbContext database, string prefix, DateTimeOffset now, CancellationToken cancellationToken)
    {
        var setting = await database.AppSettings.SingleOrDefaultAsync(item => item.Key == SettingKey, cancellationToken);
        if (setting is null)
        {
            database.AppSettings.Add(new AppSetting
            {
                Key = SettingKey,
                ValueJson = JsonSerializer.Serialize(prefix),
                Description = "Prefix applied to automatically generated client codes.",
                UpdatedAtUtc = now
            });
            return;
        }
        setting.ValueJson = JsonSerializer.Serialize(prefix);
        setting.UpdatedAtUtc = now;
    }

    public static string? ValidatePrefix(string? prefix)
    {
        var value = (prefix ?? string.Empty).Trim();
        if (value.Length is < 2 or > 5) return "The prefix must be 2 to 5 characters.";
        return value.All(char.IsAsciiLetterOrDigit) ? null : "The prefix may contain only letters and numbers.";
    }

    public static async Task<string> NextCodeAsync(AppDbContext database, CancellationToken cancellationToken)
    {
        var prefix = (await GetPrefixAsync(database, cancellationToken)).ToUpperInvariant();
        var existing = await database.Clients.AsNoTracking()
            .Where(item => item.NormalizedClientCode.StartsWith(prefix))
            .Select(item => item.NormalizedClientCode)
            .ToListAsync(cancellationToken);

        var highest = 0;
        foreach (var code in existing)
        {
            var tail = code[prefix.Length..];
            if (tail.Length > 0 && tail.All(char.IsAsciiDigit)
                && int.TryParse(tail, NumberStyles.None, CultureInfo.InvariantCulture, out var serial)
                && serial > highest)
            {
                highest = serial;
            }
        }

        return prefix + (highest + 1).ToString(CultureInfo.InvariantCulture).PadLeft(SerialDigits, '0');
    }
}
