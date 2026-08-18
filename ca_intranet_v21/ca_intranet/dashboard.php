<?php
require_once __DIR__ . '/includes/config.php';
requireLogin();
$page_title = 'Dashboard';
$db  = getDB();
$uid = $_SESSION['user_id'];
$role= $_SESSION['role'];

// ── Role-based filters — each module has its own alias ─────
// For gst_returns, etds_returns, roc_compliances: alias g, table joins clients c
// For ptax_register: alias p, joins clients c

function roleFilter($role, $uid, $alias='g') {
    if ($role === 'supervisor') {
        return [
            " AND ($alias.assigned_to = ? OR EXISTS(SELECT 1 FROM clients cx WHERE cx.id = $alias.client_id AND cx.supervisor_id = ?))",
            [$uid, $uid]
        ];
    }
    if ($role === 'staff') {
        return [" AND $alias.assigned_to = ?", [$uid]];
    }
    return ['', []];
}

[$rf_gst,  $p_gst]  = roleFilter($role, $uid, 'g');
[$rf_etds, $p_etds] = roleFilter($role, $uid, 'g');
[$rf_roc,  $p_roc]  = roleFilter($role, $uid, 'g');
[$rf_pt,   $p_pt]   = roleFilter($role, $uid, 'p');

// ── STAT COUNTS ────────────────────────────────────────────
function statCount($db, $sql, $params) {
    try {
        $s = $db->prepare($sql); $s->execute($params); return (int)$s->fetchColumn();
    } catch (Exception $e) { return 0; }
}

$gst_overdue = statCount($db,
    "SELECT COUNT(*) FROM gst_returns g WHERE status NOT IN ('Filed','Not Applicable') AND due_date < CURDATE() $rf_gst", $p_gst);
$gst_due7 = statCount($db,
    "SELECT COUNT(*) FROM gst_returns g WHERE status NOT IN ('Filed','Not Applicable') AND due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 7 DAY) $rf_gst", $p_gst);
$etds_overdue = statCount($db,
    "SELECT COUNT(*) FROM etds_returns g WHERE status != 'Filed' AND due_date_return < CURDATE() $rf_etds", $p_etds);
$etds_due7 = statCount($db,
    "SELECT COUNT(*) FROM etds_returns g WHERE status != 'Filed' AND due_date_return BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 7 DAY) $rf_etds", $p_etds);
$roc_overdue = statCount($db,
    "SELECT COUNT(*) FROM roc_compliances g WHERE status NOT IN ('Filed','Not Applicable') AND due_date < CURDATE() $rf_roc", $p_roc);
$roc_due15 = statCount($db,
    "SELECT COUNT(*) FROM roc_compliances g WHERE status NOT IN ('Filed','Not Applicable') AND due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 15 DAY) $rf_roc", $p_roc);
$pt_overdue = statCount($db,
    "SELECT COUNT(*) FROM ptax_register p WHERE status NOT IN ('Filed','Not Applicable') AND due_date < CURDATE() $rf_pt", $p_pt);
$total_clients = statCount($db, "SELECT COUNT(*) FROM clients WHERE status='Active'", []);

// ── PENDING LISTS ──────────────────────────────────────────
function fetchPending($db, $sql, $params, $limit=15) {
    try {
        $s = $db->prepare($sql . " LIMIT $limit"); $s->execute($params); return $s->fetchAll();
    } catch (Exception $e) { return []; }
}

$gst_pending = fetchPending($db,
    "SELECT g.*, c.client_name, c.pan, u.name as assigned_name
     FROM gst_returns g JOIN clients c ON c.id=g.client_id LEFT JOIN users u ON u.id=g.assigned_to
     WHERE g.status NOT IN ('Filed','Not Applicable') AND g.due_date <= DATE_ADD(CURDATE(),INTERVAL 30 DAY) $rf_gst
     ORDER BY g.due_date ASC", $p_gst);

$etds_pending = fetchPending($db,
    "SELECT g.*, c.client_name, c.pan, u.name as assigned_name
     FROM etds_returns g JOIN clients c ON c.id=g.client_id LEFT JOIN users u ON u.id=g.assigned_to
     WHERE g.status != 'Filed' AND g.due_date_return <= DATE_ADD(CURDATE(),INTERVAL 30 DAY) $rf_etds
     ORDER BY g.due_date_return ASC", $p_etds, 10);

$roc_pending = fetchPending($db,
    "SELECT g.*, c.client_name, c.pan, u.name as assigned_name
     FROM roc_compliances g JOIN clients c ON c.id=g.client_id LEFT JOIN users u ON u.id=g.assigned_to
     WHERE g.status NOT IN ('Filed','Not Applicable') AND g.due_date <= DATE_ADD(CURDATE(),INTERVAL 60 DAY) $rf_roc
     ORDER BY g.due_date ASC", $p_roc, 10);

// ── GST PERIOD SUMMARY FOR DASHBOARD ─────────────────────
$dp = defaultPeriod('gst');
$dash_summary = [];
try {
    $stmt = $db->prepare(
        "SELECT g.return_type,
                COUNT(*) as entries,
                SUM(CASE WHEN g.status='Filed' THEN 1 ELSE 0 END) as filed,
                SUM(CASE WHEN g.status IN('Data Received','Challan Sent','Challan Paid','No Challan Due') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN g.status='Pending Data' THEN 1 ELSE 0 END) as pending
         FROM gst_returns g
         JOIN clients c ON c.id=g.client_id
         WHERE g.return_period=? AND c.status='Active'
         GROUP BY g.return_type ORDER BY g.return_type"
    );
    $stmt->execute([$dp['period']]);
    $dash_summary = $stmt->fetchAll();
} catch (Exception $e) { $dash_summary = []; }

// ── PARTNER WORKLOAD SUMMARY ───────────────────────────────
// Pending (not Filed/Done/Closed) and Overdue counts per Partner, across all registers
// Partner is attached via clients.partner_id
$partner_workload = [];
try {
    $partners_list = $db->query("SELECT id, name FROM users WHERE role IN('partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
    foreach ($partners_list as $p) {
        $pid = $p['id'];

        $stmt = $db->prepare("SELECT COUNT(*) FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE c.partner_id=? AND g.status NOT IN('Filed','Not Applicable')");
        $stmt->execute([$pid]); $gst_pending = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE c.partner_id=? AND g.status NOT IN('Filed','Not Applicable') AND g.due_date < CURDATE()");
        $stmt->execute([$pid]); $gst_overdue_p = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM etds_returns e JOIN clients c ON c.id=e.client_id WHERE c.partner_id=? AND e.status NOT IN('Filed','Form 16A Downloaded','Not Applicable')");
        $stmt->execute([$pid]); $etds_pending = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM roc_compliances r JOIN clients c ON c.id=r.client_id WHERE c.partner_id=? AND r.status NOT IN('Filed','Not Applicable')");
        $stmt->execute([$pid]); $roc_pending_p = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE (i.ca_partner_id=? OR c.partner_id=?) AND i.itr_uploaded_status != 'Yes'");
        $stmt->execute([$pid, $pid]); $itr_pending = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE (i.ca_partner_id=? OR c.partner_id=?) AND i.itr_uploaded_status = 'Yes'");
        $stmt->execute([$pid, $pid]); $itr_done = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE (i.ca_partner_id=? OR c.partner_id=?) AND i.itr_uploaded_status != 'Yes' AND i.data_received_on IS NOT NULL");
        $stmt->execute([$pid, $pid]); $itr_wip = (int)$stmt->fetchColumn();

        $total_pending = $gst_pending + $etds_pending + $roc_pending_p + $itr_pending;
        if ($total_pending > 0 || true) {
            $partner_workload[] = [
                'name' => $p['name'], 'id' => $pid,
                'gst' => $gst_pending, 'gst_overdue' => $gst_overdue_p,
                'etds' => $etds_pending, 'roc' => $roc_pending_p,
                'itr' => $itr_pending, 'itr_done' => $itr_done, 'itr_wip' => $itr_wip,
                'total' => $total_pending,
            ];
        }
    }
    // Sort by highest workload first
    usort($partner_workload, fn($a,$b) => $b['total'] <=> $a['total']);
} catch (Exception $e) { $partner_workload = []; }

// ── SUPERVISOR WORKLOAD SUMMARY ────────────────────────────
// Pending counts per Supervisor, across all registers (via clients.supervisor_id)
$supervisor_workload = [];
try {
    $sup_list = $db->query("SELECT id, name FROM users WHERE role IN('supervisor','partner','admin') AND is_active=1 ORDER BY name")->fetchAll();
    foreach ($sup_list as $s) {
        $sid = $s['id'];
        $stmt = $db->prepare("SELECT COUNT(*) FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE c.supervisor_id=? AND g.status NOT IN('Filed','Not Applicable')");
        $stmt->execute([$sid]); $gst_pending = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM gst_returns g JOIN clients c ON c.id=g.client_id WHERE c.supervisor_id=? AND g.status NOT IN('Filed','Not Applicable') AND g.due_date < CURDATE()");
        $stmt->execute([$sid]); $gst_overdue_s = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM etds_returns e JOIN clients c ON c.id=e.client_id WHERE c.supervisor_id=? AND e.status NOT IN('Filed','Form 16A Downloaded','Not Applicable')");
        $stmt->execute([$sid]); $etds_pending = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM roc_compliances r JOIN clients c ON c.id=r.client_id WHERE c.supervisor_id=? AND r.status NOT IN('Filed','Not Applicable')");
        $stmt->execute([$sid]); $roc_pending_s = (int)$stmt->fetchColumn();

        $stmt = $db->prepare("SELECT COUNT(*) FROM itr_returns i JOIN clients c ON c.id=i.client_id WHERE c.supervisor_id=? AND i.itr_uploaded_status != 'Yes'");
        $stmt->execute([$sid]); $itr_pending = (int)$stmt->fetchColumn();

        $total_pending = $gst_pending + $etds_pending + $roc_pending_s + $itr_pending;
        if ($total_pending > 0) { // only show supervisors with actual work
            $supervisor_workload[] = [
                'name' => $s['name'], 'id' => $sid,
                'gst' => $gst_pending, 'gst_overdue' => $gst_overdue_s,
                'etds' => $etds_pending, 'roc' => $roc_pending_s, 'itr' => $itr_pending,
                'total' => $total_pending,
            ];
        }
    }
    usort($supervisor_workload, fn($a,$b) => $b['total'] <=> $a['total']);
} catch (Exception $e) { $supervisor_workload = []; }

// ── USER-WISE ITR SUMMARY ──────────────────────────────────
$user_itr_summary = [];
try {
    $all_users_list = $db->query("SELECT id, name FROM users WHERE is_active=1 ORDER BY name")->fetchAll();
    $cur_fy = $dp['fy'];
    foreach ($all_users_list as $u) {
        $uid = $u['id'];
        // Count ITRs where this user is accounting_done_by OR itr_prepared_by OR itr_verified_by
        $stmt = $db->prepare(
            "SELECT COUNT(*) FROM itr_returns i WHERE financial_year=?
             AND (accounting_done_by=? OR itr_prepared_by=? OR itr_verified_by=?)"
        );
        $stmt->execute([$cur_fy, $uid, $uid, $uid]); $total = (int)$stmt->fetchColumn();
        if ($total === 0) continue; // only show users with active ITR work

        $stmt = $db->prepare(
            "SELECT COUNT(*) FROM itr_returns i WHERE financial_year=?
             AND (accounting_done_by=? OR itr_prepared_by=? OR itr_verified_by=?)
             AND itr_uploaded_status='Yes'"
        );
        $stmt->execute([$cur_fy, $uid, $uid, $uid]); $done = (int)$stmt->fetchColumn();

        $stmt = $db->prepare(
            "SELECT COUNT(*) FROM itr_returns i WHERE financial_year=?
             AND (accounting_done_by=? OR itr_prepared_by=? OR itr_verified_by=?)
             AND itr_uploaded_status != 'Yes' AND data_received_on IS NOT NULL"
        );
        $stmt->execute([$cur_fy, $uid, $uid, $uid]); $wip = (int)$stmt->fetchColumn();

        $stmt = $db->prepare(
            "SELECT COUNT(*) FROM itr_returns i WHERE financial_year=?
             AND (accounting_done_by=? OR itr_prepared_by=? OR itr_verified_by=?)
             AND itr_uploaded_status != 'Yes' AND data_received_on IS NULL"
        );
        $stmt->execute([$cur_fy, $uid, $uid, $uid]); $data_pending = (int)$stmt->fetchColumn();

        $user_itr_summary[] = [
            'name'         => $u['name'],
            'id'           => $uid,
            'total'        => $total,
            'done'         => $done,
            'wip'          => $wip,
            'data_pending' => $data_pending,
        ];
    }
    usort($user_itr_summary, fn($a,$b) => $b['total'] <=> $a['total']);
} catch (Exception $e) { $user_itr_summary = []; }

include 'includes/header.php';
?>

<div class="page-header">
  <div>
    <div class="page-title">Dashboard</div>
    <div class="page-subtitle">
      Welcome, <?= htmlspecialchars($_SESSION['name']) ?>
      &nbsp;|&nbsp; <?= date('l, d F Y') ?>
      &nbsp;|&nbsp; FY <?= currentFY() ?>
    </div>
  </div>
</div>

<!-- STAT CARDS -->
<div class="stats-grid">
  <a class="stat-card danger" href="<?= url('gst_register.php?stage=list&fy=&period=&due=overdue') ?>">
    <div class="stat-number"><?= $gst_overdue ?></div>
    <div class="stat-label">GST Overdue</div>
  </a>
  <a class="stat-card warning" href="<?= url('gst_register.php?stage=list&fy=&period=&due=7d') ?>">
    <div class="stat-number"><?= $gst_due7 ?></div>
    <div class="stat-label">GST Due in 7 Days</div>
  </a>
  <a class="stat-card danger" href="<?= url('etds_register.php?stage=list&fy=') ?>">
    <div class="stat-number"><?= $etds_overdue ?></div>
    <div class="stat-label">ETDS Overdue</div>
  </a>
  <a class="stat-card warning" href="<?= url('etds_register.php?stage=list&fy=') ?>">
    <div class="stat-number"><?= $etds_due7 ?></div>
    <div class="stat-label">ETDS Due in 7 Days</div>
  </a>
  <a class="stat-card danger" href="<?= url('roc_register.php?fy=&due=overdue') ?>">
    <div class="stat-number"><?= $roc_overdue ?></div>
    <div class="stat-label">ROC Overdue</div>
  </a>
  <a class="stat-card info" href="<?= url('roc_register.php?fy=&due=15d') ?>">
    <div class="stat-number"><?= $roc_due15 ?></div>
    <div class="stat-label">ROC Due in 15 Days</div>
  </a>
  <a class="stat-card danger" href="<?= url('ptax_register.php?fy=&due=overdue') ?>">
    <div class="stat-number"><?= $pt_overdue ?></div>
    <div class="stat-label">PT Returns Overdue</div>
  </a>
  <a class="stat-card success" href="<?= url('clients.php') ?>">
    <div class="stat-number"><?= $total_clients ?></div>
    <div class="stat-label">Active Clients</div>
  </a>
</div>

<!-- PARTNER WORKLOAD TILES -->
<?php if (!empty($partner_workload) && hasRole(['admin','partner'])): ?>
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-header">
    <span class="card-title">👤 Cases by Partner — Work in Hand (Pending)</span>
  </div>
  <div class="card-body" style="padding:14px">
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px">
      <?php foreach ($partner_workload as $pw): ?>
        <div style="background:#f8f9fa;border:1px solid var(--border-lt);border-radius:10px;padding:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-weight:600;font-size:13px;color:var(--text)">👤 <?= htmlspecialchars($pw['name']) ?></span>
            <span class="badge <?= $pw['total']>0?'badge-primary':'badge-secondary' ?>" style="font-size:13px;font-weight:700"><?= $pw['total'] ?> pending</span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;text-align:center">
            <a href="<?= url('gst_register.php?stage=list&ca_partner_id='.$pw['id'].'&period=') ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:<?= $pw['gst_overdue']>0?'var(--danger)':'var(--primary)' ?>"><?= $pw['gst'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">GST Pending</div>
                <?php if ($pw['gst_overdue']>0): ?><div style="font-size:9px;color:var(--danger)">⚠ <?= $pw['gst_overdue'] ?> late</div><?php endif; ?>
              </div>
            </a>
            <a href="<?= url('etds_register.php?stage=list&supervisor_id='.$pw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:var(--primary)"><?= $pw['etds'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">ETDS Pending</div>
              </div>
            </a>
            <a href="<?= url('roc_register.php?partner_id='.$pw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:var(--primary)"><?= $pw['roc'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">ROC Pending</div>
              </div>
            </a>
            <!-- ITR: Pending / WIP / Done in one cell -->
            <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:6px 4px;font-size:10px">
              <div style="font-size:10px;font-weight:600;color:var(--text-muted);margin-bottom:4px">ITR</div>
              <a href="<?= url('itr_register.php?stage=list&ca_partner_id='.$pw['id']) ?>" style="text-decoration:none;display:block">
                <div style="color:var(--danger);font-weight:700"><?= $pw['itr'] ?> <span style="font-weight:400;font-size:9px">pending</span></div>
              </a>
              <a href="<?= url('itr_register.php?stage=list&ca_partner_id='.$pw['id']) ?>" style="text-decoration:none;display:block">
                <div style="color:var(--warning);font-weight:700"><?= $pw['itr_wip'] ?> <span style="font-weight:400;font-size:9px">WIP</span></div>
              </a>
              <a href="<?= url('itr_register.php?stage=list&ca_partner_id='.$pw['id'].'&itr_uploaded=Yes') ?>" style="text-decoration:none;display:block">
                <div style="color:var(--accent);font-weight:700"><?= $pw['itr_done'] ?> <span style="font-weight:400;font-size:9px">done</span></div>
              </a>
            </div>
          </div>
        </div>
      <?php endforeach; ?>
    </div>
  </div>
</div>
<?php endif; ?>

<!-- SUPERVISOR WORKLOAD TILES -->
<?php if (!empty($supervisor_workload) && hasRole(['admin','partner'])): ?>
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-header">
    <span class="card-title">🧑‍💼 Cases by Supervisor — Work in Hand (Pending)</span>
  </div>
  <div class="card-body" style="padding:14px">
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px">
      <?php foreach ($supervisor_workload as $sw): ?>
        <div style="background:#fafbfc;border:1px solid var(--border-lt);border-radius:10px;padding:14px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
            <span style="font-weight:600;font-size:13px;color:var(--text)">🧑‍💼 <?= htmlspecialchars($sw['name']) ?></span>
            <span class="badge <?= $sw['total']>5?'badge-danger':($sw['total']>0?'badge-warning':'badge-secondary') ?>" style="font-size:13px;font-weight:700"><?= $sw['total'] ?> pending</span>
          </div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;text-align:center">
            <a href="<?= url('gst_register.php?stage=list&supervisor_id='.$sw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:<?= $sw['gst_overdue']>0?'var(--danger)':'var(--primary)' ?>"><?= $sw['gst'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">GST</div>
                <?php if ($sw['gst_overdue']>0): ?><div style="font-size:9px;color:var(--danger)">⚠ <?= $sw['gst_overdue'] ?> late</div><?php endif; ?>
              </div>
            </a>
            <a href="<?= url('etds_register.php?stage=list&supervisor_id='.$sw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:var(--primary)"><?= $sw['etds'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">ETDS</div>
              </div>
            </a>
            <a href="<?= url('roc_register.php?supervisor_id='.$sw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:var(--primary)"><?= $sw['roc'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">ROC</div>
              </div>
            </a>
            <a href="<?= url('itr_register.php?stage=list&supervisor_id='.$sw['id']) ?>" style="text-decoration:none">
              <div style="background:#fff;border:1px solid var(--border-lt);border-radius:6px;padding:8px 4px">
                <div style="font-weight:700;font-size:16px;color:var(--primary)"><?= $sw['itr'] ?></div>
                <div style="font-size:10px;color:var(--text-muted)">ITR</div>
              </div>
            </a>
          </div>
        </div>
      <?php endforeach; ?>
    </div>
  </div>
</div>
<?php elseif (hasRole(['admin','partner'])): ?>
<div class="card" style="margin-bottom:1.25rem">
  <div class="card-body" style="text-align:center;padding:20px;color:var(--text-muted);font-size:13px">
    🎉 No pending work assigned to any supervisor right now.
  </div>
</div>
<?php endif; ?>

<!-- PERIOD SUMMARY STRIP -->
<?php if (!empty($dash_summary) && $dp['period']): ?>
<div class="card" style="margin-bottom:1.25rem;border-left:4px solid var(--primary)">
  <div class="card-header" style="background:var(--primary-bg);padding:10px 16px">
    <span class="card-title" style="color:var(--primary)">
      📊 GST Status Summary — Period: <strong><?= htmlspecialchars($dp['period']) ?></strong>
    </span>
    <a href="<?= url('gst_register.php?period='.urlencode($dp['period'])) ?>" class="btn btn-outline btn-sm">View Detail</a>
  </div>
  <div class="card-body" style="padding:12px 16px">
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <?php foreach ($dash_summary as $ds): ?>
      <div style="flex:1;min-width:160px;background:#f8f9fa;border-radius:6px;padding:10px 12px;border:1px solid var(--border-lt)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
          <span class="badge badge-primary"><?= htmlspecialchars($ds['return_type']) ?></span>
          <span style="font-size:11px;color:var(--text-muted)"><?= $ds['entries'] ?> entries</span>
        </div>
        <!-- Mini progress bar -->
        <?php $pct = $ds['entries']>0 ? round($ds['filed']/$ds['entries']*100) : 0; ?>
        <div style="height:6px;background:#e9ecef;border-radius:3px;overflow:hidden;margin-bottom:6px">
          <div style="width:<?= $pct ?>%;height:100%;background:<?= $pct===100?'#166534':'#1d6fa5' ?>;border-radius:3px"></div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;text-align:center;font-size:11px">
          <div>
            <div style="font-weight:700;color:#c0392b"><?= $ds['pending'] ?></div>
            <div style="color:var(--text-muted);font-size:10px">Pending</div>
          </div>
          <div>
            <div style="font-weight:700;color:#b45309"><?= $ds['in_progress'] ?></div>
            <div style="color:var(--text-muted);font-size:10px">In Progress</div>
          </div>
          <div>
            <div style="font-weight:700;color:#166534"><?= $ds['filed'] ?></div>
            <div style="color:var(--text-muted);font-size:10px">Filed ✓</div>
          </div>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
    <?php if (empty($dash_summary)): ?>
      <p class="text-muted" style="font-size:12px">No GST entries found for <?= htmlspecialchars($dp['period']) ?>. 
        <a href="<?= url('gst_register.php?action=bulk_create') ?>">Create entries</a> or 
        <a href="<?= url('settings.php') ?>">change default period</a>.
      </p>
    <?php endif; ?>
  </div>
</div>
<?php endif; ?>

<!-- PENDING TABLES -->
<div class="dash-grid">

  <!-- GST -->
  <div class="card">
    <div class="card-header">
      <span class="card-title">📊 GST Returns — Due / Pending</span>
      <a href="<?= url('gst_register.php') ?>" class="btn btn-outline btn-sm">View All</a>
    </div>
    <div class="table-responsive">
    <table class="data-table">
      <thead><tr><th>Client</th><th>Period</th><th>Type</th><th>Due Date</th><th>Status</th></tr></thead>
      <tbody>
      <?php foreach ($gst_pending as $r): $days = daysUntil($r['due_date']); ?>
        <tr class="<?= $days!==null&&$days<0?'row-overdue':($days!==null&&$days<=7?'row-due-soon':'') ?>">
          <td><a href="<?= url('gst_register.php?client_id=').$r['client_id'] ?>" style="font-size:12px;font-weight:500"><?= htmlspecialchars($r['client_name']) ?></a>
              <div class="text-muted" style="font-size:10px"><?= htmlspecialchars($r['pan']) ?></div></td>
          <td style="font-size:12px"><?= htmlspecialchars($r['return_period']) ?></td>
          <td><span class="badge badge-primary" style="font-size:10px"><?= htmlspecialchars($r['return_type']) ?></span></td>
          <td><?= dueDateBadge($r['due_date']) ?></td>
          <td><?= statusBadge($r['status']) ?></td>
        </tr>
      <?php endforeach; ?>
      <?php if (empty($gst_pending)): ?>
        <tr><td colspan="5" class="text-center text-muted" style="padding:1.5rem">No pending GST returns in next 30 days 🎉</td></tr>
      <?php endif; ?>
      </tbody>
    </table>
    </div>
  </div>

  <!-- ETDS -->
  <div class="card">
    <div class="card-header">
      <span class="card-title">📋 ETDS Returns — Due / Pending</span>
      <a href="<?= url('etds_register.php') ?>" class="btn btn-outline btn-sm">View All</a>
    </div>
    <div class="table-responsive">
    <table class="data-table">
      <thead><tr><th>Client</th><th>Quarter</th><th>Form</th><th>Due Date</th><th>Status</th></tr></thead>
      <tbody>
      <?php foreach ($etds_pending as $r): $days = daysUntil($r['due_date_return']); ?>
        <tr class="<?= $days!==null&&$days<0?'row-overdue':($days!==null&&$days<=7?'row-due-soon':'') ?>">
          <td><a href="<?= url('etds_register.php?client_id=').$r['client_id'] ?>" style="font-size:12px;font-weight:500"><?= htmlspecialchars($r['client_name']) ?></a>
              <div class="text-muted" style="font-size:10px"><?= htmlspecialchars($r['tan']) ?></div></td>
          <td style="font-size:12px"><?= htmlspecialchars($r['quarter']) ?> / <?= htmlspecialchars($r['financial_year']) ?></td>
          <td><span class="badge badge-primary" style="font-size:10px"><?= htmlspecialchars($r['form_type']) ?></span></td>
          <td><?= dueDateBadge($r['due_date_return']) ?></td>
          <td><?= statusBadge($r['status']) ?></td>
        </tr>
      <?php endforeach; ?>
      <?php if (empty($etds_pending)): ?>
        <tr><td colspan="5" class="text-center text-muted" style="padding:1.5rem">No pending ETDS returns 🎉</td></tr>
      <?php endif; ?>
      </tbody>
    </table>
    </div>
  </div>

  <!-- ROC -->
  <div class="card" style="grid-column:1/-1">
    <div class="card-header">
      <span class="card-title">🏢 ROC Compliances — Due in 60 Days</span>
      <a href="<?= url('roc_register.php') ?>" class="btn btn-outline btn-sm">View All</a>
    </div>
    <div class="table-responsive">
    <table class="data-table">
      <thead><tr><th>Client</th><th>Form</th><th>Description</th><th>Due Date</th><th>Due Basis</th><th>Assigned</th><th>Status</th></tr></thead>
      <tbody>
      <?php foreach ($roc_pending as $r): $days = daysUntil($r['due_date']); ?>
        <tr class="<?= $days!==null&&$days<0?'row-overdue':($days!==null&&$days<=7?'row-due-soon':'') ?>">
          <td><a href="<?= url('roc_register.php?client_id=').$r['client_id'] ?>" style="font-size:12px;font-weight:500"><?= htmlspecialchars($r['client_name']) ?></a></td>
          <td><span class="badge badge-primary" style="font-size:10px"><?= htmlspecialchars($r['form_type']) ?></span></td>
          <td style="font-size:11px"><?= htmlspecialchars($r['form_description']??'') ?></td>
          <td><?= dueDateBadge($r['due_date']) ?></td>
          <td style="font-size:10px;color:var(--text-muted)"><?= htmlspecialchars($r['due_date_basis']??'') ?></td>
          <td style="font-size:11px"><?= htmlspecialchars($r['assigned_name']??'—') ?></td>
          <td><?= statusBadge($r['status']) ?></td>
        </tr>
      <?php endforeach; ?>
      <?php if (empty($roc_pending)): ?>
        <tr><td colspan="7" class="text-center text-muted" style="padding:1.5rem">No ROC compliances due in next 60 days 🎉</td></tr>
      <?php endif; ?>
      </tbody>
    </table>
    </div>
  </div>

</div><!-- /.dash-grid -->

<!-- USER-WISE ITR SUMMARY -->
<?php if (!empty($user_itr_summary)): ?>
<div class="card" style="margin-top:1.5rem">
  <div class="card-header">
    <span class="card-title">📋 User-wise ITR Summary — FY <?= htmlspecialchars($dp['fy']) ?></span>
    <span class="text-muted" style="font-size:12px">Only users assigned to at least one ITR are shown</span>
  </div>
  <div class="table-responsive">
  <table class="data-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Team Member</th>
        <th style="text-align:center">Total Assigned</th>
        <th style="text-align:center">Data Pending</th>
        <th style="text-align:center">WIP</th>
        <th style="text-align:center">Done ✓</th>
        <th style="text-align:center">% Complete</th>
      </tr>
    </thead>
    <tbody>
    <?php foreach ($user_itr_summary as $i => $u): ?>
      <?php $pct = $u['total'] > 0 ? round($u['done'] / $u['total'] * 100) : 0; ?>
      <tr>
        <td><?= $i+1 ?></td>
        <td><strong style="font-size:13px"><?= htmlspecialchars($u['name']) ?></strong></td>
        <td style="text-align:center">
          <a href="<?= url('itr_register.php?stage=list&assigned_user='.$u['id']) ?>"
             style="font-weight:700;font-size:16px;color:var(--primary);text-decoration:none">
            <?= $u['total'] ?>
          </a>
        </td>
        <td style="text-align:center">
          <?php if ($u['data_pending'] > 0): ?>
            <a href="<?= url('itr_register.php?stage=data') ?>"
               style="font-weight:700;font-size:15px;color:var(--danger);text-decoration:none"
               title="Data not yet received">
              <?= $u['data_pending'] ?>
            </a>
          <?php else: ?>
            <span style="color:var(--text-muted)">0</span>
          <?php endif; ?>
        </td>
        <td style="text-align:center">
          <?php if ($u['wip'] > 0): ?>
            <a href="<?= url('itr_register.php?stage=list&assigned_user='.$u['id']) ?>"
               style="font-weight:700;font-size:15px;color:var(--warning);text-decoration:none">
              <?= $u['wip'] ?>
            </a>
          <?php else: ?>
            <span style="color:var(--text-muted)">0</span>
          <?php endif; ?>
        </td>
        <td style="text-align:center">
          <?php if ($u['done'] > 0): ?>
            <a href="<?= url('itr_register.php?stage=list&assigned_user='.$u['id'].'&itr_uploaded=Yes') ?>"
               style="font-weight:700;font-size:15px;color:var(--accent);text-decoration:none">
              <?= $u['done'] ?>
            </a>
          <?php else: ?>
            <span style="color:var(--text-muted)">0</span>
          <?php endif; ?>
        </td>
        <td style="text-align:center">
          <div style="display:flex;align-items:center;gap:8px;justify-content:center">
            <div style="flex:1;max-width:80px;height:8px;background:var(--border-lt);border-radius:4px;overflow:hidden">
              <div style="height:100%;width:<?= $pct ?>%;background:<?= $pct>=80?'var(--accent)':($pct>=40?'var(--warning)':'var(--danger)') ?>;border-radius:4px;transition:width .3s"></div>
            </div>
            <span style="font-size:12px;font-weight:600;color:<?= $pct>=80?'var(--accent)':($pct>=40?'var(--warning)':'var(--text-muted)') ?>"><?= $pct ?>%</span>
          </div>
        </td>
      </tr>
    <?php endforeach; ?>
    </tbody>
    <tfoot>
      <tr style="background:var(--primary-bg);font-weight:600">
        <td colspan="2" style="font-size:12px">Total (across all users, may overlap)</td>
        <td style="text-align:center"><?= array_sum(array_column($user_itr_summary,'total')) ?></td>
        <td style="text-align:center;color:var(--danger)"><?= array_sum(array_column($user_itr_summary,'data_pending')) ?></td>
        <td style="text-align:center;color:var(--warning)"><?= array_sum(array_column($user_itr_summary,'wip')) ?></td>
        <td style="text-align:center;color:var(--accent)"><?= array_sum(array_column($user_itr_summary,'done')) ?></td>
        <td></td>
      </tr>
    </tfoot>
  </table>
  </div>
</div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>
