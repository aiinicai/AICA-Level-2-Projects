<?php
require_once __DIR__ . '/includes/config.php';
// Start session manually — avoid timeout loop on entry point
if (session_status() === PHP_SESSION_NONE) {
    ini_set('session.cookie_httponly', 1);
    session_start();
}
if (!empty($_SESSION['user_id'])) {
    header('Location: ' . url('dashboard.php'));
} else {
    header('Location: ' . url('login.php'));
}
exit;
