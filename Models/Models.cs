using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace AutoBankStatementEntry.Models;

public class BankTransactionRow : INotifyPropertyChanged
{
    private bool _selected = true;
    private string _voucherType = "Payment";
    private string _selectedLedger = "";
    private double _confidence;
    private string _predictionSource = "";
    private string _postStatus = "";
    private string _postError = "";
    private string _narration = "";
    private bool _isNewLedger;
    private string _billRef = "(None)";

    public string RowId { get; set; } = "";
    public string TxnDate { get; set; } = ""; // YYYY-MM-DD
    public string DisplayDate { get; set; } = ""; // DD-MMM-YYYY
    public string ValueDate { get; set; } = "";
    public string OriginalNarration { get; set; } = "";
    public string Narration
    {
        get => _narration;
        set { if (string.IsNullOrEmpty(OriginalNarration) && !string.IsNullOrEmpty(value)) OriginalNarration = value; _narration = value; OnPropertyChanged(); }
    }
    public string RefNo { get; set; } = "";
    public decimal Debit { get; set; }
    public decimal Credit { get; set; }
    public decimal? Balance { get; set; }
    public string TxnType { get; set; } = "DR"; // DR or CR
    public decimal Amount { get; set; }
    public string PaymentMode { get; set; } = "Bank Transfer";
    public string BankDetected { get; set; } = "";
    public string BankLedger { get; set; } = "";
    public string SourceFile { get; set; } = "";
    public string TxnHash { get; set; } = "";
    public string VoucherGuid { get; set; } = "";

    public bool IsContra { get; set; }
    public string ContraTargetLedger { get; set; } = "";
    public string ContraReason { get; set; } = "";
    public string ContraSignature { get; set; } = "";

    private string _overlapStatus = "NEW";
    public string OverlapStatus
    {
        get => _overlapStatus;
        set { _overlapStatus = value ?? "NEW"; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(RowState)); }
    }
    public string OverlapReason { get; set; } = "";
    public string MatchedTallyLedger { get; set; } = "";
    public string MatchedTallyVoucherType { get; set; } = "";
    private bool _hasBalanceBreak;
    public bool HasBalanceBreak
    {
        get => _hasBalanceBreak;
        set { _hasBalanceBreak = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(RowState)); }
    }
    public string BalanceBreakNote { get; set; } = "";
    /// <summary>Non-fatal parser note (e.g. Dr/Cr corrected from running balance, date inherited from previous row).</summary>
    private string _parseWarning = "";
    public string ParseWarning
    {
        get => _parseWarning;
        set { _parseWarning = value ?? ""; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(RowState)); }
    }

    private string _tidyNarration = "";
    /// <summary>Short "Party • Mode • Ref" line built from the narration (see NarrationTidier). Empty when nothing useful was found.</summary>
    public string TidyNarration
    {
        get => _tidyNarration;
        set { _tidyNarration = value ?? ""; OnPropertyChanged(); OnPropertyChanged(nameof(HasTidyNarration)); }
    }
    public bool HasTidyNarration => !string.IsNullOrWhiteSpace(_tidyNarration);
    public bool UserEdited { get; set; }
    public string LastCommittedLedger { get; set; } = "";

    private bool _needsReview;
    /// <summary>
    /// The ledger is only a guess (low confidence, Suspense or empty): the row starts UNTICKED. Choosing or confirming a
    /// ledger clears this and ticks the row again.
    /// </summary>
    public bool NeedsReview
    {
        get => _needsReview;
        set { _needsReview = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(RowState)); }
    }

    private List<LedgerSplit> _splits = [];
    /// <summary>
    /// One bank entry posted to several ledgers (e.g. Rent ₹10,000 + GST ₹1,800 for one ₹11,800 payment).
    /// Empty = the whole amount goes to <see cref="SelectedLedger"/>. When set, the lines always add up to <see cref="Amount"/>
    /// and <see cref="SelectedLedger"/> is the line with the largest amount.
    /// </summary>
    public List<LedgerSplit> Splits
    {
        get => _splits;
        set { _splits = value ?? []; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(IsSplit)); OnPropertyChanged(nameof(GroupLabel)); }
    }
    public bool IsSplit => _splits.Count >= 2;

    /// <summary>Every ledger this entry posts to besides the bank (one, or all split lines).</summary>
    public IEnumerable<string> PostingLedgers => IsSplit ? _splits.Select(x => x.Ledger) : new[] { SelectedLedger };

    public string SplitSummary => IsSplit ? "Split: " + string.Join(" + ", _splits.Select(x => $"{x.Ledger} ₹{x.Amount:N2}")) : "";

    public bool Selected
    {
        get => _selected;
        set { _selected = value; OnPropertyChanged(); OnPropertyChanged(nameof(RowState)); }
    }

    public string VoucherType
    {
        get => _voucherType;
        set { _voucherType = value; OnPropertyChanged(); }
    }

    public string SelectedLedger
    {
        get => _selectedLedger;
        set { _selectedLedger = value; OnPropertyChanged(); OnPropertyChanged(nameof(GroupLabel)); }
    }

    // ---- "Group similar" ----
    /// <summary>Who the entry is with (from the narration), set once when the statement is analysed.</summary>
    public string PartyKey { get; set; } = "";

    private bool _keepSeparate;
    /// <summary>The user took this row out of its group ("Take out of group").</summary>
    public bool KeepSeparate
    {
        get => _keepSeparate;
        set { _keepSeparate = value; OnPropertyChanged(); OnPropertyChanged(nameof(GroupLabel)); }
    }

    /// <summary>
    /// Rows are grouped only when party, direction AND ledger are all the same. Giving a row a different ledger therefore
    /// moves it out of its group by itself. Contra, split, posted and separated rows always stand alone.
    /// </summary>
    public string GroupLabel =>
        KeepSeparate || IsSplit || IsContra || PostStatus == "DONE" || string.IsNullOrWhiteSpace(PartyKey)
            ? "\u2063" + RowId    // a group of one: shown as a normal row, without a group header
            : $"{PartyKey.ToUpperInvariant()}   •   {(TxnType == "CR" ? "Receipts" : "Payments")}   •   "
              + (string.IsNullOrWhiteSpace(SelectedLedger) ? "no ledger yet" : SelectedLedger.Trim());

    public double Confidence
    {
        get => _confidence;
        set { _confidence = value; OnPropertyChanged(); OnPropertyChanged(nameof(ConfidenceDisplay)); }
    }

    public string ConfidenceDisplay => $"{Math.Round(Confidence * 100)}%";

    public string PredictionSource
    {
        get => _predictionSource;
        set { _predictionSource = value; OnPropertyChanged(); }
    }

    public string PostStatus
    {
        get => _postStatus;
        set { _postStatus = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(GroupLabel)); OnPropertyChanged(nameof(RowState)); }
    }

    public string PostError
    {
        get => _postError;
        set { _postError = value; OnPropertyChanged(); OnPropertyChanged(nameof(StatusSummary)); OnPropertyChanged(nameof(RowState)); }
    }

    public string BillRef
    {
        get => _billRef;
        set { _billRef = string.IsNullOrWhiteSpace(value) ? "(None)" : value; OnPropertyChanged(); }
    }

    public ObservableCollection<string> AvailableBills { get; } = ["(None)"];
    public List<BillAllocation> BillAllocations { get; set; } = [];

    public bool IsNewLedger
    {
        get => _isNewLedger;
        set { _isNewLedger = value; OnPropertyChanged(); OnPropertyChanged(nameof(NewLedgerLabel)); OnPropertyChanged(nameof(StatusSummary)); }
    }

    public string NewLedgerLabel => IsNewLedger && !string.IsNullOrWhiteSpace(SelectedLedger)
        ? $"+ New Ledger: \"{SelectedLedger}\""
        : "";

    public string StatusSummary
    {
        get
        {
            if (PostStatus == "DONE") return "Done ✓";
            if (PostStatus == "FAILED") return $"Failed: {PostError}";
            if (HasBalanceBreak) return BalanceBreakNote;
            if (NeedsReview && IsSplit) return "⚠ Check split amounts (scaled from last time) — " + SplitSummary;
            if (NeedsReview) return string.IsNullOrWhiteSpace(SelectedLedger)
                ? "⚠ Choose a ledger"
                : $"⚠ Check ledger — only {ConfidenceDisplay} sure";
            if (OverlapStatus != "NEW") return $"{OverlapStatus}: {OverlapReason}";
            if (!string.IsNullOrEmpty(ParseWarning)) return $"⚠ {ParseWarning}";
            if (IsSplit) return SplitSummary;
            if (IsContra) return $"Contra: {ContraReason}";
            if (IsNewLedger && !string.IsNullOrWhiteSpace(SelectedLedger)) return $"New Ledger (\"{SelectedLedger}\")";
            return "Ready";
        }
    }

    /// <summary>
    /// Row colour: "Problem" (red: failed / balance break), "Skipped" (grey: posted, already in Tally, duplicate, or unticked),
    /// "Check" (amber: ledger is a guess or the parser left a note), "Ready" (green).
    /// </summary>
    public string RowState
    {
        get
        {
            if (PostStatus == "FAILED" || HasBalanceBreak) return "Problem";
            if (PostStatus == "DONE" || OverlapStatus != "NEW") return "Skipped";
            if (NeedsReview || !string.IsNullOrEmpty(ParseWarning)) return "Check";
            return Selected ? "Ready" : "Skipped";
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class LedgerSplit
{
    public string Ledger { get; set; } = "";
    public decimal Amount { get; set; }
}

/// <summary>Bank details stored on a party ledger in Tally (or just its name) — used to identify the party exactly.</summary>
public class PartyBankInfo
{
    public string Ledger { get; set; } = "";
    public List<string> AccountNumbers { get; set; } = [];
    public List<string> Ifscs { get; set; } = [];
    /// <summary>Beneficiary name printed on the bank details ("Payment favouring").</summary>
    public string Favouring { get; set; } = "";
}

public class OwnBankAccount
{
    public string TallyLedgerName { get; set; } = "";
    public string BankName { get; set; } = "";
    public string AccountNumber { get; set; } = "";
    public string Ifsc { get; set; } = "";
    public string Aliases { get; set; } = "";
    public string DisplayLabel =>
        $"{TallyLedgerName}" +
        (string.IsNullOrWhiteSpace(AccountNumber) ? "" : $" ({(AccountNumber.Length >= 4 ? AccountNumber[^4..] : AccountNumber)})") +
        (string.IsNullOrWhiteSpace(Ifsc) ? "" : $" [{Ifsc}]");
}

public class TallyBankDetail
{
    public string TallyLedgerName { get; set; } = "";
    public string BankName { get; set; } = "";
    public string AccountNumber { get; set; } = "";
    public string AccountLast4 { get; set; } = "";
    public string Ifsc { get; set; } = "";
}

public class TallyTarget
{
    public string Host { get; set; } = "http://localhost:9000";
    public string CompanyName { get; set; } = "";
    public bool IsActive { get; set; }
    public string Label => string.IsNullOrWhiteSpace(CompanyName)
        ? $"Tally at {Host} (No Company Open)"
        : $"{CompanyName}{(IsActive ? " [Active]" : "")} ({Host})";
    public override string ToString() => Label;
}

public class MissingLedgerItem
{
    public bool Create { get; set; } = true;
    public string Name { get; set; } = "";
    public string Role { get; set; } = "";
    public int UsageCount { get; set; }
    public string ParentGroup { get; set; } = "Indirect Expenses";
}

public class StatementBalanceInfo
{
    public decimal? StatementOpening { get; set; }
    public decimal? StatementClosing { get; set; }
    public decimal? CalculatedClosing { get; set; }
    public bool? StatementBalanced { get; set; }
    public decimal StatementDiff { get; set; }
    public decimal TotalDebit { get; set; }
    public decimal TotalCredit { get; set; }
    public string FromDate { get; set; } = "";
    public string ToDate { get; set; } = "";
    /// <summary>True when the statement had a running-balance column, so every row could be proven against it.</summary>
    public bool HasRunningBalance { get; set; }
    public int BalanceBreakCount { get; set; }
    public int ParseWarningCount { get; set; }
    /// <summary>True when the opening / closing balance was printed in the statement (not inferred from the first / last row).</summary>
    public bool OpeningPrinted { get; set; }
    public bool ClosingPrinted { get; set; }

    // ---- Completeness self-checks ----
    /// <summary>Totals the statement itself prints ("Total Debits", HDFC "Statement Summary" …), when found.</summary>
    public decimal? PrintedTotalDebit { get; set; }
    public decimal? PrintedTotalCredit { get; set; }
    public int? PrintedDebitCount { get; set; }
    public int? PrintedCreditCount { get; set; }
    /// <summary>Problems found by the completeness checks (printed totals differ, pages missing / duplicated …). Empty = none.</summary>
    public List<string> CompletenessIssues { get; set; } = new();
    /// <summary>Page-number problems (pages missing / repeated) — kept separately because they never change after parsing.</summary>
    public List<string> PageIssues { get; set; } = new();

    /// <summary>
    /// Proven complete: the running balance reconciles AND no completeness check failed. Posting is BLOCKED when this is
    /// false because of a definite failure (see <see cref="BlockReason"/>).
    /// </summary>
    public string BlockReason =>
        StatementBalanced == false ? $"Balances do not reconcile (difference ₹{StatementDiff:N2})"
        : CompletenessIssues.Count > 0 ? string.Join("; ", CompletenessIssues)
        : "";
}

/// <summary>
/// A statement layout taught once by a user ("Teach Columns"): column dividers as fractions of the page width plus the role
/// of every column. Stored in the shared database, so every PC parses that format automatically from then on.
/// </summary>
public class LayoutTemplate
{
    public long Id { get; set; }
    public string Name { get; set; } = "";
    /// <summary>Bank code the layout belongs to (SBI, HDFC …); empty = any bank.</summary>
    public string Bank { get; set; } = "";
    /// <summary>Normalised words of the table heading (may be empty when the statement prints no heading).</summary>
    public string HeaderSignature { get; set; } = "";
    /// <summary>Column edges, left to right, as a fraction of the page width (Count = Roles.Count + 1).</summary>
    public List<double> Boundaries { get; set; } = new();
    /// <summary>Role of each column: date, value_date, narration, ref_no, debit, credit, amount, drcr, balance or ignore.</summary>
    public List<string> Roles { get; set; } = new();
    public string SampleFile { get; set; } = "";
    public string CreatedBy { get; set; } = "";
    public string CreatedAt { get; set; } = "";
}

/// <summary>One statement accepted for an account — used to check that the next statement continues where this one ended.</summary>
public class StatementHistoryEntry
{
    public string CompanyName { get; set; } = "";
    public string BankLedger { get; set; } = "";
    public string FromDate { get; set; } = "";
    public string ToDate { get; set; } = "";
    public decimal Opening { get; set; }
    public decimal Closing { get; set; }
    public string SourceFile { get; set; } = "";
    public string RecordedAt { get; set; } = "";
}

public class ParsedStatementResult
{
    public string SourceFile { get; set; } = "";
    public string BankDetected { get; set; } = "Scheduled Bank (Auto)";
    public string AccountNumberDetected { get; set; } = "";
    public string ExtractionMethod { get; set; } = "Digital";
    public StatementBalanceInfo Balances { get; set; } = new();
    public List<BankTransactionRow> Transactions { get; set; } = new();
    public string DiagnosticReport { get; set; } = "";
    /// <summary>Name of the saved layout ("Teach Columns") used to read this file, if any.</summary>
    public string LayoutTemplateUsed { get; set; } = "";
    public string SourcePath { get; set; } = "";
}

public class FailedEntry
{
    public string RowId { get; set; } = "";
    public string DisplayDate { get; set; } = "";
    public string Narration { get; set; } = "";
    public string SelectedLedger { get; set; } = "";
    public decimal Amount { get; set; }
    public string Reason { get; set; } = "";
}

public class TallyExistingVoucher
{
    public string Date { get; set; } = "";
    public string VoucherType { get; set; } = "";
    public string Guid { get; set; } = "";
    /// <summary>REMOTEID — vouchers created by this app carry "ABSE-…" here (and usually as GUID too).</summary>
    public string RemoteId { get; set; } = "";
    /// <summary>Tally voucher number (for messages only).</summary>
    public string VoucherNumber { get; set; } = "";
    public string RefNo { get; set; } = "";
    public string Narration { get; set; } = "";
    public List<string> Ledgers { get; set; } = new();
    public Dictionary<string, decimal> LedgerAmounts { get; set; } = new(StringComparer.OrdinalIgnoreCase);
    public decimal Amount { get; set; }
}

public class VerificationReport
{
    public bool AllOk { get; set; } = true;
    /// <summary>True when Tally could not be read back after posting (timeout / connection) — NOT the same as "missing".</summary>
    public bool CouldNotVerify { get; set; }
    public int Expected { get; set; }
    public int Verified { get; set; }
    public List<string> Missing { get; set; } = new();
    public List<string> Duplicated { get; set; } = new();
    public List<string> Mixed { get; set; } = new();
    public string BalanceSummary { get; set; } = "";
}

public class TallyPushResult
{
    public bool Success { get; set; }
    public int Total { get; set; }
    public int Created { get; set; }
    public int FailedCount { get; set; }
    public List<BankTransactionRow> PostedEntries { get; set; } = new();
    public List<FailedEntry> FailedEntries { get; set; } = new();
    public VerificationReport? Verification { get; set; }
}

public class BillAllocation : INotifyPropertyChanged
{
    private bool _selected;
    private decimal _allocateAmount;

    public string BillName { get; set; } = "";
    public decimal PendingAmount { get; set; }
    public string BillType { get; set; } = "Agst Ref";
    /// <summary>True = we owe this bill (a purchase bill, settled by a Payment); false = it is owed to us (settled by a Receipt).</summary>
    public bool IsPayable { get; set; }

    public bool Selected
    {
        get => _selected;
        set { _selected = value; OnPropertyChanged(); }
    }

    public decimal AllocateAmount
    {
        get => _allocateAmount;
        set { _allocateAmount = Math.Round(Math.Max(0m, value), 2); OnPropertyChanged(); }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public class BatchVoucherRef
{
    public string Date { get; set; } = "";
    public string VoucherType { get; set; } = "";
    public string Guid { get; set; } = "";
    public string TxnHash { get; set; } = "";
    public string BankLedger { get; set; } = "";
    public string SelectedLedger { get; set; } = "";
    public decimal Amount { get; set; }
}

public class PostedBatchSummary
{
    public string BatchId { get; set; } = "";
    public string CompanyName { get; set; } = "";
    public string BankLedger { get; set; } = "";
    public string PostedBy { get; set; } = "";
    public int EntryCount { get; set; }
    public decimal TotalDebit { get; set; }
    public decimal TotalCredit { get; set; }
    public string FromDate { get; set; } = "";
    public string ToDate { get; set; } = "";
    public bool RolledBack { get; set; }
    public string CreatedAt { get; set; } = "";
    public List<BatchVoucherRef> Vouchers { get; set; } = new();
    public string StatusLabel => RolledBack ? "Rolled Back" : "Posted";
    public string PeriodLabel => string.IsNullOrEmpty(FromDate) ? "" : $"{FromDate} to {ToDate}";
}

public class PostedFileMatch
{
    public string FileName { get; set; } = "";
    public string CompanyName { get; set; } = "";
    public string BankLedger { get; set; } = "";
    public string PostedBy { get; set; } = "";
    public int PostedCount { get; set; }
    public string CreatedAt { get; set; } = "";
}
