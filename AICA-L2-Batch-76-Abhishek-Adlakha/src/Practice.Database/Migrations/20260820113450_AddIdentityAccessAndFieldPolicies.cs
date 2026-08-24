using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // EF migration scaffolding emits repeated constant column arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddIdentityAccessAndFieldPolicies : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "employees");

            migrationBuilder.EnsureSchema(
                name: "identity");

            migrationBuilder.CreateTable(
                name: "field_definitions",
                schema: "system",
                columns: table => new
                {
                    entity_type = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    field_key = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    label = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    description = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    is_system_required = table.Column<bool>(type: "boolean", nullable: false),
                    is_administrator_required = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_by_user_id = table.Column<Guid>(type: "uuid", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_field_definitions", x => new { x.entity_type, x.field_key });
                    table.CheckConstraint("ck_field_definitions_required", "NOT is_system_required OR is_administrator_required");
                });

            migrationBuilder.CreateTable(
                name: "permissions",
                schema: "identity",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: false),
                    module = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    action = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    description = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    supports_scope = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_permissions", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "roles",
                schema: "identity",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    description = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    is_system = table.Column<bool>(type: "boolean", nullable: false),
                    is_protected = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_roles", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "users",
                schema: "identity",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    mobile_username = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: false),
                    password_hash = table.Column<string>(type: "text", nullable: false),
                    security_stamp = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    must_change_password = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    failed_login_count = table.Column<int>(type: "integer", nullable: false),
                    locked_until_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    last_login_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_users", x => x.id);
                    table.CheckConstraint("ck_users_failed_login_count", "failed_login_count >= 0");
                    table.CheckConstraint("ck_users_mobile_username", "mobile_username ~ '^[0-9]{10}$'");
                });

            migrationBuilder.CreateTable(
                name: "role_permissions",
                schema: "identity",
                columns: table => new
                {
                    role_id = table.Column<Guid>(type: "uuid", nullable: false),
                    permission_id = table.Column<Guid>(type: "uuid", nullable: false),
                    scope_ceiling = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_role_permissions", x => new { x.role_id, x.permission_id });
                    table.CheckConstraint("ck_role_permissions_scope", "scope_ceiling IN ('OWN', 'TEAM', 'ALL')");
                    table.ForeignKey(
                        name: "fk_role_permissions_permission",
                        column: x => x.permission_id,
                        principalSchema: "identity",
                        principalTable: "permissions",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_role_permissions_role",
                        column: x => x.role_id,
                        principalSchema: "identity",
                        principalTable: "roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "employees",
                schema: "employees",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    employee_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    normalized_employee_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    display_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    email = table.Column<string>(type: "character varying(320)", maxLength: 320, nullable: true),
                    mobile_number = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: true),
                    designation = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    department = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    manager_employee_id = table.Column<Guid>(type: "uuid", nullable: true),
                    joined_on = table.Column<DateOnly>(type: "date", nullable: true),
                    left_on = table.Column<DateOnly>(type: "date", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_employees", x => x.id);
                    table.CheckConstraint("ck_employees_dates", "left_on IS NULL OR joined_on IS NULL OR left_on >= joined_on");
                    table.CheckConstraint("ck_employees_mobile", "mobile_number IS NULL OR mobile_number ~ '^[0-9]{10}$'");
                    table.ForeignKey(
                        name: "fk_employees_manager",
                        column: x => x.manager_employee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_employees_user",
                        column: x => x.user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "user_roles",
                schema: "identity",
                columns: table => new
                {
                    user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    role_id = table.Column<Guid>(type: "uuid", nullable: false),
                    assigned_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    assigned_by_user_id = table.Column<Guid>(type: "uuid", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_roles", x => new { x.user_id, x.role_id });
                    table.ForeignKey(
                        name: "fk_user_roles_role",
                        column: x => x.role_id,
                        principalSchema: "identity",
                        principalTable: "roles",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_user_roles_user",
                        column: x => x.user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "user_sessions",
                schema: "identity",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    token_hash = table.Column<byte[]>(type: "bytea", nullable: false),
                    security_stamp = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    last_seen_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    expires_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    revoked_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    revocation_reason = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: true),
                    ip_hash = table.Column<byte[]>(type: "bytea", nullable: true),
                    user_agent = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_user_sessions", x => x.id);
                    table.CheckConstraint("ck_user_sessions_token_hash", "octet_length(token_hash) = 32");
                    table.ForeignKey(
                        name: "fk_user_sessions_user",
                        column: x => x.user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "teams",
                schema: "employees",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    manager_employee_id = table.Column<Guid>(type: "uuid", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_teams", x => x.id);
                    table.ForeignKey(
                        name: "fk_teams_manager",
                        column: x => x.manager_employee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "team_memberships",
                schema: "employees",
                columns: table => new
                {
                    team_id = table.Column<Guid>(type: "uuid", nullable: false),
                    employee_id = table.Column<Guid>(type: "uuid", nullable: false),
                    valid_from = table.Column<DateOnly>(type: "date", nullable: false),
                    valid_to = table.Column<DateOnly>(type: "date", nullable: true),
                    is_lead = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_team_memberships", x => new { x.team_id, x.employee_id, x.valid_from });
                    table.CheckConstraint("ck_team_memberships_dates", "valid_to IS NULL OR valid_to >= valid_from");
                    table.ForeignKey(
                        name: "fk_team_memberships_employee",
                        column: x => x.employee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_team_memberships_team",
                        column: x => x.team_id,
                        principalSchema: "employees",
                        principalTable: "teams",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "field_key", "description", "is_active", "is_administrator_required", "is_system_required", "label", "updated_at_utc", "updated_by_user_id" },
                values: new object[,]
                {
                    { "employees.employee", "department", "Employee department.", true, false, false, "Department", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "designation", "Employee designation.", true, false, false, "Designation", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "displayName", "Employee display name.", true, true, true, "Employee name", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "email", "Employee email address.", true, false, false, "Email", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "employeeCode", "Stable firm employee code.", true, true, true, "Employee code", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "joinedOn", "Date employment commenced.", true, false, false, "Joining date", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "employees.employee", "mobileNumber", "Ten-digit login/contact mobile number.", true, true, true, "Mobile number", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "permissions",
                columns: new[] { "id", "action", "code", "description", "module", "supports_scope" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000001"), "View", "identity.users.view", "View user accounts.", "Identity", false },
                    { new Guid("20000000-0000-0000-0000-000000000002"), "Manage", "identity.users.manage", "Create, disable, and manage user accounts.", "Identity", false },
                    { new Guid("20000000-0000-0000-0000-000000000003"), "ViewRoles", "identity.roles.view", "View roles and permission assignments.", "Identity", false },
                    { new Guid("20000000-0000-0000-0000-000000000004"), "ManageRoles", "identity.roles.manage", "Create roles and configure permissions.", "Identity", false },
                    { new Guid("20000000-0000-0000-0000-000000000005"), "View", "employees.view", "View employees and teams.", "Employees", true },
                    { new Guid("20000000-0000-0000-0000-000000000006"), "Manage", "employees.manage", "Create and update employees.", "Employees", true },
                    { new Guid("20000000-0000-0000-0000-000000000007"), "ManageTeams", "teams.manage", "Create teams and manage memberships.", "Employees", true },
                    { new Guid("20000000-0000-0000-0000-000000000008"), "ManageFieldPolicies", "settings.field_policies.manage", "Configure administrator-required fields.", "System", false },
                    { new Guid("20000000-0000-0000-0000-000000000009"), "Diagnostics", "system.diagnostics.view", "View operational diagnostics.", "System", false },
                    { new Guid("20000000-0000-0000-0000-000000000010"), "View", "audit.view", "View audit history.", "Audit", false },
                    { new Guid("20000000-0000-0000-0000-000000000011"), "View", "clients.view", "View permitted clients.", "Clients", true },
                    { new Guid("20000000-0000-0000-0000-000000000012"), "Create", "clients.create", "Create clients.", "Clients", false },
                    { new Guid("20000000-0000-0000-0000-000000000013"), "Edit", "clients.edit", "Edit permitted clients.", "Clients", true },
                    { new Guid("20000000-0000-0000-0000-000000000014"), "Deactivate", "clients.deactivate", "Deactivate permitted clients.", "Clients", true },
                    { new Guid("20000000-0000-0000-0000-000000000015"), "View", "tasks.view", "View permitted tasks.", "Tasks", true },
                    { new Guid("20000000-0000-0000-0000-000000000016"), "Create", "tasks.create", "Create tasks.", "Tasks", false },
                    { new Guid("20000000-0000-0000-0000-000000000017"), "Assign", "tasks.assign", "Assign tasks.", "Tasks", true },
                    { new Guid("20000000-0000-0000-0000-000000000018"), "ChangeStatus", "tasks.change_status", "Change task status.", "Tasks", true },
                    { new Guid("20000000-0000-0000-0000-000000000019"), "View", "billing.view", "View permitted billing data.", "Billing", true },
                    { new Guid("20000000-0000-0000-0000-000000000020"), "Configure", "billing.configure", "Configure billing.", "Billing", false },
                    { new Guid("20000000-0000-0000-0000-000000000021"), "View", "reports.view", "View permitted reports.", "Reports", true },
                    { new Guid("20000000-0000-0000-0000-000000000022"), "Export", "reports.export", "Export permitted reports.", "Reports", true }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "roles",
                columns: new[] { "id", "code", "created_at_utc", "description", "is_active", "is_protected", "is_system", "name", "updated_at_utc" },
                values: new object[,]
                {
                    { new Guid("10000000-0000-0000-0000-000000000001"), "ADMINISTRATORS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Full system administration.", true, true, true, "Administrators", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("10000000-0000-0000-0000-000000000002"), "MANAGER", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Manages teams and firm work.", true, false, true, "Manager", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("10000000-0000-0000-0000-000000000003"), "ARTICLES", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Article assistants working on assigned engagements.", true, false, true, "Articles", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("10000000-0000-0000-0000-000000000004"), "PAID_ASSISTANTS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Paid assistants working on assigned engagements.", true, false, true, "Paid Assistants", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("10000000-0000-0000-0000-000000000005"), "ACCOUNTANTS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Firm accountants.", true, false, true, "Accountants", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("10000000-0000-0000-0000-000000000006"), "CLIENT_ACCOUNTANTS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "Accountants restricted to authorized client work.", true, false, true, "Client Accountants", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "role_permissions",
                columns: new[] { "permission_id", "role_id", "scope_ceiling" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000001"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000002"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000003"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000004"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000005"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000006"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000007"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000008"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000009"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000010"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000011"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000012"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000013"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000014"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000015"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000016"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000017"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000018"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000019"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000020"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000021"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000022"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" }
                });

            migrationBuilder.CreateIndex(
                name: "ix_employees_manager_active",
                schema: "employees",
                table: "employees",
                columns: new[] { "manager_employee_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_employees_name_active",
                schema: "employees",
                table: "employees",
                columns: new[] { "display_name", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ux_employees_code",
                schema: "employees",
                table: "employees",
                column: "normalized_employee_code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_employees_user",
                schema: "employees",
                table: "employees",
                column: "user_id",
                unique: true,
                filter: "user_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_field_definitions_entity_active",
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_permissions_module_action",
                schema: "identity",
                table: "permissions",
                columns: new[] { "module", "action" });

            migrationBuilder.CreateIndex(
                name: "ux_permissions_code",
                schema: "identity",
                table: "permissions",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_role_permissions_permission_role",
                schema: "identity",
                table: "role_permissions",
                columns: new[] { "permission_id", "role_id" });

            migrationBuilder.CreateIndex(
                name: "ux_roles_code",
                schema: "identity",
                table: "roles",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_roles_name",
                schema: "identity",
                table: "roles",
                column: "name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_team_memberships_employee_active",
                schema: "employees",
                table: "team_memberships",
                columns: new[] { "employee_id", "valid_to" });

            migrationBuilder.CreateIndex(
                name: "IX_teams_manager_employee_id",
                schema: "employees",
                table: "teams",
                column: "manager_employee_id");

            migrationBuilder.CreateIndex(
                name: "ux_teams_code",
                schema: "employees",
                table: "teams",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_teams_name",
                schema: "employees",
                table: "teams",
                column: "name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_user_roles_role_user",
                schema: "identity",
                table: "user_roles",
                columns: new[] { "role_id", "user_id" });

            migrationBuilder.CreateIndex(
                name: "ix_user_sessions_expires",
                schema: "identity",
                table: "user_sessions",
                column: "expires_at_utc");

            migrationBuilder.CreateIndex(
                name: "ix_user_sessions_user_active",
                schema: "identity",
                table: "user_sessions",
                columns: new[] { "user_id", "revoked_at_utc" });

            migrationBuilder.CreateIndex(
                name: "ux_user_sessions_token_hash",
                schema: "identity",
                table: "user_sessions",
                column: "token_hash",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_users_active",
                schema: "identity",
                table: "users",
                column: "is_active");

            migrationBuilder.CreateIndex(
                name: "ux_users_mobile_username",
                schema: "identity",
                table: "users",
                column: "mobile_username",
                unique: true);

            migrationBuilder.Sql("""
                DO $permissions$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA identity, employees TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA identity, employees TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA identity, employees TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON system.field_definitions TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA identity
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA employees
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END
                $permissions$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "field_definitions",
                schema: "system");

            migrationBuilder.DropTable(
                name: "role_permissions",
                schema: "identity");

            migrationBuilder.DropTable(
                name: "team_memberships",
                schema: "employees");

            migrationBuilder.DropTable(
                name: "user_roles",
                schema: "identity");

            migrationBuilder.DropTable(
                name: "user_sessions",
                schema: "identity");

            migrationBuilder.DropTable(
                name: "permissions",
                schema: "identity");

            migrationBuilder.DropTable(
                name: "teams",
                schema: "employees");

            migrationBuilder.DropTable(
                name: "roles",
                schema: "identity");

            migrationBuilder.DropTable(
                name: "employees",
                schema: "employees");

            migrationBuilder.DropTable(
                name: "users",
                schema: "identity");
        }
    }
}
