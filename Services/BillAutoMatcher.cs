using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Picks the pending bill for an entry only when there is no doubt: exactly ONE open bill of that party has exactly the
/// same amount, on the right side (a Payment settles a bill we owe, a Receipt a bill owed to us), and no other entry in
/// the statement could take that same bill. Anything else is left for the user.
/// </summary>
public static class BillAutoMatcher
{
    public static bool IsEligible(BankTransactionRow r) =>
        !r.IsContra && r.VoucherType != "Contra" && !r.IsSplit && r.PostStatus != "DONE" && r.OverlapStatus == "NEW"
        && !r.NeedsReview && !string.IsNullOrWhiteSpace(r.SelectedLedger)
        && r.BillAllocations.Count == 0 && (r.BillRef ?? "(None)") == "(None)";

    public static string BillLabel(BillAllocation b) => b.PendingAmount > 0 ? $"{b.BillName} (₹{b.PendingAmount:N2})" : b.BillName;

    /// <param name="rows">All rows of the statement (rows already holding a bill keep it, and that bill is not offered again).</param>
    /// <param name="billsByParty">Pending bills per party ledger, as read from Tally.</param>
    public static Dictionary<BankTransactionRow, BillAllocation> Pick(
        IReadOnlyCollection<BankTransactionRow> rows, IReadOnlyDictionary<string, List<BillAllocation>> billsByParty)
    {
        static string BillKey(string party, string bill) => party.Trim().ToUpperInvariant() + "|" + bill.Trim().ToUpperInvariant();

        // bills someone already chose by hand
        var taken = new HashSet<string>();
        foreach (var r in rows)
        {
            var party = (r.SelectedLedger ?? "").Trim();
            foreach (var ba in r.BillAllocations) taken.Add(BillKey(party, ba.BillName));
            var br = (r.BillRef ?? "(None)").Trim();
            if (br != "(None)" && !br.StartsWith("Split", StringComparison.OrdinalIgnoreCase))
                taken.Add(BillKey(party, System.Text.RegularExpressions.Regex.Replace(br, @"\s*\(₹[0-9,.]+\)$", "")));
        }

        var claims = new Dictionary<string, List<(BankTransactionRow row, BillAllocation bill)>>();
        foreach (var r in rows.Where(IsEligible))
        {
            var party = r.SelectedLedger.Trim();
            if (!billsByParty.TryGetValue(party, out var bills)) continue;
            bool payable = r.TxnType == "DR";
            var exact = bills.Where(b => b.PendingAmount > 0 && b.IsPayable == payable
                                         && (long)Math.Round(b.PendingAmount * 100) == (long)Math.Round(Math.Abs(r.Amount) * 100)
                                         && !taken.Contains(BillKey(party, b.BillName))).ToList();
            if (exact.Count != 1) continue;
            var key = BillKey(party, exact[0].BillName);
            if (!claims.TryGetValue(key, out var list)) claims[key] = list = [];
            list.Add((r, exact[0]));
        }

        // one bill, one entry: if two entries could both take the same bill, neither gets it
        return claims.Values.Where(l => l.Count == 1).ToDictionary(l => l[0].row, l => l[0].bill);
    }
}
