using System.Text.Json;
using System.IO;
using AutoBankStatementEntry.Models;
using Microsoft.Data.Sqlite;

namespace AutoBankStatementEntry.Services;

public class DatabaseService
{
    public string DataDir { get; }
    public string ExportDir { get; }
    public string BackupDir { get; }
    private readonly string _connStr;

    public DatabaseService(string? customDataDir = null)
    {
        if (!string.IsNullOrWhiteSpace(customDataDir))
        {
            DataDir = customDataDir.Trim();
        }
        else
        {
            var baseDir = AppContext.BaseDirectory;
            // Optional data_path.txt beside .exe lets an office point to a shared server folder (e.g. \\SERVER\Share\TallyMLData)
            var overrideFile = Path.Combine(baseDir, "data_path.txt");
            if (File.Exists(overrideFile))
            {
                var custom = File.ReadAllText(overrideFile).Trim();
                DataDir = string.IsNullOrWhiteSpace(custom) ? Path.Combine(baseDir, "data") : custom;
            }
            else
            {
                DataDir = Path.Combine(baseDir, "data");
            }
        }

        ExportDir = Path.Combine(DataDir, "exports");
        BackupDir = Path.Combine(DataDir, "tally_backups");

        var dbPath = Path.Combine(DataDir, "abse.db");
        // Pooling=False releases SMB network file handles immediately so 2-10 office PCs never lock each other out
        _connStr = new SqliteConnectionStringBuilder
        {
            DataSource = dbPath,
            Mode = SqliteOpenMode.ReadWriteCreate,
            Pooling = false,
            DefaultTimeout = 15
        }.ToString();
    }

    private bool _initialized;
    private readonly object _initLock = new();

    public void EnsureInitialized()
    {
        if (_initialized) return;
        lock (_initLock)
        {
            if (_initialized) return;
            Directory.CreateDirectory(DataDir);
            Directory.CreateDirectory(ExportDir);
            Directory.CreateDirectory(BackupDir);
            InitSchema();
            _initialized = true;
        }
    }

    private SqliteConnection Open(bool skipInit = false)
    {
        if (!skipInit && !_initialized) EnsureInitialized();
        var conn = new SqliteConnection(_connStr);
        conn.Open();
        using var pragma = conn.CreateCommand();
        pragma.CommandText = "PRAGMA busy_timeout=15000;";
        pragma.ExecuteNonQuery();
        return conn;
    }

    private static void WithWriteRetry(Action action)
    {
        for (int attempt = 0; attempt < 6; attempt++)
        {
            try
            {
                action();
                return;
            }
            catch (SqliteException ex) when (ex.SqliteErrorCode is 5 or 6 && attempt < 5)
            {
                Thread.Sleep(150 * (attempt + 1));
            }
        }
    }

    public (int maxMlId, int maxPgId) GetMlWatermark()
    {
        using var conn = Open();
        int Scalar(string sql)
        {
            using var c = conn.CreateCommand();
            c.CommandText = sql;
            var v = c.ExecuteScalar();
            return v == null || v == DBNull.Value ? 0 : Convert.ToInt32(v);
        }
        return (
            Scalar("SELECT COALESCE(MAX(id), 0) FROM ml_training_examples;"),
            Scalar("SELECT COALESCE(MAX(id), 0) FROM ml_parent_groups;")
        );
    }

    private void InitSchema()
    {
        WithWriteRetry(() => {
        using var conn = Open(skipInit: true);
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=NORMAL;
            DROP TABLE IF EXISTS own_bank_accounts;
            CREATE TABLE IF NOT EXISTS company_bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                tally_ledger_name TEXT NOT NULL,
                bank_name TEXT DEFAULT '',
                account_number TEXT DEFAULT '',
                ifsc TEXT DEFAULT '',
                aliases TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(company_name, tally_ledger_name)
            );
            CREATE TABLE IF NOT EXISTS ml_training_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                narration TEXT NOT NULL,
                normalized_text TEXT NOT NULL,
                counterparty_key TEXT DEFAULT '',
                txn_type TEXT NOT NULL,
                voucher_type TEXT NOT NULL,
                ledger_name TEXT NOT NULL,
                source TEXT DEFAULT 'user_review',
                company_name TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posted_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                txn_hash TEXT NOT NULL UNIQUE,
                voucher_guid TEXT NOT NULL,
                txn_date TEXT NOT NULL,
                amount REAL NOT NULL,
                txn_type TEXT NOT NULL,
                voucher_type TEXT NOT NULL,
                bank_ledger TEXT NOT NULL,
                counterparty_ledger TEXT NOT NULL,
                ref_no TEXT DEFAULT '',
                narration TEXT DEFAULT '',
                contra_signature TEXT DEFAULT '',
                posted_to_tally INTEGER DEFAULT 0,
                company_name TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_posted_date ON posted_transactions(txn_date, amount);
            CREATE TABLE IF NOT EXISTS ml_parent_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ledger_name TEXT NOT NULL,
                parent_group TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ml_source ON ml_training_examples(source);
            CREATE TABLE IF NOT EXISTS posted_statement_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                file_name TEXT NOT NULL,
                company_name TEXT NOT NULL,
                bank_ledger TEXT NOT NULL,
                posted_by TEXT NOT NULL,
                posted_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_psf_hash ON posted_statement_files(file_hash, company_name);
            CREATE TABLE IF NOT EXISTS posted_batches (
                batch_id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                bank_ledger TEXT NOT NULL,
                posted_by TEXT NOT NULL,
                entry_count INTEGER NOT NULL,
                total_debit REAL NOT NULL,
                total_credit REAL NOT NULL,
                from_date TEXT DEFAULT '',
                to_date TEXT DEFAULT '',
                vouchers_json TEXT NOT NULL,
                rolled_back INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS layout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                bank TEXT NOT NULL DEFAULT '',
                header_sig TEXT NOT NULL DEFAULT '',
                boundaries_json TEXT NOT NULL,
                roles_json TEXT NOT NULL,
                sample_file TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS statement_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                bank_ledger TEXT NOT NULL,
                from_date TEXT NOT NULL,
                to_date TEXT NOT NULL,
                opening REAL NOT NULL,
                closing REAL NOT NULL,
                source_file TEXT NOT NULL DEFAULT '',
                recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sh_acct ON statement_history(company_name, bank_ledger, to_date);
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS remembered_splits (
                company_name TEXT NOT NULL,
                party_key TEXT NOT NULL,
                txn_type TEXT NOT NULL,
                lines_json TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                PRIMARY KEY (company_name, party_key, txn_type)
            );
            """;
        cmd.ExecuteNonQuery();
        try
        {
            using var alt = conn.CreateCommand();
            alt.CommandText = "ALTER TABLE ml_training_examples ADD COLUMN company_name TEXT DEFAULT '';";
            alt.ExecuteNonQuery();
        }
        catch { /* column already exists */ }
        try
        {
            using var alt2 = conn.CreateCommand();
            alt2.CommandText = "ALTER TABLE posted_transactions ADD COLUMN company_name TEXT DEFAULT '';";
            alt2.ExecuteNonQuery();
        }
        catch { /* column already exists */ }
        try
        {
            using var alt3 = conn.CreateCommand();
            alt3.CommandText = "ALTER TABLE ml_training_examples ADD COLUMN txn_hash TEXT DEFAULT '';";
            alt3.ExecuteNonQuery();
        }
        catch { /* column already exists */ }
        using (var idx = conn.CreateCommand())
        {
            idx.CommandText = "CREATE INDEX IF NOT EXISTS idx_ml_txn ON ml_training_examples(txn_hash, company_name);";
            idx.ExecuteNonQuery();
        }
        });
    }

    public void UpsertOwnBanksBatch(string companyName, IEnumerable<OwnBankAccount> banks, bool overwriteExisting = true)
    {
        EnsureInitialized();
        var comp = (companyName ?? "").Trim();
        var list = banks.ToList();
        if (string.IsNullOrEmpty(comp) || list.Count == 0) return;
        WithWriteRetry(() => {
        using var conn = Open();
        using var tx = conn.BeginTransaction();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = overwriteExisting
            ? """
              INSERT INTO company_bank_accounts (company_name, tally_ledger_name, bank_name, account_number, ifsc, aliases, created_at)
              VALUES ($c, $n, $b, $a, $i, $al, $ts)
              ON CONFLICT(company_name, tally_ledger_name) DO UPDATE SET
                  bank_name = excluded.bank_name,
                  account_number = excluded.account_number,
                  ifsc = excluded.ifsc,
                  aliases = excluded.aliases;
              """
            : """
              INSERT INTO company_bank_accounts (company_name, tally_ledger_name, bank_name, account_number, ifsc, aliases, created_at)
              VALUES ($c, $n, $b, $a, $i, $al, $ts)
              ON CONFLICT(company_name, tally_ledger_name) DO UPDATE SET
                  bank_name = CASE WHEN bank_name = '' THEN excluded.bank_name ELSE bank_name END,
                  account_number = CASE WHEN account_number = '' THEN excluded.account_number ELSE account_number END,
                  ifsc = CASE WHEN ifsc = '' THEN excluded.ifsc ELSE ifsc END;
              """;
        var pC = cmd.Parameters.Add("$c", SqliteType.Text);
        var pN = cmd.Parameters.Add("$n", SqliteType.Text);
        var pB = cmd.Parameters.Add("$b", SqliteType.Text);
        var pA = cmd.Parameters.Add("$a", SqliteType.Text);
        var pI = cmd.Parameters.Add("$i", SqliteType.Text);
        var pAl = cmd.Parameters.Add("$al", SqliteType.Text);
        var pTs = cmd.Parameters.Add("$ts", SqliteType.Text);
        var now = DateTime.UtcNow.ToString("O");
        foreach (var bank in list)
        {
            pC.Value = comp;
            pN.Value = bank.TallyLedgerName.Trim();
            pB.Value = bank.BankName.Trim();
            pA.Value = bank.AccountNumber.Trim();
            pI.Value = bank.Ifsc.Trim().ToUpperInvariant();
            pAl.Value = bank.Aliases.Trim();
            pTs.Value = now;
            cmd.ExecuteNonQuery();
        }
        tx.Commit();
        });
    }

    public void DeleteOwnBank(string companyName, string ledgerName)
    {
        var comp = (companyName ?? "").Trim();
        if (string.IsNullOrEmpty(comp)) return;
        WithWriteRetry(() => {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "DELETE FROM company_bank_accounts WHERE company_name = $c AND tally_ledger_name = $n;";
        cmd.Parameters.AddWithValue("$c", comp);
        cmd.Parameters.AddWithValue("$n", ledgerName);
        cmd.ExecuteNonQuery();
        });
    }

    public List<OwnBankAccount> GetOwnBanks(string companyName)
    {
        EnsureInitialized();
        var list = new List<OwnBankAccount>();
        var comp = (companyName ?? "").Trim();
        if (string.IsNullOrEmpty(comp)) return list;
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT tally_ledger_name, bank_name, account_number, ifsc, aliases FROM company_bank_accounts WHERE company_name = $c ORDER BY tally_ledger_name;";
        cmd.Parameters.AddWithValue("$c", comp);
        using var r = cmd.ExecuteReader();
        while (r.Read())
        {
            list.Add(new OwnBankAccount
            {
                TallyLedgerName = r.GetString(0),
                BankName = r.GetString(1),
                AccountNumber = r.GetString(2),
                Ifsc = r.GetString(3),
                Aliases = r.GetString(4)
            });
        }
        return list;
    }

    public bool HasSeedSource(string sourceMarker)
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT COUNT(*) FROM ml_training_examples WHERE source = $s;";
        cmd.Parameters.AddWithValue("$s", sourceMarker);
        return Convert.ToInt32(cmd.ExecuteScalar()) > 0;
    }

    public void AddTrainingExamples(IEnumerable<(string narration, string normalized, string cpKey, string txnType, string vType, string ledger, string source, string companyName)> items)
        => AddTrainingExamplesForTxns(items.Select(i => (i.narration, i.normalized, i.cpKey, i.txnType, i.vType, i.ledger, i.source, i.companyName, "")));

    /// <summary>
    /// Adds training examples, ONE per bank transaction. When <c>txnHash</c> is set (the row's stable duplicate hash):
    /// <list type="bullet">
    /// <item>same transaction + same ledger already learned (e.g. the statement was analysed again, or the row was
    /// edited and then posted) → skipped, so re-analysis no longer inflates the weight of those rows;</item>
    /// <item>same transaction learned with a DIFFERENT ledger → the old example is replaced (a correction wins instead of
    /// both labels competing).</item>
    /// </list>
    /// Different transactions of the same party are separate hashes and still each add a vote, so learning is unchanged.
    /// Returns the number of examples actually written.
    /// </summary>
    public int AddTrainingExamplesForTxns(IEnumerable<(string narration, string normalized, string cpKey, string txnType, string vType, string ledger, string source, string companyName, string txnHash)> items)
    {
        int written = 0;
        var list = items.ToList();
        WithWriteRetry(() => {
        written = 0;
        using var conn = Open();
        using var tx = conn.BeginTransaction();
        using var find = conn.CreateCommand();
        find.CommandText = "SELECT ledger_name FROM ml_training_examples WHERE txn_hash = $h AND company_name = $cn AND source = $s;";
        var fH = find.Parameters.Add("$h", SqliteType.Text);
        var fCn = find.Parameters.Add("$cn", SqliteType.Text);
        var fS = find.Parameters.Add("$s", SqliteType.Text);
        using var del = conn.CreateCommand();
        del.CommandText = "DELETE FROM ml_training_examples WHERE txn_hash = $h AND company_name = $cn AND source = $s;";
        var dH = del.Parameters.Add("$h", SqliteType.Text);
        var dCn = del.Parameters.Add("$cn", SqliteType.Text);
        var dS = del.Parameters.Add("$s", SqliteType.Text);
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO ml_training_examples (narration, normalized_text, counterparty_key, txn_type, voucher_type, ledger_name, source, company_name, txn_hash, created_at)
            VALUES ($n, $nt, $cp, $tt, $vt, $l, $s, $cn, $h, $ts);
            """;
        var pH = cmd.Parameters.Add("$h", SqliteType.Text);
        var pN = cmd.Parameters.Add("$n", SqliteType.Text);
        var pNt = cmd.Parameters.Add("$nt", SqliteType.Text);
        var pCp = cmd.Parameters.Add("$cp", SqliteType.Text);
        var pTt = cmd.Parameters.Add("$tt", SqliteType.Text);
        var pVt = cmd.Parameters.Add("$vt", SqliteType.Text);
        var pL = cmd.Parameters.Add("$l", SqliteType.Text);
        var pS = cmd.Parameters.Add("$s", SqliteType.Text);
        var pCn = cmd.Parameters.Add("$cn", SqliteType.Text);
        var pTs = cmd.Parameters.Add("$ts", SqliteType.Text);
        var now = DateTime.UtcNow.ToString("O");

        foreach (var it in list)
        {
            if (string.IsNullOrWhiteSpace(it.ledger)) continue;
            var hash = (it.txnHash ?? "").Trim();
            var comp = (it.companyName ?? "").Trim();
            if (hash.Length > 0)
            {
                fH.Value = hash; fCn.Value = comp; fS.Value = it.source;
                var existing = new List<string>();
                using (var r = find.ExecuteReader())
                    while (r.Read()) existing.Add(r.GetString(0));
                if (existing.Count == 1 && existing[0].Equals(it.ledger.Trim(), StringComparison.OrdinalIgnoreCase))
                    continue; // already learned exactly this
                if (existing.Count > 0)
                {
                    dH.Value = hash; dCn.Value = comp; dS.Value = it.source;
                    del.ExecuteNonQuery(); // ledger was corrected: replace the old label
                }
            }
            pH.Value = hash;
            pN.Value = it.narration;
            pNt.Value = it.normalized;
            pCp.Value = it.cpKey;
            pTt.Value = it.txnType;
            pVt.Value = it.vType;
            pL.Value = it.ledger.Trim();
            pS.Value = it.source;
            pCn.Value = comp;
            pTs.Value = now;
            cmd.ExecuteNonQuery();
            written++;
        }
        tx.Commit();
        });
        return written;
    }

    /// <summary>
    /// Upper bound on user-learned examples loaded for retraining. Every analysis/post adds rows, so with 5-7 users the table
    /// grows by thousands per day; loading all of them on every retrain eventually froze the UI. The most recent examples
    /// carry the current ledger mapping, so older ones beyond this window are not needed.
    /// </summary>
    public const int MaxTrainingExamples = 150_000;

    public List<(string normalized, string cpKey, string txnType, string ledger, string source, string companyName)> GetAllTrainingExamples()
    {
        var list = new List<(string, string, string, string, string, string)>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT normalized_text, counterparty_key, txn_type, ledger_name, source, company_name FROM (
                SELECT id, normalized_text, COALESCE(counterparty_key, '') AS counterparty_key, txn_type, ledger_name, COALESCE(source, '') AS source, COALESCE(company_name, '') AS company_name
                FROM ml_training_examples WHERE source LIKE 'builtin_seed%'
                UNION ALL
                SELECT * FROM (
                    SELECT id, normalized_text, COALESCE(counterparty_key, ''), txn_type, ledger_name, COALESCE(source, ''), COALESCE(company_name, '')
                    FROM ml_training_examples WHERE source NOT LIKE 'builtin_seed%'
                    ORDER BY id DESC LIMIT $lim)
            ) ORDER BY id ASC;
            """;
        cmd.Parameters.AddWithValue("$lim", MaxTrainingExamples);
        using var r = cmd.ExecuteReader();
        while (r.Read())
        {
            list.Add((r.GetString(0), r.GetString(1), r.GetString(2), r.GetString(3), r.GetString(4), r.GetString(5)));
        }
        return list;
    }

    public void RecordPostedTransactions(IEnumerable<BankTransactionRow> rows, bool postedToTally, string companyName = "")
    {
        var comp = (companyName ?? "").Trim();
        WithWriteRetry(() => {
        using var conn = Open();
        using var tx = conn.BeginTransaction();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT OR IGNORE INTO posted_transactions
                (txn_hash, voucher_guid, txn_date, amount, txn_type, voucher_type, bank_ledger,
                 counterparty_ledger, ref_no, narration, contra_signature, posted_to_tally, company_name, created_at)
            VALUES ($h, $g, $d, $a, $tt, $vt, $bl, $cl, $ref, $nar, $cs, $pt, $cn, $ts);
            """;
        var now = DateTime.UtcNow.ToString("O");
        foreach (var r in rows)
        {
            cmd.Parameters.Clear();
            cmd.Parameters.AddWithValue("$h", r.TxnHash);
            cmd.Parameters.AddWithValue("$g", r.VoucherGuid);
            cmd.Parameters.AddWithValue("$d", r.TxnDate);
            cmd.Parameters.AddWithValue("$a", ToDb(r.Amount));
            cmd.Parameters.AddWithValue("$tt", r.TxnType);
            cmd.Parameters.AddWithValue("$vt", r.VoucherType);
            cmd.Parameters.AddWithValue("$bl", r.BankLedger);
            cmd.Parameters.AddWithValue("$cl", r.SelectedLedger);
            cmd.Parameters.AddWithValue("$ref", r.RefNo);
            cmd.Parameters.AddWithValue("$nar", r.Narration);
            cmd.Parameters.AddWithValue("$cs", r.ContraSignature);
            cmd.Parameters.AddWithValue("$pt", postedToTally ? 1 : 0);
            cmd.Parameters.AddWithValue("$cn", comp);
            cmd.Parameters.AddWithValue("$ts", now);
            cmd.ExecuteNonQuery();
        }
        tx.Commit();
        });
    }

    public HashSet<string> GetPostedHashes(string companyName = "")
    {
        var comp = (companyName ?? "").Trim();
        var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = string.IsNullOrEmpty(comp)
            ? "SELECT txn_hash FROM posted_transactions WHERE COALESCE(company_name, '') = '';"
            : "SELECT txn_hash FROM posted_transactions WHERE company_name = $c;";
        if (!string.IsNullOrEmpty(comp)) cmd.Parameters.AddWithValue("$c", comp);
        using var r = cmd.ExecuteReader();
        while (r.Read()) set.Add(r.GetString(0));
        return set;
    }

    public List<(string txnDate, decimal amount, string txnType, string bankLedger, string counterpartyLedger, string refNo)> GetPostedContras(string companyName = "")
    {
        var comp = (companyName ?? "").Trim();
        var list = new List<(string, decimal, string, string, string, string)>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = string.IsNullOrEmpty(comp)
            ? "SELECT txn_date, amount, txn_type, bank_ledger, counterparty_ledger, ref_no FROM posted_transactions WHERE voucher_type = 'Contra' AND COALESCE(company_name, '') = '';"
            : "SELECT txn_date, amount, txn_type, bank_ledger, counterparty_ledger, ref_no FROM posted_transactions WHERE voucher_type = 'Contra' AND company_name = $c;";
        if (!string.IsNullOrEmpty(comp)) cmd.Parameters.AddWithValue("$c", comp);
        using var r = cmd.ExecuteReader();
        while (r.Read())
            list.Add((r.GetString(0), FromDb(r.GetDouble(1)), r.GetString(2), r.GetString(3), r.GetString(4), r.GetString(5)));
        return list;
    }


    public void AddParentGroupExamples(IEnumerable<(string ledgerName, string parentGroup)> items)
    {
        WithWriteRetry(() => {
        using var conn = Open();
        using var tx = conn.BeginTransaction();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "INSERT INTO ml_parent_groups (ledger_name, parent_group, created_at) VALUES ($l, $p, $ts);";
        var pL = cmd.Parameters.Add("$l", SqliteType.Text);
        var pP = cmd.Parameters.Add("$p", SqliteType.Text);
        var pTs = cmd.Parameters.Add("$ts", SqliteType.Text);
        var now = DateTime.UtcNow.ToString("O");
        foreach (var it in items)
        {
            if (string.IsNullOrWhiteSpace(it.ledgerName) || string.IsNullOrWhiteSpace(it.parentGroup)) continue;
            pL.Value = it.ledgerName.Trim();
            pP.Value = it.parentGroup.Trim();
            pTs.Value = now;
            cmd.ExecuteNonQuery();
        }
        tx.Commit();
        });
    }

    public List<(string ledgerName, string parentGroup)> GetAllParentGroupExamples()
    {
        var list = new List<(string, string)>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT ledger_name, parent_group FROM ml_parent_groups ORDER BY id ASC;";
        using var r = cmd.ExecuteReader();
        while (r.Read()) list.Add((r.GetString(0), r.GetString(1)));
        return list;
    }

    public (int mlCount, int postedCount, int contraCount) GetStats()
    {
        using var conn = Open();
        int Scalar(string sql) { using var c = conn.CreateCommand(); c.CommandText = sql; return Convert.ToInt32(c.ExecuteScalar()); }
        return (
            Scalar("SELECT COUNT(*) FROM ml_training_examples;"),
            Scalar("SELECT COUNT(*) FROM posted_transactions;"),
            Scalar("SELECT COUNT(*) FROM posted_transactions WHERE voucher_type = 'Contra';")
        );
    }

    public int ClearXmlExports()
    {
        EnsureInitialized();
        int deleted = 0;
        if (Directory.Exists(ExportDir))
            foreach (var f in Directory.GetFiles(ExportDir, "*.xml")) { File.Delete(f); deleted++; }
        return deleted;
    }

    public void RecordPostedStatementFile(string fileHash, string fileName, string companyName, string bankLedger, int postedCount)
    {
        if (string.IsNullOrWhiteSpace(fileHash)) return;
        WithWriteRetry(() => {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO posted_statement_files (file_hash, file_name, company_name, bank_ledger, posted_by, posted_count, created_at)
            VALUES ($h, $fn, $c, $bl, $pb, $cnt, $ts);
            """;
        cmd.Parameters.AddWithValue("$h", fileHash);
        cmd.Parameters.AddWithValue("$fn", fileName);
        cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
        cmd.Parameters.AddWithValue("$bl", bankLedger.Trim());
        cmd.Parameters.AddWithValue("$pb", Environment.MachineName);
        cmd.Parameters.AddWithValue("$cnt", postedCount);
        cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("dd-MMM-yyyy HH:mm", System.Globalization.CultureInfo.InvariantCulture));
        cmd.ExecuteNonQuery();
        });
    }

    public PostedFileMatch? FindPreviouslyPostedFile(string fileHash, string companyName)
    {
        if (string.IsNullOrWhiteSpace(fileHash)) return null;
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT file_name, company_name, bank_ledger, posted_by, posted_count, created_at
            FROM posted_statement_files
            WHERE file_hash = $h AND (company_name = $c OR $c = '')
            ORDER BY id DESC LIMIT 1;
            """;
        cmd.Parameters.AddWithValue("$h", fileHash);
        cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
        using var r = cmd.ExecuteReader();
        if (!r.Read()) return null;
        return new PostedFileMatch
        {
            FileName = r.GetString(0),
            CompanyName = r.GetString(1),
            BankLedger = r.GetString(2),
            PostedBy = r.GetString(3),
            PostedCount = r.GetInt32(4),
            CreatedAt = r.GetString(5)
        };
    }

    public string RecordPostedBatch(string companyName, string bankLedger, List<BankTransactionRow> postedRows)
    {
        var batchId = $"B-{DateTime.Now.ToString("yyyyMMdd-HHmmss", System.Globalization.CultureInfo.InvariantCulture)}-{Guid.NewGuid().ToString("N")[..6].ToUpperInvariant()}";
        if (postedRows.Count == 0) return batchId;
        var dates = postedRows.Select(r => r.TxnDate).OrderBy(d => d).ToList();
        var refs = postedRows.Select(r => new BatchVoucherRef
        {
            Date = r.TxnDate,
            VoucherType = r.VoucherType,
            Guid = r.VoucherGuid,
            TxnHash = r.TxnHash,
            BankLedger = r.BankLedger,
            SelectedLedger = r.SelectedLedger,
            Amount = r.Amount
        }).ToList();
        var json = JsonSerializer.Serialize(refs);

        WithWriteRetry(() => {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            INSERT INTO posted_batches
                (batch_id, company_name, bank_ledger, posted_by, entry_count, total_debit, total_credit, from_date, to_date, vouchers_json, rolled_back, created_at)
            VALUES ($id, $c, $bl, $pb, $cnt, $dr, $cr, $fd, $td, $vj, 0, $ts);
            """;
        cmd.Parameters.AddWithValue("$id", batchId);
        cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
        cmd.Parameters.AddWithValue("$bl", bankLedger.Trim());
        cmd.Parameters.AddWithValue("$pb", Environment.MachineName);
        cmd.Parameters.AddWithValue("$cnt", postedRows.Count);
        cmd.Parameters.AddWithValue("$dr", ToDb(postedRows.Sum(r => r.Debit)));
        cmd.Parameters.AddWithValue("$cr", ToDb(postedRows.Sum(r => r.Credit)));
        cmd.Parameters.AddWithValue("$fd", dates.FirstOrDefault() ?? "");
        cmd.Parameters.AddWithValue("$td", dates.LastOrDefault() ?? "");
        cmd.Parameters.AddWithValue("$vj", json);
        cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("dd-MMM-yyyy HH:mm", System.Globalization.CultureInfo.InvariantCulture));
        cmd.ExecuteNonQuery();
        });
        return batchId;
    }

    public List<PostedBatchSummary> GetRecentBatches(string companyName, int limit = 30)
    {
        var list = new List<PostedBatchSummary>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT batch_id, company_name, bank_ledger, posted_by, entry_count, total_debit, total_credit, from_date, to_date, vouchers_json, rolled_back, created_at
            FROM posted_batches
            WHERE ($c = '' OR company_name = $c)
            ORDER BY rowid DESC LIMIT $lim;
            """;
        cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
        cmd.Parameters.AddWithValue("$lim", limit);
        using var r = cmd.ExecuteReader();
        while (r.Read())
        {
            List<BatchVoucherRef> vchs = [];
            try { vchs = JsonSerializer.Deserialize<List<BatchVoucherRef>>(r.GetString(9)) ?? []; } catch { }
            list.Add(new PostedBatchSummary
            {
                BatchId = r.GetString(0),
                CompanyName = r.GetString(1),
                BankLedger = r.GetString(2),
                PostedBy = r.GetString(3),
                EntryCount = r.GetInt32(4),
                TotalDebit = FromDb(r.GetDouble(5)),
                TotalCredit = FromDb(r.GetDouble(6)),
                FromDate = r.GetString(7),
                ToDate = r.GetString(8),
                Vouchers = vchs,
                RolledBack = r.GetInt32(10) != 0,
                CreatedAt = r.GetString(11)
            });
        }
        return list;
    }

    /// <summary>
    /// Records a rollback. Only the hashes of vouchers that were ACTUALLY deleted from Tally are cleared; if some could not be
    /// deleted the batch stays open with just those remaining vouchers, so the rollback can be retried and the duplicate
    /// guard still protects the entries that are still in Tally.
    /// </summary>
    public void MarkBatchRolledBack(string batchId, IEnumerable<string> txnHashes, List<BatchVoucherRef>? remainingVouchers = null)
    {
        var remaining = remainingVouchers ?? new List<BatchVoucherRef>();
        WithWriteRetry(() => {
        using var conn = Open();
        using var tx = conn.BeginTransaction();
        using (var cmd = conn.CreateCommand())
        {
            if (remaining.Count == 0)
            {
                cmd.CommandText = "UPDATE posted_batches SET rolled_back = 1 WHERE batch_id = $id;";
            }
            else
            {
                cmd.CommandText = "UPDATE posted_batches SET vouchers_json = $vj, entry_count = $cnt WHERE batch_id = $id;";
                cmd.Parameters.AddWithValue("$vj", JsonSerializer.Serialize(remaining));
                cmd.Parameters.AddWithValue("$cnt", remaining.Count);
            }
            cmd.Parameters.AddWithValue("$id", batchId);
            cmd.ExecuteNonQuery();
        }
        using (var del = conn.CreateCommand())
        {
            del.CommandText = "DELETE FROM posted_transactions WHERE txn_hash = $h;";
            var pH = del.Parameters.Add("$h", SqliteType.Text);
            foreach (var h in txnHashes)
            {
                if (string.IsNullOrWhiteSpace(h)) continue;
                pH.Value = h;
                del.ExecuteNonQuery();
            }
        }
        tx.Commit();
        });
    }

    // ------------------------------------------------------------------ saved statement layouts ("Teach Columns")
    public List<LayoutTemplate> GetLayoutTemplates()
    {
        var list = new List<LayoutTemplate>();
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT id, name, bank, header_sig, boundaries_json, roles_json, sample_file, created_by, created_at FROM layout_templates ORDER BY id DESC;";
        using var r = cmd.ExecuteReader();
        while (r.Read())
        {
            try
            {
                list.Add(new LayoutTemplate
                {
                    Id = r.GetInt64(0), Name = r.GetString(1), Bank = r.GetString(2), HeaderSignature = r.GetString(3),
                    Boundaries = JsonSerializer.Deserialize<List<double>>(r.GetString(4)) ?? [],
                    Roles = JsonSerializer.Deserialize<List<string>>(r.GetString(5)) ?? [],
                    SampleFile = r.GetString(6), CreatedBy = r.GetString(7), CreatedAt = r.GetString(8)
                });
            }
            catch (JsonException) { /* skip a damaged row, never break parsing */ }
        }
        return list.Where(t => t.Roles.Count >= 2 && t.Boundaries.Count == t.Roles.Count + 1).ToList();
    }

    public long SaveLayoutTemplate(LayoutTemplate t)
    {
        long id = 0;
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                INSERT INTO layout_templates (name, bank, header_sig, boundaries_json, roles_json, sample_file, created_by, created_at)
                VALUES ($n, $b, $s, $bj, $rj, $f, $by, $ts);
                SELECT last_insert_rowid();
                """;
            cmd.Parameters.AddWithValue("$n", t.Name.Trim());
            cmd.Parameters.AddWithValue("$b", t.Bank ?? "");
            cmd.Parameters.AddWithValue("$s", t.HeaderSignature ?? "");
            cmd.Parameters.AddWithValue("$bj", JsonSerializer.Serialize(t.Boundaries));
            cmd.Parameters.AddWithValue("$rj", JsonSerializer.Serialize(t.Roles));
            cmd.Parameters.AddWithValue("$f", t.SampleFile ?? "");
            cmd.Parameters.AddWithValue("$by", Environment.MachineName);
            cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("dd-MMM-yyyy HH:mm", System.Globalization.CultureInfo.InvariantCulture));
            id = Convert.ToInt64(cmd.ExecuteScalar(), System.Globalization.CultureInfo.InvariantCulture);
        });
        return id;
    }

    public void DeleteLayoutTemplate(long id)
    {
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "DELETE FROM layout_templates WHERE id = $id;";
            cmd.Parameters.AddWithValue("$id", id);
            cmd.ExecuteNonQuery();
        });
    }

    // ------------------------------------------------------------------ statement continuity (month to month)
    public void RecordStatement(StatementHistoryEntry e)
    {
        if (string.IsNullOrWhiteSpace(e.FromDate) || string.IsNullOrWhiteSpace(e.ToDate)) return;
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            // one entry per account + period: re-posting the same statement replaces it
            cmd.CommandText = """
                DELETE FROM statement_history WHERE company_name = $c AND bank_ledger = $b AND from_date = $f AND to_date = $t;
                INSERT INTO statement_history (company_name, bank_ledger, from_date, to_date, opening, closing, source_file, recorded_at)
                VALUES ($c, $b, $f, $t, $o, $cl, $sf, $ts);
                """;
            cmd.Parameters.AddWithValue("$c", (e.CompanyName ?? "").Trim());
            cmd.Parameters.AddWithValue("$b", (e.BankLedger ?? "").Trim());
            cmd.Parameters.AddWithValue("$f", e.FromDate);
            cmd.Parameters.AddWithValue("$t", e.ToDate);
            cmd.Parameters.AddWithValue("$o", ToDb(e.Opening));
            cmd.Parameters.AddWithValue("$cl", ToDb(e.Closing));
            cmd.Parameters.AddWithValue("$sf", e.SourceFile ?? "");
            cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("dd-MMM-yyyy HH:mm", System.Globalization.CultureInfo.InvariantCulture));
            cmd.ExecuteNonQuery();
        });
    }

    /// <summary>The latest accepted statement of this account that ENDS BEFORE <paramref name="fromDate"/> (ISO yyyy-MM-dd).</summary>
    public StatementHistoryEntry? GetPreviousStatement(string companyName, string bankLedger, string fromDate)
    {
        using var conn = Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
            SELECT company_name, bank_ledger, from_date, to_date, opening, closing, source_file, recorded_at
            FROM statement_history
            WHERE company_name = $c AND bank_ledger = $b AND to_date < $f
            ORDER BY to_date DESC, id DESC LIMIT 1;
            """;
        cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
        cmd.Parameters.AddWithValue("$b", (bankLedger ?? "").Trim());
        cmd.Parameters.AddWithValue("$f", fromDate);
        using var r = cmd.ExecuteReader();
        if (!r.Read()) return null;
        return new StatementHistoryEntry
        {
            CompanyName = r.GetString(0), BankLedger = r.GetString(1), FromDate = r.GetString(2), ToDate = r.GetString(3),
            Opening = FromDb(r.GetDouble(4)), Closing = FromDb(r.GetDouble(5)), SourceFile = r.GetString(6), RecordedAt = r.GetString(7)
        };
    }


    // ------------------------------------------------------------------ settings (shared by everyone using this data folder)
    public string? GetSetting(string key)
    {
        try
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT value FROM app_settings WHERE key = $k;";
            cmd.Parameters.AddWithValue("$k", key);
            return cmd.ExecuteScalar() as string;
        }
        catch { return null; }
    }

    public bool GetBoolSetting(string key, bool defaultValue)
    {
        var v = GetSetting(key);
        return v == null ? defaultValue : v == "1";
    }

    public void SetSetting(string key, string value)
    {
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "INSERT INTO app_settings (key, value) VALUES ($k, $v) ON CONFLICT(key) DO UPDATE SET value = excluded.value;";
            cmd.Parameters.AddWithValue("$k", key);
            cmd.Parameters.AddWithValue("$v", value ?? "");
            cmd.ExecuteNonQuery();
        });
    }

    public void SetBoolSetting(string key, bool value) => SetSetting(key, value ? "1" : "0");

    // ------------------------------------------------------------------ remembered splits (per party + direction)
    public void SaveRememberedSplit(string companyName, string partyKey, string txnType, List<LedgerSplit> lines)
    {
        if (string.IsNullOrWhiteSpace(partyKey) || lines == null || lines.Count < 2) return;
        var json = System.Text.Json.JsonSerializer.Serialize(lines.Select(l => new { l.Ledger, Amount = ToDb(l.Amount) }));
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = """
                INSERT INTO remembered_splits (company_name, party_key, txn_type, lines_json, saved_at) VALUES ($c, $p, $t, $j, $ts)
                ON CONFLICT(company_name, party_key, txn_type) DO UPDATE SET lines_json = excluded.lines_json, saved_at = excluded.saved_at;
                """;
            cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
            cmd.Parameters.AddWithValue("$p", partyKey);
            cmd.Parameters.AddWithValue("$t", txnType ?? "");
            cmd.Parameters.AddWithValue("$j", json);
            cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("dd-MMM-yyyy HH:mm", System.Globalization.CultureInfo.InvariantCulture));
            cmd.ExecuteNonQuery();
        });
    }

    public void DeleteRememberedSplit(string companyName, string partyKey, string txnType)
    {
        if (string.IsNullOrWhiteSpace(partyKey)) return;
        WithWriteRetry(() =>
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "DELETE FROM remembered_splits WHERE company_name = $c AND party_key = $p AND txn_type = $t;";
            cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
            cmd.Parameters.AddWithValue("$p", partyKey);
            cmd.Parameters.AddWithValue("$t", txnType ?? "");
            cmd.ExecuteNonQuery();
        });
    }

    /// <summary>All remembered splits of a company, keyed "partyKey|txnType".</summary>
    public Dictionary<string, List<LedgerSplit>> GetRememberedSplits(string companyName)
    {
        var map = new Dictionary<string, List<LedgerSplit>>(StringComparer.OrdinalIgnoreCase);
        try
        {
            using var conn = Open();
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT party_key, txn_type, lines_json FROM remembered_splits WHERE company_name = $c;";
            cmd.Parameters.AddWithValue("$c", (companyName ?? "").Trim());
            using var r = cmd.ExecuteReader();
            while (r.Read())
            {
                try
                {
                    using var doc = System.Text.Json.JsonDocument.Parse(r.GetString(2));
                    var lines = new List<LedgerSplit>();
                    foreach (var el in doc.RootElement.EnumerateArray())
                        lines.Add(new LedgerSplit { Ledger = el.GetProperty("Ledger").GetString() ?? "", Amount = FromDb(el.GetProperty("Amount").GetDouble()) });
                    if (lines.Count >= 2) map[r.GetString(0) + "|" + r.GetString(1)] = lines;
                }
                catch { /* a damaged row is ignored */ }
            }
        }
        catch { }
        return map;
    }


    // Money is decimal in the app. The database keeps its existing REAL columns (old data stays readable); a REAL holds
    // 15 significant digits, so a rupee amount with paise goes in and comes back exactly once rounded to 2 places.
    private static double ToDb(decimal money) => (double)Math.Round(money, 2, MidpointRounding.AwayFromZero);
    private static decimal FromDb(double stored) => Math.Round((decimal)stored, 2, MidpointRounding.AwayFromZero);

}
