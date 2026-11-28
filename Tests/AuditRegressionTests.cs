using System.Globalization;
using System.IO;
using System.Text.Json;
using AutoBankStatementEntry.Models;
using AutoBankStatementEntry.Services;
using Xunit;

namespace AutoBankStatementEntry.Tests;

/// <summary>
/// Regression tests added during the reliability audit. The fixture statements (Tests/Fixtures) are synthetic files modelled
/// on the layouts of the major Indian banks; each has a ground-truth JSON with every expected row, total, opening and closing.
/// Regenerate with Tests/Fixtures/_generator/gen_fixtures.py + gen_pdf_fixtures.py (Python, openpyxl, reportlab).
/// </summary>
public class AuditRegressionTests
{
    private static string FixtureDir => Path.Combine(AppContext.BaseDirectory, "Fixtures");

    public static IEnumerable<object[]> AllFixtures()
    {
        var manifest = Path.Combine(AppContext.BaseDirectory, "Fixtures", "manifest.json");
        using var doc = JsonDocument.Parse(File.ReadAllText(manifest));
        foreach (var e in doc.RootElement.EnumerateArray())
            yield return [e.GetProperty("file").GetString()!];
    }

    // ------------------------------------------------------------------ every bank: every debit & credit, exact totals
    [Theory]
    [MemberData(nameof(AllFixtures))]
    public async Task BankFixture_ParsesEveryDebitAndCreditExactly(string fileName)
    {
        using var truth = JsonDocument.Parse(File.ReadAllText(Path.Combine(FixtureDir, fileName + ".json")));
        var t = truth.RootElement;
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, fileName));

        Assert.Equal(t.GetProperty("bank").GetString(), res.BankDetected);
        Assert.Equal(t.GetProperty("count").GetInt32(), res.Transactions.Count);

        var expected = t.GetProperty("rows").EnumerateArray()
            .Select(r => $"{r.GetProperty("date").GetString()}|{r.GetProperty("type").GetString()}|{r.GetProperty("amount").GetDouble().ToString("F2", CultureInfo.InvariantCulture)}")
            .OrderBy(x => x, StringComparer.Ordinal).ToList();
        var actual = res.Transactions
            .Select(r => $"{r.TxnDate}|{r.TxnType}|{r.Amount.ToString("F2", CultureInfo.InvariantCulture)}")
            .OrderBy(x => x, StringComparer.Ordinal).ToList();
        Assert.Equal(expected, actual);

        Assert.Equal(t.GetProperty("total_debit").GetDecimal(), res.Balances.TotalDebit, 2);
        Assert.Equal(t.GetProperty("total_credit").GetDecimal(), res.Balances.TotalCredit, 2);
        Assert.NotNull(res.Balances.StatementOpening);
        Assert.NotNull(res.Balances.StatementClosing);
        Assert.Equal(t.GetProperty("opening").GetDecimal(), res.Balances.StatementOpening!.Value, 2);
        Assert.Equal(t.GetProperty("closing").GetDecimal(), res.Balances.StatementClosing!.Value, 2);
        Assert.True(res.Balances.StatementBalanced, $"Statement did not reconcile (diff {res.Balances.StatementDiff})");
        Assert.Empty(res.Balances.CompletenessIssues);
        Assert.Equal("", res.Balances.BlockReason);
        Assert.All(res.Transactions, r => Assert.False(r.HasBalanceBreak, $"{r.DisplayDate} {r.Narration}: {r.BalanceBreakNote}"));
        Assert.All(res.Transactions, r => Assert.Equal(r.TxnType == "DR" ? r.Amount : 0, r.Debit));
        Assert.All(res.Transactions, r => Assert.Equal(r.TxnType == "CR" ? r.Amount : 0, r.Credit));
    }

    [Fact]
    public async Task IciciTransactionsList_CrDrColumnHonoured_AndCentredDescriptionStaysOnItsOwnRow()
    {
        // Real-world report: row 1 (CR 70,200) was booked as a DEBIT and row 1's narration contained row 2's party.
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, "icici_txnlist_statement.pdf"));
        Assert.Equal(7, res.Transactions.Count);
        Assert.Equal("CR", res.Transactions[0].TxnType);
        Assert.Equal(70200.00m, res.Transactions[0].Credit);
        Assert.Equal(169079.00m, res.Balances.StatementOpening);
        Assert.True(res.Balances.StatementBalanced);
        Assert.Equal("Digital PDF", res.ExtractionMethod); // main column parser, not the fallback
        Assert.Contains("kamini1980", res.Transactions[0].Narration);
        Assert.DoesNotContain("SHREE", res.Transactions[0].Narration);
        Assert.Contains("SHREE", res.Transactions[1].Narration);
        Assert.Contains("SAHU", res.Transactions[1].Narration);
        Assert.DoesNotContain("12:04", res.Transactions[0].Narration);
    }

    [Fact]
    public async Task UnstatedDirection_IsFlaggedForTheUser_AndConfirmationRecomputesBalances()
    {
        // Single Amount column, no Dr/Cr column, no signs: only the running balance can tell the direction —
        // rows 2-3 are proven by it, row 1 (no opening printed) cannot be, so it must be ASKED, never silently guessed.
        var csv = string.Join("\r\n",
            "Date,Narration,Amount,Balance",
            "01/04/2025,NEFT CLIENT RECEIPT,5000.00,15000.00",
            "02/04/2025,UPI VENDOR,2000.00,13000.00",
            "03/04/2025,NEFT CLIENT B,1000.00,14000.00");
        var path = WriteTemp("nodir.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            var uncertain = res.Transactions.Where(BankStatementParser.IsDirectionUncertain).ToList();
            Assert.Single(uncertain);
            Assert.Same(res.Transactions[0], uncertain[0]);
            Assert.Null(res.Balances.StatementBalanced);          // not a false "BALANCED"
            Assert.Equal("DR", res.Transactions[1].TxnType);       // proven by balance
            Assert.Equal("CR", res.Transactions[2].TxnType);       // proven by balance

            BankStatementParser.ApplyConfirmedDirections(res, new Dictionary<BankTransactionRow, string> { [uncertain[0]] = "CR" });
            Assert.Equal("CR", res.Transactions[0].TxnType);
            Assert.Equal(5000.00m, res.Transactions[0].Credit);
            Assert.Equal(0.0m, res.Transactions[0].Debit);
            Assert.False(BankStatementParser.IsDirectionUncertain(res.Transactions[0]));
            Assert.Equal(10000.00m, res.Balances.StatementOpening);
            Assert.Equal(14000.00m, res.Balances.StatementClosing);
            Assert.True(res.Balances.StatementBalanced);
            Assert.All(res.Transactions, r => Assert.False(r.HasBalanceBreak));
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    [Fact]
    public async Task SwappedDebitCreditColumns_AllRowsFixed_FirstRowAskedNotGuessed()
    {
        // Real-world report: the first row "WDL TFR UPI/DR/…" ₹1,426 (a withdrawal) was posted as a RECEIPT. Later rows
        // were corrected by the running balance, the first row could not be.
        var csv = string.Join("\r\n",
            "Date,Narration,Withdrawal,Deposit,Balance",
            "01/04/2025,WDL TFR UPI/DR/509169091433/Rajendra,,1426.00,62552.96",
            "02/04/2025,WDL TFR UPI/DR/509255562086/RELIANCE,,448.00,62104.96",
            "02/04/2025,CHQ TRFR FROM 0052018191363,100000.00,,162104.96",
            "03/04/2025,UPI/DR/111/SHOP,,500.00,161604.96",
            "04/04/2025,NEFT CR CLIENT,2000.00,,163604.96");
        var path = WriteTemp("swapped.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            Assert.Equal(new[] { "DR", "DR", "CR", "DR", "CR" }, res.Transactions.Select(t => t.TxnType).ToArray());
            Assert.True(BankStatementParser.IsDirectionUncertain(res.Transactions[0])); // user confirms row 1
            Assert.Null(res.Balances.StatementBalanced);
            BankStatementParser.ApplyConfirmedDirections(res, new Dictionary<BankTransactionRow, string> { [res.Transactions[0]] = "DR" });
            Assert.Equal(63978.96m, res.Balances.StatementOpening);
            Assert.True(res.Balances.StatementBalanced);
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    [Fact]
    public async Task FirstRow_NarrationContradictsColumn_IsAskedNotPosted()
    {
        // Only row 1 is in the wrong column (no opening printed, so the balance cannot prove it)
        var csv = string.Join("\r\n",
            "Date,Narration,Withdrawal,Deposit,Balance",
            "01/04/2025,WDL TFR UPI/DR/509169091433/Rajendra,,1426.00,62552.96",
            "02/04/2025,WDL TFR UPI/DR/509255562086/RELIANCE,448.00,,62104.96",
            "02/04/2025,CHQ TRFR FROM 0052018191363,,100000.00,162104.96");
        var path = WriteTemp("row1.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            Assert.True(BankStatementParser.IsDirectionUncertain(res.Transactions[0]));
            Assert.False(BankStatementParser.IsDirectionUncertain(res.Transactions[1]));
            Assert.Null(res.Balances.StatementBalanced);
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    [Theory]
    [InlineData("WDL TFR UPI/DR/509169091433/Rajendra/SBIN", "DR")]
    [InlineData("CHQ TRFR FROM 0052018191363 OF Mrs. SIMA", "CR")]
    [InlineData("TO TRANSFER INB IMPS/582326140", "DR")]
    [InlineData("BY TRANSFER-NEFT CR-HDFC0000240", "CR")]
    [InlineData("SHARMA TRADERS", null)]
    public void NarrationDirectionHint_Works(string narr, string? expected)
    {
        Assert.Equal(expected, BankStatementParser.NarrationDirectionHint(narr));
    }

    [Fact]
    public async Task ExplicitDebitCreditColumns_NeverAskTheUser()
    {
        foreach (var f in new[] { "hdfc_statement.xlsx", "kotak_statement.csv", "union_statement.csv", "icici_txnlist_statement.pdf" })
        {
            var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, f));
            Assert.DoesNotContain(res.Transactions, BankStatementParser.IsDirectionUncertain);
        }
    }

    [Fact]
    public async Task SbiHeaderAsImage_ColumnsInferredFromTable_NoReferenceNumbersAsAmounts()
    {
        // Real-world report: SBI 2025 PDF whose header row could not be read; a stray "Date … Credit" line was taken as the
        // header and the Details text (with UPI ref 509169091433) was booked as a CREDIT of ₹5,09,16,90,91,433.
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, "sbi_new_imgheader.pdf"));
        Assert.Equal(60, res.Transactions.Count);
        Assert.True(res.Balances.StatementBalanced);
        Assert.All(res.Transactions, r => Assert.True(r.Amount < 10_000_000, $"implausible amount {r.Amount}"));
        Assert.All(res.Transactions, r => Assert.NotEqual("Bank Transaction", r.Narration));
        Assert.Contains("RELIANCE", res.Transactions[0].Narration.Replace(" ", ""));
        Assert.Contains("columns inferred from table content", res.DiagnosticReport);
    }

    [Theory]
    [InlineData("sbi_new_p1only.pdf")]          // unreadable header on page 1 only + bordered account box: page 1 rows must be kept
    [InlineData("sbi_new_runtogether.pdf")]     // headings run together: "Value DatePost Date", "DetailsRef", "₹ Debit₹ Credit"
    [InlineData("sbi_new_spaced.pdf")]          // letter-spaced headings: "V a l u e  D a t e"
    [InlineData("sbi_new_img_borderless.pdf")]  // header is an image, table body has no borders
    public async Task ColouredHeaders_AllVariants_FirstPageIncluded_AndNarrationsKept(string file)
    {
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, file));
        Assert.Equal(60, res.Transactions.Count);
        Assert.Equal("2025-04-01", res.Transactions[0].TxnDate);   // first page not skipped
        Assert.True(res.Balances.StatementBalanced);
        Assert.Equal("Digital PDF", res.ExtractionMethod);           // main parser, not the fallback
        Assert.True(res.Transactions.Count(r => r.Narration == "Bank Transaction") == 0);
    }

    [Theory]
    [InlineData("1,426.00", true)]
    [InlineData("62,552.96 Cr", true)]
    [InlineData("Rs. 1,000.00", true)]
    [InlineData("-", true)]
    [InlineData("5000", true)]
    [InlineData("WDL TFR UPI/DR/509169091433/Rajendra/", false)]
    [InlineData("509169091433", false)]              // UPI RRN
    [InlineData("0052018191363", false)]             // account number
    [InlineData("12345678901.00", true)]             // large but a real decimal amount
    public void AmountCells_RejectTextAndReferenceNumbers(string cell, bool ok)
    {
        Assert.Equal(ok, BankStatementParser.IsPlausibleAmountCell(cell));
    }

    // ------------------------------------------------------------------ amount / date primitives
    [Theory]
    [InlineData("Rs. 1,000.00", 1000.00, null)]
    [InlineData("INR 2,50,000.50", 250000.50, null)]
    [InlineData("₹ 999", 999.00, null)]
    [InlineData("1,250.00Dr", 1250.00, "DR")]
    [InlineData("82,000.00(Cr)", 82000.00, "CR")]
    [InlineData("500.00 (Dr)", 500.00, "DR")]
    [InlineData("(1,234.00)", 1234.00, "DR")]
    [InlineData("12500.00-", 12500.00, "DR")]
    [InlineData("-7,400.00", 7400.00, "DR")]
    [InlineData("1,20,749.50 Cr", 120749.50, "CR")]
    [InlineData("-", 0.0, null)]
    public void ParseIndianAmount_HandlesBankFormats(string raw, double amount, string? flag)
    {
        var (amt, f) = BankStatementParser.ParseIndianAmount(raw);
        Assert.Equal((decimal)amount, amt);   // decimal: exact, no tolerance needed
        Assert.Equal(flag, f);
    }

    [Theory]
    [InlineData("01 Sept 2025", "2025-09-01")]
    [InlineData("1 Apr 2025", "2025-04-01")]
    [InlineData("01-APR-2025", "2025-04-01")]
    [InlineData("2025-04-01T00:00:00", "2025-04-01")]
    [InlineData("05/04/25", "2025-04-05")]
    [InlineData("45748", "2025-04-01")]
    [InlineData("45,000.00", null)]
    [InlineData("INVOICE 1042", null)]
    public void ParseIndianDate_HandlesFormats_AndNeverTreatsAmountsAsDates(string raw, string? iso)
    {
        Assert.Equal(iso, BankStatementParser.ParseIndianDate(raw));
    }

    [Fact]
    public async Task SignedSingleAmountColumn_PositiveIsCredit()
    {
        var csv = string.Join("\r\n",
            "Transaction Date,Transaction Details,Amount,Balance",
            "01/04/2025,NEFT CR CLIENT,5000.00,15000.00",
            "02/04/2025,UPI DR VENDOR,-2000.00,13000.00");
        var path = WriteTemp("signed.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            Assert.Equal(new[] { "CR", "DR" }, res.Transactions.Select(r => r.TxnType).ToArray());
            Assert.Equal(10000.00m, res.Balances.StatementOpening);
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    [Fact]
    public async Task VendorNamedTotal_KeepsNarration_AndAmount()
    {
        var csv = string.Join("\r\n",
            "Date,Narration,Withdrawal Amt.,Deposit Amt.,Closing Balance",
            "01/04/2025,TOTAL ENVIRONMENT PVT LTD RENT,25000.00,,75000.00");
        var path = WriteTemp("total_vendor.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            Assert.Single(res.Transactions);
            Assert.Contains("TOTAL ENVIRONMENT", res.Transactions[0].Narration);
            Assert.Equal(25000.00m, res.Transactions[0].Debit);
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    [Theory]
    [InlineData("9200.00", true)]   // rows fully explain the printed closing
    [InlineData("8500.00", false)]  // a ₹700 movement is missing between the two rows
    public async Task MissingRow_IsReportedAsBalanceBreak_AndStatementNotBalanced(string secondBalance, bool complete)
    {
        var csv = string.Join("\r\n",
            "Opening Balance : 10000.00",
            "Date,Narration,Debit,Credit,Balance",
            "01/04/2025,UPI DR A,500.00,,9500.00",
            $"03/04/2025,UPI DR C,300.00,,{secondBalance}",
            $"Closing Balance : {secondBalance}");
        var path = WriteTemp("gap.csv", csv);
        try
        {
            var res = await BankStatementParser.ParseAsync(path);
            Assert.Equal(2, res.Transactions.Count);
            Assert.Equal(10000.00m, res.Balances.StatementOpening);
            Assert.True(res.Balances.OpeningPrinted);
            Assert.Equal(complete, res.Balances.StatementBalanced);
            Assert.Equal(!complete, res.Transactions[1].HasBalanceBreak);
            Assert.False(res.Transactions[0].HasBalanceBreak);
        }
        finally { Directory.Delete(Path.GetDirectoryName(path)!, true); }
    }

    // ------------------------------------------------------------------ "Group similar"
    [Fact]
    public void Grouping_SamePartyDirectionAndLedgerOnly_AndAnotherLedgerTakesARowOut()
    {
        BankTransactionRow R(string id, string type, string ledger) => new()
        {
            RowId = id, TxnType = type, SelectedLedger = ledger, Amount = 100m,
            PartyKey = LedgerClassifier.ExtractCounterpartyKey("UPI/DR/123456/ZOMATO LTD/zomato@hdfc")
        };
        var a = R("1", "DR", "Staff Welfare");
        var b = R("2", "DR", "Staff Welfare");
        var c = R("3", "CR", "Staff Welfare");        // other direction → other group
        var d = R("4", "DR", "Office Expenses");      // other ledger → other group
        Assert.Equal(a.GroupLabel, b.GroupLabel);
        Assert.NotEqual(a.GroupLabel, c.GroupLabel);
        Assert.NotEqual(a.GroupLabel, d.GroupLabel);

        // giving a row another ledger moves it out of the group (and the grid is told)
        var changed = new List<string?>();
        b.PropertyChanged += (_, e) => changed.Add(e.PropertyName);
        b.SelectedLedger = "Office Expenses";
        Assert.Contains(nameof(BankTransactionRow.GroupLabel), changed);
        Assert.Equal(d.GroupLabel, b.GroupLabel);

        // "Take out of group" / "Put back"
        a.KeepSeparate = true;
        Assert.NotEqual(a.GroupLabel, R("5", "DR", "Staff Welfare").GroupLabel);
        a.KeepSeparate = false;
        Assert.Equal(a.GroupLabel, R("5", "DR", "Staff Welfare").GroupLabel);

        // contra, split and posted rows always stand alone
        var contra = R("6", "DR", "Staff Welfare"); contra.IsContra = true;
        var posted = R("7", "DR", "Staff Welfare"); posted.PostStatus = "DONE";
        var split = R("8", "DR", "Staff Welfare"); split.Splits = [new() { Ledger = "A", Amount = 60m }, new() { Ledger = "B", Amount = 40m }];
        Assert.All(new[] { contra, posted, split }, r => Assert.NotEqual(a.GroupLabel, r.GroupLabel));
    }

    [Fact]
    public void GroupHeader_ShowsCountTotalAndRowsToCheck()
    {
        var rows = new List<BankTransactionRow>
        {
            new() { Amount = 1234.50m }, new() { Amount = 100000m, NeedsReview = true }, new() { Amount = 0.50m }
        };
        var text = (string)new GroupSummaryConverter().Convert([rows, 3], typeof(string), null, CultureInfo.InvariantCulture);
        Assert.Equal("3 entries   •   ₹1,01,235.00   •   ⚠ 1 to check", text);
        Assert.True((bool)new GroupOpenConverter().Convert(rows, typeof(bool), null, CultureInfo.InvariantCulture));
    }

    // ------------------------------------------------------------------ anonymised copy for support
    [Theory]
    [InlineData("TRANSFER", "TRANSFER")]            // banking words stay
    [InlineData("05-Apr-2025", "05-Apr-2025")]      // dates stay
    [InlineData("1,23,456.78", "1,23,456.78")]      // amounts stay
    [InlineData("Withdrawal", "Withdrawal")]        // column headings stay
    [InlineData("910", "910")]                      // short numbers (masked a/c, branch code, day) stay
    public void Anonymiser_KeepsWhatTheParserNeeds(string word, string expected) =>
        Assert.Equal(expected, StatementAnonymiser.AnonymiseWord(word, "salt"));

    [Fact]
    public void Anonymiser_ReplacesNamesAndLongNumbers_ConsistentlyWithinAFile()
    {
        var a = StatementAnonymiser.AnonymiseWord("RAJESH", "s1");
        Assert.NotEqual("RAJESH", a);
        Assert.Equal(6, a.Length);
        Assert.Equal(a, StatementAnonymiser.AnonymiseWord("Rajesh".ToUpperInvariant(), "s1"));      // same name → same dummy
        Assert.NotEqual(a, StatementAnonymiser.AnonymiseWord("RAJESH", "s2"));                     // another file → different
        var acc = StatementAnonymiser.AnonymiseWord("00000044078706687", "s1");
        Assert.Equal(17, acc.Length);
        Assert.NotEqual("00000044078706687", acc);
        Assert.StartsWith("SBIN0", StatementAnonymiser.AnonymiseWord("SBIN0016103", "s1"));       // bank code survives
        Assert.Equal("UPI/DR/", StatementAnonymiser.AnonymiseWord("UPI/DR/509169091433/RAJ", "s1")[..7]);
    }

    [Theory]
    [InlineData("sbi_cc_narrow_statement.pdf", "00000044078706687")]
    [InlineData("hdfc_statement.pdf", "")]
    [InlineData("sbi_new_statement.pdf", "")]
    [InlineData("axis_statement.pdf", "")]
    public async Task Anonymiser_CopyParsesExactlyLikeTheOriginal_AndHidesAccountNumbers(string file, string secret)
    {
        var src = Path.Combine(FixtureDir, file);
        var dir = Path.Combine(Path.GetTempPath(), "abse_anon_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        try
        {
            var copy = Path.Combine(dir, file);
            File.WriteAllBytes(copy, StatementAnonymiser.Anonymise(src, null));
            var orig = await BankStatementParser.ParseAsync(src);
            var anon = await BankStatementParser.ParseAsync(copy);
            Assert.Equal(orig.Transactions.Select(t => (t.TxnDate, t.TxnType, t.Amount)), anon.Transactions.Select(t => (t.TxnDate, t.TxnType, t.Amount)));
            Assert.Equal(orig.Balances.StatementOpening, anon.Balances.StatementOpening);
            Assert.Equal(orig.Balances.StatementClosing, anon.Balances.StatementClosing);
            Assert.Equal(orig.Balances.StatementBalanced, anon.Balances.StatementBalanced);
            using var doc = UglyToad.PdfPig.PdfDocument.Open(copy);
            var text = string.Join(" ", doc.GetPages().Select(p => p.Text));
            if (secret.Length > 0) Assert.DoesNotContain(secret, text);
            // every narration word the anonymiser replaces (names, places, vendors) must be gone from the copy
            var hidden = orig.Transactions.SelectMany(t => t.Narration.Split(' '))
                .Where(w => w.Length >= 6 && w.All(char.IsLetter) && StatementAnonymiser.AnonymiseWord(w, "probe") != w)
                .Distinct().Take(20).ToList();
            Assert.NotEmpty(hidden);
            Assert.All(hidden, w => Assert.DoesNotContain(w, text));
        }
        finally { try { Directory.Delete(dir, true); } catch { } }
    }

    // ------------------------------------------------------------------ money is decimal: exact to the paisa
    [Fact]
    public void Money_IsExact_NoFloatingPointDrift()
    {
        // 0.1 + 0.2 is 0.30000000000000004 as double; as decimal it is exactly 0.3
        var rows = Enumerable.Range(0, 10_000).Select(_ => new BankTransactionRow { TxnType = "DR", Amount = 0.10m, Debit = 0.10m }).ToList();
        Assert.Equal(1000.00m, rows.Sum(r => r.Debit));
        Assert.Equal(0.30m, BankStatementParser.ParseIndianAmount("0.10").amt + BankStatementParser.ParseIndianAmount("0.20").amt);
        Assert.Equal(98765432109.87m, BankStatementParser.ParseIndianAmount("9,87,65,43,21,09.87").amt);
    }

    // ------------------------------------------------------------------ exact party from Tally bank details
    private static readonly List<PartyBankInfo> Parties =
    [
        new() { Ledger = "Om Prakash Sahoo", AccountNumbers = ["42583415180"], Ifscs = ["SBIN0016103"] },
        new() { Ledger = "Rajesh Traders", AccountNumbers = ["50200012345910"], Ifscs = ["HDFC0001234"] },
        new() { Ledger = "Rajesh Steel", AccountNumbers = ["918020011223910"], Ifscs = ["UTIB0000456"] },
        new() { Ledger = "Dibya Ranjan Behera", Favouring = "DIBYA RANJAN BEHERA" },
        new() { Ledger = "Laxmi Dora" },
        new() { Ledger = "Laxmi Enterprises" },
        new() { Ledger = "Amazon" },
    ];

    [Theory]
    [InlineData("TO TRANSFER- INB own acc- TRANSFER TO 42583415180 Mr. OM PRAKASH SAHOO /", "Om Prakash Sahoo", "tally_bank_account")]
    [InlineData("TO TRANSFER-IMPS/631111/HDFC/xx910/service", "Rajesh Traders", "tally_bank_masked")]          // xx910 + HDFC → one party
    [InlineData("NEFT DR-UTIB0000456-RAJESH STEEL-XXXXXXXXXXX3910", "Rajesh Steel", "tally_bank_masked")]
    [InlineData("TO TRANSFER INB Rent Payment- TO 20229125206 Mr. DIBYA RANJAN BEHER /", "Dibya Ranjan Behera", "tally_party_name")] // truncated surname
    [InlineData("UPI/DR/631234/LAXMI DORA/SBIN/laxmi@oksbi", "Laxmi Dora", "tally_party_name")]
    public void PartyMatcher_FindsTheExactParty(string narration, string ledger, string source)
    {
        var m = PartyMatcher.Match(narration, Parties);
        Assert.NotNull(m);
        Assert.Equal(ledger, m!.Value.ledger);
        Assert.Equal(source, m.Value.source);
    }

    [Theory]
    [InlineData("IMPS/631111/xx910/service")]                // masked digits fit two parties and no bank code → not sure
    [InlineData("UPI/DR/AMAZON PAY/amazon@apl")]               // one short word is too weak to call it a party
    [InlineData("CASH WITHDRAWAL ATM 1234")]
    public void PartyMatcher_NeverGuesses(string narration) => Assert.Null(PartyMatcher.Match(narration, Parties));

    [Fact]
    public void PartyBankDetails_AreReadFromTallyLedgerXml()
    {
        var el = System.Xml.Linq.XElement.Parse("""
            <LEDGER NAME="Rajesh Traders"><PARENT>Sundry Creditors</PARENT>
              <PAYMENTDETAILS.LIST><IFSCODE>hdfc0001234</IFSCODE><ACCOUNTNUMBER>5020 0012 345910</ACCOUNTNUMBER><PAYMENTFAVOURING>RAJESH TRADERS</PAYMENTFAVOURING></PAYMENTDETAILS.LIST>
            </LEDGER>
            """);
        var info = TallyConnector.ReadPartyBankInfo("Rajesh Traders", el);
        Assert.Equal(new[] { "50200012345910" }, info.AccountNumbers);
        Assert.Equal(new[] { "HDFC0001234" }, info.Ifscs);
        Assert.Equal("RAJESH TRADERS", info.Favouring);
    }

    // ------------------------------------------------------------------ confidence floor
    [Fact]
    public void ConfidenceFloor_HoldsBackGuesses_AndChoosingALedgerTicksTheRowAgain()
    {
        var sure = new BankTransactionRow { SelectedLedger = "Rent", Confidence = 0.85, PredictionSource = "ml" };
        var unsure = new BankTransactionRow { SelectedLedger = "Rent", Confidence = 0.41, PredictionSource = "ml" };
        var suspense = new BankTransactionRow { SelectedLedger = "Suspense Account", Confidence = 0.9, PredictionSource = "ml" };
        var empty = new BankTransactionRow { SelectedLedger = "", Confidence = 0.3, PredictionSource = "contra_detector_ambiguous" };
        var posted = new BankTransactionRow { SelectedLedger = "Rent", Confidence = 0.2, PostStatus = "DONE" };
        var rows = new List<BankTransactionRow> { sure, unsure, suspense, empty, posted };

        Assert.Equal(3, ReviewPolicy.HoldBackGuesses(rows));
        Assert.True(sure.Selected);
        Assert.All(new[] { unsure, suspense, empty }, r => { Assert.False(r.Selected); Assert.True(r.NeedsReview); });
        Assert.StartsWith("⚠ Check ledger", unsure.StatusSummary);

        // the user picks the ledger → ticked again automatically
        unsure.SelectedLedger = "Office Rent"; unsure.Confidence = 1.0; unsure.PredictionSource = "user_manual";
        ReviewPolicy.ConfirmReviewed(unsure);
        Assert.True(unsure.Selected);
        Assert.False(unsure.NeedsReview);

        // choosing Suspense explicitly is still not a real ledger → stays held back
        suspense.PredictionSource = "user_manual"; suspense.Confidence = 1.0;
        ReviewPolicy.ConfirmReviewed(suspense);
        Assert.False(suspense.Selected);

        // a row that is a duplicate of a Tally entry is never re-ticked by confirming its ledger
        var dupe = new BankTransactionRow { SelectedLedger = "X", Confidence = 0.2, PredictionSource = "ml", OverlapStatus = "OVERLAP_TALLY_EXISTING" };
        ReviewPolicy.HoldBackGuesses([dupe]);
        dupe.PredictionSource = "user_manual"; dupe.Confidence = 1;
        ReviewPolicy.ConfirmReviewed(dupe);
        Assert.False(dupe.Selected);
    }

    // ------------------------------------------------------------------ split entries
    private static BankTransactionRow SplitRow(string type, params (string ledger, decimal amt)[] lines) => new()
    {
        RowId = "s1", TxnDate = "2026-10-05", DisplayDate = "05-Oct-2026", TxnType = type, Amount = lines.Sum(l => l.amt),
        VoucherType = type == "DR" ? "Payment" : "Receipt", BankLedger = "AU Bank", SelectedLedger = lines[0].ledger,
        VoucherGuid = "ABSE-split0000000001", Narration = "RENT OCT + GST",
        Splits = lines.Select(l => new LedgerSplit { Ledger = l.ledger, Amount = l.amt }).ToList()
    };

    [Fact]
    public void SplitEntry_PostsOneBankLineAndOneLinePerLedger_Balanced()
    {
        var conn = new TallyConnector("http://localhost:9000", "Co") { PartyLedgers = new(StringComparer.OrdinalIgnoreCase) { "Sharma Properties" } };
        var row = SplitRow("DR", ("Sharma Properties", 10000.00m), ("Input CGST", 900.00m), ("Input SGST", 900.00m));
        Assert.True(row.IsSplit);
        var xml = conn.BuildVouchersXml([row]);
        var doc = System.Xml.Linq.XDocument.Parse(xml);
        var entries = doc.Descendants("ALLLEDGERENTRIES.LIST").Select(e => (name: e.Element("LEDGERNAME")!.Value, amt: double.Parse(e.Element("AMOUNT")!.Value, CultureInfo.InvariantCulture))).ToList();
        Assert.Equal(4, entries.Count);
        Assert.Equal(11800.00, entries.Single(e => e.name == "AU Bank").amt, 2);           // Payment: bank credited (+)
        Assert.Equal(-10000.00, entries.Single(e => e.name == "Sharma Properties").amt, 2);
        Assert.Equal(-900.00, entries.Single(e => e.name == "Input CGST").amt, 2);
        Assert.Equal(0.0, entries.Sum(e => e.amt), 2);                                      // voucher balances
        // the party line is "On Account" so Tally's outstanding stays complete; tax lines have no bill lines
        Assert.Single(doc.Descendants("BILLALLOCATIONS.LIST"));
        Assert.Equal(new[] { "Sharma Properties", "Input CGST", "Input SGST" }, row.PostingLedgers);
    }

    [Fact]
    public void SplitEntry_ThatDoesNotAddUp_IsNeverSent()
    {
        var conn = new TallyConnector("http://localhost:9000", "Co");
        var row = SplitRow("CR", ("Customer A", 600.00m), ("Customer B", 400.00m));
        row.Amount = 1000.01m;
        Assert.Throws<InvalidOperationException>(() => conn.BuildVouchersXml([row]));
    }

    // ------------------------------------------------------------------ saved layouts ("Teach Columns")
    private static LayoutTemplate TemplateFromTruth(string file, string name = "Co-op test layout")
    {
        using var truth = JsonDocument.Parse(File.ReadAllText(Path.Combine(FixtureDir, file + ".json")));
        var tp = truth.RootElement.GetProperty("template");
        return new LayoutTemplate
        {
            Name = name,
            Boundaries = tp.GetProperty("boundaries").EnumerateArray().Select(x => x.GetDouble()).ToList(),
            Roles = tp.GetProperty("roles").EnumerateArray().Select(x => x.GetString()!).ToList()
        };
    }

    private static void AssertRowsExact(string file, ParsedStatementResult res)
    {
        using var truth = JsonDocument.Parse(File.ReadAllText(Path.Combine(FixtureDir, file + ".json")));
        var t = truth.RootElement;
        var expected = t.GetProperty("rows").EnumerateArray()
            .Select(r => $"{r.GetProperty("date").GetString()}|{r.GetProperty("type").GetString()}|{r.GetProperty("amount").GetDouble().ToString("F2", CultureInfo.InvariantCulture)}")
            .OrderBy(x => x, StringComparer.Ordinal).ToList();
        var actual = res.Transactions.Select(r => $"{r.TxnDate}|{r.TxnType}|{r.Amount.ToString("F2", CultureInfo.InvariantCulture)}")
            .OrderBy(x => x, StringComparer.Ordinal).ToList();
        Assert.Equal(expected, actual);
        Assert.Equal(t.GetProperty("opening").GetDecimal(), res.Balances.StatementOpening!.Value, 2);
        Assert.True(res.Balances.StatementBalanced);
        Assert.Empty(res.Balances.CompletenessIssues);
    }

    [Fact]
    public void SavedLayout_ReadsStatementWithNoHeadingsAndUnusualColumnOrder_Exactly()
    {
        // Date | Particulars | Balance | Withdrawal | Deposit, no headings, cover page without a table, "Page x of 3" footers
        const string f = "coop_noheader_statement.pdf";
        var res = BankStatementParser.ParsePdfWithTemplate(Path.Combine(FixtureDir, f), null, TemplateFromTruth(f));
        Assert.Equal(40, res.Transactions.Count);
        AssertRowsExact(f, res);
        Assert.Equal("Co-op test layout", res.LayoutTemplateUsed);
    }

    [Fact]
    public async Task SavedLayout_IsPickedAutomatically_WhenTheAutomaticReadIsNotProven()
    {
        const string f = "coop_noheader_statement.pdf";
        var auto = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, f));
        Assert.False(BankStatementParser.IsProvenGood(auto));            // the automatic guess is wrong — and is caught
        Assert.NotEqual("", auto.Balances.BlockReason);                    // so it could never be posted

        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, f), null, [TemplateFromTruth(f)]);
        Assert.Equal("Co-op test layout", res.LayoutTemplateUsed);
        AssertRowsExact(f, res);
        Assert.Contains("Saved layouts tried", res.DiagnosticReport);
    }

    [Fact]
    public async Task SavedLayout_ThatDoesNotReconcile_NeverReplacesAProvenAutomaticRead()
    {
        const string f = "sbi_cc_narrow_statement.pdf";
        // a wrongly taught layout: Debit and Credit swapped
        var bad = new LayoutTemplate
        {
            Name = "wrong", Bank = "SBI",
            Boundaries = new[] { 30.0, 72, 114, 250, 330, 372, 427, 482, 565 }.Select(x => x / 595.2755905511812).ToList(),
            Roles = ["date", "value_date", "narration", "ref_no", "ignore", "credit", "debit", "balance"]
        };
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, f), null, [bad]);
        Assert.Equal("", res.LayoutTemplateUsed);
        Assert.Equal(48, res.Transactions.Count);
        Assert.True(BankStatementParser.IsProvenGood(res));
    }

    [Fact]
    public async Task SavedLayout_WithMatchingHeading_IsUsed_AndHeadingSignatureIsLearned()
    {
        const string f = "sbi_cc_narrow_centred.pdf";
        var path = Path.Combine(FixtureDir, f);
        var t = new LayoutTemplate
        {
            Name = "SBI CC narrow", Bank = "SBI",
            Boundaries = new[] { 30.0, 72, 114, 250, 330, 372, 427, 482, 565 }.Select(x => x / 595.2755905511812).ToList(),
            Roles = ["date", "value_date", "narration", "ref_no", "ignore", "debit", "credit", "balance"]
        };
        t.HeaderSignature = BankStatementParser.ComputeHeaderSignature(path, null, t, 2); // learned from page 2
        foreach (var word in new[] { "txn", "date", "debit", "credit", "balance" }) Assert.Contains(word, t.HeaderSignature.Split(' '));
        var res = await BankStatementParser.ParseAsync(path, null, [t]);
        Assert.Equal("SBI CC narrow", res.LayoutTemplateUsed);
        Assert.Equal(48, res.Transactions.Count);
        Assert.True(BankStatementParser.IsProvenGood(res));
    }

    [Fact]
    public void TeachColumns_SuggestsAPageWithTheTable_NotTheCoverPage()
    {
        // page 1 is a cover/summary page without any table: the window must open on a page that has the transactions
        var snap = BankStatementParser.ReadPdfLayout(Path.Combine(FixtureDir, "coop_noheader_statement.pdf"), null);
        Assert.Equal(3, snap.Pages.Count);
        Assert.Equal(0, snap.Pages[0].DatedLineCount);
        Assert.NotEqual(0, snap.SuggestedPageIndex);
        Assert.True(snap.Pages[snap.SuggestedPageIndex].DatedLineCount >= 15);
        Assert.NotEmpty(snap.Pages[snap.SuggestedPageIndex].Words);

        // a statement with recognised headings comes pre-filled with its detected columns
        var sbi = BankStatementParser.ReadPdfLayout(Path.Combine(FixtureDir, "sbi_cc_narrow_statement.pdf"), null);
        var p = sbi.Pages[sbi.SuggestedPageIndex];
        Assert.Equal(p.SuggestedEdges.Count, p.SuggestedRoles.Count + 1);
        Assert.Contains("date", p.SuggestedRoles);
        Assert.Contains("balance", p.SuggestedRoles);
    }

    [Fact]
    public void LayoutTemplates_AndStatementHistory_RoundTripThroughTheSharedDatabase()
    {
        WithDb(db =>
        {
            var id = db.SaveLayoutTemplate(new LayoutTemplate { Name = "X", Bank = "SBI", HeaderSignature = "date debit", Boundaries = [0.1, 0.5, 0.9], Roles = ["date", "balance"] });
            var all = db.GetLayoutTemplates();
            var t = Assert.Single(all);
            Assert.Equal(id, t.Id);
            Assert.Equal(new[] { 0.1, 0.5, 0.9 }, t.Boundaries);
            Assert.Equal(new[] { "date", "balance" }, t.Roles);
            db.DeleteLayoutTemplate(id);
            Assert.Empty(db.GetLayoutTemplates());

            db.RecordStatement(new StatementHistoryEntry { CompanyName = "Co", BankLedger = "SBI CA", FromDate = "2026-10-01", ToDate = "2026-10-31", Opening = 100, Closing = 250, SourceFile = "oct.pdf" });
            db.RecordStatement(new StatementHistoryEntry { CompanyName = "Co", BankLedger = "SBI CA", FromDate = "2026-09-01", ToDate = "2026-09-30", Opening = 50, Closing = 100, SourceFile = "sep.pdf" });
            var prev = db.GetPreviousStatement("Co", "SBI CA", "2026-11-01");
            Assert.NotNull(prev);
            Assert.Equal("oct.pdf", prev!.SourceFile);
            Assert.Equal(250, prev.Closing, 2);
            Assert.Null(db.GetPreviousStatement("Co", "SBI CA", "2026-09-01"));   // nothing ends before September
            Assert.Null(db.GetPreviousStatement("Other Co", "SBI CA", "2026-11-01"));
        });
    }

    // ------------------------------------------------------------------ completeness self-checks
    private static StatementBalanceInfo Bal(decimal dr, decimal cr) => new() { TotalDebit = dr, TotalCredit = cr, StatementBalanced = true };
    private static List<BankTransactionRow> Rows(int dr, int cr) =>
        Enumerable.Range(0, dr).Select(_ => new BankTransactionRow { TxnType = "DR" })
            .Concat(Enumerable.Range(0, cr).Select(_ => new BankTransactionRow { TxnType = "CR" })).ToList();

    [Fact]
    public void Completeness_PrintedTotalsMustMatch_ElsePostingIsBlocked()
    {
        var ok = Bal(12345.50m, 999.00m);
        BankStatementParser.ApplyCompletenessChecks(ok, "Total Debits : 12,345.50\nTotal Credits : 999.00", Rows(3, 1), null);
        Assert.Empty(ok.CompletenessIssues);
        Assert.Equal("", ok.BlockReason);

        // a missing FIRST/LAST row keeps the running balance consistent — the printed total still catches it
        var bad = Bal(10345.50m, 999.00m);
        BankStatementParser.ApplyCompletenessChecks(bad, "TOTAL WITHDRAWALS  Rs. 12,345.50\nTOTAL DEPOSITS 999.00", Rows(2, 1), null);
        Assert.Single(bad.CompletenessIssues);
        Assert.Contains("12,345.50", bad.BlockReason);

        // vendor names are not totals; page-wise sub-totals that add up are fine
        var vendor = Bal(500, 0);
        BankStatementParser.ApplyCompletenessChecks(vendor, "POS TOTAL DEBIT CARD SERVICES 1,500.00", Rows(1, 0), null);
        Assert.Null(vendor.PrintedTotalDebit);
        var pages = Bal(300, 0);
        BankStatementParser.ApplyCompletenessChecks(pages, "Total Debit: 100.00\n...\nTotal Debit: 200.00", Rows(2, 0), null);
        Assert.Empty(pages.CompletenessIssues);
    }

    [Fact]
    public void Completeness_HdfcSummaryCounts_AndPageNumbers()
    {
        var b = Bal(1500.00m, 700.00m);
        var text = "STATEMENT SUMMARY :-\nOpening Balance Dr Count Cr Count Debits Credits Closing Bal\n10,000.00 3 1 1,500.00 700.00 9,200.00";
        BankStatementParser.ApplyCompletenessChecks(b, text, Rows(3, 1), null);
        Assert.Equal(3, b.PrintedDebitCount);
        Assert.Equal(1, b.PrintedCreditCount);
        Assert.Empty(b.CompletenessIssues);
        BankStatementParser.ApplyCompletenessChecks(b, text, Rows(2, 1), null);   // one debit row lost
        Assert.Contains(b.CompletenessIssues, i => i.Contains("3 debit entries"));

        var missing = Bal(0, 0);
        BankStatementParser.ApplyCompletenessChecks(missing, "", Rows(1, 0), ["... Page 1 of 3", "... Page 2 of 3"]);
        Assert.Contains(missing.CompletenessIssues, i => i.Contains("pages are missing"));
        var dup = Bal(0, 0);
        BankStatementParser.ApplyCompletenessChecks(dup, "", Rows(1, 0), ["Page 1 of 2", "Page 2 of 2", "Page 2 of 2"]);
        Assert.Contains(dup.CompletenessIssues, i => i.Contains("appears twice"));
        var fine = Bal(0, 0);
        BankStatementParser.ApplyCompletenessChecks(fine, "", Rows(1, 0), ["Page 1 of 2 … Page 1 of 2", "Page 2 of 2"]);
        Assert.Empty(fine.CompletenessIssues);
    }

    [Fact]
    public async Task Completeness_HdfcFixture_PrintedSummaryIsReadAndAgrees()
    {
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, "hdfc_statement.pdf"));
        Assert.NotNull(res.Balances.PrintedTotalDebit);
        Assert.Equal(res.Balances.TotalDebit, res.Balances.PrintedTotalDebit!.Value, 2);
        Assert.Equal(res.Balances.TotalCredit, res.Balances.PrintedTotalCredit!.Value, 2);
        Assert.Equal(res.Transactions.Count(t => t.TxnType == "DR"), res.Balances.PrintedDebitCount);
        Assert.Empty(res.Balances.CompletenessIssues);
    }

    [Fact]
    public void BlockReason_IsSetWhenTheStatementDoesNotReconcile()
    {
        var b = new StatementBalanceInfo { StatementBalanced = false, StatementDiff = 1426 };
        Assert.Contains("do not reconcile", b.BlockReason);
        Assert.Equal("", new StatementBalanceInfo { StatementBalanced = null }.BlockReason);   // unprovable: confirm, not block
    }

    // ------------------------------------------------------------------ Tally voucher read: ledger-scoped, date-filtered
    private const string OneAuVoucher = """
        <ENVELOPE><COLLECTION><VOUCHER REMOTEID="ABSE-1234567890abcdef"><DATE>20261027</DATE><VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
        <VOUCHERNUMBER>36</VOUCHERNUMBER><GUID>ABSE-1234567890abcdef</GUID><NARRATION>UPI</NARRATION>
        <ALLLEDGERENTRIES.LIST><LEDGERNAME>Travelling &amp; Conveyance</LEDGERNAME><AMOUNT>-2624.50</AMOUNT></ALLLEDGERENTRIES.LIST>
        <ALLLEDGERENTRIES.LIST><LEDGERNAME>AU Bank</LEDGERNAME><AMOUNT>2624.50</AMOUNT></ALLLEDGERENTRIES.LIST></VOUCHER></COLLECTION></ENVELOPE>
        """;

    private static async Task<(bool ok, List<TallyExistingVoucher> v, List<string> requests)> WithFakeTally(Func<string, string> answer, Func<TallyConnector, Task<(bool, List<TallyExistingVoucher>)>> call)
    {
        int port = new Random().Next(20000, 60000);
        using var listener = new System.Net.HttpListener();
        listener.Prefixes.Add($"http://localhost:{port}/");
        listener.Start();
        var requests = new List<string>();
        var cts = new CancellationTokenSource();
        var server = Task.Run(async () =>
        {
            while (!cts.IsCancellationRequested)
            {
                System.Net.HttpListenerContext ctx;
                try { ctx = await listener.GetContextAsync(); } catch { break; }
                using var rd = new StreamReader(ctx.Request.InputStream);
                var body = await rd.ReadToEndAsync();
                lock (requests) requests.Add(body);
                var bytes = System.Text.Encoding.UTF8.GetBytes(answer(body));
                ctx.Response.ContentType = "text/xml";
                await ctx.Response.OutputStream.WriteAsync(bytes);
                ctx.Response.Close();
            }
        });
        try
        {
            var (ok, v) = await call(new TallyConnector($"http://localhost:{port}", "Co", 8));
            return (ok, v, requests);
        }
        finally { cts.Cancel(); listener.Stop(); }
    }

    [Fact]
    public async Task TallyRead_AsksOnlyForTheBankLedgersVouchers_FilteredByDateInsideTally()
    {
        var (ok, v, reqs) = await WithFakeTally(_ => OneAuVoucher,
            c => c.FetchExistingVouchersExAsync("2026-10-27", "2026-10-30", padDays: 2, bankLedger: "AU Bank"));
        Assert.True(ok);
        Assert.Single(reqs);                                   // no company-wide dump when the ledger read works
        Assert.Contains("<TYPE>Vouchers : Ledger</TYPE>", reqs[0]);
        Assert.Contains("<CHILDOF>AU Bank</CHILDOF>", reqs[0]);
        Assert.Contains("<FILTER>ABSEInRange</FILTER>", reqs[0]);
        Assert.Contains("<SVFROMDATE>20261025</SVFROMDATE>", reqs[0]);
        var tv = Assert.Single(v);
        Assert.Equal("36", tv.VoucherNumber);
        Assert.Equal("ABSE-1234567890abcdef", tv.RemoteId);
        Assert.Equal(2624.50m, tv.LedgerAmounts["AU Bank"], 2);
    }

    [Fact]
    public async Task TallyRead_FallsBackToCompanyWideRead_WhenLedgerReadErrorsOrIsEmpty()
    {
        // Older Tally: ledger-scoped collection answers with an error -> company-wide (still date-filtered) read
        var (ok, v, reqs) = await WithFakeTally(body => body.Contains("Vouchers : Ledger") ? "<ENVELOPE><LINEERROR>Unknown</LINEERROR></ENVELOPE>" : OneAuVoucher,
            c => c.FetchExistingVouchersExAsync("2026-10-27", "2026-10-30", bankLedger: "AU Bank"));
        Assert.True(ok);
        Assert.Equal(2, reqs.Count);
        Assert.Contains("<TYPE>Voucher</TYPE>", reqs[1]);
        Assert.Contains("<FILTER>ABSEInRange</FILTER>", reqs[1]);
        Assert.Single(v);

        // Ledger read returns NOTHING for the bank: never trust that as "nothing in Tally" — confirm company-wide
        (ok, v, reqs) = await WithFakeTally(body => body.Contains("Vouchers : Ledger") ? "<ENVELOPE><COLLECTION></COLLECTION></ENVELOPE>" : OneAuVoucher,
            c => c.FetchExistingVouchersExAsync("2026-10-27", "2026-10-30", bankLedger: "AU Bank"));
        Assert.True(ok);
        Assert.Equal(2, reqs.Count);
        Assert.Single(v);
    }

    [Fact]
    public async Task SbiCcNarrow_OpeningFromBalanceAsOn_AndWrappedDatesAndAmounts()
    {
        var res = await BankStatementParser.ParseAsync(Path.Combine(FixtureDir, "sbi_cc_narrow_centred.pdf"));
        Assert.Equal(48, res.Transactions.Count);
        Assert.True(res.Balances.OpeningPrinted);
        Assert.Equal(-3847078.68m, res.Balances.StatementOpening!.Value, 2);
        Assert.Contains(res.Transactions, t => t.TxnType == "CR" && Math.Abs(t.Amount - 1000000.00m) < 0.005m); // "10,00,000." + "00"
        Assert.DoesNotContain(res.Transactions, t => Math.Abs(t.Amount - 16103) < 0.005m);                      // branch code is not money
        Assert.All(res.Transactions, t => Assert.True(t.Narration.Length < 400, t.Narration));
        Assert.True(res.Balances.StatementBalanced);
    }

    // ------------------------------------------------------------------ already in Tally (pre-post guard)
    private static TallyExistingVoucher TallyPay(string date, decimal amt, string party, string bank = "AU Bank", string guid = "", string no = "", bool receipt = false) => new()
    {
        Date = date, VoucherType = receipt ? "Receipt" : "Payment", Guid = guid, VoucherNumber = no,
        Ledgers = [party, bank],
        // Tally XML signs: Payment credits the bank (+), Receipt debits the bank (−)
        LedgerAmounts = new(StringComparer.OrdinalIgnoreCase) { [bank] = receipt ? -amt : amt, [party] = receipt ? amt : -amt },
        Amount = amt
    };

    private static BankTransactionRow StmtRow(string id, string date, decimal amt, string ledger, string guid = "", string type = "DR") => new()
    {
        RowId = id, SourceFile = "au.pdf", TxnDate = date, TxnType = type, Amount = amt,
        Debit = type == "DR" ? amt : 0, Credit = type == "CR" ? amt : 0,
        SelectedLedger = ledger, BankLedger = "AU Bank", VoucherGuid = guid, Narration = "UPI/" + id
    };

    [Fact]
    public void PrePostGuard_BlocksEntriesAlreadyInTally_ByVoucherIdAndByAmountDateDirection()
    {
        // The AU Bank case: 5 payments already posted (Vch 34–38); the same statement was posted again.
        var live = new List<TallyExistingVoucher>
        {
            TallyPay("2026-10-27", 2624.50m, "Travelling & Conveyance", guid: "ABSE-aaaaaaaaaaaaaaaa", no: "36"),
            TallyPay("2026-10-27", 2294.50m, "Travelling & Conveyance", no: "37"),
            TallyPay("2026-10-27", 13428.00m, "Investments - IPO", no: "38"),
            TallyPay("2026-10-28", 1178.82m, "Internet Exp", no: "35"),
            TallyPay("2026-10-30", 625.80m, "Food", no: "34"),
        };
        var rows = new List<BankTransactionRow>
        {
            StmtRow("1", "2026-10-27", 2624.50m, "Travelling & Conveyance", guid: "ABSE-aaaaaaaaaaaaaaaa"),
            StmtRow("2", "2026-10-27", 2294.50m, "Travelling & Conveyance", guid: "ABSE-bbbbbbbbbbbbbbbb"),
            StmtRow("3", "2026-10-27", 13428.00m, "Investments - IPO"),
            StmtRow("4", "2026-10-28", 1178.82m, "Internet Exp"),
            StmtRow("5", "2026-10-30", 625.80m, "Food"),
            StmtRow("6", "2026-10-30", 625.80m, "Food"),                 // a genuine SECOND ₹625.80 — only one is in Tally
            StmtRow("7", "2026-10-30", 999.00m, "Food"),                 // new
            StmtRow("8", "2026-10-27", 2624.50m, "Refund", type: "CR"),  // same amount but money IN — not the Tally payment
        };
        var hits = ContraDedupEngine.FindAlreadyInTally(rows, "AU Bank", live);
        var blocked = hits.Select(h => h.row.RowId).OrderBy(x => x).ToList();
        Assert.Equal(new[] { "1", "2", "3", "4", "5" }, blocked);
        Assert.True(hits.Single(h => h.row.RowId == "1").byId);
        Assert.Equal("36", hits.Single(h => h.row.RowId == "1").voucher.VoucherNumber);
    }

    [Fact]
    public void PrePostGuard_DoesNotBlock_OtherBankLedger_OrDatesTooFarApart()
    {
        var live = new List<TallyExistingVoucher>
        {
            TallyPay("2026-10-27", 500, "Rent", bank: "HDFC Bank"),
            TallyPay("2026-10-20", 700, "Rent"),
        };
        var rows = new List<BankTransactionRow>
        {
            StmtRow("1", "2026-10-27", 500, "Rent"),
            StmtRow("2", "2026-10-27", 700, "Rent"),
        };
        Assert.Empty(ContraDedupEngine.FindAlreadyInTally(rows, "AU Bank", live));
    }

    [Fact]
    public void Analyze_FlagsRowWhoseVoucherIdIsAlreadyInTally_EvenIfAmountReadDiffers()
    {
        WithDb(db =>
        {
            var engine = new ContraDedupEngine(db);
            var row = StmtRow("1", "2026-10-27", 2624.50m, "");
            row.Narration = "UPI/DR/123456/OLA";
            var probe = new List<BankTransactionRow> { row };
            engine.AnalyzeBatch(probe, "AU Bank", "Cash", null, "Co");
            var guid = probe[0].VoucherGuid;
            Assert.StartsWith("ABSE-", guid);

            // Tally has our voucher (same ID), but e.g. edited to a different amount afterwards
            var live = new List<TallyExistingVoucher> { TallyPay("2026-10-27", 2600.00m, "Travelling & Conveyance", guid: guid) };
            var again = new List<BankTransactionRow> { StmtRow("1", "2026-10-27", 2624.50m, "") };
            again[0].Narration = "UPI/DR/123456/OLA";
            engine.AnalyzeBatch(again, "AU Bank", "Cash", live, "Co");
            Assert.False(again[0].Selected);
            Assert.Equal("OVERLAP_TALLY_EXISTING", again[0].OverlapStatus);
            Assert.Equal("Travelling & Conveyance", again[0].MatchedTallyLedger);
        });
    }

    // ------------------------------------------------------------------ duplicate hashing
    [Fact]
    public void IdenticalSameDayRows_InOneStatement_AreBothKept_WithDistinctVoucherIds()
    {
        WithDb(db =>
        {
            var engine = new ContraDedupEngine(db);
            BankTransactionRow Row(string id) => new() { RowId = id, SourceFile = "a.csv", TxnDate = "2025-04-06", TxnType = "DR", Amount = 11.80m, Debit = 11.80m, Narration = "SMS ALERT CHARGES INCL GST" };
            var rows = new List<BankTransactionRow> { Row("1"), Row("2") };
            engine.AnalyzeBatch(rows, "SBI CA", "Cash", null, "Co");
            Assert.All(rows, r => Assert.True(r.Selected));
            Assert.All(rows, r => Assert.Equal("NEW", r.OverlapStatus));
            Assert.NotEqual(rows[0].TxnHash, rows[1].TxnHash);
            Assert.NotEqual(rows[0].VoucherGuid, rows[1].VoucherGuid);
            // occurrence #1 keeps the legacy hash so previously posted history still matches
            Assert.Equal(ContraDedupEngine.ComputeTxnHash("SBI CA", "2025-04-06", "DR", 11.80m, "", "SMS ALERT CHARGES INCL GST", "Co"), rows[0].TxnHash);
        });
    }

    [Fact]
    public void SameRow_InTwoOverlappingFiles_IsStillADuplicate()
    {
        WithDb(db =>
        {
            var engine = new ContraDedupEngine(db);
            BankTransactionRow Row(string id, string file) => new() { RowId = id, SourceFile = file, TxnDate = "2025-04-06", TxnType = "CR", Amount = 5000, Credit = 5000, Narration = "NEFT CR CLIENT", RefNo = "N12345" };
            var rows = new List<BankTransactionRow> { Row("1", "apr.csv"), Row("2", "apr_may.csv") };
            engine.AnalyzeBatch(rows, "SBI CA", "Cash", null, "Co");
            Assert.True(rows[0].Selected);
            Assert.False(rows[1].Selected);
            Assert.Equal("DUPLICATE_IN_BATCH", rows[1].OverlapStatus);
        });
    }

    [Fact]
    public void TxnHash_IsCultureInvariant()
    {
        var prev = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
            var a = ContraDedupEngine.ComputeTxnHash("B", "2025-04-01", "DR", 1234.5m, "", "X");
            CultureInfo.CurrentCulture = new CultureInfo("de-DE");
            var b = ContraDedupEngine.ComputeTxnHash("B", "2025-04-01", "DR", 1234.5m, "", "X");
            Assert.Equal(a, b);
        }
        finally { CultureInfo.CurrentCulture = prev; }
    }

    // ------------------------------------------------------------------ contra detection
    [Theory]
    [InlineData("UPI/DR/509212341234/VENDOR", false)]           // 12-digit UPI RRN containing the digits
    [InlineData("NEFT DR 2025 INVOICE 1234.00", false)]         // amount fragment
    [InlineData("TRF TO A/C XXXXXXXX1234", true)]
    [InlineData("IMPS TO **1234 SELF", true)]
    [InlineData("TRANSFER TO 50100012341234", true)]           // 14-digit account number
    [InlineData("TO OWN A/C 1234 HDFC", true)]
    public void AccountLast4Match_RequiresAnAccountReference(string narration, bool expected)
    {
        Assert.Equal(expected, ContraDedupEngine.NarrationMentionsAccount(narration, "1234"));
    }

    [Fact]
    public void AtmCharges_AreNotCashWithdrawals_AndAmbiguousSelfTransferNeedsUser()
    {
        WithDb(db =>
        {
            db.UpsertOwnBanksBatch("Co", [
                new OwnBankAccount { TallyLedgerName = "SBI CA", AccountNumber = "1111" },
                new OwnBankAccount { TallyLedgerName = "HDFC CA", AccountNumber = "2222" },
                new OwnBankAccount { TallyLedgerName = "ICICI CA", AccountNumber = "3333" }]);
            var engine = new ContraDedupEngine(db);
            var rows = new List<BankTransactionRow>
            {
                new() { RowId = "1", SourceFile = "f", TxnDate = "2025-04-01", TxnType = "DR", Amount = 236, Debit = 236, Narration = "ATM AMC CHG INCL GST" },
                new() { RowId = "2", SourceFile = "f", TxnDate = "2025-04-02", TxnType = "DR", Amount = 5000, Debit = 5000, Narration = "ATM WDL MI ROAD JAIPUR" },
                new() { RowId = "3", SourceFile = "f", TxnDate = "2025-04-03", TxnType = "DR", Amount = 90000, Debit = 90000, Narration = "SELF TRANSFER INB" },
                new() { RowId = "4", SourceFile = "f", TxnDate = "2025-04-04", TxnType = "DR", Amount = 70000, Debit = 70000, Narration = "TRF TO A/C XXXXXX2222" },
            };
            engine.AnalyzeBatch(rows, "SBI CA", "Cash", null, "Co");
            Assert.False(rows[0].IsContra);
            Assert.True(rows[1].IsContra); Assert.Equal("Cash", rows[1].ContraTargetLedger);
            Assert.True(rows[2].IsContra); Assert.Equal("", rows[2].ContraTargetLedger);  // 2 other banks → user must choose
            Assert.True(rows[3].IsContra); Assert.Equal("HDFC CA", rows[3].ContraTargetLedger);
        });
    }

    [Theory]
    [InlineData("NWD-416021XXXXXX7382-TR208703-LAKETOWN")]       // another bank's ATM (HDFC / Kotak / SBI style)
    [InlineData("EAW-416021XXXXXX7382-S1AWMU01-MUMBAI")]         // own-bank ATM (HDFC)
    [InlineData("CWDR/123456/ATM KOLKATA")]
    [InlineData("CSH WDL 7382 SALT LAKE")]
    public void AtmWithdrawal_CodesOfEveryBank_AreCashContra(string narration)
    {
        WithDb(db =>
        {
            // the masked card number ends 7382 like an own account: cash must still win
            db.UpsertOwnBanksBatch("Co", [new OwnBankAccount { TallyLedgerName = "Axis CA", AccountNumber = "9100007382" }]);
            var engine = new ContraDedupEngine(db);
            var rows = new List<BankTransactionRow>
            {
                new() { RowId = "1", SourceFile = "f", TxnDate = "2025-04-02", TxnType = "DR", Amount = 10000, Debit = 10000, Narration = narration },
                new() { RowId = "2", SourceFile = "f", TxnDate = "2025-04-03", TxnType = "DR", Amount = 23.60m, Debit = 23.60m, Narration = "NWD CHGS INCL GST" },
            };
            engine.AnalyzeBatch(rows, "HDFC CA", "Cash", null, "Co");
            Assert.True(rows[0].IsContra);
            Assert.Equal("Cash", rows[0].ContraTargetLedger);
            Assert.False(rows[1].IsContra);                      // the ATM fee is a bank charge, not cash
        });
        Assert.Equal("", NarrationTidier.Tidy(narration, "Cash/ATM", ""));
    }

    [Fact]
    public void IfscAlone_IsNotContra_ButIfscWithSelfWordingIs()
    {
        WithDb(db =>
        {
            db.UpsertOwnBanksBatch("Co", [new OwnBankAccount { TallyLedgerName = "HDFC CA", AccountNumber = "", Ifsc = "HDFC0001234" }]);
            var engine = new ContraDedupEngine(db);
            var rows = new List<BankTransactionRow>
            {
                // vendor who banks at the same branch → NOT a contra
                new() { RowId = "1", SourceFile = "f", TxnDate = "2025-04-01", TxnType = "DR", Amount = 15000, Debit = 15000, Narration = "NEFT DR-HDFC0001234-SHARMA TRADERS-INV 77" },
                // own transfer to that branch → contra
                new() { RowId = "2", SourceFile = "f", TxnDate = "2025-04-02", TxnType = "DR", Amount = 50000, Debit = 50000, Narration = "NEFT DR-HDFC0001234-TRF TO SELF" },
            };
            engine.AnalyzeBatch(rows, "SBI CA", "Cash", null, "Co");
            Assert.False(rows[0].IsContra);
            Assert.True(rows[1].IsContra);
            Assert.Equal("HDFC CA", rows[1].ContraTargetLedger);
        });
    }

    // ------------------------------------------------------------------ ML: one example per transaction
    [Fact]
    public void Learning_SameTransactionTwice_IsStoredOnce_CorrectionReplaces_OtherTransactionsStillCount()
    {
        WithDb(db =>
        {
            var clf = new LedgerClassifier(db);
            clf.Initialize();
            int baseCount = db.GetStats().mlCount;
            BankTransactionRow Row(string hash, string ledger) => new()
            {
                Narration = "UPI/DR/509112345678/METRO ENTERPRISES/HDFC", TxnType = "DR", VoucherType = "Payment", SelectedLedger = ledger, TxnHash = hash
            };

            Assert.Equal(1, clf.LearnFromRows([Row("h1", "Office Expenses")], "Co"));
            Assert.Equal(0, clf.LearnFromRows([Row("h1", "Office Expenses")], "Co"));   // re-analysis of same statement: skipped
            Assert.Equal(baseCount + 1, db.GetStats().mlCount);

            Assert.Equal(1, clf.LearnFromRows([Row("h1", "Repairs & Maintenance")], "Co")); // user corrected → replaces
            Assert.Equal(baseCount + 1, db.GetStats().mlCount);
            Assert.Equal("Repairs & Maintenance", clf.Predict("UPI/DR/509199999999/METRO ENTERPRISES/HDFC", "DR", null, "Co").ledger);

            // Different transactions of the same party each still add a vote
            Assert.Equal(2, clf.LearnFromRows([Row("h2", "Repairs & Maintenance"), Row("h3", "Repairs & Maintenance")], "Co"));
            Assert.Equal(baseCount + 3, db.GetStats().mlCount);

            // Rows without a hash (manual / legacy) are always learned
            Assert.Equal(1, clf.LearnFromRows([Row("", "Repairs & Maintenance")], "Co"));
            // Same hash in another company is a different transaction
            Assert.Equal(1, clf.LearnFromRows([Row("h1", "Office Expenses")], "OtherCo"));
        });
    }

    // ------------------------------------------------------------------ Indian number grouping (display)
    [Theory]
    [InlineData(0.0, "0.00")]
    [InlineData(999.5, "999.50")]
    [InlineData(1426.0, "1,426.00")]
    [InlineData(123456.78, "1,23,456.78")]
    [InlineData(1234567.0, "12,34,567.00")]
    [InlineData(123456789.01, "12,34,56,789.01")]
    [InlineData(-250000.0, "-2,50,000.00")]
    public void IndianNumberFormat_GroupsInLakhsAndCrores(double value, string expected)
    {
        Assert.Equal(expected, IndianNumberFormat.Format((decimal)value));
        Assert.Equal(expected, value.ToString("N2", IndianNumberFormat.Create(new CultureInfo("de-DE"))));
        Assert.Equal(expected, (string)new IndianAmountConverter().Convert(value, typeof(string), null, CultureInfo.InvariantCulture));
    }

    [Fact]
    public void IndianNumberFormat_BlankZero_AndAppCultureDoesNotLeakIntoParsingOrTallyXml()
    {
        Assert.Equal("", (string)new IndianAmountConverter().Convert(0.0m, typeof(string), "blankZero", CultureInfo.InvariantCulture));
        var prev = CultureInfo.CurrentCulture;
        try
        {
            IndianNumberFormat.ApplyToCurrentThreadAndDefaults();
            Assert.Equal("12,34,567.50", $"{1234567.5:N2}");
            // Parser still reads Indian-grouped statement amounts exactly
            Assert.Equal(1234567.5m, BankStatementParser.ParseIndianAmount("12,34,567.50").amt, 2);
            var conn = new TallyConnector("http://localhost:9000", "Co");
            var pay = new BankTransactionRow { TxnDate = "2025-04-01", TxnType = "DR", Amount = 1234567.5m, VoucherType = "Payment", SelectedLedger = "Rent", BankLedger = "SBI CA", VoucherGuid = "ABSE-9", PaymentMode = "NEFT", Narration = "rent" };
            var xml = conn.BuildVouchersXml([pay]);
            Assert.Contains("<AMOUNT>-1234567.50</AMOUNT>", xml);
            Assert.DoesNotContain("12,34,567", xml);
        }
        finally
        {
            CultureInfo.CurrentCulture = prev;
            CultureInfo.DefaultThreadCurrentCulture = null;
        }
    }

    // ------------------------------------------------------------------ Tally XML
    [Fact]
    public void VoucherXml_UsesInvariantAmounts_CorrectSigns_AndNoBillsOnContra()
    {
        var prev = CultureInfo.CurrentCulture;
        try
        {
            CultureInfo.CurrentCulture = new CultureInfo("de-DE"); // comma decimal separator
            var conn = new TallyConnector("http://localhost:9000", "Co");
            var pay = new BankTransactionRow { TxnDate = "2025-04-01", TxnType = "DR", Amount = 1234.5m, VoucherType = "Payment", SelectedLedger = "Rent", BankLedger = "SBI CA", VoucherGuid = "ABSE-1", PaymentMode = "NEFT", Narration = "rent" };
            var rec = new BankTransactionRow { TxnDate = "2025-04-02", TxnType = "CR", Amount = 99.99m, VoucherType = "Receipt", SelectedLedger = "Client", BankLedger = "SBI CA", VoucherGuid = "ABSE-2", PaymentMode = "UPI", Narration = "rcpt" };
            var con = new BankTransactionRow { TxnDate = "2025-04-03", TxnType = "DR", Amount = 500, VoucherType = "Contra", SelectedLedger = "Cash", BankLedger = "SBI CA", VoucherGuid = "ABSE-3", PaymentMode = "Cash/ATM", Narration = "atm",
                BillAllocations = [new BillAllocation { BillName = "INV-1", AllocateAmount = 500 }] };
            var xml = conn.BuildVouchersXml([pay, rec, con]);
            Assert.DoesNotContain("1234,50", xml);
            Assert.Contains("<LEDGERNAME>Rent</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-1234.50</AMOUNT>", xml);
            Assert.Contains("<LEDGERNAME>SBI CA</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>1234.50</AMOUNT>", xml);
            Assert.Contains("<LEDGERNAME>Client</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>99.99</AMOUNT>", xml);
            Assert.Contains("<LEDGERNAME>SBI CA</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-99.99</AMOUNT>", xml);
            Assert.DoesNotContain("INV-1", xml);
        }
        finally { CultureInfo.CurrentCulture = prev; }
    }

    [Fact]
    public void LedgerClassification_UsesGroupTree()
    {
        var tree = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["Bank Accounts"] = "Primary", ["Indirect Expenses"] = "Primary", ["Sundry Debtors"] = "Primary",
            ["Bank Charges"] = "Indirect Expenses", ["Debtors - Delhi"] = "Sundry Debtors", ["Current A/cs"] = "Bank Accounts", ["Cash-in-Hand"] = "Primary"
        };
        Assert.Equal(TallyConnector.LedgerKind.Other, TallyConnector.ClassifyLedgerGroup("Bank Charges", tree));
        Assert.Equal(TallyConnector.LedgerKind.Party, TallyConnector.ClassifyLedgerGroup("Debtors - Delhi", tree));
        Assert.Equal(TallyConnector.LedgerKind.Bank, TallyConnector.ClassifyLedgerGroup("Current A/cs", tree));
        Assert.Equal(TallyConnector.LedgerKind.Cash, TallyConnector.ClassifyLedgerGroup("Cash-in-Hand", tree));
        // Fallback without a group tree
        var none = new Dictionary<string, string>();
        Assert.Equal(TallyConnector.LedgerKind.Bank, TallyConnector.ClassifyLedgerGroup("Bank Accounts", none));
        Assert.Equal(TallyConnector.LedgerKind.Other, TallyConnector.ClassifyLedgerGroup("Bank Charges", none));
    }

    [Fact]
    public void DiagnoseError_DoesNotMisreadXmlTags()
    {
        var raw = "<RESPONSE><CREATED>0</CREATED><LASTVCHID>0</LASTVCHID><DATE>20250415</DATE><ERRORS>1</ERRORS></RESPONSE>";
        var row = new BankTransactionRow { TxnDate = "2025-04-15" };
        var msg = TallyConnector.DiagnoseError("Ledger 'Rent' does not exist!", raw, "", row);
        Assert.StartsWith("Missing Tally Master", msg);
        Assert.DoesNotContain("Educational", TallyConnector.DiagnoseError("Voucher totals do not match!", raw, "", row));
    }

    // ------------------------------------------------------------------ ML + DB
    [Fact]
    public void Classifier_FallbackIsSuspense_NotAGroupName()
    {
        WithDb(db =>
        {
            var clf = new LedgerClassifier(db); // untrained: only the fallback can answer
            var (ledger, _, src) = clf.Predict("ZQXW 99887766", "CR", null, "Co");
            Assert.Equal("fallback", src);
            Assert.Equal("Suspense Account", ledger);
        });
    }

    [Fact]
    public void Classifier_SparseModel_StillPredictsSeededLedgers()
    {
        WithDb(db =>
        {
            var clf = new LedgerClassifier(db);
            clf.Initialize();
            Assert.Equal("Bank Charges", clf.Predict("SMS ALERT CHARGES Q2", "DR", null, "Co").ledger);
            Assert.Equal("Interest Received", clf.Predict("SB INT CREDIT QTR", "CR", null, "Co").ledger);
            Assert.Equal("Electricity Expenses", clf.Predict("BBPS TATA POWER BILL", "DR", null, "Co").ledger);
        });
    }

    [Fact]
    public void PartialRollback_ClearsOnlyDeletedHashes_AndKeepsBatchOpen()
    {
        WithDb(db =>
        {
            var rows = new List<BankTransactionRow>
            {
                new() { TxnDate = "2025-04-01", TxnType = "DR", VoucherType = "Payment", Amount = 1, Debit = 1, BankLedger = "B", SelectedLedger = "X", TxnHash = "h1", VoucherGuid = "G1" },
                new() { TxnDate = "2025-04-02", TxnType = "DR", VoucherType = "Payment", Amount = 2, Debit = 2, BankLedger = "B", SelectedLedger = "X", TxnHash = "h2", VoucherGuid = "G2" },
            };
            db.RecordPostedTransactions(rows, true, "Co");
            var id = db.RecordPostedBatch("Co", "B", rows);
            var batch = db.GetRecentBatches("Co")[0];
            db.MarkBatchRolledBack(id, ["h1"], batch.Vouchers.Where(v => v.Guid == "G2").ToList());
            var after = db.GetRecentBatches("Co")[0];
            Assert.False(after.RolledBack);
            Assert.Single(after.Vouchers);
            var hashes = db.GetPostedHashes("Co");
            Assert.DoesNotContain("h1", hashes);
            Assert.Contains("h2", hashes);
            db.MarkBatchRolledBack(id, ["h2"], []);
            Assert.True(db.GetRecentBatches("Co")[0].RolledBack);
        });
    }

    // ------------------------------------------------------------------ helpers
    private static string WriteTemp(string name, string content)
    {
        var dir = Path.Combine(Path.GetTempPath(), "abse_audit_" + Guid.NewGuid().ToString("N")[..8]);
        Directory.CreateDirectory(dir);
        var p = Path.Combine(dir, name);
        File.WriteAllText(p, content);
        return p;
    }

    // ------------------------------------------------------------------ BRS bank date, short narration
    private static BankTransactionRow PayRow(string narration = "UPI/DR/412345678901/RAMESH KUMAR/SBIN/ramesh@oksbi/Payment") => new()
    {
        RowId = "p1", TxnDate = "2026-10-05", DisplayDate = "05-Oct-2026", TxnType = "DR", Amount = 1500.00m, Debit = 1500.00m,
        VoucherType = "Payment", BankLedger = "AU Bank", SelectedLedger = "Ramesh Kumar", VoucherGuid = "ABSE-pay00000000001",
        Narration = narration, PaymentMode = "UPI", RefNo = "412345678901"
    };

    [Fact]
    public void BankDate_IsFilledWithStatementDate_UnlessSwitchedOff()
    {
        var on = System.Xml.Linq.XDocument.Parse(new TallyConnector("http://localhost:9000", "Co").BuildVouchersXml([PayRow()]));
        Assert.Equal("20261005", on.Descendants("BANKERSDATE").Single().Value);
        var off = System.Xml.Linq.XDocument.Parse(new TallyConnector("http://localhost:9000", "Co") { SetBankDate = false }.BuildVouchersXml([PayRow()]));
        Assert.Empty(off.Descendants("BANKERSDATE"));
    }

    [Fact]
    public void Narration_Tidy_FindsPartyModeAndRef()
    {
        Assert.Equal("Ramesh Kumar • UPI • 412345678901", NarrationTidier.Tidy("UPI/DR/412345678901/RAMESH KUMAR/SBIN/ramesh@oksbi/Payment", "UPI", "412345678901"));
        Assert.Equal("Sharma Traders • NEFT • N123456789", NarrationTidier.Tidy("NEFT-N123456789-SHARMA TRADERS-HDFC0001234", "NEFT", "N123456789"));
        Assert.Equal("", NarrationTidier.Tidy("123456789012", "Bank Transfer", ""));   // nothing useful: original only
        Assert.Equal("", NarrationTidier.Tidy("", "UPI", ""));
        Assert.Equal("Sharma Traders Pvt Ltd • NEFT", NarrationTidier.Tidy("NEFT CR-HDFC0000123-SHARMA TRADERS PVT LTD-1234567890", "NEFT", ""));
        Assert.Equal("HDFC Life • UPI", NarrationTidier.Tidy("UPI/DR/412345678901/HDFC LIFE/HDFC/hdfclife@okhdfcbank/Payment", "UPI", ""));
        Assert.Equal("Umang Agarwal • RTGS • KARBR51234", NarrationTidier.Tidy("BY TRANSFER- RTGS UTR NO: KARBR51234 UMANG AGARWAL", "RTGS", "KARBR51234"));
        // cash, interest and charges keep the bank's own text only
        Assert.Equal("", NarrationTidier.Tidy("ATM WDL ATM CASH 4521 MI ROAD JAIPUR", "Cash/ATM", ""));
        Assert.Equal("", NarrationTidier.Tidy("SMS ALERT CHARGES INCL GST", "Bank Transfer", ""));
    }

    [Fact]
    public void Narration_Tidy_PostedAsFirstLine_OriginalKeptBelow_OnlyWhenOn()
    {
        var row = PayRow();
        row.TidyNarration = NarrationTidier.Tidy(row.Narration, row.PaymentMode, row.RefNo);
        var off = System.Xml.Linq.XDocument.Parse(new TallyConnector("http://localhost:9000", "Co").BuildVouchersXml([row]));
        Assert.Equal(row.Narration, off.Descendants("NARRATION").Single().Value);
        var xml = new TallyConnector("http://localhost:9000", "Co") { UseTidyNarration = true }.BuildVouchersXml([row]);
        Assert.Contains("Ramesh Kumar • UPI • 412345678901&#13;&#10;UPI/DR/", xml);
        var lines = System.Xml.Linq.XDocument.Parse(xml).Descendants("NARRATION").Single().Value.Split('\n').Select(l => l.Trim('\r')).ToArray();
        Assert.Equal(new[] { row.TidyNarration, row.Narration }, lines);
        Assert.Equal(row.Narration, row.OriginalNarration);   // the row's own narration is never changed
    }

    // ------------------------------------------------------------------ remembered splits
    [Fact]
    public void SplitMemory_SameTotal_SameAmounts_DifferentTotal_ScaledAndAddsUpExactly()
    {
        var mem = new List<LedgerSplit> { new() { Ledger = "Rent", Amount = 10000m }, new() { Ledger = "Input GST", Amount = 1800m } };
        var same = SplitMemory.Fit(mem, 11800m)!.Value;
        Assert.True(same.exact);
        Assert.Equal(new[] { 10000m, 1800m }, same.lines.Select(l => l.Amount));
        var scaled = SplitMemory.Fit(mem, 12500.01m)!.Value;
        Assert.False(scaled.exact);
        Assert.Equal(12500.01m, scaled.lines.Sum(l => l.Amount));
        Assert.Equal(1906.78m, scaled.lines[1].Amount);          // 1800 × 12500.01 / 11800 = 1906.7811…, rounded down to the paisa
        Assert.Null(SplitMemory.Fit(mem, 0.01m));                // a line would be zero: not applied
    }

    [Fact]
    public void SplitMemory_Apply_ExactTicksRow_ScaledHoldsItBack()
    {
        var mem = new Dictionary<string, List<LedgerSplit>>
        {
            [SplitMemory.Key("sharma properties", "DR")] = [new() { Ledger = "Rent", Amount = 10000m }, new() { Ledger = "Input GST", Amount = 1800m }]
        };
        var exact = new BankTransactionRow { RowId = "a", TxnType = "DR", Amount = 11800m, PartyKey = "sharma properties", SelectedLedger = "Suspense Account", NeedsReview = true, Selected = false };
        var other = new BankTransactionRow { RowId = "b", TxnType = "DR", Amount = 12000m, PartyKey = "sharma properties", SelectedLedger = "Rent" };
        var receipt = new BankTransactionRow { RowId = "c", TxnType = "CR", Amount = 11800m, PartyKey = "sharma properties", SelectedLedger = "Rent" };
        var (e, sc) = SplitMemory.Apply([exact, other, receipt], mem);
        Assert.Equal((1, 1), (e, sc));
        Assert.True(exact.IsSplit && exact.Selected && !exact.NeedsReview && exact.SelectedLedger == "Rent");
        Assert.True(other.IsSplit && !other.Selected && other.NeedsReview);
        Assert.Equal(12000m, other.Splits.Sum(l => l.Amount));
        Assert.Equal("Check", other.RowState);
        Assert.False(receipt.IsSplit);                           // other direction: not touched
    }

    [Fact]
    public void SplitMemory_SavedAndReadBack_AndForgotten()
    {
        WithDb(db =>
        {
            db.EnsureInitialized();
            db.SaveRememberedSplit("Co", "sharma properties", "DR", [new() { Ledger = "Rent", Amount = 10000.10m }, new() { Ledger = "GST", Amount = 1800m }]);
            var m = db.GetRememberedSplits("Co");
            Assert.Equal(10000.10m, m["sharma properties|DR"][0].Amount);
            Assert.Empty(db.GetRememberedSplits("Other Co"));
            db.DeleteRememberedSplit("Co", "sharma properties", "DR");
            Assert.Empty(db.GetRememberedSplits("Co"));
        });
    }

    [Fact]
    public void Settings_SavedAndReadBack_WithDefaults()
    {
        WithDb(db =>
        {
            db.EnsureInitialized();
            Assert.True(db.GetBoolSetting("brs_bank_date", true));
            db.SetBoolSetting("brs_bank_date", false);
            db.SetBoolSetting("brs_bank_date", false);   // upsert
            Assert.False(db.GetBoolSetting("brs_bank_date", true));
            db.SetBoolSetting("tidy_narration", true);
            Assert.True(db.GetBoolSetting("tidy_narration", false));
        });
    }

    // ------------------------------------------------------------------ automatic bill matching
    private static BankTransactionRow BillRow(string id, string type, decimal amt, string party) => new()
    {
        RowId = id, TxnType = type, Amount = amt, SelectedLedger = party, VoucherType = type == "DR" ? "Payment" : "Receipt"
    };

    [Fact]
    public void BillMatch_OnlyWhenExactlyOneBillHasTheSameAmountOnTheRightSide()
    {
        var bills = new Dictionary<string, List<BillAllocation>>(StringComparer.OrdinalIgnoreCase)
        {
            ["Sharma Traders"] =
            [
                new() { BillName = "PB/101", PendingAmount = 5000m, IsPayable = true },
                new() { BillName = "PB/102", PendingAmount = 7000m, IsPayable = true },
                new() { BillName = "PB/103", PendingAmount = 7000m, IsPayable = true },
                new() { BillName = "SB/9", PendingAmount = 5000m, IsPayable = false }
            ]
        };
        var pay = BillRow("1", "DR", 5000m, "Sharma Traders");     // one payable bill of 5,000 → picked
        var twoBills = BillRow("2", "DR", 7000m, "Sharma Traders"); // two bills of 7,000 → left alone
        var noBill = BillRow("3", "DR", 4999.99m, "Sharma Traders");
        var rec = BillRow("4", "CR", 5000m, "Sharma Traders");     // receipt → the receivable SB/9
        var picks = BillAutoMatcher.Pick([pay, twoBills, noBill, rec], bills);
        Assert.Equal(2, picks.Count);
        Assert.Equal("PB/101", picks[pay].BillName);
        Assert.Equal("SB/9", picks[rec].BillName);
    }

    [Fact]
    public void BillMatch_TwoEntriesForOneBill_NeitherGetsIt_AndHandPickedBillsAreNotReused()
    {
        var bills = new Dictionary<string, List<BillAllocation>>(StringComparer.OrdinalIgnoreCase)
        {
            ["Sharma Traders"] = [new() { BillName = "PB/101", PendingAmount = 5000m, IsPayable = true }],
            ["Gupta & Co"] = [new() { BillName = "G1", PendingAmount = 800m, IsPayable = true }]
        };
        var a = BillRow("a", "DR", 5000m, "Sharma Traders");
        var b = BillRow("b", "DR", 5000m, "Sharma Traders");
        var chosen = BillRow("c", "DR", 800m, "Gupta & Co"); chosen.BillRef = "G1 (₹800.00)";
        var d = BillRow("d", "DR", 800m, "Gupta & Co");
        var guess = BillRow("e", "DR", 800m, "Gupta & Co"); guess.NeedsReview = true;
        Assert.Empty(BillAutoMatcher.Pick([a, b, chosen, d, guess], bills));
    }

    // ------------------------------------------------------------------ row colours
    [Fact]
    public void RowState_GivesTheLegendColour()
    {
        var r = new BankTransactionRow { RowId = "x", SelectedLedger = "Rent" };
        Assert.Equal("Ready", r.RowState);
        r.NeedsReview = true; Assert.Equal("Check", r.RowState);
        r.NeedsReview = false; r.Selected = false; Assert.Equal("Skipped", r.RowState);
        r.Selected = true; r.OverlapStatus = "EXISTS_IN_TALLY"; Assert.Equal("Skipped", r.RowState);
        r.OverlapStatus = "NEW"; r.PostStatus = "DONE"; Assert.Equal("Skipped", r.RowState);
        r.PostStatus = "FAILED"; Assert.Equal("Problem", r.RowState);
        r.PostStatus = ""; r.HasBalanceBreak = true; Assert.Equal("Problem", r.RowState);
        var changes = new List<string?>();
        r.PropertyChanged += (_, e) => changes.Add(e.PropertyName);
        r.ParseWarning = "date inherited";
        Assert.Contains(nameof(BankTransactionRow.RowState), changes);
    }

    // ------------------------------------------------------------------ Tally on any port
    [Fact]
    public void TallyPorts_TallysOwnPortFirst_ThenUsual_ThenOther9000s_NoDuplicates()
    {
        var ports = TallyPortFinder.CandidatePorts(tallyOwnedPorts: [9123, 9000], listeningPorts: [80, 445, 9000, 9555, 9100, 65000]);
        Assert.Equal(9123, ports[0]);                       // the port Tally itself opened, even if unusual
        Assert.Equal(new[] { 9123, 9000, 9001, 9002, 9003, 9004, 9005, 9009, 9999, 9100, 9555 }, ports);
        Assert.DoesNotContain(80, ports);                   // other programs' ports outside 9000–9999 are not probed
        Assert.Equal(TallyPortFinder.UsualPorts, TallyPortFinder.CandidatePorts([], []));
    }

    [Fact]
    public async Task TallyDiscovery_FindsTallyOnAnUnusualPort()
    {
        // a fake Tally on a free port in the 9000–9999 range is found without typing the port anywhere
        var port = Enumerable.Range(9300, 600).First(p => !System.Net.NetworkInformation.IPGlobalProperties.GetIPGlobalProperties()
            .GetActiveTcpListeners().Any(ep => ep.Port == p));
        using var listener = new System.Net.HttpListener();
        listener.Prefixes.Add($"http://localhost:{port}/");
        listener.Start();
        var serve = Task.Run(async () =>
        {
            try
            {
                while (listener.IsListening)
                {
                    var ctx = await listener.GetContextAsync();
                    var body = "<ENVELOPE><BODY><DATA><COLLECTION><COMPANY NAME=\"Port Test Co\"/></COLLECTION></DATA></BODY></ENVELOPE>";
                    var bytes = System.Text.Encoding.UTF8.GetBytes(body);
                    ctx.Response.ContentType = "text/xml";
                    await ctx.Response.OutputStream.WriteAsync(bytes);
                    ctx.Response.Close();
                }
            }
            catch { /* stopped */ }
        });
        try
        {
            var found = await TallyConnector.DiscoverOpenTalliesAsync("");
            Assert.Contains(found, t => t.Host == $"http://localhost:{port}" && t.CompanyName == "Port Test Co");
        }
        finally { listener.Stop(); }
    }

    private static void WithDb(Action<DatabaseService> body)
    {
        var dir = Path.Combine(Path.GetTempPath(), "abse_auditdb_" + Guid.NewGuid().ToString("N")[..8]);
        try { body(new DatabaseService(dir)); }
        finally
        {
            Microsoft.Data.Sqlite.SqliteConnection.ClearAllPools();
            for (int i = 0; i < 20 && Directory.Exists(dir); i++)
            {
                try { Directory.Delete(dir, true); break; }
                catch (IOException) { Thread.Sleep(100); }
                catch (UnauthorizedAccessException) { Thread.Sleep(100); }
            }
        }
    }
}
