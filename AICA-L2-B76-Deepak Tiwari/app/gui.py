import os
import sys
import queue
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from .tesseract_utils import get_tesseract_status, find_tesseract_executable
from .processor import DocumentProcessor, DocumentItem, SUPPORTED_IMAGE_EXTS, SUPPORTED_PDF_EXTS
from .utils import pil_to_photoimage, format_file_size

logger = logging.getLogger(__name__)

# Style Constants
DARK_BG = "#181825"
CARD_BG = "#1E1E2E"
FRAME_BG = "#2B2B3D"
TEXT_COLOR = "#CDD6F4"
MUTED_TEXT = "#A6ADC8"
ACCENT_COLOR = "#6366F1"  # Indigo
ACCENT_HOVER = "#4F46E5"
SUCCESS_COLOR = "#10B981"
WARNING_COLOR = "#F59E0B"
ERROR_COLOR = "#EF4444"


class GuiLoggerHandler(logging.Handler):
    """Logging handler that streams log messages to GUI log queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(("LOG", msg))
        except Exception:
            pass


class DocDeskewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DocDeskew AI — Document Auto-Rotator & PDF Merger")
        self.root.geometry("1180x740")
        self.root.minsize(900, 600)

        # Set background color
        self.root.configure(bg=DARK_BG)

        # Data model
        self.items = []  # List of DocumentItem objects
        self.selected_index = None

        # Settings variables
        self.auto_rotate_var = tk.BooleanVar(value=True)
        self.deskew_var = tk.BooleanVar(value=True)
        self.osd_conf_var = tk.DoubleVar(value=0.5)
        self.compression_var = tk.StringVar(value="Balanced (Recommended)")

        # Threading & Communication
        self.gui_queue = queue.Queue()
        self.is_processing = False

        # Setup Logging
        self.setup_logging()

        # Build UI
        self.apply_theme()
        self.build_ui()

        # Check Tesseract status on launch
        self.update_tesseract_status()

        # Start Queue Poller
        self.root.after(100, self.poll_gui_queue)

    def setup_logging(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        handler = GuiLoggerHandler(self.gui_queue)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%H:%M:%S")
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    def apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")

        # General styling
        style.configure(".", background=DARK_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))

        # TFrame
        style.configure("TFrame", background=DARK_BG)
        style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        style.configure("Header.TFrame", background="#11111B")

        # TLabel
        style.configure("TLabel", background=DARK_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_COLOR)
        style.configure("Title.TLabel", background="#11111B", foreground="#FFFFFF", font=("Segoe UI", 14, "bold"))
        style.configure("SubTitle.TLabel", background="#11111B", foreground=MUTED_TEXT, font=("Segoe UI", 9))
        style.configure("Badge.TLabel", font=("Segoe UI", 9, "bold"), padding=(6, 3))

        # TButton
        style.configure("TButton", background=FRAME_BG, foreground=TEXT_COLOR, font=("Segoe UI", 9, "bold"), borderwidth=0, padding=6)
        style.map("TButton", background=[("active", ACCENT_COLOR), ("disabled", "#313244")], foreground=[("disabled", "#6C7086")])

        style.configure("Accent.TButton", background=ACCENT_COLOR, foreground="#FFFFFF", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])

        style.configure("Success.TButton", background=SUCCESS_COLOR, foreground="#FFFFFF", font=("Segoe UI", 10, "bold"), padding=8)
        style.map("Success.TButton", background=[("active", "#059669")])

        # TCheckbutton
        style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))

        # Treeview styling
        style.configure("Treeview", background=CARD_BG, foreground=TEXT_COLOR, fieldbackground=CARD_BG, rowheight=32, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=FRAME_BG, foreground=TEXT_COLOR, font=("Segoe UI", 9, "bold"), padding=5)
        style.map("Treeview", background=[("selected", ACCENT_COLOR)], foreground=[("selected", "#FFFFFF")])

        # Progressbar
        style.configure("Horizontal.TProgressbar", background=ACCENT_COLOR, troughcolor=CARD_BG, thickness=12)

    def build_ui(self):
        # 1. Header Bar
        header_frame = ttk.Frame(self.root, style="Header.TFrame", padding=(15, 10))
        header_frame.pack(side=tk.TOP, fill=tk.X)

        title_label = ttk.Label(header_frame, text="DocDeskew AI", style="Title.TLabel")
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(header_frame, text="  — Auto-Rotate, Deskew & PDF Merger", style="SubTitle.TLabel")
        subtitle_label.pack(side=tk.LEFT, padx=5)

        # Tesseract Status Pill
        self.tesseract_status_lbl = tk.Label(
            header_frame, text="Checking Tesseract...", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg="#CDD6F4", padx=10, pady=4, cursor="hand2"
        )
        self.tesseract_status_lbl.pack(side=tk.RIGHT, padx=5)
        self.tesseract_status_lbl.bind("<Button-1>", lambda e: self.configure_tesseract_path())

        # 2. Main Content PanedWindow
        main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=DARK_BG, bd=0, sashwidth=6)
        main_pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Container: Toolbar + Item List
        left_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=10)
        main_pane.add(left_frame, minsize=420)

        # Right Container: Settings + Live Preview Canvas
        right_frame = ttk.Frame(main_pane, style="Card.TFrame", padding=10)
        main_pane.add(right_frame, minsize=450)

        # Build Left Side UI
        self.build_left_panel(left_frame)

        # Build Right Side UI
        self.build_right_panel(right_frame)

        # 3. Footer Bar: Progress + Logs + Action Buttons
        footer_frame = ttk.Frame(self.root, style="Card.TFrame", padding=10)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))

        self.build_footer(footer_frame)

    def build_left_panel(self, parent):
        # Action Toolbar (Add Files, Folder, Clear)
        toolbar = ttk.Frame(parent, style="Card.TFrame")
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        btn_add_files = ttk.Button(toolbar, text="📂 Add Files...", command=self.add_files, style="Accent.TButton")
        btn_add_files.pack(side=tk.LEFT, padx=(0, 5))

        btn_add_folder = ttk.Button(toolbar, text="📁 Add Folder...", command=self.add_folder)
        btn_add_folder.pack(side=tk.LEFT, padx=5)

        btn_auto_arrange = ttk.Button(toolbar, text="🤖 AI Auto-Arrange", command=self.auto_arrange_pages, style="Accent.TButton")
        btn_auto_arrange.pack(side=tk.LEFT, padx=5)

        btn_clear = ttk.Button(toolbar, text="🗑️ Clear All", command=self.clear_all_items)
        btn_clear.pack(side=tk.RIGHT, padx=(5, 0))

        # Reordering Toolbar
        reorder_bar = ttk.Frame(parent, style="Card.TFrame")
        reorder_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        btn_up = ttk.Button(reorder_bar, text="⬆️ Move Up", command=self.move_item_up)
        btn_up.pack(side=tk.LEFT, padx=(0, 4))

        btn_down = ttk.Button(reorder_bar, text="⬇️ Move Down", command=self.move_item_down)
        btn_down.pack(side=tk.LEFT, padx=4)

        btn_rot_cw = ttk.Button(reorder_bar, text="↻ 90° CW", command=lambda: self.rotate_selected_item(90))
        btn_rot_cw.pack(side=tk.LEFT, padx=4)

        btn_rot_ccw = ttk.Button(reorder_bar, text="↺ 90° CCW", command=lambda: self.rotate_selected_item(-90))
        btn_rot_ccw.pack(side=tk.LEFT, padx=4)

        btn_remove = ttk.Button(reorder_bar, text="❌ Remove", command=self.remove_selected_item)
        btn_remove.pack(side=tk.RIGHT)

        # Document Page List Treeview
        columns = ("idx", "name", "rotation", "deskew", "status")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("idx", text="#")
        self.tree.heading("name", text="Document / Page Name")
        self.tree.heading("rotation", text="Rotation")
        self.tree.heading("deskew", text="Deskew")
        self.tree.heading("status", text="Status")

        self.tree.column("idx", width=40, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("rotation", width=80, anchor="center")
        self.tree.column("deskew", width=80, anchor="center")
        self.tree.column("status", width=80, anchor="center")

        tree_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Delete>", lambda e: self.remove_selected_item())

    def build_right_panel(self, parent):
        # Settings Header Card
        settings_card = ttk.Frame(parent, style="Card.TFrame")
        settings_card.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        lbl_settings = ttk.Label(settings_card, text="Processing Options", font=("Segoe UI", 11, "bold"), style="Card.TLabel")
        lbl_settings.pack(side=tk.TOP, anchor="w", pady=(0, 5))

        chk_auto_rotate = ttk.Checkbutton(
            settings_card, text="Auto-Rotate Upside/Sideways Pages (Tesseract OCR OSD)",
            variable=self.auto_rotate_var, style="TCheckbutton"
        )
        chk_auto_rotate.pack(side=tk.TOP, anchor="w", pady=2)

        chk_deskew = ttk.Checkbutton(
            settings_card, text="Auto-Deskew Text Skew Angle (OpenCV Line Alignment)",
            variable=self.deskew_var, style="TCheckbutton"
        )
        chk_deskew.pack(side=tk.TOP, anchor="w", pady=2)

        # Compression Level Dropdown
        comp_frame = ttk.Frame(settings_card, style="Card.TFrame")
        comp_frame.pack(side=tk.TOP, fill=tk.X, pady=(6, 2))

        lbl_comp = ttk.Label(comp_frame, text="📦 Output PDF Compression:", font=("Segoe UI", 9, "bold"), style="Card.TLabel")
        lbl_comp.pack(side=tk.LEFT, padx=(0, 8))

        comp_options = ["Balanced (Recommended)", "Smallest File (Max Compression)", "High Quality", "Original Size (No Compression)"]
        cb_compression = ttk.Combobox(comp_frame, textvariable=self.compression_var, values=comp_options, state="readonly", width=28)
        cb_compression.pack(side=tk.LEFT)

        # Separator
        sep = ttk.Separator(parent, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=8)

        # Preview Section Header & Toggle
        preview_hdr = ttk.Frame(parent, style="Card.TFrame")
        preview_hdr.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        lbl_preview = ttk.Label(preview_hdr, text="Document Page Inspector", font=("Segoe UI", 11, "bold"), style="Card.TLabel")
        lbl_preview.pack(side=tk.LEFT)

        self.preview_mode_var = tk.StringVar(value="Processed")
        btn_preview_orig = ttk.Radiobutton(preview_hdr, text="Original", value="Original", variable=self.preview_mode_var, command=self.update_preview_display)
        btn_preview_orig.pack(side=tk.RIGHT, padx=5)

        btn_preview_proc = ttk.Radiobutton(preview_hdr, text="Processed", value="Processed", variable=self.preview_mode_var, command=self.update_preview_display)
        btn_preview_proc.pack(side=tk.RIGHT)

        # Preview Canvas Container
        self.preview_canvas_frame = tk.Frame(parent, bg="#11111B", bd=1, relief="solid")
        self.preview_canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.preview_lbl = tk.Label(self.preview_canvas_frame, text="Select a document page to view live preview", bg="#11111B", fg=MUTED_TEXT, font=("Segoe UI", 11))
        self.preview_lbl.pack(expand=True)

        # Metadata Card Footer
        self.meta_lbl = ttk.Label(parent, text="No item selected", font=("Segoe UI", 9), style="Card.TLabel", foreground=MUTED_TEXT)
        self.meta_lbl.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

    def build_footer(self, parent):
        top_row = ttk.Frame(parent, style="Card.TFrame")
        top_row.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        self.status_lbl = ttk.Label(top_row, text="Ready. Add PDF or image files to begin.", font=("Segoe UI", 10), style="Card.TLabel")
        self.status_lbl.pack(side=tk.LEFT)

        self.btn_export = ttk.Button(top_row, text="⚡ Process & Export Merged PDF", command=self.start_export_process, style="Success.TButton")
        self.btn_export.pack(side=tk.RIGHT)

        # Progress bar
        self.progress_bar = ttk.Progressbar(parent, orient=tk.HORIZONTAL, mode="determinate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(side=tk.TOP, fill=tk.X)

        # Log Console Collapsible Area
        self.log_frame = ttk.Frame(parent, style="Card.TFrame")
        
        self.btn_toggle_logs = ttk.Button(parent, text="📋 Toggle Log Console", command=self.toggle_log_console)
        self.btn_toggle_logs.pack(side=tk.BOTTOM, anchor="w", pady=(5, 0))

        self.log_text = tk.Text(self.log_frame, height=6, bg="#11111B", fg="#A6E3A1", font=("Consolas", 9), bd=0)
        log_scroll = ttk.Scrollbar(self.log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def toggle_log_console(self):
        if self.log_frame.winfo_ismapped():
            self.log_frame.pack_forget()
        else:
            self.log_frame.pack(side=tk.TOP, fill=tk.X, pady=(5, 0))

    def update_tesseract_status(self):
        is_avail, path, version = get_tesseract_status()
        if is_avail:
            self.tesseract_status_lbl.config(
                text=f"✓ Tesseract OCR ({version}) Active",
                bg="#064E3B", fg="#A7F3D0"
            )
        else:
            self.tesseract_status_lbl.config(
                text="⚠️ Tesseract OCR Missing (Click to Locate)",
                bg="#7F1D1D", fg="#FECACA"
            )

    def configure_tesseract_path(self):
        filename = filedialog.askopenfilename(
            title="Locate Tesseract Executable (tesseract.exe)",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")]
        )
        if filename:
            path = find_tesseract_executable(custom_path=filename)
            self.update_tesseract_status()

    # --- File Management & Reordering ---

    def add_files(self):
        filetypes = [
            ("Supported Documents & Images", "*.pdf;*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.webp"),
            ("PDF Documents", "*.pdf"),
            ("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.webp"),
            ("All Files", "*.*")
        ]
        paths = filedialog.askopenfilenames(title="Select Documents & Images", filetypes=filetypes)
        if paths:
            self.load_files_in_background(paths)

    def add_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder Containing Documents/Images")
        if folder_path:
            paths = []
            for root, _, files in os.walk(folder_path):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in SUPPORTED_IMAGE_EXTS or ext in SUPPORTED_PDF_EXTS:
                        paths.append(os.path.join(root, f))
            if paths:
                self.load_files_in_background(paths)
            else:
                messagebox.showinfo("No Files Found", "No supported PDF or image files found in selected folder.")

    def load_files_in_background(self, paths):
        def worker():
            self.gui_queue.put(("STATUS", "Loading files..."))
            loaded_count = 0
            for path in paths:
                try:
                    items = DocumentProcessor.load_file(path)
                    for item in items:
                        self.gui_queue.put(("ADD_ITEM", item))
                        loaded_count += 1
                except Exception as e:
                    self.gui_queue.put(("LOG", f"Error loading '{path}': {e}"))

            self.gui_queue.put(("STATUS", f"Loaded {loaded_count} pages successfully."))

        threading.Thread(target=worker, daemon=True).start()

    def add_item_to_tree(self, item):
        self.items.append(item)
        idx = len(self.items)
        rot_str = f"{item.total_rotation_angle}°" if item.total_rotation_angle != 0 else "0°"
        deskew_str = f"{item.deskew_angle:+.1f}°" if item.deskew_angle != 0.0 else "0.0°"
        
        self.tree.insert("", tk.END, iid=item.id, values=(idx, item.display_name, rot_str, deskew_str, item.status))
        
        # Automatically trigger background preview processing for item
        self.process_single_item_in_bg(item)

    def process_single_item_in_bg(self, item):
        def worker():
            DocumentProcessor.process_item(
                item,
                do_auto_rotate=self.auto_rotate_var.get(),
                do_deskew=self.deskew_var.get(),
                min_osd_conf=self.osd_conf_var.get()
            )
            self.gui_queue.put(("UPDATE_ITEM_ROW", item))

        threading.Thread(target=worker, daemon=True).start()

    def update_tree_row(self, item):
        if self.tree.exists(item.id):
            idx = self.items.index(item) + 1
            rot_str = f"{item.total_rotation_angle}°" if item.total_rotation_angle != 0 else "0°"
            deskew_str = f"{item.deskew_angle:+.1f}°" if item.deskew_angle != 0.0 else "0.0°"
            self.tree.item(item.id, values=(idx, item.display_name, rot_str, deskew_str, item.status))
            
            # If item is currently selected, refresh preview
            if self.selected_index is not None and self.selected_index < len(self.items):
                if self.items[self.selected_index].id == item.id:
                    self.update_preview_display()

    def refresh_tree_indices(self):
        for idx, item in enumerate(self.items):
            if self.tree.exists(item.id):
                rot_str = f"{item.total_rotation_angle}°" if item.total_rotation_angle != 0 else "0°"
                deskew_str = f"{item.deskew_angle:+.1f}°" if item.deskew_angle != 0.0 else "0.0°"
                self.tree.item(item.id, values=(idx + 1, item.display_name, rot_str, deskew_str, item.status))

    def remove_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        for idx, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(idx)
                self.tree.delete(item_id)
                break
        self.refresh_tree_indices()
        self.clear_preview()

    def clear_all_items(self):
        self.items.clear()
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self.clear_preview()

    def move_item_up(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        idx = [i for i, item in enumerate(self.items) if item.id == item_id][0]
        if idx > 0:
            self.items[idx], self.items[idx - 1] = self.items[idx - 1], self.items[idx]
            self.tree.move(item_id, "", idx - 1)
            self.refresh_tree_indices()

    def move_item_down(self):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        idx = [i for i, item in enumerate(self.items) if item.id == item_id][0]
        if idx < len(self.items) - 1:
            self.items[idx], self.items[idx + 1] = self.items[idx + 1], self.items[idx]
            self.tree.move(item_id, "", idx + 1)
            self.refresh_tree_indices()

    def rotate_selected_item(self, degrees):
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        item = [it for it in self.items if it.id == item_id][0]
        item.manual_rotate_angle = (item.manual_rotate_angle + degrees) % 360
        item.status = "Ready"
        self.process_single_item_in_bg(item)

    # --- Live Preview & Selection ---

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.selected_index = None
            self.clear_preview()
            return
        item_id = selected[0]
        for idx, item in enumerate(self.items):
            if item.id == item_id:
                self.selected_index = idx
                self.update_preview_display()
                break

    def clear_preview(self):
        self.preview_lbl.config(image="", text="Select a document page to view live preview")
        self.preview_lbl.image = None
        self.meta_lbl.config(text="No item selected")

    def update_preview_display(self):
        if self.selected_index is None or self.selected_index >= len(self.items):
            self.clear_preview()
            return

        item = self.items[self.selected_index]
        mode = self.preview_mode_var.get()

        if mode == "Processed" and item.processed_image is not None:
            pil_img = item.processed_image
        else:
            pil_img = item.original_image

        if pil_img is None:
            self.clear_preview()
            return

        # Fit image dynamically into preview canvas
        canvas_w = max(self.preview_canvas_frame.winfo_width() - 20, 360)
        canvas_h = max(self.preview_canvas_frame.winfo_height() - 20, 380)

        preview_img = pil_img.copy()
        preview_img.thumbnail((canvas_w, canvas_h), Image.Resampling.LANCZOS)
        
        photo = pil_to_photoimage(preview_img)
        self.preview_lbl.config(image=photo, text="")
        self.preview_lbl.image = photo

        # Update metadata card
        w, h = pil_img.size
        meta_str = (
            f"📄 {item.display_name}  |  Resolution: {w}x{h} px  |  "
            f"Auto-Rotate OSD: {item.auto_rotate_angle}°  |  "
            f"Manual Rot: {item.manual_rotate_angle}°  |  "
            f"OpenCV Deskew: {item.deskew_angle:+.2f}°"
        )
        self.meta_lbl.config(text=meta_str)

    def auto_arrange_pages(self):
        if not self.items:
            messagebox.showinfo("No Items", "Please add document files before auto-arranging.")
            return

        def worker():
            self.gui_queue.put(("STATUS", "🤖 AI OCR scanning page numbers & sorting document sequence..."))
            sorted_items, count_reordered = DocumentProcessor.auto_arrange_items(self.items)
            self.items = sorted_items
            self.gui_queue.put(("REFRESH_ALL_TREE", count_reordered))

        threading.Thread(target=worker, daemon=True).start()

    # --- Processing & PDF Export ---

    def start_export_process(self):
        if not self.items:
            messagebox.showwarning("No Items", "Please add at least one document or image file before exporting.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save Merged PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF File", "*.pdf")]
        )
        if not output_path:
            return

        self.is_processing = True
        self.btn_export.config(state="disabled")
        self.progress_bar.config(value=0, maximum=len(self.items))

        do_auto_rot = self.auto_rotate_var.get()
        do_deskew = self.deskew_var.get()
        comp_preset = self.compression_var.get()

        def worker():
            try:
                def progress_cb(current, total, msg):
                    self.gui_queue.put(("PROGRESS", (current, total, msg)))

                res = DocumentProcessor.export_pdf(
                    self.items,
                    output_path,
                    do_auto_rotate=do_auto_rot,
                    do_deskew=do_deskew,
                    compression_preset=comp_preset,
                    progress_callback=progress_cb
                )
                self.gui_queue.put(("EXPORT_COMPLETE", res))
            except Exception as e:
                logger.error(f"PDF Export failed: {e}", exc_info=True)
                self.gui_queue.put(("EXPORT_ERROR", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # --- GUI Queue Poller ---

    def poll_gui_queue(self):
        try:
            while True:
                msg_type, payload = self.gui_queue.get_nowait()

                if msg_type == "ADD_ITEM":
                    self.add_item_to_tree(payload)

                elif msg_type == "UPDATE_ITEM_ROW":
                    self.update_tree_row(payload)

                elif msg_type == "REFRESH_ALL_TREE":
                    count_reordered = payload
                    for item_id in self.tree.get_children():
                        self.tree.delete(item_id)
                    for item in self.items:
                        rot_str = f"{item.total_rotation_angle}°" if item.total_rotation_angle != 0 else "0°"
                        deskew_str = f"{item.deskew_angle:+.1f}°" if item.deskew_angle != 0.0 else "0.0°"
                        idx = self.items.index(item) + 1
                        self.tree.insert("", tk.END, iid=item.id, values=(idx, item.display_name, rot_str, deskew_str, item.status))
                    self.status_lbl.config(text=f"✓ AI Auto-Arrange complete! Reordered {count_reordered} pages.")
                    if self.selected_index is not None and self.selected_index < len(self.items):
                        self.update_preview_display()

                elif msg_type == "STATUS":
                    self.status_lbl.config(text=payload)

                elif msg_type == "LOG":
                    self.log_text.insert(tk.END, payload + "\n")
                    self.log_text.see(tk.END)

                elif msg_type == "PROGRESS":
                    curr, total, msg = payload
                    self.progress_bar.config(value=curr, maximum=total)
                    self.status_lbl.config(text=msg)
                    # Refresh tree row status
                    if curr <= len(self.items):
                        self.update_tree_row(self.items[curr - 1])

                elif msg_type == "EXPORT_COMPLETE":
                    self.is_processing = False
                    self.btn_export.config(state="normal")
                    self.progress_bar.config(value=len(self.items))
                    
                    out_path = payload["output_path"]
                    final_sz_str = format_file_size(payload["final_size"])
                    page_cnt = payload["page_count"]
                    
                    msg_text = f"✓ Compressed PDF exported! Size: {final_sz_str} ({page_cnt} pages)"
                    self.status_lbl.config(text=msg_text)
                    messagebox.showinfo(
                        "PDF Export Successful",
                        f"Compressed PDF document successfully created!\n\n"
                        f"📁 Saved To: {out_path}\n"
                        f"📦 Final File Size: {final_sz_str}\n"
                        f"📄 Total Pages: {page_cnt}"
                    )

                elif msg_type == "EXPORT_ERROR":
                    self.is_processing = False
                    self.btn_export.config(state="normal")
                    self.status_lbl.config(text=f"❌ Export failed: {payload}")
                    messagebox.showerror("Export Failed", f"Failed to export merged PDF:\n\n{payload}")

        except queue.Empty:
            pass

        self.root.after(100, self.poll_gui_queue)


def launch_app():
    root = tk.Tk()
    app = DocDeskewApp(root)
    root.mainloop()
