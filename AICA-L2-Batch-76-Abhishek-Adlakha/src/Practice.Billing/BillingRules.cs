namespace Practice.Billing;

public static class BillingRules
{
    public static readonly string[] Frequencies = ["MONTHLY", "QUARTERLY", "HALF_YEARLY", "ANNUALLY", "SPECIFIC_MONTH", "ONE_TIME", "CUSTOM_MONTHS"];
    public static readonly string[] BusinessDayAdjustments = ["NONE", "PREVIOUS", "NEXT"];

    public static IReadOnlyList<string> ValidateSchedule(
        string frequencyCode, DateOnly? anchorDate, int? billingDay, DateOnly? oneTimeDate,
        IReadOnlyCollection<int> months, string businessDayAdjustment)
    {
        var errors = new List<string>();
        if (!Frequencies.Contains(frequencyCode, StringComparer.Ordinal)) errors.Add("Unsupported billing frequency.");
        if (!BusinessDayAdjustments.Contains(businessDayAdjustment, StringComparer.Ordinal)) errors.Add("Unsupported business-day adjustment.");
        if (billingDay is < 1 or > 31) errors.Add("Billing day must be from 1 to 31.");
        if (months.Any(month => month is < 1 or > 12) || months.Count != months.Distinct().Count()) errors.Add("Billing months must be unique values from 1 to 12.");

        if (frequencyCode == "ONE_TIME")
        {
            if (oneTimeDate is null) errors.Add("One-time billing requires a billing date.");
            if (anchorDate is not null || billingDay is not null || months.Count > 0) errors.Add("One-time billing cannot use an anchor, billing day, or selected months.");
        }
        else
        {
            if (anchorDate is null) errors.Add("Recurring billing requires an anchor date.");
            if (billingDay is null) errors.Add("Recurring billing requires a billing day.");
            if (oneTimeDate is not null) errors.Add("Only one-time billing can use a one-time date.");
        }

        if (frequencyCode == "SPECIFIC_MONTH" && months.Count != 1) errors.Add("Specific-month billing requires exactly one month.");
        if (frequencyCode == "CUSTOM_MONTHS" && months.Count == 0) errors.Add("Custom-month billing requires at least one month.");
        if (frequencyCode is not ("SPECIFIC_MONTH" or "CUSTOM_MONTHS") && months.Count > 0) errors.Add("Selected months are only valid for specific or custom-month billing.");
        return errors;
    }

    public static int? IntervalMonths(string frequencyCode) => frequencyCode switch
    {
        "MONTHLY" => 1, "QUARTERLY" => 3, "HALF_YEARLY" => 6, "ANNUALLY" => 12,
        "SPECIFIC_MONTH" or "CUSTOM_MONTHS" => 12, _ => null
    };
}
