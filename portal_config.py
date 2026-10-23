"""
GST portal endpoints and page elements.

Every item below was checked on the live portal (October 2026) in a logged-in
session. If GSTN changes something, this is the only file to edit.

KEY FACTS LEARNED FROM THE LIVE PORTAL
1. Typing a portal URL directly (no Referer) gives "Access Denied".
   -> The app always moves between pages from INSIDE the page (location.href),
      exactly like clicking a link.
2. The captcha appears only after the username is typed and focus leaves it.
   The captcha box accepts digits only and blocks paste.
3. GSTR-3B PDF, GSTR-1 PDF and GSTR-2B Excel are built inside the browser by
   JavaScript from JSON data. The app reads that same JSON and builds clean
   Excel files with pandas, so nothing depends on a browser "download".
4. GSTR-1 full JSON and GSTR-2A files are prepared by the portal in the
   background (up to 20 minutes) - request first, collect later.
5. The GSTR-2B page opens only through the Returns Dashboard tile (POST).
"""

SERVICES = "https://services.gst.gov.in"
RETURNS = "https://return.gst.gov.in"
GSTR2B = "https://gstr2b.gst.gov.in"
EWB = "https://ewaybillgst.gov.in"

PAGES = {
    "login": SERVICES + "/services/login",
    "services_dashboard": SERVICES + "/services/auth/dashboard",
    "certificates": SERVICES + "/services/auth/certs",
    "returns_dashboard": RETURNS + "/returns/auth/dashboard",
}

API = {
    # services.gst.gov.in
    "ustatus": "/services/api/ustatus",                                   # gstin, role
    "certs": "/services/auth/api/get/certs",                              # list: frmno, docid, applnId
    "cert_pdf": "/document/certs/{docid}/{applnId}",                      # PDF (attachment)
    "aato": "/services/auth/api/dashboard/aggTurnOver?fy={fy}",           # aggregate turnover
    # return.gst.gov.in
    "dropdown": "/returns/auth/api/dropdown",                             # FYs and months (MMYYYY)
    "rolestatus": "/returns/auth/api/rolestatus?rtn_prd={prd}",           # tiles: return_ty, due_dt, status FIL/NF
    "efiled": "/returns/auth/api/efiledReturns",                          # POST {fy, rfp, qtr, mth, rtntp}
    "gstr3b": "/returns/auth/api/gstr3b/getgenpdf?rtn_prd={prd}",         # data behind GSTR-3B PDF
    "gstr1_summary": "/returns/auth/api/gstr1/summary?rtn_prd={prd}",     # section-wise summary
    "gstr9": "/returns2/auth/api/gstr9/gstr9pdf?fp={fp}",                 # data behind GSTR-9 PDF (fp = 03YYYY)
    "offline_generate": "/returns/auth/api/offline/download/generate?flag={flag}&rtn_prd={prd}&rtn_typ={typ}",
    "offline_file": "/returns/auth/api/offline/download/url?rtn_prd={prd}&rtn_typ={typ}&file_num={n}",
    # gstr2b.gst.gov.in
    "gstr2b": "/gstr2b/auth/api/gstr2b/getjson?rtnprd={prd}",
    # notices and orders (services.gst.gov.in) - POST
    "notices": "/services/auth/api/get/notices",                          # POST searchDetail -> list of notice/order
    "notices_cases": "/litserv/auth/api/case/task/get",                   # POST {gstIn} -> adjudication/appeal tasks
    "notice_update": "/services/auth/api/update/ordsts",                  # POST {orderID} marks read
    # notice / order PDFs
    "notice_gstr3a": RETURNS + "/returns/auth/gstr3a?defaulterId={defid}&noticeOrderId={noid}&dtOfIssue={dt}",
    "notice_doc": SERVICES + "/document/{docid}",                         # order / notice PDF by docId (verified live)
}

LOGIN = {
    "username": "#username",
    "password": "#user_pass",
    "captcha_input": "#captcha",
    "captcha_img": "#imgCaptcha",
    "captcha_refresh": "button[ng-click='refreshCaptcha()']",
    "login_btn": "button[type='submit']",
    "error": "p.err:not(.ng-hide), span.err:not(.ng-hide), .alert-danger:not(.ng-hide)",
}

# e-way bill portal (ewaybillgst.gov.in) - login page, mapped live
EWB_LOGIN = {
    "page": EWB + "/login.aspx",
    "mainmenu": EWB + "/mainmenu.aspx",
    "username": "#txt_username",
    "password": "#txt_password",
    "captcha_img": "#imgcaptcha",
    "captcha_input": "#txtCaptcha",
    "captcha_refresh": "#btnCaptchaImage",
    "login_btn": "#btnLogin",
    # GSTIN + name banner on every logged-in page (used to confirm login
    # and to name the save folder). Live text:
    #   "GSTIN :37AAFCT1064P1ZW - Name : M/S ... - User : Tax Payer"
    "banner_text": "GSTIN :",
}

# e-way bill detailed reports (ASP.NET WebForms), mapped live Oct 2026.
#
# KEY FACTS LEARNED FROM THE LIVE EWB PORTAL
# 1. A report page typed as a URL redirects to mainmenu.aspx (referer rule).
#    -> reach it the way a menu click does: from inside mainmenu.aspx set
#       location.href to the report URL (Referer = mainmenu is then sent).
# 2. The detailed reports are capped at a 5-DAY range per query. A wider
#    range raises: "Date Range shouldn't be more than 5 Days..!" and nothing
#    is fetched. Allowed dates: 01/04/2018 .. today.  Date format dd/mm/yyyy.
# 3. Results render into a jQuery DataTable (#ListgenMetable) - 28 columns.
#    A real "Export To Excel" button then streams the FULL result set as an
#    .xls/.xlsx (not just the 10 rows shown on the first DataTables page).
# 4. The Subuser dropdown (ddlUserId) has an ALL option (value "0"); set it
#    so bills raised by every sub-user / API user are included.
# 5. "Monthwise download EWBs" (CommomReport_month.aspx) gives a whole month
#    in one file but is only served 8 AM - 12 PM IST; outside that window the
#    page redirects to mainmenu. Used as a fast path when in-window; the
#    5-day loop is the reliable any-time path.
EWB_REPORT = {
    "outward": EWB + "/Reports/CommomReport.aspx?id=3",   # EWB generated by me
    "inward":  EWB + "/Reports/CommomReport.aspx?id=4",   # Inward supplies
    "monthwise": EWB + "/Reports/CommomReport_month.aspx",
    "date_from": "#ctl00_ContentPlaceHolder1_txtDate",
    "date_to":   "#ctl00_ContentPlaceHolder1_txtDate1",
    "subuser":   "#ctl00_ContentPlaceHolder1_ddlUserId",  # ALL = value "0"
    "subuser_all": "0",
    "go_btn":    "#ctl00_ContentPlaceHolder1_btn_submit",
    "grid":      "#ListgenMetable",
    "export_excel": "#ctl00_ContentPlaceHolder1_List_genMe_btn_export_excel",
    "max_days": 5,                                         # portal's hard cap
    "min_date": "01/04/2018",
    "monthwise_window": (8, 12),                           # IST hours, inclusive start
    "columns": [
        "EWB.No", "EWB Date", "Supply Type", "Doc. No", "Doc. Date", "Doc. Type",
        "Other Party GSTIN.", "Transporter Details", "From GSTIN", "From GSTIN Info",
        "TO GSTIN", "TO GSTIN Info", "Status & Other Party Rejected", "No of Items",
        "Main HSN Code", "HSN Desc", "Assessable Value", "SGST Value", "CGST Value",
        "IGST Value", "CESS Value", "CESS Non.Advol Value", "Other Value",
        "Total Inv.Value", "Valid Till Date", "Mode of GEN.", "IRN", "Source",
    ],
}

RETURNS_DASH = {
    "fy": "select[name='fin']",
    "quarter": "select[name='quarter']",
    "month": "select[name='mon']",
}

# Portal error codes seen live
ERR_IN_PROGRESS = {"RTN_24_1_3B"}          # offline file being generated
ERR_NO_RECORD = {"RET13510", "RETWEB_23"}

MONTHS = ["April", "May", "June", "July", "August", "September",
          "October", "November", "December", "January", "February", "March"]


def prd_code(fy: str, month: str) -> str:
    """('2025-26','April') -> '042025'"""
    idx = MONTHS.index(month)
    mm = (idx + 3) % 12 + 1
    yyyy = int(fy[:4]) + (0 if idx < 9 else 1)
    return f"{mm:02d}{yyyy}"


def prd_label(prd: str) -> str:
    """'042025' -> '2025-04'"""
    return f"{prd[2:]}-{prd[:2]}"


def quarter_label(month: str) -> str:
    return f"Quarter {MONTHS.index(month) // 3 + 1}"
