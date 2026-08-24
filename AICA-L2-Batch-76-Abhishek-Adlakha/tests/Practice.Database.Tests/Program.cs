using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Practice.Database;
using Practice.Database.Entities;

var options = new DbContextOptionsBuilder<AppDbContext>()
    .UseNpgsql("Host=127.0.0.1;Database=model_check;Username=unused;Password=unused")
    .Options;
using var database = new AppDbContext(options);


var designModel = database.GetService<IDesignTimeModel>().Model;
var entities = designModel.GetEntityTypes().ToArray();
Require(entities.Length == 48, "Expected forty-eight entities: 47 through Phase 7 plus TAN registrations.");
Require(entities.Select(entity => entity.GetSchema()).ToHashSet(StringComparer.Ordinal)
    .SetEquals(["reference", "system", "audit", "import", "identity", "employees", "clients", "services", "tasks", "scheduling", "billing"]), "Unexpected database schema ownership.");

var stateEntity = designModel.FindEntityType(typeof(IndiaState))
    ?? throw new InvalidOperationException("IndiaState model is missing.");
Require(stateEntity.GetSeedData().Count() == 36, "Expected 36 active India state/UT reference rows.");
Require(database.Database.GetMigrations().Count() == 11, "Expected eleven migrations through the TAN registration change.");
var tanEntity = designModel.FindEntityType(typeof(TanRegistration))
    ?? throw new InvalidOperationException("TAN registration model is missing.");
Require(tanEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter() == "is_primary AND is_active"),
    "A client may hold many TANs but only one primary registration.");
// The workbook already holds the same TAN against two different PANs, so duplicates are
// reported rather than enforced. Enforcing here would block an import over a data-entry issue.
Require(!tanEntity.GetIndexes().Any(index => index.IsUnique && index.Properties.Count == 1 && index.Properties[0].Name == nameof(TanRegistration.Tan)),
    "TAN duplicates are reported, not enforced, until the firm signs off the exceptions.");

var roleEntity = designModel.FindEntityType(typeof(Role))
    ?? throw new InvalidOperationException("Role model is missing.");
Require(roleEntity.GetSeedData().Select(row => (string)row[nameof(Role.Name)]!).ToHashSet(StringComparer.Ordinal)
    .SetEquals(["Administrators", "Manager", "Articles", "Paid Assistants", "Accountants", "Client Accountants"]),
    "The required default roles were not seeded exactly.");

var permissionEntity = designModel.FindEntityType(typeof(PermissionDefinition))
    ?? throw new InvalidOperationException("Permission model is missing.");
Require(permissionEntity.GetSeedData().Count() == 34, "Expected 34 permission definitions through Phase 8.");

var fieldEntity = designModel.FindEntityType(typeof(FieldDefinition))
    ?? throw new InvalidOperationException("FieldDefinition model is missing.");
var fields = fieldEntity.GetSeedData();
Require(fields.Count() == 42, "Expected employee, client, client-service, task, and billing field policies.");
Require(fields.Where(row => (bool)row[nameof(FieldDefinition.IsSystemRequired)]!)
    .All(row => (bool)row[nameof(FieldDefinition.IsAdministratorRequired)]!),
    "System-required fields must also be administrator-required.");

var categoryEntity = designModel.FindEntityType(typeof(ClientCategory))
    ?? throw new InvalidOperationException("ClientCategory model is missing.");
Require(categoryEntity.GetSeedData().Count() == 11, "Expected eleven legal-constitution categories.");
Require(!categoryEntity.GetSeedData().Any(row => (string)row[nameof(ClientCategory.Code)]! == "FIRM"),
    "Ambiguous workbook value Firm must not be seeded as a legal category.");

var gstEntity = designModel.FindEntityType(typeof(GstRegistration))
    ?? throw new InvalidOperationException("GST registration model is missing.");
Require(gstEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter() == "is_primary AND is_active"),
    "GST registrations must enforce one active primary registration per client.");
Require(ClientRules.IsValidGstin("27AAPFU0939F1ZV"), "Known valid GSTIN should pass checksum validation.");
Require(!ClientRules.IsValidGstin("27AAPFU0939F1ZA"), "GSTIN with an invalid checksum should fail validation.");
Require(ClientRules.IsValidPan("ABCDE1234F") && !ClientRules.IsValidPan("ABCDE12345"), "PAN validation is incorrect.");

var serviceCategoryEntity = designModel.FindEntityType(typeof(ServiceCategory))
    ?? throw new InvalidOperationException("ServiceCategory model is missing.");
Require(serviceCategoryEntity.GetSeedData().Count() == 5, "Expected five service categories.");
var serviceEntity = designModel.FindEntityType(typeof(ServiceDefinition))
    ?? throw new InvalidOperationException("ServiceDefinition model is missing.");
Require(serviceEntity.GetSeedData().Count() == 21, "Expected the twenty-one approved workbook services.");
var clientServiceEntity = designModel.FindEntityType(typeof(ClientService))
    ?? throw new InvalidOperationException("ClientService model is missing.");
Require(clientServiceEntity.GetIndexes().Count(index => index.IsUnique && index.GetFilter()?.Contains("is_active", StringComparison.Ordinal) == true) == 2,
    "Client services must enforce active unscoped and GSTIN-scoped uniqueness.");

var taskStatusEntity = designModel.FindEntityType(typeof(WorkTaskStatus))
    ?? throw new InvalidOperationException("Task status model is missing.");
Require(taskStatusEntity.GetSeedData().Select(row => (string)row[nameof(WorkTaskStatus.Code)]!).ToHashSet(StringComparer.Ordinal)
    .SetEquals(["NOT_STARTED", "IN_PROCESS", "ON_HOLD", "COMPLETED", "CANCELLED"]),
    "The five approved task statuses must be seeded exactly.");
var transitionEntity = designModel.FindEntityType(typeof(TaskStatusTransition))
    ?? throw new InvalidOperationException("Task transition model is missing.");
Require(transitionEntity.GetSeedData().Count() == 11, "Expected the approved Phase 5 transition graph.");
Require(transitionEntity.GetSeedData().Where(row => (string)row[nameof(TaskStatusTransition.RequiredPermission)]! == "tasks.reopen")
    .All(row => (bool)row[nameof(TaskStatusTransition.ReasonRequired)]!), "Every reopen transition must require a reason.");
var taskEntity = designModel.FindEntityType(typeof(PracticeTask))
    ?? throw new InvalidOperationException("Task model is missing.");
Require(taskEntity.FindProperty(nameof(PracticeTask.RowVersion))?.IsConcurrencyToken == true, "Tasks must use optimistic concurrency.");
var assignmentEntity = designModel.FindEntityType(typeof(TaskAssignment))
    ?? throw new InvalidOperationException("Task assignment model is missing.");
Require(assignmentEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter()?.Contains("assignment_role = 'PRIMARY'", StringComparison.Ordinal) == true),
    "Tasks must enforce one current primary assignee.");
Require(taskEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter() == "occurrence_key IS NOT NULL"),
    "Generated task occurrence keys must be unique and nullable for manual work.");
var recurrenceEntity = designModel.FindEntityType(typeof(RecurrenceRule))
    ?? throw new InvalidOperationException("Recurrence rule model is missing.");
Require(recurrenceEntity.FindProperty(nameof(RecurrenceRule.RowVersion))?.IsConcurrencyToken == true,
    "Recurrence rules must use optimistic concurrency.");
Require(recurrenceEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter() == "is_active"),
    "Only one active recurrence version may exist per client-service agreement.");

var billingEntity = designModel.FindEntityType(typeof(BillingEntity))
    ?? throw new InvalidOperationException("BillingEntity model is missing.");
Require(!billingEntity.GetSeedData().Any(), "Legal billing entities must not be guessed or seeded.");
Require(billingEntity.GetIndexes().Any(index => index.IsUnique && index.GetFilter() == "gstin IS NOT NULL"),
    "Billing-entity GSTINs must be unique when present.");
Require(billingEntity.FindProperty(nameof(BillingEntity.RowVersion))?.IsConcurrencyToken == true,
    "Billing entities must use optimistic concurrency.");
var billingTerm = designModel.FindEntityType(typeof(BillingTerm))
    ?? throw new InvalidOperationException("BillingTerm model is missing.");
Require(billingTerm.FindProperty(nameof(BillingTerm.Amount))?.GetPrecision() == 19 && billingTerm.FindProperty(nameof(BillingTerm.Amount))?.GetScale() == 2,
    "Fixed fees must use numeric(19,2), never floating point.");
Require(billingTerm.GetIndexes().Any(index => index.IsUnique && index.Properties.Select(property => property.Name).SequenceEqual([nameof(BillingTerm.ClientServiceId), nameof(BillingTerm.Version)])),
    "Billing-term versions must be unique per client-service agreement.");
var billingSchedule = designModel.FindEntityType(typeof(BillingSchedule))
    ?? throw new InvalidOperationException("BillingSchedule model is missing.");
Require(billingSchedule.GetCheckConstraints().Any(check => check.Name == "ck_billing_schedules_shape"),
    "Billing schedules must enforce one-time versus recurring field combinations.");

var audit = new AuditEvent
{
    Id = Guid.NewGuid(),
    OccurredAtUtc = DateTimeOffset.UtcNow,
    Action = "Test",
    EntityType = "TestEntity",
    DataJson = "{}"
};
database.Attach(audit);
database.Entry(audit).State = EntityState.Modified;
try
{
    database.SaveChanges();
    throw new InvalidOperationException("Modified audit event was unexpectedly accepted.");
}
catch (InvalidOperationException exception) when (exception.Message == "Audit events are append-only.")
{
}
database.Entry(audit).State = EntityState.Unchanged;

var history = new TaskStatusHistory
{
    Id = Guid.NewGuid(), TaskId = Guid.NewGuid(), ToStatusId = TaskSeed.NotStartedId,
    ActorUserId = Guid.NewGuid(), ChangedAtUtc = DateTimeOffset.UtcNow, MetadataJson = "{}"
};
database.Attach(history);
database.Entry(history).State = EntityState.Modified;
try
{
    database.SaveChanges();
    throw new InvalidOperationException("Modified task status history was unexpectedly accepted.");
}
catch (InvalidOperationException exception) when (exception.Message == "Task status history is append-only.")
{
}

// Phase 10 audit retention: three months for routine history, twelve for security history.
var retentionNow = new DateTimeOffset(2026, 8, 21, 0, 0, 0, TimeSpan.Zero);
Require(AuditRetention.IsSecurityAction("identity.login_failed"), "identity.* actions are security history.");
Require(AuditRetention.IsSecurityAction("reports.exported"), "Exports remove confidential data and are security history.");
Require(!AuditRetention.IsSecurityAction("clients.updated"), "Routine business changes are not security history.");
Require(AuditRetention.IsExpired("clients.updated", retentionNow.AddMonths(-4), retentionNow),
    "Routine history older than three months must expire.");
Require(!AuditRetention.IsExpired("clients.updated", retentionNow.AddMonths(-2), retentionNow),
    "Routine history inside three months must be kept.");
Require(!AuditRetention.IsExpired("identity.login_failed", retentionNow.AddMonths(-4), retentionNow),
    "Security history must outlive the routine window.");
Require(AuditRetention.IsExpired("identity.login_failed", retentionNow.AddMonths(-13), retentionNow),
    "Security history older than twelve months must expire.");
Require(!AuditRetention.IsExpired("clients.updated", retentionNow.AddMonths(-3).AddMinutes(1), retentionNow),
    "The three-month boundary must not expire history a minute early.");

Console.WriteLine("Database, billing-projection permission and audit retention checks passed.");
return 0;

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
