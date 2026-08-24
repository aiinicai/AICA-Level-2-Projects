using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Identity;

public sealed class LocalAccountRecoveryService(
    AppDbContext database,
    IPasswordHasher<LoginUser> passwordHasher,
    IClock clock)
{
    public async Task<IReadOnlyList<string>> ResetPasswordAsync(
        string? mobileUsername,
        string? newPassword,
        CancellationToken cancellationToken)
    {
        if (!CredentialRules.TryNormalizeMobile(mobileUsername, out var mobile))
        {
            return ["A valid 10-digit Indian mobile number is required."];
        }

        var errors = CredentialRules.ValidatePassword(newPassword, mobile);
        if (errors.Count > 0)
        {
            return errors;
        }

        var user = await database.Users.SingleOrDefaultAsync(
            candidate => candidate.MobileUsername == mobile, cancellationToken);
        if (user is null)
        {
            return ["No login account exists for that mobile number."];
        }

        var now = clock.UtcNow;
        await using var transaction = await database.Database.BeginTransactionAsync(cancellationToken);
        user.PasswordHash = passwordHasher.HashPassword(user, newPassword!);
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        user.MustChangePassword = false;
        user.FailedLoginCount = 0;
        user.LockedUntilUtc = null;
        user.UpdatedAtUtc = now;
        await database.UserSessions.Where(session => session.UserId == user.Id && session.RevokedAtUtc == null)
            .ExecuteUpdateAsync(setters => setters
                .SetProperty(session => session.RevokedAtUtc, now)
                .SetProperty(session => session.RevocationReason, "Local password recovery"), cancellationToken);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, user.Id, "identity.password_reset_local",
            "LoginUser", user.Id.ToString(), "{}"));
        await database.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return [];
    }
}
