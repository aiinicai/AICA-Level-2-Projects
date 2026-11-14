

# ===========================================================================
# SECTION 8 - BACKGROUND WORKERS
# ---------------------------------------------------------------------------
# Document building and mail sending run off the interface thread so the
# window never freezes and progress can be reported per party.
# ===========================================================================

class GenerateWorker(QObject):
    progress = pyqtSignal(int, int, str)          # done, total, party
    produced = pyqtSignal(dict)                   # one finished document
    finished = pyqtSignal(int, int)               # ok, failed

    def __init__(self, confs, folder, make_pdf=True, top_space_cm=0.0):
        super().__init__()
        self.confs = confs
        self.folder = folder
        self.make_pdf = make_pdf
        self.top_space_cm = top_space_cm
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        used, ok, failed = set(), 0, 0
        total = len(self.confs)
        for index, conf in enumerate(self.confs):
            if self._stop:
                break
            self.progress.emit(index, total, conf.get("party_name", ""))
            base = "%s - %s" % (sanitize_filename(conf.get("party_name")),
                                sanitize_filename(conf.get("category")))
            filename = unique_filename(base, ".docx", used)
            record = {"id": conf.get("id"), "filename": filename,
                      "conf": conf, "status": "ok", "path": "",
                      "size": 0, "error": ""}
            try:
                payload = docx_bytes(conf)
                record["size"] = len(payload)
                if self.folder:
                    path = os.path.join(self.folder, filename)
                    with open(path, "wb") as handle:
                        handle.write(payload)
                    record["path"] = path
                record["data"] = payload
                ok += 1
                # the PDF is what is e-mailed and what the client prints; a
                # failure here must not cost the Word letter already written
                record.update({"pdf_filename": "", "pdf_path": "",
                               "pdf_data": b"", "pdf_error": ""})
                if self.make_pdf:
                    try:
                        pdf = pdf_bytes(conf, self.top_space_cm)
                        record["pdf_filename"] = filename[:-5] + ".pdf"
                        record["pdf_data"] = pdf
                        if self.folder:
                            pdf_path = os.path.join(self.folder,
                                                    record["pdf_filename"])
                            with open(pdf_path, "wb") as handle:
                                handle.write(pdf)
                            record["pdf_path"] = pdf_path
                    except Exception as exc:
                        record["pdf_error"] = str(exc)[:300]
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = str(exc)[:300]
                record["data"] = b""
                failed += 1
            self.produced.emit(record)
        self.progress.emit(total, total, "")
        self.finished.emit(ok, failed)


class BridgeWorker(QObject):
    """Reads the JSON feed published by the Gmail Apps Script.  It is a single
    HTTPS GET, but it goes off the interface thread so a slow or unreachable
    deployment never freezes the window."""
    finished = pyqtSignal(list, str)              # replies, error

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            request = urllib.request.Request(
                self.url,
                headers={"User-Agent": "BalanceConfirmationGenerator/"
                                       + APP_VERSION,
                         "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            self.finished.emit(
                [], "the bridge refused the request (HTTP %s). Check that the "
                    "web app is deployed and that this computer is signed in "
                    "to the same Google account." % exc.code)
            return
        except Exception as exc:
            self.finished.emit([], "could not reach the bridge: %s" % exc)
            return
        try:
            payload = json.loads(raw)
        except Exception:
            # a sign-in page comes back as HTML, which is the usual cause
            self.finished.emit(
                [], "the bridge returned a page rather than data. Open the "
                    "feed address in your browser once and sign in, then try "
                    "again.")
            return
        replies = payload.get("replies") if isinstance(payload, dict) \
            else payload
        if not isinstance(replies, list):
            self.finished.emit([], "the bridge did not return a list of "
                                   "replies.")
            return
        self.finished.emit(replies, "")


class DocumentWorker(QObject):
    """Fetches each reply's own PDF or scan from the bridge and reads it on
    this computer - text layer and OCR.  OCR takes several seconds a page, so
    it runs here, off the interface thread, one reply at a time."""
    progress = pyqtSignal(str, list, str, int, int)   # id, entries, error, n, of
    finished = pyqtSignal(int, int)                   # read, failed

    def __init__(self, url, reply_ids):
        super().__init__()
        self.url = url
        self.reply_ids = list(reply_ids)
        self.stop = False

    def run(self):
        done = failed = 0
        total = len(self.reply_ids)
        for number, reply_id in enumerate(self.reply_ids, start=1):
            if self.stop:
                break
            entries, error = [], ""
            try:
                files, skipped, error = fetch_reply_files(self.url, reply_id)
                for name, kind, data in files:
                    if self.stop:
                        break
                    entries.append(attachment_entry(
                        name, read_document(data, name, kind)))
                if not error and not entries:
                    error = "no PDF or image attached" + (
                        " (%s)" % "; ".join(skipped) if skipped else "")
            except Exception as exc:              # one bad file never stops the rest
                error = str(exc) or exc.__class__.__name__
            if error and not entries:
                failed += 1
            else:
                done += 1
            self.progress.emit(reply_id, entries, error, number, total)
        self.finished.emit(done, failed)


class SendWorker(QObject):
    progress = pyqtSignal(int, int, str)
    result = pyqtSignal(str, str, str, str)   # id, status, detail, Message-ID
    finished = pyqtSignal(int, int)

    def __init__(self, jobs, account, options, delay_ms):
        super().__init__()
        self.jobs = jobs                          # [(conf, filename, bytes)]
        self.account = account
        self.options = options
        self.delay_ms = delay_ms
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        sent, failed = 0, 0
        total = len(self.jobs)
        server = None
        try:
            server = smtp_connect(self.account["host"], self.account["port"],
                                  self.account["security"],
                                  self.account["username"],
                                  self.account["password"])
        except Exception as exc:
            for conf, _, _ in self.jobs:
                self.result.emit(conf["id"], "failed",
                                 friendly_smtp_error(exc), "")
            self.finished.emit(0, total)
            return

        try:
            for index, (conf, filename, payload) in enumerate(self.jobs):
                if self._stop:
                    break
                self.progress.emit(index, total, conf.get("party_name", ""))
                try:
                    message = build_email_message(conf, filename, payload,
                                                  self.options)
                    server.send_message(message)
                    sent += 1
                    self.result.emit(conf["id"], "sent", "",
                                     str(message["Message-ID"] or ""))
                except smtplib.SMTPServerDisconnected:
                    try:                                   # one reconnect
                        server = smtp_connect(
                            self.account["host"], self.account["port"],
                            self.account["security"],
                            self.account["username"], self.account["password"])
                        message = build_email_message(conf, filename,
                                                      payload, self.options)
                        server.send_message(message)
                        sent += 1
                        self.result.emit(conf["id"], "sent", "",
                                         str(message["Message-ID"] or ""))
                    except Exception as exc:
                        failed += 1
                        self.result.emit(conf["id"], "failed",
                                         friendly_smtp_error(exc), "")
                except Exception as exc:
                    failed += 1
                    self.result.emit(conf["id"], "failed",
                                     friendly_smtp_error(exc), "")
                if self.delay_ms and index < total - 1:
                    QThread.msleep(int(self.delay_ms))
        finally:
            try:
                if server:
                    server.quit()
            except Exception:
                pass
        self.progress.emit(total, total, "")
        self.finished.emit(sent, failed)


# ===========================================================================
# SECTION 9 - MAIN WINDOW
# ===========================================================================

ATTACH_MODES = [
    ("PDF letter (as generated)", "pdf"),
    ("Signed PDF on the client's letterhead (your own files)", "signed"),
    ("Word letter (.docx)", "docx"),
]
ATTACH_HINTS = {
    "pdf": "Each party receives the PDF of its letter exactly as generated.",
    "signed": "Each party receives the PDF you link to it: the letter printed "
              "on the client's letterhead, signed and scanned. Link a whole "
              "folder at once, or use Choose PDF… on a row. A party with no "
              "signed PDF linked is held back, never sent an unsigned letter "
              "in its place.",
    "docx": "Each party receives the editable Word letter. A PDF is usually "
            "the better choice: it cannot be altered by accident.",
}

NAV_ITEMS = [
    ("WORKSPACE", None),
    ("01  Dashboard", "dashboard"),
    ("02  Client database", "clients"),
    ("ENGAGEMENT", None),
    ("03  Import data", "import"),
    ("04  Review & mapping", "review"),
    ("05  Letter preview", "preview"),
    ("06  Generate", "generate"),
    ("07  Email delivery", "email"),
    ("RECORDS", None),
    ("08  Confirmations received", "recon"),
    ("09  Saved runs", "runs"),
    ("10  Settings", "settings"),
]


class MainWindow(QMainWindow):

    # ------------------------------------------------------------- set-up
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s  %s" % (APP_NAME, APP_VERSION))

        self.db, load_error = load_db()
        self.active_client_id = self.db["settings"].get("last_client_id")
        self.active_fy_id = self.db["settings"].get("last_fy_id")

        # import state
        self.source_path = ""
        self.sheets = {}
        self.active_sheet = ""
        self.grid = []
        self.header_index = 0
        self.header_confidence = "low"
        self.columns = []
        self.data_rows = []
        self.mapping = None
        self.records = []
        self.row_filter = "all"
        self.exclude_flagged = True
        self.preview_index = 0

        # output state
        self.generated = []
        self.current_run_id = None
        self.gen_thread = None
        self.gen_worker = None
        self.send_thread = None
        self.send_worker = None
        self.bridge_thread = None
        self.bridge_worker = None
        self.reader_thread = None
        self.reader_worker = None
        self.mail_password = ""
        self.queue = {}

        self._building = True
        self._build_ui()
        self._building = False

        self._load_settings_into_widgets()
        saved_mode = self.db["settings"].get("theme")
        apply_theme(QApplication.instance(),
                    saved_mode if saved_mode in THEMES else "dark")
        self.refresh_theme_button()
        self.style_paper()
        self.refresh_all()
        self.go("dashboard")

        if load_error:
            self.toast("The saved database could not be read (%s). Starting "
                       "with an empty one." % load_error[:120], "warn")

        # the bridge has been collecting replies while this computer was off,
        # so read it once the window is up rather than blocking the start
        if self.db["settings"].get("bridge_sync_on_start", True) and \
                (self.db["settings"].get("bridge_feed_url") or "").strip():
            QTimer.singleShot(1200, lambda: self.sync_bridge(quiet=True))

    # ------------------------------------------------------------ chrome
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.pages = {}
        for key, builder in (("dashboard", self._page_dashboard),
                             ("clients", self._page_clients),
                             ("import", self._page_import),
                             ("review", self._page_review),
                             ("preview", self._page_preview),
                             ("generate", self._page_generate),
                             ("email", self._page_email),
                             ("recon", self._page_recon),
                             ("runs", self._page_runs),
                             ("settings", self._page_settings)):
            page = builder()
            # below this width the page scrolls sideways rather than squashing
            page.setMinimumWidth(880)
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(page)
            self.pages[key] = self.stack.count()
            self.stack.addWidget(area)
        right_layout.addWidget(self.stack, 1)

        self.status_strip = QLabel("")
        self.status_strip.setObjectName("SideFoot")
        self.status_strip.setContentsMargins(18, 5, 18, 7)
        right_layout.addWidget(self.status_strip)
        root.addWidget(right, 1)

        # size the window to the screen it opens on, never larger
        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            width = min(1380, max(1000, available.width() - 80))
            height = min(900, max(620, available.height() - 90))
            self.resize(width, height)
            self.move(available.x() + (available.width() - width) // 2,
                      available.y() + max(0, (available.height() - height) // 2))
        else:
            self.resize(1280, 820)
        self.setMinimumSize(980, 600)

    def _build_sidebar(self):
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(232)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand = QWidget()
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(16, 18, 16, 14)
        brand_layout.setSpacing(3)
        mark = QLabel("Balance Confirmation")
        mark.setObjectName("BrandMark")
        mark.setWordWrap(True)
        tag = QLabel("AUDIT CONFIRMATION TOOLKIT")
        tag.setObjectName("BrandTag")
        tag.setWordWrap(True)
        brand_layout.addWidget(mark)
        brand_layout.addWidget(tag)
        layout.addWidget(brand)
        layout.addWidget(h_line())

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        self.nav.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.nav_keys = {}
        for text, key in NAV_ITEMS:
            item = QListWidgetItem(text)
            if key is None:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                font = item.font()
                font.setPointSizeF(max(7.5, font.pointSizeF() - 2.0))
                item.setFont(font)
                item.setForeground(QColor(T["text_mute"]))
            else:
                self.nav_keys[self.nav.count()] = key
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._nav_changed)
        layout.addWidget(self.nav, 1)

        foot = QWidget()
        foot_layout = QVBoxLayout(foot)
        foot_layout.setContentsMargins(16, 10, 16, 14)
        foot_layout.setSpacing(3)
        privacy = QLabel("●  Everything stays on this computer")
        privacy.setObjectName("SideFoot")
        privacy.setWordWrap(True)
        self.db_path_label = QLabel("")
        self.db_path_label.setObjectName("SideFoot")
        self.db_path_label.setWordWrap(True)
        self.db_path_label.setToolTip(DB_PATH)
        self.db_path_label.setText("Records: %s" % os.path.basename(DB_PATH))
        foot_layout.addWidget(h_line())
        foot_layout.addWidget(privacy)
        foot_layout.addWidget(self.db_path_label)
        layout.addWidget(foot)
        return bar

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(22, 14, 22, 12)
        layout.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("PageTitle")
        title_row.addWidget(self.page_title)
        title_row.addStretch(1)
        self.theme_button = QPushButton()
        self.theme_button.setObjectName("ThemeToggle")
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.setToolTip("Switch between light and dark mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        title_row.addWidget(self.theme_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.page_sub = QLabel("Generate audit confirmations from Excel")
        self.page_sub.setObjectName("PageSub")
        layout.addLayout(title_row)
        layout.addWidget(self.page_sub)

        chips = FlowLayout(spacing=7)          # wraps instead of clipping
        self.chip_client = QLabel()
        self.chip_audit = QLabel()
        self.chip_date = QLabel()
        self.chip_team = QLabel()
        self.chip_mail = QLabel()
        self.chip_status = QLabel()
        for chip in (self.chip_client, self.chip_audit, self.chip_date,
                     self.chip_team, self.chip_mail, self.chip_status):
            chip.setProperty("chip", "neutral")
            chips.addWidget(chip)
        layout.addLayout(chips)
        return bar

    def _nav_changed(self, row):
        key = self.nav_keys.get(row)
        if key:
            self.go(key)

    # ---------------------------------------------------------- theming
    def toggle_theme(self):
        self.set_mode("light" if is_dark() else "dark")

    def set_mode(self, name):
        apply_theme(QApplication.instance(), name)
        self.db["settings"]["theme"] = name
        self.persist()
        self.refresh_theme_button()
        self.restyle()

    def refresh_theme_button(self):
        self.theme_button.setText("\u25d0  Light mode" if is_dark()
                                  else "\u25d1  Dark mode")

    def restyle(self):
        """Re-apply the handful of inline styles and redraw coloured cells."""
        self.style_paper()
        if hasattr(self, "drop_zone"):
            self.drop_zone.repaint_frame(False)
        for label in (self.header_note, self.map_warning, self.pv_warning,
                      self.mail_state):
            label.setStyleSheet(style_sheet())
        self.refresh_all()
        current = self.stack.currentIndex()
        if current == self.pages["preview"]:
            self.render_preview()
        elif current == self.pages["email"]:
            self.refresh_email()
        elif current == self.pages["settings"]:
            self.refresh_settings()
        elif current == self.pages["runs"]:
            self.refresh_runs()
        elif current == self.pages["generate"]:
            self.refresh_generate()
        elif current == self.pages["recon"]:
            self.refresh_recon()

    def go(self, key):
        self.stack.setCurrentIndex(self.pages[key])
        for row, name in self.nav_keys.items():
            if name == key and self.nav.currentRow() != row:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(row)
                self.nav.blockSignals(False)
        titles = {
            "dashboard": ("Dashboard", "Everything the generator needs before "
                                       "letters are produced"),
            "clients": ("Client database", "Clients, financial years and "
                                           "saved records on this computer"),
            "import": ("Import data", "Read the party-wise balance schedule"),
            "review": ("Review & mapping", "Confirm the detected columns and "
                                           "categories"),
            "preview": ("Letter preview", "Exactly what the Word file will "
                                          "contain"),
            "generate": ("Generate",
                         "Produce a Word letter and a PDF for each party"),
            "email": ("Email delivery", "Send each letter from your own "
                                        "mailbox"),
            "recon": ("Confirmations received", "Replies reconciled against "
                                                "what was sent"),
            "runs": ("Saved runs", "Every generation, by client and year"),
            "settings": ("Settings", "Engagement, audit team and firm details"),
        }
        title, subtitle = titles.get(key, (key.title(), ""))
        self.page_title.setText(title)
        self.page_sub.setText(subtitle)
        if key == "preview":
            self.render_preview()
        elif key == "generate":
            self.refresh_generate()
        elif key == "email":
            self.refresh_email()
        elif key == "recon":
            self.refresh_recon()
        elif key == "runs":
            self.refresh_runs()
        elif key == "settings":
            self.refresh_settings()
        elif key == "dashboard":
            self.refresh_dashboard()

    # ------------------------------------------------------------ helpers
    def toast(self, text, kind="info"):
        prefix = {"info": "", "ok": "✓  ", "warn": "⚠  ",
                  "err": "✕  "}.get(kind, "")
        colour = {"ok": T["ok"], "warn": T["warn"], "err": T["err"]}.get(
            kind, T["text_soft"])
        self.status_strip.setText(prefix + text)
        self.status_strip.setStyleSheet("color: %s;" % colour)
        QTimer.singleShot(9000, lambda: (
            self.status_strip.setText("")
            if self.status_strip.text() == prefix + text else None))

    def ask(self, title, text, confirm="Confirm", danger=True):
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Warning if danger
                    else QMessageBox.Icon.Question)
        yes = box.addButton(confirm, QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is yes

    def persist(self):
        ok, error = save_db(self.db)
        if not ok:
            self.toast("The records could not be saved: %s" % error, "err")
        return ok

    def active_client(self):
        for client in self.db["clients"]:
            if client["id"] == self.active_client_id:
                return client
        return None

    def active_fy(self):
        client = self.active_client()
        if not client:
            return None
        for year in client["financial_years"]:
            if year["id"] == self.active_fy_id:
                return year
        return None

    def auditors(self):
        return [a for a in self.db["settings"].get("auditors", [])
                if valid_email(a.get("email"))]

    def mail_settings(self):
        return self.db["settings"]["mail"]
