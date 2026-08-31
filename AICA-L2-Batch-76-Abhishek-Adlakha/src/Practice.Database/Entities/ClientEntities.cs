namespace Practice.Database.Entities;

public sealed class ClientCategory
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string NormalizedName { get; set; }
    public int DisplayOrder { get; set; }
    public bool IsActive { get; set; } = true;
    public ICollection<Client> Clients { get; } = new List<Client>();
}

public sealed class Client
{
    public Guid Id { get; set; }
    public required string ClientCode { get; set; }
    public required string NormalizedClientCode { get; set; }
    public string? LegacyCode { get; set; }
    public required string DisplayName { get; set; }
    public required string NormalizedDisplayName { get; set; }
    public string? LegalName { get; set; }
    public Guid? CategoryId { get; set; }
    public ClientCategory? Category { get; set; }
    public string? Pan { get; set; }
    public string? Tan { get; set; }
    public DateOnly? OnboardedOn { get; set; }
    public required string Status { get; set; } = "ACTIVE";
    public DateOnly? DeactivatedOn { get; set; }
    public string? DeactivationReason { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<ClientContact> Contacts { get; } = new List<ClientContact>();
    public ICollection<ClientAddress> Addresses { get; } = new List<ClientAddress>();
    public ICollection<GstRegistration> GstRegistrations { get; } = new List<GstRegistration>();
    public ICollection<TanRegistration> TanRegistrations { get; } = new List<TanRegistration>();
    public ICollection<ClientGroupMembership> GroupMemberships { get; } = new List<ClientGroupMembership>();
}

public sealed class ClientContact
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public required string ContactType { get; set; }
    public required string Name { get; set; }
    public string? Designation { get; set; }
    public string? Phone { get; set; }
    public string? Email { get; set; }
    public bool IsPrimary { get; set; }
    public bool IsActive { get; set; } = true;
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class ClientAddress
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public required string AddressType { get; set; }
    public required string Line1 { get; set; }
    public string? Line2 { get; set; }
    public string? City { get; set; }
    public string? District { get; set; }
    public string? StateCode { get; set; }
    public IndiaState? State { get; set; }
    public string? PostalCode { get; set; }
    public required string CountryCode { get; set; } = "IN";
    public bool IsPrimary { get; set; }
    public bool IsActive { get; set; } = true;
    public DateOnly ValidFrom { get; set; }
    public DateOnly? ValidTo { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class GstRegistration
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public required string Gstin { get; set; }
    public required string StateCode { get; set; }
    public IndiaState State { get; set; } = null!;
    public string? TradeName { get; set; }
    public required string RegistrationStatus { get; set; } = "ACTIVE";
    public DateOnly? EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public bool IsPrimary { get; set; }
    public bool IsActive { get; set; } = true;
    public string? CancellationReason { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class ClientGroup
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string NormalizedName { get; set; }
    public string? Description { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<ClientGroupMembership> Memberships { get; } = new List<ClientGroupMembership>();
}

public sealed class ClientGroupMembership
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public Guid GroupId { get; set; }
    public ClientGroup Group { get; set; } = null!;
    public required string MembershipType { get; set; } = "SECONDARY";
    public DateOnly EffectiveFrom { get; set; }
    public DateOnly? ValidTo { get; set; }
    public string? Notes { get; set; }
}

// A deductor may hold more than one TAN, typically one per branch or division, so TANs are a
// collection like GST registrations rather than a single field. Client.Tan is kept in step with
// whichever registration is primary, because the registers, exports and reports read that column.
public sealed class TanRegistration
{
    public Guid Id { get; set; }
    public Guid ClientId { get; set; }
    public Client Client { get; set; } = null!;
    public required string Tan { get; set; }
    public string? DeductorName { get; set; }
    public string? Branch { get; set; }
    public DateOnly? EffectiveFrom { get; set; }
    public DateOnly? EffectiveTo { get; set; }
    public bool IsPrimary { get; set; }
    public bool IsActive { get; set; } = true;
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public sealed class ClientImportMapping
{
    public Guid Id { get; set; }
    public required string SourceField { get; set; }
    public required string SourceValue { get; set; }
    public required string NormalizedSourceValue { get; set; }
    public required string TargetType { get; set; }
    public Guid? TargetId { get; set; }
    public bool IsApproved { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public Guid? UpdatedByUserId { get; set; }
}

public sealed class ClientImportResult
{
    public long Id { get; set; }
    public Guid ImportRunId { get; set; }
    public ImportRun ImportRun { get; set; } = null!;
    public int SourceRowNumber { get; set; }
    public string? SourceClientCode { get; set; }
    public string? ProposedClientCode { get; set; }
    public Guid? ClientId { get; set; }
    public required string Outcome { get; set; }
    public required string DataJson { get; set; }
}
