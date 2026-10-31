namespace Sales360.Domain;

public record Stage(string Name, decimal Allocation, decimal Claimed, decimal Assessed, decimal Previous);
public record Assessment(decimal Cumulative, decimal Previous, decimal Settlement);
public static class Billing
{
    public static readonly string[] Categories = ["Design", "Supervision", "Overtime Claims", "Authority Fees", "Other Services"];
    public static decimal Money(decimal n) => decimal.Round(n, 2, MidpointRounding.AwayFromZero);
    public static Assessment Assess(decimal fee, IReadOnlyList<Stage> stages)
    {
        Require(fee > 0 && stages.Count > 0, "Fee basis and stages are required.");
        Require(stages.Sum(x => x.Allocation) == 100, "Contract allocations must total 100%.");
        foreach (var s in stages)
            Require(s.Allocation >= 0 && s.Claimed is >= 0 and <= 100 && s.Assessed >= s.Previous && s.Previous >= 0 && s.Assessed <= s.Claimed, "Completion must be within 0–100%, assessed <= claimed and >= previously certified.");
        var cumulative = stages.Sum(s => Money(fee * s.Allocation / 100 * s.Assessed / 100));
        var previous = stages.Sum(s => Money(fee * s.Allocation / 100 * s.Previous / 100));
        Require(cumulative > previous, "Certificate must contain a positive new assessment.");
        return new(cumulative, previous, cumulative - previous);
    }
    public static void Require(bool condition, string message) { if (!condition) throw new RuleException(message); }
    public static string NextApproval(string state) => state switch { "Submitted" => "Reviewer 1", "Reviewed 1" => "Reviewer 2", "Reviewed 2" => "Approver", _ => throw new RuleException("No approval is available in this state.") };
    public static void Allocate(decimal cash, decimal open, decimal amount) => Require(amount > 0 && amount <= cash && amount <= open, "Allocation exceeds available cash or invoice balance.");
    public static int AgingBucket(DateOnly due, DateOnly asOf) { var days = asOf.DayNumber - due.DayNumber; return days <= 0 ? 0 : days <= 30 ? 1 : days <= 60 ? 2 : days <= 90 ? 3 : 4; }
    public static string Words(decimal amount)
    {
        string Integers(long n) { string[] small = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"]; string[] tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]; return n < 20 ? small[n] : n < 100 ? tens[n / 10] + (n % 10 > 0 ? " " + Integers(n % 10) : "") : n < 1000 ? Integers(n / 100) + " Hundred" + (n % 100 > 0 ? " " + Integers(n % 100) : "") : n < 1000000 ? Integers(n / 1000) + " Thousand" + (n % 1000 > 0 ? " " + Integers(n % 1000) : "") : n < 1000000000 ? Integers(n / 1000000) + " Million" + (n % 1000000 > 0 ? " " + Integers(n % 1000000) : "") : Integers(n / 1000000000) + " Billion" + (n % 1000000000 > 0 ? " " + Integers(n % 1000000000) : ""); }
        Require(amount >= 0 && amount < 1000000000000, "Amount outside supported range."); amount = Money(amount);
        return "AED " + Integers((long)amount) + (amount % 1 > 0 ? " and " + Integers((long)(amount % 1 * 100)) + " Fils" : "") + " only.";
    }
}
public class RuleException(string message) : Exception(message);
