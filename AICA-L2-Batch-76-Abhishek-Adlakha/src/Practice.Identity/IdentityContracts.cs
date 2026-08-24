namespace Practice.Identity;

public sealed record AuthenticatedSession(
    Guid UserId,
    string MobileUsername,
    string DisplayName,
    bool MustChangePassword,
    string RawSessionToken,
    DateTimeOffset ExpiresAtUtc,
    IReadOnlyList<string> Roles,
    IReadOnlyDictionary<string, string> Permissions);

public sealed record ValidatedSession(
    Guid UserId,
    string MobileUsername,
    string DisplayName,
    bool MustChangePassword,
    IReadOnlyList<string> Roles,
    IReadOnlyDictionary<string, string> Permissions);

public sealed record AuthenticationAttempt(bool Succeeded, AuthenticatedSession? Session)
{
    public static readonly AuthenticationAttempt Failed = new(false, null);
}

public sealed record BootstrapAdministratorRequest(
    string DisplayName,
    string EmployeeCode,
    string MobileUsername,
    string Password);
