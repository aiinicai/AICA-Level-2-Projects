<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
$db = getDB();

// ── SCHEMA CHECK — covers both GET and POST ───────────────
// Runs before any form processing so a missing column gives a clear message
// instead of a silent failure or blank HTTP 500 on the add-entry POST.
$schema_ok = true;
try {
    $db->query("SELECT trigger_date, target_date, due_date_overridden FROM gst_returns LIMIT 1");
} catch (Exception $e) {
    $schema_ok = false;
    // If this is a POST, set a flash and redirect to GET so the error page renders cleanly
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $_SESSION['flash_msg'] = '⚠ Database upgrade required before entries can be saved. Run upgrade_dates.sql in phpMyAdmin first.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('gst_register.php')); exit;
    }
    include 'includes/header.php';
    echo '<div class="card" style="max-width:700px;margin:2rem auto"><div class="card-body">
        <h2 style="color:var(--danger)">⚠ Database Upgrade Required</h2>
        <p style="margin:1rem 0">The GST Register needs new date columns (<code>trigger_date</code>, <code>target_date</code>, <code>due_date_overridden</code>) that have not been added yet.</p>
        <p style="margin-bottom:1rem"><strong>Fix:</strong> Open phpMyAdmin → select <code>ca_intranet</code> →
        SQL tab → paste contents of <code>upgrade_dates.sql</code> → click Go.</p>
        <p style="font-size:12px;color:var(--text-muted)">Technical detail: '.htmlspecialchars($e->getMessage()).'</p>
        <a href="'.url('dashboard.php').'" class="btn btn-primary" style="margin-top:1rem">← Back to Dashboard</a>
    </div></div>';
    include 'includes/footer.php';
    exit;
}

$page_title = 'GST Return Register';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);
$stage  = $_GET['stage'] ?? 'list';
$dp     = defaultPeriod('gst');

// ── DELETE ENTRY ───────────────────────────────────────────
if ($action === 'delete' && $id && hasRole(['admin','partner','supervisor'])) {
    $db->prepare("DELETE FROM gst_returns WHERE id=?")->execute([$id]);
    auditLog('gst_returns', $id, 'DELETE');
    $_SESSION['flash_msg'] = 'Entry deleted.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('gst_register.php')); exit;
}

// ── SAVE / UPDATE ──────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $d = $_POST;
    $pa = $d['post_action'] ?? '';
    try {

    if ($pa === 'add_entry' || $pa === 'edit_entry') {
        $gstin = strtoupper(trim($d['gstin'] ?? ''));
        $rt_stmt = $db->prepare("SELECT periodicity FROM gst_return_types WHERE return_name=? LIMIT 1");
        $rt_stmt->execute([$d['return_type']]); $rt_row = $rt_stmt->fetch();
        $periodicity = $rt_row['periodicity'] ?? 'Monthly';
        $wd = getGSTWorkflowDates($d['return_type'], $d['return_period'], $periodicity);

        // Manual override of statutory due date (case-by-case, e.g. govt extension)
        $statutory_override = trim($d['due_date_override'] ?? '');
        $due           = $statutory_override ?: $wd['statutory'];
        $is_overridden = $statutory_override ? 1 : 0;
        $trigger_date  = $wd['trigger'];
        $target_date   = $wd['target'];

        // GSTR-1 has no challan — auto skip challan stage
        $is_gstr1 = (stripos($d['return_type'], 'GSTR-1') !== false);

        if ($pa === 'add_entry') {
            $db->prepare("INSERT INTO gst_returns
                (client_id,gstin,return_period,financial_year,return_type,periodicity,due_date,trigger_date,target_date,due_date_overridden,
                 data_received_date,data_received_from,data_receipt_mode,
                 status,assigned_to,created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)")
               ->execute([
                    intval($d['client_id']), $gstin,
                    $d['return_period'], $d['financial_year'], $d['return_type'], $periodicity,
                    $due, $trigger_date, $target_date, $is_overridden,
                    $d['data_received_date'] ?: null, trim($d['data_received_from'] ?? ''),
                    $d['data_receipt_mode'] ?: null,
                    $is_gstr1 ? 'No Challan Due' : 'Data Received',
                    $d['assigned_to'] ?: null, $_SESSION['user_id'],
               ]);
            auditLog('gst_returns', $db->lastInsertId(), 'CREATE');
            $_SESSION['flash_msg'] = 'Data receipt entry added.' . ($is_gstr1 ? ' (GSTR-1 — no challan required, moved to filing stage.)' : '');
        } else {
            // Full edit
            $db->prepare("UPDATE gst_returns SET
                client_id=?,gstin=?,return_period=?,financial_year=?,return_type=?,periodicity=?,
                due_date=?,trigger_date=?,target_date=?,due_date_overridden=?,
                data_received_date=?,data_received_from=?,data_receipt_mode=?,
                cgst_liability=?,sgst_liability=?,igst_liability=?,cess_liability=?,
                challan_no=?,payment_date=?,filed_date=?,arn=?,
                working_prepared_by=?,working_prepared_date=?,
                working_reviewed_by=?,working_reviewed_date=?,
                status=?,assigned_to=?,remarks=? WHERE id=?")
               ->execute([
                    intval($d['client_id']), $gstin,
                    $d['return_period'], $d['financial_year'], $d['return_type'], $periodicity,
                    $due, $trigger_date, $target_date, $is_overridden,
                    $d['data_received_date'] ?: null, trim($d['data_received_from'] ?? ''),
                    $d['data_receipt_mode'] ?: null,
                    floatval($d['cgst_liability']??0), floatval($d['sgst_liability']??0),
                    floatval($d['igst_liability']??0), floatval($d['cess_liability']??0),
                    trim($d['challan_no']??''), $d['payment_date']?:null,
                    $d['filed_date']?:null, strtoupper(trim($d['arn']??'')),
                    $d['working_prepared_by']?:null, $d['working_prepared_date']?:null,
                    $d['working_reviewed_by']?:null, $d['working_reviewed_date']?:null,
                    $d['status']??'Data Received', $d['assigned_to']?:null,
                    trim($d['remarks']??''), intval($d['gst_id']),
               ]);
            auditLog('gst_returns', intval($d['gst_id']), 'UPDATE');
            $_SESSION['flash_msg'] = 'Entry updated successfully.';
        }
        $_SESSION['flash_type'] = 'success';
    }

    elseif ($pa === 'update_challan') {
        $no_challan = ($d['challan_decision'] ?? '') === 'nil';
        $new_status = $no_challan ? 'No Challan Due' : 'Challan Sent';
        $db->prepare("UPDATE gst_returns SET status=?, remarks=? WHERE id=?")
           ->execute([
                $new_status,
                trim($d['remarks'] ?? ''),
                intval($d['gst_id']),
           ]);
        auditLog('gst_returns', intval($d['gst_id']), 'UPDATE');
        $_SESSION['flash_msg'] = $no_challan
            ? 'Marked as No Challan Due — moved to Filing stage.'
            : 'Challan marked as Sent — moved to Challan Paid stage.';
        $_SESSION['flash_type'] = 'success';
    }

    elseif ($pa === 'update_paid') {
        $db->prepare("UPDATE gst_returns SET payment_date=?, status='Challan Paid',
            remarks=CONCAT(IFNULL(remarks,''), IF(?<>'', CONCAT(' | Paid: ',?), '')) WHERE id=?")
           ->execute([
               $d['payment_date'] ?: date('Y-m-d'),
               trim($d['paid_remarks'] ?? ''), trim($d['paid_remarks'] ?? ''),
               intval($d['gst_id'])
           ]);
        auditLog('gst_returns', intval($d['gst_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Challan marked as paid — moved to Filing stage.';
        $_SESSION['flash_type'] = 'success';
    }

    elseif ($pa === 'update_filing') {
        $db->prepare("UPDATE gst_returns SET filed_date=?,arn=?,status='Filed',remarks=? WHERE id=?")
           ->execute([
                $d['filed_date']?:date('Y-m-d'),
                strtoupper(trim($d['arn']??'')),
                trim($d['remarks']??''),
                intval($d['gst_id']),
           ]);
        auditLog('gst_returns', intval($d['gst_id']), 'UPDATE');
        $_SESSION['flash_msg'] = 'Return filed. Record closed.'; $_SESSION['flash_type'] = 'success';
    }

    elseif ($pa === 'override_due_date') {
        // Manual case-by-case override of statutory due date (e.g. govt extension notification)
        $new_due = $d['new_due_date'] ?? '';
        if ($new_due) {
            $db->prepare("UPDATE gst_returns SET due_date=?, due_date_overridden=1, remarks=CONCAT(IFNULL(remarks,''),' | Due date extended to ',?,': ',?) WHERE id=?")
               ->execute([$new_due, $new_due, trim($d['override_reason']??''), intval($d['gst_id'])]);
            auditLog('gst_returns', intval($d['gst_id']), 'UPDATE', null, ['due_date_override'=>$new_due]);
            $_SESSION['flash_msg'] = 'Statutory due date updated to '.fmtDate($new_due).'.';
            $_SESSION['flash_type'] = 'success';
        }
    }

    elseif ($pa === 'bulk_create') {
        $fy = $d['financial_year']; $type = $d['return_type']; $period = $d['return_period'];
        $rt_stmt = $db->prepare("SELECT periodicity FROM gst_return_types WHERE return_name=? LIMIT 1");
        $rt_stmt->execute([$type]); $rt_row = $rt_stmt->fetch();
        $periodicity = $rt_row['periodicity'] ?? 'Monthly';
        $is_gstr1 = (stripos($type, 'GSTR-1') !== false);
        $wd = getGSTWorkflowDates($type, $period, $periodicity);

        // If specific clients were selected, restrict to those; otherwise all GST-applicable clients
        $selected_ids = array_filter(array_map('intval', $d['client_ids'] ?? []));
        if (!empty($selected_ids)) {
            $placeholders = implode(',', array_fill(0, count($selected_ids), '?'));
            $stmt = $db->prepare("SELECT c.id,c.gstin_list,c.supervisor_id FROM clients c WHERE c.gst_applicable=1 AND c.status='Active' AND c.id IN ($placeholders)");
            $stmt->execute($selected_ids);
        } else {
            $stmt = $db->query("SELECT c.id,c.gstin_list,c.supervisor_id FROM clients c WHERE c.gst_applicable=1 AND c.status='Active'");
        }
        $gst_clients = $stmt->fetchAll();

        $created = 0;
        foreach ($gst_clients as $c) {
            $chk = $db->prepare("SELECT id FROM gst_returns WHERE client_id=? AND return_period=? AND return_type=?");
            $chk->execute([$c['id'],$period,$type]); if ($chk->fetch()) continue;
            $gstins_data = $c['gstin_list'] ? json_decode($c['gstin_list'],true) : [];
            $primary_gstin = $gstins_data[0]['gstin'] ?? '';
            $init_status = $is_gstr1 ? 'No Challan Due' : 'Pending Data';
            $db->prepare("INSERT INTO gst_returns(client_id,gstin,return_period,financial_year,return_type,periodicity,due_date,trigger_date,target_date,status,assigned_to,created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)")
               ->execute([$c['id'],$primary_gstin,$period,$fy,$type,$periodicity,$wd['statutory'],$wd['trigger'],$wd['target'],$init_status,$c['supervisor_id'],$_SESSION['user_id']]);
            $created++;
        }
        $_SESSION['flash_msg'] = "Bulk create done: $created entries created."; $_SESSION['flash_type'] = 'success';
    }

    } catch (Exception $e) {
        $_SESSION['flash_msg'] = 'Error saving entry: '.htmlspecialchars($e->getMessage()).
            ' — If this mentions an unknown column, run upgrade_dates.sql in phpMyAdmin.';
        $_SESSION['flash_type'] = 'error';
    }

    header('Location: '.url('gst_register.php?stage='.$stage)); exit;
}

// ── FETCH FOR EDIT ─────────────────────────────────────────
$entry = [];
if ($action === 'edit' && $id) {
    $stmt = $db->prepare("SELECT g.*,c.client_name,c.pan,c.gstin_list FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE g.id=?");
    $stmt->execute([$id]); $entry = $stmt->fetch() ?: [];
}

// ── FILTERS ────────────────────────────────────────────────
// fy= and period= passed as empty string in URL means "no filter" (used by dashboard deep-links)
$filter_fy     = array_key_exists('fy',     $_GET) ? trim($_GET['fy'])     : $dp['fy'];
$filter_period = array_key_exists('period', $_GET) ? trim($_GET['period']) : $dp['period'];
$filter_type      = $_GET['return_type']   ?? '';
$filter_status    = $_GET['status']        ?? '';
$filter_client    = intval($_GET['client_id']    ?? 0);
$filter_due       = $_GET['due']           ?? '';
$filter_name      = trim($_GET['client_name']    ?? '');
$filter_sup       = intval($_GET['supervisor_id'] ?? 0);
$filter_partner   = intval($_GET['ca_partner_id'] ?? 0);
$page = max(1, intval($_GET['page'] ?? 1)); $per = 30;

$where = ['1=1']; $wp = [];
if ($filter_fy)       { $where[] = 'g.financial_year=?'; $wp[] = $filter_fy; }
if ($filter_period)   { $where[] = 'g.return_period=?';  $wp[] = $filter_period; }
if ($filter_type)     { $where[] = 'g.return_type=?';    $wp[] = $filter_type; }
if ($filter_status)   { $where[] = 'g.status=?';         $wp[] = $filter_status; }
if ($filter_client)   { $where[] = 'g.client_id=?';      $wp[] = $filter_client; }
if ($filter_name)     { $where[] = 'c.client_name LIKE ?'; $wp[] = "%$filter_name%"; }
if ($filter_sup)      { $where[] = 'c.supervisor_id=?';  $wp[] = $filter_sup; }
if ($filter_partner)  { $where[] = 'c.partner_id=?';     $wp[] = $filter_partner; }
if ($filter_due === 'overdue') { $where[] = 'g.due_date<CURDATE() AND g.status NOT IN("Filed","Not Applicable")'; }
if ($filter_due === '7d')      { $where[] = 'g.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 7 DAY) AND g.status NOT IN("Filed","Not Applicable")'; }
if ($_SESSION['role']==='supervisor') { $where[] = 'c.supervisor_id=?'; $wp[] = $_SESSION['user_id']; }
if ($_SESSION['role']==='staff')      { $where[] = 'g.assigned_to=?';   $wp[] = $_SESSION['user_id']; }
$ws = implode(' AND ', $where);

$total = $db->prepare("SELECT COUNT(*) FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE $ws");
$total->execute($wp); $total = $total->fetchColumn();
$pg = paginate($total, $per, $page);

$rows = $db->prepare(
    "SELECT g.*,c.client_name,c.pan,u.name assigned_name,wp.name prep_name,wr.name rev_name
     FROM gst_returns g JOIN clients c ON c.id=g.client_id
     LEFT JOIN users u  ON u.id=g.assigned_to
     LEFT JOIN users wp ON wp.id=g.working_prepared_by
     LEFT JOIN users wr ON wr.id=g.working_reviewed_by
     WHERE $ws ORDER BY g.due_date ASC,c.client_name ASC LIMIT ? OFFSET ?"
);
$rows->execute(array_merge($wp, [$per, $pg['offset']]));
$entries = $rows->fetchAll();

// Stage client lists
$all_gst_clients = $db->query("SELECT id,client_name,pan,gstin_list,group_id FROM clients WHERE gst_applicable=1 AND status='Active' ORDER BY client_name")->fetchAll();
$client_groups   = $db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$challan_pending = $db->query("SELECT g.*,c.client_name,c.pan,cp.name partner_name,sup.name sup_name,asgn.name assigned_name2 FROM gst_returns g JOIN clients c ON c.id=g.client_id LEFT JOIN users cp   ON cp.id=c.partner_id LEFT JOIN users sup  ON sup.id=c.supervisor_id LEFT JOIN users asgn ON asgn.id=g.assigned_to WHERE g.status='Data Received' ORDER BY g.due_date ASC,c.client_name")->fetchAll();
$challan_sent    = $db->query("SELECT g.*,c.client_name,c.pan,cp.name partner_name,sup.name sup_name,asgn.name assigned_name2 FROM gst_returns g JOIN clients c ON c.id=g.client_id LEFT JOIN users cp   ON cp.id=c.partner_id LEFT JOIN users sup  ON sup.id=c.supervisor_id LEFT JOIN users asgn ON asgn.id=g.assigned_to WHERE g.status='Challan Sent' ORDER BY g.due_date ASC,c.client_name")->fetchAll();
$ready_to_file   = $db->query("SELECT g.*,c.client_name,c.pan,cp.name partner_name,sup.name sup_name,asgn.name assigned_name2 FROM gst_returns g JOIN clients c ON c.id=g.client_id LEFT JOIN users cp   ON cp.id=c.partner_id LEFT JOIN users sup  ON sup.id=c.supervisor_id LEFT JOIN users asgn ON asgn.id=g.assigned_to WHERE g.status IN('Challan Paid','No Challan Due') ORDER BY g.due_date ASC,c.client_name")->fetchAll();

$all_users       = $db->query("SELECT id,name FROM users WHERE is_active=1 ORDER BY name")->fetchAll();
$all_partners    = $db->query("SELECT id,name FROM users WHERE role IN('partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
$all_supervisors = $db->query("SELECT id,name FROM users WHERE role IN('supervisor','partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
$gst_rt_opts = $db->query("SELECT DISTINCT return_name,periodicity FROM gst_return_types WHERE is_active=1 ORDER BY sort_order")->fetchAll();
$fy_list     = getFYList();

// ── EXECUTIVE SUMMARY ─────────────────────────────────────
// Only compute when a specific period AND return type are selected
$summary = null;
if ($filter_period && $filter_type) {
    // 1. Total clients where this return type is applicable (active, GST applicable)
    //    For Monthly: clients with gst_return_type = Monthly or return type is in their GSTIN list
    //    Simple approach: count distinct clients who HAVE an entry for this period+type
    //    PLUS clients who are applicable but have NO entry yet (data not received)

    // Clients with entries for this period+type
    $stmt = $db->prepare(
        "SELECT g.client_id, g.status
         FROM gst_returns g
         JOIN clients c ON c.id = g.client_id
         WHERE g.return_period = ? AND g.return_type = ? AND c.status = 'Active'
         ORDER BY g.client_id"
    );
    $stmt->execute([$filter_period, $filter_type]);
    $entry_rows = $stmt->fetchAll();

    // Count by status
    $s_total_entries  = count($entry_rows);
    $s_data_received  = 0;
    $s_challan_sent   = 0;
    $s_challan_paid   = 0;
    $s_no_challan     = 0;
    $s_filed          = 0;
    $s_pending        = 0;
    $s_on_hold        = 0;

    foreach ($entry_rows as $er) {
        switch ($er['status']) {
            case 'Data Received':             $s_data_received++; break;
            case 'Challan Sent':              $s_challan_sent++; break;
            case 'Challan Paid':              $s_challan_paid++; break;
            case 'No Challan Due':            $s_no_challan++; break;
            case 'Filed':                     $s_filed++; break;
            case 'On Hold':                   $s_on_hold++; break;
            default:                          $s_pending++; break; // Pending Data, etc.
        }
    }

    // Total applicable = all active GST clients (for the periodicity match)
    // Determine periodicity of this return type
    $pt_stmt = $db->prepare("SELECT periodicity FROM gst_return_types WHERE return_name=? LIMIT 1");
    $pt_stmt->execute([$filter_type]);
    $pt_row = $pt_stmt->fetch();
    $ret_periodicity = $pt_row['periodicity'] ?? 'Monthly';

    if ($ret_periodicity === 'Monthly') {
        $total_applicable = $db->query("SELECT COUNT(*) FROM clients WHERE gst_applicable=1 AND status='Active' AND gst_return_type='Monthly'")->fetchColumn();
    } elseif ($ret_periodicity === 'Quarterly') {
        $total_applicable = $db->query("SELECT COUNT(*) FROM clients WHERE gst_applicable=1 AND status='Active' AND gst_return_type IN('QRMP','Quarterly')")->fetchColumn();
    } elseif ($ret_periodicity === 'Annually') {
        $total_applicable = $db->query("SELECT COUNT(*) FROM clients WHERE gst_applicable=1 AND status='Active'")->fetchColumn();
    } else {
        $total_applicable = $db->query("SELECT COUNT(*) FROM clients WHERE gst_applicable=1 AND status='Active'")->fetchColumn();
    }

    // Data NOT received = applicable clients who have NO entry OR have Pending Data status
    $s_data_not_received = (int)$total_applicable - $s_data_received - $s_challan_sent - $s_challan_paid - $s_no_challan - $s_filed - $s_on_hold;
    if ($s_data_not_received < 0) $s_data_not_received = 0;

    // Ready to file = challan paid + no challan due
    $s_ready_to_file = $s_challan_paid + $s_no_challan;

    // Pending (return not yet filed, data received or further)
    $s_return_pending = $s_data_received + $s_challan_sent + $s_challan_paid + $s_no_challan;

    $summary = [
        'period'             => $filter_period,
        'return_type'        => $filter_type,
        'periodicity'        => $ret_periodicity,
        'total_applicable'   => (int)$total_applicable,
        'data_received'      => $s_data_received,
        'data_not_received'  => $s_data_not_received + $s_pending,
        'challan_sent'       => $s_challan_sent,
        'challan_paid'       => $s_challan_paid + $s_no_challan,
        'return_pending'     => $s_return_pending,
        'filed'              => $s_filed,
        'on_hold'            => $s_on_hold,
    ];
}

// Summary for all return types for the selected period (dashboard-style)
$period_summary = [];
if ($filter_period) {
    $stmt = $db->prepare(
        "SELECT g.return_type,
                COUNT(*) as total,
                SUM(CASE WHEN g.status='Filed' THEN 1 ELSE 0 END) as filed,
                SUM(CASE WHEN g.status='Data Received' THEN 1 ELSE 0 END) as data_received,
                SUM(CASE WHEN g.status IN('Challan Paid','No Challan Due') THEN 1 ELSE 0 END) as ready,
                SUM(CASE WHEN g.status IN('Pending Data') THEN 1 ELSE 0 END) as pending
         FROM gst_returns g
         JOIN clients c ON c.id=g.client_id
         WHERE g.return_period=? AND c.status='Active'
         GROUP BY g.return_type ORDER BY g.return_type"
    );
    $stmt->execute([$filter_period]);
    $period_summary = $stmt->fetchAll();
}

// ── GST STAGE FILTER HELPER ───────────────────────────────
// Renders partner/supervisor/user filter dropdowns above stage tables
// Must be defined before header include (function in control structure = fatal error)
function gstStageFilters($stage_key, $all_partners, $all_supervisors, $all_users, $filter_fy, $filter_period) {
    $sf_partner = intval($_GET['sf_partner'] ?? 0);
    $sf_sup     = intval($_GET['sf_sup']     ?? 0);
    $sf_user    = intval($_GET['sf_user']    ?? 0);
    $base = '?stage=' . $stage_key
          . '&fy='     . urlencode($filter_fy)
          . '&period=' . urlencode($filter_period);
    echo '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px 14px;border-bottom:1px solid var(--border-lt)">';
    echo '<form method="get" style="display:contents">';
    echo '<input type="hidden" name="stage"  value="' . $stage_key . '">';
    echo '<input type="hidden" name="fy"     value="' . htmlspecialchars($filter_fy) . '">';
    echo '<input type="hidden" name="period" value="' . htmlspecialchars($filter_period) . '">';
    echo '<label style="font-size:11px;color:var(--text-muted)">Filter:</label>';
    echo '<select name="sf_partner" class="form-control" style="width:auto;height:30px;font-size:12px" onchange="this.form.submit()">';
    echo '<option value="">All Partners</option>';
    foreach ($all_partners as $p)
        echo '<option value="' . $p['id'] . '" ' . ($sf_partner == $p['id'] ? 'selected' : '') . '>'
           . htmlspecialchars($p['name']) . '</option>';
    echo '</select>';
    echo '<select name="sf_sup" class="form-control" style="width:auto;height:30px;font-size:12px" onchange="this.form.submit()">';
    echo '<option value="">All Supervisors</option>';
    foreach ($all_supervisors as $s)
        echo '<option value="' . $s['id'] . '" ' . ($sf_sup == $s['id'] ? 'selected' : '') . '>'
           . htmlspecialchars($s['name']) . '</option>';
    echo '</select>';
    echo '<select name="sf_user" class="form-control" style="width:auto;height:30px;font-size:12px" onchange="this.form.submit()">';
    echo '<option value="">All Staff</option>';
    foreach ($all_users as $u)
        echo '<option value="' . $u['id'] . '" ' . ($sf_user == $u['id'] ? 'selected' : '') . '>'
           . htmlspecialchars($u['name']) . '</option>';
    echo '</select>';
    if ($sf_partner || $sf_sup || $sf_user)
        echo '<a href="' . $base . '" class="btn btn-outline btn-sm">Reset</a>';
    echo '</form></div>';
}

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">📊 GST Return Register</div>
    <div class="page-subtitle">
      FY: <?= $filter_fy ?> &nbsp;|&nbsp; Default period: <strong><?= htmlspecialchars($dp['period']) ?></strong>
      &nbsp;<a href="<?= url('settings.php') ?>" style="font-size:11px">[change]</a>
    </div>
  </div>
  <div class="d-flex gap-1">
    <a href="<?= url('gst_import.php') ?>" class="btn btn-outline">📥 Import Data</a>
    <a href="<?= url('gst_register.php?action=bulk_create') ?>" class="btn btn-outline">⚡ Bulk Create</a>
    <a href="<?= url('gst_register.php?stage=data') ?>" class="btn btn-primary">+ Add Entry</a>
  </div>
</div>

<!-- WORKFLOW STAGE TABS -->
<div style="display:flex;gap:0;margin-bottom:1.25rem;border-radius:8px;overflow:hidden;border:1px solid var(--border)">
<?php
$stages = [
    'list'    => ['⊞ All Entries',      count($entries).' shown'],
    'data'    => ['① Data Receipt',      'Add new'],
    'challan' => ['② Challan Sent',      count($challan_pending).' pending'],
    'paid'    => ['③ Challan Paid',      count($challan_sent).' waiting'],
    'filing'  => ['④ File / ARN',        count($ready_to_file).' ready'],
];
foreach ($stages as $s => [$label,$count]):
    $active = ($stage === $s) || ($action === 'bulk_create' && $s==='list') || ($action==='edit' && $s==='list');
?>
<a href="<?= url("gst_register.php?stage=$s") ?>"
   style="flex:1;padding:10px 6px;text-align:center;font-size:12px;font-weight:<?= $active?'600':'400' ?>;
          background:<?= $active?'var(--primary)':'var(--bg-card)' ?>;
          color:<?= $active?'#fff':'var(--text)' ?>;text-decoration:none;border-right:1px solid var(--border)">
  <?= $label ?><br><span style="font-size:10px;opacity:.75"><?= $count ?></span>
</a>
<?php endforeach; ?>
</div>

<?php if ($action === 'bulk_create'): ?>
<!-- ══ BULK CREATE ════════════════════════════════════════ -->
<div class="card" style="max-width:720px">
  <div class="card-header"><span class="card-title">⚡ Bulk Create GST Entries</span></div>
  <div class="card-body">
  <form method="post" action="<?= url('gst_register.php?stage=list') ?>">
    <input type="hidden" name="post_action" value="bulk_create">
    <div class="form-grid form-grid-3">
      <div class="form-group"><label>Financial Year <span class="req">*</span></label>
        <select class="form-control" name="financial_year" required>
          <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Return Type <span class="req">*</span></label>
        <select class="form-control" name="return_type" required>
          <?php foreach ($gst_rt_opts as $rt): ?>
            <option value="<?= htmlspecialchars($rt['return_name']) ?>"><?= htmlspecialchars($rt['return_name']) ?> (<?= $rt['periodicity'] ?>)</option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Period <span class="req">*</span></label>
        <select class="form-control" name="return_period" required>
          <?php foreach (getMonthPeriods($dp['fy']) as $mp): ?>
            <option value="<?= $mp ?>" <?= $mp===$dp['period']?'selected':'' ?>><?= $mp ?></option>
          <?php endforeach; ?>
          <?php foreach (getQuarterPeriods($dp['fy']) as $qp): ?>
            <option value="<?= $qp ?>" <?= $qp===$dp['period']?'selected':'' ?>><?= $qp ?></option>
          <?php endforeach; ?>
        </select></div>
    </div>

    <div class="form-section mt-2">
      <div class="form-section-title">
        Select Clients <small style="font-size:11px;font-weight:400;color:var(--text-muted)">— leave none selected to apply to ALL GST clients</small>
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
        <?php foreach ($all_gst_clients as $c): ?>
          <option value="<?= $c['id'] ?>" data-group="<?= $c['group_id'] ?? '' ?>"><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
        <?php endforeach; ?>
      </select>
    </div>

    <div class="form-actions">
      <button class="btn btn-primary" type="submit">Generate Entries</button>
      <a href="<?= url('gst_register.php') ?>" class="btn btn-outline">Cancel</a>
    </div>
  </form>
  </div>
</div>

<?php elseif ($action === 'edit'): ?>
<!-- ══ EDIT ENTRY (full edit by supervisor/partner/admin) ══ -->
<div class="page-header">
  <div class="page-title">✏️ Edit GST Return Entry</div>
  <a href="<?= url('gst_register.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card"><div class="card-body">
<form method="post" action="<?= url('gst_register.php?stage=list') ?>">
  <input type="hidden" name="post_action" value="edit_entry">
  <input type="hidden" name="gst_id" value="<?= $id ?>">
  <div class="form-grid form-grid-4">
    <div class="form-group" style="grid-column:span 2"><label>Client</label>
      <select class="form-control" name="client_id" required>
        <?php foreach ($all_gst_clients as $c): ?>
          <option value="<?= $c['id'] ?>" <?= ($entry['client_id']??0)==$c['id']?'selected':'' ?>><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>GSTIN</label>
      <input class="form-control" name="gstin" style="text-transform:uppercase" value="<?= htmlspecialchars($entry['gstin']??'') ?>"></div>
    <div class="form-group"><label>Return Type</label>
      <select class="form-control" name="return_type" required>
        <?php foreach ($gst_rt_opts as $rt): ?>
          <option value="<?= htmlspecialchars($rt['return_name']) ?>" <?= ($entry['return_type']??'')===$rt['return_name']?'selected':'' ?>><?= htmlspecialchars($rt['return_name']) ?> (<?= $rt['periodicity'] ?>)</option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>FY</label>
      <select class="form-control" name="financial_year">
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= ($entry['financial_year']??'')===$fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Period</label>
      <input class="form-control" name="return_period" value="<?= htmlspecialchars($entry['return_period']??'') ?>"></div>
    <div class="form-group"><label>Due Date</label>
      <input class="form-control" type="date" name="due_date_display" value="<?= $entry['due_date']??'' ?>" readonly style="background:#f5f5f5"></div>
    <div class="form-group"><label>Data Received Date</label>
      <input class="form-control" type="date" name="data_received_date" value="<?= $entry['data_received_date']??'' ?>"></div>
    <div class="form-group"><label>Received From</label>
      <input class="form-control" name="data_received_from" value="<?= htmlspecialchars($entry['data_received_from']??'') ?>"></div>
    <div class="form-group"><label>Receipt Mode</label>
      <select class="form-control" name="data_receipt_mode">
        <?php foreach (['','Email','WhatsApp','Physical','Portal','Other'] as $m): ?>
          <option value="<?= $m ?>" <?= ($entry['data_receipt_mode']??'')===$m?'selected':'' ?>><?= $m?:'-' ?></option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Prepared By</label>
      <select class="form-control" name="working_prepared_by"><option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['working_prepared_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Prepared Date</label>
      <input class="form-control" type="date" name="working_prepared_date" value="<?= $entry['working_prepared_date']??'' ?>"></div>
    <div class="form-group"><label>Reviewed By</label>
      <select class="form-control" name="working_reviewed_by"><option value="">—</option>
        <?php foreach ($all_users as $u): ?><option value="<?= $u['id'] ?>" <?= ($entry['working_reviewed_by']??'')==$u['id']?'selected':'' ?>><?= htmlspecialchars($u['name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Reviewed Date</label>
      <input class="form-control" type="date" name="working_reviewed_date" value="<?= $entry['working_reviewed_date']??'' ?>"></div>
    <div class="form-group"><label>CGST Liability (₹)</label>
      <input class="form-control" type="number" step="0.01" name="cgst_liability" value="<?= $entry['cgst_liability']??0 ?>"></div>
    <div class="form-group"><label>SGST Liability (₹)</label>
      <input class="form-control" type="number" step="0.01" name="sgst_liability" value="<?= $entry['sgst_liability']??0 ?>"></div>
    <div class="form-group"><label>IGST Liability (₹)</label>
      <input class="form-control" type="number" step="0.01" name="igst_liability" value="<?= $entry['igst_liability']??0 ?>"></div>
    <div class="form-group"><label>CESS (₹)</label>
      <input class="form-control" type="number" step="0.01" name="cess_liability" value="<?= $entry['cess_liability']??0 ?>"></div>
    <div class="form-group"><label>Challan No.</label>
      <input class="form-control" name="challan_no" value="<?= htmlspecialchars($entry['challan_no']??'') ?>"></div>
    <div class="form-group"><label>Payment Date</label>
      <input class="form-control" type="date" name="payment_date" value="<?= $entry['payment_date']??'' ?>"></div>
    <div class="form-group"><label>Filed Date</label>
      <input class="form-control" type="date" name="filed_date" value="<?= $entry['filed_date']??'' ?>"></div>
    <div class="form-group"><label>ARN</label>
      <input class="form-control" name="arn" style="text-transform:uppercase" value="<?= htmlspecialchars($entry['arn']??'') ?>"></div>
    <div class="form-group"><label>Status</label>
      <select class="form-control" name="status">
        <?php foreach (['Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Filed','On Hold','Not Applicable'] as $s): ?>
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
    <a href="<?= url('gst_register.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>

<?php elseif ($stage === 'data'): ?>
<!-- ══ STAGE 1: DATA RECEIPT ════════════════════════════════ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">① Add Data Receipt Entry</span>
    <span class="text-muted" style="font-size:12px">Record when client data is received. GSTR-1 automatically skips challan stage.</span>
  </div>
  <div class="card-body">
  <form method="post" action="<?= url('gst_register.php?stage=data') ?>">
    <input type="hidden" name="post_action" value="add_entry">
    <div class="form-grid form-grid-4">
      <div class="form-group" style="grid-column:span 2"><label>Client <span class="req">*</span></label>
        <select class="form-control" name="client_id" required onchange="fillGSTINs(this)">
          <option value="">— Select Client —</option>
          <?php foreach ($all_gst_clients as $c): ?>
            <option value="<?= $c['id'] ?>" data-gstins="<?= htmlspecialchars($c['gstin_list']??'') ?>">
              <?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)
            </option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>GSTIN <span class="req">*</span></label>
        <select class="form-control" id="gstin_select" name="gstin" required>
          <option value="">Select client first</option>
        </select></div>
      <div class="form-group"><label>Financial Year</label>
        <select class="form-control" name="financial_year">
          <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $fy===$dp['fy']?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Return Type <span class="req">*</span></label>
        <select class="form-control" name="return_type" required>
          <?php foreach ($gst_rt_opts as $rt): ?>
            <option value="<?= htmlspecialchars($rt['return_name']) ?>"><?= htmlspecialchars($rt['return_name']) ?> (<?= $rt['periodicity'] ?>)</option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Return Period <span class="req">*</span></label>
        <select class="form-control" name="return_period" required>
          <?php foreach (getMonthPeriods($dp['fy']) as $mp): ?>
            <option value="<?= $mp ?>" <?= $mp===$dp['period']?'selected':'' ?>><?= $mp ?></option>
          <?php endforeach; ?>
          <?php foreach (getQuarterPeriods($dp['fy']) as $qp): ?>
            <option value="<?= $qp ?>" <?= $qp===$dp['period']?'selected':'' ?>><?= $qp ?></option>
          <?php endforeach; ?>
        </select></div>
      <div class="form-group"><label>Data Received Date</label>
        <input class="form-control" type="date" name="data_received_date" value="<?= date('Y-m-d') ?>"></div>
      <div class="form-group"><label>Received From</label>
        <input class="form-control" name="data_received_from" placeholder="Contact name"></div>
      <div class="form-group"><label>Receipt Mode</label>
        <select class="form-control" name="data_receipt_mode">
          <option value="">Select</option>
          <?php foreach (['Email','WhatsApp','Physical','Portal','Other'] as $m): ?>
            <option value="<?= $m ?>"><?= $m ?></option>
          <?php endforeach; ?>
        </select></div>
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

<?php elseif ($stage === 'challan'): ?>
<!-- ══ STAGE 2: SEND CHALLAN ════════════════════════════════ -->
<div class="card">
  <div class="card-header">
    <span class="card-title">② Challan Sent — Payment Pending</span>
    <span class="text-muted" style="font-size:12px"><?= count($challan_pending) ?> entries where data received — GSTR-1 is excluded (no challan)</span>
    <button class="btn btn-export btn-sm" onclick="exportTableToXLS('challan-table','GST_ChallanSent')">⬇ Export XLS</button>
  </div>
  <?php gstStageFilters('challan',$all_partners,$all_supervisors,$all_users,$filter_fy,$filter_period); ?>
  <div class="table-responsive">
  <table class="data-table" id="challan-table">
    <thead><tr><th>Client</th><th>GSTIN</th><th>Period</th><th>Type</th><th>Partner</th><th>Supervisor</th><th>Assigned To</th><th>Due Date</th><th>Action</th></tr></thead>
    <tbody>
    <?php if (empty($challan_pending)): ?>
      <tr><td colspan="9" class="text-center text-muted" style="padding:2rem">No entries waiting for challan processing.</td></tr>
    <?php endif; ?>
    <?php foreach ($challan_pending as $r): ?>
      <tr>
        <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br><span class="text-muted" style="font-size:11px"><?= $r['pan'] ?></span></td>
        <td style="font-size:11px"><code><?= htmlspecialchars($r['gstin']) ?></code></td>
        <td><?= htmlspecialchars($r['return_period']) ?></td>
        <td><span class="badge badge-primary"><?= htmlspecialchars($r['return_type']) ?></span></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['partner_name'] ?? '—') ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['sup_name'] ?? '—') ?></td>
        <td style="font-size:11px"><?= htmlspecialchars($r['assigned_name2'] ?? '—') ?></td>
        <td><?= dueDateBadge($r['due_date']) ?></td>
        <td><button class="btn btn-primary btn-sm" onclick="openChallanModal(<?= htmlspecialchars(json_encode($r)) ?>)">Enter Challan Details</button></td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>

<!-- Challan Modal -->
<div class="modal-overlay" id="challan-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header">
      <span class="modal-title">② Challan Status</span>
      <button class="modal-close" onclick="closeModal('challan-modal')" type="button">×</button>
    </div>
    <form method="post" action="<?= url('gst_register.php?stage=challan') ?>">
      <input type="hidden" name="post_action" value="update_challan">
      <input type="hidden" name="gst_id" id="cm_gst_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1.25rem;font-size:13px" id="cm_info"></div>

        <p style="font-weight:600;font-size:14px;margin-bottom:14px">Is challan applicable?</p>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:1.25rem">
          <label style="border:2px solid var(--border);border-radius:10px;padding:18px 12px;text-align:center;cursor:pointer;transition:.15s" id="lbl_yes">
            <input type="radio" name="challan_decision" value="yes" style="display:none" onchange="highlightChallanChoice()">
            <div style="font-size:26px;margin-bottom:6px">✅</div>
            <div style="font-weight:700;font-size:15px">Yes</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">Challan to be paid<br>Moves to Challan Paid tab</div>
          </label>
          <label style="border:2px solid var(--border);border-radius:10px;padding:18px 12px;text-align:center;cursor:pointer;transition:.15s" id="lbl_nil">
            <input type="radio" name="challan_decision" value="nil" style="display:none" onchange="highlightChallanChoice()">
            <div style="font-size:26px;margin-bottom:6px">⭕</div>
            <div style="font-weight:700;font-size:15px">NIL</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:4px">No challan payable<br>Moves directly to Filing tab</div>
          </label>
        </div>

        <div class="form-group">
          <label>Remarks (optional)</label>
          <textarea class="form-control" name="remarks" rows="2" placeholder="e.g. ITC adjusted, Nil return"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" type="submit" id="cm_submit_btn" disabled>Confirm &amp; Move</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('challan-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<div class="modal-overlay" id="paid-modal">
  <div class="modal-box" style="max-width:400px">
    <div class="modal-header">
      <span class="modal-title">③ Confirm Challan Paid</span>
      <button class="modal-close" onclick="closeModal('paid-modal')" type="button">×</button>
    </div>
    <form method="post" action="<?= url('gst_register.php?stage=paid') ?>">
      <input type="hidden" name="post_action" value="update_paid">
      <input type="hidden" name="gst_id" id="pm_gst_id">
      <div class="modal-body">
        <div style="background:var(--primary-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="pm_info"></div>
        <div class="form-group mb-2">
          <label>Payment Date <span class="req">*</span></label>
          <input class="form-control" type="date" name="payment_date" value="<?= date('Y-m-d') ?>" required>
        </div>
        <div class="form-group">
          <label>Remarks (optional)</label>
          <textarea class="form-control" name="paid_remarks" rows="2" placeholder="e.g. BSR code, challan reference"></textarea>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Mark as Paid → Filing</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('paid-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<div class="modal-overlay" id="filing-modal">
  <div class="modal-box" style="max-width:460px">
    <div class="modal-header"><span class="modal-title">④ Mark Return as Filed</span>
      <button class="modal-close" onclick="closeModal('filing-modal')">×</button></div>
    <form method="post" action="<?= url('gst_register.php?stage=filing') ?>">
      <input type="hidden" name="post_action" value="update_filing">
      <input type="hidden" name="gst_id" id="fm_gst_id">
      <div class="modal-body">
        <div style="background:var(--success-bg);padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px" id="fm_info"></div>
        <div class="form-grid form-grid-2">
          <div class="form-group"><label>Filing Date <span class="req">*</span></label>
            <input class="form-control" type="date" name="filed_date" value="<?= date('Y-m-d') ?>" required></div>
          <div class="form-group"><label>ARN <span class="req">*</span></label>
            <input class="form-control" name="arn" style="text-transform:uppercase" placeholder="AA1234567890123" required></div>
          <div class="form-group" style="grid-column:span 2"><label>Remarks</label>
            <textarea class="form-control" name="remarks" rows="2"></textarea></div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" type="submit">✓ Mark as Filed &amp; Close</button>
        <button type="button" class="btn btn-outline" onclick="closeModal('filing-modal')">Cancel</button>
      </div>
    </form>
  </div>
</div>

<?php else: // LIST VIEW ?>
<!-- ══ MAIN LIST ══════════════════════════════════════════════ -->

<?php if ($summary): ?>
<!-- ── EXECUTIVE SUMMARY CARD ──────────────────────────────── -->
<div class="card" style="margin-bottom:1.25rem;border-left:4px solid var(--primary)">
  <div class="card-header" style="background:var(--primary-bg)">
    <span class="card-title" style="color:var(--primary)">
      📊 Executive Summary — <strong><?= htmlspecialchars($summary['return_type']) ?></strong>
      &nbsp;|&nbsp; Period: <strong><?= htmlspecialchars($summary['period']) ?></strong>
      &nbsp;|&nbsp; <span style="font-size:12px;font-weight:400;color:var(--text-muted)"><?= $summary['periodicity'] ?> return</span>
    </span>
    <span style="font-size:12px;color:var(--text-muted)">Live — updates as entries are added</span>
  </div>
  <div class="card-body" style="padding:14px">
    <!-- Progress bar -->
    <?php
      $tot = max(1, $summary['total_applicable']);
      $pct_filed    = round($summary['filed']           / $tot * 100);
      $pct_ready    = round($summary['challan_paid']    / $tot * 100);
      $pct_wip      = round($summary['data_received']   / $tot * 100);
      $pct_challan  = round($summary['challan_sent']    / $tot * 100);
      $pct_pending  = round($summary['data_not_received'] / $tot * 100);
    ?>
    <div style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;font-size:11px;color:var(--text-muted);margin-bottom:4px">
        <span>Progress: <?= $summary['filed'] ?> / <?= $summary['total_applicable'] ?> filed</span>
        <span><?= $pct_filed ?>% complete</span>
      </div>
      <div style="height:14px;background:#e9ecef;border-radius:7px;overflow:hidden;display:flex">
        <div style="width:<?= $pct_filed ?>%;background:#166534;transition:width .5s" title="Filed: <?= $summary['filed'] ?>"></div>
        <div style="width:<?= $pct_ready ?>%;background:#1d6fa5;transition:width .5s" title="Ready to File: <?= $summary['challan_paid'] ?>"></div>
        <div style="width:<?= $pct_wip ?>%;background:#b45309;transition:width .5s" title="Data Received: <?= $summary['data_received'] ?>"></div>
        <div style="width:<?= $pct_challan ?>%;background:#ffc107;transition:width .5s" title="Challan Sent: <?= $summary['challan_sent'] ?>"></div>
        <div style="width:<?= $pct_pending ?>%;background:#dee2e6;transition:width .5s" title="Data Not Received: <?= $summary['data_not_received'] ?>"></div>
      </div>
      <div style="display:flex;gap:12px;margin-top:5px;flex-wrap:wrap;font-size:10px">
        <span><span style="display:inline-block;width:10px;height:10px;background:#166534;border-radius:2px;margin-right:3px"></span>Filed</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#1d6fa5;border-radius:2px;margin-right:3px"></span>Ready to File</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#b45309;border-radius:2px;margin-right:3px"></span>Data Received / In Progress</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#ffc107;border-radius:2px;margin-right:3px"></span>Challan Sent</span>
        <span><span style="display:inline-block;width:10px;height:10px;background:#dee2e6;border-radius:2px;margin-right:3px"></span>Data Pending</span>
      </div>
    </div>

    <!-- Summary counts grid -->
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:8px;text-align:center">
      <div style="padding:10px 6px;background:#f8f9fa;border-radius:6px;border:1px solid var(--border-lt)">
        <div style="font-size:22px;font-weight:700;color:var(--primary)"><?= $summary['total_applicable'] ?></div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px;line-height:1.3">Total<br>Applicable</div>
      </div>
      <div style="padding:10px 6px;background:#fdf0ef;border-radius:6px;border:1px solid #fecaca;cursor:pointer" onclick="filterByStatus('')" title="Click to show all pending">
        <div style="font-size:22px;font-weight:700;color:#c0392b"><?= $summary['data_not_received'] ?></div>
        <div style="font-size:11px;color:#c0392b;margin-top:2px;line-height:1.3">Data NOT<br>Received</div>
      </div>
      <div style="padding:10px 6px;background:#fef9ec;border-radius:6px;border:1px solid #fed7aa;cursor:pointer" onclick="filterByStatus('Data Received')" title="Click to filter">
        <div style="font-size:22px;font-weight:700;color:#b45309"><?= $summary['data_received'] ?></div>
        <div style="font-size:11px;color:#b45309;margin-top:2px;line-height:1.3">Data<br>Received</div>
      </div>
      <div style="padding:10px 6px;background:#fffbeb;border-radius:6px;border:1px solid #fcd34d;cursor:pointer" onclick="filterByStatus('Challan Sent')" title="Click to filter">
        <div style="font-size:22px;font-weight:700;color:#92400e"><?= $summary['challan_sent'] ?></div>
        <div style="font-size:11px;color:#92400e;margin-top:2px;line-height:1.3">Challan<br>Sent</div>
      </div>
      <div style="padding:10px 6px;background:#e8f4fc;border-radius:6px;border:1px solid #bae6fd;cursor:pointer" onclick="filterByStatus('Challan Paid')" title="Click to filter">
        <div style="font-size:22px;font-weight:700;color:#1d6fa5"><?= $summary['challan_paid'] ?></div>
        <div style="font-size:11px;color:#1d6fa5;margin-top:2px;line-height:1.3">Challan Paid /<br>No Challan Due</div>
      </div>
      <div style="padding:10px 6px;background:#fff8f0;border-radius:6px;border:1px solid #fed7aa;cursor:pointer" onclick="filterByStatus('')" title="Return not yet filed">
        <div style="font-size:22px;font-weight:700;color:#b45309"><?= $summary['return_pending'] ?></div>
        <div style="font-size:11px;color:#b45309;margin-top:2px;line-height:1.3">Return<br>Pending</div>
      </div>
      <div style="padding:10px 6px;background:#f0fdf4;border-radius:6px;border:1px solid #bbf7d0;cursor:pointer" onclick="filterByStatus('Filed')" title="Click to filter">
        <div style="font-size:22px;font-weight:700;color:#166534"><?= $summary['filed'] ?></div>
        <div style="font-size:11px;color:#166534;margin-top:2px;line-height:1.3">Return<br>Filed ✓</div>
      </div>
    </div>

    <?php if ($summary['on_hold'] > 0): ?>
    <div style="margin-top:8px;padding:6px 10px;background:#fdf0ef;border-radius:4px;font-size:12px;color:var(--danger)">
      ⚠ <?= $summary['on_hold'] ?> entries are On Hold — review required.
    </div>
    <?php endif; ?>
  </div>
</div>
<?php endif; ?>

<?php if (!empty($period_summary) && !$filter_type): ?>
<!-- ── PERIOD OVERVIEW (when no return type selected) ──────── -->
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-header">
    <span class="card-title">📋 Period Overview — <?= htmlspecialchars($filter_period) ?> (All Return Types)</span>
  </div>
  <div class="table-responsive">
  <table class="data-table" style="font-size:12px">
    <thead>
      <tr>
        <th>Return Type</th><th>Total Entries</th><th>Pending Data</th>
        <th>Data Received</th><th>Ready to File</th><th>Filed</th><th>Completion</th>
      </tr>
    </thead>
    <tbody>
    <?php foreach ($period_summary as $ps): ?>
      <tr>
        <td><span class="badge badge-primary"><?= htmlspecialchars($ps['return_type']) ?></span></td>
        <td class="text-center"><strong><?= $ps['total'] ?></strong></td>
        <td class="text-center"><span style="color:var(--danger)"><?= $ps['pending'] ?></span></td>
        <td class="text-center"><span style="color:var(--warning)"><?= $ps['data_received'] ?></span></td>
        <td class="text-center"><span style="color:var(--info)"><?= $ps['ready'] ?></span></td>
        <td class="text-center"><span style="color:var(--success);font-weight:600"><?= $ps['filed'] ?></span></td>
        <td style="min-width:120px">
          <?php $pct = $ps['total'] > 0 ? round($ps['filed']/$ps['total']*100) : 0; ?>
          <div style="display:flex;align-items:center;gap:6px">
            <div style="flex:1;height:8px;background:#e9ecef;border-radius:4px;overflow:hidden">
              <div style="width:<?= $pct ?>%;height:100%;background:<?= $pct===100?'#166534':'#1d6fa5' ?>;border-radius:4px"></div>
            </div>
            <span style="font-size:10px;color:var(--text-muted);white-space:nowrap"><?= $pct ?>%</span>
          </div>
        </td>
      </tr>
    <?php endforeach; ?>
    </tbody>
  </table>
  </div>
</div>
<?php endif; ?>

<div class="filters-bar">
  <form method="get" style="display:contents">
    <input type="hidden" name="stage" value="list">
    <div class="filter-group"><label>Client Name</label>
      <input type="text" name="client_name" value="<?= htmlspecialchars($filter_name) ?>" placeholder="Search name..." style="width:160px"></div>
    <div class="filter-group"><label>FY</label>
      <select name="fy">
        <?php foreach ($fy_list as $fy): ?><option value="<?= $fy ?>" <?= $filter_fy===$fy?'selected':'' ?>><?= $fy ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Period</label>
      <select name="period"><option value="">All Periods</option>
        <?php foreach (getMonthPeriods($filter_fy) as $mp): ?><option value="<?= $mp ?>" <?= $filter_period===$mp?'selected':'' ?>><?= $mp ?></option><?php endforeach; ?>
        <?php foreach (getQuarterPeriods($filter_fy) as $qp): ?><option value="<?= $qp ?>" <?= $filter_period===$qp?'selected':'' ?>><?= $qp ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Return Type</label>
      <select name="return_type"><option value="">All Types</option>
        <?php foreach ($gst_rt_opts as $rt): ?><option value="<?= htmlspecialchars($rt['return_name']) ?>" <?= $filter_type===$rt['return_name']?'selected':'' ?>><?= htmlspecialchars($rt['return_name']) ?></option><?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Status</label>
      <select name="status"><option value="">All</option>
        <?php foreach (['Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Filed','On Hold','Not Applicable'] as $s): ?>
          <option value="<?= $s ?>" <?= $filter_status===$s?'selected':'' ?>><?= $s ?></option>
        <?php endforeach; ?>
      </select></div>
    <div class="filter-group"><label>Due</label>
      <select name="due"><option value="">All</option>
        <option value="overdue" <?= $filter_due==='overdue'?'selected':'' ?>>Overdue</option>
        <option value="7d"      <?= $filter_due==='7d'?'selected':'' ?>>Due in 7d</option>
      </select></div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('gst_register.php') ?>" class="btn btn-outline">Reset</a>
      <button class="btn btn-export" type="button" onclick="exportTableToXLS('gst-table','GST_Register_<?= $filter_fy ?>_<?= $filter_period ?>')">⬇ Export XLS</button>
    </div>
  </form>
</div>

<div class="card"><div class="table-responsive">
<table class="data-table" id="gst-table">
  <thead>
    <tr>
      <th>#</th><th>Client</th><th>GSTIN</th><th>Period</th><th>Type</th>
      <th>Trigger Date</th><th>Target Date</th><th>Statutory Due Date</th>
      <th>Data Recd</th><th>Prepared By</th><th>Reviewed By</th>
      <th>Liability (₹)</th><th>Payment Date</th><th>Filed Date</th><th>ARN</th>
      <th>Status</th><th class="no-export">Actions</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($entries as $i => $r): $days = daysUntil($r['due_date']); ?>
    <tr class="<?= $r['status']!=='Filed'&&$days!==null&&$days<0?'row-overdue':($r['status']!=='Filed'&&$days!==null&&$days<=7?'row-due-soon':'') ?>">
      <td><?= $pg['offset']+$i+1 ?></td>
      <td><strong style="font-size:12px"><?= htmlspecialchars($r['client_name']) ?></strong><br>
          <span class="text-muted" style="font-size:10px"><?= $r['pan'] ?></span></td>
      <td style="font-size:10px"><code><?= htmlspecialchars($r['gstin']) ?></code></td>
      <td><?= htmlspecialchars($r['return_period']) ?></td>
      <td><span class="badge badge-primary"><?= htmlspecialchars($r['return_type']) ?></span></td>
      <td style="font-size:11px"><?= triggerStatusBadge($r['trigger_date'] ?? null) ?></td>
      <td style="font-size:11px"><?= targetDateBadge($r['target_date'] ?? null) ?></td>
      <td>
        <?= dueDateBadge($r['due_date']) ?>
        <?php if (!empty($r['due_date_overridden'])): ?>
          <span class="badge badge-warning" style="font-size:9px" title="Manually extended from statutory default">EXT</span>
        <?php endif; ?>
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
          <button type="button" class="btn-icon" style="font-size:10px;padding:1px 4px"
                  onclick="openOverrideModal(<?= $r['id'] ?>,'<?= htmlspecialchars($r['due_date']) ?>','<?= htmlspecialchars(addslashes($r['client_name'])) ?>')"
                  title="Override due date (govt extension)">✏</button>
        <?php endif; ?>
      </td>
      <td style="font-size:11px"><?= $r['data_received_date']?'<span class="badge badge-success">'.fmtDate($r['data_received_date']).'</span>':'<span class="badge badge-secondary">Pending</span>' ?></td>
      <td style="font-size:11px"><?= htmlspecialchars($r['prep_name']??'—') ?></td>
      <td style="font-size:11px"><?= htmlspecialchars($r['rev_name']??'—') ?></td>
      <td class="text-right"><?php $tl=$r['cgst_liability']+$r['sgst_liability']+$r['igst_liability']+$r['cess_liability']; echo $tl>0?'₹'.number_format($tl,0):'—'; ?></td>
      <td style="font-size:11px"><?= fmtDate($r['payment_date']) ?></td>
      <td style="font-size:11px"><?= $r['filed_date']?'<span class="badge badge-success">'.fmtDate($r['filed_date']).'</span>':'—' ?></td>
      <td style="font-size:10px"><code><?= htmlspecialchars($r['arn']?:'—') ?></code></td>
      <td>
        <select class="status-select" data-id="<?= $r['id'] ?>" data-module="gst_returns"
                style="font-size:11px;height:24px;padding:0 4px;border:1px solid var(--border);border-radius:4px;min-width:120px">
          <?php foreach (['Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Filed','On Hold','Not Applicable'] as $s): ?>
            <option value="<?= $s ?>" <?= $r['status']===$s?'selected':'' ?>><?= $s ?></option>
          <?php endforeach; ?>
        </select>
      </td>
      <td class="no-export" style="white-space:nowrap">
        <?php if (hasRole(['admin','partner','supervisor'])): ?>
          <a href="<?= url('gst_register.php?action=edit&id=').$r['id'] ?>" class="btn btn-outline btn-sm">Edit</a>
          <a href="<?= url('gst_register.php?action=delete&id=').$r['id'] ?>"
             class="btn btn-danger btn-sm"
             onclick="return confirm('Delete this entry? This cannot be undone.')">Delete</a>
        <?php endif; ?>
        <?php if ($r['status']==='Data Received'): ?>
          <a href="<?= url('gst_register.php?stage=challan') ?>" class="btn btn-outline btn-sm">→ Challan</a>
        <?php elseif ($r['status']==='Challan Sent'): ?>
          <a href="<?= url('gst_register.php?stage=paid') ?>" class="btn btn-outline btn-sm">→ Paid</a>
        <?php elseif (in_array($r['status'],['Challan Paid','No Challan Due'])): ?>
          <a href="<?= url('gst_register.php?stage=filing') ?>" class="btn btn-success btn-sm">→ File</a>
        <?php elseif ($r['status']==='Filed'): ?>
          <span class="badge badge-success">✓ Filed</span>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($entries)): ?>
    <tr><td colspan="17" class="text-center text-muted" style="padding:2rem">No entries found.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div></div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i=1;$i<=$pg['total_pages'];$i++): ?>
    <a href="?stage=list&fy=<?= urlencode($filter_fy) ?>&period=<?= urlencode($filter_period) ?>&return_type=<?= urlencode($filter_type) ?>&status=<?= urlencode($filter_status) ?>&page=<?= $i ?>"
       class="page-link <?= $i===$page?'active':'' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($entries) ?> of <?= $total ?></span>
</div>
<?php endif; ?>
<?php endif; // end stage/action blocks ?>

<script>
function fillGSTINs(sel) {
  const opt = sel.options[sel.selectedIndex];
  const raw = opt.dataset.gstins || '[]';
  let gstins = [];
  try { gstins = JSON.parse(raw); } catch(e) {}
  const dd = document.getElementById('gstin_select');
  if (!dd) return;
  dd.innerHTML = '';
  if (!gstins.length) { dd.innerHTML = '<option value="">No GSTIN found</option>'; return; }
  gstins.forEach(function(g) {
    if (!g.gstin) return;
    const o = document.createElement('option');
    o.value = g.gstin;
    o.textContent = g.gstin + (g.state ? ' — ' + g.state : '');
    dd.appendChild(o);
  });
}
function toggleChallanFields(cb) { document.getElementById('challan_fields').style.display = cb.checked?'none':'block'; }
function openChallanModal(r) {
  document.getElementById('cm_gst_id').value = r.id;
  document.getElementById('cm_info').innerHTML =
    '<strong>'+r.client_name+'</strong> | '+(r.return_type||'')+' | '+r.return_period+' | Due: '+(r.due_date||'—');
  // Reset Yes/Nil card selection
  document.querySelectorAll('input[name="challan_decision"]').forEach(function(el){ el.checked = false; });
  ['lbl_yes','lbl_nil'].forEach(function(id){
    var el = document.getElementById(id);
    if (el) { el.style.borderColor='var(--border)'; el.style.background=''; }
  });
  var btn = document.getElementById('cm_submit_btn');
  if (btn) btn.disabled = true;
  openModal('challan-modal');
}
function highlightChallanChoice() {
  var yes = document.querySelector('input[name="challan_decision"][value="yes"]');
  var nil = document.querySelector('input[name="challan_decision"][value="nil"]');
  var lY  = document.getElementById('lbl_yes');
  var lN  = document.getElementById('lbl_nil');
  if (yes && yes.checked) {
    lY.style.borderColor='var(--primary)'; lY.style.background='var(--primary-bg)';
    lN.style.borderColor='var(--border)';  lN.style.background='';
  } else {
    lN.style.borderColor='#ef4444'; lN.style.background='#fef2f2';
    lY.style.borderColor='var(--border)'; lY.style.background='';
  }
  var btn = document.getElementById('cm_submit_btn');
  if (btn) btn.disabled = false;
}
function openPaidModal(r) {
  const total=(parseFloat(r.cgst_liability)||0)+(parseFloat(r.sgst_liability)||0)+(parseFloat(r.igst_liability)||0)+(parseFloat(r.cess_liability)||0);
  document.getElementById('pm_gst_id').value = r.id;
  document.getElementById('pm_info').innerHTML = '<strong>'+r.client_name+'</strong> | '+r.return_type+' '+r.return_period+' | Total: ₹'+total.toLocaleString('en-IN')+(r.challan_no?' | Challan: '+r.challan_no:'');
  openModal('paid-modal');
}
function openFilingModal(r) {
  document.getElementById('fm_gst_id').value = r.id;
  document.getElementById('fm_info').innerHTML = '<strong>'+r.client_name+'</strong> | '+r.return_type+' '+r.return_period+(r.payment_date?' | Paid: '+r.payment_date:' | Nil Return');
  openModal('filing-modal');
}

// Click on summary card → filter list by that status
function filterByStatus(status) {
  const url = new URL(window.location.href);
  url.searchParams.set('stage', 'list');
  if (status) {
    url.searchParams.set('status', status);
  } else {
    url.searchParams.delete('status');
  }
  window.location.href = url.toString();
}

function openOverrideModal(id, currentDue, clientName) {
  document.getElementById('ov_gst_id').value = id;
  document.getElementById('ov_info').innerHTML = '<strong>'+clientName+'</strong> | Current statutory due date: '+(currentDue||'—');
  document.getElementById('ov_new_date').value = currentDue || '';
  openModal('override-modal');
}
</script>

<!-- Statutory Due Date Override Modal (govt extension case-by-case) -->
<div class="modal-overlay" id="override-modal">
  <div class="modal-box" style="max-width:440px">
    <div class="modal-header">
      <span class="modal-title">✏ Override Statutory Due Date</span>
      <button class="modal-close" onclick="closeModal('override-modal')">×</button>
    </div>
    <form method="post" action="<?= url('gst_register.php?stage=list') ?>">
      <input type="hidden" name="post_action" value="override_due_date">
      <input type="hidden" name="gst_id" id="ov_gst_id">
      <div class="modal-body">
        <div style="background:#fff8f0;padding:10px;border-radius:6px;margin-bottom:1rem;font-size:13px;border:1px solid #fed7aa" id="ov_info"></div>
        <p class="text-muted" style="font-size:12px;margin-bottom:10px">
          Use this only when the Government/Department extends the due date via notification.
          This change applies to this specific entry only.
        </p>
        <div class="form-group mb-2">
          <label>New Statutory Due Date <span class="req">*</span></label>
          <input class="form-control" type="date" name="new_due_date" id="ov_new_date" required>
        </div>
        <div class="form-group">
          <label>Reason / Notification Reference</label>
          <input class="form-control" name="override_reason" placeholder="e.g. Notification No. 01/2026-Central Tax">
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
