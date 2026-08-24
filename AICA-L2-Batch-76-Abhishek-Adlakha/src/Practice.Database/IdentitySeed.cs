using Practice.Database.Entities;

namespace Practice.Database;

public static class IdentitySeed
{
    public static readonly Guid AdministratorsRoleId = new("10000000-0000-0000-0000-000000000001");
    public static readonly DateTimeOffset SeedTimestamp = new(2026, 8, 20, 0, 0, 0, TimeSpan.Zero);

    public static readonly Role[] Roles =
    [
        Role("10000000-0000-0000-0000-000000000001", "ADMINISTRATORS", "Administrators", "Full system administration.", true),
        Role("10000000-0000-0000-0000-000000000002", "MANAGER", "Manager", "Manages teams and firm work."),
        Role("10000000-0000-0000-0000-000000000003", "ARTICLES", "Articles", "Article assistants working on assigned engagements."),
        Role("10000000-0000-0000-0000-000000000004", "PAID_ASSISTANTS", "Paid Assistants", "Paid assistants working on assigned engagements."),
        Role("10000000-0000-0000-0000-000000000005", "ACCOUNTANTS", "Accountants", "Firm accountants."),
        Role("10000000-0000-0000-0000-000000000006", "CLIENT_ACCOUNTANTS", "Client Accountants", "Accountants restricted to authorized client work.")
    ];

    public static readonly PermissionDefinition[] Permissions =
    [
        Permission("20000000-0000-0000-0000-000000000001", "identity.users.view", "Identity", "View", "View user accounts."),
        Permission("20000000-0000-0000-0000-000000000002", "identity.users.manage", "Identity", "Manage", "Create, disable, and manage user accounts."),
        Permission("20000000-0000-0000-0000-000000000003", "identity.roles.view", "Identity", "ViewRoles", "View roles and permission assignments."),
        Permission("20000000-0000-0000-0000-000000000004", "identity.roles.manage", "Identity", "ManageRoles", "Create roles and configure permissions."),
        Permission("20000000-0000-0000-0000-000000000005", "employees.view", "Employees", "View", "View employees and teams.", true),
        Permission("20000000-0000-0000-0000-000000000006", "employees.manage", "Employees", "Manage", "Create and update employees.", true),
        Permission("20000000-0000-0000-0000-000000000007", "teams.manage", "Employees", "ManageTeams", "Create teams and manage memberships.", true),
        Permission("20000000-0000-0000-0000-000000000008", "settings.field_policies.manage", "System", "ManageFieldPolicies", "Configure administrator-required fields."),
        Permission("20000000-0000-0000-0000-000000000009", "system.diagnostics.view", "System", "Diagnostics", "View operational diagnostics."),
        Permission("20000000-0000-0000-0000-000000000010", "audit.view", "Audit", "View", "View audit history."),
        Permission("20000000-0000-0000-0000-000000000011", "clients.view", "Clients", "View", "View permitted clients.", true),
        Permission("20000000-0000-0000-0000-000000000012", "clients.create", "Clients", "Create", "Create clients."),
        Permission("20000000-0000-0000-0000-000000000013", "clients.edit", "Clients", "Edit", "Edit permitted clients.", true),
        Permission("20000000-0000-0000-0000-000000000014", "clients.deactivate", "Clients", "Deactivate", "Deactivate permitted clients.", true),
        Permission("20000000-0000-0000-0000-000000000015", "tasks.view", "Tasks", "View", "View permitted tasks.", true),
        Permission("20000000-0000-0000-0000-000000000016", "tasks.create", "Tasks", "Create", "Create tasks."),
        Permission("20000000-0000-0000-0000-000000000017", "tasks.assign", "Tasks", "Assign", "Assign tasks.", true),
        Permission("20000000-0000-0000-0000-000000000018", "tasks.change_status", "Tasks", "ChangeStatus", "Change task status.", true),
        Permission("20000000-0000-0000-0000-000000000019", "billing.view", "Billing", "View", "View permitted billing data.", true),
        Permission("20000000-0000-0000-0000-000000000020", "billing.configure", "Billing", "Configure", "Configure billing entities and permitted client-service fee terms.", true),
        Permission("20000000-0000-0000-0000-000000000021", "reports.view", "Reports", "View", "View permitted reports.", true),
        Permission("20000000-0000-0000-0000-000000000022", "reports.export", "Reports", "Export", "Export permitted reports.", true),
        Permission("20000000-0000-0000-0000-000000000023", "services.view", "Services", "ViewCatalogue", "View the service catalogue."),
        Permission("20000000-0000-0000-0000-000000000024", "services.catalogue.manage", "Services", "ManageCatalogue", "Create and safely deactivate service definitions."),
        Permission("20000000-0000-0000-0000-000000000025", "services.enrollments.view", "Services", "ViewEnrollments", "View permitted client service agreements.", true),
        Permission("20000000-0000-0000-0000-000000000026", "services.enrollments.manage", "Services", "ManageEnrollments", "Configure permitted client service agreements.", true),
        Permission("20000000-0000-0000-0000-000000000027", "tasks.reopen", "Tasks", "Reopen", "Reopen completed or cancelled tasks with a reason.", true),
        Permission("20000000-0000-0000-0000-000000000028", "tasks.comment", "Tasks", "Comment", "Add comments to permitted tasks.", true),
        Permission("20000000-0000-0000-0000-000000000029", "scheduling.view", "Scheduling", "View", "View recurrence rules and generator health for permitted client work.", true),
        Permission("20000000-0000-0000-0000-000000000030", "scheduling.manage", "Scheduling", "Manage", "Create and version recurrence rules for permitted client work.", true),
        Permission("20000000-0000-0000-0000-000000000031", "scheduling.generate", "Scheduling", "Generate", "Run the recurrence generator on demand."),
        Permission("20000000-0000-0000-0000-000000000032", "calendar.view", "Calendar", "View", "View permitted tasks in calendar and agenda form.", true),
        Permission("20000000-0000-0000-0000-000000000033", "scheduling.holidays.manage", "Scheduling", "ManageHolidays", "Maintain firm holidays and working-day overrides."),
        Permission("20000000-0000-0000-0000-000000000034", "billing.project", "Billing", "Project", "Calculate and inspect expected billing for permitted client services.", true)
    ];

    public static readonly RolePermissionGrant[] AdministratorPermissions = Permissions.Select(permission => new RolePermissionGrant
    {
        RoleId = AdministratorsRoleId,
        PermissionId = permission.Id,
        ScopeCeiling = "ALL"
    }).ToArray();

    public static readonly FieldDefinition[] EmployeeFields =
    [
        Field("employees.employee", "employeeCode", "Employee code", "Stable firm employee code.", true, true),
        Field("employees.employee", "displayName", "Employee name", "Employee display name.", true, true),
        Field("employees.employee", "mobileNumber", "Mobile number", "Ten-digit login/contact mobile number.", true, true),
        Field("employees.employee", "email", "Email", "Employee email address.", false, false),
        Field("employees.employee", "designation", "Designation", "Employee designation.", false, false),
        Field("employees.employee", "department", "Department", "Employee department.", false, false),
        Field("employees.employee", "joinedOn", "Joining date", "Date employment commenced.", false, false)
    ];

    public static readonly FieldDefinition[] ClientFields =
    [
        Field("clients.client", "clientCode", "Client code", "Stable firm client code.", true, true),
        Field("clients.client", "displayName", "Client name", "Name used in lists and work allocation.", true, true),
        Field("clients.client", "legalName", "Legal name", "Registered legal name, where different.", false, false),
        Field("clients.client", "categoryId", "Client category", "Legal constitution such as Individual, LLP or Company.", false, true),
        Field("clients.client", "pan", "PAN", "Permanent Account Number.", false, false),
        Field("clients.client", "tan", "TAN", "Tax Deduction and Collection Account Number.", false, false),
        Field("clients.client", "onboardedOn", "Onboarding date", "Date the client engagement began.", false, false),
        Field("clients.client", "primaryContact", "Primary contact", "At least one primary contact.", false, false),
        Field("clients.client", "primaryAddress", "Primary address", "At least one primary address.", false, false)
    ];

    public static readonly FieldDefinition[] ClientServiceFields =
    [
        Field("services.client_service", "clientId", "Client", "Client receiving the service.", true, true),
        Field("services.client_service", "serviceId", "Service", "Catalogue service being enrolled.", true, true),
        Field("services.client_service", "effectiveFrom", "Effective from", "Date the service agreement begins.", true, true),
        Field("services.client_service", "defaultPriority", "Default priority", "Priority copied to future generated work.", false, false),
        Field("services.client_service", "responsibleTeamId", "Responsible team", "Team responsible for this client service.", false, false)
    ];

    public static readonly FieldDefinition[] TaskFields =
    [
        Field("tasks.task", "clientId", "Client", "Client for whom the work is performed.", true, true),
        Field("tasks.task", "serviceId", "Service", "Service represented by the task.", true, true),
        Field("tasks.task", "clientServiceId", "Client service agreement", "Optional agreement supplying task context.", false, false),
        Field("tasks.task", "title", "Task title", "Concise description of the work item.", true, true),
        Field("tasks.task", "dueDate", "Due date", "Operational due date for the work item.", true, true),
        Field("tasks.task", "priority", "Priority", "Operational priority for the work item.", false, false),
        Field("tasks.task", "primaryAssigneeId", "Primary assignee", "Employee accountable for the task.", false, true)
    ];

    public static readonly FieldDefinition[] BillingFields =
    [
        Field("billing.billing_entity", "code", "Billing entity code", "Stable code for the legal invoicing entity.", true, true),
        Field("billing.billing_entity", "legalName", "Legal name", "Registered legal name of the billing entity.", true, true),
        Field("billing.billing_entity", "tradeName", "Trade name", "Public or trading name, where different.", false, false),
        Field("billing.billing_entity", "pan", "PAN", "Permanent Account Number of the billing entity.", false, false),
        Field("billing.billing_entity", "gstin", "GSTIN", "GST registration used by the billing entity.", false, false),
        Field("billing.billing_entity", "address", "Address", "Registered or invoicing address.", false, false),
        Field("billing.billing_entity", "email", "Email", "Billing contact email.", false, false),
        Field("billing.billing_entity", "phone", "Phone", "Billing contact phone number.", false, false),
        Field("billing.billing_entity", "currencyCode", "Currency", "Three-letter currency code for this billing entity.", true, true),
        Field("billing.billing_entity", "effectiveFrom", "Effective from", "Date from which the legal billing entity may be used.", true, true),
        Field("billing.billing_term", "clientServiceId", "Client service agreement", "Agreement receiving the commercial term.", true, true),
        Field("billing.billing_term", "isBillable", "Billable status", "Whether the agreement is charged or explicitly non-billable.", true, true),
        Field("billing.billing_term", "effectiveFrom", "Effective from", "Date from which the commercial term applies.", true, true),
        Field("billing.billing_term", "notes", "Fee notes", "Commercial notes explaining the agreed fee.", false, false)
    ];

    private static Role Role(string id, string code, string name, string description, bool isProtected = false) => new()
    {
        Id = Guid.Parse(id), Code = code, Name = name, Description = description,
        IsSystem = true, IsProtected = isProtected, IsActive = true,
        CreatedAtUtc = SeedTimestamp, UpdatedAtUtc = SeedTimestamp
    };

    private static PermissionDefinition Permission(string id, string code, string module, string action, string description, bool supportsScope = false) => new()
    {
        Id = Guid.Parse(id), Code = code, Module = module, Action = action,
        Description = description, SupportsScope = supportsScope
    };

    private static FieldDefinition Field(string entityType, string key, string label, string description, bool systemRequired, bool administratorRequired) => new()
    {
        EntityType = entityType, FieldKey = key, Label = label, Description = description,
        IsSystemRequired = systemRequired, IsAdministratorRequired = administratorRequired,
        IsActive = true, UpdatedAtUtc = SeedTimestamp
    };
}
