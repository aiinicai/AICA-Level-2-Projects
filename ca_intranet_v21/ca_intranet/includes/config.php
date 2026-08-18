<?php
// ============================================================
// CONFIGURATION
// ============================================================
define('DB_HOST',    'localhost');
define('DB_NAME',    'ca_intranet');
define('DB_USER',    'root');
define('DB_PASS',    '');
define('DB_CHARSET', 'utf8mb4');
define('APP_NAME',   'CA Firm Intranet');
define('BASE',       '/ca_intranet');      // ← subfolder under htdocs
define('FIRM_NAME',  'CA Firm Intranet'); // fallback — real name set via Admin > Firm Settings
define('SESSION_TIMEOUT', 7200);
define('TIMEZONE',   'Asia/Kolkata');

date_default_timezone_set(TIMEZONE);

function url($path='') { return BASE.'/'.ltrim($path,'/'); }

// ============================================================
// DATABASE
// ============================================================
function getDB() {
    static $pdo=null;
    if($pdo===null){
        try {
            $dsn="mysql:host=".DB_HOST.";dbname=".DB_NAME.";charset=".DB_CHARSET;
            $pdo=new PDO($dsn,DB_USER,DB_PASS,[
                PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES=>false,
                // Remove STRICT_TRANS_TABLES so MySQL warnings (1265 truncation)
                // do not bubble up as PDO exceptions. Data is still saved correctly.
                PDO::MYSQL_ATTR_INIT_COMMAND=>"SET sql_mode='NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
            ]);
        } catch(PDOException $e){
            die('<div style="font-family:sans-serif;padding:2rem;color:#c00">
                <h2>Database Connection Failed</h2>
                <p>Check <code>includes/config.php</code> DB settings</p>
                <p>'.$e->getMessage().'</p></div>');
        }
    }
    return $pdo;
}

// ============================================================
// FIRM SETTINGS (from DB, cached)
// ============================================================
function getSetting($key, $default='') {
    static $cache=null;
    if($cache===null){
        try {
            $r=getDB()->query("SELECT setting_key,setting_value FROM app_settings");
            $cache=[];
            foreach($r->fetchAll() as $row) $cache[$row['setting_key']]=$row['setting_value'];
        } catch(Exception $e){ $cache=[]; }
    }
    return $cache[$key] ?? $default;
}

function firmName() { return getSetting('firm_name','CA Firm'); }

// ============================================================
// SESSION
// ============================================================
function startSecureSession(){
    if(session_status()===PHP_SESSION_NONE){
        ini_set('session.cookie_httponly',1);
        ini_set('session.use_strict_mode',1);
        session_start();
    }
    if(isset($_SESSION['last_activity'])&&(time()-$_SESSION['last_activity'])>SESSION_TIMEOUT){
        $_SESSION=[];
        if(ini_get('session.use_cookies')){
            $p=session_get_cookie_params();
            setcookie(session_name(),'',time()-42000,$p['path'],$p['domain'],$p['secure'],$p['httponly']);
        }
        session_destroy();
        header('Location: '.url('login.php').'?timeout=1'); exit;
    }
    $_SESSION['last_activity']=time();
}

function requireLogin(){
    startSecureSession();
    if(!isset($_SESSION['user_id'])){ header('Location: '.url('login.php')); exit; }
}

function currentUser(){ return $_SESSION??[]; }

function hasRole($roles){
    if(!is_array($roles)) $roles=[$roles];
    return isset($_SESSION['role'])&&in_array($_SESSION['role'],$roles);
}

// ============================================================
// AUDIT LOG
// ============================================================
function auditLog($module,$record_id,$action,$old=null,$new=null){
    try {
        getDB()->prepare("INSERT INTO audit_log(user_id,module,record_id,action,old_values,new_values,ip_address) VALUES(?,?,?,?,?,?,?)")
            ->execute([$_SESSION['user_id']??null,$module,$record_id,$action,
                $old?json_encode($old):null,$new?json_encode($new):null,$_SERVER['REMOTE_ADDR']??null]);
    } catch(Exception $e){}
}

// ============================================================
// PAN → CONSTITUTION
// ============================================================
function getConstitutionFromPAN($pan){
    if(strlen($pan)<4) return '';
    $map=['P'=>'Individual','H'=>'HUF','F'=>'Firm/LLP','C'=>'Company',
          'A'=>'AOP','B'=>'BOI','G'=>'Government','J'=>'Artificial Juridical Person',
          'L'=>'Local Authority','T'=>'Trust'];
    return $map[strtoupper($pan[3])]??'Other';
}

// ============================================================
// AUTO CLIENT CODE
// ============================================================
function generateClientCode($constitution){
    // Short prefix map
    $prefix_map=[
        'Individual'=>'IND','HUF'=>'HUF','Firm/LLP'=>'FRM','Company'=>'COM',
        'AOP'=>'AOP','BOI'=>'BOI','Trust'=>'TRU','Government'=>'GOV',
        'Local Authority'=>'LOC','Artificial Juridical Person'=>'AJP','Other'=>'OTH'
    ];
    $prefix=$prefix_map[$constitution]??'OTH';
    $db=getDB();
    $stmt=$db->prepare("SELECT client_code FROM clients WHERE client_code LIKE ? ORDER BY id DESC LIMIT 1");
    $stmt->execute(["$prefix-%"]);
    $last=$stmt->fetchColumn();
    if($last){
        $num=intval(substr($last,strrpos($last,'-')+1))+1;
    } else {
        $num=1;
    }
    return $prefix.'-'.str_pad($num,4,'0',STR_PAD_LEFT);
}

// ============================================================
// DUE DATE HELPERS
// ============================================================
function getGSTDueDate($return_type,$period,$periodicity='Monthly'){
    $parts=explode('-',$period);
    if(count($parts)==2){
        $d=date_create("01 {$parts[0]} {$parts[1]}");
        if($d){
            $next=date_modify(clone $d,'+1 month');
            if(stripos($return_type,'GSTR-1')!==false)
                return date_format($next,'Y-m-').($periodicity==='Quarterly'?'13':'11');
            if(stripos($return_type,'GSTR-3B')!==false)
                return date_format($next,'Y-m-').($periodicity==='Quarterly'?'22':'20');
        }
    }
    if(in_array($return_type,['GSTR-9','GSTR-9C'])){
        preg_match('/(\d{4})/',$period,$m);
        if(!empty($m[1])) return ($m[1]+1).'-12-31';
    }
    if($return_type==='GSTR-4') {
        preg_match('/(\d{4})/',$period,$m);
        if(!empty($m[1])) return ($m[1]+1).'-04-30';
    }
    return null;
}

function getETDSDueDate($quarter,$fy){
    $y=intval(substr($fy,0,4));
    return ['Q1'=>$y.'-07-31','Q2'=>$y.'-10-31','Q3'=>($y+1).'-01-31','Q4'=>($y+1).'-05-31'][$quarter]??null;
}

// ============================================================
// TRIGGER / TARGET / STATUTORY DATE CALCULATION
// Statutory = legal due date as per Act (editable case-by-case)
// Target    = internal goal to finish before statutory due date
// Trigger   = date work should start / become visible as due
// ============================================================

// GST: returns ['statutory'=>date, 'target'=>date, 'trigger'=>date]
function getGSTWorkflowDates($return_type, $period, $periodicity = 'Monthly') {
    $statutory = getGSTDueDate($return_type, $period, $periodicity);
    if (!$statutory) return ['statutory'=>null,'target'=>null,'trigger'=>null];

    $is_gstr1  = (stripos($return_type, 'GSTR-1') !== false && stripos($return_type, 'GSTR-1A') === false);
    $is_gstr3b = (stripos($return_type, 'GSTR-3B') !== false);

    if ($is_gstr1) {
        // Statutory 11th (monthly) -> Target 5th, Trigger 1st of same due month
        $target  = date('Y-m-05', strtotime($statutory));
        $trigger = date('Y-m-01', strtotime($statutory));
    } elseif ($is_gstr3b) {
        // Statutory 20th (monthly) -> Target 15th, Trigger 10th of same due month
        $target  = date('Y-m-15', strtotime($statutory));
        $trigger = date('Y-m-10', strtotime($statutory));
    } else {
        // Generic: target = statutory - 5 days, trigger = statutory - 10 days
        $target  = date('Y-m-d', strtotime($statutory.' -5 days'));
        $trigger = date('Y-m-d', strtotime($statutory.' -10 days'));
    }
    return ['statutory'=>$statutory, 'target'=>$target, 'trigger'=>$trigger];
}

// ETDS: returns statutory/target/trigger for the return + auto Form 16A due date
function getETDSWorkflowDates($quarter, $fy) {
    $statutory = getETDSDueDate($quarter, $fy);
    if (!$statutory) return ['statutory'=>null,'target'=>null,'trigger'=>null,'form16a_due'=>null];

    // Target = statutory - 7 days, Trigger = statutory - 20 days (data collection starts earlier)
    $target  = date('Y-m-d', strtotime($statutory.' -7 days'));
    $trigger = date('Y-m-d', strtotime($statutory.' -20 days'));
    // Form 16A due = statutory + 15 days (as per Income Tax Rules)
    $form16a_due = date('Y-m-d', strtotime($statutory.' +15 days'));

    return ['statutory'=>$statutory, 'target'=>$target, 'trigger'=>$trigger, 'form16a_due'=>$form16a_due];
}

function getPTaxDueDate($type,$period,$fy){
    if($type==='PTEC') {
        // Annual - 30 June
        $y=intval(substr($fy,0,4));
        return ($y+1).'-06-30';
    }
    // PTRC Monthly - last day of month
    $parts=explode('-',$period);
    if(count($parts)==2){
        $d=date_create("01 {$parts[0]} {$parts[1]}");
        if($d) return date_format($d,'Y-m-t');
    }
    return null;
}

// ============================================================
// DISPLAY HELPERS
// ============================================================
function fmtDate($d){ return $d?date('d-M-Y',strtotime($d)):'-'; }

function daysUntil($d){
    if(!$d) return null;
    return intval((strtotime($d)-time())/86400);
}

function dueDateBadge($date){
    if(!$date) return '<span class="badge badge-secondary">-</span>';
    $days=daysUntil($date);
    if($days<0)   return '<span class="badge badge-danger">Overdue '.abs($days).'d</span>';
    if($days<=7)  return '<span class="badge badge-danger">'.fmtDate($date).' ('.$days.'d)</span>';
    if($days<=15) return '<span class="badge badge-warning">'.fmtDate($date).' ('.$days.'d)</span>';
    if($days<=30) return '<span class="badge badge-info">'.fmtDate($date).' ('.$days.'d)</span>';
    return '<span class="badge badge-success">'.fmtDate($date).'</span>';
}

// Shows whether work has been triggered yet, based on trigger_date vs today
function triggerStatusBadge($trigger_date) {
    if (!$trigger_date) return '<span class="badge badge-secondary">-</span>';
    $days = daysUntil($trigger_date);
    if ($days > 0) return '<span class="badge badge-secondary">Triggers in '.$days.'d</span>';
    return '<span class="badge badge-warning">⚡ Triggered '.fmtDate($trigger_date).'</span>';
}

// Generic small date badge (no urgency coloring) - for target date display
function targetDateBadge($date) {
    if (!$date) return '<span class="badge badge-secondary">-</span>';
    $days = daysUntil($date);
    if ($days < 0) return '<span class="badge badge-danger">'.fmtDate($date).' (missed)</span>';
    return '<span class="badge badge-info">'.fmtDate($date).'</span>';
}

function statusBadge($s){
    $m=['Filed'=>'badge-success','Pending Data'=>'badge-secondary','Data Received'=>'badge-info',
        'Under Preparation'=>'badge-info','Under Review'=>'badge-warning','Ready to File'=>'badge-warning',
        'On Hold'=>'badge-danger','Not Applicable'=>'badge-secondary','Pending'=>'badge-secondary',
        'Challan Pending'=>'badge-danger','Challan Paid'=>'badge-info',
        'Return Under Preparation'=>'badge-info','Correction Required'=>'badge-danger',
        'Not Started'=>'badge-secondary','Documents Pending'=>'badge-danger'];
    return '<span class="badge '.($m[$s]??'badge-secondary').'">'.htmlspecialchars($s).'</span>';
}

// ============================================================
// FINANCIAL YEAR HELPERS
// ============================================================
function currentFY(){
    $m=intval(date('n')); $y=intval(date('Y'));
    return ($m>=4?$y:$y-1).'-'.(($m>=4?$y+1:$y)-2000);
}

function getFYList($from=2022){
    $y=intval(date('Y')); $m=intval(date('n'));
    $max=$m>=4?$y+1:$y; $list=[];
    for($i=$from;$i<=$max;$i++) $list[]=$i.'-'.($i+1-2000);
    return array_reverse($list);
}

function getMonthPeriods($fy){
    $sy=intval(substr($fy,0,4));
    $months=['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar'];
    $out=[];
    foreach($months as $i=>$m) $out[]=$m.'-'.($i<9?$sy:$sy+1);
    return $out;
}

function getQuarterPeriods($fy){
    $s=substr($fy,-2);
    return ["Q1-FY$s","Q2-FY$s","Q3-FY$s","Q4-FY$s"];
}

// ── DEFAULT PERIOD FROM SETTINGS ─────────────────────────
function defaultPeriod($register = 'gst') {
    static $cache = [];
    if (isset($cache[$register])) return $cache[$register];

    // Per-register setting keys, e.g. default_fy_gst / default_period_gst
    $fy_key  = "default_fy_$register";
    $per_key = "default_period_$register";

    try {
        $r = getDB()->prepare(
            "SELECT setting_key,setting_value FROM app_settings WHERE setting_key IN(?,?,?,?)"
        );
        $r->execute([$fy_key, $per_key, 'default_fy', 'default_period']);
        $vals = ['fy_specific'=>'', 'period_specific'=>'', 'fy_legacy'=>'', 'period_legacy'=>''];
        foreach ($r->fetchAll() as $row) {
            if ($row['setting_key'] === $fy_key)            $vals['fy_specific']     = $row['setting_value'];
            if ($row['setting_key'] === $per_key)           $vals['period_specific'] = $row['setting_value'];
            if ($row['setting_key'] === 'default_fy')       $vals['fy_legacy']       = $row['setting_value'];
            if ($row['setting_key'] === 'default_period')   $vals['period_legacy']   = $row['setting_value'];
        }
        // Prefer per-register setting; fall back to legacy single setting; fall back to auto
        $fy     = $vals['fy_specific']     ?: $vals['fy_legacy']     ?: currentFY();
        $period = $vals['period_specific'] ?: $vals['period_legacy'] ?: date('M-Y', strtotime('first day of last month'));
        $dp = ['fy' => $fy, 'period' => $period];
    } catch (Exception $e) {
        $dp = ['period' => date('M-Y', strtotime('first day of last month')), 'fy' => currentFY()];
    }

    $cache[$register] = $dp;
    return $dp;
}

function paginate($total,$per_page,$page){
    return['total'=>$total,'per_page'=>$per_page,'current'=>$page,
           'total_pages'=>ceil($total/$per_page),'offset'=>($page-1)*$per_page];
}

// ── DERIVE FILED DATE FROM ITR-V ACKNOWLEDGEMENT NUMBER ──
// Last 6 digits of ITR-Ack are the filing date in ddmmyy format
function deriveFiledDateFromAck($ack) {
    $ack = trim($ack ?? '');
    // Keep only digits
    $digits = preg_replace('/[^0-9]/', '', $ack);
    if (strlen($digits) < 6) return null;
    $last6 = substr($digits, -6);
    $dd = substr($last6, 0, 2);
    $mm = substr($last6, 2, 2);
    $yy = substr($last6, 4, 2);
    // Basic sanity check
    if (intval($dd) < 1 || intval($dd) > 31) return null;
    if (intval($mm) < 1 || intval($mm) > 12) return null;
    $yyyy = '20' . $yy;
    $date = "$yyyy-$mm-$dd";
    // Validate it's a real date
    $ts = strtotime($date);
    if (!$ts || date('Y-m-d', $ts) !== $date) return null;
    return $date;
}
