using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using PracticeIdentityConstants = Practice.Identity.IdentityConstants;

namespace Practice.Api.Identity;

public static class IdentityEndpoints
{
    private static readonly string[] RequiredFieldError = ["This field is required by the current field policy."];

    public static IEndpointRouteBuilder MapIdentityEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var auth = endpoints.MapGroup("/api/v1/auth");
        auth.MapGet("/csrf", (HttpContext context, IAntiforgery antiforgery) =>
        {
            var tokens = antiforgery.GetAndStoreTokens(context);
            return Results.Ok(new { token = tokens.RequestToken });
        });
        auth.MapGet("/status", async (BootstrapAdministratorService bootstrap, CancellationToken cancellationToken) =>
            Results.Ok(new { bootstrapRequired = await bootstrap.IsRequiredAsync(cancellationToken), loginUsername = "10-digit mobile number" }));
        auth.MapPost("/login", LoginAsync).RequireRateLimiting("login").WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        auth.MapPost("/logout", LogoutAsync).RequireAuthorization().WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        auth.MapGet("/me", Me).RequireAuthorization();
        auth.MapPost("/change-password", ChangePasswordAsync).RequireAuthorization().WithMetadata(new RequireAntiforgeryTokenAttribute(true));

        var admin = endpoints.MapGroup("/api/v1/admin").RequireAuthorization("password-current");
        admin.MapGet("/employees", ListEmployeesAsync).RequireAuthorization(PermissionCodes.EmployeesView);
        admin.MapPost("/employees", CreateEmployeeAsync).RequireAuthorization(PermissionCodes.EmployeesManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapPut("/employees/{id:guid}", UpdateEmployeeAsync).RequireAuthorization(PermissionCodes.EmployeesManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapPost("/users/{userId:guid}/password", ResetUserPasswordAsync).RequireAuthorization(PermissionCodes.UsersManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapGet("/departments", ListDepartmentsAsync).RequireAuthorization(PermissionCodes.EmployeesView);
        admin.MapPost("/users/{userId:guid}/status", ChangeUserStatusAsync).RequireAuthorization(PermissionCodes.UsersManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapGet("/roles", ListRolesAsync).RequireAuthorization(PermissionCodes.RolesView);
        admin.MapPost("/roles", CreateRoleAsync).RequireAuthorization(PermissionCodes.RolesManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapPut("/roles/{roleId:guid}/permissions", SetRolePermissionsAsync).RequireAuthorization(PermissionCodes.RolesManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapGet("/permissions", ListPermissionsAsync).RequireAuthorization(PermissionCodes.RolesView);
        admin.MapGet("/field-policies", ListFieldPoliciesAsync).RequireAuthorization();
        admin.MapPut("/field-policies/{entityType}/{fieldKey}", UpdateFieldPolicyAsync)
            .RequireAuthorization(PermissionCodes.FieldPoliciesManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        admin.MapGet("/teams", ListTeamsAsync).RequireAuthorization(PermissionCodes.EmployeesView);
        admin.MapPost("/teams", CreateTeamAsync).RequireAuthorization(PermissionCodes.TeamsManage).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> LoginAsync(
        LoginRequest request,
        HttpContext context,
        IdentityService identityService,
        CancellationToken cancellationToken)
    {
        var attempt = await identityService.AuthenticateAsync(request.MobileNumber, request.Password,
            context.Request.Headers.UserAgent.ToString(), context.Connection.RemoteIpAddress?.ToString(), cancellationToken);
        if (!attempt.Succeeded || attempt.Session is null)
        {
            return Results.Problem(statusCode: StatusCodes.Status401Unauthorized,
                title: "Login failed", detail: "The mobile number or password is invalid, or the account is unavailable.");
        }

        await context.SignInAsync(PracticeIdentityConstants.AuthenticationScheme,
            IdentityService.CreatePrincipal(attempt.Session), new AuthenticationProperties
            {
                IsPersistent = false, AllowRefresh = false, ExpiresUtc = attempt.Session.ExpiresAtUtc
            });
        return Results.Ok(ToSessionResponse(attempt.Session.UserId, attempt.Session.MobileUsername,
            attempt.Session.DisplayName, attempt.Session.MustChangePassword, attempt.Session.Roles, attempt.Session.Permissions));
    }

    private static async Task<IResult> LogoutAsync(HttpContext context, IdentityService identityService, CancellationToken cancellationToken)
    {
        var userId = RequiredUserId(context.User);
        await identityService.RevokeSessionAsync(userId,
            context.User.FindFirstValue(PracticeIdentityConstants.SessionTokenClaim), "User logout", cancellationToken);
        await context.SignOutAsync(PracticeIdentityConstants.AuthenticationScheme);
        return Results.NoContent();
    }

    private static IResult Me(ClaimsPrincipal principal)
    {
        var permissions = principal.FindAll(PracticeIdentityConstants.PermissionClaim)
            .Select(claim => claim.Value)
            .Distinct(StringComparer.Ordinal)
            .ToDictionary(code => code, code => principal.FindFirstValue(PracticeIdentityConstants.ScopeClaimPrefix + code) ?? "OWN", StringComparer.Ordinal);
        return Results.Ok(ToSessionResponse(RequiredUserId(principal), principal.FindFirstValue("mobile") ?? string.Empty,
            principal.Identity?.Name ?? "User", principal.FindFirstValue("must_change_password") == "true",
            principal.FindAll(ClaimTypes.Role).Select(x => x.Value).ToArray(), permissions));
    }

    private static async Task<IResult> ChangePasswordAsync(
        ChangePasswordRequest request, HttpContext context, IdentityService identityService, CancellationToken cancellationToken)
    {
        var errors = await identityService.ChangePasswordAsync(RequiredUserId(context.User), request.CurrentPassword,
            request.NewPassword, cancellationToken);
        if (errors.Count > 0) return Results.ValidationProblem(new Dictionary<string, string[]> { ["password"] = errors.ToArray() });
        await context.SignOutAsync(PracticeIdentityConstants.AuthenticationScheme);
        return Results.NoContent();
    }

    private static async Task<IResult> ListEmployeesAsync(AppDbContext database, CancellationToken cancellationToken)
    {
        var employees = await database.Employees.AsNoTracking().OrderBy(x => x.DisplayName)
            .Select(x => new
            {
                x.Id, x.EmployeeCode, x.DisplayName, x.Email, x.MobileNumber, x.Designation, x.Department,
                x.ManagerEmployeeId, x.IsActive, x.UserId, x.JoinedOn,
                accountActive = x.User != null && x.User.IsActive,
                roles = x.User == null ? Array.Empty<string>() : x.User.UserRoles.Select(userRole => userRole.Role.Name).OrderBy(name => name).ToArray()
            }).ToArrayAsync(cancellationToken);
        return Results.Ok(employees);
    }

    private static async Task<IResult> CreateEmployeeAsync(
        CreateEmployeeRequest request,
        HttpContext context,
        AppDbContext database,
        IPasswordHasher<LoginUser> passwordHasher,
        IClock clock,
        CancellationToken cancellationToken)
    {
        var validation = await ValidateEmployeeAsync(request, database, cancellationToken);
        if (validation.Count > 0) return Results.ValidationProblem(validation);
        CredentialRules.TryNormalizeMobile(request.MobileNumber, out var mobile);
        var passwordErrors = CredentialRules.ValidatePassword(request.TemporaryPassword, mobile);
        if (passwordErrors.Count > 0) return Results.ValidationProblem(new Dictionary<string, string[]> { ["temporaryPassword"] = passwordErrors.ToArray() });
        if (await database.Users.AnyAsync(x => x.MobileUsername == mobile, cancellationToken))
            return Results.Conflict(new { message = "That mobile number already has a login account." });

        var roles = await database.Roles.Where(x => request.RoleIds.Contains(x.Id) && x.IsActive).ToArrayAsync(cancellationToken);
        if (roles.Length != request.RoleIds.Distinct().Count())
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["roleIds"] = ["One or more roles are invalid or inactive."] });

        var now = clock.UtcNow;
        var actorId = RequiredUserId(context.User);
        var user = new LoginUser
        {
            Id = Guid.NewGuid(), MobileUsername = mobile, PasswordHash = string.Empty,
            SecurityStamp = Guid.NewGuid().ToString("N"), MustChangePassword = true,
            IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        user.PasswordHash = passwordHasher.HashPassword(user, request.TemporaryPassword);
        var employee = new Employee
        {
            Id = Guid.NewGuid(), UserId = user.Id, EmployeeCode = request.EmployeeCode.Trim(),
            NormalizedEmployeeCode = request.EmployeeCode.Trim().ToUpperInvariant(), DisplayName = request.DisplayName.Trim(),
            Email = NullIfWhiteSpace(request.Email), MobileNumber = mobile, Designation = NullIfWhiteSpace(request.Designation),
            Department = NullIfWhiteSpace(request.Department), ManagerEmployeeId = request.ManagerEmployeeId,
            JoinedOn = request.JoinedOn, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.Users.Add(user);
        database.Employees.Add(employee);
        database.UserRoles.AddRange(roles.Select(role => new UserRole
        {
            UserId = user.Id, RoleId = role.Id, AssignedAtUtc = now, AssignedByUserId = actorId
        }));
        database.AuditEvents.Add(IdentityService.CreateAudit(now, actorId, "employees.created", "Employee", employee.Id.ToString(),
            JsonSerializer.Serialize(new { employee.EmployeeCode, employee.DisplayName, roles = roles.Select(x => x.Code) })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/admin/employees/{employee.Id}", new
        {
            employee.Id, employee.EmployeeCode, employee.DisplayName, UserId = user.Id
        });
    }

    // An administrator issuing a new temporary password is a credential action, not an employment
    // one, so it sits behind identity.users.manage. Every existing session is revoked and the user
    // must choose their own password before doing anything else; the value is never logged.
    private static async Task<IResult> ResetUserPasswordAsync(
        Guid userId, ResetUserPasswordRequest request, HttpContext context, AppDbContext database,
        IPasswordHasher<LoginUser> passwordHasher, IClock clock, CancellationToken cancellationToken)
    {
        var user = await database.Users.SingleOrDefaultAsync(x => x.Id == userId, cancellationToken);
        if (user is null) return Results.NotFound();

        var errors = CredentialRules.ValidatePassword(request.TemporaryPassword ?? string.Empty, user.MobileUsername);
        if (errors.Count > 0)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["temporaryPassword"] = errors.ToArray() });
        }

        var now = clock.UtcNow;
        user.PasswordHash = passwordHasher.HashPassword(user, request.TemporaryPassword!);
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        user.MustChangePassword = true;
        user.FailedLoginCount = 0;
        user.LockedUntilUtc = null;
        user.UpdatedAtUtc = now;

        await database.UserSessions.Where(x => x.UserId == userId && x.RevokedAtUtc == null)
            .ExecuteUpdateAsync(setters => setters
                .SetProperty(x => x.RevokedAtUtc, now)
                .SetProperty(x => x.RevocationReason, "Password reset by administrator"), cancellationToken);

        database.AuditEvents.Add(IdentityService.CreateAudit(now, RequiredUserId(context.User),
            "identity.password_reset_by_administrator", "LoginUser", user.Id.ToString(),
            JsonSerializer.Serialize(new { mobile = user.MobileUsername, mustChangePassword = true })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    // Departments are free text rather than a master list, so the form offers what is already in
    // use and still lets a new one be typed. That avoids a migration for what is a naming habit.
    private static async Task<IResult> ListDepartmentsAsync(AppDbContext database, CancellationToken cancellationToken) =>
        Results.Ok(await database.Employees.AsNoTracking()
            .Where(x => x.Department != null && x.Department != "")
            .Select(x => x.Department!).Distinct().OrderBy(x => x).ToArrayAsync(cancellationToken));

    // Employment details change over time: people are promoted, change department, and get a new
    // number. Editing the employee never touches the login account; the mobile used to sign in is
    // the LoginUser's, and changing it is a separate, credential-level action.
    private static async Task<IResult> UpdateEmployeeAsync(
        Guid id, UpdateEmployeeRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var employee = await database.Employees.SingleOrDefaultAsync(x => x.Id == id, cancellationToken);
        if (employee is null) return Results.NotFound();

        var errors = new Dictionary<string, string[]>(StringComparer.Ordinal);
        var displayName = (request.DisplayName ?? string.Empty).Trim();
        if (displayName.Length is < 2 or > 200) errors["displayName"] = ["Employee name must contain 2 to 200 characters."];

        var employeeCode = (request.EmployeeCode ?? string.Empty).Trim();
        if (employeeCode.Length is < 1 or > 30) errors["employeeCode"] = ["Employee code must contain 1 to 30 characters."];
        var normalizedCode = employeeCode.ToUpperInvariant();
        if (normalizedCode.Length > 0 && await database.Employees.AnyAsync(x => x.NormalizedEmployeeCode == normalizedCode && x.Id != id, cancellationToken))
            errors["employeeCode"] = ["Employee code already exists."];

        var mobile = string.IsNullOrWhiteSpace(request.MobileNumber) ? null : request.MobileNumber.Trim();
        if (mobile is not null && !CredentialRules.TryNormalizeMobile(mobile, out mobile))
            errors["mobileNumber"] = ["Enter a valid 10-digit Indian mobile number, or leave it blank."];

        if (request.ManagerEmployeeId == id) errors["managerEmployeeId"] = ["An employee cannot manage themselves."];
        if (request.ManagerEmployeeId is { } managerId && !await database.Employees.AnyAsync(x => x.Id == managerId, cancellationToken))
            errors["managerEmployeeId"] = ["Choose an existing employee as the manager."];

        if (errors.Count > 0) return Results.ValidationProblem(errors);

        var now = clock.UtcNow;
        var changed = new List<string>();
        if (employee.DisplayName != displayName) changed.Add("displayName");
        if (employee.NormalizedEmployeeCode != normalizedCode) changed.Add("employeeCode");
        if (employee.MobileNumber != mobile) changed.Add("mobileNumber");
        if (employee.Email != NullIfWhiteSpace(request.Email)) changed.Add("email");
        if (employee.Designation != NullIfWhiteSpace(request.Designation)) changed.Add("designation");
        if (employee.Department != NullIfWhiteSpace(request.Department)) changed.Add("department");
        if (employee.ManagerEmployeeId != request.ManagerEmployeeId) changed.Add("managerEmployeeId");
        if (employee.JoinedOn != request.JoinedOn) changed.Add("joinedOn");
        if (employee.IsActive != request.IsActive) changed.Add("isActive");

        employee.DisplayName = displayName;
        employee.EmployeeCode = employeeCode;
        employee.NormalizedEmployeeCode = normalizedCode;
        employee.MobileNumber = mobile;
        employee.Email = NullIfWhiteSpace(request.Email);
        employee.Designation = NullIfWhiteSpace(request.Designation);
        employee.Department = NullIfWhiteSpace(request.Department);
        employee.ManagerEmployeeId = request.ManagerEmployeeId;
        employee.JoinedOn = request.JoinedOn;
        employee.IsActive = request.IsActive;
        employee.UpdatedAtUtc = now;

        database.AuditEvents.Add(IdentityService.CreateAudit(now, RequiredUserId(context.User), "employees.updated", "Employee", employee.Id.ToString(),
            JsonSerializer.Serialize(new { employee.EmployeeCode, employee.DisplayName, changed })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<Dictionary<string, string[]>> ValidateEmployeeAsync(
        CreateEmployeeRequest request, AppDbContext database, CancellationToken cancellationToken)
    {
        var values = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["employeeCode"] = request.EmployeeCode, ["displayName"] = request.DisplayName,
            ["mobileNumber"] = request.MobileNumber, ["email"] = request.Email,
            ["designation"] = request.Designation, ["department"] = request.Department,
            ["joinedOn"] = request.JoinedOn?.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture)
        };
        var required = await database.FieldDefinitions.AsNoTracking()
            .Where(x => x.EntityType == "employees.employee" && x.IsActive && x.IsAdministratorRequired)
            .Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var errors = required.Where(key => !values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value))
            .ToDictionary(key => key, static _ => RequiredFieldError, StringComparer.Ordinal);
        if (!CredentialRules.TryNormalizeMobile(request.MobileNumber, out _))
            errors["mobileNumber"] = ["Enter a valid 10-digit Indian mobile number."];
        var normalizedEmployeeCode = request.EmployeeCode.Trim().ToUpperInvariant();
        if (await database.Employees.AnyAsync(x => x.NormalizedEmployeeCode == normalizedEmployeeCode, cancellationToken))
            errors["employeeCode"] = ["Employee code already exists."];
        return errors;
    }

    private static async Task<IResult> ChangeUserStatusAsync(
        Guid userId, ChangeUserStatusRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var actorId = RequiredUserId(context.User);
        if (userId == actorId && !request.IsActive) return Results.BadRequest(new { message = "You cannot disable your own account." });
        var user = await database.Users.SingleOrDefaultAsync(x => x.Id == userId, cancellationToken);
        if (user is null) return Results.NotFound();
        if (!request.IsActive)
        {
            var isAdministrator = await database.UserRoles.AnyAsync(x => x.UserId == userId && x.RoleId == IdentitySeed.AdministratorsRoleId, cancellationToken);
            if (isAdministrator)
            {
                var activeAdministratorCount = await database.UserRoles.CountAsync(x => x.RoleId == IdentitySeed.AdministratorsRoleId && x.User.IsActive, cancellationToken);
                if (activeAdministratorCount <= 1) return Results.BadRequest(new { message = "The last active administrator cannot be disabled." });
            }
        }
        var now = clock.UtcNow;
        user.IsActive = request.IsActive;
        user.SecurityStamp = Guid.NewGuid().ToString("N");
        user.UpdatedAtUtc = now;
        await database.UserSessions.Where(x => x.UserId == userId && x.RevokedAtUtc == null)
            .ExecuteUpdateAsync(setters => setters.SetProperty(x => x.RevokedAtUtc, now)
                .SetProperty(x => x.RevocationReason, "Account status changed"), cancellationToken);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, actorId, request.IsActive ? "identity.user_enabled" : "identity.user_disabled",
            "LoginUser", user.Id.ToString(), JsonSerializer.Serialize(new { request.IsActive, request.Reason })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListRolesAsync(AppDbContext database, CancellationToken cancellationToken) => Results.Ok(
        await database.Roles.AsNoTracking().OrderBy(x => x.Name).Select(x => new
        {
            x.Id, x.Code, x.Name, x.Description, x.IsSystem, x.IsProtected, x.IsActive,
            permissions = x.RolePermissions.OrderBy(rp => rp.Permission.Code).Select(rp => new { rp.Permission.Code, rp.ScopeCeiling }).ToArray()
        }).ToArrayAsync(cancellationToken));

    private static async Task<IResult> CreateRoleAsync(
        CreateRoleRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var name = request.Name.Trim();
        var code = string.Concat(name.ToUpperInvariant().Select(character => char.IsAsciiLetterOrDigit(character) ? character : '_')).Trim('_');
        if (name.Length is < 2 or > 100 || code.Length is < 2 or > 50)
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["name"] = ["Role name must contain 2 to 100 usable characters."] });
        if (await database.Roles.AnyAsync(x => x.Code == code || x.Name == name, cancellationToken)) return Results.Conflict(new { message = "Role already exists." });
        var now = clock.UtcNow;
        var role = new Role
        {
            Id = Guid.NewGuid(), Code = code, Name = name, Description = request.Description.Trim(),
            IsSystem = false, IsProtected = false, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.Roles.Add(role);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, RequiredUserId(context.User), "identity.role_created", "Role", role.Id.ToString(), JsonSerializer.Serialize(new { role.Code, role.Name })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/admin/roles/{role.Id}", new { role.Id, role.Code, role.Name });
    }

    private static async Task<IResult> SetRolePermissionsAsync(
        Guid roleId, SetRolePermissionsRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var role = await database.Roles.SingleOrDefaultAsync(x => x.Id == roleId, cancellationToken);
        if (role is null) return Results.NotFound();
        if (role.IsProtected) return Results.BadRequest(new { message = "Permissions of the protected Administrators role cannot be reduced." });
        if (request.Permissions.Any(x => x.Scope is not ("OWN" or "TEAM" or "ALL")))
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["permissions"] = ["Scope must be OWN, TEAM, or ALL."] });
        var ids = request.Permissions.Select(x => x.PermissionId).Distinct().ToArray();
        var permissions = await database.Permissions.Where(x => ids.Contains(x.Id)).ToArrayAsync(cancellationToken);
        if (permissions.Length != ids.Length) return Results.ValidationProblem(new Dictionary<string, string[]> { ["permissions"] = ["Unknown permission identifier."] });
        await database.RolePermissions.Where(x => x.RoleId == roleId).ExecuteDeleteAsync(cancellationToken);
        database.RolePermissions.AddRange(request.Permissions.GroupBy(x => x.PermissionId).Select(group => new RolePermissionGrant
        {
            RoleId = roleId, PermissionId = group.Key, ScopeCeiling = group.First().Scope
        }));
        var now = clock.UtcNow;
        role.UpdatedAtUtc = now;
        var affectedUsers = database.UserRoles.Where(x => x.RoleId == roleId).Select(x => x.UserId);
        await database.UserSessions.Where(x => affectedUsers.Contains(x.UserId) && x.RevokedAtUtc == null)
            .ExecuteUpdateAsync(setters => setters.SetProperty(x => x.RevokedAtUtc, now)
                .SetProperty(x => x.RevocationReason, "Role permissions changed"), cancellationToken);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, RequiredUserId(context.User), "identity.role_permissions_changed", "Role", role.Id.ToString(), JsonSerializer.Serialize(request.Permissions)));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListPermissionsAsync(AppDbContext database, CancellationToken cancellationToken) => Results.Ok(
        await database.Permissions.AsNoTracking().OrderBy(x => x.Module).ThenBy(x => x.Code).Select(x => new { x.Id, x.Code, x.Module, x.Action, x.Description, x.SupportsScope }).ToArrayAsync(cancellationToken));

    private static async Task<IResult> ListFieldPoliciesAsync(AppDbContext database, CancellationToken cancellationToken) => Results.Ok(
        await database.FieldDefinitions.AsNoTracking().OrderBy(x => x.EntityType).ThenBy(x => x.Label).ToArrayAsync(cancellationToken));

    private static async Task<IResult> UpdateFieldPolicyAsync(
        string entityType, string fieldKey, UpdateFieldPolicyRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var field = await database.FieldDefinitions.SingleOrDefaultAsync(x => x.EntityType == entityType && x.FieldKey == fieldKey, cancellationToken);
        if (field is null) return Results.NotFound();
        if (field.IsSystemRequired && !request.IsRequired) return Results.BadRequest(new { message = "System-required fields cannot be made optional." });
        field.IsAdministratorRequired = request.IsRequired;
        field.UpdatedAtUtc = clock.UtcNow;
        field.UpdatedByUserId = RequiredUserId(context.User);
        database.AuditEvents.Add(IdentityService.CreateAudit(clock.UtcNow, field.UpdatedByUserId, "system.field_policy_changed", "FieldDefinition", $"{entityType}/{fieldKey}", JsonSerializer.Serialize(new { request.IsRequired })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    private static async Task<IResult> ListTeamsAsync(AppDbContext database, CancellationToken cancellationToken) => Results.Ok(
        await database.Teams.AsNoTracking().OrderBy(x => x.Name).Select(x => new { x.Id, x.Code, x.Name, x.ManagerEmployeeId, x.IsActive, memberCount = x.Memberships.Count(m => m.ValidTo == null) }).ToArrayAsync(cancellationToken));

    private static async Task<IResult> CreateTeamAsync(
        CreateTeamRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var code = request.Code.Trim().ToUpperInvariant();
        var name = request.Name.Trim();
        if (string.IsNullOrWhiteSpace(code) || string.IsNullOrWhiteSpace(name)) return Results.ValidationProblem(new Dictionary<string, string[]> { ["team"] = ["Team code and name are required."] });
        if (await database.Teams.AnyAsync(x => x.Code == code || x.Name == name, cancellationToken)) return Results.Conflict(new { message = "Team code or name already exists." });
        var now = clock.UtcNow;
        var team = new Team { Id = Guid.NewGuid(), Code = code, Name = name, ManagerEmployeeId = request.ManagerEmployeeId, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now };
        database.Teams.Add(team);
        database.AuditEvents.Add(IdentityService.CreateAudit(now, RequiredUserId(context.User), "employees.team_created", "Team", team.Id.ToString(), JsonSerializer.Serialize(new { team.Code, team.Name })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/admin/teams/{team.Id}", new { team.Id, team.Code, team.Name });
    }

    private static Guid RequiredUserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static string? NullIfWhiteSpace(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static object ToSessionResponse(Guid id, string mobile, string name, bool mustChangePassword, IReadOnlyList<string> roles, IReadOnlyDictionary<string, string> permissions) =>
        new { id, mobileNumber = mobile, displayName = name, mustChangePassword, roles, permissions };
}

public sealed record LoginRequest(string MobileNumber, string Password);
public sealed record ChangePasswordRequest(string CurrentPassword, string NewPassword);
public sealed record CreateEmployeeRequest(string EmployeeCode, string DisplayName, string MobileNumber, string TemporaryPassword,
    Guid[] RoleIds, string? Email, string? Designation, string? Department, Guid? ManagerEmployeeId, DateOnly? JoinedOn);
public sealed record ChangeUserStatusRequest(bool IsActive, string Reason);
public sealed record CreateRoleRequest(string Name, string Description);
public sealed record PermissionAssignment(Guid PermissionId, string Scope);
public sealed record SetRolePermissionsRequest(PermissionAssignment[] Permissions);
public sealed record UpdateFieldPolicyRequest(bool IsRequired);
public sealed record CreateTeamRequest(string Code, string Name, Guid? ManagerEmployeeId);
public sealed record UpdateEmployeeRequest(string? EmployeeCode, string? DisplayName, string? MobileNumber, string? Email,
    string? Designation, string? Department, Guid? ManagerEmployeeId, DateOnly? JoinedOn, bool IsActive);
public sealed record ResetUserPasswordRequest(string? TemporaryPassword);
