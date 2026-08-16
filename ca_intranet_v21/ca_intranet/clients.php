<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
$db = getDB();
$page_title = 'Client Master';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);

// GSTIN → State lookup (first 2 digits)
function gstinToState($gstin) {
    $map = [
        '01'=>'Jammu & Kashmir','02'=>'Himachal Pradesh','03'=>'Punjab','04'=>'Chandigarh',
        '05'=>'Uttarakhand','06'=>'Haryana','07'=>'Delhi','08'=>'Rajasthan','09'=>'Uttar Pradesh',
        '10'=>'Bihar','11'=>'Sikkim','12'=>'Arunachal Pradesh','13'=>'Nagaland','14'=>'Manipur',
        '15'=>'Mizoram','16'=>'Tripura','17'=>'Meghalaya','18'=>'Assam','19'=>'West Bengal',
        '20'=>'Jharkhand','21'=>'Odisha','22'=>'Chhattisgarh','23'=>'Madhya Pradesh',
        '24'=>'Gujarat','26'=>'Dadra & Nagar Haveli / Daman & Diu','27'=>'Maharashtra',
        '28'=>'Andhra Pradesh','29'=>'Karnataka','30'=>'Goa','31'=>'Lakshadweep',
        '32'=>'Kerala','33'=>'Tamil Nadu','34'=>'Puducherry','35'=>'Andaman & Nicobar Islands',
        '36'=>'Telangana','37'=>'Andhra Pradesh (new)','38'=>'Ladakh','97'=>'Other Territory',
        '99'=>'Centre Jurisdiction',
    ];
    $code = substr(trim($gstin), 0, 2);
    return $map[$code] ?? '';
}

// ── DEACTIVATE / REACTIVATE / DELETE ─────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['post_action']) && hasRole(['admin','partner'])) {
    $pa     = $_POST['post_action'];
    $cid    = intval($_POST['client_id'] ?? 0);
    $reason = trim($_POST['action_reason'] ?? '');

    if ($pa === 'deactivate' && $cid) {
        $note = $reason ?: 'No reason provided';
        $db->prepare("UPDATE clients SET status='Inactive', notes=CONCAT(IFNULL(notes,''), ' | DEACTIVATED: ', ?) WHERE id=?")
           ->execute([$note . ' [' . date('d-M-Y') . ' by ' . ($_SESSION['name']??'') . ']', $cid]);
        auditLog('clients', $cid, 'UPDATE', ['status'=>'Active'], ['status'=>'Inactive','reason'=>$note]);
        $_SESSION['flash_msg'] = 'Client deactivated. Reason: ' . $note;
        $_SESSION['flash_type'] = 'warning';
        header('Location: '.url('clients.php')); exit;
    }

    if ($pa === 'reactivate' && $cid) {
        $note = $reason ?: 'No reason provided';
        $db->prepare("UPDATE clients SET status='Active', notes=CONCAT(IFNULL(notes,''), ' | REACTIVATED: ', ?) WHERE id=?")
           ->execute([$note . ' [' . date('d-M-Y') . ' by ' . ($_SESSION['name']??'') . ']', $cid]);
        auditLog('clients', $cid, 'UPDATE', ['status'=>'Inactive'], ['status'=>'Active','reason'=>$note]);
        $_SESSION['flash_msg'] = 'Client reactivated. Reason: ' . $note;
        $_SESSION['flash_type'] = 'success';
        header('Location: '.url('clients.php')); exit;
    }

    if ($pa === 'delete' && $cid) {
        $note = $reason ?: 'No reason provided';
        // Fetch name for log before deleting
        $nm = $db->prepare("SELECT client_name, pan FROM clients WHERE id=?");
        $nm->execute([$cid]); $nm = $nm->fetch();
        $db->prepare("DELETE FROM clients WHERE id=?")->execute([$cid]);
        auditLog('clients', $cid, 'DELETE', $nm, ['reason'=>$note]);
        $_SESSION['flash_msg'] = 'Client ' . ($nm['client_name']??'') . ' permanently deleted. Reason: ' . $note;
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('clients.php')); exit;
    }
}

// ── BULK ASSIGN PARTNER / SUPERVISOR ─────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST'
    && isset($_POST['post_action'])
    && $_POST['post_action'] === 'bulk_assign'
    && hasRole(['admin','partner'])) {

    $client_ids  = $_POST['bulk_ids'] ?? [];
    $new_partner = $_POST['bulk_partner_id'] ?: null;
    $new_sup     = $_POST['bulk_supervisor_id'] ?: null;
    $reason      = trim($_POST['bulk_reason'] ?? '');

    if (empty($client_ids)) {
        $_SESSION['flash_msg']  = 'No clients selected.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('clients.php')); exit;
    }

    $updated = 0;
    $sets = []; $vals = [];
    if ($new_partner !== null) { $sets[] = 'partner_id=?';    $vals[] = $new_partner ?: null; }
    if ($new_sup     !== null) { $sets[] = 'supervisor_id=?'; $vals[] = $new_sup ?: null; }

    if (!empty($sets)) {
        // Append reason to notes
        $note_suffix = ' | Assignment changed: '.($reason ?: 'Bulk update').' ['.date('d-M-Y').' by '.($_SESSION['name']??'').']';
        $sets[]  = "notes = CONCAT(IFNULL(notes,''), ?)";
        $vals[]  = $note_suffix;

        foreach ($client_ids as $cid) {
            $cid = intval($cid);
            if (!$cid) continue;
            $v = $vals;
            $v[] = $cid;
            $db->prepare("UPDATE clients SET ".implode(', ', $sets)." WHERE id=?")->execute($v);
            auditLog('clients', $cid, 'UPDATE', null,
                ['partner_id'=>$new_partner, 'supervisor_id'=>$new_sup, 'reason'=>$reason]);
            $updated++;
        }
        $_SESSION['flash_msg']  = "$updated client(s) updated successfully.";
        $_SESSION['flash_type'] = 'success';
    } else {
        $_SESSION['flash_msg']  = 'Please select at least one field to update (Partner or Supervisor).';
        $_SESSION['flash_type'] = 'error';
    }
    header('Location: '.url('clients.php')); exit;
}

// ── BULK MARK ITR APPLICABLE ──────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST'
    && isset($_POST['post_action'])
    && $_POST['post_action'] === 'bulk_itr_mark'
    && hasRole(['admin','partner'])) {

    $client_ids  = array_filter(array_map('intval', $_POST['bulk_ids'] ?? []));
    $itr_flag    = intval($_POST['bulk_itr_flag'] ?? 1);   // 1=applicable, 0=not applicable
    $itr_fy      = trim($_POST['bulk_itr_fy'] ?? '');
    $itr_due     = trim($_POST['bulk_itr_due_date'] ?? '');

    if (empty($client_ids)) {
        $_SESSION['flash_msg']  = 'No clients selected.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('clients.php')); exit;
    }

    $updated = 0;
    foreach ($client_ids as $cid) {
        $db->prepare("UPDATE clients SET itr_applicable=? WHERE id=?")->execute([$itr_flag, $cid]);
        auditLog('clients', $cid, 'UPDATE', null, ['itr_applicable' => $itr_flag, 'bulk_fy' => $itr_fy]);
        $updated++;
    }

    // If a FY was specified, also create ITR register entries for these clients (if not already there)
    $entries_created = 0;
    if ($itr_flag && $itr_fy) {
        foreach ($client_ids as $cid) {
            $chk = $db->prepare("SELECT id FROM itr_returns WHERE client_id=? AND financial_year=?");
            $chk->execute([$cid, $itr_fy]);
            if ($chk->fetch()) continue;
            // Get client's partner_id and group_id
            $cl = $db->prepare("SELECT partner_id, group_id FROM clients WHERE id=?");
            $cl->execute([$cid]); $cl = $cl->fetch();
            $db->prepare(
                "INSERT INTO itr_returns (client_id,financial_year,ca_partner_id,group_id,
                  accounting_status,itr_prepared_status,itr_uploaded_status,e_verified,bank_validated,created_by)
                 VALUES (?,?,?,?,'WIP','No','WIP','Pending','No',?)"
            )->execute([$cid, $itr_fy, $cl['partner_id'] ?? null, $cl['group_id'] ?? null, $_SESSION['user_id']]);
            $entries_created++;
        }
    }

    $msg = "$updated clients marked as ITR " . ($itr_flag ? 'Applicable' : 'Not Applicable') . '.';
    if ($entries_created) $msg .= " $entries_created ITR register entries created for FY $itr_fy.";
    $_SESSION['flash_msg']  = $msg;
    $_SESSION['flash_type'] = 'success';
    header('Location: '.url('clients.php')); exit;
}


if ($_SERVER['REQUEST_METHOD'] === 'POST' && hasRole(['admin','partner','supervisor'])) {
    $d = $_POST;
    $pan = strtoupper(trim($d['pan'] ?? ''));
    $constitution = getConstitutionFromPAN($pan) ?: ($d['constitution'] ?? 'Other');

    // Build contacts JSON
    $contacts = [];
    foreach (($d['c_name'] ?? []) as $ci => $cn) {
        if (trim($cn)) {
            $contacts[] = [
                'name'        => trim($cn),
                'mobile'      => trim($d['c_mobile'][$ci] ?? ''),
                'email'       => trim($d['c_email'][$ci] ?? ''),
                'designation' => trim($d['c_designation'][$ci] ?? ''),
            ];
        }
    }

    // Build GSTIN JSON — auto-detect state from GSTIN code
    $gstins_arr = [];
    foreach (($d['gstin_nos'] ?? []) as $gi => $gno) {
        $gno = strtoupper(trim($gno));
        if ($gno) {
            $state = gstinToState($gno);
            $gstins_arr[] = [
                'gstin'          => $gno,
                'state'          => $state,
                'return_type'    => $d['gstin_return_types'][$gi] ?? 'Monthly',
                'effective_from' => $d['gstin_effective_from'][$gi] ?? '',
            ];
        }
    }

    // TDS form types
    $tds_forms = !empty($d['tds_form_types']) ? json_encode($d['tds_form_types']) : null;

    // Auto-generate client code for new records
    $client_code = $id
        ? strtoupper(trim($d['client_code'] ?? ''))
        : generateClientCode($constitution);

    $data = [
        'client_code'          => $client_code,
        'client_name'          => trim($d['client_name'] ?? ''),
        'pan'                  => $pan,
        'constitution'         => $constitution,
        'constitution_subtype' => trim($d['constitution_subtype'] ?? '') ?: null,
        'contacts'             => $contacts ? json_encode($contacts) : null,
        'address'              => trim($d['address'] ?? '') ?: null,
        'gst_applicable'       => isset($d['gst_applicable']) ? 1 : 0,
        'gstin_list'           => $gstins_arr ? json_encode($gstins_arr) : null,
        'gst_return_type'      => $d['gst_return_type'] ?? 'Monthly',
        'tds_applicable'       => isset($d['tds_applicable']) ? 1 : 0,
        'tan'                  => strtoupper(trim($d['tan'] ?? '')),
        'tds_form_types'       => $tds_forms,
        // Income Tax
        'itr_applicable'       => isset($d['itr_applicable']) ? 1 : 0,
        'group_id'             => $d['group_id'] ?: null,
        'ptec_applicable'      => isset($d['ptec_applicable']) ? 1 : 0,
        'ptec_no'              => strtoupper(trim($d['ptec_no'] ?? '')),
        'ptrc_applicable'      => isset($d['ptrc_applicable']) ? 1 : 0,
        'ptrc_no'              => strtoupper(trim($d['ptrc_no'] ?? '')),
        'ptrc_periodicity'     => $d['ptrc_periodicity'] ?? 'Monthly',
        'roc_applicable'       => isset($d['roc_applicable']) ? 1 : 0,
        'cin'                  => strtoupper(trim($d['cin'] ?? '')),
        'din_list'             => trim($d['din_list'] ?? '') ?: null,
        'date_of_incorporation'=> $d['date_of_incorporation'] ?: null,
        'company_type'         => $d['company_type'] ?: null,
        'agm_date'             => $d['agm_date'] ?: null,
        'partner_id'           => $d['partner_id'] ?: null,
        'supervisor_id'        => $d['supervisor_id'] ?: null,
        'status'               => $d['status'] ?? 'Active',
        'notes'                => trim($d['notes'] ?? '') ?: null,
    ];

    try {
        if ($id) {
            $set = implode('=?, ', array_keys($data)) . '=?';
            $vals = array_values($data);
            $vals[] = $id;
            $db->prepare("UPDATE clients SET $set WHERE id=?")->execute($vals);
            auditLog('clients', $id, 'UPDATE', null, $data);
            $_SESSION['flash_msg'] = 'Client updated successfully.';
        } else {
            $cols = implode(', ', array_keys($data));
            $ph   = implode(', ', array_fill(0, count($data), '?'));
            $db->prepare("INSERT INTO clients ($cols) VALUES ($ph)")->execute(array_values($data));
            $nid  = $db->lastInsertId();
            auditLog('clients', $nid, 'CREATE', null, $data);
            $_SESSION['flash_msg'] = "Client added successfully. Code: $client_code";
        }
        $_SESSION['flash_type'] = 'success';
    } catch (Exception $e) {
        $_SESSION['flash_msg']  = 'Error saving client: ' . $e->getMessage();
        $_SESSION['flash_type'] = 'error';
    }
    header('Location: '.url('clients.php')); exit;
}

// ── FETCH FOR EDIT ─────────────────────────────────────────
$client = []; $contacts = []; $gstins = []; $tds_forms = [];
if (in_array($action, ['edit','view']) && $id) {
    $stmt = $db->prepare("SELECT * FROM clients WHERE id=?");
    $stmt->execute([$id]);
    $client = $stmt->fetch() ?: [];
    if ($client) {
        $contacts   = $client['contacts']      ? json_decode($client['contacts'], true)      : [];
        $gstins     = $client['gstin_list']     ? json_decode($client['gstin_list'], true)    : [];
        $tds_forms  = $client['tds_form_types'] ? json_decode($client['tds_form_types'], true): [];
    }
}
if (empty($contacts)) $contacts = [['name'=>'','mobile'=>'','email'=>'','designation'=>'']];
if (empty($gstins))   $gstins   = [['gstin'=>'','state'=>'','return_type'=>'Monthly','effective_from'=>'']];

// ── LIST DATA ─────────────────────────────────────────────
$search   = trim($_GET['search'] ?? '');
$fsup     = intval($_GET['supervisor_id'] ?? 0);
$fstatus  = $_GET['status'] ?? 'Active';
$show_all = isset($_GET['show_all']); // show all on one page
$page     = max(1, intval($_GET['page'] ?? 1));
$per      = $show_all ? 9999 : intval($_GET['per'] ?? 25);
if (!in_array($per, [25, 50, 100, 250])) $per = 25;

$where = ['1=1']; $wp = [];
if ($search) {
    $where[] = '(c.client_name LIKE ? OR c.pan LIKE ? OR c.client_code LIKE ?)';
    $s = "%$search%"; $wp = [$s, $s, $s];
}
if ($fsup)    { $where[] = 'c.supervisor_id=?'; $wp[] = $fsup; }
if ($fstatus) { $where[] = 'c.status=?';         $wp[] = $fstatus; }
if ($_SESSION['role'] === 'supervisor') { $where[] = 'c.supervisor_id=?'; $wp[] = $_SESSION['user_id']; }
$ws = implode(' AND ', $where);

$total = $db->prepare("SELECT COUNT(*) FROM clients c WHERE $ws");
$total->execute($wp); $total = $total->fetchColumn();
$pg = paginate($total, $per, $page);

$rows = $db->prepare(
    "SELECT c.*, p.name pname, s.name sname
     FROM clients c
     LEFT JOIN users p ON p.id=c.partner_id
     LEFT JOIN users s ON s.id=c.supervisor_id
     WHERE $ws ORDER BY c.client_name LIMIT ? OFFSET ?"
);
$rows->execute(array_merge($wp, [$per, $pg['offset']]));
$clients = $rows->fetchAll();

// ── EXPORT CURRENT LIST AS EDITABLE XLS ──────────────────
if (isset($_GET['export_edit'])) {
    require_once __DIR__.'/includes/export.php';
    $all_rows = $db->prepare(
        "SELECT c.*, p.name pname, p.username pusername,
                s.name sname, s.username susername
         FROM clients c
         LEFT JOIN users p ON p.id=c.partner_id
         LEFT JOIN users s ON s.id=c.supervisor_id
         WHERE $ws ORDER BY c.client_name"
    );
    $all_rows->execute($wp);
    $export_clients = $all_rows->fetchAll();

    startCSVDownload('Clients_Export_'.date('d-M-Y'));
    $out = fopen('php://output','w');
    writeCSVRow($out, [
        'client_name','pan','address',
        'contact_name','contact_mobile','contact_email','contact_designation',
        'gst_applicable','gstin','gst_return_type',
        'tds_applicable','tan',
        'ptec_no','ptrc_no','ptrc_periodicity',
        'partner_username','supervisor_username','notes',
        '__client_code (read only)','__constitution (read only)','__status (read only)',
    ]);
    foreach ($export_clients as $c) {
        $ct = $c['contacts']   ? json_decode($c['contacts'], true)  : [];
        $ct = $ct[0] ?? [];
        $gl = $c['gstin_list'] ? json_decode($c['gstin_list'], true) : [];
        $g0 = $gl[0] ?? [];
        writeCSVRow($out, [
            $c['client_name'],
            $c['pan'],
            $c['address']      ?? '',
            $ct['name']        ?? '',
            $ct['mobile']      ?? '',
            $ct['email']       ?? '',
            $ct['designation'] ?? '',
            $c['gst_applicable'] ? 'YES' : '',
            $g0['gstin']       ?? '',
            $g0['return_type'] ?? ($c['gst_return_type'] ?? ''),
            $c['tds_applicable'] ? 'YES' : '',
            $c['tan']          ?? '',
            $c['ptec_no']      ?? '',
            $c['ptrc_no']      ?? '',
            $c['ptrc_periodicity'] ?? 'Monthly',
            $c['pusername']    ?? '',
            $c['susername']    ?? '',
            $c['notes']        ?? '',
            $c['client_code'],
            $c['constitution'],
            $c['status'],
        ]);
    }
    fclose($out);
    exit;
}

// Dropdowns
$partners    = $db->query("SELECT id,name FROM users WHERE role IN('partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
$supervisors = $db->query("SELECT id,name FROM users WHERE role IN('supervisor','partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
$tds_types   = $db->query("SELECT * FROM tds_return_types WHERE is_active=1 ORDER BY sort_order")->fetchAll();
$client_groups = $db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$fy_list     = getFYList();
$dp          = defaultPeriod('itr');

include 'includes/header.php';
?>

<?php if ($action === 'list'): ?>
<!-- ═══════════════════════════════ LIST VIEW ═══════════════════════════════ -->
<div class="page-header">
  <div>
    <div class="page-title">👥 Client Master</div>
    <div class="page-subtitle">
      Total: <?= $total ?> clients
      &nbsp;|&nbsp; Showing: <?= $show_all ? 'All' : $per.' per page' ?>
    </div>
  </div>
  <div class="d-flex gap-1" style="flex-wrap:wrap">
    <?php if (hasRole(['admin','partner'])): ?>
    <!-- Export current filtered list for editing -->
    <?php
      $eq = http_build_query(array_filter([
        'export_edit'=>1,'search'=>$search,'supervisor_id'=>$fsup?:null,'status'=>$fstatus,
      ]));
    ?>
    <a href="<?= url('clients.php?'.$eq) ?>" class="btn btn-export" title="Export all filtered clients to Excel — edit and reimport to update">
      ⬇ Export for Editing
    </a>
    <a href="<?= url('import.php?type=clients_update') ?>" class="btn btn-outline" title="Reimport edited Excel to update client records">
      ⬆ Reimport / Update
    </a>
    <?php endif; ?>
    <a href="<?= url('import.php?type=clients') ?>" class="btn btn-outline">⬆ Import New</a>
    <?php if (hasRole(['admin','partner','supervisor'])): ?>
    <a href="<?= url('clients.php?action=add') ?>" class="btn btn-primary">+ Add Client</a>
    <?php endif; ?>
  </div>
</div>

<!-- Bulk action toolbar — shown only when rows are selected -->
<?php if (hasRole(['admin','partner'])): ?>
<div id="bulk-toolbar" style="display:none;background:var(--primary);color:#fff;padding:10px 16px;border-radius:8px;margin-bottom:10px;display:none;align-items:center;gap:12px;flex-wrap:wrap">
  <span style="font-weight:600;font-size:13px">
    <span id="bulk-count">0</span> clients selected
  </span>
  <button class="btn btn-sm" style="background:rgba(255,255,255,.2);color:#fff;border-color:rgba(255,255,255,.3)"
          onclick="openBulkModal()">
    👥 Bulk Assign Partner / Supervisor
  </button>
  <button class="btn btn-sm" style="background:rgba(255,255,255,.2);color:#fff;border-color:rgba(255,255,255,.3)"
          onclick="openBulkITRModal()">
    🧾 Mark ITR Applicable / Create Entries
  </button>
  <button class="btn btn-sm" style="background:rgba(255,255,255,.1);color:rgba(255,255,255,.8);border-color:rgba(255,255,255,.2);margin-left:auto"
          onclick="clearSelection()">
    ✕ Clear Selection
  </button>
</div>
<?php endif; ?>

<div class="filters-bar">
  <form method="get" style="display:contents">
    <div class="filter-group">
      <label>Search</label>
      <input type="text" name="search" value="<?= htmlspecialchars($search) ?>" placeholder="Name / PAN / Code" style="width:200px">
    </div>
    <div class="filter-group">
      <label>Supervisor</label>
      <select name="supervisor_id">
        <option value="">All</option>
        <?php foreach ($supervisors as $s): ?>
          <option value="<?= $s['id'] ?>" <?= $fsup==$s['id']?'selected':'' ?>><?= htmlspecialchars($s['name']) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Status</label>
      <select name="status">
        <option value=""        <?= $fstatus===''        ?'selected':'' ?>>All (incl. Inactive)</option>
        <option value="Active"   <?= $fstatus==='Active'  ?'selected':'' ?>>Active Only</option>
        <option value="Inactive" <?= $fstatus==='Inactive'?'selected':'' ?>>Inactive Only</option>
      </select>
    </div>
    <div class="filter-group">
      <label>Per Page</label>
      <select name="per" onchange="this.form.submit()">
        <?php foreach ([25,50,100,250] as $pp): ?>
          <option value="<?= $pp ?>" <?= (!$show_all && $per==$pp)?'selected':'' ?>><?= $pp ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('clients.php') ?>" class="btn btn-outline">Reset</a>
      <?php
        $all_url_params = http_build_query(array_filter([
          'show_all'=>1,'search'=>$search,'supervisor_id'=>$fsup?:null,'status'=>$fstatus,
        ]));
      ?>
      <?php if (!$show_all): ?>
        <a href="<?= url('clients.php?'.$all_url_params) ?>"
           class="btn btn-outline" title="Show all <?= $total ?> clients on one page">
          Show All (<?= $total ?>)
        </a>
      <?php else: ?>
        <a href="<?= url('clients.php?search='.urlencode($search).'&supervisor_id='.$fsup.'&status='.urlencode($fstatus)) ?>"
           class="btn btn-outline">← Back to Pages</a>
      <?php endif; ?>
      <button class="btn btn-export" type="button" onclick="exportTableToXLS('clients-table','client_master')">⬇ Export XLS</button>
    </div>
  </form>
</div>

<div class="card">
  <div style="display:flex;justify-content:flex-end;align-items:center;padding:8px 14px;border-bottom:1px solid var(--border-lt);gap:8px">
    <span style="font-size:12px;color:var(--text-muted)"><?= $total ?> clients</span>
    <button type="button" class="btn btn-outline btn-sm" onclick="toggleColumnPanel()" title="Choose which columns to show">
      ⚙ Columns
    </button>
  </div>

  <!-- Column visibility panel (hidden by default) -->
  <div id="col-panel" style="display:none;padding:12px 14px;background:var(--primary-bg);border-bottom:1px solid var(--border-lt);flex-wrap:wrap;gap:8px">
    <span style="font-size:12px;font-weight:600;color:var(--text);margin-right:4px">Show / Hide Columns:</span>
    <?php
    $toggleable_cols = [
      'col-code'        => 'Code',
      'col-pan'         => 'PAN',
      'col-constitution'=> 'Constitution',
      'col-gstin'       => 'GSTIN & Return Type',
      'col-tan'         => 'TAN',
      'col-ptec'        => 'PTEC No.',
      'col-ptrc'        => 'PTRC No.',
      'col-cin'         => 'CIN',
      'col-supervisor'  => 'Supervisor',
    ];
    foreach ($toggleable_cols as $colId => $colLabel): ?>
      <label style="display:inline-flex;align-items:center;gap:5px;font-size:12px;cursor:pointer;background:#fff;padding:4px 10px;border-radius:6px;border:1px solid var(--border-lt)">
        <input type="checkbox" checked onchange="toggleColumn('<?= $colId ?>', this.checked)" style="cursor:pointer"> <?= $colLabel ?>
      </label>
    <?php endforeach; ?>
    <button type="button" class="btn btn-outline btn-sm" onclick="resetColumns()">Reset All</button>
  </div>

<div class="table-responsive">
<table class="data-table" id="clients-table">
  <thead>
    <tr>
      <th class="no-export" style="width:36px">
        <?php if (hasRole(['admin','partner'])): ?>
        <input type="checkbox" id="select-all" title="Select all on this page"
               onchange="toggleSelectAll(this)" style="cursor:pointer">
        <?php endif; ?>
      </th>
      <th class="col-code">Code</th>
      <th>Client Name</th>
      <th class="col-pan">PAN</th>
      <th class="col-constitution">Constitution</th>
      <th class="col-gstin">GSTIN(s) &amp; Return Type</th>
      <th class="col-tan">TAN</th>
      <th class="col-ptec">PTEC No.</th>
      <th class="col-ptrc">PTRC No.</th>
      <th class="col-cin">CIN</th>
      <th class="col-supervisor">Supervisor</th>
      <th>Status</th>
      <th class="no-export">Actions</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($clients as $c):
    // Safely decode GSTIN list — handle nulls and invalid JSON
    $gstins_data = [];
    if (!empty($c['gstin_list'])) {
        $decoded = json_decode($c['gstin_list'], true);
        if (is_array($decoded)) $gstins_data = $decoded;
    }
  ?>
    <tr style="<?= $c['status']==='Inactive' ? 'opacity:0.55;background:#f9f9f9' : '' ?>" data-id="<?= $c['id'] ?>">
      <td class="no-export">
        <?php if (hasRole(['admin','partner'])): ?>
        <input type="checkbox" class="row-checkbox" value="<?= $c['id'] ?>"
               onchange="updateBulkToolbar()" style="cursor:pointer">
        <?php endif; ?>
      </td>
      <td class="col-code"><code style="font-size:11px"><?= htmlspecialchars($c['client_code']) ?></code></td>
      <td>
        <strong><?= htmlspecialchars($c['client_name']) ?></strong>
        <?php if ($c['partner_id']): ?>
          <br><span class="text-muted" style="font-size:10px">Partner: <?= htmlspecialchars($c['pname'] ?? '') ?></span>
        <?php endif; ?>
      </td>
      <td class="col-pan"><code style="font-weight:600"><?= htmlspecialchars($c['pan']) ?></code></td>
      <td class="col-constitution">
        <span class="col-constitution-inner" style="font-size:12px"><?= htmlspecialchars($c['constitution']) ?></span>
        <?php if ($c['constitution_subtype']): ?>
          <br><span class="text-muted" style="font-size:10px"><?= htmlspecialchars($c['constitution_subtype']) ?></span>
        <?php endif; ?>
      </td>

      <!-- GSTIN column — each GSTIN on its own line -->
      <td class="col-gstin" style="min-width:180px">
        <?php if (!empty($gstins_data)): ?>
          <?php foreach ($gstins_data as $gi => $gd): ?>
            <?php $gno = trim($gd['gstin'] ?? ''); if (!$gno) continue; ?>
            <div style="<?= $gi > 0 ? 'margin-top:6px;padding-top:6px;border-top:1px dashed var(--border-lt)' : '' ?>">
              <code style="font-size:11px;font-weight:700;color:var(--primary-lt);letter-spacing:.3px"><?= htmlspecialchars($gno) ?></code>
              <div style="font-size:10px;color:var(--text-muted);margin-top:1px">
                <?= htmlspecialchars($gd['state'] ?? '') ?>
                <?php if (!empty($gd['return_type'])): ?>
                  &nbsp;<span class="badge badge-primary" style="font-size:9px;padding:1px 5px"><?= htmlspecialchars($gd['return_type']) ?></span>
                <?php endif; ?>
                <?php if (!empty($gd['effective_from'])): ?>
                  <span class="text-muted"> w.e.f. <?= htmlspecialchars($gd['effective_from']) ?></span>
                <?php endif; ?>
              </div>
            </div>
          <?php endforeach; ?>
          <?php if (empty(array_filter(array_column($gstins_data, 'gstin')))): ?>
            <?php if ($c['gst_applicable']): ?>
              <span class="text-muted" style="font-size:11px">GST ✓ — No GSTIN entered</span>
            <?php endif; ?>
          <?php endif; ?>
        <?php elseif ($c['gst_applicable']): ?>
          <span class="badge badge-warning" style="font-size:10px">GST — No GSTIN</span>
        <?php else: ?>
          <span class="text-muted">—</span>
        <?php endif; ?>
      </td>

      <!-- TAN -->
      <td class="col-tan">
        <?php if ($c['tan']): ?>
          <code style="font-size:11px;font-weight:600"><?= htmlspecialchars($c['tan']) ?></code>
        <?php else: ?>
          <span class="text-muted">—</span>
        <?php endif; ?>
      </td>

      <!-- PTEC No. -->
      <td class="col-ptec">
        <?php if ($c['ptec_applicable'] && $c['ptec_no']): ?>
          <code style="font-size:11px"><?= htmlspecialchars($c['ptec_no']) ?></code>
        <?php elseif ($c['ptec_applicable']): ?>
          <span class="badge badge-info" style="font-size:10px">PTEC</span>
        <?php else: ?>
          <span class="text-muted">—</span>
        <?php endif; ?>
      </td>

      <!-- PTRC No. -->
      <td class="col-ptrc">
        <?php if ($c['ptrc_applicable'] && $c['ptrc_no']): ?>
          <code style="font-size:11px"><?= htmlspecialchars($c['ptrc_no']) ?></code>
          <br><span class="text-muted" style="font-size:10px"><?= htmlspecialchars($c['ptrc_periodicity'] ?? 'Monthly') ?></span>
        <?php elseif ($c['ptrc_applicable']): ?>
          <span class="badge badge-warning" style="font-size:10px">PTRC</span>
        <?php else: ?>
          <span class="text-muted">—</span>
        <?php endif; ?>
      </td>

      <!-- CIN -->
      <td class="col-cin">
        <?php if ($c['cin']): ?>
          <code style="font-size:10px"><?= htmlspecialchars($c['cin']) ?></code>
        <?php else: ?>
          <span class="text-muted">—</span>
        <?php endif; ?>
      </td>

      <td class="col-supervisor" style="font-size:12px"><?= htmlspecialchars($c['sname'] ?? '—') ?></td>
      <td><?= $c['status']==='Active' ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-secondary">Inactive</span>' ?></td>
      <td class="no-export" style="white-space:nowrap">
        <a href="<?= url('clients.php?action=edit&id=') . $c['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
        <a href="<?= url('gst_register.php?client_id=') . $c['id'] ?>" class="btn btn-outline btn-sm">GST</a>
        <a href="<?= url('etds_register.php?client_id=') . $c['id'] ?>" class="btn btn-outline btn-sm">ETDS</a>
        <?php if (hasRole(['admin','partner'])): ?>
          <?php if ($c['status'] === 'Active'): ?>
            <button class="btn btn-sm" style="background:#fff3cd;color:#856404;border:1px solid #ffc107"
              onclick="openActionModal(<?= $c['id'] ?>, 'deactivate', '<?= htmlspecialchars(addslashes($c['client_name'])) ?>')">
              Deactivate
            </button>
          <?php else: ?>
            <button class="btn btn-success btn-sm"
              onclick="openActionModal(<?= $c['id'] ?>, 'reactivate', '<?= htmlspecialchars(addslashes($c['client_name'])) ?>')">
              Reactivate
            </button>
          <?php endif; ?>
          <button class="btn btn-danger btn-sm"
            onclick="openActionModal(<?= $c['id'] ?>, 'delete', '<?= htmlspecialchars(addslashes($c['client_name'])) ?>')">
            Delete
          </button>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($clients)): ?>
    <tr><td colspan="13" class="text-center text-muted" style="padding:2rem">No clients found.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div></div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i=1; $i<=$pg['total_pages']; $i++): ?>
    <a href="?page=<?= $i ?>&search=<?= urlencode($search) ?>&supervisor_id=<?= $fsup ?>&status=<?= urlencode($fstatus) ?>"
       class="page-link <?= $i===$page?'active':'' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($clients) ?> of <?= $total ?></span>
</div>
<?php endif; ?>

<!-- ── BULK ASSIGN MODAL ─────────────────────────────────── -->
<?php if (hasRole(['admin','partner'])): ?>
<form method="post" action="<?= url('clients.php') ?>" id="bulk-assign-form">
  <input type="hidden" name="post_action" value="bulk_assign">
  <div id="bulk-ids-container"><!-- checkboxes injected by JS --></div>

  <div class="modal-overlay" id="bulk-modal">
    <div class="modal-box" style="max-width:520px">
      <div class="modal-header" style="background:var(--primary);color:#fff;border-radius:10px 10px 0 0">
        <span class="modal-title" style="color:#fff">👥 Bulk Assign — Partner / Supervisor</span>
        <button class="modal-close" style="color:#fff" onclick="closeModal('bulk-modal')" type="button">×</button>
      </div>
      <div class="modal-body">
        <div id="bulk-modal-summary" style="background:var(--primary-bg);padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px"></div>

        <div style="background:#fff8f0;padding:12px;border-radius:6px;border:1px solid #fed7aa;margin-bottom:1rem;font-size:12px">
          <strong>ℹ️ How it works:</strong> Select a new Partner and/or Supervisor below.
          Leave a field blank to keep the existing value unchanged.
          All selected clients will be updated at once.
        </div>

        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label>New Partner <small class="text-muted">(leave blank = no change)</small></label>
            <select class="form-control" name="bulk_partner_id" id="bulk_partner_id">
              <option value="">— No Change —</option>
              <option value="0">Clear / Remove Partner</option>
              <?php foreach ($partners as $p): ?>
                <option value="<?= $p['id'] ?>"><?= htmlspecialchars($p['name']) ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <div class="form-group">
            <label>New Supervisor <small class="text-muted">(leave blank = no change)</small></label>
            <select class="form-control" name="bulk_supervisor_id" id="bulk_supervisor_id">
              <option value="">— No Change —</option>
              <option value="0">Clear / Remove Supervisor</option>
              <?php foreach ($supervisors as $s): ?>
                <option value="<?= $s['id'] ?>"><?= htmlspecialchars($s['name']) ?></option>
              <?php endforeach; ?>
            </select>
          </div>
          <div class="form-group" style="grid-column:span 2">
            <label>Reason for Change <span class="req">*</span>
              <small class="text-muted">(recorded in audit log)</small>
            </label>
            <textarea class="form-control" name="bulk_reason" id="bulk_reason"
                      rows="2" required placeholder="e.g. Transferred to new partner, Supervisor change effective April 2026"></textarea>
          </div>
        </div>

        <!-- Selected clients preview -->
        <div style="margin-top:12px">
          <label style="font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.3px">
            Selected Clients:
          </label>
          <div id="bulk-selected-names"
               style="max-height:160px;overflow-y:auto;margin-top:6px;border:1px solid var(--border-lt);border-radius:6px;padding:8px;font-size:12px;background:#fafafa">
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit" onclick="return validateBulkForm()">
          💾 Update Selected Clients
        </button>
        <button type="button" class="btn btn-outline" onclick="closeModal('bulk-modal')">Cancel</button>
      </div>
    </div>
  </div>
</form>

<!-- ── BULK ITR APPLICABILITY MODAL ─────────────────────── -->
<form method="post" action="<?= url('clients.php') ?>" id="bulk-itr-form">
  <input type="hidden" name="post_action" value="bulk_itr_mark">
  <div id="bulk-itr-ids-container"><!-- checkboxes injected by JS --></div>

  <div class="modal-overlay" id="bulk-itr-modal">
    <div class="modal-box" style="max-width:500px">
      <div class="modal-header" style="background:var(--primary);color:#fff;border-radius:10px 10px 0 0">
        <span class="modal-title" style="color:#fff">🧾 Bulk Mark ITR Applicable</span>
        <button class="modal-close" style="color:#fff" onclick="closeModal('bulk-itr-modal')" type="button">×</button>
      </div>
      <div class="modal-body">
        <div id="bulk-itr-summary" style="background:var(--primary-bg);padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px"></div>

        <div class="form-grid form-grid-2">
          <div class="form-group" style="grid-column:span 2">
            <label>ITR Applicable?</label>
            <select class="form-control" name="bulk_itr_flag">
              <option value="1">Yes — Mark as ITR Applicable</option>
              <option value="0">No — Mark as NOT Applicable</option>
            </select>
          </div>
          <div class="form-group">
            <label>Also create ITR Register entries for FY:</label>
            <select class="form-control" name="bulk_itr_fy">
              <option value="">— Don't create register entries —</option>
              <?php foreach ($fy_list as $fy): ?>
                <option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option>
              <?php endforeach; ?>
            </select>
            <small style="font-size:11px;color:var(--text-muted)">Select a FY to create IT Return Register entries for these clients at once. Skips clients who already have an entry for that FY.</small>
          </div>
          <div class="form-group">
            <label>ITR Due Date (for your reference)</label>
            <input class="form-control" type="date" name="bulk_itr_due_date">
            <small style="font-size:11px;color:var(--text-muted)">Optional note — stored in audit log</small>
          </div>
        </div>

        <div style="margin-top:12px">
          <label style="font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.3px">Selected Clients:</label>
          <div id="bulk-itr-names" style="max-height:120px;overflow-y:auto;margin-top:6px;border:1px solid var(--border-lt);border-radius:6px;padding:8px;font-size:12px;background:#fafafa"></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit">💾 Apply to Selected Clients</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('bulk-itr-modal')">Cancel</button>
      </div>
    </div>
  </div>
</form>
<?php endif; ?>

<script>
// ── Bulk Selection Logic ──────────────────────────────────
var selectedIds   = {};   // id => client name
var selectedCount = 0;

function toggleSelectAll(cb) {
  document.querySelectorAll('.row-checkbox').forEach(function(box) {
    box.checked = cb.checked;
    const row = box.closest('tr');
    const name = row ? (row.querySelector('td:nth-child(3) strong')?.innerText || 'Client') : 'Client';
    const id   = box.value;
    if (cb.checked) {
      selectedIds[id] = name;
    } else {
      delete selectedIds[id];
    }
  });
  updateBulkToolbar();
}

function updateBulkToolbar() {
  // Rebuild selectedIds from checked boxes
  document.querySelectorAll('.row-checkbox').forEach(function(box) {
    const row  = box.closest('tr');
    const name = row ? (row.querySelector('td:nth-child(3) strong')?.innerText || 'Client #'+box.value) : 'Client #'+box.value;
    if (box.checked) {
      selectedIds[box.value] = name;
    } else {
      delete selectedIds[box.value];
    }
  });

  selectedCount = Object.keys(selectedIds).length;
  const toolbar = document.getElementById('bulk-toolbar');
  const counter = document.getElementById('bulk-count');
  if (toolbar) {
    toolbar.style.display = selectedCount > 0 ? 'flex' : 'none';
  }
  if (counter) counter.textContent = selectedCount;

  // Update select-all checkbox state
  const allBoxes     = document.querySelectorAll('.row-checkbox');
  const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
  const selectAll    = document.getElementById('select-all');
  if (selectAll && allBoxes.length > 0) {
    selectAll.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < allBoxes.length;
    selectAll.checked       = checkedBoxes.length === allBoxes.length;
  }
}

function clearSelection() {
  selectedIds   = {};
  selectedCount = 0;
  document.querySelectorAll('.row-checkbox').forEach(function(b) { b.checked = false; });
  const sa = document.getElementById('select-all');
  if (sa) { sa.checked = false; sa.indeterminate = false; }
  updateBulkToolbar();
}

// Highlight selected rows
document.addEventListener('change', function(e) {
  if (e.target.classList.contains('row-checkbox')) {
    const row = e.target.closest('tr');
    if (row) row.style.background = e.target.checked ? '#eef3fb' : '';
    updateBulkToolbar();
  }
});

function openBulkModal() {
  if (selectedCount === 0) { alert('Please select at least one client first.'); return; }

  // Summary
  const summary = document.getElementById('bulk-modal-summary');
  if (summary) summary.innerHTML = '<strong>' + selectedCount + ' client(s) selected</strong> — partner/supervisor will be updated for all of them.';

  // Show names list
  const namesDiv = document.getElementById('bulk-selected-names');
  if (namesDiv) {
    namesDiv.innerHTML = Object.entries(selectedIds).map(function([id, name]) {
      return '<div style="padding:3px 0;border-bottom:1px solid #eee">' +
             '<span style="color:var(--text-muted);margin-right:6px;font-size:10px">#' + id + '</span>' +
             name + '</div>';
    }).join('');
  }

  // Inject hidden inputs into form
  const container = document.getElementById('bulk-ids-container');
  if (container) {
    container.innerHTML = Object.keys(selectedIds).map(function(id) {
      return '<input type="hidden" name="bulk_ids[]" value="' + parseInt(id) + '">';
    }).join('');
  }

  // Reset form fields
  document.getElementById('bulk_partner_id').value    = '';
  document.getElementById('bulk_supervisor_id').value = '';
  document.getElementById('bulk_reason').value        = '';

  openModal('bulk-modal');
}

function validateBulkForm() {
  const partner = document.getElementById('bulk_partner_id').value;
  const sup     = document.getElementById('bulk_supervisor_id').value;
  const reason  = document.getElementById('bulk_reason').value.trim();

  if (!partner && !sup) {
    alert('Please select at least one field to update — Partner or Supervisor.');
    return false;
  }
  if (!reason) {
    alert('Please enter a reason for this change.');
    return false;
  }
  return true;
}

function openBulkITRModal() {
  if (selectedCount === 0) { alert('Please select at least one client first.'); return; }

  const summary = document.getElementById('bulk-itr-summary');
  if (summary) summary.innerHTML = '<strong>' + selectedCount + ' client(s) selected</strong> — ITR applicability will be updated for all of them.';

  const namesDiv = document.getElementById('bulk-itr-names');
  if (namesDiv) {
    namesDiv.innerHTML = Object.entries(selectedIds).map(function([id, name]) {
      return '<div style="padding:3px 0;border-bottom:1px solid #eee">' +
             '<span style="color:var(--text-muted);margin-right:6px;font-size:10px">#' + id + '</span>' +
             name + '</div>';
    }).join('');
  }

  const container = document.getElementById('bulk-itr-ids-container');
  if (container) {
    container.innerHTML = Object.keys(selectedIds).map(function(id) {
      return '<input type="hidden" name="bulk_ids[]" value="' + parseInt(id) + '">';
    }).join('');
  }

  openModal('bulk-itr-modal');
}

// ── Column Visibility Toggle ───────────────────────────────
// Uses localStorage to persist preferences across page loads

var COL_STORAGE_KEY = 'client_col_prefs';

function loadColumnPrefs() {
  try {
    var prefs = JSON.parse(localStorage.getItem(COL_STORAGE_KEY) || '{}');
    Object.keys(prefs).forEach(function(colId) {
      if (!prefs[colId]) {
        // Column should be hidden — hide cells and update checkbox
        toggleColumn(colId, false, true); // silent=true skips save
        var cb = document.querySelector('#col-panel input[onchange*="' + colId + '"]');
        if (cb) cb.checked = false;
      }
    });
  } catch(e) {}
}

function toggleColumn(colId, visible, silent) {
  document.querySelectorAll('.' + colId).forEach(function(el) {
    el.style.display = visible ? '' : 'none';
  });
  if (!silent) {
    try {
      var prefs = JSON.parse(localStorage.getItem(COL_STORAGE_KEY) || '{}');
      prefs[colId] = visible;
      localStorage.setItem(COL_STORAGE_KEY, JSON.stringify(prefs));
    } catch(e) {}
  }
}

function toggleColumnPanel() {
  var panel = document.getElementById('col-panel');
  if (!panel) return;
  panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function resetColumns() {
  try { localStorage.removeItem(COL_STORAGE_KEY); } catch(e) {}
  document.querySelectorAll('[class^="col-"],[class*=" col-"]').forEach(function(el) {
    el.style.display = '';
  });
  document.querySelectorAll('#col-panel input[type="checkbox"]').forEach(function(cb) {
    cb.checked = true;
  });
}

// Load preferences on page load
document.addEventListener('DOMContentLoaded', function() { loadColumnPrefs(); });
</script>

<!-- ── ACTION MODAL (Deactivate / Reactivate / Delete) ── -->
<div class="modal-overlay" id="action-modal">
  <div class="modal-box" style="max-width:460px">
    <div class="modal-header">
      <span class="modal-title" id="modal-title">Confirm Action</span>
      <button class="modal-close" onclick="closeModal('action-modal')">×</button>
    </div>
    <form method="post" action="<?= url('clients.php') ?>" id="action-form">
      <input type="hidden" name="post_action" id="modal-post-action">
      <input type="hidden" name="client_id"   id="modal-client-id">
      <div class="modal-body">
        <div id="modal-warning" style="padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px;line-height:1.6"></div>
        <div class="form-group">
          <label>Reason for this action <span class="req">*</span>
            <small class="text-muted">(will be recorded in audit log and client notes)</small>
          </label>
          <textarea class="form-control" name="action_reason" id="action-reason"
                    rows="3" required placeholder="Enter reason..."></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn" id="modal-confirm-btn" type="submit">Confirm</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('action-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<script>
function openActionModal(clientId, actionType, clientName) {
  document.getElementById('modal-client-id').value    = clientId;
  document.getElementById('modal-post-action').value  = actionType;
  document.getElementById('action-reason').value      = '';

  const warning = document.getElementById('modal-warning');
  const title   = document.getElementById('modal-title');
  const btn     = document.getElementById('modal-confirm-btn');

  if (actionType === 'deactivate') {
    title.textContent = 'Deactivate Client';
    warning.style.cssText = 'background:#fff3cd;border:1px solid #ffc107;padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px';
    warning.innerHTML = '<strong>⚠ Deactivate:</strong> <em>' + clientName + '</em><br>This client will be hidden from all registers and dropdowns until reactivated. All existing records are preserved.';
    btn.className = 'btn';
    btn.style.cssText = 'background:#856404;color:#fff;border-color:#856404';
    btn.textContent = 'Deactivate Client';
  } else if (actionType === 'reactivate') {
    title.textContent = 'Reactivate Client';
    warning.style.cssText = 'background:var(--accent-bg);border:1px solid #bbf7d0;padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px';
    warning.innerHTML = '<strong>✓ Reactivate:</strong> <em>' + clientName + '</em><br>This client will appear in all registers and dropdowns again.';
    btn.className = 'btn btn-success';
    btn.style.cssText = '';
    btn.textContent = 'Reactivate Client';
  } else if (actionType === 'delete') {
    title.textContent = 'Permanently Delete Client';
    warning.style.cssText = 'background:var(--danger-bg);border:1px solid #fecaca;padding:10px 14px;border-radius:6px;margin-bottom:1rem;font-size:13px';
    warning.innerHTML = '<strong>⛔ PERMANENT DELETE:</strong> <em>' + clientName + '</em><br><br>This will <strong>permanently delete</strong> this client and <strong>all their associated records</strong> (GST returns, ETDS, ROC, PT entries). <strong>This cannot be undone.</strong><br><br>Consider using <strong>Deactivate</strong> instead to preserve history.';
    btn.className = 'btn btn-danger';
    btn.style.cssText = '';
    btn.textContent = 'Yes, Permanently Delete';
  }

  openModal('action-modal');
}
</script>

<?php else: // ADD / EDIT FORM ?>
<!-- ═══════════════════════════════ ADD / EDIT ═══════════════════════════════ -->
<div class="page-header">
  <div>
    <div class="page-title"><?= $action==='edit' ? '✏️ Edit Client' : '➕ Add New Client' ?></div>
    <?php if ($action==='edit'): ?>
      <div class="page-subtitle">
        <?= htmlspecialchars($client['client_name'] ?? '') ?>
        &nbsp;|&nbsp; Code: <strong><?= htmlspecialchars($client['client_code'] ?? '') ?></strong>
      </div>
    <?php endif; ?>
  </div>
  <a href="<?= url('clients.php') ?>" class="btn btn-outline">← Back to List</a>
</div>

<div class="card"><div class="card-body">
<form method="post" action="<?= url('clients.php') ?>?action=<?= $action ?>&id=<?= $id ?>">

  <!-- ── BASIC INFO ──────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">Basic Information</div>
    <div class="form-grid form-grid-4">

      <div class="form-group">
        <label>Client Code</label>
        <?php if ($action==='edit'): ?>
          <input class="form-control" name="client_code"
                 value="<?= htmlspecialchars($client['client_code'] ?? '') ?>"
                 readonly style="background:#f5f5f5">
        <?php else: ?>
          <input class="form-control" value="Auto-generated on save"
                 disabled style="background:#f5f5f5;color:#888;font-style:italic">
        <?php endif; ?>
      </div>

      <div class="form-group" style="grid-column:span 2">
        <label>Client / Firm Name <span class="req">*</span></label>
        <input class="form-control" name="client_name" required
               value="<?= htmlspecialchars($client['client_name'] ?? '') ?>">
      </div>

      <div class="form-group">
        <label>Status</label>
        <select class="form-control" name="status">
          <option value="Active"   <?= ($client['status']??'Active')==='Active'  ?'selected':'' ?>>Active</option>
          <option value="Inactive" <?= ($client['status']??'')==='Inactive'?'selected':'' ?>>Inactive</option>
        </select>
      </div>

      <div class="form-group">
        <label>PAN <span class="req">*</span>
          <small class="text-muted">(auto-detects constitution)</small>
        </label>
        <input class="form-control" id="pan" name="pan" maxlength="10" required
               style="text-transform:uppercase"
               value="<?= htmlspecialchars($client['pan'] ?? '') ?>"
               placeholder="ABCDE1234F">
      </div>

      <div class="form-group">
        <label>Constitution <small class="text-muted">(from PAN)</small></label>
        <select class="form-control" id="constitution" name="constitution">
          <?php foreach (['Individual','HUF','Firm/LLP','Company','AOP','BOI','Trust','Government','Local Authority','Artificial Juridical Person','Other'] as $cc): ?>
            <option value="<?= $cc ?>" <?= ($client['constitution']??'')===$cc?'selected':'' ?>><?= $cc ?></option>
          <?php endforeach; ?>
        </select>
      </div>

      <div class="form-group">
        <label>Sub-type <small class="text-muted">(optional)</small></label>
        <input class="form-control" name="constitution_subtype"
               value="<?= htmlspecialchars($client['constitution_subtype'] ?? '') ?>"
               placeholder="e.g. LLP / OPC / Pvt Ltd">
      </div>

      <div class="form-group">
        <label>ITR Applicable</label>
        <select class="form-control" name="itr_applicable">
          <option value="1" <?= ($client['itr_applicable']??1)?'selected':'' ?>>Yes</option>
          <option value="0" <?= !($client['itr_applicable']??1)?'selected':'' ?>>No</option>
        </select>
      </div>

      <div class="form-group">
        <label>Client Group <small class="text-muted">(for IT Return grouping)</small></label>
        <select class="form-control" name="group_id" id="group_id">
          <option value="">— No Group —</option>
          <?php foreach ($client_groups as $g): ?>
            <option value="<?= $g['id'] ?>" <?= ($client['group_id']??'')==$g['id']?'selected':'' ?>><?= htmlspecialchars($g['group_name']) ?></option>
          <?php endforeach; ?>
        </select>
        <small style="font-size:11px"><a href="<?= url('client_groups.php') ?>" target="_blank">+ Manage Groups</a></small>
      </div>

      <div class="form-group" style="grid-column:span 4">
        <label>Address</label>
        <textarea class="form-control" name="address" rows="2"><?= htmlspecialchars($client['address'] ?? '') ?></textarea>
      </div>
    </div>
  </div>

  <!-- ── CONTACTS ───────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">
      Contact Persons
      <small style="font-size:11px;font-weight:400;color:var(--text-muted)">
        — add all persons (partners, directors, accounts) who should receive reminders
      </small>
    </div>
    <div id="contacts-wrap">
      <?php foreach ($contacts as $ci => $ct): ?>
      <div class="contact-row" style="display:grid;grid-template-columns:1.5fr 1fr 1.5fr 1fr auto;gap:8px;margin-bottom:8px;align-items:end">
        <div class="form-group" style="margin:0">
          <?php if ($ci===0): ?><label>Name</label><?php endif; ?>
          <input class="form-control" name="c_name[]"
                 value="<?= htmlspecialchars($ct['name']??'') ?>" placeholder="Full Name">
        </div>
        <div class="form-group" style="margin:0">
          <?php if ($ci===0): ?><label>Mobile</label><?php endif; ?>
          <input class="form-control" name="c_mobile[]"
                 value="<?= htmlspecialchars($ct['mobile']??'') ?>" placeholder="9876543210">
        </div>
        <div class="form-group" style="margin:0">
          <?php if ($ci===0): ?><label>Email</label><?php endif; ?>
          <input class="form-control" type="email" name="c_email[]"
                 value="<?= htmlspecialchars($ct['email']??'') ?>" placeholder="email@example.com">
        </div>
        <div class="form-group" style="margin:0">
          <?php if ($ci===0): ?><label>Designation</label><?php endif; ?>
          <input class="form-control" name="c_designation[]"
                 value="<?= htmlspecialchars($ct['designation']??'') ?>" placeholder="Director / Accounts">
        </div>
        <div>
          <?php if ($ci===0): ?><label style="display:block;height:18px"></label><?php endif; ?>
          <?php if ($ci>0): ?>
            <button type="button" class="btn btn-outline btn-sm"
                    onclick="this.closest('.contact-row').remove()" title="Remove">✕</button>
          <?php endif; ?>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
    <button type="button" class="btn btn-outline btn-sm mt-1" onclick="addContactRow()">+ Add Contact Person</button>
  </div>

  <!-- ── GST ────────────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="gst_applicable" name="gst_applicable" value="1"
               <?= !empty($client['gst_applicable'])?'checked':'' ?>>
        GST Details
      </label>
    </div>
    <div id="section-gst" style="<?= !empty($client['gst_applicable'])?'':'display:none' ?>">
      <p class="text-muted" style="font-size:12px;margin-bottom:10px">
        State is auto-detected from GSTIN. Add separate rows if client has multiple GSTINs or shifted return type (Monthly ↔ QRMP) — set Effective From date for each shift.
      </p>
      <div id="gstins-wrap">
        <?php foreach ($gstins as $gi => $gst): ?>
        <div class="gstin-row" style="display:grid;grid-template-columns:2fr 1.2fr 1fr 1fr auto;gap:8px;margin-bottom:8px;align-items:end">
          <div class="form-group" style="margin:0">
            <?php if ($gi===0): ?><label>GSTIN</label><?php endif; ?>
            <input class="form-control gstin-input" name="gstin_nos[]"
                   style="text-transform:uppercase"
                   value="<?= htmlspecialchars($gst['gstin']??'') ?>"
                   placeholder="27AABCU9603R1ZX"
                   oninput="autoFillState(this)">
          </div>
          <div class="form-group" style="margin:0">
            <?php if ($gi===0): ?><label>State <small class="text-muted">(auto)</small></label><?php endif; ?>
            <input class="form-control gstin-state" name="gstin_states[]"
                   value="<?= htmlspecialchars($gst['state']??'') ?>"
                   placeholder="Auto-detected" readonly
                   style="background:#f8f8f8;color:var(--text-muted)">
          </div>
          <div class="form-group" style="margin:0">
            <?php if ($gi===0): ?><label>Return Type</label><?php endif; ?>
            <select class="form-control" name="gstin_return_types[]">
              <option value="Monthly"     <?= ($gst['return_type']??'')==='Monthly'    ?'selected':'' ?>>Monthly</option>
              <option value="QRMP"        <?= ($gst['return_type']??'')==='QRMP'       ?'selected':'' ?>>QRMP (Quarterly)</option>
              <option value="Composition" <?= ($gst['return_type']??'')==='Composition'?'selected':'' ?>>Composition</option>
            </select>
          </div>
          <div class="form-group" style="margin:0">
            <?php if ($gi===0): ?><label>Effective From</label><?php endif; ?>
            <input class="form-control" type="date" name="gstin_effective_from[]"
                   value="<?= $gst['effective_from']??'' ?>"
                   title="Date from which this return type applies">
          </div>
          <div>
            <?php if ($gi===0): ?><label style="display:block;height:18px"></label><?php endif; ?>
            <?php if ($gi>0): ?>
              <button type="button" class="btn btn-outline btn-sm"
                      onclick="this.closest('.gstin-row').remove()">✕</button>
            <?php endif; ?>
          </div>
        </div>
        <?php endforeach; ?>
      </div>
      <button type="button" class="btn btn-outline btn-sm mt-1" onclick="addGSTINRow()">+ Add GSTIN</button>
    </div>
  </div>

  <!-- ── TDS ────────────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="tds_applicable" name="tds_applicable" value="1"
               <?= !empty($client['tds_applicable'])?'checked':'' ?>>
        TDS / ETDS Details
      </label>
    </div>
    <div id="section-tds" style="<?= !empty($client['tds_applicable'])?'':'display:none' ?>">
      <div class="form-grid form-grid-4">
        <div class="form-group">
          <label>TAN</label>
          <input class="form-control" name="tan" style="text-transform:uppercase"
                 maxlength="10" value="<?= htmlspecialchars($client['tan'] ?? '') ?>"
                 placeholder="ABCD12345E">
        </div>
        <div class="form-group" style="grid-column:span 3">
          <label>Return Forms Applicable <small class="text-muted">(select all that apply)</small></label>
          <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:6px">
            <?php foreach ($tds_types as $tt): ?>
            <label style="display:flex;align-items:center;gap:5px;font-size:13px;cursor:pointer;
                          background:var(--primary-bg);padding:5px 10px;border-radius:4px;border:1px solid var(--border-lt)">
              <input type="checkbox" name="tds_form_types[]"
                     value="<?= htmlspecialchars($tt['form_name']) ?>"
                     <?= in_array($tt['form_name'], $tds_forms)?'checked':'' ?>>
              <strong><?= htmlspecialchars($tt['form_name']) ?></strong>
              <span class="text-muted" style="font-size:11px">— <?= htmlspecialchars($tt['description']??'') ?></span>
            </label>
            <?php endforeach; ?>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── PROFESSIONAL TAX ───────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">Professional Tax (PT)</div>
    <div class="form-grid form-grid-4">
      <div class="form-group" style="grid-column:span 2;padding:10px;background:var(--primary-bg);border-radius:6px">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:600">
          <input type="checkbox" id="ptec_applicable" name="ptec_applicable" value="1"
                 <?= !empty($client['ptec_applicable'])?'checked':'' ?>>
          PTEC — Profession Tax Enrolment Certificate (Annual)
        </label>
        <div style="margin-top:8px">
          <label style="font-size:11px;color:var(--text-muted)">PTEC Registration Number</label>
          <input class="form-control" name="ptec_no" style="text-transform:uppercase;margin-top:3px"
                 value="<?= htmlspecialchars($client['ptec_no'] ?? '') ?>"
                 placeholder="e.g. 27123456789P">
        </div>
      </div>
      <div class="form-group" style="grid-column:span 2;padding:10px;background:#fef9ec;border-radius:6px;border:1px solid var(--border-lt)">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-weight:600">
          <input type="checkbox" id="ptrc_applicable" name="ptrc_applicable" value="1"
                 <?= !empty($client['ptrc_applicable'])?'checked':'' ?>>
          PTRC — Profession Tax Registration Certificate (Employer)
        </label>
        <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:8px">
          <div>
            <label style="font-size:11px;color:var(--text-muted)">PTRC Registration Number</label>
            <input class="form-control" name="ptrc_no" style="text-transform:uppercase;margin-top:3px"
                   value="<?= htmlspecialchars($client['ptrc_no'] ?? '') ?>"
                   placeholder="e.g. 27123456789C">
          </div>
          <div>
            <label style="font-size:11px;color:var(--text-muted)">Return Periodicity</label>
            <select class="form-control" name="ptrc_periodicity" style="margin-top:3px">
              <option value="Monthly" <?= ($client['ptrc_periodicity']??'Monthly')==='Monthly'?'selected':'' ?>>Monthly</option>
              <option value="Annual"  <?= ($client['ptrc_periodicity']??'')==='Annual' ?'selected':'' ?>>Annual</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── ROC ────────────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
        <input type="checkbox" id="roc_applicable" name="roc_applicable" value="1"
               <?= !empty($client['roc_applicable'])?'checked':'' ?>>
        ROC / MCA Details
      </label>
    </div>
    <div id="section-roc" style="<?= !empty($client['roc_applicable'])?'':'display:none' ?>">
      <div class="form-grid form-grid-4">
        <div class="form-group">
          <label>CIN</label>
          <input class="form-control" name="cin" style="text-transform:uppercase"
                 value="<?= htmlspecialchars($client['cin'] ?? '') ?>"
                 placeholder="U12345MH2010PTC123456">
        </div>
        <div class="form-group">
          <label>Company Type</label>
          <select class="form-control" name="company_type">
            <option value="">Select</option>
            <?php foreach (['Private Limited','Public Limited','OPC','LLP','Section 8','Other'] as $ct): ?>
              <option value="<?= $ct ?>" <?= ($client['company_type']??'')===$ct?'selected':'' ?>><?= $ct ?></option>
            <?php endforeach; ?>
          </select>
        </div>
        <div class="form-group">
          <label>Date of Incorporation</label>
          <input class="form-control" type="date" name="date_of_incorporation"
                 value="<?= $client['date_of_incorporation'] ?? '' ?>">
        </div>
        <div class="form-group">
          <label>Last AGM Date</label>
          <input class="form-control" type="date" name="agm_date"
                 value="<?= $client['agm_date'] ?? '' ?>">
        </div>
        <div class="form-group" style="grid-column:span 4">
          <label>DIN(s) of Directors <small class="text-muted">(Name: DIN, comma separated)</small></label>
          <input class="form-control" name="din_list"
                 value="<?= htmlspecialchars($client['din_list'] ?? '') ?>"
                 placeholder="Ramesh Kumar: 01234567, Suresh Sharma: 09876543">
        </div>
      </div>
    </div>
  </div>

  <!-- ── ASSIGNMENT ─────────────────────────────────── -->
  <div class="form-section">
    <div class="form-section-title">Assignment & Notes</div>
    <div class="form-grid form-grid-4">
      <div class="form-group">
        <label>Partner</label>
        <select class="form-control" name="partner_id">
          <option value="">Select Partner</option>
          <?php foreach ($partners as $p): ?>
            <option value="<?= $p['id'] ?>" <?= ($client['partner_id']??'')==$p['id']?'selected':'' ?>><?= htmlspecialchars($p['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group">
        <label>Supervisor</label>
        <select class="form-control" name="supervisor_id">
          <option value="">Select Supervisor</option>
          <?php foreach ($supervisors as $s): ?>
            <option value="<?= $s['id'] ?>" <?= ($client['supervisor_id']??'')==$s['id']?'selected':'' ?>><?= htmlspecialchars($s['name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group" style="grid-column:span 2">
        <label>Notes</label>
        <textarea class="form-control" name="notes" rows="2"><?= htmlspecialchars($client['notes'] ?? '') ?></textarea>
      </div>
    </div>
  </div>

  <div class="form-actions">
    <button class="btn btn-primary" type="submit">💾 Save Client</button>
    <a href="<?= url('clients.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>

<script>
// GSTIN state map
const gstinStateMap = {
  '01':'Jammu & Kashmir','02':'Himachal Pradesh','03':'Punjab','04':'Chandigarh',
  '05':'Uttarakhand','06':'Haryana','07':'Delhi','08':'Rajasthan','09':'Uttar Pradesh',
  '10':'Bihar','11':'Sikkim','12':'Arunachal Pradesh','13':'Nagaland','14':'Manipur',
  '15':'Mizoram','16':'Tripura','17':'Meghalaya','18':'Assam','19':'West Bengal',
  '20':'Jharkhand','21':'Odisha','22':'Chhattisgarh','23':'Madhya Pradesh',
  '24':'Gujarat','26':'Dadra & Nagar Haveli','27':'Maharashtra','28':'Andhra Pradesh',
  '29':'Karnataka','30':'Goa','31':'Lakshadweep','32':'Kerala','33':'Tamil Nadu',
  '34':'Puducherry','35':'Andaman & Nicobar','36':'Telangana','37':'Andhra Pradesh (New)',
  '38':'Ladakh','97':'Other Territory','99':'Centre Jurisdiction'
};

function autoFillState(input) {
  input.value = input.value.toUpperCase();
  const row = input.closest('.gstin-row');
  if (!row) return;
  const stateField = row.querySelector('.gstin-state');
  if (stateField && input.value.length >= 2) {
    stateField.value = gstinStateMap[input.value.substring(0,2)] || '';
  }
}

// PAN → Constitution auto-detect
document.getElementById('pan').addEventListener('input', function() {
  this.value = this.value.toUpperCase();
  const map = {P:'Individual',H:'HUF',F:'Firm/LLP',C:'Company',A:'AOP',B:'BOI',
                G:'Government',J:'Artificial Juridical Person',L:'Local Authority',T:'Trust'};
  if (this.value.length >= 4) {
    const c = map[this.value[3].toUpperCase()] || 'Other';
    document.getElementById('constitution').value = c;
    if (['Company','Firm/LLP'].includes(c)) {
      document.getElementById('roc_applicable').checked = true;
      document.getElementById('section-roc').style.display = 'block';
    }
  }
});

// Toggle sections
['gst_applicable','tds_applicable','roc_applicable'].forEach(function(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const sec = document.getElementById('section-' + id.replace('_applicable',''));
  if (sec) el.addEventListener('change', function() {
    sec.style.display = this.checked ? 'block' : 'none';
  });
});

// Add contact row
function addContactRow() {
  const tpl = `<div class="contact-row" style="display:grid;grid-template-columns:1.5fr 1fr 1.5fr 1fr auto;gap:8px;margin-bottom:8px;align-items:end">
    <div style="margin:0"><input class="form-control" name="c_name[]" placeholder="Full Name"></div>
    <div style="margin:0"><input class="form-control" name="c_mobile[]" placeholder="9876543210"></div>
    <div style="margin:0"><input class="form-control" type="email" name="c_email[]" placeholder="email@example.com"></div>
    <div style="margin:0"><input class="form-control" name="c_designation[]" placeholder="Director / Accounts"></div>
    <div><button type="button" class="btn btn-outline btn-sm" onclick="this.closest('.contact-row').remove()">✕</button></div>
  </div>`;
  document.getElementById('contacts-wrap').insertAdjacentHTML('beforeend', tpl);
}

// Add GSTIN row
function addGSTINRow() {
  const tpl = `<div class="gstin-row" style="display:grid;grid-template-columns:2fr 1.2fr 1fr 1fr auto;gap:8px;margin-bottom:8px;align-items:end">
    <div style="margin:0"><input class="form-control gstin-input" name="gstin_nos[]" style="text-transform:uppercase" placeholder="27AABCU9603R1ZX" oninput="autoFillState(this)"></div>
    <div style="margin:0"><input class="form-control gstin-state" name="gstin_states[]" placeholder="Auto-detected" readonly style="background:#f8f8f8;color:var(--text-muted)"></div>
    <div style="margin:0"><select class="form-control" name="gstin_return_types[]">
      <option value="Monthly">Monthly</option>
      <option value="QRMP">QRMP</option>
      <option value="Composition">Composition</option>
    </select></div>
    <div style="margin:0"><input class="form-control" type="date" name="gstin_effective_from[]"></div>
    <div><button type="button" class="btn btn-outline btn-sm" onclick="this.closest('.gstin-row').remove()">✕</button></div>
  </div>`;
  document.getElementById('gstins-wrap').insertAdjacentHTML('beforeend', tpl);
}
</script>
<?php endif; ?>
<?php include 'includes/footer.php'; ?>
