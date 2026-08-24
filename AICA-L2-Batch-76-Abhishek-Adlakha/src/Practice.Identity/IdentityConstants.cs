namespace Practice.Identity;

public static class IdentityConstants
{
    public const string AuthenticationScheme = "PracticeSession";
    public const string SessionTokenClaim = "practice_session_token";
    public const string PermissionClaim = "permission";
    public const string ScopeClaimPrefix = "scope:";
    public const int MaximumFailedLogins = 5;
    public static readonly TimeSpan LockoutDuration = TimeSpan.FromMinutes(15);
    public static readonly TimeSpan SessionDuration = TimeSpan.FromHours(12);
}

public static class PermissionCodes
{
    public const string UsersView = "identity.users.view";
    public const string UsersManage = "identity.users.manage";
    public const string RolesView = "identity.roles.view";
    public const string RolesManage = "identity.roles.manage";
    public const string EmployeesView = "employees.view";
    public const string EmployeesManage = "employees.manage";
    public const string TeamsManage = "teams.manage";
    public const string FieldPoliciesManage = "settings.field_policies.manage";
    public const string DiagnosticsView = "system.diagnostics.view";
    public const string AuditView = "audit.view";
    public const string ClientsView = "clients.view";
    public const string ClientsCreate = "clients.create";
    public const string ClientsEdit = "clients.edit";
    public const string ClientsDeactivate = "clients.deactivate";
    public const string ServicesView = "services.view";
    public const string ServicesCatalogueManage = "services.catalogue.manage";
    public const string ServiceEnrollmentsView = "services.enrollments.view";
    public const string ServiceEnrollmentsManage = "services.enrollments.manage";
    public const string TasksView = "tasks.view";
    public const string TasksCreate = "tasks.create";
    public const string TasksAssign = "tasks.assign";
    public const string TasksChangeStatus = "tasks.change_status";
    public const string TasksReopen = "tasks.reopen";
    public const string TasksComment = "tasks.comment";
    public const string SchedulingView = "scheduling.view";
    public const string SchedulingManage = "scheduling.manage";
    public const string SchedulingGenerate = "scheduling.generate";
    public const string CalendarView = "calendar.view";
    public const string HolidaysManage = "scheduling.holidays.manage";
    public const string BillingView = "billing.view";
    public const string BillingConfigure = "billing.configure";
    public const string BillingProject = "billing.project";
    public const string ReportsView = "reports.view";
    public const string ReportsExport = "reports.export";
}
