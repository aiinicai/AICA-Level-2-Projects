extern alias PracticeApi;

using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Hosting;

namespace Practice.Api.IntegrationTests;

// WebApplicationFactory infers a content root from the assembly name, which does not match this
// repository's src/ layout, so the API project directory is located explicitly.
internal sealed class ApiFactory : WebApplicationFactory<PracticeApi::Program>
{
    protected override IHost CreateHost(IHostBuilder builder)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "global.json")))
        {
            directory = directory.Parent;
        }
        var repositoryRoot = directory?.FullName
            ?? throw new InvalidOperationException("Could not locate repository root containing global.json.");
        builder.UseContentRoot(Path.Combine(repositoryRoot, "src", "Practice.Api"));
        return base.CreateHost(builder);
    }
}
