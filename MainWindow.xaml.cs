using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Input;
using System.Windows.Media;
using AutoBankStatementEntry.Models;
using AutoBankStatementEntry.Services;
using Microsoft.Win32;

namespace AutoBankStatementEntry;

public partial class MainWindow : Window
{
    private readonly DatabaseService _db = new();
    private readonly LedgerClassifier _classifier;
    private readonly ContraDedupEngine _contraEngine;

    private List<string> _tallyLedgers = [
        "Cash", "Bank Charges", "Electricity Expenses", "Telephone & Internet Expenses",
        "Rent Expense", "Salaries & Wages", "Office Expenses", "Travelling & Conveyance",
        "Printing & Stationery", "Repairs & Maintenance", "Software & Subscriptions",
        "Professional & Legal Fees", "Advertising & Marketing", "Fuel & Vehicle Expenses",
        "Insurance Expenses", "Interest Received", "Interest Paid", "GST Payable",
        "TDS Payable", "Income Tax / Advance Tax", "Sales Account", "Purchase Account",
        "Drawings Account", "Suspense Account"
    ]; // "Sundry Debtors" / "Sundry Creditors" removed: they are Tally GROUPS, a voucher cannot be posted to them
    private List<string> _tallyGroups = TallyConnector.StandardGroups.ToList();
    private Dictionary<string, TallyBankDetail> _bankDetails = new(StringComparer.OrdinalIgnoreCase);
    private HashSet<string> _partyLedgers = new(StringComparer.OrdinalIgnoreCase);
    private List<PartyBankInfo> _partyBankInfo = [];

    private const double ConfidenceFloor = ReviewPolicy.ConfidenceFloor;
    private Dictionary<string, List<BillAllocation>> _pendingBillsCache = new(StringComparer.OrdinalIgnoreCase);
    private const string SplitInvoicesOption = "Split Multiple Invoices...";
    private List<TallyTarget> _discoveredTargets = [];
    private string[] _selectedStatementFiles = [];
    private StatementBalanceInfo? _currentBalances;
    private bool _isDark;
    private bool _tallyConnected;
    private string _activeCompanyName = "";
    private bool _suppressTargetChanged;
    private bool _suppressLedgerPopup;
    private Task _startupInitTask = Task.CompletedTask;
    private bool _isCommitting;
    private string _lastDiagnosticReport = "";
    // Company / bank ledger the rows on screen were analysed for (hashes, GUIDs and bank ledger are bound to them)
    private string _analyzedCompany = "";
    private string _analyzedBankLedger = "";
    private bool _analyzedWithTallyCheck;
    private readonly List<StatementBalanceInfo> _analyzedBalances = [];
    private readonly List<ParsedStatementResult> _analyzedFiles = [];

    // Settings kept in the shared database (same for every PC)
    private const string SettingTidyNarration = "tidy_narration";
    private const string SettingBankDate = "brs_bank_date";
    private bool _loadingSettings;
    private bool _stepBarQueued;

    /// <summary>"Short narration" switch: shows the Party • Mode • Ref line in the grid (and posts it).</summary>
    public static readonly DependencyProperty ShowTidyNarrationProperty =
        DependencyProperty.Register(nameof(ShowTidyNarration), typeof(bool), typeof(MainWindow), new PropertyMetadata(false));
    public bool ShowTidyNarration
    {
        get => (bool)GetValue(ShowTidyNarrationProperty);
        set => SetValue(ShowTidyNarrationProperty, value);
    }

    public ObservableCollection<BankTransactionRow> ReviewRows { get; } = [];
    public ObservableCollection<string> DropdownLedgers { get; } = [];
    public string[] VoucherTypes { get; } = ["Payment", "Receipt", "Contra"];

    public MainWindow()
    {
        InitializeComponent();
        DataContext = this;
        _classifier = new LedgerClassifier(_db);
        _contraEngine = new ContraDedupEngine(_db);

        TxtBackupFolder.Text = _db.BackupDir;
        GridReview.ItemsSource = ReviewRows;
        RefreshDropdownLedgers();
        ReviewRows.CollectionChanged += (_, e) =>
        {
            if (e.NewItems != null) foreach (BankTransactionRow r in e.NewItems) r.PropertyChanged += Row_PropertyChanged;
            if (e.OldItems != null) foreach (BankTransactionRow r in e.OldItems) r.PropertyChanged -= Row_PropertyChanged;
            QueueStepBar();
        };
        UpdateStepBar();

        // Make sure background ML saves (ledger corrections) are written before the process exits
        Closing += (_, _) => _classifier.FlushPendingSaves(TimeSpan.FromSeconds(10));

        Loaded += async (_, _) =>
        {
            TxtFooter.Text = "Loading office database & scanning Tally...";
            _startupInitTask = Task.Run(() =>
            {
                _db.EnsureInitialized();
                _classifier.Initialize();
            });
            var tallyTask = DiscoverTalliesAsync(manualScan: false);
            try
            {
                await _startupInitTask;
                RefreshStats();
                RefreshOwnBanksSummary();
                LoadSettings();
            }
            catch (Exception ex)
            {
                // Typical cause: data_path.txt points to a server share that is offline / not permitted
                ShowThemedDialog("Office Database Not Available",
                    $"Could not open the shared data folder:\n{_db.DataDir}\n\n{ex.Message}\n\n" +
                    "Check that the server share is reachable and that this Windows user can write to it (see data_path.txt beside the .exe). " +
                    "Posting is disabled until the database opens — restart the app once the share is available.", isError: true);
                TxtFooter.Text = "Office database unavailable — posting disabled.";
                BtnAnalyze.IsEnabled = false;
            }
            try { await tallyTask; } catch (Exception ex) { TxtTallyStatus.Text = "Tally detection failed"; TxtFooter.Text = ex.Message; }
        };
    }

    private bool IsKnownTallyLedger(string? name) =>
        !string.IsNullOrWhiteSpace(name) && _tallyLedgers.Contains(name.Trim(), StringComparer.OrdinalIgnoreCase);

    private bool ShowThemedDialog(string title, string message, bool isError = false, bool yesNo = false)
    {
        var dlg = new Window
        {
            Title = title,
            Width = 560,
            SizeToContent = SizeToContent.Height,
            MaxHeight = 560,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            ResizeMode = ResizeMode.CanResize,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var root = new DockPanel { Margin = new Thickness(0) };
        var hdr = new Border
        {
            Background = new SolidColorBrush(isError ? Color.FromRgb(185, 28, 28) : Color.FromRgb(14, 138, 109)),
            Padding = new Thickness(16, 12, 16, 12)
        };
        hdr.Child = new TextBlock { Text = title, Foreground = Brushes.White, FontSize = 15, FontWeight = FontWeights.Bold, TextWrapping = TextWrapping.Wrap };
        DockPanel.SetDock(hdr, Dock.Top);
        root.Children.Add(hdr);

        var footer = new StackPanel
        {
            Orientation = Orientation.Horizontal,
            HorizontalAlignment = HorizontalAlignment.Right,
            Margin = new Thickness(16, 10, 16, 14)
        };
        bool result = false;
        if (yesNo)
        {
            var btnNo = new Button { Content = "No", Padding = new Thickness(18, 6, 18, 6), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
            var btnYes = new Button { Content = "Yes", Padding = new Thickness(18, 6, 18, 6), Background = new SolidColorBrush(isError ? Color.FromRgb(185, 28, 28) : Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
            btnNo.Click += (_, _) => { result = false; dlg.Close(); };
            btnYes.Click += (_, _) => { result = true; dlg.Close(); };
            footer.Children.Add(btnNo);
            footer.Children.Add(btnYes);
        }
        else
        {
            var btnDone = new Button { Content = "Done", Padding = new Thickness(22, 6, 22, 6), Background = new SolidColorBrush(isError ? Color.FromRgb(185, 28, 28) : Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
            btnDone.Click += (_, _) => { result = true; dlg.Close(); };
            footer.Children.Add(btnDone);
        }
        DockPanel.SetDock(footer, Dock.Bottom);
        root.Children.Add(footer);

        var bodyBox = new TextBox
        {
            Text = message,
            IsReadOnly = true,
            TextWrapping = TextWrapping.Wrap,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            MaxHeight = 360,
            Margin = new Thickness(16, 14, 16, 4),
            Padding = new Thickness(8),
            FontSize = 13,
            Background = (Brush)Application.Current.Resources["CardBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"]
        };
        root.Children.Add(bodyBox);
        dlg.Content = root;
        dlg.ShowDialog();
        return result;
    }

    private string GetActiveBackupDir()
    {
        var custom = TxtBackupFolder.Text.Trim();
        return string.IsNullOrWhiteSpace(custom) ? _db.BackupDir : custom;
    }

    private void RefreshStats()
    {
        var bDir = GetActiveBackupDir();
        _ = Task.Run(() =>
        {
            try
            {
                var (ml, posted, contra) = _db.GetStats();
                int xmlCnt = Directory.Exists(_db.ExportDir) ? Directory.GetFiles(_db.ExportDir, "*.xml").Length : 0;
                int bCnt = Directory.Exists(bDir) ? Directory.GetFiles(bDir, "*.zip").Length : 0;
                Dispatcher.BeginInvoke(() =>
                {
                    TxtStats.Text = $"ML: {ml} | Posted: {posted} | Contra: {contra}";
                    BtnClearXml.Content = $"Clear XML ({xmlCnt})";
                    BtnDeleteBackups.Content = $"Delete Backups ({bCnt})";
                });
            }
            catch { }
        });
    }

    private void RefreshDropdownLedgers()
    {
        var all = new HashSet<string>(_tallyLedgers, StringComparer.OrdinalIgnoreCase);
        foreach (var r in ReviewRows)
            if (!string.IsNullOrWhiteSpace(r.SelectedLedger)) all.Add(r.SelectedLedger.Trim());

        DropdownLedgers.Clear();
        foreach (var l in all.OrderBy(x => x, StringComparer.OrdinalIgnoreCase))
            DropdownLedgers.Add(l);

        var prevBank = CmbBankLedger.Text?.Trim() ?? "";
        var bankOnlyList = _bankDetails.Keys.OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList();
        CmbBankLedger.ItemsSource = bankOnlyList;
        if (bankOnlyList.Count > 0 && (string.IsNullOrWhiteSpace(prevBank) || !bankOnlyList.Contains(prevBank, StringComparer.OrdinalIgnoreCase)))
            CmbBankLedger.Text = bankOnlyList[0];
        else
            CmbBankLedger.Text = prevBank;

        CmbCashLedger.ItemsSource = DropdownLedgers.ToList();
        if (string.IsNullOrWhiteSpace(CmbCashLedger.Text)) CmbCashLedger.Text = "Cash";
    }

    private async Task DiscoverTalliesAsync(bool manualScan)
    {
        TxtTallyStatus.Text = "Detecting Tally...";
        _discoveredTargets = await TallyConnector.DiscoverOpenTalliesAsync(TxtTallyHost.Text.Trim());
        _suppressTargetChanged = true;
        CmbTallyTargets.ItemsSource = _discoveredTargets;
        _suppressTargetChanged = false;

        var distinctHosts = _discoveredTargets.Select(t => t.Host).Distinct(StringComparer.OrdinalIgnoreCase).Count();
        if (_discoveredTargets.Count > 1 && (distinctHosts > 1 || manualScan))
        {
            TxtTallyStatus.Text = $"{_discoveredTargets.Count} Open — Choose Tally";
            var picker = new Window
            {
                Title = "Choose Open Tally / Company",
                Width = 480, Height = 320, WindowStartupLocation = WindowStartupLocation.CenterOwner, Owner = this
            };
            var lb = new ListBox { ItemsSource = _discoveredTargets, Margin = new Thickness(12), SelectedIndex = 0 };
            var btn = new Button { Content = "Connect Selected Tally", Height = 32, Margin = new Thickness(12, 0, 12, 12), Background = new SolidColorBrush(Color.FromRgb(14, 138, 109)), Foreground = Brushes.White };
            btn.Click += (_, _) => { picker.DialogResult = true; picker.Close(); };
            var dp = new DockPanel();
            DockPanel.SetDock(btn, Dock.Bottom);
            dp.Children.Add(btn);
            dp.Children.Add(lb);
            picker.Content = dp;

            if (picker.ShowDialog() == true && lb.SelectedItem is TallyTarget chosen)
            {
                CmbTallyTargets.SelectedItem = chosen;
                TxtTallyHost.Text = chosen.Host;
                _activeCompanyName = chosen.CompanyName;
                await ConnectTallyAsync();
                return;
            }
        }
        else if (_discoveredTargets.Count >= 1)
        {
            var active = _discoveredTargets.FirstOrDefault(t => t.IsActive) ?? _discoveredTargets[0];
            CmbTallyTargets.SelectedItem = active;
            TxtTallyHost.Text = active.Host;
            _activeCompanyName = active.CompanyName;
            await ConnectTallyAsync();
            return;
        }
        await ConnectTallyAsync();
        if (!_tallyConnected) ExplainTallyNotFound(manualScan);
    }

    /// <summary>No Tally answered on any port: say in plain words what to switch on (non-technical users).</summary>
    private void ExplainTallyNotFound(bool showDialog)
    {
        bool running = TallyPortFinder.IsTallyRunning();
        TxtTallyStatus.Text = running ? "Tally open, but not sharing data" : "Tally not open (XML Ready)";
        TxtTallyStatus.ToolTip = running
            ? "Tally is running but does not accept connections. See 'Detect Tally' for the one-time setting."
            : "Open Tally and your company, then click 'Detect Tally'.";
        if (!showDialog) return;
        ShowThemedDialog("Tally Not Found",
            running
                ? "Tally is open on this PC, but it is not set to share data with other programs.\n\n" +
                  "One-time setting in TallyPrime:\n" +
                  "  1. Press F1 (Help) → Settings → Connectivity → Client/Server configuration.\n" +
                  "  2. Set 'TallyPrime acts as' = Both, 'Enable ODBC' = Yes. Any port number is fine.\n" +
                  "  3. Save, restart Tally, open your company, and click 'Detect Tally' again.\n\n" +
                  "(Tally ERP 9: F12 Configure → Advanced Configuration → same settings.)"
                : "Tally is not open on this PC.\n\nOpen Tally and your company, then click 'Detect Tally'. " +
                  "Every port is checked automatically — you do not need to know the port number.\n\n" +
                  "If Tally runs on another computer, type its address in 'Tally URL' (for example http://192.168.1.20:9000) and click Connect.",
            isError: false);
    }

    private async Task ConnectTallyAsync()
    {
        var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName);
        var (ok, activeComp, _) = await conn.TestConnectionAsync();
        _tallyConnected = ok;
        if (!ok)
        {
            TxtTallyStatus.Text = "Offline (XML Ready)";
            TxtTallyStatus.Foreground = new SolidColorBrush(Color.FromRgb(214, 137, 16));
            return;
        }

        if (!string.IsNullOrEmpty(activeComp))
        {
            if (string.IsNullOrWhiteSpace(conn.CompanyName))
                conn.CompanyName = activeComp;
            _activeCompanyName = conn.CompanyName;
        }
        // Always reflect the connected Tally + Company Name inside the Tally dropdown even when clicking Connect directly
        var connectedTarget = _discoveredTargets.FirstOrDefault(t =>
            t.Host.Equals(conn.Host, StringComparison.OrdinalIgnoreCase) &&
            t.CompanyName.Equals(conn.CompanyName, StringComparison.OrdinalIgnoreCase));
        if (connectedTarget == null)
        {
            connectedTarget = new TallyTarget { Host = conn.Host, CompanyName = conn.CompanyName, IsActive = true };
            _discoveredTargets = new List<TallyTarget>(_discoveredTargets) { connectedTarget };
        }
        _suppressTargetChanged = true;
        CmbTallyTargets.ItemsSource = null;
        CmbTallyTargets.ItemsSource = _discoveredTargets;
        CmbTallyTargets.SelectedItem = connectedTarget;
        _suppressTargetChanged = false;

        try
        {
            // one request at a time (Tally answers requests one by one)
            var (all, banks, cash, details, partyLedgers, partyInfo) = await conn.FetchLedgersAsync();
            var groups = await conn.FetchGroupsAsync();
            _partyLedgers = partyLedgers;
            _partyBankInfo = partyInfo;
            _pendingBillsCache.Clear();
            if (all.Count > 0) _tallyLedgers = all;
            _bankDetails = details;
            _tallyGroups = groups;

            await _startupInitTask;
            await Task.Run(() => _db.UpsertOwnBanksBatch(
                _activeCompanyName,
                details.Values.Select(d => new OwnBankAccount { TallyLedgerName = d.TallyLedgerName, BankName = d.BankName, AccountNumber = d.AccountNumber, Ifsc = d.Ifsc }),
                overwriteExisting: false));
            RefreshDropdownLedgers();
            RefreshOwnBanksSummary();
            TxtTallyStatus.Text = $"Connected: {conn.CompanyName} ({_tallyLedgers.Count} ledgers)";
            TxtTallyStatus.ToolTip = null;
            TxtTallyStatus.Foreground = new SolidColorBrush(Color.FromRgb(16, 185, 129));
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Tally Connection Error", TallyConnector.DiagnoseError("", "", ex.Message), isError: true);
        }
    }

    private static string DigitsTail(string? raw)
    {
        var d = System.Text.RegularExpressions.Regex.Replace(raw ?? "", @"\D", "");
        return d.Length > 4 ? d[^4..] : d;
    }

    private static string ToLast4Digits(string? raw)
    {
        var d = System.Text.RegularExpressions.Regex.Replace(raw ?? "", @"\D", "");
        return d.Length > 4 ? d[^4..] : d;
    }

    private async Task LoadBillsForRowAsync(BankTransactionRow row)
    {
        var party = (row.SelectedLedger ?? "").Trim();
        // split entries post their party lines "On Account" — no bill picking on them
        if (!_tallyConnected || row.VoucherType == "Contra" || row.IsSplit || string.IsNullOrEmpty(party) ||
            (_partyLedgers.Count > 0 && !_partyLedgers.Contains(party)))
        {
            row.BillAllocations.Clear();
            row.AvailableBills.Clear();
            row.AvailableBills.Add("(None)");
            row.BillRef = "(None)";
            return;
        }

        if (!_pendingBillsCache.TryGetValue(party, out var billObjs))
        {
            var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName, 4);
            billObjs = await conn.FetchPendingBillDetailsAsync(party);
            _pendingBillsCache[party] = billObjs;
        }

        var current = row.BillRef;
        row.AvailableBills.Clear();
        row.AvailableBills.Add("(None)");
        if (billObjs.Count > 0)
            row.AvailableBills.Add(SplitInvoicesOption);
        foreach (var b in billObjs)
            row.AvailableBills.Add(BillAutoMatcher.BillLabel(b));

        if (row.BillAllocations.Count > 0 && !row.AvailableBills.Contains(current))
            row.AvailableBills.Insert(1, current);

        row.BillRef = row.AvailableBills.Contains(current) ? current : "(None)";
    }

    private async void InvoiceCombo_DropDownOpened(object sender, EventArgs e)
    {
        try
        {
            if (sender is ComboBox cb && cb.DataContext is BankTransactionRow row)
                await LoadBillsForRowAsync(row);
        }
        catch { }
    }

    private async void InvoiceCombo_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        try
        {
            if (sender is not ComboBox cb || cb.DataContext is not BankTransactionRow row) return;
            var sel = cb.SelectedItem as string;
            if (string.IsNullOrEmpty(sel)) return;

            if (sel == SplitInvoicesOption)
            {
                await OpenSplitInvoicesDialogAsync(row);
            }
            else if (!sel.StartsWith("Split (", StringComparison.OrdinalIgnoreCase))
            {
                row.BillAllocations.Clear();
            }
        }
        catch { }
    }

    private async Task OpenSplitInvoicesDialogAsync(BankTransactionRow row)
    {
        var party = (row.SelectedLedger ?? "").Trim();
        if (!_pendingBillsCache.TryGetValue(party, out var cachedBills))
        {
            var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName, 4);
            cachedBills = await conn.FetchPendingBillDetailsAsync(party);
            _pendingBillsCache[party] = cachedBills;
        }

        if (cachedBills.Count == 0)
        {
            row.BillRef = "(None)";
            ShowThemedDialog("No Open Invoices", $"No open pending invoices were found in Tally for '{party}'.", isError: false);
            return;
        }

        var existingMap = row.BillAllocations.ToDictionary(x => x.BillName, x => x.AllocateAmount, StringComparer.OrdinalIgnoreCase);
        var items = new ObservableCollection<BillAllocation>(
            cachedBills.Select(b => new BillAllocation
            {
                BillName = b.BillName,
                PendingAmount = b.PendingAmount,
                BillType = "Agst Ref",
                Selected = existingMap.ContainsKey(b.BillName),
                AllocateAmount = existingMap.TryGetValue(b.BillName, out var a) ? a : 0
            })
        );

        var dlg = new Window
        {
            Title = $"Split Across Multiple Invoices — {party}",
            Width = 680, Height = 450,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var root = new DockPanel { Margin = new Thickness(14) };
        var topPanel = new StackPanel { Margin = new Thickness(0, 0, 0, 10) };
        var txtSummary = new TextBlock { FontSize = 13, FontWeight = FontWeights.SemiBold, TextWrapping = TextWrapping.Wrap };
        topPanel.Children.Add(txtSummary);
        DockPanel.SetDock(topPanel, Dock.Top);
        root.Children.Add(topPanel);

        void UpdateSummary()
        {
            decimal alloc = items.Where(x => x.Selected).Sum(x => x.AllocateAmount);
            decimal rem = row.Amount - alloc;
            txtSummary.Text = $"Party: {party}   |   Voucher Amount: ₹{row.Amount:N2}   |   Allocated: ₹{alloc:N2}   |   " +
                (rem >= 0 ? $"Remaining (On Account): ₹{rem:N2}" : $"OVER-ALLOCATED BY ₹{Math.Abs(rem):N2}!");
            txtSummary.Foreground = rem < 0
                ? new SolidColorBrush(Color.FromRgb(239, 68, 68))
                : (Brush)Application.Current.Resources["InkBrush"];
        }

        foreach (var it in items)
        {
            it.PropertyChanged += (_, args) =>
            {
                if (args.PropertyName == nameof(BillAllocation.Selected))
                {
                    if (it.Selected && it.AllocateAmount <= 0)
                    {
                        decimal used = items.Where(x => x != it && x.Selected).Sum(x => x.AllocateAmount);
                        decimal left = Math.Max(0m, row.Amount - used);
                        it.AllocateAmount = it.PendingAmount > 0 ? Math.Min(it.PendingAmount, left) : left;
                    }
                    else if (!it.Selected)
                    {
                        it.AllocateAmount = 0;
                    }
                }
                UpdateSummary();
            };
        }
        UpdateSummary();

        var footer = new DockPanel { Margin = new Thickness(0, 10, 0, 0) };
        var btnFifo = new Button { Content = "⚡ Auto-Fill FIFO", Height = 28, Padding = new Thickness(12, 0, 12, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var rightBtns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var btnClear = new Button { Content = "Clear (None)", Height = 28, Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnCancel = new Button { Content = "Cancel", Height = 28, Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnApply = new Button { Content = "Apply Split", Height = 28, Padding = new Thickness(16, 0, 16, 0), Background = new SolidColorBrush(Color.FromRgb(5, 150, 105)), Foreground = Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.Bold };
        rightBtns.Children.Add(btnClear);
        rightBtns.Children.Add(btnCancel);
        rightBtns.Children.Add(btnApply);
        DockPanel.SetDock(btnFifo, Dock.Left);
        footer.Children.Add(btnFifo);
        footer.Children.Add(rightBtns);
        DockPanel.SetDock(footer, Dock.Bottom);
        root.Children.Add(footer);

        var dg = new DataGrid
        {
            AutoGenerateColumns = false,
            CanUserAddRows = false,
            ItemsSource = items,
            RowHeight = 34,
            HeadersVisibility = DataGridHeadersVisibility.Column,
            RowHeaderWidth = 0,
            Background = (Brush)Application.Current.Resources["CardBg"],
            RowBackground = (Brush)Application.Current.Resources["RowBg"],
            AlternatingRowBackground = (Brush)Application.Current.Resources["RowAltBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"],
            HorizontalGridLinesBrush = (Brush)Application.Current.Resources["BorderBrush"],
            GridLinesVisibility = DataGridGridLinesVisibility.Horizontal
        };

        var chkCol = new DataGridTemplateColumn { Header = "Use", Width = 48 };
        var chkF = new FrameworkElementFactory(typeof(CheckBox));
        chkF.SetValue(HorizontalAlignmentProperty, HorizontalAlignment.Center);
        chkF.SetValue(VerticalAlignmentProperty, VerticalAlignment.Center);
        chkF.SetBinding(CheckBox.IsCheckedProperty, new Binding("Selected") { Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
        chkCol.CellTemplate = new DataTemplate { VisualTree = chkF };
        dg.Columns.Add(chkCol);

        dg.Columns.Add(new DataGridTextColumn { Header = "Invoice No.", Binding = new Binding("BillName"), IsReadOnly = true, Width = new DataGridLength(1.4, DataGridLengthUnitType.Star) });
        dg.Columns.Add(new DataGridTextColumn { Header = "Pending (₹)", Binding = new Binding("PendingAmount") { Converter = new IndianAmountConverter() }, IsReadOnly = true, Width = 115 });

        var amtCol = new DataGridTemplateColumn { Header = "Allocate (₹)", Width = 130 };
        var amtF = new FrameworkElementFactory(typeof(TextBox));
        amtF.SetValue(TextBox.HeightProperty, 26.0);
        amtF.SetBinding(TextBox.TextProperty, new Binding("AllocateAmount") { Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.LostFocus, StringFormat = "{0:0.##}" });
        amtCol.CellTemplate = new DataTemplate { VisualTree = amtF };
        dg.Columns.Add(amtCol);

        root.Children.Add(dg);

        btnFifo.Click += (_, _) =>
        {
            decimal left = row.Amount;
            foreach (var it in items)
            {
                if (left <= 0) { it.Selected = false; it.AllocateAmount = 0; }
                else
                {
                    decimal take = it.PendingAmount > 0 ? Math.Min(it.PendingAmount, left) : left;
                    it.Selected = true;
                    it.AllocateAmount = Math.Round(take, 2);
                    left = Math.Round(left - take, 2);
                }
            }
            UpdateSummary();
        };

        btnClear.Click += (_, _) =>
        {
            row.BillAllocations.Clear();
            row.BillRef = "(None)";
            dlg.Close();
        };

        btnCancel.Click += (_, _) =>
        {
            row.BillRef = row.BillAllocations.Count > 0 ? $"Split ({row.BillAllocations.Count} bills)" : "(None)";
            dlg.Close();
        };

        btnApply.Click += (_, _) =>
        {
            var chosen = items.Where(x => x.Selected && x.AllocateAmount > 0).ToList();
            decimal totalAlloc = chosen.Sum(x => x.AllocateAmount);
            if (totalAlloc > row.Amount)
            {
                ShowThemedDialog("Over-Allocated", $"Total allocated (₹{totalAlloc:N2}) exceeds the voucher amount (₹{row.Amount:N2}). Reduce the split amounts first.", isError: true);
                return;
            }
            row.BillAllocations = chosen;
            if (chosen.Count == 0)
            {
                row.BillRef = "(None)";
            }
            else if (chosen.Count == 1 && totalAlloc == row.Amount)
            {
                var lbl = chosen[0].PendingAmount > 0 ? $"{chosen[0].BillName} (₹{chosen[0].PendingAmount:N2})" : chosen[0].BillName;
                if (!row.AvailableBills.Contains(lbl)) row.AvailableBills.Add(lbl);
                row.BillRef = lbl;
            }
            else
            {
                var splitLabel = $"Split ({chosen.Count} bills)";
                if (!row.AvailableBills.Contains(splitLabel)) row.AvailableBills.Insert(1, splitLabel);
                row.BillRef = splitLabel;
            }
            dlg.Close();
        };

        dlg.Content = root;
        dlg.ShowDialog();
    }

    private void RefreshOwnBanksSummary()
    {
        if (string.IsNullOrWhiteSpace(_activeCompanyName))
        {
            TxtOwnBanksInfo.Text = "Connect to a Tally company to load its Bank Details.";
            return;
        }
        var ownBanks = _db.GetOwnBanks(_activeCompanyName);
        TxtOwnBanksInfo.Text = ownBanks.Count > 0
            ? $"Contra Banks ({_activeCompanyName}): " + string.Join(" • ", ownBanks.Select(b => b.DisplayLabel))
            : $"No bank details saved for {_activeCompanyName}. Click 'Bank Details' to add A/c last 4 digits or IFSC.";
    }

    private async void BtnNewBankLedger_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new Window
        {
            Title = string.IsNullOrWhiteSpace(_activeCompanyName) ? "Create New Bank Account" : $"Create New Bank Account — {_activeCompanyName}",
            Width = 440,
            SizeToContent = SizeToContent.Height,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            ResizeMode = ResizeMode.NoResize,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var root = new StackPanel { Margin = new Thickness(16) };
        root.Children.Add(new TextBlock { Text = "Bank Ledger Name *", FontSize = 11.5, Foreground = (Brush)Application.Current.Resources["MutedBrush"], Margin = new Thickness(0, 0, 0, 3) });
        var typed = (CmbBankLedger.Text ?? "").Trim();
        var txtName = new TextBox
        {
            Text = _bankDetails.ContainsKey(typed) ? "" : typed,
            Height = 30, Margin = new Thickness(0, 0, 0, 10)
        };
        root.Children.Add(txtName);

        root.Children.Add(new TextBlock { Text = "Under Group", FontSize = 11.5, Foreground = (Brush)Application.Current.Resources["MutedBrush"], Margin = new Thickness(0, 0, 0, 3) });
        var cmbGroup = new ComboBox { Height = 30, Margin = new Thickness(0, 0, 0, 10), ItemsSource = new[] { "Bank Accounts", "Bank OD A/c", "Bank OCC A/c" }, SelectedIndex = 0 };
        root.Children.Add(cmbGroup);

        var rowGrid = new Grid { Margin = new Thickness(0, 0, 0, 14) };
        rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(10) });
        rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });

        var spAcc = new StackPanel();
        spAcc.Children.Add(new TextBlock { Text = "A/c Last 4 Digits (Optional)", FontSize = 11.5, Foreground = (Brush)Application.Current.Resources["MutedBrush"], Margin = new Thickness(0, 0, 0, 3) });
        var txtAcc = new TextBox { Height = 30, MaxLength = 4 };
        spAcc.Children.Add(txtAcc);
        Grid.SetColumn(spAcc, 0);
        rowGrid.Children.Add(spAcc);

        var spIfsc = new StackPanel();
        spIfsc.Children.Add(new TextBlock { Text = "IFSC Code (Optional)", FontSize = 11.5, Foreground = (Brush)Application.Current.Resources["MutedBrush"], Margin = new Thickness(0, 0, 0, 3) });
        var txtIfsc = new TextBox { Height = 30, MaxLength = 11 };
        spIfsc.Children.Add(txtIfsc);
        Grid.SetColumn(spIfsc, 2);
        rowGrid.Children.Add(spIfsc);
        root.Children.Add(rowGrid);

        var btns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var btnCancel = new Button { Content = "Cancel", Height = 30, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnCreate = new Button { Content = "Create Bank Account", Height = 30, Padding = new Thickness(16, 0, 16, 0), Background = new SolidColorBrush(Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        btns.Children.Add(btnCancel);
        btns.Children.Add(btnCreate);
        root.Children.Add(btns);

        bool confirmed = false;
        btnCancel.Click += (_, _) => dlg.Close();
        btnCreate.Click += (_, _) =>
        {
            if (string.IsNullOrWhiteSpace(txtName.Text))
            {
                ShowThemedDialog("Missing Name", "Please enter a Bank Ledger Name.", isError: true);
                return;
            }
            confirmed = true;
            dlg.Close();
        };

        dlg.Content = root;
        dlg.Loaded += (_, _) => { txtName.Focus(); txtName.SelectAll(); };
        dlg.ShowDialog();
        if (!confirmed) return;

        var ledgerName = txtName.Text.Trim();
        var parentGroup = cmbGroup.SelectedItem?.ToString() ?? "Bank Accounts";
        var accLast4 = ToLast4Digits(txtAcc.Text);
        var ifsc = (txtIfsc.Text ?? "").Trim().ToUpperInvariant();

        if (_tallyConnected)
        {
            TxtFooter.Text = $"Creating bank ledger '{ledgerName}' in Tally...";
            var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName);
            var (ok, err) = await conn.CreateLedgersAsync([new MissingLedgerItem { Name = ledgerName, ParentGroup = parentGroup, Role = "Bank" }]);
            if (!ok)
            {
                ShowThemedDialog("Could Not Create Bank Ledger", $"Tally returned an error while creating '{ledgerName}':\n{err}", isError: true);
                return;
            }
        }

        if (!_tallyLedgers.Contains(ledgerName, StringComparer.OrdinalIgnoreCase))
            _tallyLedgers.Add(ledgerName);
        _bankDetails[ledgerName] = new TallyBankDetail
        {
            TallyLedgerName = ledgerName,
            BankName = ledgerName,
            AccountNumber = accLast4,
            AccountLast4 = accLast4,
            Ifsc = ifsc
        };

        if (!string.IsNullOrWhiteSpace(_activeCompanyName))
        {
            await _startupInitTask;
            await Task.Run(() => _db.UpsertOwnBanksBatch(
                _activeCompanyName,
                [new OwnBankAccount { TallyLedgerName = ledgerName, BankName = ledgerName, AccountNumber = accLast4, Ifsc = ifsc }],
                overwriteExisting: true));
            RefreshOwnBanksSummary();
        }

        RefreshDropdownLedgers();
        CmbBankLedger.Text = ledgerName;
        TxtFooter.Text = _tallyConnected
            ? $"Created bank account '{ledgerName}' under '{parentGroup}' in Tally."
            : $"Added bank account '{ledgerName}' (will be created in Tally when pushed/exported).";
    }

    private void BtnBankDetails_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_activeCompanyName))
        {
            ShowThemedDialog("No Tally Company Connected", "Please connect to a Tally company first so bank details are saved strictly for that company.", isError: true);
            return;
        }
        var banks = new ObservableCollection<OwnBankAccount>(_db.GetOwnBanks(_activeCompanyName).Select(b => { b.AccountNumber = ToLast4Digits(b.AccountNumber); return b; }));

        var dlg = new Window
        {
            Title = $"Bank Details — {_activeCompanyName} (Sourced from Tally + Editable)",
            Width = 760, Height = 460,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var root = new DockPanel { Margin = new Thickness(14) };

        var info = new TextBlock
        {
            Text = "Bank A/c last 4 digits and IFSC are auto-sourced from Tally (or extracted from bank ledger names). Edit any blank cell or add a bank below so inter-bank transfers auto-detect as Contra:",
            TextWrapping = TextWrapping.Wrap,
            FontSize = 12.5,
            Margin = new Thickness(0, 0, 0, 10)
        };
        DockPanel.SetDock(info, Dock.Top);
        root.Children.Add(info);

        // Quick Add Row + Save / Close footer
        var bottomPanel = new StackPanel { Margin = new Thickness(0, 10, 0, 0) };
        var addGrid = new Grid { Margin = new Thickness(0, 0, 0, 10) };
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1.4, GridUnitType.Star) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(0.8, GridUnitType.Star) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(0.9, GridUnitType.Star) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(8) });
        addGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

        var cmbNewBank = new ComboBox { IsEditable = true, Height = 28, ItemsSource = DropdownLedgers, ToolTip = "Tally Bank Ledger Name" };
        var txtNewAcc = new TextBox { Height = 28, MaxLength = 4, ToolTip = "Last 4 digits only (e.g. 1592)" };
        var txtNewIfsc = new TextBox { Height = 28, ToolTip = "IFSC Code (e.g. AUBL0002345)" };
        var btnAdd = new Button { Content = "+ Add Bank", Height = 28, Padding = new Thickness(12, 0, 12, 0), Background = new SolidColorBrush(Color.FromRgb(29, 78, 216)), Foreground = Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.SemiBold };

        Grid.SetColumn(cmbNewBank, 0);
        Grid.SetColumn(txtNewAcc, 2);
        Grid.SetColumn(txtNewIfsc, 4);
        Grid.SetColumn(btnAdd, 6);
        addGrid.Children.Add(cmbNewBank);
        addGrid.Children.Add(txtNewAcc);
        addGrid.Children.Add(txtNewIfsc);
        addGrid.Children.Add(btnAdd);

        var addLabels = new TextBlock
        {
            Text = "Add Bank:  [Tally Bank Ledger]   |   [A/c Last 4 Digits]   |   [IFSC Code]",
            FontSize = 11,
            Foreground = (Brush)Application.Current.Resources["MutedBrush"],
            Margin = new Thickness(0, 0, 0, 3)
        };
        bottomPanel.Children.Add(addLabels);
        bottomPanel.Children.Add(addGrid);

        var btnBar = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var btnDelete = new Button { Content = "Remove Selected", Height = 28, Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnCancel = new Button { Content = "Cancel", Height = 28, Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnSave = new Button { Content = "Save Bank Details", Height = 28, Padding = new Thickness(16, 0, 16, 0), Background = new SolidColorBrush(Color.FromRgb(5, 150, 105)), Foreground = Brushes.White, BorderThickness = new Thickness(0), FontWeight = FontWeights.Bold };
        btnBar.Children.Add(btnDelete);
        btnBar.Children.Add(btnCancel);
        btnBar.Children.Add(btnSave);
        bottomPanel.Children.Add(btnBar);

        DockPanel.SetDock(bottomPanel, Dock.Bottom);
        root.Children.Add(bottomPanel);

        var dg = new DataGrid
        {
            AutoGenerateColumns = false,
            CanUserAddRows = false,
            ItemsSource = banks,
            RowHeight = 36,
            HeadersVisibility = DataGridHeadersVisibility.Column,
            RowHeaderWidth = 0,
            Background = (Brush)Application.Current.Resources["CardBg"],
            RowBackground = (Brush)Application.Current.Resources["RowBg"],
            AlternatingRowBackground = (Brush)Application.Current.Resources["RowAltBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"],
            HorizontalGridLinesBrush = (Brush)Application.Current.Resources["BorderBrush"],
            GridLinesVisibility = DataGridGridLinesVisibility.Horizontal
        };

        DataGridTemplateColumn MakeInputCol(string header, string prop, double starWidth)
        {
            var col = new DataGridTemplateColumn { Header = header, Width = new DataGridLength(starWidth, DataGridLengthUnitType.Star) };
            var tbFactory = new FrameworkElementFactory(typeof(TextBox));
            tbFactory.SetValue(TextBox.HeightProperty, 26.0);
            tbFactory.SetBinding(TextBox.TextProperty, new Binding(prop) { Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
            col.CellTemplate = new DataTemplate { VisualTree = tbFactory };
            return col;
        }

        dg.Columns.Add(new DataGridTextColumn { Header = "Tally Bank Ledger", Binding = new Binding("TallyLedgerName"), IsReadOnly = true, Width = new DataGridLength(1.5, DataGridLengthUnitType.Star) });
        dg.Columns.Add(MakeInputCol("Last 4 Digits", "AccountNumber", 0.9));
        dg.Columns.Add(MakeInputCol("IFSC Code", "Ifsc", 1.1));
        root.Children.Add(dg);

        btnAdd.Click += (_, _) =>
        {
            var lName = (cmbNewBank.Text ?? "").Trim();
            if (string.IsNullOrEmpty(lName)) return;
            var existing = banks.FirstOrDefault(b => b.TallyLedgerName.Equals(lName, StringComparison.OrdinalIgnoreCase));
            if (existing != null)
            {
                if (!string.IsNullOrWhiteSpace(txtNewAcc.Text)) existing.AccountNumber = ToLast4Digits(txtNewAcc.Text);
                if (!string.IsNullOrWhiteSpace(txtNewIfsc.Text)) existing.Ifsc = txtNewIfsc.Text.Trim().ToUpperInvariant();
                dg.Items.Refresh();
            }
            else
            {
                banks.Add(new OwnBankAccount
                {
                    TallyLedgerName = lName,
                    AccountNumber = ToLast4Digits(txtNewAcc.Text),
                    Ifsc = txtNewIfsc.Text.Trim().ToUpperInvariant()
                });
            }
            cmbNewBank.Text = "";
            txtNewAcc.Text = "";
            txtNewIfsc.Text = "";
        };

        var removedNames = new List<string>();
        btnDelete.Click += (_, _) =>
        {
            if (dg.SelectedItem is OwnBankAccount sel)
            {
                removedNames.Add(sel.TallyLedgerName);
                banks.Remove(sel);
            }
        };

        btnCancel.Click += (_, _) => dlg.Close();
        btnSave.Click += (_, _) =>
        {
            foreach (var rName in removedNames) _db.DeleteOwnBank(_activeCompanyName, rName);
            foreach (var b in banks) { b.AccountNumber = ToLast4Digits(b.AccountNumber); b.Ifsc = (b.Ifsc ?? "").Trim().ToUpperInvariant(); b.Aliases = ""; }
            _db.UpsertOwnBanksBatch(_activeCompanyName, banks, overwriteExisting: true);
            RefreshOwnBanksSummary();
            dlg.Close();
        };

        dlg.Content = root;
        dlg.ShowDialog();
    }

    private async void BtnDetectTally_Click(object sender, RoutedEventArgs e) => await DiscoverTalliesAsync(manualScan: true);
    private async void BtnConnect_Click(object sender, RoutedEventArgs e) => await ConnectTallyAsync();

    private void BtnBrowseBackup_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog
        {
            Title = "Choose Tally Backup Destination Folder",
            InitialDirectory = Directory.Exists(GetActiveBackupDir()) ? GetActiveBackupDir() : _db.BackupDir
        };
        if (dlg.ShowDialog() == true)
        {
            TxtBackupFolder.Text = dlg.FolderName;
            RefreshStats();
        }
    }

    private async void CmbTallyTargets_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (!_suppressTargetChanged && CmbTallyTargets.SelectedItem is TallyTarget t && IsLoaded)
        {
            TxtTallyHost.Text = t.Host;
            _activeCompanyName = t.CompanyName;
            await ConnectTallyAsync();
        }
    }

    // Separate Button 1: Select File(s)
    private void BtnSelectFiles_Click(object sender, RoutedEventArgs e)
    {
        var dlg = new OpenFileDialog
        {
            Multiselect = true,
            Filter = "Bank Statements (PDF, Excel, CSV)|*.pdf;*.xlsx;*.xlsm;*.xls;*.csv"
        };
        if (dlg.ShowDialog() != true) return;
        SetSelectedFiles(dlg.FileNames);
    }

    private static readonly string[] StatementExtensions = [".pdf", ".xlsx", ".xlsm", ".xls", ".csv"];

    private void SetSelectedFiles(string[] files)
    {
        _selectedStatementFiles = files;
        _filesChangedSinceAnalyze = true;
        if (SetupPanel.Visibility != Visibility.Visible) BtnToggleSetup_Click(BtnToggleSetup, new RoutedEventArgs());   // Analyze button is there
        var names = _selectedStatementFiles.Select(Path.GetFileName).ToList();
        TxtSelectedFiles.Text = names.Count == 1 ? names[0]! : $"{names.Count} files: {string.Join(", ", names)}";
        TxtFooter.Text = $"Selected {names.Count} file(s). Click 'Analyze' to parse and predict ledgers.";
        UpdateStepBar();
    }

    // ------------------------------------------------------------------ drag & drop statement files onto the window
    private static string[] DroppedStatementFiles(DragEventArgs e) =>
        e.Data.GetDataPresent(DataFormats.FileDrop) && e.Data.GetData(DataFormats.FileDrop) is string[] paths
            ? paths.Where(p => File.Exists(p) && StatementExtensions.Contains(Path.GetExtension(p).ToLowerInvariant())).ToArray()
            : [];

    private void Window_PreviewDragOver(object sender, DragEventArgs e)
    {
        if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;   // text dragged inside a cell: leave it alone
        e.Effects = DroppedStatementFiles(e).Length > 0 && !_isCommitting && BtnAnalyze.IsEnabled ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }

    private void Window_PreviewDrop(object sender, DragEventArgs e)
    {
        if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return;
        e.Handled = true;
        if (_isCommitting || !BtnAnalyze.IsEnabled) return;
        var files = DroppedStatementFiles(e);
        if (files.Length == 0)
        {
            // shown after the drop finishes, so Explorer is not left waiting on our dialog
            Dispatcher.BeginInvoke(new Action(() =>
                ShowThemedDialog("Not a Statement File", "Drop a bank statement file: PDF, Excel (.xlsx / .xls / .xlsm) or CSV.", isError: false)));
            return;
        }
        SetSelectedFiles(files);
    }

    // ------------------------------------------------------------------ step bar: Choose → Analyze → Check → Post
    private bool _filesChangedSinceAnalyze;

    private void Row_PropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(BankTransactionRow.NeedsReview) or nameof(BankTransactionRow.PostStatus) or nameof(BankTransactionRow.Selected))
            QueueStepBar();
    }

    /// <summary>Many rows change at once (bulk set, posting): update the bar once, after they are done.</summary>
    private void QueueStepBar()
    {
        if (_stepBarQueued) return;
        _stepBarQueued = true;
        Dispatcher.BeginInvoke(new Action(() => { _stepBarQueued = false; UpdateStepBar(); }), System.Windows.Threading.DispatcherPriority.Background);
    }

    private void UpdateStepBar()
    {
        int toCheck = 0, toPost = 0, done = 0;
        foreach (var r in ReviewRows)
        {
            if (r.PostStatus == "DONE") { done++; continue; }
            if (r.NeedsReview) toCheck++;
            else if (r.Selected) toPost++;
        }
        int now;
        if (_selectedStatementFiles.Length == 0 && ReviewRows.Count == 0) now = 1;
        else if (ReviewRows.Count == 0 || _filesChangedSinceAnalyze) now = 2;
        else if (toCheck > 0) now = 3;
        else now = 4;
        bool allPosted = ReviewRows.Count > 0 && !_filesChangedSinceAnalyze && done > 0 && toPost == 0 && toCheck == 0;

        var pills = new[] { Step1, Step2, Step3, Step4 };
        for (int i = 0; i < 4; i++)
            pills[i].Tag = (i + 1) < now || (allPosted && i == 3) ? "Done" : (i + 1) == now ? "Now" : null;
        TxtStep3.Text = toCheck > 0 && now == 3 ? $"3 Check ⚠ ({toCheck})" : "3 Check ⚠";
        Step3.ToolTip = toCheck > 0 ? $"{toCheck} row(s) need a ledger check — press F8 to jump to the next one" : "Rows marked ⚠ need a ledger check";
    }

    /// <summary>Hide / show the Tally and Statement panels, so more rows fit on the screen.</summary>
    private void BtnToggleSetup_Click(object sender, RoutedEventArgs e)
    {
        bool hide = SetupPanel.Visibility == Visibility.Visible;
        SetupPanel.Visibility = hide ? Visibility.Collapsed : Visibility.Visible;
        BtnToggleSetup.Content = hide ? "▼ Show setup" : "▲ Hide setup";
        // while hidden, still show what the rows belong to
        BtnToggleSetup.ToolTip = hide
            ? $"Show the Tally and Statement panels.\nCompany: {_activeCompanyName}\nBank ledger: {CmbBankLedger.Text}\nFile: {TxtSelectedFiles.Text}"
            : "Hide the Tally and Statement panels to see more rows. Click again to show them.";
    }

    // ------------------------------------------------------------------ settings + More ▾ menu
    private void LoadSettings()
    {
        _loadingSettings = true;
        try
        {
            ChkTidy.IsChecked = _db.GetBoolSetting(SettingTidyNarration, false);
            MenuBankDate.IsChecked = _db.GetBoolSetting(SettingBankDate, true);
            ShowTidyNarration = ChkTidy.IsChecked == true;
        }
        finally { _loadingSettings = false; }
    }

    private void ChkTidy_Changed(object sender, RoutedEventArgs e)
    {
        ShowTidyNarration = ChkTidy.IsChecked == true;
        if (_loadingSettings) return;
        try { _db.SetBoolSetting(SettingTidyNarration, ShowTidyNarration); } catch { /* shown again next start */ }
        TxtFooter.Text = ShowTidyNarration
            ? "Short narration ON — Tally gets 'Party • Mode • Ref' on the first line and the bank's text below it."
            : "Short narration OFF — Tally gets only the bank's original narration.";
    }

    private void MenuBankDate_Click(object sender, RoutedEventArgs e)
    {
        try { _db.SetBoolSetting(SettingBankDate, MenuBankDate.IsChecked); } catch { }
        TxtFooter.Text = MenuBankDate.IsChecked
            ? "Bank date (BRS) will be filled with the statement date on posted entries."
            : "Bank date (BRS) will be left empty on posted entries.";
    }

    private void BtnMore_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button b || b.ContextMenu == null) return;
        b.ContextMenu.PlacementTarget = b;
        b.ContextMenu.Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom;
        b.ContextMenu.IsOpen = true;
    }

    // ------------------------------------------------------------------ automatic bill matching
    /// <summary>
    /// Reads the pending bills of the parties involved and picks a bill wherever exactly one bill has exactly the entry's
    /// amount (see <see cref="BillAutoMatcher"/>). Runs after Analyze and after a ledger is changed.
    /// </summary>
    private async Task AutoMatchBillsAsync(IEnumerable<BankTransactionRow> changedRows)
    {
        if (!_tallyConnected) return;
        try
        {
            var parties = changedRows.Where(BillAutoMatcher.IsEligible).Select(r => r.SelectedLedger.Trim())
                .Where(p => _partyLedgers.Contains(p)).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
            if (parties.Count == 0) return;
            var company = _activeCompanyName;
            foreach (var party in parties.Where(p => !_pendingBillsCache.ContainsKey(p)))
            {
                var conn = new TallyConnector(TxtTallyHost.Text.Trim(), company, 4);
                var bills = await conn.FetchPendingBillDetailsAsync(party);
                if (company != _activeCompanyName) return;   // company switched meanwhile
                _pendingBillsCache[party] = bills;
            }
            var partySet = new HashSet<string>(parties, StringComparer.OrdinalIgnoreCase);
            var billsByParty = _pendingBillsCache.Where(kv => partySet.Contains(kv.Key)).ToDictionary(kv => kv.Key, kv => kv.Value, StringComparer.OrdinalIgnoreCase);
            var picks = BillAutoMatcher.Pick(ReviewRows.ToList(), billsByParty);
            int n = 0;
            foreach (var (row, bill) in picks)
            {
                if (!partySet.Contains(row.SelectedLedger.Trim())) continue;
                await LoadBillsForRowAsync(row);
                var label = BillAutoMatcher.BillLabel(bill);
                if (!row.AvailableBills.Contains(label)) row.AvailableBills.Add(label);
                row.BillRef = label;
                n++;
            }
            if (n > 0) TxtFooter.Text += $"  •  🧾 {n} bill(s) matched automatically (same amount, only one open bill)";
        }
        catch { /* bills stay for the user to choose */ }
    }

    private static string ComputeFileSha256(string filePath)
    {
        using var sha = System.Security.Cryptography.SHA256.Create();
        using var fs = File.Open(filePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        return Convert.ToHexString(sha.ComputeHash(fs)).ToLowerInvariant();
    }

    private void UpdateSelectedTotalsBar()
    {
        if (ReviewRows.Count == 0)
        {
            SelectedTotalsBar.Visibility = Visibility.Collapsed;
            return;
        }
        int selCnt = 0;
        decimal selDr = 0, selCr = 0;
        foreach (var r in ReviewRows)
        {
            if (!r.Selected) continue;
            selCnt++;
            selDr += r.Debit;
            selCr += r.Credit;
        }
        decimal net = selCr - selDr;
        var netSign = net >= 0 ? "+" : "−";
        TxtSelectedTotals.Text = $"Selected to Post: {selCnt} / {ReviewRows.Count} rows   •   Total Dr (Receipts): ₹{selCr:N2}   •   Total Cr (Payments): ₹{selDr:N2}   •   Net Change in Bank: {netSign}₹{Math.Abs(net):N2}";
        SelectedTotalsBar.Visibility = Visibility.Visible;
    }

    private void PostCheckBox_Click(object sender, RoutedEventArgs e) => UpdateSelectedTotalsBar();

    // Separate Button 2: Analyze
    private async void BtnAnalyze_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedStatementFiles.Length == 0)
        {
            ShowThemedDialog("No File Selected", "Please click 'Select File(s)' first to choose a digital bank statement (PDF, Excel, or CSV).", isError: true);
            return;
        }

        var bankLedger = CmbBankLedger.Text.Trim();
        var cashLedger = string.IsNullOrWhiteSpace(CmbCashLedger.Text) ? "Cash" : CmbCashLedger.Text.Trim();
        if (string.IsNullOrEmpty(bankLedger))
        {
            ShowThemedDialog("Missing Bank Ledger", "Please select or type your Tally Bank Ledger name first.", isError: true);
            return;
        }

        BtnAnalyze.IsEnabled = false;
        TxtFooter.Text = "Analyzing statement(s), checking balances & overlaps, and predicting ledgers...";
        await _startupInitTask;
        try
        {
            _lastDiagnosticReport = "";
            var allTxns = new List<BankTransactionRow>();
            StatementBalanceInfo? firstBal = null;
            var summaries = new List<string>();
            var parsedFiles = new List<ParsedStatementResult>();

            var savedLayouts = await Task.Run(() => { try { return _db.GetLayoutTemplates(); } catch { return new List<LayoutTemplate>(); } });
            foreach (var file in _selectedStatementFiles)
            {
                var fHash = await Task.Run(() => ComputeFileSha256(file));
                var prevFile = await Task.Run(() => _db.FindPreviouslyPostedFile(fHash, _activeCompanyName));
                if (prevFile != null)
                {
                    var dupMsg = $"This exact file ('{Path.GetFileName(file)}') was ALREADY posted:\n\n"
                        + $"• Company: {prevFile.CompanyName}\n"
                        + $"• Bank Ledger: {prevFile.BankLedger}\n"
                        + $"• Entries Posted: {prevFile.PostedCount}\n"
                        + $"• Posted On: {prevFile.CreatedAt} by {prevFile.PostedBy}\n\n"
                        + "Do you still want to analyze this file?";
                    if (!ShowThemedDialog("Duplicate Statement File Detected", dupMsg, isError: true, yesNo: true))
                        return;
                }
                var parsed = await BankStatementParser.ParseAsync(file, PwdPdf.Password, savedLayouts);
                // Not read reliably (nothing found / does not reconcile / incomplete / layout not understood)?
                // Offer to teach this format's columns once — saved for every PC — and read it again.
                var unreliable = UnreliableReadReason(parsed);
                if (unreliable.Length > 0 && Path.GetExtension(file).Equals(".pdf", StringComparison.OrdinalIgnoreCase)
                    && ShowThemedDialog("Statement Not Read Reliably",
                        $"'{Path.GetFileName(file)}' was not read reliably:\n\n{unreliable}\n\n"
                        + "Teach its columns now? You mark the columns once on any page that shows the transactions; the layout is "
                        + "saved for every PC and used automatically for this bank's statements from then on.",
                        isError: true, yesNo: true))
                {
                    if (TeachLayoutWindow.ShowFor(this, _db, file, PwdPdf.Password))
                    {
                        savedLayouts = await Task.Run(() => _db.GetLayoutTemplates());
                        parsed = await BankStatementParser.ParseAsync(file, PwdPdf.Password, savedLayouts);
                    }
                }
                parsedFiles.Add(parsed);
                firstBal ??= parsed.Balances;
                _lastDiagnosticReport = string.IsNullOrEmpty(_lastDiagnosticReport)
                    ? parsed.DiagnosticReport
                    : _lastDiagnosticReport + "\n\n" + parsed.DiagnosticReport;
                summaries.Add($"{parsed.SourceFile} ({parsed.BankDetected}, {parsed.Transactions.Count} txns, {parsed.ExtractionMethod})");
                allTxns.AddRange(parsed.Transactions);
            }

            if (allTxns.Count == 0)
            {
                ShowThemedDialog("Analysis Failed", "No transactions were found in the selected file(s).", isError: true);
                return;
            }

            // Several files analysed together are all posted to ONE bank ledger — stop if they are clearly different accounts
            var distinctAccounts = parsedFiles.Select(p => DigitsTail(p.AccountNumberDetected)).Where(a => a.Length >= 4).Distinct().ToList();
            var distinctBanks = parsedFiles.Select(p => p.BankDetected).Where(b => b != "Scheduled Bank (Auto)").Distinct().ToList();
            if (parsedFiles.Count > 1 && (distinctAccounts.Count > 1 || distinctBanks.Count > 1))
            {
                var mixMsg = "The selected files look like DIFFERENT bank accounts, but all rows will be posted to the single bank ledger "
                    + $"'{bankLedger}':\n\n" + string.Join("\n", parsedFiles.Select(p => $"• {p.SourceFile}: {p.BankDetected} A/c {p.AccountNumberDetected}"))
                    + "\n\nContinue anyway?";
                if (!ShowThemedDialog("Different Bank Accounts Selected", mixMsg, isError: true, yesNo: true))
                    return;
            }

            // Month-to-month continuity: this statement must open where the previous statement of the account closed
            var gaps = new List<string>();
            foreach (var pf in parsedFiles)
            {
                var pb = pf.Balances;
                if (pb.StatementOpening is not decimal op || string.IsNullOrEmpty(pb.FromDate)) continue;
                StatementHistoryEntry? prevSt = null;
                try { prevSt = await Task.Run(() => _db.GetPreviousStatement(_activeCompanyName, bankLedger, pb.FromDate)); } catch { /* optional check */ }
                if (prevSt != null && prevSt.Closing != op)
                    gaps.Add($"• {pf.SourceFile} opens with ₹{op:N2} on {BankStatementParser.FormatDisplayDate(pb.FromDate)}, but the previous statement "
                        + $"posted for '{bankLedger}' ({prevSt.SourceFile}) closed with ₹{prevSt.Closing:N2} on {BankStatementParser.FormatDisplayDate(prevSt.ToDate)} "
                        + $"— difference ₹{Math.Abs(prevSt.Closing - op):N2}.");
            }
            if (gaps.Count > 0 && !ShowThemedDialog("Statements Do Not Continue",
                    string.Join("\n", gaps) + "\n\nTransactions between these statements may be missing, or a statement / period was skipped. "
                    + "Check that no statement is missing before posting.\n\nContinue analysing?", isError: true, yesNo: true))
                return;

            // Ask the user for every row whose Debit/Credit the statement does not state and the running balance cannot
            // prove — BEFORE duplicate / contra / ML analysis, so everything downstream uses the confirmed direction.
            var uncertain = allTxns.Where(BankStatementParser.IsDirectionUncertain).ToList();
            if (uncertain.Count > 0)
            {
                var answers = ShowConfirmDirectionDialog(uncertain);
                if (answers == null)
                {
                    TxtFooter.Text = "Analysis cancelled — Dr/Cr of some rows was not confirmed.";
                    return;
                }
                foreach (var pf in parsedFiles)
                {
                    var mine = answers.Where(a => pf.Transactions.Contains(a.Key)).ToDictionary(a => a.Key, a => a.Value);
                    if (mine.Count > 0) BankStatementParser.ApplyConfirmedDirections(pf, mine);
                }
                firstBal = parsedFiles[0].Balances;
                _lastDiagnosticReport = string.Join("\n\n", parsedFiles.Select(pf => pf.DiagnosticReport));
            }

            List<TallyExistingVoucher>? liveVouchers = null;
            (bool found, decimal op, decimal cl) tallyBal = (false, 0m, 0m);
            bool tallyCheckOk = false;
            if (_tallyConnected)
            {
                var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName, 8);
                var dates = allTxns.Select(t => t.TxnDate).OrderBy(d => d, StringComparer.Ordinal).ToList();
                // One request at a time: Tally serves XML requests one by one, so two heavy requests sent together made the
                // second wait behind the first and hit its timeout ("Tally timed out" while Tally was working normally).
                var (vchOk, vchList) = await conn.FetchExistingVouchersExAsync(dates[0], dates[^1], bankLedger: bankLedger);
                tallyCheckOk = vchOk;
                liveVouchers = vchOk ? vchList : null;
                tallyBal = await conn.FetchLedgerBalancesAsync(bankLedger, dates[0], dates[^1]);
                if (!vchOk)
                {
                    ShowThemedDialog("Tally Duplicate Check Unavailable",
                        "Could not read the existing vouchers from Tally for this period (Tally busy, timed out, or the company is not open).\n\n"
                        + "Rows will NOT be checked against entries already in Tally, so duplicates are possible. Re-run Analyze once Tally responds before posting.",
                        isError: true);
                }
            }

            var partyInfoCopy = _partyBankInfo;
            await Task.Run(() =>
            {
                _classifier.SyncFromServerIfUpdated();
                _contraEngine.AnalyzeBatch(allTxns, bankLedger, cashLedger, liveVouchers, _activeCompanyName);

                // 1. Place overlapping Tally entries into their exact matched Tally ledger & teach ML immediately!
                var tallyOverlapRows = new List<BankTransactionRow>();
                foreach (var row in allTxns)
                {
                    if (!string.IsNullOrWhiteSpace(row.MatchedTallyLedger))
                    {
                        row.SelectedLedger = row.MatchedTallyLedger;
                        if (row.MatchedTallyVoucherType is "Payment" or "Receipt" or "Contra")
                            row.VoucherType = row.MatchedTallyVoucherType;
                        row.IsContra = row.VoucherType == "Contra";
                        row.Confidence = 1.0;
                        row.PredictionSource = "tally_overlap";
                        if (!row.IsContra) tallyOverlapRows.Add(row);
                    }
                }
                if (tallyOverlapRows.Count > 0)
                    _classifier.LearnFromRows(tallyOverlapRows, _activeCompanyName);

                // 2. Predict all remaining rows using the freshly updated ML model
                foreach (var row in allTxns)
                {
                    if (!string.IsNullOrWhiteSpace(row.MatchedTallyLedger)) continue;
                    if (row.IsContra)
                    {
                        if (string.IsNullOrEmpty(row.ContraTargetLedger))
                        {
                            // Ambiguous self-transfer: leave the ledger for the user to pick (posting is blocked while empty)
                            row.SelectedLedger = "";
                            row.Confidence = 0.30;
                            row.PredictionSource = "contra_detector_ambiguous";
                        }
                        else
                        {
                            row.SelectedLedger = row.ContraTargetLedger;
                            row.Confidence = 0.95;
                            row.PredictionSource = "contra_detector";
                        }
                    }
                    else
                    {
                        var (ledger, conf, src) = _classifier.Predict(row.Narration, row.TxnType, _tallyLedgers, _activeCompanyName);
                        // Exact party from the bank details / name stored in Tally beats an ML guess. A name match yields
                        // to a very confident ML prediction (learned from your own corrections).
                        var party = PartyMatcher.Match(row.Narration, partyInfoCopy);
                        if (party is { } pm && (pm.source != "tally_party_name" || conf < 0.90))
                            (ledger, conf, src) = (pm.ledger, pm.confidence, pm.source);
                        row.SelectedLedger = ledger;
                        row.Confidence = conf;
                        row.PredictionSource = src;
                    }
                }
            });

            // Guarantee identical counterparty+direction rows in the same statement are never treated inconsistently
            var canonicalByVendor = new Dictionary<string, (string ledger, double conf, string src)>(StringComparer.OrdinalIgnoreCase);
            foreach (var row in allTxns.Where(r => !r.IsContra))
            {
                var key = $"{LedgerClassifier.ExtractCounterpartyKey(string.IsNullOrWhiteSpace(row.OriginalNarration) ? row.Narration : row.OriginalNarration)}|{row.TxnType}";
                if (key.Length > 4)
                {
                    if (!canonicalByVendor.TryGetValue(key, out var best) || row.Confidence > best.conf)
                        canonicalByVendor[key] = (row.SelectedLedger, row.Confidence, row.PredictionSource);
                }
            }
            foreach (var row in allTxns.Where(r => !r.IsContra))
            {
                var key = $"{LedgerClassifier.ExtractCounterpartyKey(string.IsNullOrWhiteSpace(row.OriginalNarration) ? row.Narration : row.OriginalNarration)}|{row.TxnType}";
                if (canonicalByVendor.TryGetValue(key, out var best))
                {
                    row.SelectedLedger = best.ledger;
                    row.Confidence = best.conf;
                    row.PredictionSource = best.src;
                }
            }
            foreach (var row in allTxns)
            {
                row.IsNewLedger = !IsKnownTallyLedger(row.SelectedLedger);
                row.LastCommittedLedger = row.SelectedLedger ?? "";
                row.PartyKey = LedgerClassifier.ExtractCounterpartyKey(row.Narration);
            }
            // Confidence floor: a guessed ledger is never posted silently — the row starts unticked until someone confirms it
            int needReview = ReviewPolicy.HoldBackGuesses(allTxns);

            // Splits remembered from earlier statements (same party, same direction)
            var (splitExact, splitScaled) = SplitMemory.Apply(allTxns, _db.GetRememberedSplits(_activeCompanyName));
            foreach (var r in allTxns.Where(x => x.PredictionSource == "remembered_split"))
                r.IsNewLedger = r.Splits.Any(sl => !IsKnownTallyLedger(sl.Ledger));
            needReview = allTxns.Count(x => x.NeedsReview);

            foreach (var r in allTxns) r.TidyNarration = NarrationTidier.Tidy(r.Narration, r.PaymentMode, r.RefNo);

            ReviewRows.Clear();
            foreach (var r in allTxns) ReviewRows.Add(r);
            _currentBalances = firstBal;
            _analyzedCompany = _activeCompanyName;
            _analyzedBankLedger = bankLedger;
            _analyzedWithTallyCheck = tallyCheckOk;
            _analyzedBalances.Clear();
            _analyzedBalances.AddRange(parsedFiles.Select(p => p.Balances));
            _analyzedFiles.Clear();
            _analyzedFiles.AddRange(parsedFiles);
            RefreshDropdownLedgers();
            UpdateBalanceBanner(firstBal, tallyBal);
            UpdateSelectedTotalsBar();
            TxtFooter.Text = $"Analyzed {allTxns.Count} rows: {string.Join(" • ", summaries)}"
                + (needReview > 0 ? $"  •  ⚠ {needReview} row(s) need a ledger check (not ticked — choose the ledger to tick them)" : "")
                + (splitExact + splitScaled > 0 ? $"  •  ✂ {splitExact + splitScaled} split(s) applied from last time" + (splitScaled > 0 ? $" ({splitScaled} scaled — check them)" : "") : "");
            _filesChangedSinceAnalyze = false;
            UpdateStepBar();
            _ = AutoMatchBillsAsync(allTxns);
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Statement Analysis Failed", ex.Message, isError: true);
            TxtFooter.Text = $"Analysis failed: {ex.Message}";
        }
        finally
        {
            BtnAnalyze.IsEnabled = true;
        }
    }

    public sealed class DirectionChoiceItem : System.ComponentModel.INotifyPropertyChanged
    {
        private string _choice = ChoiceCr;
        public const string ChoiceDr = "Dr – Receipt (money in)";
        public const string ChoiceCr = "Cr – Payment (money out)";
        public BankTransactionRow Row { get; init; } = null!;
        public string DisplayDate => Row.DisplayDate;
        public string Narration => Row.Narration;
        public string AmountText => Row.Amount.ToString("N2");
        public string BalanceText => Row.Balance.HasValue ? Row.Balance.Value.ToString("N2") : "—";
        public string Choice { get => _choice; set { _choice = value; PropertyChanged?.Invoke(this, new(nameof(Choice))); } }
        public event System.ComponentModel.PropertyChangedEventHandler? PropertyChanged;
    }

    /// <summary>
    /// Lets the user decide Debit / Credit for rows the statement does not label and the running balance cannot prove.
    /// Returns row → "DR"/"CR", or null when the user cancels (analysis then stops; nothing is guessed silently).
    /// </summary>
    private Dictionary<BankTransactionRow, string>? ShowConfirmDirectionDialog(List<BankTransactionRow> rows)
    {
        var items = rows.Select(r => new DirectionChoiceItem { Row = r, Choice = r.TxnType == "CR" ? DirectionChoiceItem.ChoiceDr : DirectionChoiceItem.ChoiceCr }).ToList();
        var dlg = new Window
        {
            Title = $"Confirm Dr / Cr (as per Tally) — {rows.Count} row(s)",
            Width = 900, Height = 460,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };
        var root = new DockPanel { Margin = new Thickness(14) };
        var info = new TextBlock
        {
            Text = "The statement does not say whether these rows are withdrawals or deposits, and the running balance cannot prove it " +
                   "(usually the FIRST row when no opening balance is printed). Check each against the PDF and choose, as per Tally: " +
                   "Dr – Receipt (money came IN; the bank prints it as Credit/Deposit) or Cr – Payment (money went OUT; the bank prints it as " +
                   "Debit/Withdrawal). The pre-selected value is only the parser's guess.",
            TextWrapping = TextWrapping.Wrap, FontSize = 12.5, Margin = new Thickness(0, 0, 0, 10)
        };
        DockPanel.SetDock(info, Dock.Top);
        root.Children.Add(info);

        var btnBar = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        var btnCancel = new Button { Content = "Cancel Analysis", Height = 30, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnOk = new Button { Content = "Confirm & Continue", Height = 30, Padding = new Thickness(16, 0, 16, 0), Background = new SolidColorBrush(Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        bool confirmed = false;
        btnCancel.Click += (_, _) => dlg.Close();
        btnOk.Click += (_, _) => { confirmed = true; dlg.Close(); };
        btnBar.Children.Add(btnCancel);
        btnBar.Children.Add(btnOk);
        DockPanel.SetDock(btnBar, Dock.Bottom);
        root.Children.Add(btnBar);

        var dg = new DataGrid
        {
            AutoGenerateColumns = false, CanUserAddRows = false, ItemsSource = items, RowHeight = 34,
            HeadersVisibility = DataGridHeadersVisibility.Column, RowHeaderWidth = 0,
            Background = (Brush)Application.Current.Resources["CardBg"],
            RowBackground = (Brush)Application.Current.Resources["RowBg"],
            AlternatingRowBackground = (Brush)Application.Current.Resources["RowAltBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"],
            GridLinesVisibility = DataGridGridLinesVisibility.Horizontal
        };
        dg.Columns.Add(new DataGridTextColumn { Header = "Date", Binding = new Binding("DisplayDate"), IsReadOnly = true, Width = 95 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Narration", Binding = new Binding("Narration"), IsReadOnly = true, Width = new DataGridLength(1, DataGridLengthUnitType.Star) });
        dg.Columns.Add(new DataGridTextColumn { Header = "Amount (₹)", Binding = new Binding("AmountText"), IsReadOnly = true, Width = 110 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Balance after (₹)", Binding = new Binding("BalanceText"), IsReadOnly = true, Width = 125 });
        var choiceCol = new DataGridTemplateColumn { Header = "Dr / Cr (Tally)", Width = 200 };
        var cf = new FrameworkElementFactory(typeof(ComboBox));
        cf.SetValue(ComboBox.HeightProperty, 26.0);
        cf.SetValue(ComboBox.ItemsSourceProperty, new[] { DirectionChoiceItem.ChoiceDr, DirectionChoiceItem.ChoiceCr });
        cf.SetBinding(ComboBox.SelectedItemProperty, new Binding("Choice") { Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
        choiceCol.CellTemplate = new DataTemplate { VisualTree = cf };
        dg.Columns.Add(choiceCol);
        root.Children.Add(dg);

        dlg.Content = root;
        dlg.ShowDialog();
        if (!confirmed) return null;
        return items.ToDictionary(i => i.Row, i => i.Choice == DirectionChoiceItem.ChoiceDr ? "CR" : "DR");
    }

    /// <summary>Why a parse cannot be trusted as is ("" = it can).</summary>
    private static string UnreliableReadReason(ParsedStatementResult p)
    {
        var why = new List<string>();
        if (p.Transactions.Count == 0) why.Add("• No transactions could be read.");
        if (p.Balances.StatementBalanced == false) why.Add($"• The balances do not reconcile (difference ₹{p.Balances.StatementDiff:N2}).");
        foreach (var ci in p.Balances.CompletenessIssues) why.Add("• " + ci + ".");
        int lnu = p.Transactions.Count(t => (t.ParseWarning ?? "").Contains("Layout not understood", StringComparison.Ordinal));
        if (lnu > 0) why.Add($"• {lnu} row(s) look like several transactions merged together.");
        if (p.ExtractionMethod.Contains("fallback", StringComparison.OrdinalIgnoreCase)) why.Add("• The table layout was not recognised (last-resort reading was used).");
        return string.Join("\n", why);
    }

    private void UpdateBalanceBanner(StatementBalanceInfo? b, (bool found, decimal op, decimal cl) tallyBal)
    {
        if (b == null)
        {
            BalanceBanner.Visibility = Visibility.Collapsed;
            return;
        }
        var fromLbl = string.IsNullOrEmpty(b.FromDate) ? "Statement Start" : BankStatementParser.FormatDisplayDate(b.FromDate);
        var parts = new List<string>
        {
            $"Statement Opening ({fromLbl}): ₹{b.StatementOpening:N2}"
        };
        bool mismatch = false;

        if (tallyBal.found && b.StatementOpening.HasValue)
        {
            decimal tOp = tallyBal.op;
            decimal overlapDr = ReviewRows.Where(r => r.OverlapStatus.StartsWith("OVERLAP_TALLY", StringComparison.Ordinal)).Sum(r => r.Debit);
            decimal overlapCr = ReviewRows.Where(r => r.OverlapStatus.StartsWith("OVERLAP_TALLY", StringComparison.Ordinal)).Sum(r => r.Credit);
            decimal overlapNet = overlapCr - overlapDr;
            decimal expectedAfterOverlaps = b.StatementOpening.Value + overlapNet;

            decimal opDiff = tOp - b.StatementOpening.Value;
            decimal adjDiff = tOp - expectedAfterOverlaps;

            if (opDiff == 0)
            {
                parts.Add($"Tally Opening ({fromLbl}) Matched ✓ (₹{tOp:N2})");
            }
            else if ((overlapDr > 0 || overlapCr > 0) && adjDiff == 0)
            {
                var sign = overlapNet >= 0 ? "+" : "−";
                parts.Add($"Tally Balance Matched ✓ (₹{tOp:N2} = Stmt ₹{b.StatementOpening.Value:N2} {sign} ₹{Math.Abs(overlapNet):N2} overlapping entries already in Tally)");
            }
            else
            {
                var extra = (overlapDr > 0 || overlapCr > 0)
                    ? $" — incl. ₹{Math.Abs(overlapNet):N2} overlapping entries in Tally; unexplained diff ₹{adjDiff:N2}"
                    : "";
                parts.Add($"Tally Opening ({fromLbl}) Mismatch: Tally ₹{tOp:N2} (Diff ₹{opDiff:N2}{extra})");
                mismatch = true;
            }
        }
        if (b.StatementClosing.HasValue)
            parts.Add($"Statement Closing: ₹{b.StatementClosing:N2}");

        // Completeness proof: Opening + Dr (receipts) − Cr (payments) must equal Closing for EVERY file
        var fileBals = _analyzedBalances.Count > 0 ? _analyzedBalances : new List<StatementBalanceInfo> { b };
        var unbalanced = fileBals.Where(fb => fb.StatementBalanced == false).ToList();
        if (unbalanced.Count > 0)
        {
            var u = unbalanced[0];
            parts.Add($"⚠ Statement does NOT reconcile: Opening ₹{u.StatementOpening:N2} + Dr ₹{u.TotalCredit:N2} − Cr ₹{u.TotalDebit:N2} = ₹{u.CalculatedClosing:N2} vs Closing ₹{u.StatementClosing:N2} (Diff ₹{u.StatementDiff:N2}) — some rows may be missing or mis-read");
            mismatch = true;
        }
        foreach (var ci in fileBals.SelectMany(fb => fb.CompletenessIssues).Distinct())
        {
            parts.Add("⛔ " + ci);
            mismatch = true;
        }
        if (fileBals.Any(fb => fb.CompletenessIssues.Count > 0)) { /* not "Reconciled" while a completeness check failed */ }
        else if (fileBals.All(fb => fb.StatementBalanced == true))
        {
            parts.Add($"Reconciled ✓ (Dr ₹{fileBals.Sum(fb => fb.TotalCredit):N2} • Cr ₹{fileBals.Sum(fb => fb.TotalDebit):N2})");
        }
        if (fileBals.Any(fb => fb.HasRunningBalance && fb.StatementBalanced == null))
        {
            parts.Add("⚠ Could not prove the statement: opening balance not printed and the first row's Dr/Cr was not stated — check the first row");
            mismatch = true;
        }
        if (fileBals.Any(fb => !fb.HasRunningBalance))
        {
            parts.Add("⚠ No running-balance column — completeness cannot be proven row by row; tally the totals with the printed statement");
            mismatch = true;
        }
        int breakCnt = ReviewRows.Count(r => r.HasBalanceBreak);
        if (breakCnt > 0)
        {
            parts.Add($"⚠ {breakCnt} Balance Break(s) — use 'Balance Breaks' filter to inspect");
            mismatch = true;
        }
        int warnCnt = ReviewRows.Count(r => !string.IsNullOrEmpty(r.ParseWarning));
        if (warnCnt > 0)
        {
            parts.Add($"⚠ {warnCnt} row(s) with parser notes — use 'Parser Warnings' filter");
            mismatch = true;
        }
        if (_tallyConnected && !_analyzedWithTallyCheck)
        {
            parts.Add("⚠ Not checked against existing Tally entries (Tally could not be read)");
            mismatch = true;
        }

        BalanceBanner.Visibility = Visibility.Visible;
        BalanceBanner.Background = new SolidColorBrush(mismatch ? Color.FromRgb(253, 237, 236) : Color.FromRgb(232, 248, 245));
        BalanceBanner.BorderBrush = new SolidColorBrush(mismatch ? Color.FromRgb(192, 57, 43) : Color.FromRgb(14, 138, 109));
        TxtBalanceBanner.Foreground = new SolidColorBrush(mismatch ? Color.FromRgb(146, 43, 33) : Color.FromRgb(14, 98, 81));
        TxtBalanceBanner.Text = string.Join("   •   ", parts);
    }

    private static void ConfirmReviewed(BankTransactionRow r) => ReviewPolicy.ConfirmReviewed(r);

    private void CommitLedgerEdit(BankTransactionRow row, string? rawValue)
    {
        var newVal = (rawValue ?? "").Trim();
        if (string.IsNullOrEmpty(newVal)) return;
        bool changed = !newVal.Equals(row.LastCommittedLedger, StringComparison.Ordinal);
        row.SelectedLedger = newVal;
        row.LastCommittedLedger = newVal;
        row.UserEdited = true;
        row.Confidence = 1.0;
        row.PredictionSource = "user_manual";
        row.IsNewLedger = !IsKnownTallyLedger(newVal);
        // Typing / choosing a different ledger replaces a split with that single ledger
        if (changed && row.IsSplit) row.Splits = [];
        ConfirmReviewed(row);
        if (!DropdownLedgers.Contains(newVal, StringComparer.OrdinalIgnoreCase))
            DropdownLedgers.Add(newVal);
        if (changed)
        {
            // Bills chosen for the OLD party must never be posted against the new ledger
            row.BillAllocations = [];
            row.BillRef = "(None)";
            CascadeMlBelow(row);
            _ = LoadBillsForRowAsync(row);
            _ = AutoMatchBillsAsync(ReviewRows.Where(r => r.SelectedLedger.Equals(newVal, StringComparison.OrdinalIgnoreCase)).ToList());
            RefreshStats();
        }
    }

    private static (TextBox? box, Popup? popup, ListBox? list) FindLedgerPickerParts(FrameworkElement el)
    {
        DependencyObject? cur = el;
        while (cur != null)
        {
            if (cur is Grid g && g.Name == "LedgerPickerRoot")
            {
                return (
                    g.FindName("LedgerBox") as TextBox,
                    g.FindName("LedgerPopup") as Popup,
                    g.FindName("LedgerSuggestList") as ListBox
                );
            }
            cur = VisualTreeHelper.GetParent(cur) ?? (cur as FrameworkElement)?.Parent;
        }
        return (null, null, null);
    }

    private BankTransactionRow? NextVisibleRow(BankTransactionRow currentRow)
    {
        var visible = CollectionViewSource.GetDefaultView(ReviewRows).Cast<BankTransactionRow>().ToList();
        int idx = visible.IndexOf(currentRow);
        return idx < 0 || idx + 1 >= visible.Count ? null : visible[idx + 1];
    }

    private void FocusRowLedgerBox(BankTransactionRow nextRow)
    {
        GridReview.SelectedItem = nextRow;
        GridReview.ScrollIntoView(nextRow);
        Dispatcher.BeginInvoke(System.Windows.Threading.DispatcherPriority.Input, () =>
        {
            if (GridReview.ItemContainerGenerator.ContainerFromItem(nextRow) is DataGridRow dgRow)
            {
                var nextBox = FindVisualChildByName<TextBox>(dgRow, "LedgerBox");
                if (nextBox != null)
                {
                    nextBox.Focus();
                    nextBox.SelectAll();
                }
            }
        });
    }

    private static T? FindVisualChildByName<T>(DependencyObject parent, string name) where T : FrameworkElement
    {
        int count = VisualTreeHelper.GetChildrenCount(parent);
        for (int i = 0; i < count; i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            if (child is T typed && typed.Name == name) return typed;
            var res = FindVisualChildByName<T>(child, name);
            if (res != null) return res;
        }
        return null;
    }

    private void LedgerDropBtn_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not FrameworkElement btn) return;
        var (box, popup, list) = FindLedgerPickerParts(btn);
        if (popup == null || list == null) return;
        if (popup.IsOpen)
        {
            popup.IsOpen = false;
            return;
        }
        list.ItemsSource = DropdownLedgers.ToList();
        list.SelectedIndex = -1;
        popup.IsOpen = true;
        box?.Focus();
    }

    private void LedgerBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (_suppressLedgerPopup || sender is not TextBox box || !box.IsKeyboardFocusWithin) return;
        var (_, popup, list) = FindLedgerPickerParts(box);
        if (popup == null || list == null) return;

        var typed = (box.Text ?? "").Trim();
        if (string.IsNullOrEmpty(typed))
        {
            list.ItemsSource = DropdownLedgers.ToList();
            list.SelectedIndex = -1;
            popup.IsOpen = true;
            return;
        }

        var matches = DropdownLedgers
            .Where(l => l.StartsWith(typed, StringComparison.OrdinalIgnoreCase))
            .Concat(DropdownLedgers.Where(l => !l.StartsWith(typed, StringComparison.OrdinalIgnoreCase) && l.Contains(typed, StringComparison.OrdinalIgnoreCase)))
            .ToList();

        if (matches.Count > 0)
        {
            list.ItemsSource = matches;
            list.SelectedIndex = 0; // Highlight top match ONLY inside popup — NEVER changes box.Text!
            popup.IsOpen = true;
        }
        else
        {
            popup.IsOpen = false;
        }
    }

    private void LedgerBox_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (sender is not TextBox box || box.DataContext is not BankTransactionRow row) return;
        var (_, popup, list) = FindLedgerPickerParts(box);

        // Down Arrow: move highlight down in Popup ListBox ONLY (NEVER changes box.Text!)
        if (e.Key == Key.Down)
        {
            if (popup != null && list != null)
            {
                if (!popup.IsOpen)
                {
                    list.ItemsSource = DropdownLedgers.ToList();
                    list.SelectedIndex = 0;
                    popup.IsOpen = true;
                }
                else if (list.Items.Count > 0)
                {
                    list.SelectedIndex = Math.Min(list.Items.Count - 1, list.SelectedIndex + 1);
                    list.ScrollIntoView(list.SelectedItem);
                }
            }
            e.Handled = true;
            return;
        }

        // Up Arrow: move highlight up in Popup ListBox ONLY (NEVER changes box.Text!)
        if (e.Key == Key.Up)
        {
            if (popup != null && list != null && popup.IsOpen && list.Items.Count > 0)
            {
                list.SelectedIndex = Math.Max(0, list.SelectedIndex - 1);
                list.ScrollIntoView(list.SelectedItem);
            }
            e.Handled = true;
            return;
        }

        // Escape: close popup without changing text
        if (e.Key == Key.Escape)
        {
            if (popup != null) popup.IsOpen = false;
            e.Handled = true;
            return;
        }

        // Enter: commit EXACT typed text (no autofill!), close popup, and move straight to the next row!
        if (e.Key == Key.Enter)
        {
            if (popup != null) popup.IsOpen = false;
            var nextRow = NextVisibleRow(row);   // before saving: with grouping on, the row may move to another group
            CommitLedgerEdit(row, box.Text);
            if (row.IsNewLedger)
                TxtFooter.Text = $"New ledger \"{row.SelectedLedger}\" set (will be created in Tally when posting).";
            if (nextRow != null) FocusRowLedgerBox(nextRow);
            e.Handled = true;
            return;
        }

        // Tab: autocomplete ONLY to the highlighted item in the open popup (or top match) & close popup cleanly
        if (e.Key == Key.Tab)
        {
            string? target = null;
            if (popup != null && popup.IsOpen && list != null && list.Items.Count > 0)
            {
                target = (list.SelectedItem as string) ?? (list.Items[0] as string);
            }
            else
            {
                var typed = (box.Text ?? "").Trim();
                if (!string.IsNullOrEmpty(typed))
                    target = DropdownLedgers.FirstOrDefault(l => l.StartsWith(typed, StringComparison.OrdinalIgnoreCase))
                        ?? DropdownLedgers.FirstOrDefault(l => l.Contains(typed, StringComparison.OrdinalIgnoreCase));
            }

            if (popup != null) popup.IsOpen = false;
            if (!string.IsNullOrWhiteSpace(target))
            {
                _suppressLedgerPopup = true;
                box.Text = target;
                box.CaretIndex = target.Length;
                _suppressLedgerPopup = false;
                CommitLedgerEdit(row, target);
                e.Handled = true;
                return;
            }
            CommitLedgerEdit(row, box.Text);
        }
    }

    private void LedgerSuggestList_Click(object sender, MouseButtonEventArgs e)
    {
        if (sender is not ListBox list || list.SelectedItem is not string chosen) return;
        if (list.Parent is Border b && b.Parent is Popup popup && popup.PlacementTarget is Grid g)
        {
            popup.IsOpen = false;
            if (g.FindName("LedgerBox") is TextBox box && box.DataContext is BankTransactionRow row)
            {
                _suppressLedgerPopup = true;
                box.Text = chosen;
                box.CaretIndex = chosen.Length;
                _suppressLedgerPopup = false;
                CommitLedgerEdit(row, chosen);
            }
        }
    }

    private void LedgerBox_LostFocus(object sender, RoutedEventArgs e)
    {
        if (sender is not TextBox box || box.DataContext is not BankTransactionRow row) return;
        var (_, popup, _) = FindLedgerPickerParts(box);
        if (popup != null && popup.IsKeyboardFocusWithin) return;
        CommitLedgerEdit(row, box.Text);
    }

    private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        bool typing = Keyboard.FocusedElement is TextBox or ComboBox or PasswordBox;
        bool ctrl = (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control;

        // Ctrl+F: jump to the search box
        if (e.Key == Key.F && ctrl)
        {
            TxtSearch.Focus();
            TxtSearch.SelectAll();
            e.Handled = true;
            return;
        }

        // F8: next row that still needs a ledger check (held back below the confidence floor / no ledger)
        if (e.Key == Key.F8 && ReviewRows.Count > 0)
        {
            var visible = CollectionViewSource.GetDefaultView(ReviewRows).Cast<BankTransactionRow>().ToList();
            int from = GridReview.SelectedItem is BankTransactionRow cur ? visible.IndexOf(cur) : -1;
            var next = visible.Skip(from + 1).Concat(visible.Take(from + 1))
                .FirstOrDefault(r => r.PostStatus != "DONE" && (r.NeedsReview || string.IsNullOrWhiteSpace(r.SelectedLedger)));
            if (next == null)
            {
                TxtFooter.Text = "✓ No row is waiting for a ledger check.";
            }
            else
            {
                FocusRowLedgerBox(next);
                TxtFooter.Text = $"Check ledger: {next.DisplayDate} ₹{next.Amount:N2} — {next.Narration}";
            }
            e.Handled = true;
            return;
        }

        // Space (outside a text box): tick / untick the highlighted row(s)
        if (e.Key == Key.Space && !typing && Keyboard.FocusedElement is not CheckBox && GridReview.SelectedItems.Count > 0)
        {
            var rows = GridReview.SelectedItems.OfType<BankTransactionRow>().Where(r => r.PostStatus != "DONE").ToList();
            if (rows.Count > 0)
            {
                bool tick = rows.Any(r => !r.Selected);
                foreach (var sr in rows) sr.Selected = tick;
                UpdateSelectedTotalsBar();
                e.Handled = true;
                return;
            }
        }

        if (e.Key == Key.D && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
        {
            var visible = CollectionViewSource.GetDefaultView(ReviewRows).Cast<BankTransactionRow>().ToList();
            if (GridReview.SelectedItem is BankTransactionRow current)
            {
                int idx = visible.IndexOf(current);
                if (idx > 0)
                {
                    var above = visible[idx - 1].SelectedLedger;
                    if (!string.IsNullOrWhiteSpace(above))
                    {
                        CommitLedgerEdit(current, above);
                        TxtFooter.Text = $"Copied '{above}' from row above (Ctrl+D).";
                        e.Handled = true;
                    }
                }
            }
        }
    }

    private void CascadeMlBelow(BankTransactionRow editedRow)
    {
        if (editedRow.VoucherType == "Contra" || string.IsNullOrWhiteSpace(editedRow.SelectedLedger)) return;
        // Instant <1ms in-memory learning + background server save (eliminates SMB UI freeze!)
        _classifier.LearnInstantAndSaveInBackground(editedRow, _activeCompanyName);
        int startIdx = ReviewRows.IndexOf(editedRow);
        if (startIdx < 0) return;
        int updated = 0;
        var avail = DropdownLedgers.ToList();
        for (int i = startIdx + 1; i < ReviewRows.Count; i++)
        {
            var r = ReviewRows[i];
            if (r.UserEdited || r.IsContra || r.VoucherType == "Contra") continue;
            // Never touch rows already posted, or rows whose ledger was read from the matching entry in Tally
            if (r.PostStatus == "DONE" || r.PredictionSource == "tally_overlap" || r.IsSplit
                || r.PredictionSource.StartsWith("tally_bank", StringComparison.Ordinal)) continue;
            var (pred, conf, src) = _classifier.Predict(string.IsNullOrWhiteSpace(r.OriginalNarration) ? r.Narration : r.OriginalNarration, r.TxnType, avail, _activeCompanyName);
            if (!pred.Equals(r.SelectedLedger, StringComparison.OrdinalIgnoreCase))
            {
                r.SelectedLedger = pred;
                r.LastCommittedLedger = pred;
                r.IsNewLedger = !IsKnownTallyLedger(pred);
                r.Confidence = conf;
                r.PredictionSource = src;
                updated++;
            }
            // a held-back row whose prediction is now confident (learned from this correction) is ticked again
            ConfirmReviewed(r);
        }
        if (updated > 0) TxtFooter.Text = $"ML learned '{editedRow.SelectedLedger}' and updated {updated} matching row(s) below.";
    }

    // Proper Interactive Dialog to select Tally Parent Group (Head) for every missing ledger
    private List<MissingLedgerItem>? ShowMissingLedgersDialog(List<MissingLedgerItem> missing)
    {
        var dlg = new Window
        {
            Title = "Create Missing Ledgers in Tally — Choose Account Head",
            Width = 680, Height = 420,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var root = new DockPanel { Margin = new Thickness(14) };
        var hdr = new TextBlock
        {
            Text = "The following ledgers are not present in Tally. Select the Tally Parent Group (Head) for each ledger to create:",
            TextWrapping = TextWrapping.Wrap,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 0, 0, 10)
        };
        DockPanel.SetDock(hdr, Dock.Top);
        root.Children.Add(hdr);

        var btnBar = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        var btnCancel = new Button { Content = "Cancel", Padding = new Thickness(14, 6, 14, 6), Margin = new Thickness(0, 0, 8, 0) };
        var btnSkip = new Button { Content = "Skip Creation", Padding = new Thickness(14, 6, 14, 6), Margin = new Thickness(0, 0, 8, 0) };
        var btnCreate = new Button { Content = "Create Ledgers & Continue", Padding = new Thickness(16, 6, 16, 6), Background = new SolidColorBrush(Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold };

        bool skipped = false;
        btnCancel.Click += (_, _) => { dlg.DialogResult = false; dlg.Close(); };
        btnSkip.Click += (_, _) => { skipped = true; dlg.DialogResult = true; dlg.Close(); };
        btnCreate.Click += (_, _) => { dlg.DialogResult = true; dlg.Close(); };

        btnBar.Children.Add(btnCancel);
        btnBar.Children.Add(btnSkip);
        btnBar.Children.Add(btnCreate);
        DockPanel.SetDock(btnBar, Dock.Bottom);
        root.Children.Add(btnBar);

        var dg = new DataGrid
        {
            AutoGenerateColumns = false,
            CanUserAddRows = false,
            ItemsSource = missing,
            RowHeight = 36,
            Background = (Brush)Application.Current.Resources["CardBg"],
            RowBackground = (Brush)Application.Current.Resources["RowBg"],
            AlternatingRowBackground = (Brush)Application.Current.Resources["RowAltBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"],
            HeadersVisibility = DataGridHeadersVisibility.Column,
            RowHeaderWidth = 0,
            HorizontalGridLinesBrush = (Brush)Application.Current.Resources["BorderBrush"],
            GridLinesVisibility = DataGridGridLinesVisibility.Horizontal
        };
        dg.Columns.Add(new DataGridCheckBoxColumn { Header = "Create", Binding = new Binding("Create") { UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged }, Width = 54 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Ledger Name", Binding = new Binding("Name"), IsReadOnly = true, Width = new DataGridLength(1.35, DataGridLengthUnitType.Star) });
        dg.Columns.Add(new DataGridTextColumn { Header = "Txns", Binding = new Binding("UsageCount"), IsReadOnly = true, Width = 52 });

        // Always-visible Tally Head ComboBox matching the main Tally Ledger dropdown!
        var headCol = new DataGridTemplateColumn { Header = "Under Tally Head (Parent Group)", Width = new DataGridLength(1.5, DataGridLengthUnitType.Star) };
        var comboFactory = new FrameworkElementFactory(typeof(ComboBox));
        comboFactory.SetValue(ComboBox.IsEditableProperty, true);
        comboFactory.SetValue(ComboBox.IsTextSearchEnabledProperty, true);
        comboFactory.SetValue(ComboBox.HeightProperty, 26.0);
        comboFactory.SetValue(ComboBox.ItemsSourceProperty, _tallyGroups);
        comboFactory.SetBinding(ComboBox.TextProperty, new Binding("ParentGroup") { Mode = BindingMode.TwoWay, UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged });
        headCol.CellTemplate = new DataTemplate { VisualTree = comboFactory };
        dg.Columns.Add(headCol);
        root.Children.Add(dg);
        dlg.Content = root;

        if (dlg.ShowDialog() != true) return null; // Cancelled
        return skipped ? [] : missing.Where(m => m.Create).ToList();
    }

    private async void BtnPushTally_Click(object sender, RoutedEventArgs e) => await CommitAsync(pushDirect: true);
    private async void BtnExportXml_Click(object sender, RoutedEventArgs e) => await CommitAsync(pushDirect: false);

    private async Task CommitAsync(bool pushDirect)
    {
        if (_isCommitting) return;
        _isCommitting = true;
        try
        {
            await CommitCoreAsync(pushDirect);
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Posting Error", ex.Message, isError: true);
            TxtFooter.Text = $"Error: {ex.Message}";
        }
        finally
        {
            _isCommitting = false;
        }
    }

    private async Task CommitCoreAsync(bool pushDirect)
    {
        Keyboard.ClearFocus();
        var approved = ReviewRows.Where(r => r.Selected).ToList();
        if (approved.Count == 0)
        {
            ShowThemedDialog("Nothing Selected", "No rows are selected for posting.", isError: true);
            return;
        }

        if (pushDirect && !_tallyConnected)
        {
            ShowThemedDialog("Tally Not Connected", "Connect to Tally first (Detect Tally / Connect), or use 'Export XML' to create an import file.", isError: true);
            return;
        }

        // Guardrail 0a: rows were analysed (hashes, GUIDs, bank ledger, duplicate checks) for a specific company + bank ledger
        if (!string.Equals(_analyzedCompany.Trim(), _activeCompanyName.Trim(), StringComparison.OrdinalIgnoreCase))
        {
            ShowThemedDialog("Company Changed Since Analyze",
                $"These rows were analysed for company '{_analyzedCompany}', but Tally is now connected to '{_activeCompanyName}'.\n\n"
                + "Click 'Analyze' again so duplicates, contra entries and ledgers are checked against the correct company.", isError: true);
            return;
        }
        var currentBank = (CmbBankLedger.Text ?? "").Trim();
        if (!string.IsNullOrEmpty(_analyzedBankLedger) && !currentBank.Equals(_analyzedBankLedger, StringComparison.OrdinalIgnoreCase))
        {
            ShowThemedDialog("Bank Ledger Changed Since Analyze",
                $"These rows were analysed for bank ledger '{_analyzedBankLedger}', but '{currentBank}' is now selected.\n\n"
                + "Click 'Analyze' again (or switch the Bank Ledger back) before posting.", isError: true);
            return;
        }

        // Guardrail 0b: every row needs a ledger
        var noLedger = approved.Where(r => r.PostingLedgers.Any(string.IsNullOrWhiteSpace)).ToList();
        if (noLedger.Count > 0)
        {
            ShowThemedDialog("Ledger Missing",
                $"{noLedger.Count} selected row(s) have no Tally Ledger (e.g. a self-transfer where the other bank could not be determined):\n\n"
                + string.Join("\n", noLedger.Take(10).Select(r => $"• {r.DisplayDate} | ₹{r.Amount:N2} | {r.Narration}")), isError: true);
            return;
        }

        // Guardrail 0c: voucher type must agree with the money direction
        var dirMismatch = approved.Where(r => (r.VoucherType == "Payment" && r.TxnType == "CR") || (r.VoucherType == "Receipt" && r.TxnType == "DR")).ToList();
        if (dirMismatch.Count > 0)
        {
            var dmMsg = $"{dirMismatch.Count} row(s) have a voucher type that does not match the bank direction (Payment on a deposit / Receipt on a withdrawal):\n\n"
                + string.Join("\n", dirMismatch.Take(10).Select(r => $"• {r.DisplayDate} | {(r.TxnType == "DR" ? "Withdrawal" : "Deposit")} ₹{r.Amount:N2} | {r.VoucherType} | {r.Narration}"))
                + "\n\nThe bank side is always posted by the statement direction. Continue anyway?";
            if (!ShowThemedDialog("Voucher Type vs Dr/Cr", dmMsg, isError: true, yesNo: true))
                return;
        }

        // Guardrail 0d (HARD): a statement that is proven WRONG — balances do not reconcile, printed totals differ, pages are
        // missing or repeated — cannot be posted at all. Rows would be missing or mis-read; there is no "post anyway".
        var blocked = _analyzedFiles.Count > 0
            ? _analyzedFiles.Where(f => f.Balances.BlockReason.Length > 0).Select(f => $"• {f.SourceFile}: {f.Balances.BlockReason}").ToList()
            : _analyzedBalances.Where(b => b.BlockReason.Length > 0).Select(b => $"• {b.BlockReason}").ToList();
        if (blocked.Count > 0)
        {
            ShowThemedDialog("Posting Blocked — Statement Not Proven Complete",
                string.Join("\n", blocked)
                + "\n\nNothing was posted. Posting such a statement would leave entries missing or wrong in Tally.\n\n"
                + "What to do:\n• Use '🧩 Teach Columns' to mark this statement's columns once, then Analyze again, or\n"
                + "• Download the Excel/CSV version of the statement from netbanking, or\n"
                + "• Save the '📋 Debug' report and send it for a parser fix.",
                isError: true);
            TxtFooter.Text = "Posting blocked — the statement is not proven complete.";
            return;
        }

        // Guardrail 0d (soft): what cannot be proven either way still needs a conscious decision
        var recon = new List<string>();
        foreach (var fb in _analyzedBalances)
        {
            if (!fb.HasRunningBalance)
                recon.Add("• A statement has no running-balance column, so completeness could not be proven row by row.");
            else if (fb.StatementBalanced == null)
                recon.Add("• A statement could not be proven: opening balance not printed and the first row's Dr/Cr was guessed — check the first row.");
        }
        int brk = approved.Count(r => r.HasBalanceBreak);
        int pw = approved.Count(r => !string.IsNullOrEmpty(r.ParseWarning));
        if (brk > 0) recon.Add($"• {brk} selected row(s) have a running-balance break.");
        if (pw > 0) recon.Add($"• {pw} selected row(s) have parser notes (see 'Parser Warnings' filter).");
        if (pushDirect && !_analyzedWithTallyCheck) recon.Add("• Rows were NOT checked against entries already in Tally (Tally could not be read during Analyze).");
        if (recon.Count > 0)
        {
            if (!ShowThemedDialog("Statement Check Before Posting", string.Join("\n", recon.Distinct()) + "\n\nReview these rows first. Continue posting anyway?", isError: true, yesNo: true))
                return;
        }

        // Guardrail 1: Block self-posting (Tally Ledger == Bank Ledger)
        var selfPosts = approved.Where(r => r.PostingLedgers.Any(l => l.Trim().Equals(r.BankLedger.Trim(), StringComparison.OrdinalIgnoreCase))).ToList();
        if (selfPosts.Count > 0)
        {
            var selfMsg = $"Cannot post {selfPosts.Count} entry/entries because the Tally Ledger is the same as the Bank Ledger ('{selfPosts[0].BankLedger}'):\n\n"
                + string.Join("\n", selfPosts.Take(10).Select(r => $"• {r.DisplayDate} | ₹{r.Amount:N2} | {r.Narration}"));
            ShowThemedDialog("Self-Posting Blocked", selfMsg, isError: true);
            return;
        }

        // Guardrail 2: Warn on Suspense Account or Low-Confidence unedited rows
        var suspenseRows = approved.Where(r => r.PostingLedgers.Any(l => l.Trim().Equals("Suspense Account", StringComparison.OrdinalIgnoreCase))).ToList();
        var lowConfRows = approved.Where(r => r.VoucherType != "Contra" && r.Confidence < ConfidenceFloor && r.PredictionSource != "user_manual").ToList();
        if (suspenseRows.Count > 0 || lowConfRows.Count > 0)
        {
            var warnParts = new List<string>();
            if (suspenseRows.Count > 0) warnParts.Add($"• {suspenseRows.Count} row(s) are still set to 'Suspense Account'.");
            if (lowConfRows.Count > 0) warnParts.Add($"• {lowConfRows.Count} row(s) were ticked by hand but their ledger is only a guess (below {ConfidenceFloor:P0}) and was never confirmed.");
            if (!ShowThemedDialog("Review Before Posting", string.Join("\n", warnParts) + "\n\nDo you want to continue posting to Tally?", isError: false, yesNo: true))
                return;
        }

        var vendorConflicts = approved
            .Where(r => r.VoucherType != "Contra" && !r.IsSplit)
            .GroupBy(r => $"{LedgerClassifier.ExtractCounterpartyKey(string.IsNullOrWhiteSpace(r.OriginalNarration) ? r.Narration : r.OriginalNarration)}|{r.TxnType}", StringComparer.OrdinalIgnoreCase)
            .Where(g => g.Key.Length > 4 && g.Select(x => x.SelectedLedger.Trim()).Distinct(StringComparer.OrdinalIgnoreCase).Count() > 1)
            .Select(g => $"• {g.Key.Split('|')[0]} ({g.Key.Split('|')[1]}): " + string.Join(" vs ", g.Select(x => $"{x.SelectedLedger} ({x.DisplayDate})").Distinct()))
            .ToList();

        if (vendorConflicts.Count > 0)
        {
            var confirmMsg = "Similar transactions from the same party have different ledgers selected:\n\n"
                + string.Join("\n", vendorConflicts.Take(10))
                + "\n\nAre these different ledger selections intentional? Click Yes to proceed or No to review them.";
            if (!ShowThemedDialog("Confirm Different Ledgers for Same Party", confirmMsg, isError: false, yesNo: true))
                return;
        }

        var conn = new TallyConnector(TxtTallyHost.Text.Trim(), _activeCompanyName)
        {
            PartyLedgers = _partyLedgers,
            SetBankDate = MenuBankDate.IsChecked,
            UseTidyNarration = ShowTidyNarration
        };

        // Guardrail 3 — dates Tally would reject or that cannot be right: before the company's "Books beginning from",
        // or in the future. Such entries are NEVER posted (Tally rejects the first; the second is a mis-read date).
        var badDates = new List<(BankTransactionRow row, string why)>();
        var todayIso = DateTime.Today.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
        foreach (var fr in approved.Where(x => string.CompareOrdinal(x.TxnDate, todayIso) > 0)) badDates.Add((fr, "future date"));
        if (_tallyConnected)
        {
            var booksStartYmd = await conn.FetchCompanyBooksStartYmdAsync();
            if (DateTime.TryParseExact(booksStartYmd, "yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out var booksStartDt))
            {
                var booksIso = booksStartDt.ToString("yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture);
                foreach (var br in approved.Where(x => string.CompareOrdinal(x.TxnDate, booksIso) < 0))
                    badDates.Add((br, $"before Tally's Books Beginning ({booksStartDt:dd-MMM-yyyy})"));
            }
        }
        if (badDates.Count > 0)
        {
            var dateMsg = $"{badDates.Count} selected entr{(badDates.Count == 1 ? "y has a date" : "ies have dates")} Tally cannot accept:\n\n"
                + string.Join("\n", badDates.Take(10).Select(bd => $"• {bd.row.DisplayDate} | ₹{bd.row.Amount:N2} | {bd.row.SelectedLedger} — {bd.why}"))
                + (badDates.Count > 10 ? $"\n… and {badDates.Count - 10} more" : "")
                + "\n\nYes = untick these and post the rest.   No = cancel.";
            if (!ShowThemedDialog("Dates Tally Cannot Accept", dateMsg, isError: true, yesNo: true)) return;
            var skipDates = badDates.Select(bd => bd.row).ToHashSet();
            foreach (var sr in skipDates) sr.Selected = false;
            approved = approved.Where(x => !skipDates.Contains(x)).ToList();
            UpdateSelectedTotalsBar();
            if (approved.Count == 0) { TxtFooter.Text = "Nothing posted — no entry with a valid date was selected."; return; }
        }

        // 0. Live Opening Balance check against Tally bank balance just before the first entry is passed
        if (pushDirect && _tallyConnected && _currentBalances?.StatementOpening != null)
        {
            var bankLedgerName = approved[0].BankLedger;
            var allDates = ReviewRows.Select(r => r.TxnDate).OrderBy(d => d).ToList();
            if (allDates.Count > 0)
            {
                var liveBal = await conn.FetchLedgerBalancesAsync(bankLedgerName, allDates[0], allDates[^1]);
                if (liveBal.found)
                {
                    decimal overlapDr = ReviewRows.Where(r => r.OverlapStatus.StartsWith("OVERLAP_TALLY", StringComparison.Ordinal)).Sum(r => r.Debit);
                    decimal overlapCr = ReviewRows.Where(r => r.OverlapStatus.StartsWith("OVERLAP_TALLY", StringComparison.Ordinal)).Sum(r => r.Credit);
                    decimal overlapNet = overlapCr - overlapDr;
                    decimal expectedAfterOverlaps = _currentBalances.StatementOpening.Value + overlapNet;

                    decimal opDiff = liveBal.opening - _currentBalances.StatementOpening.Value;
                    decimal adjDiff = liveBal.opening - expectedAfterOverlaps;
                    if (opDiff != 0 && adjDiff != 0)
                    {
                        var fromLbl = BankStatementParser.FormatDisplayDate(allDates[0]);
                        var warn = $"Opening balance does NOT match Tally's '{bankLedgerName}' balance before {fromLbl}:\n\n"
                            + $"• Statement Opening Balance: ₹{_currentBalances.StatementOpening.Value:N2}\n"
                            + (overlapDr > 0 || overlapCr > 0 ? $"• Overlapping Entries Already in Tally: ₹{overlapNet:N2} (Expected Tally Bal: ₹{expectedAfterOverlaps:N2})\n" : "")
                            + $"• Actual Tally Balance: ₹{liveBal.opening:N2}\n"
                            + $"• Unexplained Difference: ₹{adjDiff:N2}\n\n"
                            + "Do you still want to pass these entries into Tally?";
                        if (!ShowThemedDialog("Opening Balance Mismatch Warning", warn, isError: true, yesNo: true))
                            return;
                    }
                }
            }
        }

        // Guardrail 4 — LAST-MOMENT duplicate check against Tally itself, immediately before anything is written.
        // Analyze already checks, but the grid can be stale: a re-post after "Failed" (Tally saved the voucher but the reply
        // timed out), posting the same statement from another PC, a second Post click, or a newer parser producing a different
        // row hash. Tally's own books are the final word, so every post is re-checked here; if Tally cannot be read we do NOT
        // post silently.
        if (_tallyConnected)
        {
            TxtFooter.Text = "Checking Tally for entries that already exist...";
            var bankForCheck = approved[0].BankLedger;
            var chkDates = approved.Select(r => r.TxnDate).OrderBy(d => d, StringComparer.Ordinal).ToList();
            var (chkOk, chkLive) = await conn.FetchExistingVouchersExAsync(chkDates[0], chkDates[^1], padDays: 3, bankLedger: bankForCheck);
            if (!chkOk)
            {
                if (!ShowThemedDialog("Cannot Check Tally for Duplicates",
                        "Tally did not return its existing vouchers for this period (busy, timed out, or the company is not open), so "
                        + "these entries cannot be checked against what is already in Tally.\n\n"
                        + "Recommended: click No, wait for Tally, and post again.\n\nPost anyway (duplicates possible)?",
                        isError: true, yesNo: true))
                {
                    TxtFooter.Text = "Posting cancelled — Tally duplicate check unavailable.";
                    return;
                }
            }
            else
            {
                var already = ContraDedupEngine.FindAlreadyInTally(approved, bankForCheck, chkLive);
                if (already.Count > 0)
                {
                    var dupLines = already.Take(15).Select(h =>
                        $"• {h.row.DisplayDate} | {(h.row.TxnType == "CR" ? "Dr" : "Cr")} ₹{h.row.Amount:N2} | {h.row.SelectedLedger}  →  in Tally: "
                        + $"{h.voucher.VoucherType}{(string.IsNullOrEmpty(h.voucher.VoucherNumber) ? "" : " No. " + h.voucher.VoucherNumber)} "
                        + $"dated {BankStatementParser.FormatDisplayDate(h.voucher.Date)}{(h.byId ? " (posted earlier by this app)" : "")}");
                    var dupMsg = $"{already.Count} of the {approved.Count} selected entries are ALREADY in Tally for '{bankForCheck}':\n\n"
                        + string.Join("\n", dupLines)
                        + (already.Count > 15 ? $"\n… and {already.Count - 15} more" : "")
                        + "\n\nYes = untick these and post only the remaining entries (recommended).\nNo = cancel posting.";
                    if (!ShowThemedDialog("Entries Already in Tally", dupMsg, isError: true, yesNo: true))
                    {
                        TxtFooter.Text = "Posting cancelled — some entries already exist in Tally.";
                        return;
                    }
                    foreach (var dup in already)
                    {
                        dup.row.Selected = false;
                        dup.row.OverlapStatus = "OVERLAP_TALLY_EXISTING";
                        dup.row.OverlapReason = $"Already in Tally ({dup.voucher.VoucherType} {dup.voucher.VoucherNumber}, {dup.voucher.Date}) — found by the pre-post check.";
                    }
                    var dupSkip = already.Select(h => h.row).ToHashSet();
                    approved = approved.Where(r => !dupSkip.Contains(r)).ToList();
                    UpdateSelectedTotalsBar();
                    try { GridReview.CommitEdit(DataGridEditingUnit.Row, true); GridReview.Items.Refresh(); } catch { /* display only */ }
                    if (approved.Count == 0)
                    {
                        TxtFooter.Text = "Nothing posted — every selected entry is already in Tally.";
                        ShowThemedDialog("Nothing to Post", "Every selected entry already exists in Tally. Nothing was posted.", isError: false);
                        return;
                    }
                }
            }
        }

        // 1. Automatic Backup ONLY if the Backup checkbox is ticked (no popup asking every time!)
        if (pushDirect && ChkBackupBeforePost.IsChecked == true)
        {
            TxtFooter.Text = "Creating Tally backup...";
            var (bOk, bMsg) = await conn.CreateBackupSnapshotAsync(GetActiveBackupDir());
            RefreshStats();
            if (!bOk)
            {
                ShowThemedDialog("Tally Backup Failed", bMsg, isError: true);
                return;
            }
        }

        // 2. Check Missing Ledgers & show interactive Head (Parent Group) selector dialog
        var existingSet = new HashSet<string>(_tallyLedgers, StringComparer.OrdinalIgnoreCase);
        var missingMap = new Dictionary<string, MissingLedgerItem>(StringComparer.OrdinalIgnoreCase);
        foreach (var r in approved)
        {
            foreach (var (name, isBank) in r.PostingLedgers.Select(l => (l.Trim(), false)).Prepend((r.BankLedger, true)))
            {
                if (string.IsNullOrWhiteSpace(name) || existingSet.Contains(name)) continue;
                if (!missingMap.TryGetValue(name, out var item))
                    missingMap[name] = new MissingLedgerItem { Name = name, Role = isBank ? "Bank" : "Party/Expense", UsageCount = 1, ParentGroup = _classifier.PredictParentGroup(name, r.VoucherType, r.TxnType, isBank) };
                else item.UsageCount++;
            }
        }

        _classifier.SyncFromServerIfUpdated();
        if (missingMap.Count > 0)
        {
            var chosenToCreate = ShowMissingLedgersDialog(missingMap.Values.ToList());
            if (chosenToCreate == null) return; // User clicked Cancel
            if (chosenToCreate.Count > 0)
            {
                if (pushDirect)
                {
                    var (cOk, cErr) = await conn.CreateLedgersAsync(chosenToCreate);
                    if (!cOk)
                    {
                        ShowThemedDialog("Ledger Creation Error", $"Could not create missing ledgers in Tally:\n{cErr}", isError: true);
                        return;
                    }
                    _classifier.LearnParentGroups(chosenToCreate);
                    foreach (var m in chosenToCreate) _tallyLedgers.Add(m.Name);
                    foreach (var row in ReviewRows) row.IsNewLedger = row.PostingLedgers.Any(l => !IsKnownTallyLedger(l));
                }
                else
                {
                    var xmlPath = Path.Combine(_db.ExportDir, $"tally_ledgers_{Environment.MachineName}_{DateTime.Now:yyyyMMdd_HHmmss}.xml");
                    _classifier.LearnParentGroups(chosenToCreate);
                    await File.WriteAllTextAsync(xmlPath, conn.BuildLedgersXml(chosenToCreate));
                }
            }
        }

        // 3. Train ML (off the UI thread; a learning failure must never block posting)
        var learnRows = approved.ToList();
        var learnComp = _activeCompanyName;
        try { await Task.Run(() => _classifier.LearnFromRows(learnRows, learnComp)); }
        catch (Exception ex) { TxtFooter.Text = $"ML learning skipped: {ex.Message}"; }

        if (!pushDirect)
        {
            var xmlFile = Path.Combine(_db.ExportDir, $"tally_vouchers_{Environment.MachineName}_{DateTime.Now:yyyyMMdd_HHmmss}.xml");
            await File.WriteAllTextAsync(xmlFile, conn.BuildVouchersXml(approved));
            _db.RecordPostedTransactions(approved, postedToTally: false, _activeCompanyName);
            RefreshStats();
            ShowThemedDialog("Tally XML Exported — Done", $"Exported {approved.Count} vouchers to:\n{xmlFile}", isError: false);
            return;
        }

        // 4. Direct Push (zero XML created) + Per-entry Done/Failed + Post-Push Verification
        TxtFooter.Text = $"Posting {approved.Count} entries directly to Tally...";
        var res = await conn.PushVouchersIndividuallyAsync(approved, _currentBalances);

        var postedIds = res.PostedEntries.Select(p => p.RowId).ToHashSet();
        var failedMap = new Dictionary<string, string>();
        foreach (var f in res.FailedEntries) failedMap.TryAdd(f.RowId, f.Reason);
        foreach (var r in ReviewRows)
        {
            if (postedIds.Contains(r.RowId)) { r.PostStatus = "DONE"; r.Selected = false; }
            else if (failedMap.TryGetValue(r.RowId, out var err)) { r.PostStatus = "FAILED"; r.PostError = err; r.Selected = true; }
        }
        string recordError = "";
        if (res.PostedEntries.Count > 0)
        {
            try
            {
                var postedCopy = res.PostedEntries.ToList();
                var compForDb = _activeCompanyName;
                await Task.Run(() =>
                {
                    _db.RecordPostedTransactions(postedCopy, postedToTally: true, compForDb);
                    _db.RecordPostedBatch(compForDb, postedCopy[0].BankLedger, postedCopy);
                });
            }
            catch (Exception ex)
            {
                // The vouchers ARE in Tally; only the local history failed. Re-analysis still detects them from Tally itself.
                recordError = $"\n\n⚠ Entries were posted to Tally, but saving the posting history to the office database failed: {ex.Message}\n"
                    + "Re-analysing this statement will still detect them as 'Already in Tally'. Batch rollback for this post is not available.";
            }
            if (res.FailedEntries.Count == 0 && _selectedStatementFiles.Length > 0)
            {
                var postedBank = res.PostedEntries[0].BankLedger;
                var postedCnt = res.PostedEntries.Count;
                var filesCopy = _selectedStatementFiles.ToArray();
                var compCopy = _activeCompanyName;
                // Remember where each PROVEN statement ended, so the next statement of this account must continue from it
                var history = _analyzedFiles
                    .Where(f => f.Balances.StatementBalanced == true && f.Balances.CompletenessIssues.Count == 0
                                && f.Balances.StatementOpening.HasValue && f.Balances.StatementClosing.HasValue)
                    .Select(f => new StatementHistoryEntry
                    {
                        CompanyName = compCopy, BankLedger = postedBank, FromDate = f.Balances.FromDate, ToDate = f.Balances.ToDate,
                        Opening = f.Balances.StatementOpening!.Value, Closing = f.Balances.StatementClosing!.Value, SourceFile = f.SourceFile
                    }).ToList();
                _ = Task.Run(() =>
                {
                    foreach (var fp in filesCopy)
                    {
                        try { _db.RecordPostedStatementFile(ComputeFileSha256(fp), Path.GetFileName(fp), compCopy, postedBank, postedCnt); }
                        catch { }
                    }
                    foreach (var h in history)
                    {
                        try { _db.RecordStatement(h); } catch { /* continuity check is advisory */ }
                    }
                });
            }
        }
        RefreshStats();
        UpdateSelectedTotalsBar();

        var msg = $"{res.Created} of {res.Total} entries posted — Done.\n";
        if (res.Verification != null)
        {
            if (res.Verification.CouldNotVerify)
                msg += "\nVerification: could not read the vouchers back from Tally (timeout). Open the Day Book in Tally to confirm.";
            else if (res.Verification.AllOk)
                msg += $"\nVerification Passed: All {res.Verification.Verified}/{res.Verification.Expected} entries verified in Tally (zero overlaps, zero mixed ledgers).";
            else
            {
                msg += $"\nVerification Warnings: Missing {res.Verification.Missing.Count}, Duplicates {res.Verification.Duplicated.Count}, Mixed {res.Verification.Mixed.Count}.";
                foreach (var line in res.Verification.Missing.Concat(res.Verification.Duplicated).Concat(res.Verification.Mixed).Take(10))
                    msg += $"\n  • {line}";
            }
            if (!string.IsNullOrEmpty(res.Verification.BalanceSummary))
                msg += $"\n{res.Verification.BalanceSummary}";
        }
        if (res.FailedEntries.Count > 0)
        {
            msg += $"\n\nFailed Entries ({res.FailedEntries.Count}):\n" +
                string.Join("\n", res.FailedEntries.Take(15).Select(f => $"• {f.DisplayDate} | {f.SelectedLedger} | ₹{f.Amount:N2} — {f.Reason}"));
        }

        msg += recordError;
        bool fullySuccessful = res.FailedEntries.Count == 0 && res.Created > 0 && string.IsNullOrEmpty(recordError);
        if (fullySuccessful)
            ClearLoadedStatement();

        ShowThemedDialog(fullySuccessful ? $"Done — {res.Created} Entries Posted" : $"Posted {res.Created} Done, {res.FailedEntries.Count} Failed", msg, isError: res.FailedEntries.Count > 0);
        TxtFooter.Text = fullySuccessful
            ? $"{res.Created} of {res.Total} entries posted — Done. Statement cleared and ready for next file."
            : $"{res.Created} of {res.Total} entries posted — Done. ({res.FailedEntries.Count} failed)";
    }

    private void ClearLoadedStatement()
    {
        _selectedStatementFiles = [];
        TxtSelectedFiles.Text = "No file selected — or drag files onto this window";
        PwdPdf.Clear();
        ReviewRows.Clear();
        _currentBalances = null;
        BalanceBanner.Visibility = Visibility.Collapsed;
        SelectedTotalsBar.Visibility = Visibility.Collapsed;
        TxtSearch.Text = "";
        if (CmbFilter.Items.Count > 0) CmbFilter.SelectedIndex = 0;
        _pendingBillsCache.Clear();
    }

    private void TxtSearch_TextChanged(object sender, TextChangedEventArgs e) => ApplyFilter();
    private void CmbFilter_SelectionChanged(object sender, SelectionChangedEventArgs e) => ApplyFilter();

    private void ApplyFilter()
    {
        if (!IsLoaded) return;
        var view = CollectionViewSource.GetDefaultView(ReviewRows);
        var q = (TxtSearch.Text ?? "").Trim().ToLowerInvariant();
        var mode = (CmbFilter.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "All Rows";
        view.Filter = obj =>
        {
            if (obj is not BankTransactionRow r) return false;
            if (!string.IsNullOrEmpty(q) && !$"{r.Narration} {r.SelectedLedger} {r.RefNo}".ToLowerInvariant().Contains(q)) return false;
            return mode switch
            {
                "Selected to Post" => r.Selected,
                "Contra Entries" => r.VoucherType == "Contra",
                "Overlaps / Duplicates" => r.OverlapStatus != "NEW",
                "Needs Ledger Check" => r.PostStatus != "DONE" && (r.NeedsReview || ReviewPolicy.IsGuess(r)),
                "Balance Breaks" => r.HasBalanceBreak,
                "Parser Warnings" => !string.IsNullOrEmpty(r.ParseWarning) || r.HasBalanceBreak,
                _ => true
            };
        };
    }

    private void BtnTheme_Click(object sender, RoutedEventArgs e)
    {
        _isDark = !_isDark;
        var res = Application.Current.Resources;
        if (_isDark)
        {
            // True AMOLED Black Dark Mode
            res["AppBg"] = new SolidColorBrush(Colors.Black);
            res["CardBg"] = new SolidColorBrush(Color.FromRgb(10, 10, 10));
            res["HeaderBg"] = new SolidColorBrush(Colors.Black);
            res["InkBrush"] = new SolidColorBrush(Color.FromRgb(248, 250, 252));
            res["MutedBrush"] = new SolidColorBrush(Color.FromRgb(156, 163, 175));
            res["BorderBrush"] = new SolidColorBrush(Color.FromRgb(82, 82, 91));
            res["GridHeaderBg"] = new SolidColorBrush(Color.FromRgb(18, 18, 18));
            res["GridHeaderFg"] = new SolidColorBrush(Colors.White);
            res["RowBg"] = new SolidColorBrush(Colors.Black);
            res["RowAltBg"] = new SolidColorBrush(Color.FromRgb(12, 12, 12));
            res["RowSelBg"] = new SolidColorBrush(Color.FromRgb(23, 45, 74));
            res["RowSelFg"] = new SolidColorBrush(Colors.White);
            res["InputBg"] = new SolidColorBrush(Color.FromRgb(18, 18, 18));
            res["InputFg"] = new SolidColorBrush(Colors.White);
            res["PopupBg"] = new SolidColorBrush(Color.FromRgb(14, 14, 14));
            res["HoverBg"] = new SolidColorBrush(Color.FromRgb(30, 58, 95));
            BtnTheme.Content = "☀️ Light";
        }
        else
        {
            res["AppBg"] = new SolidColorBrush(Color.FromRgb(243, 246, 250));
            res["CardBg"] = new SolidColorBrush(Colors.White);
            res["HeaderBg"] = new SolidColorBrush(Color.FromRgb(27, 79, 114));
            res["InkBrush"] = new SolidColorBrush(Color.FromRgb(17, 24, 39));
            res["MutedBrush"] = new SolidColorBrush(Color.FromRgb(100, 116, 139));
            res["BorderBrush"] = new SolidColorBrush(Color.FromRgb(203, 213, 225));
            res["GridHeaderBg"] = new SolidColorBrush(Color.FromRgb(226, 232, 240));
            res["GridHeaderFg"] = new SolidColorBrush(Color.FromRgb(15, 23, 42));
            res["RowBg"] = new SolidColorBrush(Colors.White);
            res["RowAltBg"] = new SolidColorBrush(Color.FromRgb(248, 250, 252));
            res["RowSelBg"] = new SolidColorBrush(Color.FromRgb(219, 234, 254));
            res["RowSelFg"] = new SolidColorBrush(Color.FromRgb(15, 23, 42));
            res["InputBg"] = new SolidColorBrush(Colors.White);
            res["InputFg"] = new SolidColorBrush(Color.FromRgb(17, 24, 39));
            res["PopupBg"] = new SolidColorBrush(Colors.White);
            res["HoverBg"] = new SolidColorBrush(Color.FromRgb(224, 242, 254));
            BtnTheme.Content = "🌙 Dark";
        }
    }

    private void BtnBatchHistory_Click(object sender, RoutedEventArgs e)
    {
        var batches = _db.GetRecentBatches(_activeCompanyName, 30);
        var dlg = new Window
        {
            Title = string.IsNullOrWhiteSpace(_activeCompanyName) ? "Posted Batches & Rollback" : $"Posted Batches — {_activeCompanyName}",
            Width = 860, Height = 460,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var rootPanel = new DockPanel { Margin = new Thickness(14) };
        var info = new TextBlock
        {
            Text = "Recent batches pushed to Tally. Select a batch and click 'Rollback Selected Batch from Tally' to remove those exact vouchers if posted to the wrong bank/company.",
            FontSize = 12, Foreground = (Brush)Application.Current.Resources["MutedBrush"],
            TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 0, 0, 10)
        };
        DockPanel.SetDock(info, Dock.Top);
        rootPanel.Children.Add(info);

        var footer = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 10, 0, 0) };
        var btnRollback = new Button { Content = "Rollback Selected Batch from Tally", Height = 30, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Background = new SolidColorBrush(Color.FromRgb(185, 28, 28)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        var btnClose = new Button { Content = "Close", Height = 30, Padding = new Thickness(16, 0, 16, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        footer.Children.Add(btnRollback);
        footer.Children.Add(btnClose);
        DockPanel.SetDock(footer, Dock.Bottom);
        rootPanel.Children.Add(footer);

        var dg = new DataGrid
        {
            ItemsSource = batches,
            AutoGenerateColumns = false,
            IsReadOnly = true,
            CanUserAddRows = false,
            SelectionMode = DataGridSelectionMode.Single,
            Background = (Brush)Application.Current.Resources["CardBg"],
            RowBackground = (Brush)Application.Current.Resources["RowBg"],
            AlternatingRowBackground = (Brush)Application.Current.Resources["RowAltBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"],
            BorderBrush = (Brush)Application.Current.Resources["BorderBrush"],
            GridLinesVisibility = DataGridGridLinesVisibility.Horizontal,
            HeadersVisibility = DataGridHeadersVisibility.Column
        };
        dg.Columns.Add(new DataGridTextColumn { Header = "Posted On", Binding = new Binding("CreatedAt"), Width = 135 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Company", Binding = new Binding("CompanyName"), Width = 125 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Bank Ledger", Binding = new Binding("BankLedger"), Width = 140 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Period", Binding = new Binding("PeriodLabel"), Width = 155 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Entries", Binding = new Binding("EntryCount"), Width = 62 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Dr (₹)", Binding = new Binding("TotalCredit") { Converter = new IndianAmountConverter() }, Width = 92 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Cr (₹)", Binding = new Binding("TotalDebit") { Converter = new IndianAmountConverter() }, Width = 92 });
        dg.Columns.Add(new DataGridTextColumn { Header = "Status", Binding = new Binding("StatusLabel"), Width = 86 });
        rootPanel.Children.Add(dg);

        btnClose.Click += (_, _) => dlg.Close();
        btnRollback.Click += async (_, _) =>
        {
            if (dg.SelectedItem is not PostedBatchSummary sel)
            {
                ShowThemedDialog("Select a Batch", "Please select a posted batch row first.", isError: false);
                return;
            }
            if (sel.RolledBack)
            {
                ShowThemedDialog("Already Rolled Back", $"Batch {sel.BatchId} was already rolled back.", isError: false);
                return;
            }
            if (!_tallyConnected)
            {
                ShowThemedDialog("Tally Not Connected", "Connect to Tally first to rollback vouchers.", isError: true);
                return;
            }
            var confirm = $"Delete all {sel.EntryCount} voucher(s) from Tally for batch {sel.BatchId}?\n\n"
                + $"• Company: {sel.CompanyName}\n• Bank Ledger: {sel.BankLedger}\n• Period: {sel.PeriodLabel}\n\n"
                + "Their local duplicate hashes will also be cleared so you can re-upload the statement cleanly.";
            if (!ShowThemedDialog("Confirm Batch Rollback", confirm, isError: true, yesNo: true))
                return;

            btnRollback.IsEnabled = false;
            try
            {
                if (!string.Equals(sel.CompanyName.Trim(), _activeCompanyName.Trim(), StringComparison.OrdinalIgnoreCase))
                {
                    ShowThemedDialog("Different Company Open", $"This batch belongs to '{sel.CompanyName}', but Tally is connected to '{_activeCompanyName}'. Connect to the correct company first.", isError: true);
                    return;
                }
                var conn = new TallyConnector(TxtTallyHost.Text.Trim(), sel.CompanyName);
                var (del, fail, summary, deletedGuids) = await conn.DeleteVouchersByGuidAsync(sel.Vouchers);
                if (del > 0)
                {
                    // Clear duplicate-guard hashes ONLY for vouchers really removed from Tally; keep the rest in the batch for a retry
                    var deletedSet = new HashSet<string>(deletedGuids, StringComparer.OrdinalIgnoreCase);
                    var removed = sel.Vouchers.Where(v => deletedSet.Contains(v.Guid)).ToList();
                    var remaining = sel.Vouchers.Where(v => !deletedSet.Contains(v.Guid)).ToList();
                    await Task.Run(() => _db.MarkBatchRolledBack(sel.BatchId, removed.Select(v => v.TxnHash), remaining));
                }
                RefreshStats();
                ShowThemedDialog(fail > 0 ? "Batch Rollback — Partly Done" : "Batch Rollback Complete",
                    fail > 0 ? summary + "\n\nThe vouchers that could not be deleted are kept in this batch; fix the cause in Tally and roll back again." : summary,
                    isError: fail > 0);
                dg.ItemsSource = _db.GetRecentBatches(_activeCompanyName, 30);
            }
            catch (Exception ex)
            {
                ShowThemedDialog("Rollback Error", ex.Message, isError: true);
            }
            finally
            {
                btnRollback.IsEnabled = true;
            }
        };

        dlg.Content = rootPanel;
        dlg.ShowDialog();
    }

    private void BtnBulkSetLedger_Click(object sender, RoutedEventArgs e)
    {
        var rows = GridReview.SelectedItems.OfType<BankTransactionRow>().ToList();
        if (rows.Count == 0)
        {
            ShowThemedDialog("No Rows Highlighted", "Click or Shift+Click / Ctrl+Click one or more rows in the table first, then click 'Bulk Set Ledger'.", isError: false);
            return;
        }
        BulkSetLedger(rows);
    }

    // ------------------------------------------------------------------ "Group similar"
    private void ChkGroup_Changed(object sender, RoutedEventArgs e) => ApplyGrouping();

    /// <summary>Groups the grid by party + direction + ledger (live: a row whose ledger changes moves to its new group).</summary>
    private void ApplyGrouping()
    {
        if (CollectionViewSource.GetDefaultView(ReviewRows) is not ListCollectionView view) return;
        // regrouping is not allowed while a cell is being edited: finish (or drop) the edit first
        try { GridReview.CommitEdit(DataGridEditingUnit.Cell, true); GridReview.CommitEdit(DataGridEditingUnit.Row, true); } catch { GridReview.CancelEdit(); }
        if (view.IsEditingItem) view.CommitEdit();
        if (view.IsAddingNew) view.CommitNew();
        using (view.DeferRefresh())
        {
            view.GroupDescriptions.Clear();
            view.LiveGroupingProperties.Clear();
            if (ChkGroup.IsChecked == true)
            {
                view.GroupDescriptions.Add(new PropertyGroupDescription(nameof(BankTransactionRow.GroupLabel)));
                view.LiveGroupingProperties.Add(nameof(BankTransactionRow.GroupLabel));
                view.IsLiveGrouping = true;
            }
            else view.IsLiveGrouping = false;
        }
    }

    private void GroupSetLedger_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.DataContext is not CollectionViewGroup group) return;
        var rows = group.Items.OfType<BankTransactionRow>().Where(r => r.PostStatus != "DONE").ToList();
        if (rows.Count > 0) BulkSetLedger(rows);
        e.Handled = true;   // do not fold / unfold the group
    }

    private void MenuUngroup_Click(object sender, RoutedEventArgs e)
    {
        var rows = GridReview.SelectedItems.OfType<BankTransactionRow>().ToList();
        foreach (var r in rows) r.KeepSeparate = true;
        TxtFooter.Text = rows.Count == 0 ? "Highlight a row first." : $"{rows.Count} row(s) taken out of their group.";
    }

    private void MenuRegroup_Click(object sender, RoutedEventArgs e)
    {
        var rows = GridReview.SelectedItems.OfType<BankTransactionRow>().ToList();
        foreach (var r in rows) r.KeepSeparate = false;
        TxtFooter.Text = rows.Count == 0 ? "Highlight a row first." : $"{rows.Count} row(s) back in their group (same party, direction and ledger).";
    }

    private void BulkSetLedger(List<BankTransactionRow> selectedRows)
    {

        var dlg = new Window
        {
            Title = $"Bulk Set Tally Ledger ({selectedRows.Count} rows)",
            Width = 440,
            SizeToContent = SizeToContent.Height,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            Owner = this,
            ResizeMode = ResizeMode.NoResize,
            Background = (Brush)Application.Current.Resources["AppBg"],
            Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };

        var rootPanel = new StackPanel { Margin = new Thickness(16) };
        rootPanel.Children.Add(new TextBlock
        {
            Text = $"Assign one Tally Ledger to all {selectedRows.Count} row(s):",
            FontSize = 12.5,
            Margin = new Thickness(0, 0, 0, 8),
            TextWrapping = TextWrapping.Wrap
        });
        var cmbLedger = new ComboBox
        {
            IsEditable = true,
            Height = 30,
            ItemsSource = DropdownLedgers.ToList(),
            Text = selectedRows[0].SelectedLedger ?? "",
            Margin = new Thickness(0, 0, 0, 14)
        };
        rootPanel.Children.Add(cmbLedger);

        var btns = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
        var btnCancel = new Button { Content = "Cancel", Height = 30, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var btnApply = new Button { Content = "Apply to All", Height = 30, Padding = new Thickness(16, 0, 16, 0), Background = new SolidColorBrush(Color.FromRgb(14, 138, 109)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        btns.Children.Add(btnCancel);
        btns.Children.Add(btnApply);
        rootPanel.Children.Add(btns);

        bool confirmed = false;
        btnCancel.Click += (_, _) => dlg.Close();
        btnApply.Click += (_, _) =>
        {
            if (string.IsNullOrWhiteSpace(cmbLedger.Text)) return;
            confirmed = true;
            dlg.Close();
        };

        dlg.Content = rootPanel;
        dlg.Loaded += (_, _) => cmbLedger.Focus();
        dlg.ShowDialog();
        if (!confirmed) return;

        var chosen = cmbLedger.Text.Trim();
        foreach (var row in selectedRows)
        {
            if (!string.Equals(row.SelectedLedger, chosen, StringComparison.Ordinal))
            {
                row.BillAllocations = [];
                row.BillRef = "(None)";
            }
            row.SelectedLedger = chosen;
            row.LastCommittedLedger = chosen;
            row.UserEdited = true;
            row.Confidence = 1.0;
            row.PredictionSource = "user_manual";
            row.IsNewLedger = !IsKnownTallyLedger(chosen);
            if (row.IsSplit) row.Splits = [];
            ConfirmReviewed(row);
        }
        if (!DropdownLedgers.Contains(chosen, StringComparer.OrdinalIgnoreCase))
            DropdownLedgers.Add(chosen);

        var comp = _activeCompanyName;
        var rowsCopy = selectedRows.ToList();
        _ = Task.Run(() =>
        {
            _classifier.LearnFromRows(rowsCopy, comp);
            Dispatcher.BeginInvoke(RefreshStats);
        });
        TxtFooter.Text = $"Updated {selectedRows.Count} row(s) to '{chosen}'.";
        _ = AutoMatchBillsAsync(selectedRows);
    }

    // ------------------------------------------------------------------ split one bank entry across several ledgers
    private void BtnSplit_Click(object sender, RoutedEventArgs e)
    {
        if (GridReview.SelectedItem is not BankTransactionRow row)
        {
            ShowThemedDialog("Split Entry", "Click the bank entry you want to split first, then click '✂ Split Entry'.", isError: false);
            return;
        }
        if (row.PostStatus == "DONE") { ShowThemedDialog("Split Entry", "This entry is already posted to Tally.", isError: false); return; }
        if (row.IsContra || row.VoucherType == "Contra")
        {
            ShowThemedDialog("Split Entry", "A Contra (bank ↔ bank / cash) entry cannot be split. Change it to Payment or Receipt first.", isError: false);
            return;
        }
        ShowSplitDialog(row);
    }

    private sealed class SplitLineUi
    {
        public ComboBox Ledger { get; init; } = null!;
        public TextBox Amount { get; init; } = null!;
        public Grid Panel { get; init; } = null!;
    }

    private void ShowSplitDialog(BankTransactionRow row)
    {
        long totalPaise = (long)Math.Round(row.Amount * 100);
        var dlg = new Window
        {
            Title = "✂ Split Entry", Width = 620, SizeToContent = SizeToContent.Height, MaxHeight = 720,
            WindowStartupLocation = WindowStartupLocation.CenterOwner, Owner = this, ResizeMode = ResizeMode.NoResize,
            Background = (Brush)Application.Current.Resources["AppBg"], Foreground = (Brush)Application.Current.Resources["InkBrush"]
        };
        var root = new StackPanel { Margin = new Thickness(16) };
        root.Children.Add(new TextBlock
        {
            Text = $"{row.DisplayDate}   •   {(row.TxnType == "CR" ? "Receipt (Dr bank)" : "Payment (Cr bank)")}   •   ₹{row.Amount:N2}",
            FontWeight = FontWeights.Bold, FontSize = 14
        });
        root.Children.Add(new TextBlock { Text = row.Narration, TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 4, 0, 10), Opacity = 0.8 });
        root.Children.Add(new TextBlock { Text = "Post this one bank entry to these ledgers (the amounts must add up exactly):", Margin = new Thickness(0, 0, 0, 6) });

        var linesPanel = new StackPanel();
        root.Children.Add(linesPanel);
        var lines = new List<SplitLineUi>();
        var remaining = new TextBlock { FontWeight = FontWeights.SemiBold, Margin = new Thickness(0, 8, 0, 0) };
        var save = new Button { Content = "✓ Save Split", Height = 32, Padding = new Thickness(18, 0, 18, 0), IsEnabled = false,
            Background = new SolidColorBrush(Color.FromRgb(5, 150, 105)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        bool firstTouched = row.IsSplit;   // the first line fills itself with what is left until you type in it
        bool updating = false;

        long Paise(TextBox tb)
        {
            var t = tb.Text.Trim();
            if (t.Length == 0) return 0;
            var (amt, _) = BankStatementParser.ParseIndianAmount(t);
            return amt > 0 ? (long)Math.Round(amt * 100) : -1;
        }

        void Recalc()
        {
            if (updating) return;
            updating = true;
            if (!firstTouched && lines.Count >= 2)
            {
                long others = lines.Skip(1).Sum(l => Math.Max(0, Paise(l.Amount)));
                lines[0].Amount.Text = (Math.Max(0, totalPaise - others) / 100m).ToString("0.00", System.Globalization.CultureInfo.InvariantCulture);
            }
            updating = false;
            long sum = lines.Sum(l => Math.Max(0, Paise(l.Amount)));
            long left = totalPaise - sum;
            bool amountsOk = lines.All(l => Paise(l.Amount) > 0);
            var names = lines.Select(l => (l.Ledger.Text ?? "").Trim()).ToList();
            bool namesOk = names.All(n => n.Length > 0) && names.Distinct(StringComparer.OrdinalIgnoreCase).Count() == names.Count
                           && !names.Any(n => n.Equals(row.BankLedger.Trim(), StringComparison.OrdinalIgnoreCase));
            remaining.Text = left == 0 ? "✓ Adds up to the bank amount" : left > 0 ? $"Remaining to allocate: ₹{left / 100m:N2}" : $"Over by ₹{-left / 100m:N2}";
            remaining.Foreground = left == 0 ? Brushes.SeaGreen : Brushes.Firebrick;
            save.IsEnabled = lines.Count >= 2 && left == 0 && amountsOk && namesOk;
            save.ToolTip = !namesOk ? "Every line needs a different ledger (not the bank ledger itself)" : !amountsOk ? "Every line needs an amount" : null;
        }

        void AddLine(string ledger, decimal? amount)
        {
            var g = new Grid { Margin = new Thickness(0, 0, 0, 6) };
            g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(140) });
            g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(36) });
            var cb = new ComboBox { IsEditable = true, IsTextSearchEnabled = true, ItemsSource = DropdownLedgers, Text = ledger, Height = 28, Margin = new Thickness(0, 0, 8, 0) };
            var tb = new TextBox { Height = 28, VerticalContentAlignment = VerticalAlignment.Center, TextAlignment = TextAlignment.Right,
                Text = amount.HasValue ? amount.Value.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture) : "" };
            var del = new Button { Content = "✕", Height = 28, Margin = new Thickness(6, 0, 0, 0), ToolTip = "Remove this line", Style = (Style)Application.Current.Resources["SecBtn"] };
            Grid.SetColumn(tb, 1); Grid.SetColumn(del, 2);
            g.Children.Add(cb); g.Children.Add(tb); g.Children.Add(del);
            var line = new SplitLineUi { Ledger = cb, Amount = tb, Panel = g };
            lines.Add(line);
            linesPanel.Children.Add(g);
            cb.AddHandler(System.Windows.Controls.Primitives.TextBoxBase.TextChangedEvent, new TextChangedEventHandler((_, _) => Recalc()));
            cb.SelectionChanged += (_, _) => Dispatcher.BeginInvoke(new Action(Recalc));
            tb.TextChanged += (_, _) =>
            {
                if (!updating && lines.Count > 0 && ReferenceEquals(line, lines[0])) firstTouched = true;
                Recalc();
            };
            del.Click += (_, _) =>
            {
                if (lines.Count <= 2) return;   // a split has at least two lines
                lines.Remove(line);
                linesPanel.Children.Remove(g);
                Recalc();
            };
        }

        if (row.IsSplit) foreach (var sp in row.Splits) AddLine(sp.Ledger, sp.Amount);
        else { AddLine(row.SelectedLedger, row.Amount); AddLine("", null); }

        var add = new Button { Content = "+ Add line", Height = 28, Padding = new Thickness(12, 0, 12, 0), HorizontalAlignment = HorizontalAlignment.Left, Style = (Style)Application.Current.Resources["SecBtn"] };
        add.Click += (_, _) => { AddLine("", null); Recalc(); };
        root.Children.Add(add);
        root.Children.Add(remaining);

        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 14, 0, 0) };
        bool remove = false, ok = false;
        if (row.IsSplit)
        {
            var unsplit = new Button { Content = "Remove Split", Height = 32, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"],
                ToolTip = "Post the whole amount to the first ledger again" };
            unsplit.Click += (_, _) => { remove = true; dlg.Close(); };
            buttons.Children.Add(unsplit);
        }
        var cancel = new Button { Content = "Cancel", Height = 32, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(0, 0, 8, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        cancel.Click += (_, _) => dlg.Close();
        save.Click += (_, _) => { ok = true; dlg.Close(); };
        buttons.Children.Add(cancel); buttons.Children.Add(save);
        root.Children.Add(buttons);
        dlg.Content = root;
        dlg.Loaded += (_, _) => { Recalc(); lines[^1].Ledger.Focus(); };
        dlg.ShowDialog();

        if (remove)
        {
            var keep = row.Splits[0].Ledger;
            row.Splits = [];
            if (SplitMemory.CanRemember(row))
                try { _db.DeleteRememberedSplit(_activeCompanyName, row.PartyKey, row.TxnType); } catch { }
            CommitLedgerEdit(row, keep);
            TxtFooter.Text = $"Split removed — the whole ₹{row.Amount:N2} goes to '{keep}'.";
            return;
        }
        if (!ok) return;

        var split = lines.Select(l => new LedgerSplit { Ledger = (l.Ledger.Text ?? "").Trim(), Amount = Paise(l.Amount) / 100m }).ToList();
        var main = split.OrderByDescending(sl => sl.Amount).First().Ledger;
        row.Splits = split;
        row.SelectedLedger = main;
        row.LastCommittedLedger = main;
        row.UserEdited = true;
        row.Confidence = 1.0;
        row.PredictionSource = "user_manual";
        row.BillAllocations = [];
        row.BillRef = "(None)";
        row.IsNewLedger = split.Any(sl => !IsKnownTallyLedger(sl.Ledger));
        foreach (var newName in split.Select(sl => sl.Ledger).Where(n => !DropdownLedgers.Contains(n, StringComparer.OrdinalIgnoreCase)).ToList()) DropdownLedgers.Add(newName);
        ConfirmReviewed(row);
        // remembered for the next entry with this party (same direction) — applied automatically at Analyze
        bool remembered = false;
        if (SplitMemory.CanRemember(row))
            try { _db.SaveRememberedSplit(_activeCompanyName, row.PartyKey, row.TxnType, split); remembered = true; } catch { }
        TxtFooter.Text = $"Split saved: {row.SplitSummary}" + (remembered ? "  •  remembered for this party next time" : "");
    }

    private void BtnTeachColumns_Click(object sender, RoutedEventArgs e)
    {
        var pdf = _selectedStatementFiles.FirstOrDefault(f => Path.GetExtension(f).Equals(".pdf", StringComparison.OrdinalIgnoreCase));
        if (pdf == null || _selectedStatementFiles.Count(f => Path.GetExtension(f).Equals(".pdf", StringComparison.OrdinalIgnoreCase)) > 1)
        {
            var dlg = new Microsoft.Win32.OpenFileDialog { Filter = "PDF bank statement (*.pdf)|*.pdf", Title = "Statement whose columns to teach" };
            if (pdf != null) dlg.InitialDirectory = Path.GetDirectoryName(pdf);
            if (dlg.ShowDialog(this) != true) return;
            pdf = dlg.FileName;
        }
        try
        {
            if (TeachLayoutWindow.ShowFor(this, _db, pdf, PwdPdf.Password))
                TxtFooter.Text = "Layout saved — click ⚡ Analyze to read the statement with it.";
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Teach Columns", ex.Message, isError: true);
        }
    }

    private void BtnExportDebug_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_lastDiagnosticReport))
        {
            ShowThemedDialog("No Statement Analyzed", "Analyze a bank statement first, then click 'Debug' to save its parser diagnostic log.", isError: false);
            return;
        }
        try
        {
            Directory.CreateDirectory(_db.ExportDir);
            var path = Path.Combine(_db.ExportDir, $"parser_debug_{DateTime.Now:yyyyMMdd_HHmmss}.txt");
            File.WriteAllText(path, _lastDiagnosticReport, System.Text.Encoding.UTF8);
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("notepad.exe", $"\"{path}\"") { UseShellExecute = true });
            TxtFooter.Text = $"Saved parser diagnostic to {Path.GetFileName(path)}";

            // Optional: an anonymised copy of each PDF statement — safe to send for a parser fix
            var pdfs = _selectedStatementFiles.Where(f => Path.GetExtension(f).Equals(".pdf", StringComparison.OrdinalIgnoreCase)).ToList();
            if (pdfs.Count > 0 && ShowThemedDialog("Anonymised Copy for Support",
                    "Also make an anonymised copy of the statement PDF?\n\n"
                    + "Names, narrations and account / reference numbers are replaced with dummy text; dates, amounts, column headings "
                    + "and the page layout stay exactly as they are. Send that copy (with the debug report) instead of the real statement.",
                    isError: false, yesNo: true))
            {
                var made = new List<string>();
                foreach (var pdf in pdfs)
                {
                    var outPath = Path.Combine(_db.ExportDir, $"{Path.GetFileNameWithoutExtension(pdf)}_anonymised.pdf");
                    File.WriteAllBytes(outPath, StatementAnonymiser.Anonymise(pdf, PwdPdf.Password));
                    made.Add(outPath);
                }
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo("explorer.exe", $"/select,\"{made[0]}\"") { UseShellExecute = true });
                ShowThemedDialog("Anonymised Copy Saved",
                    string.Join("\n", made.Select(m => Path.GetFileName(m))) + "\n\nOpen it once and check that no client name or account number is left before sending it.",
                    isError: false);
            }
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Debug Export Error", ex.Message, isError: true);
        }
    }

    private void BtnClearXml_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            if (!ShowThemedDialog("Clear XML Exports", $"Delete all exported Tally XML files in:\n{_db.ExportDir}?\n\nOnly do this after they have been imported into Tally.", isError: true, yesNo: true)) return;
            int n = _db.ClearXmlExports();
            RefreshStats();
            ShowThemedDialog("XML Files Cleared", $"Cleared {n} exported XML file(s).", isError: false);
        }
        catch (Exception ex)
        {
            ShowThemedDialog("Could Not Clear XML", ex.Message, isError: true);
        }
    }

    private void BtnDeleteBackups_Click(object sender, RoutedEventArgs e)
    {
        var bDir = GetActiveBackupDir();
        if (!ShowThemedDialog("Delete Backups", $"Delete all saved Tally backup files (*.zip) in:\n{bDir}?", isError: true, yesNo: true)) return;
        int n = 0, failed = 0;
        if (Directory.Exists(bDir))
        {
            // Only our backup archives — never other files that happen to live in a user-chosen folder
            foreach (var f in Directory.GetFiles(bDir, "*.zip"))
            {
                try { File.Delete(f); n++; } catch { failed++; }
            }
        }
        RefreshStats();
        ShowThemedDialog("Backups Deleted", failed > 0 ? $"Deleted {n} backup file(s); {failed} could not be deleted (in use?)." : $"Deleted {n} Tally backup file(s).", isError: failed > 0);
    }
}
