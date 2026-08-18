<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
$db=getDB();$page_title='Professional Tax Register';
$action=$_GET['action']??'list';$id=intval($_GET['id']??0);

// ── SAVE ─────────────────────────────────────────────────
if($_SERVER['REQUEST_METHOD']==='POST'&&$action!=='bulk_create'){
    $d=$_POST;
    $data=['client_id'=>intval($d['client_id']),'pt_type'=>$d['pt_type'],'financial_year'=>$d['financial_year'],
           'period'=>$d['period'],'due_date'=>$d['due_date']?:null,'amount'=>floatval($d['amount']??0),
           'payment_date'=>$d['payment_date']?:null,'challan_no'=>trim($d['challan_no']??''),
           'filed_date'=>$d['filed_date']?:null,'acknowledgement_no'=>trim($d['acknowledgement_no']??''),
           'prepared_by'=>$d['prepared_by']?:null,'prepared_date'=>$d['prepared_date']?:null,
           'status'=>$d['status']??'Pending','remarks'=>trim($d['remarks']??''),
           'assigned_to'=>$d['assigned_to']?:null,'created_by'=>$_SESSION['user_id']];
    if($id){
        $cols=implode('=?,',array_keys($data)).'=?';
        $db->prepare("UPDATE ptax_register SET $cols WHERE id=?")->execute([...array_values($data),$id]);
        auditLog('ptax_register',$id,'UPDATE');
        $_SESSION['flash_msg']='PT entry updated.';$_SESSION['flash_type']='success';
    } else {
        $cols=implode(',',array_keys($data));$ph=implode(',',array_fill(0,count($data),'?'));
        $db->prepare("INSERT INTO ptax_register($cols)VALUES($ph)")->execute(array_values($data));
        auditLog('ptax_register',$db->lastInsertId(),'CREATE');
        $_SESSION['flash_msg']='PT entry added.';$_SESSION['flash_type']='success';
    }
    header('Location: '.url('ptax_register.php'));exit;
}

// ── BULK CREATE ───────────────────────────────────────────
if($_SERVER['REQUEST_METHOD']==='POST'&&$action==='bulk_create'){
    $d=$_POST;$fy=$d['financial_year'];$pt_type=$d['pt_type'];$created=0;
    $fy_start=intval(substr($fy,0,4));
    $where_col=$pt_type==='PTEC'?'ptec_applicable':'ptrc_applicable';

    $selected_ids = array_filter(array_map('intval', $d['client_ids'] ?? []));
    if (!empty($selected_ids)) {
        $placeholders = implode(',', array_fill(0, count($selected_ids), '?'));
        $stmt = $db->prepare("SELECT * FROM clients WHERE $where_col=1 AND status='Active' AND id IN ($placeholders)");
        $stmt->execute($selected_ids);
    } else {
        $stmt = $db->query("SELECT * FROM clients WHERE $where_col=1 AND status='Active'");
    }
    $clients = $stmt->fetchAll();
    foreach($clients as $c){
        if($pt_type==='PTEC'){
            // One entry per year
            $chk=$db->prepare("SELECT id FROM ptax_register WHERE client_id=? AND pt_type='PTEC' AND financial_year=?");
            $chk->execute([$c['id'],$fy]);if($chk->fetch()) continue;
            $due=($fy_start+1).'-06-30';$period=$fy;
            $ins=$db->prepare("INSERT INTO ptax_register(client_id,pt_type,financial_year,period,due_date,status,created_by) VALUES(?,?,?,?,?,?,?)");
            $ins->execute([$c['id'],'PTEC',$fy,$period,$due,'Pending',$_SESSION['user_id']]);$created++;
        } else {
            // PTRC — Monthly or Annual
            if($c['ptrc_periodicity']==='Annual'){
                $chk=$db->prepare("SELECT id FROM ptax_register WHERE client_id=? AND pt_type='PTRC' AND financial_year=?");
                $chk->execute([$c['id'],$fy]);if($chk->fetch()) continue;
                $due=($fy_start+1).'-03-31';
                $db->prepare("INSERT INTO ptax_register(client_id,pt_type,financial_year,period,due_date,status,created_by) VALUES(?,?,?,?,?,?,?)")
                   ->execute([$c['id'],'PTRC',$fy,$fy,$due,'Pending',$_SESSION['user_id']]);$created++;
            } else {
                // Monthly - 12 entries
                $months=getMonthPeriods($fy);
                foreach($months as $mp){
                    $chk=$db->prepare("SELECT id FROM ptax_register WHERE client_id=? AND pt_type='PTRC' AND period=?");
                    $chk->execute([$c['id'],$mp]);if($chk->fetch()) continue;
                    $pts=explode('-',$mp);$dt=date_create("01 {$pts[0]} {$pts[1]}");
                    $due=$dt?date_format($dt,'Y-m-t'):null;
                    $db->prepare("INSERT INTO ptax_register(client_id,pt_type,financial_year,period,due_date,status,created_by) VALUES(?,?,?,?,?,?,?)")
                       ->execute([$c['id'],'PTRC',$fy,$mp,$due,'Pending',$_SESSION['user_id']]);$created++;
                }
            }
        }
    }
    $_SESSION['flash_msg']="Bulk create done: $created PT entries created.";$_SESSION['flash_type']='success';
    header('Location: '.url('ptax_register.php'));exit;
}

// ── FETCH EDIT ────────────────────────────────────────────
$entry=[];
if($action==='edit'&&$id){
    $stmt=$db->prepare("SELECT p.*,c.client_name,c.pan FROM ptax_register p JOIN clients c ON c.id=p.client_id WHERE p.id=?");
    $stmt->execute([$id]);$entry=$stmt->fetch()??[];
}

// ── LIST ─────────────────────────────────────────────────
$fpt=$_GET['pt_type']??'';$ffy=array_key_exists('fy',$_GET)?trim($_GET['fy']):currentFY();$fstatus=$_GET['status']??'';$fdue=$_GET['due']??'';
$page=max(1,intval($_GET['page']??1));$per=30;

$where=['1=1'];$wp=[];
if($ffy){$where[]='p.financial_year=?';$wp[]=$ffy;}
if($fpt){$where[]='p.pt_type=?';$wp[]=$fpt;}
if($fstatus){$where[]='p.status=?';$wp[]=$fstatus;}
if($fdue==='overdue'){$where[]='p.due_date<CURDATE() AND p.status!="Filed"';}
if($fdue==='15d'){$where[]='p.due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(),INTERVAL 15 DAY) AND p.status!="Filed"';}
if($_SESSION['role']==='supervisor'){$where[]='c.supervisor_id=?';$wp[]=$_SESSION['user_id'];}
if($_SESSION['role']==='staff'){$where[]='p.assigned_to=?';$wp[]=$_SESSION['user_id'];}
$ws=implode(' AND ',$where);

$total=$db->prepare("SELECT COUNT(*) FROM ptax_register p JOIN clients c ON c.id=p.client_id WHERE $ws");
$total->execute($wp);$total=$total->fetchColumn();
$pg=paginate($total,$per,$page);

$rows=$db->prepare("SELECT p.*,c.client_name,c.pan,s.name sname,u.name aname,pp.name prep_name
    FROM ptax_register p JOIN clients c ON c.id=p.client_id
    LEFT JOIN users s ON s.id=c.supervisor_id LEFT JOIN users u ON u.id=p.assigned_to
    LEFT JOIN users pp ON pp.id=p.prepared_by
    WHERE $ws ORDER BY p.due_date ASC,c.client_name ASC LIMIT ? OFFSET ?");
$rows->execute([...$wp,$per,$pg['offset']]);$entries=$rows->fetchAll();

$all_clients=$db->query("SELECT id,client_name,pan,ptec_applicable,ptrc_applicable,ptrc_periodicity,group_id FROM clients WHERE (ptec_applicable=1 OR ptrc_applicable=1) AND status='Active' ORDER BY client_name")->fetchAll();
$client_groups=$db->query("SELECT id,group_name FROM client_groups ORDER BY group_name")->fetchAll();
$all_users=$db->query("SELECT id,name FROM users WHERE is_active=1 ORDER BY name")->fetchAll();
$fy_list=getFYList();

include 'includes/header.php';
?>

<?php if($action==='bulk_create'): ?>
<div class="page-header"><div class="page-title">💼 PT Register — Bulk Create</div><a href="<?=url('ptax_register.php')?>" class="btn btn-outline">← Back</a></div>
<div class="card" style="max-width:720px"><div class="card-body">
<form method="post" action="<?=url('ptax_register.php?action=bulk_create')?>">
  <div class="form-grid form-grid-2">
    <div class="form-group"><label>Financial Year</label>
      <select class="form-control" name="financial_year" required>
        <?php foreach($fy_list as $fy): ?><option value="<?=$fy?>" <?=$fy===currentFY()?'selected':''?>><?=$fy?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>PT Type</label>
      <select class="form-control" name="pt_type" required>
        <option value="PTEC">PTEC (Enrolment — Annual)</option>
        <option value="PTRC">PTRC (Registration — Monthly/Annual as per client)</option>
      </select></div>
  </div>

  <div class="form-section mt-2">
    <div class="form-section-title">
      Select Clients <small style="font-size:11px;font-weight:400;color:var(--text-muted)">— leave none selected to apply to ALL eligible clients</small>
    </div>
    <div class="form-grid form-grid-3 mb-1">
      <div class="form-group">
        <label>Filter by Group</label>
        <select class="form-control" id="bulk_group_filter" onchange="filterClientsByGroup('bulk_group_filter','bulk_client_ids')">
          <option value="">— All Groups —</option>
          <?php foreach ($client_groups as $g): ?>
            <option value="<?= $g['id'] ?>"><?= htmlspecialchars($g['group_name']) ?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div class="form-group" style="justify-content:flex-end">
        <label style="visibility:hidden">.</label>
        <div class="d-flex gap-1">
          <button type="button" class="btn btn-outline btn-sm" onclick="selectAllVisibleClients('bulk_client_ids');updateClientSelectionCount('bulk_client_ids','bulk_sel_count')">Select All Visible</button>
          <button type="button" class="btn btn-outline btn-sm" onclick="selectNoneClients('bulk_client_ids');updateClientSelectionCount('bulk_client_ids','bulk_sel_count')">Clear</button>
        </div>
      </div>
      <div class="form-group" style="justify-content:center;align-items:flex-end">
        <span id="bulk_sel_count" class="text-muted" style="font-size:12px">0 clients selected</span>
      </div>
    </div>
    <select class="form-control" name="client_ids[]" id="bulk_client_ids" multiple size="10"
            onchange="updateClientSelectionCount('bulk_client_ids','bulk_sel_count')" style="height:220px">
      <?php foreach ($all_clients as $c): ?>
        <option value="<?= $c['id'] ?>" data-group="<?= $c['group_id'] ?? '' ?>"><?= htmlspecialchars($c['client_name']) ?> (<?= $c['pan'] ?>)</option>
      <?php endforeach; ?>
    </select>
  </div>

  <div class="form-actions"><button class="btn btn-primary" type="submit">⚡ Generate Entries</button><a href="<?=url('ptax_register.php')?>" class="btn btn-outline">Cancel</a></div>
</form></div></div>

<?php elseif($action==='add'||$action==='edit'): ?>
<div class="page-header"><div class="page-title"><?=$action==='edit'?'✏️ Edit PT Entry':'➕ Add PT Entry'?></div><a href="<?=url('ptax_register.php')?>" class="btn btn-outline">← Back</a></div>
<div class="card"><div class="card-body">
<form method="post">
  <div class="form-grid form-grid-4">
    <div class="form-group" style="grid-column:span 2"><label>Client <span class="req">*</span></label>
      <select class="form-control" name="client_id" required>
        <option value="">Select Client</option>
        <?php foreach($all_clients as $c): ?><option value="<?=$c['id']?>" <?=($entry['client_id']??0)==$c['id']?'selected':''?>><?=htmlspecialchars($c['client_name'])?> (<?=$c['pan']?>)</option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>PT Type <span class="req">*</span></label>
      <select class="form-control" name="pt_type" required>
        <option value="PTEC" <?=($entry['pt_type']??'')==='PTEC'?'selected':''?>>PTEC (Annual)</option>
        <option value="PTRC" <?=($entry['pt_type']??'')==='PTRC'?'selected':''?>>PTRC</option>
      </select></div>
    <div class="form-group"><label>Financial Year</label>
      <select class="form-control" name="financial_year">
        <?php foreach($fy_list as $fy): ?><option value="<?=$fy?>" <?=($entry['financial_year']??currentFY())===$fy?'selected':''?>><?=$fy?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Period</label>
      <input class="form-control" name="period" value="<?=htmlspecialchars($entry['period']??'')?>" placeholder="e.g. Apr-2025 or 2025-26"></div>
    <div class="form-group"><label>Due Date</label>
      <input class="form-control" type="date" name="due_date" value="<?=$entry['due_date']??''?>"></div>
    <div class="form-group"><label>PT Amount (₹)</label>
      <input class="form-control" type="number" step="0.01" name="amount" value="<?=$entry['amount']??0?>"></div>
    <div class="form-group"><label>Payment Date</label>
      <input class="form-control" type="date" name="payment_date" value="<?=$entry['payment_date']??''?>"></div>
    <div class="form-group"><label>Challan No.</label>
      <input class="form-control" name="challan_no" value="<?=htmlspecialchars($entry['challan_no']??'')?>"></div>
    <div class="form-group"><label>Filed Date</label>
      <input class="form-control" type="date" name="filed_date" value="<?=$entry['filed_date']??''?>"></div>
    <div class="form-group"><label>Acknowledgement No.</label>
      <input class="form-control" name="acknowledgement_no" value="<?=htmlspecialchars($entry['acknowledgement_no']??'')?>"></div>
    <div class="form-group"><label>Prepared By</label>
      <select class="form-control" name="prepared_by"><option value="">Select</option>
        <?php foreach($all_users as $u): ?><option value="<?=$u['id']?>" <?=($entry['prepared_by']??'')==$u['id']?'selected':''?>><?=htmlspecialchars($u['name'])?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Prepared Date</label>
      <input class="form-control" type="date" name="prepared_date" value="<?=$entry['prepared_date']??''?>"></div>
    <div class="form-group"><label>Assigned To</label>
      <select class="form-control" name="assigned_to"><option value="">Select</option>
        <?php foreach($all_users as $u): ?><option value="<?=$u['id']?>" <?=($entry['assigned_to']??'')==$u['id']?'selected':''?>><?=htmlspecialchars($u['name'])?></option><?php endforeach; ?>
      </select></div>
    <div class="form-group"><label>Status</label>
      <select class="form-control" name="status">
        <?php foreach(['Pending','Under Preparation','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
          <option value="<?=$s?>" <?=($entry['status']??'Pending')===$s?'selected':''?>><?=$s?></option>
        <?php endforeach; ?>
      </select></div>
    <div class="form-group" style="grid-column:span 4"><label>Remarks</label>
      <textarea class="form-control" name="remarks" rows="2"><?=htmlspecialchars($entry['remarks']??'')?></textarea></div>
  </div>
  <div class="form-actions"><button class="btn btn-primary" type="submit">💾 Save</button><a href="<?=url('ptax_register.php')?>" class="btn btn-outline">Cancel</a></div>
</form></div></div>

<?php else: // LIST ?>
<div class="page-header">
  <div><div class="page-title">💼 Professional Tax Register</div><div class="page-subtitle">Total: <?=$total?> entries</div></div>
  <div class="d-flex gap-1">
    <a href="<?=url('ptax_register.php?action=bulk_create')?>" class="btn btn-outline">⚡ Bulk Create</a>
    <a href="<?=url('ptax_register.php?action=add')?>" class="btn btn-primary">+ Add Entry</a>
  </div>
</div>
<div class="filters-bar"><form method="get" style="display:contents">
  <div class="filter-group"><label>FY</label><select name="fy">
    <?php foreach($fy_list as $fy): ?><option value="<?=$fy?>" <?=$ffy===$fy?'selected':''?>><?=$fy?></option><?php endforeach; ?>
  </select></div>
  <div class="filter-group"><label>PT Type</label><select name="pt_type">
    <option value="">All</option><option value="PTEC" <?=$fpt==='PTEC'?'selected':''?>>PTEC</option><option value="PTRC" <?=$fpt==='PTRC'?'selected':''?>>PTRC</option>
  </select></div>
  <div class="filter-group"><label>Status</label><select name="status">
    <option value="">All</option>
    <?php foreach(['Pending','Under Preparation','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
      <option value="<?=$s?>" <?=$fstatus===$s?'selected':''?>><?=$s?></option>
    <?php endforeach; ?>
  </select></div>
  <div class="filter-group"><label>Due</label><select name="due">
    <option value="">All</option><option value="overdue" <?=$fdue==='overdue'?'selected':''?>>Overdue</option>
    <option value="15d" <?=$fdue==='15d'?'selected':''?>>Due in 15d</option>
  </select></div>
  <div class="filter-actions">
    <button class="btn btn-primary" type="submit">Filter</button>
    <a href="<?=url('ptax_register.php')?>" class="btn btn-outline">Reset</a>
    <button class="btn btn-export" type="button" onclick="exportTableToXLS('ptax-table','ptax_<?=$ffy?>')">⬇ Export</button>
  </div>
</form></div>
<div class="card"><div class="table-responsive">
<table class="data-table" id="ptax-table">
  <thead><tr><th>#</th><th>Client</th><th>Type</th><th>FY</th><th>Period</th><th>Due Date</th><th>Amount (₹)</th><th>Challan</th><th>Filed Date</th><th>Ack No.</th><th>Prepared By</th><th>Assigned</th><th>Status</th><th class="no-export">Actions</th></tr></thead>
  <tbody>
  <?php foreach($entries as $i=>$r): $days=daysUntil($r['due_date']); ?>
  <tr class="<?=$r['status']!=='Filed'&&$days!==null&&$days<0?'row-overdue':($r['status']!=='Filed'&&$days!==null&&$days<=7?'row-due-soon':'')?>">
    <td><?=$pg['offset']+$i+1?></td>
    <td><strong style="font-size:12px"><?=htmlspecialchars($r['client_name'])?></strong><br><span class="text-muted" style="font-size:11px"><?=$r['pan']?></span></td>
    <td><span class="badge <?=$r['pt_type']==='PTEC'?'badge-info':'badge-warning'?>"><?=$r['pt_type']?></span></td>
    <td><?=htmlspecialchars($r['financial_year'])?></td>
    <td><?=htmlspecialchars($r['period'])?></td>
    <td><?=dueDateBadge($r['due_date'])?></td>
    <td class="text-right"><?=$r['amount']>0?'₹'.number_format($r['amount'],0):'-'?></td>
    <td style="font-size:11px"><?=htmlspecialchars($r['challan_no']?:'-')?></td>
    <td style="font-size:12px"><?=$r['filed_date']?'<span class="badge badge-success">'.fmtDate($r['filed_date']).'</span>':'-'?></td>
    <td style="font-size:11px"><?=htmlspecialchars($r['acknowledgement_no']?:'-')?></td>
    <td style="font-size:12px"><?=htmlspecialchars($r['prep_name']??'-')?></td>
    <td style="font-size:12px"><?=htmlspecialchars($r['aname']??'-')?></td>
    <td><select class="status-select" data-id="<?=$r['id']?>" data-module="ptax_register" style="font-size:11px;height:24px;padding:0 4px;border:1px solid #d1d8e0;border-radius:4px">
      <?php foreach(['Pending','Under Preparation','Ready to File','Filed','On Hold','Not Applicable'] as $s): ?>
        <option value="<?=$s?>" <?=$r['status']===$s?'selected':''?>><?=$s?></option>
      <?php endforeach; ?></select></td>
    <td class="no-export">
        <?php if(hasRole(['admin','partner','supervisor'])): ?>
          <a href="<?=url('ptax_register.php?action=edit&id=').$r['id']?>" class="btn btn-outline btn-sm">Edit</a>
          <a href="<?=url('ptax_register.php?action=delete&id=').$r['id']?>" class="btn btn-danger btn-sm" onclick="return confirm('Delete this PT entry?')">Delete</a>
        <?php endif; ?>
      </td>
  </tr>
  <?php endforeach; ?>
  <?php if(empty($entries)): ?><tr><td colspan="14" class="text-center text-muted" style="padding:2rem">No entries found.</td></tr><?php endif; ?>
  </tbody>
</table></div></div>
<?php if($pg['total_pages']>1): ?>
<div class="pagination">
  <?php for($i=1;$i<=$pg['total_pages'];$i++): ?>
    <a href="?fy=<?=urlencode($ffy)?>&pt_type=<?=urlencode($fpt)?>&status=<?=urlencode($fstatus)?>&page=<?=$i?>" class="page-link <?=$i===$page?'active':''?>"><?=$i?></a>
  <?php endfor; ?>
  <span class="page-info">Showing <?=count($entries)?> of <?=$total?></span>
</div>
<?php endif; ?>
<?php endif; ?>
<?php include 'includes/footer.php'; ?>
