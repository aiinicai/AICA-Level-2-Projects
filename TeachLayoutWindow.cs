using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using Rectangle = System.Windows.Shapes.Rectangle;
using AutoBankStatementEntry.Models;
using AutoBankStatementEntry.Services;

namespace AutoBankStatementEntry;

/// <summary>
/// "Teach Columns": shows a statement page exactly as laid out (any page — the transaction table does not have to be on
/// page 1), lets the user place column dividers and name each column, proves the result against the running balance, and
/// saves it as a layout every PC then uses automatically.
/// </summary>
public sealed class TeachLayoutWindow : Window
{
    private const double S = 1.35; // screen pixels per PDF point

    private static readonly (string role, string label, Color color)[] RoleInfo =
    [
        ("ignore", "— ignore —", Color.FromArgb(0, 0, 0, 0)),
        ("date", "Date", Color.FromArgb(46, 37, 99, 235)),
        ("value_date", "Value Date", Color.FromArgb(30, 37, 99, 235)),
        ("narration", "Description", Color.FromArgb(22, 100, 116, 139)),
        ("ref_no", "Ref / Cheque No", Color.FromArgb(30, 234, 179, 8)),
        ("debit", "Debit (Withdrawal)", Color.FromArgb(40, 220, 38, 38)),
        ("credit", "Credit (Deposit)", Color.FromArgb(40, 22, 163, 74)),
        ("amount", "Amount (one column)", Color.FromArgb(40, 234, 88, 12)),
        ("drcr", "Dr/Cr marker", Color.FromArgb(40, 234, 88, 12)),
        ("balance", "Balance", Color.FromArgb(40, 147, 51, 234)),
    ];

    private readonly DatabaseService _db;
    private readonly string _path;
    private readonly string? _pwd;
    private readonly BankStatementParser.PdfLayoutSnapshot _snap;
    private int _pageIdx;
    private List<double> _fr = [];      // column edges as a fraction of the page width
    private List<string> _roles = [];   // one per column
    private bool _saved;
    private LayoutTemplate? _lastTested;
    private bool _lastTestProven;
    private bool _lastTestUnprovable;

    private readonly Canvas _page = new() { Background = Brushes.White, ClipToBounds = true };
    private readonly Canvas _roleBar = new() { Height = 30 };
    private readonly TextBlock _pageLbl = new() { VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(8, 0, 8, 0), FontWeight = FontWeights.SemiBold };
    private readonly TextBlock _result = new() { TextWrapping = TextWrapping.Wrap, Margin = new Thickness(0, 6, 0, 6), FontSize = 12.5 };
    private readonly DataGrid _preview = new()
    {
        AutoGenerateColumns = false, IsReadOnly = true, Height = 170, HeadersVisibility = DataGridHeadersVisibility.Column,
        RowHeaderWidth = 0, CanUserAddRows = false
    };
    private readonly TextBox _name = new() { Width = 260, Height = 26, VerticalContentAlignment = VerticalAlignment.Center };
    private readonly Button _btnSave = new() { Content = "💾 Save Layout", Height = 30, Padding = new Thickness(14, 0, 14, 0), IsEnabled = false, FontWeight = FontWeights.Bold };
    private readonly ListBox _savedList = new() { Height = 90 };

    private int _dragIdx = -1;

    public static bool ShowFor(Window owner, DatabaseService db, string pdfPath, string? password)
    {
        BankStatementParser.PdfLayoutSnapshot snap;
        try { snap = BankStatementParser.ReadPdfLayout(pdfPath, password); }
        catch (Exception ex)
        {
            MessageBox.Show(owner, $"The PDF could not be opened: {ex.Message}", "Teach Columns", MessageBoxButton.OK, MessageBoxImage.Error);
            return false;
        }
        if (snap.Pages.Count == 0 || snap.Pages.All(p => p.Words.Count == 0))
        {
            MessageBox.Show(owner, "This PDF has no readable text (a scanned image), so there are no columns to mark. Please download the digital PDF or Excel/CSV from netbanking.",
                "Teach Columns", MessageBoxButton.OK, MessageBoxImage.Warning);
            return false;
        }
        var w = new TeachLayoutWindow(db, pdfPath, password, snap) { Owner = owner };
        w.ShowDialog();
        return w._saved;
    }

    private TeachLayoutWindow(DatabaseService db, string path, string? pwd, BankStatementParser.PdfLayoutSnapshot snap)
    {
        _db = db; _path = path; _pwd = pwd; _snap = snap;
        Title = $"🧩 Teach Columns — {Path.GetFileName(path)}";
        Width = 1180; Height = 900;
        WindowStartupLocation = WindowStartupLocation.CenterOwner;
        Background = (Brush)Application.Current.Resources["AppBg"];
        Foreground = (Brush)Application.Current.Resources["InkBrush"];

        _pageIdx = Math.Clamp(snap.SuggestedPageIndex, 0, snap.Pages.Count - 1);
        LoadSuggestion(_pageIdx);

        var root = new DockPanel { Margin = new Thickness(12) };

        // ---- top: instructions + page navigation
        var top = new StackPanel();
        top.Children.Add(new TextBlock
        {
            TextWrapping = TextWrapping.Wrap, FontSize = 12.5, Margin = new Thickness(0, 0, 0, 8),
            Text = "1) Go to ANY page that shows the transaction table — it does not have to be the first page (cover / summary pages are fine to skip).\n"
                 + "2) Red lines are column dividers: drag to move • click on the page to add one • right-click a divider to remove it. "
                 + "Put a divider on the LEFT and RIGHT edge of the table too.\n"
                 + "3) Choose what each column is in the boxes above the page (columns you don't need: '— ignore —').\n"
                 + "4) Click 'Test' — the layout can be saved only when every row is proven by the running balance. "
                 + "It then applies to all pages, including pages without headings."
        });
        var nav = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 6) };
        var prev = new Button { Content = "◀ Prev page", Height = 28, Padding = new Thickness(10, 0, 10, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var next = new Button { Content = "Next page ▶", Height = 28, Padding = new Thickness(10, 0, 10, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        var reset = new Button { Content = "↺ Detected columns", Height = 28, Padding = new Thickness(10, 0, 10, 0), Margin = new Thickness(16, 0, 0, 0), Style = (Style)Application.Current.Resources["SecBtn"],
            ToolTip = "Replace the dividers with the columns the app detected on this page" };
        prev.Click += (_, _) => { if (_pageIdx > 0) { _pageIdx--; Redraw(); } };
        next.Click += (_, _) => { if (_pageIdx < _snap.Pages.Count - 1) { _pageIdx++; Redraw(); } };
        reset.Click += (_, _) => { LoadSuggestion(_pageIdx); Redraw(); };
        nav.Children.Add(prev); nav.Children.Add(_pageLbl); nav.Children.Add(next); nav.Children.Add(reset);
        top.Children.Add(nav);
        DockPanel.SetDock(top, Dock.Top);
        root.Children.Add(top);

        // ---- bottom: test result, preview, name, buttons, saved layouts
        var bottom = new StackPanel { Margin = new Thickness(0, 8, 0, 0) };
        bottom.Children.Add(_result);
        _preview.Columns.Add(new DataGridTextColumn { Header = "Date", Binding = new System.Windows.Data.Binding("DisplayDate"), Width = 95 });
        _preview.Columns.Add(new DataGridTextColumn { Header = "Dr (₹)", Binding = new System.Windows.Data.Binding("Credit") { Converter = new IndianAmountConverter(), ConverterParameter = "blankZero" }, Width = 100 });
        _preview.Columns.Add(new DataGridTextColumn { Header = "Cr (₹)", Binding = new System.Windows.Data.Binding("Debit") { Converter = new IndianAmountConverter(), ConverterParameter = "blankZero" }, Width = 100 });
        _preview.Columns.Add(new DataGridTextColumn { Header = "Balance", Binding = new System.Windows.Data.Binding("Balance") { Converter = new IndianAmountConverter() }, Width = 115 });
        _preview.Columns.Add(new DataGridTextColumn { Header = "Description", Binding = new System.Windows.Data.Binding("Narration"), Width = new DataGridLength(1, DataGridLengthUnitType.Star) });
        _preview.Columns.Add(new DataGridTextColumn { Header = "Note", Binding = new System.Windows.Data.Binding("BalanceBreakNote"), Width = 180 });
        bottom.Children.Add(_preview);

        var actions = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 8, 0, 0) };
        actions.Children.Add(new TextBlock { Text = "Layout name:", VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(0, 0, 6, 0) });
        var bankLbl = _snap.Bank.StartsWith("Scheduled", StringComparison.OrdinalIgnoreCase) ? "Bank" : _snap.Bank;
        _name.Text = $"{bankLbl} – {Path.GetFileNameWithoutExtension(path)}";
        actions.Children.Add(_name);
        var test = new Button { Content = "▶ Test", Height = 30, Padding = new Thickness(16, 0, 16, 0), Margin = new Thickness(10, 0, 8, 0),
            Background = new SolidColorBrush(Color.FromRgb(29, 78, 216)), Foreground = Brushes.White, FontWeight = FontWeights.Bold, BorderThickness = new Thickness(0) };
        test.Click += async (_, _) => await RunTestAsync(test);
        _btnSave.Background = new SolidColorBrush(Color.FromRgb(5, 150, 105));
        _btnSave.Foreground = Brushes.White;
        _btnSave.BorderThickness = new Thickness(0);
        _btnSave.Click += (_, _) => Save();
        var close = new Button { Content = "Close", Height = 30, Padding = new Thickness(14, 0, 14, 0), Margin = new Thickness(8, 0, 0, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        close.Click += (_, _) => Close();
        actions.Children.Add(test); actions.Children.Add(_btnSave); actions.Children.Add(close);
        bottom.Children.Add(actions);

        var savedHdr = new DockPanel { Margin = new Thickness(0, 10, 0, 2) };
        var del = new Button { Content = "🗑 Delete selected layout", Height = 26, Padding = new Thickness(10, 0, 10, 0), Style = (Style)Application.Current.Resources["SecBtn"] };
        del.Click += (_, _) => DeleteSelected();
        DockPanel.SetDock(del, Dock.Right);
        savedHdr.Children.Add(del);
        savedHdr.Children.Add(new TextBlock { Text = "Saved layouts (shared by every PC):", FontWeight = FontWeights.SemiBold, VerticalAlignment = VerticalAlignment.Center });
        bottom.Children.Add(savedHdr);
        bottom.Children.Add(_savedList);
        DockPanel.SetDock(bottom, Dock.Bottom);
        root.Children.Add(bottom);

        // ---- centre: role boxes + the page, scrolling together
        var stack = new StackPanel();
        stack.Children.Add(_roleBar);
        stack.Children.Add(new Border { BorderBrush = Brushes.Gray, BorderThickness = new Thickness(1), Child = _page, HorizontalAlignment = HorizontalAlignment.Left });
        root.Children.Add(new ScrollViewer { HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, VerticalScrollBarVisibility = ScrollBarVisibility.Auto, Content = stack });

        _page.MouseLeftButtonDown += PageMouseDown;
        _page.MouseMove += PageMouseMove;
        _page.MouseLeftButtonUp += (_, _) => { if (_dragIdx >= 0) { _dragIdx = -1; _page.ReleaseMouseCapture(); Redraw(); } };

        Content = root;
        RefreshSavedList();
        Redraw();
    }

    private BankStatementParser.PdfPageSnapshot Pg => _snap.Pages[_pageIdx];

    private void LoadSuggestion(int pageIdx)
    {
        var p = _snap.Pages[pageIdx];
        if (p.SuggestedEdges.Count >= 2 && p.SuggestedRoles.Count == p.SuggestedEdges.Count - 1)
        {
            _fr = p.SuggestedEdges.Select(x => x / p.Width).ToList();
            _roles = [.. p.SuggestedRoles];
        }
        else if (p.Words.Count > 0)
        {
            _fr = [Math.Max(0, p.Words.Min(w => w.X) - 2) / p.Width, Math.Min(p.Width, p.Words.Max(w => w.X + w.W) + 2) / p.Width];
            _roles = ["ignore"];
        }
        else
        {
            _fr = [0.05, 0.95];
            _roles = ["ignore"];
        }
        Invalidate();
    }

    private void Invalidate()
    {
        _lastTested = null;
        _lastTestProven = _lastTestUnprovable = false;
        _btnSave.IsEnabled = false;
    }

    // ------------------------------------------------------------------ drawing
    private void Redraw()
    {
        var p = Pg;
        _pageLbl.Text = $"Page {p.Number} of {_snap.Pages.Count}" + (p.DatedLineCount > 0 ? $"  ({p.DatedLineCount} dated lines)" : "  (no transactions on this page)");
        double w = p.Width * S, h = p.Height * S;
        _page.Width = w; _page.Height = h; _roleBar.Width = w;
        _page.Children.Clear(); _roleBar.Children.Clear();

        // column shading by role
        for (int c = 0; c < _roles.Count; c++)
        {
            var col = RoleInfo.FirstOrDefault(r => r.role == _roles[c]).color;
            double x1 = _fr[c] * w, x2 = _fr[c + 1] * w;
            var rect = new Rectangle { Width = Math.Max(1, x2 - x1), Height = h, Fill = new SolidColorBrush(col), IsHitTestVisible = false };
            Canvas.SetLeft(rect, x1); _page.Children.Add(rect);
        }
        // the words, where they are on the page
        foreach (var wd in p.Words)
        {
            var tb = new TextBlock { Text = wd.Text, FontSize = Math.Max(5, wd.H * S * 0.82), Foreground = Brushes.Black, IsHitTestVisible = false };
            Canvas.SetLeft(tb, wd.X * S); Canvas.SetTop(tb, wd.Y * S - 1); _page.Children.Add(tb);
        }
        // dividers
        for (int i = 0; i < _fr.Count; i++)
        {
            int idx = i;
            var line = new Rectangle { Width = 3, Height = h, Fill = Brushes.Red, Opacity = 0.75, Cursor = Cursors.SizeWE, Tag = i,
                ToolTip = "Drag to move • right-click to remove" };
            Canvas.SetLeft(line, _fr[i] * w - 1.5);
            line.MouseLeftButtonDown += (s, e) => { _dragIdx = idx; _page.CaptureMouse(); e.Handled = true; };
            line.MouseRightButtonDown += (s, e) => { RemoveDivider(idx); e.Handled = true; };
            _page.Children.Add(line);
        }
        // a role box above each column
        var labels = RoleInfo.Select(r => r.label).ToList();
        for (int c = 0; c < _roles.Count; c++)
        {
            int col = c;
            double x1 = _fr[c] * w, x2 = _fr[c + 1] * w;
            var cb = new ComboBox
            {
                ItemsSource = labels, Width = Math.Max(36, x2 - x1 - 4), Height = 26, FontSize = 11,
                SelectedIndex = Math.Max(0, Array.FindIndex(RoleInfo, r => r.role == _roles[c])),
                ToolTip = "What is in this column?"
            };
            cb.SelectionChanged += (_, _) =>
            {
                if (cb.SelectedIndex < 0) return;
                _roles[col] = RoleInfo[cb.SelectedIndex].role;
                Invalidate();
                Dispatcher.BeginInvoke(new Action(Redraw));
            };
            Canvas.SetLeft(cb, x1 + 2); _roleBar.Children.Add(cb);
        }
    }

    private void PageMouseDown(object sender, MouseButtonEventArgs e)
    {
        // a click on the page (not on a divider) adds a divider there
        double f = e.GetPosition(_page).X / (Pg.Width * S);
        if (_fr.Any(x => Math.Abs(x - f) * Pg.Width < 3)) return;
        int c = _fr.FindIndex(x => x > f);
        if (c < 0) { _fr.Add(f); _roles.Add("ignore"); }                // right of the table: new last column
        else if (c == 0) { _fr.Insert(0, f); _roles.Insert(0, "ignore"); } // left of the table: new first column
        else { _fr.Insert(c, f); _roles.Insert(c, "ignore"); }           // split column c-1: the right part starts as "ignore"
        Invalidate();
        Redraw();
    }

    private void PageMouseMove(object sender, MouseEventArgs e)
    {
        if (_dragIdx < 0 || e.LeftButton != MouseButtonState.Pressed) return;
        double f = e.GetPosition(_page).X / (Pg.Width * S);
        double lo = _dragIdx > 0 ? _fr[_dragIdx - 1] + 4 / Pg.Width : 0;
        double hi = _dragIdx < _fr.Count - 1 ? _fr[_dragIdx + 1] - 4 / Pg.Width : 1;
        _fr[_dragIdx] = Math.Clamp(f, lo, hi);
        Invalidate();
        // move just the divider while dragging (full redraw on release)
        foreach (var r in _page.Children.OfType<Rectangle>().Where(r => r.Tag is int t && t == _dragIdx))
            Canvas.SetLeft(r, _fr[_dragIdx] * Pg.Width * S - 1.5);
    }

    private void RemoveDivider(int i)
    {
        if (_fr.Count <= 2) return;
        if (i == 0) { _fr.RemoveAt(0); _roles.RemoveAt(0); }
        else if (i == _fr.Count - 1) { _fr.RemoveAt(i); _roles.RemoveAt(_roles.Count - 1); }
        else
        {
            // merge the two columns around the divider; keep the named role
            var keep = _roles[i - 1] != "ignore" ? _roles[i - 1] : _roles[i];
            _fr.RemoveAt(i);
            _roles.RemoveAt(i);
            _roles[i - 1] = keep;
        }
        Invalidate();
        Redraw();
    }

    // ------------------------------------------------------------------ test / save
    private string? Validate()
    {
        var named = _roles.Where(r => r != "ignore").ToList();
        if (!named.Contains("date")) return "Mark the transaction DATE column.";
        bool split = named.Contains("debit") && named.Contains("credit");
        if (!split && !named.Contains("amount")) return "Mark both the DEBIT and CREDIT columns (or a single AMOUNT column).";
        var dup = named.GroupBy(r => r).FirstOrDefault(g => g.Count() > 1);
        if (dup != null) return $"'{RoleInfo.First(r => r.role == dup.Key).label}' is marked on more than one column.";
        if (!named.Contains("balance")) return null; // allowed, but it cannot be proven — handled after the test
        return null;
    }

    private LayoutTemplate BuildTemplate() => new()
    {
        Name = _name.Text.Trim(),
        Bank = _snap.Bank.StartsWith("Scheduled", StringComparison.OrdinalIgnoreCase) ? "" : _snap.Bank,
        Boundaries = [.. _fr],
        Roles = [.. _roles],
        SampleFile = Path.GetFileName(_path)
    };

    private async Task RunTestAsync(Button btn)
    {
        var problem = Validate();
        if (problem != null) { _result.Text = "⚠ " + problem; _result.Foreground = Brushes.DarkRed; return; }
        var t = BuildTemplate();
        btn.IsEnabled = false;
        _result.Text = "Reading every page with these columns…"; _result.Foreground = (Brush)Application.Current.Resources["InkBrush"];
        try
        {
            var res = await Task.Run(() => BankStatementParser.ParsePdfWithTemplate(_path, _pwd, t));
            var b = res.Balances;
            _preview.ItemsSource = res.Transactions;
            var head = $"{res.Transactions.Count} rows • Dr (receipts) ₹{b.TotalCredit:N2} • Cr (payments) ₹{b.TotalDebit:N2} • "
                     + $"Opening ₹{b.StatementOpening:N2} • Closing ₹{b.StatementClosing:N2}\n";
            _lastTested = t;
            _lastTestProven = res.Transactions.Count > 0 && b.StatementBalanced == true && b.CompletenessIssues.Count == 0
                              && res.Transactions.All(x => !x.HasBalanceBreak);
            _lastTestUnprovable = res.Transactions.Count > 0 && b.StatementBalanced == null && b.CompletenessIssues.Count == 0;
            if (res.Transactions.Count == 0)
            {
                _result.Text = "✗ No transactions found with these columns. Check the DATE column and that the outer dividers enclose the table.";
                _result.Foreground = Brushes.DarkRed;
            }
            else if (_lastTestProven)
            {
                _result.Text = head + "✓ PROVEN — every row agrees with the running balance. You can save this layout.";
                _result.Foreground = Brushes.DarkGreen;
            }
            else if (_lastTestUnprovable)
            {
                _result.Text = head + "⚠ Cannot be proven (no running-balance column, or the first row's Dr/Cr is not stated). "
                             + "Compare the totals with the printed statement before saving.";
                _result.Foreground = Brushes.DarkOrange;
            }
            else
            {
                var why = b.StatementBalanced == false ? $"balances do not reconcile (difference ₹{b.StatementDiff:N2})" : string.Join("; ", b.CompletenessIssues);
                int brk = res.Transactions.Count(x => x.HasBalanceBreak);
                _result.Text = head + $"✗ NOT proven: {why}{(brk > 0 ? $"; {brk} row(s) break the running balance (see 'Note')" : "")}. "
                             + "Adjust the dividers / column names and test again.";
                _result.Foreground = Brushes.DarkRed;
            }
            _btnSave.IsEnabled = _lastTestProven || _lastTestUnprovable;
        }
        catch (Exception ex)
        {
            _result.Text = "✗ " + ex.Message; _result.Foreground = Brushes.DarkRed;
        }
        finally { btn.IsEnabled = true; }
    }

    private void Save()
    {
        if (_lastTested == null) return;
        if (string.IsNullOrWhiteSpace(_name.Text)) { _result.Text = "⚠ Give the layout a name."; return; }
        if (!_lastTestProven && MessageBox.Show(this,
                "This layout could not be PROVEN against a running balance. Save it anyway? Statements read with it will still be checked on every Analyze.",
                "Save Layout", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes)
            return;
        var t = _lastTested;
        t.Name = _name.Text.Trim();
        try
        {
            t.HeaderSignature = BankStatementParser.ComputeHeaderSignature(_path, _pwd, t, Pg.Number);
            if (string.IsNullOrEmpty(t.HeaderSignature))
            {
                // headings may only be printed on another page (often page 1) — look there too
                foreach (var p in _snap.Pages.Where(p => p.Number != Pg.Number && p.DatedLineCount > 0))
                {
                    t.HeaderSignature = BankStatementParser.ComputeHeaderSignature(_path, _pwd, t, p.Number);
                    if (!string.IsNullOrEmpty(t.HeaderSignature)) break;
                }
            }
            _db.SaveLayoutTemplate(t);
            _saved = true;
            MessageBox.Show(this, $"Layout '{t.Name}' saved for every PC.\n\nStatements of this format are now read with it automatically (only when the result is proven by the running balance).",
                "Teach Columns", MessageBoxButton.OK, MessageBoxImage.Information);
            Close();
        }
        catch (Exception ex)
        {
            _result.Text = "✗ Could not save: " + ex.Message; _result.Foreground = Brushes.DarkRed;
        }
    }

    private sealed record SavedItem(LayoutTemplate T)
    {
        public override string ToString() =>
            $"{T.Name}   [{(string.IsNullOrEmpty(T.Bank) ? "any bank" : T.Bank)}]   {T.Roles.Count(r => r != "ignore")} columns   {T.CreatedAt} by {T.CreatedBy}";
    }

    private void RefreshSavedList()
    {
        try { _savedList.ItemsSource = _db.GetLayoutTemplates().Select(t => new SavedItem(t)).ToList(); }
        catch { _savedList.ItemsSource = null; }
    }

    private void DeleteSelected()
    {
        if (_savedList.SelectedItem is not SavedItem it) return;
        if (MessageBox.Show(this, $"Delete saved layout '{it.T.Name}' for every PC?", "Delete Layout", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes)
            return;
        try { _db.DeleteLayoutTemplate(it.T.Id); } catch (Exception ex) { MessageBox.Show(this, ex.Message, "Delete Layout"); }
        RefreshSavedList();
    }
}
