using System.Security.Claims;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;

namespace Practice.Api.Scheduling;

public static class CalendarEndpoints
{
    public static IEndpointRouteBuilder MapCalendarEndpoints(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapGet("/api/v1/calendar", GetAsync).RequireAuthorization("password-current", PermissionCodes.CalendarView);
        return endpoints;
    }

    private static async Task<IResult> GetAsync(DateOnly? from, DateOnly? to, string? view, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        // Default to the current Asia/Kolkata month so an unparameterised request returns the
        // obvious calendar page instead of failing parameter binding.
        var today = DateOnly.FromDateTime(clock.UtcNow.ToOffset(TimeSpan.FromMinutes(330)).DateTime);
        var selectedFrom = from ?? new DateOnly(today.Year, today.Month, 1);
        var selectedTo = to ?? selectedFrom.AddMonths(1).AddDays(-1);
        if (selectedTo < selectedFrom || selectedTo.DayNumber - selectedFrom.DayNumber > 92) return Results.ValidationProblem(new Dictionary<string, string[]> { ["to"] = ["Calendar ranges are limited to 93 days."] });
        var query = database.Tasks.AsNoTracking().Where(item => item.DueDate >= selectedFrom && item.DueDate <= selectedTo);
        query = await ApplyScopeAsync(query, principal, view, database, cancellationToken);
        var tasks = await query.OrderBy(item => item.DueDate).ThenBy(item => item.TaskNumber).Select(item => new
        {
            item.Id, item.TaskNumber, item.Title, item.DueDate, item.Priority, item.CreatedSource,
            clientName = item.Client.DisplayName, serviceName = item.Service.Name,
            status = new { item.Status.Code, item.Status.Label, item.Status.Color, item.Status.IsTerminal },
            primaryAssignee = item.Assignments.Where(assignment => assignment.UnassignedAtUtc == null && assignment.AssignmentRole == "PRIMARY").Select(assignment => assignment.Employee.DisplayName).FirstOrDefault()
        }).ToArrayAsync(cancellationToken);
        return Results.Ok(new { from = selectedFrom, to = selectedTo, tasks, countsByDate = tasks.GroupBy(item => item.DueDate).ToDictionary(group => group.Key, group => group.Count()) });
    }

    private static async Task<IQueryable<PracticeTask>> ApplyScopeAsync(IQueryable<PracticeTask> query, ClaimsPrincipal principal, string? requestedView, AppDbContext database, CancellationToken cancellationToken)
    {
        var ceiling = principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + PermissionCodes.CalendarView) ?? "OWN";
        var effective = requestedView?.Trim().ToUpperInvariant() switch { "ALL" when ceiling == "ALL" => "ALL", "TEAM" when ceiling is "TEAM" or "ALL" => "TEAM", _ => ceiling == "ALL" && requestedView is null ? "ALL" : "OWN" };
        if (effective == "ALL") return query;
        var userId = Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
        var employeeId = await database.Employees.Where(item => item.UserId == userId && item.IsActive).Select(item => (Guid?)item.Id).SingleOrDefaultAsync(cancellationToken);
        if (employeeId is null) return query.Where(_ => false);
        if (effective == "OWN") return query.Where(item => item.Assignments.Any(assignment => assignment.EmployeeId == employeeId && assignment.UnassignedAtUtc == null));
        var employeeIds = database.Employees.Where(item => item.IsActive && (item.Id == employeeId || item.ManagerEmployeeId == employeeId)).Select(item => item.Id);
        var teamIds = database.TeamMemberships.Where(item => item.EmployeeId == employeeId && item.ValidTo == null).Select(item => item.TeamId)
            .Concat(database.Teams.Where(item => item.ManagerEmployeeId == employeeId && item.IsActive).Select(item => item.Id));
        employeeIds = employeeIds.Concat(database.TeamMemberships.Where(item => teamIds.Contains(item.TeamId) && item.ValidTo == null).Select(item => item.EmployeeId)).Distinct();
        return query.Where(item => item.Assignments.Any(assignment => employeeIds.Contains(assignment.EmployeeId) && assignment.UnassignedAtUtc == null));
    }
}
