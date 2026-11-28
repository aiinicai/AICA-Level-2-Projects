using System.Text.RegularExpressions;
using AutoBankStatementEntry.Models;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Identifies the party of a bank entry EXACTLY from the details already stored in Tally's party ledgers, before any ML
/// guess:
/// 1. the party's full account number appears in the narration                       → 99 %
/// 2. a masked account ("xx910", "XXXXXX4521") whose last digits AND bank (IFSC code) match one party → 97 %
/// 3. the party's ledger name / beneficiary name appears as whole words in the narration → 92 %
/// A match is used only when exactly ONE party fits; two candidates means "not sure" and the ML decides.
/// </summary>
public static class PartyMatcher
{
    public const double AccountConfidence = 0.99;
    public const double MaskedConfidence = 0.97;
    public const double NameConfidence = 0.92;

    private static readonly Regex DigitRunRe = new(@"\d{6,20}", RegexOptions.Compiled);
    private static readonly Regex MaskedRe = new(@"[X*]{2,}[\s\-]?(\d{3,6})(?!\d)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex BankCodeRe = new(@"(?<![A-Z])([A-Z]{4})(?:0[A-Z0-9]{6})?(?![A-Z])", RegexOptions.Compiled);
    private static readonly HashSet<string> Titles = new(StringComparer.OrdinalIgnoreCase)
        { "MR", "MRS", "MS", "MISS", "M", "S", "DR", "SHRI", "SMT", "KUM", "THE", "AND", "OF" };

    public static (string ledger, double confidence, string source)? Match(string narration, IReadOnlyList<PartyBankInfo> parties)
    {
        if (string.IsNullOrWhiteSpace(narration) || parties.Count == 0) return null;
        var up = narration.ToUpperInvariant();

        // 1. Full account number
        var runs = DigitRunRe.Matches(up).Select(m => m.Value.TrimStart('0')).Where(r => r.Length >= 6).ToHashSet();
        if (runs.Count > 0)
        {
            var hits = parties.Where(p => p.AccountNumbers.Any(a => a.Length >= 8 && runs.Contains(a.TrimStart('0'))))
                              .Select(p => p.Ledger).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            if (hits.Count == 1) return (hits[0], AccountConfidence, "tally_bank_account");
        }

        // 2. Masked account + bank code from the IFSC ("IMPS/631111/HDFC/xx910")
        var masked = MaskedRe.Matches(up).Select(m => m.Groups[1].Value).Distinct().ToList();
        if (masked.Count > 0)
        {
            var codes = BankCodeRe.Matches(up).Select(m => m.Groups[1].Value).ToHashSet();
            var hits = parties.Where(p =>
                    p.AccountNumbers.Any(a => masked.Any(d => a.Length > d.Length && a.EndsWith(d, StringComparison.Ordinal)))
                    && p.Ifscs.Any(i => i.Length >= 4 && codes.Contains(i[..4].ToUpperInvariant())))
                .Select(p => p.Ledger).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            if (hits.Count == 1) return (hits[0], MaskedConfidence, "tally_bank_masked");
        }

        // 3. Party / beneficiary name as whole words (a truncated last word such as "BEHER" for "Behera" still counts)
        var words = Tokens(up);
        if (words.Count == 0) return null;
        string? best = null; int bestLen = 0; bool tie = false;
        foreach (var p in parties)
        {
            foreach (var name in new[] { p.Ledger, p.Favouring })
            {
                if (string.IsNullOrWhiteSpace(name)) continue;
                var nt = NameTokens.GetOrAdd(name, n => Tokens(n.ToUpperInvariant()));
                bool usable = nt.Count >= 2 || (nt.Count == 1 && nt[0].Length >= 8);
                if (!usable || !ContainsSequence(words, nt)) continue;
                int len = nt.Sum(t => t.Length);
                if (len > bestLen) { best = p.Ledger; bestLen = len; tie = false; }
                else if (len == bestLen && best != null && !best.Equals(p.Ledger, StringComparison.OrdinalIgnoreCase)) tie = true;
            }
        }
        return best != null && !tie ? (best, NameConfidence, "tally_party_name") : null;
    }

    // party names are tokenised once, not once per bank row (thousands of ledgers × hundreds of rows)
    private static readonly System.Collections.Concurrent.ConcurrentDictionary<string, List<string>> NameTokens = new(StringComparer.Ordinal);

    private static List<string> Tokens(string s) =>
        Regex.Split(s, "[^A-Z0-9]+").Where(t => t.Length > 0 && !Titles.Contains(t)).ToList();

    private static bool ContainsSequence(List<string> words, List<string> seq)
    {
        for (int i = 0; i + seq.Count <= words.Count; i++)
        {
            bool ok = true;
            for (int k = 0; k < seq.Count && ok; k++)
            {
                var w = words[i + k];
                bool last = k == seq.Count - 1;
                ok = w == seq[k] || (last && seq.Count >= 2 && w.Length >= 4 && seq[k].StartsWith(w, StringComparison.Ordinal));
            }
            if (ok) return true;
        }
        return false;
    }
}
