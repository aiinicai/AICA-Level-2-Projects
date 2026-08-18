<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner','supervisor'])) {
    header('Location: '.url('dashboard.php')); exit;
}
$db = getDB();
$page_title = 'GST Return Data Import';
$results = []; $errors = []; $summary = [];

// ── DOWNLOAD TEMPLATE (clean CSV) ────────────────────────
if (isset($_GET['download'])) {
    require_once __DIR__.'/includes/export.php';
    startCSVDownload('GST_Returns_Import_Template');
    $out = fopen('php://output','w');
    // Header row
    writeCSVRow($out, [
        'pan *',
        'gstin *',
        'return_type * (GSTR-1 / GSTR-3B / GSTR-9 etc)',
        'return_period * (e.g. Apr-2026 or Q1-FY27)',
        'financial_year * (e.g. 2026-27)',
        'status * (Filed / Data Received / Challan Sent / No Challan Due / Challan Paid / Pending Data / On Hold / Not Applicable)',
        'filed_date (DD-MM-YYYY or YYYY-MM-DD)',
        'arn',
        'data_received_date (DD-MM-YYYY or YYYY-MM-DD)',
        'cgst_liability',
        'sgst_liability',
        'igst_liability',
        'cess_liability',
        'challan_no',
        'payment_date (DD-MM-YYYY or YYYY-MM-DD)',
        'remarks',
    ]);
    // Sample rows
    writeCSVRow($out, ['AAABR1234P','27AAABR1234P1ZX','GSTR-3B','Apr-2026','2026-27',
        'Filed','15-05-2026','AA2604260012345','01-05-2026','5000','5000','0','0','CBI12345','10-05-2026','']);
    writeCSVRow($out, ['AAACA5678C','27AAACA5678C1ZX','GSTR-1','Apr-2026','2026-27',
        'Filed','11-05-2026','AA2604260054321','02-05-2026','0','0','0','0','','','Nil return']);
    writeCSVRow($out, ['AABHM9012H','27AABHM9012H1ZX','GSTR-3B','Apr-2026','2026-27',
        'Challan Sent','','','05-05-2026','12000','12000','0','0','CBI99887','','Challan sent awaiting payment']);
    writeCSVRow($out, ['AAACJ2345S','27AAACJ2345S1ZX','GSTR-3B','Apr-2026','2026-27',
        'Pending Data','','','','0','0','0','0','','','Data not yet received from client']);
    fclose($out);
    exit;
}

// ── DOWNLOAD TEMPLATE WITH DROPDOWNS (.xlsx) ───────────────
if (isset($_GET['download_xlsx'])) {
    require_once __DIR__.'/includes/xlsx_export.php';
    if (!xlsxIsAvailable()) {
        $_SESSION['flash_msg'] = 'Dropdown template unavailable on this server (PHP Zip extension not installed). Use the plain CSV template instead.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('gst_import.php')); exit;
    }
    $return_type_names = $db->query("SELECT DISTINCT return_name FROM gst_return_types WHERE is_active=1 ORDER BY return_name")->fetchAll(PDO::FETCH_COLUMN);
    if (empty($return_type_names)) $return_type_names = ['GSTR-1','GSTR-3B','GSTR-9','GSTR-9C'];
    $status_values = ['Filed','Data Received','Challan Sent','No Challan Due','Challan Paid','Pending Data','On Hold','Not Applicable'];

    $headers = [
        'pan*','gstin*','return_type*','return_period*','financial_year*','status*',
        'filed_date','arn','data_received_date','cgst_liability','sgst_liability',
        'igst_liability','cess_liability','challan_no','payment_date','remarks',
    ];
    $samples = [
        ['AAABR1234P','27AAABR1234P1ZX','GSTR-3B','Apr-2026','2026-27','Filed','15-05-2026','AA2604260012345','01-05-2026','5000','5000','0','0','CBI12345','10-05-2026',''],
        ['AAACA5678C','27AAACA5678C1ZX','GSTR-1','Apr-2026','2026-27','Filed','11-05-2026','AA2604260054321','02-05-2026','0','0','0','0','','','Nil return'],
    ];
    $dropdowns = [
        2 => $return_type_names,  // return_type
        5 => $status_values,      // status
    ];
    streamXLSXWithDropdowns('GST_Returns_Import_Template_dropdowns', $headers, $samples, $dropdowns);
}

// ── PARSE DATE (handles DD-MM-YYYY and YYYY-MM-DD) ────────
function parseDate($raw) {
    $raw = trim($raw ?? '');
    if (!$raw) return null;
    // DD-MM-YYYY or DD/MM/YYYY
    if (preg_match('/^(\d{1,2})[-\/](\d{1,2})[-\/](\d{4})$/', $raw, $m)) {
        return sprintf('%04d-%02d-%02d', $m[3], $m[2], $m[1]);
    }
    // YYYY-MM-DD already
    if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $raw)) return $raw;
    // Try strtotime as fallback
    $ts = strtotime($raw);
    return $ts ? date('Y-m-d', $ts) : null;
}

// ── VALID STATUSES ─────────────────────────────────────────
$valid_statuses = [
    'Filed', 'Data Received', 'Challan Sent', 'No Challan Due',
    'Challan Paid', 'Pending Data', 'On Hold', 'Not Applicable',
];

// ── PROCESS UPLOAD ─────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['import_file'])) {
    $file = $_FILES['import_file'];
    if ($file['error'] !== 0) {
        $errors[] = 'File upload error. Please try again.';
    } else {
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, ['csv'])) {
            $errors[] = 'Please upload a CSV file. Open the XLS template in Excel → Save As → CSV UTF-8.';
        } else {
            $handle = fopen($file['tmp_name'], 'r');
            $header_row = fgetcsv($handle); // skip header
            $row_num = 1;
            $counts  = ['created'=>0, 'updated'=>0, 'skipped'=>0, 'errors'=>0];
            $status_counts = [];

            while (($row = fgetcsv($handle)) !== false) {
                $row_num++;
                if (count($row) < 5 || empty(trim($row[0] ?? ''))) { $counts['skipped']++; continue; }

                // Column mapping
                $pan         = strtoupper(trim($row[0] ?? ''));
                $gstin       = strtoupper(trim($row[1] ?? ''));
                $return_type = trim($row[2] ?? '');
                $period      = trim($row[3] ?? '');
                $fy          = trim($row[4] ?? '');
                $status_raw  = trim($row[5] ?? 'Pending Data');
                $filed_date  = parseDate($row[6] ?? '');
                $arn         = strtoupper(trim($row[7] ?? ''));
                $data_recd   = parseDate($row[8] ?? '');
                $cgst        = floatval($row[9]  ?? 0);
                $sgst        = floatval($row[10] ?? 0);
                $igst        = floatval($row[11] ?? 0);
                $cess        = floatval($row[12] ?? 0);
                $challan_no  = trim($row[13] ?? '');
                $pay_date    = parseDate($row[14] ?? '');
                $remarks     = trim($row[15] ?? '');

                // Validate
                if (!$pan || strlen($pan) !== 10) {
                    $errors[] = "Row $row_num: Invalid PAN '$pan'"; $counts['errors']++; continue;
                }
                if (!$return_type || !$period || !$fy) {
                    $errors[] = "Row $row_num: Missing return_type, period or FY"; $counts['errors']++; continue;
                }

                // Normalise status
                $status = 'Pending Data';
                foreach ($valid_statuses as $vs) {
                    if (strtolower($status_raw) === strtolower($vs)) { $status = $vs; break; }
                }

                // Find client by PAN
                $cl_stmt = $db->prepare("SELECT id, supervisor_id FROM clients WHERE pan=? AND status='Active'");
                $cl_stmt->execute([$pan]);
                $client = $cl_stmt->fetch();
                if (!$client) {
                    $errors[] = "Row $row_num: PAN $pan not found in client master — skipped.";
                    $counts['skipped']++; continue;
                }
                $client_id = $client['id'];

                // Determine periodicity
                $rt_stmt = $db->prepare("SELECT periodicity FROM gst_return_types WHERE return_name=? LIMIT 1");
                $rt_stmt->execute([$return_type]);
                $rt_row      = $rt_stmt->fetch();
                $periodicity = $rt_row['periodicity'] ?? 'Monthly';
                $due_date    = getGSTDueDate($return_type, $period, $periodicity);

                // Check if entry already exists
                $chk = $db->prepare(
                    "SELECT id FROM gst_returns WHERE client_id=? AND return_period=? AND return_type=? AND gstin=?"
                );
                $chk->execute([$client_id, $period, $return_type, $gstin]);
                $existing = $chk->fetch();

                try {
                    if ($existing) {
                        // UPDATE existing entry
                        $db->prepare(
                            "UPDATE gst_returns SET
                                status=?, filed_date=?, arn=?,
                                data_received_date=?,
                                cgst_liability=?, sgst_liability=?, igst_liability=?, cess_liability=?,
                                challan_no=?, payment_date=?, remarks=?
                            WHERE id=?"
                        )->execute([
                            $status,
                            $filed_date,
                            $arn,
                            $data_recd ?: null,
                            $cgst, $sgst, $igst, $cess,
                            $challan_no ?: null,
                            $pay_date ?: null,
                            $remarks ?: null,
                            $existing['id'],
                        ]);
                        auditLog('gst_returns', $existing['id'], 'UPDATE', null,
                            ['status'=>$status,'arn'=>$arn,'source'=>'import']);
                        $counts['updated']++;
                        $results[] = [
                            'type'=>'updated','row'=>$row_num,'pan'=>$pan,'gstin'=>$gstin,
                            'period'=>$period,'return_type'=>$return_type,'status'=>$status,
                            'arn'=>$arn,'filed_date'=>$filed_date,
                        ];
                    } else {
                        // CREATE new entry
                        $db->prepare(
                            "INSERT INTO gst_returns
                                (client_id,gstin,return_period,financial_year,return_type,periodicity,
                                 due_date,status,filed_date,arn,
                                 data_received_date,cgst_liability,sgst_liability,igst_liability,cess_liability,
                                 challan_no,payment_date,remarks,created_by)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                        )->execute([
                            $client_id, $gstin, $period, $fy, $return_type, $periodicity,
                            $due_date, $status, $filed_date ?: null, $arn ?: null,
                            $data_recd ?: null, $cgst, $sgst, $igst, $cess,
                            $challan_no ?: null, $pay_date ?: null,
                            $remarks ?: null, $_SESSION['user_id'],
                        ]);
                        auditLog('gst_returns', $db->lastInsertId(), 'CREATE', null,
                            ['status'=>$status,'source'=>'import']);
                        $counts['created']++;
                        $results[] = [
                            'type'=>'created','row'=>$row_num,'pan'=>$pan,'gstin'=>$gstin,
                            'period'=>$period,'return_type'=>$return_type,'status'=>$status,
                            'arn'=>$arn,'filed_date'=>$filed_date,
                        ];
                    }

                    // Tally status counts
                    $status_counts[$status] = ($status_counts[$status] ?? 0) + 1;

                } catch (Exception $e) {
                    $errors[] = "Row $row_num: DB error — ".$e->getMessage();
                    $counts['errors']++;
                }
            }
            fclose($handle);

            $summary = $counts;
            $summary['status_counts'] = $status_counts;

            $_SESSION['flash_msg'] = sprintf(
                'Import complete: %d created, %d updated, %d skipped, %d errors.',
                $counts['created'], $counts['updated'], $counts['skipped'], $counts['errors']
            );
            $_SESSION['flash_type'] = ($counts['errors'] > 0) ? 'warning' : 'success';
        }
    }
}

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">📥 GST Return Data Import</div>
    <div class="page-subtitle">Import filed / in-progress return data for any period from a CSV file</div>
  </div>
  <a href="<?= url('gst_register.php') ?>" class="btn btn-outline">← GST Register</a>
</div>

<!-- HOW IT WORKS -->
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem;margin-bottom:1.25rem">

  <div class="card">
    <div class="card-header"><span class="card-title">📋 How to Import</span></div>
    <div class="card-body" style="font-size:13px;line-height:2">
      <div style="counter-reset:steps">
        <?php foreach ([
          'Download the Excel template below',
          'Fill in your data — one row per return per client',
          'For filed returns: fill <strong>filed_date</strong> and <strong>ARN</strong>, set status = <code>Filed</code>',
          'For partially done: set the correct status (see legend below)',
          'Save the file as <strong>CSV UTF-8</strong> from Excel',
          'Upload the CSV here — existing entries are updated, new ones are created',
        ] as $i => $step): ?>
        <div style="display:flex;gap:10px;margin-bottom:6px">
          <span style="background:var(--primary);color:#fff;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0"><?= $i+1 ?></span>
          <span><?= $step ?></span>
        </div>
        <?php endforeach; ?>
      </div>
      <div class="d-flex gap-1" style="flex-wrap:wrap;margin-top:10px">
        <a href="<?= url('gst_import.php?download_xlsx=1') ?>" class="btn btn-export">
          ⬇ Download with Dropdowns (.xlsx) <span style="font-size:10px;opacity:.85">— recommended</span>
        </a>
        <a href="<?= url('gst_import.php?download=1') ?>" class="btn btn-outline">
          ⬇ Download Plain Template (.csv)
        </a>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-title">🔖 Status Values Reference</span></div>
    <div class="card-body">
      <?php
      $status_guide = [
        'Filed'           => ['badge-success', 'Return filed, ARN received — record complete'],
        'Data Received'   => ['badge-info',    'Data received from client, working in progress'],
        'Challan Sent'    => ['badge-warning',  'Working done, challan sent to client for payment'],
        'No Challan Due'  => ['badge-info',    'Nil return or ITC adjusted — no challan required'],
        'Challan Paid'    => ['badge-info',    'Paid challan received back, ready to file'],
        'Pending Data'    => ['badge-secondary','Data not yet received from client'],
        'On Hold'         => ['badge-danger',   'Return on hold — review required'],
        'Not Applicable'  => ['badge-secondary','This return is not applicable for this client'],
      ];
      foreach ($status_guide as $st => [$badge, $desc]): ?>
      <div style="display:flex;align-items:center;gap:10px;padding:5px 0;border-bottom:1px solid var(--border-lt)">
        <span class="badge <?= $badge ?>" style="min-width:120px;text-align:center"><?= $st ?></span>
        <span style="font-size:12px;color:var(--text-muted)"><?= $desc ?></span>
      </div>
      <?php endforeach; ?>
    </div>
  </div>

</div>

<!-- UPLOAD FORM -->
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-header"><span class="card-title">⬆ Upload CSV File</span></div>
  <div class="card-body">
    <form method="post" enctype="multipart/form-data">
      <div style="display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap">
        <div class="form-group" style="flex:1;min-width:250px">
          <label>Select CSV File <span class="req">*</span></label>
          <input type="file" name="import_file" accept=".csv" class="form-control" style="height:auto;padding:6px">
        </div>
        <div>
          <button class="btn btn-primary" type="submit" style="height:34px">
            ⬆ Import Now
          </button>
        </div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-top:6px">
        ℹ Matching is done by <strong>PAN + GSTIN + Return Type + Period</strong>.
        If a matching entry exists it will be <strong>updated</strong>. If not, a new entry will be <strong>created</strong>.
      </div>
    </form>
  </div>
</div>

<?php if (!empty($summary)): ?>
<!-- IMPORT SUMMARY -->
<div class="card" style="margin-bottom:1.25rem;border-left:4px solid var(--primary)">
  <div class="card-header" style="background:var(--primary-bg)">
    <span class="card-title" style="color:var(--primary)">✅ Import Summary</span>
  </div>
  <div class="card-body">
    <!-- Count cards -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1rem">
      <div style="text-align:center;padding:12px;background:#eaf3de;border-radius:6px;border:1px solid #c0dd97">
        <div style="font-size:28px;font-weight:700;color:#3b6d11"><?= $summary['created'] ?></div>
        <div style="font-size:12px;color:#3b6d11">New Entries Created</div>
      </div>
      <div style="text-align:center;padding:12px;background:#e6f1fb;border-radius:6px;border:1px solid #b5d4f4">
        <div style="font-size:28px;font-weight:700;color:#185fa5"><?= $summary['updated'] ?></div>
        <div style="font-size:12px;color:#185fa5">Existing Entries Updated</div>
      </div>
      <div style="text-align:center;padding:12px;background:#f0f2f5;border-radius:6px;border:1px solid var(--border)">
        <div style="font-size:28px;font-weight:700;color:var(--text-muted)"><?= $summary['skipped'] ?></div>
        <div style="font-size:12px;color:var(--text-muted)">Rows Skipped (blank)</div>
      </div>
      <div style="text-align:center;padding:12px;background:<?= $summary['errors']>0 ? '#fdf0ef' : '#f0f2f5' ?>;border-radius:6px;border:1px solid <?= $summary['errors']>0 ? '#fecaca' : 'var(--border)' ?>">
        <div style="font-size:28px;font-weight:700;color:<?= $summary['errors']>0 ? 'var(--danger)' : 'var(--text-muted)' ?>"><?= $summary['errors'] ?></div>
        <div style="font-size:12px;color:<?= $summary['errors']>0 ? 'var(--danger)' : 'var(--text-muted)' ?>">Errors</div>
      </div>
    </div>

    <!-- Status breakdown -->
    <?php if (!empty($summary['status_counts'])): ?>
    <div style="margin-bottom:1rem">
      <div style="font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px">
        Breakdown by Status:
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <?php foreach ($summary['status_counts'] as $st => $cnt):
          $badge_map = [
            'Filed'=>'badge-success','Data Received'=>'badge-info','Challan Sent'=>'badge-warning',
            'No Challan Due'=>'badge-info','Challan Paid'=>'badge-info',
            'Pending Data'=>'badge-secondary','On Hold'=>'badge-danger','Not Applicable'=>'badge-secondary',
          ];
          $badge = $badge_map[$st] ?? 'badge-secondary';
        ?>
          <div style="display:flex;align-items:center;gap:6px;padding:6px 12px;background:#f8f9fa;border-radius:20px;border:1px solid var(--border-lt)">
            <span class="badge <?= $badge ?>"><?= htmlspecialchars($st) ?></span>
            <span style="font-size:14px;font-weight:700"><?= $cnt ?></span>
          </div>
        <?php endforeach; ?>
      </div>
    </div>
    <?php endif; ?>

    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <a href="<?= url('gst_register.php') ?>" class="btn btn-primary">View GST Register</a>
      <a href="<?= url('gst_register.php?status=Pending+Data') ?>" class="btn btn-outline">View Pending Data</a>
      <a href="<?= url('gst_register.php?status=Filed') ?>" class="btn btn-outline">View Filed Returns</a>
    </div>
  </div>
</div>
<?php endif; ?>

<!-- ERRORS -->
<?php if (!empty($errors)): ?>
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-header" style="background:var(--danger-bg)">
    <span class="card-title" style="color:var(--danger)">⚠ Errors (<?= count($errors) ?>)</span>
  </div>
  <div class="card-body" style="max-height:300px;overflow-y:auto;font-size:12px">
    <?php foreach ($errors as $e): ?>
      <div style="padding:4px 0;border-bottom:1px solid var(--border-lt);color:var(--danger)">✗ <?= htmlspecialchars($e) ?></div>
    <?php endforeach; ?>
  </div>
</div>
<?php endif; ?>

<!-- DETAILED RESULTS -->
<?php if (!empty($results)): ?>
<div class="card">
  <div class="card-header">
    <span class="card-title">📋 Detailed Import Results (<?= count($results) ?> rows processed)</span>
    <button class="btn btn-outline btn-sm" onclick="document.getElementById('results-detail').style.display = document.getElementById('results-detail').style.display==='none'?'block':'none'">
      Show / Hide
    </button>
  </div>
  <div id="results-detail" style="display:none">
  <div class="table-responsive">
  <table class="data-table" style="font-size:12px">
    <thead>
      <tr>
        <th>Row</th><th>Action</th><th>PAN</th><th>GSTIN</th>
        <th>Return Type</th><th>Period</th><th>Status</th><th>ARN</th><th>Filed Date</th>
      </tr>
    </thead>
    <tbody>
    <?php foreach ($results as $r): ?>
      <tr>
        <td><?= $r['row'] ?></td>
        <td>
          <?php if ($r['type']==='created'): ?>
            <span class="badge badge-success">Created</span>
          <?php else: ?>
            <span class="badge badge-info">Updated</span>
          <?php endif; ?>
        </td>
        <td><code><?= htmlspecialchars($r['pan']) ?></code></td>
        <td style="font-size:10px"><code><?= htmlspecialchars($r['gstin']) ?></code></td>
        <td><span class="badge badge-primary"><?= htmlspecialchars($r['return_type']) ?></span></td>
        <td><?= htmlspecialchars($r['period']) ?></td>
        <td><?= statusBadge($r['status']) ?></td>
        <td style="font-size:10px"><code><?= htmlspecialchars($r['arn'] ?: '—') ?></code></td>
        <td><?= $r['filed_date'] ? fmtDate($r['filed_date']) : '—' ?></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
  </div>
</div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>
