using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class TaskModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureStatuses(modelBuilder);
        ConfigureTasks(modelBuilder);
        ConfigureAssignments(modelBuilder);
        ConfigureHistory(modelBuilder);
        ConfigureComments(modelBuilder);
    }

    private static void ConfigureStatuses(ModelBuilder modelBuilder)
    {
        var status = modelBuilder.Entity<WorkTaskStatus>();
        status.ToTable("task_statuses", "tasks");
        status.HasKey(x => x.Id).HasName("pk_task_statuses");
        status.Property(x => x.Id).HasColumnName("id");
        status.Property(x => x.Code).HasColumnName("code").HasMaxLength(30);
        status.Property(x => x.Label).HasColumnName("label").HasMaxLength(80);
        status.Property(x => x.Color).HasColumnName("color").HasMaxLength(20);
        status.Property(x => x.DisplayOrder).HasColumnName("display_order");
        status.Property(x => x.IsTerminal).HasColumnName("is_terminal");
        status.Property(x => x.CountsAsComplete).HasColumnName("counts_as_complete");
        status.Property(x => x.IsActive).HasColumnName("is_active");
        status.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_task_statuses_code");
        status.HasIndex(x => new { x.IsActive, x.DisplayOrder }).HasDatabaseName("ix_task_statuses_active_order");
        status.HasData(TaskSeed.Statuses);

        var transition = modelBuilder.Entity<TaskStatusTransition>();
        transition.ToTable("task_status_transitions", "tasks");
        transition.HasKey(x => new { x.FromStatusId, x.ToStatusId }).HasName("pk_task_status_transitions");
        transition.Property(x => x.FromStatusId).HasColumnName("from_status_id");
        transition.Property(x => x.ToStatusId).HasColumnName("to_status_id");
        transition.Property(x => x.RequiredPermission).HasColumnName("required_permission").HasMaxLength(120);
        transition.Property(x => x.ReasonRequired).HasColumnName("reason_required");
        transition.Property(x => x.CompletionDataRequired).HasColumnName("completion_data_required");
        transition.HasOne(x => x.FromStatus).WithMany().HasForeignKey(x => x.FromStatusId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_transitions_from_status");
        transition.HasOne(x => x.ToStatus).WithMany().HasForeignKey(x => x.ToStatusId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_transitions_to_status");
        transition.HasData(TaskSeed.Transitions);
    }

    private static void ConfigureTasks(ModelBuilder modelBuilder)
    {
        var clientService = modelBuilder.Entity<ClientService>();
        clientService.HasAlternateKey(x => new { x.Id, x.ClientId, x.ServiceId }).HasName("ak_client_services_id_client_service");

        var task = modelBuilder.Entity<PracticeTask>();
        task.ToTable("tasks", "tasks", table =>
        {
            table.HasCheckConstraint("ck_tasks_period", "period_end IS NULL OR period_start IS NULL OR period_end >= period_start");
            table.HasCheckConstraint("ck_tasks_priority", "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
            table.HasCheckConstraint("ck_tasks_source", "created_source IN ('MANUAL', 'RECURRENCE', 'IMPORT')");
            table.HasCheckConstraint("ck_tasks_row_version", "row_version > 0");
            table.HasCheckConstraint("ck_tasks_completed_metadata", "(completed_at_utc IS NULL AND completed_by_user_id IS NULL) OR (completed_at_utc IS NOT NULL AND completed_by_user_id IS NOT NULL)");
            table.HasCheckConstraint("ck_tasks_cancelled_metadata", "(cancelled_at_utc IS NULL AND cancelled_by_user_id IS NULL AND cancellation_reason IS NULL) OR (cancelled_at_utc IS NOT NULL AND cancelled_by_user_id IS NOT NULL AND length(trim(cancellation_reason)) > 0)");
        });
        task.HasKey(x => x.Id).HasName("pk_tasks");
        task.Property(x => x.Id).HasColumnName("id");
        task.Property(x => x.TaskNumber).HasColumnName("task_number").UseIdentityByDefaultColumn();
        task.Property(x => x.ClientId).HasColumnName("client_id");
        task.Property(x => x.ServiceId).HasColumnName("service_id");
        task.Property(x => x.ClientServiceId).HasColumnName("client_service_id");
        task.Property(x => x.GstRegistrationId).HasColumnName("gst_registration_id");
        task.Property(x => x.RecurrenceRuleId).HasColumnName("recurrence_rule_id");
        task.Property(x => x.OccurrenceKey).HasColumnName("occurrence_key").HasMaxLength(160);
        task.Property(x => x.Title).HasColumnName("title").HasMaxLength(250);
        task.Property(x => x.Description).HasColumnName("description").HasMaxLength(4000);
        task.Property(x => x.PeriodStart).HasColumnName("period_start");
        task.Property(x => x.PeriodEnd).HasColumnName("period_end");
        task.Property(x => x.DueDate).HasColumnName("due_date");
        task.Property(x => x.StatusId).HasColumnName("status_id");
        task.Property(x => x.Priority).HasColumnName("priority").HasMaxLength(20);
        task.Property(x => x.BillableSnapshot).HasColumnName("billable_snapshot");
        task.Property(x => x.CompletedAtUtc).HasColumnName("completed_at_utc");
        task.Property(x => x.CompletedByUserId).HasColumnName("completed_by_user_id");
        task.Property(x => x.CancelledAtUtc).HasColumnName("cancelled_at_utc");
        task.Property(x => x.CancelledByUserId).HasColumnName("cancelled_by_user_id");
        task.Property(x => x.CancellationReason).HasColumnName("cancellation_reason").HasMaxLength(1000);
        task.Property(x => x.ReopenedCount).HasColumnName("reopened_count");
        task.Property(x => x.CreatedSource).HasColumnName("created_source").HasMaxLength(20);
        task.Property(x => x.CreatedByUserId).HasColumnName("created_by_user_id");
        task.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        task.Property(x => x.UpdatedByUserId).HasColumnName("updated_by_user_id");
        task.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        task.Property(x => x.RowVersion).HasColumnName("row_version").IsConcurrencyToken();
        task.HasOne(x => x.Client).WithMany().HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_client");
        task.HasOne(x => x.Service).WithMany().HasForeignKey(x => x.ServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_service");
        task.HasOne(x => x.ClientService).WithMany().HasForeignKey(x => new { x.ClientServiceId, x.ClientId, x.ServiceId })
            .HasPrincipalKey(x => new { x.Id, x.ClientId, x.ServiceId }).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_client_service_scope");
        task.HasOne(x => x.GstRegistration).WithMany().HasForeignKey(x => new { x.GstRegistrationId, x.ClientId })
            .HasPrincipalKey(x => new { x.Id, x.ClientId }).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_gstin_client");
        task.HasOne(x => x.RecurrenceRule).WithMany().HasForeignKey(x => x.RecurrenceRuleId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_recurrence_rule");
        task.HasOne(x => x.Status).WithMany().HasForeignKey(x => x.StatusId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_status");
        task.HasOne(x => x.CompletedByUser).WithMany().HasForeignKey(x => x.CompletedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_completed_by");
        task.HasOne(x => x.CancelledByUser).WithMany().HasForeignKey(x => x.CancelledByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_cancelled_by");
        task.HasOne(x => x.CreatedByUser).WithMany().HasForeignKey(x => x.CreatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_created_by");
        task.HasOne(x => x.UpdatedByUser).WithMany().HasForeignKey(x => x.UpdatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_tasks_updated_by");
        task.HasIndex(x => x.TaskNumber).IsUnique().HasDatabaseName("ux_tasks_number");
        task.HasIndex(x => x.OccurrenceKey).IsUnique().HasFilter("occurrence_key IS NOT NULL").HasDatabaseName("ux_tasks_occurrence_key");
        task.HasIndex(x => new { x.DueDate, x.StatusId }).HasDatabaseName("ix_tasks_due_status");
        task.HasIndex(x => new { x.ClientId, x.DueDate }).HasDatabaseName("ix_tasks_client_due");
        task.HasIndex(x => new { x.ServiceId, x.DueDate }).HasDatabaseName("ix_tasks_service_due");
        task.HasIndex(x => new { x.ClientServiceId, x.PeriodStart }).HasDatabaseName("ix_tasks_client_service_period");
        task.HasIndex(x => new { x.StatusId, x.DueDate }).HasFilter("status_id IN ('50000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000003')").HasDatabaseName("ix_tasks_open_due");
        task.HasIndex(x => x.CreatedAtUtc).HasDatabaseName("ix_tasks_created");
    }

    private static void ConfigureAssignments(ModelBuilder modelBuilder)
    {
        var assignment = modelBuilder.Entity<TaskAssignment>();
        assignment.ToTable("task_assignments", "tasks", table =>
        {
            table.HasCheckConstraint("ck_task_assignments_role", "assignment_role IN ('PRIMARY', 'SECONDARY', 'REVIEWER')");
            table.HasCheckConstraint("ck_task_assignments_unassigned", "(unassigned_at_utc IS NULL AND unassigned_by_user_id IS NULL AND unassignment_reason IS NULL) OR (unassigned_at_utc IS NOT NULL AND unassigned_by_user_id IS NOT NULL AND length(trim(unassignment_reason)) > 0)");
        });
        assignment.HasKey(x => x.Id).HasName("pk_task_assignments");
        assignment.Property(x => x.Id).HasColumnName("id");
        assignment.Property(x => x.TaskId).HasColumnName("task_id");
        assignment.Property(x => x.EmployeeId).HasColumnName("employee_id");
        assignment.Property(x => x.AssignmentRole).HasColumnName("assignment_role").HasMaxLength(20);
        assignment.Property(x => x.AssignedAtUtc).HasColumnName("assigned_at_utc");
        assignment.Property(x => x.AssignedByUserId).HasColumnName("assigned_by_user_id");
        assignment.Property(x => x.UnassignedAtUtc).HasColumnName("unassigned_at_utc");
        assignment.Property(x => x.UnassignedByUserId).HasColumnName("unassigned_by_user_id");
        assignment.Property(x => x.Remarks).HasColumnName("remarks").HasMaxLength(1000);
        assignment.Property(x => x.UnassignmentReason).HasColumnName("unassignment_reason").HasMaxLength(1000);
        assignment.HasOne(x => x.Task).WithMany(x => x.Assignments).HasForeignKey(x => x.TaskId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_assignments_task");
        assignment.HasOne(x => x.Employee).WithMany().HasForeignKey(x => x.EmployeeId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_assignments_employee");
        assignment.HasOne(x => x.AssignedByUser).WithMany().HasForeignKey(x => x.AssignedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_assignments_assigned_by");
        assignment.HasOne(x => x.UnassignedByUser).WithMany().HasForeignKey(x => x.UnassignedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_assignments_unassigned_by");
        assignment.HasIndex(x => x.TaskId).IsUnique().HasFilter("unassigned_at_utc IS NULL AND assignment_role = 'PRIMARY'").HasDatabaseName("ux_task_assignments_current_primary");
        assignment.HasIndex(x => new { x.TaskId, x.EmployeeId, x.AssignmentRole }).IsUnique().HasFilter("unassigned_at_utc IS NULL").HasDatabaseName("ux_task_assignments_current_employee_role");
        assignment.HasIndex(x => new { x.EmployeeId, x.UnassignedAtUtc, x.TaskId }).HasDatabaseName("ix_task_assignments_employee_active");
    }

    private static void ConfigureHistory(ModelBuilder modelBuilder)
    {
        var history = modelBuilder.Entity<TaskStatusHistory>();
        history.ToTable("task_status_history", "tasks");
        history.HasKey(x => x.Id).HasName("pk_task_status_history");
        history.Property(x => x.Id).HasColumnName("id");
        history.Property(x => x.TaskId).HasColumnName("task_id");
        history.Property(x => x.FromStatusId).HasColumnName("from_status_id");
        history.Property(x => x.ToStatusId).HasColumnName("to_status_id");
        history.Property(x => x.ActorUserId).HasColumnName("actor_user_id");
        history.Property(x => x.ChangedAtUtc).HasColumnName("changed_at_utc");
        history.Property(x => x.Reason).HasColumnName("reason").HasMaxLength(1000);
        history.Property(x => x.CompletionNote).HasColumnName("completion_note").HasMaxLength(2000);
        history.Property(x => x.MetadataJson).HasColumnName("metadata_json").HasColumnType("jsonb");
        history.HasOne(x => x.Task).WithMany(x => x.StatusHistory).HasForeignKey(x => x.TaskId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_history_task");
        history.HasOne(x => x.FromStatus).WithMany().HasForeignKey(x => x.FromStatusId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_history_from_status");
        history.HasOne(x => x.ToStatus).WithMany().HasForeignKey(x => x.ToStatusId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_history_to_status");
        history.HasOne(x => x.ActorUser).WithMany().HasForeignKey(x => x.ActorUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_history_actor");
        history.HasIndex(x => new { x.TaskId, x.ChangedAtUtc }).IsDescending(false, true).HasDatabaseName("ix_task_history_task_changed");
        history.HasIndex(x => new { x.ToStatusId, x.ChangedAtUtc }).HasDatabaseName("ix_task_history_status_changed");
    }

    private static void ConfigureComments(ModelBuilder modelBuilder)
    {
        var comment = modelBuilder.Entity<TaskComment>();
        comment.ToTable("task_comments", "tasks", table => table.HasCheckConstraint("ck_task_comments_redaction", "(NOT is_redacted AND redacted_at_utc IS NULL AND redacted_by_user_id IS NULL) OR (is_redacted AND redacted_at_utc IS NOT NULL AND redacted_by_user_id IS NOT NULL)"));
        comment.HasKey(x => x.Id).HasName("pk_task_comments");
        comment.Property(x => x.Id).HasColumnName("id");
        comment.Property(x => x.TaskId).HasColumnName("task_id");
        comment.Property(x => x.AuthorUserId).HasColumnName("author_user_id");
        comment.Property(x => x.Body).HasColumnName("body").HasMaxLength(4000);
        comment.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        comment.Property(x => x.EditedAtUtc).HasColumnName("edited_at_utc");
        comment.Property(x => x.IsRedacted).HasColumnName("is_redacted");
        comment.Property(x => x.RedactedAtUtc).HasColumnName("redacted_at_utc");
        comment.Property(x => x.RedactedByUserId).HasColumnName("redacted_by_user_id");
        comment.HasOne(x => x.Task).WithMany(x => x.Comments).HasForeignKey(x => x.TaskId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_comments_task");
        comment.HasOne(x => x.AuthorUser).WithMany().HasForeignKey(x => x.AuthorUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_comments_author");
        comment.HasOne(x => x.RedactedByUser).WithMany().HasForeignKey(x => x.RedactedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_task_comments_redacted_by");
        comment.HasIndex(x => new { x.TaskId, x.CreatedAtUtc }).HasDatabaseName("ix_task_comments_task_created");
    }
}
