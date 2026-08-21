namespace Practice.BuildingBlocks.Clock;

public interface IClock
{
    DateTimeOffset UtcNow { get; }
}

