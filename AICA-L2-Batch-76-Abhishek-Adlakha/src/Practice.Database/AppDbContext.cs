using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

public sealed class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<IndiaState> IndiaStates => Set<IndiaState>();
    public DbSet<AppSetting> AppSettings => Set<AppSetting>();
    public DbSet<HolidayCalendar> HolidayCalendars => Set<HolidayCalendar>();
    public DbSet<Holiday> Holidays => Set<Holiday>();
    public DbSet<AuditEvent> AuditEvents => Set<AuditEvent>();
    public DbSet<OutboxMessage> OutboxMessages => Set<OutboxMessage>();
    public DbSet<ImportRun> ImportRuns => Set<ImportRun>();
    public DbSet<ImportIssue> ImportIssues => Set<ImportIssue>();
    public DbSet<LoginUser> Users => Set<LoginUser>();
    public DbSet<UserSession> UserSessions => Set<UserSession>();
    public DbSet<Role> Roles => Set<Role>();
    public DbSet<PermissionDefinition> Permissions => Set<PermissionDefinition>();
    public DbSet<UserRole> UserRoles => Set<UserRole>();
    public DbSet<RolePermissionGrant> RolePermissions => Set<RolePermissionGrant>();
    public DbSet<Employee> Employees => Set<Employee>();
    public DbSet<Team> Teams => Set<Team>();
    public DbSet<TeamMembership> TeamMemberships => Set<TeamMembership>();
    public DbSet<FieldDefinition> FieldDefinitions => Set<FieldDefinition>();
    public DbSet<ClientCategory> ClientCategories => Set<ClientCategory>();
    public DbSet<Client> Clients => Set<Client>();
    public DbSet<ClientContact> ClientContacts => Set<ClientContact>();
    public DbSet<ClientAddress> ClientAddresses => Set<ClientAddress>();
    public DbSet<GstRegistration> GstRegistrations => Set<GstRegistration>();
    public DbSet<TanRegistration> TanRegistrations => Set<TanRegistration>();
    public DbSet<ClientGroup> ClientGroups => Set<ClientGroup>();
    public DbSet<ClientGroupMembership> ClientGroupMemberships => Set<ClientGroupMembership>();
    public DbSet<ClientImportMapping> ClientImportMappings => Set<ClientImportMapping>();
    public DbSet<ClientImportResult> ClientImportResults => Set<ClientImportResult>();
    public DbSet<ServiceCategory> ServiceCategories => Set<ServiceCategory>();
    public DbSet<ServiceDefinition> Services => Set<ServiceDefinition>();
    public DbSet<ClientService> ClientServices => Set<ClientService>();
    public DbSet<ServiceImportProposal> ServiceImportProposals => Set<ServiceImportProposal>();
    public DbSet<WorkTaskStatus> TaskStatuses => Set<WorkTaskStatus>();
    public DbSet<TaskStatusTransition> TaskStatusTransitions => Set<TaskStatusTransition>();
    public DbSet<PracticeTask> Tasks => Set<PracticeTask>();
    public DbSet<TaskAssignment> TaskAssignments => Set<TaskAssignment>();
    public DbSet<TaskStatusHistory> TaskStatusHistory => Set<TaskStatusHistory>();
    public DbSet<TaskComment> TaskComments => Set<TaskComment>();
    public DbSet<RecurrenceRule> RecurrenceRules => Set<RecurrenceRule>();
    public DbSet<RecurrenceRuleMonth> RecurrenceRuleMonths => Set<RecurrenceRuleMonth>();
    public DbSet<RecurrenceAdjustment> RecurrenceExceptions => Set<RecurrenceAdjustment>();
    public DbSet<TaskGenerationRun> TaskGenerationRuns => Set<TaskGenerationRun>();
    public DbSet<TaskGenerationRunItem> TaskGenerationRunItems => Set<TaskGenerationRunItem>();
    public DbSet<BillingEntity> BillingEntities => Set<BillingEntity>();
    public DbSet<BillingTerm> BillingTerms => Set<BillingTerm>();
    public DbSet<BillingSchedule> BillingSchedules => Set<BillingSchedule>();
    public DbSet<BillingScheduleMonth> BillingScheduleMonths => Set<BillingScheduleMonth>();
    public DbSet<BillingImportProposal> BillingImportProposals => Set<BillingImportProposal>();

    public override int SaveChanges(bool acceptAllChangesOnSuccess)
    {
        GuardImmutableAuditEvents();
        return base.SaveChanges(acceptAllChangesOnSuccess);
    }

    public override Task<int> SaveChangesAsync(
        bool acceptAllChangesOnSuccess,
        CancellationToken cancellationToken = default)
    {
        GuardImmutableAuditEvents();
        return base.SaveChangesAsync(acceptAllChangesOnSuccess, cancellationToken);
    }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        FoundationModel.Configure(modelBuilder);
        IdentityModel.Configure(modelBuilder);
        ClientModel.Configure(modelBuilder);
        ServiceModel.Configure(modelBuilder);
        SchedulingModel.Configure(modelBuilder);
        TaskModel.Configure(modelBuilder);
        BillingModel.Configure(modelBuilder);
    }

    private void GuardImmutableAuditEvents()
    {
        if (ChangeTracker.Entries<AuditEvent>().Any(entry =>
                entry.State is EntityState.Modified or EntityState.Deleted))
        {
            throw new InvalidOperationException("Audit events are append-only.");
        }

        if (ChangeTracker.Entries<TaskStatusHistory>().Any(entry =>
                entry.State is EntityState.Modified or EntityState.Deleted))
        {
            throw new InvalidOperationException("Task status history is append-only.");
        }
    }
}
