using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Identity;

public sealed class BootstrapAdministratorService(
    AppDbContext database,
    IPasswordHasher<LoginUser> passwordHasher,
    IClock clock)
{
    public async Task<bool> IsRequiredAsync(CancellationToken cancellationToken) =>
        !await database.Users.AnyAsync(cancellationToken);

    public async Task<IReadOnlyList<string>> BootstrapAsync(
        BootstrapAdministratorRequest request,
        CancellationToken cancellationToken)
    {
        var errors = new List<string>();
        if (!CredentialRules.TryNormalizeMobile(request.MobileUsername, out var mobile))
            errors.Add("A valid 10-digit Indian mobile number is required.");
        if (string.IsNullOrWhiteSpace(request.DisplayName)) errors.Add("Administrator name is required.");
        if (string.IsNullOrWhiteSpace(request.EmployeeCode)) errors.Add("Employee code is required.");
        errors.AddRange(CredentialRules.ValidatePassword(request.Password, mobile));
        if (errors.Count > 0) return errors;

        await using var transaction = await database.Database.BeginTransactionAsync(cancellationToken);
        if (await database.Users.AnyAsync(cancellationToken))
            return ["Bootstrap is disabled because a user account already exists."];

        var now = clock.UtcNow;
        var user = new LoginUser
        {
            Id = Guid.NewGuid(), MobileUsername = mobile, PasswordHash = string.Empty,
            SecurityStamp = Guid.NewGuid().ToString("N"), MustChangePassword = false,
            IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        user.PasswordHash = passwordHasher.HashPassword(user, request.Password);
        var employee = new Employee
        {
            Id = Guid.NewGuid(), UserId = user.Id, EmployeeCode = request.EmployeeCode.Trim(),
            NormalizedEmployeeCode = request.EmployeeCode.Trim().ToUpperInvariant(),
            DisplayName = request.DisplayName.Trim(), MobileNumber = mobile, IsActive = true,
            CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.Users.Add(user);
        database.Employees.Add(employee);
        database.UserRoles.Add(new UserRole
        {
            UserId = user.Id, RoleId = IdentitySeed.AdministratorsRoleId, AssignedAtUtc = now
        });
        database.AuditEvents.Add(IdentityService.CreateAudit(now, user.Id, "identity.bootstrap_administrator",
            "LoginUser", user.Id.ToString(), "{\"role\":\"Administrators\"}"));
        await database.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return [];
    }
}
