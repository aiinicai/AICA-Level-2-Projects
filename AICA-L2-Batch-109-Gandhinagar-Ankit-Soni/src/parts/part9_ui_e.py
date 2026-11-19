
    # =====================================================================
    # PAGE 07 - EMAIL DELIVERY
    # =====================================================================
    def _page_email(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, _ = card("Your mailbox",
                              "Letters are sent from your own account")
        body.addWidget(notice(
            "warn", "Use an <b>app password</b>, not your normal password. "
                    "Gmail, Outlook, Yahoo and Zoho all issue one from the "
                    "security page of your account once two-factor "
                    "authentication is on. Nothing is sent anywhere except to "
                    "your own mail server, and every message lands in your "
                    "Sent items."))
        grid = QGridLayout()
        grid.setSpacing(9)

        def add(row, column, label, widget, span=1):
            holder = QVBoxLayout()
            holder.setSpacing(4)
            holder.addWidget(field_label(label))
            holder.addWidget(widget)
            wrapper = pane()
            wrapper.setLayout(holder)
            grid.addWidget(wrapper, row, column, 1, span)

        self.mail_provider = QComboBox()
        self.mail_provider.addItems(list(SMTP_PRESETS))
        self.mail_provider.currentTextChanged.connect(self.on_provider_changed)
        self.mail_host = QLineEdit()
        self.mail_port = QSpinBox()
        self.mail_port.setRange(1, 65535)
        self.mail_port.setValue(587)
        self.mail_security = QComboBox()
        self.mail_security.addItem("STARTTLS (587)", "starttls")
        self.mail_security.addItem("SSL / TLS (465)", "ssl")
        self.mail_security.addItem("None (not recommended)", "none")
        self.mail_username = QLineEdit()
        self.mail_username.setPlaceholderText("you@yourfirm.com")
        self.mail_password_edit = QLineEdit()
        self.mail_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.mail_password_edit.setPlaceholderText("app password")
        self.mail_sender = QLineEdit()
        self.mail_sender.setPlaceholderText("leave blank to use the username")
        self.mail_sender_name = QLineEdit()
        self.mail_sender_name.setPlaceholderText("Ankit Soni and Associates")
        for widget in (self.mail_host, self.mail_username, self.mail_sender,
                       self.mail_sender_name):
            widget.editingFinished.connect(self.save_mail_settings)
        self.mail_port.valueChanged.connect(self.save_mail_settings)
        self.mail_security.currentIndexChanged.connect(self.save_mail_settings)

        add(0, 0, "Provider", self.mail_provider)
        add(0, 1, "SMTP server", self.mail_host)
        add(0, 2, "Port", self.mail_port)
        add(0, 3, "Encryption", self.mail_security)
        add(1, 0, "Username", self.mail_username, 2)
        add(1, 2, "App password", self.mail_password_edit, 2)
        add(2, 0, "From address", self.mail_sender, 2)
        add(2, 1 + 1, "From name", self.mail_sender_name, 2)
        body.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(9)
        self.remember_check = QCheckBox(
            "Remember the password in this computer's credential store"
            if HAS_KEYRING else
            "Remember the password (needs the keyring library)")
        self.remember_check.setEnabled(HAS_KEYRING)
        self.remember_check.stateChanged.connect(self.on_remember_changed)
        test_btn = button("Test connection", "brass")
        test_btn.clicked.connect(self.test_connection)
        self.btn_test_mail = button("Send a test letter to myself")
        self.btn_test_mail.clicked.connect(self.send_test_email)
        row.addWidget(self.remember_check)
        row.addStretch(1)
        row.addWidget(test_btn)
        row.addWidget(self.btn_test_mail)
        body.addLayout(row)
        self.mail_state = QLabel("")
        self.mail_state.setWordWrap(True)
        self.mail_state.setVisible(False)
        body.addWidget(self.mail_state)
        layout.addWidget(frame)

        frame2, body2, header2 = card(
            "Message", "Placeholders: " + "  ".join(PLACEHOLDERS), light=True)
        reset = button("Restore default wording", small=True)
        reset.clicked.connect(self.reset_message)
        header2.addWidget(reset)
        body2.addWidget(field_label("Subject", light=True))
        self.mail_subject = QLineEdit()
        self.mail_subject.editingFinished.connect(self.save_mail_settings)
        body2.addWidget(self.mail_subject)
        body2.addWidget(field_label("Body", light=True))
        self.mail_body = QPlainTextEdit()
        self.mail_body.setMinimumHeight(190)
        self.mail_body.textChanged.connect(self.on_body_changed)
        body2.addWidget(self.mail_body)
        options = QHBoxLayout()
        options.setSpacing(16)
        self.cc_check = QCheckBox("Cc the audit team")
        self.cc_check.stateChanged.connect(self.save_mail_settings)
        self.reply_check = QCheckBox("Set Reply-To to the audit team")
        self.reply_check.stateChanged.connect(self.save_mail_settings)
        delay_box = QHBoxLayout()
        delay_box.setSpacing(6)
        delay_label = QLabel("Gap between sends (ms)")
        delay_label.setObjectName("HintLight")
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 20000)
        self.delay_spin.setSingleStep(250)
        self.delay_spin.setFixedWidth(100)
        self.delay_spin.valueChanged.connect(self.save_mail_settings)
        delay_box.addWidget(delay_label)
        delay_box.addWidget(self.delay_spin)
        options.addWidget(self.cc_check)
        options.addWidget(self.reply_check)
        options.addLayout(delay_box)
        options.addStretch(1)
        body2.addLayout(options)
        layout.addWidget(frame2)

        frame3, body3, header3 = card("Send queue", "")
        self.mail_note = QLabel("No documents generated yet")
        self.mail_note.setObjectName("HintDark")
        header3.addWidget(self.mail_note)
        self.btn_send = button("Send all confirmations", "primary")
        self.btn_send.clicked.connect(lambda: self.start_send(False))
        self.btn_retry = button("Retry failed")
        self.btn_retry.clicked.connect(lambda: self.start_send(True))
        self.btn_log = button("Export send log (CSV)")
        self.btn_log.clicked.connect(self.export_send_log)
        for widget in (self.btn_send, self.btn_retry, self.btn_log):
            header3.addWidget(widget)
        attach_row = QHBoxLayout()
        attach_row.setSpacing(9)
        attach_label = QLabel("Attach to each e-mail")
        attach_label.setObjectName("HintDark")
        self.attach_mode = QComboBox()
        for label, key in ATTACH_MODES:
            self.attach_mode.addItem(label, key)
        self.attach_mode.setMinimumWidth(330)
        self.attach_mode.currentIndexChanged.connect(self.on_attach_mode)
        self.btn_link_signed = button("Link signed PDFs from a folder…",
                                      "brass")
        self.btn_link_signed.setToolTip(
            "Pick the folder holding the letters the client printed on its "
            "letterhead, signed and scanned. Each PDF is tied to its party by "
            "the reference code or the party name in the file name.")
        self.btn_link_signed.clicked.connect(self.link_signed_folder)
        attach_row.addWidget(attach_label)
        attach_row.addWidget(self.attach_mode)
        attach_row.addWidget(self.btn_link_signed)
        attach_row.addStretch(1)
        body3.addLayout(attach_row)
        self.attach_hint = QLabel("")
        self.attach_hint.setObjectName("HintDark")
        self.attach_hint.setWordWrap(True)
        body3.addWidget(self.attach_hint)
        self.mail_bar = QProgressBar()
        self.mail_bar.setValue(0)
        self.mail_progress = QLabel("Idle")
        self.mail_progress.setObjectName("HintDark")
        body3.addWidget(self.mail_bar)
        body3.addWidget(self.mail_progress)
        self.mail_table = table(["Party", "Category", "To", "Attachment",
                                 "Status", "Detail", "Signed PDF"],
                                stretch_column=5)
        self.mail_table.setMinimumHeight(260)
        body3.addWidget(self.mail_table)
        layout.addWidget(frame3, 1)
        return page

    def on_provider_changed(self, name):
        if self._building:
            return
        host, port, security = SMTP_PRESETS.get(name, ("", 587, "starttls"))
        if host:
            self.mail_host.setText(host)
            self.mail_port.setValue(port)
            index = self.mail_security.findData(security)
            if index >= 0:
                self.mail_security.setCurrentIndex(index)
        self.save_mail_settings()

    def on_body_changed(self):
        if not self._building:
            self.mail_settings()["body"] = self.mail_body.toPlainText()
            self._mail_save_pending = True
            QTimer.singleShot(600, self._flush_mail_settings)

    def _flush_mail_settings(self):
        if getattr(self, "_mail_save_pending", False):
            self._mail_save_pending = False
            self.persist()

    def save_mail_settings(self):
        # never write the blank start-up state over saved settings: the mail
        # widgets only hold real values once refresh_email() has filled them
        if self._building or not getattr(self, "_mail_loaded", False):
            return
        mail = self.mail_settings()
        mail["provider"] = self.mail_provider.currentText()
        mail["host"] = self.mail_host.text().strip()
        mail["port"] = self.mail_port.value()
        mail["security"] = self.mail_security.currentData()
        mail["username"] = self.mail_username.text().strip()
        mail["sender"] = self.mail_sender.text().strip()
        mail["sender_name"] = self.mail_sender_name.text().strip()
        mail["subject"] = self.mail_subject.text()
        mail["body"] = self.mail_body.toPlainText()
        mail["cc_team"] = self.cc_check.isChecked()
        mail["reply_to_team"] = self.reply_check.isChecked()
        mail["delay_ms"] = self.delay_spin.value()
        mail["remember_password"] = self.remember_check.isChecked()
        self.persist()

    def on_remember_changed(self, _state):
        if self._building:
            return
        self.save_mail_settings()
        if not HAS_KEYRING:
            return
        username = self.mail_username.text().strip()
        password = self.mail_password_edit.text()
        try:
            if self.remember_check.isChecked() and username and password:
                keyring.set_password("BalanceConfirmationGenerator",
                                     username, password)
                self.toast("Password stored in this computer's credential "
                           "store.", "ok")
            elif not self.remember_check.isChecked() and username:
                try:
                    keyring.delete_password("BalanceConfirmationGenerator",
                                            username)
                except Exception:
                    pass
                self.toast("Stored password removed.", "ok")
        except Exception as exc:
            self.toast("The credential store refused: %s" % exc, "warn")

    def reset_message(self):
        self.mail_subject.setText(DEFAULT_SUBJECT)
        self.mail_body.setPlainText(DEFAULT_BODY)
        self.save_mail_settings()
        self.toast("Default wording restored.", "ok")

    def mail_account(self):
        mail = self.mail_settings()
        password = self.mail_password_edit.text()
        if not password and HAS_KEYRING and mail.get("remember_password"):
            try:
                password = keyring.get_password(
                    "BalanceConfirmationGenerator",
                    mail.get("username", "")) or ""
            except Exception:
                password = ""
        return {"host": mail.get("host", ""), "port": int(mail.get("port", 587)),
                "security": mail.get("security", "starttls"),
                "username": mail.get("username", ""), "password": password}

    def mail_options(self):
        mail = self.mail_settings()
        return {"subject": mail.get("subject") or DEFAULT_SUBJECT,
                "body": mail.get("body") or DEFAULT_BODY,
                "cc_team": mail.get("cc_team", True),
                "reply_to_team": mail.get("reply_to_team", True),
                "sender": mail.get("sender") or mail.get("username", ""),
                "sender_name": mail.get("sender_name", "")}

    def mail_ready(self):
        account = self.mail_account()
        missing = []
        if not account["host"]:
            missing.append("the SMTP server")
        if not account["username"]:
            missing.append("the username")
        if not account["password"]:
            missing.append("the app password")
        return (not missing), missing

    def show_mail_state(self, text, kind):
        self.mail_state.setText(text)
        self.mail_state.setObjectName({"green": "NoticeGreen",
                                       "blue": "NoticeBlue",
                                       "warn": "NoticeWarn",
                                       "red": "NoticeRed"}[kind])
        self.mail_state.setStyleSheet(style_sheet())
        self.mail_state.setVisible(True)

    def test_connection(self):
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        account = self.mail_account()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            server = smtp_connect(account["host"], account["port"],
                                  account["security"], account["username"],
                                  account["password"], timeout=25)
            server.quit()
            QApplication.restoreOverrideCursor()
            self.show_mail_state(
                "Signed in to <b>%s</b> as <b>%s</b>. Messages will be sent "
                "from this mailbox." % (account["host"], account["username"]),
                "green")
            self.toast("Mail server connection succeeded.", "ok")
            if HAS_KEYRING and self.remember_check.isChecked():
                try:
                    keyring.set_password("BalanceConfirmationGenerator",
                                         account["username"],
                                         account["password"])
                except Exception:
                    pass
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.show_mail_state(friendly_smtp_error(exc), "red")
            self.toast("Connection failed.", "err")
        self.refresh_email()

    def send_test_email(self):
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        done = [g for g in self.generated if g["status"] == "ok"]
        if not done:
            self.toast("Generate at least one letter first.", "warn")
            return
        account = self.mail_account()
        options = dict(self.mail_options())
        record = done[0]
        conf = dict(record["conf"])
        conf["party_email"] = options["sender"] or account["username"]
        options["cc_team"] = False
        options["subject"] = "[TEST] " + options["subject"]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            server = smtp_connect(account["host"], account["port"],
                                  account["security"], account["username"],
                                  account["password"], timeout=40)
            name, payload, problem = self.attachment_for(record)
            if problem:
                raise ValueError(problem)
            server.send_message(build_email_message(
                conf, name, payload, options))
            server.quit()
            QApplication.restoreOverrideCursor()
            self.show_mail_state("Test letter sent to <b>%s</b>. Check that it "
                                 "arrived, then send the full run."
                                 % conf["party_email"], "green")
            self.toast("Test email sent.", "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.show_mail_state(friendly_smtp_error(exc), "red")
            self.toast("Test email failed.", "err")

    # ------------------------------------------------------ what is attached
    def attach_key(self):
        return self.mail_settings().get("attach_mode") or "pdf"

    def on_attach_mode(self, _index=0):
        if self._building:
            return
        self.mail_settings()["attach_mode"] = self.attach_mode.currentData()
        self.persist()
        self.refresh_email()

    def attachment_for(self, record):
        """(file name, bytes, problem) for one party under the chosen mode.
        Nothing is ever substituted silently: where the chosen kind of file is
        missing the problem is returned instead."""
        mode = self.attach_key()
        if mode == "signed":
            path = record.get("signed_path") or ""
            if not path:
                return "", b"", "No signed PDF linked"
            try:
                with open(path, "rb") as handle:
                    data = handle.read()
            except Exception as exc:
                return "", b"", "Signed PDF could not be read: %s" % exc
            if data[:5] != b"%PDF-":
                return "", b"", "The linked file is not a PDF"
            return os.path.basename(path), data, ""
        if mode == "docx":
            if not record.get("data"):
                return "", b"", "Document not available"
            return record["filename"], record["data"], ""
        if not record.get("pdf_data"):               # made on the spot if absent
            try:
                record["pdf_data"] = pdf_bytes(
                    record["conf"],
                    float(self.db["settings"].get("letterhead_space_cm", 0)
                          or 0))
                record["pdf_filename"] = \
                    os.path.splitext(record["filename"])[0] + ".pdf"
            except Exception as exc:
                return "", b"", "PDF could not be produced: %s" % exc
        return record["pdf_filename"], record["pdf_data"], ""

    def attachment_label(self, record):
        mode = self.attach_key()
        if mode == "signed":
            path = record.get("signed_path") or ""
            return os.path.basename(path) if path else "— none linked —"
        if mode == "docx":
            return record["filename"]
        return record.get("pdf_filename") or \
            os.path.splitext(record["filename"])[0] + ".pdf"

    def link_signed_folder(self, _checked=False, folder=None):
        done = [g for g in self.generated if g["status"] == "ok"]
        if not done:
            self.toast("Generate the letters first.", "warn")
            return
        if not folder:
            folder = QFileDialog.getExistingDirectory(
                self, "Folder holding the signed PDFs",
                self.run_output_folder() or os.path.expanduser("~"))
        if not folder:
            return
        try:
            paths = sorted(os.path.join(folder, name)
                           for name in os.listdir(folder)
                           if name.lower().endswith(".pdf"))
        except Exception as exc:
            self.toast("That folder could not be read: %s" % exc, "err")
            return
        # the unsigned PDFs this application wrote are not signed copies,
        # even when the client's scans are saved beside them
        generated = {os.path.normcase(os.path.abspath(g["pdf_path"]))
                     for g in done if g.get("pdf_path")}
        unsigned = [p for p in paths
                    if os.path.normcase(os.path.abspath(p)) in generated]
        paths = [p for p in paths if p not in unsigned and looks_like_pdf(p)]
        documents = [{"id": g["id"], "party_name": g["conf"]["party_name"],
                      "category": g["conf"]["category"],
                      "reference": g["conf"].get("reference", ""),
                      "filename": g["filename"]} for g in done]
        linked, loose = match_signed_pdfs(paths, documents)
        for record in done:
            if record["id"] in linked:
                record["signed_path"] = linked[record["id"]]
        if linked and self.attach_key() != "signed":
            self.mail_settings()["attach_mode"] = "signed"
            self.persist()
        self.refresh_email()
        text = "%d signed PDF%s linked" % (len(linked),
                                           "" if len(linked) == 1 else "s")
        if loose:
            text += ", %d file%s not matched to a party" % (
                len(loose), "" if len(loose) == 1 else "s")
        missing = len(done) - len([g for g in done if g.get("signed_path")])
        if missing:
            text += " · %d part%s still without one" % (
                missing, "y" if missing == 1 else "ies")
        if unsigned:
            text += " · %d unsigned original%s from this run left out" % (
                len(unsigned), "" if len(unsigned) == 1 else "s")
        self.toast(text + ".", "ok" if linked and not loose else "warn")

    def choose_signed_pdf(self, document_id, path=None):
        record = next((g for g in self.generated if g["id"] == document_id),
                      None)
        if not record:
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Signed PDF for %s" % record["conf"]["party_name"],
                os.path.dirname(record.get("signed_path") or "")
                or self.run_output_folder() or os.path.expanduser("~"),
                "PDF files (*.pdf)")
        if not path:
            return
        if not looks_like_pdf(path):
            self.toast("That file is not a PDF.", "err")
            return
        record["signed_path"] = path
        self.refresh_email()

    def build_queue(self):
        existing = self.queue
        self.queue = {}
        for record in self.generated:
            if record["status"] != "ok":
                continue
            earlier = existing.get(record["id"])
            self.queue[record["id"]] = {
                "id": record["id"], "party": record["conf"]["party_name"],
                "category": record["conf"]["category"],
                "to": record["conf"].get("party_email", ""),
                "filename": record["filename"],
                "attachment": self.attachment_label(record),
                "has_attachment": self.attach_key() != "signed"
                                  or bool(record.get("signed_path")),
                "status": earlier["status"] if earlier else (
                    "pending" if valid_email(record["conf"].get("party_email"))
                    else "no email"),
                "detail": earlier["detail"] if earlier else "",
                "sent_at": earlier["sent_at"] if earlier else "",
            }

    def render_mail_table(self):
        self.mail_table.setRowCount(0)
        for entry in self.queue.values():
            row = self.mail_table.rowCount()
            self.mail_table.insertRow(row)
            self.mail_table.setItem(row, 0, cell(entry["party"], bold=True))
            self.mail_table.setItem(row, 1, cell(entry["category"]))
            self.mail_table.setItem(row, 2, cell(entry["to"] or "—"))
            self.mail_table.setItem(row, 3, cell(
                entry["attachment"],
                color=None if entry["has_attachment"] else T["warn"]))
            colour = {"sent": T["ok"], "failed": T["err"],
                      "no email": T["warn"]}.get(entry["status"], T["text_soft"])
            self.mail_table.setItem(row, 4, cell(entry["status"].upper(),
                                                 color=colour, bold=True))
            self.mail_table.setItem(row, 5, cell(entry["detail"]))
            pick = button("Choose PDF…")
            pick.setToolTip("Attach the signed, scanned letter for this party")
            pick.clicked.connect(
                lambda _=False, key=entry["id"]: self.choose_signed_pdf(key))
            self.mail_table.setCellWidget(row, 6, pick)
        self.mail_table.resizeColumnsToContents()
        fit_widget_columns(self.mail_table, [6])

    def refresh_email(self):
        self._building = True
        mail = self.mail_settings()
        index = self.mail_provider.findText(mail.get("provider", ""))
        if index >= 0:
            self.mail_provider.setCurrentIndex(index)
        self.mail_host.setText(mail.get("host", ""))
        self.mail_port.setValue(int(mail.get("port", 587) or 587))
        security = self.mail_security.findData(mail.get("security", "starttls"))
        if security >= 0:
            self.mail_security.setCurrentIndex(security)
        self.mail_username.setText(mail.get("username", ""))
        self.mail_sender.setText(mail.get("sender", ""))
        self.mail_sender_name.setText(mail.get("sender_name", ""))
        self.mail_subject.setText(mail.get("subject") or DEFAULT_SUBJECT)
        if self.mail_body.toPlainText() != (mail.get("body") or DEFAULT_BODY):
            self.mail_body.setPlainText(mail.get("body") or DEFAULT_BODY)
        self.cc_check.setChecked(bool(mail.get("cc_team", True)))
        self.reply_check.setChecked(bool(mail.get("reply_to_team", True)))
        self.delay_spin.setValue(int(mail.get("delay_ms", 1500) or 0))
        mode_index = self.attach_mode.findData(self.attach_key())
        if mode_index >= 0:
            self.attach_mode.setCurrentIndex(mode_index)
        self.remember_check.setChecked(bool(mail.get("remember_password"))
                                       and HAS_KEYRING)
        if (HAS_KEYRING and mail.get("remember_password")
                and not self.mail_password_edit.text()
                and mail.get("username")):
            try:
                stored = keyring.get_password("BalanceConfirmationGenerator",
                                              mail["username"])
                if stored:
                    self.mail_password_edit.setText(stored)
            except Exception:
                pass
        self._building = False
        self._mail_loaded = True

        self.build_queue()
        self.render_mail_table()
        pending = len([q for q in self.queue.values()
                       if q["status"] == "pending"])
        no_address = len([q for q in self.queue.values()
                          if q["status"] == "no email"])
        failed = len([q for q in self.queue.values()
                      if q["status"] == "failed"])
        self.attach_hint.setText(ATTACH_HINTS.get(self.attach_key(), ""))
        self.mail_note.setText(
            "%d documents · %d ready to send%s"
            % (len(self.queue), pending,
               (" · %d without a recipient address" % no_address)
               if no_address else "") if self.queue
            else "No documents generated yet")
        ready, _ = self.mail_ready()
        busy = self.send_thread is not None
        self.btn_send.setEnabled(bool(pending or failed) and ready and not busy)
        self.btn_retry.setEnabled(bool(failed) and ready and not busy)
        self.btn_log.setEnabled(bool(self.queue))
        self.btn_test_mail.setEnabled(
            bool([g for g in self.generated if g["status"] == "ok"]))
        self.refresh_chips()

    def start_send(self, retry_only):
        if self.send_thread:
            return
        ready, missing = self.mail_ready()
        if not ready:
            self.show_mail_state("Still needed: %s." % ", ".join(missing),
                                 "warn")
            return
        wanted = ["failed"] if retry_only else ["pending", "failed"]
        targets = [q for q in self.queue.values() if q["status"] in wanted]
        if not targets:
            self.toast("Nothing to send. Add party email addresses in "
                       "Review & mapping.", "warn")
            return
        account = self.mail_account()
        team = ", ".join(a["email"] for a in self.auditors())
        if not self.ask(
                "Send %d confirmation email%s"
                % (len(targets), "" if len(targets) == 1 else "s"),
                "From: %s\nRecipients: %d parties, each with its own %s."
                "%s\n\nConfirm that the letters have been reviewed. "
                "Emails sent cannot be recalled."
                % (account["username"], len(targets),
                   {"pdf": "PDF letter", "docx": "Word letter",
                    "signed": "signed PDF"}[self.attach_key()],
                   ("\nCc: " + team) if self.cc_check.isChecked() and team
                   else ""),
                "Send now", danger=False):
            return

        by_id = {g["id"]: g for g in self.generated}
        jobs, skipped = [], 0
        for entry in targets:
            record = by_id.get(entry["id"])
            if not record:
                entry["status"] = "failed"
                entry["detail"] = "Document not available"
                continue
            conf = record["conf"]
            if not valid_email(conf.get("party_email")):
                entry["status"] = "no email"
                entry["detail"] = "No valid recipient"
                continue
            name, payload, problem = self.attachment_for(record)
            if problem:
                # held back rather than sent with a different file: the
                # auditor chose what the party is to receive
                if entry["status"] != "failed":
                    entry["status"] = "pending"
                entry["detail"] = "Not sent: " + problem
                skipped += 1
                continue
            jobs.append((conf, name, payload))
        if not jobs:
            self.render_mail_table()
            self.toast("Nothing was sent: %s." % (
                "no signed PDF is linked to these parties"
                if skipped and self.attach_key() == "signed"
                else "no message had a valid recipient and attachment"),
                "warn")
            return

        for conf, _, _ in jobs:
            self.queue[conf["id"]]["status"] = "sending"
            self.queue[conf["id"]]["detail"] = ""
        self.render_mail_table()
        self.btn_send.setEnabled(False)
        self.btn_retry.setEnabled(False)
        self.mail_bar.setValue(0)

        self.send_thread = QThread(self)
        self.send_worker = SendWorker(jobs, account, self.mail_options(),
                                      self.delay_spin.value())
        self.send_worker.moveToThread(self.send_thread)
        self.send_thread.started.connect(self.send_worker.run)
        self.send_worker.progress.connect(self.on_send_progress)
        self.send_worker.result.connect(self.on_send_result)
        self.send_worker.finished.connect(self.on_send_finished)
        self.send_thread.start()

    def on_send_progress(self, done, total, party):
        self.mail_bar.setMaximum(max(total, 1))
        self.mail_bar.setValue(done)
        self.mail_progress.setText(
            "Sending…  %d of %d completed  —  %s" % (done, total,
                                                               party)
            if party else "Sending…  %d of %d completed" % (done, total))

    def on_send_result(self, document_id, status, detail, message_id=""):
        entry = self.queue.get(document_id)
        if entry:
            entry["status"] = status
            entry["detail"] = detail
            entry["sent_at"] = (datetime.now().isoformat(timespec="seconds")
                                if status == "sent" else "")
            self.render_mail_table()
        run = next((r for r in self.db["runs"]
                    if r["id"] == self.current_run_id), None)
        if run and entry:
            for document in run["documents"]:
                if document["filename"] == entry["filename"]:
                    document["email_status"] = status
                    document["email"] = entry["to"]
                    document["email_at"] = datetime.now().isoformat(
                        timespec="seconds")
                    document["sent_at"] = document["email_at"]
                    if message_id:
                        document["message_id"] = message_id

    def on_send_finished(self, sent, failed):
        if self.send_thread:
            self.send_thread.quit()
            self.send_thread.wait(5000)
        self.send_thread = None
        self.send_worker = None
        self.mail_progress.setText(
            "Finished — %d sent%s." % (sent, (", %d failed" % failed)
                                            if failed else ""))
        self.persist()
        self.refresh_email()
        self.toast("%d email%s sent%s." % (sent, "" if sent == 1 else "s",
                                           (", %d failed" % failed) if failed
                                           else ""),
                   "warn" if failed else "ok")

    def export_send_log(self):
        if not self.queue:
            return
        suggested = os.path.join(
            self.db["settings"].get("output_folder") or os.path.expanduser("~"),
            "balance-confirmation-send-log-%s.csv" % date.today().isoformat())
        path, _ = QFileDialog.getSaveFileName(self, "Export send log",
                                              suggested, "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Party", "Category", "Recipient", "File",
                                 "Status", "Detail", "Sent at"])
                for entry in self.queue.values():
                    writer.writerow([entry["party"], entry["category"],
                                     entry["to"], entry["filename"],
                                     entry["status"], entry["detail"],
                                     entry["sent_at"]])
            self.toast("Send log written to %s" % path, "ok")
        except Exception as exc:
            self.toast("The log could not be written: %s" % exc, "err")

    # =====================================================================
    # PAGE 08 - SAVED RUNS
    # =====================================================================
    def _page_runs(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Saved runs", "", light=True)
        self.runs_note = QLabel("No runs saved")
        self.runs_note.setObjectName("HintLight")
        header.addWidget(self.runs_note)
        self.runs_table = table(["Date", "Client", "Type of audit",
                                 "Year / period", "Source", "Documents",
                                 "Sent", ""], stretch_column=3)
        self.runs_table.setMinimumHeight(260)
        body.addWidget(self.runs_table)
        layout.addWidget(frame)

        self.run_detail_card, detail_body, detail_header = card(
            "Run detail", "")
        self.run_detail_note = QLabel("")
        self.run_detail_note.setObjectName("HintDark")
        detail_header.addWidget(self.run_detail_note)
        close = button("Close", small=True)
        close.clicked.connect(lambda: self.run_detail_card.setVisible(False))
        detail_header.addWidget(close)
        self.run_detail_table = table(["Party", "Category", "Balance", "File",
                                       "Email", "Delivery"], stretch_column=0)
        detail_body.addWidget(self.run_detail_table)
        self.run_detail_card.setVisible(False)
        layout.addWidget(self.run_detail_card, 1)
        layout.addStretch(1)
        return page

    def refresh_runs(self):
        runs = self.db["runs"]
        self.runs_note.setText("%d run(s) saved" % len(runs) if runs
                               else "No runs saved")
        self.runs_table.setRowCount(0)
        for run in runs:
            row = self.runs_table.rowCount()
            self.runs_table.insertRow(row)
            sent = len([d for d in run.get("documents", [])
                        if d.get("email_status") == "sent"])
            span = run.get("period_label") or period_label(
                run.get("basis"), run.get("as_at") or run.get("year_end"),
                run.get("period_start")) or ""
            audit = run.get("audit_type", "Statutory Audit")
            if audit == "Other":
                audit = run.get("audit_type_other") or "Other"
            self.runs_table.setItem(row, 0, cell(stamp_text(
                run.get("created_at"))))
            self.runs_table.setItem(row, 1, cell(run.get("client_name"),
                                                 bold=True))
            self.runs_table.setItem(row, 2, cell(audit))
            self.runs_table.setItem(row, 3, cell("%s  ·  %s"
                                                 % (run.get("year"), span)))
            source = run.get("source")
            self.runs_table.setItem(row, 4, cell(
                "%s / %s" % (source["name"], source["sheet"]) if source
                else "—"))
            self.runs_table.setItem(row, 5, cell(len(run.get("documents", [])),
                                                 align_right=True))
            self.runs_table.setItem(row, 6, cell(sent, align_right=True))
            holder = pane()
            box = QHBoxLayout(holder)
            box.setContentsMargins(4, 2, 4, 2)
            box.setSpacing(5)
            view = button("View", small=True)
            view.clicked.connect(lambda _, r=run: self.show_run(r))
            folder = button("Folder", small=True)
            folder.clicked.connect(lambda _, r=run: self.open_run_folder(r))
            delete = button("Delete", "danger", small=True)
            delete.clicked.connect(lambda _, r=run: self.delete_run(r))
            for widget in (view, folder, delete):
                box.addWidget(widget)
            box.addStretch(1)
            self.runs_table.setCellWidget(row, 7, holder)
        self.runs_table.resizeColumnsToContents()
        fit_widget_columns(self.runs_table, [7])

    def show_run(self, run):
        self.run_detail_card.setVisible(True)
        audit = run.get("audit_type", "Statutory Audit")
        if audit == "Other":
            audit = run.get("audit_type_other") or "Other"
        span = run.get("period_label") or ""
        self.run_detail_note.setText(
            "%s · %s · %s · %s"
            % (run.get("client_name"), audit, span,
               stamp_text(run.get("created_at"))))
        self.run_detail_table.setRowCount(0)
        for document in run.get("documents", []):
            row = self.run_detail_table.rowCount()
            self.run_detail_table.insertRow(row)
            self.run_detail_table.setItem(row, 0, cell(document["party_name"],
                                                       bold=True))
            self.run_detail_table.setItem(row, 1, cell(document["category"]))
            self.run_detail_table.setItem(row, 2, cell(
                amount_label(document.get("amount"),
                             document.get("currency")) or "—",
                align_right=True))
            self.run_detail_table.setItem(row, 3, cell(document["filename"]))
            self.run_detail_table.setItem(row, 4,
                                          cell(document.get("email") or "—"))
            status = document.get("email_status", "not sent")
            colour = {"sent": T["ok"], "failed": T["err"]}.get(status,
                                                                  T["text_mute"])
            self.run_detail_table.setItem(row, 5, cell(status.upper(),
                                                       color=colour))
        self.run_detail_table.resizeColumnsToContents()

    def open_run_folder(self, run):
        folder = run.get("folder")
        if not folder or not os.path.isdir(folder):
            self.toast("That run's folder is no longer on this computer.",
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

    def delete_run(self, run):
        if not self.ask("Delete run",
                        "Delete the run of %s for %s? The Word files already "
                        "saved on disk are not affected."
                        % (stamp_text(run.get("created_at")),
                           run.get("client_name")), "Delete run"):
            return
        self.db["runs"] = [r for r in self.db["runs"] if r["id"] != run["id"]]
        self.persist()
        self.refresh_runs()
        self.refresh_clients()
        self.toast("Run deleted.", "ok")
