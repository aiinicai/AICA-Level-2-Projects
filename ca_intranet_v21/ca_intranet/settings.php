<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner'])) { header('Location: '.url('dashboard.php')); exit; }
$db = getDB(); $page_title = 'Firm Settings';

$registers = [
    'gst'  => ['label' => '📊 GST Returns',       'periodicity' => 'monthly_quarterly'],
    'etds' => ['label' => '📋 ETDS Returns',      'periodicity' => 'quarterly'],
    'itr'  => ['label' => '🧾 IT Return Register','periodicity' => 'annual'],
    'roc'  => ['label' => '🏢 ROC Compliance',    'periodicity' => 'annual'],
];

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Firm info fields
    $fields = ['firm_name','firm_address','firm_phone','firm_email','firm_gstin','firm_pan','app_version'];
    foreach ($fields as $k) {
        $v = trim($_POST[$k] ?? '');
        $db->prepare("INSERT INTO app_settings(setting_key,setting_value,updated_by) VALUES(?,?,?)
                      ON DUPLICATE KEY UPDATE setting_value=?,updated_by=?")
           ->execute([$k,$v,$_SESSION['user_id'],$v,$_SESSION['user_id']]);
    }
    // Per-register default FY / period
    foreach (array_keys($registers) as $reg) {
        foreach (['fy','period'] as $suffix) {
            $key = "default_{$suffix}_{$reg}";
            $v = trim($_POST[$key] ?? '');
            $db->prepare("INSERT INTO app_settings(setting_key,setting_value,updated_by) VALUES(?,?,?)
                          ON DUPLICATE KEY UPDATE setting_value=?,updated_by=?")
               ->execute([$key,$v,$_SESSION['user_id'],$v,$_SESSION['user_id']]);
        }
    }
    auditLog('settings', 0, 'UPDATE');
    $_SESSION['flash_msg'] = 'Settings saved.'; $_SESSION['flash_type'] = 'success';
    header('Location: '.url('settings.php')); exit;
}

// Quick-set a register's period via link
if (isset($_GET['quickset_reg'], $_GET['quickset_val'])) {
    $reg = preg_replace('/[^a-z]/', '', $_GET['quickset_reg']);
    if (array_key_exists($reg, $registers)) {
        $val = trim($_GET['quickset_val']);
        $db->prepare("INSERT INTO app_settings(setting_key,setting_value,updated_by) VALUES(?,?,?)
                      ON DUPLICATE KEY UPDATE setting_value=?,updated_by=?")
           ->execute(["default_period_$reg",$val,$_SESSION['user_id'],$val,$_SESSION['user_id']]);
        $_SESSION['flash_msg'] = ucfirst($reg)." period set to $val."; $_SESSION['flash_type'] = 'success';
    }
    header('Location: '.url('settings.php')); exit;
}

$s = [];
foreach ($db->query("SELECT setting_key,setting_value FROM app_settings")->fetchAll() as $r)
    $s[$r['setting_key']] = $r['setting_value'];

$fy_list = getFYList();

include 'includes/header.php';
?>
<div class="page-header"><div class="page-title">⚙ Firm Settings</div></div>

<div class="card mb-2">
  <div class="card-header"><span class="card-title">🏢 Firm Information</span></div>
  <div class="card-body">
  <form method="post" id="settings-form">
    <div class="form-grid form-grid-2">
      <div class="form-group" style="grid-column:span 2">
        <label>Firm Name <span class="req">*</span></label>
        <input class="form-control" name="firm_name" required value="<?= htmlspecialchars($s['firm_name']??'') ?>">
      </div>
      <div class="form-group" style="grid-column:span 2">
        <label>Address</label>
        <textarea class="form-control" name="firm_address" rows="2"><?= htmlspecialchars($s['firm_address']??'') ?></textarea>
      </div>
      <div class="form-group">
        <label>Phone</label>
        <input class="form-control" name="firm_phone" value="<?= htmlspecialchars($s['firm_phone']??'') ?>">
      </div>
      <div class="form-group">
        <label>Email</label>
        <input class="form-control" type="email" name="firm_email" value="<?= htmlspecialchars($s['firm_email']??'') ?>">
      </div>
      <div class="form-group">
        <label>Firm GSTIN</label>
        <input class="form-control" name="firm_gstin" style="text-transform:uppercase" value="<?= htmlspecialchars($s['firm_gstin']??'') ?>">
      </div>
      <div class="form-group">
        <label>Firm PAN</label>
        <input class="form-control" name="firm_pan" style="text-transform:uppercase" value="<?= htmlspecialchars($s['firm_pan']??'') ?>">
      </div>
      <div class="form-group">
        <label>App Version <small class="text-muted">(shown in footer — update this yourself when you consider a milestone reached)</small></label>
        <input class="form-control" name="app_version" value="<?= htmlspecialchars($s['app_version']??'1.0') ?>" placeholder="e.g. 1.0" style="max-width:120px">
      </div>
    </div>
  </div>
</div>

<div class="card-header" style="margin-top:1.5rem;border-radius:8px 8px 0 0">
  <span class="card-title">📅 Default Period — Per Register</span>
</div>
<p class="text-muted" style="font-size:12px;margin:8px 2px 14px">
  Each register has its own independent default period. For example, your IT Return Register can stay on
  <strong>FY 2025-26</strong> while GST Returns moves ahead to <strong>FY 2026-27</strong> — they no longer share one setting.
  This is pre-selected for all users when they open that specific register.
</p>

<div class="dash-grid">
<?php foreach ($registers as $reg => $info):
    $cur_fy = $s["default_fy_$reg"] ?? currentFY();
    $month_periods = getMonthPeriods($cur_fy);
    $qtr_periods   = getQuarterPeriods($cur_fy);
    $cur_period    = $s["default_period_$reg"] ?? '';
?>
  <div class="card">
    <div class="card-header"><span class="card-title"><?= $info['label'] ?></span></div>
    <div class="card-body">

      <div style="text-align:center;padding:0.75rem 0 1rem;border-bottom:1px solid var(--border-lt);margin-bottom:1rem">
        <div style="font-size:24px;font-weight:700;color:var(--primary)"><?= htmlspecialchars($cur_period ?: '— Not set —') ?></div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:2px">FY <?= htmlspecialchars($cur_fy) ?></div>
      </div>

      <div class="form-group mb-2">
        <label>Financial Year</label>
        <select class="form-control" name="default_fy_<?= $reg ?>" form="settings-form" id="fy_<?= $reg ?>">
          <?php foreach ($fy_list as $fy): ?>
            <option value="<?= $fy ?>" <?= $cur_fy===$fy?'selected':'' ?>><?= $fy ?></option>
          <?php endforeach; ?>
        </select>
      </div>

      <?php if ($info['periodicity'] !== 'annual'): ?>
      <div class="form-group mb-2">
        <label>Default Period <small class="text-muted">(month<?= $info['periodicity']==='monthly_quarterly'?' or quarter':'' ?>)</small></label>
        <select class="form-control" name="default_period_<?= $reg ?>" form="settings-form">
          <optgroup label="Monthly">
            <?php foreach ($month_periods as $mp): ?>
              <option value="<?= $mp ?>" <?= $cur_period===$mp?'selected':'' ?>><?= $mp ?></option>
            <?php endforeach; ?>
          </optgroup>
          <?php if ($info['periodicity'] === 'monthly_quarterly'): ?>
          <optgroup label="Quarterly">
            <?php foreach ($qtr_periods as $qp): ?>
              <option value="<?= $qp ?>" <?= $cur_period===$qp?'selected':'' ?>><?= $qp ?></option>
            <?php endforeach; ?>
          </optgroup>
          <?php endif; ?>
        </select>
      </div>
      <div style="font-size:11px;color:var(--text-muted)">
        <strong>Quick set:</strong>
        <?php foreach (array_slice($month_periods, 0, 3) as $mp): ?>
          <a href="?quickset_reg=<?= $reg ?>&quickset_val=<?= urlencode($mp) ?>" class="btn btn-outline btn-sm" style="margin:2px 2px 0 0;padding:2px 8px"><?= $mp ?></a>
        <?php endforeach; ?>
      </div>
      <?php else: ?>
      <input type="hidden" name="default_period_<?= $reg ?>" value="<?= htmlspecialchars($cur_fy) ?>" form="settings-form">
      <div style="font-size:11px;color:var(--text-muted);padding:8px;background:var(--primary-bg);border-radius:6px">
        Annual register — only Financial Year applies here.
      </div>
      <?php endif; ?>

    </div>
  </div>
<?php endforeach; ?>
</div>

<div class="form-actions mt-2">
  <button class="btn btn-primary" type="submit" form="settings-form">💾 Save All Settings</button>
</div>

<?php include 'includes/footer.php'; ?>
