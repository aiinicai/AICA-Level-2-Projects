"""Portal-specific URLs, request fields, response aliases, and policy."""
from dataclasses import dataclass
BASE = "https://services.gst.gov.in"
PATHS = {"page":"/services/searchtp", "pan_page":"/services/searchtpbypan", "captcha":"/services/captcha", "GSTIN":"/services/api/search/taxpayerDetails", "PAN":"/services/api/get/gstndtls", "returns":"/services/api/search/taxpayerReturnDetails"}
HEADERS = {"User-Agent":"Mozilla/5.0 GSTLookup/1.0", "Accept":"application/json, text/plain, */*", "Referer": BASE+PATHS["page"], "Origin": BASE}
FIELDS = {"GSTIN":"gstin", "PAN":"panNO", "captcha":"captcha", "year":"fy", "error":"errorCode", "pan_list":"gstinResList", "returns":"filingStatus"}
ALIASES = {"TRADE NAME":["tradeNam","tradeName"], "DATE OF REGISTRATION":["rgdt"], "CONSTITUTION":["ctb"], "GSTIN/UIN STATUS":["sts"], "TAXPAYER":["dty"], "ADMIN OFFICE":["admOfc"], "OTHER OFFICE":["othrOfc"], "PRINCIPAL PLACE ADDRESS":["pradr"], "ADDITIONAL PLACE OF BUSINESS":["adadr"], "GOODS":["gds"], "SERVICES":["sac"]}
RETURN_FIELDS = {"type":"rtntype", "period":"taxp", "status":"status", "date":"dof", "year":"fy"}
NOT_FOUND = {"SWEB_9032","SWEB_9035","SWEB_10001"}
CAPTCHA_ERRORS = {"SWEB_9000"}
COLUMNS = ["PAN", "GST NUMBER", "TRADE NAME", "DATE OF REGISTRATION", "CONSTITUTION", "GSTIN/UIN STATUS", "TAXPAYER", "ADMIN OFFICE", "OTHER OFFICE", "PRINCIPAL PLACE ADDRESS", "ADDITIONAL PLACE OF BUSINESS", "DEALING IN GOODS AND SERVICES (HSN / SAC CODE WITH DESCRIPTION)", "RETURN STATUS YEAR", "GSTR-3B", "GSTR-1/IFF", "GSTR-9", "GSTR-9C"]
NA = "Not Available"
@dataclass
class Settings:
    base: str = BASE
    interval: float = 3.0
    timeout: float = 25.0
    daily_cap: int = 100
    retries: int = 3
    demo: bool = False
    def __post_init__(self):
        if not self.demo: self.interval = max(2.0, self.interval)
        self.retries = min(3,max(1,self.retries))

STRUCTURE = {"address":"adr", "business":"bzsdtls", "goods_code":"hsncd", "service_code":"saccd", "goods_description":"gdes", "service_description":"sdes", "nested_error":"error", "error_code":"error_cd", "captcha_query":"rnd"}

PATHS["goods"] = "/services/api/search/goodservice"
STRUCTURE.update({"goods_list":"bzgddtls", "services_list":"bzsdtls", "centre":"ctj", "state":"stj"})

# Observed in current searchtpCtrl1.0.js: initialize years, then send selected year.value.
PATHS['years'] = '/services/api/dropdownfinyear'
YEAR_FIELDS = {'status':'status','data':'data','label':'year','value':'value'}

COLUMNS.append("Legal Name of Business")
ALIASES["Legal Name of Business"] = ["lgnm", "legalNameOfBusiness"]
CAPTCHA_PATTERN = r"[0-9]{6}"

# Public searchtaxpayer template displays cxdt as the effective date for cancelled/suspended statuses.
STATUS_DATE_FIELD = "cxdt"

REQUEST_LABELS = {PATHS["page"]:"Opening GST taxpayer search", PATHS["captcha"]:"Loading CAPTCHA image", PATHS["GSTIN"]:"Validating taxpayer details", PATHS["PAN"]:"Finding GSTINs for this PAN", PATHS["goods"]:"Loading goods and services", PATHS["years"]:"Loading available financial years", PATHS["returns"]:"Loading return filing records"}
