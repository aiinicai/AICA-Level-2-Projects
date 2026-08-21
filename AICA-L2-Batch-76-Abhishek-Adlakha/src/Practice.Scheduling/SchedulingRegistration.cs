using Microsoft.Extensions.DependencyInjection;

namespace Practice.Scheduling;

public static class SchedulingRegistration
{
    public static IServiceCollection AddPracticeScheduling(this IServiceCollection services)
    {
        services.AddScoped<TaskGenerationService>();
        return services;
    }
}
