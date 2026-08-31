using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1825 // Generated migration uses framework-required array arguments
#pragma warning disable CA1861 // Generated migration constants are intentionally local

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddRecurringSchedulingAndCalendar : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "scheduling");

            migrationBuilder.AlterColumn<Guid>(
                name: "updated_by_user_id",
                schema: "tasks",
                table: "tasks",
                type: "uuid",
                nullable: true,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<Guid>(
                name: "created_by_user_id",
                schema: "tasks",
                table: "tasks",
                type: "uuid",
                nullable: true,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AddColumn<string>(
                name: "occurrence_key",
                schema: "tasks",
                table: "tasks",
                type: "character varying(160)",
                maxLength: 160,
                nullable: true);

            migrationBuilder.AddColumn<Guid>(
                name: "recurrence_rule_id",
                schema: "tasks",
                table: "tasks",
                type: "uuid",
                nullable: true);

            migrationBuilder.AlterColumn<Guid>(
                name: "actor_user_id",
                schema: "tasks",
                table: "task_status_history",
                type: "uuid",
                nullable: true,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.AlterColumn<Guid>(
                name: "assigned_by_user_id",
                schema: "tasks",
                table: "task_assignments",
                type: "uuid",
                nullable: true,
                oldClrType: typeof(Guid),
                oldType: "uuid");

            migrationBuilder.CreateTable(
                name: "generation_runs",
                schema: "scheduling",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    window_from = table.Column<DateOnly>(type: "date", nullable: false),
                    window_to = table.Column<DateOnly>(type: "date", nullable: false),
                    trigger = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    status = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    worker_id = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    triggered_by_user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    started_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    finished_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    created_count = table.Column<int>(type: "integer", nullable: false),
                    existing_count = table.Column<int>(type: "integer", nullable: false),
                    skipped_count = table.Column<int>(type: "integer", nullable: false),
                    error_count = table.Column<int>(type: "integer", nullable: false),
                    error_summary = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_generation_runs", x => x.id);
                    table.CheckConstraint("ck_generation_runs_counts", "created_count >= 0 AND existing_count >= 0 AND skipped_count >= 0 AND error_count >= 0");
                    table.CheckConstraint("ck_generation_runs_status", "status IN ('RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'SKIPPED_LOCKED')");
                    table.CheckConstraint("ck_generation_runs_trigger", "trigger IN ('MANUAL', 'SCHEDULED')");
                    table.CheckConstraint("ck_generation_runs_window", "window_to >= window_from");
                    table.ForeignKey(
                        name: "fk_generation_runs_triggered_by",
                        column: x => x.triggered_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "recurrence_rules",
                schema: "scheduling",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_service_id = table.Column<Guid>(type: "uuid", nullable: false),
                    holiday_calendar_id = table.Column<Guid>(type: "uuid", nullable: false),
                    default_primary_assignee_id = table.Column<Guid>(type: "uuid", nullable: true),
                    frequency_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    interval_count = table.Column<short>(type: "smallint", nullable: false),
                    anchor_date = table.Column<DateOnly>(type: "date", nullable: false),
                    due_rule_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    due_day = table.Column<short>(type: "smallint", nullable: false),
                    due_month_offset = table.Column<short>(type: "smallint", nullable: false),
                    due_day_offset = table.Column<short>(type: "smallint", nullable: false),
                    business_day_adjustment = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    generate_lead_days = table.Column<short>(type: "smallint", nullable: false),
                    time_zone_id = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: false),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    rule_version = table.Column<int>(type: "integer", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    row_version = table.Column<long>(type: "bigint", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_recurrence_rules", x => x.id);
                    table.CheckConstraint("ck_recurrence_rules_business_day", "business_day_adjustment IN ('NONE', 'PREVIOUS_BUSINESS_DAY', 'NEXT_BUSINESS_DAY')");
                    table.CheckConstraint("ck_recurrence_rules_due_rule", "due_rule_code = 'FIXED_DAY_OF_OFFSET_MONTH'");
                    table.CheckConstraint("ck_recurrence_rules_effective", "effective_to IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_recurrence_rules_frequency", "frequency_code IN ('MONTHLY', 'QUARTERLY', 'HALF_YEARLY', 'YEARLY', 'CUSTOM_MONTHS')");
                    table.CheckConstraint("ck_recurrence_rules_values", "interval_count BETWEEN 1 AND 24 AND due_day BETWEEN 1 AND 31 AND due_month_offset BETWEEN 0 AND 24 AND due_day_offset BETWEEN -90 AND 90 AND generate_lead_days BETWEEN 0 AND 365 AND rule_version > 0 AND row_version > 0");
                    table.ForeignKey(
                        name: "fk_recurrence_rules_assignee",
                        column: x => x.default_primary_assignee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_rules_calendar",
                        column: x => x.holiday_calendar_id,
                        principalSchema: "system",
                        principalTable: "holiday_calendars",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_rules_client_service",
                        column: x => x.client_service_id,
                        principalSchema: "services",
                        principalTable: "client_services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_rules_created_by",
                        column: x => x.created_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_rules_updated_by",
                        column: x => x.updated_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "generation_run_items",
                schema: "scheduling",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    recurrence_rule_id = table.Column<Guid>(type: "uuid", nullable: false),
                    occurrence_key = table.Column<string>(type: "character varying(160)", maxLength: 160, nullable: false),
                    outcome = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    task_id = table.Column<Guid>(type: "uuid", nullable: true),
                    period_start = table.Column<DateOnly>(type: "date", nullable: false),
                    period_end = table.Column<DateOnly>(type: "date", nullable: false),
                    due_date = table.Column<DateOnly>(type: "date", nullable: true),
                    message = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_generation_run_items", x => x.id);
                    table.CheckConstraint("ck_generation_run_items_outcome", "outcome IN ('CREATED', 'EXISTING', 'SKIPPED', 'ERROR')");
                    table.ForeignKey(
                        name: "fk_generation_run_items_rule",
                        column: x => x.recurrence_rule_id,
                        principalSchema: "scheduling",
                        principalTable: "recurrence_rules",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_generation_run_items_run",
                        column: x => x.run_id,
                        principalSchema: "scheduling",
                        principalTable: "generation_runs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_generation_run_items_task",
                        column: x => x.task_id,
                        principalSchema: "tasks",
                        principalTable: "tasks",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "recurrence_exceptions",
                schema: "scheduling",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    recurrence_rule_id = table.Column<Guid>(type: "uuid", nullable: false),
                    period_start = table.Column<DateOnly>(type: "date", nullable: false),
                    period_end = table.Column<DateOnly>(type: "date", nullable: false),
                    action = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    override_due_date = table.Column<DateOnly>(type: "date", nullable: true),
                    override_title = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: true),
                    override_primary_assignee_id = table.Column<Guid>(type: "uuid", nullable: true),
                    override_priority = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false),
                    created_by_user_id = table.Column<Guid>(type: "uuid", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_recurrence_exceptions", x => x.id);
                    table.CheckConstraint("ck_recurrence_exceptions_action", "action IN ('SKIP', 'OVERRIDE')");
                    table.CheckConstraint("ck_recurrence_exceptions_period", "period_end >= period_start");
                    table.CheckConstraint("ck_recurrence_exceptions_priority", "override_priority IS NULL OR override_priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
                    table.ForeignKey(
                        name: "fk_recurrence_exceptions_assignee",
                        column: x => x.override_primary_assignee_id,
                        principalSchema: "employees",
                        principalTable: "employees",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_exceptions_created_by",
                        column: x => x.created_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_recurrence_exceptions_rule",
                        column: x => x.recurrence_rule_id,
                        principalSchema: "scheduling",
                        principalTable: "recurrence_rules",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "recurrence_rule_months",
                schema: "scheduling",
                columns: table => new
                {
                    recurrence_rule_id = table.Column<Guid>(type: "uuid", nullable: false),
                    month_number = table.Column<short>(type: "smallint", nullable: false),
                    display_order = table.Column<short>(type: "smallint", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_recurrence_rule_months", x => new { x.recurrence_rule_id, x.month_number });
                    table.CheckConstraint("ck_recurrence_rule_months_month", "month_number BETWEEN 1 AND 12");
                    table.ForeignKey(
                        name: "fk_recurrence_rule_months_rule",
                        column: x => x.recurrence_rule_id,
                        principalSchema: "scheduling",
                        principalTable: "recurrence_rules",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "permissions",
                columns: new[] { "id", "action", "code", "description", "module", "supports_scope" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000029"), "View", "scheduling.view", "View recurrence rules and generator health for permitted client work.", "Scheduling", true },
                    { new Guid("20000000-0000-0000-0000-000000000030"), "Manage", "scheduling.manage", "Create and version recurrence rules for permitted client work.", "Scheduling", true },
                    { new Guid("20000000-0000-0000-0000-000000000031"), "Generate", "scheduling.generate", "Run the recurrence generator on demand.", "Scheduling", false },
                    { new Guid("20000000-0000-0000-0000-000000000032"), "View", "calendar.view", "View permitted tasks in calendar and agenda form.", "Calendar", true },
                    { new Guid("20000000-0000-0000-0000-000000000033"), "ManageHolidays", "scheduling.holidays.manage", "Maintain firm holidays and working-day overrides.", "Scheduling", false }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "role_permissions",
                columns: new[] { "permission_id", "role_id", "scope_ceiling" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000029"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000030"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000031"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000032"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000033"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" }
                });

            migrationBuilder.CreateIndex(
                name: "IX_tasks_recurrence_rule_id",
                schema: "tasks",
                table: "tasks",
                column: "recurrence_rule_id");

            migrationBuilder.CreateIndex(
                name: "ux_tasks_occurrence_key",
                schema: "tasks",
                table: "tasks",
                column: "occurrence_key",
                unique: true,
                filter: "occurrence_key IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ix_generation_run_items_occurrence",
                schema: "scheduling",
                table: "generation_run_items",
                column: "occurrence_key");

            migrationBuilder.CreateIndex(
                name: "IX_generation_run_items_recurrence_rule_id",
                schema: "scheduling",
                table: "generation_run_items",
                column: "recurrence_rule_id");

            migrationBuilder.CreateIndex(
                name: "IX_generation_run_items_task_id",
                schema: "scheduling",
                table: "generation_run_items",
                column: "task_id");

            migrationBuilder.CreateIndex(
                name: "ux_generation_run_items_occurrence",
                schema: "scheduling",
                table: "generation_run_items",
                columns: new[] { "run_id", "recurrence_rule_id", "occurrence_key" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_generation_runs_started",
                schema: "scheduling",
                table: "generation_runs",
                column: "started_at_utc",
                descending: new bool[0]);

            migrationBuilder.CreateIndex(
                name: "IX_generation_runs_triggered_by_user_id",
                schema: "scheduling",
                table: "generation_runs",
                column: "triggered_by_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_exceptions_created_by_user_id",
                schema: "scheduling",
                table: "recurrence_exceptions",
                column: "created_by_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_exceptions_override_primary_assignee_id",
                schema: "scheduling",
                table: "recurrence_exceptions",
                column: "override_primary_assignee_id");

            migrationBuilder.CreateIndex(
                name: "ux_recurrence_exceptions_rule_period",
                schema: "scheduling",
                table: "recurrence_exceptions",
                columns: new[] { "recurrence_rule_id", "period_start", "period_end" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_rules_created_by_user_id",
                schema: "scheduling",
                table: "recurrence_rules",
                column: "created_by_user_id");

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_rules_default_primary_assignee_id",
                schema: "scheduling",
                table: "recurrence_rules",
                column: "default_primary_assignee_id");

            migrationBuilder.CreateIndex(
                name: "ix_recurrence_rules_generation",
                schema: "scheduling",
                table: "recurrence_rules",
                columns: new[] { "is_active", "effective_from", "effective_to" });

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_rules_holiday_calendar_id",
                schema: "scheduling",
                table: "recurrence_rules",
                column: "holiday_calendar_id");

            migrationBuilder.CreateIndex(
                name: "IX_recurrence_rules_updated_by_user_id",
                schema: "scheduling",
                table: "recurrence_rules",
                column: "updated_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ux_recurrence_rules_active_agreement",
                schema: "scheduling",
                table: "recurrence_rules",
                column: "client_service_id",
                unique: true,
                filter: "is_active");

            migrationBuilder.CreateIndex(
                name: "ux_recurrence_rules_agreement_version",
                schema: "scheduling",
                table: "recurrence_rules",
                columns: new[] { "client_service_id", "rule_version" },
                unique: true);

            migrationBuilder.AddForeignKey(
                name: "fk_tasks_recurrence_rule",
                schema: "tasks",
                table: "tasks",
                column: "recurrence_rule_id",
                principalSchema: "scheduling",
                principalTable: "recurrence_rules",
                principalColumn: "id",
                onDelete: ReferentialAction.Restrict);

            migrationBuilder.Sql(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA scheduling TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA scheduling TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA scheduling TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA scheduling
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END $$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "fk_tasks_recurrence_rule",
                schema: "tasks",
                table: "tasks");

            migrationBuilder.DropTable(
                name: "generation_run_items",
                schema: "scheduling");

            migrationBuilder.DropTable(
                name: "recurrence_exceptions",
                schema: "scheduling");

            migrationBuilder.DropTable(
                name: "recurrence_rule_months",
                schema: "scheduling");

            migrationBuilder.DropTable(
                name: "generation_runs",
                schema: "scheduling");

            migrationBuilder.DropTable(
                name: "recurrence_rules",
                schema: "scheduling");

            migrationBuilder.DropIndex(
                name: "IX_tasks_recurrence_rule_id",
                schema: "tasks",
                table: "tasks");

            migrationBuilder.DropIndex(
                name: "ux_tasks_occurrence_key",
                schema: "tasks",
                table: "tasks");

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000029"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000030"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000031"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000032"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000033"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000029"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000030"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000031"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000032"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000033"));

            migrationBuilder.DropColumn(
                name: "occurrence_key",
                schema: "tasks",
                table: "tasks");

            migrationBuilder.DropColumn(
                name: "recurrence_rule_id",
                schema: "tasks",
                table: "tasks");

            migrationBuilder.AlterColumn<Guid>(
                name: "updated_by_user_id",
                schema: "tasks",
                table: "tasks",
                type: "uuid",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"),
                oldClrType: typeof(Guid),
                oldType: "uuid",
                oldNullable: true);

            migrationBuilder.AlterColumn<Guid>(
                name: "created_by_user_id",
                schema: "tasks",
                table: "tasks",
                type: "uuid",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"),
                oldClrType: typeof(Guid),
                oldType: "uuid",
                oldNullable: true);

            migrationBuilder.AlterColumn<Guid>(
                name: "actor_user_id",
                schema: "tasks",
                table: "task_status_history",
                type: "uuid",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"),
                oldClrType: typeof(Guid),
                oldType: "uuid",
                oldNullable: true);

            migrationBuilder.AlterColumn<Guid>(
                name: "assigned_by_user_id",
                schema: "tasks",
                table: "task_assignments",
                type: "uuid",
                nullable: false,
                defaultValue: new Guid("00000000-0000-0000-0000-000000000000"),
                oldClrType: typeof(Guid),
                oldType: "uuid",
                oldNullable: true);
        }
    }
}
