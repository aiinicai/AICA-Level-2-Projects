using System.Collections.Concurrent;
using System.Text.RegularExpressions;
using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// 100% Local Offline ML Ledger Classifier in pure C#:
/// - Prefilled with 100+ Indian banking & Tally ledger seeds (user edits weighted 3.5x)
/// - Indian CA/Tally short-form ledger resolver ("Int Rec", "Int from SB", "Elec Exp", "Ptg & Stat", etc.)
/// - TF-IDF + Multinomial Naive Bayes + Counterparty Memory + Live Online Retraining
/// </summary>
public class LedgerClassifier
{
    private const string SeedMarker = "builtin_seed_v2";
    private readonly DatabaseService _db;
    private readonly object _modelLock = new();

    private Dictionary<string, int> _vocab = new();
    private double[] _idf = [];
    private List<string> _classes = [];
    private Dictionary<string, double> _classLogPrior = new();
    // Sparse model (feature index -> value). Mathematically identical to the previous dense arrays, but memory/time grow with
    // the number of tokens actually seen instead of (documents x vocabulary), which froze the UI once the shared office
    // training table reached tens of thousands of rows.
    private Dictionary<string, Dictionary<int, double>> _classTf = new();
    private Dictionary<string, double> _classDenom = new();
    private Dictionary<string, Dictionary<int, double>> _classCentroids = new();
    private Dictionary<string, Dictionary<string, int>> _counterpartyMap = new();
    private Dictionary<string, Dictionary<string, int>> _userVendorTokenMap = new();
    private Dictionary<string, Dictionary<string, int>> _companyCounterpartyMap = new(StringComparer.OrdinalIgnoreCase);
    private Dictionary<string, Dictionary<string, int>> _companyVendorTokenMap = new(StringComparer.OrdinalIgnoreCase);
    private Dictionary<string, string> _exactParentGroupMap = new(StringComparer.OrdinalIgnoreCase);
    private Dictionary<string, Dictionary<string, int>> _parentGroupTokenMap = new(StringComparer.OrdinalIgnoreCase);

    public int SampleCount { get; private set; }
    private int _lastMlId;
    private int _lastPgId;

    private static readonly HashSet<string> Stopwords = new(StringComparer.OrdinalIgnoreCase)
    {
        "to","by","from","for","the","and","of","in","on","at","via","transfer","trf",
        "payment","paid","received","recvd","ref","no","txn","date","upi","neft","rtgs",
        "imps","p2a","p2p","p2m","dr","cr","inft","bil","mb","ib","okhdfcbank","okicici",
        "oksbi","okaxis","ybl","ibl","paytm","ac","account"
    };

    private static readonly Dictionary<string, string[]> Abbreviations = new(StringComparer.OrdinalIgnoreCase)
    {
        ["int"] = ["interest"], ["intr"] = ["interest"], ["rec"] = ["received"], ["recd"] = ["received"],
        ["rcvd"] = ["received"], ["pd"] = ["paid"], ["sb"] = ["savings", "bank", "interest"],
        ["fd"] = ["fixed", "deposit", "interest"], ["od"] = ["overdraft", "interest"],
        ["chg"] = ["charges"], ["chgs"] = ["charges"], ["comm"] = ["commission", "charges"],
        ["exp"] = ["expenses"], ["exps"] = ["expenses"], ["elec"] = ["electricity"], ["eb"] = ["electricity"],
        ["tel"] = ["telephone"], ["mob"] = ["mobile", "telephone"], ["net"] = ["internet", "broadband"],
        ["sal"] = ["salaries", "salary"], ["stf"] = ["staff", "salaries"], ["rnt"] = ["rent"],
        ["off"] = ["office"], ["misc"] = ["miscellaneous", "office"], ["trav"] = ["travelling", "travel"],
        ["conv"] = ["conveyance", "travelling"], ["ptg"] = ["printing"], ["stat"] = ["stationery"],
        ["rep"] = ["repairs"], ["maint"] = ["maintenance"], ["amc"] = ["maintenance", "repairs"],
        ["soft"] = ["software"], ["sub"] = ["subscriptions"], ["prof"] = ["professional"],
        ["aud"] = ["audit", "professional"], ["adv"] = ["advertising"], ["mktg"] = ["marketing"],
        ["ins"] = ["insurance"], ["veh"] = ["vehicle", "fuel"], ["cour"] = ["courier", "postage"],
        ["frt"] = ["freight", "cartage"], ["drwg"] = ["drawings"], ["susp"] = ["suspense"]
    };

    private static readonly (string pattern, string reqType, string ledger, double conf)[] RulePriors =
    [
        (@"\b(sms\s*chg|bank\s*chg|service\s*charge|folio\s*chg|cheque\s*return|min\s*bal|amb\s*chg|amc\s*chg|imps\s*chg)\b", "DR", "Bank Charges", 0.88),
        (@"\b(int\.?\s*pd|interest\s*cr|credit\s*interest|sb\s*int|fd\s*int|int\s*from\s*sb|int\s*rec|interest\s*capitalised)\b", "CR", "Interest Received", 0.90),
        (@"\b(interest\s*dr|od\s*interest|loan\s*interest|cc\s*int|debit\s*interest)\b", "DR", "Interest Paid", 0.85),
        (@"\b(gst\s*payment|gstn|cbic|igst|cgst|sgst|pmt[\-\s]?06)\b", "DR", "GST Payable", 0.88),
        (@"\b(tds|nsdl|traces|challan\s*281)\b", "DR", "TDS Payable", 0.88),
        (@"\b(income\s*tax|advance\s*tax|challan\s*280|oltas)\b", "DR", "Income Tax / Advance Tax", 0.88),
        (@"\b(tpcodl|tpnodl|bescom|tata\s*power|msedcl|bses|cesc|electricity|power\s*bill|eb\s*bill)\b", "DR", "Electricity Expenses", 0.86),
        (@"\b(airtel|jio|vodafone|bsnl|act\s*fibernet|broadband|telecom|internet\s*bill)\b", "DR", "Telephone & Internet Expenses", 0.85),
        (@"\b(rent|lease\s*rent|office\s*rent|godown\s*rent|shop\s*rent)\b", "DR", "Rent Expense", 0.84),
        (@"\b(salary|salaries|payroll|wages|staff\s*sal|bonus)\b", "DR", "Salaries & Wages", 0.86),
        (@"\b(aws|google\s*cloud|microsoft|zoho|tally\s*solutions|adobe|zoom|saas|subscription)\b", "DR", "Software & Subscriptions", 0.82),
        (@"\b(irctc|indigo|air\s*india|uber|ola|rapido|makemytrip|goibibo|hotel|travel|flight)\b", "DR", "Travelling & Conveyance", 0.80),
        (@"\b(hpcl|bpcl|iocl|petrol|diesel|fuel|fastag|toll)\b", "DR", "Fuel & Vehicle Expenses", 0.82),
        (@"\b(lic|hdfc\s*ergo|icici\s*lombard|bajaj\s*allianz|insurance|policy)\b", "DR", "Insurance Expenses", 0.82),
        (@"\b(ca\s*fees|audit\s*fee|legal|advocate|consultancy|professional\s*fee)\b", "DR", "Professional & Legal Fees", 0.80),
        (@"\b(dtdc|bluedart|delhivery|courier|postage)\b", "DR", "Courier & Postage", 0.82),
        (@"\b(stationery|printing|xerox|toner|cartridge)\b", "DR", "Printing & Stationery", 0.80),
        (@"\b(ac\s*service|computer\s*repair|maintenance|amc)\b", "DR", "Repairs & Maintenance", 0.80),
        (@"\b(amazon|flipkart|swiggy|zomato|bigbasket|blinkit|pantry)\b", "DR", "Office Expenses", 0.72),
    ];

    private static readonly Regex PunctRe = new(@"[/\-_:@|,.*#]+", RegexOptions.Compiled);
    private static readonly Regex LongNumRe = new(@"\b\d{4,}\b", RegexOptions.Compiled);
    private static readonly Regex WordRe = new(@"[a-z]{2,}", RegexOptions.Compiled);
    private static readonly Regex SlashSplitRe = new(@"[/\-]", RegexOptions.Compiled);
    private static readonly Regex IfscRe = new(@"^[A-Z]{4}0[A-Z0-9]{6}$", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex Alpha3Re = new(@"[A-Za-z]{3,}", RegexOptions.Compiled);
    private static readonly Regex MultiSpaceRe = new(@"\s+", RegexOptions.Compiled);

    private static readonly (Regex regex, string reqType, string ledger, double conf)[] CompiledRulePriors = RulePriors
        .Select(r => (new Regex(r.pattern, RegexOptions.IgnoreCase | RegexOptions.Compiled), r.reqType, r.ledger, r.conf))
        .ToArray();

    private static readonly (string narr, string ttype, string vtype, string ledger)[] BuiltinSeeds =
    [
        ("SMS ALERT CHARGES Q1 FY26", "DR", "Payment", "Bank Charges"),
        ("NEFT RTGS IMPS TRANSACTION CHARGES", "DR", "Payment", "Bank Charges"),
        ("CHEQUE RETURN CHARGES ECS BOUNCE", "DR", "Payment", "Bank Charges"),
        ("DEBIT CARD ANNUAL MAINTENANCE AMC CHG", "DR", "Payment", "Bank Charges"),
        ("MIN BAL NON MAINTENANCE CHARGES AMB QAB", "DR", "Payment", "Bank Charges"),
        ("FOLIO CHARGES SERVICE CHG GST", "DR", "Payment", "Bank Charges"),
        ("INT.PD SAVINGS ACCOUNT CREDIT INTEREST", "CR", "Receipt", "Interest Received"),
        ("CREDIT INTEREST CAPITALISED SB", "CR", "Receipt", "Interest Received"),
        ("SB INT CREDIT FOR QUARTER", "CR", "Receipt", "Interest Received"),
        ("INT FROM SB ACCOUNT", "CR", "Receipt", "Interest Received"),
        ("FD INTEREST CREDIT MATURITY", "CR", "Receipt", "Interest Received"),
        ("OD INTEREST DEBIT CC LOAN INTEREST", "DR", "Payment", "Interest Paid"),
        ("UPI/DR/TPCODL ELECTRICITY BILL PAYMENT", "DR", "Payment", "Electricity Expenses"),
        ("BBPS ELECTRICITY BILL BESCOM TATA POWER", "DR", "Payment", "Electricity Expenses"),
        ("NEFT MSEDCL BSES ADANI ELECTRICITY", "DR", "Payment", "Electricity Expenses"),
        ("UPI/DR/AIRTEL POSTPAID BROADBAND BILL", "DR", "Payment", "Telephone & Internet Expenses"),
        ("UPI/DR/JIO FIBER RECHARGE TELECOM", "DR", "Payment", "Telephone & Internet Expenses"),
        ("BSNL ACT FIBERNET INTERNET BILL", "DR", "Payment", "Telephone & Internet Expenses"),
        ("NEFT OFFICE RENT MONTHLY LEASE", "DR", "Payment", "Rent Expense"),
        ("UPI/DR/GODOWN SHOP RENT PAYMENT", "DR", "Payment", "Rent Expense"),
        ("NEFT STAFF SALARY PAYROLL APRIL", "DR", "Payment", "Salaries & Wages"),
        ("IMPS WAGES BONUS STAFF SALARIES", "DR", "Payment", "Salaries & Wages"),
        ("UPI/DR/AMAZON OFFICE SUPPLIES PURCHASE", "DR", "Payment", "Office Expenses"),
        ("UPI/DR/FLIPKART PANTRY TEA COFFEE OFFICE", "DR", "Payment", "Office Expenses"),
        ("UPI/DR/SWIGGY ZOMATO STAFF REFRESHMENT", "DR", "Payment", "Office Expenses"),
        ("UPI/DR/IRCTC RAIL TICKET BOOKING", "DR", "Payment", "Travelling & Conveyance"),
        ("POS INDIGO AIR INDIA FLIGHT TICKET", "DR", "Payment", "Travelling & Conveyance"),
        ("UPI/DR/UBER OLA RAPIDO CAB AUTO", "DR", "Payment", "Travelling & Conveyance"),
        ("MAKEMYTRIP GOIBIBO HOTEL STAY TRAVEL", "DR", "Payment", "Travelling & Conveyance"),
        ("UPI/DR/STATIONERY PRINTING XEROX PAPER", "DR", "Payment", "Printing & Stationery"),
        ("UPI/DR/DTDC BLUEDART DELHIVERY COURIER", "DR", "Payment", "Courier & Postage"),
        ("NEFT VRL LOGISTICS FREIGHT CARTAGE", "DR", "Payment", "Freight & Cartage"),
        ("UPI/DR/AC SERVICE COMPUTER REPAIR MAINT", "DR", "Payment", "Repairs & Maintenance"),
        ("POS AWS GOOGLE CLOUD MICROSOFT 365", "DR", "Payment", "Software & Subscriptions"),
        ("UPI/DR/ZOHO TALLY SOLUTIONS RENEWAL", "DR", "Payment", "Software & Subscriptions"),
        ("NEFT CA AUDIT FEES TAX CONSULTANCY", "DR", "Payment", "Professional & Legal Fees"),
        ("NEFT ADVOCATE LEGAL RETAINER FEE", "DR", "Payment", "Professional & Legal Fees"),
        ("POS GOOGLE ADS META FACEBOOK MARKETING", "DR", "Payment", "Advertising & Marketing"),
        ("UPI/DR/HPCL BPCL IOCL PETROL PUMP FUEL", "DR", "Payment", "Fuel & Vehicle Expenses"),
        ("UPI/DR/FASTAG NHAI TOLL RECHARGE", "DR", "Payment", "Fuel & Vehicle Expenses"),
        ("NEFT LIC HDFC ERGO INSURANCE PREMIUM", "DR", "Payment", "Insurance Expenses"),
        ("GSTN CBIC GST CHALLAN PMT-06 PAYMENT", "DR", "Payment", "GST Payable"),
        ("NSDL TRACES TDS CHALLAN 281 PAYMENT", "DR", "Payment", "TDS Payable"),
        ("INCOME TAX ADVANCE TAX CHALLAN 280 OLTAS", "DR", "Payment", "Income Tax / Advance Tax"),
        ("NEFT EPFO ESIC PROVIDENT FUND CHALLAN", "DR", "Payment", "EPF & ESIC Payable"),
        ("NEFT CR CUSTOMER SALES INVOICE RECEIPT", "CR", "Receipt", "Sales Account"),
        ("UPI/CR/POS SETTLEMENT MERCHANT SALES", "CR", "Receipt", "Sales Account"),
        ("NEFT SUPPLIER MATERIAL PURCHASE BILL", "DR", "Payment", "Purchase Account"),
        ("UPI/DR/PROPRIETOR DRAWINGS PERSONAL", "DR", "Payment", "Drawings Account"),
    ];

    public LedgerClassifier(DatabaseService db)
    {
        _db = db;
    }

    public void Initialize()
    {
        if (!_db.HasSeedSource(SeedMarker))
        {
            _db.AddTrainingExamples(BuiltinSeeds.Select(s =>
                (s.narr, Normalize(s.narr, s.ttype), "", s.ttype, s.vtype, s.ledger, SeedMarker, "")));
        }
        Retrain();
    }

    public static string Normalize(string narration, string txnType = "")
    {
        var s = PunctRe.Replace(narration.ToLowerInvariant(), " ");
        s = LongNumRe.Replace(s, " ");
        var tokens = new List<string>();
        foreach (Match m in WordRe.Matches(s))
        {
            var t = m.Value;
            if (Stopwords.Contains(t)) continue;
            tokens.Add(t);
            if (Abbreviations.TryGetValue(t, out var exps))
                foreach (var e in exps) if (e != t && !Stopwords.Contains(e)) tokens.Add(e);
        }
        if (!string.IsNullOrEmpty(txnType)) tokens.Add($"txntype_{txnType.ToLowerInvariant()}");
        return string.Join(" ", tokens);
    }

    public static string ExtractCounterpartyKey(string narration)
    {
        var u = narration.Trim();
        var parts = SlashSplitRe.Split(u).Select(p => p.Trim()).Where(p => p.Length > 0).ToArray();
        if (u.StartsWith("UPI", StringComparison.OrdinalIgnoreCase))
        {
            var vpa = parts.FirstOrDefault(p => p.Contains('@'));
            if (vpa != null) return vpa.ToLowerInvariant();
        }
        if (u.StartsWith("UPI", StringComparison.OrdinalIgnoreCase) || u.Contains("NEFT", StringComparison.OrdinalIgnoreCase) || u.Contains("IMPS", StringComparison.OrdinalIgnoreCase) || u.Contains("RTGS", StringComparison.OrdinalIgnoreCase))
        {
            foreach (var p in parts.Skip(1))
            {
                if (IfscRe.IsMatch(p)) continue;
                if (p.Length >= 10 && p.Count(char.IsDigit) >= 6) continue;
                if (Alpha3Re.IsMatch(p) && p.ToUpperInvariant() is not (
                    "DR" or "CR" or "P2A" or "P2M" or "P2P" or "UPI" or "NEFT" or "RTGS" or "IMPS"
                    or "IPO" or "INFT" or "BIL" or "ACH" or "NACH" or "ECS" or "CHQ" or "ATM" or "POS"
                    or "REV" or "REFUND" or "MOB" or "NET" or "WEB" or "APP" or "TXN" or "TRF" or "FT"
                    or "PAY" or "INT" or "CHG" or "FEE" or "CMS" or "MMT" or "CLG"))
                    return MultiSpaceRe.Replace(p.ToLowerInvariant(), " ").Trim();
            }
        }
        var normWords = Normalize(narration).Split(' ', StringSplitOptions.RemoveEmptyEntries).Where(w => !w.StartsWith("txntype_")).Take(3);
        return string.Join(" ", normWords);
    }

    private static readonly Regex AlphaSeqRe = new(@"[a-z]+", RegexOptions.Compiled);
    private static readonly Regex RmRe = new(@"\br\s*[&/]\s*m\b", RegexOptions.Compiled);
    private static readonly HashSet<string> LedgerNoiseWords = new(StringComparer.OrdinalIgnoreCase)
        { "expenses", "expense", "account", "charges", "charge", "payable", "from", "and", "the", "for", "of", "on", "to", "by", "in" };
    private static readonly ConcurrentDictionary<string, (HashSet<string> full, HashSet<string> core)> LedgerTokenCache = new(StringComparer.OrdinalIgnoreCase);

    private static HashSet<string> ExpandTokens(string text)
    {
        var low = text.ToLowerInvariant();
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (Match m in AlphaSeqRe.Matches(low))
        {
            var w = m.Value;
            if (w.Length < 2 && w is not ("r" or "m")) continue;
            set.Add(w);
            if (Abbreviations.TryGetValue(w, out var exps)) foreach (var e in exps) set.Add(e);
        }
        if (RmRe.IsMatch(low)) { set.Add("repairs"); set.Add("maintenance"); }
        return set;
    }

    private static (HashSet<string> full, HashSet<string> core) GetCachedLedgerTokens(string ledgerName)
    {
        // Narrations are also passed through here; cap the cache so a long session cannot grow it without bound
        if (LedgerTokenCache.Count > 50_000) LedgerTokenCache.Clear();
        return LedgerTokenCache.GetOrAdd(ledgerName, static name =>
        {
            var full = ExpandTokens(name);
            var core = new HashSet<string>(full.Where(t => !LedgerNoiseWords.Contains(t)), StringComparer.OrdinalIgnoreCase);
            if (core.Count == 0) core = full;
            return (full, core);
        });
    }

    public static (string matched, double score) MatchExistingTallyLedger(string canonical, string narration, IList<string>? availableLedgers)
    {
        if (availableLedgers == null || availableLedgers.Count == 0) return (canonical, 0);
        for (int i = 0; i < availableLedgers.Count; i++)
            if (availableLedgers[i].Equals(canonical, StringComparison.OrdinalIgnoreCase))
                return (availableLedgers[i], 1.0);

        var (_, coreCanon) = GetCachedLedgerTokens(canonical);
        var narrCore = ExpandTokens(narration);
        narrCore.ExceptWith(LedgerNoiseWords);

        string bestAv = canonical;
        double bestScore = 0;

        foreach (var av in availableLedgers)
        {
            var (avTokens, avCore) = GetCachedLedgerTokens(av);
            if (coreCanon.Contains("received") && avTokens.Contains("paid") && !avTokens.Contains("received")) continue;
            if (coreCanon.Contains("paid") && avTokens.Contains("received") && !avTokens.Contains("paid")) continue;

            double hits = avCore.Count(t => coreCanon.Contains(t));
            foreach (var t in avCore)
            {
                if (coreCanon.Contains(t)) continue;
                if (t.Length >= 3 && coreCanon.Any(c => c.Length >= 3 && (c.StartsWith(t, StringComparison.OrdinalIgnoreCase) || t.StartsWith(c, StringComparison.OrdinalIgnoreCase))))
                    hits += 0.85;
            }
            if (hits <= 0) continue;

            double avCov = hits / Math.Max(avCore.Count, 1);
            double canCov = hits / Math.Max(coreCanon.Count, 1);
            double narrBonus = Math.Min(0.25, 0.12 * avCore.Count(t => narrCore.Contains(t)));
            double score = 0.60 * avCov + 0.35 * canCov + narrBonus;
            if (score > bestScore) { bestScore = score; bestAv = av; }
        }
        return bestScore >= 0.45 ? (bestAv, Math.Min(0.98, bestScore)) : (canonical, 0);
    }

    private static List<string> Tokenize(string norm)
    {
        var words = norm.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var list = new List<string>(words.Length * 2);
        list.AddRange(words);
        for (int i = 0; i < words.Length - 1; i++) list.Add($"{words[i]}_{words[i + 1]}");
        return list;
    }

    /// <summary>Checks if another office PC added new ML or Parent Group learnings to the shared server DB and reloads automatically.</summary>
    public bool SyncFromServerIfUpdated()
    {
        var (mlId, pgId) = _db.GetMlWatermark();
        if (mlId != _lastMlId || pgId != _lastPgId)
        {
            Retrain();
            return true;
        }
        return false;
    }

    public void Retrain()
    {
        var examples = _db.GetAllTrainingExamples();
        var (wmMl, wmPg) = _db.GetMlWatermark();
        var newCpMap = new Dictionary<string, Dictionary<string, int>>(StringComparer.OrdinalIgnoreCase);
        var newUserTokMap = new Dictionary<string, Dictionary<string, int>>(StringComparer.OrdinalIgnoreCase);
        var newCompCpMap = new Dictionary<string, Dictionary<string, int>>(StringComparer.OrdinalIgnoreCase);
        var newCompTokMap = new Dictionary<string, Dictionary<string, int>>(StringComparer.OrdinalIgnoreCase);
        RetrainParentGroups();
        if (examples.Count == 0)
        {
            lock (_modelLock)
            {
                SampleCount = 0;
                _lastMlId = wmMl;
                _lastPgId = wmPg;
                _counterpartyMap = newCpMap;
                _userVendorTokenMap = newUserTokMap;
                _companyCounterpartyMap = newCompCpMap;
                _companyVendorTokenMap = newCompTokMap;
                _classes = [];
                _vocab = new();
                _idf = [];
                _classLogPrior = new();
                _classTf = new();
                _classDenom = new();
                _classCentroids = new();
            }
            return;
        }

        var docs = new List<List<string>>(examples.Count);
        var labels = new List<string>(examples.Count);
        var weights = new List<double>(examples.Count);
        var df = new Dictionary<string, int>();

        foreach (var ex in examples)
        {
            bool isSeed = ex.source.StartsWith("builtin_seed", StringComparison.OrdinalIgnoreCase);
            double w = isSeed ? 1.0 : 5.0;
            if (!isSeed)
            {
                var comp = (ex.companyName ?? "").Trim();
                if (!string.IsNullOrEmpty(ex.cpKey))
                {
                    var k = $"{ex.cpKey}|{ex.txnType}";
                    if (!newCpMap.TryGetValue(k, out var d)) newCpMap[k] = d = new(StringComparer.OrdinalIgnoreCase);
                    d[ex.ledger] = d.GetValueOrDefault(ex.ledger) + 1;
                    if (!string.IsNullOrEmpty(comp))
                    {
                        var ck = $"{comp}|{k}";
                        if (!newCompCpMap.TryGetValue(ck, out var cd)) newCompCpMap[ck] = cd = new(StringComparer.OrdinalIgnoreCase);
                        cd[ex.ledger] = cd.GetValueOrDefault(ex.ledger) + 1;
                    }
                }
                foreach (var vTok in ex.normalized.Split(' ', StringSplitOptions.RemoveEmptyEntries))
                {
                    if (vTok.Length < 4 || vTok.StartsWith("txntype_") || Stopwords.Contains(vTok)) continue;
                    var tk = $"{vTok}|{ex.txnType}";
                    if (!newUserTokMap.TryGetValue(tk, out var td)) newUserTokMap[tk] = td = new(StringComparer.OrdinalIgnoreCase);
                    td[ex.ledger] = td.GetValueOrDefault(ex.ledger) + 1;
                    if (!string.IsNullOrEmpty(comp))
                    {
                        var ctk = $"{comp}|{tk}";
                        if (!newCompTokMap.TryGetValue(ctk, out var ctd)) newCompTokMap[ctk] = ctd = new(StringComparer.OrdinalIgnoreCase);
                        ctd[ex.ledger] = ctd.GetValueOrDefault(ex.ledger) + 1;
                    }
                }
            }
            var toks = Tokenize(ex.normalized);
            docs.Add(toks);
            labels.Add(ex.ledger);
            weights.Add(w);
            foreach (var t in toks.Distinct()) df[t] = df.GetValueOrDefault(t) + 1;
        }

        var sortedVocab = df.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        var newVocab = sortedVocab.Select((t, i) => (t, i)).ToDictionary(x => x.t, x => x.i);
        int nDocs = docs.Count, nFeats = sortedVocab.Count;
        var newIdf = sortedVocab.Select(t => Math.Log((1.0 + nDocs) / (1.0 + df[t])) + 1.0).ToArray();

        var classCounts = labels.GroupBy(l => l).ToDictionary(g => g.Key, g => g.Count());
        var newClasses = classCounts.Keys.OrderBy(k => k, StringComparer.Ordinal).ToList();
        var tfSum = newClasses.ToDictionary(c => c, _ => new Dictionary<int, double>());
        var vecSum = newClasses.ToDictionary(c => c, _ => new Dictionary<int, double>());
        var wSum = newClasses.ToDictionary(c => c, _ => 0.0);

        for (int i = 0; i < nDocs; i++)
        {
            var vec = new Dictionary<int, double>();
            foreach (var t in docs[i]) if (newVocab.TryGetValue(t, out int idx)) vec[idx] = vec.GetValueOrDefault(idx) + 1.0;
            double normSq = 0;
            foreach (var j in vec.Keys.ToList()) { vec[j] *= newIdf[j]; normSq += vec[j] * vec[j]; }
            double norm = Math.Sqrt(normSq);
            var c = labels[i];
            var w = weights[i];
            var tfArr = tfSum[c];
            var vArr = vecSum[c];
            foreach (var (j, val) in vec)
            {
                if (val == 0) continue;
                tfArr[j] = tfArr.GetValueOrDefault(j) + val * w;
                vArr[j] = vArr.GetValueOrDefault(j) + (norm > 0 ? val / norm : val) * w;
            }
            wSum[c] += w;
        }

        var newClassLogPrior = new Dictionary<string, double>();
        var newClassTf = new Dictionary<string, Dictionary<int, double>>();
        var newClassDenom = new Dictionary<string, double>();
        var newClassCentroids = new Dictionary<string, Dictionary<int, double>>();
        foreach (var c in newClasses)
        {
            newClassLogPrior[c] = Math.Log((double)classCounts[c] / nDocs);
            newClassTf[c] = tfSum[c];
            newClassDenom[c] = tfSum[c].Values.Sum() + 0.5 * nFeats;
            double divisor = Math.Max(wSum[c], 1.0);
            var cent = vecSum[c].ToDictionary(kv => kv.Key, kv => kv.Value / divisor);
            double cn = Math.Sqrt(cent.Values.Sum(v => v * v));
            newClassCentroids[c] = cn > 0 ? cent.ToDictionary(kv => kv.Key, kv => kv.Value / cn) : cent;
        }

        lock (_modelLock)
        {
            SampleCount = examples.Count;
            _lastMlId = wmMl;
            _lastPgId = wmPg;
            _counterpartyMap = newCpMap;
            _userVendorTokenMap = newUserTokMap;
            _companyCounterpartyMap = newCompCpMap;
            _companyVendorTokenMap = newCompTokMap;
            _vocab = newVocab;
            _idf = newIdf;
            _classes = newClasses;
            _classLogPrior = newClassLogPrior;
            _classTf = newClassTf;
            _classDenom = newClassDenom;
            _classCentroids = newClassCentroids;
        }
    }

    public (string ledger, double confidence, string source) Predict(string narration, string txnType, IList<string>? availableLedgers = null, string companyName = "")
    {
        var norm = Normalize(narration, txnType);
        var cpKey = ExtractCounterpartyKey(narration);
        var comp = (companyName ?? "").Trim();
        var candidates = new List<(string ledger, double conf, string src)>();

        lock (_modelLock)
        {
            // 1. Same-company counterparty memory takes top priority over cross-company office memory
            if (!string.IsNullOrEmpty(comp) && !string.IsNullOrEmpty(cpKey) &&
                _companyCounterpartyMap.TryGetValue($"{comp}|{cpKey}|{txnType}", out var compCpDict))
            {
                int tot = compCpDict.Values.Sum();
                var top = compCpDict.OrderByDescending(kv => kv.Value).First();
                double conf = Math.Min(0.99, 0.93 + 0.03 * Math.Min(top.Value, 2) * ((double)top.Value / tot));
                candidates.Add((top.Key, conf, "company_party_memory"));
            }
            else if (!string.IsNullOrEmpty(cpKey) && _counterpartyMap.TryGetValue($"{cpKey}|{txnType}", out var cpDict))
            {
                int tot = cpDict.Values.Sum();
                var top = cpDict.OrderByDescending(kv => kv.Value).First();
                var (mapped, _) = MatchExistingTallyLedger(top.Key, narration, availableLedgers);
                double conf = Math.Min(0.95, 0.86 + 0.04 * Math.Min(top.Value, 3) * ((double)top.Value / tot));
                candidates.Add((mapped, conf, "learned_party_memory"));
            }

            // 2. Same-company vendor tokens first, then shared office vendor tokens
            var compVendorVotes = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
            var globalVendorVotes = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase);
            foreach (var tok in norm.Split(' ', StringSplitOptions.RemoveEmptyEntries).Distinct())
            {
                if (tok.Length < 4 || tok.StartsWith("txntype_")) continue;
                if (!string.IsNullOrEmpty(comp) && _companyVendorTokenMap.TryGetValue($"{comp}|{tok}|{txnType}", out var ctd))
                {
                    int tTot = ctd.Values.Sum();
                    foreach (var (lName, cnt) in ctd)
                    {
                        double purity = (double)cnt / tTot;
                        if (purity >= 0.6) compVendorVotes[lName] = compVendorVotes.GetValueOrDefault(lName) + purity;
                    }
                }
                if (_userVendorTokenMap.TryGetValue($"{tok}|{txnType}", out var td))
                {
                    int tTot = td.Values.Sum();
                    foreach (var (lName, cnt) in td)
                    {
                        double purity = (double)cnt / tTot;
                        if (purity >= 0.6) globalVendorVotes[lName] = globalVendorVotes.GetValueOrDefault(lName) + purity;
                    }
                }
            }
            if (compVendorVotes.Count > 0)
            {
                var topV = compVendorVotes.OrderByDescending(kv => kv.Value).First();
                double vConf = Math.Min(0.98, 0.91 + 0.04 * Math.Min(topV.Value, 2));
                candidates.Add((topV.Key, vConf, "company_user_ml"));
            }
            else if (globalVendorVotes.Count > 0)
            {
                var topV = globalVendorVotes.OrderByDescending(kv => kv.Value).First();
                var (mapped, _) = MatchExistingTallyLedger(topV.Key, narration, availableLedgers);
                double vConf = Math.Min(0.94, 0.84 + 0.05 * Math.Min(topV.Value, 2));
                candidates.Add((mapped, vConf, "learned_user_ml"));
            }
        }

        List<string> snapClasses;
        Dictionary<string, int> snapVocab;
        double[] snapIdf;
        Dictionary<string, double> snapLogPrior;
        Dictionary<string, Dictionary<int, double>> snapTf;
        Dictionary<string, double> snapDenom;
        Dictionary<string, Dictionary<int, double>> snapCentroids;
        lock (_modelLock)
        {
            snapClasses = _classes;
            snapVocab = _vocab;
            snapIdf = _idf;
            snapLogPrior = _classLogPrior;
            snapTf = _classTf;
            snapDenom = _classDenom;
            snapCentroids = _classCentroids;
        }

        if (snapClasses.Count > 0 && snapVocab.Count > 0)
        {
            var vec = new Dictionary<int, double>();
            foreach (var t in Tokenize(norm)) if (snapVocab.TryGetValue(t, out int idx)) vec[idx] = vec.GetValueOrDefault(idx) + 1.0;
            if (vec.Count > 0)
            {
                double normSq = 0;
                foreach (var j in vec.Keys.ToList()) { vec[j] *= snapIdf[j]; normSq += vec[j] * vec[j]; }
                double nrm = Math.Sqrt(normSq);
                var nb = new Dictionary<string, double>();
                var cos = new Dictionary<string, double>();
                foreach (var c in snapClasses)
                {
                    double nbScore = snapLogPrior[c], cosScore = 0;
                    var tf = snapTf[c];
                    var cent = snapCentroids[c];
                    double denom = snapDenom[c];
                    foreach (var (j, val) in vec)
                    {
                        nbScore += val * Math.Log((tf.GetValueOrDefault(j) + 0.5) / denom);
                        cosScore += (nrm > 0 ? val / nrm : val) * cent.GetValueOrDefault(j);
                    }
                    nb[c] = nbScore;
                    cos[c] = Math.Max(0, cosScore);
                }
                double maxNb = nb.Values.Max();
                var expNb = nb.ToDictionary(kv => kv.Key, kv => Math.Exp(kv.Value - maxNb));
                double sumExp = expNb.Values.Sum();
                var best = snapClasses.Select(c => (c, score: 0.55 * (expNb[c] / sumExp) + 0.45 * cos[c]))
                    .OrderByDescending(x => x.score).First();
                if (best.score >= 0.25)
                {
                    var (mapped, msc) = MatchExistingTallyLedger(best.c, narration, availableLedgers);
                    candidates.Add((mapped, Math.Min(0.96, best.score), mapped != best.c && msc > 0 ? "ml_tally_shortform" : "ml_model"));
                }
            }
        }

        if (availableLedgers is { Count: > 0 })
        {
            var (dl, dsc) = MatchExistingTallyLedger(narration, narration, availableLedgers);
            if (dsc >= 0.65) candidates.Add((dl, Math.Min(0.89, dsc), "tally_shortform_match"));
        }

        foreach (var (rx, reqType, ledger, conf) in CompiledRulePriors)
        {
            if (reqType != "ANY" && reqType != txnType) continue;
            if (rx.IsMatch(narration))
            {
                var (mapped, _) = MatchExistingTallyLedger(ledger, narration, availableLedgers);
                candidates.Add((mapped, conf, "rule_prior"));
                break;
            }
        }

        // "Sundry Debtors" is a Tally GROUP, not a ledger: posting to it failed (or tried to create a ledger with a group's name)
        var fallback = "Suspense Account";
        var (fbMapped, _) = MatchExistingTallyLedger(fallback, narration, availableLedgers);
        candidates.Add((fbMapped, 0.35, "fallback"));

        var winner = candidates.OrderByDescending(c => c.conf).First();
        return (winner.ledger, Math.Round(winner.conf, 3), winner.src);
    }


    public void RetrainParentGroups()
    {
        var newExact = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        var newTok = new Dictionary<string, Dictionary<string, int>>(StringComparer.OrdinalIgnoreCase);
        foreach (var (lName, pGroup) in _db.GetAllParentGroupExamples())
        {
            newExact[lName.Trim()] = pGroup.Trim();
            foreach (var tok in ExpandTokens(lName))
            {
                if (tok.Length < 3) continue;
                if (!newTok.TryGetValue(tok, out var d))
                    newTok[tok] = d = new(StringComparer.OrdinalIgnoreCase);
                d[pGroup.Trim()] = d.GetValueOrDefault(pGroup.Trim()) + 1;
            }
        }
        lock (_modelLock)
        {
            _exactParentGroupMap = newExact;
            _parentGroupTokenMap = newTok;
        }
    }

    public void LearnParentGroups(IEnumerable<MissingLedgerItem> createdLedgers)
    {
        var items = createdLedgers
            .Where(m => !string.IsNullOrWhiteSpace(m.Name) && !string.IsNullOrWhiteSpace(m.ParentGroup))
            .Select(m => (m.Name.Trim(), m.ParentGroup.Trim()))
            .ToList();
        if (items.Count > 0)
        {
            _db.AddParentGroupExamples(items);
            RetrainParentGroups();
        }
    }

    public string PredictParentGroup(string ledgerName, string voucherType, string txnType, bool isBank)
    {
        var clean = ledgerName.Trim();
        var scores = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        lock (_modelLock)
        {
            if (_exactParentGroupMap.TryGetValue(clean, out var exact))
                return exact;
            foreach (var tok in ExpandTokens(clean))
            {
                if (_parentGroupTokenMap.TryGetValue(tok, out var d))
                    foreach (var (pg, cnt) in d)
                        scores[pg] = scores.GetValueOrDefault(pg) + cnt;
            }
        }
        if (scores.Count > 0)
            return scores.OrderByDescending(kv => kv.Value).First().Key;

        return TallyConnector.SuggestParentGroup(clean, voucherType, txnType, isBank);
    }

    /// <summary>Instant <1ms in-memory ML update for zero-lag UI cascading over slow SMB shares; persists to server SQLite in background.</summary>
    public void LearnInstantAndSaveInBackground(BankTransactionRow row, string companyName = "")
    {
        if (string.IsNullOrWhiteSpace(row.SelectedLedger) || row.VoucherType == "Contra") return;
        var mlNarr = string.IsNullOrWhiteSpace(row.OriginalNarration) ? row.Narration : row.OriginalNarration;
        var norm = Normalize(mlNarr, row.TxnType);
        var cpKey = ExtractCounterpartyKey(mlNarr);
        var ledger = row.SelectedLedger.Trim();
        var comp = (companyName ?? "").Trim();

        lock (_modelLock)
        {
            static void BoostWinner(Dictionary<string, int> dict, string targetLedger)
            {
                int cur = dict.GetValueOrDefault(targetLedger);
                int maxOther = dict.Where(kv => !kv.Key.Equals(targetLedger, StringComparison.OrdinalIgnoreCase)).Select(kv => kv.Value).DefaultIfEmpty(0).Max();
                dict[targetLedger] = Math.Max(cur + 1, maxOther + 1);
            }
            if (!string.IsNullOrEmpty(cpKey))
            {
                var k = $"{cpKey}|{row.TxnType}";
                if (!_counterpartyMap.TryGetValue(k, out var d)) _counterpartyMap[k] = d = new(StringComparer.OrdinalIgnoreCase);
                BoostWinner(d, ledger);
                if (!string.IsNullOrEmpty(comp))
                {
                    var ck = $"{comp}|{k}";
                    if (!_companyCounterpartyMap.TryGetValue(ck, out var cd)) _companyCounterpartyMap[ck] = cd = new(StringComparer.OrdinalIgnoreCase);
                    BoostWinner(cd, ledger);
                }
            }
            foreach (var vTok in norm.Split(' ', StringSplitOptions.RemoveEmptyEntries))
            {
                if (vTok.Length < 4 || vTok.StartsWith("txntype_") || Stopwords.Contains(vTok)) continue;
                var tk = $"{vTok}|{row.TxnType}";
                if (!_userVendorTokenMap.TryGetValue(tk, out var td)) _userVendorTokenMap[tk] = td = new(StringComparer.OrdinalIgnoreCase);
                td[ledger] = td.GetValueOrDefault(ledger) + 1;
                if (!string.IsNullOrEmpty(comp))
                {
                    var ctk = $"{comp}|{tk}";
                    if (!_companyVendorTokenMap.TryGetValue(ctk, out var ctd)) _companyVendorTokenMap[ctk] = ctd = new(StringComparer.OrdinalIgnoreCase);
                    ctd[ledger] = ctd.GetValueOrDefault(ledger) + 1;
                }
            }
            SampleCount++;
        }

        var tType = row.TxnType;
        var vType = row.VoucherType;
        var hash = row.TxnHash ?? "";
        // Saves run one after another (never in parallel), so two quick edits of the same row are stored in order and
        // the per-transaction de-duplication always keeps the LAST ledger chosen.
        lock (_saveChainLock)
        {
            _saveChain = _saveChain.ContinueWith(_ =>
            {
                try
                {
                    _db.AddTrainingExamplesForTxns([(mlNarr, norm, cpKey, tType, vType, ledger, "user_review", comp, hash)]);
                    // Do NOT advance the sync watermark here: other office PCs may have added learnings in the meantime, and
                    // skipping the watermark forward hid them until the next change.
                }
                catch { }
            }, TaskScheduler.Default);
        }
    }

    private readonly object _saveChainLock = new();
    private Task _saveChain = Task.CompletedTask;

    /// <summary>
    /// Waits until every background ML save has reached the database. Called when the app closes (so the last edits are
    /// never lost) and by tests before they delete their temporary database.
    /// </summary>
    public bool FlushPendingSaves(TimeSpan timeout)
    {
        Task pending;
        lock (_saveChainLock) pending = _saveChain;
        try { return pending.Wait(timeout); }
        catch { return false; }
    }

    public int LearnFromRows(IEnumerable<BankTransactionRow> rows, string companyName = "")
    {
        var comp = (companyName ?? "").Trim();
        var items = rows
            .Where(r => !string.IsNullOrWhiteSpace(r.SelectedLedger) && r.VoucherType != "Contra")
            .Select(r => { var mlNarr = string.IsNullOrWhiteSpace(r.OriginalNarration) ? r.Narration : r.OriginalNarration; return (mlNarr, Normalize(mlNarr, r.TxnType), ExtractCounterpartyKey(mlNarr), r.TxnType, r.VoucherType, r.SelectedLedger.Trim(), "user_review", comp, r.TxnHash ?? ""); })
            .ToList();
        int written = 0;
        if (items.Count > 0)
        {
            // Rows already learned with the same ledger (same transaction hash) are skipped — see AddTrainingExamplesForTxns
            written = _db.AddTrainingExamplesForTxns(items);
            if (written > 0) Retrain();
        }
        return written;
    }
}
