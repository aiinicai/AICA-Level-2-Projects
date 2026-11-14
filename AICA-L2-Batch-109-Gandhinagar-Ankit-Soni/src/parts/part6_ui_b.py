
    # =====================================================================
    # PAGE 01 - DASHBOARD
    # =====================================================================
    def _page_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card(
            "Engagement readiness",
            "Everything the generator needs before letters are produced")
        import_btn = button("Import data")
        import_btn.clicked.connect(lambda: self.go("import"))
        gen_btn = button("Go to generate", "primary")
        gen_btn.clicked.connect(lambda: self.go("generate"))
        header.addWidget(import_btn)
        header.addWidget(gen_btn)
        self.dash_checks = QVBoxLayout()
        self.dash_checks.setSpacing(6)
        body.addLayout(self.dash_checks)
        layout.addWidget(frame)

        frame2, body2, _ = card("Portfolio summary",
                                "Current import, by balance category")
        self.dash_stats = QHBoxLayout()
        self.dash_stats.setSpacing(10)
        body2.addLayout(self.dash_stats)
        layout.addWidget(frame2)

        frame2b, body2b, header2b = card(
            "Confirmations received",
            "Replies reconciled against what was sent")
        open_recon = button("Open the reports")
        open_recon.clicked.connect(lambda: self.go("recon"))
        header2b.addWidget(open_recon)
        self.dash_recon = QHBoxLayout()
        self.dash_recon.setSpacing(10)
        body2b.addLayout(self.dash_recon)
        layout.addWidget(frame2b)

        row = QHBoxLayout()
        row.setSpacing(16)
        frame3, body3, _ = card("How this works")
        steps = QLabel(
            "<ol style='margin-left:-20px; line-height:170%'>"
            "<li>Create the client and its financial year in "
            "<b>Client database</b>.</li>"
            "<li>Choose the <b>type of audit</b> and whether the confirmation "
            "is for a year end or a period end, in <b>Settings</b>.</li>"
            "<li>Add the audit team members who should receive replies.</li>"
            "<li>Import the balance schedule in <b>Import data</b>.</li>"
            "<li>Confirm the detected columns in <b>Review &amp; mapping</b>."
            "</li>"
            "<li>Check one letter in <b>Letter preview</b>, then produce the "
            "files in <b>Generate</b>.</li>"
            "<li>Send them from your own mailbox in <b>Email delivery</b>.</li>"
            "</ol>")
        steps.setWordWrap(True)
        steps.setTextFormat(Qt.TextFormat.RichText)
        body3.addWidget(steps)
        row.addWidget(frame3, 1)

        frame4, body4, _ = card("Data handling")
        body4.addWidget(notice(
            "green", "Your spreadsheet is read on this computer. Nothing is "
                     "uploaded anywhere."))
        body4.addWidget(notice(
            "blue", "Letters, the local records and the preview are all built "
                    "here. Data leaves this computer only when you press "
                    "<b>Send</b> in Email delivery, and then it goes to your "
                    "own mail server."))
        body4.addWidget(notice(
            "warn", "Use an <b>app password</b> for Gmail, Outlook, Yahoo and "
                    "Zoho, never your main account password."))
        body4.addStretch(1)
        row.addWidget(frame4, 1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _clear(self, layout):
        """Empty a layout completely.  Widgets are detached at once, not just
        scheduled for deletion, so nothing stale is left on screen."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
                continue
            child = item.layout()
            if child is not None:
                self._clear(child)
                child.deleteLater()

    def refresh_dashboard(self):
        checks = self.validation()
        self._clear(self.dash_checks)
        last = len(checks["items"]) - 1
        for index, item in enumerate(checks["items"]):
            soft = (index == last and not item["ok"] and self.exclude_flagged)
            mark = "✓" if item["ok"] else ("!" if soft else "✕")
            colour = T["ok"] if item["ok"] else (T["warn"] if soft
                                                   else T["err"])
            row = QHBoxLayout()
            row.setSpacing(9)
            box = QLabel(mark)
            box.setFixedWidth(18)
            box.setStyleSheet("color:%s; font-weight:700;" % colour)
            text = QLabel("<b>%s</b><br><span style='color:%s; font-size:11px'>"
                          "%s%s</span>"
                          % (item["title"], T["text_mute"], item["detail"],
                             " — these rows will be skipped" if soft
                             else ""))
            text.setWordWrap(True)
            text.setTextFormat(Qt.TextFormat.RichText)
            row.addWidget(box, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self.dash_checks.addLayout(row)

        self._clear(self.dash_stats)
        counts = self.category_counts()
        for key, value, meta, accent in (
                ("Rows imported", len(self.records),
                 os.path.basename(self.source_path) if self.source_path
                 else "No file yet", T["accent"]),
                ("Trade Receivable", counts["Trade Receivable"],
                 "Owed to the client", T["accent"]),
                ("Trade Payable", counts["Trade Payable"],
                 "Owed by the client", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "Received by the client", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"],
                 "Paid by the client", T["info"]),
                ("Needs review", counts["review"],
                 "Category or name missing", T["warn"]),
                ("Generated", len([g for g in self.generated
                                   if g["status"] == "ok"]),
                 "This session", T["err"])):
            self.dash_stats.addWidget(stat_card(key, value, meta, accent))
        self.dash_stats.addStretch(1)

        # confirmations that have come back, across every run for this year
        rows, _exceptions = build_reconciliation(
            self.sent_documents(), self.stored_replies(),
            tolerance=float(self.db["settings"].get("variance_tolerance",
                                                    DEFAULT_TOLERANCE)),
            reminders=tuple(self.db["settings"].get("reminder_days",
                                                    DEFAULT_REMINDERS)))
        summary = summarise(rows)
        self._clear(self.dash_recon)
        for key, value, meta, accent in (
                ("Sent", summary["sent"], "Confirmations issued", T["accent"]),
                ("Received", summary["received"], "Replies matched", T["info"]),
                ("Matched", summary["agreed"], "No variance", T["ok"]),
                ("With variance", summary["variance"], "Difference found",
                 T["warn"]),
                ("Pending", summary["pending"], "No reply yet",
                 T["text_mute"]),
                ("Coverage", "%.1f%%" % summary["coverage_pct"],
                 "By value of balances", T["accent_hi"])):
            self.dash_recon.addWidget(stat_card(key, value, meta, accent))
        self.dash_recon.addStretch(1)

    # =====================================================================
    # PAGE 02 - CLIENT DATABASE
    # =====================================================================
    def _page_clients(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)

        frame, body, _ = card("Add client", "Stored on this computer only",
                              light=True)
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.cl_name = QLineEdit()
        self.cl_name.setPlaceholderText("Example Manufacturing Private Limited")
        self.cl_city = QLineEdit()
        self.cl_city.setPlaceholderText("Mumbai")
        self.cl_code = QLineEdit()
        self.cl_code.setPlaceholderText("EMPL-01")
        self.cl_notes = QLineEdit()
        self.cl_notes.setPlaceholderText("Statutory audit — FY 2026-27")
        for label, widget in (
                ("Client name (as it should appear in the letter)",
                 self.cl_name),
                ("City / place", self.cl_city),
                ("Client code", self.cl_code),
                ("Notes", self.cl_notes)):
            form.addRow(field_label(label, light=True), widget)
        body.addLayout(form)
        add_client = button("+  Add client", "primary")
        add_client.clicked.connect(self.add_client)
        self.cl_name.returnPressed.connect(self.add_client)
        body.addWidget(add_client, 0, Qt.AlignmentFlag.AlignLeft)
        top.addWidget(frame, 1)

        frame2, body2, _ = card("Financial years", "", light=True)
        self.fy_for = QLabel("No client selected")
        self.fy_for.setObjectName("HintLight")
        body2.addWidget(self.fy_for)
        fy_form = QHBoxLayout()
        fy_form.setSpacing(8)
        self.fy_year = QLineEdit()
        self.fy_year.setPlaceholderText("2026-27")
        self.fy_end = QDateEdit()
        self.fy_end.setCalendarPopup(True)
        self.fy_end.setDisplayFormat("dd MMMM yyyy")
        self.fy_end.setDate(QDate(date.today().year + 1, 3, 31))
        left = QVBoxLayout()
        left.addWidget(field_label("Financial year", light=True))
        left.addWidget(self.fy_year)
        right = QVBoxLayout()
        right.addWidget(field_label("Financial year end", light=True))
        right.addWidget(self.fy_end)
        fy_form.addLayout(left, 1)
        fy_form.addLayout(right, 1)
        body2.addLayout(fy_form)
        add_year = button("+  Add year", "primary")
        add_year.clicked.connect(self.add_year)
        body2.addWidget(add_year, 0, Qt.AlignmentFlag.AlignLeft)
        hint = QLabel("The audit type and the year-end or period-end date are "
                      "set per financial year, in Settings.")
        hint.setObjectName("HintLight")
        hint.setWordWrap(True)
        body2.addWidget(hint)
        body2.addWidget(h_line(light=True))
        self.fy_table = table(["Year", "Type of audit", "Confirmation as at",
                               "Runs", ""])
        self.fy_table.setMinimumHeight(150)
        body2.addWidget(self.fy_table)
        top.addWidget(frame2, 1)
        layout.addLayout(top)

        frame3, body3, header3 = card("Clients on this computer", "",
                                      light=True)
        self.cl_count = QLabel("")
        self.cl_count.setObjectName("HintLight")
        header3.addWidget(self.cl_count)
        self.cl_table = table(["Client", "Code", "Years", "Active year",
                               "Added", ""], stretch_column=0)
        body3.addWidget(self.cl_table)
        layout.addWidget(frame3)

        frame4, body4, _ = card("Records file", "Backup and restore")
        self.db_note = QLabel("")
        self.db_note.setObjectName("HintDark")
        self.db_note.setWordWrap(True)
        body4.addWidget(self.db_note)
        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        export_btn = button("Export records (JSON)", "brass")
        export_btn.clicked.connect(self.export_db)
        import_btn = button("Import records…")
        import_btn.clicked.connect(self.import_db)
        folder_btn = button("Open records folder")
        folder_btn.clicked.connect(self.open_db_folder)
        clear_btn = button("Clear all data", "danger")
        clear_btn.clicked.connect(self.clear_db)
        for widget in (export_btn, import_btn, folder_btn, clear_btn):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        body4.addLayout(buttons)
        layout.addWidget(frame4)
        layout.addStretch(1)
        return page

    def add_client(self):
        name = self.cl_name.text().strip()
        if not name:
            self.toast("Enter the client name as it should appear in the "
                       "letter.", "warn")
            self.cl_name.setFocus()
            return
        for client in self.db["clients"]:
            if client["name"].lower() == name.lower():
                self.toast("That client already exists — selecting it.",
                           "info")
                self.set_active_client(client["id"])
                return
        client = {"id": new_id(), "name": name,
                  "city": self.cl_city.text().strip(),
                  "code": self.cl_code.text().strip(),
                  "notes": self.cl_notes.text().strip(),
                  "created_at": datetime.now().isoformat(timespec="seconds"),
                  "financial_years": []}
        self.db["clients"].append(client)
        for widget in (self.cl_name, self.cl_city, self.cl_code, self.cl_notes):
            widget.clear()
        self.set_active_client(client["id"])
        self.toast("Client added: %s" % name, "ok")

    def set_active_client(self, client_id):
        self.active_client_id = client_id
        self.db["settings"]["last_client_id"] = client_id
        client = self.active_client()
        years = client["financial_years"] if client else []
        self.active_fy_id = years[-1]["id"] if years else None
        self.db["settings"]["last_fy_id"] = self.active_fy_id
        self.persist()
        self.refresh_all()

    def set_active_fy(self, fy_id):
        self.active_fy_id = fy_id
        self.db["settings"]["last_fy_id"] = fy_id
        self.persist()
        self.refresh_all()

    def add_year(self):
        client = self.active_client()
        if not client:
            self.toast("Select a client first.", "warn")
            return
        label = self.fy_year.text().strip()
        if not label:
            self.toast("Enter the financial year, for example 2026-27.", "warn")
            return
        if any(y["year"].lower() == label.lower()
               for y in client["financial_years"]):
            self.toast("That financial year already exists for this client.",
                       "warn")
            return
        year = {"id": new_id(), "year": label,
                "year_end": self.fy_end.date().toString("yyyy-MM-dd"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "audit_type": self.db["settings"].get("last_audit_type",
                                                      "Statutory Audit"),
                "audit_type_other": "", "basis": "year",
                "period_start": "", "period_end": ""}
        client["financial_years"].append(year)
        self.fy_year.clear()
        self.set_active_fy(year["id"])
        self.toast("Financial year %s added." % label, "ok")

    def refresh_clients(self):
        clients = self.db["clients"]
        self.cl_count.setText("%d client%s" % (len(clients),
                                               "" if len(clients) == 1 else "s"))
        self.cl_table.setRowCount(0)
        for client in clients:
            row = self.cl_table.rowCount()
            self.cl_table.insertRow(row)
            is_active = client["id"] == self.active_client_id
            name = client["name"] + ("   ● active" if is_active else "")
            self.cl_table.setItem(row, 0, cell(name, bold=is_active,
                                               color=T["ok"] if is_active
                                               else None))
            self.cl_table.setItem(row, 1, cell(client.get("code") or "—"))
            self.cl_table.setItem(row, 2, cell(len(client["financial_years"]),
                                               align_right=True))
            active_year = self.active_fy() if is_active else None
            self.cl_table.setItem(row, 3, cell(
                "%s (%s)" % (active_year["year"],
                             fmt_date_long(fy_as_at(active_year)))
                if active_year else "—"))
            created = (client.get("created_at") or "")[:10]
            self.cl_table.setItem(row, 4, cell(created))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            select = button("Selected" if is_active else "Select",
                            None if is_active else "primary", small=True)
            select.setEnabled(not is_active)
            select.clicked.connect(
                lambda _, cid=client["id"]: self.set_active_client(cid))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(
                lambda _, c=client: self.delete_client(c))
            box.addWidget(select)
            box.addWidget(delete)
            box.addStretch(1)
            self.cl_table.setCellWidget(row, 5, holder)
        self.cl_table.resizeColumnsToContents()
        fit_widget_columns(self.cl_table, [5])

        client = self.active_client()
        self.fy_for.setText("For %s" % client["name"] if client
                            else "No client selected")
        self.fy_table.setRowCount(0)
        for year in (client["financial_years"] if client else []):
            row = self.fy_table.rowCount()
            self.fy_table.insertRow(row)
            is_active = year["id"] == self.active_fy_id
            self.fy_table.setItem(row, 0, cell(
                year["year"] + ("   ●" if is_active else ""),
                bold=is_active, color=T["ok"] if is_active else None))
            audit = fy_audit_type(year)
            if audit == "Other":
                audit = year.get("audit_type_other") or "Other"
            self.fy_table.setItem(row, 1, cell(audit))
            as_at = fy_as_at(year)
            self.fy_table.setItem(row, 2, cell(
                "%s  (%s)" % (fmt_date_long(as_at), fy_basis_label(year))
                if as_at else "— not set —"))
            runs = len([r for r in self.db["runs"] if r.get("fy_id") == year["id"]])
            self.fy_table.setItem(row, 3, cell(runs, align_right=True))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            select = button("Selected" if is_active else "Select", small=True)
            select.setEnabled(not is_active)
            select.clicked.connect(
                lambda _, yid=year["id"]: self.set_active_fy(yid))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(lambda _, y=year: self.delete_year(y))
            box.addWidget(select)
            box.addWidget(delete)
            box.addStretch(1)
            self.fy_table.setCellWidget(row, 4, holder)
        self.fy_table.resizeColumnsToContents()
        fit_widget_columns(self.fy_table, [4])

        documents = sum(len(r.get("documents", [])) for r in self.db["runs"])
        years = sum(len(c["financial_years"]) for c in self.db["clients"])
        self.db_note.setText(
            "%d clients · %d financial years · %d saved runs · "
            "%d documents recorded<br><span style='font-size:11px'>Stored at "
            "%s</span>" % (len(clients), years, len(self.db["runs"]),
                           documents, DB_PATH))
        self.db_note.setTextFormat(Qt.TextFormat.RichText)

    def delete_client(self, client):
        if not self.ask("Delete client",
                        "Delete %s, its financial years and all saved runs "
                        "for it? This cannot be undone." % client["name"],
                        "Delete client"):
            return
        self.db["clients"] = [c for c in self.db["clients"]
                              if c["id"] != client["id"]]
        self.db["runs"] = [r for r in self.db["runs"]
                           if r.get("client_id") != client["id"]]
        if self.active_client_id == client["id"]:
            self.active_client_id = None
            self.active_fy_id = None
        self.persist()
        self.refresh_all()
        self.toast("Client deleted.", "ok")

    def delete_year(self, year):
        client = self.active_client()
        if not client:
            return
        runs = len([r for r in self.db["runs"] if r.get("fy_id") == year["id"]])
        if not self.ask("Delete financial year",
                        "Delete %s and its %d saved run(s)?"
                        % (year["year"], runs), "Delete year"):
            return
        client["financial_years"] = [y for y in client["financial_years"]
                                     if y["id"] != year["id"]]
        self.db["runs"] = [r for r in self.db["runs"]
                           if r.get("fy_id") != year["id"]]
        if self.active_fy_id == year["id"]:
            self.active_fy_id = (client["financial_years"][0]["id"]
                                 if client["financial_years"] else None)
        self.persist()
        self.refresh_all()
        self.toast("Financial year deleted.", "ok")

    def export_db(self):
        suggested = os.path.join(
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "balance-confirmation-records-%s.json" % date.today().isoformat())
        path, _ = QFileDialog.getSaveFileName(
            self, "Export records", suggested, "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self.db, handle, indent=2, ensure_ascii=False)
            self.toast("Records exported to %s" % path, "ok")
        except Exception as exc:
            self.toast("Export failed: %s" % exc, "err")

    def import_db(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import records", os.path.expanduser("~"),
            "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            self.toast("That file is not valid JSON: %s" % exc, "err")
            return
        if not isinstance(data, dict) or "clients" not in data:
            self.toast("That file is not a Balance Confirmation backup.", "err")
            return

        box = QMessageBox(self)
        box.setWindowTitle("Import records")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("The backup holds %d clients and %d runs."
                    % (len(data.get("clients") or []),
                       len(data.get("runs") or [])))
        box.setInformativeText(
            "Merge keeps what you already have and adds anything new. "
            "Replace discards the current records.")
        merge = box.addButton("Merge", QMessageBox.ButtonRole.AcceptRole)
        replace = box.addButton("Replace", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (merge, replace):
            return

        incoming = normalise_db(data)
        if clicked is replace:
            self.db = incoming
        else:
            existing = {c["name"].lower(): c for c in self.db["clients"]}
            for client in incoming["clients"]:
                match = existing.get(client["name"].lower())
                if not match:
                    self.db["clients"].append(client)
                    existing[client["name"].lower()] = client
                    continue
                known = {y["year"] for y in match["financial_years"]}
                for year in client["financial_years"]:
                    if year["year"] not in known:
                        match["financial_years"].append(year)
            seen = {r.get("id") for r in self.db["runs"]}
            for run in incoming["runs"]:
                if run.get("id") not in seen:
                    self.db["runs"].append(run)
        self.active_client_id = None
        self.active_fy_id = None
        self.persist()
        self._load_settings_into_widgets()
        self.refresh_all()
        self.toast("Records imported.", "ok")

    def open_db_folder(self):
        folder = app_data_dir()
        try:
            if os.name == "nt":
                os.startfile(folder)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            self.toast("Opened %s" % folder, "ok")
        except Exception:
            self.toast("The records are at %s" % folder, "info")

    def clear_db(self):
        if not self.ask("Clear all data",
                        "This removes every client, financial year and saved "
                        "run from this computer. Export a backup first if you "
                        "need one.", "Clear everything"):
            return
        self.db = blank_db()
        self.active_client_id = None
        self.active_fy_id = None
        self.persist()
        self._load_settings_into_widgets()
        self.refresh_all()
        self.toast("All local data cleared.", "ok")
