// Lease116.exe - Windows launcher for Lease116 (Ind AS 116 / IFRS 16 lease accounting).
//
// Double-click to use Lease116: the local server starts in the background (no console window), the browser opens at
// http://127.0.0.1:8116 and a Lease116 icon appears next to the clock (right-click it > Stop Lease116 to close the app).
// The launcher uses the private Python environment created by Setup.bat (%LOCALAPPDATA%\Lease116\venv); it contains no
// accounting logic. Server output is written to %LOCALAPPDATA%\Lease116\logs\server.log.
//
// Build: installer\launcher\build_launcher.sh (Mono) or build_launcher.cmd (the C# compiler included with Windows).
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Lease116")]
[assembly: AssemblyDescription("Lease116 - Ind AS 116 / IFRS 16 lease accounting")]
[assembly: AssemblyProduct("Lease116")]
[assembly: AssemblyCopyright("Lease116")]
[assembly: AssemblyVersion("1.0.1.0")]
[assembly: AssemblyFileVersion("1.0.1.0")]
[assembly: ComVisible(false)]

namespace Lease116
{
    static class Program
    {
        [DllImport("user32.dll")]
        static extern bool SetProcessDPIAware();

        [STAThread]
        static int Main(string[] args)
        {
            try { SetProcessDPIAware(); } catch { }       // crisp tray icon and messages on scaled displays
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            var env = new LaunchEnv();
            bool first;
            using (var mutex = new Mutex(true, @"Local\Lease116.Launcher", out first))
            {
                if (!first)
                {
                    // Lease116.exe is already running (starting or started the server): just show the app
                    if (env.WaitHealthy(90000)) env.OpenBrowser();
                    else Msg.Info("Lease116 is still starting. The browser will open as soon as it is ready.");
                    return 0;
                }
                if (env.ExeInAppDir)
                {
                    try { Shortcuts.Update(env); } catch { /* shortcuts are a convenience only */ }
                }
                var ctx = new TrayContext(env);
                if (ctx.Result >= 0) return ctx.Result;
                Application.Run(ctx);
                GC.KeepAlive(mutex);
                return 0;
            }
        }
    }

    sealed class LaunchEnv
    {
        public readonly string Exe, ExeDir, AppDir, Base, Python, LogDir, LogFile, TokenFile, Url, HealthUrl;
        public readonly int Port;

        public LaunchEnv()
        {
            Exe = Application.ExecutablePath;
            ExeDir = Path.GetDirectoryName(Exe);
            Base = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Lease116");
            // normally Lease116.exe sits in the program folder; a copy kept elsewhere (Desktop, Downloads) finds the
            // installed program folder from the record written by Setup
            AppDir = HasApp(ExeDir) ? ExeDir : (InstalledAppDir() ?? ExeDir);
            Python = Path.Combine(Base, @"venv\Scripts\python.exe");
            LogDir = Path.Combine(Base, "logs");
            LogFile = Path.Combine(LogDir, "server.log");
            TokenFile = Path.Combine(Base, "launcher.token");
            int p;
            Port = int.TryParse(Environment.GetEnvironmentVariable("LEASE116_PORT"), out p) && p > 0 && p < 65536 ? p : 8116;
            Url = "http://127.0.0.1:" + Port + "/";
            HealthUrl = Url + "api/health";
        }

        public bool AppPresent { get { return HasApp(AppDir); } }
        public bool ExeInAppDir { get { return AppPresent && string.Equals(ExeDir, AppDir, StringComparison.OrdinalIgnoreCase); } }

        static bool HasApp(string dir)
        {
            try { return !string.IsNullOrEmpty(dir) && File.Exists(Path.Combine(dir, @"app\__main__.py")); } catch { return false; }
        }

        string InstalledAppDir()
        {
            try
            {
                string f = Path.Combine(Base, "install.json");
                if (!File.Exists(f)) return null;
                var m = Regex.Match(File.ReadAllText(f), "\"app_dir\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"");
                if (!m.Success) return null;
                string dir = Regex.Unescape(m.Groups[1].Value);
                return HasApp(dir) ? dir : null;
            }
            catch { return null; }
        }
        public bool IsInstalled { get { return File.Exists(Python); } }

        public bool Healthy()
        {
            try
            {
                var req = (HttpWebRequest)WebRequest.Create(HealthUrl);
                req.Proxy = null;                       // never route the local app through a proxy / VPN
                req.Timeout = 1500;
                req.ReadWriteTimeout = 1500;
                using (var resp = (HttpWebResponse)req.GetResponse())
                using (var sr = new StreamReader(resp.GetResponseStream()))
                    return resp.StatusCode == HttpStatusCode.OK && sr.ReadToEnd().Contains("\"ok\"");
            }
            catch { return false; }
        }

        public bool WaitHealthy(int ms)
        {
            var sw = Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < ms)
            {
                if (Healthy()) return true;
                Thread.Sleep(500);
            }
            return false;
        }

        public bool PortInUse()
        {
            try
            {
                using (var c = new TcpClient())
                {
                    var ar = c.BeginConnect("127.0.0.1", Port, null, null);
                    if (!ar.AsyncWaitHandle.WaitOne(800)) return false;
                    c.EndConnect(ar);
                    return true;
                }
            }
            catch { return false; }
        }

        public void OpenBrowser()
        {
            try { Process.Start(new ProcessStartInfo(Url) { UseShellExecute = true }); }
            catch (Exception ex)
            {
                Msg.Error("Lease116 is running, but the browser could not be opened automatically.\n\n" +
                          "Open this address in your browser:\n" + Url + "\n\n(" + ex.Message + ")");
            }
        }

        public string ReadToken()
        {
            try { return File.Exists(TokenFile) ? File.ReadAllText(TokenFile).Trim() : null; }
            catch { return null; }
        }

        public bool RequestShutdown(string token)
        {
            if (string.IsNullOrEmpty(token)) return false;
            try
            {
                var req = (HttpWebRequest)WebRequest.Create(Url + "api/system/shutdown");
                req.Method = "POST";
                req.Proxy = null;
                req.Timeout = 4000;
                req.ContentLength = 0;
                req.Headers["X-Lease116-Token"] = token;
                using (var resp = (HttpWebResponse)req.GetResponse())
                    return resp.StatusCode == HttpStatusCode.OK;
            }
            catch { return false; }
        }
    }

    sealed class TrayContext : ApplicationContext
    {
        readonly LaunchEnv env;
        readonly object logLock = new object();
        NotifyIcon icon;
        Process proc;                  // the server this launcher started (null when an earlier launch left it running)
        string token;
        StreamWriter log;
        System.Windows.Forms.Timer timer;
        Stopwatch starting;
        bool ready, stopping;

        /// <summary>-1 = keep running in the notification area; 0/1 = finished (exit code).</summary>
        public int Result = -1;

        public TrayContext(LaunchEnv e)
        {
            env = e;
            if (!env.AppPresent)
            {
                Msg.Error("The Lease116 program folder was not found.\n\nKeep Lease116.exe inside the 'Ind AS 116 Lease App' folder, " +
                          "or run Setup.bat from that folder once so that Lease116.exe can find it.");
                Result = 1;
                return;
            }
            if (env.Healthy())
            {
                env.OpenBrowser();
                token = env.ReadToken();       // started by an earlier Lease116.exe? then it can still be stopped here
                if (token == null) { Result = 0; return; }
                CreateIcon("Lease116 - running");
                ready = true;
                StartTimer(5000);
                return;
            }
            if (!env.IsInstalled)
            {
                if (Msg.YesNo("Lease116 is not set up on this PC yet.\n\nRun Setup now? (one time, 5-15 minutes, internet needed)"))
                {
                    try { Process.Start(new ProcessStartInfo(Path.Combine(env.AppDir, "Setup.bat")) { UseShellExecute = true, WorkingDirectory = env.AppDir }); }
                    catch (Exception ex) { Msg.Error("Setup could not be started: " + ex.Message); }
                }
                Result = 0;
                return;
            }
            if (env.PortInUse())
            {
                Msg.Error("Port " + env.Port + " is being used by another program, so Lease116 cannot start.\n\n" +
                          "Close that program (or restart the PC) and open Lease116 again.");
                Result = 1;
                return;
            }
            if (!StartServer()) { Result = 1; return; }
            CreateIcon("Lease116 - starting...");
            icon.ShowBalloonTip(4000, "Lease116", "Starting... the browser will open in a few seconds.", ToolTipIcon.Info);
            starting = Stopwatch.StartNew();
            StartTimer(700);
        }

        bool StartServer()
        {
            try
            {
                Directory.CreateDirectory(env.LogDir);
                try { if (File.Exists(env.LogFile)) File.Copy(env.LogFile, Path.Combine(env.LogDir, "server.previous.log"), true); }
                catch { }
                log = new StreamWriter(new FileStream(env.LogFile, FileMode.Create, FileAccess.Write, FileShare.ReadWrite), new UTF8Encoding(false));
                log.AutoFlush = true;
                Log("[launcher] Lease116.exe " + Assembly.GetExecutingAssembly().GetName().Version + " - starting the server in " + env.AppDir);
                token = NewToken();
                var psi = new ProcessStartInfo(env.Python, "-m app --no-browser")
                {
                    WorkingDirectory = env.AppDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };
                psi.EnvironmentVariables["LEASE116_LAUNCHER_TOKEN"] = token;
                psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1";
                psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                proc = new Process { StartInfo = psi };
                proc.OutputDataReceived += (s, a) => { if (a.Data != null) Log(a.Data); };
                proc.ErrorDataReceived += (s, a) => { if (a.Data != null) Log(a.Data); };
                proc.Start();
                proc.BeginOutputReadLine();
                proc.BeginErrorReadLine();
                try { File.WriteAllText(env.TokenFile, token); } catch { }
                return true;
            }
            catch (Exception ex)
            {
                Msg.Error("Lease116 could not be started.\n\n" + ex.Message + "\n\nYou can also start it with Start.bat in:\n" + env.AppDir);
                return false;
            }
        }

        void CreateIcon(string text)
        {
            var menu = new ContextMenuStrip();
            var open = new ToolStripMenuItem("Open Lease116", null, (s, a) => env.OpenBrowser());
            open.Font = new Font(open.Font, FontStyle.Bold);
            menu.Items.Add(open);
            menu.Items.Add(new ToolStripMenuItem("Show log file", null, (s, a) => ShowLog()));
            menu.Items.Add(new ToolStripSeparator());
            menu.Items.Add(new ToolStripMenuItem("Stop Lease116", null, (s, a) => Stop()));
            icon = new NotifyIcon { Icon = TrayIcon(), Text = text, ContextMenuStrip = menu, Visible = true };
            icon.DoubleClick += (s, a) => env.OpenBrowser();
            icon.BalloonTipClicked += (s, a) => { if (ready) env.OpenBrowser(); };
        }

        static Icon TrayIcon()
        {
            try
            {
                using (var st = Assembly.GetExecutingAssembly().GetManifestResourceStream("Lease116.tray.ico"))
                    if (st != null) return new Icon(st, SystemInformation.SmallIconSize);
            }
            catch { }
            try { return Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }
            return SystemIcons.Application;
        }

        void StartTimer(int ms)
        {
            timer = new System.Windows.Forms.Timer { Interval = ms };
            timer.Tick += Tick;
            timer.Start();
        }

        void Tick(object sender, EventArgs e)
        {
            if (stopping) return;
            if (proc != null && proc.HasExited)
            {
                timer.Stop();
                Thread.Sleep(400);             // let the last lines of server output reach the log
                string msg = ready
                    ? "Lease116 has stopped unexpectedly."
                    : "Lease116 could not start (exit code " + ExitCode() + ").";
                Finish();
                Msg.Error(msg + "\n\nLast lines of the log:\n\n" + Tail(20) + "\n\nFull log: " + env.LogFile);
                return;
            }
            if (!ready)
            {
                if (env.Healthy())
                {
                    ready = true;
                    timer.Interval = 5000;
                    icon.Text = "Lease116 - running";
                    Log("[launcher] server ready at " + env.Url + " after " + starting.Elapsed.TotalSeconds.ToString("0.0") + " s");
                    env.OpenBrowser();
                    icon.ShowBalloonTip(6000, "Lease116 is running",
                        "Use it in your browser. To close Lease116, right-click this icon and choose Stop Lease116.", ToolTipIcon.Info);
                }
                else if (starting.Elapsed.TotalSeconds > 180)
                {
                    timer.Stop();
                    string tail = Tail(20);
                    Stop();
                    Msg.Error("Lease116 did not start within 3 minutes.\n\nLast lines of the log:\n\n" + tail + "\n\nFull log: " + env.LogFile);
                }
            }
            else if (proc == null && !env.Healthy())
            {
                Finish();          // a server started by an earlier launch has been stopped elsewhere
            }
        }

        void Stop()
        {
            if (stopping) return;
            stopping = true;
            if (timer != null) timer.Stop();
            if (icon != null) icon.Text = "Lease116 - stopping...";
            bool accepted = env.RequestShutdown(token);
            if (proc != null)
            {
                try
                {
                    if (!proc.WaitForExit(accepted ? 15000 : 200)) { KillTree(proc); proc.WaitForExit(5000); }
                }
                catch { }
                Log("[launcher] server stopped");
            }
            else if (accepted)
            {
                var sw = Stopwatch.StartNew();
                while (sw.ElapsedMilliseconds < 15000 && env.Healthy()) Thread.Sleep(300);
            }
            else
            {
                Msg.Info("This Lease116 session was started from Start.bat. Close its black window to stop it.");
            }
            Finish();
        }

        void Finish()
        {
            if (timer != null) timer.Stop();
            if (icon != null) { icon.Visible = false; icon.Dispose(); icon = null; }
            if (proc == null || proc.HasExited)
            {
                try { if (token != null && token == env.ReadToken()) File.Delete(env.TokenFile); } catch { }
            }
            lock (logLock) { if (log != null) { log.Dispose(); log = null; } }
            ExitThread();
        }

        void ShowLog()
        {
            try { Process.Start(new ProcessStartInfo("notepad.exe", "\"" + env.LogFile + "\"") { UseShellExecute = true }); }
            catch (Exception ex) { Msg.Error("The log could not be opened: " + ex.Message + "\n\n" + env.LogFile); }
        }

        void Log(string line)
        {
            lock (logLock)
            {
                if (log == null) return;
                try { log.WriteLine(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "  " + line); } catch { }
            }
        }

        string Tail(int n)
        {
            try
            {
                string[] all;
                using (var fs = new FileStream(env.LogFile, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
                using (var sr = new StreamReader(fs, Encoding.UTF8))
                    all = sr.ReadToEnd().Replace("\r", "").Split('\n');
                int start = Math.Max(0, all.Length - n);
                var sb = new StringBuilder();
                for (int i = start; i < all.Length; i++) if (all[i].Trim().Length > 0) sb.AppendLine(all[i]);
                string s = sb.ToString().Trim();
                return s.Length > 0 ? s : "(the log is empty)";
            }
            catch { return "(the log could not be read)"; }
        }

        static void KillTree(Process p)
        {
            // venv\Scripts\python.exe is a small redirector that runs the real interpreter as a child process,
            // so a forced stop must end the whole process tree (the normal stop is the clean shutdown request)
            try
            {
                var k = Process.Start(new ProcessStartInfo("taskkill.exe", "/PID " + p.Id + " /T /F") { UseShellExecute = false, CreateNoWindow = true });
                if (k != null) k.WaitForExit(8000);
            }
            catch { }
            try { if (!p.HasExited) p.Kill(); } catch { }
        }

        int ExitCode()
        {
            try { return proc.ExitCode; } catch { return -1; }
        }

        static string NewToken()
        {
            var b = new byte[24];
            using (var rng = new RNGCryptoServiceProvider()) rng.GetBytes(b);
            var sb = new StringBuilder();
            foreach (var x in b) sb.Append(x.ToString("x2"));
            return sb.ToString();
        }
    }

    static class Shortcuts
    {
        /// <summary>Point the Desktop / Start-menu "Lease116" shortcuts at this launcher (created by Setup for Start.bat).
        /// Shortcuts are created only on the launcher's first run, so a shortcut the user deleted later stays deleted.</summary>
        public static void Update(LaunchEnv env)
        {
            Type t = Type.GetTypeFromProgID("WScript.Shell");
            if (t == null) return;
            string marker = Path.Combine(env.Base, "launcher.shortcuts");
            bool firstRun = !File.Exists(marker);
            object shell = Activator.CreateInstance(t);
            try
            {
                foreach (var folder in new[] { Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                                               Environment.GetFolderPath(Environment.SpecialFolder.Programs) })
                {
                    if (string.IsNullOrEmpty(folder) || !Directory.Exists(folder)) continue;
                    string path = Path.Combine(folder, "Lease116.lnk");
                    bool exists = File.Exists(path);
                    if (!exists && !firstRun) continue;
                    object lnk = t.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { path });
                    try
                    {
                        Type lt = lnk.GetType();
                        string target = (lt.InvokeMember("TargetPath", BindingFlags.GetProperty, null, lnk, null) as string) ?? "";
                        if (exists)
                        {
                            string name = Path.GetFileName(target);
                            bool ours = name.Equals("Start.bat", StringComparison.OrdinalIgnoreCase) ||
                                        name.Equals("Lease116.exe", StringComparison.OrdinalIgnoreCase);
                            if (!ours || target.Equals(env.Exe, StringComparison.OrdinalIgnoreCase)) continue;
                        }
                        lt.InvokeMember("TargetPath", BindingFlags.SetProperty, null, lnk, new object[] { env.Exe });
                        lt.InvokeMember("Arguments", BindingFlags.SetProperty, null, lnk, new object[] { "" });
                        lt.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, lnk, new object[] { env.AppDir });
                        lt.InvokeMember("IconLocation", BindingFlags.SetProperty, null, lnk, new object[] { env.Exe + ",0" });
                        lt.InvokeMember("Description", BindingFlags.SetProperty, null, lnk,
                                        new object[] { "Lease116 - Ind AS 116 / IFRS 16 lease accounting" });
                        lt.InvokeMember("Save", BindingFlags.InvokeMethod, null, lnk, null);
                    }
                    finally { Marshal.ReleaseComObject(lnk); }
                }
            }
            finally
            {
                Marshal.ReleaseComObject(shell);
                try { Directory.CreateDirectory(env.Base); File.WriteAllText(marker, DateTime.Now.ToString("s")); } catch { }
            }
        }
    }

    static class Msg
    {
        // Win32 MessageBox so that messages from this window-less app always come to the front (MB_TOPMOST | MB_SETFOREGROUND)
        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern int MessageBoxW(IntPtr hWnd, string text, string caption, uint type);

        const uint Front = 0x40000 | 0x10000;
        public static void Info(string text) { MessageBoxW(IntPtr.Zero, text, "Lease116", 0x40 | Front); }
        public static void Error(string text) { MessageBoxW(IntPtr.Zero, text, "Lease116", 0x30 | Front); }
        public static bool YesNo(string text) { return MessageBoxW(IntPtr.Zero, text, "Lease116", 0x04 | 0x20 | Front) == 6; }
    }
}
