<?php
// logout.php — destroy session and redirect to login cleanly
require_once __DIR__ . '/includes/config.php';

// Start session WITHOUT the timeout redirect check
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    session_start();
}

// Log the logout event before destroying session
if (isset($_SESSION['user_id'])) {
    auditLog('auth', $_SESSION['user_id'], 'LOGOUT');
}

// Destroy session completely
$_SESSION = [];
if (ini_get('session.use_cookies')) {
    $p = session_get_cookie_params();
    setcookie(session_name(), '', time() - 42000,
        $p['path'], $p['domain'], $p['secure'], $p['httponly']);
}
session_destroy();

// Redirect to login — use absolute path to avoid any BASE issues
header('Location: ' . url('login.php'));
exit;
