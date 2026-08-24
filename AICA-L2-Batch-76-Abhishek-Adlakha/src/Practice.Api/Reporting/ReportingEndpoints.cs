using System.Globalization;
using System.Security.Claims;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.Api.Billing;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Reporting;

namespace Practice.Api.Reporting;

public static class ReportingEndpoints
{
    private static readonly TimeSpan IndiaOffset = TimeSpan.FromMinutes(330);
    private const int MaximumExportRows = 10_000;
    private static readonly ReportCatalogItem[] CatalogItems =
    [
        new("CLIENTS", "Client register", "Clients", "Active/inactive clients, category, primary group and GSTIN coverage.", ["Status", "Category", "Primary group", "GSTIN"], true),
        new("TASKS", "Task register", "Tasks", "Due-date, status, employee, client, service and billable work reporting.", ["Bucket", "Status", "Employee", "Client", "Service", "Due date"], true),
        new("PROJECTION", "Billing projection", "Billing", "Expected fees by month, client, primary group, billing entity and service.", ["Month", "Client", "Group", "Entity", "Service"], true)
    ];

    public static IEndpointRouteBuilder MapReportingEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var reports = endpoints.MapGroup("/api/v1/reports").RequireAuthorization("password-current", PermissionCodes.ReportsView);
        reports.MapGet("/catalog", Catalog);
        reports.MapGet("/masters", MastersAsync);
        reports.MapGet("/clients", ClientsAsync);
        reports.MapGet("/tasks", TasksAsync);
        reports.MapPost("/clients:export", ExportClientsAsync).RequireAuthorization(PermissionCodes.ReportsExport).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        reports.MapPost("/tasks:export", ExportTasksAsync).RequireAuthorization(PermissionCodes.ReportsExport).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        endpoints.MapGet("/api/v1/dashboard", DashboardAsync).RequireAuthorization("password-current", PermissionCodes.ReportsView);
        return endpoints;
    }

    private static IResult Catalog() => Results.Ok(CatalogItems);

    private static async Task<IResult> DashboardAsync(
        DateOnly? from,
        DateOnly? to,
        ClaimsPrincipal principal,
        AppDbContext database,
        IClock clock,
        CancellationToken cancellationToken)
    {
        var today = LocalToday(clock); var selectedFrom = from ?? new DateOnly(today.Year, today.Month, 1); var selectedTo = to ?? selectedFrom.AddMonths(1).AddDays(-1);
        if (selectedTo < selectedFrom || selectedTo.DayNumber - selectedFrom.DayNumber > 366)
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["to"] = ["Dashboard period must contain between 1 and 367 days."] });

        var taskQuery = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        var utc = ReportingRules.UtcRange(selectedFrom, selectedTo, IndiaOffset);
        var taskFacts = await taskQuery.GroupBy(_ => 1).Select(group => new
        {
            DueToday = group.Count(item => !item.Status.IsTerminal && item.DueDate == today),
            Overdue = group.Count(item => !item.Status.IsTerminal && item.DueDate < today),
            InProcess = group.Count(item => item.Status.Code == "IN_PROCESS"),
            Completed = group.Count(item => item.Status.Code == "COMPLETED" && item.CompletedAtUtc >= utc.StartUtc && item.CompletedAtUtc < utc.EndExclusiveUtc),
            Cancelled = group.Count(item => item.Status.Code == "CANCELLED" && item.CancelledAtUtc >= utc.StartUtc && item.CancelledAtUtc < utc.EndExclusiveUtc)
        }).SingleOrDefaultAsync(cancellationToken);

        var clientQuery = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        var clientFacts = await clientQuery.GroupBy(_ => 1).Select(group => new
        {
            Active = group.Count(item => item.Status == "ACTIVE"),
            Inactive = group.Count(item => item.Status == "INACTIVE"),
            WithGstin = group.Count(item => item.GstRegistrations.Any(registration => registration.IsActive))
        }).SingleOrDefaultAsync(cancellationToken);

        var taskIds = taskQuery.Select(item => item.Id);
        var byEmployeeRows = await database.TaskAssignments.AsNoTracking()
            .Where(item => taskIds.Contains(item.TaskId) && item.UnassignedAtUtc == null && item.AssignmentRole == "PRIMARY")
            .GroupBy(item => new { item.EmployeeId, item.Employee.DisplayName })
            .Select(group => new { group.Key.EmployeeId, group.Key.DisplayName, Value = group.Count() })
            .OrderByDescending(item => item.Value).ThenBy(item => item.DisplayName).Take(12).ToArrayAsync(cancellationToken);
        var byEmployee = byEmployeeRows.Select(item => new DashboardBreakdown(item.EmployeeId.ToString(), item.DisplayName, item.Value)).ToArray();

        ProjectionReport? projection = null;
        if (principal.HasClaim(IdentityConstants.PermissionClaim, PermissionCodes.BillingProject))
        {
            var monthFrom = new DateOnly(today.Year, today.Month, 1); var monthTo = monthFrom.AddMonths(1).AddDays(-1);
            projection = await BillingProjectionEndpoints.CalculateReportAsync(new ProjectionRequest(monthFrom, monthTo, today, null, null, null, null, null, null), principal, database, clock, cancellationToken, PermissionCodes.ReportsView);
        }

        var metrics = new List<DashboardMetric>
        {
            new("ACTIVE_CLIENTS", "Active clients", clientFacts?.Active ?? 0, "CLIENTS", "ACTIVE", "Clients whose current lifecycle status is active."),
            new("DUE_TODAY", "Due today", taskFacts?.DueToday ?? 0, "TASKS", "DUE_TODAY", "Non-terminal tasks due on the current Asia/Kolkata date."),
            new("OVERDUE", "Overdue", taskFacts?.Overdue ?? 0, "TASKS", "OVERDUE", "Non-terminal tasks with a due date before today."),
            new("IN_PROCESS", "In process", taskFacts?.InProcess ?? 0, "TASKS", "IN_PROCESS", "Tasks whose current status is In Process."),
            new("COMPLETED", "Completed", taskFacts?.Completed ?? 0, "TASKS", "COMPLETED", "Tasks completed during the selected Asia/Kolkata period."),
            new("CANCELLED", "Cancelled", taskFacts?.Cancelled ?? 0, "TASKS", "CANCELLED", "Tasks cancelled during the selected Asia/Kolkata period."),
            new("INACTIVE_CLIENTS", "Inactive clients", clientFacts?.Inactive ?? 0, "CLIENTS", "INACTIVE", "Clients whose current lifecycle status is inactive."),
            new("CLIENTS_WITH_GSTIN", "Clients with GSTIN", clientFacts?.WithGstin ?? 0, "CLIENTS", "WITH_GSTIN", "Visible clients with at least one active GST registration.")
        };

        return Results.Ok(new
        {
            today, selectedFrom, selectedTo, generatedAtUtc = clock.UtcNow,
            scope = principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + PermissionCodes.ReportsView),
            metrics,
            tasksByEmployee = byEmployee,
            projectionAvailable = projection is not null,
            projectionDefinition = projection?.Definition,
            currentMonthProjectionTotals = projection?.Totals ?? [],
            currentMonthProjectionByEntity = projection?.BillingEntities ?? []
        });
    }

    private static async Task<IResult> MastersAsync(ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var tasks = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        var clients = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        var today = LocalToday(clock); var visibleClientIds = clients.Select(item => item.Id);
        var taskClientIds = tasks.Select(item => item.ClientId); var serviceIds = tasks.Select(item => item.ServiceId);
        var employeeIds = tasks.SelectMany(item => item.Assignments.Where(assignment => assignment.UnassignedAtUtc == null).Select(assignment => assignment.EmployeeId));
        return Results.Ok(new
        {
            clients = await clients.Where(item => taskClientIds.Contains(item.Id) || item.Status == "ACTIVE").OrderBy(item => item.DisplayName).Select(item => new { item.Id, item.ClientCode, item.DisplayName }).ToArrayAsync(cancellationToken),
            services = await database.Services.AsNoTracking().Where(item => serviceIds.Contains(item.Id)).OrderBy(item => item.Name).Select(item => new { item.Id, item.Code, item.Name }).ToArrayAsync(cancellationToken),
            employees = await database.Employees.AsNoTracking().Where(item => employeeIds.Contains(item.Id)).OrderBy(item => item.DisplayName).Select(item => new { item.Id, item.EmployeeCode, item.DisplayName }).ToArrayAsync(cancellationToken),
            statuses = await database.TaskStatuses.AsNoTracking().OrderBy(item => item.DisplayOrder).Select(item => new { item.Code, item.Label }).ToArrayAsync(cancellationToken),
            categories = await database.ClientCategories.AsNoTracking().Where(item => item.IsActive && clients.Any(client => client.CategoryId == item.Id)).OrderBy(item => item.DisplayOrder).Select(item => new { item.Id, item.Code, item.Name }).ToArrayAsync(cancellationToken),
            groups = await database.ClientGroupMemberships.AsNoTracking().Where(item => visibleClientIds.Contains(item.ClientId) && item.MembershipType == "PRIMARY" && item.EffectiveFrom <= today && (item.ValidTo == null || item.ValidTo >= today) && item.Group.IsActive).Select(item => new { item.Group.Id, item.Group.Code, item.Group.Name }).Distinct().OrderBy(item => item.Name).ToArrayAsync(cancellationToken)
        });
    }

    private static async Task<IResult> ClientsAsync(
        string? status, bool? hasGstin, Guid? categoryId, Guid? groupId, string? search,
        int? page, int? pageSize, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var selectedPage = Math.Max(1, page ?? 1); var selectedPageSize = Math.Clamp(pageSize is null or 0 ? 50 : pageSize.Value, 1, 100); var today = LocalToday(clock);
        var query = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        query = ApplyClientFilters(query, status, hasGstin, categoryId, groupId, search, today);
        var total = await query.CountAsync(cancellationToken);
        var items = await ProjectClients(OrderClients(query), today).Skip((selectedPage - 1) * selectedPageSize).Take(selectedPageSize).ToArrayAsync(cancellationToken);
        var byStatusRows = await query.GroupBy(item => item.Status)
            .Select(group => new { group.Key, Value = group.Count() })
            .OrderBy(item => item.Key).ToArrayAsync(cancellationToken);
        var byStatus = byStatusRows.Select(item => new ReportBreakdown(item.Key, item.Key, item.Value)).ToArray();
        var byCategoryRows = await query.GroupBy(item => item.Category == null ? "Unclassified" : item.Category.Name)
            .Select(group => new { group.Key, Value = group.Count() })
            .OrderByDescending(item => item.Value).ThenBy(item => item.Key).ToArrayAsync(cancellationToken);
        var byCategory = byCategoryRows.Select(item => new ReportBreakdown(item.Key, item.Key, item.Value)).ToArray();
        return Results.Ok(new { items, page = selectedPage, pageSize = selectedPageSize, totalCount = total, totalPages = (int)Math.Ceiling(total / (double)selectedPageSize), byStatus, byCategory, definition = "Client lifecycle and GSTIN coverage as currently stored; primary group is effective on the report date." });
    }

    private static async Task<IResult> TasksAsync(
        string? bucket, string? status, DateOnly? from, DateOnly? to, Guid? employeeId, Guid? clientId, Guid? serviceId, bool? billable, string? search,
        int? page, int? pageSize, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var selectedPage = Math.Max(1, page ?? 1); var selectedPageSize = Math.Clamp(pageSize is null or 0 ? 50 : pageSize.Value, 1, 100); var today = LocalToday(clock);
        var validation = ValidateTaskDates(from, to); if (validation is not null) return validation;
        var query = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        query = ApplyTaskFilters(query, bucket, status, from, to, employeeId, clientId, serviceId, billable, search, today);
        var total = await query.CountAsync(cancellationToken);
        var items = await ProjectTasks(OrderTasks(query)).Skip((selectedPage - 1) * selectedPageSize).Take(selectedPageSize).ToArrayAsync(cancellationToken);
        var byStatusRows = await query.GroupBy(item => new { item.Status.Code, item.Status.Label })
            .Select(group => new { group.Key.Code, group.Key.Label, Value = group.Count() })
            .OrderByDescending(item => item.Value).ThenBy(item => item.Label).ToArrayAsync(cancellationToken);
        var byStatus = byStatusRows.Select(item => new ReportBreakdown(item.Code, item.Label, item.Value)).ToArray();
        var byServiceRows = await query.GroupBy(item => new { item.ServiceId, item.Service.Name })
            .Select(group => new { group.Key.ServiceId, group.Key.Name, Value = group.Count() })
            .OrderByDescending(item => item.Value).ThenBy(item => item.Name).Take(20).ToArrayAsync(cancellationToken);
        var byService = byServiceRows.Select(item => new ReportBreakdown(item.ServiceId.ToString(), item.Name, item.Value)).ToArray();
        return Results.Ok(new { items, page = selectedPage, pageSize = selectedPageSize, totalCount = total, totalPages = (int)Math.Ceiling(total / (double)selectedPageSize), byStatus, byService, today, definition = "Task metrics use current status, current active assignments and Asia/Kolkata date boundaries." });
    }

    private static async Task<IResult> ExportClientsAsync(ClientExportRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var formatError = ValidateFormat(request.Format); if (formatError is not null) return formatError; var today = LocalToday(clock);
        var query = await ApplyClientScopeAsync(database.Clients.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        query = await ApplyClientScopeAsync(query, principal, PermissionCodes.ReportsExport, database, cancellationToken);
        query = ApplyClientFilters(query, request.Filters.Status, request.Filters.HasGstin, request.Filters.CategoryId, request.Filters.GroupId, request.Filters.Search, today);
        var count = await query.CountAsync(cancellationToken); if (count > MaximumExportRows) return ExportLimit(count);
        var rows = await ProjectClients(OrderClients(query), today).ToArrayAsync(cancellationToken);
        var columns = new[] { new ExportColumn("Client code"), new ExportColumn("Client"), new ExportColumn("Status"), new ExportColumn("Category"), new ExportColumn("Primary group"), new ExportColumn("PAN"), new ExportColumn("Active GSTINs", true) };
        var values = rows.Select(item => (IReadOnlyList<string>)[item.ClientCode, item.DisplayName, item.Status, item.Category ?? "", item.PrimaryGroup ?? "", item.Pan ?? "", item.GstinCount.ToString(CultureInfo.InvariantCulture)]);
        await RecordExportAsync(database, clock, principal, "CLIENTS", request.Format, rows.Length, cancellationToken);
        return ExportFile(request.Format, "client-report", columns, values);
    }

    private static async Task<IResult> ExportTasksAsync(TaskExportRequest request, ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var formatError = ValidateFormat(request.Format); if (formatError is not null) return formatError;
        var dateError = ValidateTaskDates(request.Filters.From, request.Filters.To); if (dateError is not null) return dateError; var today = LocalToday(clock);
        var query = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking(), principal, PermissionCodes.ReportsView, database, cancellationToken);
        query = await ApplyTaskScopeAsync(query, principal, PermissionCodes.ReportsExport, database, cancellationToken);
        query = ApplyTaskFilters(query, request.Filters.Bucket, request.Filters.Status, request.Filters.From, request.Filters.To, request.Filters.EmployeeId, request.Filters.ClientId, request.Filters.ServiceId, request.Filters.Billable, request.Filters.Search, today);
        var count = await query.CountAsync(cancellationToken); if (count > MaximumExportRows) return ExportLimit(count);
        var rows = await ProjectTasks(OrderTasks(query)).ToArrayAsync(cancellationToken);
        var columns = new[] { new ExportColumn("Task number", true), new ExportColumn("Title"), new ExportColumn("Client code"), new ExportColumn("Client"), new ExportColumn("Service"), new ExportColumn("Due date"), new ExportColumn("Status"), new ExportColumn("Priority"), new ExportColumn("Primary assignee"), new ExportColumn("Billable") };
        var values = rows.Select(item => (IReadOnlyList<string>)[item.TaskNumber.ToString(CultureInfo.InvariantCulture), item.Title, item.ClientCode, item.ClientName, item.ServiceName, item.DueDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), item.StatusLabel, item.Priority, item.PrimaryAssignee ?? "", item.Billable ? "Yes" : "No"]);
        await RecordExportAsync(database, clock, principal, "TASKS", request.Format, rows.Length, cancellationToken);
        return ExportFile(request.Format, "task-report", columns, values);
    }

    private static IQueryable<Client> ApplyClientFilters(IQueryable<Client> query, string? status, bool? hasGstin, Guid? categoryId, Guid? groupId, string? search, DateOnly today)
    {
        if (!string.IsNullOrWhiteSpace(status) && !string.Equals(status.Trim(), "ALL", StringComparison.OrdinalIgnoreCase)) { var normalized = status.Trim().ToUpperInvariant(); query = query.Where(item => item.Status == normalized); }
        if (hasGstin is not null) query = hasGstin.Value ? query.Where(item => item.GstRegistrations.Any(registration => registration.IsActive)) : query.Where(item => !item.GstRegistrations.Any(registration => registration.IsActive));
        if (categoryId is not null) query = query.Where(item => item.CategoryId == categoryId);
        if (groupId is not null) query = query.Where(item => item.GroupMemberships.Any(membership => membership.GroupId == groupId && membership.MembershipType == "PRIMARY" && membership.EffectiveFrom <= today && (membership.ValidTo == null || membership.ValidTo >= today)));
        if (!string.IsNullOrWhiteSpace(search)) { var term = search.Trim(); query = query.Where(item => EF.Functions.ILike(item.DisplayName, $"%{term}%") || EF.Functions.ILike(item.ClientCode, $"%{term}%") || (item.Pan != null && EF.Functions.ILike(item.Pan, $"%{term}%"))); }
        return query;
    }

    // Order the entity before projecting. Ordering the projected row instead makes PostgreSQL
    // translation fail, because the row carries correlated subqueries that cannot appear in ORDER BY.
    private static IQueryable<Client> OrderClients(IQueryable<Client> query) =>
        query.OrderBy(item => item.DisplayName).ThenBy(item => item.ClientCode);

    private static IQueryable<ClientReportRow> ProjectClients(IQueryable<Client> query, DateOnly today) => query.Select(item => new ClientReportRow(
        item.Id, item.ClientCode, item.DisplayName, item.Status, item.Category == null ? null : item.Category.Name, item.Pan,
        item.GstRegistrations.Count(registration => registration.IsActive),
        item.GroupMemberships.Where(membership => membership.MembershipType == "PRIMARY" && membership.EffectiveFrom <= today && (membership.ValidTo == null || membership.ValidTo >= today)).OrderByDescending(membership => membership.EffectiveFrom).Select(membership => membership.Group.Name).FirstOrDefault()));

    private static IQueryable<PracticeTask> ApplyTaskFilters(IQueryable<PracticeTask> query, string? bucket, string? status, DateOnly? from, DateOnly? to, Guid? employeeId, Guid? clientId, Guid? serviceId, bool? billable, string? search, DateOnly today)
    {
        var normalizedBucket = bucket?.Trim().ToUpperInvariant();
        if (normalizedBucket == "OVERDUE") query = query.Where(item => !item.Status.IsTerminal && item.DueDate < today);
        else if (normalizedBucket == "DUE_TODAY") query = query.Where(item => !item.Status.IsTerminal && item.DueDate == today);
        else if (normalizedBucket == "UPCOMING") query = query.Where(item => !item.Status.IsTerminal && item.DueDate > today);
        else if (normalizedBucket == "IN_PROCESS") query = query.Where(item => item.Status.Code == "IN_PROCESS");
        else if (normalizedBucket is "COMPLETED" or "CANCELLED")
        {
            var selectedFrom = from ?? new DateOnly(today.Year, today.Month, 1); var selectedTo = to ?? selectedFrom.AddMonths(1).AddDays(-1); var utc = ReportingRules.UtcRange(selectedFrom, selectedTo, IndiaOffset);
            query = normalizedBucket == "COMPLETED"
                ? query.Where(item => item.Status.Code == "COMPLETED" && item.CompletedAtUtc >= utc.StartUtc && item.CompletedAtUtc < utc.EndExclusiveUtc)
                : query.Where(item => item.Status.Code == "CANCELLED" && item.CancelledAtUtc >= utc.StartUtc && item.CancelledAtUtc < utc.EndExclusiveUtc);
        }
        else { if (from is not null) query = query.Where(item => item.DueDate >= from.Value); if (to is not null) query = query.Where(item => item.DueDate <= to.Value); }
        if (!string.IsNullOrWhiteSpace(status)) { var normalized = status.Trim().ToUpperInvariant(); query = query.Where(item => item.Status.Code == normalized); }
        if (employeeId is not null) query = query.Where(item => item.Assignments.Any(assignment => assignment.EmployeeId == employeeId && assignment.UnassignedAtUtc == null));
        if (clientId is not null) query = query.Where(item => item.ClientId == clientId);
        if (serviceId is not null) query = query.Where(item => item.ServiceId == serviceId);
        if (billable is not null) query = query.Where(item => item.BillableSnapshot == billable);
        if (!string.IsNullOrWhiteSpace(search)) { var term = search.Trim(); query = query.Where(item => EF.Functions.ILike(item.Title, $"%{term}%") || EF.Functions.ILike(item.Client.DisplayName, $"%{term}%") || EF.Functions.ILike(item.Service.Name, $"%{term}%")); }
        return query;
    }

    private static IQueryable<PracticeTask> OrderTasks(IQueryable<PracticeTask> query) =>
        query.OrderBy(item => item.DueDate).ThenBy(item => item.TaskNumber);

    private static IQueryable<TaskReportRow> ProjectTasks(IQueryable<PracticeTask> query) => query.Select(item => new TaskReportRow(
        item.Id, item.TaskNumber, item.Title, item.ClientId, item.Client.ClientCode, item.Client.DisplayName, item.ServiceId, item.Service.Name,
        item.DueDate, item.Status.Code, item.Status.Label, item.Priority, item.BillableSnapshot,
        item.Assignments.Where(assignment => assignment.UnassignedAtUtc == null && assignment.AssignmentRole == "PRIMARY").Select(assignment => assignment.Employee.DisplayName).SingleOrDefault()));

    private static async Task<IQueryable<PracticeTask>> ApplyTaskScopeAsync(IQueryable<PracticeTask> query, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, permission); if (scope == "ALL") return query;
        var current = await CurrentEmployeeIdAsync(principal, database, cancellationToken); if (current is null) return query.Where(_ => false);
        if (scope == "OWN") return query.Where(item => item.Assignments.Any(assignment => assignment.EmployeeId == current && assignment.UnassignedAtUtc == null));
        var employees = await AccessibleEmployeeIdsAsync(current.Value, database, cancellationToken);
        return query.Where(item => item.Assignments.Any(assignment => employees.Contains(assignment.EmployeeId) && assignment.UnassignedAtUtc == null));
    }

    private static async Task<IQueryable<Client>> ApplyClientScopeAsync(IQueryable<Client> query, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, permission); if (scope == "ALL") return query;
        var current = await CurrentEmployeeIdAsync(principal, database, cancellationToken); if (current is null) return query.Where(_ => false);
        var teams = await AccessibleTeamIdsAsync(current.Value, scope, database, cancellationToken);
        return query.Where(item => database.ClientServices.Any(agreement => agreement.ClientId == item.Id && agreement.ResponsibleTeamId != null && teams.Contains(agreement.ResponsibleTeamId.Value)));
    }

    private static async Task<Guid[]> AccessibleEmployeeIdsAsync(Guid employeeId, AppDbContext database, CancellationToken cancellationToken)
    {
        var teams = await AccessibleTeamIdsAsync(employeeId, "TEAM", database, cancellationToken);
        return await database.Employees.Where(item => item.IsActive && (item.Id == employeeId || item.ManagerEmployeeId == employeeId || database.TeamMemberships.Any(membership => membership.EmployeeId == item.Id && membership.ValidTo == null && teams.Contains(membership.TeamId)))).Select(item => item.Id).Distinct().ToArrayAsync(cancellationToken);
    }

    private static async Task<Guid[]> AccessibleTeamIdsAsync(Guid employeeId, string? scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var teams = database.TeamMemberships.Where(item => item.EmployeeId == employeeId && item.ValidTo == null).Select(item => item.TeamId);
        if (scope == "TEAM") teams = teams.Concat(database.Teams.Where(item => item.ManagerEmployeeId == employeeId && item.IsActive).Select(item => item.Id));
        return await teams.Distinct().ToArrayAsync(cancellationToken);
    }

    private static async Task<Guid?> CurrentEmployeeIdAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken) =>
        await database.Employees.Where(item => item.UserId == UserId(principal) && item.IsActive).Select(item => (Guid?)item.Id).SingleOrDefaultAsync(cancellationToken);

    private static IResult ExportFile(string format, string stem, IReadOnlyList<ExportColumn> columns, IEnumerable<IReadOnlyList<string>> rows)
    {
        var normalized = format.Trim().ToLowerInvariant();
        return normalized == "csv"
            ? Results.File(TabularExport.Csv(columns, rows), "text/csv; charset=utf-8", $"{stem}.csv")
            : Results.File(TabularExport.Xlsx(stem, columns, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", $"{stem}.xlsx");
    }

    private static IResult? ValidateFormat(string format) => format.Trim().ToLowerInvariant() is "csv" or "xlsx" ? null : Results.ValidationProblem(new Dictionary<string, string[]> { ["format"] = ["Export format must be CSV or XLSX."] });
    private static IResult ExportLimit(int count) => Results.Problem(statusCode: 422, title: "Export is too large", detail: $"The filtered report contains {count:N0} rows. Narrow the filters to {MaximumExportRows:N0} rows or fewer.");
    private static IResult? ValidateTaskDates(DateOnly? from, DateOnly? to) => from is not null && to is not null && (to < from || to.Value.DayNumber - from.Value.DayNumber > 1_827) ? Results.ValidationProblem(new Dictionary<string, string[]> { ["to"] = ["Task report range must end after its start and cover no more than five years."] }) : null;
    // Exports leave the system with confidential data, so who exported what, in which shape, and
    // how many rows is recorded. The exported values themselves are never written to the audit.
    private static async Task RecordExportAsync(
        AppDbContext database, IClock clock, ClaimsPrincipal principal, string report, string format, int rowCount, CancellationToken cancellationToken)
    {
        database.AuditEvents.Add(Practice.Identity.IdentityService.CreateAudit(
            clock.UtcNow, UserId(principal), "reports.exported", "Report", report,
            System.Text.Json.JsonSerializer.Serialize(new
            {
                report,
                format = format.ToUpperInvariant(),
                rowCount,
                scope = Scope(principal, PermissionCodes.ReportsExport)
            })));
        await database.SaveChangesAsync(cancellationToken);
    }

    private static DateOnly LocalToday(IClock clock) => DateOnly.FromDateTime(clock.UtcNow.ToOffset(IndiaOffset).DateTime);
    private static string? Scope(ClaimsPrincipal principal, string permission) => principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
}

public sealed record DashboardMetric(string Code, string Label, int Value, string Report, string Filter, string Definition);
public sealed record ReportCatalogItem(string Code, string Name, string Module, string Description, string[] Dimensions, bool Exportable);
public sealed record DashboardBreakdown(string Key, string Label, int Value);
public sealed record ReportBreakdown(string Key, string Label, int Value);
public sealed record ClientReportFilters(string? Status, bool? HasGstin, Guid? CategoryId, Guid? GroupId, string? Search);
public sealed record ClientExportRequest(string Format, ClientReportFilters Filters);
public sealed record TaskReportFilters(string? Bucket, string? Status, DateOnly? From, DateOnly? To, Guid? EmployeeId, Guid? ClientId, Guid? ServiceId, bool? Billable, string? Search);
public sealed record TaskExportRequest(string Format, TaskReportFilters Filters);
public sealed record ClientReportRow(Guid Id, string ClientCode, string DisplayName, string Status, string? Category, string? Pan, int GstinCount, string? PrimaryGroup);
public sealed record TaskReportRow(Guid Id, long TaskNumber, string Title, Guid ClientId, string ClientCode, string ClientName, Guid ServiceId, string ServiceName, DateOnly DueDate, string StatusCode, string StatusLabel, string Priority, bool Billable, string? PrimaryAssignee);
