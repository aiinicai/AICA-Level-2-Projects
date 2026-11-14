
    # =====================================================================
    # CONFIRMATION RECORD  -  what both the preview and the DOCX consume
    # =====================================================================
    def to_confirmation(self, record):
        client = self.active_client()
        year = self.active_fy()
        as_at = fy_as_at(year)
        settings = self.db["settings"]
        return {
            "id": record["id"],
            "client_name": client["name"] if client else "",
            "financial_year": year["year"] if year else "",
            "audit_type": fy_audit_type(year),
            "audit_type_other": (year or {}).get("audit_type_other", ""),
            "basis": "period" if (year and year.get("basis") == "period")
                     else "year",
            "period_start": (year or {}).get("period_start", ""),
            "period_end": (year or {}).get("period_end", ""),
            "as_at": as_at,
            "year_end": as_at,
            "year_end_label": fmt_date_long(as_at) if as_at else "",
            "firm_name": settings.get("firm_name") or "the audit firm",
            "firm_designation": settings.get("firm_designation")
                                or "Statutory Auditor",
            "partner_name": settings.get("partner_name", ""),
            "letterhead_note": settings.get("letterhead_note", True),
            "reference": new_reference(),
            "print_reference": settings.get("print_reference", True),
            "letter_date": letter_date(self.db),
            "letter_date_label": fmt_date_long(letter_date(self.db)),
            "signatory_name": client.get("signatory_name", "") if client else "",
            "signatory_designation": (client.get("signatory_designation", "")
                                      if client else ""),
            "party_name": record["party_name"],
            "address_lines": list(record["address_lines"]),
            "contact_person": record["contact_person"],
            "party_email": record["email"],
            "amount": record["amount"],
            "currency": record["currency"],
            "category": record["category"],
            "auditors": [{"name": a["name"], "email": a["email"]}
                         for a in self.auditors()],
        }

    # =====================================================================
    # VALIDATION
    # =====================================================================
    def validation(self):
        client = self.active_client()
        year = self.active_fy()
        team = self.auditors()
        ready = self.generable_records()
        as_at = fy_as_at(year)
        audit_ok = fy_audit_ok(year)
        mapping_ok = bool(self.mapping and self.mapping["partyName"]["cols"])

        items = [
            {"ok": bool(self.source_path), "title": "Spreadsheet imported",
             "detail": ("%s · %d rows"
                        % (os.path.basename(self.source_path),
                           len(self.data_rows))) if self.source_path
                       else "Open an Excel or CSV file in Import data"},
            {"ok": mapping_ok, "title": "Party-name column identified",
             "detail": self.column_label(self.mapping["partyName"]["cols"][0])
                       if mapping_ok
                       else "Choose the column in Review & mapping"},
            {"ok": bool(client), "title": "Client selected",
             "detail": client["name"] if client
                       else "Add or select a client in Client database"},
            {"ok": audit_ok, "title": "Type of audit chosen",
             "detail": (
                 "Add a financial year, then choose the type in Settings"
                 if not year else
                 ('%s — letters open "Our %s, %s, are engaged in %s …"'
                  % (fy_audit_type(year), auditors_label(fy_audit_type(year)),
                     self.db["settings"].get("firm_name") or "[firm]",
                     engagement_phrase(fy_audit_type(year),
                                       year.get("audit_type_other"))))
                 if audit_ok else
                 "Describe the engagement in Settings, or pick a listed type")},
            {"ok": bool(as_at), "title": "%s set" % fy_basis_label(year),
             "detail": ("Add a financial year for the client" if not year
                        else ("%s · %s" % (year["year"],
                                                fy_span_text(year)))
                        if as_at else
                        ("Enter the period end date in Settings"
                         if year.get("basis") == "period"
                         else "Enter the financial year end in Settings"))},
            {"ok": bool(client and str(client.get("signatory_name") or "").strip()),
             "title": "Company signatory named",
             "detail": ("Select a client first" if not client
                        else ("%s, %s" % (client.get("signatory_name"),
                                          client.get("signatory_designation")
                                          or "Director / CFO"))
                        if str(client.get("signatory_name") or "").strip()
                        else "The letter is signed by the client \u2014 add "
                             "the officer in Settings")},
            {"ok": bool(team), "title": "At least one valid audit team email",
             "detail": ("%d address(es): %s"
                        % (len(team), ", ".join(a["email"] for a in team)))
                       if team else "Add a team member in Settings"},
            {"ok": bool(ready), "title": "At least one party ready",
             "detail": ("%d letters will be produced" % len(ready)) if ready
                       else "No row has both a party name and a category"},
            {"ok": self.flagged_count() == 0,
             "title": "Every included row has a valid category",
             "detail": ("%d row(s) need a category or a party name"
                        % self.flagged_count()) if self.flagged_count()
                       else "No rows flagged"},
        ]
        last = len(items) - 1
        hard = [item for index, item in enumerate(items)
                if not item["ok"] and not (index == last
                                           and self.exclude_flagged)]
        return {"items": items, "hard": hard, "ready": not hard,
                "generable": ready}

    def column_label(self, index):
        for column in self.columns:
            if column["index"] == index:
                return column["label"]
        return "Column " + col_letter(index)

    # =====================================================================
    # PAGE 05 - LETTER PREVIEW
    # =====================================================================
    def _page_preview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(14)

        frame, body, _ = card("Letter preview",
                              "Exactly what the Word file will contain")
        controls = QHBoxLayout()
        controls.setSpacing(9)
        previous = button("‹  Previous", small=True)
        previous.clicked.connect(lambda: self.step_preview(-1))
        self.pv_combo = QComboBox()
        self.pv_combo.setMinimumWidth(420)
        self.pv_combo.currentIndexChanged.connect(self.on_preview_selected)
        nxt = button("Next  ›", small=True)
        nxt.clicked.connect(lambda: self.step_preview(1))
        self.pv_position = QLabel("—")
        self.pv_position.setProperty("chip", "neutral")
        controls.addWidget(previous)
        controls.addWidget(self.pv_combo)
        controls.addWidget(nxt)
        controls.addWidget(self.pv_position)
        controls.addStretch(1)
        body.addLayout(controls)
        self.pv_warning = QLabel("")
        self.pv_warning.setWordWrap(True)
        self.pv_warning.setVisible(False)
        body.addWidget(self.pv_warning)
        layout.addWidget(frame)

        self.paper = QTextBrowser()
        self.paper.setObjectName("Paper")
        self.paper.setOpenExternalLinks(False)
        self.style_paper()
        self.paper.setMinimumHeight(560)
        layout.addWidget(self.paper, 1)
        return page

    def style_paper(self):
        """The letter is a printed page, so it stays paper-coloured in both
        modes; only its frame follows the theme."""
        self.paper.setStyleSheet(
            "QTextBrowser#Paper { background:%s; color:%s; border:1px solid %s;"
            " border-radius:6px; padding:18px 26px; }"
            % (T["paper"], T["paper_ink"], T["paper_line"]))

    def on_preview_selected(self, index):
        if index >= 0 and not self._building:
            self.preview_index = index
            self.render_preview(rebuild_list=False)

    def step_preview(self, delta):
        total = len(self.generable_records())
        if not total:
            return
        self.preview_index = (self.preview_index + delta) % total
        self.render_preview()

    def render_preview(self, rebuild_list=True):
        ready = self.generable_records()
        if self.preview_index >= len(ready):
            self.preview_index = 0
        if rebuild_list:
            self.pv_combo.blockSignals(True)
            self.pv_combo.clear()
            for record in ready:
                self.pv_combo.addItem("%s  —  %s" % (record["party_name"],
                                                          record["category"]))
            if ready:
                self.pv_combo.setCurrentIndex(self.preview_index)
            self.pv_combo.blockSignals(False)
        self.pv_position.setText("%d of %d" % (self.preview_index + 1,
                                               len(ready)) if ready
                                 else "0 of 0")

        client = self.active_client()
        year = self.active_fy()
        warnings = []
        if not client:
            warnings.append("No client selected — the client name will "
                            "be blank.")
        if not year:
            warnings.append("No financial year selected — the date will "
                            "be blank.")
        elif not fy_as_at(year):
            warnings.append(
                "No period end date set — the confirmation date will be "
                "blank." if year.get("basis") == "period"
                else "No financial year end set — the confirmation date "
                     "will be blank.")
        if not self.auditors():
            warnings.append("No audit team email added — the letter has "
                            "nowhere to direct replies.")
        if warnings:
            self.pv_warning.setText("<br>".join(warnings))
            self.pv_warning.setObjectName("NoticeWarn")
            self.pv_warning.setStyleSheet(style_sheet())
            self.pv_warning.setVisible(True)
        else:
            self.pv_warning.setVisible(False)

        if not ready:
            self.paper.setHtml(
                "<div style='color:%s; padding:40px; text-align:center; "
                "font-family:Calibri,sans-serif'>No party is ready to preview. "
                "Check Review &amp; mapping.</div>" % T["text_mute"])
            return
        try:
            model = build_letter_model(self.to_confirmation(
                ready[self.preview_index]))
        except Exception as exc:
            self.paper.setHtml("<div style='color:%s; padding:40px'>%s</div>"
                               % (T["err"], xml_escape(str(exc))))
            return
        self.paper.setHtml(self.letter_html(model))

    @staticmethod
    def letter_html(model):
        """The on-screen letter, built from the same model as the .docx.

        Qt's rich text ignores margins on <div>, so every block is a <p> with
        <br> between its lines - that is what gives the letter its spacing."""
        esc = xml_escape
        compact = model.get("compact")
        gap = 9 if compact else 14

        def block(lines, space_after=None, align=""):
            return ("<p style='margin:0 0 %dpx%s'>%s</p>"
                    % (gap if space_after is None else space_after,
                       ("; text-align:" + align) if align else "",
                       "<br>".join(esc(t) for t in lines)))

        html = ["<div style=\"font-family:Calibri,'Segoe UI',sans-serif; "
                "font-size:14px; line-height:1.45; color:%s\">" % T["paper_ink"]]
        if model["letterhead_note"]:
            html.append("<p style='margin:0 0 2px; text-align:center'>%s</p>"
                        % esc(model["letterhead_note"]))
        html.append("<p style='margin:0 0 %dpx; text-align:center; "
                    "font-weight:700'>%s</p>"
                    % (18 if compact else 24, esc(model["title"])))
        date_lines = [model["date_line"]]
        if model.get("reference_line"):
            date_lines.append(model["reference_line"])
        html.append(block(date_lines, space_after=6, align="right"))
        html.append(block([l["text"] for l in model["party_block"]]))
        html.append(block([model["salutation"]]))
        for index, text in enumerate(model["paras"]):
            html.append("<p style='margin:0 0 %dpx; text-align:justify'>%s</p>"
                        % (6 if index == len(model["paras"]) - 1 else gap,
                           esc(text)))
        html.append(block([l["text"] for l in model["auditor_block"]]))
        for text in model["closing_paras"]:
            html.append("<p style='margin:0 0 %dpx; text-align:justify'>%s</p>"
                        % (gap, esc(text)))
        signature = model["signature"]
        first = [l["text"] for l in signature if not l.get("gap")][:2]
        rest = [l["text"] for l in signature[len(first):]]
        html.append(block(first, space_after=22 if rest else gap))
        if rest:
            html.append(block(rest, space_after=gap))
        html.append("<p style='margin:20px 0 12px; text-align:justify'>%s</p>"
                    % esc(model["slip"]["sentence"]))
        rows = "".join(
            "<tr><td width='34%%' style='padding:3px 0'>%s</td>"
            "<td style='padding:3px 0'>:&nbsp;&nbsp;______________________</td>"
            "</tr>" % esc(label) for label in model["slip"]["rows"])
        html.append("<table width='70%%' cellspacing='0' cellpadding='0' "
                    "style='border-collapse:collapse'>%s</table></div>" % rows)
        return "".join(html)

    # =====================================================================
    # PAGE 06 - GENERATE
    # =====================================================================
    def _page_generate(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Pre-generation checks", "")
        self.gen_status = QLabel("")
        self.gen_status.setObjectName("HintDark")
        header.addWidget(self.gen_status)
        self.gen_checks = QVBoxLayout()
        self.gen_checks.setSpacing(6)
        body.addLayout(self.gen_checks)
        layout.addWidget(frame)

        frame2, body2, _ = card("Output folder",
                                "Where the Word and PDF letters are written")
        folder_row = QHBoxLayout()
        folder_row.setSpacing(9)
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText(
            "Choose the folder the confirmations should be saved in")
        self.folder_edit.setReadOnly(True)
        choose = button("Choose folder…", "brass")
        choose.clicked.connect(self.choose_output_folder)
        open_folder = button("Open folder")
        open_folder.clicked.connect(self.open_output_folder)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(choose)
        folder_row.addWidget(open_folder)
        body2.addLayout(folder_row)
        hint = QLabel("A sub-folder is created for the client and year, so "
                      "repeat runs never overwrite one another.")
        hint.setObjectName("HintDark")
        hint.setWordWrap(True)
        body2.addWidget(hint)
        layout.addWidget(frame2)

        frame3, body3, _ = card("Generation",
                                "One Word file and one PDF per party")
        self.gen_stats = QHBoxLayout()
        self.gen_stats.setSpacing(10)
        body3.addLayout(self.gen_stats)
        head_row = QHBoxLayout()
        head_row.setSpacing(8)
        head_label = QLabel("Space to leave at the top of the PDF for the "
                            "client's letterhead (cm)")
        head_label.setObjectName("HintDark")
        self.head_space = QDoubleSpinBox()
        self.head_space.setRange(0.0, 8.0)
        self.head_space.setSingleStep(0.5)
        self.head_space.setDecimals(1)
        self.head_space.setFixedWidth(90)
        self.head_space.setToolTip(
            "Leave 0 for plain paper. For pre-printed letterhead, measure the "
            "depth of the printed head and enter it here; the letter still "
            "fits on one page.")
        self.head_space.setValue(float(
            self.db["settings"].get("letterhead_space_cm", 0) or 0))
        self.head_space.valueChanged.connect(self.on_head_space)
        head_row.addWidget(head_label)
        head_row.addWidget(self.head_space)
        head_row.addStretch(1)
        body3.addLayout(head_row)
        buttons = QHBoxLayout()
        buttons.setSpacing(9)
        self.btn_generate = button("Generate letters (Word + PDF)", "primary")
        self.btn_generate.clicked.connect(self.run_generation)
        self.btn_open_output = button("Open output folder")
        self.btn_open_output.clicked.connect(self.open_output_folder)
        self.btn_open_output.setEnabled(False)
        self.btn_email = button("Go to email delivery", "blue")
        self.btn_email.clicked.connect(lambda: self.go("email"))
        self.btn_email.setEnabled(False)
        for widget in (self.btn_generate, self.btn_open_output, self.btn_email):
            buttons.addWidget(widget)
        buttons.addStretch(1)
        body3.addLayout(buttons)
        self.gen_bar = QProgressBar()
        self.gen_bar.setValue(0)
        self.gen_progress = QLabel("Idle")
        self.gen_progress.setObjectName("HintDark")
        body3.addWidget(self.gen_bar)
        body3.addWidget(self.gen_progress)
        layout.addWidget(frame3)

        frame4, body4, header4 = card("Generated files", "", light=True)
        self.gen_count = QLabel("None yet")
        self.gen_count.setObjectName("HintLight")
        header4.addWidget(self.gen_count)
        self.gen_table = table(["#", "File name", "Category", "Balance",
                                "Size", "Status"], stretch_column=1)
        body4.addWidget(self.gen_table)
        layout.addWidget(frame4, 1)
        return page

    def on_head_space(self, value):
        self.db["settings"]["letterhead_space_cm"] = float(value)
        self.persist()

    def choose_output_folder(self):
        start = (self.db["settings"].get("output_folder")
                 or os.path.expanduser("~"))
        folder = QFileDialog.getExistingDirectory(
            self, "Choose the folder for the confirmation letters", start)
        if folder:
            self.db["settings"]["output_folder"] = folder
            self.folder_edit.setText(folder)
            self.persist()
            self.refresh_generate()

    def run_output_folder(self):
        """Per-run sub-folder: <chosen folder>/<client> - <year>."""
        base = self.db["settings"].get("output_folder")
        if not base:
            return ""
        client = self.active_client()
        year = self.active_fy()
        name = sanitize_filename(
            "%s - Balance Confirmations - %s"
            % (client["name"] if client else "Client",
               year["year"] if year else ""))
        return os.path.join(base, name)

    def open_output_folder(self):
        folder = self.run_output_folder() or self.db["settings"].get(
            "output_folder")
        if not folder or not os.path.isdir(folder):
            self.toast("No output folder yet — choose one and generate.",
                       "warn")
            return
        try:
            if os.name == "nt":
                os.startfile(folder)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            self.toast("The files are in %s" % folder, "info")

    def refresh_generate(self):
        checks = self.validation()
        self._clear(self.gen_checks)
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
            self.gen_checks.addLayout(row)

        folder = self.db["settings"].get("output_folder") or ""
        self.folder_edit.setText(folder)
        self.gen_status.setText(
            "Ready to Generate" if checks["ready"]
            else "%d item%s need attention" % (len(checks["hard"]),
                                               "" if len(checks["hard"]) == 1
                                               else "s"))
        counts = self.category_counts()
        self._clear(self.gen_stats)
        for key, value, meta, accent in (
                ("Total parties", len(checks["generable"]),
                 "Letters to be produced", T["accent"]),
                ("Trade Receivable", counts["Trade Receivable"], "", T["accent"]),
                ("Trade Payable", counts["Trade Payable"], "", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"], "",
                 T["info"]),
                ("Needs review", counts["review"],
                 "Will be skipped" if self.exclude_flagged
                 else "Blocks generation", T["warn"])):
            self.gen_stats.addWidget(stat_card(key, value, meta, accent))
        self.gen_stats.addStretch(1)

        busy = self.gen_thread is not None
        self.btn_generate.setEnabled(checks["ready"] and bool(folder)
                                     and not busy)
        if not folder:
            self.btn_generate.setToolTip("Choose an output folder first.")
        else:
            self.btn_generate.setToolTip("")
        done = [g for g in self.generated if g["status"] == "ok"]
        self.btn_open_output.setEnabled(bool(done))
        self.btn_email.setEnabled(bool(done))
        self.render_generated_table()

    def render_generated_table(self):
        self.gen_table.setRowCount(0)
        for index, record in enumerate(self.generated):
            row = self.gen_table.rowCount()
            self.gen_table.insertRow(row)
            conf = record["conf"]
            self.gen_table.setItem(row, 0, cell(index + 1, align_right=True,
                                                color=T["text_mute"]))
            self.gen_table.setItem(row, 1, cell(record["filename"]))
            self.gen_table.setItem(row, 2, cell(conf["category"]))
            self.gen_table.setItem(row, 3, cell(
                amount_label(conf["amount"], conf["currency"]) or "—",
                align_right=True))
            self.gen_table.setItem(row, 4, cell(
                "%.1f KB" % (record["size"] / 1024.0) if record["size"]
                else "—", align_right=True))
            ok = record["status"] == "ok"
            if ok and record.get("pdf_data"):
                state, tone = "Word + PDF", T["ok"]
            elif ok and record.get("pdf_error"):
                state, tone = "Word only (PDF failed: %s)" \
                    % record["pdf_error"][:60], T["warn"]
            elif ok:
                state, tone = "Generated", T["ok"]
            else:
                state, tone = "Failed: " + record.get("error", ""), T["err"]
            self.gen_table.setItem(row, 5, cell(state, color=tone, bold=True))
        self.gen_table.resizeColumnsToContents()
        produced = len([g for g in self.generated if g["status"] == "ok"])
        self.gen_count.setText("%d of %d produced" % (produced,
                                                      len(self.generated))
                               if self.generated else "None yet")

    def run_generation(self):
        if self.gen_thread:
            return
        checks = self.validation()
        if not checks["ready"]:
            self.toast("Resolve the items listed above before generating.",
                       "warn")
            return
        folder = self.run_output_folder()
        if not folder:
            self.toast("Choose an output folder first.", "warn")
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            self.toast("The output folder could not be created: %s" % exc,
                       "err")
            return

        self.generated = []
        self.queue = {}
        self.render_generated_table()
        confs = [self.to_confirmation(r) for r in checks["generable"]]
        self.btn_generate.setEnabled(False)
        self.gen_bar.setValue(0)

        self.gen_thread = QThread(self)
        self.gen_worker = GenerateWorker(
            confs, folder, True,
            float(self.db["settings"].get("letterhead_space_cm", 0) or 0))
        self.gen_worker.moveToThread(self.gen_thread)
        self.gen_thread.started.connect(self.gen_worker.run)
        self.gen_worker.progress.connect(self.on_generate_progress)
        self.gen_worker.produced.connect(self.on_generated)
        self.gen_worker.finished.connect(self.on_generate_finished)
        self.gen_thread.start()

    def on_generate_progress(self, done, total, party):
        self.gen_bar.setMaximum(max(total, 1))
        self.gen_bar.setValue(done)
        self.gen_progress.setText(
            "Generating confirmations…  %d of %d completed  —  %s"
            % (done, total, party) if party
            else "Generating confirmations…  %d of %d completed"
                 % (done, total))

    def on_generated(self, record):
        self.generated.append(record)
        self.render_generated_table()

    def on_generate_finished(self, ok, failed):
        if self.gen_thread:
            self.gen_thread.quit()
            self.gen_thread.wait(4000)
        self.gen_thread = None
        self.gen_worker = None
        folder = self.run_output_folder()
        self.gen_progress.setText(
            "Done — %d generated%s.  Saved in %s"
            % (ok, (", %d failed" % failed) if failed else "", folder))
        self.save_run(folder)
        self.refresh_all()
        self.refresh_generate()
        self.toast("%d confirmation%s generated%s."
                   % (ok, "" if ok == 1 else "s",
                      (", %d failed" % failed) if failed else ""),
                   "warn" if failed else "ok")

    def save_run(self, folder):
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return
        run = {
            "id": new_id(), "client_id": client["id"],
            "client_name": client["name"], "fy_id": year["id"],
            "year": year["year"], "year_end": year.get("year_end", ""),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "audit_type": fy_audit_type(year),
            "audit_type_other": year.get("audit_type_other", ""),
            "basis": year.get("basis", "year"),
            "period_start": year.get("period_start", ""),
            "period_end": year.get("period_end", ""),
            "as_at": fy_as_at(year), "period_label": fy_span_text(year),
            "firm_name": self.db["settings"].get("firm_name", ""),
            "folder": folder,
            "auditors": [{"name": a["name"], "email": a["email"]}
                         for a in self.auditors()],
            "source": {"name": os.path.basename(self.source_path),
                       "sheet": self.active_sheet,
                       "rows": len(self.data_rows)} if self.source_path
                      else None,
            "documents": [{
                "filename": g["filename"],
                "pdf_filename": g.get("pdf_filename", ""),
                "party_name": g["conf"]["party_name"],
                "reference": g["conf"].get("reference", ""),
                "thread_id": "", "message_id": "",
                "category": g["conf"]["category"], "amount": g["conf"]["amount"],
                "currency": g["conf"]["currency"],
                "email": g["conf"].get("party_email", ""),
                "address": ", ".join(g["conf"]["address_lines"]),
                "status": g["status"], "email_status": "not sent",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
            } for g in self.generated],
        }
        self.db["runs"].insert(0, run)
        del self.db["runs"][300:]
        self.current_run_id = run["id"]
        self.persist()
