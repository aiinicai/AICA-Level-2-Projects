using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Identity;

if (args.Length == 0 || args[0] is "--help" or "help")
{
    Console.WriteLine("Usage: Practice.AdminCli bootstrap-admin --mobile <10-digits> [--name <name>] [--employee-code <code>]");
    Console.WriteLine("       Practice.AdminCli reset-password --mobile <10-digits>");
    Console.WriteLine("The password is entered twice without echo, or read from PRACTICE_BOOTSTRAP_PASSWORD for controlled automation.");
    return args.Length == 0 ? 2 : 0;
}

if (args[0] is not ("bootstrap-admin" or "reset-password"))
{
    Console.Error.WriteLine("Unknown command. Use --help.");
    return 2;
}

var mobile = Option(args, "--mobile") ?? throw new ArgumentException("--mobile is required.");
var password = Environment.GetEnvironmentVariable("PRACTICE_BOOTSTRAP_PASSWORD");
if (password is null)
{
    password = ReadSecret("New password: ");
    var confirmation = ReadSecret("Confirm new password: ");
    if (!string.Equals(password, confirmation, StringComparison.Ordinal))
    {
        Console.Error.WriteLine("The passwords did not match. No change was made.");
        return 1;
    }
}

var builder = Host.CreateApplicationBuilder(args);
var externalConfigurationPath = Environment.GetEnvironmentVariable("PRACTICE_CONFIG_FILE");
if (!string.IsNullOrWhiteSpace(externalConfigurationPath))
{
    builder.Configuration.AddJsonFile(externalConfigurationPath, optional: false, reloadOnChange: false);
}
builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddPracticeDatabase(builder.Configuration, addReadinessCheck: false);
builder.Services.AddPracticeIdentity();
using var host = builder.Build();
await using var scope = host.Services.CreateAsyncScope();
IReadOnlyList<string> errors;
if (args[0] == "bootstrap-admin")
{
    var name = Option(args, "--name") ?? "Abhishek Adlakha";
    var employeeCode = Option(args, "--employee-code") ?? "ADMIN001";
    var service = scope.ServiceProvider.GetRequiredService<BootstrapAdministratorService>();
    errors = await service.BootstrapAsync(
        new BootstrapAdministratorRequest(name, employeeCode, mobile, password), CancellationToken.None);
}
else
{
    var service = scope.ServiceProvider.GetRequiredService<LocalAccountRecoveryService>();
    errors = await service.ResetPasswordAsync(mobile, password, CancellationToken.None);
}
if (errors.Count > 0)
{
    foreach (var error in errors) Console.Error.WriteLine(error);
    return 1;
}

Console.WriteLine(args[0] == "bootstrap-admin"
    ? "Bootstrap administrator created. The password was not logged or stored in plaintext."
    : "Password reset completed. Existing sessions were revoked and the password was not logged or stored in plaintext.");
return 0;

static string? Option(string[] arguments, string name)
{
    var index = Array.IndexOf(arguments, name);
    return index >= 0 && index + 1 < arguments.Length ? arguments[index + 1] : null;
}

static string ReadSecret(string prompt)
{
    Console.Write(prompt);
    var characters = new List<char>();
    while (true)
    {
        var key = Console.ReadKey(intercept: true);
        if (key.Key == ConsoleKey.Enter) break;
        if (key.Key == ConsoleKey.Backspace && characters.Count > 0)
        {
            characters.RemoveAt(characters.Count - 1);
            continue;
        }
        if (!char.IsControl(key.KeyChar)) characters.Add(key.KeyChar);
    }
    Console.WriteLine();
    return new string(characters.ToArray());
}
