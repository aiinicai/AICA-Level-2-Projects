using System.Security.Claims;
using System.Text.Json;
using System.Globalization;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Reporting;

namespace Practice.Api.Tasks;

public static class TaskEndpoints
{
    private static readonly string[] Priorities = ["LOW", "NORMAL", "HIGH", "URGENT"];
    private static readonly string[] AssignmentRoles = ["PRIMARY", "SECONDARY", "REVIEWER"];
    private static readonly string[] OwnView = ["mine"];
    private static readonly string[] TeamViews = ["mine", "team"];
    private static readonly string[] AllViews = ["mine", "team", "all"];

    public static IEndpointRouteBuilder MapTaskEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var tasks = endpoints.MapGroup("/api/v1/tasks").RequireAuthorization("password-current");
        tasks.MapGet("/", ListAsync).RequireAuthorization(PermissionCodes.TasksView);
        tasks.MapGet("/masters", MastersAsync).RequireAuthorization(PermissionCodes.TasksView);
        tasks.MapGet("/{id:guid}", DetailAsync).RequireAuthorization(PermissionCodes.TasksView);
        tasks.MapPost("/", CreateAsync).RequireAuthorization(PermissionCodes.TasksCreate).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        tasks.MapPost("/{id:guid}/status", ChangeStatusAsync).RequireAuthorization(PermissionCodes.TasksChangeStatus).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        tasks.MapPost("/{id:guid}/assignments", AssignAsync).RequireAuthorization(PermissionCodes.TasksAssign).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        tasks.MapPost("/{id:guid}/assignments/{assignmentId:guid}/unassign", UnassignAsync).RequireAuthorization(PermissionCodes.TasksAssign).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        tasks.MapPost("/{id:guid}/comments", CommentAsync).RequireAuthorization(PermissionCodes.TasksComment).WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> ListAsync(
        string? view, string? status, DateOnly? dueFrom, DateOnly? dueTo, string? search,
        int? page, int? pageSize, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var selectedPage = Math.Max(1, page ?? 1); var selectedPageSize = Math.Clamp(pageSize is null or 0 ? 25 : pageSize.Value, 1, 100);
        var query = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking(), principal, PermissionCodes.TasksView, view, database, cancellationToken);
        if (!string.IsNullOrWhiteSpace(status)) { var normalizedStatus = status.Trim().ToUpperInvariant(); query = query.Where(x => x.Status.Code == normalizedStatus); }
        if (dueFrom is not null) query = query.Where(x => x.DueDate >= dueFrom);
        if (dueTo is not null) query = query.Where(x => x.DueDate <= dueTo);
        if (!string.IsNullOrWhiteSpace(search))
        {
            var term = search.Trim(); query = query.Where(x => EF.Functions.ILike(x.Title, $"%{term}%") || EF.Functions.ILike(x.Client.DisplayName, $"%{term}%") || EF.Functions.ILike(x.Service.Name, $"%{term}%"));
        }
        var total = await query.CountAsync(cancellationToken);
        var items = await query.OrderBy(x => x.Status.IsTerminal).ThenBy(x => x.DueDate).ThenByDescending(x => x.Priority).ThenBy(x => x.TaskNumber)
            .Skip((selectedPage - 1) * selectedPageSize).Take(selectedPageSize).Select(x => new
            {
                x.Id, x.TaskNumber, x.Title, x.DueDate, x.Priority, x.BillableSnapshot, x.RowVersion,
                x.ClientId, clientCode = x.Client.ClientCode, clientName = x.Client.DisplayName,
                x.ServiceId, serviceCode = x.Service.Code, serviceName = x.Service.Name,
                x.GstRegistrationId, gstin = x.GstRegistration == null ? null : x.GstRegistration.Gstin,
                status = new { x.Status.Id, x.Status.Code, x.Status.Label, x.Status.Color, x.Status.IsTerminal },
                assignments = x.Assignments.Where(a => a.UnassignedAtUtc == null).OrderBy(a => a.AssignmentRole).Select(a => new { a.Id, a.EmployeeId, employeeName = a.Employee.DisplayName, role = a.AssignmentRole })
            }).ToArrayAsync(cancellationToken);
        return Results.Ok(new { items, page = selectedPage, pageSize = selectedPageSize, totalCount = total, totalPages = (int)Math.Ceiling(total / (double)selectedPageSize) });
    }

    private static DateOnly LocalToday(IClock clock) =>
        DateOnly.FromDateTime(clock.UtcNow.ToOffset(TimeSpan.FromMinutes(330)).DateTime);

    private static async Task<IResult> MastersAsync(ClaimsPrincipal principal, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var maxScope = Scope(principal, PermissionCodes.TasksView)!;
        var accessibleEmployees = await AccessibleEmployeeIdsAsync(principal, maxScope, database, cancellationToken);
        var agreements = database.ClientServices.AsNoTracking().Where(x => x.IsActive && x.Client.Status == "ACTIVE" && x.Service.IsActive);
        if (maxScope != "ALL")
        {
            var teams = await AccessibleTeamIdsAsync(principal, maxScope, database, cancellationToken);
            agreements = agreements.Where(x => x.ResponsibleTeamId != null && teams.Contains(x.ResponsibleTeamId.Value));
        }
        var agreementRows = await agreements.OrderBy(x => x.Client.DisplayName).ThenBy(x => x.Service.Name).Select(x => new
        {
            x.Id, x.ClientId, clientCode = x.Client.ClientCode, clientName = x.Client.DisplayName,
            x.ServiceId, serviceName = x.Service.Name, x.GstRegistrationId,
            gstin = x.GstRegistration == null ? null : x.GstRegistration.Gstin,
            title = x.TitleOverride ?? x.Service.Name, priority = x.DefaultPriority, billable = x.Service.DefaultBillable
        }).ToArrayAsync(cancellationToken);
        var employees = database.Employees.AsNoTracking().Where(x => x.IsActive);
        var assignScope = Scope(principal, PermissionCodes.TasksAssign);
        if (assignScope != "ALL")
        {
            var ids = assignScope is null ? accessibleEmployees : await AccessibleEmployeeIdsAsync(principal, assignScope, database, cancellationToken);
            employees = employees.Where(x => ids.Contains(x.Id));
        }
        var required = await database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == "tasks.task" && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        return Results.Ok(new
        {
            agreements = agreementRows,
            statuses = await database.TaskStatuses.AsNoTracking().Where(x => x.IsActive).OrderBy(x => x.DisplayOrder).Select(x => new { x.Id, x.Code, x.Label, x.Color, x.IsTerminal }).ToArrayAsync(cancellationToken),
            transitions = await database.TaskStatusTransitions.AsNoTracking().Select(x => new { x.FromStatusId, x.ToStatusId, x.ReasonRequired, x.CompletionDataRequired, x.RequiredPermission }).ToArrayAsync(cancellationToken),
            employees = await employees.OrderBy(x => x.DisplayName).Select(x => new { x.Id, x.EmployeeCode, x.DisplayName }).ToArrayAsync(cancellationToken),
            requiredFields = required,
            allowedViews = maxScope == "ALL" ? AllViews : maxScope == "TEAM" ? TeamViews : OwnView,
            // Most statutory work is filed for a financial year rather than a date, so the task
            // form offers the year and derives the period from it.
            financialYears = ReportingRules.FinancialYearChoices(LocalToday(clock))
                .Select(year =>
                {
                    var range = ReportingRules.FinancialYearRange(year);
                    return new { startYear = year, label = ReportingRules.FinancialYearLabel(year), from = range.From, to = range.To };
                })
                .OrderByDescending(item => item.startYear)
                .ToArray()
        });
    }

    private static async Task<IResult> DetailAsync(Guid id, HttpContext context, AppDbContext database, CancellationToken cancellationToken)
    {
        var scoped = await ApplyTaskScopeAsync(database.Tasks.AsNoTracking().Where(x => x.Id == id), context.User, PermissionCodes.TasksView, null, database, cancellationToken);
        var item = await scoped.Select(x => new
        {
            x.Id, x.TaskNumber, x.ClientId, clientCode = x.Client.ClientCode, clientName = x.Client.DisplayName,
            x.ServiceId, serviceCode = x.Service.Code, serviceName = x.Service.Name, x.ClientServiceId,
            x.GstRegistrationId, gstin = x.GstRegistration == null ? null : x.GstRegistration.Gstin,
            x.Title, x.Description, x.PeriodStart, x.PeriodEnd, x.DueDate, x.Priority, x.BillableSnapshot,
            status = new { x.Status.Id, x.Status.Code, x.Status.Label, x.Status.Color, x.Status.IsTerminal },
            x.CompletedAtUtc, x.CancelledAtUtc, x.CancellationReason, x.ReopenedCount, x.CreatedSource, x.CreatedAtUtc, x.UpdatedAtUtc, x.RowVersion,
            assignments = x.Assignments.OrderByDescending(a => a.AssignedAtUtc).Select(a => new { a.Id, a.EmployeeId, employeeName = a.Employee.DisplayName, role = a.AssignmentRole, a.AssignedAtUtc, a.UnassignedAtUtc, a.Remarks, a.UnassignmentReason }),
            timeline = x.StatusHistory.OrderByDescending(h => h.ChangedAtUtc).Select(h => new { h.Id, fromStatus = h.FromStatus == null ? null : h.FromStatus.Label, toStatus = h.ToStatus.Label, h.ChangedAtUtc, h.Reason, h.CompletionNote, actor = database.Employees.Where(e => e.UserId == h.ActorUserId).Select(e => e.DisplayName).FirstOrDefault() }),
            comments = x.Comments.OrderByDescending(c => c.CreatedAtUtc).Select(c => new { c.Id, body = c.IsRedacted ? "[Comment redacted]" : c.Body, c.CreatedAtUtc, c.EditedAtUtc, c.IsRedacted, author = database.Employees.Where(e => e.UserId == c.AuthorUserId).Select(e => e.DisplayName).FirstOrDefault() })
        }).SingleOrDefaultAsync(cancellationToken);
        if (item is null) return Results.NotFound();
        context.Response.Headers.ETag = $"\"{item.RowVersion}\"";
        return Results.Ok(item);
    }

    private static async Task<IResult> CreateAsync(TaskCreateRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var errors = await ValidateCreateAsync(request, database, cancellationToken);
        if (errors.Count > 0) return Results.ValidationProblem(errors);
        var creationScopeError = await ValidateCreationScopeAsync(request.ClientServiceId, context.User, database, cancellationToken);
        if (creationScopeError is not null) return creationScopeError;
        if (request.PrimaryAssigneeId is not null)
        {
            if (!context.User.HasClaim(IdentityConstants.PermissionClaim, PermissionCodes.TasksAssign)) return Results.Forbid();
            if (!await CanTargetEmployeeAsync(request.PrimaryAssigneeId.Value, context.User, PermissionCodes.TasksAssign, database, cancellationToken)) return ScopeDenied("The primary assignee is outside your assignment scope.");
        }
        foreach (var employeeId in request.SecondaryAssigneeIds.Distinct())
            if (!await CanTargetEmployeeAsync(employeeId, context.User, PermissionCodes.TasksAssign, database, cancellationToken)) return ScopeDenied("A secondary assignee is outside your assignment scope.");

        var actor = UserId(context.User); var now = clock.UtcNow;
        var service = await database.Services.AsNoTracking().SingleAsync(x => x.Id == request.ServiceId, cancellationToken);
        var task = new PracticeTask
        {
            Id = Guid.NewGuid(), ClientId = request.ClientId, ServiceId = request.ServiceId, ClientServiceId = request.ClientServiceId,
            GstRegistrationId = request.GstRegistrationId, Title = request.Title.Trim(), Description = Clean(request.Description),
            PeriodStart = request.PeriodStart, PeriodEnd = request.PeriodEnd, DueDate = request.DueDate, StatusId = TaskSeed.NotStartedId,
            Priority = NormalizePriority(request.Priority), BillableSnapshot = request.Billable ?? service.DefaultBillable,
            CreatedSource = "MANUAL", CreatedByUserId = actor, UpdatedByUserId = actor, CreatedAtUtc = now, UpdatedAtUtc = now, RowVersion = 1
        };
        database.Tasks.Add(task);
        database.TaskStatusHistory.Add(new TaskStatusHistory { Id = Guid.NewGuid(), TaskId = task.Id, ToStatusId = TaskSeed.NotStartedId, ActorUserId = actor, ChangedAtUtc = now, Reason = "Task created", MetadataJson = "{}" });
        if (request.PrimaryAssigneeId is not null) database.TaskAssignments.Add(NewAssignment(task.Id, request.PrimaryAssigneeId.Value, "PRIMARY", actor, now, request.AssignmentRemarks));
        foreach (var employeeId in request.SecondaryAssigneeIds.Distinct()) database.TaskAssignments.Add(NewAssignment(task.Id, employeeId, "SECONDARY", actor, now, request.AssignmentRemarks));
        database.AuditEvents.Add(Audit(now, actor, "tasks.created", task.Id, new { task.ClientId, task.ServiceId, task.ClientServiceId, task.DueDate, task.Priority, request.PrimaryAssigneeId }));
        await database.SaveChangesAsync(cancellationToken);
        return Results.Created($"/api/v1/tasks/{task.Id}", new { task.Id, task.TaskNumber, task.RowVersion });
    }

    private static async Task<IResult> ChangeStatusAsync(Guid id, TaskStatusChangeRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var task = await ScopedTaskForMutationAsync(id, context.User, PermissionCodes.TasksChangeStatus, database, cancellationToken);
        if (task is null) return Results.NotFound();
        if (task.RowVersion != request.ExpectedVersion) return VersionConflict(task.RowVersion);
        var transition = await database.TaskStatusTransitions.AsNoTracking().SingleOrDefaultAsync(x => x.FromStatusId == task.StatusId && x.ToStatusId == request.ToStatusId, cancellationToken);
        if (transition is null) return Results.Conflict(new { message = "This status transition is not allowed." });
        if (!context.User.HasClaim(IdentityConstants.PermissionClaim, transition.RequiredPermission)) return Results.Forbid();
        if (transition.RequiredPermission == PermissionCodes.TasksReopen &&
            await ScopedTaskForMutationAsync(id, context.User, PermissionCodes.TasksReopen, database, cancellationToken) is null)
            return ScopeDenied("The task is outside your reopen scope.");
        if (transition.ReasonRequired && string.IsNullOrWhiteSpace(request.Reason)) return Validation("reason", "A reason is required for this transition.");
        if (transition.CompletionDataRequired && string.IsNullOrWhiteSpace(request.CompletionNote)) return Validation("completionNote", "A completion note is required.");
        var target = await database.TaskStatuses.AsNoTracking().SingleAsync(x => x.Id == request.ToStatusId && x.IsActive, cancellationToken);
        var actor = UserId(context.User); var now = clock.UtcNow; var from = task.StatusId;
        task.StatusId = target.Id; task.UpdatedAtUtc = now; task.UpdatedByUserId = actor; task.RowVersion++;
        if (target.Code == "COMPLETED") { task.CompletedAtUtc = now; task.CompletedByUserId = actor; }
        if (target.Code == "CANCELLED") { task.CancelledAtUtc = now; task.CancelledByUserId = actor; task.CancellationReason = request.Reason!.Trim(); }
        if (transition.RequiredPermission == PermissionCodes.TasksReopen)
        {
            task.CompletedAtUtc = null; task.CompletedByUserId = null; task.CancelledAtUtc = null; task.CancelledByUserId = null; task.CancellationReason = null; task.ReopenedCount++;
        }
        database.TaskStatusHistory.Add(new TaskStatusHistory { Id = Guid.NewGuid(), TaskId = task.Id, FromStatusId = from, ToStatusId = target.Id, ActorUserId = actor, ChangedAtUtc = now, Reason = Clean(request.Reason), CompletionNote = Clean(request.CompletionNote), MetadataJson = "{}" });
        database.AuditEvents.Add(Audit(now, actor, transition.RequiredPermission == PermissionCodes.TasksReopen ? "tasks.reopened" : "tasks.status_changed", task.Id, new { fromStatusId = from, toStatusId = target.Id }, request.Reason));
        return await SaveMutationAsync(database, task.RowVersion, cancellationToken);
    }

    private static async Task<IResult> AssignAsync(Guid id, TaskAssignmentRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        var task = await ScopedTaskForMutationAsync(id, context.User, PermissionCodes.TasksAssign, database, cancellationToken);
        if (task is null) return Results.NotFound();
        if (task.RowVersion != request.ExpectedVersion) return VersionConflict(task.RowVersion);
        var role = request.Role.Trim().ToUpperInvariant();
        if (!AssignmentRoles.Contains(role)) return Validation("role", "Role must be PRIMARY, SECONDARY, or REVIEWER.");
        if (!await CanTargetEmployeeAsync(request.EmployeeId, context.User, PermissionCodes.TasksAssign, database, cancellationToken)) return ScopeDenied("The employee is outside your assignment scope.");
        if (!await database.Employees.AnyAsync(x => x.Id == request.EmployeeId && x.IsActive, cancellationToken)) return Validation("employeeId", "Choose an active employee.");
        if (await database.TaskAssignments.AnyAsync(x => x.TaskId == id && x.EmployeeId == request.EmployeeId && x.AssignmentRole == role && x.UnassignedAtUtc == null, cancellationToken)) return Results.Conflict(new { message = "This employee already has that active assignment role." });
        var actor = UserId(context.User); var now = clock.UtcNow;
        if (role == "PRIMARY")
        {
            var prior = await database.TaskAssignments.Where(x => x.TaskId == id && x.AssignmentRole == "PRIMARY" && x.UnassignedAtUtc == null).SingleOrDefaultAsync(cancellationToken);
            if (prior is not null) { prior.UnassignedAtUtc = now; prior.UnassignedByUserId = actor; prior.UnassignmentReason = "Reassigned to another primary employee"; }
        }
        database.TaskAssignments.Add(NewAssignment(id, request.EmployeeId, role, actor, now, request.Remarks));
        task.UpdatedAtUtc = now; task.UpdatedByUserId = actor; task.RowVersion++;
        database.AuditEvents.Add(Audit(now, actor, "tasks.assigned", task.Id, new { request.EmployeeId, role }));
        return await SaveMutationAsync(database, task.RowVersion, cancellationToken);
    }

    private static async Task<IResult> UnassignAsync(Guid id, Guid assignmentId, TaskUnassignRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Reason)) return Validation("reason", "An unassignment reason is required.");
        var task = await ScopedTaskForMutationAsync(id, context.User, PermissionCodes.TasksAssign, database, cancellationToken);
        if (task is null) return Results.NotFound();
        if (task.RowVersion != request.ExpectedVersion) return VersionConflict(task.RowVersion);
        var assignment = await database.TaskAssignments.SingleOrDefaultAsync(x => x.Id == assignmentId && x.TaskId == id && x.UnassignedAtUtc == null, cancellationToken);
        if (assignment is null) return Results.NotFound();
        var actor = UserId(context.User); var now = clock.UtcNow;
        assignment.UnassignedAtUtc = now; assignment.UnassignedByUserId = actor; assignment.UnassignmentReason = request.Reason.Trim();
        task.UpdatedAtUtc = now; task.UpdatedByUserId = actor; task.RowVersion++;
        database.AuditEvents.Add(Audit(now, actor, "tasks.unassigned", task.Id, new { assignment.EmployeeId, assignment.AssignmentRole }, request.Reason));
        return await SaveMutationAsync(database, task.RowVersion, cancellationToken);
    }

    private static async Task<IResult> CommentAsync(Guid id, TaskCommentRequest request, HttpContext context, AppDbContext database, IClock clock, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.Body) || request.Body.Trim().Length > 4000) return Validation("body", "Comment must contain 1 to 4,000 characters.");
        var task = await ScopedTaskForMutationAsync(id, context.User, PermissionCodes.TasksComment, database, cancellationToken);
        if (task is null) return Results.NotFound();
        if (task.RowVersion != request.ExpectedVersion) return VersionConflict(task.RowVersion);
        var actor = UserId(context.User); var now = clock.UtcNow;
        var comment = new TaskComment { Id = Guid.NewGuid(), TaskId = id, AuthorUserId = actor, Body = request.Body.Trim(), CreatedAtUtc = now };
        database.TaskComments.Add(comment); task.UpdatedAtUtc = now; task.UpdatedByUserId = actor; task.RowVersion++;
        database.AuditEvents.Add(Audit(now, actor, "tasks.comment_added", task.Id, new { commentId = comment.Id }));
        var saved = await SaveMutationAsync(database, task.RowVersion, cancellationToken);
        return saved is IStatusCodeHttpResult { StatusCode: StatusCodes.Status204NoContent } ? Results.Created($"/api/v1/tasks/{id}#comment-{comment.Id}", new { comment.Id, task.RowVersion }) : saved;
    }

    private static async Task<Dictionary<string, string[]>> ValidateCreateAsync(TaskCreateRequest request, AppDbContext database, CancellationToken cancellationToken)
    {
        var values = new Dictionary<string, string?> { ["clientId"] = request.ClientId == Guid.Empty ? null : request.ClientId.ToString(), ["serviceId"] = request.ServiceId == Guid.Empty ? null : request.ServiceId.ToString(), ["clientServiceId"] = request.ClientServiceId?.ToString(), ["title"] = request.Title, ["dueDate"] = request.DueDate == default ? null : request.DueDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), ["priority"] = request.Priority, ["primaryAssigneeId"] = request.PrimaryAssigneeId?.ToString() };
        var required = await database.FieldDefinitions.AsNoTracking().Where(x => x.EntityType == "tasks.task" && x.IsActive && x.IsAdministratorRequired).Select(x => x.FieldKey).ToArrayAsync(cancellationToken);
        var errors = required.Where(key => !values.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value)).ToDictionary(key => key, _ => (string[])["This field is required by the administrator."]);
        if (string.IsNullOrWhiteSpace(request.Title) || request.Title.Trim().Length > 250) errors["title"] = ["Title must contain 1 to 250 characters."];
        if (!Priorities.Contains(NormalizePriority(request.Priority))) errors["priority"] = ["Priority must be LOW, NORMAL, HIGH, or URGENT."];
        if (request.PeriodEnd is not null && request.PeriodStart is not null && request.PeriodEnd < request.PeriodStart) errors["periodEnd"] = ["Period end cannot precede period start."];
        var clientActive = await database.Clients.AnyAsync(x => x.Id == request.ClientId && x.Status == "ACTIVE", cancellationToken);
        var service = await database.Services.AsNoTracking().SingleOrDefaultAsync(x => x.Id == request.ServiceId && x.IsActive, cancellationToken);
        if (!clientActive) errors["clientId"] = ["Choose an active client."]; if (service is null) errors["serviceId"] = ["Choose an active service."];
        if (request.ClientServiceId is not null)
        {
            var agreement = await database.ClientServices.AsNoTracking().SingleOrDefaultAsync(x => x.Id == request.ClientServiceId && x.IsActive, cancellationToken);
            if (agreement is null || agreement.ClientId != request.ClientId || agreement.ServiceId != request.ServiceId || agreement.GstRegistrationId != request.GstRegistrationId) errors["clientServiceId"] = ["The active agreement must match the selected client, service, and GSTIN scope."];
        }
        else if (request.GstRegistrationId is not null)
        {
            if (service is not null && !service.SupportsGstinScope) errors["gstRegistrationId"] = ["This service does not support GSTIN-specific work."];
            if (!await database.GstRegistrations.AnyAsync(x => x.Id == request.GstRegistrationId && x.ClientId == request.ClientId && x.IsActive, cancellationToken)) errors["gstRegistrationId"] = ["Choose an active GSTIN belonging to the client."];
        }
        var assignees = request.SecondaryAssigneeIds.Append(request.PrimaryAssigneeId ?? Guid.Empty).Where(x => x != Guid.Empty).Distinct().ToArray();
        if (await database.Employees.CountAsync(x => assignees.Contains(x.Id) && x.IsActive, cancellationToken) != assignees.Length) errors["assignees"] = ["Every assignee must be an active employee."];
        if (request.PrimaryAssigneeId is not null && request.SecondaryAssigneeIds.Contains(request.PrimaryAssigneeId.Value)) errors["secondaryAssigneeIds"] = ["The primary assignee cannot also be secondary."];
        return errors;
    }

    private static async Task<PracticeTask?> ScopedTaskForMutationAsync(Guid id, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var query = await ApplyTaskScopeAsync(database.Tasks.Where(x => x.Id == id), principal, permission, null, database, cancellationToken);
        return await query.SingleOrDefaultAsync(cancellationToken);
    }

    private static async Task<IResult?> ValidateCreationScopeAsync(Guid? clientServiceId, ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, PermissionCodes.TasksAssign);
        if (scope == "ALL") return null;
        if (clientServiceId is null) return ScopeDenied("A scoped creator must use an accessible client service agreement.");
        var teamId = await database.ClientServices.Where(x => x.Id == clientServiceId).Select(x => x.ResponsibleTeamId).SingleAsync(cancellationToken);
        if (teamId is null) return ScopeDenied("A responsible team is required for scoped task creation.");
        var teams = await AccessibleTeamIdsAsync(principal, scope ?? "OWN", database, cancellationToken);
        return teams.Contains(teamId.Value) ? null : ScopeDenied("The client service agreement is outside your task-creation scope.");
    }

    private static async Task<IQueryable<PracticeTask>> ApplyTaskScopeAsync(IQueryable<PracticeTask> query, ClaimsPrincipal principal, string permission, string? requestedView, AppDbContext database, CancellationToken cancellationToken)
    {
        var maximum = Scope(principal, permission) ?? "OWN"; var requested = requestedView?.Trim().ToLowerInvariant();
        if (maximum == "ALL" && (requested is null or "all")) return query;
        var ownEmployee = await CurrentEmployeeIdAsync(principal, database, cancellationToken);
        if (ownEmployee is null) return query.Where(_ => false);
        if (requested == "mine" || maximum == "OWN") return query.Where(x => x.Assignments.Any(a => a.EmployeeId == ownEmployee && a.UnassignedAtUtc == null));
        var employees = await AccessibleEmployeeIdsAsync(principal, maximum, database, cancellationToken);
        return query.Where(x => x.Assignments.Any(a => employees.Contains(a.EmployeeId) && a.UnassignedAtUtc == null));
    }

    private static async Task<bool> CanTargetEmployeeAsync(Guid employeeId, ClaimsPrincipal principal, string permission, AppDbContext database, CancellationToken cancellationToken)
    {
        var scope = Scope(principal, permission) ?? "OWN"; if (scope == "ALL") return true;
        var employees = await AccessibleEmployeeIdsAsync(principal, scope, database, cancellationToken); return employees.Contains(employeeId);
    }

    private static async Task<Guid[]> AccessibleEmployeeIdsAsync(ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var employeeId = await CurrentEmployeeIdAsync(principal, database, cancellationToken); if (employeeId is null) return [];
        if (scope == "OWN") return [employeeId.Value];
        var teamIds = await AccessibleTeamIdsAsync(principal, scope, database, cancellationToken);
        return await database.Employees.Where(x => x.IsActive && (x.Id == employeeId || x.ManagerEmployeeId == employeeId || database.TeamMemberships.Any(m => m.EmployeeId == x.Id && m.ValidTo == null && teamIds.Contains(m.TeamId)))).Select(x => x.Id).Distinct().ToArrayAsync(cancellationToken);
    }

    private static async Task<Guid[]> AccessibleTeamIdsAsync(ClaimsPrincipal principal, string scope, AppDbContext database, CancellationToken cancellationToken)
    {
        var employeeId = await CurrentEmployeeIdAsync(principal, database, cancellationToken); if (employeeId is null) return [];
        var query = database.TeamMemberships.Where(x => x.EmployeeId == employeeId && x.ValidTo == null).Select(x => x.TeamId);
        if (scope is "TEAM" or "ALL") query = query.Concat(database.Teams.Where(x => x.ManagerEmployeeId == employeeId && x.IsActive).Select(x => x.Id));
        return await query.Distinct().ToArrayAsync(cancellationToken);
    }

    private static async Task<Guid?> CurrentEmployeeIdAsync(ClaimsPrincipal principal, AppDbContext database, CancellationToken cancellationToken) =>
        await database.Employees.Where(x => x.UserId == UserId(principal) && x.IsActive).Select(x => (Guid?)x.Id).SingleOrDefaultAsync(cancellationToken);

    private static TaskAssignment NewAssignment(Guid taskId, Guid employeeId, string role, Guid actor, DateTimeOffset now, string? remarks) => new() { Id = Guid.NewGuid(), TaskId = taskId, EmployeeId = employeeId, AssignmentRole = role, AssignedAtUtc = now, AssignedByUserId = actor, Remarks = Clean(remarks) };
    private static async Task<IResult> SaveMutationAsync(AppDbContext database, long newVersion, CancellationToken cancellationToken) { try { await database.SaveChangesAsync(cancellationToken); return Results.NoContent(); } catch (DbUpdateConcurrencyException) { return Results.Conflict(new { message = "The task changed after it was loaded. Refresh and try again.", currentVersion = newVersion - 1 }); } }
    private static IResult VersionConflict(long current) => Results.Conflict(new { message = "The task changed after it was loaded. Refresh and try again.", currentVersion = current });
    private static IResult ScopeDenied(string detail) => Results.Problem(statusCode: 403, title: "Task scope denied", detail: detail);
    private static IResult Validation(string key, string message) => Results.ValidationProblem(new Dictionary<string, string[]> { [key] = [message] });
    private static string NormalizePriority(string? value) => string.IsNullOrWhiteSpace(value) ? "NORMAL" : value.Trim().ToUpperInvariant();
    private static string? Clean(string? value) => string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    private static string? Scope(ClaimsPrincipal principal, string permission) => principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
    private static AuditEvent Audit(DateTimeOffset at, Guid actor, string action, Guid id, object data, string? reason = null) => new() { Id = Guid.NewGuid(), OccurredAtUtc = at, ActorUserId = actor, Action = action, EntityType = "PracticeTask", EntityId = id.ToString(), Reason = Clean(reason), DataJson = JsonSerializer.Serialize(data) };
}

public sealed record TaskCreateRequest(Guid ClientId, Guid ServiceId, Guid? ClientServiceId, Guid? GstRegistrationId, string Title, string? Description, DateOnly? PeriodStart, DateOnly? PeriodEnd, DateOnly DueDate, string? Priority, bool? Billable, Guid? PrimaryAssigneeId, Guid[] SecondaryAssigneeIds, string? AssignmentRemarks);
public sealed record TaskStatusChangeRequest(Guid ToStatusId, string? Reason, string? CompletionNote, long ExpectedVersion);
public sealed record TaskAssignmentRequest(Guid EmployeeId, string Role, string? Remarks, long ExpectedVersion);
public sealed record TaskUnassignRequest(string Reason, long ExpectedVersion);
public sealed record TaskCommentRequest(string Body, long ExpectedVersion);
