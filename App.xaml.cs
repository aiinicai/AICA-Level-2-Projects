using System.IO;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Threading;

namespace AutoBankStatementEntry;

public partial class App : Application
{
    /// <summary>Per-PC crash/diagnostic log: %LOCALAPPDATA%\AutoBankStatementEntry\logs\app-yyyyMMdd.log</summary>
    public static string LogDir { get; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AutoBankStatementEntry", "logs");

    private static readonly object LogLock = new();

    protected override void OnStartup(StartupEventArgs e)
    {
        // Any exception escaping an event handler used to terminate the whole app (losing the reviewed grid).
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            Log("UnobservedTaskException", args.Exception);
            args.SetObserved();
        };
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
            Log("AppDomain.UnhandledException", args.ExceptionObject as Exception);
        // Every ₹ amount on screen in lakh/crore grouping (12,34,567.89). Dates keep the PC's own settings.
        AutoBankStatementEntry.Models.IndianNumberFormat.ApplyToCurrentThreadAndDefaults();
        base.OnStartup(e);
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        Log("DispatcherUnhandledException", e.Exception);
        e.Handled = true;
        try
        {
            MessageBox.Show(
                $"An unexpected error occurred and was logged:\n\n{e.Exception.Message}\n\nYour work on screen has been kept. " +
                $"If this repeats, send the log file from:\n{LogDir}",
                "Auto Bank Statement Entry — Error", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        catch { /* never throw from the crash handler */ }
    }

    public static void Log(string context, Exception? ex)
    {
        try
        {
            lock (LogLock)
            {
                Directory.CreateDirectory(LogDir);
                var file = Path.Combine(LogDir, $"app-{DateTime.Now.ToString("yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture)}.log");
                File.AppendAllText(file,
                    $"[{DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", System.Globalization.CultureInfo.InvariantCulture)}] {Environment.MachineName}\\{Environment.UserName} {context}: {ex}{Environment.NewLine}{Environment.NewLine}");
            }
        }
        catch { /* logging must never crash the app */ }
    }
}
