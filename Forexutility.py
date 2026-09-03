import os
import shutil
import sqlite3
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from PIL import Image, ImageTk

# Modern Corporate UI Framework
import customtkinter as ctk

# ==========================================
# 1. CORPORATE THEMING & DB SETUP
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# KK Advisory Palette - Navy & Gold
CORP_BG = "#060D1A"          # Deep Dark Blue/Navy
CORP_CARD = "#0F1C38"        # Card Navy Surface
CORP_HEADER_CARD = "#14254B" # Light Navy for Header Card/Logo frame
CORP_ACCENT = "#D4AF37"      # Gold Accent
CORP_SUCCESS = "#10B981"     # Emerald Green
CORP_WARNING = "#F59E0B"     # Amber
CORP_ERROR = "#EF4444"       # Vibrant Red
CORP_TEXT = "#FFFFFF"        # Bright White for high contrast
CORP_TEXT_MUTED = "#CBD5E1"  # Soft Off-White for readability

DB_FILE = "remittance_corporate.db"

def execute_query(query, params=(), fetch=False, fetch_all=True):
    with sqlite3.connect(DB_FILE, timeout=20) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall() if fetch_all else cursor.fetchone()
        conn.commit()

def init_db():
    queries = [
        '''CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY, vendor_name TEXT NOT NULL,
            remittance_type TEXT NOT NULL, currency TEXT NOT NULL, amount REAL NOT NULL,
            status TEXT NOT NULL, folder_path TEXT NOT NULL, created_at TEXT NOT NULL,
            detailed_service TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS documents (
            doc_id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
            doc_type TEXT NOT NULL, file_name TEXT NOT NULL, file_path TEXT NOT NULL,
            uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS processing_details (
            request_id TEXT PRIMARY KEY, purpose_code TEXT, swift_ref TEXT, updated_at TEXT
        )''',
        '''CREATE TABLE IF NOT EXISTS messages (
            msg_id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
            sender_role TEXT NOT NULL, message TEXT NOT NULL, timestamp TEXT NOT NULL
        )'''
    ]
    for q in queries:
        execute_query(q)
    
    try:
        execute_query("ALTER TABLE requests ADD COLUMN detailed_service TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

init_db()

REMITTANCE_CATEGORIES = {
    "Form A1 (Import of Goods)": ["Commercial Invoice", "Bill of Entry (BOE)", "Transport Document (BL / Airway)", "Internal Approval Note"],
    "Form A2 (Services / Royalty / Travel)": ["Vendor Invoice / Agreement", "Tax Residency Cert (TRC) / 10F", "Internal Approval Note"]
}

def open_local_file(filepath):
    if not os.path.exists(filepath):
        messagebox.showerror("Error", "File not found on disk.")
        return
    if platform.system() == 'Windows':
        os.startfile(filepath)
    elif platform.system() == 'Darwin':
        subprocess.call(('open', filepath))
    else:
        subprocess.call(('xdg-open', filepath))

# ==========================================
# 2. APPLICATION SHELL
# ==========================================
class CorporateRemittanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("KK Advisory Services | Global Remittance Portal")
        self.geometry("1300x850")
        self.configure(fg_color=CORP_BG)

        self.root_storage = os.path.join(os.getcwd(), "Remittance_Repository")
        os.makedirs(self.root_storage, exist_ok=True)

        self.selected_files = {} 
        self.known_req_ids = set()
        self.current_selected_req_id = None

        self.setup_ttk_styles()
        self.build_header()
        self.build_tabs()
        
        # Safe thread-free polling loop
        self.start_realtime_polling()

    def setup_ttk_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", 
                        background=CORP_CARD, foreground=CORP_TEXT, 
                        fieldbackground=CORP_CARD, rowheight=35, borderwidth=0, font=("Segoe UI", 11))
        style.configure("Treeview.Heading", 
                        background="#081023", foreground=CORP_ACCENT, 
                        font=("Segoe UI", 11, "bold"), borderwidth=1)
        style.map("Treeview", background=[('selected', CORP_ACCENT)], foreground=[('selected', "#000000")])

    def build_header(self):
        header = ctk.CTkFrame(self, fg_color=CORP_CARD, corner_radius=0, height=85)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Embedded Container for Logo
        logo_container = ctk.CTkFrame(header, fg_color="#FFFFFF", corner_radius=8, width=170, height=60)
        logo_container.pack(side="left", padx=20, pady=12)
        logo_container.pack_propagate(False)

        logo_loaded = False
        if os.path.exists("KK Logo.png"):
            try:
                pil_img = Image.open("KK Logo.png")
                # Maintain aspect ratio fitting nicely inside 150x50
                pil_img.thumbnail((150, 50), Image.Resampling.LANCZOS)
                logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                
                lbl_logo = ctk.CTkLabel(logo_container, image=logo_img, text="")
                lbl_logo.pack(expand=True)
                logo_loaded = True
            except Exception:
                logo_loaded = False

        if not logo_loaded:
            ctk.CTkLabel(logo_container, text="KK ADVISORY", font=ctk.CTkFont(size=14, weight="bold"), text_color="#0F1C38").pack(expand=True)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=10, pady=15)

        ctk.CTkLabel(title_frame, text="KK ADVISORY SERVICES", font=ctk.CTkFont(size=18, weight="bold"), text_color=CORP_ACCENT).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Outward Remittance & Forex Operations Management", font=ctk.CTkFont(size=12), text_color=CORP_TEXT_MUTED).pack(anchor="w")

        btn_change = ctk.CTkButton(header, text="Configure Directory", width=140, fg_color="#1E3A8A", hover_color="#2563EB", text_color=CORP_TEXT, font=ctk.CTkFont(weight="bold"), command=self.change_storage_path)
        btn_change.pack(side="right", padx=20, pady=22)

    def change_storage_path(self):
        folder = filedialog.askdirectory(initialdir=self.root_storage, title="Select Master Storage Directory")
        if folder:
            self.root_storage = folder
            messagebox.showinfo("Configured", f"Storage path updated successfully.\nNew Path: {self.root_storage}")

    def build_tabs(self):
        self.main_tabs = ctk.CTkTabview(self, fg_color=CORP_BG, segmented_button_fg_color=CORP_CARD, segmented_button_selected_color=CORP_ACCENT, segmented_button_selected_hover_color="#B89B2B", text_color=CORP_TEXT)
        self.main_tabs.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        self.tab_req = self.main_tabs.add("  Requestor Department  ")
        self.tab_treasury = self.main_tabs.add("  Treasury Operations  ")

        self.build_requestor_dashboard()
        self.build_treasury_dashboard()

    # ==========================================
    # 3. REQUESTOR DASHBOARD
    # ==========================================
    def build_requestor_dashboard(self):
        req_tabs = ctk.CTkTabview(self.tab_req, fg_color="transparent", segmented_button_selected_color="#1E3A8A")
        req_tabs.pack(fill="both", expand=True)

        t_new = req_tabs.add("New Submission")
        t_track = req_tabs.add("Track Payment Status")

        # --- SUB TAB: NEW SUBMISSION ---
        container = ctk.CTkScrollableFrame(t_new, fg_color="transparent")
        container.pack(fill="both", expand=True)

        card = ctk.CTkFrame(container, fg_color=CORP_CARD, corner_radius=8)
        card.pack(fill="x", pady=10)

        ctk.CTkLabel(card, text="Initiate Outward Remittance", font=ctk.CTkFont(size=18, weight="bold"), text_color=CORP_ACCENT).pack(anchor="w", padx=20, pady=(20, 10))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=10)

        lbl_font = ctk.CTkFont(size=13, weight="bold")
        
        ctk.CTkLabel(grid, text="Beneficiary Name*", font=lbl_font, text_color=CORP_TEXT).grid(row=0, column=0, sticky="w", padx=5, pady=8)
        self.ent_vendor = ctk.CTkEntry(grid, width=280, text_color=CORP_TEXT, font=ctk.CTkFont(size=13))
        self.ent_vendor.grid(row=0, column=1, sticky="w", padx=5, pady=8)

        ctk.CTkLabel(grid, text="Amount*", font=lbl_font, text_color=CORP_TEXT).grid(row=0, column=2, sticky="w", padx=15, pady=8)
        self.ent_amount = ctk.CTkEntry(grid, width=140, text_color=CORP_TEXT, font=ctk.CTkFont(size=13))
        self.ent_amount.grid(row=0, column=3, sticky="w", padx=5, pady=8)

        ctk.CTkLabel(grid, text="Currency*", font=lbl_font, text_color=CORP_TEXT).grid(row=1, column=0, sticky="w", padx=5, pady=8)
        self.cmb_currency = ctk.CTkComboBox(grid, values=["USD", "EUR", "GBP", "JPY", "AED", "SGD"], width=140, text_color=CORP_TEXT, font=ctk.CTkFont(size=13))
        self.cmb_currency.grid(row=1, column=1, sticky="w", padx=5, pady=8)

        ctk.CTkLabel(grid, text="Payment Category*", font=lbl_font, text_color=CORP_TEXT).grid(row=1, column=2, sticky="w", padx=15, pady=8)
        self.cmb_nature = ctk.CTkComboBox(grid, values=list(REMITTANCE_CATEGORIES.keys()), width=320, text_color=CORP_TEXT, font=ctk.CTkFont(size=13), command=self.render_doc_checklist)
        self.cmb_nature.grid(row=1, column=3, sticky="w", padx=5, pady=8)

        # DETAILED NATURE OF SERVICE TEXT BOX
        ctk.CTkLabel(card, text="Detailed Nature of Service:", font=lbl_font, text_color=CORP_TEXT).pack(anchor="w", padx=20, pady=(10, 2))
        self.txt_detailed_service = ctk.CTkTextbox(card, height=75, fg_color="#071022", border_width=1, border_color="#1E3A8A", text_color=CORP_TEXT, font=ctk.CTkFont(size=13))
        self.txt_detailed_service.pack(fill="x", padx=20, pady=(0, 10))

        # Dynamic Checklist Frame
        self.chk_frame = ctk.CTkFrame(card, fg_color="#071022", corner_radius=6, border_width=1, border_color="#1E3A8A")
        self.chk_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(card, text="Treasury Instructions / Remarks:", font=lbl_font, text_color=CORP_TEXT).pack(anchor="w", padx=20, pady=(5, 2))
        self.txt_req_msg = ctk.CTkTextbox(card, height=60, fg_color="#071022", border_width=1, border_color="#1E3A8A", text_color=CORP_TEXT, font=ctk.CTkFont(size=13))
        self.txt_req_msg.pack(fill="x", padx=20, pady=(0, 20))

        btn_bar = ctk.CTkFrame(card, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(btn_bar, text="Clear Form", fg_color="#1E3A8A", hover_color="#2563EB", text_color=CORP_TEXT, font=ctk.CTkFont(weight="bold"), command=self.reset_form).pack(side="left")
        ctk.CTkButton(btn_bar, text="Submit Package to Treasury", font=ctk.CTkFont(size=14, weight="bold"), text_color="#000000", fg_color=CORP_ACCENT, hover_color="#B89B2B", height=40, command=self.submit_request).pack(side="right")

        self.render_doc_checklist(self.cmb_nature.get())

        # --- SUB TAB: TRACK STATUS ---
        track_card = ctk.CTkFrame(t_track, fg_color=CORP_CARD, corner_radius=8)
        track_card.pack(fill="both", expand=True, pady=10)

        search_bar = ctk.CTkFrame(track_card, fg_color="transparent")
        search_bar.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(search_bar, text="Request ID:", font=ctk.CTkFont(weight="bold"), text_color=CORP_TEXT).pack(side="left", padx=5)
        self.ent_search = ctk.CTkEntry(search_bar, width=280, placeholder_text="e.g., REQ_20260901_123000", text_color=CORP_TEXT)
        self.ent_search.pack(side="left", padx=10)
        ctk.CTkButton(search_bar, text="Check Status", font=ctk.CTkFont(weight="bold"), fg_color="#1E3A8A", hover_color="#2563EB", text_color=CORP_TEXT, command=self.search_requestor_status).pack(side="left", padx=5)

        self.status_disp = ctk.CTkTextbox(track_card, fg_color="#071022", text_color=CORP_TEXT, border_width=1, border_color="#1E3A8A", font=ctk.CTkFont(size=13, family="Consolas"))
        self.status_disp.pack(fill="both", expand=True, padx=20, pady=10)

        self.btn_download_swift = ctk.CTkButton(track_card, text="⬇ Open Final SWIFT Copy", text_color="#000000", fg_color=CORP_ACCENT, hover_color="#B89B2B", font=ctk.CTkFont(weight="bold", size=14), state="disabled")
        self.btn_download_swift.pack(pady=20)

    def render_doc_checklist(self, choice):
        for w in self.chk_frame.winfo_children():
            w.destroy()
        self.selected_files.clear()

        ctk.CTkLabel(self.chk_frame, text="Mandatory Documents — Multiple files allowed per category", font=ctk.CTkFont(size=13, weight="bold"), text_color=CORP_ACCENT).pack(anchor="w", padx=15, pady=(15, 10))

        docs = REMITTANCE_CATEGORIES.get(choice, [])
        for doc in docs:
            self.selected_files[doc] = [] 
            row = ctk.CTkFrame(self.chk_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=6)

            ctk.CTkLabel(row, text=f"• {doc}:", width=250, anchor="w", font=ctk.CTkFont(size=13), text_color=CORP_TEXT).pack(side="left")
            st_lbl = ctk.CTkLabel(row, text="No files selected", text_color=CORP_ERROR, font=ctk.CTkFont(slant="italic", size=13))
            st_lbl.pack(side="left", padx=10)

            ctk.CTkButton(row, text="Select File(s)", width=100, font=ctk.CTkFont(weight="bold"), fg_color="#1E3A8A", hover_color="#2563EB", text_color=CORP_TEXT, command=lambda d=doc, l=st_lbl: self.browse_multiple_files(d, l)).pack(side="right")

    def browse_multiple_files(self, doc_name, label):
        paths = filedialog.askopenfilenames(title=f"Select files for {doc_name}", filetypes=[("Documents", "*.pdf *.png *.jpg *.jpeg")])
        if paths:
            self.selected_files[doc_name].extend(paths)
            count = len(self.selected_files[doc_name])
            label.configure(text=f"✓ {count} file(s) selected", text_color=CORP_SUCCESS)

    def reset_form(self):
        self.ent_vendor.delete(0, "end")
        self.ent_amount.delete(0, "end")
        self.txt_detailed_service.delete("1.0", "end")
        self.txt_req_msg.delete("1.0", "end")
        self.render_doc_checklist(self.cmb_nature.get())

    def submit_request(self):
        vendor = self.ent_vendor.get().strip()
        amt_str = self.ent_amount.get().strip()
        nature = self.cmb_nature.get()
        curr = self.cmb_currency.get()
        detailed_service = self.txt_detailed_service.get("1.0", "end-1c").strip()
        msg = self.txt_req_msg.get("1.0", "end-1c").strip()

        if not vendor or not amt_str:
            messagebox.showerror("Validation Error", "Beneficiary Name and Amount are required.")
            return

        try:
            amt = float(amt_str)
        except ValueError:
            messagebox.showerror("Validation Error", "Amount must be a valid number.")
            return

        req_docs = REMITTANCE_CATEGORIES.get(nature, [])
        missing = [d for d in req_docs if len(self.selected_files.get(d, [])) == 0]
        if missing:
            messagebox.showerror("Missing Attachments", f"Please attach at least one file for:\n\n{chr(10).join(missing)}")
            return

        req_id = f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        clean_vendor = "".join(x for x in vendor if x.isalnum() or x == " ").strip().replace(" ", "_")
        folder = os.path.join(self.root_storage, f"{req_id}_{clean_vendor}")
        os.makedirs(folder, exist_ok=True)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute_query('''INSERT INTO requests (request_id, vendor_name, remittance_type, currency, amount, status, folder_path, created_at, detailed_service)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                         (req_id, vendor, nature, curr, amt, "Pending Review", folder, now, detailed_service))

        for doc_type, file_list in self.selected_files.items():
            for idx, src in enumerate(file_list):
                base, ext = os.path.splitext(os.path.basename(src))
                fname = f"{base}_{idx+1}{ext}" if len(file_list) > 1 else base + ext
                dest = os.path.join(folder, fname)
                shutil.copy(src, dest)
                execute_query('''INSERT INTO documents (request_id, doc_type, file_name, file_path, uploaded_by, uploaded_at)
                                 VALUES (?, ?, ?, ?, ?, ?)''', 
                                 (req_id, doc_type, fname, dest, "Requestor", now))

        if msg:
            execute_query('''INSERT INTO messages (request_id, sender_role, message, timestamp) VALUES (?, ?, ?, ?)''', 
                          (req_id, "Requestor", msg, now))

        messagebox.showinfo("Success", f"Payment Package Submitted!\n\nYour Tracker ID is:\n{req_id}")
        self.reset_form()
        self.refresh_queue()

    def search_requestor_status(self):
        req_id = self.ent_search.get().strip()
        if not req_id: return
        
        req = execute_query("SELECT * FROM requests WHERE request_id = ?", (req_id,), fetch=True, fetch_all=False)
        if not req:
            messagebox.showerror("Not Found", "Invalid Request ID.")
            return

        msgs = execute_query("SELECT * FROM messages WHERE request_id = ? ORDER BY timestamp ASC", (req_id,), fetch=True)
        swift = execute_query("SELECT file_path FROM documents WHERE request_id = ? AND doc_type = 'SWIFT Acknowledgment'", (req_id,), fetch=True, fetch_all=False)

        self.status_disp.configure(state="normal")
        self.status_disp.delete("1.0", "end")
        
        self.status_disp.insert("end", f"[{req['status'].upper()}] - {req['vendor_name']} ({req['currency']} {req['amount']:,})\n")
        if req['detailed_service']:
            self.status_disp.insert("end", f"DETAILED NATURE: {req['detailed_service']}\n")
        self.status_disp.insert("end", "-"*60 + "\n\nCOMMUNICATION LOG:\n")
        
        if not msgs: self.status_disp.insert("end", "No remarks.\n")
        for m in msgs:
            self.status_disp.insert("end", f"[{m['timestamp']}] {m['sender_role']}: {m['message']}\n")
        
        self.status_disp.configure(state="disabled")

        if req['status'] == "Completed" and swift:
            self.btn_download_swift.configure(state="normal", command=lambda p=swift['file_path']: open_local_file(p))
        else:
            self.btn_download_swift.configure(state="disabled")

    # ==========================================
    # 4. TREASURY DASHBOARD
    # ==========================================
    def build_treasury_dashboard(self):
        treasury_tabs = ctk.CTkTabview(self.tab_treasury, fg_color="transparent", segmented_button_selected_color="#1E3A8A")
        treasury_tabs.pack(fill="both", expand=True)

        t_queue = treasury_tabs.add("Active Queue")
        t_tracker = treasury_tabs.add("Lifetime Tracker")

        # --- SUB TAB: ACTIVE QUEUE ---
        pane = ctk.CTkFrame(t_queue, fg_color="transparent")
        pane.pack(fill="both", expand=True, pady=5)

        left = ctk.CTkFrame(pane, width=420, fg_color=CORP_CARD, corner_radius=8)
        left.pack(side="left", fill="both", padx=(0, 10))

        hdr_f = ctk.CTkFrame(left, fg_color="transparent")
        hdr_f.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(hdr_f, text="Pending & Action Required", font=ctk.CTkFont(size=15, weight="bold"), text_color=CORP_TEXT).pack(side="left")
        ctk.CTkLabel(hdr_f, text="Live Sync 🟢", text_color=CORP_SUCCESS, font=ctk.CTkFont(size=12)).pack(side="right")

        self.queue_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.queue_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        right = ctk.CTkFrame(pane, fg_color=CORP_CARD, corner_radius=8)
        right.pack(side="right", fill="both", expand=True)

        self.lbl_selected = ctk.CTkLabel(right, text="Select Request to Process", font=ctk.CTkFont(size=18, weight="bold"), text_color=CORP_ACCENT)
        self.lbl_selected.pack(anchor="w", padx=20, pady=15)

        self.txt_audit = ctk.CTkTextbox(right, height=220, fg_color="#071022", border_width=1, border_color="#1E3A8A", text_color=CORP_TEXT, font=ctk.CTkFont(size=13, family="Consolas"))
        self.txt_audit.pack(fill="x", padx=20, pady=5)

        act = ctk.CTkFrame(right, fg_color="#071022", corner_radius=6, border_width=1, border_color="#1E3A8A")
        act.pack(fill="both", expand=True, padx=20, pady=15)

        grid_t = ctk.CTkFrame(act, fg_color="transparent")
        grid_t.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(grid_t, text="Purpose Code:", font=ctk.CTkFont(size=13, weight="bold"), text_color=CORP_TEXT).grid(row=0, column=0, sticky="w", padx=5)
        self.ent_purpose = ctk.CTkEntry(grid_t, width=150, text_color=CORP_TEXT)
        self.ent_purpose.grid(row=0, column=1, sticky="w", padx=5)

        ctk.CTkLabel(grid_t, text="Bank Ref #:", font=ctk.CTkFont(size=13, weight="bold"), text_color=CORP_TEXT).grid(row=0, column=2, sticky="w", padx=15)
        self.ent_swift = ctk.CTkEntry(grid_t, width=150, text_color=CORP_TEXT)
        self.ent_swift.grid(row=0, column=3, sticky="w", padx=5)

        ctk.CTkLabel(act, text="Query / Remarks for Requestor:", font=ctk.CTkFont(size=13, weight="bold"), text_color=CORP_TEXT).pack(anchor="w", padx=20)
        self.txt_treasury_msg = ctk.CTkEntry(act, placeholder_text="Enter discrepancy details if sending back...", height=35, text_color=CORP_TEXT)
        self.txt_treasury_msg.pack(fill="x", padx=20, pady=(5, 15))

        btn_row = ctk.CTkFrame(act, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_row, text="🔴 Send Back (Query)", font=ctk.CTkFont(weight="bold"), fg_color=CORP_ERROR, hover_color="#DC2626", text_color="#FFFFFF", command=self.send_back_req).pack(side="left")
        ctk.CTkButton(btn_row, text="🟢 Attach SWIFT & Complete", font=ctk.CTkFont(weight="bold"), fg_color=CORP_SUCCESS, hover_color="#059669", text_color="#FFFFFF", command=self.complete_req).pack(side="right")

        # --- SUB TAB: LIFETIME TRACKER ---
        tracker_f = ctk.CTkFrame(t_tracker, fg_color=CORP_CARD, corner_radius=8)
        tracker_f.pack(fill="both", expand=True, pady=10)

        t_head = ctk.CTkFrame(tracker_f, fg_color="transparent")
        t_head.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(t_head, text="Master Remittance Database", font=ctk.CTkFont(size=18, weight="bold"), text_color=CORP_ACCENT).pack(side="left")
        ctk.CTkButton(t_head, text="Refresh Database", width=120, font=ctk.CTkFont(weight="bold"), fg_color="#1E3A8A", hover_color="#2563EB", text_color=CORP_TEXT, command=self.refresh_lifetime_tracker).pack(side="right")

        columns = ("id", "date", "vendor", "curr", "amt", "status", "purpose", "swift")
        self.tree = ttk.Treeview(tracker_f, columns=columns, show="headings")
        
        self.tree.heading("id", text="Request ID")
        self.tree.heading("date", text="Date Created")
        self.tree.heading("vendor", text="Beneficiary")
        self.tree.heading("curr", text="CCY")
        self.tree.heading("amt", text="Amount")
        self.tree.heading("status", text="Status")
        self.tree.heading("purpose", text="Purpose")
        self.tree.heading("swift", text="Bank Ref")

        self.tree.column("id", width=170)
        self.tree.column("date", width=120)
        self.tree.column("vendor", width=190)
        self.tree.column("curr", width=50, anchor="center")
        self.tree.column("amt", width=110, anchor="e")
        self.tree.column("status", width=130, anchor="center")
        self.tree.column("purpose", width=90, anchor="center")
        
        self.tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.refresh_queue()
        self.refresh_lifetime_tracker()

    # SAFE POLLING MECHANISM (Thread-Free Main Thread Loop)
    def start_realtime_polling(self):
        self.check_queue_updates()

    def check_queue_updates(self):
        try:
            rows = execute_query("SELECT request_id, status FROM requests", fetch=True)
            current_state = frozenset((r["request_id"], r["status"]) for r in rows)
            if current_state != self.known_req_ids:
                self.refresh_queue()
                self.refresh_lifetime_tracker()
        except Exception:
            pass
        # Safely re-trigger update on the main GUI event loop every 3000ms
        self.after(3000, self.check_queue_updates)

    def refresh_queue(self):
        for w in self.queue_scroll.winfo_children(): w.destroy()

        rows = execute_query("SELECT * FROM requests WHERE status != 'Completed' ORDER BY created_at DESC", fetch=True)
        self.known_req_ids = frozenset((r["request_id"], r["status"]) for r in execute_query("SELECT request_id, status FROM requests", fetch=True))

        for r in rows:
            req_id, status = r["request_id"], r["status"]
            card_bg = "#1E3A8A" if req_id == self.current_selected_req_id else "#071022"
            card = ctk.CTkFrame(self.queue_scroll, fg_color=card_bg, corner_radius=6, border_width=1, border_color="#1E3A8A")
            card.pack(fill="x", pady=4, padx=2)

            badge = CORP_WARNING if status == "Pending Review" else CORP_ERROR
            
            ctk.CTkLabel(card, text=req_id, font=ctk.CTkFont(size=13, weight="bold"), text_color=CORP_TEXT).pack(anchor="w", padx=10, pady=(8, 0))
            ctk.CTkLabel(card, text=f"{r['vendor_name']} | {r['currency']} {r['amount']:,}", font=ctk.CTkFont(size=12), text_color=CORP_TEXT_MUTED).pack(anchor="w", padx=10)
            ctk.CTkLabel(card, text=status, text_color=badge, font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="e", padx=10, pady=(0, 8))

            for w in card.winfo_children() + [card]:
                w.bind("<Button-1>", lambda e, rid=req_id: self.inspect_request(rid))

    def refresh_lifetime_tracker(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        
        query = '''SELECT r.request_id, r.created_at, r.vendor_name, r.currency, r.amount, r.status, 
                          p.purpose_code, p.swift_ref 
                   FROM requests r LEFT JOIN processing_details p ON r.request_id = p.request_id
                   ORDER BY r.created_at DESC'''
        rows = execute_query(query, fetch=True)
        
        for r in rows:
            dt = r["created_at"].split(" ")[0]
            amt = f"{r['amount']:,.2f}"
            self.tree.insert("", "end", values=(r["request_id"], dt, r["vendor_name"], r["currency"], amt, r["status"], r["purpose_code"] or "-", r["swift_ref"] or "-"))

    def inspect_request(self, req_id):
        self.current_selected_req_id = req_id
        self.refresh_queue()
        self.lbl_selected.configure(text=f"Inspecting: {req_id}")

        req = execute_query("SELECT * FROM requests WHERE request_id = ?", (req_id,), fetch=True, fetch_all=False)
        docs = execute_query("SELECT doc_type, file_name, file_path FROM documents WHERE request_id = ?", (req_id,), fetch=True)
        msgs = execute_query("SELECT sender_role, message, timestamp FROM messages WHERE request_id = ? ORDER BY timestamp ASC", (req_id,), fetch=True)

        self.txt_audit.configure(state="normal")
        self.txt_audit.delete("1.0", "end")

        self.txt_audit.insert("end", f"BENEFICIARY: {req['vendor_name']} | {req['currency']} {req['amount']:,}\n")
        self.txt_audit.insert("end", f"CATEGORY: {req['remittance_type']}\n")
        if req['detailed_service']:
            self.txt_audit.insert("end", f"DETAILED SERVICE: {req['detailed_service']}\n")
        
        self.txt_audit.insert("end", "\n[ ATTACHED DOCUMENTS ]\n")
        for d in docs:
            self.txt_audit.insert("end", f" • {d['doc_type']}: {d['file_name']}\n")

        self.txt_audit.insert("end", "\n[ AUDIT TRAIL ]\n")
        for m in msgs:
            self.txt_audit.insert("end", f" > {m['sender_role']} ({m['timestamp']}): {m['message']}\n")

        self.txt_audit.configure(state="disabled")

    def send_back_req(self):
        if not self.current_selected_req_id: return messagebox.showwarning("Select", "Select a request.")
        msg = self.txt_treasury_msg.get().strip()
        if not msg: return messagebox.showerror("Error", "Provide details on what is missing.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        execute_query("UPDATE requests SET status = ? WHERE request_id = ?", ("Action Required", self.current_selected_req_id))
        execute_query("INSERT INTO messages (request_id, sender_role, message, timestamp) VALUES (?, ?, ?, ?)",
                      (self.current_selected_req_id, "Treasury", msg, now))
        
        messagebox.showinfo("Updated", "Request sent back to initiator.")
        self.txt_treasury_msg.delete(0, "end")
        self.current_selected_req_id = None
        self.refresh_queue()
        self.refresh_lifetime_tracker()

    def complete_req(self):
        if not self.current_selected_req_id: return messagebox.showwarning("Select", "Select a request.")
        purp = self.ent_purpose.get().strip()
        ref = self.ent_swift.get().strip()
        if not purp or not ref: return messagebox.showerror("Error", "Purpose Code and Bank Ref are required.")

        path = filedialog.askopenfilename(title="Upload SWIFT Copy", filetypes=[("PDF/Images", "*.pdf *.png *.jpg")])
        if not path: return

        folder = execute_query("SELECT folder_path FROM requests WHERE request_id = ?", (self.current_selected_req_id,), fetch=True, fetch_all=False)["folder_path"]
        fname = os.path.basename(path)
        dest = os.path.join(folder, fname)
        shutil.copy(path, dest)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        execute_query("INSERT INTO documents (request_id, doc_type, file_name, file_path, uploaded_by, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (self.current_selected_req_id, "SWIFT Acknowledgment", fname, dest, "Treasury", now))
        execute_query("INSERT OR REPLACE INTO processing_details (request_id, purpose_code, swift_ref, updated_at) VALUES (?, ?, ?, ?)",
                      (self.current_selected_req_id, purp, ref, now))
        execute_query("UPDATE requests SET status = ? WHERE request_id = ?", ("Completed", self.current_selected_req_id))

        msg = self.txt_treasury_msg.get().strip()
        if msg:
            execute_query("INSERT INTO messages (request_id, sender_role, message, timestamp) VALUES (?, ?, ?, ?)",
                          (self.current_selected_req_id, "Treasury", msg, now))

        messagebox.showinfo("Success", "Remittance complete and SWIFT attached.")
        self.txt_treasury_msg.delete(0, "end")
        self.ent_purpose.delete(0, "end")
        self.ent_swift.delete(0, "end")
        self.current_selected_req_id = None
        self.refresh_queue()
        self.refresh_lifetime_tracker()

if __name__ == "__main__":
    app = CorporateRemittanceApp()
    app.mainloop()
