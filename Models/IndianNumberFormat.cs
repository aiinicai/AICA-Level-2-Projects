using System;
using System.Globalization;
using System.Windows.Data;

namespace AutoBankStatementEntry.Models;

/// <summary>
/// Indian digit grouping for every amount shown on screen: 12,34,56,789.00 (lakh / crore) instead of 123,456,789.00.
/// Display only — parsing and the Tally XML stay culture-invariant.
/// </summary>
public static class IndianNumberFormat
{
    /// <summary>The user's own culture (dates, etc. unchanged) with Indian number grouping and '.' as decimal point.</summary>
    public static CultureInfo Create(CultureInfo baseCulture)
    {
        var c = (CultureInfo)baseCulture.Clone();
        var nf = c.NumberFormat;
        nf.NumberGroupSizes = [3, 2];
        nf.CurrencyGroupSizes = [3, 2];
        nf.PercentGroupSizes = [3, 2];
        nf.NumberGroupSeparator = ",";
        nf.CurrencyGroupSeparator = ",";
        nf.PercentGroupSeparator = ",";
        nf.NumberDecimalSeparator = ".";
        nf.CurrencyDecimalSeparator = ".";
        nf.PercentDecimalSeparator = ".";
        nf.CurrencySymbol = "₹";
        nf.NegativeSign = "-";
        return c;
    }

    public static CultureInfo Culture { get; } = Create(CultureInfo.InvariantCulture);

    /// <summary>12,34,567.89</summary>
    public static string Format(decimal value) => value.ToString("#,##0.00", Culture);

    /// <summary>
    /// Makes the whole app (string interpolation such as $"{x:N2}") use Indian grouping.
    /// Keeps the user's date / calendar settings; only the number format changes.
    /// </summary>
    public static void ApplyToCurrentThreadAndDefaults()
    {
        var c = Create(CultureInfo.CurrentCulture);
        CultureInfo.CurrentCulture = c;
        CultureInfo.DefaultThreadCurrentCulture = c;
    }
}

/// <summary>
/// WPF binding converter for amounts. WPF bindings format with the element's Language (en-US by default), not
/// CurrentCulture, so bound amount columns use this converter. ConverterParameter "blankZero" shows 0 as empty.
/// </summary>
public sealed class IndianAmountConverter : IValueConverter
{
    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
    {
        if (value == null) return "";
        decimal d;
        try { d = System.Convert.ToDecimal(value, CultureInfo.InvariantCulture); }
        catch { return value.ToString() ?? ""; }
        if (string.Equals(parameter as string, "blankZero", StringComparison.OrdinalIgnoreCase) && Math.Abs(d) < 0.005m)
            return "";
        return IndianNumberFormat.Format(d);
    }

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
