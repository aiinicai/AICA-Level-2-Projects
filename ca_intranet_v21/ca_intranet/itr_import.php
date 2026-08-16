<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner','supervisor'])) { header('Location: '.url('dashboard.php')); exit; }
$db = getDB();
$page_title = 'Import ITR Filing Data';

// ── SCHEMA CHECK ──────────────────────────────────────────
try {
    $db->query("SELECT 1 FROM itr_returns LIMIT 1");
} catch (Exception $e) {
    include 'includes/header.php';
    echo '<div class="card" style="max-width:600px;margin:2rem auto"><div class="card-body">
        <h2 style="color:var(--danger)">⚠ ITR Register not set up yet</h2>
        <p>Run <code>upgrade_itr.sql</code> in phpMyAdmin first.</p>
        <a href="'.url('dashboard.php').'" class="btn btn-primary" style="margin-top:1rem">← Dashboard</a>
    </div></div>';
    include 'includes/footer.php'; exit;
}

// ── FIND PYTHON3 ──────────────────────────────────────────
// PHP's shell_exec uses a minimal PATH — try known locations explicitly
function findPython3() {
    $candidates = [
        '/usr/bin/python3',
        '/usr/local/bin/python3',
        '/opt/lampp/bin/python3',
        '/usr/bin/python',
        'python3',
        'python',
    ];
    foreach ($candidates as $py) {
        $out = @shell_exec(escapeshellcmd($py) . ' -c "import sys; print(sys.version)" 2>&1');
        if ($out && strpos($out, 'Error') === false && trim($out) !== '') {
            return $py;
        }
    }
    return null;
}

// ── AUTO-INSTALL xlrd IF MISSING ──────────────────────────
function ensureXlrd($python) {
    $check = @shell_exec(escapeshellcmd($python) . ' -c "import xlrd; print(xlrd.__version__)" 2>&1');
    if ($check && strpos($check, 'Error') === false && strpos($check, 'No module') === false) {
        return true; // already installed
    }
    // Try installing
    $pip_cmds = [
        escapeshellcmd($python) . ' -m pip install xlrd openpyxl --break-system-packages -q 2>&1',
        'pip3 install xlrd openpyxl --break-system-packages -q 2>&1',
        'pip install xlrd openpyxl --break-system-packages -q 2>&1',
    ];
    foreach ($pip_cmds as $cmd) {
        @shell_exec($cmd);
        $check2 = @shell_exec(escapeshellcmd($python) . ' -c "import xlrd; print(\'ok\')" 2>&1');
        if ($check2 && strpos($check2, 'ok') !== false) {
            return true;
        }
    }
    return false;
}

// ── PROCESS UPLOADED FILE ─────────────────────────────────
$results = [];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['itr_file'])) {
    $file = $_FILES['itr_file'];

    if ($file['error'] !== 0) {
        $results[] = ['type'=>'error', 'msg'=>'Upload failed (error code '.$file['error'].'). Check PHP upload_max_filesize and post_max_size settings.'];
    } else {
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, ['xls','xlsx'])) {
            $results[] = ['type'=>'error', 'msg'=>'Only .xls or .xlsx files are accepted.'];
        } else {
            $python = findPython3();

            if (!$python) {
                $results[] = ['type'=>'error', 'msg'=>'Python3 not found on this server. Please install Python3 (sudo apt install python3) and try again.'];
            } else {
                // Ensure xlrd is installed for this Python
                if (!ensureXlrd($python)) {
                    $results[] = ['type'=>'error', 'msg'=>'Could not install required Python library (xlrd). Please run manually: <code>pip3 install xlrd openpyxl --break-system-packages</code>'];
                } else {
                    try {
                        $tmpPath = tempnam(sys_get_temp_dir(), 'itr_') . '.' . $ext;
                        move_uploaded_file($file['tmp_name'], $tmpPath);

                        $parserPath = __DIR__ . '/itr_import_parse.py';
                        $cmd = escapeshellcmd($python) . ' ' .
                               escapeshellarg($parserPath) . ' ' .
                               escapeshellarg($tmpPath) . ' ' .
                               escapeshellarg($ext) . ' 2>&1';
                        $json_out = shell_exec($cmd);
                        @unlink($tmpPath);

                        if (!trim($json_out)) {
                            $results[] = ['type'=>'error', 'msg'=>'Parser returned no output. Command used: <code>'.htmlspecialchars($cmd).'</code>'];
                        } else {
                            $parsed = json_decode($json_out, true);
                            if (!$parsed || isset($parsed['error'])) {
                                $results[] = ['type'=>'error', 'msg'=>'Parse error: '.htmlspecialchars($parsed['error'] ?? $json_out)];
                            } else {
                                $fy      = trim($_POST['financial_year'] ?? '');
                                $created = 0; $updated = 0; $skipped = 0; $not_found = 0;
                                $row_details = [];

                                foreach ($parsed['rows'] as $row) {
                                    $pan        = strtoupper(trim($row['pan'] ?? ''));
                                    $itr_ack    = trim($row['itr_ack'] ?? '');
                                    $filed_date = trim($row['filed_date'] ?? '');
                                    $gti        = ($row['gti'] !== null && $row['gti'] !== '') ? floatval($row['gti']) : null;
                                    $itr_form   = trim($row['itr_form'] ?? '');
                                    $e_verified = $row['e_verified'] ? 'Yes' : 'Pending';
                                    $name       = trim($row['name'] ?? '');

                                    if (!$pan || strlen($pan) !== 10) { $skipped++; continue; }

                                    // Match client by PAN
                                    $cl = $db->prepare("SELECT id, partner_id, group_id FROM clients WHERE pan=? AND status='Active' LIMIT 1");
                                    $cl->execute([$pan]);
                                    $client = $cl->fetch();

                                    if (!$client) {
                                        $not_found++;
                                        $row_details[] = ['status'=>'not_found','pan'=>$pan,'name'=>$name,'ack'=>'','filed'=>''];
                                        continue;
                                    }

                                    // Check for existing ITR entry for this FY
                                    $ex = $db->prepare("SELECT id FROM itr_returns WHERE client_id=? AND financial_year=? LIMIT 1");
                                    $ex->execute([$client['id'], $fy]);
                                    $entry = $ex->fetch();

                                    if ($entry) {
                                        // UPDATE — fill in filing fields only; leave accounting/prepared-by untouched
                                        $db->prepare(
                                            "UPDATE itr_returns SET
                                                itr_ack             = ?,
                                                filed_date          = ?,
                                                itr_uploaded_status = 'Yes',
                                                itr_prepared_status = CASE WHEN itr_prepared_status = 'No' THEN 'Yes' ELSE itr_prepared_status END,
                                                itr_form_no         = CASE WHEN ? <> '' THEN ? ELSE itr_form_no END,
                                                gti                 = CASE WHEN ? IS NOT NULL THEN ? ELSE gti END,
                                                e_verified          = ?,
                                                data_received_on    = COALESCE(data_received_on, ?)
                                             WHERE id = ?"
                                        )->execute([
                                            $itr_ack, $filed_date,
                                            $itr_form, $itr_form,
                                            $gti, $gti,
                                            $e_verified,
                                            $filed_date,
                                            $entry['id'],
                                        ]);
                                        auditLog('itr_returns', $entry['id'], 'UPDATE', null,
                                            ['source'=>'computax_import','pan'=>$pan,'ack'=>$itr_ack]);
                                        $updated++;
                                        $row_details[] = ['status'=>'updated','pan'=>$pan,'name'=>$name,'ack'=>$itr_ack,'filed'=>$filed_date];
                                    } else {
                                        // CREATE new entry — no prior data receipt done, filing already complete
                                        $db->prepare(
                                            "INSERT INTO itr_returns
                                                (client_id, financial_year, ca_partner_id, group_id,
                                                 itr_ack, filed_date, itr_uploaded_status,
                                                 itr_prepared_status, itr_form_no, gti, e_verified,
                                                 data_received_on, accounting_status, created_by)
                                             VALUES (?,?,?,?,?,?,'Yes','Yes',?,?,?,?,?,?)"
                                        )->execute([
                                            $client['id'], $fy,
                                            $client['partner_id'], $client['group_id'],
                                            $itr_ack, $filed_date,
                                            $itr_form ?: null, $gti, $e_verified,
                                            $filed_date,
                                            'NA',
                                            $_SESSION['user_id'],
                                        ]);
                                        auditLog('itr_returns', $db->lastInsertId(), 'CREATE', null,
                                            ['source'=>'computax_import','pan'=>$pan,'ack'=>$itr_ack]);
                                        $created++;
                                        $row_details[] = ['status'=>'created','pan'=>$pan,'name'=>$name,'ack'=>$itr_ack,'filed'=>$filed_date];
                                    }
                                }

                                $results[] = [
                                    'type' => 'success',
                                    'msg'  => "Import complete — <strong>$updated existing entries updated</strong>, <strong>$created new entries created</strong>, <strong>$not_found PAN not matched in client master</strong>" . ($skipped ? ", $skipped rows skipped" : ""),
                                ];
                                $results[] = ['type'=>'detail','rows'=>$row_details];
                            }
                        }
                    } catch (Exception $e) {
                        $results[] = ['type'=>'error', 'msg'=>'Database error: '.htmlspecialchars($e->getMessage())];
                    }
                }
            }
        }
    }
}

$fy_list = getFYList();
$dp      = defaultPeriod('itr');

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">📥 Import ITR Filing Data — Computax</div>
    <div class="page-subtitle">Uploads ACK, filing date, GTI, ITR form type and e-verification status — matched by PAN</div>
  </div>
  <a href="<?= url('itr_register.php') ?>" class="btn btn-outline">← IT Return Register</a>
</div>

<?php foreach ($results as $r): ?>
  <?php if ($r['type'] === 'success'): ?>
    <div style="padding:14px;border-radius:8px;background:var(--success-bg);border:1px solid var(--accent);margin-bottom:1.25rem;font-size:13px"><?= $r['msg'] ?></div>
  <?php elseif ($r['type'] === 'error'): ?>
    <div style="padding:14px;border-radius:8px;background:var(--danger-bg);border:1px solid var(--danger);color:var(--danger);margin-bottom:1.25rem;font-size:13px"><?= $r['msg'] ?></div>
  <?php elseif ($r['type'] === 'detail' && !empty($r['rows'])): ?>
    <div class="card" style="margin-bottom:1.25rem">
      <div class="card-header">
        <span class="card-title">Import Details</span>
        <?php
          $upd = count(array_filter($r['rows'], fn($x)=>$x['status']==='updated'));
          $cre = count(array_filter($r['rows'], fn($x)=>$x['status']==='created'));
          $nf  = count(array_filter($r['rows'], fn($x)=>$x['status']==='not_found'));
        ?>
        <span class="text-muted" style="font-size:12px"><?= $upd ?> updated &middot; <?= $cre ?> new &middot; <?= $nf ?> not found in client master</span>
      </div>
      <div class="table-responsive" style="max-height:380px;overflow-y:auto">
        <table class="data-table">
          <thead><tr><th>Result</th><th>PAN</th><th>Name</th><th>ACK Number</th><th>Filed Date</th></tr></thead>
          <tbody>
          <?php foreach ($r['rows'] as $row): ?>
            <tr>
              <td>
                <?php if ($row['status']==='updated'): ?><span class="badge badge-success">✓ Updated</span>
                <?php elseif ($row['status']==='created'): ?><span class="badge badge-info">+ New Entry</span>
                <?php else: ?><span class="badge badge-warning">⚠ Not Found</span>
                <?php endif; ?>
              </td>
              <td><code style="font-size:11px"><?= htmlspecialchars($row['pan']) ?></code></td>
              <td style="font-size:12px"><?= htmlspecialchars($row['name']) ?></td>
              <td style="font-size:11px"><code><?= htmlspecialchars($row['ack'] ?: '—') ?></code></td>
              <td style="font-size:12px"><?= $row['filed'] ? fmtDate($row['filed']) : '—' ?></td>
            </tr>
          <?php endforeach; ?>
          </tbody>
        </table>
      </div>
    </div>
  <?php endif; ?>
<?php endforeach; ?>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.25rem">

  <div class="card">
    <div class="card-header"><span class="card-title">📤 Upload Computax XLS Report</span></div>
    <div class="card-body">
      <div style="background:var(--primary-bg);padding:14px;border-radius:8px;margin-bottom:1.25rem;font-size:13px;line-height:1.9;border:1px solid var(--border-lt)">
        <strong>Export from Computax:</strong><br>
        Reports → Returns Filed Details → Select AY → Export to Excel (.xls)<br><br>
        <strong>Re-import is safe</strong> — existing entries update, no duplicates created.
      </div>
      <form method="post" enctype="multipart/form-data">
        <div class="form-group mb-2">
          <label>Financial Year <span class="req">*</span></label>
          <select class="form-control" name="financial_year" required>
            <?php foreach ($fy_list as $fy): ?>
              <option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group mb-2">
          <label>Computax XLS / XLSX File <span class="req">*</span></label>
          <input type="file" name="itr_file" accept=".xls,.xlsx" class="form-control" style="height:auto;padding:8px" required>
        </div>
        <div class="form-actions">
          <button class="btn btn-primary" type="submit">⬆ Upload &amp; Import</button>
        </div>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-title">ℹ What gets updated per client</span></div>
    <div class="card-body" style="font-size:13px;line-height:1.9">
      <p style="margin-bottom:10px"><strong>Matched by PAN.</strong> PANs not in your Client Master are listed as Not Found.</p>
      <p style="margin-bottom:6px"><strong>If register entry exists for this FY:</strong></p>
      <ul style="margin:0 0 12px 18px">
        <li>ITR ACK Number, Filing Date, ITR Form No., GTI → updated</li>
        <li>E-Verification Status → updated</li>
        <li>ITR Uploaded &amp; Prepared Status → set to Yes</li>
        <li>Data Received On → set to filing date <em>only if blank</em></li>
        <li style="color:var(--text-muted)">Accounting By, Prepared By, Verified By → <strong>not touched</strong></li>
      </ul>
      <p style="margin-bottom:6px"><strong>If no register entry exists yet:</strong></p>
      <ul style="margin:0 0 0 18px">
        <li>New entry created, ITR marked as Filed</li>
        <li>Accounting, Prepared By, Verified By → blank (fill in later from the register)</li>
      </ul>
    </div>
  </div>

</div>

<?php include 'includes/footer.php'; ?>
