<?php
require_once __DIR__ . '/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner'])) {
    $_SESSION['flash_msg'] = 'Access denied.'; $_SESSION['flash_type'] = 'error';
    header('Location: '.url('dashboard.php')); exit;
}
$db = getDB();
$page_title = 'User Management';
$action = $_GET['action'] ?? 'list';
$id     = intval($_GET['id'] ?? 0);

// ── SAVE ──────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $d = $_POST;
    $data = [
        'name'      => trim($d['name'] ?? ''),
        'username'  => strtolower(trim($d['username'] ?? '')),
        'role'      => $d['role'] ?? 'staff',
        'email'     => trim($d['email'] ?? ''),
        'mobile'    => trim($d['mobile'] ?? ''),
        'is_active' => isset($d['is_active']) ? 1 : 0,
    ];
    // Only admin can create/edit admin/partner roles
    if (!hasRole('admin') && in_array($data['role'], ['admin','partner'])) {
        $_SESSION['flash_msg'] = 'Only admin can assign admin/partner roles.';
        $_SESSION['flash_type'] = 'error';
        header('Location: '.url('users.php')); exit;
    }
    if ($id) {
        // Update - password optional
        if (!empty($d['password'])) {
            $data['password'] = password_hash($d['password'], PASSWORD_DEFAULT);
        }
        $cols = implode(' = ?, ', array_keys($data)) . ' = ?';
        $stmt = $db->prepare("UPDATE users SET $cols WHERE id = ?");
        $stmt->execute(array_merge(array_values($data), [$id]));
        auditLog('users', $id, 'UPDATE');
        $_SESSION['flash_msg'] = 'User updated.'; $_SESSION['flash_type'] = 'success';
    } else {
        if (empty($d['password'])) {
            $_SESSION['flash_msg'] = 'Password is required for new users.'; $_SESSION['flash_type'] = 'error';
            header('Location: '.url('users.php?action=add')); exit;
        }
        $data['password'] = password_hash($d['password'], PASSWORD_DEFAULT);
        $cols = implode(', ', array_keys($data));
        $ph   = implode(', ', array_fill(0, count($data), '?'));
        $stmt = $db->prepare("INSERT INTO users ($cols) VALUES ($ph)");
        $stmt->execute(array_values($data));
        auditLog('users', $db->lastInsertId(), 'CREATE');
        $_SESSION['flash_msg'] = 'User created.'; $_SESSION['flash_type'] = 'success';
    }
    header('Location: '.url('users.php')); exit;
}

$user = [];
if ($action === 'edit' && $id) {
    $stmt = $db->prepare("SELECT * FROM users WHERE id = ?");
    $stmt->execute([$id]); $user = $stmt->fetch() ?: [];
}

$users = $db->query("SELECT * FROM users ORDER BY role, name")->fetchAll();

include 'includes/header.php';
?>

<?php if ($action === 'list'): ?>
<div class="page-header">
  <div class="page-title">⚙ User Management</div>
  <a href="<?= url('users.php?action=add') ?>" class="btn btn-primary">+ Add User</a>
</div>
<div class="card">
<div class="table-responsive">
<table class="data-table">
  <thead>
    <tr><th>#</th><th>Name</th><th>Username</th><th>Role</th><th>Email</th><th>Mobile</th><th>Status</th><th>Actions</th></tr>
  </thead>
  <tbody>
  <?php foreach ($users as $i => $u): ?>
    <tr>
      <td><?= $i + 1 ?></td>
      <td><strong><?= htmlspecialchars($u['name']) ?></strong></td>
      <td><code><?= htmlspecialchars($u['username']) ?></code></td>
      <td><span class="badge role-badge-<?= $u['role'] ?>"><?= ucfirst($u['role']) ?></span></td>
      <td><?= htmlspecialchars($u['email'] ?: '-') ?></td>
      <td><?= htmlspecialchars($u['mobile'] ?: '-') ?></td>
      <td><?= $u['is_active'] ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-secondary">Inactive</span>' ?></td>
      <td><a href="<?= url('users.php?action=edit&id=') . $u['id'] ?>" class="btn btn-outline btn-sm">Edit</a></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
</div>
</div>

<?php else: ?>
<div class="page-header">
  <div class="page-title"><?= $action === 'edit' ? '✏️ Edit User' : '➕ Add User' ?></div>
  <a href="<?= url('users.php') ?>" class="btn btn-outline">← Back</a>
</div>
<div class="card" style="max-width:560px;">
<div class="card-body">
<form method="post">
  <div class="form-grid form-grid-2">
    <div class="form-group">
      <label>Full Name <span class="req">*</span></label>
      <input class="form-control" name="name" required value="<?= htmlspecialchars($user['name'] ?? '') ?>">
    </div>
    <div class="form-group">
      <label>Username <span class="req">*</span></label>
      <input class="form-control" name="username" required value="<?= htmlspecialchars($user['username'] ?? '') ?>" <?= $action === 'edit' ? 'readonly' : '' ?>>
    </div>
    <div class="form-group">
      <label><?= $action === 'edit' ? 'New Password (leave blank to keep)' : 'Password *' ?></label>
      <input class="form-control" type="password" name="password" autocomplete="new-password" <?= $action === 'add' ? 'required' : '' ?>>
    </div>
    <div class="form-group">
      <label>Role <span class="req">*</span></label>
      <select class="form-control" name="role" required>
        <?php $roles = hasRole('admin') ? ['admin','partner','supervisor','staff'] : ['supervisor','staff']; ?>
        <?php foreach ($roles as $r): ?>
          <option value="<?= $r ?>" <?= ($user['role'] ?? 'staff') === $r ? 'selected' : '' ?>><?= ucfirst($r) ?></option>
        <?php endforeach; ?>
      </select>
    </div>
    <div class="form-group">
      <label>Email</label>
      <input class="form-control" type="email" name="email" value="<?= htmlspecialchars($user['email'] ?? '') ?>">
    </div>
    <div class="form-group">
      <label>Mobile</label>
      <input class="form-control" name="mobile" value="<?= htmlspecialchars($user['mobile'] ?? '') ?>">
    </div>
  </div>
  <div class="form-group mt-1" style="flex-direction:row;align-items:center;gap:8px;">
    <input type="checkbox" name="is_active" value="1" id="is_active" <?= ($user['is_active'] ?? 1) ? 'checked' : '' ?>>
    <label for="is_active" style="text-transform:none;font-size:13px;letter-spacing:0;">Active User</label>
  </div>
  <div class="form-actions mt-2">
    <button class="btn btn-primary" type="submit">💾 Save</button>
    <a href="<?= url('users.php') ?>" class="btn btn-outline">Cancel</a>
  </div>
</form>
</div></div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>
