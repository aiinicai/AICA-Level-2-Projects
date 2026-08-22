using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Diagnostics;
using System.Windows.Forms;
using System.Drawing;
using System.Reflection;
using System.Collections.Generic;

namespace LovableCRM
{
    static class Program
    {
        private static HttpListener listener;
        private static int port;
        private static NotifyIcon trayIcon;
        private static ContextMenuStrip trayMenu;
        private static Dictionary<string, byte[]> embeddedFiles = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Load embedded resources
            LoadEmbeddedResources();

            // Find free port
            port = GetFreePort();

            // Start HTTP Server
            StartServer(port);

            // Open default browser
            string url = "http://localhost:" + port + "/";
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });

            // Create Tray Icon
            trayMenu = new ContextMenuStrip();
            trayMenu.Items.Add("Open Lovable CRM", null, (s, e) => {
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
            });
            trayMenu.Items.Add(new ToolStripSeparator());
            trayMenu.Items.Add("Exit Lovable CRM", null, (s, e) => {
                StopServer();
                if (trayIcon != null) {
                    trayIcon.Visible = false;
                    trayIcon.Dispose();
                }
                Application.Exit();
            });

            trayIcon = new NotifyIcon
            {
                Text = "Lovable CRM (Port " + port + ")",
                Icon = SystemIcons.Application,
                ContextMenuStrip = trayMenu,
                Visible = true
            };

            trayIcon.ShowBalloonTip(2000, "Lovable CRM", "App is running at " + url + "\nRight-click tray icon to exit.", ToolTipIcon.Info);

            Application.Run();
        }

        private static int GetFreePort()
        {
            TcpListener l = new TcpListener(IPAddress.Loopback, 0);
            l.Start();
            int p = ((IPEndPoint)l.LocalEndpoint).Port;
            l.Stop();
            return p;
        }

        private static void LoadEmbeddedResources()
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            foreach (string name in asm.GetManifestResourceNames())
            {
                using (Stream stream = asm.GetManifestResourceStream(name))
                {
                    if (stream != null)
                    {
                        byte[] buffer = new byte[stream.Length];
                        int totalRead = 0;
                        while (totalRead < buffer.Length)
                        {
                            int read = stream.Read(buffer, totalRead, buffer.Length - totalRead);
                            if (read == 0) break;
                            totalRead += read;
                        }
                        embeddedFiles[name] = buffer;
                    }
                }
            }
        }

        private static void StartServer(int p)
        {
            listener = new HttpListener();
            listener.Prefixes.Add("http://localhost:" + p + "/");
            listener.Prefixes.Add("http://127.0.0.1:" + p + "/");
            listener.Start();

            ThreadPool.QueueUserWorkItem((o) =>
            {
                while (listener != null && listener.IsListening)
                {
                    try
                    {
                        HttpListenerContext ctx = listener.GetContext();
                        ThreadPool.QueueUserWorkItem((c) => ProcessRequest((HttpListenerContext)c), ctx);
                    }
                    catch { }
                }
            });
        }

        private static void StopServer()
        {
            try
            {
                if (listener != null)
                {
                    listener.Stop();
                    listener.Close();
                    listener = null;
                }
            }
            catch { }
        }

        private static void ProcessRequest(HttpListenerContext ctx)
        {
            try
            {
                string rawPath = ctx.Request.Url.AbsolutePath.TrimStart('/');
                if (string.IsNullOrEmpty(rawPath))
                {
                    rawPath = "index.html";
                }

                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                string localDistPath = Path.Combine(baseDir, "dist", rawPath.Replace('/', Path.DirectorySeparatorChar));
                string localDirectPath = Path.Combine(baseDir, rawPath.Replace('/', Path.DirectorySeparatorChar));

                byte[] data = null;
                string mime = GetMimeType(rawPath);

                if (File.Exists(localDistPath))
                {
                    data = File.ReadAllBytes(localDistPath);
                }
                else if (File.Exists(localDirectPath))
                {
                    data = File.ReadAllBytes(localDirectPath);
                }
                else
                {
                    string resKey = rawPath.Replace('/', '_').Replace('\\', '_');
                    foreach (var kvp in embeddedFiles)
                    {
                        if (kvp.Key.EndsWith(resKey, StringComparison.OrdinalIgnoreCase) ||
                            kvp.Key.EndsWith("." + resKey, StringComparison.OrdinalIgnoreCase))
                        {
                            data = kvp.Value;
                            break;
                        }
                    }

                    // Fallback to index.html for SPA client-side routing
                    if (data == null)
                    {
                        string indexDist = Path.Combine(baseDir, "dist", "index.html");
                        if (File.Exists(indexDist))
                        {
                            data = File.ReadAllBytes(indexDist);
                            mime = "text/html; charset=utf-8";
                        }
                        else
                        {
                            foreach (var kvp in embeddedFiles)
                            {
                                if (kvp.Key.EndsWith("index.html", StringComparison.OrdinalIgnoreCase))
                                {
                                    data = kvp.Value;
                                    mime = "text/html; charset=utf-8";
                                    break;
                                }
                            }
                        }
                    }
                }

                if (data != null)
                {
                    ctx.Response.ContentType = mime;
                    ctx.Response.ContentLength64 = data.Length;
                    ctx.Response.StatusCode = 200;
                    ctx.Response.OutputStream.Write(data, 0, data.Length);
                }
                else
                {
                    ctx.Response.StatusCode = 404;
                    byte[] notFound = Encoding.UTF8.GetBytes("Not Found");
                    ctx.Response.OutputStream.Write(notFound, 0, notFound.Length);
                }
            }
            catch { }
            finally
            {
                try
                {
                    ctx.Response.OutputStream.Close();
                }
                catch { }
            }
        }

        private static string GetMimeType(string path)
        {
            string ext = Path.GetExtension(path).ToLowerInvariant();
            switch (ext)
            {
                case ".html": return "text/html; charset=utf-8";
                case ".js": return "application/javascript; charset=utf-8";
                case ".css": return "text/css; charset=utf-8";
                case ".svg": return "image/svg+xml";
                case ".json": return "application/json";
                case ".png": return "image/png";
                case ".jpg":
                case ".jpeg": return "image/jpeg";
                case ".ico": return "image/x-icon";
                case ".woff": return "font/woff";
                case ".woff2": return "font/woff2";
                case ".ttf": return "font/ttf";
                default: return "application/octet-stream";
            }
        }
    }
}
