<?php
// login.php
require_once __DIR__ . '/includes/config.php';

// Start session manually — NOT using startSecureSession() to avoid timeout loop
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    ini_set('session.use_strict_mode', 1);
    session_start();
}

// Already logged in — go to dashboard
if (!empty($_SESSION['user_id'])) {
    header('Location: ' . url('dashboard.php'));
    exit;
}

$error   = '';
$timeout = isset($_GET['timeout']);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $username = trim($_POST['username'] ?? '');
    $password = $_POST['password'] ?? '';

    if ($username && $password) {
        $db   = getDB();
        $stmt = $db->prepare("SELECT * FROM users WHERE username = ? AND is_active = 1");
        $stmt->execute([$username]);
        $user = $stmt->fetch();

        if ($user && password_verify($password, $user['password'])) {
            // Regenerate session ID to prevent fixation
            session_regenerate_id(true);
            $_SESSION['user_id']       = $user['id'];
            $_SESSION['username']      = $user['username'];
            $_SESSION['name']          = $user['name'];
            $_SESSION['role']          = $user['role'];
            $_SESSION['last_activity'] = time();
            auditLog('auth', $user['id'], 'LOGIN');
            header('Location: ' . url('dashboard.php'));
            exit;
        } else {
            $error = 'Invalid username or password.';
        }
    } else {
        $error = 'Please enter both username and password.';
    }
}

// Get firm name — try DB first, fall back to config constant
try {
    $firm = firmName();
} catch (Exception $e) {
    $firm = defined('FIRM_NAME') ? FIRM_NAME : 'CA Firm Intranet';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login — <?= htmlspecialchars($firm) ?></title>
<link rel="stylesheet" href="<?= url('assets/css/app.css') ?>">
</head>
<body>
<div class="login-wrap">
  <div class="login-card">
    <div class="login-logo">
      <div class="icon">⚖️</div>
      <h1><?= htmlspecialchars($firm) ?></h1>
      <p>Compliance Management Intranet</p>
    </div>

    <?php if ($timeout): ?>
      <div class="flash flash-warning" style="margin-bottom:1rem;font-size:12px;">
        Session expired. Please log in again.
      </div>
    <?php endif; ?>

    <?php if ($error): ?>
      <div class="flash flash-error" style="margin-bottom:1rem;font-size:12px;">
        <?= htmlspecialchars($error) ?>
      </div>
    <?php endif; ?>

    <form method="post" action="<?= url('login.php') ?>">
      <div class="form-group" style="margin-bottom:1rem;">
        <label>Username</label>
        <input class="form-control" type="text" name="username" autofocus
               autocomplete="username"
               value="<?= htmlspecialchars($_POST['username'] ?? '') ?>">
      </div>
      <div class="form-group" style="margin-bottom:1.25rem;">
        <label>Password</label>
        <input class="form-control" type="password" name="password"
               autocomplete="current-password">
      </div>
      <button class="btn btn-primary w-100" type="submit"
              style="justify-content:center;">Login</button>
    </form>

    <p style="text-align:center;font-size:11px;color:var(--text-muted);margin-top:1rem;">
      Default password: <code>password</code> — change after first login
    </p>
    <div style="margin-top:16px;padding-top:16px;border-top:1px solid #eee;text-align:center;">
      <a href="<?= url('sop_hub.html') ?>"
         style="display:inline-flex;align-items:center;gap:8px;font-size:16px;font-weight:600;
                color:#1a4b8c;background:#e6f1fb;padding:12px 24px;border-radius:10px;
                text-decoration:none;border:1px solid #c8ddf3;">
        📚 Browse SOP Hub
      </a>
      <div style="font-size:12px;color:var(--text-muted);margin-top:6px;">No login required</div>
    </div>
  </div>
</div>
</body>
</html>
