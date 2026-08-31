using Microsoft.AspNetCore.Identity;
using Microsoft.Extensions.DependencyInjection;
using Practice.Database.Entities;

namespace Practice.Identity;

public static class IdentityRegistration
{
    public static IServiceCollection AddPracticeIdentity(this IServiceCollection services)
    {
        services.AddScoped<IPasswordHasher<LoginUser>, PasswordHasher<LoginUser>>();
        services.AddScoped<IdentityService>();
        services.AddScoped<BootstrapAdministratorService>();
        services.AddScoped<LocalAccountRecoveryService>();
        return services;
    }
}
