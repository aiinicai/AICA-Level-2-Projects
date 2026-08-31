using Practice.Database.Entities;

namespace Practice.Database;

internal static class IndiaStateSeed
{
    public static readonly IndiaState[] All =
    [
        State("01", "Jammu and Kashmir", true), State("02", "Himachal Pradesh"),
        State("03", "Punjab"), State("04", "Chandigarh", true), State("05", "Uttarakhand"),
        State("06", "Haryana"), State("07", "Delhi", true), State("08", "Rajasthan"),
        State("09", "Uttar Pradesh"), State("10", "Bihar"), State("11", "Sikkim"),
        State("12", "Arunachal Pradesh"), State("13", "Nagaland"), State("14", "Manipur"),
        State("15", "Mizoram"), State("16", "Tripura"), State("17", "Meghalaya"),
        State("18", "Assam"), State("19", "West Bengal"), State("20", "Jharkhand"),
        State("21", "Odisha"), State("22", "Chhattisgarh"), State("23", "Madhya Pradesh"),
        State("24", "Gujarat"), State("26", "Dadra and Nagar Haveli and Daman and Diu", true),
        State("27", "Maharashtra"), State("29", "Karnataka"), State("30", "Goa"),
        State("31", "Lakshadweep", true), State("32", "Kerala"), State("33", "Tamil Nadu"),
        State("34", "Puducherry", true), State("35", "Andaman and Nicobar Islands", true),
        State("36", "Telangana"), State("37", "Andhra Pradesh"), State("38", "Ladakh", true)
    ];

    private static IndiaState State(string code, string name, bool unionTerritory = false) => new()
    {
        GstCode = code,
        Name = name,
        IsUnionTerritory = unionTerritory,
        IsActive = true
    };
}
