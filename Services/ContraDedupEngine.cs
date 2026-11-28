using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

public class ContraDedupEngine
{
    private readonly DatabaseService _db;
    private static readonly Regex CashWdlRe = new(@"\b(atm|atw|nfs|nwd|eaw|cwdr|cash\s*wdl|csh\s*wdl|cash\s*wd|cash\s*withdrawal|self\s*chq|to\s*self|self\s*cheque)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CashDepRe = new(@"\b(cash\s*dep|cash\s*deposit|cdm|bna|by\s*cash|cash\s*cr)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex SelfTrfRe = new(@"\b(self\s*trf|self\s*transfer|own\s*a/?c|internal\s*trf|auto\s*sweep|sweep\s*(?:in|out))\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex ElectronicTrfRe = new(@"(?<![a-z])(neft|rtgs|imps)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex IfscSelfRe = new(@"(?<![a-z])((?:to|by|from)\s*self|self|own\s*a/?c|own\s*account)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex MultiSpaceRe = new(@"\s+", RegexOptions.Compiled);
    private static readonly Regex NonDigitRe = new(@"\D", RegexOptions.Compiled);

    public ContraDedupEngine(DatabaseService db) => _db = db;

    private static readonly Regex AtmChargeRe = new(@"(?<![a-z])(chg|chgs|charge|charges|fee|fees|amc|gst|annual|issuance|decline|penalty|commission)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>
    /// Stable duplicate-detection hash. <paramref name="occurrence"/> is the 1-based position of this row among rows with the
    /// IDENTICAL seed inside the same statement file: two genuine ₹10 "SMS CHG" debits on the same day used to share one hash
    /// (and one Tally REMOTEID), so the second was auto-unticked as a duplicate — or, if re-ticked, silently overwrote the first
    /// voucher in Tally. Occurrence 1 keeps the legacy hash so existing posted-history keeps working.
    /// </summary>
    public static string ComputeTxnHash(string bankLedger, string date, string txnType, decimal amount, string refNo, string narration, string companyName = "", int occurrence = 1)
    {
        var seed = BuildHashSeed(bankLedger, date, txnType, amount, refNo, narration, companyName);
        if (occurrence > 1) seed += $"|#{occurrence.ToString(CultureInfo.InvariantCulture)}";
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(seed)))[..24].ToLowerInvariant();
    }

    private static string BuildHashSeed(string bankLedger, string date, string txnType, decimal amount, string refNo, string narration, string companyName)
    {
        var n = MultiSpaceRe.Replace((narration ?? "").Trim().ToLowerInvariant(), " ");
        if (n.Length > 80) n = n[..80];
        var compPrefix = string.IsNullOrWhiteSpace(companyName) ? "" : $"{companyName.Trim().ToLowerInvariant()}|";
        // InvariantCulture: the amount must hash identically on every office PC regardless of Windows regional settings
        var amt = amount.ToString("F2", CultureInfo.InvariantCulture);
        return $"{compPrefix}{(bankLedger ?? "").Trim().ToLowerInvariant()}|{date}|{txnType}|{amt}|{(refNo ?? "").Trim().ToLowerInvariant()}|{n}";
    }

    private static int DaysBetween(string d1, string d2) =>
        DateTime.TryParseExact(d1, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var a) &&
        DateTime.TryParseExact(d2, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var b)
            ? Math.Abs((a - b).Days) : 999;

    private static Dictionary<string, int> BuildIdIndex(List<TallyExistingVoucher> live)
    {
        var byId = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (int i = 0; i < live.Count; i++)
        {
            foreach (var id in new[] { live[i].Guid, live[i].RemoteId })
                if (!string.IsNullOrWhiteSpace(id) && id.StartsWith("ABSE-", StringComparison.OrdinalIgnoreCase))
                    byId.TryAdd(id.Trim(), i);
        }
        return byId;
    }

    /// <summary>
    /// Last-moment duplicate guard, run immediately before posting: which of <paramref name="rows"/> already exist in Tally?
    /// Match 1: the voucher ID this app stamps on every entry (REMOTEID/GUID "ABSE-…") — catches a re-post after a timeout
    /// where Tally saved the voucher but the reply never arrived.
    /// Match 2: same bank ledger, same amount, same direction, date within 1 day (3 days with a matching cheque/UTR) — catches
    /// entries posted earlier from an older grid, another PC, or typed manually.
    /// Each Tally voucher can absorb only ONE row, so genuine repeated payments (two ₹625.80 on one day) are not over-blocked.
    /// </summary>
    public static List<(BankTransactionRow row, TallyExistingVoucher voucher, bool byId)> FindAlreadyInTally(
        IReadOnlyList<BankTransactionRow> rows, string bankLedger, List<TallyExistingVoucher> live)
    {
        var hits = new List<(BankTransactionRow, TallyExistingVoucher, bool)>();
        var used = new HashSet<int>();
        var byId = BuildIdIndex(live);
        var pending = new List<BankTransactionRow>();
        foreach (var row in rows)
        {
            if (!string.IsNullOrWhiteSpace(row.VoucherGuid) && byId.TryGetValue(row.VoucherGuid, out var idx) && used.Add(idx))
                hits.Add((row, live[idx], true));
            else
                pending.Add(row);
        }
        foreach (var row in pending)
        {
            long rowPaise = (long)Math.Round(row.Amount * 100m);
            int best = -1, bestScore = -1;
            for (int vi = 0; vi < live.Count; vi++)
            {
                if (used.Contains(vi)) continue;
                var tv = live[vi];
                if (!tv.LedgerAmounts.TryGetValue(bankLedger, out var bankSigned)) continue;
                if ((long)Math.Round(Math.Abs(bankSigned) * 100m) != rowPaise) continue;
                // Tally XML: bank credited (+) = withdrawal (statement DR); bank debited (−) = deposit (statement CR)
                bool dirMatches = (row.TxnType == "DR" && bankSigned > 0) || (row.TxnType == "CR" && bankSigned < 0);
                if (!dirMatches) continue;
                bool refMatch = !string.IsNullOrWhiteSpace(row.RefNo) && row.RefNo.Length >= 5 &&
                    ((!string.IsNullOrWhiteSpace(tv.RefNo) && tv.RefNo.Contains(row.RefNo, StringComparison.OrdinalIgnoreCase))
                     || (!string.IsNullOrWhiteSpace(tv.Narration) && tv.Narration.Contains(row.RefNo, StringComparison.OrdinalIgnoreCase)));
                int dayDiff = DaysBetween(tv.Date, row.TxnDate);
                if (dayDiff > (refMatch ? 3 : 1)) continue;
                int score = (refMatch ? 20 : 0) + (dayDiff == 0 ? 10 : 5)
                    + (tv.Ledgers.Contains(row.SelectedLedger, StringComparer.OrdinalIgnoreCase) ? 4 : 0);
                if (score > bestScore) { bestScore = score; best = vi; }
            }
            if (best >= 0)
            {
                used.Add(best);
                hits.Add((row, live[best], false));
            }
        }
        return hits;
    }

    public void AnalyzeBatch(
        List<BankTransactionRow> rows,
        string sourceBankLedger,
        string cashLedger,
        List<TallyExistingVoucher>? tallyVouchers = null,
        string companyName = "")
    {
        var ownBanks = _db.GetOwnBanks(companyName);
        var postedHashes = _db.GetPostedHashes(companyName);
        var postedContras = _db.GetPostedContras(companyName);
        var liveVouchers = tallyVouchers ?? [];

        var seenBatchHashes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var inBatchContras = new List<BankTransactionRow>();
        var usedTallyIndices = new HashSet<int>();

        // Index live Tally vouchers touching sourceBankLedger by amount in paise for O(1) overlap lookup
        var tallyByPaise = new Dictionary<long, List<(int idx, decimal signedAmt)>>();
        for (int vi = 0; vi < liveVouchers.Count; vi++)
        {
            if (!liveVouchers[vi].LedgerAmounts.TryGetValue(sourceBankLedger, out var bSigned)) continue;
            long paise = (long)Math.Round(Math.Abs(bSigned) * 100m);
            if (!tallyByPaise.TryGetValue(paise, out var bucket))
            {
                bucket = [];
                tallyByPaise[paise] = bucket;
            }
            bucket.Add((vi, bSigned));
        }

        // Vouchers this app created carry REMOTEID/GUID = row.VoucherGuid: an exact, amount-independent match
        var tallyById = BuildIdIndex(liveVouchers);

        // Occurrence counter per (source file, hash seed): identical genuine rows inside ONE statement get distinct hashes,
        // while the same row appearing in two overlapping statement files still collides (= real duplicate).
        var occurrenceCounter = new Dictionary<string, int>(StringComparer.Ordinal);

        foreach (var row in rows)
        {
            row.BankLedger = sourceBankLedger;
            var seedKey = $"{row.SourceFile}\u0001{BuildHashSeed(sourceBankLedger, row.TxnDate, row.TxnType, row.Amount, row.RefNo, row.Narration, companyName)}";
            int occurrence = occurrenceCounter.TryGetValue(seedKey, out var seen) ? seen + 1 : 1;
            occurrenceCounter[seedKey] = occurrence;
            row.TxnHash = ComputeTxnHash(sourceBankLedger, row.TxnDate, row.TxnType, row.Amount, row.RefNo, row.Narration, companyName, occurrence);
            row.VoucherGuid = $"ABSE-{row.TxnHash[..16]}";

            var (isContra, target, reason) = DetectContra(row.Narration, row.TxnType, sourceBankLedger, ownBanks, cashLedger);
            row.IsContra = isContra;
            row.ContraReason = reason;
            row.ContraTargetLedger = target ?? "";
            row.VoucherType = isContra ? "Contra" : (row.TxnType == "DR" ? "Payment" : "Receipt");
            row.MatchedTallyLedger = "";
            row.MatchedTallyVoucherType = "";

            string ovStatus = "NEW", ovReason = "";
            bool selected = true;

            // Check LIVE Tally vouchers first (O(1) by paise amount) so we always capture the exact Tally ledger for ML learning!
            long rowPaise = (long)Math.Round(row.Amount * 100m);
            int bestIdx = -1;
            int bestScore = -1;
            int oppIdx = -1;
            int oppScore = -1;
            if (tallyById.TryGetValue(row.VoucherGuid, out var idHit) && !usedTallyIndices.Contains(idHit))
            {
                bestIdx = idHit; // this exact row was already posted by this app (e.g. a retry after a timeout)
            }
            else if (tallyByPaise.TryGetValue(rowPaise, out var candidates))
            {
                foreach (var (vi, bankSignedAmt) in candidates)
                {
                    if (usedTallyIndices.Contains(vi)) continue;
                    var tv = liveVouchers[vi];

                    int dayDiff = DaysBetween(tv.Date, row.TxnDate);
                    bool refMatch = !string.IsNullOrWhiteSpace(row.RefNo) && row.RefNo.Length >= 5 &&
                        ((!string.IsNullOrWhiteSpace(tv.RefNo) && tv.RefNo.Contains(row.RefNo, StringComparison.OrdinalIgnoreCase))
                         || (!string.IsNullOrWhiteSpace(tv.Narration) && tv.Narration.Contains(row.RefNo, StringComparison.OrdinalIgnoreCase)));

                    if (dayDiff > (refMatch ? 3 : 1)) continue;

                    // In Tally XML: bankSignedAmt > 0 means Bank CR (bank statement DR withdrawal); bankSignedAmt < 0 means Bank DR (bank statement CR deposit)
                    bool dirMatches = (row.TxnType == "DR" && bankSignedAmt > 0) || (row.TxnType == "CR" && bankSignedAmt < 0);
                    int score = (refMatch ? 20 : 0) + (dayDiff == 0 ? 10 : (dayDiff == 1 ? 5 : 1))
                        + (tv.VoucherType.Equals(row.VoucherType, StringComparison.OrdinalIgnoreCase) ? 3 : 0);

                    if (dirMatches)
                    {
                        if (score > bestScore) { bestScore = score; bestIdx = vi; }
                    }
                    else
                    {
                        if (score > oppScore) { oppScore = score; oppIdx = vi; }
                    }
                }
            }
            {
                if (bestIdx >= 0)
                {
                    usedTallyIndices.Add(bestIdx);
                    var tv = liveVouchers[bestIdx];
                    var counterLedger = tv.LedgerAmounts
                        .Where(kv => !kv.Key.Equals(sourceBankLedger, StringComparison.OrdinalIgnoreCase))
                        .OrderByDescending(kv => Math.Abs(kv.Value))
                        .Select(kv => kv.Key)
                        .FirstOrDefault() ?? "";
                    row.MatchedTallyLedger = counterLedger;
                    row.MatchedTallyVoucherType = tv.VoucherType;
                    ovStatus = tv.VoucherType.Equals("Contra", StringComparison.OrdinalIgnoreCase)
                        ? "OVERLAP_TALLY_CONTRA"
                        : "OVERLAP_TALLY_EXISTING";
                    ovReason = string.IsNullOrEmpty(counterLedger)
                        ? $"Already in Tally ({tv.VoucherType}, {tv.Date}, ₹{row.Amount:N2})."
                        : $"Already in Tally as {tv.VoucherType} → {counterLedger} ({tv.Date}, ₹{row.Amount:N2}).";
                    selected = false;
                }
                else if (oppIdx >= 0)
                {
                    var tv = liveVouchers[oppIdx];
                    var counterLedger = tv.LedgerAmounts
                        .Where(kv => !kv.Key.Equals(sourceBankLedger, StringComparison.OrdinalIgnoreCase))
                        .OrderByDescending(kv => Math.Abs(kv.Value))
                        .Select(kv => kv.Key)
                        .FirstOrDefault() ?? "";
                    ovStatus = "WARN_OPPOSITE_TALLY";
                    ovReason = string.IsNullOrEmpty(counterLedger)
                        ? $"⚠ Opposite-side entry in Tally ({tv.VoucherType}, {tv.Date}, ₹{row.Amount:N2}) — check Dr/Cr in Tally!"
                        : $"⚠ Opposite-side entry in Tally ({tv.VoucherType} → {counterLedger}, {tv.Date}, ₹{row.Amount:N2}) — check Dr/Cr in Tally!";
                }
            }

            if (selected && postedHashes.Contains(row.TxnHash))
            {
                ovStatus = "DUPLICATE_POSTED";
                ovReason = "Already posted to Tally / exported to XML earlier (tick 'Post' only if that XML was never imported).";
                selected = false;
            }
            else if (selected && !seenBatchHashes.Add(row.TxnHash))
            {
                ovStatus = "DUPLICATE_IN_BATCH";
                ovReason = "Duplicate row inside this upload.";
                selected = false;
            }

            if (selected && isContra && !string.IsNullOrEmpty(row.ContraTargetLedger) && !row.ContraTargetLedger.Equals(cashLedger, StringComparison.OrdinalIgnoreCase))
            {
                foreach (var prev in postedContras)
                {
                    var samePair = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { prev.bankLedger, prev.counterpartyLedger }
                        .SetEquals([sourceBankLedger, row.ContraTargetLedger]);
                    bool sameRef = !string.IsNullOrEmpty(row.RefNo) && row.RefNo.Equals(prev.refNo, StringComparison.OrdinalIgnoreCase);
                    if (prev.amount == row.Amount && DaysBetween(prev.txnDate, row.TxnDate) <= 2 && (sameRef || (samePair && prev.txnType != row.TxnType)))
                    {
                        ovStatus = "OVERLAP_CONTRA";
                        ovReason = $"Contra pair already posted via {prev.bankLedger} on {prev.txnDate}. Skipped to avoid double-entry.";
                        selected = false;
                        break;
                    }
                }
            }

            if (selected && isContra && !string.IsNullOrEmpty(row.ContraTargetLedger) && !row.ContraTargetLedger.Equals(cashLedger, StringComparison.OrdinalIgnoreCase))
            {
                foreach (var prev in inBatchContras)
                {
                    var samePair = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { prev.BankLedger, prev.ContraTargetLedger }
                        .SetEquals([sourceBankLedger, row.ContraTargetLedger]);
                    bool sameRef = !string.IsNullOrEmpty(row.RefNo) && row.RefNo.Equals(prev.RefNo, StringComparison.OrdinalIgnoreCase);
                    if (prev.Amount == row.Amount && DaysBetween(prev.TxnDate, row.TxnDate) <= 2 && (sameRef || (samePair && prev.TxnType != row.TxnType)))
                    {
                        ovStatus = "OVERLAP_CONTRA_IN_BATCH";
                        ovReason = $"Opposite leg already included in this batch. Auto-skipped.";
                        selected = false;
                        break;
                    }
                }
            }

            row.OverlapStatus = ovStatus;
            row.OverlapReason = ovReason;
            row.Selected = selected;
            if (selected && isContra) inBatchContras.Add(row);
        }
    }

    private static (bool isContra, string? target, string reason) DetectContra(
        string narr, string txnType, string srcBank, List<OwnBankAccount> ownBanks, string cashLedger)
    {
        // "ATM AMC CHG", "DEBIT CARD ANNUAL FEE", "ATM DECLINE CHARGES" are bank charges, not cash withdrawals
        bool looksLikeCharge = AtmChargeRe.IsMatch(narr);
        // NEFT / RTGS / IMPS are account-to-account transfers and can never be a cash withdrawal ("NEFT ... TRF TO SELF")
        bool electronicTransfer = ElectronicTrfRe.IsMatch(narr);
        if (txnType == "DR" && CashWdlRe.IsMatch(narr) && !looksLikeCharge && !electronicTransfer) return (true, cashLedger, "Cash withdrawal (ATM/Self)");
        if (txnType == "CR" && CashDepRe.IsMatch(narr) && !looksLikeCharge) return (true, cashLedger, "Cash deposit (CDM/Branch)");

        foreach (var b in ownBanks)
        {
            if (b.TallyLedgerName.Equals(srcBank, StringComparison.OrdinalIgnoreCase)) continue;
            var digits = NonDigitRe.Replace(b.AccountNumber ?? "", "");
            if (digits.Length >= 4 && NarrationMentionsAccount(narr, digits[^4..]))
                return (true, b.TallyLedgerName, $"Inter-bank → {b.TallyLedgerName} (A/c …{digits[^4..]}" + (string.IsNullOrEmpty(b.Ifsc) ? ")" : $", {b.Ifsc})"));
            // IFSC identifies a BRANCH, not an account: a vendor banking at the same branch has the same IFSC. IFSC alone is
            // therefore only accepted together with a self / own-account transfer wording (account digits were checked above).
            if ((b.Ifsc ?? "").Length >= 8 && narr.Contains(b.Ifsc!, StringComparison.OrdinalIgnoreCase) && (SelfTrfRe.IsMatch(narr) || IfscSelfRe.IsMatch(narr)))
                return (true, b.TallyLedgerName, $"Inter-bank self transfer → {b.TallyLedgerName} (IFSC {b.Ifsc})");
            foreach (var al in (b.Aliases ?? "").Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
                if (al.Length >= 3 && narr.Contains(al, StringComparison.OrdinalIgnoreCase))
                    return (true, b.TallyLedgerName, $"Inter-bank transfer matching alias '{al}'");
        }

        if (SelfTrfRe.IsMatch(narr))
        {
            var others = ownBanks.Where(b => !b.TallyLedgerName.Equals(srcBank, StringComparison.OrdinalIgnoreCase)).ToList();
            // Only auto-pick the target when it is unambiguous; with 2+ other banks the user must choose (previously the
            // alphabetically-first bank was silently used).
            if (others.Count == 1)
                return (true, others[0].TallyLedgerName, "Self/Internal transfer detected");
            return (true, "", others.Count == 0
                ? "Self/Internal transfer detected — choose the other bank / cash ledger"
                : $"Self/Internal transfer detected — choose which of your {others.Count} other banks");
        }
        return (false, null, "");
    }

    /// <summary>
    /// True when <paramref name="last4"/> appears in the narration as an account reference: as a stand-alone 4-digit number,
    /// after mask characters ("XXXX1234", "**1234", "...1234"), or as the tail of an account-number-length digit run.
    /// Plain substring matching made any UPI/IMPS reference number, amount or date ("2025") that happened to contain the
    /// digits trigger a false Contra.
    /// </summary>
    public static bool NarrationMentionsAccount(string narr, string last4)
    {
        if (string.IsNullOrEmpty(narr) || last4.Length != 4) return false;
        foreach (Match m in Regex.Matches(narr, $@"(?<![0-9])((?:[xX*]+|\.{{2,}})?)([0-9]*){last4}(?![0-9])"))
        {
            int leadDigits = m.Groups[2].Value.Length;
            bool masked = m.Groups[1].Value.Length > 0;
            if (masked) return true;                              // XXXX1234 / **1234 / ...1234 / XXXXXX001234
            if (leadDigits == 0)
            {
                // Bare "1234": accept unless it is obviously a year / time / amount fragment
                int idx = m.Index;
                char prev = idx > 0 ? narr[idx - 1] : ' ';
                char next = m.Index + m.Length < narr.Length ? narr[m.Index + m.Length] : ' ';
                if (prev is '.' or ',' or ':' || next is '.' or ',' or ':') continue;
                if (last4.StartsWith("19", StringComparison.Ordinal) || last4.StartsWith("20", StringComparison.Ordinal)) continue;
                return true;
            }
            int total = leadDigits + 4;
            // Account numbers are 9-18 digits; exclude 12-digit UPI/IMPS RRNs and 16-digit card numbers
            if (total >= 9 && total <= 18 && total != 12 && total != 16) return true;
        }
        return false;
    }
}
