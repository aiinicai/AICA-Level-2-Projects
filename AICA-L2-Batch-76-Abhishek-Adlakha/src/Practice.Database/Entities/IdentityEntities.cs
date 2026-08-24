namespace Practice.Database.Entities;

public sealed class LoginUser
{
    public Guid Id { get; set; }
    public required string MobileUsername { get; set; }
    public required string PasswordHash { get; set; }
    public required string SecurityStamp { get; set; }
    public bool MustChangePassword { get; set; }
    public bool IsActive { get; set; } = true;
    public int FailedLoginCount { get; set; }
    public DateTimeOffset? LockedUntilUtc { get; set; }
    public DateTimeOffset? LastLoginAtUtc { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<UserSession> Sessions { get; } = new List<UserSession>();
    public ICollection<UserRole> UserRoles { get; } = new List<UserRole>();
}

public sealed class UserSession
{
    public Guid Id { get; set; }
    public Guid UserId { get; set; }
    public LoginUser User { get; set; } = null!;
    public required byte[] TokenHash { get; set; }
    public required string SecurityStamp { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset LastSeenAtUtc { get; set; }
    public DateTimeOffset ExpiresAtUtc { get; set; }
    public DateTimeOffset? RevokedAtUtc { get; set; }
    public string? RevocationReason { get; set; }
    public byte[]? IpHash { get; set; }
    public string? UserAgent { get; set; }
}

public sealed class Role
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public required string Description { get; set; }
    public bool IsSystem { get; set; }
    public bool IsProtected { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<UserRole> UserRoles { get; } = new List<UserRole>();
    public ICollection<RolePermissionGrant> RolePermissions { get; } = new List<RolePermissionGrant>();
}

public sealed class PermissionDefinition
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Module { get; set; }
    public required string Action { get; set; }
    public required string Description { get; set; }
    public bool SupportsScope { get; set; }
    public ICollection<RolePermissionGrant> RolePermissions { get; } = new List<RolePermissionGrant>();
}

public sealed class UserRole
{
    public Guid UserId { get; set; }
    public LoginUser User { get; set; } = null!;
    public Guid RoleId { get; set; }
    public Role Role { get; set; } = null!;
    public DateTimeOffset AssignedAtUtc { get; set; }
    public Guid? AssignedByUserId { get; set; }
}

public sealed class RolePermissionGrant
{
    public Guid RoleId { get; set; }
    public Role Role { get; set; } = null!;
    public Guid PermissionId { get; set; }
    public PermissionDefinition Permission { get; set; } = null!;
    public required string ScopeCeiling { get; set; }
}

public sealed class Employee
{
    public Guid Id { get; set; }
    public Guid? UserId { get; set; }
    public LoginUser? User { get; set; }
    public required string EmployeeCode { get; set; }
    public required string NormalizedEmployeeCode { get; set; }
    public required string DisplayName { get; set; }
    public string? Email { get; set; }
    public string? MobileNumber { get; set; }
    public string? Designation { get; set; }
    public string? Department { get; set; }
    public Guid? ManagerEmployeeId { get; set; }
    public Employee? ManagerEmployee { get; set; }
    public DateOnly? JoinedOn { get; set; }
    public DateOnly? LeftOn { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<Employee> DirectReports { get; } = new List<Employee>();
    public ICollection<TeamMembership> TeamMemberships { get; } = new List<TeamMembership>();
}

public sealed class Team
{
    public Guid Id { get; set; }
    public required string Code { get; set; }
    public required string Name { get; set; }
    public Guid? ManagerEmployeeId { get; set; }
    public Employee? ManagerEmployee { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<TeamMembership> Memberships { get; } = new List<TeamMembership>();
}

public sealed class TeamMembership
{
    public Guid TeamId { get; set; }
    public Team Team { get; set; } = null!;
    public Guid EmployeeId { get; set; }
    public Employee Employee { get; set; } = null!;
    public DateOnly ValidFrom { get; set; }
    public DateOnly? ValidTo { get; set; }
    public bool IsLead { get; set; }
}

public sealed class FieldDefinition
{
    public required string EntityType { get; set; }
    public required string FieldKey { get; set; }
    public required string Label { get; set; }
    public required string Description { get; set; }
    public bool IsSystemRequired { get; set; }
    public bool IsAdministratorRequired { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public Guid? UpdatedByUserId { get; set; }
}
