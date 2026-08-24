using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class FoundationModel
{
    private static readonly Guid DefaultCalendarId = new("70a45f7b-dfde-4af0-a634-876797f19501");
    private static readonly DateTimeOffset SeedTimestamp = new(2026, 8, 20, 0, 0, 0, TimeSpan.Zero);

    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureReference(modelBuilder);
        ConfigureSystem(modelBuilder);
        ConfigureAudit(modelBuilder);
        ConfigureImport(modelBuilder);
    }

    private static void ConfigureReference(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<IndiaState>();
        entity.ToTable("india_states", "reference");
        entity.HasKey(x => x.GstCode).HasName("pk_india_states");
        entity.Property(x => x.GstCode).HasColumnName("gst_code").HasMaxLength(2);
        entity.Property(x => x.Name).HasColumnName("name").HasMaxLength(100);
        entity.Property(x => x.IsUnionTerritory).HasColumnName("is_union_territory");
        entity.Property(x => x.IsActive).HasColumnName("is_active");
        entity.HasIndex(x => x.Name).IsUnique().HasDatabaseName("ux_india_states_name");
        entity.HasData(IndiaStateSeed.All);
    }

    private static void ConfigureSystem(ModelBuilder modelBuilder)
    {
        var setting = modelBuilder.Entity<AppSetting>();
        setting.ToTable("app_settings", "system");
        setting.HasKey(x => x.Key).HasName("pk_app_settings");
        setting.Property(x => x.Key).HasColumnName("key").HasMaxLength(100);
        setting.Property(x => x.ValueJson).HasColumnName("value_json").HasColumnType("jsonb");
        setting.Property(x => x.Description).HasColumnName("description").HasMaxLength(500);
        setting.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        setting.HasData(
            new AppSetting
            {
                Key = "organization.time_zone",
                ValueJson = "\"Asia/Kolkata\"",
                Description = "IANA time zone used for firm-local dates and scheduling.",
                UpdatedAtUtc = SeedTimestamp
            },
            new AppSetting
            {
                Key = "reporting.financial_year_start",
                ValueJson = "{\"month\":4,\"day\":1}",
                Description = "Start of the Indian financial reporting year.",
                UpdatedAtUtc = SeedTimestamp
            });

        var calendar = modelBuilder.Entity<HolidayCalendar>();
        calendar.ToTable("holiday_calendars", "system");
        calendar.HasKey(x => x.Id).HasName("pk_holiday_calendars");
        calendar.Property(x => x.Id).HasColumnName("id");
        calendar.Property(x => x.Code).HasColumnName("code").HasMaxLength(30);
        calendar.Property(x => x.Name).HasColumnName("name").HasMaxLength(150);
        calendar.Property(x => x.TimeZoneId).HasColumnName("time_zone_id").HasMaxLength(80);
        calendar.Property(x => x.RegionCode).HasColumnName("region_code").HasMaxLength(20);
        calendar.Property(x => x.IsActive).HasColumnName("is_active");
        calendar.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        calendar.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_holiday_calendars_code");
        calendar.HasData(new HolidayCalendar
        {
            Id = DefaultCalendarId,
            Code = "IN-DEFAULT",
            Name = "India firm default",
            TimeZoneId = "Asia/Kolkata",
            RegionCode = "IN",
            IsActive = true,
            CreatedAtUtc = SeedTimestamp
        });

        var holiday = modelBuilder.Entity<Holiday>();
        holiday.ToTable("holidays", "system", table => table.HasCheckConstraint(
            "ck_holidays_type", "holiday_type IN ('Public', 'Firm', 'Optional')"));
        holiday.HasKey(x => x.Id).HasName("pk_holidays");
        holiday.Property(x => x.Id).HasColumnName("id");
        holiday.Property(x => x.HolidayCalendarId).HasColumnName("holiday_calendar_id");
        holiday.Property(x => x.HolidayDate).HasColumnName("holiday_date");
        holiday.Property(x => x.Name).HasColumnName("name").HasMaxLength(150);
        holiday.Property(x => x.HolidayType).HasColumnName("holiday_type").HasMaxLength(20);
        holiday.Property(x => x.IsWorkingDayOverride).HasColumnName("is_working_day_override");
        holiday.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(500);
        holiday.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        holiday.HasOne(x => x.HolidayCalendar).WithMany(x => x.Holidays)
            .HasForeignKey(x => x.HolidayCalendarId).OnDelete(DeleteBehavior.Restrict)
            .HasConstraintName("fk_holidays_calendar");
        holiday.HasIndex(x => new { x.HolidayCalendarId, x.HolidayDate })
            .IsUnique().HasDatabaseName("ux_holidays_calendar_date");
    }

    private static void ConfigureAudit(ModelBuilder modelBuilder)
    {
        var audit = modelBuilder.Entity<AuditEvent>();
        audit.ToTable("audit_events", "audit");
        audit.HasKey(x => x.Id).HasName("pk_audit_events");
        audit.Property(x => x.Id).HasColumnName("id");
        audit.Property(x => x.OccurredAtUtc).HasColumnName("occurred_at_utc");
        audit.Property(x => x.ActorUserId).HasColumnName("actor_user_id");
        audit.Property(x => x.Action).HasColumnName("action").HasMaxLength(100);
        audit.Property(x => x.EntityType).HasColumnName("entity_type").HasMaxLength(150);
        audit.Property(x => x.EntityId).HasColumnName("entity_id").HasMaxLength(100);
        audit.Property(x => x.Reason).HasColumnName("reason").HasMaxLength(500);
        audit.Property(x => x.CorrelationId).HasColumnName("correlation_id").HasMaxLength(100);
        audit.Property(x => x.DataJson).HasColumnName("data_json").HasColumnType("jsonb");
        audit.HasIndex(x => x.OccurredAtUtc).HasDatabaseName("ix_audit_events_occurred");
        audit.HasIndex(x => new { x.EntityType, x.EntityId, x.OccurredAtUtc })
            .HasDatabaseName("ix_audit_events_entity");

        var outbox = modelBuilder.Entity<OutboxMessage>();
        outbox.ToTable("outbox_messages", "system", table => table.HasCheckConstraint(
            "ck_outbox_attempt_count", "attempt_count >= 0"));
        outbox.HasKey(x => x.Id).HasName("pk_outbox_messages");
        outbox.Property(x => x.Id).HasColumnName("id");
        outbox.Property(x => x.OccurredAtUtc).HasColumnName("occurred_at_utc");
        outbox.Property(x => x.MessageType).HasColumnName("message_type").HasMaxLength(300);
        outbox.Property(x => x.PayloadJson).HasColumnName("payload_json").HasColumnType("jsonb");
        outbox.Property(x => x.ProcessedAtUtc).HasColumnName("processed_at_utc");
        outbox.Property(x => x.NextAttemptAtUtc).HasColumnName("next_attempt_at_utc");
        outbox.Property(x => x.AttemptCount).HasColumnName("attempt_count");
        outbox.Property(x => x.LastError).HasColumnName("last_error").HasMaxLength(2000);
        outbox.HasIndex(x => new { x.ProcessedAtUtc, x.NextAttemptAtUtc })
            .HasDatabaseName("ix_outbox_pending");
    }

    private static void ConfigureImport(ModelBuilder modelBuilder)
    {
        var run = modelBuilder.Entity<ImportRun>();
        run.ToTable("import_runs", "import", table =>
        {
            table.HasCheckConstraint("ck_import_runs_mode", "mode IN ('Profile', 'DryRun', 'Import')");
            table.HasCheckConstraint("ck_import_runs_status", "status IN ('Running', 'Completed', 'Failed')");
            table.HasCheckConstraint("ck_import_runs_size", "source_size_bytes >= 0");
        });
        run.HasKey(x => x.Id).HasName("pk_import_runs");
        run.Property(x => x.Id).HasColumnName("id");
        run.Property(x => x.SourceFileName).HasColumnName("source_file_name").HasMaxLength(260);
        run.Property(x => x.SourceSha256).HasColumnName("source_sha256").HasMaxLength(64);
        run.Property(x => x.Mode).HasColumnName("mode").HasMaxLength(20);
        run.Property(x => x.Status).HasColumnName("status").HasMaxLength(20);
        run.Property(x => x.StartedAtUtc).HasColumnName("started_at_utc");
        run.Property(x => x.CompletedAtUtc).HasColumnName("completed_at_utc");
        run.Property(x => x.SourceSizeBytes).HasColumnName("source_size_bytes");
        run.Property(x => x.ReportJson).HasColumnName("report_json").HasColumnType("jsonb");
        run.Property(x => x.ErrorSummary).HasColumnName("error_summary").HasMaxLength(2000);
        run.HasIndex(x => x.SourceSha256).HasDatabaseName("ix_import_runs_source_sha256");
        run.HasIndex(x => x.StartedAtUtc).HasDatabaseName("ix_import_runs_started");

        var issue = modelBuilder.Entity<ImportIssue>();
        issue.ToTable("import_issues", "import", table => table.HasCheckConstraint(
            "ck_import_issues_severity", "severity IN ('Info', 'Warning', 'Error')"));
        issue.HasKey(x => x.Id).HasName("pk_import_issues");
        issue.Property(x => x.Id).HasColumnName("id").UseIdentityByDefaultColumn();
        issue.Property(x => x.ImportRunId).HasColumnName("import_run_id");
        issue.Property(x => x.Severity).HasColumnName("severity").HasMaxLength(20);
        issue.Property(x => x.IssueCode).HasColumnName("issue_code").HasMaxLength(80);
        issue.Property(x => x.SheetName).HasColumnName("sheet_name").HasMaxLength(100);
        issue.Property(x => x.RowNumber).HasColumnName("row_number");
        issue.Property(x => x.ColumnName).HasColumnName("column_name").HasMaxLength(150);
        issue.Property(x => x.RawValue).HasColumnName("raw_value").HasMaxLength(1000);
        issue.Property(x => x.NormalizedValue).HasColumnName("normalized_value").HasMaxLength(1000);
        issue.Property(x => x.Message).HasColumnName("message").HasMaxLength(1000);
        issue.HasOne(x => x.ImportRun).WithMany(x => x.Issues)
            .HasForeignKey(x => x.ImportRunId).OnDelete(DeleteBehavior.Cascade)
            .HasConstraintName("fk_import_issues_run");
        issue.HasIndex(x => new { x.ImportRunId, x.Severity, x.IssueCode })
            .HasDatabaseName("ix_import_issues_run_severity_code");
    }
}
