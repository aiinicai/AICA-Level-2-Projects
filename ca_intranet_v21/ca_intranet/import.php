<?php
require_once __DIR__.'/includes/config.php';
requireLogin();
if (!hasRole(['admin','partner'])) { header('Location: '.url('dashboard.php')); exit; }
$db = getDB();
$page_title = 'Import Data';
$type = $_GET['type'] ?? 'clients';
$results = []; $errors = [];

// ── DOWNLOAD TEMPLATES (clean CSV) ────────────────────────
if (isset($_GET['download'])) {
    require_once __DIR__.'/includes/export.php';
    $dl = $_GET['download'];

    if ($dl === 'clients') {
        startCSVDownload('clients_import_template');
        $out = fopen('php://output','w');
        writeCSVRow($out, [
            'client_name*','pan*','address',
            'contact_name','contact_mobile','contact_email','contact_designation',
            'gst_applicable (YES or blank)','gstin','gst_return_type (Monthly/QRMP/Composition)',
            'tds_applicable (YES or blank)','tan',
            'ptec_no','ptrc_no','ptrc_periodicity (Monthly or Annual)',
            'partner_username','supervisor_username','notes',
        ]);
        // Sample rows
        writeCSVRow($out, [
            'Ramesh Traders','AAABR1234P','Shop 5 MG Road Nagpur',
            'Ramesh Gupta','9876543210','ramesh@example.com','Proprietor',
            'YES','27AAABR1234P1ZX','Monthly',
            '','','','','Monthly',
            'partner1','supervisor1','',
        ]);
        writeCSVRow($out, [
            'ABC Pvt Ltd','AAACA5678C','Plot 10 MIDC Nagpur',
            'Sanjay Shah','9988776655','sanjay@abc.com','Director',
            'YES','27AAACA5678C1ZX','Monthly',
            'YES','ABCA12345E','','27123456789C','Monthly',
            'partner1','supervisor1','Company with TDS and PTRC',
        ]);
        writeCSVRow($out, [
            'Mehta HUF','AABHM9012H','15 Civil Lines Nagpur',
            'Mahesh Mehta','9112233445','mahesh@mehta.com','Karta',
            '','','',
            '','','','','',
            'partner1','supervisor1','',
        ]);
        fclose($out); exit;
    }

    if ($dl === 'users') {
        startCSVDownload('users_import_template');
        $out = fopen('php://output','w');
        writeCSVRow($out, ['name*','username*','password*','role* (admin/partner/supervisor/staff)','email','mobile']);
        writeCSVRow($out, ['Priya Sharma','priya','Welcome@123','supervisor','priya@firm.com','9876500001']);
        writeCSVRow($out, ['Rahul Verma','rahul','Welcome@123','staff','rahul@firm.com','9876500002']);
        fclose($out); exit;
    }

    // ── XLSX WITH DROPDOWNS (clients) — prevents typos on import ──
    if ($dl === 'clients_xlsx') {
        require_once __DIR__.'/includes/xlsx_export.php';
        if (!xlsxIsAvailable()) {
            $_SESSION['flash_msg'] = 'Dropdown template unavailable on this server (PHP Zip extension not installed). Use the plain CSV template instead.';
            $_SESSION['flash_type'] = 'error';
            header('Location: '.url('import.php?type=clients')); exit;
        }
        $partner_names    = $db->query("SELECT username FROM users WHERE role IN('partner','admin') AND is_active=1 ORDER BY username")->fetchAll(PDO::FETCH_COLUMN);
        $supervisor_names = $db->query("SELECT username FROM users WHERE role IN('supervisor','admin') AND is_active=1 ORDER BY username")->fetchAll(PDO::FETCH_COLUMN);

        $headers = [
            'client_name*','pan*','address',
            'contact_name','contact_mobile','contact_email','contact_designation',
            'gst_applicable','gstin','gst_return_type',
            'tds_applicable','tan',
            'ptec_no','ptrc_no','ptrc_periodicity',
            'partner_username','supervisor_username','notes',
        ];
        $samples = [
            ['Ramesh Traders','AAABR1234P','Shop 5 MG Road Nagpur','Ramesh Gupta','9876543210','ramesh@example.com','Proprietor','YES','27AAABR1234P1ZX','Monthly','','','','','Monthly', $partner_names[0]??'', $supervisor_names[0]??'',''],
            ['ABC Pvt Ltd','AAACA5678C','Plot 10 MIDC Nagpur','Sanjay Shah','9988776655','sanjay@abc.com','Director','YES','27AAACA5678C1ZX','Monthly','YES','ABCA12345E','','27123456789C','Monthly', $partner_names[0]??'', $supervisor_names[0]??'','Company with TDS and PTRC'],
        ];
        $dropdowns = [
            7  => ['YES',''],                          // gst_applicable
            9  => ['Monthly','QRMP','Composition'],     // gst_return_type
            10 => ['YES',''],                           // tds_applicable
            14 => ['Monthly','Annual'],                 // ptrc_periodicity
            15 => $partner_names ?: ['(no partners set up yet)'],    // partner_username
            16 => $supervisor_names ?: ['(no supervisors set up yet)'], // supervisor_username
        ];
        streamXLSXWithDropdowns('clients_import_template_dropdowns', $headers, $samples, $dropdowns);
    }

    // ── XLSX WITH DROPDOWNS (users) ──
    if ($dl === 'users_xlsx') {
        require_once __DIR__.'/includes/xlsx_export.php';
        if (!xlsxIsAvailable()) {
            $_SESSION['flash_msg'] = 'Dropdown template unavailable on this server (PHP Zip extension not installed). Use the plain CSV template instead.';
            $_SESSION['flash_type'] = 'error';
            header('Location: '.url('import.php?type=users')); exit;
        }
        $headers = ['name*','username*','password*','role*','email','mobile'];
        $samples = [
            ['Priya Sharma','priya','Welcome@123','supervisor','priya@firm.com','9876500001'],
            ['Rahul Verma','rahul','Welcome@123','staff','rahul@firm.com','9876500002'],
        ];
        $dropdowns = [3 => ['admin','partner','supervisor','staff']]; // role
        streamXLSXWithDropdowns('users_import_template_dropdowns', $headers, $samples, $dropdowns);
    }
}

// ── PROCESS CSV UPLOAD ────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['import_file'])) {
    $file = $_FILES['import_file'];
    if ($file['error'] !== 0) {
        $errors[] = 'File upload error code: ' . $file['error'];
    } else {
        $ext = strtolower(pathinfo($file['name'], PATHINFO_EXTENSION));
        if (!in_array($ext, ['csv'])) {
            $errors[] = 'Only CSV files are supported for upload. Download the template, fill it in Excel, then save as CSV (UTF-8) before uploading.';
        } else {
            $handle = fopen($file['tmp_name'], 'r');
            fgetcsv($handle); // skip header
            $row_num = 1; $ok = 0; $skip = 0;

            if ($type === 'clients') {
                $partners_map = $db->query("SELECT username,id FROM users WHERE role IN('partner','admin')")->fetchAll(PDO::FETCH_KEY_PAIR);
                $sup_map      = $db->query("SELECT username,id FROM users WHERE role IN('supervisor','admin')")->fetchAll(PDO::FETCH_KEY_PAIR);

                // Full state map for GSTIN auto-detection
                $state_map = [
                    '01'=>'Jammu & Kashmir','02'=>'Himachal Pradesh','03'=>'Punjab',
                    '04'=>'Chandigarh','05'=>'Uttarakhand','06'=>'Haryana','07'=>'Delhi',
                    '08'=>'Rajasthan','09'=>'Uttar Pradesh','10'=>'Bihar','11'=>'Sikkim',
                    '12'=>'Arunachal Pradesh','13'=>'Nagaland','14'=>'Manipur','15'=>'Mizoram',
                    '16'=>'Tripura','17'=>'Meghalaya','18'=>'Assam','19'=>'West Bengal',
                    '20'=>'Jharkhand','21'=>'Odisha','22'=>'Chhattisgarh','23'=>'Madhya Pradesh',
                    '24'=>'Gujarat','26'=>'Dadra & Nagar Haveli','27'=>'Maharashtra',
                    '28'=>'Andhra Pradesh','29'=>'Karnataka','30'=>'Goa','31'=>'Lakshadweep',
                    '32'=>'Kerala','33'=>'Tamil Nadu','34'=>'Puducherry','35'=>'Andaman & Nicobar',
                    '36'=>'Telangana','37'=>'Andhra Pradesh (New)','38'=>'Ladakh',
                    '97'=>'Other Territory','99'=>'Centre Jurisdiction',
                ];
                $updated = 0;

                while (($row = fgetcsv($handle)) !== false) {
                    $row_num++;
                    // Skip blank rows
                    if (count($row) < 2 || empty(trim($row[0] ?? ''))) { $skip++; continue; }

                    $name = trim($row[0] ?? '');
                    $pan  = strtoupper(trim($row[1] ?? ''));

                    if (!$pan || strlen($pan) !== 10) {
                        $errors[] = "Row $row_num: Invalid PAN '$pan' — skipped."; $skip++; continue;
                    }

                    // Warn if column count is wrong (should be 18 columns, 0-17)
                    if (count($row) < 9) {
                        $errors[] = "Row $row_num: Only ".count($row)." columns found — expected 18. Check your CSV format. PAN: $pan skipped.";
                        $skip++; continue;
                    }

                    // Parse GSTIN from this row (column 8)
                    $gstin       = strtoupper(trim($row[8] ?? ''));
                    $gstin_state = ($gstin && strlen($gstin) >= 2) ? ($state_map[substr($gstin,0,2)] ?? '') : '';

                    // Sanitize gst_return_type
                    $raw_gst_type = strtolower(trim($row[9] ?? ''));
                    if (strpos($raw_gst_type, 'qrmp') !== false || strpos($raw_gst_type, 'quarter') !== false) {
                        $gst_return_type = 'QRMP';
                    } elseif (strpos($raw_gst_type, 'comp') !== false) {
                        $gst_return_type = 'Composition';
                    } else {
                        $gst_return_type = 'Monthly';
                    }

                    // Sanitize ptrc_periodicity
                    $raw_ptrc = strtolower(trim($row[14] ?? ''));
                    $ptrc_periodicity = (strpos($raw_ptrc, 'ann') !== false) ? 'Annual' : 'Monthly';

                    // Contact details
                    $cname  = trim($row[3] ?? '');
                    $cmob   = trim($row[4] ?? '');
                    $cemail = trim($row[5] ?? '');
                    $cdesig = trim($row[6] ?? '');

                    $partner_id = $partners_map[trim($row[15] ?? '')] ?? null;
                    $sup_id     = $sup_map[trim($row[16] ?? '')] ?? null;

                    // ── CHECK IF PAN ALREADY EXISTS ───────────────────────────
                    $chk = $db->prepare("SELECT id, gstin_list, contacts FROM clients WHERE pan=?");
                    $chk->execute([$pan]);
                    $existing = $chk->fetch();

                    if ($existing) {
                        // PAN exists — just merge in the new GSTIN if provided
                        $existing_id = $existing['id'];

                        if ($gstin) {
                            $existing_gstins = $existing['gstin_list'] ? json_decode($existing['gstin_list'], true) : [];
                            if (!is_array($existing_gstins)) $existing_gstins = [];

                            // Check if this GSTIN already exists
                            $already = false;
                            foreach ($existing_gstins as $eg) {
                                if (($eg['gstin'] ?? '') === $gstin) { $already = true; break; }
                            }

                            if (!$already) {
                                $existing_gstins[] = [
                                    'gstin'          => $gstin,
                                    'state'          => $gstin_state,
                                    'return_type'    => $gst_return_type,
                                    'effective_from' => '',
                                ];
                                $db->prepare("UPDATE clients SET gstin_list=?, gst_applicable=1 WHERE id=?")
                                   ->execute([json_encode($existing_gstins), $existing_id]);
                                $results[] = "Row $row_num: ↑ Updated — $name ($pan) — added GSTIN $gstin ($gstin_state).";
                                $updated++;
                            } else {
                                $results[] = "Row $row_num: ↔ Skipped — $name ($pan) — GSTIN $gstin already present.";
                                $skip++;
                            }
                        } else {
                            $results[] = "Row $row_num: ↔ Skipped — $name ($pan) already exists, no new GSTIN.";
                            $skip++;
                        }
                        continue;
                    }

                    // ── NEW CLIENT — insert fresh ─────────────────────────────
                    $constitution = getConstitutionFromPAN($pan);
                    $code         = generateClientCode($constitution);

                    $gstin_list = $gstin
                        ? json_encode([['gstin'=>$gstin,'state'=>$gstin_state,'return_type'=>$gst_return_type,'effective_from'=>'']])
                        : null;

                    $contacts = $cname
                        ? json_encode([['name'=>$cname,'mobile'=>$cmob,'email'=>$cemail,'designation'=>$cdesig]])
                        : null;

                    // gst_applicable = YES column OR gstin present (whichever is true)
                    $gst_yes_col  = strtolower(trim($row[7] ?? ''));
                    $gst_flag     = ($gstin || in_array($gst_yes_col, ['yes','y','1','true'])) ? 1 : 0;

                    // tds_applicable = YES column OR tan present
                    $tds_yes_col  = strtolower(trim($row[10] ?? ''));
                    $tan_val      = strtoupper(trim($row[11] ?? ''));
                    $tds_flag     = ($tan_val || in_array($tds_yes_col, ['yes','y','1','true'])) ? 1 : 0;

                    $data = [
                        'client_code'      => $code,
                        'client_name'      => $name,
                        'pan'              => $pan,
                        'constitution'     => $constitution,
                        'contacts'         => $contacts,
                        'address'          => trim($row[2] ?? ''),
                        'gst_applicable'   => $gst_flag,
                        'gstin_list'       => $gstin_list,
                        'gst_return_type'  => $gst_return_type,
                        'tds_applicable'   => $tds_flag,
                        'tan'              => $tan_val,
                        'ptec_no'          => strtoupper(trim($row[12] ?? '')),
                        'ptec_applicable'  => !empty(trim($row[12] ?? '')) ? 1 : 0,
                        'ptrc_no'          => strtoupper(trim($row[13] ?? '')),
                        'ptrc_applicable'  => !empty(trim($row[13] ?? '')) ? 1 : 0,
                        'ptrc_periodicity' => $ptrc_periodicity,
                        'partner_id'       => $partner_id,
                        'supervisor_id'    => $sup_id,
                        'status'           => 'Active',
                        'notes'            => trim($row[17] ?? ''),
                    ];

                    try {
                        $cols = implode(', ', array_keys($data));
                        $ph   = implode(', ', array_fill(0, count($data), '?'));
                        $db->prepare("INSERT INTO clients ($cols) VALUES ($ph)")->execute(array_values($data));
                        $ok++;
                        $gstin_info = $gstin ? " | GSTIN: $gstin" . ($gstin_state ? " ($gstin_state)" : '') . " [$gst_return_type]" : ' | No GSTIN';
                        $tan_info   = $tan_val ? " | TAN: $tan_val" : '';
                        $results[]  = "Row $row_num: ✓ Added — $name ($pan) → Code: $code$gstin_info$tan_info";
                    } catch (Exception $e) {
                        $errors[] = "Row $row_num: DB error — " . $e->getMessage();
                        $skip++;
                    }
                }
                auditLog('clients', 0, 'IMPORT', null, ['imported'=>$ok, 'updated'=>$updated, 'skipped'=>$skip]);

            } elseif ($type === 'clients_update') {
                // ── UPDATE EXISTING CLIENTS (matched by PAN) ─────────────
                // Same column layout as export: name,pan,address,c_name,c_mobile,c_email,c_desig,
                // gst_app,gstin,gst_type,tds_app,tan,ptec_no,ptrc_no,ptrc_per,partner_user,sup_user,notes
                // Extra columns __client_code, __constitution, __status are ignored
                $partners_map = $db->query("SELECT username,id FROM users WHERE role IN('partner','admin')")->fetchAll(PDO::FETCH_KEY_PAIR);
                $sup_map      = $db->query("SELECT username,id FROM users WHERE role IN('supervisor','admin')")->fetchAll(PDO::FETCH_KEY_PAIR);
                $state_map    = ['01'=>'J&K','02'=>'HP','03'=>'Punjab','04'=>'Chandigarh','05'=>'Uttarakhand',
                    '06'=>'Haryana','07'=>'Delhi','08'=>'Rajasthan','09'=>'UP','10'=>'Bihar',
                    '11'=>'Sikkim','12'=>'Arunachal','13'=>'Nagaland','14'=>'Manipur','15'=>'Mizoram',
                    '16'=>'Tripura','17'=>'Meghalaya','18'=>'Assam','19'=>'WB','20'=>'Jharkhand',
                    '21'=>'Odisha','22'=>'Chhattisgarh','23'=>'MP','24'=>'Gujarat','26'=>'D&NH',
                    '27'=>'Maharashtra','28'=>'AP','29'=>'Karnataka','30'=>'Goa','31'=>'Lakshadweep',
                    '32'=>'Kerala','33'=>'TN','34'=>'Puducherry','35'=>'A&N','36'=>'Telangana',
                    '37'=>'AP New','38'=>'Ladakh'];

                while (($row = fgetcsv($handle)) !== false) {
                    $row_num++;
                    if (count($row) < 2 || empty(trim($row[0] ?? ''))) { $skip++; continue; }

                    $name = trim($row[0] ?? '');
                    $pan  = strtoupper(trim($row[1] ?? ''));
                    if (!$pan || strlen($pan) !== 10) {
                        $errors[] = "Row $row_num: Invalid PAN '$pan'"; $skip++; continue;
                    }

                    // Find existing client by PAN
                    $chk = $db->prepare("SELECT id, gstin_list FROM clients WHERE pan=?");
                    $chk->execute([$pan]);
                    $existing = $chk->fetch();
                    if (!$existing) {
                        $errors[] = "Row $row_num: PAN $pan not found — use 'Import New' to add new clients.";
                        $skip++; continue;
                    }

                    // Parse fields — only update fields that are non-blank
                    $raw_gst_type = strtolower(trim($row[9] ?? ''));
                    if (strpos($raw_gst_type,'qrmp')!==false||strpos($raw_gst_type,'quarter')!==false)
                        $gst_return_type = 'QRMP';
                    elseif (strpos($raw_gst_type,'comp')!==false)
                        $gst_return_type = 'Composition';
                    else
                        $gst_return_type = 'Monthly';

                    $raw_ptrc = strtolower(trim($row[14] ?? ''));
                    $ptrc_per = strpos($raw_ptrc,'ann')!==false ? 'Annual' : 'Monthly';

                    $gstin = strtoupper(trim($row[8] ?? ''));
                    $gstin_state = ($gstin && strlen($gstin)>=2) ? ($state_map[substr($gstin,0,2)] ?? '') : '';

                    // Build updates — only set fields that have values in the CSV
                    $updates = [];
                    $uvals   = [];

                    // Always update these if present
                    if ($name)             { $updates[] = 'client_name=?';     $uvals[] = $name; }
                    if (trim($row[2]??'')) { $updates[] = 'address=?';         $uvals[] = trim($row[2]); }
                    if (trim($row[10]??'')){ $updates[] = 'tds_applicable=?';  $uvals[] = 1; }
                    if (trim($row[11]??'')){ $updates[] = 'tan=?';             $uvals[] = strtoupper(trim($row[11])); }
                    if (trim($row[12]??'')){ $updates[] = 'ptec_no=?';         $uvals[] = strtoupper(trim($row[12]));
                                            $updates[] = 'ptec_applicable=?';  $uvals[] = 1; }
                    if (trim($row[13]??'')){ $updates[] = 'ptrc_no=?';         $uvals[] = strtoupper(trim($row[13]));
                                            $updates[] = 'ptrc_applicable=?';  $uvals[] = 1; }
                    if (trim($row[17]??'')){ $updates[] = 'notes=?';           $uvals[] = trim($row[17]); }

                    // Partner / Supervisor — update if username is valid
                    $puser = trim($row[15] ?? '');
                    $suser = trim($row[16] ?? '');
                    if ($puser && isset($partners_map[$puser])) {
                        $updates[] = 'partner_id=?';    $uvals[] = $partners_map[$puser];
                    }
                    if ($suser && isset($sup_map[$suser])) {
                        $updates[] = 'supervisor_id=?'; $uvals[] = $sup_map[$suser];
                    }

                    // GST: merge new GSTIN into existing list if provided
                    if ($gstin) {
                        $existing_gstins = $existing['gstin_list'] ? json_decode($existing['gstin_list'],true) : [];
                        if (!is_array($existing_gstins)) $existing_gstins = [];
                        $found = false;
                        foreach ($existing_gstins as &$eg) {
                            if (($eg['gstin']??'') === $gstin) {
                                $eg['return_type'] = $gst_return_type; // update return type
                                $found = true; break;
                            }
                        }
                        unset($eg);
                        if (!$found) {
                            $existing_gstins[] = ['gstin'=>$gstin,'state'=>$gstin_state,
                                'return_type'=>$gst_return_type,'effective_from'=>''];
                        }
                        $updates[] = 'gstin_list=?';      $uvals[] = json_encode($existing_gstins);
                        $updates[] = 'gst_applicable=?';  $uvals[] = 1;
                        $updates[] = 'gst_return_type=?'; $uvals[] = $gst_return_type;
                    }

                    // Contact — update if name provided
                    $cname = trim($row[3] ?? '');
                    if ($cname) {
                        $ct = [['name'=>$cname,'mobile'=>trim($row[4]??''),
                                'email'=>trim($row[5]??''),'designation'=>trim($row[6]??'')]];
                        $updates[] = 'contacts=?'; $uvals[] = json_encode($ct);
                    }

                    if (empty($updates)) { $skip++; continue; }

                    try {
                        $uvals[] = $existing['id'];
                        $db->prepare("UPDATE clients SET ".implode(', ',$updates)." WHERE id=?")
                           ->execute($uvals);
                        auditLog('clients', $existing['id'], 'UPDATE', null,
                            ['source'=>'reimport','pan'=>$pan,'partner'=>$puser,'supervisor'=>$suser]);
                        $ok++;
                        $results[] = "Row $row_num: ↑ Updated — $name ($pan)".
                            ($puser?" | Partner: $puser":'').($suser?" | Supervisor: $suser":'');
                    } catch (Exception $e) {
                        $errors[] = "Row $row_num: DB error — ".$e->getMessage(); $skip++;
                    }
                }
                auditLog('clients', 0, 'IMPORT', null, ['updated'=>$ok,'skipped'=>$skip]);

            } elseif ($type === 'users') {
                while (($row = fgetcsv($handle)) !== false) {
                    $row_num++;
                    if (count($row) < 3 || empty(trim($row[0]??''))) { $skip++; continue; }
                    $uname = strtolower(trim($row[1]??''));
                    $chk = $db->prepare("SELECT id FROM users WHERE username=?"); $chk->execute([$uname]);
                    if ($chk->fetch()) { $errors[] = "Row $row_num: Username '$uname' already exists — skipped."; $skip++; continue; }
                    $role = trim($row[3]??'staff');
                    if (!in_array($role, ['admin','partner','supervisor','staff'])) $role = 'staff';
                    $data = ['name'=>trim($row[0]),'username'=>$uname,
                             'password'=>password_hash(trim($row[2]), PASSWORD_DEFAULT),
                             'role'=>$role,'email'=>trim($row[4]??''),'mobile'=>trim($row[5]??''),'is_active'=>1];
                    try {
                        $cols = implode(',', array_keys($data));
                        $ph   = implode(',', array_fill(0, count($data), '?'));
                        $db->prepare("INSERT INTO users ($cols) VALUES ($ph)")->execute(array_values($data));
                        $ok++;
                        $results[] = "Row $row_num: ✓ User added — {$row[0]} ($uname)";
                    } catch (Exception $e) { $errors[] = "Row $row_num: ".$e->getMessage(); $skip++; }
                }
                auditLog('users', 0, 'IMPORT', null, ['imported'=>$ok,'skipped'=>$skip]);
            }
            fclose($handle);
            $_SESSION['flash_msg'] = ($type==='clients_update')
                ? "Update complete: $ok records updated, $skip skipped."
                : "Import complete: $ok added, $updated updated (new GSTIN merged), $skip skipped.";
            $_SESSION['flash_type'] = $errors ? 'warning' : 'success';
        }
    }
}

include 'includes/header.php';
?>
<div class="page-header">
  <div class="page-title">⬆ Import Data</div>
  <a href="<?= url('clients.php') ?>" class="btn btn-outline">← Back</a>
</div>

<div class="d-flex gap-2 mb-2" style="flex-wrap:wrap">
  <a href="<?= url('import.php?type=clients') ?>"        class="btn <?= $type==='clients'       ?'btn-primary':'btn-outline' ?>">Import New Clients</a>
  <a href="<?= url('import.php?type=clients_update') ?>" class="btn <?= $type==='clients_update'?'btn-primary':'btn-outline' ?>">✏️ Update Existing Clients</a>
  <a href="<?= url('import.php?type=users') ?>"          class="btn <?= $type==='users'         ?'btn-primary':'btn-outline' ?>">Import Users</a>
</div>

<?php if ($type === 'clients'): ?>
<div class="card mb-2">
  <div class="card-header"><span class="card-title">📥 Bulk Import Clients from Excel / CSV</span></div>
  <div class="card-body">
    <div style="background:var(--primary-bg);padding:14px;border-radius:6px;margin-bottom:1rem;font-size:13px;line-height:1.8">
      <strong>How to import:</strong><br>
      1. Download a template below (the dropdown version helps prevent typos in Partner/Supervisor/GST Type fields)<br>
      2. Fill in your client data (columns marked * are mandatory)<br>
      3. Save the file as <strong>CSV (UTF-8)</strong> from Excel: File → Save As → CSV UTF-8 <em>(required even if you used the dropdown version)</em><br>
      4. Upload the CSV file here<br><br>
      <strong>Notes:</strong> Constitution is auto-detected from PAN. Client code is auto-generated. Duplicate PANs are skipped.
    </div>
    <div class="d-flex gap-1 mb-2" style="flex-wrap:wrap">
      <a href="<?= url('import.php?type=clients&download=clients_xlsx') ?>" class="btn btn-export">
        ⬇ Download with Dropdowns (.xlsx) <span style="font-size:10px;opacity:.85">— recommended</span>
      </a>
      <a href="<?= url('import.php?type=clients&download=clients') ?>" class="btn btn-outline">
        ⬇ Download Plain Template (.csv)
      </a>
    </div>
    <hr style="margin:1rem 0;border-color:var(--border-lt)">
    <form method="post" enctype="multipart/form-data">
      <div class="form-group mb-2">
        <label>Upload CSV File <span class="req">*</span></label>
        <input type="file" name="import_file" accept=".csv" class="form-control" style="height:auto;padding:6px">
      </div>
      <button class="btn btn-primary" type="submit">⬆ Upload &amp; Import</button>
    </form>
  </div>
</div>

<?php elseif ($type === 'clients_update'): ?>
<div class="card mb-2">
  <div class="card-header" style="background:var(--primary-bg)">
    <span class="card-title" style="color:var(--primary)">✏️ Update Existing Clients — Reimport from Excel</span>
  </div>
  <div class="card-body">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem">
      <div style="background:#eaf3de;padding:14px;border-radius:6px;font-size:13px;line-height:1.8;border:1px solid #c0dd97">
        <strong>✅ What gets UPDATED:</strong><br>
        • Client name, address<br>
        • Partner &amp; Supervisor assignment<br>
        • GSTIN list (adds new, updates return type of existing)<br>
        • TAN, PTEC No., PTRC No.<br>
        • Contact person details<br>
        • Notes
      </div>
      <div style="background:#fdf0ef;padding:14px;border-radius:6px;font-size:13px;line-height:1.8;border:1px solid #fecaca">
        <strong>⚠️ What does NOT change:</strong><br>
        • Client Code (auto-generated, never changes)<br>
        • PAN (used for matching — cannot be changed)<br>
        • Constitution (derived from PAN)<br>
        • If a column is blank in the file, existing value is kept unchanged
      </div>
    </div>
    <div style="background:var(--primary-bg);padding:12px;border-radius:6px;font-size:13px;margin-bottom:1rem;line-height:1.8">
      <strong>How to use:</strong><br>
      1. Go to <a href="<?= url('clients.php') ?>">Client Master</a> →
         click <strong>"Export for Editing"</strong> button (top right)<br>
      2. The Excel file will have all your current client data pre-filled<br>
      3. Edit the columns you want to change (e.g. update partner_username, supervisor_username columns)<br>
      4. Leave other columns unchanged — blank cells will keep the existing value<br>
      5. Save as <strong>CSV UTF-8</strong> from Excel → upload here
    </div>
    <a href="<?= url('clients.php?export_edit=1') ?>" class="btn btn-export mb-2">
      ⬇ Export Current Client Data for Editing
    </a>
    <hr style="margin:1rem 0;border-color:var(--border-lt)">
    <form method="post" enctype="multipart/form-data">
      <div class="form-group mb-2">
        <label>Upload Edited CSV File <span class="req">*</span></label>
        <input type="file" name="import_file" accept=".csv" class="form-control" style="height:auto;padding:6px">
      </div>
      <button class="btn btn-primary" type="submit">⬆ Upload &amp; Update Clients</button>
    </form>
  </div>
</div>

<?php else: ?>
<div class="card mb-2">
  <div class="card-header"><span class="card-title">📥 Bulk Import Users from Excel / CSV</span></div>
  <div class="card-body">
    <div style="background:var(--primary-bg);padding:14px;border-radius:6px;margin-bottom:1rem;font-size:13px;line-height:1.8">
      <strong>How to import:</strong><br>
      1. Download a template below (the dropdown version restricts Role to valid values)<br>
      2. Fill in user details — role must be one of: <code>admin / partner / supervisor / staff</code><br>
      3. Save as CSV (UTF-8) from Excel <em>(required even if you used the dropdown version)</em><br>
      4. Upload the CSV file here<br><br>
      <strong>Note:</strong> Passwords are stored securely. Existing usernames are automatically skipped.
    </div>
    <div class="d-flex gap-1 mb-2" style="flex-wrap:wrap">
      <a href="<?= url('import.php?type=users&download=users_xlsx') ?>" class="btn btn-export">
        ⬇ Download with Dropdowns (.xlsx) <span style="font-size:10px;opacity:.85">— recommended</span>
      </a>
      <a href="<?= url('import.php?type=users&download=users') ?>" class="btn btn-outline">
        ⬇ Download Plain Template (.csv)
      </a>
    </div>
    <hr style="margin:1rem 0;border-color:var(--border-lt)">
    <form method="post" enctype="multipart/form-data">
      <div class="form-group mb-2">
        <label>Upload CSV File <span class="req">*</span></label>
        <input type="file" name="import_file" accept=".csv" class="form-control" style="height:auto;padding:6px">
      </div>
      <button class="btn btn-primary" type="submit">⬆ Upload &amp; Import</button>
    </form>
  </div>
</div>
<?php endif; ?>

<?php if ($results || $errors): ?>
<div class="card">
  <div class="card-header"><span class="card-title">Import Results</span></div>
  <div class="card-body" style="font-size:13px;max-height:400px;overflow-y:auto">
    <?php foreach ($results as $r): ?>
      <div style="color:var(--success);padding:3px 0;border-bottom:1px solid var(--border-lt)"><?= htmlspecialchars($r) ?></div>
    <?php endforeach; ?>
    <?php foreach ($errors as $e): ?>
      <div style="color:var(--danger);padding:3px 0;border-bottom:1px solid var(--border-lt)">⚠ <?= htmlspecialchars($e) ?></div>
    <?php endforeach; ?>
  </div>
</div>
<?php endif; ?>

<?php include 'includes/footer.php'; ?>
