<?php
require_once dirname(__DIR__).'/includes/config.php';
requireLogin();
header('Content-Type: application/json');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { echo json_encode(['success'=>false]); exit; }
$input = json_decode(file_get_contents('php://input'), true);
$id = intval($input['id'] ?? 0);
$module = $input['module'] ?? '';
$status = $input['status'] ?? '';
$allowed = [
    'gst_returns'    => ['Pending Data','Data Received','Challan Sent','No Challan Due','Challan Paid','Filed','On Hold','Not Applicable'],
    'etds_returns'   => ['Pending Data','Data Received','Working Done','Challan Sent','No Challan Due','Challan Paid','Return Prepared','Filed','Form 16A Downloaded','On Hold','Not Applicable'],
    'roc_compliances'=> ['Not Started','Documents Pending','Under Preparation','Under Review','Ready to File','Filed','On Hold','Not Applicable'],
    'ptax_register'  => ['Pending','Under Preparation','Ready to File','Filed','On Hold','Not Applicable'],
];
if (!$id || !isset($allowed[$module]) || !in_array($status, $allowed[$module])) {
    echo json_encode(['success'=>false,'error'=>'Invalid input']); exit;
}
try {
    getDB()->prepare("UPDATE `{$module}` SET status=? WHERE id=?")->execute([$status, $id]);
    auditLog($module, $id, 'UPDATE', null, ['status'=>$status]);
    echo json_encode(['success'=>true]);
} catch (Exception $e) {
    echo json_encode(['success'=>false,'error'=>'DB error']);
}
