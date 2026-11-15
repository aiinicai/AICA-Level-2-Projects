"""Visible, user-triggered ICAI handoff. Legacy selectors are UNVERIFIED live.
No credential/OTP capture, internal API, CAPTCHA bypass or final submission.
"""
import datetime,os,re,threading,time
from decimal import Decimal,ROUND_HALF_UP

LOGIN_URL='https://udin.icai.org/ICAI/login'
SELECTOR_STATUS='UNVERIFIED live; mapped from the supplied original app'
NAV="//*[self::a or self::button or @role='button' or @role='menuitem'][translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='generate udin']"

def payload_from_case(case):
    missing=[]
    names=' & '.join(p.name for p in case.applicants if p.name.strip())
    if not case.applicants or any(not p.name.strip() for p in case.applicants):missing.append('Applicant name(s)')
    frn=case.settings.get('frn','').strip()
    if not frn:missing.append('Firm registration number (FRN)')
    raw=case.report.get('cert_date','');date=''
    for fmt in ('%d.%m.%Y','%d-%m-%Y','%d/%m/%Y'):
        try:date=datetime.datetime.strptime(raw,fmt).strftime('%d-%m-%Y');break
        except ValueError:pass
    if not date:missing.append('Valid signing/certificate date')
    if not any(i['kind']=='asset' for i in case.items):missing.append('At least one reviewed asset')
    def total(immovable):return format(sum((Decimal(str(i['amount'])) for i in case.items if i['kind']=='asset' and (i['category']=='Immovable Property')==immovable),Decimal(0)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'f')
    purpose=case.report.get('purpose','').strip() or 'Embassy Purpose'
    suffix='net asset certificate for embassy purpose'
    description='Net Asset Report for '+names+'; '+purpose
    if suffix.casefold() not in description.casefold():description+='; '+suffix
    return dict(frn=frn,name=names,cert_date=date,imm_total=total(True),mov_total=total(False),description=description),missing

def create_driver():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
    except ImportError as exc:raise RuntimeError('Install optional Selenium requirements and Chrome to use assisted UDIN. The manual portal remains available.') from exc
    options=webdriver.ChromeOptions();options.add_argument('--start-maximized')
    service=Service(log_output=os.devnull)
    if os.name=='nt':
        import subprocess
        service.creation_flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    return webdriver.Chrome(options=options,service=service)

def wait_for(check,timeout=30):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        found=check()
        if found:return found
        time.sleep(.25)
    raise RuntimeError('Expected visible portal control not found in time. Selectors are unverified; finish that field manually in the browser.')

class UdinSession:
    def __init__(self,driver,waiter=wait_for,clock=time.monotonic):
        self.driver=driver;self.waiter=waiter;self.clock=clock;self.filled=False;self._otp_lock=threading.Lock();self._last_otp=None
    def visible(self,by,locator):return [e for e in self.driver.find_elements(by,locator) if e.is_displayed()]
    def first(self,by,locator,timeout=30):
        def check():
            candidates=self.visible(by,locator)
            return candidates[0] if len(candidates)==1 else False
        return self.waiter(check,timeout)
    def set_value(self,field,value):
        try:field.click();field.clear();field.send_keys(str(value))
        except Exception:
            if not field.is_displayed():raise RuntimeError('Expected input is not visible.')
            self.driver.execute_script("const e=arguments[0],v=arguments[1],p=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,'value').set.call(e,v);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}));",field,str(value))
    def choose(self,control,typed,match):
        self.set_value(control,typed)
        def option():
            choices=[e for e in self.visible('xpath',"//mat-option | //*[@role='option'] | //ng-dropdown-panel//div[contains(@class,'ng-option')]") if match.lower() in e.text.strip().lower()]
            return choices[0] if len(choices)==1 else False
        self.waiter(option,15).click()
    def login(self,username,password):
        fields=self.visible('xpath',"//input")
        username_fields=[field for field in fields if (field.get_attribute('type') or 'text').lower()!='password' and any(word in ((field.get_attribute('id') or '')+' '+(field.get_attribute('name') or '')+' '+(field.get_attribute('placeholder') or '')).lower() for word in ('user','member','mrn','login'))]
        if len(username_fields)!=1:raise RuntimeError('Could not uniquely locate the ICAI MRN/username field.')
        password_fields=[field for field in fields if (field.get_attribute('type') or '').lower()=='password']
        if len(password_fields)!=1:raise RuntimeError('Could not uniquely locate the ICAI password field.')
        self.set_value(username_fields[0],username);self.set_value(password_fields[0],password)
        self.filled=False
        return 'Credentials filled. Complete CAPTCHA and click Login in Chrome.'
    def open_and_fill(self,data,credentials=None):
        self.driver.get(LOGIN_URL)
        # User alone enters credentials/CAPTCHA and signs in. Presence of a password
        # disappearing is not treated as proof of successful authentication.
        if credentials:
            self.login(credentials['username'],credentials['password'])
            self.waiter(lambda: any(e.is_displayed() and re.search(r'generate\s+udin',e.text or '',re.I) for e in self.visible('xpath',"//body//*[self::a or self::button or @role='button']")),300)
        nav=self.first('xpath',NAV,180);nav.click()
        failures=[]
        def step(label,action):
            try:action()
            except Exception:failures.append(label+' (visible control/option not verified; complete manually)')
        step('FRN',lambda:self.choose(self.first('id','FRN'),data['frn'].split()[0],data['frn'].split()[0]))
        # Official option remains Net Worth: do not invent a renamed portal option.
        step('Certificate type',lambda:self.choose(self.first('id','certficateType'),'net worth','net worth'))
        step('Signing date',lambda:self.set_value(self.first('xpath',"//input[contains(translate(@placeholder,'DMY','dmy'),'dd-mm-yyyy')]"),data['cert_date']))
        try:
            if self.visible('xpath',"//*[contains(@class,'mat-datepicker-content') or contains(@class,'mat-calendar')]"):self.driver.find_element('tag name','body').send_keys('\ue00c')
        except Exception:failures.append('Close date picker manually before continuing')
        def figures():
            ps=self.visible('xpath',"//input[translate(normalize-space(@placeholder),'PARTICULARS','particulars')='particulars']")
            fs=self.visible('xpath',"//input[translate(normalize-space(@placeholder),'FIGURES IN INR','figures in inr')='figures in inr']")
            if len(ps)!=2 or len(fs)!=2:raise RuntimeError('Two required numerical rows not uniquely identified.')
            for p,f,label,amount in zip(ps,fs,('Total Immovable Assets','Total Movable Assets'),(data['imm_total'],data['mov_total'])):
                self.set_value(p,label);self.set_value(f,amount)
                rows=p.find_elements('xpath',"./ancestor::*[count(.//input[translate(normalize-space(@placeholder),'PARTICULARS','particulars')='particulars'])=1 and count(.//input[translate(normalize-space(@placeholder),'FIGURES IN INR','figures in inr')='figures in inr'])=1][1]")
                if len(rows)!=1:raise RuntimeError('Numerical row container not unique.')
                controls=[e for e in rows[0].find_elements('css selector','ng-select, mat-select, select, [role="combobox"]') if e.is_displayed()]
                preferred=[e for e in controls if e.tag_name.lower() in ('ng-select','mat-select','select')]
                controls=preferred or controls
                if len(controls)!=1:raise RuntimeError('Actual denomination selector not unique.')
                control=controls[0]
                if control.tag_name.lower()=='select':
                    from selenium.webdriver.support.ui import Select
                    Select(control).select_by_visible_text('Actual')
                else:
                    click_target=control
                    if control.tag_name.lower()=='ng-select':
                        containers=control.find_elements('css selector','.ng-select-container')
                        if len(containers)==1:click_target=containers[0]
                    click_target.click()
                    self.waiter(lambda:next((e for e in self.visible('xpath',"//mat-option | //*[@role='option'] | //ng-dropdown-panel//div[contains(@class,'ng-option')]") if e.text.strip().lower()=='actual'),False),15).click()
        step('Immovable / movable numerical rows and Actual denomination',figures)
        step('Document description',lambda:self.set_value(self.first('xpath',"//textarea[contains(translate(@placeholder,'DETAILS OF THE DOCUMENT','details of the document'),'details of the document')]"),data['description']))
        self.filled=not failures
        return failures
    def request_otp(self):
        if not self.filled:raise ValueError('The assisted mapping is incomplete. Review/fill the portal manually; request OTP in the portal yourself, or restart the assistant after verifying its fields.')
        with self._otp_lock:
            now=self.clock()
            if self._last_otp is not None and now-self._last_otp<60:raise ValueError('An OTP request was already attempted. Wait at least 60 seconds before an explicit retry.')
            # Reserve before clicking: a timeout/error must not trigger a duplicate send.
            self._last_otp=now
        def ready():
            controls=self.visible('xpath',"//button | //input[@type='button'] | //*[@role='button']")
            matches=[e for e in controls if re.sub(r'\s+','',(e.text or e.get_attribute('value') or '')).lower() in ('sendotp','requestotp') and e.is_enabled()]
            return matches[0] if len(matches)==1 else False
        button=self.waiter(ready,15);button.click()
        return 'OTP requested once. Enter the OTP and complete final generation yourself in the browser. Nothing was generated/submitted by this app.'
    def read_generated_udin(self):
        body=self.driver.find_element('tag name','body').text
        if not re.search(r'generated\s+successfully|udin\s+generated',body,re.I):raise ValueError('A successful generation message was not found. Complete final generation yourself in the browser.')
        found=re.findall(r'\bUDIN\s*[: -]\s*([A-Z0-9]{18})\b',body,re.I)
        if len(set(found))!=1:raise ValueError('Generated UDIN was not unique/readable. Copy it manually to the report field.')
        return found[0]
