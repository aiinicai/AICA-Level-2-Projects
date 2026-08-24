namespace Practice.Database.Entities;

public sealed class ServiceCategory
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string NormalizedName { get; set; }
    public int DisplayOrder { get; set; }
    public bool IsActive { get; set; } = true;
    public ICollection<ServiceDefinition> Services { get; } = new List<ServiceDefinition>();
}

public sealed class ServiceDefinition
{
    public Guid Id { get; set; }
    public Guid CategoryId { get; set; }
    public ServiceCategory Category { get; set; } = null!;
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string NormalizedName { get; set; }
    public string? Description { get; set; }
    public bool DefaultBillable { get; set; } = true;
    public bool SupportsRecurrence { get; set; }
    public bool SupportsGstinScope { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<ClientService> ClientServices { get; } = new List<ClientService>();
}

public sealed class ClientService
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public Guid ServiceId { get; set; }
    public ServiceDefinition Service { get; set; } = null!;
    public Guid? GstRegistrationId { get; set; }
    public GstRegistration? GstRegistration { get; set; }
    public string? EngagementCode { get; set; }
    public string? TitleOverride { get; set; }
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public bool IsActive { get; set; } = true;
    public required string DefaultPriority { get; set; } = "NORMAL";
    public Guid? ResponsibleTeamId { get; set; }
    public Team? ResponsibleTeam { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset? DeactivatedAtUtc { get; set; }
    public string? DeactivationReason { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class ServiceImportProposal
{
    public long Id { get; set; }
    public Guid ImportRunId { get; set; }
    public ImportRun ImportRun { get; set; } = null!;
    public int SourceRowNumber { get; set; }
    public string? SourceClientCode { get; set; }
    public string? ProposedClientCode { get; set; }
    public required string SourceColumn { get; set; }
    public required string ServiceCode { get; set; }
    public string? ProposedGstin { get; set; }
    public Guid? ClientServiceId { get; set; }
    public ClientService? ClientService { get; set; }
    public required string Outcome { get; set; }
    public required string DataJson { get; set; }
}
