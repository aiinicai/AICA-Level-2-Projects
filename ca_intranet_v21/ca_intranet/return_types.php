<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if(!hasRole(['admin','partner'])){ header('Location: '.url('dashboard.php'));exit; }
$db=getDB();$page_title='Return Type Settings';

// ── SAVE GST TYPE ─────────────────────────────────────────
if($_SERVER['REQUEST_METHOD']==='POST'&&isset($_POST['save_gst'])){
    $d=$_POST;
    if($_POST['gst_id']??0){
        $db->prepare("UPDATE gst_return_types SET return_name=?,periodicity=?,description=?,is_active=?,sort_order=? WHERE id=?")
           ->execute([$d['return_name'],$d['periodicity'],$d['description'],isset($d['is_active'])?1:0,intval($d['sort_order']),$d['gst_id']]);
    } else {
        $db->prepare("INSERT INTO gst_return_types(return_name,periodicity,description,is_active,sort_order) VALUES(?,?,?,?,?)")
           ->execute([$d['return_name'],$d['periodicity'],$d['description']??'',1,intval($d['sort_order']??0)]);
    }
    $_SESSION['flash_msg']='GST return type saved.';$_SESSION['flash_type']='success';
    header('Location: '.url('return_types.php'));exit;
}

// ── SAVE TDS TYPE ─────────────────────────────────────────
if($_SERVER['REQUEST_METHOD']==='POST'&&isset($_POST['save_tds'])){
    $d=$_POST;
    if($_POST['tds_id']??0){
        $db->prepare("UPDATE tds_return_types SET form_name=?,description=?,is_active=?,sort_order=? WHERE id=?")
           ->execute([$d['form_name'],$d['description'],isset($d['is_active'])?1:0,intval($d['sort_order']),$d['tds_id']]);
    } else {
        $db->prepare("INSERT INTO tds_return_types(form_name,description,is_active,sort_order) VALUES(?,?,?,?)")
           ->execute([$d['form_name'],$d['description']??'',1,intval($d['sort_order']??0)]);
    }
    $_SESSION['flash_msg']='TDS return type saved.';$_SESSION['flash_type']='success';
    header('Location: '.url('return_types.php'));exit;
}

$gst_types=$db->query("SELECT * FROM gst_return_types ORDER BY sort_order,return_name")->fetchAll();
$tds_types=$db->query("SELECT * FROM tds_return_types ORDER BY sort_order,form_name")->fetchAll();
$edit_gst_id=intval($_GET['edit_gst']??0);
$edit_tds_id=intval($_GET['edit_tds']??0);
$edit_gst=$edit_gst_id?array_values(array_filter($gst_types,fn($r)=>$r['id']==$edit_gst_id))[0]??[]:[];
$edit_tds=$edit_tds_id?array_values(array_filter($tds_types,fn($r)=>$r['id']==$edit_tds_id))[0]??[]:[];

include 'includes/header.php';
?>
<div class="page-header"><div class="page-title">⚙ Return Type Settings</div></div>
<div class="dash-grid">

<div class="card">
  <div class="card-header"><span class="card-title">📊 GST Return Types</span></div>
  <div class="card-body">
    <form method="post" style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--border-lt)">
      <input type="hidden" name="gst_id" value="<?=$edit_gst['id']??0?>">
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Return Name <span class="req">*</span></label>
          <input class="form-control" name="return_name" required value="<?=htmlspecialchars($edit_gst['return_name']??'')?>" placeholder="e.g. GSTR-1"></div>
        <div class="form-group"><label>Periodicity <span class="req">*</span></label>
          <select class="form-control" name="periodicity" required>
            <?php foreach(['Monthly','Quarterly','Annually','Event-based'] as $p): ?>
              <option value="<?=$p?>" <?=($edit_gst['periodicity']??'')===$p?'selected':''?>><?=$p?></option>
            <?php endforeach; ?>
          </select></div>
        <div class="form-group" style="grid-column:span 2"><label>Description</label>
          <input class="form-control" name="description" value="<?=htmlspecialchars($edit_gst['description']??'')?>"></div>
        <div class="form-group"><label>Sort Order</label>
          <input class="form-control" type="number" name="sort_order" value="<?=$edit_gst['sort_order']??0?>"></div>
        <div class="form-group" style="justify-content:flex-end;flex-direction:row;align-items:center;gap:8px">
          <input type="checkbox" name="is_active" value="1" id="gst_active" <?=($edit_gst['is_active']??1)?'checked':''?>>
          <label for="gst_active" style="text-transform:none;font-size:13px">Active</label>
        </div>
      </div>
      <div class="form-actions" style="padding-top:0.5rem">
        <button class="btn btn-primary btn-sm" name="save_gst" value="1">💾 <?=$edit_gst_id?'Update':'Add New'?></button>
        <?php if($edit_gst_id): ?><a href="<?=url('return_types.php')?>" class="btn btn-outline btn-sm">Cancel</a><?php endif; ?>
      </div>
    </form>
    <table class="data-table" style="font-size:12px">
      <thead><tr><th>Name</th><th>Periodicity</th><th>Description</th><th>Status</th><th>Edit</th></tr></thead>
      <tbody>
      <?php foreach($gst_types as $r): ?>
        <tr><td><strong><?=htmlspecialchars($r['return_name'])?></strong></td>
          <td><span class="badge badge-info"><?=$r['periodicity']?></span></td>
          <td><?=htmlspecialchars($r['description']??'')?></td>
          <td><?=$r['is_active']?'<span class="badge badge-success">Active</span>':'<span class="badge badge-secondary">Inactive</span>'?></td>
          <td><a href="<?=url('return_types.php?edit_gst=').$r['id']?>" class="btn btn-outline btn-sm">Edit</a></td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>

<div class="card">
  <div class="card-header"><span class="card-title">📋 TDS / ETDS Return Types</span></div>
  <div class="card-body">
    <form method="post" style="margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid var(--border-lt)">
      <input type="hidden" name="tds_id" value="<?=$edit_tds['id']??0?>">
      <div class="form-grid form-grid-2">
        <div class="form-group"><label>Form Name <span class="req">*</span></label>
          <input class="form-control" name="form_name" required value="<?=htmlspecialchars($edit_tds['form_name']??'')?>" placeholder="e.g. 26Q"></div>
        <div class="form-group"><label>Sort Order</label>
          <input class="form-control" type="number" name="sort_order" value="<?=$edit_tds['sort_order']??0?>"></div>
        <div class="form-group" style="grid-column:span 2"><label>Description</label>
          <input class="form-control" name="description" value="<?=htmlspecialchars($edit_tds['description']??'')?>"></div>
        <div class="form-group" style="flex-direction:row;align-items:center;gap:8px">
          <input type="checkbox" name="is_active" value="1" id="tds_active" <?=($edit_tds['is_active']??1)?'checked':''?>>
          <label for="tds_active" style="text-transform:none;font-size:13px">Active</label>
        </div>
      </div>
      <div class="form-actions" style="padding-top:0.5rem">
        <button class="btn btn-primary btn-sm" name="save_tds" value="1">💾 <?=$edit_tds_id?'Update':'Add New'?></button>
        <?php if($edit_tds_id): ?><a href="<?=url('return_types.php')?>" class="btn btn-outline btn-sm">Cancel</a><?php endif; ?>
      </div>
    </form>
    <table class="data-table" style="font-size:12px">
      <thead><tr><th>Form</th><th>Description</th><th>Status</th><th>Edit</th></tr></thead>
      <tbody>
      <?php foreach($tds_types as $r): ?>
        <tr><td><strong><?=htmlspecialchars($r['form_name'])?></strong></td>
          <td><?=htmlspecialchars($r['description']??'')?></td>
          <td><?=$r['is_active']?'<span class="badge badge-success">Active</span>':'<span class="badge badge-secondary">Inactive</span>'?></td>
          <td><a href="<?=url('return_types.php?edit_tds=').$r['id']?>" class="btn btn-outline btn-sm">Edit</a></td>
        </tr>
      <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>

</div>
<?php include 'includes/footer.php'; ?>
