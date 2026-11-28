using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// When a predicted ledger may be posted without a person looking at it.
/// A guess (empty ledger, Suspense, or ML confidence below <see cref="ConfidenceFloor"/>) starts UNTICKED; choosing or
/// confirming a ledger ticks the row again.
/// </summary>
public static class ReviewPolicy
{
    public const double ConfidenceFloor = 0.60;

    public static bool IsGuess(BankTransactionRow r) =>
        string.IsNullOrWhiteSpace(r.SelectedLedger)
        || r.PostingLedgers.Any(l => l.Trim().Equals("Suspense Account", StringComparison.OrdinalIgnoreCase))
        || (!r.IsSplit && r.PredictionSource != "user_manual" && r.Confidence < ConfidenceFloor);

    /// <summary>After analysis: hold back every guess. Returns how many rows were held back.</summary>
    public static int HoldBackGuesses(IEnumerable<BankTransactionRow> rows)
    {
        int n = 0;
        foreach (var r in rows)
        {
            if (!r.Selected || r.PostStatus == "DONE" || !IsGuess(r)) continue;
            r.NeedsReview = true;
            r.Selected = false;
            n++;
        }
        return n;
    }

    /// <summary>A person chose / confirmed the ledger: a row held back for review is ticked again (unless it is still a guess).</summary>
    public static void ConfirmReviewed(BankTransactionRow r)
    {
        if (!r.NeedsReview || IsGuess(r)) return;
        r.NeedsReview = false;
        if (r.PostStatus != "DONE" && r.OverlapStatus == "NEW") r.Selected = true;
    }
}
