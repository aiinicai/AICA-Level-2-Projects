<?php
require_once __DIR__ . '/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner'])) {
    header('Location: '.url('dashboard.php')); exit;
}
$db = getDB();
$page_title = 'Audit Log';

$filter_module = $_GET['module'] ?? '';
$filter_action = $_GET['action_type'] ?? '';
$filter_user   = intval($_GET['user_id'] ?? 0);
$filter_date   = $_GET['date'] ?? '';
$page = max(1, intval($_GET['page'] ?? 1));
$per_page = 50;

$where = ['1=1']; $wparams = [];
if ($filter_module) { $where[] = 'a.module = ?'; $wparams[] = $filter_module; }
if ($filter_action) { $where[] = 'a.action = ?'; $wparams[] = $filter_action; }
if ($filter_user)   { $where[] = 'a.user_id = ?'; $wparams[] = $filter_user; }
if ($filter_date)   { $where[] = 'DATE(a.created_at) = ?'; $wparams[] = $filter_date; }
$whereStr = implode(' AND ', $where);

$stmt = $db->prepare("SELECT COUNT(*) FROM audit_log a WHERE $whereStr");
$stmt->execute($wparams); $total = $stmt->fetchColumn();
$pg = paginate($total, $per_page, $page);

$stmt = $db->prepare("SELECT a.*, u.name as user_name FROM audit_log a LEFT JOIN users u ON u.id = a.user_id WHERE $whereStr ORDER BY a.created_at DESC LIMIT ? OFFSET ?");
$stmt->execute(array_merge($wparams, [$per_page, $pg['offset']]));
$logs = $stmt->fetchAll();

$all_users = $db->query("SELECT id, name FROM users ORDER BY name")->fetchAll();

include 'includes/header.php';
?>

<div class="page-header">
  <div class="page-title">🔍 Audit Log</div>
  <div class="page-subtitle">Total: <?= $total ?> events</div>
</div>

<div class="filters-bar">
  <form method="get" style="display:contents;">
    <div class="filter-group">
      <label>Module</label>
      <select name="module">
        <option value="">All Modules</option>
        <?php foreach (['auth','clients','gst_returns','etds_returns','roc_compliances','users'] as $m): ?>
          <option value="<?= $m ?>" <?= $filter_module === $m ? 'selected' : '' ?>><?= ucfirst(str_replace('_',' ',$m)) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Action</label>
      <select name="action_type">
        <option value="">All</option>
        <?php foreach (['CREATE','UPDATE','DELETE','LOGIN','LOGOUT','EXPORT'] as $a): ?>
          <option value="<?= $a ?>" <?= $filter_action === $a ? 'selected' : '' ?>><?= $a ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>User</label>
      <select name="user_id">
        <option value="">All Users</option>
        <?php foreach ($all_users as $u): ?>
          <option value="<?= $u['id'] ?>" <?= $filter_user == $u['id'] ? 'selected' : '' ?>><?= htmlspecialchars($u['name']) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="filter-group">
      <label>Date</label>
      <input type="date" name="date" value="<?= htmlspecialchars($filter_date) ?>">
    </div>
    <div class="filter-actions">
      <button class="btn btn-primary" type="submit">Filter</button>
      <a href="<?= url('audit_log.php') ?>" class="btn btn-outline">Reset</a>
    </div>
  </form>
</div>

<div class="card">
<div class="table-responsive">
<table class="data-table">
  <thead>
    <tr><th>#</th><th>Date/Time</th><th>User</th><th>Module</th><th>Record ID</th><th>Action</th><th>IP Address</th><th>Details</th></tr>
  </thead>
  <tbody>
  <?php foreach ($logs as $i => $l): ?>
    <tr>
      <td><?= $pg['offset'] + $i + 1 ?></td>
      <td style="font-size:12px;white-space:nowrap;"><?= date('d-M-Y H:i:s', strtotime($l['created_at'])) ?></td>
      <td><?= htmlspecialchars($l['user_name'] ?? 'System') ?></td>
      <td><span class="badge badge-primary"><?= htmlspecialchars($l['module'] ?? '') ?></span></td>
      <td><?= $l['record_id'] ?: '-' ?></td>
      <td>
        <?php $action_colors = ['CREATE'=>'badge-success','UPDATE'=>'badge-info','DELETE'=>'badge-danger','LOGIN'=>'badge-warning','LOGOUT'=>'badge-secondary','EXPORT'=>'badge-secondary']; ?>
        <span class="badge <?= $action_colors[$l['action']] ?? 'badge-secondary' ?>"><?= $l['action'] ?></span>
      </td>
      <td style="font-size:12px;"><?= htmlspecialchars($l['ip_address'] ?? '-') ?></td>
      <td style="font-size:11px;max-width:300px;overflow:hidden;text-overflow:ellipsis;">
        <?php if ($l['new_values']): ?>
          <span class="text-muted"><?= htmlspecialchars(substr($l['new_values'], 0, 120)) ?>...</span>
        <?php endif; ?>
      </td>
    </tr>
  <?php endforeach; ?>
  <?php if (empty($logs)): ?>
    <tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No audit log entries found.</td></tr>
  <?php endif; ?>
  </tbody>
</table>
</div>
</div>

<?php if ($pg['total_pages'] > 1): ?>
<div class="pagination">
  <?php for ($i = 1; $i <= min($pg['total_pages'],20); $i++): ?>
    <a href="?module=<?= urlencode($filter_module) ?>&action_type=<?= urlencode($filter_action) ?>&user_id=<?= $filter_user ?>&date=<?= urlencode($filter_date) ?>&page=<?= $i ?>" class="page-link <?= $i === $page ? 'active' : '' ?>"><?= $i ?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?= count($logs) ?> of <?= $total ?></span>
</div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>
