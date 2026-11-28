using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Runtime.InteropServices;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Finds the port Tally is listening on, whatever it was set to — nobody has to know it is 9000.
/// 1. Ports opened by a running Tally program (tally.exe / TallyPrime), read from Windows' own connection table.
/// 2. The usual Tally ports (9000 …).
/// 3. Any other port listening on this PC in the 9000–9999 range.
/// Every candidate is then asked for its company list; only a real Tally answers that.
/// </summary>
public static class TallyPortFinder
{
    public static readonly int[] UsualPorts = [9000, 9001, 9002, 9003, 9004, 9005, 9009, 9999];

    /// <summary>Order: Tally's own ports, the usual ports, then other listening ports in 9000–9999. No duplicates.</summary>
    public static List<int> CandidatePorts(IEnumerable<int> tallyOwnedPorts, IEnumerable<int> listeningPorts)
    {
        var list = new List<int>();
        foreach (var p in tallyOwnedPorts.Concat(UsualPorts).Concat(listeningPorts.Where(p => p is >= 9000 and <= 9999).OrderBy(p => p)))
            if (p is > 0 and <= 65535 && !list.Contains(p)) list.Add(p);
        return list;
    }

    public static List<int> FindCandidatePorts()
    {
        List<int> owned = [], listening = [];
        try { owned = TallyOwnedPorts(); } catch { /* not Windows / no permission: fall back to the usual ports */ }
        try
        {
            listening = IPGlobalProperties.GetIPGlobalProperties().GetActiveTcpListeners()
                .Where(ep => IPAddress.IsLoopback(ep.Address) || ep.Address.Equals(IPAddress.Any) || ep.Address.Equals(IPAddress.IPv6Any))
                .Select(ep => ep.Port).Distinct().ToList();
        }
        catch { }
        return CandidatePorts(owned, listening);
    }

    /// <summary>Is a Tally program running on this PC? (Used to explain what to switch on when it does not answer.)</summary>
    public static bool IsTallyRunning()
    {
        try { return Process.GetProcesses().Any(p => IsTallyProcess(SafeName(p))); }
        catch { return false; }
    }

    private static bool IsTallyProcess(string name) => name.StartsWith("tally", StringComparison.OrdinalIgnoreCase);

    private static string SafeName(Process p)
    {
        try { return p.ProcessName; } catch { return ""; }
    }

    // ------------------------------------------------------------------ Windows TCP table with owning process
    private const int AF_INET = 2;
    private const int TCP_TABLE_OWNER_PID_LISTENER = 3;

    [DllImport("iphlpapi.dll", SetLastError = true)]
    private static extern uint GetExtendedTcpTable(IntPtr pTcpTable, ref int dwOutBufLen, bool sort, int ipVersion, int tblClass, uint reserved);

    [StructLayout(LayoutKind.Sequential)]
    private struct MibTcpRowOwnerPid
    {
        public uint state, localAddr;
        public byte localPort1, localPort2, localPort3, localPort4;
        public uint remoteAddr;
        public byte remotePort1, remotePort2, remotePort3, remotePort4;
        public uint owningPid;
    }

    private static List<int> TallyOwnedPorts()
    {
        var result = new List<int>();
        if (!OperatingSystem.IsWindows()) return result;
        var tallyPids = new HashSet<int>();
        foreach (var p in Process.GetProcesses())
        {
            try { if (IsTallyProcess(p.ProcessName)) tallyPids.Add(p.Id); } catch { }
            finally { p.Dispose(); }
        }
        if (tallyPids.Count == 0) return result;

        int size = 0;
        GetExtendedTcpTable(IntPtr.Zero, ref size, false, AF_INET, TCP_TABLE_OWNER_PID_LISTENER, 0);
        if (size <= 0) return result;
        var buf = Marshal.AllocHGlobal(size);
        try
        {
            if (GetExtendedTcpTable(buf, ref size, false, AF_INET, TCP_TABLE_OWNER_PID_LISTENER, 0) != 0) return result;
            int count = Marshal.ReadInt32(buf);
            var rowPtr = buf + 4;
            int rowSize = Marshal.SizeOf<MibTcpRowOwnerPid>();
            for (int i = 0; i < count; i++, rowPtr += rowSize)
            {
                var row = Marshal.PtrToStructure<MibTcpRowOwnerPid>(rowPtr);
                if (!tallyPids.Contains((int)row.owningPid)) continue;
                int port = (row.localPort1 << 8) | row.localPort2;   // network byte order
                if (!result.Contains(port)) result.Add(port);
            }
        }
        finally { Marshal.FreeHGlobal(buf); }
        return result;
    }
}
