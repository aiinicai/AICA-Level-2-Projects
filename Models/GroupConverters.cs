using System.Collections;
using System.Globalization;
using System.Windows.Data;

namespace AutoBankStatementEntry.Models;

/// <summary>Group header text: "14 entries • ₹6,240.00 • ⚠ 3 to check".</summary>
public sealed class GroupSummaryConverter : IMultiValueConverter
{
    public object Convert(object?[] values, Type targetType, object? parameter, CultureInfo culture)
    {
        if (values.Length == 0 || values[0] is not IEnumerable items) return "";
        var rows = items.OfType<BankTransactionRow>().ToList();
        int check = rows.Count(r => r.NeedsReview);
        return $"{rows.Count} entries   •   ₹{IndianNumberFormat.Format(rows.Sum(r => r.Amount))}"
               + (check > 0 ? $"   •   ⚠ {check} to check" : "");
    }

    public object[] ConvertBack(object? value, Type[] targetTypes, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}

/// <summary>A group opens by itself when one of its rows needs a ledger check; the others start folded.</summary>
public sealed class GroupOpenConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture) =>
        value is IEnumerable items && items.OfType<BankTransactionRow>().Any(r => r.NeedsReview);

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
