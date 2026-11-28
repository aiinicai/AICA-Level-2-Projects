using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using UglyToad.PdfPig;
using UglyToad.PdfPig.Core;
using UglyToad.PdfPig.Fonts.Standard14Fonts;
using UglyToad.PdfPig.Writer;

namespace AutoBankStatementEntry.Services;

/// <summary>
/// Makes a copy of a statement PDF that is safe to send for support:
/// every name, narration word, account / reference number is replaced, while every word stays at its exact position and
/// dates, amounts, balances, column headings and the table lines are kept. The parser only uses positions, dates, amounts
/// and headings, so the copy fails (or succeeds) in exactly the same way as the original.
/// </summary>
public static class StatementAnonymiser
{
    // Banking words that carry no personal data but help recognise a layout / a transaction type
    private static readonly HashSet<string> KeepWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "UPI", "NEFT", "RTGS", "IMPS", "ATM", "CASH", "DEPOSIT", "DEP", "WITHDRAWAL", "WDL", "TFR", "TRF", "TRFR", "TRANSFER", "BY", "TO",
        "FROM", "CR", "DR", "DEBIT", "CREDIT", "BALANCE", "BAL", "OPENING", "CLOSING", "TOTAL", "PAGE", "OF", "STATEMENT", "ACCOUNT",
        "CHQ", "CHEQUE", "CLG", "INT", "INTEREST", "CHARGES", "CHG", "GST", "SMS", "POS", "ECOM", "ACH", "NACH", "BIL", "ONL", "INB",
        "SELF", "REF", "NO", "SUMMARY", "BROUGHT", "FORWARD", "CARRIED", "AS", "ON", "PERIOD", "IFS", "IFSC", "MICR", "RS", "INR",
        "COUNT", "DEBITS", "CREDITS", "WITHDRAWALS", "DEPOSITS", "AND", "THE", "FOR", "AT", "IN", "OWN", "SERVICE", "SALARY", "RENT",
        "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "SEPT", "OCT", "NOV", "DEC",
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    };

    private static readonly Regex MoneyRe = new(@"^[\(\-₹]?(?:Rs\.?)?(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{0,2}[\)\-]?(?:Dr|Cr|DR|CR)?$", RegexOptions.Compiled);
    private static readonly Regex SegmentRe = new(@"[A-Za-z]+|\d+|[^A-Za-z\d]+", RegexOptions.Compiled);

    /// <summary>Anonymises one word. <paramref name="salt"/> is random per file: the same name maps to the same dummy
    /// within a file (layouts stay consistent) but cannot be reversed by guessing names.</summary>
    public static string AnonymiseWord(string word, string salt)
    {
        if (string.IsNullOrEmpty(word)) return word;
        if (BankStatementParser.ParseIndianDate(word) != null || MoneyRe.IsMatch(word)) return word;
        var sb = new StringBuilder(word.Length);
        foreach (Match m in SegmentRe.Matches(word))
        {
            var seg = m.Value;
            if (char.IsLetter(seg[0]))
                sb.Append(KeepWords.Contains(seg) || BankStatementParser.IsLayoutWord(seg) ? seg : Dummy(seg, salt, letters: true));
            else if (char.IsDigit(seg[0]))
                // short numbers (day, year, branch code, serial, page no., masked "xx910") are not identifying; long ones are
                sb.Append(seg.Length <= 5 ? seg : Dummy(seg, salt, letters: false));
            else sb.Append(seg);
        }
        return sb.ToString();
    }

    private static string Dummy(string seg, string salt, bool letters)
    {
        var h = SHA256.HashData(Encoding.UTF8.GetBytes(salt + "|" + seg.ToUpperInvariant()));
        var outp = new char[seg.Length];
        for (int i = 0; i < seg.Length; i++)
        {
            int b = h[i % h.Length] + i * 7;
            if (letters)
            {
                // only Q X Z J K V: a dummy can never spell a banking word ("DEP", "WDL", "CR") that changes how a row is read
                char c = "QXZJKV"[b % 6];
                outp[i] = char.IsLower(seg[i]) ? char.ToLowerInvariant(c) : c;
            }
            // a leading 0 stays 0 (keeps "SBIN0…" IFSC codes and zero-padded account numbers recognisable)
            else outp[i] = i == 0 && seg[0] == '0' ? '0' : (char)('0' + (i == 0 ? 1 + b % 9 : b % 10));
        }
        return new string(outp);
    }

    /// <summary>Writes the anonymised copy and returns its bytes.</summary>
    public static byte[] Anonymise(string pdfPath, string? password)
    {
        var salt = Guid.NewGuid().ToString("N");
        var opts = string.IsNullOrEmpty(password) ? new ParsingOptions() : new ParsingOptions { Password = password };
        using var src = PdfDocument.Open(pdfPath, opts);
        var builder = new PdfDocumentBuilder();
        var font = builder.AddStandard14Font(Standard14Font.Helvetica);
        foreach (var page in src.GetPages())
        {
            var outPage = builder.AddPage(page.Width, page.Height);
            // table lines (borders, row rules) — needed for row / column detection
            try
            {
                foreach (var path in page.ExperimentalAccess.Paths)
                {
                    var rr = path.GetBoundingRectangle();
                    if (!rr.HasValue) continue;
                    var r = rr.Value;
                    if (r.Height <= 3.0 && r.Width >= 5.0)
                        outPage.DrawLine(new PdfPoint(r.Left, (r.Top + r.Bottom) / 2), new PdfPoint(r.Right, (r.Top + r.Bottom) / 2));
                    else if (r.Width <= 3.0 && r.Height >= 5.0)
                        outPage.DrawLine(new PdfPoint((r.Left + r.Right) / 2, r.Bottom), new PdfPoint((r.Left + r.Right) / 2, r.Top));
                    else if (r.Width >= 8.0 && r.Height >= 8.0 && r.Width < page.Width * 0.96)
                    {
                        outPage.DrawLine(new PdfPoint(r.Left, r.Bottom), new PdfPoint(r.Right, r.Bottom));
                        outPage.DrawLine(new PdfPoint(r.Left, r.Top), new PdfPoint(r.Right, r.Top));
                        outPage.DrawLine(new PdfPoint(r.Left, r.Bottom), new PdfPoint(r.Left, r.Top));
                        outPage.DrawLine(new PdfPoint(r.Right, r.Bottom), new PdfPoint(r.Right, r.Top));
                    }
                }
            }
            catch { /* a page whose drawing cannot be read still gets its text */ }

            foreach (var w in page.GetWords())
            {
                var text = Ascii(AnonymiseWord(w.Text, salt));
                if (text.Length == 0) continue;
                var b = w.BoundingBox;
                double orig = w.Letters.Count > 0 && w.Letters[0].PointSize > 0 ? w.Letters[0].PointSize : Math.Max(4, b.Height / 0.72);
                // Same WIDTH as the original word, so the gaps between words (which tell columns and heading phrases apart)
                // stay exactly as they were
                double size = Math.Clamp(b.Width / Math.Max(0.1, TextWidth(text)), 3.0, Math.Max(3.0, orig * 1.6));
                // numbers are right-aligned in statements: keep their RIGHT edge where it was
                double x = MoneyRe.IsMatch(w.Text) ? b.Right - TextWidth(text) * size : b.Left;
                outPage.AddText(text, size, new PdfPoint(Math.Max(0, x), b.Bottom), font);
            }
        }
        return builder.Build();
    }

    // Helvetica character widths (Adobe AFM, 1/1000 em) for ' ' … '~'
    private static readonly int[] HelveticaWidths =
    [
        278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556,
        556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778,
        667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556,
        556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584
    ];

    /// <summary>Width of <paramref name="s"/> in Helvetica at 1 pt.</summary>
    public static double TextWidth(string s) => s.Sum(c => c is >= ' ' and <= '~' ? HelveticaWidths[c - ' '] / 1000.0 : 0.556);

    // The standard PDF font has no ₹ / curly quotes / dashes: map them to plain characters
    private static string Ascii(string s)
    {
        var sb = new StringBuilder(s.Length);
        foreach (var c in s.Replace("₹", "Rs."))
            sb.Append(c is >= ' ' and <= '~' ? c : c is '–' or '—' or '−' ? '-' : c is '‘' or '’' ? '\'' : c is '“' or '”' ? '"' : '?');
        return sb.ToString().Trim();
    }
}
