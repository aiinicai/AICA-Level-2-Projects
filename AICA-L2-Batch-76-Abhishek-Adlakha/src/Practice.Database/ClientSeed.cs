using Practice.Database.Entities;

namespace Practice.Database;

public static class ClientSeed
{
    private static readonly (string Id, string Code, string Name)[] Definitions =
    [
        ("30000000-0000-0000-0000-000000000001", "INDIVIDUAL", "Individual"),
        ("30000000-0000-0000-0000-000000000002", "HUF", "HUF"),
        ("30000000-0000-0000-0000-000000000003", "PARTNERSHIP", "Partnership"),
        ("30000000-0000-0000-0000-000000000004", "LLP", "LLP"),
        ("30000000-0000-0000-0000-000000000005", "PRIVATE_LIMITED", "Private Limited Company"),
        ("30000000-0000-0000-0000-000000000006", "PUBLIC_LIMITED", "Public Limited Company"),
        ("30000000-0000-0000-0000-000000000007", "TRUST", "Trust"),
        ("30000000-0000-0000-0000-000000000008", "SOCIETY", "Society"),
        ("30000000-0000-0000-0000-000000000009", "PROPRIETORSHIP", "Proprietorship"),
        ("30000000-0000-0000-0000-000000000010", "OPC", "One Person Company"),
        ("30000000-0000-0000-0000-000000000011", "OTHER", "Other")
    ];

    public static readonly ClientCategory[] Categories = Definitions.Select((item, index) => new ClientCategory
    {
        Id = Guid.Parse(item.Id), Code = item.Code, Name = item.Name,
        NormalizedName = item.Name.ToUpperInvariant(), DisplayOrder = (index + 1) * 10, IsActive = true
    }).ToArray();
}
