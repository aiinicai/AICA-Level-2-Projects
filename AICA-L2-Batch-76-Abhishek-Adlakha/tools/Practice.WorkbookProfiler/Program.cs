using System.Text.Json;
using Practice.WorkbookProfiler;

if (args.Length == 0 || args.Contains("--help", StringComparer.Ordinal))
{
    Console.WriteLine("Usage: dotnet run --project tools/Practice.WorkbookProfiler -- <workbook.xlsx|xlsm> [--client-dry-run|--service-dry-run] [--reference <values.txt>] [--output <report.json>]");
    return args.Length == 0 ? 2 : 0;
}

var workbookPath = Path.GetFullPath(args[0]);
var referencePath = GetOption(args, "--reference");
var outputPath = GetOption(args, "--output");
var referenceValues = referencePath is null
    ? Array.Empty<string>()
    : await File.ReadAllLinesAsync(Path.GetFullPath(referencePath));

object report = args.Contains("--service-dry-run", StringComparer.Ordinal)
    ? ServiceDryRunService.Analyze(workbookPath)
    : args.Contains("--client-dry-run", StringComparer.Ordinal)
        ? ClientDryRunService.Analyze(workbookPath)
        : WorkbookProfilerService.Profile(workbookPath, referenceValues);
var json = JsonSerializer.Serialize(report, WorkbookProfilerService.JsonOptions);

if (outputPath is null)
{
    Console.WriteLine(json);
}
else
{
    await File.WriteAllTextAsync(Path.GetFullPath(outputPath), json + Environment.NewLine);
    Console.WriteLine($"Profile written to {Path.GetFullPath(outputPath)}");
}

return 0;

static string? GetOption(string[] arguments, string option)
{
    var index = Array.IndexOf(arguments, option);
    if (index < 0)
    {
        return null;
    }

    if (index + 1 >= arguments.Length)
    {
        throw new ArgumentException($"{option} requires a value.");
    }

    return arguments[index + 1];
}
