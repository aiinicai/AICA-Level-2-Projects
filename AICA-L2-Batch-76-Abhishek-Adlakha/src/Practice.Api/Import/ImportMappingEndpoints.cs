using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;

namespace Practice.Api.Import;

// Mapping workbook owner names to employees is administrative setup, not day-to-day business, so
// it sits behind employees.manage: every action here either assigns or creates an employee. The
// names themselves are staged by the import tool; this module never reads the workbook.
public static class ImportMappingEndpoints
{
    private const string SourceField = "EMPLOYEE_NAME";
    private const string TargetType = "EMPLOYEE";

    public static IEndpointRouteBuilder MapImportMappingEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var group = endpoints.MapGroup("/api/v1/admin/import/people")
            .RequireAuthorization("password-current", PermissionCodes.EmployeesManage);
        group.MapGet("", ListAsync);
        group.MapPut("/{id:guid}", AssignAsync).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        group.MapPost("/{id:guid}/employee", CreateAndAssignAsync).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> ListAsync(AppDbContext database, CancellationToken cancellationToken)
    {
        var mappings = await database.ClientImportMappings.AsNoTracking()
            .Where(item => item.SourceField == SourceField)
            .OrderBy(item => item.TargetId != null).ThenBy(item => item.SourceValue)
            .Select(item => new
            {
                item.Id,
                name = item.SourceValue,
                usedIn = item.Notes,
                employeeId = item.TargetId,
                item.IsApproved
            })
            .ToArrayAsync(cancellationToken);

        var employeeIds = mappings.Where(item => item.employeeId != null).Select(item => item.employeeId!.Value).ToArray();
        var names = await database.Employees.AsNoTracking()
            .Where(item => employeeIds.Contains(item.Id))
            .ToDictionaryAsync(item => item.Id, item => item.DisplayName, cancellationToken);

        var employees = await database.Employees.AsNoTracking()
            .Where(item => item.IsActive)
            .OrderBy(item => item.DisplayName)
            .Select(item => new { item.Id, item.EmployeeCode, item.DisplayName, hasLogin = item.UserId != null })
            .ToArrayAsync(cancellationToken);

        return Results.Ok(new
        {
            items = mappings.Select(item => new
            {
                item.Id,
                item.name,
                item.usedIn,
                item.employeeId,
                employeeName = item.employeeId != null && names.TryGetValue(item.employeeId.Value, out var found) ? found : null,
                mapped = item.employeeId != null
            }).ToArray(),
            employees,
            unmappedCount = mappings.Count(item => item.employeeId is null),
            totalCount = mappings.Length
        });
    }

    private static async Task<IResult> AssignAsync(
        Guid id, AssignPersonRequest request, ClaimsPrincipal principal,
        AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var mapping = await database.ClientImportMappings
            .SingleOrDefaultAsync(item => item.Id == id && item.SourceField == SourceField, cancellationToken);
        if (mapping is null) return Results.NotFound();

        if (request.EmployeeId is { } employeeId)
        {
            if (!await database.Employees.AnyAsync(item => item.Id == employeeId && item.IsActive, cancellationToken))
            {
                return Results.ValidationProblem(new Dictionary<string, string[]>
                {
                    ["employeeId"] = ["Choose an active employee."]
                });
            }
            mapping.TargetId = employeeId;
            mapping.IsApproved = true;
        }
        else
        {
            // Clearing a mapping is deliberate: it returns the name to the unmapped list rather
            // than leaving a stale owner attached to future agreements.
            mapping.TargetId = null;
            mapping.IsApproved = false;
        }

        mapping.UpdatedAtUtc = clock.UtcNow;
        mapping.UpdatedByUserId = UserId(principal);
        database.AuditEvents.Add(IdentityService.CreateAudit(clock.UtcNow, mapping.UpdatedByUserId,
            "import.person_mapped", "ClientImportMapping", mapping.Id.ToString(),
            JsonSerializer.Serialize(new { mapping.SourceValue, mapping.TargetId })));
        await database.SaveChangesAsync(cancellationToken);
        return Results.NoContent();
    }

    // An employee created here has no login on purpose. Employment identity and credential identity
    // are separate, and most of these people only need to own work, not sign in yet.
    private static async Task<IResult> CreateAndAssignAsync(
        Guid id, CreatePersonRequest request, ClaimsPrincipal principal,
        AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var mapping = await database.ClientImportMappings
            .SingleOrDefaultAsync(item => item.Id == id && item.SourceField == SourceField, cancellationToken);
        if (mapping is null) return Results.NotFound();

        var displayName = (request.DisplayName ?? mapping.SourceValue).Trim();
        if (displayName.Length is < 2 or > 200)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]>
            {
                ["displayName"] = ["Enter a name between 2 and 200 characters."]
            });
        }

        var code = (request.EmployeeCode ?? SuggestCode(displayName)).Trim().ToUpperInvariant();
        if (code.Length is < 2 or > 30)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]>
            {
                ["employeeCode"] = ["Enter an employee code between 2 and 30 characters."]
            });
        }
        if (await database.Employees.AnyAsync(item => item.NormalizedEmployeeCode == code, cancellationToken))
        {
            return Results.Conflict(new { message = $"Employee code {code} is already in use." });
        }

        var now = clock.UtcNow;
        var employee = new Employee
        {
            Id = Guid.NewGuid(), EmployeeCode = code, NormalizedEmployeeCode = code,
            DisplayName = displayName, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.Employees.Add(employee);

        mapping.TargetId = employee.Id;
        mapping.IsApproved = true;
        mapping.UpdatedAtUtc = now;
        mapping.UpdatedByUserId = UserId(principal);

        database.AuditEvents.Add(IdentityService.CreateAudit(now, mapping.UpdatedByUserId,
            "employees.created", "Employee", employee.Id.ToString(),
            JsonSerializer.Serialize(new { employee.EmployeeCode, employee.DisplayName, source = "import mapping", hasLogin = false })));
        // Record the mapping too, so import.person_mapped alone answers "which workbook name became
        // which employee" without having to correlate it with employee creation events.
        database.AuditEvents.Add(IdentityService.CreateAudit(now, mapping.UpdatedByUserId,
            "import.person_mapped", "ClientImportMapping", mapping.Id.ToString(),
            JsonSerializer.Serialize(new { mapping.SourceValue, mapping.TargetId, createdEmployee = true })));
        await database.SaveChangesAsync(cancellationToken);

        return Results.Ok(new { employee.Id, employee.EmployeeCode, employee.DisplayName });
    }

    private static string SuggestCode(string displayName)
    {
        var letters = new string(displayName.Where(char.IsAsciiLetterOrDigit).ToArray()).ToUpperInvariant();
        return letters.Length == 0 ? "EMP" : letters[..Math.Min(letters.Length, 12)];
    }

    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
}

public sealed record AssignPersonRequest(Guid? EmployeeId);
public sealed record CreatePersonRequest(string? DisplayName, string? EmployeeCode);
