using System.Globalization;

namespace Practice.Identity;

public static class CredentialRules
{
    private static readonly string[] CommonPasswords =
    [
        "password", "password123", "123456789012", "qwerty123456", "admin123456", "welcome12345"
    ];

    public static bool TryNormalizeMobile(string? value, out string normalized)
    {
        normalized = string.Empty;
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        if (value.Any(character => !char.IsAsciiDigit(character) &&
            !char.IsWhiteSpace(character) && character is not ('-' or '(' or ')')))
        {
            return false;
        }

        normalized = string.Concat(value.Where(char.IsAsciiDigit));
        return normalized.Length == 10 && normalized[0] is >= '6' and <= '9';
    }

    public static IReadOnlyList<string> ValidatePassword(string? password, string normalizedMobile)
    {
        var errors = new List<string>();
        if (string.IsNullOrEmpty(password) || password.Length < 12)
        {
            errors.Add("Password must contain at least 12 characters.");
        }
        else if (password.Length > 128)
        {
            errors.Add("Password must not exceed 128 characters.");
        }

        if (!string.IsNullOrEmpty(password) && password.Contains(normalizedMobile, StringComparison.Ordinal))
        {
            errors.Add("Password must not contain the login mobile number.");
        }

        if (!string.IsNullOrEmpty(password) && CommonPasswords.Contains(password.ToLower(CultureInfo.InvariantCulture), StringComparer.Ordinal))
        {
            errors.Add("Password is too common.");
        }

        return errors;
    }
}
