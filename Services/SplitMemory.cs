using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Remembers how an entry with a party was split last time (e.g. Rent ₹10,000 + GST ₹1,800) and applies it to the
/// next entry with the same party and direction.
/// Same total → the same amounts, row stays ticked. Different total → amounts scaled in the same ratio, row held back
/// for checking (unticked).
/// </summary>
public static class SplitMemory
{
    public static string Key(string partyKey, string txnType) => $"{partyKey}|{txnType}";

    public static bool CanRemember(BankTransactionRow r) =>
        !r.IsContra && r.VoucherType != "Contra" && (r.PartyKey ?? "").Trim().Length >= 4;

    /// <summary>
    /// Fits the remembered lines to <paramref name="amount"/>. Exact = same total. Scaled lines are rounded down to the
    /// paisa and the remainder goes to the largest line, so they always add up exactly. Null if it cannot be done.
    /// </summary>
    public static (List<LedgerSplit> lines, bool exact)? Fit(List<LedgerSplit> remembered, decimal amount)
    {
        if (remembered == null || remembered.Count < 2 || amount <= 0) return null;
        long total = remembered.Sum(l => (long)Math.Round(l.Amount * 100));
        long target = (long)Math.Round(amount * 100);
        if (total <= 0) return null;
        if (total == target)
            return (remembered.Select(l => new LedgerSplit { Ledger = l.Ledger, Amount = l.Amount }).ToList(), true);

        var paise = remembered.Select(l => (long)Math.Floor((decimal)(long)Math.Round(l.Amount * 100) * target / total)).ToList();
        int largest = 0;
        for (int i = 1; i < remembered.Count; i++) if (remembered[i].Amount > remembered[largest].Amount) largest = i;
        paise[largest] += target - paise.Sum();
        if (paise.Any(p => p <= 0)) return null;
        return (remembered.Select((l, i) => new LedgerSplit { Ledger = l.Ledger, Amount = paise[i] / 100m }).ToList(), false);
    }

    /// <summary>Applies remembered splits to rows that are not split yet. Returns (exact, scaled) counts.</summary>
    public static (int exact, int scaled) Apply(IEnumerable<BankTransactionRow> rows, IReadOnlyDictionary<string, List<LedgerSplit>> memory)
    {
        int exact = 0, scaled = 0;
        if (memory.Count == 0) return (0, 0);
        foreach (var r in rows)
        {
            if (r.IsSplit || r.PostStatus == "DONE" || r.OverlapStatus != "NEW" || !CanRemember(r)) continue;
            if (!memory.TryGetValue(Key(r.PartyKey, r.TxnType), out var lines)) continue;
            if (Fit(lines, r.Amount) is not { } fit) continue;
            r.Splits = fit.lines;
            r.SelectedLedger = fit.lines.OrderByDescending(l => l.Amount).First().Ledger;
            r.LastCommittedLedger = r.SelectedLedger;
            r.PredictionSource = "remembered_split";
            r.BillAllocations = [];
            r.BillRef = "(None)";
            if (fit.exact)
            {
                r.Confidence = 1.0;
                if (r.NeedsReview) { r.NeedsReview = false; r.Selected = true; }   // the ledger guess is replaced by your own split
                exact++;
            }
            else
            {
                r.Confidence = 0.5;
                r.NeedsReview = true;
                r.Selected = false;
                scaled++;
            }
        }
        return (exact, scaled);
    }
}
