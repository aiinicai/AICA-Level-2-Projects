<?php
$current_user=currentUser();
$current_page=basename($_SERVER['PHP_SELF'],'.php');
$firm=firmName();
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title><?=htmlspecialchars($page_title??APP_NAME)?> — <?=htmlspecialchars($firm)?></title>
<link rel="stylesheet" href="<?=url('assets/css/app.css')?>">
</head>
<body>
<nav class="navbar">
  <div class="navbar-brand">
    <span class="brand-icon">⚖</span>
    <span class="brand-name"><?=htmlspecialchars($firm)?></span>
    <span class="brand-sub">Intranet</span>
  </div>
  <div class="navbar-links">
    <a href="<?=url('dashboard.php')?>" class="nav-link <?=$current_page==='dashboard'?'active':''?>">⊞ Dashboard</a>
    <a href="<?=url('clients.php')?>" class="nav-link <?=$current_page==='clients'?'active':''?>">👥 Clients</a>
    <a href="<?=url('sop_hub.html')?>" class="nav-link" target="_blank">📚 SOP Hub</a>
    <a href="http://192.168.3.102:3000" class="nav-link" target="_blank">💬 Jamku Pulse</a>
    <a href="http://192.168.3.52:3000" class="nav-link" target="_blank">💬 Chatwoot</a>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=$current_page==='itr_register'?'active':''?>">🧾 IT Return ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('itr_register.php')?>" class="dropdown-item">IT Return Register</a>
        <a href="<?=url('itr_register.php?stage=data')?>" class="dropdown-item">① Add Data Receipt</a>
        <a href="<?=url('itr_import.php')?>" class="dropdown-item">📥 Import from Computax</a>
        <a href="<?=url('client_groups.php')?>" class="dropdown-item">🏷 Manage Client Groups</a>
      </div>
    </div>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=$current_page==='gst_register'?'active':''?>">📊 GST ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('gst_register.php')?>" class="dropdown-item">GST Return Register</a>
        <a href="<?=url('gst_register.php?action=bulk_create')?>" class="dropdown-item">Bulk Create Entries</a>
        <a href="<?=url('gst_import.php')?>" class="dropdown-item">📥 Import Return Data</a>
      </div>
    </div>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=$current_page==='etds_register'?'active':''?>">📋 ETDS ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('etds_register.php')?>" class="dropdown-item">ETDS Return Register</a>
        <a href="<?=url('etds_register.php?stage=data')?>" class="dropdown-item">① Add Data Receipt</a>
        <a href="<?=url('etds_register.php?action=bulk_create')?>" class="dropdown-item">⚡ Bulk Create</a>
      </div>
    </div>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=$current_page==='ptax_register'?'active':''?>">💼 Prof Tax ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('ptax_register.php')?>" class="dropdown-item">PT Register (PTEC + PTRC)</a>
        <a href="<?=url('ptax_register.php?action=bulk_create')?>" class="dropdown-item">Bulk Create</a>
      </div>
    </div>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=$current_page==='roc_register'?'active':''?>">🏢 ROC ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('roc_register.php')?>" class="dropdown-item">ROC Compliance Register</a>
        <a href="<?=url('roc_register.php?action=bulk_create')?>" class="dropdown-item">Bulk Create</a>
      </div>
    </div>
    <?php if(hasRole(['admin','partner'])): ?>
    <div class="nav-dropdown">
      <a href="#" class="nav-link <?=in_array($current_page,['users','audit_log','settings','return_types'])?'active':''?>">⚙ Admin ▾</a>
      <div class="dropdown-menu">
        <a href="<?=url('users.php')?>" class="dropdown-item">User Management</a>
        <a href="<?=url('import.php')?>" class="dropdown-item">Import Clients / Users</a>
        <a href="<?=url('return_types.php')?>" class="dropdown-item">Return Type Settings</a>
        <a href="<?=url('settings.php')?>" class="dropdown-item">Firm Settings</a>
        <a href="<?=url('audit_log.php')?>" class="dropdown-item">Audit Log</a>
      </div>
    </div>
    <?php endif; ?>
  </div>
  <div class="navbar-user">
    <span class="user-badge role-<?=$current_user['role']??''?>"><?=ucfirst($current_user['role']??'')?></span>
    <span class="user-name"><?=htmlspecialchars($current_user['name']??'')?></span>
    <a href="<?=url('logout.php')?>" class="btn-logout">Logout</a>
  </div>
</nav>
<div class="page-wrapper">
<?php if(isset($_SESSION['flash_msg'])): ?>
  <div class="flash flash-<?=$_SESSION['flash_type']??'info'?>">
    <?=htmlspecialchars($_SESSION['flash_msg'])?>
    <button class="flash-close" onclick="this.parentElement.remove()">×</button>
  </div>
  <?php unset($_SESSION['flash_msg'],$_SESSION['flash_type']); ?>
<?php endif; ?>
