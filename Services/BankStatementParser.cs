using System.Globalization;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using AutoBankStatementEntry.Models;
using ExcelDataReader;
using UglyToad.PdfPig;

namespace AutoBankStatementEntry.Services;

public static class BankStatementParser
{
    // Bank name keywords are matched as whole words; the 4-letter codes are matched ONLY as a full IFSC
    // (e.g. "SBIN0001234"). Plain substring matching of codes such as "sury", "ratn" or "sibl" used to
    // misdetect banks from names like "Surya" / "Ratnakar" or words like "possible" / "responsible".
    private static readonly (string code, string[] names, string ifsc)[] ScheduledBanks =
    [
        ("SBI", ["state bank of india", "onlinesbi", "sbi"], "SBIN"),
        ("HDFC", ["hdfc bank", "hdfc"], "HDFC"),
        ("ICICI", ["icici bank", "icici"], "ICIC"),
        ("AXIS", ["axis bank", "axisbank", "axis account"], "UTIB"),
        ("BOI", ["bank of india", "starconnect"], "BKID"),
        ("KOTAK", ["kotak mahindra", "kotak"], "KKBK"),
        ("PNB", ["punjab national bank", "pnb"], "PUNB"),
        ("BOB", ["bank of baroda", "bob world"], "BARB"),
        ("CANARA", ["canara bank"], "CNRB"),
        ("UNION", ["union bank of india", "union bank"], "UBIN"),
        ("INDIAN", ["indian bank"], "IDIB"),
        ("CBI", ["central bank of india"], "CBIN"),
        ("IDBI", ["idbi bank", "idbi"], "IBKL"),
        ("INDUSIND", ["indusind bank", "indusind"], "INDB"),
        ("YES", ["yes bank"], "YESB"),
        ("FEDERAL", ["federal bank"], "FDRL"),
        ("IDFC", ["idfc first", "idfc bank"], "IDFB"),
        ("RBL", ["rbl bank", "ratnakar bank"], "RATN"),
        ("BANDHAN", ["bandhan bank"], "BDBL"),
        ("AU", ["au small finance", "au bank"], "AUBL"),
        ("UCO", ["uco bank"], "UCBA"),
        ("IOB", ["indian overseas bank"], "IOBA"),
        ("BOM", ["bank of maharashtra"], "MAHB"),
        ("PSB", ["punjab & sind bank", "punjab and sind bank"], "PSIB"),
        ("SIB", ["south indian bank"], "SIBL"),
        ("KVB", ["karur vysya bank"], "KVBL"),
        ("KARNATAKA", ["karnataka bank"], "KARB"),
        ("CUB", ["city union bank"], "CIUB"),
        ("TMB", ["tamilnad mercantile"], "TMBL"),
        ("CSB", ["csb bank", "catholic syrian bank"], "CSBK"),
        ("DCB", ["dcb bank"], "DCBL"),
        ("DHANLAXMI", ["dhanlaxmi bank"], "DLXB"),
        ("JKB", ["jammu & kashmir bank", "jammu and kashmir bank", "j&k bank"], "JAKA"),
        ("EQUITAS", ["equitas small finance"], "ESFB"),
        ("UJJIVAN", ["ujjivan small finance"], "UJVN"),
        ("JANA", ["jana small finance"], "JSFB"),
        ("SURYODAY", ["suryoday small finance"], "SURY"),
        ("UTKARSH", ["utkarsh small finance"], "UTKS"),
        ("ESAF", ["esaf small finance"], "ESMF"),
        ("SARASWAT", ["saraswat bank", "saraswat co-operative"], "SRCB"),
        ("COSMOS", ["cosmos bank", "cosmos co-operative"], "COSB"),
        ("SVC", ["svc co-operative", "svc bank"], "SVCB"),
        ("SCB", ["standard chartered"], "SCBL"),
        ("HSBC", ["hsbc"], "HSBC"),
        ("DBS", ["dbs bank"], "DBSS"),
        ("CITI", ["citibank"], "CITI"),
        ("DEUTSCHE", ["deutsche bank"], "DEUT"),
    ];

    private static readonly (string code, Regex re)[] BankDetectors = ScheduledBanks
        .SelectMany(b => b.names
            .Select(n => (b.code, new Regex($@"(?<![a-z0-9]){Regex.Escape(n)}(?![a-z0-9])", RegexOptions.IgnoreCase | RegexOptions.Compiled)))
            // IFSC only when printed as the account's own IFSC ("IFSC Code : SBIN0001234"); IFSCs inside narrations belong to the
            // OTHER party of a transfer and used to mislabel the statement's bank.
            .Append((b.code, new Regex($@"ifs(?:c)?\.?(?:\s*code)?\s*[:\-]?\s*{b.ifsc}0[a-z0-9]{{6}}(?![a-z0-9])", RegexOptions.IgnoreCase | RegexOptions.Compiled))))
        .ToArray();

    private static readonly Dictionary<string, string[]> ColumnAliases = new()
    {
        ["sr_no"] = ["s no.", "s no", "s.no.", "s.no", "sr no.", "sr no", "sr. no.", "sr. no", "sr.no.", "sr.no", "sl no.", "sl no", "sl. no.", "sl. no", "serial no", "sno", "sl#", "srl no", "srl.", "srl"],
        ["value_date"] = ["value date", "val date", "value dt", "val dt", "valuedate", "value. date"],
        ["date"] = ["txn date", "txn. date", "txndate", "transaction date", "tran date", "tran. date", "trans date", "trans. date", "date of transaction", "posting date", "post date", "entry date", "value/txn date", "date", "dt"],
        ["narration"] = ["transaction remarks", "transaction particulars", "tran particulars", "transaction details", "txn description", "description/particulars", "description / narration", "narration", "description", "particulars", "particular", "remarks", "remark", "details", "chq/narration"],
        ["ref_no"] = ["ref no./cheque no.", "ref.no./cheque no.", "ref no / cheque no", "ref no/cheque no", "chq / ref number", "chq/ref number", "chq./ref.no.", "chq / ref no.", "chq / ref no", "chq/ref no", "chqno", "cheque/ref no", "cheque number", "chq number", "cheque details", "cheque id", "chq id", "chq.no.", "chq.no", "chequeno.", "chequeno", "cheque no.", "chq. no", "ref.no.", "ref.no", "ref. no", "ref no", "reference no", "reference number", "cheque no", "chq no", "instrument no", "inst no", "inst. no", "utr no", "reference", "utr", "tran id", "transaction id"],
        ["debit"] = ["withdrawl amount", "withdrawl amt", "withdrawls", "withdrawl", "withdrawal amount (inr )", "withdrawal amount (inr)", "withdrawal amount", "withdrawal amt", "withdrawal (dr)", "withdrawal(dr)", "withdrawals", "withdrawal", "debit amount (inr)", "debit amount(inr)", "debit (inr)", "debit(inr)", "debit (rs.)", "debit(rs)", "debit (dr)", "debit(dr)", "debit amt", "debit amount", "amount debited", "debited", "debit", "dr amount", "dr amt", "dr.", "dr"],
        ["credit"] = ["deposit amount (inr )", "deposit amount (inr)", "deposit amount", "deposit amt", "deposit (cr)", "deposit(cr)", "deposits", "deposit", "credit amount (inr)", "credit amount(inr)", "credit (inr)", "credit(inr)", "credit (rs.)", "credit(rs)", "credit (cr)", "credit(cr)", "credit amt", "credit amount", "amount credited", "credited", "credit", "cr amount", "cr amt", "cr.", "cr"],
        ["drcr"] = ["dr/cr", "cr/dr", "dr / cr", "cr / dr", "dr|cr", "debit/credit", "credit/debit", "debit / credit", "credit / debit", "type (dr/cr)", "dr/cr indicator", "cr/dr indicator", "txn type", "type", "indicator", "d/c", "c/d"],
        ["balance"] = ["closing balance", "running balance", "available balance", "balance (inr )", "balance (inr)", "balance(inr)", "balance (rs.)", "balance(rs)", "running bal", "closing bal", "balance", "bal.", "bal"],
        ["amount"] = ["amount (inr)", "amount(inr)", "amount (rs.)", "txn amount", "transaction amount", "amount", "amt"],
        // SBI "Branch Code" (16103 / 99922 / 4430): a column of its own, so 5-digit codes are never read as Debit amounts
        ["branch"] = ["branch code", "branchcode", "br code", "br. code", "br.code"],
    };

    private static readonly string[] CanonicalRoles =
        ["date", "value_date", "narration", "ref_no", "debit", "credit", "amount", "drcr", "balance"];

    private static readonly Dictionary<string, int> CanonicalColMap =
        CanonicalRoles.Select((r, i) => (r, i)).ToDictionary(x => x.r, x => x.i);

    private static readonly string[] DateFormats =
    [
        "dd/MM/yyyy", "d/M/yyyy", "d/MM/yyyy", "dd/M/yyyy",
        "dd-MM-yyyy", "d-M-yyyy", "d-MM-yyyy", "dd-M-yyyy",
        "dd.MM.yyyy", "d.M.yyyy", "d.MM.yyyy", "dd.M.yyyy",
        "dd/MM/yy", "d/M/yy", "dd-MM-yy", "d-M-yy", "dd.MM.yy",
        "dd-MMM-yyyy", "d-MMM-yyyy", "dd MMM yyyy", "d MMM yyyy",
        "dd/MMM/yyyy", "d/MMM/yyyy", "dd-MMM-yy", "d-MMM-yy",
        "dd MMM yy", "d MMM yy", "dd/MMM/yy", "d/MMM/yy",
        "dd-MMMM-yyyy", "d-MMMM-yyyy", "dd MMMM yyyy", "d MMMM yyyy",
        "MMM dd, yyyy", "MMM d, yyyy", "dd MMM, yyyy", "d MMM, yyyy", "ddMMMyyyy",
        "yyyy-MM-dd", "yyyy/MM/dd", "yyyyMMdd"
    ];

    private static readonly Regex SkipRowRegex = new(
        @"^(opening\s+bal|closing\s+bal|brought\s+forward|carried\s+forward|b/f\b|c/f\b|statement\s+summary|page\s+(?:no\.?\s*)?\d+)",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex FooterNoiseRegex = new(
        @"(^\s*page\s+(?:no\.?\s*)?\d+|^\s*page\s+of\b|^\s*(?:grand\s+|sub[\-\s]*)?total\b|(?:this\s+is\s+(?:a|an)\s+)?auto[\-\s]*generated\s+statement|(?:this\s+is\s+(?:a|an)\s+)?computer\s+generated|(?:this\s+is\s+(?:a|an)\s+)?system\s+generated|end\s+of\s+statement|statement\s+summary|account\s+summary|disclaimer|registered\s+office|corporate\s+office|toll[\-\s]*free|abbreviations\s+used|legends?\s*:|for\s+any\s+discrepancy|please\s+examine\s+your\s+statement|please\s+review\s+the\s+information|inform\s+the\s+bank\s+immediately|call\s+us\s+at|follow\s+us\s+on|customer\s+care\s*(?:no|number|email|helpline|:))",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex SerialTokenRe = new(@"^\d{1,5}\.?$", RegexOptions.Compiled);
    private static readonly Regex FullDateTokenRe = new(@"^(\d{1,2}[/\-.](\d{1,2}|[A-Za-z]{3,9})[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})$", RegexOptions.Compiled);
    private static readonly Regex TwoDigitRe = new(@"^\d{1,2}$", RegexOptions.Compiled);
    private static readonly Regex Year4Re = new(@"^(19|20)\d{2}$", RegexOptions.Compiled);
    private static readonly Regex MoneyOrDashRe = new(@"^[\(\₹\-]?(?:\d{1,3}(?:,\d{2,3})*|\d+)(?:\.\d{0,2})?[\-\)]?(?:\s*\(?(?:Dr|Cr|DR|CR)\.?\)?)?$", RegexOptions.Compiled);
    private static readonly Regex MoneyDecimalRe = new(@"^\-?(?:\d{1,3}(?:,\d{2,3})*|\d+)\.\d{2}\-?$", RegexOptions.Compiled);
    private static readonly Regex MultiSpaceRe = new(@"\s+", RegexOptions.Compiled);
    private static readonly Regex TimeSuffixRe = new(@"\s+\d{1,2}:\d{2}(:\d{2})?(\s*[APap][Mm])?$", RegexOptions.Compiled);
    private static readonly Regex EmbeddedDateRe = new(@"\b(\d{1,2}[/\-.\s](?:\d{1,2}|[A-Za-z]{3,9})[/\-.\s]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})\b", RegexOptions.Compiled);
    // Letter-boundaries (not \b) so "1,250.00Dr" / "82,000.00(Cr)" / "500.00 DR" are all recognised.
    private static readonly Regex DrWordRe = new(@"(?<![a-z])(dr|debit)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CrWordRe = new(@"(?<![a-z])(cr|credit)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    // First number in a cell; "Rs.1,000.00" / "INR 1,000.00" / "₹ 1,000" must give 1000 (the old [^0-9.] strip turned "Rs. 1,000.00" into ".1000.00" = unparseable = row silently dropped)
    private static readonly Regex AmountNumberRe = new(@"\d[\d,]*(?:\.\d+)?", RegexOptions.Compiled);
    private static readonly Regex PlainOaDateRe = new(@"^\d{5}(?:\.\d+)?$", RegexOptions.Compiled);
    private static readonly Regex IsoDateTimeRe = new(@"^(\d{4}-\d{2}-\d{2})[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+\-]\d{2}:?\d{2})?$", RegexOptions.Compiled);
    private static readonly Regex RefExtractRe = new(@"\b([A-Z]{4}[A-Z0-9]{12,18}|[0-9]{12})\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex IndicatorHeaderRe = new(@"(?:^|\s)\(?(?:cr|dr)\s*/\s*(?:cr|dr)\)?\.?$", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex LoneDashRe = new(@"(?<=^|\s)[-–—](?=\s|$)", RegexOptions.Compiled);
    private static readonly Regex TimeTokenRe = new(@"^(\d{1,2}:\d{2}(:\d{2})?|[AaPp]\.?[Mm]\.?)$", RegexOptions.Compiled);
    private static readonly Regex PayModeUpiRe = new(@"(?<![a-z])upi(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PayModeNeftRe = new(@"(?<![a-z])neft(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PayModeRtgsRe = new(@"(?<![a-z])rtgs(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PayModeImpsRe = new(@"(?<![a-z])imps(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PayModeCashRe = new(@"(?<![a-z])(atm|atw|nfs|nwd|eaw|cwdr|cdm|cash)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PayModeChqRe = new(@"(?<![a-z])(chq|cheque|clg|clearing)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly HashSet<string> MonthWords = new(StringComparer.OrdinalIgnoreCase)
    {
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
        "january", "february", "march", "april", "june", "july", "august", "september", "october", "november", "december"
    };

    public static async Task<ParsedStatementResult> ParseAsync(string filePath, string? filePassword = null, IReadOnlyList<LayoutTemplate>? savedLayouts = null)
    {
        Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
        var ext = Path.GetExtension(filePath).ToLowerInvariant();
        var fileName = Path.GetFileName(filePath);

        if (ext is ".xlsx" or ".xlsm" or ".xls" or ".csv")
            return await Task.Run(() => ParseExcelOrCsv(filePath, fileName, ext, filePassword));

        if (ext == ".pdf")
            return await Task.Run(() =>
            {
                ParsedStatementResult auto;
                InvalidOperationException? autoError = null;
                try { auto = ParsePdf(filePath, fileName, filePassword); }
                catch (InvalidOperationException ex) when (savedLayouts is { Count: > 0 } && !ex.Message.Contains("password", StringComparison.OrdinalIgnoreCase))
                {
                    // nothing readable automatically — a saved layout may still read it
                    autoError = ex;
                    auto = new ParsedStatementResult { SourceFile = fileName, ExtractionMethod = "Digital PDF (not understood)" };
                }
                auto.SourcePath = filePath;
                var res = savedLayouts is { Count: > 0 } ? ChooseWithTemplates(filePath, fileName, filePassword, auto, savedLayouts) : auto;
                if (res.Transactions.Count == 0 && autoError != null) throw autoError;
                return res;
            });

        throw new InvalidOperationException($"Unsupported file format '{ext}'. Please upload a digital PDF, XLSX, XLS, or CSV bank statement downloaded from netbanking.");
    }

    private static List<List<string>> ParseHtmlOrDelimitedFallback(string path)
    {
        var text = File.ReadAllText(path, Encoding.UTF8);
        var rows = new List<List<string>>();

        // Case 1: HTML <table> disguised as .xls (very common in SBI, BOI, PNB, Canara netbanking exports)
        if (Regex.IsMatch(text, @"<tr(?=[\s>])", RegexOptions.IgnoreCase) && Regex.IsMatch(text, @"<t[dh](?=[\s>])", RegexOptions.IgnoreCase))
        {
            // Drop scripts / styles so their text never becomes cells
            text = Regex.Replace(text, @"<(script|style)\b.*?</\1\s*>", " ", RegexOptions.IgnoreCase | RegexOptions.Singleline);
            int tblIdx = text.IndexOf("<table", StringComparison.OrdinalIgnoreCase);
            if (tblIdx > 0)
            {
                var preHtml = Regex.Replace(text[..tblIdx], @"<[^>]+>", " ");
                preHtml = MultiSpaceRe.Replace(WebUtility.HtmlDecode(preHtml), " ").Trim();
                if (!string.IsNullOrWhiteSpace(preHtml))
                    rows.Add([preHtml]);
            }
            // Split on <tr ...> openings instead of requiring </tr> / </td>: many netbanking exports omit closing tags.
            var trParts = Regex.Split(text, @"<tr(?=[\s>])[^>]*>", RegexOptions.IgnoreCase);
            for (int p = 1; p < trParts.Length; p++)
            {
                var rowHtml = trParts[p];
                int endTbl = rowHtml.IndexOf("</table", StringComparison.OrdinalIgnoreCase);
                if (endTbl >= 0) rowHtml = rowHtml[..endTbl];
                // Split yields: [beforeFirstCell, attrs1, content1, attrs2, content2, ...]
                var cellParts = Regex.Split(rowHtml, @"<t[dh](?=[\s>])([^>]*)>", RegexOptions.IgnoreCase);
                var cells = new List<string>();
                for (int c = 1; c + 1 < cellParts.Length; c += 2)
                {
                    var clean = Regex.Replace(cellParts[c + 1], @"<[^>]+>", " ");
                    clean = WebUtility.HtmlDecode(clean).Replace('\u00A0', ' ');
                    cells.Add(MultiSpaceRe.Replace(clean, " ").Trim());
                    // Expand colspan so header and data columns stay aligned
                    var cs = Regex.Match(cellParts[c], @"colspan\s*=\s*[""']?(\d+)", RegexOptions.IgnoreCase);
                    if (cs.Success && int.TryParse(cs.Groups[1].Value, out int span) && span > 1 && span <= 50)
                        for (int k = 1; k < span; k++) cells.Add("");
                }
                if (cells.Count > 0 && cells.Any(x => x.Length > 0)) rows.Add(cells);
            }
            if (rows.Count > 0) return rows;
        }

        // Case 2: Tab-separated (SBI .xls!) or Comma-separated text file
        var lines = text.Split(["\r\n", "\n", "\r"], StringSplitOptions.None);
        int tabCount = lines.Take(50).Sum(l => l.Count(c => c == '\t'));
        int commaCount = lines.Take(50).Sum(l => l.Count(c => c == ','));
        char sep = tabCount >= Math.Max(5, commaCount / 2) ? '\t' : ',';

        foreach (var line in lines)
        {
            if (string.IsNullOrWhiteSpace(line)) continue;
            if (sep == '\t')
            {
                rows.Add(line.Split('\t').Select(c => c.Trim().Trim('"')).ToList());
            }
            else
            {
                var cells = new List<string>();
                var sb = new StringBuilder();
                bool inQ = false;
                foreach (char ch in line)
                {
                    if (ch == '"') inQ = !inQ;
                    else if (ch == ',' && !inQ) { cells.Add(sb.ToString().Trim()); sb.Clear(); }
                    else sb.Append(ch);
                }
                cells.Add(sb.ToString().Trim());
                rows.Add(cells);
            }
        }
        return rows;
    }

    private static List<List<string>> NormalizeRowsToCanonical(List<List<string>> rows, Dictionary<string, int> colMap)
    {
        var result = new List<List<string>>(rows.Count);
        int balCanon = CanonicalColMap["balance"];
        bool hasBalDrCr = colMap.TryGetValue("balance_drcr", out int balDrCrIdx);
        foreach (var r in rows)
        {
            var canon = new List<string>(CanonicalRoles.Length);
            foreach (var role in CanonicalRoles)
            {
                canon.Add(colMap.TryGetValue(role, out int idx) && idx < r.Count ? (r[idx] ?? "").Trim() : "");
            }
            // Fold a separate balance-side "Dr/Cr" indicator into the balance cell so overdraft (Dr) balances keep their sign
            if (hasBalDrCr && balDrCrIdx < r.Count && !string.IsNullOrWhiteSpace(r[balDrCrIdx]) && !string.IsNullOrWhiteSpace(canon[balCanon]))
                canon[balCanon] = $"{canon[balCanon]} {r[balDrCrIdx].Trim()}";
            result.Add(canon);
        }
        return result;
    }

    private static ParsedStatementResult ParseExcelOrCsv(string path, string fileName, string ext, string? password)
    {
        var rawRows = new List<List<string>>();
        string method = "Digital Excel/CSV";
        bool usedFallback = false;

        try
        {
            using var stream = File.Open(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            var config = string.IsNullOrEmpty(password)
                ? null
                : new ExcelReaderConfiguration { Password = password };
            using var reader = ext == ".csv"
                ? ExcelReaderFactory.CreateCsvReader(stream)
                : ExcelReaderFactory.CreateReader(stream, config);

            var ds = reader.AsDataSet();
            var bestTable = ds.Tables.Cast<System.Data.DataTable>()
                .OrderByDescending(t => t.Rows.Count)
                .FirstOrDefault() ?? throw new InvalidOperationException("No readable worksheet found.");

            foreach (System.Data.DataRow dr in bestTable.Rows)
            {
                var row = new List<string>(bestTable.Columns.Count);
                for (int c = 0; c < bestTable.Columns.Count; c++)
                {
                    var val = dr[c];
                    if (val is DateTime dt) row.Add(dt.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture));
                    else if (val is double d) row.Add(Math.Abs(d) >= 1e9 && Math.Abs(d - Math.Round(d)) < 1e-6 ? d.ToString("F0", CultureInfo.InvariantCulture) : d.ToString(CultureInfo.InvariantCulture));
                    else if (val is decimal dec) row.Add(dec.ToString(CultureInfo.InvariantCulture));
                    else if (val is float f) row.Add(f.ToString(CultureInfo.InvariantCulture));
                    else row.Add(val == null || val == DBNull.Value ? "" : val.ToString()!.Trim());
                }
                rawRows.Add(row);
            }
        }
        catch (ExcelDataReader.Exceptions.InvalidPasswordException)
        {
            throw new InvalidOperationException($"'{fileName}' is password-protected or the Excel password is incorrect.");
        }
        catch (Exception ex) when (ex.Message.Contains("password", StringComparison.OrdinalIgnoreCase) || ex.Message.Contains("encrypt", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"'{fileName}' is password-protected or the Excel password is incorrect.");
        }
        catch
        {
            rawRows = ParseHtmlOrDelimitedFallback(path);
            usedFallback = true;
            method = "Digital Text/HTML Statement";
        }

        var (hdrIdx, hdrSkip, colMap) = FindHeaderRow(rawRows);
        if (hdrIdx < 0 && !usedFallback)
        {
            rawRows = ParseHtmlOrDelimitedFallback(path);
            (hdrIdx, hdrSkip, colMap) = FindHeaderRow(rawRows);
            method = "Digital Text/HTML Statement";
        }
        if (hdrIdx < 0)
            throw new InvalidOperationException("Could not locate Date / Debit / Credit / Amount columns in this Excel/CSV file.");

        var fullText = string.Join("\n", rawRows.Select(r => string.Join(" ", r)));
        var headerText = string.Join("\n", rawRows.Take(Math.Max(1, hdrIdx)).Select(r => string.Join(" ", r)));
        var (bank, acc) = DetectBankAndAccount(headerText);
        if (bank == "Scheduled Bank (Auto)" || string.IsNullOrEmpty(acc))
        {
            var (fbBank, fbAcc) = DetectBankAndAccount(fullText.Length > 4000 ? fullText[..4000] : fullText);
            if (bank == "Scheduled Bank (Auto)") bank = fbBank;
            if (string.IsNullOrEmpty(acc)) acc = fbAcc;
        }
        var canonRows = NormalizeRowsToCanonical(rawRows.Skip(hdrIdx + hdrSkip).ToList(), colMap);
        bool hasSeparateDrCr = colMap.ContainsKey("debit") || colMap.ContainsKey("credit");
        var txns = BuildTransactions(canonRows, hasSeparateDrCr, bank, fileName);
        var balances = ExtractBalances(fullText, txns, canonRows);
        ApplyCompletenessChecks(balances, fullText, txns, null);

        return new ParsedStatementResult
        {
            SourceFile = fileName,
            BankDetected = bank,
            AccountNumberDetected = acc,
            ExtractionMethod = method,
            Balances = balances,
            Transactions = txns,
            DiagnosticReport = BuildDiagnosticReport(fileName, bank, method, balances, txns)
        };
    }

    private static ParsedStatementResult ParsePdf(string path, string fileName, string? password)
    {
        var opts = string.IsNullOrEmpty(password)
            ? new ParsingOptions()
            : new ParsingOptions { Password = password };

        var pagesData = new List<(double width, List<List<WordBox>> lines)>();
        var pageTexts = new List<string>();
        var fullTextSb = new StringBuilder();
        var pdfDiag = new StringBuilder();
        var canonicalRows = new List<List<string>>();
        bool anySeparateDrCr = false;

        try
        {
            using var doc = PdfDocument.Open(path, opts);
            // PASS 1 — read every page and work out its columns (header, letter-rebuilt header, or inferred from content).
            var pageInfos = ReadPdfPageLayouts(doc);
            foreach (var pi in pageInfos)
            {
                pageTexts.Add(string.Join("\n", pi.Lines.Select(l => string.Join(" ", l.Select(w => w.Text)))));
                pagesData.Add((pi.Width, pi.Lines));
                // Build the page text from the positioned words (one line per visual line). page.Text concatenates glyphs
                // without reliable spaces/newlines, so "Closing Bal" on a label line ran straight into the NEXT line's numbers.
                foreach (var ln in pi.Lines) fullTextSb.AppendLine(string.Join(" ", ln.Select(w => w.Text)));
            }

            // The best layout found on ANY page (a readable header beats an inferred one). Earlier code fixed the columns
            // from page 1 only, so when page 1's header was unreadable its rows were parsed with a bogus layout and lost.
            var bestHeader = pageInfos.Where(pi => pi.Header != null).OrderByDescending(pi => pi.Header!.Count).Select(pi => pi.Header).FirstOrDefault();
            var bestInferred = pageInfos.Where(pi => pi.Inferred != null).OrderByDescending(pi => pi.Inferred!.Count).Select(pi => pi.Inferred).FirstOrDefault();
            var globalAnchors = bestHeader ?? bestInferred;

            // PASS 2 — parse every page with its own readable header, else its own inferred columns, else the best layout.
            foreach (var pi in pageInfos)
            {
                Dictionary<string, double>? use;
                List<List<WordBox>> dataLines;
                string how;
                if (pi.Header != null)
                {
                    // Never let a weaker repeated header on a later page win over a richer one
                    use = bestHeader != null && bestHeader.Count > pi.Header.Count ? bestHeader : pi.Header;
                    dataLines = pi.Lines.Skip(pi.HeaderIdx + pi.HeaderSpan).ToList();
                    how = pi.Note;
                }
                else if (pi.Inferred != null && bestHeader == null)
                {
                    use = pi.Inferred; dataLines = pi.Lines; how = pi.Note;
                }
                else if (globalAnchors != null)
                {
                    use = globalAnchors; dataLines = pi.Lines;
                    how = $"{(pi.Note.Length > 0 ? pi.Note + "; " : "")}using the columns found on another page";
                }
                else
                {
                    use = null; dataLines = []; how = pi.Note;
                }

                pdfDiag.AppendLine(use != null
                    ? $"  Page {pi.Number}: {how} → columns: {string.Join(", ", use.OrderBy(a => a.Value).Select(a => $"{a.Key}@{a.Value:F0}"))}{(pi.GridXs.Count > 0 ? $" | {pi.GridXs.Count} vertical borders" : "")}"
                    : $"  Page {pi.Number}: {how}; no columns could be determined.");
                if (use == null && pi.Number == 1)
                {
                    pdfDiag.AppendLine("    Words near the top of page 1 (text@x):");
                    foreach (var ln in pi.Lines.Take(30))
                        pdfDiag.AppendLine($"    y={ln[0].Y:F0}: " + string.Join("  ", ln.Select(w => $"{w.Text}@{w.X:F0}")));
                }

                if (use != null && dataLines.Count > 0)
                {
                    // Bordered tables (ICICI "Transactions List", SBI 2025 …) centre multi-line cells on the row; keep each
                    // row's lines together so descriptions never attach to the previous transaction.
                    dataLines = ReorderLinesWithinRowBands(dataLines, pi.RuleYs, use);
                    var (rows, colMap) = LinesToTableRows(dataLines, use, pi.GridXs);
                    if (colMap.ContainsKey("debit") || colMap.ContainsKey("credit"))
                        anySeparateDrCr = true;
                    canonicalRows.AddRange(NormalizeRowsToCanonical(rows, colMap));
                }
            }
        }
        catch (Exception ex) when (ex.Message.Contains("password", StringComparison.OrdinalIgnoreCase) || ex.Message.Contains("encrypt", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"'{fileName}' is password-protected or the PDF password is incorrect.");
        }

        var fullText = fullTextSb.ToString();
        var nonSpaceChars = Regex.Replace(fullText, @"\s+", "").Length;
        var (bank, acc) = DetectBankAndAccount(fullText.Length > 4000 ? fullText[..4000] : fullText);
        var txns = canonicalRows.Count > 0
            ? BuildTransactions(canonicalRows, anySeparateDrCr, bank, fileName)
            : [];
        string pdfMethod = "Digital PDF";

        if (txns.Count == 0 && nonSpaceChars >= 80)
        {
            txns = ParseSpatialFallback(pagesData, bank, fileName);
            pdfMethod = "Digital PDF (layout fallback — verify Dr/Cr)";
        }

        if (txns.Count == 0 && nonSpaceChars >= 80)
        {
            txns = ParseTextFallback(fullText, bank, fileName);
            pdfMethod = "Digital PDF (text fallback — verify Dr/Cr)";
        }

        if (txns.Count == 0 && nonSpaceChars < 80)
            throw new InvalidOperationException($"'{fileName}' appears to be a scanned/photographed image PDF with no digital text. Please download the digital PDF or Excel/CSV statement from your bank's netbanking portal.");

        // A row whose description swallowed half a page means the table layout was NOT understood (this is what a wrongly
        // read statement looks like: 1 row, a 3,000-character narration). Flag it instead of presenting it as normal.
        foreach (var t in txns.Where(t => (t.Narration?.Length ?? 0) > 400))
            t.ParseWarning = (string.IsNullOrEmpty(t.ParseWarning) ? "" : t.ParseWarning + "; ")
                + "Layout not understood: this row's description is unusually long and probably contains several transactions — check against the PDF";
        var pdfBalances = ExtractBalances(fullText, txns, canonicalRows);
        ApplyCompletenessChecks(pdfBalances, fullText, txns, pageTexts);
        return new ParsedStatementResult
        {
            SourceFile = fileName,
            BankDetected = bank,
            AccountNumberDetected = acc,
            ExtractionMethod = pdfMethod,
            Balances = pdfBalances,
            Transactions = txns,
            DiagnosticReport = BuildDiagnosticReport(fileName, bank, pdfMethod, pdfBalances, txns)
                + "\n--- PDF Layout Detection ---\n" + pdfDiag
        };
    }

    /// <summary>Reads every page: words grouped into lines, drawn borders / rules, and the columns found on that page.</summary>
    private static List<PdfPageLayout> ReadPdfPageLayouts(PdfDocument doc)
    {
        var pageInfos = new List<PdfPageLayout>();
        foreach (var page in doc.GetPages())
        {
            var words = page.GetWords()
                .Select(w => new WordBox(
                    w.Text.Trim(),
                    w.BoundingBox.Left,
                    page.Height - w.BoundingBox.Top,
                    w.BoundingBox.Width,
                    w.BoundingBox.Height))
                .Where(w => !string.IsNullOrWhiteSpace(w.Text))
                .ToList();

            var lines = GroupWordsIntoLines(words);

            var gridXs = ExtractVerticalGridLines(page);
            var ruleYs = ExtractHorizontalRules(page);
            var (hdrIdx, hdrSpan, pageAnchors) = DetectColumnAnchors(lines, gridXs);
            string note;
            if (IsStrongHeader(pageAnchors))
            {
                note = $"header at line {hdrIdx + 1} (+{hdrSpan - 1} wrapped)";
            }
            else
            {
                // Coloured / letter-spaced headings: rebuild words from individual glyphs and retry
                try
                {
                    var letterLines = GroupWordsIntoLines(WordsFromLetters(page));
                    var (hIdx2, hSpan2, anchors2) = DetectColumnAnchors(letterLines, gridXs);
                    if (IsStrongHeader(anchors2))
                    {
                        // Use the rebuilt letters ONLY to read the header; transaction rows keep the normal words
                        // (glyph-level grouping can fuse neighbouring cells of data rows).
                        double headerBottom = letterLines.Skip(hIdx2).Take(hSpan2).SelectMany(l => l).Max(w => w.Y + w.H);
                        int firstData = lines.FindIndex(l => l.Average(w => w.Yc) > headerBottom);
                        if (firstData >= 0)
                        {
                            (hdrIdx, hdrSpan, pageAnchors) = (firstData, 0, anchors2);
                        }
                    }
                }
                catch { /* keep the original words */ }
                note = IsStrongHeader(pageAnchors) ? $"header at line {hdrIdx + 1} read after rebuilding words from individual letters" : "";
            }

            Dictionary<string, double>? inferred = null;
            if (!IsStrongHeader(pageAnchors))
            {
                // Header missing, an image, or only a stray "Date … Credit" line matched: infer the columns from the
                // table's CONTENT (dates / long text / amounts / right-most running balance).
                // Try BOTH drawn borders and the empty gaps between columns; borders can be partial (e.g. separators
                // only inside a coloured header row), so keep whichever yields the more complete column set.
                var byBorders = InferAnchorsFromTableContent(lines, gridXs, ruleYs);
                Dictionary<string, double>? byGaps = null;
                var (gapXs, tableLines) = ColumnGapsFromContent(lines);
                if (gapXs.Count >= 5) byGaps = InferAnchorsFromTableContent(tableLines, gapXs, []);
                static int Score(Dictionary<string, double>? a) => a == null ? -1 : a.Count + (a.ContainsKey("balance") ? 3 : 0) + (a.ContainsKey("debit") && a.ContainsKey("credit") ? 2 : 0);
                inferred = Score(byGaps) > Score(byBorders) ? byGaps : byBorders;
                note = inferred != null
                    ? $"header {(hdrIdx >= 0 ? "too weak (" + string.Join(", ", pageAnchors.Keys) + ")" : "not readable")} → columns inferred from table content"
                    : (hdrIdx >= 0 ? $"only a weak header found ({string.Join(", ", pageAnchors.Keys)}) — ignored" : "no header row found");
            }
            pageInfos.Add(new PdfPageLayout(page.Number, lines, gridXs, ruleYs, IsStrongHeader(pageAnchors) ? hdrIdx : -1, hdrSpan,
                IsStrongHeader(pageAnchors) ? pageAnchors : null, inferred, note, page.Width, page.Height));
        }
        return pageInfos;
    }

    private sealed record PdfPageLayout(int Number, List<List<WordBox>> Lines, List<double> GridXs, List<double> RuleYs,
        int HeaderIdx, int HeaderSpan, Dictionary<string, double>? Header, Dictionary<string, double>? Inferred, string Note,
        double Width, double Height);

    private record WordBox(string Text, double X, double Y, double W, double H)
    {
        public double Xc => X + W / 2.0;
        public double Yc => Y + H / 2.0;
        public double X2 => X + W;
    }

    private static List<List<WordBox>> GroupWordsIntoLines(List<WordBox> words)
    {
        if (words.Count == 0) return [];
        var heights = words.Select(w => w.H).OrderBy(h => h).ToList();
        var medH = heights[heights.Count / 2];
        var yTol = Math.Max(3.5, medH * 0.65);

        var sorted = words.OrderBy(w => w.Yc).ThenBy(w => w.X).ToList();
        var lines = new List<List<WordBox>>();
        var lineYs = new List<double>();

        foreach (var w in sorted)
        {
            bool placed = false;
            for (int i = lines.Count - 1; i >= Math.Max(0, lines.Count - 5); i--)
            {
                if (Math.Abs(w.Yc - lineYs[i]) <= yTol)
                {
                    lines[i].Add(w);
                    lineYs[i] = lines[i].Average(x => x.Yc);
                    placed = true;
                    break;
                }
            }
            if (!placed) { lines.Add([w]); lineYs.Add(w.Yc); }
        }
        foreach (var ln in lines) ln.Sort((a, b) => a.X.CompareTo(b.X));
        return lines;
    }

    private static List<(string text, double x1, double x2)> MergeLinePhrases(List<WordBox> line, List<double>? gridXs = null)
    {
        var phrases = new List<(string text, double x1, double x2)>();
        foreach (var w in line.OrderBy(x => x.X))
        {
            // Never merge two header words that a drawn column border separates ("Cr/Dr" | "Transaction Amount")
            bool borderBetween = phrases.Count > 0 && gridXs is { Count: > 0 } && gridXs.Any(g => g > phrases[^1].x2 - 0.5 && g < w.X + 0.5);
            // A "Cr/Dr" / "Dr/Cr" indicator heading is always its own column; never let it swallow "Amount(INR)" next to it
            bool afterIndicator = phrases.Count > 0 && IndicatorHeaderRe.IsMatch(phrases[^1].text);
            if (phrases.Count > 0 && !borderBetween && !afterIndicator && (w.X - phrases[^1].x2) <= Math.Max(6.0, w.H * 1.1))
            {
                var prev = phrases[^1];
                phrases[^1] = ($"{prev.text} {w.Text}", prev.x1, Math.Max(prev.x2, w.X2));
            }
            else phrases.Add((w.Text, w.X, w.X2));
        }
        return phrases;
    }

    private static bool IsSerialToken(string s) =>
        SerialTokenRe.IsMatch(s.Trim());

    private static bool LineStartsWithDate(List<WordBox> line)
    {
        if (line.Count == 0) return false;
        int start = IsSerialToken(line[0].Text) && line.Count >= 2 ? 1 : 0;
        if (ParseIndianDate(line[start].Text) != null) return true;
        if (start + 2 < line.Count && ParseIndianDate($"{line[start].Text} {line[start + 1].Text} {line[start + 2].Text}") != null) return true;
        return false;
    }

    private static (int hdrIdx, int hdrSpan, Dictionary<string, double> anchors) DetectColumnAnchors(List<List<WordBox>> lines, List<double>? gridXs = null)
    {
        int bestIdx = -1, bestSpan = 1, bestScore = 0;
        var bestAnchors = new Dictionary<string, double>();

        int limit = Math.Min(70, lines.Count);
        for (int idx = 0; idx < limit; idx++)
        {
            if (LineStartsWithDate(lines[idx])) continue;

            // Try 1-line, 2-line, 3-line, and 4-line wrapped headers (e.g. SBI "Ref No /\nCheque\nNo", ICICI wrapped headers)
            var merged = new List<(string text, double x1, double x2)>(SplitRunTogetherPhrases(MergeLinePhrases(lines[idx], gridXs)));
            for (int span = 1; span <= 4 && idx + span - 1 < limit; span++)
            {
                if (span > 1)
                {
                    var nextLine = lines[idx + span - 1];
                    if (LineStartsWithDate(nextLine)) break;
                    var pNext = SplitRunTogetherPhrases(MergeLinePhrases(nextLine, gridXs));
                    foreach (var item in pNext)
                    {
                        double mid = (item.x1 + item.x2) / 2.0;
                        int matchIdx = merged.FindIndex(m => mid >= m.x1 - 18 && mid <= m.x2 + 18);
                        if (matchIdx >= 0)
                        {
                            var m = merged[matchIdx];
                            merged[matchIdx] = ($"{m.text} {item.text}", Math.Min(m.x1, item.x1), Math.Max(m.x2, item.x2));
                        }
                        else merged.Add(item);
                    }
                }

                var anchors = new Dictionary<string, double>();
                foreach (var (text, x1, x2) in merged.OrderBy(m => m.x1))
                {
                    var role = MatchColumnRole(text);
                    if (role != null && !anchors.ContainsKey(role))
                        anchors[role] = (x1 + x2) / 2.0;
                }
                bool hasDate = anchors.ContainsKey("date") || anchors.ContainsKey("value_date");
                bool hasMoney = anchors.ContainsKey("debit") || anchors.ContainsKey("credit") || anchors.ContainsKey("amount");
                int score = anchors.Count * 2 + (hasDate ? 4 : 0) + (hasMoney ? 4 : 0);
                if (hasDate && hasMoney && score > bestScore + (span > 1 ? 1 : 0))
                {
                    bestScore = score;
                    bestIdx = idx;
                    bestSpan = span;
                    bestAnchors = anchors;
                }
            }
        }
        return (bestIdx, bestSpan, bestAnchors);
    }

    private static bool LooksLikeDatePart(string s)
    {
        var t = s.Trim().TrimEnd(',', '.');
        if (FullDateTokenRe.IsMatch(t))
            return true;
        // Support space-separated dates split into 3 PdfPig words: "05", "Apr", "2025"
        if (MonthWords.Contains(t)) return true;
        if (TwoDigitRe.IsMatch(t) && int.TryParse(t, out int d) && d >= 1 && d <= 31) return true;
        if (Year4Re.IsMatch(t)) return true;
        return false;
    }

    private static bool LooksLikeMoneyOrDashToken(string s)
    {
        var t = s.Trim();
        if (t is "-" or "–" or "—" or "DR" or "CR" or "Dr" or "Cr" or "₹" or "Rs." or "Rs" or "INR") return true;
        return MoneyOrDashRe.IsMatch(t);
    }

    private static bool IsMoneyRole(string role) =>
        role is "debit" or "credit" or "amount" or "balance";

    private static string CompactHeader(string s) =>
        new string(s.ToLowerInvariant().Where(ch => !char.IsWhiteSpace(ch) && ch != '₹').ToArray());

    // Aliases (spaces removed) long enough to be found safely inside a run-together header, longest first
    private static readonly (string role, string alias)[] CompactAliases = ColumnAliases
        .SelectMany(kv => kv.Value.Select(a => (role: kv.Key, alias: CompactHeader(a))))
        .Where(x => x.alias.Length >= 4)
        .Distinct()
        .OrderByDescending(x => x.alias.Length)
        .ToArray();

    /// <summary>
    /// Finds several column headings inside ONE run-together phrase and returns each role with an x position interpolated
    /// across the phrase. Returns fewer than 2 entries when the phrase is an ordinary single heading.
    /// </summary>
    /// <summary>
    /// Coloured header cells often lose the spaces between headings ("Value DatePost DateDetails…"). Each phrase of ONE
    /// header line that contains two or more headings is cut into one sub-phrase per heading, with its own x range.
    /// </summary>
    private static List<(string text, double x1, double x2)> SplitRunTogetherPhrases(List<(string text, double x1, double x2)> phrases)
    {
        var outList = new List<(string text, double x1, double x2)>();
        foreach (var ph in phrases)
        {
            var parts = SplitPhraseIntoRoles(ph.text, ph.x1, ph.x2);
            if (parts.Count >= 2) outList.AddRange(parts.Select(p => (p.text, p.x1, p.x2)));
            else outList.Add(ph);
        }
        return outList;
    }

    private static List<(string role, string text, double x1, double x2)> SplitPhraseIntoRoles(string text, double x1, double x2)
    {
        var result = new List<(string role, string text, double x1, double x2)>();
        if (string.IsNullOrWhiteSpace(text) || text.Length < 8) return result;
        var low = text.ToLowerInvariant();
        var chars = new List<(char ch, int orig)>();
        for (int i = 0; i < low.Length; i++)
            if (!char.IsWhiteSpace(low[i]) && low[i] != '₹') chars.Add((low[i], i));
        var compact = new string(chars.Select(c => c.ch).ToArray());
        var taken = new bool[compact.Length];
        var found = new List<(string role, int start, int len)>();
        foreach (var (role, alias) in CompactAliases)
        {
            int from = 0;
            while (from < compact.Length)
            {
                int at = compact.IndexOf(alias, from, StringComparison.Ordinal);
                if (at < 0) break;
                bool free = true;
                for (int k = at; k < at + alias.Length; k++) if (taken[k]) { free = false; break; }
                if (free)
                {
                    for (int k = at; k < at + alias.Length; k++) taken[k] = true;
                    found.Add((role, at, alias.Length));
                }
                from = at + 1;
            }
        }
        if (found.Select(f => f.role).Distinct().Count() < 2) return result;
        double width = Math.Max(1.0, x2 - x1);
        foreach (var f in found.OrderBy(f => f.start))
        {
            int a = chars[f.start].orig, b = chars[f.start + f.len - 1].orig + 1;
            if (result.Any(r => r.role == f.role)) continue;
            result.Add((f.role, text.Substring(a, b - a), x1 + width * a / low.Length, x1 + width * b / low.Length));
        }
        return result;
    }

    /// <summary>
    /// Rebuilds words from individual glyphs. Used when the library's word grouping fails on a header (letter-spaced
    /// "V a l u e  D a t e", or glyphs drawn one by one in coloured cells): words are split at gaps clearly wider than the
    /// typical gap between letters of that line.
    /// </summary>
    private static List<WordBox> WordsFromLetters(UglyToad.PdfPig.Content.Page page)
    {
        var glyphs = new List<WordBox>();
        foreach (var l in page.Letters)
        {
            var r = l.GlyphRectangle;
            glyphs.Add(new WordBox(l.Value ?? "", r.Left, page.Height - r.Top, Math.Max(0.1, r.Width), Math.Max(0.1, r.Height)));
        }
        var words = new List<WordBox>();
        foreach (var line in GroupWordsIntoLines(glyphs.Where(g => g.Text.Length > 0).ToList()))
        {
            var gaps = new List<double>();
            for (int i = 1; i < line.Count; i++)
                if (!string.IsNullOrWhiteSpace(line[i].Text) && !string.IsNullOrWhiteSpace(line[i - 1].Text))
                    gaps.Add(line[i].X - line[i - 1].X2);
            gaps.Sort();
            double med = gaps.Count > 0 ? Math.Max(0, gaps[gaps.Count / 2]) : 0;
            double thr = Math.Max(1.2, med * 1.6 + 0.3);
            var sb = new StringBuilder();
            double wx = 0, wx2 = 0, wy = 0, wh = 0;
            void Flush()
            {
                if (sb.Length > 0) words.Add(new WordBox(sb.ToString(), wx, wy, Math.Max(0.1, wx2 - wx), wh));
                sb.Clear();
            }
            foreach (var g in line)
            {
                if (string.IsNullOrWhiteSpace(g.Text)) { Flush(); continue; }
                if (sb.Length > 0 && g.X - wx2 > thr) Flush();
                if (sb.Length == 0) { wx = g.X; wy = g.Y; wh = g.H; }
                sb.Append(g.Text);
                wx2 = Math.Max(wx2, g.X2);
                wh = Math.Max(wh, g.H);
            }
            Flush();
        }
        return words;
    }

    /// <summary>
    /// For BORDERLESS tables: derives column boundaries from the empty vertical gaps between columns of the transaction
    /// rows (lines between the first and last dated line), so content-based column inference also works without borders.
    /// </summary>
    private static (List<double> xs, List<List<WordBox>> tableLines) ColumnGapsFromContent(List<List<WordBox>> lines)
    {
        // Transaction lines only (a date AND an amount): a dated line in the account-details block would fill the gaps
        bool IsTxnLine(List<WordBox> l) =>
            l.Any(w => FullDateTokenRe.IsMatch(w.Text.Trim()) && ParseIndianDate(w.Text) != null) && l.Any(w => MoneyCellTokenRe.IsMatch(w.Text.Trim()));
        int first = lines.FindIndex(IsTxnLine);
        int last = lines.FindLastIndex(IsTxnLine);
        if (first < 0 || last - first < 2) return (new List<double>(), new List<List<WordBox>>());
        var table = lines.GetRange(first, last - first + 1);
        var words = table.SelectMany(l => l).ToList();
        double minX = words.Min(w => w.X), maxX = words.Max(w => w.X2);
        int bins = (int)Math.Ceiling((maxX - minX) * 2) + 1;
        if (bins <= 0 || bins > 20000) return (new List<double>(), new List<List<WordBox>>());
        var covered = new bool[bins];
        foreach (var w in words)
            for (int b = (int)((w.X - minX) * 2); b <= (int)((w.X2 - minX) * 2) && b < bins; b++) if (b >= 0) covered[b] = true;
        var xs = new List<double> { minX - 1 };
        int i = 0;
        while (i < bins)
        {
            if (covered[i]) { i++; continue; }
            int j = i;
            while (j < bins && !covered[j]) j++;
            if (j - i >= 6) xs.Add(minX + (i + j) / 4.0); // gap of 3pt or more
            i = j;
        }
        xs.Add(maxX + 1);
        return (xs, table);
    }

    private static bool IsStrongHeader(Dictionary<string, double> a) =>
        (a.ContainsKey("date") || a.ContainsKey("value_date")) && a.ContainsKey("narration") &&
        (a.ContainsKey("debit") || a.ContainsKey("credit") || a.ContainsKey("amount")) && a.Count >= 4;

    private static readonly Regex MoneyCellTokenRe = new(@"^[\(\-]?(?:\d{1,3}(?:,\d{2,3})*|\d+)\.\d{2}[\-\)]?(?:\(?(?:Dr|Cr|DR|CR)\.?\)?)?$", RegexOptions.Compiled);
    private static readonly Regex DrCrOnlyTokenRe = new(@"^\(?(dr|cr)\.?\)?$", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>
    /// Infers column roles of a BORDERED table from what its cells contain, for statements whose header row is an image,
    /// unreadable, or not recognised. Returns null unless dates, a text column and amount columns are all clearly present.
    /// </summary>
    private static Dictionary<string, double>? InferAnchorsFromTableContent(List<List<WordBox>> lines, List<double> gridXs, List<double> ruleYs)
    {
        if (gridXs.Count < 5) return null;
        // Only words INSIDE the table (between its top and bottom horizontal borders): the account-details block above the
        // table shares the same x-range and would otherwise dilute the column statistics.
        if (ruleYs.Count >= 2)
        {
            double top = ruleYs.Min() - 2, bottom = ruleYs.Max() + 2;
            lines = lines.Where(l => l.Count > 0 && l.Average(w => w.Yc) >= top && l.Average(w => w.Yc) <= bottom).ToList();
        }
        // …and only from the first to the last TRANSACTION line (a date and an amount on the same line), so a bordered
        // account-details box above the table cannot skew the statistics.
        bool IsTxnLine(List<WordBox> l) =>
            l.Any(w => FullDateTokenRe.IsMatch(w.Text.Trim()) && ParseIndianDate(w.Text) != null) && l.Any(w => MoneyCellTokenRe.IsMatch(w.Text.Trim()));
        int firstTxn = lines.FindIndex(IsTxnLine), lastTxn = lines.FindLastIndex(IsTxnLine);
        if (firstTxn < 0 || lastTxn - firstTxn < 2) return null;
        lines = lines.GetRange(firstTxn, lastTxn - firstTxn + 1);
        var cols = new List<(double l, double r)>();
        for (int i = 0; i + 1 < gridXs.Count; i++)
            if (gridXs[i + 1] - gridXs[i] >= 15) cols.Add((gridXs[i], gridXs[i + 1]));
        if (cols.Count < 4) return null;
        int n = cols.Count;
        var dateCnt = new int[n]; var moneyCnt = new int[n]; var dashCnt = new int[n]; var wordCnt = new int[n]; var drcrCnt = new int[n]; var total = new int[n];
        var moneyLinesPerCol = new List<HashSet<int>>();
        for (int c = 0; c < n; c++) moneyLinesPerCol.Add([]);
        int datedLines = 0;
        for (int li = 0; li < lines.Count; li++)
        {
            bool lineHasDate = false;
            foreach (var w in lines[li])
            {
                int c = cols.FindIndex(cc => w.Xc >= cc.l && w.Xc <= cc.r);
                if (c < 0) continue;
                var t = w.Text.Trim();
                total[c]++;
                if (FullDateTokenRe.IsMatch(t) && ParseIndianDate(t) != null) { dateCnt[c]++; lineHasDate = true; }
                else if (MoneyCellTokenRe.IsMatch(t)) { moneyCnt[c]++; moneyLinesPerCol[c].Add(li); }
                else if (t is "-" or "–" or "—") dashCnt[c]++;
                else if (DrCrOnlyTokenRe.IsMatch(t)) drcrCnt[c]++;
                else if (t.Any(char.IsLetter)) wordCnt[c]++;
            }
            if (lineHasDate) datedLines++;
        }
        if (datedLines < 3) return null;

        var dateCols = Enumerable.Range(0, n).Where(c => dateCnt[c] >= datedLines * 0.5 && dateCnt[c] >= total[c] * 0.5).ToList();
        var moneyCols = Enumerable.Range(0, n).Where(c => !dateCols.Contains(c) && moneyCnt[c] >= 2 && moneyCnt[c] + dashCnt[c] >= total[c] * 0.6).ToList();
        var drcrCols = Enumerable.Range(0, n).Where(c => drcrCnt[c] >= datedLines * 0.5 && drcrCnt[c] >= total[c] * 0.6).ToList();
        var textCands = Enumerable.Range(0, n).Where(c => !dateCols.Contains(c) && !moneyCols.Contains(c) && !drcrCols.Contains(c)).ToList();
        if (dateCols.Count == 0 || moneyCols.Count == 0 || textCands.Count == 0) return null;
        int narr = textCands.OrderByDescending(c => wordCnt[c]).First();
        if (wordCnt[narr] < datedLines * 0.5) return null;

        double Center(int c) => (cols[c].l + cols[c].r) / 2.0;
        var a = new Dictionary<string, double>();
        a["date"] = Center(dateCols[0]);
        if (dateCols.Count > 1) a["value_date"] = Center(dateCols[1]);
        a["narration"] = Center(narr);
        if (drcrCols.Count > 0) a["drcr"] = Center(drcrCols[0]);
        var ms = moneyCols.OrderBy(c => cols[c].l).ToList();
        // Right-most amount column present on (nearly) every row = running balance
        int balCol = ms[^1];
        bool balanceLike = moneyLinesPerCol[balCol].Count >= datedLines * 0.8;
        if (ms.Count >= 3)
        {
            a["balance"] = Center(ms[^1]); a["credit"] = Center(ms[^2]); a["debit"] = Center(ms[^3]);
        }
        else if (ms.Count == 2)
        {
            int both = moneyLinesPerCol[ms[0]].Intersect(moneyLinesPerCol[ms[1]]).Count();
            int either = moneyLinesPerCol[ms[0]].Union(moneyLinesPerCol[ms[1]]).Count();
            if (balanceLike && both >= either * 0.6) { a["amount"] = Center(ms[0]); a["balance"] = Center(ms[1]); }
            else { a["debit"] = Center(ms[0]); a["credit"] = Center(ms[1]); }
        }
        else a["amount"] = Center(ms[0]);
        // A remaining column between the text and the amounts holding refs / cheque numbers / dashes
        var refCand = textCands.Where(c => c != narr && dashCnt[c] + total[c] > 0).OrderByDescending(c => total[c]).FirstOrDefault(-1);
        if (refCand >= 0 && !a.Values.Contains(Center(refCand))) a["ref_no"] = Center(refCand);
        return a;
    }

    /// <summary>Y positions (top-down, like WordBox.Y) of horizontal table rules / cell top+bottom edges.</summary>
    private static List<double> ExtractHorizontalRules(UglyToad.PdfPig.Content.Page page)
    {
        var ys = new List<double>();
        try
        {
            foreach (var p in page.ExperimentalAccess.Paths)
            {
                var rect = p.GetBoundingRectangle();
                if (!rect.HasValue) continue;
                var r = rect.Value;
                if (r.Height <= 3.0 && r.Width >= 40.0) ys.Add(page.Height - (r.Top + r.Bottom) / 2.0);
                // Ends of vertical column borders = top / bottom of the table (needed when the header row is an image)
                else if (r.Width <= 3.0 && r.Height >= 10.0) { ys.Add(page.Height - r.Top); ys.Add(page.Height - r.Bottom); }
                else if (r.Height >= 8.0 && r.Width >= 8.0 && r.Width < page.Width * 0.96) { ys.Add(page.Height - r.Top); ys.Add(page.Height - r.Bottom); }
            }
        }
        catch { return []; }
        ys.Sort();
        var clustered = new List<double>();
        foreach (var y in ys)
        {
            if (clustered.Count == 0 || y - clustered[^1] > 2.0) clustered.Add(y);
            else clustered[^1] = (clustered[^1] + y) / 2.0;
        }
        return clustered.Count >= 3 ? clustered : [];
    }

    /// <summary>
    /// Inside each band between two horizontal rules (= one table row), moves the line that carries the row's date to the
    /// front, so lines printed above it (vertically-centred descriptions) attach to THIS transaction, not the previous one.
    /// Without horizontal rules the order is left unchanged.
    /// </summary>
    private static List<List<WordBox>> ReorderLinesWithinRowBands(List<List<WordBox>> lines, List<double> ruleYs, Dictionary<string, double> anchors)
    {
        if (lines.Count < 2) return lines;
        var dateCenters = anchors.Where(a => a.Key is "date" or "value_date").Select(a => a.Value).ToList();
        if (dateCenters.Count == 0) return lines;
        double colTol = 45.0;
        bool IsDatedLine(List<WordBox> ln) =>
            ln.Any(w => dateCenters.Any(c => Math.Abs(w.Xc - c) <= colTol) && ParseIndianDate(w.Text) != null);
        var allAnchors = anchors.ToList();
        // "3 Nov" + "2026" on the next line, or "03 Nov 2026" as three words: rebuild each date column's text for the band
        bool BandHasDate(List<List<WordBox>> group)
        {
            foreach (var role in new[] { "date", "value_date" })
            {
                if (!anchors.ContainsKey(role)) continue;
                var parts = group.SelectMany(l => l.OrderBy(w => w.X))
                    .Where(w => allAnchors.OrderBy(a => Math.Abs(w.Xc - a.Value)).First().Key == role)
                    .Select(w => w.Text).ToList();
                if (parts.Count > 0 && ParseIndianDate(string.Join(" ", parts)) != null) return true;
            }
            return false;
        }
        int DatedCount(List<List<WordBox>> group) => Math.Max(group.Count(IsDatedLine), BandHasDate(group) ? 1 : 0);

        if (ruleYs.Count < 3)
        {
            // BORDERLESS table: rows are separated by a larger vertical gap than the lines inside a row. Use those gaps
            // as row boundaries — but only if that really yields one dated line per row (otherwise leave the order alone).
            var ycs = lines.Select(l => l.Average(w => w.Yc)).ToList();
            var gaps = new List<double>();
            for (int k = 1; k < ycs.Count; k++) gaps.Add(ycs[k] - ycs[k - 1]);
            var sortedGaps = gaps.Where(g => g > 0.5).OrderBy(g => g).ToList();
            if (sortedGaps.Count < 4) return lines;
            double med = sortedGaps[sortedGaps.Count / 2];
            var synthetic = new List<double>();
            for (int k = 1; k < ycs.Count; k++)
                if (gaps[k - 1] > med * 1.3 && gaps[k - 1] > med + 2.0) synthetic.Add((ycs[k] + ycs[k - 1]) / 2.0);
            if (synthetic.Count < 3) return lines;
            // Count only bands between the first and last band holding a date (account-details lines above the table
            // and footer lines below it are not table rows).
            var datedCounts = new List<int>();
            for (int k = 0; k <= synthetic.Count; k++)
            {
                double lo = k == 0 ? double.MinValue : synthetic[k - 1], hi = k == synthetic.Count ? double.MaxValue : synthetic[k];
                var band = lines.Where((l, idx) => ycs[idx] > lo && ycs[idx] < hi).ToList();
                if (band.Count > 0) datedCounts.Add(DatedCount(band));
            }
            int firstB = datedCounts.FindIndex(c => c > 0), lastB = datedCounts.FindLastIndex(c => c > 0);
            if (firstB < 0) return lines;
            var tableBands = datedCounts.GetRange(firstB, lastB - firstB + 1);
            if (tableBands.Count < 3 || tableBands.Count(c => c == 1) < tableBands.Count * 0.8) return lines;
            ruleYs = synthetic;
        }
        int Band(List<WordBox> ln)
        {
            double yc = ln.Average(w => w.Yc);
            int b = 0;
            foreach (var ry in ruleYs) if (ry < yc) b++;
            return b;
        }

        var result = new List<List<WordBox>>(lines.Count);
        int i = 0;
        while (i < lines.Count)
        {
            int band = Band(lines[i]);
            int j = i;
            while (j < lines.Count && Band(lines[j]) == band) j++;
            var group = lines.GetRange(i, j - i);
            var dated = group.Where(IsDatedLine).ToList();
            if (group.Count > 1 && (dated.Count == 1 || (dated.Count == 0 && BandHasDate(group))))
            {
                // Fold the whole row band into ONE logical line: words keep top-to-bottom, left-to-right order, so the
                // description reads in its printed order and every column value lands on the dated transaction.
                var mergedLine = new List<WordBox>();
                foreach (var ln in group) mergedLine.AddRange(ln.OrderBy(w => w.X));
                result.Add(mergedLine);
            }
            else result.AddRange(group);
            i = j;
        }
        return result;
    }

    private static List<double> ExtractVerticalGridLines(UglyToad.PdfPig.Content.Page page)
    {
        var rawXs = new List<double>();
        try
        {
            foreach (var p in page.ExperimentalAccess.Paths)
            {
                var rect = p.GetBoundingRectangle();
                if (!rect.HasValue) continue;
                var r = rect.Value;
                if (r.Height < 10.0) continue;
                if (r.Width <= 3.0)
                {
                    rawXs.Add((r.Left + r.Right) / 2.0);
                }
                else if (r.Width >= 18.0 && r.Width < page.Width * 0.96)
                {
                    rawXs.Add(r.Left);
                    rawXs.Add(r.Right);
                }
            }
        }
        catch { return []; }

        if (rawXs.Count < 4) return [];
        rawXs.Sort();
        var clustered = new List<double>();
        foreach (var x in rawXs)
        {
            if (clustered.Count == 0 || x - clustered[^1] > 4.0)
                clustered.Add(x);
            else
                clustered[^1] = (clustered[^1] + x) / 2.0;
        }
        return clustered.Count >= 4 && (clustered[^1] - clustered[0]) >= page.Width * 0.45 ? clustered : [];
    }

    private static (List<List<string>> rows, Dictionary<string, int> colMap) LinesToTableRows(
        List<List<WordBox>> lines, Dictionary<string, double> anchors, List<double>? gridXs = null)
    {
        var ordered = anchors.OrderBy(kv => kv.Value).ToList();
        var roles = ordered.Select(kv => kv.Key).ToList();
        var centers = ordered.Select(kv => kv.Value).ToList();
        var colMap = roles.Select((r, i) => (r, i)).ToDictionary(x => x.r, x => x.i);

        // Snap column boundaries to exact drawn PDF vector grid lines when available (bordered bank PDFs!)
        List<double>? vectorBounds = null;
        if (gridXs != null && gridXs.Count >= roles.Count)
        {
            var snapped = new List<double>();
            bool valid = true;
            for (int i = 0; i < centers.Count - 1; i++)
            {
                double lo = centers[i], hi = centers[i + 1];
                var between = gridXs.Where(gx => gx > lo + 2.0 && gx < hi - 2.0).ToList();
                if (between.Count == 0) { valid = false; break; }
                // Pick the vertical grid line closest to the midpoint between adjacent header centers
                double mid = (lo + hi) / 2.0;
                snapped.Add(between.OrderBy(gx => Math.Abs(gx - mid)).First());
            }
            if (valid && snapped.Count == centers.Count - 1)
                vectorBounds = snapped;
        }

        // Compute right-edge (X2) cluster centers specifically for money columns (fixes right-aligned ICICI / Axis / HDFC numbers!)
        var moneyIndices = Enumerable.Range(0, roles.Count).Where(i => IsMoneyRole(roles[i])).ToList();
        double[]? moneyX2Centers = null;
        double moneyZoneMinX = 0;

        if (moneyIndices.Count >= 2)
        {
            moneyZoneMinX = moneyIndices[0] > 0
                ? (centers[moneyIndices[0] - 1] + centers[moneyIndices[0]]) / 2.0
                : 0.0;

            var moneySamples = new List<double>();
            foreach (var ln in lines)
            {
                foreach (var w in ln)
                {
                    if (w.Xc >= moneyZoneMinX - 15 && MoneyDecimalRe.IsMatch(w.Text.Trim()))
                        moneySamples.Add(w.X2);
                }
            }
            if (moneySamples.Count >= moneyIndices.Count * 2)
            {
                var kCenters = moneyIndices.Select(i => centers[i]).ToArray();
                for (int iter = 0; iter < 8; iter++)
                {
                    var sums = new double[kCenters.Length];
                    var cnts = new int[kCenters.Length];
                    foreach (var x in moneySamples)
                    {
                        int bestK = 0;
                        double bestD = Math.Abs(x - kCenters[0]);
                        for (int k = 1; k < kCenters.Length; k++)
                        {
                            double d = Math.Abs(x - kCenters[k]);
                            if (d < bestD) { bestD = d; bestK = k; }
                        }
                        sums[bestK] += x;
                        cnts[bestK]++;
                    }
                    for (int k = 0; k < kCenters.Length; k++)
                        if (cnts[k] > 0) kCenters[k] = sums[k] / cnts[k];
                }
                bool monotonic = Enumerable.Range(0, kCenters.Length - 1).All(k => kCenters[k] < kCenters[k + 1] - 6);
                if (monotonic) moneyX2Centers = kCenters;
            }
        }

        // Left edge of the printed amounts: a number that ends LEFT of every real amount is part of a wrapped narration
        // (e.g. "...INVOICE 371") and must not be read as a debit/credit just because it lies right of the header midpoint.
        double moneyLeftEdge = double.MinValue;
        if (moneyIndices.Count > 0)
        {
            var firstMoneyMinX = moneyIndices.Count > 0 ? (moneyIndices[0] > 0 ? (centers[moneyIndices[0] - 1] + centers[moneyIndices[0]]) / 2.0 : 0.0) : 0.0;
            var decimalLefts = lines.SelectMany(l => l)
                .Where(w => w.Xc >= firstMoneyMinX - 15 && MoneyDecimalRe.IsMatch(w.Text.Trim()))
                .Select(w => w.X).OrderBy(x => x).ToList();
            if (decimalLefts.Count >= 3) moneyLeftEdge = decimalLefts[Math.Min(decimalLefts.Count - 1, decimalLefts.Count / 50)] - 4.0;
        }

        var bounds = vectorBounds ?? Enumerable.Range(0, centers.Count - 1).Select(i => (centers[i] + centers[i + 1]) / 2.0).ToList();
        var rows = new List<List<string>>(lines.Count);
        int narrCol = colMap.TryGetValue("narration", out var nc) ? nc : -1;

        foreach (var ln in lines)
        {
            var buckets = roles.Select(_ => new List<string>()).ToList();
            foreach (var w in ln)
            {
                int col = 0;
                // Consistent coordinate space: if token is a money token inside the money zone and X2 clusters exist, match by X2!
                if (vectorBounds == null && moneyX2Centers != null && w.Xc >= moneyZoneMinX - 10 && LooksLikeMoneyOrDashToken(w.Text))
                {
                    int bestK = 0;
                    double bestD = Math.Abs(w.X2 - moneyX2Centers[0]);
                    for (int k = 1; k < moneyX2Centers.Length; k++)
                    {
                        double d = Math.Abs(w.X2 - moneyX2Centers[k]);
                        if (d < bestD) { bestD = d; bestK = k; }
                    }
                    col = moneyIndices[bestK];
                }
                else
                {
                    while (col < bounds.Count && w.Xc > bounds[col]) col++;
                }

                var role = roles[col];

                if (vectorBounds == null && IsMoneyRole(role) && narrCol >= 0 && w.X2 < moneyLeftEdge && !MoneyDecimalRe.IsMatch(w.Text.Trim()))
                {
                    buckets[narrCol].Add(w.Text);
                    continue;
                }

                // Type-aware boundary guards
                if (role == "sr_no" && !IsSerialToken(w.Text) && narrCol >= 0)
                {
                    buckets[narrCol].Add(w.Text);
                    continue;
                }
                if ((role == "date" || role == "value_date") && TimeTokenRe.IsMatch(w.Text.Trim()))
                    continue; // "12:04:10 PM" in a posted-date column
                if ((role == "date" || role == "value_date") && !LooksLikeDatePart(w.Text) && narrCol >= 0)
                {
                    buckets[narrCol].Add(w.Text);
                    continue;
                }
                if (IsMoneyRole(role) && !LooksLikeMoneyOrDashToken(w.Text) && narrCol >= 0)
                {
                    buckets[narrCol].Add(w.Text);
                    continue;
                }
                // A stand-alone "-" in a money column means "nil"; if it drifted into the Balance (or other money) bucket it
                // used to turn "54,000.00 -" into a NEGATIVE (Dr) balance.
                if (IsMoneyRole(role) && w.Text.Trim() is "-" or "–" or "—")
                    continue;

                buckets[col].Add(w.Text);
            }
            rows.Add(buckets.Select(b => string.Join(" ", b).Trim()).ToList());
        }
        // An amount split over two lines of the same cell ("10,00,000." + "00") — joined when the row band was merged
        foreach (var r in rows)
            for (int i = 0; i < roles.Count; i++)
                if (IsMoneyRole(roles[i]) && r[i].Length > 0) r[i] = WrappedAmountInCellRe.Replace(r[i], "$1$2");
        JoinWrappedCells(rows, roles);
        return (rows, colMap);
    }

    private static readonly Regex PartialDateRe = new(@"^(\d{1,2}[\s\-/.]?[A-Za-z]{3,9}\.?[\s\-/.,]?|[A-Za-z]{3,9}\.?\s+\d{1,2},?|\d{1,2}[/\-.]\d{1,2}[/\-.]?)$", RegexOptions.Compiled);
    private static readonly Regex YearPartRe = new(@"^(?:19|20)?\d{2}$", RegexOptions.Compiled);
    private static readonly Regex WrappedAmountHeadRe = new(@"^[\(\-]?\d[\d,]*(?:\.\d?|,)$", RegexOptions.Compiled);
    private static readonly Regex WrappedAmountTailRe = new(@"^\d{1,3}[\)\-]?(?:\s*(?:Dr|Cr|DR|CR))?$", RegexOptions.Compiled);
    private static readonly Regex WrappedAmountInCellRe = new(@"(\d[\d,]*(?:\.\d?|,))\s+(\d{1,3})(?![\d,.])", RegexOptions.Compiled);

    /// <summary>
    /// Narrow-column statements (SBI cash-credit / netbanking) wrap cells onto the next line: the date prints as "3 Nov" with
    /// "2026" underneath and big amounts as "10,00,000." with "00" underneath. Without the year no row had a date, so the
    /// whole statement collapsed into ONE transaction. Re-join such pieces before rows are built.
    /// </summary>
    private static void JoinWrappedCells(List<List<string>> rows, List<string> roles)
    {
        var dateCols = Enumerable.Range(0, roles.Count).Where(i => roles[i] is "date" or "value_date").ToList();
        var moneyCols = Enumerable.Range(0, roles.Count).Where(i => IsMoneyRole(roles[i])).ToList();
        for (int r = 0; r < rows.Count; r++)
        {
            foreach (var dc in dateCols)
            {
                var cell = rows[r][dc];
                if (cell.Length == 0 || ParseIndianDate(cell) != null || !PartialDateRe.IsMatch(cell)) continue;
                var acc = cell;
                for (int k = 1; k <= 2 && r + k < rows.Count; k++)
                {
                    var next = rows[r + k][dc];
                    if (next.Length == 0) continue;
                    if (ParseIndianDate(next) != null || PartialDateRe.IsMatch(next)) break; // the next row's own date
                    var joined = acc + (acc[^1] is '/' or '-' or '.' ? "" : " ") + next;
                    if (ParseIndianDate(joined) != null)
                    {
                        rows[r][dc] = joined;
                        for (int kk = 1; kk <= k; kk++) rows[r + kk][dc] = "";
                        break;
                    }
                    if (!YearPartRe.IsMatch(next)) break;
                    acc = joined;
                }
            }
            foreach (var mc in moneyCols)
            {
                var cell = rows[r][mc];
                if (cell.Length > 0 && WrappedAmountHeadRe.IsMatch(cell) && r + 1 < rows.Count && WrappedAmountTailRe.IsMatch(rows[r + 1][mc]))
                {
                    rows[r][mc] = cell + rows[r + 1][mc];
                    rows[r + 1][mc] = "";
                }
            }
        }
    }

    private static string? MatchColumnRole(string cell)
    {
        var h = Regex.Replace(cell.Trim(), @"[₹]+", " ");
        h = Regex.Replace(h.ToLowerInvariant(), @"\s+", " ").Trim();
        if (string.IsNullOrEmpty(h)) return null;
        foreach (var (role, aliases) in ColumnAliases)
            if (aliases.Contains(h)) return role;
        // Wrapped / squeezed header words: "Transactio n ID" -> "transactionid", "ChequeNo." -> "chequeno."
        var compact = h.Replace(" ", "");
        foreach (var (role, aliases) in ColumnAliases)
            if (aliases.Any(a => a.Length > 3 && a.Replace(" ", "") == compact)) return role;
        foreach (var (role, aliases) in ColumnAliases)
        {
            foreach (var a in aliases.OrderByDescending(x => x.Length))
            {
                if ((role == "debit" || role == "credit") && (h.Contains("dr/cr") || h.Contains("cr/dr") || h.Contains("dr / cr") || h.Contains("cr / dr"))) continue;
                bool matched = a.Length <= 3
                    ? Regex.IsMatch(h, $@"(?:^|[^a-z]){Regex.Escape(a)}(?:$|[^a-z])")
                    : h.Contains(a);
                if (matched) return role;
            }
        }
        return null;
    }

    private static Dictionary<string, int> BuildHeaderMap(IReadOnlyList<string> cells)
    {
        var map = new Dictionary<string, int>();
        var drcrCols = new List<int>();
        for (int c = 0; c < cells.Count; c++)
        {
            var role = MatchColumnRole(cells[c]);
            if (role == null) continue;
            if (role == "drcr") drcrCols.Add(c);
            if (!map.ContainsKey(role)) map[role] = c;
        }

        // A Dr/Cr column printed immediately AFTER the Balance column describes the BALANCE sign
        // (Kotak "Balance | Dr / Cr", Federal "Balance | DR/CR"), not the transaction direction.
        if (map.TryGetValue("balance", out int balIdx) && drcrCols.Contains(balIdx + 1))
        {
            bool hasSeparateCols = map.ContainsKey("debit") || map.ContainsKey("credit");
            var txnDrCr = drcrCols.Where(c => c != balIdx + 1).ToList();
            if (txnDrCr.Count > 0 || hasSeparateCols)
            {
                map["balance_drcr"] = balIdx + 1;
                if (txnDrCr.Count > 0) map["drcr"] = txnDrCr[0];
                else map.Remove("drcr");
            }
        }
        return map;
    }

    private static int ScoreHeaderMap(Dictionary<string, int> map, out bool valid)
    {
        bool hasDate = map.ContainsKey("date") || map.ContainsKey("value_date");
        bool hasMoney = map.ContainsKey("debit") || map.ContainsKey("credit") || map.ContainsKey("amount");
        valid = hasDate && hasMoney;
        return map.Count * 2 + (hasDate ? 4 : 0) + (hasMoney ? 4 : 0);
    }

    private static (int idx, int skipRows, Dictionary<string, int> map) FindHeaderRow(List<List<string>> rows)
    {
        int bestIdx = -1, bestSkip = 1, bestScore = 0;
        var bestMap = new Dictionary<string, int>();
        int limit = Math.Min(80, rows.Count);
        for (int idx = 0; idx < limit; idx++)
        {
            var map = BuildHeaderMap(rows[idx]);
            int score = ScoreHeaderMap(map, out bool valid);
            if (valid && score > bestScore) { bestScore = score; bestIdx = idx; bestSkip = 1; bestMap = map; }

            // Also check 2-row wrapped Excel header (e.g. ICICI / BOI / SBI)
            if (idx + 1 < limit && rows[idx + 1].All(cell => ParseIndianDate(cell) == null))
            {
                int cols = Math.Max(rows[idx].Count, rows[idx + 1].Count);
                var mergedCells = new List<string>(cols);
                for (int c = 0; c < cols; c++)
                {
                    var s1 = c < rows[idx].Count ? rows[idx][c] : "";
                    var s2 = c < rows[idx + 1].Count ? rows[idx + 1][c] : "";
                    mergedCells.Add($"{s1} {s2}".Trim());
                }
                var map2 = BuildHeaderMap(mergedCells);
                int score2 = ScoreHeaderMap(map2, out bool valid2);
                if (valid2 && score2 > bestScore + 1) { bestScore = score2; bestIdx = idx; bestSkip = 2; bestMap = map2; }
            }
        }
        return (bestIdx, bestSkip, bestMap);
    }

    private static (string bank, string acc) DetectBankAndAccount(string text)
    {
        string bank = "Scheduled Bank (Auto)";
        int bestPos = int.MaxValue, bestLen = 0;
        foreach (var (code, re) in BankDetectors)
        {
            var bm = re.Match(text);
            if (!bm.Success) continue;
            // Earliest mention wins; on a tie the longer (more specific) name wins, e.g. "union bank of india" over "bank of india".
            if (bm.Index < bestPos || (bm.Index == bestPos && bm.Length > bestLen))
            {
                bestPos = bm.Index;
                bestLen = bm.Length;
                bank = code;
            }
        }
        var m = Regex.Match(text, @"(?:a/c|account|acct)\s*(?:no\.?|number|#|:)?\s*[:\-]?\s*([0-9Xx\*]{9,20})", RegexOptions.IgnoreCase);
        return (bank, m.Success ? m.Groups[1].Value : "");
    }

    public static string? ParseIndianDate(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return null;
        var trimmed = raw.Trim();
        // Excel serial dates only when the cell is a plain 5-digit number ("45,000.00" amounts must never become dates)
        if (PlainOaDateRe.IsMatch(trimmed) && double.TryParse(trimmed, NumberStyles.Float, CultureInfo.InvariantCulture, out var oa) && oa >= 35000 && oa <= 65000)
        {
            try { return DateTime.FromOADate(oa).ToString("yyyy-MM-dd", CultureInfo.InvariantCulture); } catch { }
        }
        var iso = IsoDateTimeRe.Match(trimmed);
        if (iso.Success) trimmed = iso.Groups[1].Value;
        var s = TimeSuffixRe.Replace(trimmed, "").Trim();
        s = MultiSpaceRe.Replace(s, " ");
        // "Sept" (4 letters) is printed by several banks but is not a .NET "MMM" token
        s = Regex.Replace(s, @"(?<![A-Za-z])Sept(?![A-Za-z])", "Sep", RegexOptions.IgnoreCase);
        foreach (var fmt in DateFormats)
            if (DateTime.TryParseExact(s, fmt, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt))
                return dt.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

        // Extract an embedded full date token if cell had a prefix like a serial number (only for short cells)
        if (s.Length <= 32)
        {
            var m = EmbeddedDateRe.Match(s);
            if (m.Success)
            {
                var cand = Regex.Replace(m.Groups[1].Value, @"\s+", " ").Trim();
                foreach (var fmt in DateFormats)
                    if (DateTime.TryParseExact(cand, fmt, CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt2))
                        return dt2.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            }
        }
        return null;
    }

    public static string FormatDisplayDate(string isoDate) =>
        DateTime.TryParseExact(isoDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var dt)
            ? dt.ToString("dd-MMM-yyyy", CultureInfo.InvariantCulture)
            : isoDate;

    public static (decimal amt, string? flag) ParseIndianAmount(string raw)
    {
        var (amt, flag, _) = ParseIndianAmountEx(raw);
        return (amt, flag);
    }

    private static (decimal amt, string? flag, bool hasNumber) ParseIndianAmountEx(string raw)
    {
        if (string.IsNullOrWhiteSpace(raw)) return (0m, null, false);
        var s = raw.Trim().Replace('\u2212', '-').Replace('\u2013', '-'); // unicode minus / en-dash used by some PDFs
        string? flag = null;

        if (DrWordRe.IsMatch(s)) flag = "DR";
        else if (CrWordRe.IsMatch(s)) flag = "CR";
        else if (s.StartsWith('(') && s.EndsWith(')')) flag = "DR"; // accounting negative "(1,234.00)"

        var m = AmountNumberRe.Match(s);
        if (!m.Success) return (0m, flag, false);

        // Leading or trailing minus (trailing minus is common in PNB / BoB / BOI / Canara OD statements)
        var before = s[..m.Index].TrimEnd();
        var after = s[(m.Index + m.Length)..].TrimStart();
        if (before.EndsWith('-') || after.StartsWith('-')) flag ??= "DR";

        var cleaned = m.Value.Replace(",", "");
        // decimal: "1,23,456.78" is kept EXACTLY (a double holds 123456.78 only approximately)
        if (decimal.TryParse(cleaned, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var val))
            return (Math.Round(Math.Abs(val), 2, MidpointRounding.AwayFromZero), flag, true);
        return (0m, flag, false);
    }

    private static decimal? ParseSignedBalance(string raw)
    {
        var (val, flag, hasNum) = ParseIndianAmountEx(raw);
        if (!hasNum) return null;
        return flag == "DR" ? -val : val;
    }

    private sealed class RawTxn
    {
        public string Dt = "";
        public string ValDt = "";
        public string Narr = "";
        public string RefNo = "";
        public string DebStr = "";
        public string CredStr = "";
        public string AmtStr = "";
        public string DrCrStr = "";
        public string BalStr = "";
        public string Warning = "";

        public bool HasAmount =>
            ParseIndianAmount(DebStr).amt > 0 || ParseIndianAmount(CredStr).amt > 0 || ParseIndianAmount(AmtStr).amt > 0;
    }

    private static int CountAmountNumbers(string? s) =>
        string.IsNullOrWhiteSpace(s) ? 0 : AmountNumberRe.Matches(s).Count;

    private static string StripFooter(string narr)
    {
        if (string.IsNullOrWhiteSpace(narr) || !FooterNoiseRegex.IsMatch(narr)) return narr;
        var head = FooterNoiseRegex.Split(narr)[0].Trim();
        // Keep the narration if the "footer" word is at the very start (e.g. a vendor called "TOTAL ENVIRONMENT PVT LTD")
        return string.IsNullOrWhiteSpace(head) ? narr : head;
    }

    private static void AppendWarning(RawTxn t, string w)
    {
        if (string.IsNullOrEmpty(t.Warning)) t.Warning = w;
        else if (!t.Warning.Contains(w, StringComparison.Ordinal)) t.Warning = $"{t.Warning}; {w}";
    }

    private static void AppendWarning(BankTransactionRow t, string w)
    {
        if (string.IsNullOrEmpty(t.ParseWarning)) t.ParseWarning = w;
        else if (!t.ParseWarning.Contains(w, StringComparison.Ordinal)) t.ParseWarning = $"{t.ParseWarning}; {w}";
    }

    private static List<BankTransactionRow> BuildTransactions(
        List<List<string>> rows, bool hasSeparateDrCr, string bank, string sourceFile)
    {
        var txns = new List<BankTransactionRow>();
        static string Cell(List<string> r, string key)
        {
            var v = CanonicalColMap.TryGetValue(key, out int i) && i < r.Count ? (r[i] ?? "").Trim() : "";
            // A money column must hold an amount. Narration text that drifted into it ("WDL TFR UPI/DR/509169091433/…") or a
            // bare 10+ digit reference number must NEVER be read as money (it produced credits of ₹5,09,16,90,91,433).
            if (key is "debit" or "credit" or "amount" or "balance" && v.Length > 0 && !IsPlausibleAmountCell(v)) return "";
            return v;
        }

        // Group multi-line rows into complete transaction records
        var grouped = new List<RawTxn>();
        bool inPageFooter = false;

        foreach (var row in rows)
        {
            if (row.All(string.IsNullOrWhiteSpace)) continue;
            var fullRowStr = string.Join(" ", row).Trim();
            var rawDate = Cell(row, "date");
            if (string.IsNullOrEmpty(rawDate)) rawDate = Cell(row, "value_date");
            var dt = ParseIndianDate(rawDate);
            var narr = Cell(row, "narration");

            if (dt == null)
            {
                if (inPageFooter) continue;
                var d0 = Cell(row, "debit");
                var c0 = Cell(row, "credit");
                var a0 = Cell(row, "amount");
                decimal d0Amt = ParseIndianAmount(d0).amt;
                decimal c0Amt = ParseIndianAmount(c0).amt;
                decimal a0Amt = ParseIndianAmount(a0).amt;

                // An undated row with BOTH Debit > 0 AND Credit > 0 is ALWAYS a Total/Summary row — enters page footer state!
                if (d0Amt > 0 && c0Amt > 0) { inPageFooter = true; continue; }
                if (FooterNoiseRegex.IsMatch(narr) || FooterNoiseRegex.IsMatch(fullRowStr) || SkipRowRegex.IsMatch(narr))
                {
                    inPageFooter = true;
                    continue;
                }

                if (grouped.Count > 0)
                {
                    var last = grouped[^1];
                    bool rowHasAmt = d0Amt > 0 || c0Amt > 0 || a0Amt > 0;
                    var b0 = Cell(row, "balance");
                    bool rowHasBal = ParseSignedBalance(b0).HasValue;

                    // Some banks print the date only on the FIRST transaction of each day. An undated line that carries its
                    // own amount while the previous transaction already has one is a separate same-day transaction —
                    // previously its amount was silently discarded (missing debit/credit).
                    // A running balance on the line is required: it proves the line is a separate ledger movement and not a
                    // stray number from a wrapped narration (the balance check then verifies the amount).
                    if (rowHasAmt && last.HasAmount && rowHasBal)
                    {
                        var inherited = new RawTxn
                        {
                            Dt = last.Dt,
                            ValDt = ParseIndianDate(Cell(row, "value_date")) ?? last.Dt,
                            Narr = narr,
                            RefNo = Cell(row, "ref_no"),
                            DebStr = d0,
                            CredStr = c0,
                            AmtStr = a0,
                            DrCrStr = Cell(row, "drcr"),
                            BalStr = b0
                        };
                        AppendWarning(inherited, "Date not printed on this line — used previous row's date");
                        grouped.Add(inherited);
                        continue;
                    }

                    if (!string.IsNullOrWhiteSpace(narr))
                        last.Narr = MultiSpaceRe.Replace($"{last.Narr} {narr}", " ").Trim();
                    if (string.IsNullOrWhiteSpace(last.RefNo) || last.RefNo == "-")
                    {
                        var r0 = Cell(row, "ref_no");
                        if (!string.IsNullOrWhiteSpace(r0) && r0 != "-") last.RefNo = r0;
                    }
                    // Only pull amounts from continuation lines if the transaction does NOT already have an amount!
                    if (!last.HasAmount)
                    {
                        if (d0Amt > 0) last.DebStr = d0;
                        else if (c0Amt > 0) last.CredStr = c0;
                        else if (a0Amt > 0) { last.AmtStr = a0; last.DrCrStr = Cell(row, "drcr"); }
                    }
                    if ((string.IsNullOrWhiteSpace(last.BalStr) || last.BalStr == "-") && rowHasBal)
                        last.BalStr = b0;
                }
                continue;
            }
            inPageFooter = false;
            if (SkipRowRegex.IsMatch(narr)) continue;
            var cur = new RawTxn
            {
                Dt = dt,
                ValDt = ParseIndianDate(Cell(row, "value_date")) ?? dt,
                Narr = narr,
                RefNo = Cell(row, "ref_no"),
                DebStr = Cell(row, "debit"),
                CredStr = Cell(row, "credit"),
                AmtStr = Cell(row, "amount"),
                DrCrStr = Cell(row, "drcr"),
                BalStr = Cell(row, "balance")
            };
            if (FooterNoiseRegex.IsMatch(fullRowStr))
            {
                if (!cur.HasAmount) { inPageFooter = true; continue; }
                // Dated transaction with an inline footer on the same line: keep the transaction and strip the footer!
                cur.Narr = StripFooter(cur.Narr);
                inPageFooter = true;
            }
            grouped.Add(cur);
        }

        // Single "Amount" column with no Dr/Cr indicator column: if the bank prints withdrawals as negative numbers
        // (or with "Dr"), then an un-flagged positive amount is a CREDIT. Previously every positive amount became a debit.
        bool noDrCrIndicator = !hasSeparateDrCr && grouped.All(g => string.IsNullOrWhiteSpace(g.DrCrStr));
        bool signedAmountConvention = noDrCrIndicator && grouped.Any(g => ParseIndianAmount(g.AmtStr).flag == "DR");

        foreach (var g in grouped)
        {
            decimal debit = 0, credit = 0;
            if (hasSeparateDrCr)
            {
                (debit, _) = ParseIndianAmount(g.DebStr);
                (credit, _) = ParseIndianAmount(g.CredStr);
                if (CountAmountNumbers(g.DebStr) > 1 || CountAmountNumbers(g.CredStr) > 1)
                    AppendWarning(g, "More than one number in the Debit/Credit cell — verify amount");
            }
            if (debit <= 0 && credit <= 0 && !string.IsNullOrWhiteSpace(g.AmtStr))
            {
                var (amt, flag) = ParseIndianAmount(g.AmtStr);
                var drcr = g.DrCrStr.Trim().ToUpperInvariant();
                bool isCr = drcr.Contains("CR") || drcr == "C" || drcr.Contains("DEP") || flag == "CR";
                bool isDr = drcr.Contains("DR") || drcr == "D" || drcr.Contains("DEB") || drcr.Contains("WDL") || drcr.Contains("WITHDRAW") || flag == "DR";
                if (isCr && !isDr) credit = amt;
                else if (isDr && !isCr) debit = amt;
                else if (!isCr && !isDr && signedAmountConvention) credit = amt;
                else
                {
                    debit = amt;
                    if (!isCr && !isDr) AppendWarning(g, "Dr/Cr not stated in statement — assumed Debit");
                }
            }
            if (debit <= 0 && credit <= 0) continue;
            if (debit > 0 && credit > 0)
                AppendWarning(g, $"Both Debit ({debit:N2}) and Credit ({credit:N2}) present on one line — verify");

            var txnType = debit >= credit ? "DR" : "CR";
            var amount = Math.Round(txnType == "DR" ? debit : credit, 2);
            var refNo = g.RefNo;
            if (string.IsNullOrEmpty(refNo) || refNo is "-" or "0") refNo = ExtractRef(g.Narr);
            var bal = ParseSignedBalance(g.BalStr);
            var trimmedNarr = StripFooter(g.Narr);
            // Drop stand-alone dash placeholders (empty cheque-no. cells) that drift into the narration
            trimmedNarr = LoneDashRe.Replace(trimmedNarr ?? "", " ");
            var cleanNarr = string.IsNullOrWhiteSpace(trimmedNarr) ? "Bank Transaction" : MultiSpaceRe.Replace(trimmedNarr, " ").Trim();

            txns.Add(new BankTransactionRow
            {
                RowId = ShortHash(FormattableString.Invariant($"{sourceFile}|{txns.Count}|{g.Dt}|{txnType}|{amount:F2}|{refNo}|{cleanNarr}")),
                TxnDate = g.Dt,
                DisplayDate = FormatDisplayDate(g.Dt),
                ValueDate = g.ValDt,
                Narration = cleanNarr,
                RefNo = refNo,
                Debit = txnType == "DR" ? amount : 0,
                Credit = txnType == "CR" ? amount : 0,
                Balance = bal,
                TxnType = txnType,
                Amount = amount,
                PaymentMode = DetectPaymentMode(cleanNarr),
                BankDetected = bank,
                SourceFile = sourceFile,
                ParseWarning = g.Warning
            });
        }

        VerifyAndCorrectDrCrByRunningBalance(txns);
        return txns;
    }

    private static bool IsReverseChronological(List<BankTransactionRow> txns)
    {
        if (txns.Count < 2) return false;
        int cmp = string.CompareOrdinal(txns[0].TxnDate, txns[^1].TxnDate);
        if (cmp > 0) return true;
        if (cmp < 0) return false;

        // Single-day statement: infer true order from running balance progression
        var withBal = txns.Where(t => t.Balance.HasValue).ToList();
        if (withBal.Count < 2) return false;
        int fwd = 0, rev = 0;
        for (int i = 1; i < withBal.Count; i++)
        {
            decimal prev = withBal[i - 1].Balance!.Value, curr = withBal[i].Balance!.Value;
            if (Math.Abs((prev - withBal[i].Debit + withBal[i].Credit) - curr) <= BalanceTolerance) fwd++;
            if (Math.Abs((curr - withBal[i - 1].Debit + withBal[i - 1].Credit) - prev) <= BalanceTolerance) rev++;
        }
        return rev > fwd;
    }

    private static void VerifyAndCorrectDrCrByRunningBalance(List<BankTransactionRow> txns)
    {
        if (txns.Count < 2 || txns.Count(t => t.Balance.HasValue) < 2) return;
        bool isChronological = !IsReverseChronological(txns);

        // Whole-statement check: if MOST rows that the running balance can prove have the opposite direction, the
        // Debit/Credit columns were mapped the wrong way round. Flip EVERY row — including the first row, which has no
        // previous balance and so could never be corrected individually (it stayed reversed).
        int provenRight = 0, provenWrong = 0;
        for (int k = 1; k < txns.Count; k++)
        {
            var prevRow = isChronological ? txns[k - 1] : txns[txns.Count - k];
            var row = isChronological ? txns[k] : txns[txns.Count - k - 1];
            if (!prevRow.Balance.HasValue || !row.Balance.HasValue || row.Amount <= 0) continue;
            bool mDr = Math.Abs((prevRow.Balance.Value - row.Amount) - row.Balance.Value) <= BalanceTolerance;
            bool mCr = Math.Abs((prevRow.Balance.Value + row.Amount) - row.Balance.Value) <= BalanceTolerance;
            if (mDr == mCr) continue;
            if ((mDr && row.TxnType == "DR") || (mCr && row.TxnType == "CR")) provenRight++; else provenWrong++;
        }
        if (provenWrong >= 3 && provenWrong > provenRight * 2)
        {
            foreach (var t in txns)
            {
                var flipped = t.TxnType == "DR" ? "CR" : "DR";
                t.TxnType = flipped;
                t.Debit = flipped == "DR" ? t.Amount : 0;
                t.Credit = flipped == "CR" ? t.Amount : 0;
            }
            // Every other row is re-proven by the running balance below; the chronologically FIRST row cannot be, so ask.
            var firstRow = isChronological ? txns[0] : txns[^1];
            AppendWarning(firstRow, "Dr/Cr inferred: Debit/Credit columns were swapped in this statement and corrected from the running balance — please confirm this first row");
        }

        if (isChronological)
        {
            for (int i = 1; i < txns.Count; i++)
                FixRowDrCrFromPrevBalance(txns[i - 1].Balance, txns[i]);
        }
        else
        {
            for (int i = txns.Count - 2; i >= 0; i--)
                FixRowDrCrFromPrevBalance(txns[i + 1].Balance, txns[i]);
        }
    }

    /// <summary>
    /// Money is decimal, so a running balance either agrees to the paisa or it does not. (With double, 0.1 + 0.2 is
    /// 0.30000000000000004 and a 5-paise slack was needed — which could also hide a real 1–4 paise error.)
    /// </summary>
    private const decimal BalanceTolerance = 0.005m;

    private static void FixRowDrCrFromPrevBalance(decimal? prevBal, BankTransactionRow row)
    {
        if (!prevBal.HasValue || !row.Balance.HasValue || row.Amount <= 0) return;
        decimal amt = row.Amount;
        bool matchesDr = Math.Abs((prevBal.Value - amt) - row.Balance.Value) <= BalanceTolerance;
        bool matchesCr = Math.Abs((prevBal.Value + amt) - row.Balance.Value) <= BalanceTolerance;
        if (matchesDr && !matchesCr && row.TxnType != "DR")
        {
            row.TxnType = "DR";
            row.Debit = amt;
            row.Credit = 0;
            row.ParseWarning = RemoveAssumedNote(row.ParseWarning);
            AppendWarning(row, "Dr/Cr corrected to Debit using running balance");
        }
        else if (matchesCr && !matchesDr && row.TxnType != "CR")
        {
            row.TxnType = "CR";
            row.Credit = amt;
            row.Debit = 0;
            row.ParseWarning = RemoveAssumedNote(row.ParseWarning);
            AppendWarning(row, "Dr/Cr corrected to Credit using running balance");
        }
        else if (matchesDr != matchesCr)
        {
            // Direction is now PROVEN by the running balance; drop any "assumed" note
            row.ParseWarning = RemoveAssumedNote(row.ParseWarning);
        }
    }

    private static readonly Regex DrHintRe = new(@"(?<![a-z])(wdl|withdrawal|upi/dr|imps/dr|neft\s*dr|rtgs\s*dr|to\s*transfer|to\s*trf|debit\s*card|atm\s*wdl|chq\s*paid|bil/|ach\s*d-|nach\s*dr|/dr/)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex CrHintRe = new(@"(?<![a-z])(dep|deposit|upi/cr|imps/cr|neft\s*cr|rtgs\s*cr|by\s*transfer|by\s*trf|by\s*clg|credit\s*interest|int\.?\s*pd|/cr/|trfr\s*from|cash\s*dep)(?![a-z])", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    /// <summary>"DR"/"CR" when the narration clearly indicates the direction, otherwise null. Used only for rows the running balance cannot prove.</summary>
    public static string? NarrationDirectionHint(string? narr)
    {
        if (string.IsNullOrWhiteSpace(narr)) return null;
        bool dr = DrHintRe.IsMatch(narr), cr = CrHintRe.IsMatch(narr);
        return dr == cr ? null : (dr ? "DR" : "CR");
    }

    private static string RemoveAssumedNote(string warning)
    {
        if (string.IsNullOrEmpty(warning)) return "";
        var parts = warning.Split("; ", StringSplitOptions.RemoveEmptyEntries)
            .Where(p => !p.StartsWith("Dr/Cr not stated", StringComparison.Ordinal) && !p.StartsWith("Dr/Cr inferred", StringComparison.Ordinal));
        return string.Join("; ", parts);
    }
    private static List<BankTransactionRow> ParseSpatialFallback(
        List<(double width, List<List<WordBox>> lines)> pagesData, string bank, string sourceFile)
    {
        var blocks = new List<(string dt, List<string> narrWords, List<(decimal amt, string? flag, double xc, string raw)> moneyTokens, List<string> drcrTokens)>();
        var drCrTokenRe = new Regex(@"^\(?(dr|cr|debit|credit|d|c)\.?\)?$", RegexOptions.IgnoreCase);
        var amtTokenRe = new Regex(@"^[\(\-]?(?:\d{1,3}(?:,\d{2,3})*|\d+)\.\d{2}[\-\)]?(?:\s*(?:Dr|Cr|DR|CR))?$");

        foreach (var (pageW, lines) in pagesData)
        {
            double moneyMinX = pageW * 0.42;
            bool inPageFooter = false;
            foreach (var ln in lines)
            {
                if (ln.Count == 0) continue;
                var lineStr = string.Join(" ", ln.Select(w => w.Text));
                if (FooterNoiseRegex.IsMatch(lineStr) || Regex.IsMatch(lineStr, @"^\s*statement\s+from", RegexOptions.IgnoreCase))
                {
                    inPageFooter = true;
                    continue;
                }

                string? dt = null;
                int startIdx = IsSerialToken(ln[0].Text) && ln.Count >= 2 ? 1 : 0;
                int dateEndIdx = startIdx;

                // The date may follow a serial number AND a transaction-ID column ("1 S97833778 21/11/2026 ...")
                for (int k = startIdx; k < Math.Min(ln.Count, startIdx + 3) && dt == null; k++)
                {
                    if (ln[k].X >= pageW * 0.38) break;
                    dt = ParseIndianDate(ln[k].Text);
                    if (dt != null) { dateEndIdx = k + 1; break; }
                    if (k + 2 < ln.Count)
                    {
                        dt = ParseIndianDate($"{ln[k].Text} {ln[k + 1].Text} {ln[k + 2].Text}");
                        if (dt != null) { dateEndIdx = k + 3; break; }
                    }
                }

                if (dt != null)
                {
                    inPageFooter = false;
                    blocks.Add((dt, [], [], []));
                }
                else if (inPageFooter || blocks.Count == 0) continue;

                var cur = blocks[^1];
                for (int i = dateEndIdx; i < ln.Count; i++)
                {
                    var w = ln[i];
                    if (w.Xc >= moneyMinX && drCrTokenRe.IsMatch(w.Text.Trim()))
                    {
                        cur.drcrTokens.Add(w.Text.Trim().Trim('(', ')', '.').ToUpperInvariant());
                        continue;
                    }
                    if (w.Xc >= moneyMinX && amtTokenRe.IsMatch(w.Text))
                    {
                        var (a, fl, hasNum) = ParseIndianAmountEx(w.Text);
                        if (hasNum)
                            cur.moneyTokens.Add((a, fl, w.Xc, w.Text));
                    }
                    else if (w.Text is not ("-" or "–" or "—"))
                    {
                        if (i == dateEndIdx && ParseIndianDate(w.Text) != null) continue;
                        cur.narrWords.Add(w.Text);
                    }
                }
            }
        }

        var txns = new List<BankTransactionRow>();
        decimal? prevBal = null;
        foreach (var b in blocks)
        {
            var rawNarr = Regex.Replace(string.Join(" ", b.narrWords), @"\s+", " ").Trim();
            var narr = FooterNoiseRegex.IsMatch(rawNarr) ? FooterNoiseRegex.Split(rawNarr)[0].Trim() : rawNarr;
            if (SkipRowRegex.IsMatch(narr) || b.moneyTokens.Count == 0) continue;

            var orderedMoney = b.moneyTokens.OrderBy(m => m.xc).ToList();
            decimal? bal = orderedMoney.Count >= 2 ? ParseSignedBalance(orderedMoney[^1].raw) : null;
            var candidateAmts = orderedMoney.Count >= 2 ? orderedMoney.Take(orderedMoney.Count - 1).ToList() : orderedMoney;
            var picked = candidateAmts.FirstOrDefault(m => m.amt > 0);
            if (picked.amt <= 0) continue;

            decimal txnAmt = picked.amt;
            string? flag = picked.flag;
            // A stand-alone Cr/Dr column value is authoritative (previously ignored → first row direction was guessed)
            if (flag == null && b.drcrTokens.Count > 0)
            {
                bool anyCr = b.drcrTokens.Any(t => t is "CR" or "C" or "CREDIT");
                bool anyDr = b.drcrTokens.Any(t => t is "DR" or "D" or "DEBIT");
                if (anyCr != anyDr) flag = anyCr ? "CR" : "DR";
            }
            string txnType = flag ?? "DR";
            if (flag == null && prevBal.HasValue && bal.HasValue)
            {
                if (Math.Abs((prevBal.Value + txnAmt) - bal.Value) <= BalanceTolerance) txnType = "CR";
                else if (Math.Abs((prevBal.Value - txnAmt) - bal.Value) <= BalanceTolerance) txnType = "DR";
                else txnType = bal.Value >= prevBal.Value ? "CR" : "DR";
            }
            else if (flag == null && (narr.Contains("CR/", StringComparison.OrdinalIgnoreCase) || narr.Contains("BY ", StringComparison.OrdinalIgnoreCase) || narr.Contains("FROM ", StringComparison.OrdinalIgnoreCase) || narr.Contains("INT", StringComparison.OrdinalIgnoreCase)))
            {
                txnType = "CR";
            }
            bool typeGuessed = flag == null && !(prevBal.HasValue && bal.HasValue);
            if (bal.HasValue) prevBal = bal;

            var refNo = ExtractRef(narr);
            txns.Add(new BankTransactionRow
            {
                RowId = ShortHash(FormattableString.Invariant($"{sourceFile}|{txns.Count}|{b.dt}|{txnType}|{txnAmt:F2}|{refNo}|{narr}")),
                ParseWarning = typeGuessed ? "Dr/Cr inferred from narration/layout — verify" : "",
                TxnDate = b.dt,
                DisplayDate = FormatDisplayDate(b.dt),
                ValueDate = b.dt,
                Narration = string.IsNullOrWhiteSpace(narr) ? "Bank Transaction" : narr,
                RefNo = refNo,
                Debit = txnType == "DR" ? txnAmt : 0,
                Credit = txnType == "CR" ? txnAmt : 0,
                Balance = bal,
                TxnType = txnType,
                Amount = txnAmt,
                PaymentMode = DetectPaymentMode(narr),
                BankDetected = bank,
                SourceFile = sourceFile
            });
        }
        VerifyAndCorrectDrCrByRunningBalance(txns);
        return txns;
    }

    private static List<BankTransactionRow> ParseTextFallback(string fullText, string bank, string sourceFile)
    {
        var txns = new List<BankTransactionRow>();
        var dateRe = new Regex(@"^(?:\d{1,5}\.?\s+)?(\d{1,2}[/\-.\s](?:\d{1,2}|[A-Za-z]{3,9})[/\-.\s]\d{2,4})\s+(.+)$");
        var amtRe = new Regex(@"[\(\-]?(?:\d{1,3}(?:,\d{2,3})*|\d+)\.\d{2}[\-\)]?(?:\s*(?:Dr|Cr|DR|CR))?");
        decimal? prevBal = null;

        foreach (var raw in fullText.Split('\n'))
        {
            var line = Regex.Replace(raw, @"\s+", " ").Trim();
            if (FooterNoiseRegex.IsMatch(line)) continue;
            var m = dateRe.Match(line);
            if (!m.Success) continue;
            var dt = ParseIndianDate(m.Groups[1].Value);
            if (dt == null) continue;
            var rest = m.Groups[2].Value;
            var rawAmts = amtRe.Matches(rest).Select(x => x.Value).ToList();
            if (rawAmts.Count == 0) continue;

            decimal? bal = rawAmts.Count >= 2 ? ParseSignedBalance(rawAmts[^1]) : null;
            var candidates = rawAmts.Count >= 2 ? rawAmts.Take(rawAmts.Count - 1).Select(ParseIndianAmount).ToList() : [ParseIndianAmount(rawAmts[0])];
            var picked = candidates.FirstOrDefault(x => x.amt > 0);
            if (picked.amt <= 0) continue;

            var narr = amtRe.Replace(rest, "").Trim(' ', '-', '|');
            if (SkipRowRegex.IsMatch(narr)) { if (bal.HasValue) prevBal = bal; continue; }

            var txnType = picked.flag ?? (prevBal.HasValue && bal.HasValue ? (bal.Value >= prevBal.Value ? "CR" : "DR") : (narr.Contains("CR/", StringComparison.OrdinalIgnoreCase) || narr.Contains("BY ", StringComparison.OrdinalIgnoreCase) ? "CR" : "DR"));
            bool typeGuessed = picked.flag == null && !(prevBal.HasValue && bal.HasValue);
            if (bal.HasValue) prevBal = bal;

            txns.Add(new BankTransactionRow
            {
                RowId = ShortHash(FormattableString.Invariant($"{sourceFile}|{txns.Count}|{dt}|{txnType}|{picked.amt:F2}|{narr}")),
                ParseWarning = typeGuessed ? "Dr/Cr inferred from narration/layout — verify" : "",
                TxnDate = dt,
                DisplayDate = FormatDisplayDate(dt),
                ValueDate = dt,
                Narration = string.IsNullOrWhiteSpace(narr) ? "Bank Transaction" : narr,
                RefNo = ExtractRef(narr),
                Debit = txnType == "DR" ? picked.amt : 0,
                Credit = txnType == "CR" ? picked.amt : 0,
                Balance = bal,
                TxnType = txnType,
                Amount = picked.amt,
                PaymentMode = DetectPaymentMode(narr),
                BankDetected = bank,
                SourceFile = sourceFile
            });
        }
        VerifyAndCorrectDrCrByRunningBalance(txns);
        return txns;
    }

    private const string BalanceNumberPattern =
        @"([\(\-]?(?:\d{1,3}(?:,\d{2,3})*|\d+)\.\d{2}[\-\)]?(?:\s*(?:Dr|Cr|DR|CR)\b(?!\s*(?:count|cnt|txn|trans|amt|amount|total)))?)";
    private static readonly Regex OpeningLabelRe = new(@"(?:opening\s+balance|opening\s+bal\.?|brought\s+forward|(?<![a-z])(?:balance\s+)?b/f(?![a-z]))[^\d\-\r\n]{0,25}" + BalanceNumberPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex ClosingLabelRe = new(@"(?:closing\s+balance|closing\s+bal\.?|carried\s+forward|(?<![a-z])(?:balance\s+)?c/f(?![a-z]))[^\d\-\r\n]{0,25}" + BalanceNumberPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex BalanceAsOnRe = new(@"balance\s+as\s+on\s+(?<d>\d{1,2}[\s\-/.](?:[A-Za-z]{3,9}|\d{1,2})[\s\-/.,]*\d{2,4})\s*[:\-]?\s*" + BalanceNumberPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex OpeningRowRe = new(@"\b(opening\s+bal|brought\s+forward|b/f)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex ClosingRowRe = new(@"\b(closing\s+bal|carried\s+forward|c/f)\b", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex AmountNoiseWordsRe = new(@"(?<![a-z])(dr|cr|rs|inr)(?![a-z])\.?", RegexOptions.IgnoreCase | RegexOptions.Compiled);

    private static readonly Regex LongBareIntegerRe = new(@"(?<![\d,.])\d{11,}(?![\d,]|\.\d)", RegexOptions.Compiled);

    /// <summary>An amount cell: digits with optional Dr/Cr/Rs/INR/₹/sign/brackets, no words, and not a bare 11+ digit reference (UPI RRN / account no.).</summary>
    public static bool IsPlausibleAmountCell(string? cell)
    {
        if (string.IsNullOrWhiteSpace(cell)) return false;
        var t = cell.Trim();
        if (t is "-" or "–" or "—") return true;
        return IsPureAmountCell(t) && !LongBareIntegerRe.IsMatch(t);
    }

    /// <summary>True when a cell holds only an amount (optionally with Dr/Cr/Rs/INR), not a label like "Closing Balance : 1,000.00".</summary>
    private static bool IsPureAmountCell(string? cell)
    {
        if (string.IsNullOrWhiteSpace(cell)) return false;
        var stripped = AmountNoiseWordsRe.Replace(cell, "").Replace("₹", "");
        return stripped.Any(char.IsDigit) && !stripped.Any(char.IsLetter);
    }

    private static decimal? BalanceAfterLabel(string text, Regex labelRe)
    {
        var m = labelRe.Match(text);
        return m.Success ? ParseSignedBalance(m.Groups[1].Value) : null;
    }

    /// <summary>True when the statement did not state the row's Dr/Cr and the running balance could not prove it.</summary>
    public static bool IsDirectionUncertain(BankTransactionRow r) =>
        !string.IsNullOrEmpty(r.ParseWarning) &&
        (r.ParseWarning.Contains("Dr/Cr not stated", StringComparison.Ordinal) || r.ParseWarning.Contains("Dr/Cr inferred", StringComparison.Ordinal));

    /// <summary>
    /// Applies the user's Debit/Credit answers for uncertain rows of ONE parsed statement, then recomputes the opening /
    /// closing / running-balance proof with the confirmed directions (printed opening/closing balances are kept).
    /// </summary>
    public static void ApplyConfirmedDirections(ParsedStatementResult res, IReadOnlyDictionary<BankTransactionRow, string> choices)
    {
        foreach (var (row, choice) in choices)
        {
            if (!res.Transactions.Contains(row)) continue;
            var type = string.Equals(choice, "CR", StringComparison.OrdinalIgnoreCase) ? "CR" : "DR";
            row.TxnType = type;
            row.Debit = type == "DR" ? row.Amount : 0;
            row.Credit = type == "CR" ? row.Amount : 0;
            row.ParseWarning = RemoveAssumedNote(row.ParseWarning);
        }
        var prev = res.Balances;
        foreach (var t in res.Transactions) { t.HasBalanceBreak = false; t.BalanceBreakNote = ""; }
        res.Balances = ExtractBalances("", res.Transactions, [],
            prev.OpeningPrinted ? prev.StatementOpening : null,
            prev.ClosingPrinted ? prev.StatementClosing : null);
        res.Balances.PrintedTotalDebit = prev.PrintedTotalDebit;
        res.Balances.PrintedTotalCredit = prev.PrintedTotalCredit;
        res.Balances.PrintedDebitCount = prev.PrintedDebitCount;
        res.Balances.PrintedCreditCount = prev.PrintedCreditCount;
        res.Balances.PageIssues = prev.PageIssues;
        RecomputeCompleteness(res.Balances, res.Transactions);
        res.DiagnosticReport = BuildDiagnosticReport(res.SourceFile, res.BankDetected, res.ExtractionMethod + " + Dr/Cr confirmed by user", res.Balances, res.Transactions);
    }

    private static StatementBalanceInfo ExtractBalances(
        string rawText, List<BankTransactionRow> txns, List<List<string>> canonRows, decimal? printedOpening = null, decimal? printedClosing = null)
    {
        decimal? op = printedOpening, cl = printedClosing;
        int balCol = CanonicalColMap["balance"];

        foreach (var r in canonRows)
        {
            var line = string.Join(" ", r);
            if (op == null && OpeningRowRe.IsMatch(line))
            {
                // Prefer the number printed right after the label; fall back to the Balance cell only when it is a pure amount.
                // (HDFC's summary row has "Closing Balance : x" in the Balance column, which was being read as the OPENING balance.)
                var v = BalanceAfterLabel(line, OpeningLabelRe)
                    ?? (balCol < r.Count && IsPureAmountCell(r[balCol]) ? ParseSignedBalance(r[balCol]) : null);
                if (v.HasValue) op = v.Value;
            }
            if (ClosingRowRe.IsMatch(line))
            {
                var v = BalanceAfterLabel(line, ClosingLabelRe)
                    ?? (balCol < r.Count && IsPureAmountCell(r[balCol]) ? ParseSignedBalance(r[balCol]) : null);
                if (v.HasValue) cl = v.Value;
            }
        }

        // Also check header/summary text outside the table (e.g. ICICI / HDFC / Axis "Opening Balance : 1,23,456.78")
        if (op == null && !string.IsNullOrWhiteSpace(rawText))
            op = BalanceAfterLabel(rawText, OpeningLabelRe);
        if (cl == null && !string.IsNullOrWhiteSpace(rawText))
        {
            // The LAST printed closing balance is the statement's closing (multi-page statements print one per page)
            var all = ClosingLabelRe.Matches(rawText);
            for (int i = all.Count - 1; i >= 0 && cl == null; i--)
                cl = ParseSignedBalance(all[i].Groups[1].Value);
        }

        // SBI prints the opening only as "Balance as on 1 Nov 2026 :-38,47,078.68": it is the opening when dated on/before the
        // first transaction, the closing when dated on/after the last one.
        if ((op == null || cl == null) && txns.Count > 0 && !string.IsNullOrWhiteSpace(rawText))
        {
            var firstD = txns.Min(t => t.TxnDate) ?? ""; var lastD = txns.Max(t => t.TxnDate) ?? "";
            foreach (Match m in BalanceAsOnRe.Matches(rawText))
            {
                var d = ParseIndianDate(m.Groups["d"].Value);
                var v = ParseSignedBalance(m.Groups[1].Value);
                if (d == null || v == null) continue;
                if (op == null && string.CompareOrdinal(d, firstD) <= 0) op = v;
                else if (cl == null && string.CompareOrdinal(d, lastD) >= 0 && string.CompareOrdinal(d, firstD) > 0) cl = v;
            }
        }

        bool opPrinted = op.HasValue, clPrinted = cl.HasValue;
        bool firstRowUnproven = false;
        var withBal = txns.Where(t => t.Balance.HasValue).ToList();
        if (withBal.Count > 0)
        {
            bool isReverse = IsReverseChronological(txns);
            var chrono = isReverse ? Enumerable.Reverse(txns).ToList() : txns;

            // Verify & auto-correct the first row's DR/CR direction if Opening Balance was printed in the statement
            if (op.HasValue) FixRowDrCrFromPrevBalance(op, chrono[0]);

            // Opening = first available running balance unwound by every movement up to and including that row
            // (handles banks that print the balance only on the last transaction of each day)
            int firstBalIdx = chrono.FindIndex(t => t.Balance.HasValue);
            decimal unwind = 0;
            for (int i = 0; i <= firstBalIdx; i++) unwind += chrono[i].Debit - chrono[i].Credit;
            var calcOp = Math.Round(chrono[firstBalIdx].Balance!.Value + unwind, 2);

            int lastBalIdx = chrono.FindLastIndex(t => t.Balance.HasValue);
            decimal tail = 0;
            for (int i = lastBalIdx + 1; i < chrono.Count; i++) tail += chrono[i].Credit - chrono[i].Debit;
            var calcLastCl = Math.Round(chrono[lastBalIdx].Balance!.Value + tail, 2);
            // If the opening is derived from the first row and that row's Dr/Cr was only GUESSED, the reconciliation below
            // is circular (it would always "balance") — report it as not verifiable instead of a false "BALANCED".
            // The first row (no printed opening) can't be proven by the balance. If its narration clearly says the opposite
            // ("WDL", "UPI/DR", "TO TRANSFER" booked as a credit), do NOT trust the column — ask the user.
            if (!opPrinted)
            {
                var hint = NarrationDirectionHint(chrono[0].Narration);
                if (hint != null && hint != chrono[0].TxnType)
                    AppendWarning(chrono[0], $"Dr/Cr inferred: the column says {(chrono[0].TxnType == "DR" ? "Debit" : "Credit")} but the narration suggests {(hint == "DR" ? "Debit" : "Credit")} — please confirm");
            }
            firstRowUnproven = !opPrinted && (chrono[0].ParseWarning.Contains("inferred", StringComparison.Ordinal) || chrono[0].ParseWarning.Contains("not stated", StringComparison.Ordinal));
            op ??= calcOp;
            cl ??= calcLastCl;

            // Row-by-row Running Balance Proof over EVERY row (rows without a printed balance are carried forward),
            // pinpointing any row where prevBal - Debit + Credit != printed balance.
            decimal? running = opPrinted ? op : null;
            foreach (var curr in chrono)
            {
                if (running.HasValue) running = Math.Round(running.Value - curr.Debit + curr.Credit, 2);
                if (!curr.Balance.HasValue) continue;
                if (running.HasValue)
                {
                    decimal expected = running.Value;
                    decimal rowDiff = Math.Round(expected - curr.Balance.Value, 2);
                    if (Math.Abs(rowDiff) > BalanceTolerance)
                    {
                        curr.HasBalanceBreak = true;
                        curr.BalanceBreakNote = $"⚠ Balance Break: expected ₹{expected:N2}, got ₹{curr.Balance.Value:N2} (Diff ₹{rowDiff:N2}) — a row may be missing or mis-read above this one";
                    }
                }
                running = curr.Balance.Value;
            }
        }

        var totDr = Math.Round(txns.Sum(t => t.Debit), 2);
        var totCr = Math.Round(txns.Sum(t => t.Credit), 2);
        decimal? calcCl = op.HasValue ? Math.Round(op.Value - totDr + totCr, 2) : null;
        decimal diff = calcCl.HasValue && cl.HasValue ? Math.Round(calcCl.Value - cl.Value, 2) : 0;
        var dates = txns.Select(t => t.TxnDate).OrderBy(d => d, StringComparer.Ordinal).ToList();

        return new StatementBalanceInfo
        {
            StatementOpening = op,
            StatementClosing = cl,
            CalculatedClosing = calcCl,
            TotalDebit = totDr,
            TotalCredit = totCr,
            StatementDiff = diff,
            StatementBalanced = calcCl.HasValue && cl.HasValue && !firstRowUnproven ? Math.Abs(diff) <= BalanceTolerance : null,
            FromDate = dates.FirstOrDefault() ?? "",
            ToDate = dates.LastOrDefault() ?? "",
            HasRunningBalance = withBal.Count > 0,
            BalanceBreakCount = txns.Count(t => t.HasBalanceBreak),
            ParseWarningCount = txns.Count(t => !string.IsNullOrEmpty(t.ParseWarning)),
            OpeningPrinted = opPrinted,
            ClosingPrinted = clPrinted
        };
    }
    private static string BuildDiagnosticReport(string fileName, string bank, string method, StatementBalanceInfo bal, List<BankTransactionRow> txns)
    {
        var sb = new StringBuilder();
        sb.AppendLine($"=== Auto Bank Statement Entry — Parser Diagnostic ===");
        sb.AppendLine($"File: {fileName} | Bank: {bank} | Method: {method}");
        sb.AppendLine($"Rows Parsed: {txns.Count} | Period: {bal.FromDate} to {bal.ToDate}");
        sb.AppendLine($"Opening: {bal.StatementOpening:N2} | Total Dr: {bal.TotalDebit:N2} | Total Cr: {bal.TotalCredit:N2} | Closing: {bal.StatementClosing:N2} | Calc Closing: {bal.CalculatedClosing:N2} | Diff: {bal.StatementDiff:N2}");
        sb.AppendLine($"Opening printed in statement: {(bal.OpeningPrinted ? "Yes" : "No (derived from first row)")} | Closing printed: {(bal.ClosingPrinted ? "Yes" : "No (derived from last row)")} | Running balance column: {(bal.HasRunningBalance ? "Yes" : "NO — completeness cannot be proven row-by-row")}");
        sb.AppendLine($"Reconciliation: {(bal.StatementBalanced == true ? "BALANCED ✓" : bal.StatementBalanced == false ? $"NOT BALANCED (diff {bal.StatementDiff:N2})" : "Not verifiable")}");
        sb.AppendLine($"Printed totals: Dr {(bal.PrintedTotalDebit is decimal ptd ? ptd.ToString("N2") : "not printed")} | Cr {(bal.PrintedTotalCredit is decimal ptc ? ptc.ToString("N2") : "not printed")}"
            + (bal.PrintedDebitCount is int pdc ? $" | Dr count {pdc}" : "") + (bal.PrintedCreditCount is int pcc ? $" | Cr count {pcc}" : ""));
        sb.AppendLine($"Completeness checks: {(bal.CompletenessIssues.Count == 0 ? "OK" : "FAILED")}");
        foreach (var ci in bal.CompletenessIssues) sb.AppendLine($"  [INCOMPLETE] {ci}");
        var breaks = txns.Where(t => t.HasBalanceBreak).ToList();
        sb.AppendLine($"Balance Breaks: {breaks.Count}");
        foreach (var b in breaks.Take(20))
            sb.AppendLine($"  [BREAK] {b.DisplayDate} | {b.TxnType} {b.Amount:N2} | Bal {b.Balance:N2} | {b.BalanceBreakNote} | {b.Narration}");
        var warns = txns.Where(t => !string.IsNullOrEmpty(t.ParseWarning)).ToList();
        sb.AppendLine($"Parse Warnings: {warns.Count}");
        foreach (var w in warns.Take(20))
            sb.AppendLine($"  [WARN] {w.DisplayDate} | {w.TxnType} {w.Amount:N2} | {w.ParseWarning} | {w.Narration}");
        sb.AppendLine("\n--- First 25 Parsed Rows ---");
        foreach (var t in txns.Take(25))
            sb.AppendLine($"  {t.DisplayDate} | {t.TxnType,-2} | {t.Amount,12:N2} | Bal: {t.Balance,12:N2} | Ref: {t.RefNo} | {t.Narration}");
        return sb.ToString();
    }

    private static string DetectPaymentMode(string narr)
    {
        // Whole-word matching: "CASHFREE" (payment gateway) / "BATMAN" must not become Cash/ATM
        if (PayModeUpiRe.IsMatch(narr)) return "UPI";
        if (PayModeNeftRe.IsMatch(narr)) return "NEFT";
        if (PayModeRtgsRe.IsMatch(narr)) return "RTGS";
        if (PayModeImpsRe.IsMatch(narr)) return "IMPS";
        if (PayModeCashRe.IsMatch(narr)) return "Cash/ATM";
        if (PayModeChqRe.IsMatch(narr)) return "Cheque";
        return "Bank Transfer";
    }

    private static string ExtractRef(string narr)
    {
        var m = RefExtractRe.Match(narr);
        return m.Success ? m.Groups[1].Value : "";
    }

    private static string ShortHash(string seed)
    {
        var bytes = SHA1.HashData(Encoding.UTF8.GetBytes(seed));
        return Convert.ToHexString(bytes)[..12].ToLowerInvariant();
    }

    // =====================================================================================================================
    //  SAVED LAYOUTS ("Teach Columns") — a user marks the columns of an unfamiliar statement ONCE; every PC then parses that
    //  format with those exact column edges. A layout is only ever used when its result is proven by the running balance.
    // =====================================================================================================================

    public static readonly string[] TeachableRoles = ["ignore", "date", "value_date", "narration", "ref_no", "debit", "credit", "amount", "drcr", "balance"];

    public sealed record PdfWordInfo(string Text, double X, double Y, double W, double H);

    public sealed class PdfPageSnapshot
    {
        public int Number { get; init; }
        public double Width { get; init; }
        public double Height { get; init; }
        public List<PdfWordInfo> Words { get; init; } = [];
        /// <summary>Suggested column edges (absolute x, left to right) and the role of each column, from auto-detection.</summary>
        public List<double> SuggestedEdges { get; init; } = [];
        public List<string> SuggestedRoles { get; init; } = [];
        /// <summary>Number of lines that start with a date — pages without a transaction table have 0.</summary>
        public int DatedLineCount { get; init; }
    }

    public sealed class PdfLayoutSnapshot
    {
        public string Bank { get; init; } = "";
        public List<PdfPageSnapshot> Pages { get; init; } = [];
        /// <summary>Index (0-based) of the page that best shows the transaction table — NOT necessarily the first page.</summary>
        public int SuggestedPageIndex { get; init; }
    }

    /// <summary>Everything the Teach Columns window needs to draw the pages and pre-fill the dividers.</summary>
    public static PdfLayoutSnapshot ReadPdfLayout(string path, string? password)
    {
        var opts = string.IsNullOrEmpty(password) ? new ParsingOptions() : new ParsingOptions { Password = password };
        using var doc = PdfDocument.Open(path, opts);
        var infos = ReadPdfPageLayouts(doc);
        var text = string.Join("\n", infos.Take(2).SelectMany(pi => pi.Lines).Select(l => string.Join(" ", l.Select(w => w.Text))));
        var (bank, _) = DetectBankAndAccount(text.Length > 4000 ? text[..4000] : text);
        var bestHeader = infos.Where(pi => pi.Header != null).OrderByDescending(pi => pi.Header!.Count).Select(pi => pi.Header).FirstOrDefault();
        var bestInferred = infos.Where(pi => pi.Inferred != null).OrderByDescending(pi => pi.Inferred!.Count).Select(pi => pi.Inferred).FirstOrDefault();
        var pages = new List<PdfPageSnapshot>();
        foreach (var pi in infos)
        {
            var anchors = pi.Header ?? pi.Inferred ?? bestHeader ?? bestInferred;
            var words = pi.Lines.SelectMany(l => l).Select(w => new PdfWordInfo(w.Text, w.X, w.Y, w.W, w.H)).ToList();
            // a transaction line STARTS with its date (or has it right after a serial number); "Period : 01-10-2026 to …"
            // on a cover page does not count
            int dated = pi.Lines.Count(l => l.Count > 0 && (
                ParseIndianDate(l[0].Text) != null
                || (l.Count > 1 && Regex.IsMatch(l[0].Text, @"^\d{1,4}\.?$") && ParseIndianDate(l[1].Text) != null)
                || (Regex.IsMatch(l[0].Text, @"^\d{1,2}$") && ParseIndianDate(string.Join(" ", l.Take(3).Select(w => w.Text))) != null)));
            var (edges, roles) = SuggestColumns(pi, anchors);
            pages.Add(new PdfPageSnapshot { Number = pi.Number, Width = pi.Width, Height = pi.Height, Words = words,
                SuggestedEdges = edges, SuggestedRoles = roles, DatedLineCount = dated });
        }
        int suggested = pages.Count == 0 ? 0 : pages.IndexOf(pages.OrderByDescending(p => p.DatedLineCount).ThenBy(p => p.Number).First());
        return new PdfLayoutSnapshot { Bank = bank, Pages = pages, SuggestedPageIndex = Math.Max(0, suggested) };
    }

    private static (List<double> edges, List<string> roles) SuggestColumns(PdfPageLayout pi, Dictionary<string, double>? anchors)
    {
        var all = pi.Lines.SelectMany(l => l).ToList();
        if (all.Count == 0) return (new List<double>(), new List<string>());
        if (anchors == null || anchors.Count < 2)
        {
            // Nothing recognised: offer the empty gaps between columns as dividers, every column "ignore"
            var (gapXs, tableLines) = ColumnGapsFromContent(pi.Lines);
            var tl = tableLines.SelectMany(l => l).ToList();
            if (gapXs.Count < 2 || tl.Count == 0) return (new List<double>(), new List<string>());
            var e = new List<double> { tl.Min(w => w.X) - 2 };
            e.AddRange(gapXs.Where(x => x > e[0] + 4).OrderBy(x => x));
            e.Add(Math.Max(e[^1] + 10, tl.Max(w => w.X2) + 2));
            return (e, Enumerable.Repeat("ignore", e.Count - 1).ToList());
        }
        var ordered = anchors.OrderBy(a => a.Value).ToList();
        var edgesOut = new List<double>();
        for (int i = 0; i < ordered.Count - 1; i++)
        {
            double lo = ordered[i].Value, hi = ordered[i + 1].Value, mid = (lo + hi) / 2;
            var between = pi.GridXs.Where(g => g > lo + 2 && g < hi - 2).ToList();
            edgesOut.Add(between.Count > 0 ? between.OrderBy(g => Math.Abs(g - mid)).First() : mid);
        }
        // Outer edges: the drawn border, else the extent of the words in the first / last column
        double firstEdge = edgesOut.Count > 0 ? edgesOut[0] : ordered[0].Value + 40;
        double left = pi.GridXs.Where(g => g < ordered[0].Value - 2).DefaultIfEmpty(double.NaN).Max();
        if (double.IsNaN(left)) left = all.Where(w => w.Xc < firstEdge).Select(w => w.X).DefaultIfEmpty(ordered[0].Value - 30).Min() - 2;
        double lastEdge = edgesOut.Count > 0 ? edgesOut[^1] : ordered[^1].Value - 40;
        double right = pi.GridXs.Where(g => g > ordered[^1].Value + 2).DefaultIfEmpty(double.NaN).Min();
        if (double.IsNaN(right)) right = all.Where(w => w.Xc > lastEdge).Select(w => w.X2).DefaultIfEmpty(ordered[^1].Value + 30).Max() + 2;
        var edgesAll = new List<double> { left };
        edgesAll.AddRange(edgesOut);
        edgesAll.Add(right);
        var roles = ordered.Select(a => TeachableRoles.Contains(a.Key) ? a.Key : "ignore").ToList();
        return (edgesAll, roles);
    }

    /// <summary>Lower-case heading words (letters only, 2+ chars), de-duplicated and sorted — robust to wrapping and spacing.</summary>
    public static string NormalizeHeaderSignature(IEnumerable<string> words) =>
        string.Join(" ", words.SelectMany(w => Regex.Split(w.ToLowerInvariant(), "[^a-z]+")).Where(w => w.Length >= 2).Distinct().OrderBy(w => w, StringComparer.Ordinal));

    private static double SignatureSimilarity(string a, string b)
    {
        var sa = a.Split(' ', StringSplitOptions.RemoveEmptyEntries).ToHashSet();
        var sb = b.Split(' ', StringSplitOptions.RemoveEmptyEntries).ToHashSet();
        if (sa.Count < 2 || sb.Count < 2) return 0;
        return (double)sa.Intersect(sb).Count() / sa.Union(sb).Count();
    }

    private static string TemplateCellText(List<WordBox> line, List<double> edges, int col) =>
        string.Join(" ", line.Where(w => w.Xc >= edges[col] && w.Xc < edges[col + 1]).OrderBy(w => w.X).Select(w => w.Text));

    private static bool TemplateLineHasDate(List<WordBox> line, List<double> edges, List<string> roles)
    {
        for (int c = 0; c < roles.Count; c++)
        {
            if (roles[c] is not ("date" or "value_date")) continue;
            var t = TemplateCellText(line, edges, c);
            if (t.Length > 0 && (ParseIndianDate(t) != null || PartialDateRe.IsMatch(t))) return true;
        }
        return false;
    }

    /// <summary>Heading words just above the first transaction on the page (wrapped headings included), for matching later.</summary>
    public static string ComputeHeaderSignature(string path, string? password, LayoutTemplate t, int pageNumber)
    {
        var opts = string.IsNullOrEmpty(password) ? new ParsingOptions() : new ParsingOptions { Password = password };
        using var doc = PdfDocument.Open(path, opts);
        var pi = ReadPdfPageLayouts(doc).FirstOrDefault(p => p.Number == pageNumber);
        if (pi == null) return "";
        var edges = t.Boundaries.Select(f => f * pi.Width).ToList();
        var lines = ClipToTable(pi.Lines, edges);
        int first = lines.FindIndex(l => TemplateLineHasDate(l, edges, t.Roles));
        if (first <= 0) return "";
        // The heading is the 1–3 consecutive lines (within 10 lines above the first transaction) with the most column-heading
        // words — NOT simply the lines right above it: centred cells put a description's first lines above its date.
        string best = ""; int bestHits = 1;
        for (int i = Math.Max(0, first - 10); i < first; i++)
            for (int k = 1; k <= 3 && i + k <= first; k++)
            {
                var words = lines.Skip(i).Take(k).SelectMany(l => l).Select(w => w.Text).ToList();
                if (words.Any(w => ParseIndianDate(w) != null || MoneyDecimalRe.IsMatch(w))) continue;
                var sig = NormalizeHeaderSignature(words);
                int hits = sig.Split(' ', StringSplitOptions.RemoveEmptyEntries).Count(HeadingVocabulary.Contains);
                if (hits > bestHits || (hits == bestHits && hits > 1 && sig.Length < best.Length)) { bestHits = hits; best = sig; }
            }
        return bestHits >= 2 ? best : "";
    }

    /// <summary>Column-heading / bank-name words — never sensitive, and needed to recognise a layout (used by the anonymiser).</summary>
    public static bool IsLayoutWord(string word)
    {
        var w = word.ToLowerInvariant();
        return HeadingVocabulary.Contains(w) || ScheduledBanks.Any(b => b.code.Equals(word, StringComparison.OrdinalIgnoreCase)
            || b.ifsc.Equals(word, StringComparison.OrdinalIgnoreCase) || b.names.Any(n => n.Split(' ').Contains(w)));
    }

    private static readonly HashSet<string> HeadingVocabulary = ColumnAliases.Values.SelectMany(a => a)
        .SelectMany(a => Regex.Split(a.ToLowerInvariant(), "[^a-z]+")).Where(w => w.Length >= 2).ToHashSet();

    private static List<List<WordBox>> ClipToTable(List<List<WordBox>> lines, List<double> edges) =>
        lines.Select(l => l.Where(w => w.Xc >= edges[0] - 3 && w.Xc <= edges[^1] + 3).ToList()).Where(l => l.Count > 0).ToList();

    /// <summary>Parse a PDF with a saved layout. <paramref name="signatureMatched"/> tells whether the layout's heading was found.</summary>
    public static ParsedStatementResult ParsePdfWithTemplate(string path, string? password, LayoutTemplate t) =>
        ParsePdfWithTemplateCore(path, Path.GetFileName(path), password, t, out _);

    private static ParsedStatementResult ParsePdfWithTemplateCore(string path, string fileName, string? password, LayoutTemplate t, out bool signatureMatched)
    {
        signatureMatched = false;
        if (t.Roles.Count < 2 || t.Boundaries.Count != t.Roles.Count + 1)
            throw new InvalidOperationException($"Saved layout '{t.Name}' is incomplete.");
        var opts = string.IsNullOrEmpty(password) ? new ParsingOptions() : new ParsingOptions { Password = password };
        var fullTextSb = new StringBuilder();
        var pageTexts = new List<string>();
        var canonicalRows = new List<List<string>>();
        var diag = new StringBuilder();
        try
        {
            using var doc = PdfDocument.Open(path, opts);
            foreach (var pi in ReadPdfPageLayouts(doc))
            {
                foreach (var ln in pi.Lines) fullTextSb.AppendLine(string.Join(" ", ln.Select(w => w.Text)));
                pageTexts.Add(string.Join("\n", pi.Lines.Select(l => string.Join(" ", l.Select(w => w.Text)))));
                var edges = t.Boundaries.Select(f => f * pi.Width).ToList();
                // Every column is an anchor ("ignore" columns too, so their words never spill into a neighbour)
                var anchors = new Dictionary<string, double>();
                for (int c = 0; c < t.Roles.Count; c++)
                {
                    var key = t.Roles[c] == "ignore" || anchors.ContainsKey(t.Roles[c]) ? $"ignore{c}" : t.Roles[c];
                    anchors[key] = (edges[c] + edges[c + 1]) / 2.0;
                }
                var lines = ClipToTable(pi.Lines, edges);

                int start = 0;
                if (!string.IsNullOrEmpty(t.HeaderSignature))
                {
                    for (int i = 0; i < lines.Count; i++)
                    {
                        var one = NormalizeHeaderSignature(lines[i].Select(w => w.Text));
                        var two = i + 1 < lines.Count ? NormalizeHeaderSignature(lines[i].Concat(lines[i + 1]).Select(w => w.Text)) : one;
                        var three = i + 2 < lines.Count ? NormalizeHeaderSignature(lines[i].Concat(lines[i + 1]).Concat(lines[i + 2]).Select(w => w.Text)) : two;
                        if (new[] { one, two, three }.Any(sg => SignatureSimilarity(sg, t.HeaderSignature) >= 0.6))
                        {
                            signatureMatched = true;
                            start = i + 1;
                            break;
                        }
                    }
                }
                int firstRow = lines.FindIndex(start, l => TemplateLineHasDate(l, edges, t.Roles));
                if (firstRow < 0)
                {
                    diag.AppendLine($"  Page {pi.Number}: saved layout '{t.Name}' — no dated rows on this page");
                    continue;
                }
                var dataLines = ReorderLinesWithinRowBands(lines.Skip(firstRow).ToList(), pi.RuleYs, anchors);
                var (rows, colMap) = LinesToTableRows(dataLines, anchors, edges);
                canonicalRows.AddRange(NormalizeRowsToCanonical(rows, colMap));
                diag.AppendLine($"  Page {pi.Number}: saved layout '{t.Name}' from line {firstRow + 1} → columns: "
                    + string.Join(", ", t.Roles.Select((r, c) => $"{r}@{edges[c]:F0}-{edges[c + 1]:F0}")));
            }
        }
        catch (Exception ex) when (ex.Message.Contains("password", StringComparison.OrdinalIgnoreCase) || ex.Message.Contains("encrypt", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException($"'{fileName}' is password-protected or the PDF password is incorrect.");
        }

        var fullText = fullTextSb.ToString();
        var (bank, acc) = DetectBankAndAccount(fullText.Length > 4000 ? fullText[..4000] : fullText);
        bool sepDrCr = t.Roles.Contains("debit") || t.Roles.Contains("credit");
        var txns = canonicalRows.Count > 0 ? BuildTransactions(canonicalRows, sepDrCr, bank, fileName) : [];
        foreach (var x in txns.Where(x => (x.Narration?.Length ?? 0) > 400))
            x.ParseWarning = (string.IsNullOrEmpty(x.ParseWarning) ? "" : x.ParseWarning + "; ")
                + "Layout not understood: this row's description is unusually long and probably contains several transactions — check against the PDF";
        var bal = ExtractBalances(fullText, txns, canonicalRows);
        ApplyCompletenessChecks(bal, fullText, txns, pageTexts);
        var method = $"Digital PDF (saved layout '{t.Name}')";
        return new ParsedStatementResult
        {
            SourceFile = fileName,
            SourcePath = path,
            BankDetected = bank,
            AccountNumberDetected = acc,
            ExtractionMethod = method,
            Balances = bal,
            Transactions = txns,
            LayoutTemplateUsed = t.Name,
            DiagnosticReport = BuildDiagnosticReport(fileName, bank, method, bal, txns) + "\n--- PDF Layout (saved layout) ---\n" + diag
        };
    }

    /// <summary>A result that is proven complete: rows found, running balance reconciles, no warnings, no completeness issue.</summary>
    public static bool IsProvenGood(ParsedStatementResult r) =>
        r.Transactions.Count > 0 && r.Balances.StatementBalanced == true && r.Balances.ParseWarningCount == 0 && r.Balances.CompletenessIssues.Count == 0;

    /// <summary>
    /// Try the saved layouts for this bank and keep whichever result is PROVEN by the running balance:
    /// 1) a layout whose heading matches this file, 2) the automatic parse, 3) any other layout of the bank.
    /// An unproven layout result never replaces the automatic one.
    /// </summary>
    private static ParsedStatementResult ChooseWithTemplates(string path, string fileName, string? password, ParsedStatementResult auto, IReadOnlyList<LayoutTemplate> templates)
    {
        bool autoUnknownBank = auto.BankDetected.StartsWith("Scheduled Bank", StringComparison.OrdinalIgnoreCase);
        var candidates = templates.Where(t => string.IsNullOrEmpty(t.Bank) || autoUnknownBank
                                              || string.Equals(t.Bank, auto.BankDetected, StringComparison.OrdinalIgnoreCase)).ToList();
        if (candidates.Count == 0) return auto;
        var tried = new List<(ParsedStatementResult res, bool sig)>();
        var notes = new StringBuilder();
        foreach (var t in candidates)
        {
            try
            {
                var r = ParsePdfWithTemplateCore(path, fileName, password, t, out var sig);
                tried.Add((r, sig));
                notes.AppendLine($"  Saved layout '{t.Name}': {r.Transactions.Count} rows, heading {(sig ? "matched" : "not found")}, "
                    + $"balances {(r.Balances.StatementBalanced == true ? "reconcile ✓" : r.Balances.StatementBalanced == false ? "do NOT reconcile" : "not provable")}"
                    + (r.Balances.CompletenessIssues.Count > 0 ? $", issues: {string.Join("; ", r.Balances.CompletenessIssues)}" : ""));
            }
            catch (Exception ex) { notes.AppendLine($"  Saved layout '{t.Name}': failed — {ex.Message}"); }
        }
        ParsedStatementResult? pick =
            tried.Where(x => x.sig && IsProvenGood(x.res)).OrderByDescending(x => x.res.Transactions.Count).Select(x => x.res).FirstOrDefault()
            ?? (IsProvenGood(auto) ? auto : null)
            ?? tried.Where(x => IsProvenGood(x.res)).OrderByDescending(x => x.res.Transactions.Count).Select(x => x.res).FirstOrDefault()
            ?? auto;
        pick.DiagnosticReport += "\n--- Saved layouts tried ---\n" + notes
            + $"  → used: {(ReferenceEquals(pick, auto) ? "automatic detection" : "saved layout '" + pick.LayoutTemplateUsed + "'")}\n";
        return pick;
    }


    // =====================================================================================================================
    //  COMPLETENESS SELF-CHECKS — prove nothing is missing, beyond the running balance:
    //  * totals the statement itself prints (a missing FIRST or LAST row keeps the running balance consistent, but not these)
    //  * "Page x of N" numbers (a missing or repeated page)
    // =====================================================================================================================

    private const string TotalAmountPattern = @"\s*(?:\(?(?:rs\.?|inr|₹)\)?\s*)?[:\-]?\s*(?:rs\.?|inr|₹)?\s*((?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2})(?![\d,])";
    private static readonly Regex PrintedTotalDebitRe = new(@"(?<![a-z])total\s+(?:of\s+)?(?:debits?|withdrawals?|dr\.?|payments?)(?:\s+amount)?(?!\s*card)" + TotalAmountPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PrintedTotalCreditRe = new(@"(?<![a-z])total\s+(?:of\s+)?(?:credits?|deposits?|cr\.?|receipts?)(?:\s+amount)?(?!\s*card)" + TotalAmountPattern, RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex PageOfRe = new(@"(?<![a-z])page\s*(?:no\.?\s*)?:?\s*(\d{1,3})\s*(?:of|/)\s*(\d{1,3})(?!\d)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private const string PeriodDate = @"\d{1,2}[\s\-/.](?:[A-Za-z]{3,9}|\d{1,2})[\s\-/.,]*\d{2,4}";
    private static readonly Regex StatementPeriodRe = new(@"(?<![a-z])(?:from|period)\s*[:\-]?\s*(?<a>" + PeriodDate + @")\s*(?:to|till|upto|-)\s*:?\s*(?<b>" + PeriodDate + ")",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex SummaryNumberRe = new(@"^-?(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{2})?$", RegexOptions.Compiled);

    /// <summary>Reads the printed totals and page numbers into <paramref name="bal"/> and evaluates them.</summary>
    public static void ApplyCompletenessChecks(StatementBalanceInfo bal, string fullText, List<BankTransactionRow> txns, List<string>? pageTexts)
    {
        if (!string.IsNullOrWhiteSpace(fullText))
        {
            bal.PrintedTotalDebit = PickPrintedTotal(PrintedTotalDebitRe, fullText, bal.TotalDebit);
            bal.PrintedTotalCredit = PickPrintedTotal(PrintedTotalCreditRe, fullText, bal.TotalCredit);
            ReadSummaryTable(bal, fullText);
        }
        bal.PageIssues = pageTexts == null ? new List<string>() : CheckPageNumbers(pageTexts);
        // Rows dated outside the period printed at the top ("Statement from 01-10-2026 to 31-10-2026") were mis-read
        // (usually a wrong year) — they would post into the wrong period in Tally.
        var head = fullText.Length > 3000 ? fullText[..3000] : fullText;
        var pm = StatementPeriodRe.Match(head);
        if (pm.Success && ParseIndianDate(pm.Groups["a"].Value) is string pa && ParseIndianDate(pm.Groups["b"].Value) is string pb
            && string.CompareOrdinal(pa, pb) <= 0 && txns.Count > 0)
        {
            var outside = txns.Where(t => string.CompareOrdinal(t.TxnDate, pa) < 0 || string.CompareOrdinal(t.TxnDate, pb) > 0).ToList();
            if (outside.Count > 0)
                bal.PageIssues.Add($"{outside.Count} row(s) are dated outside the statement period {FormatDisplayDate(pa)} – {FormatDisplayDate(pb)} "
                    + $"(e.g. {outside[0].DisplayDate}) — dates were mis-read");
        }
        RecomputeCompleteness(bal, txns);
    }

    /// <summary>Several "Total Debit" figures (page sub-totals + grand total): any one that equals our total proves it; else the last.</summary>
    private static decimal? PickPrintedTotal(Regex re, string text, decimal ours)
    {
        var vals = re.Matches(text).Select(m => ParseIndianAmount(m.Groups[1].Value).amt).Where(v => v > 0).ToList();
        if (vals.Count == 0) return null;
        if (vals.Contains(ours)) return ours;
        if (vals.Count > 1 && vals.Sum() == ours) return ours; // page-wise sub-totals only
        return vals[^1];
    }

    /// <summary>HDFC-style summary: a heading line with "Dr Count", "Cr Count", "Debits", "Credits" and a line of numbers below.</summary>
    private static void ReadSummaryTable(StatementBalanceInfo bal, string text)
    {
        // Split on \r AND \n: on Windows the page text ends lines with "\r\n", and a trailing "\r" made the last number fail
        var lines = text.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries);
        for (int i = 0; i < lines.Length - 1; i++)
        {
            var h = lines[i].ToLowerInvariant();
            if (!(h.Contains("dr count") && h.Contains("cr count") && h.Contains("debits") && h.Contains("credits"))) continue;
            for (int j = i + 1; j < Math.Min(lines.Length, i + 4); j++)
            {
                var nums = lines[j].Split(' ', StringSplitOptions.RemoveEmptyEntries).Where(t => SummaryNumberRe.IsMatch(t)).ToList();
                if (nums.Count < 6) continue;
                // Opening | Dr Count | Cr Count | Debits | Credits | Closing
                if (int.TryParse(nums[1].Replace(",", ""), NumberStyles.Integer, CultureInfo.InvariantCulture, out var dc)) bal.PrintedDebitCount = dc;
                if (int.TryParse(nums[2].Replace(",", ""), NumberStyles.Integer, CultureInfo.InvariantCulture, out var cc)) bal.PrintedCreditCount = cc;
                bal.PrintedTotalDebit ??= ParseIndianAmount(nums[3]).amt;
                bal.PrintedTotalCredit ??= ParseIndianAmount(nums[4]).amt;
                return;
            }
        }
    }

    private static List<string> CheckPageNumbers(List<string> pageTexts)
    {
        var issues = new List<string>();
        var seen = new Dictionary<int, int>();   // printed page number -> file page
        int declared = 0;
        for (int p = 0; p < pageTexts.Count; p++)
        {
            var m = PageOfRe.Match(pageTexts[p]);
            if (!m.Success) continue;
            int x = int.Parse(m.Groups[1].Value, CultureInfo.InvariantCulture), n = int.Parse(m.Groups[2].Value, CultureInfo.InvariantCulture);
            if (x < 1 || n < 1 || x > n || n > 999) continue;
            declared = Math.Max(declared, n);
            if (seen.TryGetValue(x, out var firstAt))
                issues.Add($"Page {x} appears twice (file pages {firstAt + 1} and {p + 1}) — rows may be counted twice");
            else seen[x] = p;
        }
        if (declared > 0 && declared > pageTexts.Count)
            issues.Add($"The statement says it has {declared} pages but this file has only {pageTexts.Count} — pages are missing");
        return issues;
    }

    /// <summary>Re-evaluates the printed-totals / page checks (call again after the user changes a row's Dr/Cr).</summary>
    public static void RecomputeCompleteness(StatementBalanceInfo bal, List<BankTransactionRow> txns)
    {
        var issues = new List<string>(bal.PageIssues);
        if (txns.Count > 0)
        {
            if (bal.PrintedTotalDebit is decimal pd && pd != bal.TotalDebit)
                issues.Add($"Statement prints Total Debits ₹{pd:N2} but ₹{bal.TotalDebit:N2} was read — rows are missing or mis-read");
            if (bal.PrintedTotalCredit is decimal pc && pc != bal.TotalCredit)
                issues.Add($"Statement prints Total Credits ₹{pc:N2} but ₹{bal.TotalCredit:N2} was read — rows are missing or mis-read");
            int drN = txns.Count(t => t.TxnType == "DR"), crN = txns.Count(t => t.TxnType == "CR");
            if (bal.PrintedDebitCount is int dc && dc != drN) issues.Add($"Statement prints {dc} debit entries but {drN} were read");
            if (bal.PrintedCreditCount is int cc && cc != crN) issues.Add($"Statement prints {cc} credit entries but {crN} were read");
        }
        bal.CompletenessIssues = issues;
    }

}
