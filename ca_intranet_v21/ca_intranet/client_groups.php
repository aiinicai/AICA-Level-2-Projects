<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner','supervisor'])) { header('Location: '.url('dashboard.php')); exit; }
$db = getDB();
$page_title = 'Client Groups';

// ── ADD SINGLE GROUP ──────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['add_group'])) {
    $name = trim($_POST['group_name'] ?? '');
    if ($name) {
        try {
            $db->prepare("INSERT INTO client_groups (group_name) VALUES (?)")->execute([$name]);
            auditLog('client_groups', $db->lastInsertId(), 'CREATE');
            $_SESSION['flash_msg'] = "Group '$name' added."; $_SESSION['flash_type'] = 'success';
        } catch (Exception $e) {
            $_SESSION['flash_msg'] = 'Group already exists or error occurred.'; $_SESSION['flash_type'] = 'error';
        }
    }
    header('Location: '.url('client_groups.php')); exit;
}

// ── DELETE GROUP ───────────────────────────────────────────
if (isset($_GET['delete'])) {
    $gid = intval($_GET['delete']);
    $db->prepare("UPDATE clients SET group_id=NULL WHERE group_id=?")->execute([$gid]);
    $db->prepare("DELETE FROM client_groups WHERE id=?")->execute([$gid]);
    auditLog('client_groups', $gid, 'DELETE');
    $_SESSION['flash_msg'] = 'Group deleted.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('client_groups.php')); exit;
}

// ── BULK IMPORT GROUPS FROM CSV ───────────────────────────
$import_results = [];
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['group_file'])) {
    $file = $_FILES['group_file'];
    if ($file['error'] === 0) {
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if ($ext === 'csv') {
            $handle = fopen($file['tmp_name'], 'r');
            fgetcsv($handle); // skip header
            $added = 0; $skipped = 0;
            while (($row = fgetcsv($handle)) !== false) {
                $name = trim($row[0] ?? '');
                if (!$name) continue;
                $chk = $db->prepare("SELECT id FROM client_groups WHERE group_name=?");
                $chk->execute([$name]);
                if ($chk->fetch()) { $skipped++; continue; }
                $db->prepare("INSERT INTO client_groups (group_name) VALUES (?)")->execute([$name]);
                $added++;
            }
            fclose($handle);
            auditLog('client_groups', 0, 'IMPORT', null, ['added'=>$added,'skipped'=>$skipped]);
            $_SESSION['flash_msg'] = "Import complete: $added groups added, $skipped already existed.";
            $_SESSION['flash_type'] = 'success';
        } else {
            $_SESSION['flash_msg'] = 'Please upload a CSV file.'; $_SESSION['flash_type'] = 'error';
        }
    }
    header('Location: '.url('client_groups.php')); exit;
}

// ── TEMPLATE DOWNLOAD ─────────────────────────────────────
if (isset($_GET['download_template'])) {
    require_once __DIR__.'/includes/export.php';
    startCSVDownload('client_groups_template');
    $out = fopen('php://output','w');
    writeCSVRow($out, ['group_name']);
    writeCSVRow($out, ['Sharma Family Group']);
    writeCSVRow($out, ['ABC Industries Group']);
    fclose($out); exit;
}

$groups = $db->query(
    "SELECT g.*, COUNT(c.id) as client_count
     FROM client_groups g LEFT JOIN clients c ON c.group_id = g.id
     GROUP BY g.id ORDER BY g.group_name"
)->fetchAll();

include 'includes/header.php';
?>
<div class="page-header">
  <div>
    <div class="page-title">🏷 Client Groups</div>
    <div class="page-subtitle">Total: <?= count($groups) ?> groups — used for grouping related clients in the IT Return Register</div>
  </div>
  <a href="<?= url('clients.php') ?>" class="btn btn-outline">← Back to Clients</a>
</div>

<div class="dash-grid">

  <div class="card">
    <div class="card-header"><span class="card-title">➕ Add Single Group</span></div>
    <div class="card-body">
      <form method="post">
        <div class="form-group mb-2">
          <label>Group Name <span class="req">*</span></label>
          <input class="form-control" name="group_name" required placeholder="e.g. Sharma Family Group">
        </div>
        <button class="btn btn-primary" type="submit" name="add_group" value="1">Add Group</button>
      </form>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="card-title">📥 Bulk Import Groups from Excel/CSV</span></div>
    <div class="card-body">
      <div style="background:var(--primary-bg);padding:10px;border-radius:6px;font-size:12px;margin-bottom:10px">
        Download the template, add one group name per row, save as CSV, then upload.
      </div>
      <a href="<?= url('client_groups.php?download_template=1') ?>" class="btn btn-export mb-2">⬇ Download Template</a>
      <form method="post" enctype="multipart/form-data">
        <div class="form-group mb-2">
          <input type="file" name="group_file" accept=".csv" class="form-control" style="height:auto;padding:6px">
        </div>
        <button class="btn btn-primary" type="submit">⬆ Upload &amp; Import</button>
      </form>
    </div>
  </div>

</div>

<div class="card mt-2">
  <div class="card-header"><span class="card-title">All Groups</span></div>
  <div class="table-responsive">
  <table class="data-table">
    <thead><tr><th>#</th><th>Group Name</th><th>Clients in Group</th><th>Actions</th></tr></thead>
    <tbody>
    <?php foreach ($groups as $i => $g): ?>
      <tr>
        <td><?= $i+1 ?></td>
        <td><strong><?= htmlspecialchars($g['group_name']) ?></strong></td>
        <td><span class="badge badge-primary"><?= $g['client_count'] ?> clients</span></td>
        <td>
          <a href="<?= url('clients.php?search='.urlencode($g['group_name'])) ?>" class="btn btn-outline btn-sm">View Clients</a>
          <?php if ($g['client_count'] == 0): ?>
            <a href="<?= url('client_groups.php?delete='.$g['id']) ?>" class="btn btn-danger btn-sm" onclick="return confirm('Delete this group?')">Delete</a>
          <?php endif; ?>
        </td>
      </tr>
    <?php endforeach; ?>
    <?php if (empty($groups)): ?>
      <tr><td colspan="4" class="text-center text-muted" style="padding:2rem">No groups yet. Add one above.</td></tr>
    <?php endif; ?>
    </tbody>
  </table>
  </div>
</div>

<?php include 'includes/footer.php'; ?>
