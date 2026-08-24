using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddTaskLifecycleAndAssignments : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "tasks");

            migrationBuilder.AddUniqueConstraint(
                name: "ak_client_services_id_client_service",
                schema: "services",
                table: "client_services",
                columns: new[] { "id", "client_id", "service_id" });

            migrationBuilder.CreateTable(
                name: "task_statuses",
                schema: "tasks",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    label = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    color = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    display_order = table.Column<int>(type: "integer", nullable: false),
                    is_terminal = table.Column<bool>(type: "boolean", nullable: false),
                    counts_as_complete = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_task_statuses", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "task_status_transitions",
                schema: "tasks",
                columns: table => new
                {
                    from_status_id = table.Column<Guid>(type: "uuid", nullable: false),
                    to_status_id = table.Column<Guid>(type: "uuid", nullable: false),
                    required_permission = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: false),
                    reason_required = table.Column<bool>(type: "boolean", nullable: false),
                    completion_data_required = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_task_status_transitions", x => new { x.from_status_id, x.to_status_id });
                    table.ForeignKey(
                        name: "fk_task_transitions_from_status",
                        column: x => x.from_status_id,
                        principalSchema: "tasks",
                        principalTable: "task_statuses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_transitions_to_status",
                        column: x => x.to_status_id,
                        principalSchema: "tasks",
                        principalTable: "task_statuses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "tasks",
                schema: "tasks",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    task_number = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    service_id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_service_id = table.Column<Guid>(type: "uuid", nullable: true),
                    gst_registration_id = table.Column<Guid>(type: "uuid", nullable: true),
                    title = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    description = table.Column<string>(type: "character varying(4000)", maxLength: 4000, nullable: true),
                    period_start = table.Column<DateOnly>(type: "date", nullable: true),
                    period_end = table.Column<DateOnly>(type: "date", nullable: true),
                    due_date = table.Column<DateOnly>(type: "date", nullable: false),
                    status_id = table.Column<Guid>(type: "uuid", nullable: false),
                    priority = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    billable_snapshot = table.Column<bool>(type: "boolean", nullable: false),
                    completed_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    completed_by_user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    cancelled_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    cancelled_by_user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    cancellation_reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    reopened_count = table.Column<int>(type: "integer", nullable: false),
                    created_source = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    created_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    row_version = table.Column<long>(type: "bigint", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_tasks", x => x.id);
                    table.CheckConstraint("ck_tasks_cancelled_metadata", "(cancelled_at_utc IS NULL AND cancelled_by_user_id IS NULL AND cancellation_reason IS NULL) OR (cancelled_at_utc IS NOT NULL AND cancelled_by_user_id IS NOT NULL AND length(trim(cancellation_reason)) > 0)");
                    table.CheckConstraint("ck_tasks_completed_metadata", "(completed_at_utc IS NULL AND completed_by_user_id IS NULL) OR (completed_at_utc IS NOT NULL AND completed_by_user_id IS NOT NULL)");
                    table.CheckConstraint("ck_tasks_period", "period_end IS NULL OR period_start IS NULL OR period_end >= period_start");
                    table.CheckConstraint("ck_tasks_priority", "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
                    table.CheckConstraint("ck_tasks_row_version", "row_version > 0");
                    table.CheckConstraint("ck_tasks_source", "created_source IN ('MANUAL', 'RECURRENCE', 'IMPORT')");
                    table.ForeignKey(
                        name: "fk_tasks_cancelled_by",
                        column: x => x.cancelled_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_client_service_scope",
                        columns: x => new { x.client_service_id, x.client_id, x.service_id },
                        principalSchema: "services",
                        principalTable: "client_services",
                        principalColumns: new[] { "id", "client_id", "service_id" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_completed_by",
                        column: x => x.completed_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_created_by",
                        column: x => x.created_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_gstin_client",
                        columns: x => new { x.gst_registration_id, x.client_id },
                        principalSchema: "clients",
                        principalTable: "gst_registrations",
                        principalColumns: new[] { "id", "client_id" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_service",
                        column: x => x.service_id,
                        principalSchema: "services",
                        principalTable: "services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_status",
                        column: x => x.status_id,
                        principalSchema: "tasks",
                        principalTable: "task_statuses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_tasks_updated_by",
                        column: x => x.updated_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "task_assignments",
                schema: "tasks",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    task_id = table.Column<Guid>(type: "uuid", nullable: false),
                    employee_id = table.Column<Guid>(type: "uuid", nullable: false),
                    assignment_role = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    assigned_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    assigned_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    unassigned_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    unassigned_by_user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    remarks = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    unassignment_reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_task_assignments", x => x.id);
                    table.CheckConstraint("ck_task_assignments_role", "assignment_role IN ('PRIMARY', 'SECONDARY', 'REVIEWER')");
                    table.CheckConstraint("ck_task_assignments_unassigned", "(unassigned_at_utc IS NULL AND unassigned_by_user_id IS NULL AND unassignment_reason IS NULL) OR (unassigned_at_utc IS NOT NULL AND unassigned_by_user_id IS NOT NULL AND length(trim(unassignment_reason)) > 0)");
                    table.ForeignKey(
                        name: "fk_task_assignments_assigned_by",
                        column: x => x.assigned_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_assignments_employee",
                        column: x => x.employee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_assignments_task",
                        column: x => x.task_id,
                        principalSchema: "tasks",
                        principalTable: "tasks",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_assignments_unassigned_by",
                        column: x => x.unassigned_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "task_comments",
                schema: "tasks",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    task_id = table.Column<Guid>(type: "uuid", nullable: false),
                    author_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    body = table.Column<string>(type: "character varying(4000)", maxLength: 4000, nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    edited_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    is_redacted = table.Column<bool>(type: "boolean", nullable: false),
                    redacted_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    redacted_by_user_id = table.Column<Guid>(type: "uuid", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_task_comments", x => x.id);
                    table.CheckConstraint("ck_task_comments_redaction", "(NOT is_redacted AND redacted_at_utc IS NULL AND redacted_by_user_id IS NULL) OR (is_redacted AND redacted_at_utc IS NOT NULL AND redacted_by_user_id IS NOT NULL)");
                    table.ForeignKey(
                        name: "fk_task_comments_author",
                        column: x => x.author_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_comments_redacted_by",
                        column: x => x.redacted_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_comments_task",
                        column: x => x.task_id,
                        principalSchema: "tasks",
                        principalTable: "tasks",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "task_status_history",
                schema: "tasks",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    task_id = table.Column<Guid>(type: "uuid", nullable: false),
                    from_status_id = table.Column<Guid>(type: "uuid", nullable: true),
                    to_status_id = table.Column<Guid>(type: "uuid", nullable: false),
                    actor_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    changed_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    completion_note = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    metadata_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_task_status_history", x => x.id);
                    table.ForeignKey(
                        name: "fk_task_history_actor",
                        column: x => x.actor_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_history_from_status",
                        column: x => x.from_status_id,
                        principalSchema: "tasks",
                        principalTable: "task_statuses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_history_task",
                        column: x => x.task_id,
                        principalSchema: "tasks",
                        principalTable: "tasks",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_task_history_to_status",
                        column: x => x.to_status_id,
                        principalSchema: "tasks",
                        principalTable: "task_statuses",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "field_key", "description", "is_active", "is_administrator_required", "is_system_required", "label", "updated_at_utc", "updated_by_user_id" },
                values: new object[,]
                {
                    { "tasks.task", "clientId", "Client for whom the work is performed.", true, true, true, "Client", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "clientServiceId", "Optional agreement supplying task context.", true, false, false, "Client service agreement", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "dueDate", "Operational due date for the work item.", true, true, true, "Due date", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "primaryAssigneeId", "Employee accountable for the task.", true, true, false, "Primary assignee", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "priority", "Operational priority for the work item.", true, false, false, "Priority", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "serviceId", "Service represented by the task.", true, true, true, "Service", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "tasks.task", "title", "Concise description of the work item.", true, true, true, "Task title", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "permissions",
                columns: new[] { "id", "action", "code", "description", "module", "supports_scope" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000027"), "Reopen", "tasks.reopen", "Reopen completed or cancelled tasks with a reason.", "Tasks", true },
                    { new Guid("20000000-0000-0000-0000-000000000028"), "Comment", "tasks.comment", "Add comments to permitted tasks.", "Tasks", true }
                });

            migrationBuilder.InsertData(
                schema: "tasks",
                table: "task_statuses",
                columns: new[] { "id", "code", "color", "counts_as_complete", "display_order", "is_active", "is_terminal", "label" },
                values: new object[,]
                {
                    { new Guid("50000000-0000-0000-0000-000000000001"), "NOT_STARTED", "#64748b", false, 10, true, false, "Not Started" },
                    { new Guid("50000000-0000-0000-0000-000000000002"), "IN_PROCESS", "#2563eb", false, 20, true, false, "In Process" },
                    { new Guid("50000000-0000-0000-0000-000000000003"), "ON_HOLD", "#d97706", false, 30, true, false, "On Hold" },
                    { new Guid("50000000-0000-0000-0000-000000000004"), "COMPLETED", "#059669", true, 40, true, true, "Completed" },
                    { new Guid("50000000-0000-0000-0000-000000000005"), "CANCELLED", "#dc2626", false, 50, true, true, "Cancelled" }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "role_permissions",
                columns: new[] { "permission_id", "role_id", "scope_ceiling" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000027"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000028"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" }
                });

            migrationBuilder.InsertData(
                schema: "tasks",
                table: "task_status_transitions",
                columns: new[] { "from_status_id", "to_status_id", "completion_data_required", "reason_required", "required_permission" },
                values: new object[,]
                {
                    { new Guid("50000000-0000-0000-0000-000000000001"), new Guid("50000000-0000-0000-0000-000000000002"), false, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000001"), new Guid("50000000-0000-0000-0000-000000000003"), false, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000001"), new Guid("50000000-0000-0000-0000-000000000004"), true, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000001"), new Guid("50000000-0000-0000-0000-000000000005"), false, true, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000002"), new Guid("50000000-0000-0000-0000-000000000003"), false, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000002"), new Guid("50000000-0000-0000-0000-000000000004"), true, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000002"), new Guid("50000000-0000-0000-0000-000000000005"), false, true, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000003"), new Guid("50000000-0000-0000-0000-000000000002"), false, false, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000003"), new Guid("50000000-0000-0000-0000-000000000005"), false, true, "tasks.change_status" },
                    { new Guid("50000000-0000-0000-0000-000000000004"), new Guid("50000000-0000-0000-0000-000000000002"), false, true, "tasks.reopen" },
                    { new Guid("50000000-0000-0000-0000-000000000005"), new Guid("50000000-0000-0000-0000-000000000001"), false, true, "tasks.reopen" }
                });

            migrationBuilder.CreateIndex(
                name: "IX_task_assignments_assigned_by_user_id",
                schema: "tasks",
                table: "task_assignments",
                column: "assigned_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_task_assignments_employee_active",
                schema: "tasks",
                table: "task_assignments",
                columns: new[] { "employee_id", "unassigned_at_utc", "task_id" });

            migrationBuilder.CreateIndex(
                name: "IX_task_assignments_unassigned_by_user_id",
                schema: "tasks",
                table: "task_assignments",
                column: "unassigned_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ux_task_assignments_current_employee_role",
                schema: "tasks",
                table: "task_assignments",
                columns: new[] { "task_id", "employee_id", "assignment_role" },
                unique: true,
                filter: "unassigned_at_utc IS NULL");

            migrationBuilder.CreateIndex(
                name: "ux_task_assignments_current_primary",
                schema: "tasks",
                table: "task_assignments",
                column: "task_id",
                unique: true,
                filter: "unassigned_at_utc IS NULL AND assignment_role = 'PRIMARY'");

            migrationBuilder.CreateIndex(
                name: "IX_task_comments_author_user_id",
                schema: "tasks",
                table: "task_comments",
                column: "author_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_task_comments_redacted_by_user_id",
                schema: "tasks",
                table: "task_comments",
                column: "redacted_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_task_comments_task_created",
                schema: "tasks",
                table: "task_comments",
                columns: new[] { "task_id", "created_at_utc" });

            migrationBuilder.CreateIndex(
                name: "ix_task_history_status_changed",
                schema: "tasks",
                table: "task_status_history",
                columns: new[] { "to_status_id", "changed_at_utc" });

            migrationBuilder.CreateIndex(
                name: "ix_task_history_task_changed",
                schema: "tasks",
                table: "task_status_history",
                columns: new[] { "task_id", "changed_at_utc" },
                descending: new[] { false, true });

            migrationBuilder.CreateIndex(
                name: "IX_task_status_history_actor_user_id",
                schema: "tasks",
                table: "task_status_history",
                column: "actor_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_task_status_history_from_status_id",
                schema: "tasks",
                table: "task_status_history",
                column: "from_status_id");

            migrationBuilder.CreateIndex(
                name: "IX_task_status_transitions_to_status_id",
                schema: "tasks",
                table: "task_status_transitions",
                column: "to_status_id");

            migrationBuilder.CreateIndex(
                name: "ix_task_statuses_active_order",
                schema: "tasks",
                table: "task_statuses",
                columns: new[] { "is_active", "display_order" });

            migrationBuilder.CreateIndex(
                name: "ux_task_statuses_code",
                schema: "tasks",
                table: "task_statuses",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_tasks_cancelled_by_user_id",
                schema: "tasks",
                table: "tasks",
                column: "cancelled_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_tasks_client_due",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "client_id", "due_date" });

            migrationBuilder.CreateIndex(
                name: "IX_tasks_client_service_id_client_id_service_id",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "client_service_id", "client_id", "service_id" });

            migrationBuilder.CreateIndex(
                name: "ix_tasks_client_service_period",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "client_service_id", "period_start" });

            migrationBuilder.CreateIndex(
                name: "IX_tasks_completed_by_user_id",
                schema: "tasks",
                table: "tasks",
                column: "completed_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_tasks_created",
                schema: "tasks",
                table: "tasks",
                column: "created_at_utc");

            migrationBuilder.CreateIndex(
                name: "IX_tasks_created_by_user_id",
                schema: "tasks",
                table: "tasks",
                column: "created_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_tasks_due_status",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "due_date", "status_id" });

            migrationBuilder.CreateIndex(
                name: "IX_tasks_gst_registration_id_client_id",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "gst_registration_id", "client_id" });

            migrationBuilder.CreateIndex(
                name: "ix_tasks_open_due",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "status_id", "due_date" },
                filter: "status_id IN ('50000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000003')");

            migrationBuilder.CreateIndex(
                name: "ix_tasks_service_due",
                schema: "tasks",
                table: "tasks",
                columns: new[] { "service_id", "due_date" });

            migrationBuilder.CreateIndex(
                name: "IX_tasks_updated_by_user_id",
                schema: "tasks",
                table: "tasks",
                column: "updated_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ux_tasks_number",
                schema: "tasks",
                table: "tasks",
                column: "task_number",
                unique: true);

            migrationBuilder.Sql(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA tasks TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tasks TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tasks TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA tasks
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END $$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "task_assignments",
                schema: "tasks");

            migrationBuilder.DropTable(
                name: "task_comments",
                schema: "tasks");

            migrationBuilder.DropTable(
                name: "task_status_history",
                schema: "tasks");

            migrationBuilder.DropTable(
                name: "task_status_transitions",
                schema: "tasks");

            migrationBuilder.DropTable(
                name: "tasks",
                schema: "tasks");

            migrationBuilder.DropTable(
                name: "task_statuses",
                schema: "tasks");

            migrationBuilder.DropUniqueConstraint(
                name: "ak_client_services_id_client_service",
                schema: "services",
                table: "client_services");

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "clientId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "clientServiceId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "dueDate" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "primaryAssigneeId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "priority" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "serviceId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "tasks.task", "title" });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000027"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000028"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000027"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000028"));
        }
    }
}
