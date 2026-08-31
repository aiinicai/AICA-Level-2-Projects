using System.Text.RegularExpressions;

namespace Practice.Database;

public static partial class ClientRules
{
    private const string Base36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    public static string NormalizeCode(string value) => CollapseWhitespace().Replace(value.Trim(), "-").ToUpperInvariant();
    public static string NormalizeName(string value) => CollapseWhitespace().Replace(value.Trim(), " ").ToUpperInvariant();
    public static string? NormalizeTaxId(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim().ToUpperInvariant();
    public static bool IsValidPan(string? value) => value is null || PanPattern().IsMatch(value);
    public static bool IsValidTan(string? value) => value is null || TanPattern().IsMatch(value);
    public static bool IsValidGstin(string? value)
    {
        if (value is null || !GstinPattern().IsMatch(value)) return false;
        var factor = 1; var sum = 0;
        for (var index = 0; index < 14; index++) { var product = Base36.IndexOf(value[index]) * factor; sum += product / 36 + product % 36; factor = factor == 2 ? 1 : 2; }
        return value[14] == Base36[(36 - sum % 36) % 36];
    }
    [GeneratedRegex(@"\s+")] private static partial Regex CollapseWhitespace();
    [GeneratedRegex("^[A-Z]{5}[0-9]{4}[A-Z]$")] private static partial Regex PanPattern();
    [GeneratedRegex("^[A-Z]{4}[0-9]{5}[A-Z]$")] private static partial Regex TanPattern();
    [GeneratedRegex("^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")] private static partial Regex GstinPattern();
}
