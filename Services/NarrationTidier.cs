using System.Globalization;
using System.Text.RegularExpressions;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Builds a short "Party • Mode • Ref" line from a bank narration, e.g.
/// "UPI/DR/412345678901/RAMESH KUMAR/SBIN/ramesh@oksbi/Payment" → "Ramesh Kumar • UPI • 412345678901".
/// The original narration is never changed; the short line is only added on top of it (when the setting is on).
/// Returns "" when no party can be found — the original alone is then used.
/// </summary>
public static class NarrationTidier
{
    private static readonly Regex SplitRe = new(@"[/\-:|*,]+|\s{2,}", RegexOptions.Compiled);
    private static readonly Regex IfscRe = new(@"^[A-Z]{4}0[A-Z0-9]{6}$", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex LettersRe = new(@"[A-Za-z]", RegexOptions.Compiled);
    private static readonly Regex NachRe = new(@"\b(NACH|ECS|ACH)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex ChargesRe = new(@"\b(CHGS?|CHRGS?|CHARGES?|FEES?|GST|SMS ALERT|AMC)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex InterestRe = new(@"\b(INT\.?\s*PD|INTEREST|INT\s+CREDIT|INT\.?CR)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CardRe = new(@"\b(POS|ECOM|DEBIT CARD|VISA|MASTERCARD|RUPAY)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>Words that are never the party (bank/mode jargon).</summary>
    private static readonly HashSet<string> Jargon = new(StringComparer.OrdinalIgnoreCase)
    {
        "UPI", "NEFT", "RTGS", "IMPS", "DR", "CR", "P2A", "P2M", "P2P", "IPO", "INFT", "BIL", "ACH", "NACH", "ECS", "CHQ",
        "CHEQUE", "ATM", "POS", "REV", "REFUND", "MOB", "NET", "WEB", "APP", "TXN", "TRF", "FT", "PAY", "PAYMENT", "INT",
        "CHG", "CHGS", "FEE", "CMS", "MMT", "CLG", "TO", "BY", "FROM", "TRANSFER", "INB", "IB", "BIB", "DEP", "CASH",
        "WDL", "WITHDRAWAL", "DEPOSIT", "SENT", "RECEIVED", "USING", "VIA", "ONLINE", "ACCOUNT", "AC", "NA",
        "OTHERS", "OTHER", "UPIINTENT", "COLLECT", "PAID", "RECD", "INWARD", "OUTWARD", "REMITTANCE", "MANDATE",
        "SELF", "OK", "YES", "NO", "REF", "UTR", "NO.", "MB", "SI", "MICR", "CTS", "ONL", "NETBANK", "OWN", "MR", "MR.",
        "MRS", "MRS.", "MS", "MS.", "SHRI", "SMT", "M/S", "ALERT", "CREDIT", "DEBIT", "CLEARING", "PHONEPE", "GPAY"
    };

    /// <summary>Kept in capitals when a name is title-cased.</summary>
    private static readonly HashSet<string> Acronyms = new(StringComparer.OrdinalIgnoreCase)
    {
        "HDFC", "SBI", "ICICI", "IDBI", "IDFC", "LIC", "GST", "TDS", "EMI", "BSNL", "IRCTC", "NSDL", "CBDT", "EPFO", "ESIC",
        "NPS", "PNB", "BOB", "UCO", "RBL", "AU", "HUF", "LLP", "KYC", "MSEB", "BESCOM", "TNEB", "ONGC", "IOCL", "HPCL", "BPCL"
    };

    /// <summary>Skipped when they stand alone, kept inside a name: bank codes (first 4 letters of an IFSC) and words such as
    /// BANK / LTD ("HDFC Life", "Sharma Traders Pvt Ltd").</summary>
    private static readonly HashSet<string> BankCodes = new(StringComparer.OrdinalIgnoreCase)
    {
        "BANK", "LTD", "THE", "PVT", "LIMITED",
        "SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "BARB", "CNRB", "KKBK", "YESB", "IDIB", "UBIN", "IOBA", "BKID", "MAHB",
        "INDB", "FDRL", "IDFB", "AUBL", "CBIN", "UCBA", "PSIB", "KARB", "SIBL", "CSBK", "RATN", "BDBL", "IBKL"
    };

    public static string Tidy(string narration, string paymentMode, string refNo)
    {
        if (string.IsNullOrWhiteSpace(narration)) return "";
        var mode = ModeLabel(narration, paymentMode);
        // cash, interest and bank charges have no party: the bank's own text says it best
        if (mode is "Cash" or "Interest" or "Bank charges") return "";
        var party = FindParty(narration);
        if (party.Length == 0) return "";
        var parts = new List<string> { party };
        if (mode.Length > 0) parts.Add(mode);
        var r = (refNo ?? "").Trim();
        if (r.Length > 0) parts.Add(r);
        return string.Join(" • ", parts);
    }

    private static string ModeLabel(string narr, string paymentMode)
    {
        if (InterestRe.IsMatch(narr)) return "Interest";
        if (NachRe.IsMatch(narr)) return "NACH";
        switch (paymentMode)
        {
            case "UPI": case "NEFT": case "RTGS": case "IMPS": case "Cheque": return paymentMode;
            case "Cash/ATM": return "Cash";
        }
        if (CardRe.IsMatch(narr)) return "Card";
        if (ChargesRe.IsMatch(narr)) return "Bank charges";
        return "Transfer";
    }

    private static string FindParty(string narr)
    {
        var parts = SplitRe.Split(narr).Select(p => p.Trim()).Where(p => p.Length > 0).ToList();
        string? vpaUser = null;
        foreach (var p in parts)
        {
            if (p.Contains('@'))
            {
                vpaUser ??= p.Split('@')[0];
                continue;
            }
            if (IfscRe.IsMatch(p)) continue;
            var digits = p.Count(char.IsDigit);
            var letters = p.Count(char.IsLetter);
            if (letters < 3 || digits > letters) continue;      // reference numbers, account numbers, dates
            // words carrying a number (UTR / account / "kamini1980") are references, not names
            var all = p.Split(' ', StringSplitOptions.RemoveEmptyEntries).Where(w => LettersRe.IsMatch(w) && w.Count(char.IsDigit) < 3).ToList();
            if (all.All(w => Jargon.Contains(w.Trim('.', ',', '*')) || BankCodes.Contains(w.Trim('.', ',', '*')))) continue;
            var words = all.Where(w => !Jargon.Contains(w.Trim('.', ',', '*'))).ToList();
            if (words.Count == 0) continue;
            var name = string.Join(" ", words);
            if (name.Count(char.IsLetter) < 3) continue;
            return TitleCase(name.Length > 40 ? name[..40].Trim() : name);
        }
        if (!string.IsNullOrEmpty(vpaUser) && vpaUser.Count(char.IsLetter) >= 3) return vpaUser.ToLowerInvariant();
        return "";
    }

    private static string TitleCase(string s) =>
        // "SHARMA TRADERS PVT LTD" → "Sharma Traders Pvt Ltd"; known short forms (HDFC, LIC, GST …) stay in capitals
        string.Join(" ", s.Split(' ', StringSplitOptions.RemoveEmptyEntries).Select(w =>
            Acronyms.Contains(w.Trim('.', ',')) ? w.ToUpperInvariant()
            : CultureInfo.InvariantCulture.TextInfo.ToTitleCase(w.ToLowerInvariant())));
}
