using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Net.Http;
using System.Security;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

public class TallyConnector
{
    public static readonly string[] StandardGroups =
    [
        "Indirect Expenses", "Direct Expenses", "Indirect Incomes", "Direct Incomes",
        "Sundry Creditors", "Sundry Debtors", "Bank Accounts", "Bank OD A/c", "Cash-in-Hand",
        "Duties & Taxes", "Sales Accounts", "Purchase Accounts", "Current Assets",
        "Current Liabilities", "Fixed Assets", "Investments", "Loans (Liability)",
        "Loans & Advances (Asset)", "Capital Account", "Suspense A/c"
    ];

    private static readonly HttpClient SharedHttp = new(new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(2),
        MaxConnectionsPerServer = 16
    })
    { Timeout = Timeout.InfiniteTimeSpan };

    private static readonly Regex XmlCtrlDecRe = new(@"&#(?:[0-8]|1[12]|1[4-9]|2\d|3[01]);", RegexOptions.Compiled);
    private static readonly Regex XmlCtrlHexRe = new(@"&#x(?:0?[0-8BbCcEeFf]|1[0-9A-Fa-f]);", RegexOptions.Compiled);
    private static readonly Regex XmlCtrlRawRe = new(@"[\x00-\x08\x0b\x0c\x0e-\x1f]", RegexOptions.Compiled);

    private readonly TimeSpan _timeout;
    public string Host { get; set; }
    public string CompanyName { get; set; }

    public TallyConnector(string host = "http://localhost:9000", string companyName = "", int timeoutSec = 8)
    {
        Host = host.TrimEnd('/');
        CompanyName = companyName.Trim();
        _timeout = TimeSpan.FromSeconds(timeoutSec);
    }

    private static string Esc(string? s) => SecurityElement.Escape(s ?? "") ?? "";

    public static string SanitizeXml(string raw)
    {
        var cleaned = XmlCtrlDecRe.Replace(raw, "");
        cleaned = XmlCtrlHexRe.Replace(cleaned, "");
        return XmlCtrlRawRe.Replace(cleaned, "");
    }

    /// <summary>Large exports (all vouchers of a period) and imports need far longer than a ping; Tally can take 30s+ on big companies.</summary>
    private static readonly TimeSpan LongTimeout = TimeSpan.FromSeconds(120);
    private static readonly TimeSpan PostTimeout = TimeSpan.FromSeconds(60);
    // Opening balance = ledger opening + every voucher of the bank from "Books beginning from" — can be years of data
    private static readonly TimeSpan BalanceTimeout = TimeSpan.FromSeconds(300);

    private static string Inv(decimal v) => v.ToString("F2", CultureInfo.InvariantCulture);

    private async Task<string> PostXmlAsync(string xml, TimeSpan? timeoutOverride = null)
    {
        var effective = timeoutOverride.HasValue && timeoutOverride.Value > _timeout ? timeoutOverride.Value : _timeout;
        using var cts = new CancellationTokenSource(effective);
        using var content = new StringContent(xml, Encoding.UTF8, "application/xml");
        using var resp = await SharedHttp.PostAsync(Host, content, cts.Token);
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadAsStringAsync(cts.Token);
    }

    public async Task<string> FetchActiveCompanyAsync()
    {
        const string req = """
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Function</TYPE><ID>$$CurrentCompany</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req)));
            return (doc.Descendants("RESULT").FirstOrDefault()?.Value ?? "").Trim();
        }
        catch { return ""; }
    }

    public async Task<(bool connected, string activeCompany, List<string> companies)> TestConnectionAsync()
    {
        const string req = """
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>List of Companies</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req)));
            var companies = doc.Descendants("COMPANY")
                .Select(c => (c.Attribute("NAME")?.Value ?? c.Element("NAME")?.Value ?? "").Trim())
                .Where(n => !string.IsNullOrEmpty(n)).Distinct().ToList();
            var active = await FetchActiveCompanyAsync();
            if (!string.IsNullOrEmpty(active))
                companies = new[] { active }.Concat(companies.Where(c => !c.Equals(active, StringComparison.OrdinalIgnoreCase))).ToList();
            return (true, string.IsNullOrEmpty(active) ? (companies.FirstOrDefault() ?? "") : active, companies);
        }
        catch { return (false, "", []); }
    }

    private static string NormalizeHost(string url) =>
        url.Trim().TrimEnd('/').Replace("127.0.0.1", "localhost", StringComparison.OrdinalIgnoreCase).ToLowerInvariant();

    public static async Task<List<TallyTarget>> DiscoverOpenTalliesAsync(string extraHost = "")
    {
        // every port Tally could be on: its own ports (read from Windows), the usual ones, other listening 9000–9999 ports
        var ports = await Task.Run(() => TallyPortFinder.FindCandidatePorts());
        var urls = ports.Select(p => $"http://localhost:{p}").ToList();
        if (!string.IsNullOrWhiteSpace(extraHost) && !urls.Contains(extraHost.TrimEnd('/'), StringComparer.OrdinalIgnoreCase))
            urls.Insert(0, extraHost.TrimEnd('/'));

        var tasks = urls.Select(async url =>
        {
            var conn = new TallyConnector(url, "", 1);
            var (ok, active, comps) = await conn.TestConnectionAsync();
            if (!ok) return new List<TallyTarget>();
            if (comps.Count == 0) return [new TallyTarget { Host = url, CompanyName = "", IsActive = true }];
            return comps.Select((c, i) => new TallyTarget
            {
                Host = url,
                CompanyName = c,
                IsActive = !string.IsNullOrEmpty(active) ? c.Equals(active, StringComparison.OrdinalIgnoreCase) : i == 0
            }).ToList();
        });

        var all = await Task.WhenAll(tasks);
        // the same Tally can answer on "localhost:9000" typed in the box and on the scanned port: list it once
        return all.SelectMany(x => x)
            .GroupBy(t => (NormalizeHost(t.Host), t.CompanyName.ToUpperInvariant()))
            .Select(g => g.First()).ToList();
    }

    public async Task<(List<string> all, List<string> banks, List<string> cash, Dictionary<string, TallyBankDetail> bankDetails, HashSet<string> partyLedgers, List<PartyBankInfo> partyBankInfo)> FetchLedgersAsync()
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var req = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>AllLedgers</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE><COLLECTION NAME="AllLedgers"><TYPE>Ledger</TYPE><FETCH>NAME, PARENT, BANKDETAILS, IFSCODE, BANKINGCONFIGBANK, BANKACCHOLDERNAME, PAYMENTDETAILS.LIST</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        var groupParentsTask = FetchGroupParentsAsync();
        var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req, LongTimeout)));
        var groupParents = await groupParentsTask;
        var all = new List<string>();
        var seenAll = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var banks = new List<string>();
        var cash = new List<string>();
        var details = new Dictionary<string, TallyBankDetail>(StringComparer.OrdinalIgnoreCase);
        var partyLedgers = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var partyInfo = new List<PartyBankInfo>();

        foreach (var el in doc.Descendants("LEDGER"))
        {
            var name = (el.Attribute("NAME")?.Value ?? el.Element("NAME")?.Value ?? el.Descendants("NAME").FirstOrDefault()?.Value ?? "").Trim();
            if (string.IsNullOrEmpty(name)) continue;
            var parentRaw = (el.Element("PARENT")?.Value ?? "").Trim();
            if (seenAll.Add(name)) all.Add(name);
            var kind = ClassifyLedgerGroup(parentRaw, groupParents);
            if (kind == LedgerKind.Bank)
            {
                if (!banks.Contains(name, StringComparer.OrdinalIgnoreCase)) banks.Add(name);
                var acc = (el.Element("BANKDETAILS")?.Value ?? el.Element("ACCOUNTNUMBER")?.Value ?? "").Trim();
                var ifsc = (el.Element("IFSCODE")?.Value ?? el.Element("IFSC")?.Value ?? "").Trim().ToUpperInvariant();
                var digits = Regex.Replace(acc, @"\D", "");
                // Many Indian Tally ledgers put the account last digits in the ledger name itself (e.g. "AU Bank 1592", "HDFC CA-8842")
                if (digits.Length < 4)
                {
                    var nameDigits = Regex.Matches(name, @"\d{4,}").Select(m => m.Value).LastOrDefault();
                    if (!string.IsNullOrEmpty(nameDigits))
                    {
                        acc = nameDigits;
                        digits = nameDigits;
                    }
                }
                if (string.IsNullOrEmpty(ifsc))
                {
                    var nameIfsc = Regex.Match(name, @"\b[A-Za-z]{4}0[A-Za-z0-9]{6}\b");
                    if (nameIfsc.Success) ifsc = nameIfsc.Value.ToUpperInvariant();
                }
                details[name] = new TallyBankDetail
                {
                    TallyLedgerName = name,
                    BankName = (el.Element("BANKINGCONFIGBANK")?.Value ?? "").Trim(),
                    AccountNumber = digits.Length >= 4 ? digits[^4..] : acc,
                    AccountLast4 = digits.Length >= 4 ? digits[^4..] : acc,
                    Ifsc = ifsc
                };
            }
            else if (kind == LedgerKind.Cash && !cash.Contains(name, StringComparer.OrdinalIgnoreCase))
                cash.Add(name);
            if (kind == LedgerKind.Party && partyLedgers.Add(name))
                partyInfo.Add(ReadPartyBankInfo(name, el));
        }
        all.Sort(StringComparer.OrdinalIgnoreCase);
        banks.Sort(StringComparer.OrdinalIgnoreCase);
        cash.Sort(StringComparer.OrdinalIgnoreCase);
        return (all, banks, cash, details, partyLedgers, partyInfo);
    }

    /// <summary>
    /// A party ledger's bank details: TallyPrime keeps them in PAYMENTDETAILS.LIST (account number, IFSC, favouring name);
    /// older releases on the ledger itself (BANKDETAILS / IFSCODE / BANKACCHOLDERNAME).
    /// </summary>
    public static PartyBankInfo ReadPartyBankInfo(string name, XElement el)
    {
        var info = new PartyBankInfo { Ledger = name };
        void AddAcc(string? v)
        {
            var d = Regex.Replace(v ?? "", @"\D", "");
            if (d.Length >= 6 && !info.AccountNumbers.Contains(d)) info.AccountNumbers.Add(d);
        }
        void AddIfsc(string? v)
        {
            var i = (v ?? "").Trim().ToUpperInvariant();
            if (Regex.IsMatch(i, "^[A-Z]{4}0[A-Z0-9]{6}$") && !info.Ifscs.Contains(i)) info.Ifscs.Add(i);
        }
        AddAcc(el.Element("BANKDETAILS")?.Value);
        AddIfsc(el.Element("IFSCODE")?.Value);
        info.Favouring = (el.Element("BANKACCHOLDERNAME")?.Value ?? "").Trim();
        foreach (var pd in el.Descendants("PAYMENTDETAILS.LIST"))
        {
            AddAcc(pd.Element("ACCOUNTNUMBER")?.Value);
            AddIfsc(pd.Element("IFSCODE")?.Value);
            var fav = (pd.Element("PAYMENTFAVOURING")?.Value ?? "").Trim();
            if (info.Favouring.Length == 0 && fav.Length > 0) info.Favouring = fav;
        }
        return info;
    }

    public enum LedgerKind { Other, Bank, Cash, Party }

    private static readonly HashSet<string> BankPrimaryGroups = new(StringComparer.OrdinalIgnoreCase) { "Bank Accounts", "Bank OD A/c", "Bank OCC A/c" };
    private static readonly HashSet<string> PartyPrimaryGroups = new(StringComparer.OrdinalIgnoreCase) { "Sundry Debtors", "Sundry Creditors" };

    /// <summary>
    /// Classifies a ledger by walking its group up to the Tally primary group. The old "parent name contains 'bank'" test
    /// treated ledgers under groups like "Bank Charges" / "Bank Interest" as BANK accounts, and missed party ledgers placed
    /// in sub-groups such as "Debtors - Delhi" (so their open bills were never offered).
    /// </summary>
    public static LedgerKind ClassifyLedgerGroup(string parentGroup, IReadOnlyDictionary<string, string> groupParents)
    {
        var g = (parentGroup ?? "").Trim();
        if (groupParents.Count > 0)
        {
            for (int depth = 0; depth < 25 && !string.IsNullOrEmpty(g); depth++)
            {
                if (BankPrimaryGroups.Contains(g)) return LedgerKind.Bank;
                if (g.Equals("Cash-in-Hand", StringComparison.OrdinalIgnoreCase) || g.Equals("Cash-in-hand", StringComparison.OrdinalIgnoreCase)) return LedgerKind.Cash;
                if (PartyPrimaryGroups.Contains(g)) return LedgerKind.Party;
                if (!groupParents.TryGetValue(g, out var up)) break;
                up = (up ?? "").Trim();
                if (up.Length == 0 || up.Equals("Primary", StringComparison.OrdinalIgnoreCase) || up.Equals(g, StringComparison.OrdinalIgnoreCase)) break;
                g = up;
            }
            if (BankPrimaryGroups.Contains(g)) return LedgerKind.Bank;
            if (PartyPrimaryGroups.Contains(g)) return LedgerKind.Party;
            if (g.Equals("Cash-in-Hand", StringComparison.OrdinalIgnoreCase)) return LedgerKind.Cash;
            if (groupParents.ContainsKey((parentGroup ?? "").Trim())) return LedgerKind.Other;
        }
        // Fallback when the group tree is unavailable: keyword test, excluding expense/income groups that merely mention "bank"
        var low = (parentGroup ?? "").ToLowerInvariant();
        if (low.Contains("bank") && !low.Contains("charge") && !low.Contains("interest") && !low.Contains("commission") && !low.Contains("loan"))
            return LedgerKind.Bank;
        if (low.Contains("cash")) return LedgerKind.Cash;
        if (low.Contains("debtor") || low.Contains("creditor")) return LedgerKind.Party;
        return LedgerKind.Other;
    }

    private async Task<Dictionary<string, string>> FetchGroupParentsAsync()
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var req = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>ABSEGroupTree</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE><COLLECTION NAME="ABSEGroupTree"><TYPE>Group</TYPE><FETCH>NAME, PARENT</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req, LongTimeout)));
            foreach (var g in doc.Descendants("GROUP"))
            {
                var name = (g.Attribute("NAME")?.Value ?? g.Element("NAME")?.Value ?? "").Trim();
                if (name.Length == 0) continue;
                result[name] = (g.Element("PARENT")?.Value ?? "").Trim();
            }
        }
        catch { /* fall back to keyword classification */ }
        return result;
    }

    public async Task<List<BillAllocation>> FetchPendingBillDetailsAsync(string partyLedger)
    {
        var results = new List<BillAllocation>();
        if (string.IsNullOrWhiteSpace(partyLedger)) return results;
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var escParty = Esc(partyLedger.Trim());
        var req = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>PartyPendingBills</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE>
              <COLLECTION NAME="PartyPendingBills">
                <TYPE>Bill</TYPE>
                <FETCH>NAME, CLOSINGBALANCE, PARENT</FETCH>
                <FILTER>OnlyThisParty</FILTER>
              </COLLECTION>
              <SYSTEM TYPE="Formulae" NAME="OnlyThisParty">$Parent = "{escParty}" AND NOT $$IsEmpty:$ClosingBalance</SYSTEM>
            </TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req)));
            foreach (var b in doc.Descendants("BILL"))
            {
                var bName = (b.Attribute("NAME")?.Value ?? b.Element("NAME")?.Value ?? "").Trim();
                if (string.IsNullOrEmpty(bName)) continue;
                decimal.TryParse((b.Element("CLOSINGBALANCE")?.Value ?? "").Trim(), NumberStyles.Any, CultureInfo.InvariantCulture, out var bv);
                if (results.All(x => !x.BillName.Equals(bName, StringComparison.OrdinalIgnoreCase)))
                    // Tally XML writes a debit balance as negative: a negative bill is owed TO us (receivable), a positive one is ours to pay.
                    results.Add(new BillAllocation { BillName = bName, PendingAmount = Math.Round(Math.Abs(bv), 2), BillType = "Agst Ref", IsPayable = bv > 0 });
            }
        }
        catch { }
        return results;
    }

    public async Task<List<string>> FetchGroupsAsync()
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var req = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>AllGroups</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE><COLLECTION NAME="AllGroups"><TYPE>Group</TYPE><FETCH>NAME</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req)));
            var groups = doc.Descendants("GROUP")
                .Select(g => (g.Attribute("NAME")?.Value ?? g.Element("NAME")?.Value ?? "").Trim())
                .Where(n => !string.IsNullOrEmpty(n)).Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(n => n, StringComparer.OrdinalIgnoreCase).ToList();
            return groups.Count > 0 ? groups : StandardGroups.ToList();
        }
        catch { return StandardGroups.ToList(); }
    }

    private static decimal ParseTallySignedAssetBalance(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return 0m;
        var s = raw.Trim();
        bool hasDr = Regex.IsMatch(s, @"\bDr\b", RegexOptions.IgnoreCase);
        bool hasCr = Regex.IsMatch(s, @"\bCr\b", RegexOptions.IgnoreCase);
        var cleaned = Regex.Replace(s, @"[^0-9.\-]", "");
        if (!decimal.TryParse(cleaned, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out var val))
            return 0m;
        decimal res;
        if (hasDr) res = Math.Abs(val);
        else if (hasCr) res = -Math.Abs(val);
        else res = -val; // In Tally raw XML, Debit asset balance is negative (-63978.96 = +63978.96 Dr)
        return Math.Round(res, 2);
    }

    public async Task<string> FetchCompanyBooksStartYmdAsync()
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var req = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>ABSECompDates</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE><COLLECTION NAME="ABSECompDates"><TYPE>Company</TYPE><FETCH>NAME, STARTINGFROM, BOOKSFROM</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(req)));
            var companies = doc.Descendants("COMPANY").ToList();
            var match = !string.IsNullOrWhiteSpace(CompanyName)
                ? companies.FirstOrDefault(c => string.Equals((c.Attribute("NAME")?.Value ?? c.Element("NAME")?.Value ?? "").Trim(), CompanyName.Trim(), StringComparison.OrdinalIgnoreCase))
                : null;
            // Only fall back to "the" company when there is no ambiguity (never read another loaded company's dates)
            if (match == null && (string.IsNullOrWhiteSpace(CompanyName) || companies.Count == 1)) match = companies.FirstOrDefault();
            if (match != null)
            {
                var bf = (match.Element("BOOKSFROM")?.Value ?? "").Trim();
                var sf = (match.Element("STARTINGFROM")?.Value ?? "").Trim();
                var raw = !string.IsNullOrEmpty(bf) ? bf : sf;
                if (raw.Length == 8 && raw.All(char.IsDigit)) return raw;
                if (DateTime.TryParse(raw, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)) return dt.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            }
        }
        catch { }
        return "";
    }

    private async Task<(bool found, decimal masterOp, decimal masterCl)> FetchLedgerMasterBalancesAsync(string ledgerName)
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";

        // 1. Official Tally Export Object request for a single Ledger (never affected by SVFROMDATE collection quirks)
        var objReq = $"""
            <ENVELOPE>
              <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Object</TYPE><SUBTYPE>Ledger</SUBTYPE><ID TYPE="Name">{Esc(ledgerName)}</ID></HEADER>
              <BODY><DESC>
                <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
                <FETCHLIST><FETCH>NAME</FETCH><FETCH>OPENINGBALANCE</FETCH><FETCH>CLOSINGBALANCE</FETCH></FETCHLIST>
              </DESC></BODY>
            </ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(objReq)));
            var el = doc.Descendants("LEDGER").FirstOrDefault();
            if (el != null)
            {
                var opEl = el.Element("OPENINGBALANCE");
                var clEl = el.Element("CLOSINGBALANCE");
                if (opEl != null || clEl != null)
                {
                    decimal op = ParseTallySignedAssetBalance(opEl?.Value);
                    decimal cl = ParseTallySignedAssetBalance(clEl?.Value);
                    return (true, op, cl);
                }
            }
        }
        catch { }

        // 2. Fallback: unfiltered Ledger Collection without SVFROMDATE
        var colReq = $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>AllLedBal</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE><COLLECTION NAME="AllLedBal"><TYPE>Ledger</TYPE><FETCH>NAME, OPENINGBALANCE, CLOSINGBALANCE</FETCH></COLLECTION></TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        try
        {
            var doc = XDocument.Parse(SanitizeXml(await PostXmlAsync(colReq)));
            var el = doc.Descendants("LEDGER").FirstOrDefault(x =>
                string.Equals((x.Attribute("NAME")?.Value ?? x.Element("NAME")?.Value ?? x.Descendants("NAME").FirstOrDefault()?.Value ?? "").Trim(), ledgerName.Trim(), StringComparison.OrdinalIgnoreCase));
            if (el != null)
            {
                decimal op = ParseTallySignedAssetBalance(el.Element("OPENINGBALANCE")?.Value);
                decimal cl = ParseTallySignedAssetBalance(el.Element("CLOSINGBALANCE")?.Value);
                return (true, op, cl);
            }
        }
        catch { }

        return (false, 0, 0);
    }

    public async Task<(bool found, decimal opening, decimal closing)> FetchLedgerBalancesAsync(string ledgerName, string fromDate, string toDate)
    {
        var masterTask = FetchLedgerMasterBalancesAsync(ledgerName);
        var booksStartTask = FetchCompanyBooksStartYmdAsync();
        await Task.WhenAll(masterTask, booksStartTask);

        var (found, masterOp, masterCl) = masterTask.Result;
        if (!found) return (false, 0, 0);

        if (!DateTime.TryParseExact(fromDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var stmtStartDt))
            return (true, masterOp, masterCl);

        string booksStartYmd = booksStartTask.Result;
        if (string.IsNullOrEmpty(booksStartYmd))
        {
            // Default Indian FY start (01-Apr) for stmtStartDt
            int fyYear = stmtStartDt.Month >= 4 ? stmtStartDt.Year : stmtStartDt.Year - 1;
            booksStartYmd = $"{fyYear}0401";
        }

        decimal openingOnStmtStart = masterOp;
        decimal closingOnStmtEnd = masterCl;
        bool hasToDate = DateTime.TryParseExact(toDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var stmtEndDt);

        if (DateTime.TryParseExact(booksStartYmd, "yyyyMMdd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var booksDt))
        {
            var fetchEndDt = hasToDate && stmtEndDt >= stmtStartDt ? stmtEndDt : stmtStartDt.AddDays(-1);
            if (fetchEndDt >= booksDt)
            {
                var booksIso = booksDt.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                var fetchEndIso = fetchEndDt.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                var (vchOk, vouchersToEnd) = await FetchExistingVouchersExAsync(booksIso, fetchEndIso, padDays: 0, bankLedger: ledgerName, timeout: BalanceTimeout, confirmEmpty: false);
                // Could not read the vouchers: the master opening alone is NOT the balance on the statement date — report
                // "not found" rather than a wrong number that triggers false mismatch warnings.
                if (!vchOk) return (false, 0, 0);
                decimal priorNet = 0, toEndNet = 0;
                foreach (var v in vouchersToEnd)
                {
                    if (!v.LedgerAmounts.TryGetValue(ledgerName, out var signedAmt)) continue;
                    // In Tally XML, Bank DR (deposit) is negative (<0) and Bank CR (withdrawal) is positive (>0)
                    decimal assetDelta = -signedAmt;
                    if (string.CompareOrdinal(v.Date, fromDate) < 0) priorNet += assetDelta;
                    if (!hasToDate || string.CompareOrdinal(v.Date, toDate) <= 0) toEndNet += assetDelta;
                }
                if (stmtStartDt > booksDt) openingOnStmtStart = Math.Round(masterOp + priorNet, 2);
                if (hasToDate) closingOnStmtEnd = Math.Round(masterOp + toEndNet, 2);
            }
        }

        return (true, openingOnStmtStart, closingOnStmtEnd);
    }


    /// <summary>
    /// Fetches live Tally vouchers for the period. <c>ok</c> is FALSE when Tally could not be read (timeout / error) so callers
    /// can warn the user instead of silently treating "could not read" as "no existing entries" (which disabled the
    /// duplicate-against-Tally check and produced false "Missing" verification results).
    /// </summary>
    public async Task<(bool ok, List<TallyExistingVoucher> vouchers)> FetchExistingVouchersExAsync(string fromDate, string toDate, int padDays = 2, string bankLedger = "", TimeSpan? timeout = null, bool confirmEmpty = true)
    {
        bool hasFrom = DateTime.TryParseExact(fromDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var fDt);
        bool hasTo = DateTime.TryParseExact(toDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var tDt);
        string fromYmd = hasFrom ? fDt.AddDays(-padDays).ToString("yyyyMMdd", CultureInfo.InvariantCulture) : fromDate.Replace("-", "");
        string toYmd = hasTo ? tDt.AddDays(padDays).ToString("yyyyMMdd", CultureInfo.InvariantCulture) : toDate.Replace("-", "");
        string fromIso = hasFrom ? fDt.AddDays(-padDays).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : "";
        string toIso = hasTo ? tDt.AddDays(padDays).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : "";

        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        const string fetch = "<FETCH>DATE, VOUCHERTYPENAME, VOUCHERNUMBER, GUID, REMOTEID, NARRATION, ISCANCELLED, ISOPTIONAL, ALLLEDGERENTRIES.LIST, LEDGERENTRIES.LIST</FETCH>";
        // Date range is filtered INSIDE Tally (FILTER formula) — some Tally builds ignore SVFROMDATE on custom collections and
        // used to stream the company's ENTIRE voucher history (every ledger, every year), which took minutes and "timed out"
        // although Tally was working normally.
        const string dateFilter = "<FILTER>ABSEInRange</FILTER></COLLECTION><SYSTEM TYPE=\"Formulae\" NAME=\"ABSEInRange\">$Date &gt;= ##SVFromDate AND $Date &lt;= ##SVToDate</SYSTEM>";
        string Envelope(string collection) => $"""
            <ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>ExistingVch</ID></HEADER>
            <BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT><SVFROMDATE>{fromYmd}</SVFROMDATE><SVTODATE>{toYmd}</SVTODATE>{compTag}</STATICVARIABLES>
            <TDL><TDLMESSAGE>{collection}</TDLMESSAGE></TDL></DESC></BODY></ENVELOPE>
            """;
        // Preferred: only the vouchers of THIS bank ledger (Tally's own ledger-voucher index — what Display > Ledger uses).
        // This is a tiny fraction of the company's vouchers, so it returns in seconds even on large data.
        var ledgerReq = string.IsNullOrWhiteSpace(bankLedger) ? null : Envelope(
            $"<COLLECTION NAME=\"ExistingVch\"><TYPE>Vouchers : Ledger</TYPE><CHILDOF>{Esc(bankLedger.Trim())}</CHILDOF>{fetch}{dateFilter}");
        var companyReq = Envelope($"<COLLECTION NAME=\"ExistingVch\"><TYPE>Voucher</TYPE>{fetch}{dateFilter}");

        var list = new List<TallyExistingVoucher>();
        try
        {
            string raw;
            if (ledgerReq != null)
            {
                raw = await PostXmlAsync(ledgerReq, timeout ?? LongTimeout);
                // A Tally build that does not understand the ledger-scoped collection answers with an error, not vouchers:
                // fall back to the company-wide (date-filtered) collection.
                if (raw.Contains("<LINEERROR>", StringComparison.OrdinalIgnoreCase) || (!raw.Contains("<VOUCHER", StringComparison.OrdinalIgnoreCase) && !raw.Contains("<COLLECTION", StringComparison.OrdinalIgnoreCase) && !raw.Contains("<ENVELOPE", StringComparison.OrdinalIgnoreCase)))
                    raw = await PostXmlAsync(companyReq, timeout ?? LongTimeout);
            }
            else raw = await PostXmlAsync(companyReq, timeout ?? LongTimeout);
            ParseVouchersInto(raw, fromIso, toIso, list);
            // Safety net: if the ledger-scoped answer contains NO voucher of the bank (misspelt CHILDOF, older Tally build),
            // never treat that as "nothing exists in Tally" — confirm with the company-wide, date-filtered collection.
            if (ledgerReq != null && confirmEmpty && !list.Any(tv => tv.LedgerAmounts.ContainsKey(bankLedger.Trim())))
            {
                list.Clear();
                ParseVouchersInto(await PostXmlAsync(companyReq, timeout ?? LongTimeout), fromIso, toIso, list);
            }
        }
        catch
        {
            return (false, list);
        }
        return (true, list);
    }

    private static void ParseVouchersInto(string raw, string fromIso, string toIso, List<TallyExistingVoucher> list)
    {
        {
            var doc = XDocument.Parse(SanitizeXml(raw));
            foreach (var v in doc.Descendants("VOUCHER"))
            {
                if (string.Equals((v.Element("ISCANCELLED")?.Value ?? "").Trim(), "Yes", StringComparison.OrdinalIgnoreCase)) continue;
                if (string.Equals((v.Element("ISOPTIONAL")?.Value ?? "").Trim(), "Yes", StringComparison.OrdinalIgnoreCase)) continue;
                var td = (v.Element("DATE")?.Value ?? "").Trim();
                var iso = td.Length == 8 ? $"{td[..4]}-{td[4..6]}-{td[6..8]}" : td;
                // Some Tally builds ignore SVFROMDATE/SVTODATE on custom Voucher collections — enforce the period client-side
                if (fromIso.Length > 0 && iso.Length == 10 && string.CompareOrdinal(iso, fromIso) < 0) continue;
                if (toIso.Length > 0 && iso.Length == 10 && string.CompareOrdinal(iso, toIso) > 0) continue;

                // ALLLEDGERENTRIES.LIST is the complete set; LEDGERENTRIES.LIST repeats the same entries for ordinary vouchers.
                // Reading BOTH doubled every amount (bank ₹500 seen as ₹1,000), which broke overlap detection and
                // Tally balance computation. Use ALL... when present, else LEDGERENTRIES.LIST (invoice-mode vouchers).
                var allEntries = v.Descendants("ALLLEDGERENTRIES.LIST").ToList();
                var entryNodes = allEntries.Count > 0 ? allEntries : v.Descendants("LEDGERENTRIES.LIST").ToList();
                var ledgers = new List<string>();
                var ledgerAmounts = new Dictionary<string, decimal>(StringComparer.OrdinalIgnoreCase);
                string instNo = "";
                foreach (var le in entryNodes)
                {
                    var lname = (le.Element("LEDGERNAME")?.Value ?? "").Trim();
                    if (string.IsNullOrEmpty(lname)) continue;
                    if (!ledgers.Contains(lname, StringComparer.OrdinalIgnoreCase)) ledgers.Add(lname);
                    if (decimal.TryParse((le.Element("AMOUNT")?.Value ?? "").Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var a))
                    {
                        ledgerAmounts[lname] = ledgerAmounts.TryGetValue(lname, out var prev) ? Math.Round(prev + a, 2) : Math.Round(a, 2);
                    }
                    if (string.IsNullOrEmpty(instNo))
                    {
                        instNo = (le.Descendants("INSTRUMENTNUMBER").FirstOrDefault()?.Value ?? "").Trim();
                    }
                }
                var maxAmt = ledgerAmounts.Values.Select(x => Math.Abs(x)).DefaultIfEmpty(0m).Max();
                if (!string.IsNullOrEmpty(iso) && maxAmt > 0)
                {
                    list.Add(new TallyExistingVoucher
                    {
                        Date = iso,
                        VoucherType = (v.Element("VOUCHERTYPENAME")?.Value ?? "").Trim(),
                        Guid = (v.Element("GUID")?.Value ?? "").Trim(),
                        RemoteId = ((string?)v.Attribute("REMOTEID") ?? v.Element("REMOTEID")?.Value ?? "").Trim(),
                        VoucherNumber = (v.Element("VOUCHERNUMBER")?.Value ?? "").Trim(),
                        RefNo = instNo,
                        Narration = (v.Element("NARRATION")?.Value ?? "").Trim(),
                        Ledgers = ledgers,
                        LedgerAmounts = ledgerAmounts,
                        Amount = Math.Round(maxAmt, 2)
                    });
                }
            }
        }
    }

    public static string SuggestParentGroup(string name, string vtype, string txnType, bool isBank)
    {
        var low = name.ToLowerInvariant();
        if (isBank || low.Contains("bank") || low.Contains("current a/c")) return low.Contains("od") ? "Bank OD A/c" : "Bank Accounts";
        if (low == "cash" || low.Contains("petty cash")) return "Cash-in-Hand";
        if (low.Contains("gst") || low.Contains("tds") || low.Contains("tax")) return "Duties & Taxes";
        if (low.Contains("suspense")) return "Suspense A/c";
        if (low.Contains("drawing") || low.Contains("capital")) return "Capital Account";
        if (low.Contains("sales")) return "Sales Accounts";
        if (low.Contains("purchase")) return "Purchase Accounts";
        if (low.Contains("creditor") || low.Contains("traders") || low.Contains("enterprises")) return txnType == "CR" && !low.Contains("creditor") ? "Sundry Debtors" : "Sundry Creditors";
        if (low.Contains("debtor") || low.Contains("client")) return "Sundry Debtors";
        if (low.Contains("expense") || low.Contains("charges") || low.Contains("insurance") || low.Contains("rent") || low.Contains("salary") || low.Contains("electricity") || low.Contains("repair") || low.Contains("stationery") || low.Contains("travel") || low.Contains("fuel")) return "Indirect Expenses";
        if (low.Contains("interest received") || vtype == "Receipt" || txnType == "CR") return "Indirect Incomes";
        return "Indirect Expenses";
    }

    public string BuildLedgersXml(IEnumerable<MissingLedgerItem> items)
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var sb = new StringBuilder();
        sb.AppendLine($"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>All Masters</REPORTNAME><STATICVARIABLES>{compTag}</STATICVARIABLES></REQUESTDESC><REQUESTDATA>");
        foreach (var it in items)
        {
            var bw = it.ParentGroup is "Sundry Creditors" or "Sundry Debtors" ? "Yes" : "No";
            sb.AppendLine($"<TALLYMESSAGE xmlns:UDF=\"TallyUDF\"><LEDGER NAME=\"{Esc(it.Name)}\" ACTION=\"Create\"><NAME.LIST><NAME>{Esc(it.Name)}</NAME></NAME.LIST><PARENT>{Esc(it.ParentGroup)}</PARENT><ISBILLWISEON>{bw}</ISBILLWISEON><AFFECTSSTOCK>No</AFFECTSSTOCK></LEDGER></TALLYMESSAGE>");
        }
        sb.AppendLine("</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>");
        return sb.ToString();
    }

    public async Task<(bool success, string error)> CreateLedgersAsync(IEnumerable<MissingLedgerItem> items)
    {
        try
        {
            var raw = await PostXmlAsync(BuildLedgersXml(items));
            var doc = XDocument.Parse(SanitizeXml(raw));
            int errs = int.TryParse(doc.Descendants("ERRORS").FirstOrDefault()?.Value, out var e) ? e : 0;
            var lineErr = (doc.Descendants("LINEERROR").FirstOrDefault()?.Value ?? "").Trim();
            return (errs == 0 && string.IsNullOrEmpty(lineErr), DiagnoseError(lineErr, raw, ""));
        }
        catch (Exception ex) { return (false, DiagnoseError("", "", ex.Message)); }
    }

    /// <summary>Party (bill-wise) ledgers: split lines to these get an "On Account" bill line so Tally's outstanding stays complete.</summary>
    public HashSet<string> PartyLedgers { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Fill the bank date (BRS) with the statement date, so the entry shows as reconciled in Tally's Bank Reconciliation.</summary>
    public bool SetBankDate { get; set; } = true;

    /// <summary>Post "Party • Mode • Ref" as the first narration line, with the bank's original text on the next line.</summary>
    public bool UseTidyNarration { get; set; }

    public string NarrationFor(BankTransactionRow v) =>
        UseTidyNarration && v.HasTidyNarration && !string.Equals(v.TidyNarration.Trim(), (v.Narration ?? "").Trim(), StringComparison.OrdinalIgnoreCase)
            ? v.TidyNarration.Trim() + "\r\n" + (v.Narration ?? "")
            : v.Narration ?? "";

    public string BuildVouchersXml(IEnumerable<BankTransactionRow> vouchers)
    {
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        var sb = new StringBuilder();
        sb.AppendLine($"<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>{compTag}</STATICVARIABLES></REQUESTDESC><REQUESTDATA>");
        foreach (var v in vouchers)
        {
            var td = v.TxnDate.Replace("-", "");
            var amt = Math.Round(Math.Abs(v.Amount), 2);
            var bankPos = v.TxnType == "DR" ? "No" : "Yes";
            // Amounts MUST be culture-invariant ("1234.50"): on a PC whose regional settings use a comma decimal
            // separator, "{amt:F2}" produced "1234,50" which Tally mis-reads.
            var bankAmt = v.TxnType == "DR" ? Inv(amt) : $"-{Inv(amt)}";
            var partyPos = v.TxnType == "DR" ? "Yes" : "No";
            var partyAmt = v.TxnType == "DR" ? $"-{Inv(amt)}" : Inv(amt);
            var instXml = string.IsNullOrWhiteSpace(v.RefNo) ? "" : $"<INSTRUMENTNUMBER>{Esc(v.RefNo)}</INSTRUMENTNUMBER>";
            var bankDateXml = SetBankDate ? $"<BANKERSDATE>{td}</BANKERSDATE>" : "";
            // a line break inside the narration must survive XML: write it as a character reference
            var narrXml = Esc(NarrationFor(v)).Replace("\r\n", "&#13;&#10;").Replace("\n", "&#13;&#10;");
            string billAllocXml = "";
            // Bill-wise allocations only make sense on Payment/Receipt to a party; never on Contra (cash/bank) vouchers
            bool allowBills = !string.Equals(v.VoucherType, "Contra", StringComparison.OrdinalIgnoreCase);
            if (allowBills && v.BillAllocations is { Count: > 0 })
            {
                var bSb = new StringBuilder();
                decimal allocatedSum = 0;
                foreach (var ba in v.BillAllocations.Where(x => x.AllocateAmount > 0))
                {
                    decimal takeAmt = Math.Round(Math.Min(ba.AllocateAmount, Math.Max(0m, amt - allocatedSum)), 2);
                    if (takeAmt <= 0) break;
                    var signedAmt = v.TxnType == "DR" ? $"-{Inv(takeAmt)}" : Inv(takeAmt);
                    allocatedSum = Math.Round(allocatedSum + takeAmt, 2);
                    if (ba.BillType.Equals("On Account", StringComparison.OrdinalIgnoreCase))
                        bSb.Append($"<BILLALLOCATIONS.LIST><BILLTYPE>On Account</BILLTYPE><AMOUNT>{signedAmt}</AMOUNT></BILLALLOCATIONS.LIST>");
                    else
                        bSb.Append($"<BILLALLOCATIONS.LIST><NAME>{Esc(ba.BillName)}</NAME><BILLTYPE>Agst Ref</BILLTYPE><AMOUNT>{signedAmt}</AMOUNT></BILLALLOCATIONS.LIST>");
                }
                decimal rem = Math.Round(amt - allocatedSum, 2);
                if (rem > 0)
                {
                    var remSigned = v.TxnType == "DR" ? $"-{Inv(rem)}" : Inv(rem);
                    bSb.Append($"<BILLALLOCATIONS.LIST><BILLTYPE>On Account</BILLTYPE><AMOUNT>{remSigned}</AMOUNT></BILLALLOCATIONS.LIST>");
                }
                billAllocXml = bSb.ToString();
            }
            else if (allowBills)
            {
                var billRaw = (v.BillRef ?? "").Trim();
                var billName = (billRaw.StartsWith("(None", StringComparison.OrdinalIgnoreCase) || billRaw.StartsWith("Split", StringComparison.OrdinalIgnoreCase))
                    ? ""
                    : Regex.Replace(billRaw, @"\s*\(₹[0-9,.]+\)$", "").Trim();
                if (!string.IsNullOrEmpty(billName))
                    billAllocXml = $"<BILLALLOCATIONS.LIST><NAME>{Esc(billName)}</NAME><BILLTYPE>Agst Ref</BILLTYPE><AMOUNT>{partyAmt}</AMOUNT></BILLALLOCATIONS.LIST>";
            }
            var tMode = v.PaymentMode.Contains("Cheque") ? "Cheque/DD" : (v.PaymentMode.Contains("Cash") ? "Cash" : "e-Fund Transfer");

            // One bank line + one line per ledger. A split must add up to the bank amount to the paisa — an unbalanced
            // voucher is never sent.
            string partyLines;
            if (v.IsSplit)
            {
                long totalPaise = (long)Math.Round(amt * 100), splitPaise = v.Splits.Sum(x => (long)Math.Round(Math.Abs(x.Amount) * 100));
                if (splitPaise != totalPaise || v.Splits.Any(x => string.IsNullOrWhiteSpace(x.Ledger) || x.Amount <= 0))
                    throw new InvalidOperationException($"Split of {v.DisplayDate} ₹{amt:N2} does not add up to the bank amount.");
                var pl = new StringBuilder();
                foreach (var sp in v.Splits)
                {
                    var sa = Math.Round(Math.Abs(sp.Amount), 2);
                    var sAmt = v.TxnType == "DR" ? $"-{Inv(sa)}" : Inv(sa);
                    var sBill = allowBills && PartyLedgers.Contains(sp.Ledger.Trim())
                        ? $"<BILLALLOCATIONS.LIST><BILLTYPE>On Account</BILLTYPE><AMOUNT>{sAmt}</AMOUNT></BILLALLOCATIONS.LIST>" : "";
                    pl.Append($"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{Esc(sp.Ledger.Trim())}</LEDGERNAME><ISDEEMEDPOSITIVE>{partyPos}</ISDEEMEDPOSITIVE><AMOUNT>{sAmt}</AMOUNT>{sBill}</ALLLEDGERENTRIES.LIST>");
                }
                partyLines = pl.ToString();
            }
            else
                partyLines = $"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{Esc(v.SelectedLedger)}</LEDGERNAME><ISDEEMEDPOSITIVE>{partyPos}</ISDEEMEDPOSITIVE><AMOUNT>{partyAmt}</AMOUNT>{billAllocXml}</ALLLEDGERENTRIES.LIST>";

            sb.AppendLine($"""
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                  <VOUCHER REMOTEID="{Esc(v.VoucherGuid)}" VCHTYPE="{Esc(v.VoucherType)}" ACTION="Create" OBJVIEW="Accounting Voucher View">
                    <DATE>{td}</DATE><EFFECTIVEDATE>{td}</EFFECTIVEDATE><GUID>{Esc(v.VoucherGuid)}</GUID>
                    <VOUCHERTYPENAME>{Esc(v.VoucherType)}</VOUCHERTYPENAME><NARRATION>{narrXml}</NARRATION>
                    {partyLines}
                    <ALLLEDGERENTRIES.LIST><LEDGERNAME>{Esc(v.BankLedger)}</LEDGERNAME><ISDEEMEDPOSITIVE>{bankPos}</ISDEEMEDPOSITIVE><AMOUNT>{bankAmt}</AMOUNT>
                      <BANKALLOCATIONS.LIST><DATE>{td}</DATE><INSTRUMENTDATE>{td}</INSTRUMENTDATE>{bankDateXml}<NAME>{Esc(v.VoucherGuid)}</NAME><TRANSACTIONTYPE>{tMode}</TRANSACTIONTYPE>{instXml}<PAYMENTFAVOURING>{Esc(v.SelectedLedger)}</PAYMENTFAVOURING><AMOUNT>{bankAmt}</AMOUNT></BANKALLOCATIONS.LIST>
                    </ALLLEDGERENTRIES.LIST>
                  </VOUCHER>
                </TALLYMESSAGE>
                """);
        }
        sb.AppendLine("</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>");
        return sb.ToString();
    }

    public async Task<TallyPushResult> PushVouchersIndividuallyAsync(List<BankTransactionRow> vouchers, StatementBalanceInfo? stmtBal = null)
    {
        var result = new TallyPushResult { Total = vouchers.Count };
        for (int i = 0; i < vouchers.Count; i++)
        {
            var v = vouchers[i];
            try
            {
                var raw = await PostXmlAsync(BuildVouchersXml([v]), PostTimeout);
                var doc = XDocument.Parse(SanitizeXml(raw));
                int created = int.TryParse(doc.Descendants("CREATED").FirstOrDefault()?.Value, out var c) ? c : 0;
                int altered = int.TryParse(doc.Descendants("ALTERED").FirstOrDefault()?.Value, out var a) ? a : 0;
                int errs = int.TryParse(doc.Descendants("ERRORS").FirstOrDefault()?.Value, out var e) ? e : 0;
                int exceptions = int.TryParse(doc.Descendants("EXCEPTIONS").FirstOrDefault()?.Value, out var x) ? x : 0;
                int ignored = int.TryParse(doc.Descendants("IGNORED").FirstOrDefault()?.Value, out var ig) ? ig : 0;
                var lineErr = string.Join(" | ", doc.Descendants("LINEERROR").Select(l => l.Value.Trim()).Where(l => l.Length > 0));

                if (errs == 0 && exceptions == 0 && string.IsNullOrEmpty(lineErr) && (created > 0 || altered > 0))
                    result.PostedEntries.Add(v);
                else
                {
                    var why = DiagnoseError(lineErr, raw, "", v);
                    if (string.IsNullOrEmpty(lineErr) && (exceptions > 0 || ignored > 0))
                        why = $"Tally did not create the voucher (exceptions: {exceptions}, ignored: {ignored}). Check that the ledgers / voucher type exist and the date is inside the books period.";
                    result.FailedEntries.Add(new FailedEntry { RowId = v.RowId, DisplayDate = v.DisplayDate, Narration = v.Narration, SelectedLedger = v.SelectedLedger, Amount = v.Amount, Reason = why });
                }
            }
            catch (Exception ex)
            {
                var reason = DiagnoseError("", "", ex.Message, v);
                if (ex is HttpRequestException or TaskCanceledException)
                {
                    // The entry that was in flight may HAVE been saved by Tally even though no reply arrived. It is reported
                    // as failed, but the next Post re-checks Tally (by its voucher ID) and will not create it a second time.
                    var inFlight = ex is TaskCanceledException
                        ? reason + " — Tally did not reply in time; it MAY have saved this entry. Posting again is safe: it is re-checked against Tally first."
                        : reason;
                    result.FailedEntries.Add(new FailedEntry { RowId = v.RowId, DisplayDate = v.DisplayDate, Narration = v.Narration, SelectedLedger = v.SelectedLedger, Amount = v.Amount, Reason = inFlight });
                    foreach (var rem in vouchers.Skip(i + 1))
                        result.FailedEntries.Add(new FailedEntry { RowId = rem.RowId, DisplayDate = rem.DisplayDate, Narration = rem.Narration, SelectedLedger = rem.SelectedLedger, Amount = rem.Amount, Reason = reason });
                    break;
                }
                result.FailedEntries.Add(new FailedEntry { RowId = v.RowId, DisplayDate = v.DisplayDate, Narration = v.Narration, SelectedLedger = v.SelectedLedger, Amount = v.Amount, Reason = reason });
            }
        }

        result.Created = result.PostedEntries.Count;
        result.FailedCount = result.FailedEntries.Count;
        result.Success = result.FailedCount == 0 && result.Created > 0;

        if (result.PostedEntries.Count > 0)
        {
            var dates = result.PostedEntries.Select(r => r.TxnDate).OrderBy(d => d, StringComparer.Ordinal).ToList();
            // Sequential on purpose (Tally answers one request at a time — parallel heavy requests time each other out)
            var (liveOk, liveList) = await FetchExistingVouchersExAsync(dates[0], dates[^1], bankLedger: result.PostedEntries[0].BankLedger);
            (bool found, decimal opening, decimal closing)? balRes = stmtBal != null
                ? await FetchLedgerBalancesAsync(result.PostedEntries[0].BankLedger, stmtBal.FromDate, stmtBal.ToDate)
                : null;
            result.Verification = liveOk
                ? VerifyPosted(result.PostedEntries, liveList)
                : new VerificationReport { AllOk = false, CouldNotVerify = true, Expected = result.PostedEntries.Count };
            if (stmtBal != null && balRes.HasValue)
            {
                var bankName = result.PostedEntries[0].BankLedger;
                var (found, tOp, tCl) = balRes.Value;
                if (found)
                {
                    var opStatus = stmtBal.StatementOpening.HasValue ? (tOp == stmtBal.StatementOpening.Value ? "Matched ✓" : $"Diff ₹{tOp - stmtBal.StatementOpening.Value:N2}") : "N/A";
                    var clStatus = stmtBal.StatementClosing.HasValue ? (tCl == stmtBal.StatementClosing.Value ? "Matched ✓" : $"Diff ₹{tCl - stmtBal.StatementClosing.Value:N2}") : "N/A";
                    result.Verification.BalanceSummary = $"Bank Balance ({bankName}) — Opening: Tally ₹{tOp:N2} ({opStatus}) | Closing: Tally ₹{tCl:N2} ({clStatus})";
                }
            }
        }
        return result;
    }

    private static VerificationReport VerifyPosted(List<BankTransactionRow> expected, List<TallyExistingVoucher> live)
    {
        var rep = new VerificationReport { Expected = expected.Count };
        var byGuid = new Dictionary<string, List<TallyExistingVoucher>>(StringComparer.OrdinalIgnoreCase);
        var byDateAmt = new Dictionary<(string date, long paise), List<TallyExistingVoucher>>();

        foreach (var tv in live)
        {
            if (!string.IsNullOrEmpty(tv.Guid))
            {
                if (!byGuid.TryGetValue(tv.Guid, out var gl)) byGuid[tv.Guid] = gl = [];
                gl.Add(tv);
            }
            var key = (tv.Date, (long)Math.Round(tv.Amount * 100m));
            if (!byDateAmt.TryGetValue(key, out var dl)) byDateAmt[key] = dl = [];
            dl.Add(tv);
        }

        foreach (var exp in expected)
        {
            var pair = new HashSet<string>(exp.PostingLedgers.Append(exp.BankLedger).Select(l => l.Trim()), StringComparer.OrdinalIgnoreCase);
            List<TallyExistingVoucher>? matches = null;
            if (!string.IsNullOrEmpty(exp.VoucherGuid) && byGuid.TryGetValue(exp.VoucherGuid, out var gHits))
                matches = gHits;
            else if (byDateAmt.TryGetValue((exp.TxnDate, (long)Math.Round(exp.Amount * 100m)), out var dHits))
                matches = dHits.Where(tv => new HashSet<string>(tv.Ledgers, StringComparer.OrdinalIgnoreCase).SetEquals(pair)).ToList();

            if (matches == null || matches.Count == 0) rep.Missing.Add($"{exp.DisplayDate} | {exp.SelectedLedger} | ₹{exp.Amount:N2}");
            else if (matches.Count > 1) rep.Duplicated.Add($"{exp.DisplayDate} | {exp.SelectedLedger} (found {matches.Count}×)");
            else if (!new HashSet<string>(matches[0].Ledgers, StringComparer.OrdinalIgnoreCase).SetEquals(pair))
                rep.Mixed.Add($"{exp.DisplayDate} | Mixed ledgers in Tally");
            else rep.Verified++;
        }
        rep.AllOk = rep.Missing.Count == 0 && rep.Duplicated.Count == 0 && rep.Mixed.Count == 0;
        return rep;
    }

    private async Task<(string companyNumber, string actualDestination, string defaultDataPath)> FetchActiveCompanyStorageInfoAsync()
    {
        string compNum = "";
        string actualDest = "";
        string defaultPath = "";
        try
        {
            var req = """
                <ENVELOPE>
                  <HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>ABSECompStorage</ID></HEADER>
                  <BODY><DESC>
                    <STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES>
                    <TDL><TDLMESSAGE>
                      <COLLECTION NAME="ABSECompStorage" ISMODIFY="No">
                        <TYPE>Company</TYPE>
                        <FETCH>Name, CompanyNumber, Destination, Path</FETCH>
                        <COMPUTE>ActualCompanyPath : $Destination</COMPUTE>
                        <COMPUTE>TallyDataPath : $$SysInfo:CurrentPath</COMPUTE>
                      </COLLECTION>
                    </TDLMESSAGE></TDL>
                  </DESC></BODY>
                </ENVELOPE>
                """;
            var raw = await PostXmlAsync(req);
            var doc = XDocument.Parse(SanitizeXml(raw));
            if (doc != null)
            {
                var companies = doc.Descendants("COMPANY").ToList();
                XElement? match = null;
                if (!string.IsNullOrWhiteSpace(CompanyName))
                {
                    match = companies.FirstOrDefault(c =>
                        string.Equals((c.Attribute("NAME")?.Value ?? c.Element("NAME")?.Value ?? "").Trim(), CompanyName.Trim(), StringComparison.OrdinalIgnoreCase));
                }
                // Never back up a DIFFERENT loaded company because the name did not match exactly
                if (match == null && (string.IsNullOrWhiteSpace(CompanyName) || companies.Count == 1)) match = companies.FirstOrDefault();
                if (match != null)
                {
                    compNum = (match.Element("COMPANYNUMBER")?.Value ?? "").Trim();
                    actualDest = (match.Element("ACTUALCOMPANYPATH")?.Value
                        ?? match.Element("DESTINATION")?.Value
                        ?? match.Element("PATH")?.Value ?? "").Trim();
                    defaultPath = (match.Element("TALLYDATAPATH")?.Value ?? "").Trim();
                }
            }
        }
        catch { }
        return (compNum, actualDest, defaultPath);
    }

    private static bool LooksLikeTallyCompanyFolder(string dir)
    {
        if (!Directory.Exists(dir)) return false;
        return File.Exists(Path.Combine(dir, "Company.1800"))
            || File.Exists(Path.Combine(dir, "Company.900"))
            || File.Exists(Path.Combine(dir, "Manager.1800"))
            || File.Exists(Path.Combine(dir, "Manager.900"));
    }

    public async Task<(bool success, string message)> CreateBackupSnapshotAsync(string backupDir, string customDataPath = "")
    {
        Directory.CreateDirectory(backupDir);
        var ts = DateTime.Now.ToString("dd-MMM-yyyy_HHmmss", CultureInfo.InvariantCulture);
        var displayComp = string.IsNullOrWhiteSpace(CompanyName) ? "TallyCompany" : CompanyName.Trim();
        var safeComp = Regex.Replace(displayComp, @"[\\/:*?""<>|]+", "_").Trim();

        var (companyNumber, actualDestination, defaultDataPath) = await FetchActiveCompanyStorageInfoAsync();

        string? companyFolder = null;

        // 1. Check the EXACT loaded company path ($Destination) first (works for server shares, custom drives, Select from Drive)
        if (!string.IsNullOrWhiteSpace(actualDestination))
        {
            var dest = actualDestination.TrimEnd('\\', '/');
            if (LooksLikeTallyCompanyFolder(dest))
                companyFolder = dest;
            else if (!string.IsNullOrWhiteSpace(companyNumber) && LooksLikeTallyCompanyFolder(Path.Combine(dest, companyNumber)))
                companyFolder = Path.Combine(dest, companyNumber);
        }

        // 2. Fallback to customDataPath / tally.ini default data path + companyNumber
        if (companyFolder == null && !string.IsNullOrWhiteSpace(companyNumber))
        {
            var dataRoots = new List<string>();
            if (!string.IsNullOrWhiteSpace(customDataPath)) dataRoots.Add(customDataPath);
            if (!string.IsNullOrWhiteSpace(defaultDataPath)) dataRoots.Add(defaultDataPath);
            dataRoots.AddRange([@"C:\Users\Public\TallyPrime\Data", @"C:\TallyPrime\Data", @"C:\Tally.ERP9\Data"]);

            foreach (var rootDir in dataRoots.Distinct(StringComparer.OrdinalIgnoreCase))
            {
                var candidate = Path.Combine(rootDir, companyNumber);
                if (LooksLikeTallyCompanyFolder(candidate) || Directory.Exists(candidate))
                {
                    companyFolder = candidate;
                    break;
                }
            }
        }

        if (companyFolder != null)
        {
            var zipName = $"{safeComp} ({companyNumber})_{ts}.zip";
            var zipPath = Path.Combine(backupDir, zipName);
            var folder = companyFolder;
            try
            {
                // Off the UI thread: a large company folder over the network can take minutes to zip
                await Task.Run(() =>
                {
                    using var fs = new FileStream(zipPath, FileMode.Create, FileAccess.Write, FileShare.None);
                    using var archive = new ZipArchive(fs, ZipArchiveMode.Create);
                    var parent = Directory.GetParent(folder)?.FullName ?? folder;
                    foreach (var file in Directory.GetFiles(folder, "*", SearchOption.AllDirectories))
                    {
                        var relPath = Path.GetRelativePath(parent, file);
                        var entry = archive.CreateEntry(relPath, CompressionLevel.Fastest);
                        using var entryStream = entry.Open();
                        using var srcStream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
                        srcStream.CopyTo(entryStream);
                    }
                });
            }
            catch (Exception ex)
            {
                // Never leave a half-written zip that looks like a valid backup
                try { if (File.Exists(zipPath)) File.Delete(zipPath); } catch { }
                return (false, $"Backup of '{displayComp}' failed ({ex.Message}). Please take a native backup in Tally (Alt+Y → Backup) before posting.");
            }
            return (true, $"Backup saved (only {displayComp} / {companyNumber}): {zipName}");
        }

        return (false, string.IsNullOrWhiteSpace(companyNumber)
            ? $"Could not detect Tally company number for '{displayComp}'. Please take a native backup in Tally (Alt+Y → Backup)."
            : $"Could not locate company folder '{companyNumber}' in Tally Data path. Please take a native backup in Tally (Alt+Y → Backup).");
    }

    public static string DiagnoseError(string lineError, string rawResp, string exMsg, BankTransactionRow? row = null)
    {
        // Only inspect Tally's own error text and the exception message — the raw XML response contains tag names
        // (e.g. ...DATE..., ...CONNECT...) that used to trigger the wrong diagnosis.
        var err = (lineError ?? "").ToLowerInvariant();
        var ex = (exMsg ?? "").ToLowerInvariant();
        if (ex.Contains("refused") || ex.Contains("timed out") || ex.Contains("timeout") || ex.Contains("canceled") || ex.Contains("cancelled")
            || ex.Contains("no connection") || ex.Contains("actively refused") || ex.Contains("unreachable") || ex.Contains("connect"))
            return "Cannot connect to Tally (or Tally did not answer in time). Make sure Tally is open with the company loaded and F1 → Settings → Connectivity → Client/Server is enabled on the configured port.";
        if (err.Contains("educational"))
            return $"Tally Educational Mode restriction ({lineError}): Educational Mode only accepts the 1st, 2nd or 31st of a month.";
        if (err.Contains("date") && (err.Contains("outside") || err.Contains("period") || err.Contains("before") || err.Contains("books")))
            return $"Date outside the company's books / financial year: {lineError}";
        if (err.Contains("does not exist") || err.Contains("could not find") || err.Contains("not found"))
            return $"Missing Tally Master: {lineError}";
        if (!string.IsNullOrWhiteSpace(lineError)) return lineError;
        if (!string.IsNullOrWhiteSpace(exMsg)) return exMsg;
        return "Tally rejected the entry.";
    }

    public async Task<(int deleted, int failed, string summary, List<string> deletedGuids)> DeleteVouchersByGuidAsync(List<BatchVoucherRef> vouchers)
    {
        int deleted = 0, failed = 0;
        var deletedGuids = new List<string>();
        var compTag = string.IsNullOrEmpty(CompanyName) ? "" : $"<SVCURRENTCOMPANY>{Esc(CompanyName)}</SVCURRENTCOMPANY>";
        foreach (var v in vouchers)
        {
            if (string.IsNullOrWhiteSpace(v.Guid)) { failed++; continue; }
            var tallyDate = v.Date.Replace("-", "");
            // REMOTEID identifies the voucher we created (we always import with REMOTEID = GUID)
            var xml = $"""
                <ENVELOPE>
                  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
                  <BODY><IMPORTDATA>
                    <REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>{compTag}</STATICVARIABLES></REQUESTDESC>
                    <REQUESTDATA>
                      <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <VOUCHER REMOTEID="{Esc(v.Guid)}" VCHTYPE="{Esc(v.VoucherType)}" ACTION="Delete" OBJVIEW="Accounting Voucher View">
                          <DATE>{tallyDate}</DATE>
                          <GUID>{Esc(v.Guid)}</GUID>
                          <VOUCHERTYPENAME>{Esc(v.VoucherType)}</VOUCHERTYPENAME>
                        </VOUCHER>
                      </TALLYMESSAGE>
                    </REQUESTDATA>
                  </IMPORTDATA></BODY>
                </ENVELOPE>
                """;
            try
            {
                var raw = await PostXmlAsync(xml, PostTimeout);
                var doc = XDocument.Parse(SanitizeXml(raw));
                int del = int.TryParse(doc.Descendants("DELETED").FirstOrDefault()?.Value, out var d) ? d : 0;
                int errs = int.TryParse(doc.Descendants("ERRORS").FirstOrDefault()?.Value, out var e) ? e : 0;
                if (del > 0 && errs == 0) { deleted++; deletedGuids.Add(v.Guid); }
                else failed++;
            }
            catch { failed++; }
        }
        return (deleted, failed, $"Rolled back {deleted} of {vouchers.Count} voucher(s) from Tally ({failed} not found / failed).", deletedGuids);
    }
}
