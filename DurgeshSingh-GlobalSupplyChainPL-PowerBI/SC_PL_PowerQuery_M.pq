// =====================================================================================
// Global Supply Chain P&L - Power Query (M) - ingestion, validation, transformation
// Target: Power BI Dataflow (recommended) or the semantic model itself (prototype).
// Source: SharePoint Online document library  SC_PL / 01_Inbox  +  SC_PL / 03_Archive
// File naming: SCPL_YYYYMM_vN.xlsx | .csv  (one reporting month per file; Actual + Budget + LY rows)
// Prototype tip: replace SharePoint.Files(...) with Folder.Files("C:\...\SC_PL") to test locally
//                with SCPL_202608_v1_SAMPLE.csv / SC_PL_Prototype_Sample_Data.xlsx.
// =====================================================================================

// ==== [PARAMS] ====
// Parameters (Manage Parameters)
SharePointSite = "https://<tenant>.sharepoint.com/sites/SC-Finance" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
LibraryPath    = "/SC_PL/"                                              meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]

// Mandatory columns - aligned to the template (Accounts | Channel | Accdetail) + filters (Year, Month, Region, Country, BU)
RequiredColumns = {"Year", "Month", "Region", "Country", "OpCo Code", "BU", "SC Function",
                   "Account", "Channel", "AccDetail", "Scenario", "Currency", "Amount"}

// ==== [FUNCTIONS] ====
// fxClean - null-safe trim
fxClean = (v as any) as nullable text => if v = null then null else Text.Trim(Text.From(v))

// fxReadExtract - reads one .xlsx (first sheet) or .csv file and promotes headers
fxReadExtract = (content as binary, fileName as text) as table =>
let
    isCsv    = Text.EndsWith(Text.Lower(fileName), ".csv"),
    raw      = if isCsv
               then Csv.Document(content, [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])
               else Table.SelectRows(Excel.Workbook(content, null, true), each [Kind] = "Sheet"){0}[Data],
    promoted = Table.PromoteHeaders(raw, [PromoteAllScalars = true]),
    names    = Table.TransformColumnNames(promoted, Text.Trim)
in
    names

// fxMissingColumns - list of mandatory columns not present in a file (DQ03)
fxMissingColumns = (t as table) as list => List.Difference(RequiredColumns, Table.ColumnNames(t))

// ==== [STG_FILES] ====
// Stg_Files - one row per candidate file; latest version per period; file-level checks (DQ02, DQ03)
let
    Source      = SharePoint.Files(SharePointSite, [ApiVersion = 15]),
    InScope     = Table.SelectRows(Source, each
                      Text.Contains([Folder Path], LibraryPath & "01_Inbox/")
                   or Text.Contains([Folder Path], LibraryPath & "03_Archive/")),
    AddPeriod   = Table.AddColumn(InScope, "File Period",
                      each try Int64.From(Text.Middle([Name], 5, 6)) otherwise null, Int64.Type),
    AddVersion  = Table.AddColumn(AddPeriod, "File Version",
                      each try Int64.From(Text.BetweenDelimiters([Name], "_v", ".")) otherwise 1, Int64.Type),
    AddNameOK   = Table.AddColumn(AddVersion, "Name Valid", each
                      Text.StartsWith([Name], "SCPL_")
                      and [File Period] <> null
                      and List.Contains({".xlsx", ".csv"}, Text.Lower([Extension])), type logical),
    ValidNames  = Table.SelectRows(AddNameOK, each [Name Valid]),
    // keep only the highest version per reporting month (v2 replaces v1 - auditability kept in Archive)
    Grouped     = Table.Group(ValidNames, {"File Period"},
                      {{"Latest", each Table.First(Table.Sort(_, {{"File Version", Order.Descending}})), type record}}),
    Latest      = Table.FromRecords(Grouped[Latest]),
    AddData     = Table.AddColumn(Latest, "Data", each try fxReadExtract([Content], [Name]) otherwise null),
    AddMissing  = Table.AddColumn(AddData, "Missing Columns", each
                      if [Data] = null then "UNREADABLE FILE" else Text.Combine(fxMissingColumns([Data]), ", "), type text),
    Result      = Table.SelectColumns(AddMissing, {"Name", "Folder Path", "File Period", "File Version", "Date modified", "Data", "Missing Columns"})
in
    Result

// ==== [STG_EXTRACT] ====
// Stg_Extract - combined, cleansed, typed rows from all structurally valid files
let
    Files      = Table.SelectRows(Stg_Files, each [Missing Columns] = ""),
    Keep       = Table.SelectColumns(Files, {"Name", "File Period", "File Version", "Data"}),
    Expanded   = Table.ExpandTableColumn(Keep, "Data", RequiredColumns),
    Cleaned    = Table.TransformColumns(Expanded, {
                     {"Region", fxClean, type nullable text}, {"Country", fxClean, type nullable text},
                     {"OpCo Code", each Text.Upper(fxClean(_) ?? ""), type text},
                     {"BU", fxClean, type nullable text}, {"SC Function", fxClean, type nullable text},
                     {"Account", each Text.Upper(fxClean(_) ?? ""), type text},
                     {"Channel", fxClean, type nullable text}, {"AccDetail", fxClean, type nullable text},
                     {"Scenario", fxClean, type nullable text}, {"Currency", each Text.Upper(fxClean(_) ?? ""), type text}}),
    Typed      = Table.TransformColumns(Cleaned, {
                     {"Year",   each try Int64.From(_) otherwise null, type nullable number},
                     {"Month",  each try Int64.From(_) otherwise null, type nullable number},
                     {"Amount", each try Number.From(_, "en-US") otherwise null, type nullable number}}),
    WithRowNo  = Table.AddIndexColumn(Typed, "Row No", 1, 1, Int64.Type)
in
    WithRowNo

// ==== [DQ_EXCEPTIONS] ====
// DQ_Exceptions - every validation failure, one row per issue (feeds DQ page, approval flow, and fact filter)
let
    S              = Stg_Extract,
    OpCoList       = List.Buffer(Dim_OpCo[OpCo Code]),
    AccountList    = List.Buffer(Dim_Account[Account Code]),
    FunctionList   = List.Buffer(Dim_SC_Function[SC Function]),
    Mandatory      = {"Year", "Month", "Country", "OpCo Code", "SC Function", "Account", "Scenario", "Currency", "Amount"},
    // ---- row-level rules
    AddIssues = Table.AddColumn(S, "Issues", each
        List.RemoveNulls({
            if List.AnyTrue(List.Transform(Mandatory, (c) => Record.Field(_, c) = null or Record.Field(_, c) = ""))
                then "DQ04|Critical|Mandatory field blank (OpCo / Country / Month / other)" else null,
            if [Year] = null or [Month] = null or [Month] < 1 or [Month] > 12
                then "DQ05|Critical|Invalid year / month" else null,
            if [Year] <> null and [Month] <> null and [Year] * 100 + [Month] <> [File Period]
                then "DQ05|Critical|Row period differs from file period" else null,
            if not List.Contains({"Actual", "Budget", "LY"}, [Scenario])
                then "DQ07|Critical|Invalid scenario '" & ([Scenario] ?? "") & "'" else null,
            if [Currency] <> "USD"
                then "DQ08|Critical|Currency '" & [Currency] & "' is not USD" else null,
            if [Amount] = null
                then "DQ09|Critical|Amount is not numeric" else null,
            if List.Contains({"PURCH_PAIRS", "PROD_PAIRS"}, [Account]) and [Amount] <> null
               and ([Amount] < 0 or Number.Round([Amount]) <> [Amount])
                then "DQ09|Critical|Pairs must be non-negative whole numbers" else null,
            if [OpCo Code] <> "" and not List.Contains(OpCoList, [OpCo Code])
                then "DQ06|High|OpCo not in Dim_OpCo (new OpCo? map it)" else null,
            if [Account] <> "" and not List.Contains(AccountList, [Account])
                then "DQ06|High|Account not in Dim_Account (map it)" else null,
            if [SC Function] <> null and not List.Contains(FunctionList, [SC Function])
                then "DQ06|High|SC Function not in Dim_SC_Function" else null
        })),
    RowIssues  = Table.ExpandListColumn(Table.SelectRows(AddIssues, each List.Count([Issues]) > 0), "Issues"),
    RowSplit   = Table.SplitColumn(RowIssues, "Issues", Splitter.SplitTextByDelimiter("|"), {"Rule ID", "Severity", "Message"}),
    RowOut     = Table.SelectColumns(RowSplit, {"Name", "File Period", "Row No", "OpCo Code", "Account", "Scenario", "Rule ID", "Severity", "Message"}),
    // ---- duplicates (DQ10)
    KeyCols    = {"File Period", "OpCo Code", "SC Function", "Account", "Scenario", "Channel", "AccDetail"},
    Dup        = Table.Group(S, KeyCols, {{"Count", Table.RowCount, Int64.Type}, {"Name", each List.First([Name]), type text}}),
    DupOut     = Table.AddColumn(
                     Table.AddColumn(
                         Table.AddColumn(Table.SelectRows(Dup, each [Count] > 1), "Rule ID", each "DQ10"),
                         "Severity", each "High"),
                     "Message", each "Duplicate key - " & Text.From([Count]) & " rows"),
    // ---- file-level (DQ02 name/format handled by flow; DQ03 missing columns / unreadable here)
    FileOut    = Table.AddColumn(
                     Table.AddColumn(
                         Table.AddColumn(Table.SelectRows(Stg_Files, each [Missing Columns] <> ""), "Rule ID", each "DQ03"),
                         "Severity", each "Critical"),
                     "Message", each "Missing columns: " & [Missing Columns]),
    // ---- completeness (DQ11): active OpCos with no Actual rows for the newest file period
    NewestPeriod = List.Max(S[File Period]),
    LoadedOpCos  = List.Distinct(Table.SelectRows(S, each [File Period] = NewestPeriod and [Scenario] = "Actual")[OpCo Code]),
    MissingOpCos = Table.SelectRows(Dim_OpCo, each [Active] = "Y" and not List.Contains(LoadedOpCos, [OpCo Code])),
    MissOut      = Table.AddColumn(
                       Table.AddColumn(
                           Table.AddColumn(
                               Table.AddColumn(Table.SelectColumns(MissingOpCos, {"OpCo Code"}), "File Period", each NewestPeriod),
                               "Rule ID", each "DQ11"),
                           "Severity", each "High"),
                       "Message", each "Active OpCo has no Actual rows in file"),
    Combined   = Table.Combine({RowOut, DupOut, FileOut, MissOut}),
    WithStatus = Table.AddColumn(Combined, "Status", each "Open", type text),
    Typed      = Table.TransformColumnTypes(WithStatus, {{"Rule ID", type text}, {"Severity", type text}, {"Message", type text}})
in
    Typed

// ==== [FACT] ====
// Fact_SC_PL - only rows without Critical issues, only periods the Administrator has Published
let
    S           = Stg_Extract,
    CriticalRows = Table.SelectRows(DQ_Exceptions, each [Severity] = "Critical" and [Row No] <> null),
    NoCritical  = Table.NestedJoin(S, {"Name", "Row No"}, CriticalRows, {"Name", "Row No"}, "Err", JoinKind.LeftAnti),
    PublishedPeriods = List.Buffer(Table.SelectRows(Publish_Control, each [Status] = "Published")[Period]),
    Published   = Table.SelectRows(NoCritical, each List.Contains(PublishedPeriods, [File Period])),
    AddDate     = Table.AddColumn(Published, "Date Key", each #date([Year], [Month], 1), type date),
    JoinAcc     = Table.NestedJoin(AddDate, {"Account"}, Dim_Account, {"Account Code"}, "Acc", JoinKind.Inner),
    ExpAcc      = Table.ExpandTableColumn(JoinAcc, "Acc", {"Measure Type"}),
    JoinFunc    = Table.NestedJoin(ExpAcc, {"SC Function"}, Dim_SC_Function, {"SC Function"}, "Fn", JoinKind.Inner),
    ExpFunc     = Table.ExpandTableColumn(JoinFunc, "Fn", {"Function Code"}),
    // split value column into USD amount and pairs (template rows PURCH_PAIRS / PROD_PAIRS)
    AddUSD      = Table.AddColumn(ExpFunc, "Amount USD", each if [Measure Type] = "USD" then [Amount] else null, type nullable number),
    AddPairs    = Table.AddColumn(AddUSD, "Volume Pairs", each if [Measure Type] = "Pairs" then [Amount] else null, type nullable number),
    Final       = Table.SelectColumns(AddPairs, {"Date Key", "OpCo Code", "Function Code", "Account", "Scenario",
                                                 "Channel", "AccDetail", "Amount USD", "Volume Pairs", "Name", "File Version"}),
    Renamed     = Table.RenameColumns(Final, {{"Account", "Account Code"}, {"Function Code", "SC Function Code"}, {"Name", "Source File"}})
in
    Renamed

// ==== [PUBLISH_CONTROL] ====
// Publish_Control - SharePoint List maintained by the approval flow (Admin decision is the publication gate)
let
    Source  = SharePoint.Tables(SharePointSite, [ApiVersion = 15]),
    List    = Source{[Title = "SCPL_Publish_Control"]}[Items],
    Keep    = Table.SelectColumns(List, {"Period", "Scenario", "File Name", "Version", "Status", "Approved By", "Approved On"}),
    Typed   = Table.TransformColumnTypes(Keep, {{"Period", Int64.Type}, {"Version", Int64.Type}, {"Approved On", type datetime}})
in
    Typed

// ==== [USER_ACCESS] ====
// User_Access - SharePoint List maintained by the Administrator (drives dynamic RLS; no hard-coded users)
let
    Source  = SharePoint.Tables(SharePointSite, [ApiVersion = 15]),
    List    = Source{[Title = "SCPL_User_Access"]}[Items],
    Keep    = Table.SelectColumns(List, {"User Email", "App Role", "Region", "OpCo Code", "SC Function", "Active", "Valid From", "Valid To"}),
    Clean   = Table.TransformColumns(Keep, {{"User Email", each Text.Lower(Text.Trim(_)), type text},
                                            {"Region", each if _ = null or _ = "" then "ALL" else _, type text},
                                            {"OpCo Code", each if _ = null or _ = "" then "ALL" else Text.Upper(_), type text},
                                            {"SC Function", each if _ = null or _ = "" then "ALL" else _, type text}}),
    Typed   = Table.TransformColumnTypes(Clean, {{"Valid From", type date}, {"Valid To", type date}})
in
    Typed

// ==== [DIM_DATE] ====
// Dim_Date - daily calendar (mark as date table); fact joins on first day of month
let
    StartDate = #date(2024, 1, 1),
    EndDate   = Date.EndOfYear(Date.AddYears(DateTime.Date(DateTime.LocalNow()), 1)),
    Dates     = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),
    T         = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),
    Typed     = Table.TransformColumnTypes(T, {{"Date", type date}}),
    AddYear   = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),
    AddMonth  = Table.AddColumn(AddYear, "Month", each Date.Month([Date]), Int64.Type),
    AddMName  = Table.AddColumn(AddMonth, "Month Name", each Date.MonthName([Date], "en-US"), type text),
    AddMShort = Table.AddColumn(AddMName, "Month Short", each Text.Start(Date.MonthName([Date], "en-US"), 3), type text),
    AddQtr    = Table.AddColumn(AddMShort, "Quarter", each "Q" & Text.From(Date.QuarterOfYear([Date])), type text),
    AddPeriod = Table.AddColumn(AddQtr, "Period", each Date.Year([Date]) * 100 + Date.Month([Date]), Int64.Type)
in
    AddPeriod

// ==== [REFRESH_STAMP] ====
// Refresh_Stamp - "Last Refresh Time" shown on every page (as in template)
let
    Source = #table(type table [#"Refreshed At (UTC)" = datetimezone], {{DateTimeZone.UtcNow()}})
in
    Source
