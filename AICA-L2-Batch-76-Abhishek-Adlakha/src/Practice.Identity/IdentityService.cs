using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Identity;

public sealed class IdentityService(
    AppDbContext database,
    IPasswordHasher<LoginUser> passwordHasher,
    IClock clock)
{
    public async Task<AuthenticationAttempt> AuthenticateAsync(
        string? mobile,
        string? password,
        string? userAgent,
        string? remoteAddress,
        CancellationToken cancellationToken)
    {
        var normalized = CredentialRules.TryNormalizeMobile(mobile, out var normalizedMobile)
            ? normalizedMobile
            : "0000000000";
        var user = await database.Users.SingleOrDefaultAsync(x => x.MobileUsername == normalized, cancellationToken);
        var verification = user is null
            ? VerifyMissingUserPassword(passwordHasher, password)
            : passwordHasher.VerifyHashedPassword(user, user.PasswordHash, password ?? string.Empty);
        var now = clock.UtcNow;

        if (user is null || !user.IsActive || user.LockedUntilUtc > now || verification == PasswordVerificationResult.Failed)
        {
            // The caller still receives one generic failure. The audit trail may distinguish the
            // cause because it is administrator-only and brute-force detection depends on it.
            var outcome = user is null ? "unknown_user"
                : !user.IsActive ? "inactive_account"
                : user.LockedUntilUtc > now ? "locked_out"
                : "invalid_password";
            var lockedNow = false;
            if (user is not null && user.IsActive && user.LockedUntilUtc <= now)
            {
                user.FailedLoginCount++;
                if (user.FailedLoginCount >= IdentityConstants.MaximumFailedLogins)
                {
                    user.LockedUntilUtc = now.Add(IdentityConstants.LockoutDuration);
                    user.FailedLoginCount = 0;
                    lockedNow = true;
                }
                user.UpdatedAtUtc = now;
            }

            // Only the normalised login identifier is recorded. The submitted password must never
            // reach the audit trail, not even when the account does not exist.
            database.AuditEvents.Add(CreateAudit(now, user?.Id, "identity.login_failed", "LoginUser",
                user?.Id.ToString() ?? normalized,
                JsonSerializer.Serialize(new { mobile = normalized, outcome })));
            if (lockedNow)
            {
                database.AuditEvents.Add(CreateAudit(now, user!.Id, "identity.account_locked", "LoginUser",
                    user.Id.ToString(),
                    JsonSerializer.Serialize(new { mobile = normalized, lockedUntilUtc = user.LockedUntilUtc })));
            }
            await database.SaveChangesAsync(cancellationToken);
            return AuthenticationAttempt.Failed;
        }

        if (verification == PasswordVerificationResult.SuccessRehashNeeded)
        {
            user.PasswordHash = passwordHasher.HashPassword(user, password!);
        }

        user.FailedLoginCount = 0;
        user.LockedUntilUtc = null;
        user.LastLoginAtUtc = now;
        user.UpdatedAtUtc = now;

        var rawToken = SessionToken.Create();
        var expires = now.Add(IdentityConstants.SessionDuration);
        database.UserSessions.Add(new UserSession
        {
            Id = Guid.NewGuid(), UserId = user.Id, TokenHash = SessionToken.Hash(rawToken),
            SecurityStamp = user.SecurityStamp, CreatedAtUtc = now, LastSeenAtUtc = now,
            ExpiresAtUtc = expires, UserAgent = Truncate(userAgent, 500), IpHash = HashAddress(remoteAddress)
        });

        database.AuditEvents.Add(CreateAudit(now, user.Id, "identity.login", "LoginUser", user.Id.ToString(), "{}"));
        await database.SaveChangesAsync(cancellationToken);

        var access = await LoadAccessAsync(user.Id, cancellationToken);
        return new AuthenticationAttempt(true, new AuthenticatedSession(
            user.Id, user.MobileUsername, access.DisplayName, user.MustChangePassword,
            rawToken, expires, access.Roles, access.Permissions));
    }

    public async Task<ValidatedSession?> ValidateSessionAsync(
        Guid userId,
        string? rawToken,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(rawToken))
        {
            return null;
        }

        var tokenHash = SessionToken.Hash(rawToken);
        var now = clock.UtcNow;
        var session = await database.UserSessions.Include(x => x.User)
            .SingleOrDefaultAsync(x => x.UserId == userId && x.TokenHash == tokenHash, cancellationToken);
        if (session is null || session.RevokedAtUtc is not null || session.ExpiresAtUtc <= now ||
            !session.User.IsActive || session.SecurityStamp != session.User.SecurityStamp)
        {
            return null;
        }

        if (session.LastSeenAtUtc < now.AddMinutes(-5))
        {
            session.LastSeenAtUtc = now;
            await database.SaveChangesAsync(cancellationToken);
        }

        var access = await LoadAccessAsync(userId, cancellationToken);
        return new ValidatedSession(userId, session.User.MobileUsername, access.DisplayName,
            session.User.MustChangePassword, access.Roles, access.Permissions);
    }

    public async Task RevokeSessionAsync(Guid userId, string? rawToken, string reason, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(rawToken))
        {
            return;
        }
        var tokenHash = SessionToken.Hash(rawToken);
        var session = await database.UserSessions.SingleOrDefaultAsync(
            x => x.UserId == userId && x.TokenHash == tokenHash && x.RevokedAtUtc == null, cancellationToken);
        if (session is null)
        {
            return;
        }
        var revokedAt = clock.UtcNow;
        session.RevokedAtUtc = revokedAt;
        session.RevocationReason = Truncate(reason, 300);
        database.AuditEvents.Add(CreateAudit(revokedAt, userId, "identity.session_revoked", "UserSession",
            session.Id.ToString(), JsonSerializer.Serialize(new { reason = session.RevocationReason })));
        await database.SaveChangesAsync(cancellationToken);
    }

    public async Task<IReadOnlyList<string>> ChangePasswordAsync(
        Guid userId, string currentPassword, string newPassword, CancellationToken cancellationToken)
    {
        var user = await database.Users.SingleAsync(x => x.Id == userId, cancellationToken);
        if (passwordHasher.VerifyHashedPassword(user, user.PasswordHash, currentPassword) == PasswordVerificationResult.Failed)
        {
            return ["Current password is incorrect."];
        }
        var errors = CredentialRules.ValidatePassword(newPassword, user.MobileUsername);
        if (errors.Count > 0)
        {
            return errors;
        }

        var now = clock.UtcNow;
        user.PasswordHash = passwordHasher.HashPassword(user, newPassword);
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        user.MustChangePassword = false;
        user.UpdatedAtUtc = now;
        await database.UserSessions.Where(x => x.UserId == userId && x.RevokedAtUtc == null)
            .ExecuteUpdateAsync(setters => setters
                .SetProperty(x => x.RevokedAtUtc, now)
                .SetProperty(x => x.RevocationReason, "Password changed"), cancellationToken);
        database.AuditEvents.Add(CreateAudit(now, userId, "identity.password_changed", "LoginUser", userId.ToString(), "{}"));
        await database.SaveChangesAsync(cancellationToken);
        return [];
    }

    // Keep the encrypted browser ticket deliberately small. Roles and permissions are
    // reloaded from the database by SessionCookieEvents on every authenticated request.
    public static ClaimsPrincipal CreatePrincipal(AuthenticatedSession session) =>
        new(new ClaimsIdentity(
        [
            new Claim(ClaimTypes.NameIdentifier, session.UserId.ToString()),
            new Claim(IdentityConstants.SessionTokenClaim, session.RawSessionToken)
        ], IdentityConstants.AuthenticationScheme));

    public static ClaimsPrincipal CreatePrincipal(ValidatedSession session, string rawToken) => CreatePrincipal(
        session.UserId, session.MobileUsername, session.DisplayName, session.MustChangePassword,
        rawToken, session.Roles, session.Permissions);

    private static ClaimsPrincipal CreatePrincipal(
        Guid userId, string mobile, string displayName, bool mustChangePassword, string rawToken,
        IReadOnlyList<string> roles, IReadOnlyDictionary<string, string> permissions)
    {
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, userId.ToString()), new(ClaimTypes.Name, displayName),
            new("mobile", mobile), new(IdentityConstants.SessionTokenClaim, rawToken),
            new("must_change_password", mustChangePassword ? "true" : "false")
        };
        claims.AddRange(roles.Select(role => new Claim(ClaimTypes.Role, role)));
        foreach (var permission in permissions)
        {
            claims.Add(new Claim(IdentityConstants.PermissionClaim, permission.Key));
            claims.Add(new Claim(IdentityConstants.ScopeClaimPrefix + permission.Key, permission.Value));
        }
        return new ClaimsPrincipal(new ClaimsIdentity(claims, IdentityConstants.AuthenticationScheme));
    }

    private async Task<(string DisplayName, string[] Roles, Dictionary<string, string> Permissions)> LoadAccessAsync(
        Guid userId, CancellationToken cancellationToken)
    {
        var displayName = await database.Employees.Where(x => x.UserId == userId)
            .Select(x => x.DisplayName).SingleOrDefaultAsync(cancellationToken) ?? "User";
        var roles = await database.UserRoles.Where(x => x.UserId == userId && x.Role.IsActive)
            .Select(x => x.Role.Name).OrderBy(x => x).ToArrayAsync(cancellationToken);
        var permissions = await database.UserRoles.Where(x => x.UserId == userId && x.Role.IsActive)
            .SelectMany(x => x.Role.RolePermissions)
            .Select(x => new { x.Permission.Code, x.ScopeCeiling })
            .ToArrayAsync(cancellationToken);
        return (displayName, roles, permissions.GroupBy(x => x.Code, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => MaximumScope(group.Select(x => x.ScopeCeiling)), StringComparer.Ordinal));
    }

    private static string MaximumScope(IEnumerable<string> scopes)
    {
        var result = "OWN";
        foreach (var scope in scopes)
        {
            if (scope == "ALL") return "ALL";
            if (scope == "TEAM") result = "TEAM";
        }
        return result;
    }

    private static byte[]? HashAddress(string? address) => string.IsNullOrWhiteSpace(address)
        ? null
        : SHA256.HashData(Encoding.UTF8.GetBytes(address));

    private static PasswordVerificationResult VerifyMissingUserPassword(
        IPasswordHasher<LoginUser> passwordHasher, string? password)
    {
        _ = passwordHasher.HashPassword(new LoginUser
        {
            MobileUsername = "0000000000",
            PasswordHash = string.Empty,
            SecurityStamp = string.Empty
        }, password ?? string.Empty);
        return PasswordVerificationResult.Failed;
    }

    private static string? Truncate(string? value, int maximum) => string.IsNullOrEmpty(value)
        ? value
        : value[..Math.Min(value.Length, maximum)];

    public static AuditEvent CreateAudit(DateTimeOffset now, Guid? actorId, string action, string entityType, string entityId, string dataJson) => new()
    {
        Id = Guid.NewGuid(), OccurredAtUtc = now, ActorUserId = actorId, Action = action,
        EntityType = entityType, EntityId = entityId, DataJson = dataJson
    };
}
