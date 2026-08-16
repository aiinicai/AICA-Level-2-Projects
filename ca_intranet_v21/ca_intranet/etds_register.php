<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
$db = getDB();

// ── SCHEMA CHECK — covers both GET and POST ──────────────
try {
    $db->query("SELECT trigger_date, target_date, form16a_due_date, form16a_status FROM etds_returns LIMIT 1");
} catch (Exception $e) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $_SESSION['flash_msg'] = '⚠ Database upgrade required before entries can be saved. Run upgrade_dates.sql in phpMyAdmin first.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('etds_register.php')); exit;
    }
    include 'includes/header.php';
    echo '<div class="card" style="max-width:700px;margin:2rem auto"><div class="card-body">
        <h2 style="color:var(--danger)">⚠ Database Upgrade Required</h2>
        <p style="margin:1rem 0">The ETDS Register needs new columns (trigger/target dates, Form 16A tracking) that have not been added yet.</p>
        <p style="margin-bottom:1rem"><strong>Fix:</strong> Open phpMyAdmin → select <code>ca_intranet</code> →
        SQL tab → paste contents of <code>upgrade_dates.sql</code> → click Go.</p>
        <p style="font-size:12px;color:var(--text-muted)">Technical detail: '.htmlspecialchars($e->getMessage()).'</p>
        <a href="'.url('dashboard.php').'" class="btn btn-primary" style="margin-top:1rem">← Back to Dashboard</a>
    </div></div>';
    include 'includes/footer.php';
    exit;
}

$page_title = 'ETDS Return Register';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);
$stage  = $_GET['stage'] ?? 'list';
$dp     = defaultPeriod('etds');

// ── DELETE ────────────────────────────────────────────────
if ($action === 'delete' && $id && hasRole(['admin','partner','supervisor'])) {
    $db->prepare("DELETE FROM etds_returns WHERE id=?")->execute([$id]);
    auditLog('etds_returns', $id, 'DELETE');
    $_SESSION['flash_msg'] = 'Entry deleted.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('etds_register.php')); exit;
}

// ── SAVE / STAGE UPDATES ────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $d = $_POST;
    $pa = $d['post_action'] ?? '';

    // STAGE 1: Data Receipt — create new entry
    if ($pa === 'add_entry') {
        $qtr = $d['quarter'];
        $fy  = $d['financial_year'];
        $wd  = getETDSWorkflowDates($qtr, $fy);

        $db->prepare(
            "INSERT INTO etds_returns
                (client_id,tan,financial_year,quarter,form_type,due_date_return,trigger_date,target_date,form16a_due_date,
                 data_received_date,status,assigned_to,created_by)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
        )->execute([
            intval($d['client_id']), strtoupper(trim($d['tan'] ?? '')), $fy, $qtr, $d['form_type'] ?? '26Q',
            $wd['statutory'], $wd['trigger'], $wd['target'], $wd['form16a_due'],
            $d['data_received_date'] ?: date('Y-m-d'),
            'Data Received', $d['assigned_to'] ?: null, $_SESSION['user_id'],
        ]);
        auditLog('etds_returns', $db->lastInsertId(), 'CREATE');
        $_SESSION['flash_msg'] = 'Data receipt entry added.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=data')); exit;
    }

    // FULL EDIT (admin/partner/supervisor override)
    if ($pa === 'edit_entry') {
        $statutory_override = trim($d['due_date_override'] ?? '');
        $is_overridden = $statutory_override ? 1 : 0;
        $due = $statutory_override ?: $d['due_date_return'];

        $db->prepare(
            "UPDATE etds_returns SET
                client_id=?,tan=?,financial_year=?,quarter=?,form_type=?,due_date_return=?,due_date_overridden=?,
                data_received_date=?,total_tds_deducted=?,total_tds_deposited=?,
                return_prepared_by=?,return_prepared_date=?,return_reviewed_by=?,return_reviewed_date=?,
                return_filed_date=?,prn=?,form16a_due_date=?,form16a_downloaded_date=?,form16a_status=?,
                status=?,assigned_to=?,remarks=?
             WHERE id=?"
        )->execute([
            intval($d['client_id']), strtoupper(trim($d['tan']??'')), $d['financial_year'], $d['quarter'], $d['form_type'],
            $due, $is_overridden,
            $d['data_received_date'] ?: null, floatval($d['total_tds_deducted']??0), floatval($d['total_tds_deposited']??0),
            $d['return_prepared_by'] ?: null, $d['return_prepared_date'] ?: null,
            $d['return_reviewed_by'] ?: null, $d['return_reviewed_date'] ?: null,
            $d['return_filed_date'] ?: null, strtoupper(trim($d['prn']??'')),
            $d['form16a_due_date'] ?: null, $d['form16a_downloaded_date'] ?: null, $d['form16a_status'] ?? 'Pending',
            $d['status'] ?? 'Data Received', $d['assigned_to'] ?: null, trim($d['remarks']??''),
            intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Entry updated successfully.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=list')); exit;
    }

    // STAGE 2: Working Done (Challan prep, e.g. challan mail/computation)
    if ($pa === 'update_working') {
        $db->prepare(
            "UPDATE etds_returns SET
                total_tds_deducted=?, return_prepared_by=?, return_prepared_date=?, status='Working Done', remarks=?
             WHERE id=?"
        )->execute([
            floatval($d['total_tds_deducted']??0), $d['working_done_by'] ?: null, $d['working_done_date'] ?: date('Y-m-d'),
            trim($d['remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Working details saved.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=working')); exit;
    }

    // STAGE 3: Challan Sent (mail/details sent to client for payment)
    if ($pa === 'update_challan_sent') {
        $no_challan = isset($d['no_challan']);
        $db->prepare(
            "UPDATE etds_returns SET status=?, remarks=? WHERE id=?"
        )->execute([
            $no_challan ? 'No Challan Due' : 'Challan Sent', trim($d['remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = $no_challan ? 'Marked as No Challan Due.' : 'Marked as Challan Sent.';
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=challan')); exit;
    }

    // STAGE 4: Challan Paid (receipt of paid challan from client)
    if ($pa === 'update_challan_paid') {
        $db->prepare(
            "UPDATE etds_returns SET total_tds_deposited=?, status='Challan Paid', remarks=CONCAT(IFNULL(remarks,''),' | Challan paid: ',?) WHERE id=?"
        )->execute([
            floatval($d['total_tds_deposited']??0), trim($d['paid_remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Challan marked as paid.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=paid')); exit;
    }

    // STAGE 5: Return Preparation
    if ($pa === 'update_preparation') {
        $db->prepare(
            "UPDATE etds_returns SET return_prepared_by=?, return_prepared_date=?, return_reviewed_by=?, return_reviewed_date=?, status='Return Prepared', remarks=? WHERE id=?"
        )->execute([
            $d['return_prepared_by'] ?: null, $d['return_prepared_date'] ?: date('Y-m-d'),
            $d['return_reviewed_by'] ?: null, $d['return_reviewed_date'] ?: null,
            trim($d['remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Return preparation details saved.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=preparation')); exit;
    }

    // STAGE 6: Filing of Return — auto-sets Form 16A due date trigger (already set at creation, but re-confirm)
    if ($pa === 'update_filing') {
        $db->prepare(
            "UPDATE etds_returns SET return_filed_date=?, prn=?, status='Filed', form16a_status='Pending', remarks=? WHERE id=?"
        )->execute([
            $d['return_filed_date'] ?: date('Y-m-d'), strtoupper(trim($d['prn']??'')),
            trim($d['remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Return filed. Form 16A is now due in 15 days from the statutory due date.';
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=filing')); exit;
    }

    // STAGE 7: Form 16A Download — closes the record
    if ($pa === 'update_form16a') {
        $no_form16a = isset($d['no_form16a']);
        $db->prepare(
            "UPDATE etds_returns SET form16a_downloaded_date=?, form16a_status=?, status=?, remarks=? WHERE id=?"
        )->execute([
            $no_form16a ? null : ($d['form16a_downloaded_date'] ?: date('Y-m-d')),
            $no_form16a ? 'Not Applicable' : 'Downloaded',
            $no_form16a ? 'Filed' : 'Form 16A Downloaded',
            trim($d['remarks']??''), intval($d['etds_id']),
        ]);
        auditLog('etds_returns', intval($d['etds_id']), 'UPDATE');
        $_SESSION['flash_msg'] = $no_form16a ? 'Marked as Form 16A Not Applicable.' : 'Form 16A marked as downloaded. Record closed.';
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=form16a')); exit;
    }

    // Manual statutory due date override (govt extension)
    if ($pa === 'override_due_date') {
        $new_due = $d['new_due_date'] ?? '';
        if ($new_due) {
            // Recompute Form 16A due date based on new statutory date (+15 days)
            $new_form16a_due = date('Y-m-d', strtotime($new_due.' +15 days'));
            $db->prepare(
                "UPDATE etds_returns SET due_date_return=?, due_date_overridden=1, form16a_due_date=?,
                 remarks=CONCAT(IFNULL(remarks,''),' | Due date extended to ',?,': ',?) WHERE id=?"
            )->execute([$new_due, $new_form16a_due, $new_due, trim($d['override_reason']??''), intval($d['etds_id'])]);
            auditLog('etds_returns', intval($d['etds_id']), 'UPDATE', null, ['due_date_override'=>$new_due]);
            $_SESSION['flash_msg'] = 'Statutory due date updated to '.fmtDate($new_due).'. Form 16A due date recalculated.';
            $_SESSION['flash_type'] = 'success';
        }
        header('Location: '.url('etds_register.php?stage=list')); exit;
    }

    // BULK CREATE
    if ($pa === 'bulk_create') {
        $fy = $d['financial_year']; $qtr = $d['quarter']; $ft = $d['form_type'];
        $wd = getETDSWorkflowDates($qtr, $fy);

        $selected_ids = array_filter(array_map('intval', $d['client_ids'] ?? []));
        if (!empty($selected_ids)) {
            $placeholders = implode(',', array_fill(0, count($selected_ids), '?'));
            $stmt = $db->prepare("SELECT id, tan, supervisor_id FROM clients WHERE tds_applicable=1 AND status='Active' AND tan IS NOT NULL AND tan != '' AND id IN ($placeholders)");
            $stmt->execute($selected_ids);
        } else {
            $stmt = $db->query("SELECT id, tan, supervisor_id FROM clients WHERE tds_applicable=1 AND status='Active' AND tan IS NOT NULL AND tan != ''");
        }
        $tds_clients = $stmt->fetchAll();

        $created = 0;
        foreach ($tds_clients as $c) {
            $chk = $db->prepare("SELECT id FROM etds_returns WHERE client_id=? AND financial_year=? AND quarter=? AND form_type=?");
            $chk->execute([$c['id'], $fy, $qtr, $ft]); if ($chk->fetch()) continue;
            $db->prepare(
                "INSERT INTO etds_returns (client_id,tan,financial_year,quarter,form_type,due_date_return,trigger_date,target_date,form16a_due_date,status,assigned_to,created_by)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
            )->execute([$c['id'], $c['tan'], $fy, $qtr, $ft, $wd['statutory'], $wd['trigger'], $wd['target'], $wd['form16a_due'], 'Pending Data', $c['supervisor_id'], $_SESSION['user_id']]);
            $created++;
        }
        $_SESSION['flash_msg'] = "Bulk create done: $created entries created."; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('etds_register.php?stage=list')); exit;
    }
}

// ── FETCH SINGLE ENTRY ────────────────────────────────────
$entry = [];
if ($id) {
    $stmt = $db->prepare("SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id WHERE e.id=?");
    $stmt->execute([$id]); $entry = $stmt->fetch() ?: [];
}

// ── LIST FILTERS ───────────────────────────────────────────
$filter_fy     = array_key_exists('fy', $_GET) ? trim($_GET['fy']) : $dp['fy'];
$filter_qtr    = $_GET['quarter']      ?? '';
$filter_form   = $_GET['form_type']    ?? '';
$filter_status = $_GET['status']       ?? '';
$filter_name   = trim($_GET['client_name'] ?? '');
$filter_sup    = intval($_GET['supervisor_id'] ?? 0);
$filter_due    = $_GET['due']          ?? '';
$page = max(1, intval($_GET['page'] ?? 1)); $per = 30;

$where = ['1=1']; $wp = [];
if ($filter_fy)     { $where[] = 'e.financial_year=?'; $wp[] = $filter_fy; }
if ($filter_qtr)    { $where[] = 'e.quarter=?'; $wp[] = $filter_qtr; }
if ($filter_form)   { $where[] = 'e.form_type=?'; $wp[] = $filter_form; }
if ($filter_status) { $where[] = 'e.status=?'; $wp[] = $filter_status; }
if ($filter_name)   { $where[] = 'c.client_name LIKE ?'; $wp[] = "%$filter_name%"; }
if ($filter_sup)    { $where[] = 'c.supervisor_id=?'; $wp[] = $filter_sup; }
if ($filter_due === 'overdue') { $where[] = 'e.due_date_return < CURDATE() AND e.status NOT IN("Filed","Form 16A Downloaded","Not Applicable")'; }
if ($filter_due === '7d')      { $where[] = 'e.due_date_return BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 7 DAY) AND e.status NOT IN("Filed","Form 16A Downloaded","Not Applicable")'; }
if ($_SESSION['role']==='supervisor') { $where[] = 'c.supervisor_id=?'; $wp[] = $_SESSION['user_id']; }
if ($_SESSION['role']==='staff')      { $where[] = 'e.assigned_to=?'; $wp[] = $_SESSION['user_id']; }
$ws = implode(' AND ', $where);

$total = $db->prepare("SELECT COUNT(*) FROM etds_returns e JOIN clients c ON c.id=e.client_id WHERE $ws");
$total->execute($wp); $total = $total->fetchColumn();
$pg = paginate($total, $per, $page);

$rows = $db->prepare(
    "SELECT e.*, c.client_name, c.pan, u.name assigned_name, wp.name prep_name, wr.name rev_name
     FROM etds_returns e
     JOIN clients c ON c.id=e.client_id
     LEFT JOIN users u  ON u.id=e.assigned_to
     LEFT JOIN users wp ON wp.id=e.return_prepared_by
     LEFT JOIN users wr ON wr.id=e.return_reviewed_by
     WHERE $ws ORDER BY e.due_date_return ASC,c.client_name ASC LIMIT ? OFFSET ?"
);
$rows->execute(array_merge($wp, [$per, $pg['offset']]));
$entries = $rows->fetchAll();

// ── STAGE QUEUES ───────────────────────────────────────────
$q_working = $db->query(
    "SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id
     WHERE e.status='Data Received' ORDER BY e.due_date_return ASC,c.client_name"
)->fetchAll();

$q_challan = $db->query(
    "SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id
     WHERE e.status='Working Done' ORDER BY e.due_date_return ASC,c.client_name"
)->fetchAll();

$q_paid = $db->query(
    "SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id
     WHERE e.status='Challan Sent' ORDER BY e.due_date_return ASC,c.client_name"
)->fetchAll();

$q_preparation = $db->query(
    "SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id
     WHERE e.status IN('Challan Paid','No Challan Due') ORDER BY e.due_date_return ASC,c.client_name"
)->fetchAll();

$q_filing = $db->query(
    "SELECT e.*,c.client_name,c.pan,wp.name prep_name FROM etds_returns e
     JOIN clients c ON c.id=e.client_id LEFT JOIN users wp ON wp.id=e.return_prepared_by
     WHERE e.status='Return Prepared' ORDER BY e.due_date_return ASC,c.client_name"
)->fetchAll();

// Form 16A queue — filed, form16a not yet downloaded, AND today >= form16a_due_date - 15 (i.e. trigger as soon as filed)
$q_form16a = $db->query(
    "SELECT e.*,c.client_name,c.pan FROM etds_returns e JOIN clients c ON c.id=e.client_id
     WHERE e.status='Filed' AND e.form16a_status='Pending'
     ORDER BY e.form16a_due_date ASC,c.client_name"
)->fetchAll();

// ── EXECUTIVE SUMMARY ──────────────────────────────────────
$summary = null;
if ($filter_fy) {
    $sw = ['e.financial_year=?']; $sp = [$filter_fy];
    if ($filter_qtr)  { $sw[] = 'e.quarter=?'; $sp[] = $filter_qtr; }
    if ($filter_form) { $sw[] = 'e.form_type=?'; $sp[] = $filter_form; }
    $sws = implode(' AND ', $sw);
    $stmt = $db->prepare("SELECT e.* FROM etds_returns e JOIN clients c ON c.id=e.client_id WHERE $sws");
    $stmt->execute($sp);
    $s_rows = $stmt->fetchAll();

    $total_count=count($s_rows); $data_pending=0; $working_pending=0; $challan_pending=0; $paid_pending=0;
    $prep_pending=0; $filing_pending=0; $form16a_pending=0; $filed=0; $closed=0;
    foreach ($s_rows as $r) {
        if ($r['status']==='Pending Data') $data_pending++;
        if ($r['status']==='Data Received') $working_pending++;
        if ($r['status']==='Working Done') $challan_pending++;
        if ($r['status']==='Challan Sent') $paid_pending++;
        if (in_array($r['status'],['Challan Paid','No Challan Due'])) $prep_pending++;
        if ($r['status']==='Return Prepared') $filing_pending++;
        if ($r['status']==='Filed' && $r['form16a_status']==='Pending') $form16a_pending++;
        if (in_array($r['status'],['Filed','Form 16A Downloaded'])) $filed++;
        if ($r['status']==='Form 16A Downloaded' || $r['form16a_status']==='Not Applicable') $closed++;
    }
    $summary = compact('total_count','data_pending','working_pending','challan_pending','paid_pending','prep_pending','filing_pending','form16a_pending','filed','closed');
}

$all_clients   = $db->query("SELECT id,client_name,pan,tan,group_id FROM clients WHERE tds_applicable=1 AND status='Active' ORDER BY client_name")->fetchAll();
$client_groups = $db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$all_users   = $db->query("SELECT id,name FROM users WHERE is_active=1 ORDER BY name")->fetchAll();
$fy_list     = getFYList();

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">📋 ETDS Return Register</div>
    <div class="page-subtitle">FY: <?= htmlspecialchars($filter_fy) ?> &nbsp;|&nbsp; Total entries: <?= $total ?></div>
  </div>
  <div class="d-flex gap-1" style="align-items:center">
    <form method="get" style="display:inline-flex;gap:6px;align-items:center">
      <input type="hidden" name="stage" value="<?= htmlspecialchars($stage) ?>">
      <label style="font-size:12px;color:var(--text-muted);white-space:nowrap">Viewing FY:</label>
      <select name="fy" class="form-control" style="width:auto;height:34px" onchange="this.form.submit()">
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$filter_fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select>
    </form>
    <?php if (hasRole(['admin','partner','supervisor'])): ?>
    <a href="<?= url('etds_register.php?action=bulk_create') ?>" class="btn btn-outline">⚡ Bulk Create</a>
    <?php endif; ?>
    <a href="<?= url('etds_register.php?stage=data') ?>" class="btn btn-primary">+ Add Entry</a>
  </div>
</div>

<!-- STAGE TAB NAV -->
<div style="display:flex;gap:0;margin-bottom:1.25rem;border-radius:8px;overflow:hidden;border:1px solid var(--border);flex-wrap:wrap">
<?php
$stages = [
  'list'        => ['⊞ All Entries',  count($entries).' shown'],
  'data'        => ['① Data Receipt', 'Add new'],
  'working'     => ['② Working Done', count($q_working).' pending'],
  'challan'     => ['③ Send Challan', count($q_challan).' pending'],
  'paid'        => ['④ Challan Paid', count($q_paid).' waiting'],
  'preparation' => ['⑤ Return Prep',  count($q_preparation).' ready'],
  'filing'      => ['⑥ File Return',  count($q_filing).' ready'],
  'form16a'     => ['⑦ Form 16A',     count($q_form16a).' due'],
];
foreach ($stages as $s => [$label,$count]):
    $active = ($stage === $s);
?>
<a href="<?= url("etds_register.php?stage=$s") ?>"
   style="flex:1;min-width:100px;padding:9px 5px;text-align:center;font-size:11px;font-weight:<?= $active?'600':'400' ?>;
          background:<?= $active?'var(--primary)':'var(--bg-card)' ?>;
          color:<?= $active?'#fff':'var(--text)' ?>;text-decoration:none;border-right:1px solid var(--border)">
  <?= $label ?><br><span style="font-size:10px;opacity:.75"><?= $count ?></span>
</a>
<?php endforeach; ?>
</div>

<?php if ($action === 'bulk_create'): ?>
<!-- ══ BULK CREATE ══ -->
<div class="card" style="max-width:720px">
  <div class="card-header"><span class="card-title">⚡ Bulk Create ETDS Entries</span></div>
  <div class="card-body">
  <form method="post" action="<?= url('etds_register.php?stage=list') ?>">
    <input type="hidden" name="post_action" value="bulk_create">
    <div class="form-grid form-grid-3">
      <div class="form-group"><label>Financial Year <span class="req">*</span></label>
        <select class="form-control" name="financial_year" required>
          <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Quarter <span class="req">*</span></label>
        <select class="form-control" name="quarter" required>
          <?php foreach (['Q1'=>'Q1 (Apr-Jun)','Q2'=>'Q2 (Jul-Sep)','Q3'=>'Q3 (Oct-Dec)','Q4'=>'Q4 (Jan-Mar)'] as $qv=>$ql): ?>
            <option value="<?= $qv ?>"><?= $ql ?></option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Form Type <span class="req">*</span></label>
        <select class="form-control" name="form_type" required>
          <?php foreach (['24Q','26Q','27Q','27EQ'] as $ft): ?><option value="<?= $ft ?>"><?= $ft ?></option><?php endforeach; ?>
        </select></div>
    </div>

    <div class="form-section mt-2">
      <div class="form-section-title">
        Select Clients <small style="font-size:11px;font-weight:400;color:var(--text-muted)">— leave none selected to apply to ALL TDS clients</small>
      </div>
      <div class="form-grid form-grid-3 mb-1">
        <div class="form-group">
          <label>Filter by Group</label>
          <select class="form-control" id="bulk_group_filter" onchange="filterClientsByGroup('bulk_group_filter','bulk_client_ids')">
            <option value="">— All Groups —</option>
            <?php foreach ($client_groups as $g): ?>
              <option value="<?= $g['id'] ?>"><?= htmlspecialchars($g['group_name']) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group" style="justify-content:flex-end">
          <label style="visibility:hidden">.</label>
          <div class="d-flex gap-1">
            <button type="button" class="btn btn-outline btn-sm" onclick="selectAllVisibleClients('bulk_client_ids');updateClientSelectionCount('bulk_client_ids','bulk_sel_count')">Select All Visible</button>
            <button type="button" class="btn btn-outline btn-sm" onclick="selectNoneClients('bulk_client_ids');updateClientSelectionCount('bulk_client_ids','bulk_sel_count')">Clear</button>
          </div>
        </div>
        <div class="form-group" style="justify-content:center;align-items:flex-end">
          <span id="bulk_sel_count" class="text-muted" style="font-size:12px">0 clients selected</span>
        </div>
      </div>
      <select class="form-control" name="client_ids[]" id="bulk_client_ids" multiple size="10"
              onchange="updateClientSelectionCount('bulk_client_ids','bulk_sel_count')" style="height:220px">
        <?php foreach ($all_clients as $c): ?>
          <option value="<?= $c['id'] ?>" data-group="<?= $c['group_id'] ?? '' ?>"><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
        <?php endforeach; ?>
      </select>
    </div>

    <div class="form-actions">

      <button class="btn btn-primary" type="submit">Generate Entries</button>
      <a href="<?= url('etds_register.php') ?>" class="btn btn-outline">Cancel</a>
    </div>
  </form>
  </div>
</div>

<?php elseif ($action === 'edit'): ?>
<!-- ══ FULL EDIT (override) ══ -->
<div class="page-header">
  <div class="page-title">✏️ Edit ETDS Entry (Full Override)</div>
  <a href="<?= url('etds_register.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card"><div class="card-body">
<form method="post" action="<?= url('etds_register.php?stage=list') ?>">
  <input type="hidden" name="post_action" value="edit_entry">
  <input type="hidden" name="etds_id" value="<?= $id ?>">
  <div class="form-grid form-grid-4">
    <div class="form-group" style="grid-column:span 2"><label>Client</label>
      <select class="form-control" name="client_id" required>
        <?php foreach ($all_clients as $c): ?>
          <option value="<?= $c['id'] ?>" <?= ($entry['client_id']??0)==$c['id']?'selected':'' ?>><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>TAN</label>
      <input class="form-control" name="tan" style="text-transform:uppercase" value="<?= htmlspecialchars($entry['tan']??'') ?>"></div>
    <div class="form-group"><label>FY</label>
      <select class="form-control" name="financial_year">
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= ($entry['financial_year']??'')===$fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Quarter</label>
      <select class="form-control" name="quarter">
        <?php foreach (['Q1','Q2','Q3','Q4'] as $q): ?><option value="<?= $q ?>" <?= ($entry['quarter']??'')===$q?'selected':'' ?>><?= $q ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Form Type</label>
      <select class="form-control" name="form_type">
        <?php foreach (['24Q','26Q','27Q','27EQ'] as $ft): ?><option value="<?= $ft ?>" <?= ($entry['form_type']??'')===$ft?'selected':'' ?>><?= $ft ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Statutory Due Date</label>
      <input class="form-control" type="date" name="due_date_return" value="<?= $entry['due_date_return']??'' ?>"></div>
    <div class="form-group"><label>Data Received On</label>
      <input class="form-control" type="date" name="data_received_date" value="<?= $entry['data_received_date']??'' ?>"></div>
    <div class="form-group"><label>TDS Deducted</label>
      <input class="form-control" type="number" step="0.01" name="total_tds_deducted" value="<?= $entry['total_tds_deducted']??0 ?>"></div>
    <div class="form-group"><label>TDS Deposited</label>
      <input class="form-control" type="number" step="0.01" name="total_tds_deposited" value="<?= $entry['total_tds_deposited']??0 ?>"></div>
    <div class="form-group"><label>Prepared By</label>
      <select class="form-control" name="return_prepared_by"><option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['return_prepared_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Prepared Date</label>
      <input class="form-control" type="date" name="return_prepared_date" value="<?= $entry['return_prepared_date']??'' ?>"></div>
    <div class="form-group"><label>Reviewed By</label>
      <select class="form-control" name="return_reviewed_by"><option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['return_reviewed_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Reviewed Date</label>
      <input class="form-control" type="date" name="return_reviewed_date" value="<?= $entry['return_reviewed_date']??'' ?>"></div>
    <div class="form-group"><label>Filed Date</label>
      <input class="form-control" type="date" name="return_filed_date" value="<?= $entry['return_filed_date']??'' ?>"></div>
    <div class="form-group"><label>PRN</label>
      <input class="form-control" name="prn" style="text-transform:uppercase" value="<?= htmlspecialchars($entry['prn']??'') ?>"></div>
    <div class="form-group"><label>Form 16A Due Date</label>
      <input class="form-control" type="date" name="form16a_due_date" value="<?= $entry['form16a_due_date']??'' ?>"></div>
    <div class="form-group"><label>Form 16A Downloaded Date</label>
      <input class="form-control" type="date" name="form16a_downloaded_date" value="<?= $entry['form16a_downloaded_date']??'' ?>"></div>
    <div class="form-group"><label>Form 16A Status</label>
      <select class="form-control" name="form16a_status">
        <?php foreach (['Pending','Downloaded','Not Applicable'] as $s): ?><option value="<?= $s ?>" <?= ($entry['form16a_status']??'')===$s?'selected':'' ?>><?= $s ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Status</label>
      <select class="form-control" name="status">
        <?php foreach (['Pending Data','Data Received','Working Done','Challan Sent','No Challan Due','Challan Paid','Return Prepared','Filed','Form 16A Downloaded','On Hold','Not Applicable'] as $s): ?>
          <option value="<?= $s ?>" <?= ($entry['status']??'')===$s?'selected':'' ?>><?= $s ?></option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Assigned To</label>
      <select class="form-control" name="assigned_to"><option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['assigned_to']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group" style="grid-column:span 4"><label>Remarks</label>
      <textarea class="form-control" name="remarks" rows="2"><?= htmlspecialchars($entry['remarks']??'') ?></textarea></div>
  </div>
  <div class="form-actions">
    <button class="btn btn-primary" type="submit">💾 Save Changes</button>
    <a href="<?= url('etds_register.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>

<?php elseif ($stage === 'data'): ?>
<!-- ══ STAGE 1: DATA RECEIPT ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">① Add Data Receipt Entry</span>
    <span class="text-muted" style="font-size:12px">Trigger/Target/Statutory dates and Form 16A due date are computed automatically</span>
  </div>
  <div class="card-body">
  <form method="post" action="<?= url('etds_register.php?stage=data') ?>">
    <input type="hidden" name="post_action" value="add_entry">
    <div class="form-grid form-grid-4">
      <div class="form-group" style="grid-column:span 2"><label>Client <span class="req">*</span></label>
        <select class="form-control" name="client_id" required onchange="fillTAN(this)">
          <option value="">— Select Client —</option>
          <?php foreach ($all_clients as $c): ?>
            <option value="<?= $c['id'] ?>" data-tan="<?= htmlspecialchars($c['tan']??'') ?>"><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>TAN</label>
        <input class="form-control" id="tan_field" name="tan" style="text-transform:uppercase"></div>
      <div class="form-group"><label>Financial Year</label>
        <select class="form-control" name="financial_year">
          <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Quarter <span class="req">*</span></label>
        <select class="form-control" name="quarter" required>
          <?php foreach (['Q1'=>'Q1 (Apr-Jun)','Q2'=>'Q2 (Jul-Sep)','Q3'=>'Q3 (Oct-Dec)','Q4'=>'Q4 (Jan-Mar)'] as $qv=>$ql): ?>
            <option value="<?= $qv ?>"><?= $ql ?></option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Form Type</label>
        <select class="form-control" name="form_type">
          <?php foreach (['24Q'=>'24Q (Salary)','26Q'=>'26Q (Non-Salary)','27Q'=>'27Q (Foreign)','27EQ'=>'27EQ (TCS)'] as $fv=>$fl): ?>
            <option value="<?= $fv ?>"><?= $fl ?></option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Data Received On</label>
        <input class="form-control" type="date" name="data_received_date" value="<?= date('Y-m-d') ?>"></div>
      <div class="form-group"><label>Assign To</label>
        <select class="form-control" name="assigned_to"><option value="">Select</option>
          <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
        </select></div>
    </div>
    <div class="form-actions">
      <button class="btn btn-primary" type="submit">💾 Save Data Receipt</button>
    </div>
  </form>
  </div>
</div>

<?php elseif ($stage === 'working'): ?>
<!-- ══ STAGE 2: WORKING DONE (Challan computation/mail prep) ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">② Working Done — Challan Computation</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_working) ?> entries with data received, working pending</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>Form</th><th>Statutory Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_working)): ?><tr><td colspan="5" class="text-center text-muted" style="padding:2rem">No entries pending working.</td></tr><?php endif; ?>
    <?php foreach ($q_working as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td><span class="badge badge-primary"><?= $r['form_type'] ?></span></td>
        <td><?= dueDateBadge($r['due_date_return']) ?></td>
        <td><button class="btn btn-primary btn-sm" onclick="openWorkingModal(<?= htmlspecialchars(json_encode($r)) ?>)">Mark Working Done</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="working-modal">
  <div class="modal-box" style="max-width:460px">
    <div class="modal-header"><span class="modal-title">② Working Details (Challan Computation)</span><button class="modal-close" onclick="closeModal('working-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=working') ?>">
      <input type="hidden" name="post_action" value="update_working">
      <input type="hidden" name="etds_id" id="wm_etds_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="wm_info"></div>
        <div class="form-group mb-2"><label>Total TDS Deducted (₹)</label>
          <input class="form-control" type="number" step="0.01" name="total_tds_deducted" required></div>
        <div class="form-group mb-2"><label>Working Done By</label>
          <select class="form-control" name="working_done_by"><option value="">Select</option>
            <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
          </select></div>
        <div class="form-group mb-2"><label>Working Done Date</label>
          <input class="form-control" type="date" name="working_done_date" value="<?= date('Y-m-d') ?>"></div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('working-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'challan'): ?>
<!-- ══ STAGE 3: SEND CHALLAN ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">③ Send Challan to Client</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_challan) ?> entries with working done</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>TDS Deducted</th><th>Statutory Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_challan)): ?><tr><td colspan="5" class="text-center text-muted" style="padding:2rem">No entries waiting for challan dispatch.</td></tr><?php endif; ?>
    <?php foreach ($q_challan as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td class="text-right">₹<?= number_format($r['total_tds_deducted'],0) ?></td>
        <td><?= dueDateBadge($r['due_date_return']) ?></td>
        <td><button class="btn btn-primary btn-sm" onclick="openChallanSentModal(<?= htmlspecialchars(json_encode($r)) ?>)">Send Challan</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="challan-sent-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header"><span class="modal-title">③ Send Challan</span><button class="modal-close" onclick="closeModal('challan-sent-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=challan') ?>">
      <input type="hidden" name="post_action" value="update_challan_sent">
      <input type="hidden" name="etds_id" id="csm_etds_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="csm_info"></div>
        <label style="display:flex;align-items:center;gap:8px;margin-bottom:10px;cursor:pointer">
          <input type="checkbox" name="no_challan"> No Challan Due (Nil TDS this quarter)
        </label>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2" placeholder="e.g. Challan emailed to client"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Confirm Sent</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('challan-sent-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'paid'): ?>
<!-- ══ STAGE 4: CHALLAN PAID ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">④ Receipt of Paid Challan</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_paid) ?> entries with challan sent, awaiting payment confirmation</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>TDS Deducted</th><th>Statutory Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_paid)): ?><tr><td colspan="5" class="text-center text-muted" style="padding:2rem">No challans pending payment confirmation.</td></tr><?php endif; ?>
    <?php foreach ($q_paid as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td class="text-right">₹<?= number_format($r['total_tds_deducted'],0) ?></td>
        <td><?= dueDateBadge($r['due_date_return']) ?></td>
        <td><button class="btn btn-success btn-sm" onclick="openPaidModal(<?= htmlspecialchars(json_encode($r)) ?>)">Mark Paid</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="paid-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header"><span class="modal-title">④ Confirm Challan Payment</span><button class="modal-close" onclick="closeModal('paid-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=paid') ?>">
      <input type="hidden" name="post_action" value="update_challan_paid">
      <input type="hidden" name="etds_id" id="pdm_etds_id">
      <div class="modal-body">
        <div style="background:var(--accent-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="pdm_info"></div>
        <div class="form-group mb-2"><label>Total TDS Deposited (₹)</label>
          <input class="form-control" type="number" step="0.01" name="total_tds_deposited" required></div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="paid_remarks" rows="2" placeholder="BSR code, challan no."></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Confirm Paid</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('paid-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'preparation'): ?>
<!-- ══ STAGE 5: RETURN PREPARATION ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">⑤ Return Preparation</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_preparation) ?> entries with challan paid / no challan due, ready for return prep</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>Statutory Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_preparation)): ?><tr><td colspan="4" class="text-center text-muted" style="padding:2rem">No entries ready for return preparation.</td></tr><?php endif; ?>
    <?php foreach ($q_preparation as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td><?= dueDateBadge($r['due_date_return']) ?></td>
        <td><button class="btn btn-primary btn-sm" onclick="openPrepModal(<?= htmlspecialchars(json_encode($r)) ?>)">Prepare Return</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="prep-modal">
  <div class="modal-box" style="max-width:480px">
    <div class="modal-header"><span class="modal-title">⑤ Return Preparation Details</span><button class="modal-close" onclick="closeModal('prep-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=preparation') ?>">
      <input type="hidden" name="post_action" value="update_preparation">
      <input type="hidden" name="etds_id" id="prm_etds_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="prm_info"></div>
        <div class="form-grid form-grid-2">
          <div class="form-group"><label>Prepared By</label>
            <select class="form-control" name="return_prepared_by"><option value="">Select</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>Prepared Date</label>
            <input class="form-control" type="date" name="return_prepared_date" value="<?= date('Y-m-d') ?>"></div>
          <div class="form-group"><label>Reviewed By</label>
            <select class="form-control" name="return_reviewed_by"><option value="">Select</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>Reviewed Date</label>
            <input class="form-control" type="date" name="return_reviewed_date" value="<?= date('Y-m-d') ?>"></div>
        </div>
        <div class="form-group mt-2"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('prep-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'filing'): ?>
<!-- ══ STAGE 6: FILE RETURN ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">⑥ File Return</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_filing) ?> entries prepared, ready to file — Form 16A becomes due automatically (+15 days) once filed</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>Prepared By</th><th>Statutory Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_filing)): ?><tr><td colspan="5" class="text-center text-muted" style="padding:2rem">No entries ready to file.</td></tr><?php endif; ?>
    <?php foreach ($q_filing as $r): ?>
      <tr class="<?= daysUntil($r['due_date_return'])<0?'row-overdue':(daysUntil($r['due_date_return'])<=7?'row-due-soon':'') ?>">
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td style="font-size:12px"><?= htmlspecialchars($r['prep_name']??'—') ?></td>
        <td><?= dueDateBadge($r['due_date_return']) ?></td>
        <td><button class="btn btn-success btn-sm" onclick="openFilingModal(<?= htmlspecialchars(json_encode($r)) ?>)">File Return</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="filing-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header"><span class="modal-title">⑥ Filing Details</span><button class="modal-close" onclick="closeModal('filing-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=filing') ?>">
      <input type="hidden" name="post_action" value="update_filing">
      <input type="hidden" name="etds_id" id="fm_etds_id">
      <div class="modal-body">
        <div style="background:var(--success-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="fm_info"></div>
        <div class="form-group mb-2"><label>Filing Date <span class="req">*</span></label>
          <input class="form-control" type="date" name="return_filed_date" value="<?= date('Y-m-d') ?>" required></div>
        <div class="form-group mb-2"><label>PRN (Provisional Receipt No.) <span class="req">*</span></label>
          <input class="form-control" name="prn" style="text-transform:uppercase" required></div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Mark as Filed</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('filing-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'form16a'): ?>
<!-- ══ STAGE 7: FORM 16A DOWNLOAD ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">⑦ Form 16A Download</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_form16a) ?> entries filed, Form 16A pending — due 15 days from statutory due date</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>Client</th><th>FY/Qtr</th><th>PRN</th><th>Filed Date</th><th>Form 16A Due</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_form16a)): ?><tr><td colspan="6" class="text-center text-muted" style="padding:2rem">No Form 16A downloads pending.</td></tr><?php endif; ?>
    <?php foreach ($q_form16a as $r): ?>
      <tr class="<?= daysUntil($r['form16a_due_date'])<0?'row-overdue':(daysUntil($r['form16a_due_date'])<=7?'row-due-soon':'') ?>">
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><?= htmlspecialchars($r['financial_year']) ?> / <?= $r['quarter'] ?></td>
        <td style="font-size:11px"><code><?= htmlspecialchars($r['prn']?:'—') ?></code></td>
        <td style="font-size:12px"><?= fmtDate($r['return_filed_date']) ?></td>
        <td><?= dueDateBadge($r['form16a_due_date']) ?></td>
        <td><button class="btn btn-success btn-sm" onclick="openForm16aModal(<?= htmlspecialchars(json_encode($r)) ?>)">Mark Downloaded</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<div class="modal-overlay" id="form16a-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header"><span class="modal-title">⑦ Form 16A Download</span><button class="modal-close" onclick="closeModal('form16a-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=form16a') ?>">
      <input type="hidden" name="post_action" value="update_form16a">
      <input type="hidden" name="etds_id" id="f16_etds_id">
      <div class="modal-body">
        <div style="background:var(--success-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="f16_info"></div>
        <label style="display:flex;align-items:center;gap:8px;margin-bottom:10px;cursor:pointer">
          <input type="checkbox" name="no_form16a" onchange="document.getElementById('f16_date_field').style.display=this.checked?'none':'block'">
          Not Applicable for this quarter
        </label>
        <div id="f16_date_field">
          <div class="form-group"><label>Downloaded Date</label>
            <input class="form-control" type="date" name="form16a_downloaded_date" value="<?= date('Y-m-d') ?>"></div>
        </div>
        <div class="form-group mt-2"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Save &amp; Close Record</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('form16a-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php else: // LIST VIEW ?>

<?php if ($summary): ?>
<div class="card" style="margin-bottom:1.25rem;border-left:4px solid var(--primary)">
  <div class="card-header" style="background:var(--primary-bg)">
    <span class="card-title" style="color:var(--primary)">📊 Executive Summary — FY <?= htmlspecialchars($filter_fy) ?></span>
  </div>
  <div class="card-body" style="padding:14px">
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;text-align:center;margin-bottom:8px">
      <div style="padding:10px 6px;background:#f8f9fa;border-radius:6px;border:1px solid var(--border-lt)">
        <div style="font-size:20px;font-weight:700;color:var(--primary)"><?= $summary['total_count'] ?></div>
        <div style="font-size:10px;color:var(--text-muted)">Total Cases</div>
      </div>
      <a href="<?= url('etds_register.php?stage=working') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#fdf0ef;border-radius:6px;border:1px solid #fecaca">
        <div style="font-size:20px;font-weight:700;color:#c0392b"><?= $summary['data_pending']+$summary['working_pending'] ?></div>
        <div style="font-size:10px;color:#c0392b">Data/Working Pending</div>
      </div></a>
      <a href="<?= url('etds_register.php?stage=challan') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#fef9ec;border-radius:6px;border:1px solid #fed7aa">
        <div style="font-size:20px;font-weight:700;color:#b45309"><?= $summary['challan_pending']+$summary['paid_pending'] ?></div>
        <div style="font-size:10px;color:#b45309">Challan Stage</div>
      </div></a>
      <a href="<?= url('etds_register.php?stage=preparation') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#e8f4fc;border-radius:6px;border:1px solid #bae6fd">
        <div style="font-size:20px;font-weight:700;color:#1d6fa5"><?= $summary['prep_pending']+$summary['filing_pending'] ?></div>
        <div style="font-size:10px;color:#1d6fa5">Prep/Filing Pending</div>
      </div></a>
      <a href="<?= url('etds_register.php?stage=form16a') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#f1ecfb;border-radius:6px;border:1px solid #ddd0f5">
        <div style="font-size:20px;font-weight:700;color:#6a4fb0"><?= $summary['form16a_pending'] ?></div>
        <div style="font-size:10px;color:#6a4fb0">Form 16A Pending</div>
      </div></a>
    </div>
    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;text-align:center">
      <div style="padding:10px 6px;background:#f0fdf4;border-radius:6px;border:1px solid #bbf7d0">
        <div style="font-size:20px;font-weight:700;color:#166534"><?= $summary['filed'] ?></div>
        <div style="font-size:10px;color:#166534">Returns Filed ✓</div>
      </div>
      <div style="padding:10px 6px;background:#f0fdf4;border-radius:6px;border:1px solid #bbf7d0">
        <div style="font-size:20px;font-weight:700;color:#166534"><?= $summary['closed'] ?></div>
        <div style="font-size:10px;color:#166534">Fully Closed (16A Done) ✓</div>
      </div>
    </div>
  </div>
</div>
<?php endif; ?>

<div class="filters-bar">
  <form method="get" style="display:contents">
    <input type="hidden" name="stage" value="list">
    <div class="filter-group"><label>Client Name</label>
      <input type="text" name="client_name" value="<?= htmlspecialchars($filter_name) ?>" placeholder="Search..." style="width:150px"></div>
    <div class="filter-group"><label>FY</label>
      <select name="fy"><?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $filter_fy===$fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?></select></div>
    <div class="filter-group"><label>Quarter</label>
      <select name="quarter"><option value="">All</option>
        <?php foreach (['Q1','Q2','Q3','Q4'] as $q): ?><option value="<?= $q ?>" <?= $filter_qtr===$q?'selected':'' ?>><?= $q ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Form Type</label>
      <select name="form_type"><option value="">All</option>
        <?php foreach (['24Q','26Q','27Q','27EQ'] as $ft): ?><option value="<?= $ft ?>" <?= $filter_form===$ft?'selected':'' ?>><?= $ft ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('etds_register.php') ?>" class="btn btn-outline">Reset</a>
      <button class="btn btn-export" type="button" onclick="exportTableToXLS('etds-table','ETDS_Register_<?= $filter_fy ?>')">⬇ Export XLS</button>
    </div>
  </form>
</div>

<div class="card"><div class="table-responsive">
<table class="data-table" id="etds-table">
  <thead>
    <tr>
      <th>#</th><th>Client</th><th>TAN</th><th>FY/Qtr</th><th>Form</th>
      <th>Trigger Date</th><th>Target Date</th><th>Statutory Due</th>
      <th>TDS Deducted</th><th>TDS Deposited</th><th>Prepared By</th>
      <th>Filed Date</th><th>PRN</th><th>Form 16A Due</th><th>Form 16A Status</th>
      <th>Status</th><th class="no-export">Actions</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($entries as $i => $r): $days = daysUntil($r['due_date_return']); ?>
    <tr class="<?= !in_array($r['status'],['Filed','Form 16A Downloaded'])&&$days!==null&&$days<0?'row-overdue':(!in_array($r['status'],['Filed','Form 16A Downloaded'])&&$days!==null&&$days<=7?'row-due-soon':'') ?>">
      <td><?= $pg['offset']+$i+1 ?></td>
      <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:10px"><?= $r['pan'] ?></span></td>
      <td style="font-size:10px"><code><?= htmlspecialchars($r['tan']) ?></code></td>
      <td><?= htmlspecialchars($r['financial_year']) ?> / <span class="badge badge-primary"><?= $r['quarter'] ?></span></td>
      <td><span class="badge badge-info"><?= $r['form_type'] ?></span></td>
      <td style="font-size:11px"><?= triggerStatusBadge($r['trigger_date'] ?? null) ?></td>
      <td style="font-size:11px"><?= targetDateBadge($r['target_date'] ?? null) ?></td>
      <td>
        <?= dueDateBadge($r['due_date_return']) ?>
        <?php if (!empty($r['due_date_overridden'])): ?><span class="badge badge-warning" style="font-size:9px">EXT</span><?php endif; ?>
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
          <button type="button" class="btn-icon" style="font-size:10px;padding:1px 4px"
                  onclick="openOverrideModal(<?= $r['id'] ?>,'<?= htmlspecialchars($r['due_date_return']) ?>','<?= htmlspecialchars(addslashes($r['client_name'])) ?>')"
                  title="Override due date">✏</button>
        <?php endif; ?>
      </td>
      <td class="text-right">₹<?= number_format($r['total_tds_deducted'],0) ?></td>
      <td class="text-right">₹<?= number_format($r['total_tds_deposited'],0) ?></td>
      <td style="font-size:12px"><?= htmlspecialchars($r['prep_name']??'—') ?></td>
      <td style="font-size:11px"><?= $r['return_filed_date']?'<span class="badge badge-success">'.fmtDate($r['return_filed_date']).'</span>':'—' ?></td>
      <td style="font-size:10px"><code><?= htmlspecialchars($r['prn']?:'—') ?></code></td>
      <td style="font-size:11px"><?= $r['form16a_due_date']?dueDateBadge($r['form16a_due_date']):'—' ?></td>
      <td><?php
        $f16_badges = ['Pending'=>'badge-secondary','Downloaded'=>'badge-success','Not Applicable'=>'badge-secondary'];
        echo '<span class="badge '.($f16_badges[$r['form16a_status']]??'badge-secondary').'">'.htmlspecialchars($r['form16a_status']).'</span>';
      ?></td>
      <td>
        <select class="status-select" data-id="<?= $r['id'] ?>" data-module="etds_returns" style="font-size:11px;height:24px;padding:0 4px;border:1px solid var(--border);border-radius:4px;min-width:130px">
          <?php foreach (['Pending Data','Data Received','Working Done','Challan Sent','No Challan Due','Challan Paid','Return Prepared','Filed','Form 16A Downloaded','On Hold','Not Applicable'] as $s): ?>
            <option value="<?= $s ?>" <?= $r['status']===$s?'selected':'' ?>><?= $s ?></option>
          <?php endforeach; ?>
        </select>
      </td>
      <td class="no-export" style="white-space:nowrap">
        <a href="<?= url('etds_register.php?action=edit&id=').$r['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
        <a href="<?= url('etds_register.php?action=delete&id=').$r['id'] ?>" class="btn btn-danger btn-sm" onclick="return confirm('Delete this entry?')">Delete</a>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($entries)): ?>
    <tr><td colspan="17" class="text-center text-muted" style="padding:2rem">No entries found. Go to ① Data Receipt to add the first entry.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div></div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i=1; $i<=$pg['total_pages']; $i++): ?>
    <a href="?stage=list&fy=<?= urlencode($filter_fy) ?>&quarter=<?= urlencode($filter_qtr) ?>&page=<?= $i ?>" class="page-link <?= $i===$page?'active':'' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($entries) ?> of <?= $total ?></span>
</div>
<?php endif; ?>
<?php endif; // end stage/action blocks ?>

<script>
function fillTAN(sel) {
  const opt = sel.options[sel.selectedIndex];
  document.getElementById('tan_field').value = (opt.dataset.tan || '').toUpperCase();
}
function openWorkingModal(r) {
  document.getElementById('wm_etds_id').value = r.id;
  document.getElementById('wm_info').innerHTML = '<strong>'+r.client_name+'</strong> | '+r.financial_year+' '+r.quarter+' | Due: '+(r.due_date_return||'—');
  openModal('working-modal');
}
function openChallanSentModal(r) {
  document.getElementById('csm_etds_id').value = r.id;
  document.getElementById('csm_info').innerHTML = '<strong>'+r.client_name+'</strong> | TDS Deducted: ₹'+(parseFloat(r.total_tds_deducted)||0).toLocaleString('en-IN');
  openModal('challan-sent-modal');
}
function openPaidModal(r) {
  document.getElementById('pdm_etds_id').value = r.id;
  document.getElementById('pdm_info').innerHTML = '<strong>'+r.client_name+'</strong> | TDS Deducted: ₹'+(parseFloat(r.total_tds_deducted)||0).toLocaleString('en-IN');
  openModal('paid-modal');
}
function openPrepModal(r) {
  document.getElementById('prm_etds_id').value = r.id;
  document.getElementById('prm_info').innerHTML = '<strong>'+r.client_name+'</strong> | '+r.financial_year+' '+r.quarter;
  openModal('prep-modal');
}
function openFilingModal(r) {
  document.getElementById('fm_etds_id').value = r.id;
  document.getElementById('fm_info').innerHTML = '<strong>'+r.client_name+'</strong> | '+r.financial_year+' '+r.quarter+' | Form 16A will be due 15 days after statutory due date';
  openModal('filing-modal');
}
function openForm16aModal(r) {
  document.getElementById('f16_etds_id').value = r.id;
  document.getElementById('f16_info').innerHTML = '<strong>'+r.client_name+'</strong> | PRN: '+(r.prn||'—')+' | Due: '+(r.form16a_due_date||'—');
  openModal('form16a-modal');
}
function openOverrideModal(id, currentDue, clientName) {
  document.getElementById('ov_etds_id').value = id;
  document.getElementById('ov_info').innerHTML = '<strong>'+clientName+'</strong> | Current statutory due date: '+(currentDue||'—');
  document.getElementById('ov_new_date').value = currentDue || '';
  openModal('override-modal');
}
</script>

<!-- Statutory Due Date Override Modal -->
<div class="modal-overlay" id="override-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header"><span class="modal-title">✏ Override Statutory Due Date</span><button class="modal-close" onclick="closeModal('override-modal')">×</button></div>
    <form method="post" action="<?= url('etds_register.php?stage=list') ?>">
      <input type="hidden" name="post_action" value="override_due_date">
      <input type="hidden" name="etds_id" id="ov_etds_id">
      <div class="modal-body">
        <div style="background:#fff8f0;padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px;border:1px solid #fed7aa" id="ov_info"></div>
        <p class="text-muted" style="font-size:12px;margin-bottom:10px">
          Use this only when CBDT extends the due date. Form 16A due date is automatically recalculated (+15 days from new date).
        </p>
        <div class="form-group mb-2">
          <label>New Statutory Due Date <span class="req">*</span></label>
          <input class="form-control" type="date" name="new_due_date" id="ov_new_date" required>
        </div>
        <div class="form-group">
          <label>Reason / Notification Reference</label>
          <input class="form-control" name="override_reason" placeholder="e.g. CBDT Circular No...">
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save Extended Due Date</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('override-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php include 'includes/footer.php'; ?>
