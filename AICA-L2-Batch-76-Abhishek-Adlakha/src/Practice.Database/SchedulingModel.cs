using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class SchedulingModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureRules(modelBuilder);
        ConfigureExceptions(modelBuilder);
        ConfigureRuns(modelBuilder);
    }

    private static void ConfigureRules(ModelBuilder modelBuilder)
    {
        var rule = modelBuilder.Entity<RecurrenceRule>();
        rule.ToTable("recurrence_rules", "scheduling", table =>
        {
            table.HasCheckConstraint("ck_recurrence_rules_frequency", "frequency_code IN ('MONTHLY', 'QUARTERLY', 'HALF_YEARLY', 'YEARLY', 'CUSTOM_MONTHS')");
            table.HasCheckConstraint("ck_recurrence_rules_due_rule", "due_rule_code = 'FIXED_DAY_OF_OFFSET_MONTH'");
            table.HasCheckConstraint("ck_recurrence_rules_business_day", "business_day_adjustment IN ('NONE', 'PREVIOUS_BUSINESS_DAY', 'NEXT_BUSINESS_DAY')");
            table.HasCheckConstraint("ck_recurrence_rules_values", "interval_count BETWEEN 1 AND 24 AND due_day BETWEEN 1 AND 31 AND due_month_offset BETWEEN 0 AND 24 AND due_day_offset BETWEEN -90 AND 90 AND generate_lead_days BETWEEN 0 AND 365 AND rule_version > 0 AND row_version > 0");
            table.HasCheckConstraint("ck_recurrence_rules_effective", "effective_to IS NULL OR effective_to >= effective_from");
        });
        rule.HasKey(x => x.Id).HasName("pk_recurrence_rules");
        rule.Property(x => x.Id).HasColumnName("id");
        rule.Property(x => x.ClientServiceId).HasColumnName("client_service_id");
        rule.Property(x => x.HolidayCalendarId).HasColumnName("holiday_calendar_id");
        rule.Property(x => x.DefaultPrimaryAssigneeId).HasColumnName("default_primary_assignee_id");
        rule.Property(x => x.FrequencyCode).HasColumnName("frequency_code").HasMaxLength(30);
        rule.Property(x => x.IntervalCount).HasColumnName("interval_count");
        rule.Property(x => x.AnchorDate).HasColumnName("anchor_date");
        rule.Property(x => x.DueRuleCode).HasColumnName("due_rule_code").HasMaxLength(50);
        rule.Property(x => x.DueDay).HasColumnName("due_day");
        rule.Property(x => x.DueMonthOffset).HasColumnName("due_month_offset");
        rule.Property(x => x.DueDayOffset).HasColumnName("due_day_offset");
        rule.Property(x => x.BusinessDayAdjustment).HasColumnName("business_day_adjustment").HasMaxLength(30);
        rule.Property(x => x.GenerateLeadDays).HasColumnName("generate_lead_days");
        rule.Property(x => x.TimeZoneId).HasColumnName("time_zone_id").HasMaxLength(80);
        rule.Property(x => x.EffectiveFrom).HasColumnName("effective_from");
        rule.Property(x => x.EffectiveTo).HasColumnName("effective_to");
        rule.Property(x => x.RuleVersion).HasColumnName("rule_version");
        rule.Property(x => x.IsActive).HasColumnName("is_active");
        rule.Property(x => x.CreatedByUserId).HasColumnName("created_by_user_id");
        rule.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        rule.Property(x => x.UpdatedByUserId).HasColumnName("updated_by_user_id");
        rule.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        rule.Property(x => x.RowVersion).HasColumnName("row_version").IsConcurrencyToken();
        rule.HasOne(x => x.ClientService).WithMany().HasForeignKey(x => x.ClientServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_rules_client_service");
        rule.HasOne(x => x.HolidayCalendar).WithMany().HasForeignKey(x => x.HolidayCalendarId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_rules_calendar");
        rule.HasOne(x => x.DefaultPrimaryAssignee).WithMany().HasForeignKey(x => x.DefaultPrimaryAssigneeId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_rules_assignee");
        rule.HasOne(x => x.CreatedByUser).WithMany().HasForeignKey(x => x.CreatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_rules_created_by");
        rule.HasOne(x => x.UpdatedByUser).WithMany().HasForeignKey(x => x.UpdatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_rules_updated_by");
        rule.HasIndex(x => new { x.ClientServiceId, x.RuleVersion }).IsUnique().HasDatabaseName("ux_recurrence_rules_agreement_version");
        rule.HasIndex(x => x.ClientServiceId).IsUnique().HasFilter("is_active").HasDatabaseName("ux_recurrence_rules_active_agreement");
        rule.HasIndex(x => new { x.IsActive, x.EffectiveFrom, x.EffectiveTo }).HasDatabaseName("ix_recurrence_rules_generation");

        var month = modelBuilder.Entity<RecurrenceRuleMonth>();
        month.ToTable("recurrence_rule_months", "scheduling", table => table.HasCheckConstraint("ck_recurrence_rule_months_month", "month_number BETWEEN 1 AND 12"));
        month.HasKey(x => new { x.RecurrenceRuleId, x.MonthNumber }).HasName("pk_recurrence_rule_months");
        month.Property(x => x.RecurrenceRuleId).HasColumnName("recurrence_rule_id");
        month.Property(x => x.MonthNumber).HasColumnName("month_number");
        month.Property(x => x.DisplayOrder).HasColumnName("display_order");
        month.HasOne(x => x.RecurrenceRule).WithMany(x => x.Months).HasForeignKey(x => x.RecurrenceRuleId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_recurrence_rule_months_rule");
    }

    private static void ConfigureExceptions(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<RecurrenceAdjustment>();
        entity.ToTable("recurrence_exceptions", "scheduling", table =>
        {
            table.HasCheckConstraint("ck_recurrence_exceptions_period", "period_end >= period_start");
            table.HasCheckConstraint("ck_recurrence_exceptions_action", "action IN ('SKIP', 'OVERRIDE')");
            table.HasCheckConstraint("ck_recurrence_exceptions_priority", "override_priority IS NULL OR override_priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
        });
        entity.HasKey(x => x.Id).HasName("pk_recurrence_exceptions");
        entity.Property(x => x.Id).HasColumnName("id");
        entity.Property(x => x.RecurrenceRuleId).HasColumnName("recurrence_rule_id");
        entity.Property(x => x.PeriodStart).HasColumnName("period_start");
        entity.Property(x => x.PeriodEnd).HasColumnName("period_end");
        entity.Property(x => x.Action).HasColumnName("action").HasMaxLength(20);
        entity.Property(x => x.OverrideDueDate).HasColumnName("override_due_date");
        entity.Property(x => x.OverrideTitle).HasColumnName("override_title").HasMaxLength(250);
        entity.Property(x => x.OverridePrimaryAssigneeId).HasColumnName("override_primary_assignee_id");
        entity.Property(x => x.OverridePriority).HasColumnName("override_priority").HasMaxLength(20);
        entity.Property(x => x.Reason).HasColumnName("reason").HasMaxLength(1000);
        entity.Property(x => x.CreatedByUserId).HasColumnName("created_by_user_id");
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        entity.HasOne(x => x.RecurrenceRule).WithMany(x => x.Exceptions).HasForeignKey(x => x.RecurrenceRuleId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_recurrence_exceptions_rule");
        entity.HasOne(x => x.OverridePrimaryAssignee).WithMany().HasForeignKey(x => x.OverridePrimaryAssigneeId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_exceptions_assignee");
        entity.HasOne(x => x.CreatedByUser).WithMany().HasForeignKey(x => x.CreatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_recurrence_exceptions_created_by");
        entity.HasIndex(x => new { x.RecurrenceRuleId, x.PeriodStart, x.PeriodEnd }).IsUnique().HasDatabaseName("ux_recurrence_exceptions_rule_period");
    }

    private static void ConfigureRuns(ModelBuilder modelBuilder)
    {
        var run = modelBuilder.Entity<TaskGenerationRun>();
        run.ToTable("generation_runs", "scheduling", table =>
        {
            table.HasCheckConstraint("ck_generation_runs_window", "window_to >= window_from");
            table.HasCheckConstraint("ck_generation_runs_trigger", "trigger IN ('MANUAL', 'SCHEDULED')");
            table.HasCheckConstraint("ck_generation_runs_status", "status IN ('RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'SKIPPED_LOCKED')");
            table.HasCheckConstraint("ck_generation_runs_counts", "created_count >= 0 AND existing_count >= 0 AND skipped_count >= 0 AND error_count >= 0");
        });
        run.HasKey(x => x.Id).HasName("pk_generation_runs");
        run.Property(x => x.Id).HasColumnName("id");
        run.Property(x => x.WindowFrom).HasColumnName("window_from");
        run.Property(x => x.WindowTo).HasColumnName("window_to");
        run.Property(x => x.Trigger).HasColumnName("trigger").HasMaxLength(20);
        run.Property(x => x.Status).HasColumnName("status").HasMaxLength(30);
        run.Property(x => x.WorkerId).HasColumnName("worker_id").HasMaxLength(150);
        run.Property(x => x.TriggeredByUserId).HasColumnName("triggered_by_user_id");
        run.Property(x => x.StartedAtUtc).HasColumnName("started_at_utc");
        run.Property(x => x.FinishedAtUtc).HasColumnName("finished_at_utc");
        run.Property(x => x.CreatedCount).HasColumnName("created_count");
        run.Property(x => x.ExistingCount).HasColumnName("existing_count");
        run.Property(x => x.SkippedCount).HasColumnName("skipped_count");
        run.Property(x => x.ErrorCount).HasColumnName("error_count");
        run.Property(x => x.ErrorSummary).HasColumnName("error_summary").HasMaxLength(2000);
        run.HasOne(x => x.TriggeredByUser).WithMany().HasForeignKey(x => x.TriggeredByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_generation_runs_triggered_by");
        run.HasIndex(x => x.StartedAtUtc).IsDescending().HasDatabaseName("ix_generation_runs_started");

        var item = modelBuilder.Entity<TaskGenerationRunItem>();
        item.ToTable("generation_run_items", "scheduling", table => table.HasCheckConstraint("ck_generation_run_items_outcome", "outcome IN ('CREATED', 'EXISTING', 'SKIPPED', 'ERROR')"));
        item.HasKey(x => x.Id).HasName("pk_generation_run_items");
        item.Property(x => x.Id).HasColumnName("id").UseIdentityByDefaultColumn();
        item.Property(x => x.RunId).HasColumnName("run_id");
        item.Property(x => x.RecurrenceRuleId).HasColumnName("recurrence_rule_id");
        item.Property(x => x.OccurrenceKey).HasColumnName("occurrence_key").HasMaxLength(160);
        item.Property(x => x.Outcome).HasColumnName("outcome").HasMaxLength(20);
        item.Property(x => x.TaskId).HasColumnName("task_id");
        item.Property(x => x.PeriodStart).HasColumnName("period_start");
        item.Property(x => x.PeriodEnd).HasColumnName("period_end");
        item.Property(x => x.DueDate).HasColumnName("due_date");
        item.Property(x => x.Message).HasColumnName("message").HasMaxLength(1000);
        item.HasOne(x => x.Run).WithMany(x => x.Items).HasForeignKey(x => x.RunId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_generation_run_items_run");
        item.HasOne(x => x.RecurrenceRule).WithMany().HasForeignKey(x => x.RecurrenceRuleId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_generation_run_items_rule");
        item.HasOne(x => x.Task).WithMany().HasForeignKey(x => x.TaskId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_generation_run_items_task");
        item.HasIndex(x => new { x.RunId, x.RecurrenceRuleId, x.OccurrenceKey }).IsUnique().HasDatabaseName("ux_generation_run_items_occurrence");
        item.HasIndex(x => x.OccurrenceKey).HasDatabaseName("ix_generation_run_items_occurrence");
    }
}
