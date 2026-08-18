<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
$db = getDB();

// ── SCHEMA CHECK — friendly error instead of blank HTTP 500 ──
try {
    $db->query("SELECT 1 FROM itr_returns LIMIT 1");
    $db->query("SELECT 1 FROM client_groups LIMIT 1");
} catch (Exception $e) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $_SESSION['flash_msg'] = '⚠ Database setup required. Run upgrade_itr.sql in phpMyAdmin first.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('itr_register.php')); exit;
    }
    include 'includes/header.php';
    echo '<div class="card" style="max-width:700px;margin:2rem auto"><div class="card-body">
        <h2 style="color:var(--danger)">⚠ Database Setup Required</h2>
        <p style="margin:1rem 0">The IT Return Register needs two database tables that have not been created yet:
        <code>itr_returns</code> and <code>client_groups</code>.</p>
        <p style="margin-bottom:1rem"><strong>Fix:</strong> Open phpMyAdmin → select the <code>ca_intranet</code> database →
        click the <strong>SQL</strong> tab → paste the contents of <code>upgrade_itr.sql</code> (found in your project folder) → click Go.</p>
        <p style="font-size:12px;color:var(--text-muted)">Technical detail: '.htmlspecialchars($e->getMessage()).'</p>
        <a href="'.url('dashboard.php').'" class="btn btn-primary" style="margin-top:1rem">← Back to Dashboard</a>
    </div></div>';
    include 'includes/footer.php';
    exit;
}

$page_title = 'IT Return Register';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);
$stage  = $_GET['stage'] ?? 'list';
$dp     = defaultPeriod('itr');

// ── DELETE ────────────────────────────────────────────────
if ($action === 'delete' && $id && hasRole(['admin','partner','supervisor'])) {
    $db->prepare("DELETE FROM itr_returns WHERE id=?")->execute([$id]);
    auditLog('itr_returns', $id, 'DELETE');
    $_SESSION['flash_msg'] = 'Entry deleted.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('itr_register.php')); exit;
}

// ── BULK UPDATE ───────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST'
    && ($_POST['post_action'] ?? '') === 'bulk_update'
    && hasRole(['admin','partner','supervisor'])) {
    $d   = $_POST;
    $ids = array_filter(array_map('intval', $d['bulk_ids'] ?? []));
    if (!empty($ids)) {
        $sets = []; $params = [];
        if (!empty($d['bulk_accounting_done_by']))  { $sets[] = 'accounting_done_by=?';  $params[] = intval($d['bulk_accounting_done_by']); }
        if (!empty($d['bulk_itr_prepared_by']))     { $sets[] = 'itr_prepared_by=?';     $params[] = intval($d['bulk_itr_prepared_by']); }
        if (!empty($d['bulk_itr_verified_by']))     { $sets[] = 'itr_verified_by=?';     $params[] = intval($d['bulk_itr_verified_by']); }
        if (!empty($d['bulk_ca_partner_id']))        { $sets[] = 'ca_partner_id=?';        $params[] = intval($d['bulk_ca_partner_id']); }
        if (!empty($d['bulk_accounting_status']))    { $sets[] = 'accounting_status=?';    $params[] = $d['bulk_accounting_status']; }
        if (!empty($d['bulk_itr_prepared_status'])) { $sets[] = 'itr_prepared_status=?'; $params[] = $d['bulk_itr_prepared_status']; }
        if (!empty($d['bulk_e_verified']))          { $sets[] = 'e_verified=?';           $params[] = $d['bulk_e_verified']; }
        if (!empty($d['bulk_refund_status']))       { $sets[] = 'refund_status=?';        $params[] = $d['bulk_refund_status']; }
        if (!empty($sets)) {
            $ph  = implode(',', array_fill(0, count($ids), '?'));
            $db->prepare("UPDATE itr_returns SET ".implode(', ',$sets)." WHERE id IN ($ph)")
               ->execute(array_merge($params, $ids));
            foreach ($ids as $bid) auditLog('itr_returns', $bid, 'UPDATE', null, ['bulk'=>true]);
            $_SESSION['flash_msg'] = 'Bulk update applied to '.count($ids).' entries.';
            $_SESSION['flash_type'] = 'success';
        }
    }
    $go_stage = $_GET['stage'] ?? 'list';
    $go_fy    = urlencode($d['current_fy'] ?? '');
    header('Location: '.url("itr_register.php?stage=$go_stage&fy=$go_fy")); exit;
}

// ── REFUND STATUS UPDATE ──────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST'
    && ($_POST['post_action'] ?? '') === 'update_refund') {
    $d = $_POST;
    $db->prepare(
        "UPDATE itr_returns SET
            refund_status=?, refund_received_date=?,
            refund_received_amount=?, refund_intimation_no=?, remarks=?
         WHERE id=?"
    )->execute([
        $d['refund_status'],
        $d['refund_received_date'] ?: null,
        $d['refund_received_amount'] !== '' ? floatval($d['refund_received_amount']) : null,
        trim($d['refund_intimation_no'] ?? ''),
        trim($d['remarks'] ?? ''),
        intval($d['itr_id']),
    ]);
    auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
    $_SESSION['flash_msg'] = 'Refund status updated.'; $_SESSION['flash_type'] = 'success';
    $go_fy = urlencode($d['current_fy'] ?? '');
    header('Location: '.url("itr_register.php?stage=refunds&fy=$go_fy")); exit;
}

// ── SAVE / STAGE UPDATES ─────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $d = $_POST;
    $pa = $d['post_action'] ?? '';

    // STAGE 1: Data Receipt — create new entry
    if ($pa === 'add_entry') {
        $db->prepare(
            "INSERT INTO itr_returns
                (client_id,financial_year,ca_partner_id,group_id,return_category,
                 data_received_on,accounting_status,itr_prepared_status,itr_uploaded_status,
                 e_verified,bank_validated,created_by)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
        )->execute([
            intval($d['client_id']), $d['financial_year'], $d['ca_partner_id'] ?: null, $d['group_id'] ?: null,
            $d['return_category'] ?? 'ITR', $d['data_received_on'] ?: date('Y-m-d'),
            'WIP', 'No', 'WIP', 'Pending', 'No', $_SESSION['user_id'],
        ]);
        auditLog('itr_returns', $db->lastInsertId(), 'CREATE');
        $_SESSION['flash_msg'] = 'Data receipt entry added.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=data')); exit;
    }

    // FULL EDIT (admin/partner/supervisor override — edits every field at once)
    if ($pa === 'edit_entry') {
        $gti    = (($d['gti'] ?? '') !== '') ? floatval($d['gti']) : null;
        $sa_tax = (($d['sa_tax'] ?? '') !== '') ? abs(floatval($d['sa_tax'])) : null;
        $refund = (($d['refund'] ?? '') !== '') ? abs(floatval($d['refund'])) : null;
        $itr_ack = trim($d['itr_ack'] ?? '');
        $filed_date = $itr_ack ? deriveFiledDateFromAck($itr_ack) : null;
        if (!$filed_date && !empty($d['filed_date_manual'])) $filed_date = $d['filed_date_manual'];

        $db->prepare(
            "UPDATE itr_returns SET
                client_id=?,financial_year=?,ca_partner_id=?,group_id=?,return_category=?,
                data_received_on=?,accounting_done_by=?,accounting_started_on=?,accounting_na=?,accounting_status=?,
                itr_prepared_by=?,itr_prepared_status=?,itr_verified_by=?,itr_uploaded_status=?,
                itr_ack=?,filed_date=?,e_verified=?,itr_form_no=?,gti=?,sa_tax=?,refund=?,bank_validated=?,remarks=?
             WHERE id=?"
        )->execute([
            intval($d['client_id']), $d['financial_year'], $d['ca_partner_id'] ?: null, $d['group_id'] ?: null,
            $d['return_category'] ?? 'ITR',
            $d['data_received_on'] ?: null, $d['accounting_done_by'] ?: null,
            isset($d['accounting_na']) ? null : ($d['accounting_started_on'] ?: null),
            isset($d['accounting_na']) ? 1 : 0,
            isset($d['accounting_na']) ? 'NA' : ($d['accounting_status'] ?? 'WIP'),
            $d['itr_prepared_by'] ?: null, $d['itr_prepared_status'] ?? 'No',
            $d['itr_verified_by'] ?: null, $d['itr_uploaded_status'] ?? 'WIP',
            $itr_ack ?: null, $filed_date, $d['e_verified'] ?? 'Pending',
            trim($d['itr_form_no'] ?? ''), $gti, $sa_tax, $refund,
            $d['bank_validated'] ?? 'No', trim($d['remarks'] ?? '') ?: null,
            intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Entry updated successfully.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=list')); exit;
    }

    // STAGE 2: Accounting
    if ($pa === 'update_accounting') {
        $is_na = isset($d['accounting_na']);
        $db->prepare(
            "UPDATE itr_returns SET
                accounting_done_by=?, accounting_started_on=?, accounting_na=?, accounting_status=?, remarks=?
             WHERE id=?"
        )->execute([
            $d['accounting_done_by'] ?: null,
            $is_na ? null : ($d['accounting_started_on'] ?: null),
            $is_na ? 1 : 0,
            $is_na ? 'NA' : ($d['accounting_status'] ?? 'WIP'),
            trim($d['remarks'] ?? '') ?: null,
            intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Accounting details saved.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=accounting')); exit;
    }

    // STAGE 3: ITR Preparation
    if ($pa === 'update_preparation') {
        $gti    = (($d['gti'] ?? '') !== '') ? floatval($d['gti']) : null;
        $sa_tax = (($d['sa_tax'] ?? '') !== '') ? abs(floatval($d['sa_tax'])) : null;
        $db->prepare(
            "UPDATE itr_returns SET
                itr_prepared_by=?, itr_prepared_status=?, itr_form_no=?, gti=?, sa_tax=?, remarks=?
             WHERE id=?"
        )->execute([
            $d['itr_prepared_by'] ?: null, $d['itr_prepared_status'] ?? 'No',
            trim($d['itr_form_no'] ?? ''), $gti, $sa_tax,
            trim($d['remarks'] ?? '') ?: null, intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'ITR preparation details saved.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=preparation')); exit;
    }

    // STAGE 4: Verification
    if ($pa === 'update_verification') {
        $db->prepare(
            "UPDATE itr_returns SET itr_verified_by=?, bank_validated=?, remarks=? WHERE id=?"
        )->execute([
            $d['itr_verified_by'] ?: null, $d['bank_validated'] ?? 'No',
            trim($d['remarks'] ?? '') ?: null, intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Verification details saved.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=verification')); exit;
    }

    // STAGE 5: Filing
    if ($pa === 'update_filing') {
        $itr_ack = trim($d['itr_ack'] ?? '');
        $filed_date = $itr_ack ? deriveFiledDateFromAck($itr_ack) : null;
        if (!$filed_date && !empty($d['filed_date_manual'])) $filed_date = $d['filed_date_manual'];
        $refund = (($d['refund'] ?? '') !== '') ? abs(floatval($d['refund'])) : null;

        $db->prepare(
            "UPDATE itr_returns SET
                itr_uploaded_status=?, itr_ack=?, filed_date=?, refund=?, remarks=?
             WHERE id=?"
        )->execute([
            $d['itr_uploaded_status'] ?? 'WIP', $itr_ack ?: null, $filed_date, $refund,
            trim($d['remarks'] ?? '') ?: null, intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Filing details saved.' . ($filed_date ? ' Filed date auto-detected: '.fmtDate($filed_date) : '');
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=filing')); exit;
    }

    // STAGE 6: E-Verification — closes the record
    if ($pa === 'update_everify') {
        $db->prepare(
            "UPDATE itr_returns SET e_verified=?, remarks=? WHERE id=?"
        )->execute([
            $d['e_verified'] ?? 'Pending', trim($d['remarks'] ?? '') ?: null, intval($d['itr_id']),
        ]);
        auditLog('itr_returns', intval($d['itr_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'E-Verification status updated.'; $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=everify')); exit;
    }

    // BULK CREATE
    if ($pa === 'bulk_create') {
        $fy = $d['bulk_create_fy'] ?: $d['financial_year'];

        $selected_ids = array_filter(array_map('intval', $d['client_ids'] ?? []));
        if (!empty($selected_ids)) {
            $placeholders = implode(',', array_fill(0, count($selected_ids), '?'));
            $stmt = $db->prepare("SELECT id, partner_id, group_id FROM clients WHERE itr_applicable=1 AND status='Active' AND id IN ($placeholders)");
            $stmt->execute($selected_ids);
        } else {
            $stmt = $db->query("SELECT id, partner_id, group_id FROM clients WHERE itr_applicable=1 AND status='Active'");
        }
        $clients = $stmt->fetchAll();

        $created = 0;
        foreach ($clients as $c) {
            $chk = $db->prepare("SELECT id FROM itr_returns WHERE client_id=? AND financial_year=?");
            $chk->execute([$c['id'], $fy]); if ($chk->fetch()) continue;
            $db->prepare(
                "INSERT INTO itr_returns (client_id,financial_year,ca_partner_id,group_id,accounting_status,itr_prepared_status,itr_uploaded_status,e_verified,bank_validated,created_by)
                 VALUES (?,?,?,?,?,?,?,?,?,?)"
            )->execute([$c['id'], $fy, $c['partner_id'], $c['group_id'], 'WIP', 'No', 'WIP', 'Pending', 'No', $_SESSION['user_id']]);
            $created++;
        }
        $_SESSION['flash_msg'] = "Bulk create done: $created entries created for FY $fy.";
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('itr_register.php?stage=list')); exit;
    }
}

// ── FETCH SINGLE ENTRY (for edit form) ────────────────────
$entry = [];
if ($id) {
    $stmt = $db->prepare("SELECT i.*, c.client_name, c.pan FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE i.id=?");
    $stmt->execute([$id]); $entry = $stmt->fetch() ?: [];
}

// ── LIST FILTERS ───────────────────────────────────────────
$filter_fy       = array_key_exists('fy', $_GET) ? trim($_GET['fy']) : $dp['fy'];
$filter_category = $_GET['category']     ?? '';
$filter_partner  = intval($_GET['ca_partner_id']  ?? 0);
$filter_group    = intval($_GET['group_id']       ?? 0);
$filter_sup      = intval($_GET['supervisor_id']  ?? 0);
$filter_name     = trim($_GET['client_name'] ?? '');
$page = max(1, intval($_GET['page'] ?? 1)); $per = 30;

$where = ['1=1']; $wp = [];
if ($filter_fy)       { $where[] = 'i.financial_year=?'; $wp[] = $filter_fy; }
if ($filter_category) { $where[] = 'i.return_category=?'; $wp[] = $filter_category; }
if ($filter_partner)  { $where[] = 'i.ca_partner_id=?'; $wp[] = $filter_partner; }
if ($filter_group)    { $where[] = 'i.group_id=?'; $wp[] = $filter_group; }
if ($filter_sup)      { $where[] = 'c.supervisor_id=?'; $wp[] = $filter_sup; }
if ($filter_name)     { $where[] = 'c.client_name LIKE ?'; $wp[] = "%$filter_name%"; }

if ($_SESSION['role'] === 'supervisor') {
    $where[] = '(c.supervisor_id=? OR i.accounting_done_by=? OR i.itr_prepared_by=? OR i.itr_verified_by=?)';
    $wp = array_merge($wp, [$_SESSION['user_id'],$_SESSION['user_id'],$_SESSION['user_id'],$_SESSION['user_id']]);
}
if ($_SESSION['role'] === 'staff') {
    $where[] = '(i.accounting_done_by=? OR i.itr_prepared_by=? OR i.itr_verified_by=?)';
    $wp = array_merge($wp, [$_SESSION['user_id'],$_SESSION['user_id'],$_SESSION['user_id']]);
}
$ws = implode(' AND ', $where);

$total = $db->prepare("SELECT COUNT(*) FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE $ws");
$total->execute($wp); $total = $total->fetchColumn();
$pg = paginate($total, $per, $page);

$rows = $db->prepare(
    "SELECT i.*, c.client_name, c.pan, c.supervisor_id,
            ca.name ca_name, sup.name sup_name,
            ad.name acc_done_name, ip.name itr_prep_name, iv.name itr_verify_name,
            g.group_name
     FROM itr_returns i
     JOIN clients c ON c.id=i.client_id
     LEFT JOIN users ca  ON ca.id=i.ca_partner_id
     LEFT JOIN users sup ON sup.id=c.supervisor_id
     LEFT JOIN users ad  ON ad.id=i.accounting_done_by
     LEFT JOIN users ip  ON ip.id=i.itr_prepared_by
     LEFT JOIN users iv  ON iv.id=i.itr_verified_by
     LEFT JOIN client_groups g ON g.id=i.group_id
     WHERE $ws ORDER BY c.client_name ASC LIMIT ? OFFSET ?"
);
$rows->execute(array_merge($wp, [$per, $pg['offset']]));
$entries = $rows->fetchAll();

// ── STAGE QUEUES ───────────────────────────────────────────
// Stage 2: Accounting — entries with data received, accounting not yet Done/NA
$q_accounting = $db->query(
    "SELECT i.*, c.client_name, c.pan FROM itr_returns i JOIN clients c ON c.id=i.client_id
     WHERE i.data_received_on IS NOT NULL AND i.accounting_status NOT IN('Done','NA')
     ORDER BY i.data_received_on ASC, c.client_name"
)->fetchAll();

// Stage 3: ITR Preparation — accounting Done or NA, ITR not yet prepared
$q_preparation = $db->query(
    "SELECT i.*, c.client_name, c.pan FROM itr_returns i JOIN clients c ON c.id=i.client_id
     WHERE i.accounting_status IN('Done','NA') AND i.itr_prepared_status != 'Yes'
     ORDER BY c.client_name"
)->fetchAll();

// Stage 4: Verification — ITR prepared = Yes, not yet verified
$q_verification = $db->query(
    "SELECT i.*, c.client_name, c.pan, ip.name itr_prep_name FROM itr_returns i
     JOIN clients c ON c.id=i.client_id LEFT JOIN users ip ON ip.id=i.itr_prepared_by
     WHERE i.itr_prepared_status='Yes' AND i.itr_verified_by IS NULL
     ORDER BY c.client_name"
)->fetchAll();

// Stage 5: Filing — verified, not yet uploaded/filed
$q_filing = $db->query(
    "SELECT i.*, c.client_name, c.pan, iv.name itr_verify_name FROM itr_returns i
     JOIN clients c ON c.id=i.client_id LEFT JOIN users iv ON iv.id=i.itr_verified_by
     WHERE i.itr_verified_by IS NOT NULL AND i.itr_uploaded_status != 'Yes'
     ORDER BY c.client_name"
)->fetchAll();

// Stage 6: E-Verify — uploaded=Yes, e_verified not yet Yes
$q_everify = $db->query(
    "SELECT i.*, c.client_name, c.pan FROM itr_returns i JOIN clients c ON c.id=i.client_id
     WHERE i.itr_uploaded_status='Yes' AND i.e_verified != 'Yes'
     ORDER BY c.client_name"
)->fetchAll();

// Refund tracking — entries with refund > 0 for the current FY
$refund_fy    = $filter_fy ?: currentFY();
$q_ref_stmt   = $db->prepare(
    "SELECT i.*, c.client_name, c.pan,
            ca.name ca_name, sup.name sup_name
     FROM itr_returns i
     JOIN clients c ON c.id=i.client_id
     LEFT JOIN users ca  ON ca.id=i.ca_partner_id
     LEFT JOIN users sup ON sup.id=c.supervisor_id
     WHERE i.financial_year=? AND i.refund IS NOT NULL AND i.refund > 0
     ORDER BY FIELD(i.refund_status,'Pending','Partially Received','Received','Adjusted','Not Applicable'),
              i.refund DESC, c.client_name"
);
$q_ref_stmt->execute([$refund_fy]);
$q_refunds = $q_ref_stmt->fetchAll();

// ── EXECUTIVE SUMMARY ──────────────────────────────────────
$summary = null;
if ($filter_fy) {
    $sw = ['i.financial_year=?']; $sp = [$filter_fy];
    if ($filter_category) { $sw[] = 'i.return_category=?'; $sp[] = $filter_category; }
    if ($filter_partner)  { $sw[] = 'i.ca_partner_id=?'; $sp[] = $filter_partner; }
    if ($filter_group)    { $sw[] = 'i.group_id=?'; $sp[] = $filter_group; }
    $sws = implode(' AND ', $sw);
    $stmt = $db->prepare("SELECT i.* FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE $sws");
    $stmt->execute($sp);
    $s_rows = $stmt->fetchAll();

    $total_count = count($s_rows);
    $data_pending = 0; $acc_pending = 0; $prep_pending = 0; $verify_pending = 0; $filing_pending = 0; $everify_pending = 0; $filed = 0;
    foreach ($s_rows as $r) {
        if (!$r['data_received_on']) $data_pending++;
        if ($r['data_received_on'] && !in_array($r['accounting_status'], ['Done','NA'])) $acc_pending++;
        if (in_array($r['accounting_status'], ['Done','NA']) && $r['itr_prepared_status'] !== 'Yes') $prep_pending++;
        if ($r['itr_prepared_status'] === 'Yes' && !$r['itr_verified_by']) $verify_pending++;
        if ($r['itr_verified_by'] && $r['itr_uploaded_status'] !== 'Yes') $filing_pending++;
        if ($r['itr_uploaded_status'] === 'Yes' && $r['e_verified'] !== 'Yes') $everify_pending++;
        if ($r['itr_uploaded_status'] === 'Yes') $filed++;
    }
    $summary = compact('total_count','data_pending','acc_pending','prep_pending','verify_pending','filing_pending','everify_pending','filed');
}

$all_clients = $db->query("SELECT id, client_name, pan, partner_id, group_id FROM clients WHERE itr_applicable=1 AND status='Active' ORDER BY client_name")->fetchAll();
$client_groups = $db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$partners    = $db->query("SELECT id, name FROM users WHERE role IN('partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
$all_users   = $db->query("SELECT id, name FROM users WHERE is_active=1 ORDER BY name")->fetchAll();
$groups      = $db->query("SELECT id, group_name FROM client_groups ORDER BY group_name")->fetchAll();
$fy_list     = getFYList();

// ── STAGE FILTER HELPER ───────────────────────────────────
// Must be defined before header include (PHP cannot declare functions inside
// if/elseif/else control structures — so it lives here in pure-PHP section)
function stageFilterBar($stage_name, $rows, $all_users, $partners, $filter_fy) {
    $sf_user    = intval($_GET['sf_user']    ?? 0);
    $sf_partner = intval($_GET['sf_partner'] ?? 0);
    // Filter rows by user (any of accounting_done_by / itr_prepared_by / itr_verified_by)
    if ($sf_user || $sf_partner) {
        $rows = array_filter($rows, function($r) use ($sf_user, $sf_partner) {
            if ($sf_user) {
                $match = ($r['accounting_done_by'] ?? 0) == $sf_user
                      || ($r['itr_prepared_by']    ?? 0) == $sf_user
                      || ($r['itr_verified_by']    ?? 0) == $sf_user;
                if (!$match) return false;
            }
            if ($sf_partner && ($r['ca_partner_id'] ?? 0) != $sf_partner) return false;
            return true;
        });
    }
    $fyq  = '&fy=' . urlencode($filter_fy);
    $base = '?stage=' . $stage_name . $fyq;
    echo '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:6px 0 10px">';
    echo '<form method="get" style="display:contents">';
    echo '<input type="hidden" name="stage" value="' . $stage_name . '">';
    echo '<input type="hidden" name="fy" value="' . htmlspecialchars($filter_fy) . '">';
    echo '<label style="font-size:11px;color:var(--text-muted)">Filter:</label>';
    echo '<select name="sf_partner" class="form-control" style="width:auto;height:30px;font-size:12px" onchange="this.form.submit()">';
    echo '<option value="">All Partners</option>';
    foreach ($partners as $p)
        echo '<option value="' . $p['id'] . '" ' . ($sf_partner == $p['id'] ? 'selected' : '') . '>'
           . htmlspecialchars($p['name']) . '</option>';
    echo '</select>';
    echo '<select name="sf_user" class="form-control" style="width:auto;height:30px;font-size:12px" onchange="this.form.submit()">';
    echo '<option value="">All Staff</option>';
    foreach ($all_users as $u)
        echo '<option value="' . $u['id'] . '" ' . ($sf_user == $u['id'] ? 'selected' : '') . '>'
           . htmlspecialchars($u['name']) . '</option>';
    echo '</select>';
    if ($sf_user || $sf_partner)
        echo '<a href="' . $base . '" class="btn btn-outline btn-sm">Reset</a>';
    echo '<button type="button" class="btn btn-sm" style="background:var(--primary);color:#fff" '
       . 'onclick="selectAllStageCBs()">☑ Select All</button>';
    echo '<button type="button" class="btn btn-outline btn-sm" onclick="clearITRBulk()">Clear</button>';
    echo '</form>';
    echo '</div>';
    return array_values($rows);
}

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">🧾 IT Return Register</div>
    <div class="page-subtitle">FY: <?= htmlspecialchars($filter_fy) ?> &nbsp;|&nbsp; Total entries: <?= $total ?></div>
  </div>
  <div class="d-flex gap-1" style="align-items:center">
    <!-- Real FY filter — drives the page list AND executive summary -->
    <form method="get" style="display:inline-flex;gap:6px;align-items:center">
      <input type="hidden" name="stage" value="<?= htmlspecialchars($stage) ?>">
      <label style="font-size:12px;color:var(--text-muted);white-space:nowrap">Viewing FY:</label>
      <select name="fy" class="form-control" style="width:auto;height:34px" onchange="this.form.submit()">
        <?php foreach ($fy_list as $fy): ?>
          <option value="<?= $fy ?>" <?= $fy===$filter_fy?'selected':'' ?>><?= $fy ?></option>
        <?php endforeach; ?>
      </select>
    </form>
    <?php if (hasRole(['admin','partner','supervisor'])): ?>
    <a href="<?= url('itr_register.php?action=bulk_create') ?>" class="btn btn-outline">⚡ Bulk Create</a>
    <?php endif; ?>
  </div>
</div>

<!-- STAGE TAB NAV -->
<div style="display:flex;gap:0;margin-bottom:1.25rem;border-radius:8px;overflow:hidden;border:1px solid var(--border);flex-wrap:wrap">
<?php
$fyq = $filter_fy ? '&fy='.urlencode($filter_fy) : '&fy=';
$stages = [
  'list'        => ['⊞ All Entries',      count($entries).' shown'],
  'data'        => ['① Data Receipt',      'Add new'],
  'accounting'  => ['② Accounting',        count($q_accounting).' pending'],
  'preparation' => ['③ ITR Prep',          count($q_preparation).' pending'],
  'verification'=> ['④ Verification',      count($q_verification).' pending'],
  'filing'      => ['⑤ Filing',            count($q_filing).' ready'],
  'everify'     => ['⑥ E-Verify',          count($q_everify).' pending'],
  'refunds'     => ['💰 Refunds',           count($q_refunds).' tracked'],
];
foreach ($stages as $s => [$label,$count]):
    $active = ($stage === $s);
?>
<a href="<?= url("itr_register.php?stage=$s$fyq") ?>"
   style="flex:1;min-width:95px;padding:9px 4px;text-align:center;font-size:11px;font-weight:<?= $active?'600':'400' ?>;
          background:<?= $active?'var(--primary)':'var(--bg-card)' ?>;
          color:<?= $active?'#fff':'var(--text)' ?>;text-decoration:none;border-right:1px solid var(--border)">
  <?= $label ?><br><span style="font-size:10px;opacity:.75"><?= $count ?></span>
</a>
<?php endforeach; ?>
</div>

<?php if ($action === 'bulk_create'): ?>
<!-- ══ BULK CREATE ══ -->
<div class="card" style="max-width:720px">
  <div class="card-header"><span class="card-title">⚡ Bulk Create IT Return Entries</span></div>
  <div class="card-body">
  <form method="post" action="<?= url('itr_register.php?stage=list') ?>" onsubmit="return confirm('Create IT Return entries for the selected clients?')">
    <input type="hidden" name="post_action" value="bulk_create">
    <div class="form-group mb-2" style="max-width:240px"><label>Financial Year <span class="req">*</span></label>
      <select class="form-control" name="financial_year" required>
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$filter_fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select></div>

    <div class="form-section mt-2">
      <div class="form-section-title">
        Select Clients <small style="font-size:11px;font-weight:400;color:var(--text-muted)">— leave none selected to apply to ALL ITR-applicable clients</small>
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
      <a href="<?= url('itr_register.php') ?>" class="btn btn-outline">Cancel</a>
    </div>
  </form>
  </div>
</div>

<?php elseif ($stage === 'data'): ?>
<!-- ══ STAGE 1: DATA RECEIPT ══ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">① Add Data Receipt Entry</span>
    <span class="text-muted" style="font-size:12px">First step — record when client data is received</span>
  </div>
  <div class="card-body">
  <form method="post" action="<?= url('itr_register.php?stage=data') ?>">
    <input type="hidden" name="post_action" value="add_entry">
    <div class="form-grid form-grid-4">
      <div class="form-group" style="grid-column:span 2">
        <label>Client <span class="req">*</span></label>
        <select class="form-control" name="client_id" required onchange="autoFillFromClient(this)">
          <option value="">— Select Client —</option>
          <?php foreach ($all_clients as $c): ?>
            <option value="<?= $c['id'] ?>" data-partner="<?= $c['partner_id']??'' ?>" data-group="<?= $c['group_id']??'' ?>">
              <?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)
            </option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Financial Year <span class="req">*</span></label>
        <select class="form-control" name="financial_year" required>
          <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>CA Looking After</label>
        <select class="form-control" name="ca_partner_id" id="ca_partner_id">
          <option value="">Select</option>
          <?php foreach ($partners as $p): ?><option value="<?= $p['id'] ?>"><?= htmlspecialchars($p['name']) ?></option><?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Client Group</label>
        <select class="form-control" name="group_id" id="group_id_field">
          <option value="">— No Group —</option>
          <?php foreach ($groups as $g): ?><option value="<?= $g['id'] ?>"><?= htmlspecialchars($g['group_name']) ?></option><?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>ITR / Audit <span class="req">*</span></label>
        <select class="form-control" name="return_category" required>
          <option value="ITR">ITR</option>
          <option value="Audit">Audit</option>
        </select>
      </div>
      <div class="form-group">
        <label>Data Received On</label>
        <input class="form-control" type="date" name="data_received_on" value="<?= date('Y-m-d') ?>">
      </div>
    </div>
    <div class="form-actions">
      <button class="btn btn-primary" type="submit">💾 Save Data Receipt</button>
    </div>
  </form>
  </div>
</div>

<?php elseif ($stage === 'accounting'): ?>
<!-- ══ STAGE 2: ACCOUNTING ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">② Accounting Stage</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_accounting) ?> entries with data received, accounting pending</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('acc-table','ITR_Accounting_<?= $filter_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="card-body" style="padding:10px 14px 0"><?php $q_acc_f = stageFilterBar('accounting',$q_accounting,$all_users,$partners,$filter_fy); ?></div>
  <div class="table-responsive">
  <table class="data-table" id="acc-table">
    <thead><tr>
      <th class="no-export" style="width:32px"><input type="checkbox" onchange="itrSelectAll(this)"></th>
      <th>Client</th><th>FY</th><th>Partner</th><th>Data Recd</th><th>Status</th><th>Action</th>
    </tr></thead>
    <tbody>
    <?php if (empty($q_acc_f)): ?>
      <tr><td colspan="7" class="text-center text-muted" style="padding:2rem">No entries pending accounting.</td></tr>
    <?php endif; ?>
    <?php foreach ($q_acc_f as $r): ?>
      <tr>
        <td class="no-export"><input type="checkbox" class="itr-row-cb" value="<?= $r['id'] ?>" data-name="<?= htmlspecialchars($r['client_name']) ?>" onchange="updateITRBulk()"></td>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['ca_name'] ?? '—') ?></td>
        <td><?= fmtDate($r['data_received_on']) ?></td>
        <td><span class="badge badge-warning"><?= htmlspecialchars($r['accounting_status']) ?></span></td>
        <td><button class="btn btn-primary btn-sm" onclick="openAccModal(<?= htmlspecialchars(json_encode($r)) ?>)">Update Accounting</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<div class="modal-overlay" id="acc-modal">
  <div class="modal-box" style="max-width:520px">
    <div class="modal-header"><span class="modal-title">② Accounting Details</span><button class="modal-close" onclick="closeModal('acc-modal')">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=accounting') ?>">
      <input type="hidden" name="post_action" value="update_accounting">
      <input type="hidden" name="itr_id" id="am_itr_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="am_info"></div>
        <div class="form-group mb-2"><label>Accounting Done By</label>
          <select class="form-control" name="accounting_done_by">
            <option value="">Select</option>
            <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
          </select></div>
        <label style="display:flex;align-items:center;gap:8px;margin-bottom:10px;cursor:pointer">
          <input type="checkbox" id="acc_na_cb" name="accounting_na" onchange="toggleAccNA(this)">
          N/A — no accounting required for this client
        </label>
        <div id="acc_fields">
          <div class="form-group mb-2"><label>Accounting Started On</label>
            <input class="form-control" type="date" name="accounting_started_on" id="acc_started_input"></div>
          <div class="form-group mb-2"><label>Accounting Status</label>
            <select class="form-control" name="accounting_status" id="acc_status_input">
              <?php foreach (['WIP','Pending for Client Inputs','Pending for Verification - Supervisor','Pending for Verification - Partner','Done'] as $s): ?>
                <option value="<?= $s ?>"><?= $s ?></option>
              <?php endforeach; ?>
            </select></div>
        </div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('acc-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'preparation'): ?>
<!-- ══ STAGE 3: ITR PREPARATION ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">③ ITR Preparation Stage</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_preparation) ?> entries with accounting complete, ITR not yet prepared</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('prep-table','ITR_Prep_<?= $filter_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="card-body" style="padding:10px 14px 0"><?php $q_prep_f = stageFilterBar('preparation',$q_preparation,$all_users,$partners,$filter_fy); ?></div>
  <div class="table-responsive">
  <table class="data-table" id="prep-table">
    <thead><tr>
      <th class="no-export" style="width:32px"><input type="checkbox" onchange="itrSelectAll(this)"></th>
      <th>Client</th><th>FY</th><th>Partner</th><th>Acc. Status</th><th>Action</th>
    </tr></thead>
    <tbody>
    <?php if (empty($q_prep_f)): ?>
      <tr><td colspan="6" class="text-center text-muted" style="padding:2rem">No entries ready for ITR preparation.</td></tr>
    <?php endif; ?>
    <?php foreach ($q_prep_f as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?></td>
        <td><span class="badge badge-success"><?= htmlspecialchars($r['accounting_status']) ?></span></td>
        <td><button class="btn btn-primary btn-sm" onclick="openPrepModal(<?= htmlspecialchars(json_encode($r)) ?>)">Update Preparation</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<div class="modal-overlay" id="prep-modal">
  <div class="modal-box" style="max-width:520px">
    <div class="modal-header"><span class="modal-title">③ ITR Preparation Details</span><button class="modal-close" onclick="closeModal('prep-modal')">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=preparation') ?>">
      <input type="hidden" name="post_action" value="update_preparation">
      <input type="hidden" name="itr_id" id="pm_itr_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="pm_info"></div>
        <div class="form-grid form-grid-2">
          <div class="form-group"><label>ITR Prepared By</label>
            <select class="form-control" name="itr_prepared_by">
              <option value="">Select</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>ITR Prepared?</label>
            <select class="form-control" name="itr_prepared_status">
              <option value="Yes">Yes</option><option value="No" selected>No</option><option value="NA">NA</option>
            </select></div>
          <div class="form-group"><label>ITR Form No.</label>
            <input class="form-control" name="itr_form_no" list="itr_form_list" placeholder="1-7 or custom"></div>
          <div class="form-group"><label>GTI <small class="text-muted">(can be negative)</small></label>
            <input class="form-control" type="number" step="0.01" name="gti"></div>
          <div class="form-group" style="grid-column:span 2"><label>Self-Assessment Tax</label>
            <input class="form-control" type="number" step="0.01" min="0" name="sa_tax"></div>
        </div>
        <datalist id="itr_form_list"><option value="1"><option value="2"><option value="3"><option value="4"><option value="5"><option value="6"><option value="7"></datalist>
        <div class="form-group mt-2"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('prep-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'verification'): ?>
<!-- ══ STAGE 4: VERIFICATION ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">④ Verification Stage</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_verification) ?> entries with ITR prepared, awaiting verification</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('verify-table','ITR_Verification_<?= $filter_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="card-body" style="padding:10px 14px 0"><?php $q_verify_f = stageFilterBar('verification',$q_verification,$all_users,$partners,$filter_fy); ?></div>
  <div class="table-responsive">
  <table class="data-table" id="verify-table">
    <thead><tr>
      <th class="no-export" style="width:32px"><input type="checkbox" onchange="itrSelectAll(this)"></th>
      <th>Client</th><th>FY</th><th>Partner</th><th>Prepared By</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_verify_f)): ?>
      <tr><td colspan="6" class="text-center text-muted" style="padding:2rem">No entries awaiting verification.</td></tr>
    <?php endif; ?>
    <?php foreach ($q_verify_f as $r): ?>
      <tr>
        <td class="no-export"><input type="checkbox" class="itr-row-cb" value="<?= $r['id'] ?>" data-name="<?= htmlspecialchars($r['client_name']) ?>" onchange="updateITRBulk()"></td>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['ca_name'] ?? '—') ?></td>
        <td style="font-size:12px"><?= htmlspecialchars($r['itr_prep_name'] ?? '—') ?></td>
        <td><button class="btn btn-primary btn-sm" onclick="openVerifyModal(<?= htmlspecialchars(json_encode($r)) ?>)">Verify</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<div class="modal-overlay" id="verify-modal">
  <div class="modal-box" style="max-width:460px">
    <div class="modal-header"><span class="modal-title">④ Verification Details</span><button class="modal-close" onclick="closeModal('verify-modal')">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=verification') ?>">
      <input type="hidden" name="post_action" value="update_verification">
      <input type="hidden" name="itr_id" id="vm_itr_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="vm_info"></div>
        <div class="form-group mb-2"><label>ITR Verified By <span class="req">*</span></label>
          <select class="form-control" name="itr_verified_by" required>
            <option value="">Select</option>
            <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
          </select></div>
        <div class="form-group mb-2"><label>Bank Validated?</label>
          <select class="form-control" name="bank_validated">
            <option value="No">No</option><option value="Yes">Yes</option>
          </select></div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Confirm Verification</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('verify-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'filing'): ?>
<!-- ══ STAGE 5: FILING ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">⑤ Filing Stage</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_filing) ?> entries verified, ready to file</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('filing-table','ITR_Filing_<?= $filter_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="card-body" style="padding:10px 14px 0"><?php $q_filing_f = stageFilterBar('filing',$q_filing,$all_users,$partners,$filter_fy); ?></div>
  <div class="table-responsive">
  <table class="data-table" id="filing-table">
    <thead><tr>
      <th class="no-export" style="width:32px"><input type="checkbox" onchange="itrSelectAll(this)"></th>
      <th>Client</th><th>FY</th><th>Partner</th><th>Verified By</th><th>Uploaded?</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_filing_f)): ?>
      <tr><td colspan="7" class="text-center text-muted" style="padding:2rem">No entries ready for filing.</td></tr>
    <?php endif; ?>
    <?php foreach ($q_filing_f as $r): ?>
      <tr>
        <td class="no-export"><input type="checkbox" class="itr-row-cb" value="<?= $r['id'] ?>" data-name="<?= htmlspecialchars($r['client_name']) ?>" onchange="updateITRBulk()"></td>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['ca_name'] ?? '—') ?></td>
        <td style="font-size:12px"><?= htmlspecialchars($r['itr_verify_name'] ?? '—') ?></td>
        <td><span class="badge badge-secondary"><?= htmlspecialchars($r['itr_uploaded_status']) ?></span></td>
        <td><button class="btn btn-success btn-sm" onclick="openFilingModal(<?= htmlspecialchars(json_encode($r)) ?>)">File Return</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<div class="modal-overlay" id="filing-modal">
  <div class="modal-box" style="max-width:500px">
    <div class="modal-header"><span class="modal-title">⑤ Filing Details</span><button class="modal-close" onclick="closeModal('filing-modal')">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=filing') ?>">
      <input type="hidden" name="post_action" value="update_filing">
      <input type="hidden" name="itr_id" id="fm_itr_id">
      <div class="modal-body">
        <div style="background:var(--success-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="fm_info"></div>
        <div class="form-group mb-2"><label>ITR Uploaded?</label>
          <select class="form-control" name="itr_uploaded_status" id="fm_uploaded">
            <option value="WIP">WIP</option><option value="Ready">Ready</option><option value="Yes">Yes</option>
          </select></div>
        <div class="form-group mb-2"><label>ITR ACK Number <small class="text-muted">(filing date auto-detected)</small></label>
          <input class="form-control" name="itr_ack" id="fm_ack" oninput="previewFiledDate(this.value)" placeholder="e.g. 123456789012345"></div>
        <div id="fm_date_preview" style="font-size:11px;color:var(--text-muted);margin-bottom:8px"></div>
        <div class="form-group mb-2"><label>Filed Date <small class="text-muted">(manual override)</small></label>
          <input class="form-control" type="date" name="filed_date_manual"></div>
        <div class="form-group"><label>Refund (₹)</label>
          <input class="form-control" type="number" step="0.01" min="0" name="refund" placeholder="positive value only"></div>
        <div class="form-group mt-2"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Save Filing Details</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('filing-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'everify'): ?>
<!-- ══ STAGE 6: E-VERIFY ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">⑥ E-Verification Stage</span>
    <span class="text-muted" style="font-size:12px"><?= count($q_everify) ?> entries uploaded, awaiting e-verification — closes the record</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('everify-table','ITR_EVerify_<?= $filter_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="card-body" style="padding:10px 14px 0"><?php $q_ev_f = stageFilterBar('everify',$q_everify,$all_users,$partners,$filter_fy); ?></div>
  <div class="table-responsive">
  <table class="data-table" id="everify-table">
    <thead><tr><th>Client</th><th>FY</th><th>ITR ACK</th><th>Filed Date</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($q_ev_f)): ?>
      <tr><td colspan="5" class="text-center text-muted" style="padding:2rem">No entries pending e-verification.</td></tr>
    <?php endif; ?>
    <?php foreach ($q_ev_f as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td><?= htmlspecialchars($r['financial_year']) ?></td>
        <td style="font-size:11px"><code><?= htmlspecialchars($r['itr_ack']?:'—') ?></code></td>
        <td style="font-size:12px"><?= fmtDate($r['filed_date']) ?></td>
        <td><button class="btn btn-success btn-sm" onclick="openEverifyModal(<?= htmlspecialchars(json_encode($r)) ?>)">Mark E-Verified</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<div class="modal-overlay" id="everify-modal">
  <div class="modal-box" style="max-width:420px">
    <div class="modal-header"><span class="modal-title">⑥ E-Verification Status</span><button class="modal-close" onclick="closeModal('everify-modal')">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=everify') ?>">
      <input type="hidden" name="post_action" value="update_everify">
      <input type="hidden" name="itr_id" id="em_itr_id">
      <div class="modal-body">
        <div style="background:var(--success-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="em_info"></div>
        <div class="form-group mb-2"><label>E-Verified?</label>
          <select class="form-control" name="e_verified">
            <option value="Pending">Pending</option><option value="Yes">Yes</option><option value="No">No</option>
          </select></div>
        <div class="form-group"><label>Remarks</label><textarea class="form-control" name="remarks" rows="2"></textarea></div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Save &amp; Close</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('everify-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php elseif ($stage === 'refunds'): ?>
<!-- ══ REFUNDS TRACKING ══ -->
<div class="card">
  <div class="card-header" style="flex-wrap:wrap;gap:8px">
    <span class="card-title">💰 Refund Cases — FY <?= htmlspecialchars($refund_fy) ?></span>
    <span class="text-muted" style="font-size:12px"><?= count($q_refunds) ?> cases with refund due</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('refunds-table','ITR_Refunds_<?= $refund_fy ?>')">⬇ Export XLS</button>
  </div>
  <div class="table-responsive">
  <table class="data-table" id="refunds-table">
    <thead>
      <tr>
        <th>Client</th><th>PAN</th><th>Partner</th><th>Supervisor</th>
        <th>Form</th><th>Filed Date</th><th>ACK</th>
        <th>Refund Due (₹)</th><th>Refund Status</th>
        <th>Received Date</th><th>Received (₹)</th><th>Intimation No.</th>
        <th class="no-export">Update</th>
      </tr>
    </thead>
    <tbody>
    <?php if (empty($q_refunds)): ?>
      <tr><td colspan="13" class="text-center text-muted" style="padding:2rem">
        No refund cases for FY <?= htmlspecialchars($refund_fy) ?>. Refund amount must be entered on the entry to appear here.
      </td></tr>
    <?php endif; ?>
    <?php foreach ($q_refunds as $r):
      $rsc = ['Pending'=>'badge-secondary','Received'=>'badge-success',
              'Partially Received'=>'badge-warning','Adjusted'=>'badge-info',
              'Not Applicable'=>'badge-secondary'];
    ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
        <td><code style="font-size:11px"><?= htmlspecialchars($r['pan']) ?></code></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['ca_name']  ?? '—') ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['sup_name'] ?? '—') ?></td>
        <td><span class="badge badge-primary"><?= htmlspecialchars($r['itr_form_no'] ?? '—') ?></span></td>
        <td style="font-size:11px"><?= fmtDate($r['filed_date']) ?></td>
        <td style="font-size:10px"><code><?= htmlspecialchars($r['itr_ack'] ?? '—') ?></code></td>
        <td class="text-right" style="font-weight:600;color:var(--primary)">₹<?= number_format($r['refund'], 0) ?></td>
        <td><span class="badge <?= $rsc[$r['refund_status'] ?? 'Pending'] ?? 'badge-secondary' ?>"><?= htmlspecialchars($r['refund_status'] ?? 'Pending') ?></span></td>
        <td style="font-size:11px"><?= fmtDate($r['refund_received_date'] ?? null) ?></td>
        <td class="text-right"><?= $r['refund_received_amount'] ? '₹'.number_format($r['refund_received_amount'],0) : '—' ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['refund_intimation_no'] ?? '—') ?></td>
        <td class="no-export">
          <button type="button" class="btn btn-outline btn-sm" onclick="openRefundModal(<?= htmlspecialchars(json_encode($r)) ?>)">Update</button>
        </td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<!-- Refund Update Modal -->
<div class="modal-overlay" id="refund-modal">
  <div class="modal-box" style="max-width:500px">
    <div class="modal-header"><span class="modal-title">💰 Update Refund Status</span>
      <button class="modal-close" onclick="closeModal('refund-modal')" type="button">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage=refunds&fy='.urlencode($refund_fy)) ?>">
      <input type="hidden" name="post_action" value="update_refund">
      <input type="hidden" name="itr_id"     id="rfm_id">
      <input type="hidden" name="current_fy" value="<?= htmlspecialchars($refund_fy) ?>">
      <div class="modal-body">
        <div id="rfm_info" style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px"></div>
        <div class="form-grid form-grid-2">
          <div class="form-group" style="grid-column:span 2">
            <label>Refund Status</label>
            <select class="form-control" name="refund_status" id="rfm_status">
              <?php foreach (['Pending','Received','Partially Received','Adjusted','Not Applicable'] as $rs): ?>
                <option value="<?= $rs ?>"><?= $rs ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <div class="form-group"><label>Received Date</label>
            <input class="form-control" type="date" name="refund_received_date" id="rfm_date"></div>
          <div class="form-group"><label>Received Amount (₹)</label>
            <input class="form-control" type="number" step="0.01" name="refund_received_amount" id="rfm_amt"></div>
          <div class="form-group" style="grid-column:span 2"><label>Intimation / Reference No.</label>
            <input class="form-control" name="refund_intimation_no" id="rfm_ref"></div>
          <div class="form-group" style="grid-column:span 2"><label>Remarks</label>
            <textarea class="form-control" name="remarks" rows="2"></textarea></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Save</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('refund-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>


<?php elseif ($action === 'edit'): ?>
<!-- ══ FULL EDIT (override — all fields at once) ══ -->
<div class="page-header">
  <div class="page-title">✏️ Edit IT Return Entry (Full Override)</div>
  <a href="<?= url('itr_register.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card"><div class="card-body">
<form method="post" action="<?= url('itr_register.php?stage=list') ?>">
  <input type="hidden" name="post_action" value="edit_entry">
  <input type="hidden" name="itr_id" value="<?= $id ?>">
  <div class="form-grid form-grid-4">
    <div class="form-group" style="grid-column:span 2"><label>Client</label>
      <select class="form-control" name="client_id" required>
        <?php foreach ($all_clients as $c): ?>
          <option value="<?= $c['id'] ?>" <?= ($entry['client_id']??0)==$c['id']?'selected':'' ?>><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>FY</label>
      <select class="form-control" name="financial_year">
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= ($entry['financial_year']??'')===$fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR / Audit</label>
      <select class="form-control" name="return_category">
        <option value="ITR" <?= ($entry['return_category']??'')==='ITR'?'selected':'' ?>>ITR</option>
        <option value="Audit" <?= ($entry['return_category']??'')==='Audit'?'selected':'' ?>>Audit</option>
      </select></div>
    <div class="form-group"><label>CA Looking After</label>
      <select class="form-control" name="ca_partner_id">
        <option value="">—</option>
        <?php foreach ($partners as $p): ?><option value="<?= $p['id'] ?>" <?= ($entry['ca_partner_id']??'')==$p['id']?'selected':'' ?>><?= htmlspecialchars($p['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Group</label>
      <select class="form-control" name="group_id">
        <option value="">—</option>
        <?php foreach ($groups as $g): ?><option value="<?= $g['id'] ?>" <?= ($entry['group_id']??'')==$g['id']?'selected':'' ?>><?= htmlspecialchars($g['group_name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Data Received On</label>
      <input class="form-control" type="date" name="data_received_on" value="<?= $entry['data_received_on']??'' ?>"></div>
    <div class="form-group"><label>Accounting Done By</label>
      <select class="form-control" name="accounting_done_by">
        <option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['accounting_done_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Accounting Started On</label>
      <input class="form-control" type="date" name="accounting_started_on" value="<?= $entry['accounting_started_on']??'' ?>" <?= !empty($entry['accounting_na'])?'disabled':'' ?>></div>
    <div class="form-group" style="flex-direction:row;align-items:center;gap:8px">
      <input type="checkbox" name="accounting_na" id="edit_acc_na" <?= !empty($entry['accounting_na'])?'checked':'' ?>>
      <label style="text-transform:none;font-size:12px" for="edit_acc_na">N/A</label>
    </div>
    <div class="form-group"><label>Accounting Status</label>
      <select class="form-control" name="accounting_status">
        <?php foreach (['NA','WIP','Pending for Client Inputs','Pending for Verification - Supervisor','Pending for Verification - Partner','Done'] as $s): ?>
          <option value="<?= $s ?>" <?= ($entry['accounting_status']??'')===$s?'selected':'' ?>><?= $s ?></option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR Prepared By</label>
      <select class="form-control" name="itr_prepared_by">
        <option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['itr_prepared_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR Prepared?</label>
      <select class="form-control" name="itr_prepared_status">
        <?php foreach (['Yes','No','NA'] as $s): ?><option value="<?= $s ?>" <?= ($entry['itr_prepared_status']??'')===$s?'selected':'' ?>><?= $s ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR Verified By</label>
      <select class="form-control" name="itr_verified_by">
        <option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['itr_verified_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR Uploaded?</label>
      <select class="form-control" name="itr_uploaded_status">
        <?php foreach (['WIP','Ready','Yes'] as $s): ?><option value="<?= $s ?>" <?= ($entry['itr_uploaded_status']??'')===$s?'selected':'' ?>><?= $s ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR ACK</label>
      <input class="form-control" name="itr_ack" value="<?= htmlspecialchars($entry['itr_ack']??'') ?>"></div>
    <div class="form-group"><label>Filed Date (manual)</label>
      <input class="form-control" type="date" name="filed_date_manual" value="<?= $entry['filed_date']??'' ?>"></div>
    <div class="form-group"><label>E-Verified?</label>
      <select class="form-control" name="e_verified">
        <?php foreach (['Pending','Yes','No'] as $s): ?><option value="<?= $s ?>" <?= ($entry['e_verified']??'')===$s?'selected':'' ?>><?= $s ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>ITR Form No.</label>
      <input class="form-control" name="itr_form_no" value="<?= htmlspecialchars($entry['itr_form_no']??'') ?>"></div>
    <div class="form-group"><label>GTI</label>
      <input class="form-control" type="number" step="0.01" name="gti" value="<?= $entry['gti']??'' ?>"></div>
    <div class="form-group"><label>SA Tax</label>
      <input class="form-control" type="number" step="0.01" min="0" name="sa_tax" value="<?= $entry['sa_tax']??'' ?>"></div>
    <div class="form-group"><label>Refund</label>
      <input class="form-control" type="number" step="0.01" min="0" name="refund" value="<?= $entry['refund']??'' ?>"></div>
    <div class="form-group"><label>Bank Validated?</label>
      <select class="form-control" name="bank_validated">
        <option value="No" <?= ($entry['bank_validated']??'')==='No'?'selected':'' ?>>No</option>
        <option value="Yes" <?= ($entry['bank_validated']??'')==='Yes'?'selected':'' ?>>Yes</option>
      </select></div>
    <div class="form-group" style="grid-column:span 4"><label>Remarks</label>
      <textarea class="form-control" name="remarks" rows="2"><?= htmlspecialchars($entry['remarks']??'') ?></textarea></div>
  </div>
  <div class="form-actions">
    <button class="btn btn-primary" type="submit">💾 Save Changes</button>
    <a href="<?= url('itr_register.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>

<?php else: // LIST VIEW ?>

<?php if ($summary): ?>
<div class="card" style="margin-bottom:1.25rem;border-left:4px solid var(--primary)">
  <div class="card-header" style="background:var(--primary-bg)">
    <span class="card-title" style="color:var(--primary)">📊 Executive Summary — FY <?= htmlspecialchars($filter_fy) ?></span>
  </div>
  <div class="card-body" style="padding:14px">
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;text-align:center">
      <div style="padding:10px 6px;background:#f8f9fa;border-radius:6px;border:1px solid var(--border-lt)">
        <div style="font-size:20px;font-weight:700;color:var(--primary)"><?= $summary['total_count'] ?></div>
        <div style="font-size:10px;color:var(--text-muted)">Total Cases</div>
      </div>
      <a href="?stage=list&fy=<?= urlencode($filter_fy) ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#fdf0ef;border-radius:6px;border:1px solid #fecaca">
        <div style="font-size:20px;font-weight:700;color:#c0392b"><?= $summary['data_pending'] ?></div>
        <div style="font-size:10px;color:#c0392b">Data Pending</div>
      </div></a>
      <a href="<?= url('itr_register.php?stage=accounting') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#fef9ec;border-radius:6px;border:1px solid #fed7aa">
        <div style="font-size:20px;font-weight:700;color:#b45309"><?= $summary['acc_pending'] ?></div>
        <div style="font-size:10px;color:#b45309">Accounting Pending</div>
      </div></a>
      <a href="<?= url('itr_register.php?stage=preparation') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#e8f4fc;border-radius:6px;border:1px solid #bae6fd">
        <div style="font-size:20px;font-weight:700;color:#1d6fa5"><?= $summary['prep_pending'] ?></div>
        <div style="font-size:10px;color:#1d6fa5">ITR Prep Pending</div>
      </div></a>
      <a href="<?= url('itr_register.php?stage=verification') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#f1ecfb;border-radius:6px;border:1px solid #ddd0f5">
        <div style="font-size:20px;font-weight:700;color:#6a4fb0"><?= $summary['verify_pending'] ?></div>
        <div style="font-size:10px;color:#6a4fb0">Verification Pending</div>
      </div></a>
      <a href="<?= url('itr_register.php?stage=filing') ?>" style="text-decoration:none">
      <div style="padding:10px 6px;background:#fff8f0;border-radius:6px;border:1px solid #fed7aa">
        <div style="font-size:20px;font-weight:700;color:#b45309"><?= $summary['filing_pending'] ?></div>
        <div style="font-size:10px;color:#b45309">Filing Pending</div>
      </div></a>
      <div style="padding:10px 6px;background:#f0fdf4;border-radius:6px;border:1px solid #bbf7d0">
        <div style="font-size:20px;font-weight:700;color:#166534"><?= $summary['filed'] ?></div>
        <div style="font-size:10px;color:#166534">Filed ✓</div>
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
    <div class="filter-group"><label>ITR/Audit</label>
      <select name="category"><option value="">All</option>
        <option value="ITR" <?= $filter_category==='ITR'?'selected':'' ?>>ITR</option>
        <option value="Audit" <?= $filter_category==='Audit'?'selected':'' ?>>Audit</option>
      </select></div>
    <div class="filter-group"><label>CA Partner</label>
      <select name="ca_partner_id"><option value="">All</option>
        <?php foreach ($partners as $p): ?><option value="<?= $p['id'] ?>" <?= $filter_partner==$p['id']?'selected':'' ?>><?= htmlspecialchars($p['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Group</label>
      <select name="group_id"><option value="">All</option>
        <?php foreach ($groups as $g): ?><option value="<?= $g['id'] ?>" <?= $filter_group==$g['id']?'selected':'' ?>><?= htmlspecialchars($g['group_name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('itr_register.php') ?>" class="btn btn-outline">Reset</a>
      <button class="btn btn-export" type="button" onclick="exportTableToXLS('itr-table','ITR_Register_<?= $filter_fy ?>')">⬇ Export XLS</button>
    </div>
  </form>
</div>

<div class="card"><div class="table-responsive">
<table class="data-table" id="itr-table">
  <thead>
    <tr>
      <th>Sr.No.</th><th>PAN</th><th>CA Looking After</th><th>Client Name</th><th>Group</th>
      <th>ITR/Audit</th><th>Data Recd On</th><th>Accounting By</th><th>Acc. Started</th><th>Acc. Status</th>
      <th>ITR Prep By</th><th>ITR Prepared?</th><th>ITR Verified By</th><th>ITR Uploaded?</th>
      <th>ITR ACK</th><th>Filed Date</th><th>E-Verified?</th><th>Form No.</th>
      <th>GTI</th><th>SA Tax</th><th>Refund</th><th>Bank Validated?</th>
      <th class="no-export">Actions</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($entries as $i => $r): ?>
    <tr>
      <td><?= $pg['offset']+$i+1 ?></td>
      <td><code style="font-size:11px"><?= htmlspecialchars($r['pan']) ?></code></td>
      <td style="font-size:12px"><?= htmlspecialchars($r['ca_name'] ?? '—') ?></td>
      <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong></td>
      <td style="font-size:11px"><?= htmlspecialchars($r['group_name'] ?? '—') ?></td>
      <td><span class="badge <?= $r['return_category']==='Audit'?'badge-warning':'badge-primary' ?>"><?= $r['return_category'] ?></span></td>
      <td style="font-size:11px"><?= $r['data_received_on'] ? '<span class="badge badge-success">'.fmtDate($r['data_received_on']).'</span>' : '<span class="badge badge-secondary">Pending</span>' ?></td>
      <td style="font-size:12px"><?= htmlspecialchars($r['acc_done_name'] ?? '—') ?></td>
      <td style="font-size:11px"><?= $r['accounting_na'] ? 'N/A' : fmtDate($r['accounting_started_on']) ?></td>
      <td><?php
        $acc_badges = ['NA'=>'badge-secondary','WIP'=>'badge-info','Pending for Client Inputs'=>'badge-warning',
                       'Pending for Verification - Supervisor'=>'badge-warning','Pending for Verification - Partner'=>'badge-warning','Done'=>'badge-success'];
        echo '<span class="badge '.($acc_badges[$r['accounting_status']]??'badge-secondary').'" style="font-size:10px">'.htmlspecialchars($r['accounting_status']).'</span>';
      ?></td>
      <td style="font-size:12px"><?= htmlspecialchars($r['itr_prep_name'] ?? '—') ?></td>
      <td><?php
        $prep_badges = ['Yes'=>'badge-success','No'=>'badge-secondary','NA'=>'badge-secondary'];
        echo '<span class="badge '.($prep_badges[$r['itr_prepared_status']]??'badge-secondary').'">'.$r['itr_prepared_status'].'</span>';
      ?></td>
      <td style="font-size:12px"><?= htmlspecialchars($r['itr_verify_name'] ?? '—') ?></td>
      <td><?php
        $upl_badges = ['Yes'=>'badge-success','Ready'=>'badge-info','WIP'=>'badge-secondary'];
        echo '<span class="badge '.($upl_badges[$r['itr_uploaded_status']]??'badge-secondary').'">'.$r['itr_uploaded_status'].'</span>';
      ?></td>
      <td style="font-size:10px"><code><?= htmlspecialchars($r['itr_ack'] ?: '—') ?></code></td>
      <td style="font-size:11px"><?= $r['filed_date'] ? '<span class="badge badge-success">'.fmtDate($r['filed_date']).'</span>' : '—' ?></td>
      <td><?php
        $ev_badges = ['Yes'=>'badge-success','No'=>'badge-danger','Pending'=>'badge-secondary'];
        echo '<span class="badge '.($ev_badges[$r['e_verified']]??'badge-secondary').'">'.$r['e_verified'].'</span>';
      ?></td>
      <td><?= htmlspecialchars($r['itr_form_no'] ?: '—') ?></td>
      <td class="text-right" style="<?= $r['gti']<0?'color:var(--danger)':'' ?>"><?= $r['gti']!==null ? '₹'.number_format($r['gti'],0) : '—' ?></td>
      <td class="text-right"><?= $r['sa_tax']!==null ? '₹'.number_format($r['sa_tax'],0) : '—' ?></td>
      <td class="text-right"><?= $r['refund']!==null ? '₹'.number_format($r['refund'],0) : '—' ?></td>
      <td><?= $r['bank_validated']==='Yes' ? '<span class="badge badge-success">Yes</span>' : '<span class="badge badge-secondary">No</span>' ?></td>
      <td class="no-export" style="white-space:nowrap">
        <a href="<?= url('itr_register.php?action=edit&id=').$r['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
        <a href="<?= url('itr_register.php?action=delete&id=').$r['id'] ?>" class="btn btn-danger btn-sm" onclick="return confirm('Delete this entry?')">Delete</a>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($entries)): ?>
    <tr><td colspan="22" class="text-center text-muted" style="padding:2rem">No entries found. Go to ① Data Receipt to add the first entry.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div></div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i=1; $i<=$pg['total_pages']; $i++): ?>
    <a href="?stage=list&fy=<?= urlencode($filter_fy) ?>&category=<?= urlencode($filter_category) ?>&page=<?= $i ?>" class="page-link <?= $i===$page?'active':'' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($entries) ?> of <?= $total ?></span>
</div>
<?php endif; ?>

<?php endif; // end stage/action blocks ?>

<!-- ══ BULK UPDATE TOOLBAR (sticky, shown when entries selected) ══ -->
<?php if (hasRole(['admin','partner','supervisor'])): ?>
<div id="bulk-toolbar"
     style="display:none;position:sticky;bottom:0;z-index:100;background:var(--primary);
            color:#fff;padding:10px 16px;border-radius:8px 8px 0 0;
            margin-top:8px;align-items:center;gap:12px;flex-wrap:wrap">
  <span style="font-weight:600;font-size:13px"><span id="itr-bulk-count">0</span> entries selected</span>
  <button type="button" class="btn btn-sm"
          style="background:rgba(255,255,255,.2);color:#fff;border-color:rgba(255,255,255,.3)"
          onclick="openITRBulkModal()">✏ Bulk Update Fields</button>
  <button type="button" class="btn btn-sm"
          style="background:rgba(255,255,255,.1);color:rgba(255,255,255,.8);border-color:rgba(255,255,255,.2);margin-left:auto"
          onclick="clearITRBulk()">✕ Clear</button>
</div>

<!-- Bulk Update Modal -->
<div class="modal-overlay" id="itr-bulk-modal">
  <div class="modal-box" style="max-width:560px">
    <div class="modal-header"><span class="modal-title">✏ Bulk Update ITR Entries</span>
      <button class="modal-close" onclick="closeModal('itr-bulk-modal')" type="button">×</button></div>
    <form method="post" action="<?= url('itr_register.php?stage='.$stage) ?>" id="itr-bulk-form">
      <input type="hidden" name="post_action" value="bulk_update">
      <input type="hidden" name="current_fy" value="<?= htmlspecialchars($filter_fy) ?>">
      <div id="itr-bulk-ids"></div>
      <div class="modal-body">
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:10px">
          Only fields you fill will be updated. Leave blank to keep existing value.
        </p>
        <div id="itr-bulk-preview"
             style="background:var(--primary-bg);padding:8px 12px;border-radius:6px;
                    margin-bottom:12px;font-size:12px;max-height:70px;overflow-y:auto"></div>
        <div class="form-grid form-grid-2">
          <div class="form-group"><label>Accounting Done By</label>
            <select class="form-control" name="bulk_accounting_done_by">
              <option value="">— No change —</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>ITR Prepared By</label>
            <select class="form-control" name="bulk_itr_prepared_by">
              <option value="">— No change —</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>ITR Verified By</label>
            <select class="form-control" name="bulk_itr_verified_by">
              <option value="">— No change —</option>
              <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>"><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>CA Partner</label>
            <select class="form-control" name="bulk_ca_partner_id">
              <option value="">— No change —</option>
              <?php foreach ($partners as $p): ?><option value="<?= $p['id'] ?>"><?= htmlspecialchars($p['name']) ?></option><?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>Accounting Status</label>
            <select class="form-control" name="bulk_accounting_status">
              <option value="">— No change —</option>
              <?php foreach (['NA','WIP','Pending for Client Inputs','Pending for Verification - Supervisor','Pending for Verification - Partner','Done'] as $s): ?>
                <option value="<?= $s ?>"><?= $s ?></option>
              <?php endforeach; ?>
            </select></div>
          <div class="form-group"><label>ITR Prepared Status</label>
            <select class="form-control" name="bulk_itr_prepared_status">
              <option value="">— No change —</option>
              <option value="Yes">Yes</option><option value="No">No</option><option value="NA">N/A</option>
            </select></div>
          <div class="form-group"><label>E-Verified?</label>
            <select class="form-control" name="bulk_e_verified">
              <option value="">— No change —</option>
              <option value="Yes">Yes</option><option value="Pending">Pending</option><option value="No">No</option>
            </select></div>
          <div class="form-group"><label>Refund Status</label>
            <select class="form-control" name="bulk_refund_status">
              <option value="">— No change —</option>
              <?php foreach (['Pending','Received','Partially Received','Adjusted','Not Applicable'] as $rs): ?>
                <option value="<?= $rs ?>"><?= $rs ?></option>
              <?php endforeach; ?>
            </select></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">Apply to Selected</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('itr-bulk-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>
<?php endif; ?>

<script>
function autoFillFromClient(sel) {
  const opt = sel.options[sel.selectedIndex];
  if (opt.dataset.partner) document.getElementById('ca_partner_id').value = opt.dataset.partner;
  if (opt.dataset.group)   document.getElementById('group_id_field').value = opt.dataset.group;
}
function toggleAccNA(cb) { document.getElementById('acc_fields').style.display = cb.checked ? 'none' : 'block'; }
function previewFiledDate(ack) {
  const digits = ack.replace(/[^0-9]/g, '');
  const preview = document.getElementById('fm_date_preview');
  if (digits.length >= 6) {
    const last6 = digits.slice(-6);
    const dd = last6.slice(0,2), mm = last6.slice(2,4), yy = last6.slice(4,6);
    const d = parseInt(dd), m = parseInt(mm);
    if (d>=1 && d<=31 && m>=1 && m<=12) {
      preview.textContent = '📅 Filed Date (auto-detected): ' + dd + '-' + mm + '-20' + yy;
      return;
    }
  }
  preview.textContent = '';
}
function openAccModal(r) {
  document.getElementById('am_itr_id').value = r.id;
  document.getElementById('am_info').innerHTML = '<strong>'+r.client_name+'</strong> | FY '+r.financial_year+' | PAN: '+r.pan;
  openModal('acc-modal');
}
function openPrepModal(r) {
  document.getElementById('pm_itr_id').value = r.id;
  document.getElementById('pm_info').innerHTML = '<strong>'+r.client_name+'</strong> | FY '+r.financial_year+' | Accounting: '+r.accounting_status;
  openModal('prep-modal');
}
function openVerifyModal(r) {
  document.getElementById('vm_itr_id').value = r.id;
  document.getElementById('vm_info').innerHTML = '<strong>'+r.client_name+'</strong> | FY '+r.financial_year+' | Prepared by: '+(r.itr_prep_name||'—');
  openModal('verify-modal');
}
function openFilingModal(r) {
  document.getElementById('fm_itr_id').value = r.id;
  document.getElementById('fm_info').innerHTML = '<strong>'+r.client_name+'</strong> | FY '+r.financial_year+' | Verified by: '+(r.itr_verify_name||'—');
  document.getElementById('fm_uploaded').value = r.itr_uploaded_status || 'WIP';
  openModal('filing-modal');
}
function openEverifyModal(r) {
  document.getElementById('em_itr_id').value = r.id;
  document.getElementById('em_info').innerHTML = '<strong>'+r.client_name+'</strong> | FY '+r.financial_year+' | ACK: '+(r.itr_ack||'—');
  openModal('everify-modal');
}

// ── BULK SELECTION ─────────────────────────────────────────
var itrBulkSelected = {};
function updateITRBulk() {
  itrBulkSelected = {};
  document.querySelectorAll('.itr-row-cb:checked').forEach(function(cb) {
    itrBulkSelected[cb.value] = cb.dataset.name || ('Entry #' + cb.value);
  });
  var n = Object.keys(itrBulkSelected).length;
  var tb = document.getElementById('bulk-toolbar');
  if (tb) { tb.style.display = n > 0 ? 'flex' : 'none'; }
  var cnt = document.getElementById('itr-bulk-count');
  if (cnt) cnt.textContent = n;
}
function itrSelectAll(masterCb) {
  document.querySelectorAll('.itr-row-cb').forEach(function(cb) { cb.checked = masterCb.checked; });
  updateITRBulk();
}
function selectAllStageCBs() {
  document.querySelectorAll('.itr-row-cb').forEach(function(cb) { cb.checked = true; });
  updateITRBulk();
}
function clearITRBulk() {
  document.querySelectorAll('.itr-row-cb').forEach(function(cb) { cb.checked = false; });
  var sa = document.getElementById('itr-select-all');
  if (sa) sa.checked = false;
  updateITRBulk();
}
function openITRBulkModal() {
  if (!Object.keys(itrBulkSelected).length) { alert('Please select at least one entry first.'); return; }
  var container = document.getElementById('itr-bulk-ids');
  if (container) {
    container.innerHTML = Object.keys(itrBulkSelected).map(function(id) {
      return '<input type="hidden" name="bulk_ids[]" value="' + parseInt(id) + '">';
    }).join('');
  }
  var preview = document.getElementById('itr-bulk-preview');
  if (preview) {
    var names = Object.values(itrBulkSelected).slice(0, 8).join(', ');
    var extra = Object.keys(itrBulkSelected).length > 8 ? ' … and ' + (Object.keys(itrBulkSelected).length - 8) + ' more' : '';
    preview.innerHTML = '<strong>' + Object.keys(itrBulkSelected).length + ' entries:</strong> ' + names + extra;
  }
  openModal('itr-bulk-modal');
}

// ── REFUND MODAL ───────────────────────────────────────────
function openRefundModal(r) {
  document.getElementById('rfm_id').value  = r.id;
  document.getElementById('rfm_info').innerHTML =
    '<strong>' + r.client_name + '</strong> | Refund Due: ₹' +
    parseFloat(r.refund || 0).toLocaleString('en-IN') +
    ' | Status: <strong>' + (r.refund_status || 'Pending') + '</strong>';
  document.getElementById('rfm_status').value = r.refund_status || 'Pending';
  document.getElementById('rfm_date').value   = r.refund_received_date || '';
  document.getElementById('rfm_amt').value    = r.refund_received_amount || '';
  document.getElementById('rfm_ref').value    = r.refund_intimation_no  || '';
  openModal('refund-modal');
}
</script>

<?php include 'includes/footer.php'; ?>
