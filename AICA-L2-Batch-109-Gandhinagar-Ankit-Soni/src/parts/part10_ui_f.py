
    # =====================================================================
    # PAGE 09 - SETTINGS
    # =====================================================================
    def _page_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        top = QHBoxLayout()
        top.setSpacing(16)

        frame, body, _ = card("Engagement", "", light=True)
        body.addWidget(field_label("Active client", light=True))
        self.set_client = QComboBox()
        self.set_client.currentIndexChanged.connect(self.on_set_client)
        body.addWidget(self.set_client)
        body.addWidget(field_label("Financial year", light=True))
        self.set_fy = QComboBox()
        self.set_fy.currentIndexChanged.connect(self.on_set_fy)
        body.addWidget(self.set_fy)
        body.addWidget(h_line(light=True))

        body.addWidget(field_label("Type of audit", light=True))
        self.set_audit_type = QComboBox()
        for name in AUDIT_TYPE_ORDER:
            self.set_audit_type.addItem(
                "Other (describe below)" if name == "Other" else name, name)
        self.set_audit_type.currentIndexChanged.connect(self.on_audit_type)
        body.addWidget(self.set_audit_type)

        self.audit_other_box = pane()
        other_layout = QVBoxLayout(self.audit_other_box)
        other_layout.setContentsMargins(0, 0, 0, 0)
        other_layout.setSpacing(4)
        other_layout.addWidget(field_label("Describe the engagement",
                                           light=True))
        self.set_audit_other = QLineEdit()
        self.set_audit_other.setPlaceholderText(
            "agreed-upon procedures engagement")
        self.set_audit_other.textChanged.connect(self.on_audit_other)
        other_layout.addWidget(self.set_audit_other)
        self.audit_other_hint = QLabel("")
        self.audit_other_hint.setObjectName("HintLight")
        self.audit_other_hint.setWordWrap(True)
        other_layout.addWidget(self.audit_other_hint)
        self.audit_other_box.setVisible(False)
        body.addWidget(self.audit_other_box)

        body.addWidget(field_label("Confirmation is for", light=True))
        self.set_basis = QComboBox()
        self.set_basis.addItem("A financial year end", "year")
        self.set_basis.addItem("A period end (interim / stub period)", "period")
        self.set_basis.currentIndexChanged.connect(self.on_basis)
        body.addWidget(self.set_basis)

        self.year_end_box = pane()
        year_layout = QVBoxLayout(self.year_end_box)
        year_layout.setContentsMargins(0, 0, 0, 0)
        year_layout.setSpacing(4)
        year_layout.addWidget(field_label("Financial year end", light=True))
        self.set_year_end = QDateEdit()
        self.set_year_end.setCalendarPopup(True)
        self.set_year_end.setDisplayFormat("dd MMMM yyyy")
        self.set_year_end.dateChanged.connect(self.on_year_end)
        year_layout.addWidget(self.set_year_end)
        body.addWidget(self.year_end_box)

        self.period_box = pane()
        period_layout = QHBoxLayout(self.period_box)
        period_layout.setContentsMargins(0, 0, 0, 0)
        period_layout.setSpacing(10)
        start_col = QVBoxLayout()
        start_col.setSpacing(4)
        start_col.addWidget(field_label("Period from (optional)", light=True))
        start_row = QHBoxLayout()
        start_row.setSpacing(6)
        self.set_period_start = QDateEdit()
        self.set_period_start.setCalendarPopup(True)
        self.set_period_start.setDisplayFormat("dd MMMM yyyy")
        self.set_period_start.dateChanged.connect(self.on_period_start)
        clear_start = button("Clear", small=True)
        clear_start.clicked.connect(self.clear_period_start)
        start_row.addWidget(self.set_period_start, 1)
        start_row.addWidget(clear_start)
        start_col.addLayout(start_row)
        end_col = QVBoxLayout()
        end_col.setSpacing(4)
        end_col.addWidget(field_label("Period ended on", light=True))
        self.set_period_end = QDateEdit()
        self.set_period_end.setCalendarPopup(True)
        self.set_period_end.setDisplayFormat("dd MMMM yyyy")
        self.set_period_end.dateChanged.connect(self.on_period_end)
        end_col.addWidget(self.set_period_end)
        period_layout.addLayout(start_col, 1)
        period_layout.addLayout(end_col, 1)
        self.period_box.setVisible(False)
        body.addWidget(self.period_box)

        date_row = QHBoxLayout()
        date_row.setSpacing(10)
        date_col = QVBoxLayout()
        date_col.setSpacing(4)
        date_col.addWidget(field_label("Date printed on the letter", light=True))
        self.set_letter_date = QDateEdit()
        self.set_letter_date.setCalendarPopup(True)
        self.set_letter_date.setDisplayFormat("dd MMMM yyyy")
        self.set_letter_date.dateChanged.connect(self.on_letter_date)
        date_col.addWidget(self.set_letter_date)
        self.set_letterhead = QCheckBox(
            "Print \u201c(on the letter head of the Company)\u201d")
        self.set_letterhead.stateChanged.connect(self.on_letterhead)
        date_row.addLayout(date_col, 1)
        date_row.addWidget(self.set_letterhead, 1,
                           Qt.AlignmentFlag.AlignBottom)
        body.addLayout(date_row)

        self.engagement_echo = QLabel("")
        self.engagement_echo.setObjectName("HintLight")
        self.engagement_echo.setWordWrap(True)
        body.addWidget(self.engagement_echo)
        body.addWidget(h_line(light=True))

        signer_row = QHBoxLayout()
        signer_row.setSpacing(10)
        signer_col = QVBoxLayout()
        signer_col.setSpacing(4)
        signer_col.addWidget(field_label("Letter signed by (company officer)",
                                         light=True))
        self.set_signatory = QLineEdit()
        self.set_signatory.setPlaceholderText("Mr. R. Mehta")
        self.set_signatory.textChanged.connect(self.on_signatory)
        signer_col.addWidget(self.set_signatory)
        desig_col = QVBoxLayout()
        desig_col.setSpacing(4)
        desig_col.addWidget(field_label("Officer's designation", light=True))
        self.set_sig_designation = QLineEdit()
        self.set_sig_designation.setPlaceholderText("Director / CFO")
        self.set_sig_designation.textChanged.connect(self.on_signatory_designation)
        desig_col.addWidget(self.set_sig_designation)
        signer_row.addLayout(signer_col, 1)
        signer_row.addLayout(desig_col, 1)
        body.addLayout(signer_row)
        signer_hint = QLabel("The confirmation is issued by the client on its "
                             "own letterhead, so it is signed by the company, "
                             "not by the audit firm. Saved against this client.")
        signer_hint.setObjectName("HintLight")
        signer_hint.setWordWrap(True)
        body.addWidget(signer_hint)
        body.addWidget(h_line(light=True))

        body.addWidget(field_label("Audit firm name", light=True))
        self.set_firm = QLineEdit()
        self.set_firm.setPlaceholderText("Ankit Soni and Associates")
        self.set_firm.textChanged.connect(self.on_firm_changed)
        body.addWidget(self.set_firm)
        firm_hint = QLabel("Printed as the auditors the signed reply must be "
                           "sent to.")
        firm_hint.setObjectName("HintLight")
        firm_hint.setWordWrap(True)
        body.addWidget(firm_hint)
        body.addWidget(field_label("Engagement partner (optional)", light=True))
        self.set_partner = QLineEdit()
        self.set_partner.setPlaceholderText("CA Ankit Soni")
        self.set_partner.textChanged.connect(self.on_partner_changed)
        body.addWidget(self.set_partner)
        body.addWidget(field_label("Designation line (email sign-off)",
                                   light=True))
        self.set_designation = QLineEdit()
        self.set_designation.setPlaceholderText("Statutory Auditor")
        self.set_designation.textChanged.connect(self.on_designation_changed)
        body.addWidget(self.set_designation)
        designation_hint = QLabel("Follows the type of audit unless you type "
                                  "your own.")
        designation_hint.setObjectName("HintLight")
        body.addWidget(designation_hint)
        top.addWidget(frame, 1)

        frame2, body2, _ = card("Audit team",
                                "Replies are directed to these addresses",
                                light=True)
        team_form = QHBoxLayout()
        team_form.setSpacing(8)
        name_col = QVBoxLayout()
        name_col.setSpacing(4)
        name_col.addWidget(field_label("Name", light=True))
        self.aud_name = QLineEdit()
        self.aud_name.setPlaceholderText("M. A")
        name_col.addWidget(self.aud_name)
        email_col = QVBoxLayout()
        email_col.setSpacing(4)
        email_col.addWidget(field_label("Email address", light=True))
        self.aud_email = QLineEdit()
        self.aud_email.setPlaceholderText("a@example.com")
        self.aud_email.returnPressed.connect(self.add_auditor)
        email_col.addWidget(self.aud_email)
        team_form.addLayout(name_col, 1)
        team_form.addLayout(email_col, 1)
        body2.addLayout(team_form)
        add_member = button("+  Add member", "primary")
        add_member.clicked.connect(self.add_auditor)
        body2.addWidget(add_member, 0, Qt.AlignmentFlag.AlignLeft)
        team_hint = QLabel("At least one valid address is required before "
                           "letters can be generated.")
        team_hint.setObjectName("HintLight")
        team_hint.setWordWrap(True)
        body2.addWidget(team_hint)
        body2.addWidget(h_line(light=True))
        self.aud_table = table(["Name", "Email", "Status", ""],
                               stretch_column=1)
        self.aud_table.setMinimumHeight(220)
        body2.addWidget(self.aud_table)
        body2.addStretch(1)
        top.addWidget(frame2, 1)
        layout.addLayout(top)

        frameb, bodyb, headerb = card(
            "Gmail bridge",
            "Collects replies on Google's servers while this computer is off")
        self.bridge_status = QLabel("")
        self.bridge_status.setObjectName("HintDark")
        headerb.addWidget(self.bridge_status)
        sync_now = button("Sync now", "primary")
        sync_now.clicked.connect(lambda: self.sync_bridge())
        headerb.addWidget(sync_now)

        bodyb.addWidget(field_label("Feed address (the Apps Script web-app "
                                    "URL)"))
        self.bridge_url = QLineEdit()
        self.bridge_url.setPlaceholderText(
            "https://script.google.com/macros/s/…/exec")
        self.bridge_url.textChanged.connect(self.on_bridge_url)
        bodyb.addWidget(self.bridge_url)
        self.bridge_start = QCheckBox("Sync automatically when the "
                                      "application starts")
        self.bridge_start.stateChanged.connect(self.on_bridge_start)
        bodyb.addWidget(self.bridge_start)
        bridge_hint = QLabel(
            "Deploy the supplied Apps Script (balance-confirmation-bridge.gs) "
            "in your own Google account as a web app set to <b>Execute as: "
            "Me</b> and <b>Who has access: Only myself</b>, then paste the "
            "deployment URL here.  The script reads unread mail whose subject "
            "carries \"balance confirmation\", records the confirmed figures "
            "in a Google Sheet, and labels what it has processed.  Nothing "
            "leaves your own Google account, and no mail is ever deleted.")
        bridge_hint.setObjectName("HintDark")
        bridge_hint.setTextFormat(Qt.TextFormat.RichText)
        bridge_hint.setWordWrap(True)
        bodyb.addWidget(bridge_hint)
        layout.addWidget(frameb)

        frame3, body3, _ = card("Column mapping in force",
                                "Read-only summary of the current import")
        self.map_summary = QLabel("No import loaded.")
        self.map_summary.setObjectName("HintDark")
        self.map_summary.setTextFormat(Qt.TextFormat.RichText)
        self.map_summary.setWordWrap(True)
        body3.addWidget(self.map_summary)
        layout.addWidget(frame3)
        layout.addStretch(1)
        return page

    # ------------------------------------------------- settings handlers
    def _load_settings_into_widgets(self):
        self._building = True
        settings = self.db["settings"]
        self.set_firm.setText(settings.get("firm_name", ""))
        self.set_designation.setText(settings.get("firm_designation", ""))
        self.currency_edit.setText(settings.get("default_currency", "INR"))
        self.folder_edit.setText(settings.get("output_folder", ""))
        self.bridge_url.setText(settings.get("bridge_feed_url", ""))
        self.bridge_start.setChecked(
            bool(settings.get("bridge_sync_on_start", True)))
        self._building = False
        self.refresh_bridge_status()

    def refresh_bridge_status(self):
        if not hasattr(self, "bridge_status"):
            return
        settings = self.db["settings"]
        url = (settings.get("bridge_feed_url") or "").strip()
        stamp = settings.get("bridge_last_sync") or ""
        count = len(self.db.get("replies", []))
        if not url:
            self.bridge_status.setText("not connected")
        elif stamp:
            self.bridge_status.setText(
                "last read %s · %d repl%s on record"
                % (stamp_text(stamp), count, "y" if count == 1 else "ies"))
        else:
            self.bridge_status.setText("connected, not yet read")
        self.refresh_bridge_note()

    def on_bridge_url(self, text):
        if self._building:
            return
        self.db["settings"]["bridge_feed_url"] = text.strip()
        self.persist()
        self.refresh_bridge_status()

    def on_bridge_start(self, state):
        if self._building:
            return
        self.db["settings"]["bridge_sync_on_start"] = \
            self.bridge_start.isChecked()
        self.persist()

    def on_set_client(self, index):
        if self._building:
            return
        client_id = self.set_client.currentData()
        self.set_active_client(client_id)

    def on_set_fy(self, index):
        if self._building:
            return
        fy_id = self.set_fy.currentData()
        if fy_id:
            self.set_active_fy(fy_id)

    def on_audit_type(self, index):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        previous = fy_audit_type(year)
        year["audit_type"] = self.set_audit_type.currentData()
        self.db["settings"]["last_audit_type"] = year["audit_type"]
        # the signature line follows the engagement unless it was hand-edited
        current = self.db["settings"].get("firm_designation") or ""
        if not current or current == audit_designation(previous):
            self.db["settings"]["firm_designation"] = audit_designation(
                year["audit_type"])
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def on_audit_other(self, text):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["audit_type_other"] = text
        self.audit_other_hint.setText(
            'Written into the letter as "As part of the %s of [client]", so '
            "keep it lower case and in noun form."
            % audit_phrase("Other", text))
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()

    def on_basis(self, index):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["basis"] = self.set_basis.currentData()
        if year["basis"] == "period" and not year.get("period_end"):
            year["period_end"] = year.get("year_end", "")
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def on_year_end(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        year["year_end"] = qdate.toString("yyyy-MM-dd")
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()
        self.refresh_clients()

    def on_period_start(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        value = qdate.toString("yyyy-MM-dd")
        if year.get("period_end") and value > year["period_end"]:
            self.toast("The period cannot start after it ends.", "warn")
            return
        year["period_start"] = value
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()

    def clear_period_start(self):
        year = self.active_fy()
        if not year:
            return
        year["period_start"] = ""
        self.persist()
        self.refresh_settings()
        self.update_engagement_echo()

    def on_period_end(self, qdate):
        if self._building:
            return
        year = self.active_fy()
        if not year:
            return
        value = qdate.toString("yyyy-MM-dd")
        if year.get("period_start") and year["period_start"] > value:
            self.toast("The period cannot end before it starts.", "warn")
            return
        year["period_end"] = value
        self.persist()
        self.update_engagement_echo()
        self.refresh_chips()
        self.refresh_clients()

    def on_letter_date(self, qdate):
        if self._building:
            return
        self.db["settings"]["letter_date"] = qdate.toString("yyyy-MM-dd")
        self.persist()
        self.update_engagement_echo()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_letterhead(self, _state):
        if self._building:
            return
        self.db["settings"]["letterhead_note"] = self.set_letterhead.isChecked()
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_signatory(self, text):
        if self._building:
            return
        client = self.active_client()
        if not client:
            return
        client["signatory_name"] = text
        self.persist()
        self.refresh_chips()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_signatory_designation(self, text):
        if self._building:
            return
        client = self.active_client()
        if not client:
            return
        client["signatory_designation"] = text
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_partner_changed(self, text):
        if self._building:
            return
        self.db["settings"]["partner_name"] = text
        self.persist()
        if self.stack.currentIndex() == self.pages["preview"]:
            self.render_preview()

    def on_firm_changed(self, text):
        if self._building:
            return
        self.db["settings"]["firm_name"] = text
        self.persist()
        self.refresh_chips()

    def on_designation_changed(self, text):
        if self._building:
            return
        self.db["settings"]["firm_designation"] = text
        self.persist()

    def update_engagement_echo(self):
        year = self.active_fy()
        client = self.active_client()
        if not year:
            self.engagement_echo.setText("")
            return
        as_at = fy_as_at(year)
        span = period_phrase(year.get("basis"), as_at,
                             year.get("period_start"))
        self.engagement_echo.setText(
            'Letters will open “Our %s, %s, are engaged in %s of our '
            'financial statements…” and confirm balances as on %s. '
            "The responding party's own date field is always left blank."
            % (auditors_label(fy_audit_type(year)),
               self.db["settings"].get("firm_name") or "[firm]",
               engagement_phrase(fy_audit_type(year),
                                 year.get("audit_type_other")),
               fmt_date_long(as_at) if as_at else "— not set —"))

    def add_auditor(self):
        email = self.aud_email.text().strip()
        name = self.aud_name.text().strip()
        if not valid_email(email):
            self.toast("Enter a valid email address for the team member.",
                       "warn")
            self.aud_email.setFocus()
            return
        if not name:
            name = email.split("@")[0]
        team = self.db["settings"].setdefault("auditors", [])
        if any(a["email"].lower() == email.lower() for a in team):
            self.toast("That address is already on the team list.", "warn")
            return
        team.append({"id": new_id(), "name": name, "email": email})
        self.aud_name.clear()
        self.aud_email.clear()
        self.persist()
        self.refresh_all()
        self.refresh_settings()
        self.toast("Team member added.", "ok")

    def remove_auditor(self, member):
        self.db["settings"]["auditors"] = [
            a for a in self.db["settings"]["auditors"] if a["id"] != member["id"]]
        self.persist()
        self.refresh_all()
        self.refresh_settings()

    def refresh_settings(self):
        self._building = True
        self.set_client.clear()
        self.set_client.addItem("— select a client —", None)
        for client in self.db["clients"]:
            self.set_client.addItem(client["name"], client["id"])
        index = self.set_client.findData(self.active_client_id)
        self.set_client.setCurrentIndex(max(index, 0))

        client = self.active_client()
        self.set_fy.clear()
        if client and client["financial_years"]:
            for year in client["financial_years"]:
                self.set_fy.addItem(year["year"], year["id"])
            index = self.set_fy.findData(self.active_fy_id)
            self.set_fy.setCurrentIndex(max(index, 0))
        else:
            self.set_fy.addItem("— no financial year —", None)

        year = self.active_fy()
        enabled = year is not None
        index = self.set_audit_type.findData(fy_audit_type(year))
        self.set_audit_type.setCurrentIndex(max(index, 0))
        self.set_audit_type.setEnabled(enabled)
        is_other = fy_audit_type(year) == "Other"
        self.audit_other_box.setVisible(is_other)
        self.set_audit_other.setText((year or {}).get("audit_type_other", ""))
        self.audit_other_hint.setText(
            'Written into the letter as "As part of the %s of [client]", so '
            "keep it lower case and in noun form."
            % audit_phrase("Other", (year or {}).get("audit_type_other", "")))

        basis = "period" if (year and year.get("basis") == "period") else "year"
        self.set_basis.setCurrentIndex(self.set_basis.findData(basis))
        self.set_basis.setEnabled(enabled)
        self.year_end_box.setVisible(basis == "year")
        self.period_box.setVisible(basis == "period")

        today = QDate.currentDate()
        year_end = to_date((year or {}).get("year_end"))
        self.set_year_end.setDate(QDate(year_end.year, year_end.month,
                                        year_end.day) if year_end else today)
        self.set_year_end.setEnabled(enabled)
        start = to_date((year or {}).get("period_start"))
        self.set_period_start.setSpecialValueText("")
        self.set_period_start.setDate(QDate(start.year, start.month, start.day)
                                      if start else today)
        end = to_date((year or {}).get("period_end"))
        self.set_period_end.setDate(QDate(end.year, end.month, end.day)
                                    if end else today)
        self.set_period_start.setEnabled(enabled)
        self.set_period_end.setEnabled(enabled)
        self.update_engagement_echo()

        stamp = to_date(letter_date(self.db)) or date.today()
        self.set_letter_date.setDate(QDate(stamp.year, stamp.month, stamp.day))
        self.set_letterhead.setChecked(
            self.db["settings"].get("letterhead_note", True))
        self.set_signatory.setText(
            client.get("signatory_name", "") if client else "")
        self.set_sig_designation.setText(
            client.get("signatory_designation", "") if client else "")
        self.set_signatory.setEnabled(bool(client))
        self.set_sig_designation.setEnabled(bool(client))
        self.set_firm.setText(self.db["settings"].get("firm_name", ""))
        self.set_partner.setText(self.db["settings"].get("partner_name", ""))
        self.set_designation.setText(
            self.db["settings"].get("firm_designation", ""))
        self._building = False

        team = self.db["settings"].get("auditors", [])
        self.aud_table.setRowCount(0)
        for member in team:
            row = self.aud_table.rowCount()
            self.aud_table.insertRow(row)
            ok = valid_email(member["email"])
            self.aud_table.setItem(row, 0, cell(member["name"], bold=True))
            self.aud_table.setItem(row, 1, cell(member["email"]))
            self.aud_table.setItem(row, 2, cell("VALID" if ok else "INVALID",
                                                color=T["ok"] if ok
                                                else T["err"], bold=True))
            remove = button("Remove", "danger", small=True)
            remove.clicked.connect(lambda _, m=member: self.remove_auditor(m))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.addWidget(remove)
            box.addStretch(1)
            self.aud_table.setCellWidget(row, 3, holder)
        self.aud_table.resizeColumnsToContents()
        fit_widget_columns(self.aud_table, [3])
        self.render_map_summary()

    def render_map_summary(self):
        if not self.mapping:
            self.map_summary.setText("No import loaded.")
            return
        rows = []
        for field in FIELD_ORDER:
            entry = self.mapping[field]
            labels = ", ".join(self.column_label(c) for c in entry["cols"]) \
                or "—"
            colour = {"detected": T["ok"], "review": T["warn"],
                      "missing": T["err"]}[entry["status"]]
            rows.append(
                "<tr><td style='padding:3px 16px 3px 0; color:%s'>%s</td>"
                "<td style='padding:3px 16px 3px 0'>%s</td>"
                "<td style='padding:3px 0; color:%s'>%s</td></tr>"
                % (T["text_mute"], entry["label"], labels, colour,
                   entry["status"].upper()))
        self.map_summary.setText("<table>%s</table>" % "".join(rows))

    # =====================================================================
    # GLOBAL REFRESH
    # =====================================================================
    def refresh_chips(self):
        client = self.active_client()
        year = self.active_fy()
        team = self.auditors()
        checks = self.validation()
        as_at = fy_as_at(year)
        audit = fy_audit_type(year)
        if audit == "Other":
            audit = (year or {}).get("audit_type_other") or "to be described"

        def paint(widget, text, kind):
            widget.setText(text)
            widget.setProperty("chip", kind)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

        paint(self.chip_client,
              "Client:  %s" % (client["name"] if client else "not selected"),
              "green" if client else "warn")
        paint(self.chip_audit, "Audit:  %s" % (audit if year else "not set"),
              "blue" if fy_audit_ok(year) else "warn")
        paint(self.chip_date, "%s:  %s" % (fy_basis_label(year),
                                           fmt_date_long(as_at) if as_at
                                           else "not set"),
              "green" if as_at else "warn")
        paint(self.chip_team, "Team:  %d" % len(team),
              "green" if team else "warn")
        ready_mail, _ = self.mail_ready()
        paint(self.chip_mail, "Mailbox:  %s"
              % (self.mail_settings().get("username") or "not set up"
                 if ready_mail else "not set up"),
              "brass" if ready_mail else "neutral")
        paint(self.chip_status, "Status:  %s"
              % ("Ready to Generate" if checks["ready"]
                 else "%d item%s need attention"
                      % (len(checks["hard"]),
                         "" if len(checks["hard"]) == 1 else "s")),
              "green" if checks["ready"] else "warn")

        for row, key in self.nav_keys.items():
            item = self.nav.item(row)
            base = dict(NAV_ITEMS)
            label = [text for text, k in NAV_ITEMS if k == key][0]
            if key == "import" and self.records:
                label += "   (%d)" % len(self.records)
            elif key == "review" and self.flagged_count():
                label += "   (%d)" % self.flagged_count()
            elif key == "generate":
                done = len([g for g in self.generated if g["status"] == "ok"])
                if done:
                    label += "   (%d)" % done
            elif key == "email":
                pending = len([q for q in self.queue.values()
                               if q["status"] == "pending"])
                if pending:
                    label += "   (%d)" % pending
            item.setText(label)

    def refresh_all(self):
        self.refresh_clients()
        self.render_mapping()
        self.render_cat_stats()
        self.render_records()
        self.refresh_chips()
        current = self.stack.currentIndex()
        if current == self.pages["dashboard"]:
            self.refresh_dashboard()
        elif current == self.pages["preview"]:
            self.render_preview()
        elif current == self.pages["generate"]:
            self.refresh_generate()
        elif current == self.pages["email"]:
            self.refresh_email()
        elif current == self.pages["runs"]:
            self.refresh_runs()
        elif current == self.pages["settings"]:
            self.refresh_settings()

    def closeEvent(self, event):
        if self.gen_thread or self.send_thread:
            if not self.ask("Work in progress",
                            "Documents are still being produced or sent. "
                            "Close anyway?", "Close"):
                event.ignore()
                return
            for worker, thread in ((self.gen_worker, self.gen_thread),
                                   (self.send_worker, self.send_thread)):
                if worker:
                    worker.stop()
                if thread:
                    thread.quit()
                    thread.wait(3000)
        if getattr(self, "reader_thread", None):      # reading can be redone
            self.reader_worker.stop = True
            self.reader_thread.quit()
            self.reader_thread.wait(8000)
        if getattr(self, "bridge_thread", None):      # a read needs no asking
            self.bridge_thread.quit()
            self.bridge_thread.wait(3000)
        self.persist()
        event.accept()


# ---------------------------------------------------------------------------
# Drag-and-drop panel used on the Import page
# ---------------------------------------------------------------------------
class DropZone(QFrame):

    def __init__(self, on_file):
        super().__init__()
        self.on_file = on_file
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(132)
        self.repaint_frame(False)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        title = QLabel("Drop your balance schedule here")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = title
        title.setStyleSheet("color:%s; font-size:16px;" % T["text"])
        subtitle = QLabel("or click to browse — .xlsx, .xls, .csv")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label = subtitle
        subtitle.setStyleSheet("color:%s; font-size:12px;" % T["text_mute"])
        browse = button("Choose file…", "brass")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(browse)
        row.addStretch(1)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(row)
        layout.addStretch(1)

    def repaint_frame(self, hot):
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet("color:%s; font-size:16px;" % T["text"])
            self.sub_label.setStyleSheet("color:%s; font-size:12px;" % T["text_mute"])
        # scoped by name: an unscoped QFrame rule would also box in the two
        # labels, a label being a frame itself
        self.setObjectName("DropZone")
        self.setStyleSheet(
            "#DropZone { border: 2px dashed %s; border-radius: 12px; "
            "background: %s; } #DropZone QLabel { border: 0; "
            "background: transparent; }"
            % (T["accent_hi"] if hot else T["line_soft"],
               T["panel_tint"] if hot else T["well"]))

    def _browse(self):
        window = self.window()
        if hasattr(window, "choose_file"):
            window.choose_file()

    def mousePressEvent(self, event):
        self._browse()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.repaint_frame(True)

    def dragLeaveEvent(self, event):
        self.repaint_frame(False)

    def dropEvent(self, event):
        self.repaint_frame(False)
        urls = event.mimeData().urls()
        if urls:
            self.on_file(urls[0].toLocalFile())
            event.acceptProposedAction()


# ===========================================================================
# SECTION 10 - START-UP
# ===========================================================================

def excepthook(kind, value, trace):
    """Never show a raw traceback to the user; log it to the console."""
    traceback.print_exception(kind, value, trace)
    try:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Unexpected error")
        box.setText("Something went wrong and the action was stopped.")
        box.setInformativeText(str(value)[:400])
        box.setDetailedText("".join(traceback.format_exception(kind, value,
                                                               trace)))
        box.exec()
    except Exception:
        pass


def main():
    sys.excepthook = excepthook
    QApplication.setApplicationName(APP_NAME)
    QApplication.setOrganizationName("Balance Confirmation Generator")
    app = QApplication(sys.argv)
    # Fusion renders identically on Windows, macOS and Linux, so the window
    # looks the same wherever it is opened; the palette keeps the native
    # pieces (calendar pop-ups, menus) in step with the dark theme.
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(T["window"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(T["surface"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(T["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(T["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(T["accent_text"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(T["raised"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(T["text"]))
    app.setPalette(palette)
    app.setStyleSheet(style_sheet())
    font = app.font()
    if os.name == "nt":
        font.setFamily("Segoe UI")
    elif sys.platform == "darwin":
        font.setFamily("Helvetica Neue")
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
