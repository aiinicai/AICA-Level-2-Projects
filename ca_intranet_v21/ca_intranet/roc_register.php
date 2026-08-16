<?php
require_once __DIR__ . '/includes/config.php';
requireLogin();
$db = getDB();
$page_title = 'ROC Compliance Register';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);

// ROC form definitions with standard due dates
$roc_forms = [
    'MGT-7'         => ['Annual Return (Companies)','60 days from AGM date'],
    'MGT-7A'        => ['Annual Return (OPC/Small Co.)','60 days from AGM date'],
    'AOC-4'         => ['Financial Statements Filing','30 days from AGM date'],
    'AOC-4 XBRL'    => ['Financial Statements (XBRL)','30 days from AGM date'],
    'ADT-1'         => ['Auditor Appointment','15 days from AGM date'],
    'DIR-3 KYC'     => ['DIN KYC (with DSC)','30 September annually'],
    'DIR-3 KYC Web' => ['DIN KYC (Web-based)','30 September annually'],
    'DPT-3'         => ['Return of Deposits / Loans','30 June annually'],
    'MSME-1'        => ['Outstanding Payments to MSME','30 Apr & 31 Oct half-yearly'],
    'MGT-14'        => ['Filing Resolutions','30 days from passing resolution'],
    'INC-20A'       => ['Declaration of Commencement','180 days from incorporation'],
    'BEN-2'         => ['Significant Beneficial Owner','30 days from event'],
    'PAS-3'         => ['Return of Allotment','15 days from allotment'],
    'SH-7'          => ['Alteration of Share Capital','30 days from SR'],
    'CHG-1'         => ['Creation/Modification of Charge','30 days from creation'],
    'CHG-4'         => ['Satisfaction of Charge','30 days from satisfaction'],
    'LLP-11'        => ['LLP Annual Return','60 days from end of FY (30 May)'],
    'LLP-8'         => ['LLP Statement of Account & Solvency','30 October annually'],
    'Form 8 LLP'    => ['LLP Financial Statements','30 October annually'],
    'Other'         => ['Other Compliance','As applicable'],
];

// ── DELETE ────────────────────────────────────────────────
if ($action === 'delete' && $id && hasRole(['admin','partner','supervisor'])) {
    $db->prepare("DELETE FROM roc_compliances WHERE id=?")->execute([$id]);
    auditLog('roc_compliances', $id, 'DELETE');
    $_SESSION['flash_msg'] = 'ROC entry deleted.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('roc_register.php')); exit;
}

// ── SAVE ──────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action !== 'bulk_create') {
    $d = $_POST;
    $form_type = $d['form_type'] ?? '';
    $data = [
        'client_id'           => intval($d['client_id']),
        'financial_year'      => $d['financial_year'] ?? '',
        'form_type'           => $form_type,
        'form_description'    => $roc_forms[$form_type][0] ?? trim($d['form_description'] ?? ''),
        'due_date'            => $d['due_date'] ?: null,
        'due_date_basis'      => $roc_forms[$form_type][1] ?? trim($d['due_date_basis'] ?? ''),
        'documents_received_date' => $d['documents_received_date'] ?: null,
        'prepared_by'         => $d['prepared_by'] ?: null,
        'prepared_date'       => $d['prepared_date'] ?: null,
        'reviewed_by'         => $d['reviewed_by'] ?: null,
        'reviewed_date'       => $d['reviewed_date'] ?: null,
        'filed_date'          => $d['filed_date'] ?: null,
        'srn'                 => strtoupper(trim($d['srn'] ?? '')),
        'challan_amount'      => floatval($d['challan_amount'] ?? 0),
        'late_fee'            => floatval($d['late_fee'] ?? 0),
        'status'              => $d['status'] ?? 'Not Started',
        'remarks'             => trim($d['remarks'] ?? ''),
        'assigned_to'         => $d['assigned_to'] ?: null,
        'created_by'          => $_SESSION['user_id'],
    ];
    if ($id) {
        $cols = implode(' = ?, ', array_keys($data)) . ' = ?';
        $stmt = $db->prepare("UPDATE roc_compliances SET $cols WHERE id = ?");
        $stmt->execute(array_merge(array_values($data), [$id]));
        auditLog('roc_compliances', $id, 'UPDATE', null, $data);
        $_SESSION['flash_msg'] = 'ROC entry updated.'; $_SESSION['flash_type'] = 'success';
    } else {
        $cols = implode(', ', array_keys($data));
        $ph   = implode(', ', array_fill(0, count($data), '?'));
        $stmt = $db->prepare("INSERT INTO roc_compliances ($cols) VALUES ($ph)");
        $stmt->execute(array_values($data));
        auditLog('roc_compliances', $db->lastInsertId(), 'CREATE', null, $data);
        $_SESSION['flash_msg'] = 'ROC entry added.'; $_SESSION['flash_type'] = 'success';
    }
    header('Location: '.url('roc_register.php')); exit;
}

// ── BULK CREATE ───────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'bulk_create' && hasRole(['admin','partner','supervisor'])) {
    $fy       = $_POST['financial_year'];
    $forms    = $_POST['forms'] ?? [];
    $client_ids = $_POST['client_ids'] ?? [];
    $created = 0;
    foreach ($client_ids as $cid) {
        // Get client details for due date computation
        $cl = $db->prepare("SELECT * FROM clients WHERE id = ?"); $cl->execute([$cid]); $cl = $cl->fetch();
        if (!$cl) continue;
        foreach ($forms as $form) {
            $check = $db->prepare("SELECT id FROM roc_compliances WHERE client_id = ? AND financial_year = ? AND form_type = ?");
            $check->execute([$cid, $fy, $form]);
            if ($check->fetch()) continue;
            // Compute due date based on form type and client AGM
            $due = null;
            $agm = $cl['agm_date'];
            $fy_start = intval(substr($fy, 0, 4));
            $due_map = [
                'MGT-7'         => $agm ? date('Y-m-d', strtotime($agm . ' +60 days')) : null,
                'MGT-7A'        => $agm ? date('Y-m-d', strtotime($agm . ' +60 days')) : null,
                'AOC-4'         => $agm ? date('Y-m-d', strtotime($agm . ' +30 days')) : null,
                'AOC-4 XBRL'    => $agm ? date('Y-m-d', strtotime($agm . ' +30 days')) : null,
                'ADT-1'         => $agm ? date('Y-m-d', strtotime($agm . ' +15 days')) : null,
                'DIR-3 KYC'     => ($fy_start+1) . '-09-30',
                'DIR-3 KYC Web' => ($fy_start+1) . '-09-30',
                'DPT-3'         => ($fy_start+1) . '-06-30',
                'MSME-1'        => ($fy_start+1) . '-04-30', // first half
                'LLP-11'        => ($fy_start+1) . '-05-30',
                'LLP-8'         => ($fy_start+1) . '-10-30',
                'Form 8 LLP'    => ($fy_start+1) . '-10-30',
            ];
            $due = $due_map[$form] ?? null;
            $ins = $db->prepare("INSERT INTO roc_compliances (client_id, financial_year, form_type, form_description, due_date, due_date_basis, status, created_by) VALUES (?,?,?,?,?,?,?,?)");
            $ins->execute([$cid, $fy, $form, $roc_forms[$form][0] ?? '', $due, $roc_forms[$form][1] ?? '', 'Not Started', $_SESSION['user_id']]);
            $created++;
        }
    }
    $_SESSION['flash_msg'] = "Bulk create done: $created ROC entries created.";
    $_SESSION['flash_type'] = 'success';
    header('Location: '.url('roc_register.php')); exit;
}

// ── FETCH FOR EDIT ─────────────────────────────────────────
$entry = [];
if ($action === 'edit' && $id) {
    $stmt = $db->prepare("SELECT r.*, c.client_name, c.pan, c.cin FROM roc_compliances r JOIN clients c ON c.id = r.client_id WHERE r.id = ?");
    $stmt->execute([$id]); $entry = $stmt->fetch() ?: [];
}

// ── FILTERS ────────────────────────────────────────────────
$dp = defaultPeriod('roc');
$filter_fy     = array_key_exists('fy', $_GET) ? trim($_GET['fy']) : $dp['fy'];
$filter_form   = $_GET['form_type']    ?? '';
$filter_status = $_GET['status']       ?? '';
$filter_client = intval($_GET['client_id']     ?? 0);
$filter_due    = $_GET['due']          ?? '';
$filter_sup    = intval($_GET['supervisor_id'] ?? 0);
$filter_partner= intval($_GET['partner_id']    ?? 0);
$page = max(1, intval($_GET['page'] ?? 1));
$per_page = 30;

$where = ['1=1']; $wparams = [];
if ($filter_fy)      { $where[] = 'r.financial_year = ?'; $wparams[] = $filter_fy; }
if ($filter_form)    { $where[] = 'r.form_type = ?'; $wparams[] = $filter_form; }
if ($filter_status)  { $where[] = 'r.status = ?'; $wparams[] = $filter_status; }
if ($filter_client)  { $where[] = 'r.client_id = ?'; $wparams[] = $filter_client; }
if ($filter_sup)     { $where[] = 'c.supervisor_id = ?'; $wparams[] = $filter_sup; }
if ($filter_partner) { $where[] = 'c.partner_id = ?'; $wparams[] = $filter_partner; }
if ($filter_due === 'overdue')  { $where[] = 'r.due_date < CURDATE() AND r.status NOT IN ("Filed","Not Applicable")'; }
if ($filter_due === '15d')      { $where[] = 'r.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 15 DAY) AND r.status NOT IN ("Filed","Not Applicable")'; }
if ($filter_due === '30d')      { $where[] = 'r.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) AND r.status NOT IN ("Filed","Not Applicable")'; }
$page = max(1, intval($_GET['page'] ?? 1));
$per_page = 30;

$where = ['1=1']; $wparams = [];
if ($filter_fy)     { $where[] = 'r.financial_year = ?'; $wparams[] = $filter_fy; }
if ($filter_form)   { $where[] = 'r.form_type = ?'; $wparams[] = $filter_form; }
if ($filter_status) { $where[] = 'r.status = ?'; $wparams[] = $filter_status; }
if ($filter_client) { $where[] = 'r.client_id = ?'; $wparams[] = $filter_client; }
if ($filter_due === 'overdue')  { $where[] = 'r.due_date < CURDATE() AND r.status NOT IN ("Filed","Not Applicable")'; }
if ($filter_due === '15d')      { $where[] = 'r.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 15 DAY) AND r.status NOT IN ("Filed","Not Applicable")'; }
if ($filter_due === '30d')      { $where[] = 'r.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY) AND r.status NOT IN ("Filed","Not Applicable")'; }
if ($_SESSION['role'] === 'supervisor') { $where[] = 'c.supervisor_id = ?'; $wparams[] = $_SESSION['user_id']; }
if ($_SESSION['role'] === 'staff')      { $where[] = 'r.assigned_to = ?'; $wparams[] = $_SESSION['user_id']; }
$whereStr = implode(' AND ', $where);

$stmt = $db->prepare("SELECT COUNT(*) FROM roc_compliances r JOIN clients c ON c.id = r.client_id WHERE $whereStr");
$stmt->execute($wparams); $total = $stmt->fetchColumn();
$pg = paginate($total, $per_page, $page);

$stmt = $db->prepare("SELECT r.*, c.client_name, c.pan, c.cin, p.name as partner_name, s.name as supervisor_name, u.name as assigned_name, wp.name as prep_name, wr.name as rev_name
    FROM roc_compliances r
    JOIN clients c ON c.id = r.client_id
    LEFT JOIN users p ON p.id = c.partner_id
    LEFT JOIN users s ON s.id = c.supervisor_id
    LEFT JOIN users u ON u.id = r.assigned_to
    LEFT JOIN users wp ON wp.id = r.prepared_by
    LEFT JOIN users wr ON wr.id = r.reviewed_by
    WHERE $whereStr ORDER BY r.due_date ASC, c.client_name ASC LIMIT ? OFFSET ?");
$stmt->execute(array_merge($wparams, [$per_page, $pg['offset']]));
$entries = $stmt->fetchAll();

$roc_clients = $db->query("SELECT id, client_name, pan, cin, group_id FROM clients WHERE roc_applicable = 1 AND status = 'Active' ORDER BY client_name")->fetchAll();
$client_groups = $db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$all_users   = $db->query("SELECT id, name FROM users WHERE is_active = 1 ORDER BY name")->fetchAll();
$fy_list     = getFYList();

include 'includes/header.php';
?>

<?php if ($action === 'bulk_create'): ?>
<div class="page-header">
  <div class="page-title">🏢 ROC Register — Bulk Create</div>
  <a href="<?= url('roc_register.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card">
<div class="card-header"><span class="card-title">Generate ROC compliance entries for selected clients</span></div>
<div class="card-body">
<form method="post" action="<?= url('roc_register.php?action=bulk_create') ?>">
  <div class="form-grid form-grid-3">
    <div class="form-group">
      <label>Financial Year <span class="req">*</span></label>
      <select class="form-control" name="financial_year" required>
        <?php foreach ($fy_list as $fy): ?>
          <option value="<?= $fy ?>" <?= $fy === currentFY() ? 'selected' : '' ?>><?= $fy ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group" style="grid-column:span 2;">
      <label>Select Forms to Create <small class="text-muted">(hold Ctrl for multiple)</small></label>
      <select class="form-control" name="forms[]" multiple required style="height:160px;">
        <?php foreach ($roc_forms as $fv => $fd): ?>
          <option value="<?= $fv ?>" selected><?= $fv ?> — <?= $fd[0] ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group" style="grid-column:span 3;">
      <label>Select Clients <small class="text-muted">(hold Ctrl for multiple, or Ctrl+A for all)</small></label>
      <div class="d-flex gap-1 mb-1" style="align-items:flex-end">
        <div class="form-group" style="margin:0;flex:1">
          <label style="font-size:11px">Filter by Group</label>
          <select class="form-control" id="bulk_group_filter" onchange="filterClientsByGroup('bulk_group_filter','roc_bulk_client_ids')">
            <option value="">— All Groups —</option>
            <?php foreach ($client_groups as $g): ?>
              <option value="<?= $g['id'] ?>"><?= htmlspecialchars($g['group_name']) ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <button type="button" class="btn btn-outline btn-sm" onclick="selectAllVisibleClients('roc_bulk_client_ids');updateClientSelectionCount('roc_bulk_client_ids','roc_bulk_sel_count')">Select All Visible</button>
        <button type="button" class="btn btn-outline btn-sm" onclick="selectNoneClients('roc_bulk_client_ids');updateClientSelectionCount('roc_bulk_client_ids','roc_bulk_sel_count')">Clear</button>
        <span id="roc_bulk_sel_count" class="text-muted" style="font-size:12px;white-space:nowrap">0 selected</span>
      </div>
      <select class="form-control" name="client_ids[]" id="roc_bulk_client_ids" multiple required style="height:200px;"
              onchange="updateClientSelectionCount('roc_bulk_client_ids','roc_bulk_sel_count')">
        <?php foreach ($roc_clients as $c): ?>
          <option value="<?= $c['id'] ?>" data-group="<?= $c['group_id'] ?? '' ?>" selected><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)<?= $c['cin'] ? ' — '.$c['cin'] : '' ?></option>
        <?php endforeach; ?>
      </select>
    </div>
  </div>
  <div class="form-actions">
    <button class="btn btn-primary" type="submit">⚡ Generate Entries</button>
    <a href="<?= url('roc_register.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>

<?php elseif ($action === 'add' || $action === 'edit'): ?>
<div class="page-header">
  <div class="page-title"><?= $action === 'edit' ? '✏️ Edit ROC Entry' : '➕ Add ROC Entry' ?></div>
  <a href="<?= url('roc_register.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card">
<div class="card-body">
<form method="post" action="">
  <div class="form-section">
    <div class="form-section-title">Compliance Details</div>
    <div class="form-grid form-grid-4">
      <div class="form-group" style="grid-column:span 2;">
        <label>Client <span class="req">*</span></label>
        <select class="form-control" name="client_id" required>
          <option value="">-- Select Client --</option>
          <?php foreach ($roc_clients as $c): ?>
            <option value="<?= $c['id'] ?>" <?= ($entry['client_id'] ?? 0) == $c['id'] ? 'selected' : '' ?>><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)<?= $c['cin'] ? ' — '.$c['cin'] : '' ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Financial Year <span class="req">*</span></label>
        <select class="form-control" name="financial_year" required>
          <?php foreach ($fy_list as $fy): ?>
            <option value="<?= $fy ?>" <?= ($entry['financial_year'] ?? currentFY()) === $fy ? 'selected' : '' ?>><?= $fy ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Form Type <span class="req">*</span></label>
        <select class="form-control" name="form_type" id="form_type" required onchange="setFormDesc(this.value)">
          <option value="">Select Form</option>
          <?php foreach ($roc_forms as $fv => $fd): ?>
            <option value="<?= $fv ?>" <?= ($entry['form_type'] ?? '') === $fv ? 'selected' : '' ?>><?= $fv ?> — <?= $fd[0] ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group" style="grid-column:span 2;">
        <label>Form Description</label>
        <input class="form-control" name="form_description" id="form_description" value="<?= htmlspecialchars($entry['form_description'] ?? '') ?>">
      </div>
      <div class="form-group">
        <label>Due Date <span class="req">*</span></label>
        <input class="form-control" type="date" name="due_date" id="roc_due_date" value="<?= $entry['due_date'] ?? '' ?>">
      </div>
      <div class="form-group" style="grid-column:span 2;">
        <label>Due Date Basis</label>
        <input class="form-control" name="due_date_basis" id="due_date_basis" value="<?= htmlspecialchars($entry['due_date_basis'] ?? '') ?>" placeholder="e.g. 60 days from AGM">
      </div>
      <div class="form-group">
        <label>Status</label>
        <select class="form-control" name="status">
          <?php foreach (['Not Started','Documents Pending','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
            <option value="<?= $s ?>" <?= ($entry['status'] ?? 'Not Started') === $s ? 'selected' : '' ?>><?= $s ?></option>
          <?php endforeach; ?>
        </select>
      </div>
    </div>
  </div>

  <div class="form-section">
    <div class="form-section-title">Preparation & Filing</div>
    <div class="form-grid form-grid-4">
      <div class="form-group">
        <label>Documents Received</label>
        <input class="form-control" type="date" name="documents_received_date" value="<?= $entry['documents_received_date'] ?? '' ?>">
      </div>
      <div class="form-group">
        <label>Prepared By</label>
        <select class="form-control" name="prepared_by">
          <option value="">Select</option>
          <?php foreach ($all_users as $u): ?>
            <option value="<?= $u['id'] ?>" <?= ($entry['prepared_by'] ?? '') == $u['id'] ? 'selected' : '' ?>><?= htmlspecialchars($u['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Prepared Date</label>
        <input class="form-control" type="date" name="prepared_date" value="<?= $entry['prepared_date'] ?? '' ?>">
      </div>
      <div class="form-group">
        <label>Reviewed By</label>
        <select class="form-control" name="reviewed_by">
          <option value="">Select</option>
          <?php foreach ($all_users as $u): ?>
            <option value="<?= $u['id'] ?>" <?= ($entry['reviewed_by'] ?? '') == $u['id'] ? 'selected' : '' ?>><?= htmlspecialchars($u['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Reviewed Date</label>
        <input class="form-control" type="date" name="reviewed_date" value="<?= $entry['reviewed_date'] ?? '' ?>">
      </div>
      <div class="form-group">
        <label>Filed Date</label>
        <input class="form-control" type="date" name="filed_date" value="<?= $entry['filed_date'] ?? '' ?>">
      </div>
      <div class="form-group">
        <label>SRN (Service Request No.)</label>
        <input class="form-control" name="srn" data-uppercase value="<?= htmlspecialchars($entry['srn'] ?? '') ?>">
      </div>
      <div class="form-group">
        <label>MCA Challan Amount (₹)</label>
        <input class="form-control" type="number" step="0.01" name="challan_amount" value="<?= $entry['challan_amount'] ?? 0 ?>">
      </div>
      <div class="form-group">
        <label>Late Fee (₹)</label>
        <input class="form-control" type="number" step="0.01" name="late_fee" value="<?= $entry['late_fee'] ?? 0 ?>">
      </div>
      <div class="form-group">
        <label>Assigned To</label>
        <select class="form-control" name="assigned_to">
          <option value="">Select</option>
          <?php foreach ($all_users as $u): ?>
            <option value="<?= $u['id'] ?>" <?= ($entry['assigned_to'] ?? '') == $u['id'] ? 'selected' : '' ?>><?= htmlspecialchars($u['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group" style="grid-column:span 4;">
        <label>Remarks</label>
        <textarea class="form-control" name="remarks" rows="2"><?= htmlspecialchars($entry['remarks'] ?? '') ?></textarea>
      </div>
    </div>
  </div>
  <div class="form-actions">
    <button class="btn btn-primary" type="submit">💾 Save Entry</button>
    <a href="<?= url('roc_register.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>
<script>
const rocForms = <?= json_encode(array_map(fn($v) => ['desc' => $v[0], 'basis' => $v[1]], $roc_forms)) ?>;
function setFormDesc(val) {
  if (rocForms[val]) {
    document.getElementById('form_description').value = rocForms[val].desc;
    document.getElementById('due_date_basis').value    = rocForms[val].basis;
  }
}
</script>

<?php else: // LIST ?>
<div class="page-header">
  <div>
    <div class="page-title">🏢 ROC Compliance Register</div>
    <div class="page-subtitle">Total: <?= $total ?> entries</div>
  </div>
  <div class="d-flex gap-1">
    <?php if (hasRole(['admin','partner','supervisor'])): ?>
    <a href="<?= url('roc_register.php?action=bulk_create') ?>" class="btn btn-outline">⚡ Bulk Create</a>
    <?php endif; ?>
    <a href="<?= url('roc_register.php?action=add') ?>" class="btn btn-primary">+ Add Entry</a>
  </div>
</div>

<div class="filters-bar">
  <form method="get" style="display:contents;">
    <div class="filter-group">
      <label>FY</label>
      <select name="fy">
        <?php foreach ($fy_list as $fy): ?>
          <option value="<?= $fy ?>" <?= $filter_fy === $fy ? 'selected' : '' ?>><?= $fy ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Form Type</label>
      <select name="form_type">
        <option value="">All Forms</option>
        <?php foreach (array_keys($roc_forms) as $fv): ?>
          <option value="<?= $fv ?>" <?= $filter_form === $fv ? 'selected' : '' ?>><?= $fv ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Status</label>
      <select name="status">
        <option value="">All</option>
        <?php foreach (['Not Started','Documents Pending','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
          <option value="<?= $s ?>" <?= $filter_status === $s ? 'selected' : '' ?>><?= $s ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Due</label>
      <select name="due">
        <option value="">All</option>
        <option value="overdue" <?= $filter_due === 'overdue' ? 'selected' : '' ?>>Overdue</option>
        <option value="15d"     <?= $filter_due === '15d' ? 'selected' : '' ?>>Due in 15d</option>
        <option value="30d"     <?= $filter_due === '30d' ? 'selected' : '' ?>>Due in 30d</option>
      </select>
    </div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('roc_register.php') ?>" class="btn btn-outline">Reset</a>
      <button class="btn btn-export" type="button" onclick="exportTableToXLS('roc-table','ROC_Register_<?= $filter_fy ?>')">⬇ Export Excel</button>
    </div>
  </form>
</div>

<div class="card">
<div class="table-responsive">
<table class="data-table" id="roc-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Client</th>
      <th>CIN</th>
      <th>FY</th>
      <th>Form</th>
      <th>Description</th>
      <th>Due Date</th>
      <th>Due Basis</th>
      <th>Docs Recd</th>
      <th>Prepared By</th>
      <th>Reviewed By</th>
      <th>Filed Date</th>
      <th>SRN</th>
      <th>Challan (₹)</th>
      <th>Late Fee (₹)</th>
      <th>Assigned</th>
      <th>Status</th>
      <th class="no-export">Actions</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($entries as $i => $r): $days = daysUntil($r['due_date']); ?>
    <tr class="<?= !in_array($r['status'],['Filed','Not Applicable']) && $days !== null && $days < 0 ? 'row-overdue' : (!in_array($r['status'],['Filed','Not Applicable']) && $days !== null && $days <= 15 ? 'row-due-soon' : '') ?>">
      <td><?= $pg['offset'] + $i + 1 ?></td>
      <td>
        <strong style="font-size:12px;"><?= htmlspecialchars($r['client_name']) ?></strong><br>
        <span class="text-muted" style="font-size:11px;"><?= htmlspecialchars($r['pan']) ?></span>
      </td>
      <td style="font-size:11px;"><code><?= htmlspecialchars($r['cin'] ?: '-') ?></code></td>
      <td><?= htmlspecialchars($r['financial_year']) ?></td>
      <td><span class="badge badge-primary"><?= htmlspecialchars($r['form_type']) ?></span></td>
      <td style="font-size:12px;"><?= htmlspecialchars($r['form_description'] ?? '') ?></td>
      <td><?= dueDateBadge($r['due_date']) ?></td>
      <td style="font-size:11px;color:var(--text-muted);"><?= htmlspecialchars($r['due_date_basis'] ?? '') ?></td>
      <td style="font-size:12px;"><?= $r['documents_received_date'] ? '<span class="badge badge-success">'.fmtDate($r['documents_received_date']).'</span>' : '<span class="badge badge-secondary">Pending</span>' ?></td>
      <td style="font-size:12px;"><?= htmlspecialchars($r['prep_name'] ?? '-') ?></td>
      <td style="font-size:12px;"><?= htmlspecialchars($r['rev_name'] ?? '-') ?></td>
      <td style="font-size:12px;"><?= $r['filed_date'] ? '<span class="badge badge-success">'.fmtDate($r['filed_date']).'</span>' : '-' ?></td>
      <td style="font-size:11px;"><code><?= htmlspecialchars($r['srn'] ?: '-') ?></code></td>
      <td class="text-right"><?= $r['challan_amount'] > 0 ? '₹'.number_format($r['challan_amount'],0) : '-' ?></td>
      <td><?= $r['late_fee'] > 0 ? '<span class="badge badge-danger">₹'.number_format($r['late_fee'],0).'</span>' : '-' ?></td>
      <td style="font-size:12px;"><?= htmlspecialchars($r['assigned_name'] ?? '-') ?></td>
      <td>
        <select class="status-select" data-id="<?= $r['id'] ?>" data-module="roc_compliances" style="font-size:11px;height:24px;padding:0 4px;border:1px solid #d1d8e0;border-radius:4px;min-width:130px;">
          <?php foreach (['Not Started','Documents Pending','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
            <option value="<?= $s ?>" <?= $r['status'] === $s ? 'selected' : '' ?>><?= $s ?></option>
          <?php endforeach; ?>
        </select>
      </td>
      <td class="no-export">
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
          <a href="<?= url('roc_register.php?action=edit&id=') . $r['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
          <a href="<?= url('roc_register.php?action=delete&id=') . $r['id'] ?>"
             class="btn btn-danger btn-sm"
             onclick="return confirm('Delete this ROC entry? Cannot be undone.')">Delete</a>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($entries)): ?>
    <tr><td colspan="18" class="text-center text-muted" style="padding:2rem;">No entries found.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div>
</div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i = 1; $i <= min($pg['total_pages'],20); $i++): ?>
    <a href="?fy=<?= urlencode($filter_fy) ?>&form_type=<?= urlencode($filter_form) ?>&status=<?= urlencode($filter_status) ?>&page=<?= $i ?>" class="page-link <?= $i === $page ? 'active' : '' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($entries) ?> of <?= $total ?></span>
</div>
<?php endif; ?>

<?php endif; ?>
<?php include 'includes/footer.php'; ?>
