
    # =====================================================================
    # PAGE 03 - IMPORT DATA
    # =====================================================================
    def _page_import(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, _ = card("Open the balance schedule",
                              ".xlsx  ·  .xls  ·  .csv")
        body.addWidget(notice("green", "The file is read on this computer and "
                                       "is never modified or uploaded."))
        self.drop_zone = DropZone(self.load_file)
        body.addWidget(self.drop_zone)
        self.file_status = QLabel("")
        self.file_status.setObjectName("HintDark")
        self.file_status.setWordWrap(True)
        self.file_status.setTextFormat(Qt.TextFormat.RichText)
        body.addWidget(self.file_status)

        self.sheet_row = pane()
        sheet_layout = QHBoxLayout(self.sheet_row)
        sheet_layout.setContentsMargins(0, 4, 0, 0)
        sheet_layout.setSpacing(10)
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(field_label("Worksheet"))
        self.sheet_combo = QComboBox()
        self.sheet_combo.currentTextChanged.connect(self.on_sheet_changed)
        left.addWidget(self.sheet_combo)
        middle = QVBoxLayout()
        middle.setSpacing(4)
        middle.addWidget(field_label("Header row"))
        self.header_combo = QComboBox()
        self.header_combo.currentIndexChanged.connect(self.on_header_changed)
        middle.addWidget(self.header_combo)
        sheet_layout.addLayout(left, 1)
        sheet_layout.addLayout(middle, 2)
        redetect = button("Re-run detection")
        redetect.clicked.connect(lambda: self.load_sheet(self.active_sheet,
                                                         None))
        sheet_layout.addWidget(redetect, 0, Qt.AlignmentFlag.AlignBottom)
        self.sheet_row.setVisible(False)
        body.addWidget(self.sheet_row)
        self.header_note = QLabel("")
        self.header_note.setWordWrap(True)
        self.header_note.setVisible(False)
        body.addWidget(self.header_note)
        layout.addWidget(frame)

        frame_t, body_t, header_t = card(
            "Sample template",
            "A ready-to-fill Excel file the application reads without mapping")
        download = button("Download sample template (.xlsx)", "primary")
        download.setToolTip("Saves an Excel workbook with the right headings, "
                            "a category drop-down, four example rows and a "
                            "sheet of instructions")
        download.clicked.connect(self.download_sample_template)
        header_t.addWidget(download)
        template_note = QLabel(
            "Give this file to the client, or paste the client's listing into "
            "it. Its headings are <b>Name</b>, <b>Address line 1</b>, "
            "<b>Pincode</b>, <b>State</b>, <b>Country</b>, <b>Currency</b>, "
            "<b>Closing balance</b>, <b>Category</b>, <b>Email ID</b> and "
            "<b>Contact person</b>. Only <b>Name</b> is compulsory; the "
            "category is picked from a drop-down so every row lands on one of "
            "the four letter formats.")
        template_note.setObjectName("HintDark")
        template_note.setTextFormat(Qt.TextFormat.RichText)
        template_note.setWordWrap(True)
        body_t.addWidget(template_note)
        layout.addWidget(frame_t)

        frame2, body2, header2 = card("Worksheet preview", "", light=True)
        self.preview_note = QLabel("Nothing imported yet")
        self.preview_note.setObjectName("HintLight")
        header2.addWidget(self.preview_note)
        self.sheet_table = table([""])
        self.sheet_table.setMinimumHeight(300)
        body2.addWidget(self.sheet_table)
        layout.addWidget(frame2, 1)
        return page

    def download_sample_template(self, _checked=False, path=None):
        """Save the built-in party listing template wherever the user says."""
        if not path:
            start = os.path.join(
                self.db["settings"].get("output_folder") or
                os.path.expanduser("~"), SAMPLE_TEMPLATE_NAME)
            path, _ = QFileDialog.getSaveFileName(
                self, "Save the sample template", start,
                "Excel workbook (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            write_sample_template(path)
        except Exception as exc:
            self.toast("The template could not be saved: %s" % exc, "err")
            return
        self.toast("Sample template saved to %s" % path, "ok")
        return path

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open balance schedule",
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "Spreadsheets (*.xlsx *.xlsm *.xls *.csv);;All files (*)")
        if path:
            self.load_file(path)

    def load_file(self, path):
        if not os.path.exists(path):
            self.toast("That file could not be found.", "err")
            return
        if not re.search(r"\.(xlsx|xlsm|xls|csv)$", path, re.I):
            self.file_status.setText(
                "<span style='color:#eda28e'>Unsupported file type. Choose an "
                ".xlsx, .xls or .csv file.</span>")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            sheets = read_workbook(path)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.file_status.setText(
                "<span style='color:#eda28e'>%s</span>"
                % str(exc).replace("\n", "<br>"))
            self.toast("The file could not be read.", "err")
            return
        QApplication.restoreOverrideCursor()

        if not sheets:
            self.file_status.setText("<span style='color:#eda28e'>The "
                                     "workbook contains no worksheets.</span>")
            return
        self.source_path = path
        self.sheets = sheets
        with_data = [name for name, grid in sheets.items()
                     if any(any(clean(c) for c in (row or []))
                            for row in grid)]
        first = with_data[0] if with_data else list(sheets)[0]
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItems(list(sheets))
        self.sheet_combo.setCurrentText(first)
        self.sheet_combo.blockSignals(False)
        self.sheet_row.setVisible(True)
        self.header_note.setVisible(True)
        self.load_sheet(first, None)

    def on_sheet_changed(self, name):
        if name and not self._building:
            self.load_sheet(name, None)

    def on_header_changed(self, index):
        if index >= 0 and not self._building and self.active_sheet:
            self.load_sheet(self.active_sheet, index)

    def load_sheet(self, name, forced_header):
        if not name or name not in self.sheets:
            return
        self.active_sheet = name
        self.grid = trim_grid(self.sheets[name])
        if not self.grid:
            self.file_status.setText(
                "<span style='color:#eda28e'>Worksheet <b>%s</b> is empty. "
                "Choose another worksheet.</span>" % name)
            self.records, self.mapping, self.columns = [], None, []
            self.data_rows = []
            self.refresh_all()
            return

        detected = detect_header_row(self.grid)
        self.header_index = (detected["index"] if forced_header is None
                             else forced_header)
        self.header_confidence = (detected["confidence"]
                                  if forced_header is None else "high")

        self.header_combo.blockSignals(True)
        self.header_combo.clear()
        for r in range(min(len(self.grid), 25)):
            preview = " | ".join(
                [c for c in (clean(v) for v in (self.grid[r] or [])) if c][:6])
            if len(preview) > 70:
                preview = preview[:70] + "…"
            self.header_combo.addItem("Row %d  —  %s"
                                      % (r + 1, preview or "(blank)"))
        self.header_combo.setCurrentIndex(min(self.header_index,
                                              self.header_combo.count() - 1))
        self.header_combo.blockSignals(False)

        if self.header_confidence == "high":
            self.header_note.setText(
                "Header row detected automatically at <b>row %d</b>. Change it "
                "above if that is not right." % (self.header_index + 1))
            self.header_note.setObjectName("NoticeBlue")
        else:
            self.header_note.setText(
                "The header row could not be identified with confidence — "
                "<b>row %d</b> was assumed. Please check the selection above."
                % (self.header_index + 1))
            self.header_note.setObjectName("NoticeWarn")
        self.header_note.setStyleSheet("")
        self.header_note.setStyleSheet(style_sheet())

        built = build_columns(self.grid, self.header_index)
        self.columns = built["columns"]
        self.data_rows = built["data_rows"]
        self.mapping = detect_mapping(self.columns)
        self.build_records(reset=True)

        size_kb = os.path.getsize(self.source_path) / 1024.0
        self.file_status.setText(
            "<b>%s</b> · %.1f KB · worksheet <b>%s</b> · %d "
            "data rows · %d columns"
            % (os.path.basename(self.source_path), size_kb, name,
               len(self.data_rows), len(self.columns)))
        self.render_sheet_preview()
        self.refresh_all()
        self.toast("%d rows read from %s." % (len(self.data_rows), name), "ok")

    def render_sheet_preview(self):
        rows = self.data_rows[:15]
        self.sheet_table.clear()
        self.sheet_table.setColumnCount(len(self.columns) + 1)
        self.sheet_table.setHorizontalHeaderLabels(
            ["#"] + [c["label"] for c in self.columns])
        self.sheet_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.sheet_table.setItem(r, 0, cell(r + 1, align_right=True,
                                                color=T["text_mute"]))
            for c, column in enumerate(self.columns):
                index = column["index"]
                value = clean(row[index]) if index < len(row) else ""
                self.sheet_table.setItem(r, c + 1, cell(value))
        self.sheet_table.resizeColumnsToContents()
        self.preview_note.setText(
            "Showing %d of %d rows · %d columns"
            % (len(rows), len(self.data_rows), len(self.columns)))

    # =====================================================================
    # RECORDS
    # =====================================================================
    def build_records(self, reset=False):
        if not self.mapping:
            self.records = []
            return
        previous = {} if reset else {r["key"]: r for r in self.records}
        default_currency = (self.db["settings"].get("default_currency")
                            or "INR").upper()
        records = []
        for index, row in enumerate(self.data_rows):
            key = "r%d" % index

            def value_at(col):
                return clean(row[col]) if col < len(row) else ""

            mapping = self.mapping
            name = (value_at(mapping["partyName"]["cols"][0])
                    if mapping["partyName"]["cols"] else "")
            address = []
            for col in mapping["address"]["cols"]:
                text = value_at(col)
                if text:
                    address.extend([p.strip() for p in text.splitlines()
                                    if p.strip()])
            raw_amount = (row[mapping["amount"]["cols"][0]]
                          if mapping["amount"]["cols"]
                          and mapping["amount"]["cols"][0] < len(row) else None)
            amount, currency_from_text, _ = parse_amount(raw_amount)
            currency = (value_at(mapping["currency"]["cols"][0]).upper()
                        if mapping["currency"]["cols"] else "")
            if not currency:
                currency = currency_from_text or default_currency
            category_raw = (value_at(mapping["category"]["cols"][0])
                            if mapping["category"]["cols"] else "")
            email = (value_at(mapping["email"]["cols"][0])
                     if mapping["email"]["cols"] else "")
            contact = (value_at(mapping["contactPerson"]["cols"][0])
                       if mapping["contactPerson"]["cols"] else "")

            earlier = previous.get(key)
            record = {
                "id": earlier["id"] if earlier else new_id(),
                "key": key, "row_index": index,
                "party_name": name, "address_lines": address,
                "contact_person": contact,
                "email": earlier["email"] if earlier
                         and earlier.get("email_edited") else email,
                "email_edited": bool(earlier and earlier.get("email_edited")),
                "amount": amount,
                "currency": currency,
                "category_raw": category_raw,
                "category": earlier["category"] if earlier
                            and earlier.get("category_edited")
                            else normalize_category(category_raw),
                "category_edited": bool(earlier
                                        and earlier.get("category_edited")),
                "include": earlier["include"] if earlier else True,
            }
            self.compute_issues(record)
            records.append(record)
        self.records = records
        self.preview_index = 0

    @staticmethod
    def compute_issues(record):
        issues = []
        if not record["party_name"]:
            issues.append(("miss", "Party name missing"))
        if not record["category"]:
            issues.append(("rev", 'Category "%s" not recognised'
                           % record["category_raw"] if record["category_raw"]
                           else "Category missing"))
        if record["amount"] is None:
            issues.append(("rev", "Balance missing"))
        elif record["amount"] < 0:
            issues.append(("rev", "Negative balance — verify "
                                  "classification"))
        if not record["address_lines"]:
            issues.append(("info", "No address"))
        if record["email"] and not valid_email(record["email"]):
            issues.append(("rev", "Invalid email address"))
        record["issues"] = issues

    @staticmethod
    def is_blocking(record):
        return not record["party_name"] or not record["category"]

    def generable_records(self):
        return [r for r in self.records
                if r["include"] and not self.is_blocking(r)]

    def flagged_count(self):
        return len([r for r in self.records
                    if r["include"] and self.is_blocking(r)])

    def category_counts(self):
        counts = {c: 0 for c in CATEGORIES}
        counts["review"] = 0
        for record in self.records:
            if not record["include"]:
                continue
            if self.is_blocking(record):
                counts["review"] += 1
            else:
                counts[record["category"]] += 1
        return counts

    # =====================================================================
    # PAGE 04 - REVIEW & MAPPING
    # =====================================================================
    def _page_review(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card(
            "Detected fields", "Change any column the detector did not get "
                               "right", light=True)
        redetect = button("Re-run detection", small=True)
        redetect.clicked.connect(self.redetect_mapping)
        header.addWidget(redetect)
        self.map_grid = QGridLayout()
        self.map_grid.setSpacing(10)
        for column in range(3):
            self.map_grid.setColumnStretch(column, 1)
        body.addLayout(self.map_grid)
        self.map_warning = QLabel("")
        self.map_warning.setWordWrap(True)
        self.map_warning.setVisible(False)
        body.addWidget(self.map_warning)
        layout.addWidget(frame)

        frame2, body2, _ = card("Category mix",
                                "Flagged rows are not generated until a "
                                "category is chosen")
        self.cat_stats = QHBoxLayout()
        self.cat_stats.setSpacing(10)
        body2.addLayout(self.cat_stats)
        controls = QHBoxLayout()
        controls.setSpacing(12)
        currency_box = QVBoxLayout()
        currency_box.setSpacing(4)
        currency_box.addWidget(field_label("Default currency"))
        self.currency_edit = QLineEdit()
        self.currency_edit.setMaxLength(6)
        self.currency_edit.setFixedWidth(110)
        self.currency_edit.editingFinished.connect(self.on_currency_changed)
        currency_box.addWidget(self.currency_edit)
        filter_box = QVBoxLayout()
        filter_box.setSpacing(4)
        filter_box.addWidget(field_label("Show"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All rows", "Only rows needing attention",
                                    "Only included rows"])
        self.filter_combo.setFixedWidth(250)
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_box.addWidget(self.filter_combo)
        self.exclude_check = QCheckBox("Exclude flagged rows from generation")
        self.exclude_check.setChecked(True)
        self.exclude_check.stateChanged.connect(self.on_exclude_changed)
        controls.addLayout(currency_box)
        controls.addLayout(filter_box)
        controls.addWidget(self.exclude_check, 0, Qt.AlignmentFlag.AlignBottom)
        controls.addStretch(1)
        body2.addLayout(controls)
        layout.addWidget(frame2)

        frame3, body3, header3 = card("Party records", "", light=True)
        self.rec_note = QLabel("0 rows")
        self.rec_note.setObjectName("HintLight")
        header3.addWidget(self.rec_note)
        all_btn = button("Include all", small=True)
        all_btn.clicked.connect(lambda: self.set_all_included(True))
        none_btn = button("Include none", small=True)
        none_btn.clicked.connect(lambda: self.set_all_included(False))
        header3.addWidget(all_btn)
        header3.addWidget(none_btn)
        self.rec_table = table(["Use", "#", "Party", "Address", "Contact",
                                "Party email", "Amount", "Ccy", "Category",
                                "Status"], stretch_column=9)
        self.rec_table.setMinimumHeight(340)
        body3.addWidget(self.rec_table)
        layout.addWidget(frame3, 1)
        return page

    def redetect_mapping(self):
        if not self.columns:
            self.toast("Import a file first.", "warn")
            return
        self.mapping = detect_mapping(self.columns)
        self.build_records(reset=True)
        self.refresh_all()
        self.toast("Detection re-run.", "ok")

    def on_currency_changed(self):
        text = (self.currency_edit.text() or "INR").upper()[:6]
        self.currency_edit.setText(text)
        self.db["settings"]["default_currency"] = text
        self.persist()
        self.build_records()
        self.refresh_all()

    def on_filter_changed(self, index):
        self.row_filter = ["all", "attention", "included"][index]
        self.render_records()

    def on_exclude_changed(self, _state):
        self.exclude_flagged = self.exclude_check.isChecked()
        self.refresh_all()

    def set_all_included(self, included):
        for record in self.records:
            record["include"] = included
        self.refresh_all()

    def render_mapping(self):
        self._clear(self.map_grid)
        if not self.mapping:
            empty = QLabel("Import a file first.")
            empty.setObjectName("HintLight")
            self.map_grid.addWidget(empty, 0, 0)
            self.map_warning.setVisible(False)
            return
        self.map_combos = {}
        for position, field in enumerate(FIELD_ORDER):
            entry = self.mapping[field]
            definition = FIELD_DEFS[field]
            holder = pane()
            box = QVBoxLayout(holder)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(4)
            status = entry["status"]
            colour = {"detected": T["ok"], "review": T["warn"],
                      "missing": T["err"]}[status]
            label = QLabel(
                "<span style='color:%s; font-size:10px; font-weight:600; "
                "letter-spacing:1.1px'>%s%s</span>  <span style='color:%s; "
                "font-size:10px; font-weight:700'>%s</span>"
                % (T["text_soft"], definition["label"].upper(),
                   " *" if definition["required"] else "", colour,
                   status.upper()))
            label.setTextFormat(Qt.TextFormat.RichText)
            box.addWidget(label)

            if definition["multi"]:
                combo = QListWidget()
                combo.setSelectionMode(
                    QAbstractItemView.SelectionMode.MultiSelection)
                combo.setFixedHeight(86)
                combo.setStyleSheet(
                    "QListWidget { background:%s; border:1px solid %s;"
                    " border-radius:6px; color:%s; }"
                    " QListWidget::item { padding:3px 6px; }"
                    " QListWidget::item:selected { background:%s; color:%s; }"
                    % (T["raised"], T["line_soft"], T["text"],
                       T["accent"], T["accent_text"]))
                for column in self.columns:
                    item = QListWidgetItem(column["label"])
                    item.setData(Qt.ItemDataRole.UserRole, column["index"])
                    combo.addItem(item)
                    if column["index"] in entry["cols"]:
                        item.setSelected(True)
                combo.itemSelectionChanged.connect(
                    lambda f=field, w=combo: self.on_multi_map_changed(f, w))
                box.addWidget(combo)
                hint = QLabel("Ctrl-click to combine several columns — "
                              "each becomes a line of the address.")
            else:
                combo = QComboBox()
                combo.addItem("— none —", -1)
                for column in self.columns:
                    combo.addItem(column["label"], column["index"])
                if entry["cols"]:
                    position_in_list = combo.findData(entry["cols"][0])
                    if position_in_list >= 0:
                        combo.setCurrentIndex(position_in_list)
                combo.currentIndexChanged.connect(
                    lambda _i, f=field, w=combo: self.on_map_changed(f, w))
                box.addWidget(combo)
                sample = self.sample_for(entry["cols"][0]) if entry["cols"] \
                    else ""
                hint = QLabel(("Sample: " + sample) if sample
                              else "No column matched.")
            hint.setObjectName("HintLight")
            hint.setWordWrap(True)
            box.addWidget(hint)
            self.map_combos[field] = combo
            self.map_grid.addWidget(holder, position // 3, position % 3)

        if not self.mapping["partyName"]["cols"]:
            self.map_warning.setText(
                "No party-name column was identified. Choose one above "
                "— letters cannot be produced without it.")
            self.map_warning.setObjectName("NoticeRed")
            self.map_warning.setStyleSheet(style_sheet())
            self.map_warning.setVisible(True)
        else:
            self.map_warning.setVisible(False)

    def sample_for(self, column_index):
        for column in self.columns:
            if column["index"] == column_index:
                values = [v for v in column["values"] if v][:2]
                return " · ".join(values) or "(no values)"
        return ""

    def on_map_changed(self, field, combo):
        if self._building:
            return
        value = combo.currentData()
        self.mapping[field]["cols"] = [] if value in (None, -1) else [value]
        self.mapping[field]["status"] = ("detected"
                                         if self.mapping[field]["cols"]
                                         else "missing")
        self.build_records()
        self.refresh_all()

    def on_multi_map_changed(self, field, widget):
        if self._building:
            return
        self.mapping[field]["cols"] = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in widget.selectedItems()]
        self.mapping[field]["status"] = ("detected"
                                         if self.mapping[field]["cols"]
                                         else "missing")
        self.build_records()
        self.refresh_all()

    def render_cat_stats(self):
        self._clear(self.cat_stats)
        counts = self.category_counts()
        for key, value, meta, accent in (
                ("Trade Receivable", counts["Trade Receivable"],
                 "Owed to the client", T["accent"]),
                ("Trade Payable", counts["Trade Payable"],
                 "Owed by the client", T["info"]),
                ("Advance from Customers", counts["Advance from Customers"],
                 "Received by the client", T["accent"]),
                ("Advance to Vendors", counts["Advance to Vendors"],
                 "Paid by the client", T["info"]),
                ("Needs review", counts["review"],
                 "Not generated until fixed", T["warn"])):
            self.cat_stats.addWidget(stat_card(key, value, meta, accent))
        self.cat_stats.addStretch(1)

    def render_records(self):
        rows = self.records
        if self.row_filter == "attention":
            rows = [r for r in rows
                    if self.is_blocking(r)
                    or any(kind == "rev" for kind, _ in r["issues"])]
        elif self.row_filter == "included":
            rows = [r for r in rows if r["include"]]

        self.rec_table.setRowCount(0)
        for record in rows:
            index = self.rec_table.rowCount()
            self.rec_table.insertRow(index)

            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(8, 0, 0, 0)
            check = QCheckBox()
            check.setChecked(record["include"])
            check.stateChanged.connect(
                lambda _s, r=record, c=check: self.on_include_changed(r, c))
            box.addWidget(check)
            box.addStretch(1)
            self.rec_table.setCellWidget(index, 0, holder)

            self.rec_table.setItem(index, 1, cell(record["row_index"] + 1,
                                                  align_right=True,
                                                  color=T["text_mute"]))
            self.rec_table.setItem(index, 2, cell(
                record["party_name"] or "— no name —",
                bold=True,
                color=None if record["party_name"] else T["err"]))
            self.rec_table.setItem(index, 3,
                                   cell(", ".join(record["address_lines"])))
            self.rec_table.setItem(index, 4, cell(record["contact_person"]))

            email = QLineEdit(record["email"] or "")
            email.setPlaceholderText("party@example.com")
            email.editingFinished.connect(
                lambda r=record, w=email: self.on_email_changed(r, w))
            self.rec_table.setCellWidget(index, 5, email)

            label = amount_label(record["amount"], record["currency"])
            self.rec_table.setItem(index, 6, cell(
                fmt_amount(record["amount"], record["currency"])
                if label else "missing", align_right=True,
                color=None if label else T["warn"]))
            self.rec_table.setItem(index, 7, cell(record["currency"]))

            combo = QComboBox()
            combo.addItem("Needs review", "")
            for category in CATEGORIES:
                combo.addItem(category, category)
            if record["category"]:
                combo.setCurrentIndex(combo.findData(record["category"]))
            combo.currentIndexChanged.connect(
                lambda _i, r=record, w=combo: self.on_category_changed(r, w))
            self.rec_table.setCellWidget(index, 8, combo)

            status = "  ".join(text for _kind, text in record["issues"])
            colour = None
            if any(kind == "miss" for kind, _ in record["issues"]):
                colour = T["err"]
            elif any(kind == "rev" for kind, _ in record["issues"]):
                colour = T["warn"]
            self.rec_table.setItem(index, 9, cell(status, color=colour))

            if self.is_blocking(record):
                for column in range(self.rec_table.columnCount()):
                    item = self.rec_table.item(index, column)
                    if item:
                        item.setBackground(QColor(T["warn_bg"]))

        self.rec_table.resizeColumnsToContents()
        self.rec_table.setColumnWidth(5, 190)
        self.rec_table.setColumnWidth(8, 180)
        included = len([r for r in self.records if r["include"]])
        self.rec_note.setText("%d of %d rows shown · %d included"
                              % (len(rows), len(self.records), included))

    def on_include_changed(self, record, check):
        record["include"] = check.isChecked()
        self.refresh_chips()
        self.render_cat_stats()
        self.rec_note.setText(
            "%d of %d rows shown · %d included"
            % (self.rec_table.rowCount(), len(self.records),
               len([r for r in self.records if r["include"]])))

    def on_email_changed(self, record, widget):
        text = widget.text().strip()
        if text == record["email"]:
            return
        record["email"] = text
        record["email_edited"] = True
        self.compute_issues(record)
        self.render_records()
        self.refresh_chips()

    def on_category_changed(self, record, widget):
        if self._building:
            return
        record["category"] = widget.currentData() or None
        record["category_edited"] = True
        self.compute_issues(record)
        self.render_records()
        self.render_cat_stats()
        self.refresh_chips()
