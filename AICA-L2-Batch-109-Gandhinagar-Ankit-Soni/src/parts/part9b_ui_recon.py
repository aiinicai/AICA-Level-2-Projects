
    # =====================================================================
    # PAGE 08 - CONFIRMATIONS RECEIVED
    # ---------------------------------------------------------------------
    # The replies that came back, reconciled against what was sent, with the
    # six reports an auditor puts in the working papers.  Replies reach this
    # page from the saved records; the Gmail bridge writes into the same
    # place, so nothing here has to change when it is connected.
    # =====================================================================
    def _page_recon(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 26)
        layout.setSpacing(16)

        frame, body, header = card("Position", "")
        self.recon_scope = QLabel("")
        self.recon_scope.setObjectName("HintDark")
        header.addWidget(self.recon_scope)
        refresh = button("Recalculate")
        refresh.clicked.connect(self.refresh_recon)
        sync = button("Sync Gmail bridge", "primary")
        sync.setToolTip(
            "Read the replies the Apps Script has been collecting on Google's "
            "servers since the last sync")
        sync.clicked.connect(lambda: self.sync_bridge())
        import_replies = button("Import replies (JSON)…", "brass")
        import_replies.setToolTip(
            "Load replies from a file you have prepared or downloaded "
            "yourself")
        import_replies.clicked.connect(self.import_replies)
        header.addWidget(refresh)
        header.addWidget(sync)
        header.addWidget(import_replies)

        self.bridge_note = QLabel("")
        self.bridge_note.setObjectName("HintDark")
        body.addWidget(self.bridge_note)

        # the reply's own document: fetched, opened and read on this computer
        reader_row = QHBoxLayout()
        reader_row.setSpacing(8)
        self.btn_read_docs = button("Read attached PDFs (OCR)", "primary")
        self.btn_read_docs.setToolTip(
            "Download each reply's PDF or scan from the bridge and read the "
            "confirmed amount from it on this computer")
        self.btn_read_docs.clicked.connect(
            lambda: self.read_reply_documents(retry=True))
        self.btn_add_pdf = button("Add a reply from a PDF or scan…")
        self.btn_add_pdf.setToolTip(
            "For a confirmation received by post, by hand or on another "
            "mailbox: the file is read and matched to its party")
        self.btn_add_pdf.clicked.connect(lambda: self.add_reply_from_file())
        self.reader_note = QLabel("")
        self.reader_note.setObjectName("HintDark")
        self.reader_note.setWordWrap(True)
        reader_row.addWidget(self.btn_read_docs)
        reader_row.addWidget(self.btn_add_pdf)
        reader_row.addWidget(self.reader_note, 1)
        body.addLayout(reader_row)
        self.recon_stats = QHBoxLayout()
        self.recon_stats.setSpacing(10)
        body.addLayout(self.recon_stats)
        # replies waiting for a decision are never left for the reviewer to
        # stumble on: the page says so and takes them there
        self.btn_queue = button("", "brass")
        self.btn_queue.setToolTip("Open the Exception Queue")
        self.btn_queue.clicked.connect(
            lambda: self.show_report(REPORT_EXCEPTIONS))
        self.btn_queue.setVisible(False)
        queue_row = QHBoxLayout()
        queue_row.addWidget(self.btn_queue)
        queue_row.addStretch(1)
        body.addLayout(queue_row)
        layout.addWidget(frame)

        frame2, body2, header2 = card("Reports", "", light=True)
        self.report_note = QLabel("")
        self.report_note.setObjectName("HintLight")
        header2.addWidget(self.report_note)
        self.btn_assign = button("Review reply…")
        self.btn_assign.setToolTip(
            "Read the selected reply, choose the party and request it "
            "belongs to, and accept the confirmed value - or set it aside")
        self.btn_assign.clicked.connect(self.assign_selected_reply)
        header2.addWidget(self.btn_assign)
        self.btn_audit = button("Audit status…")
        self.btn_audit.setToolTip(
            "Create or open the follow-up record for the selected "
            "confirmation")
        self.btn_audit.clicked.connect(self.audit_selected_row)
        header2.addWidget(self.btn_audit)
        excel = button("Export all to Excel", "primary")
        excel.clicked.connect(self.export_reports_excel)
        pdf = button("Export all to PDF", "blue")
        pdf.clicked.connect(self.export_reports_pdf)
        header2.addWidget(excel)
        header2.addWidget(pdf)

        chooser = QHBoxLayout()
        chooser.setSpacing(8)
        chooser.addWidget(field_label("Report", light=True))
        self.report_combo = QComboBox()
        for key, title, _subtitle in REPORT_TITLES:
            self.report_combo.addItem(title, key)
        self.report_combo.setMinimumWidth(300)
        self.report_combo.currentIndexChanged.connect(self.render_report)
        chooser.addWidget(self.report_combo)
        self.report_subtitle = QLabel("")
        self.report_subtitle.setObjectName("HintLight")
        chooser.addWidget(self.report_subtitle)
        chooser.addStretch(1)
        body2.addLayout(chooser)

        self.report_table = table([""])
        self.report_table.setMinimumHeight(360)
        self.report_table.cellClicked.connect(self.on_report_cell)
        body2.addWidget(self.report_table)
        self.report_totals = QLabel("")
        self.report_totals.setObjectName("HintLight")
        self.report_totals.setWordWrap(True)
        body2.addWidget(self.report_totals)
        layout.addWidget(frame2, 1)
        return page

    # ----------------------------------------------------------- the data
    def sent_documents(self):
        """Every confirmation issued for the active client and year, flattened
        out of the saved runs so repeat runs do not double-count a party."""
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return []
        documents, seen = [], set()
        for run in self.db["runs"]:
            if run.get("client_id") != client["id"] or \
                    run.get("fy_id") != year["id"]:
                continue
            for document in run.get("documents", []):
                key = (document.get("party_name", ""),
                       document.get("category", ""))
                if key in seen:          # a later run supersedes an earlier one
                    continue
                seen.add(key)
                entry = dict(document)
                entry.setdefault("id", document.get("filename"))
                entry.setdefault("sent_at", document.get("email_at")
                                 or document.get("generated_at"))
                documents.append(entry)
        return documents

    def stored_replies(self):
        client = self.active_client()
        year = self.active_fy()
        if not client or not year:
            return []
        return [r for r in self.db.get("replies", [])
                if r.get("client_id") in (None, client["id"])
                and r.get("fy_id") in (None, year["id"])]

    def refresh_recon(self):
        documents = self.sent_documents()
        replies = self.stored_replies()
        for held in replies:    # dates recorded a day early by older builds
            if held.get("received_at"):
                held["received_at"] = local_stamp(held["received_at"])
        settings = self.db["settings"]
        mail = settings.get("mail") or {}
        self.recon_ignored = []
        self.recon_set_aside = []
        self.recon_rows, self.recon_exceptions = build_reconciliation(
            documents, replies,
            tolerance=float(settings.get("variance_tolerance",
                                         DEFAULT_TOLERANCE)),
            reminders=tuple(settings.get("reminder_days", DEFAULT_REMINDERS)),
            # the request is copied to the team, so it comes back through the
            # bridge: our own letter must never be counted as a reply
            own_addresses=(mail.get("username"), mail.get("sender")),
            ignored=self.recon_ignored, set_aside=self.recon_set_aside)
        attach_audit_status(self.recon_rows, self.audit_records())
        self.recon_summary = summarise(self.recon_rows)

        client = self.active_client()
        year = self.active_fy()
        self.recon_scope.setText(
            "%s · %s · %d confirmations issued, %d replies on record%s"
            % (client["name"] if client else "no client",
               year["year"] if year else "no year",
               len(documents), len(replies) - len(self.recon_ignored),
               ((" · %d cop%s of your own request ignored"
                 % (len(self.recon_ignored),
                    "y" if len(self.recon_ignored) == 1 else "ies"))
                if self.recon_ignored else "") +
               ((" · %d set aside" % len(self.recon_set_aside))
                if self.recon_set_aside else ""))
            if client else "Select a client to see its position")

        summary = self.recon_summary
        self._clear(self.recon_stats)
        for key, value, meta, accent in (
                ("Sent", summary["sent"], "Confirmations issued", T["accent"]),
                ("Received", summary["received"], "Replies matched", T["info"]),
                ("Matched", summary["agreed"], "No variance", T["ok"]),
                ("Mismatch", summary["variance"],
                 "Differs from books", T["err"]),
                ("Review", len(self.recon_exceptions),
                 "Replies to decide", T["warn"]),
                ("Pending", summary["pending"], "No reply yet", T["text_mute"]),
                ("Returned", summary["returned"], "Undelivered", T["err"]),
                ("Coverage", "%.1f%%" % summary["coverage_pct"],
                 "By value of balances", T["accent_hi"])):
            self.recon_stats.addWidget(stat_card(key, value, meta, accent))
        self.recon_stats.addStretch(1)
        waiting = len(self.recon_exceptions)
        self.btn_queue.setVisible(bool(waiting))
        self.btn_queue.setText(
            "%d repl%s received but not yet counted - review %s in the "
            "Exception Queue" % (waiting, "y" if waiting == 1 else "ies",
                                 "it" if waiting == 1 else "them"))
        self.refresh_bridge_note()
        self.refresh_reader_note()
        self.render_report()
        self.refresh_chips()

    def current_reports(self):
        if not hasattr(self, "recon_rows"):
            self.recon_rows, self.recon_exceptions = [], []
        return build_all_reports(
            self.recon_rows, self.recon_exceptions, self.report_context())

    def report_context(self):
        return {"reminders": tuple(self.db["settings"].get(
                    "reminder_days", DEFAULT_REMINDERS)),
                "audit_records": self.audit_records()}

    def audit_records(self):
        """Follow-up records for the confirmations of this client and year."""
        keys = {document_key(d) for d in self.sent_documents()}
        return [r for r in self.db.setdefault("audit_status", [])
                if r.get("document_id") in keys]

    def show_report(self, key):
        index = self.report_combo.findData(key)
        if index >= 0:
            self.report_combo.setCurrentIndex(index)
            self.render_report()

    def render_report(self):
        key = self.report_combo.currentData()
        report = build_report(key, getattr(self, "recon_rows", []),
                              getattr(self, "recon_exceptions", []),
                              self.report_context())
        self.current_report = report
        self.report_subtitle.setText(report["subtitle"])
        if hasattr(self, "btn_assign"):
            self.btn_assign.setVisible(key == REPORT_EXCEPTIONS)
            self.btn_audit.setVisible(key in (REPORT_COMPARISON,
                                              REPORT_REGISTER, REPORT_AUDIT))
        headings = [h for h, _k, _t in report["columns"]]
        self.report_table.clear()
        self.report_table.setColumnCount(len(headings))
        self.report_table.setHorizontalHeaderLabels(headings)
        self.report_table.setRowCount(len(report["rows"]))

        tone = {STATUS_AGREED: T["ok"], STATUS_VARIANCE: T["err"],
                STATUS_REVIEW: T["err"], STATUS_RETURNED: T["err"],
                STATUS_PENDING: T["text_mute"], STATUS_NOT_SENT: T["text_mute"]}
        for row_index, row in enumerate(report["rows"]):
            currency = row.get("currency") or "INR"
            for column_index, (_heading, field, kind) in enumerate(
                    report["columns"]):
                value = row.get(field)
                is_link = kind in ("link", "action")
                if is_link:
                    # on screen a link says what clicking it does
                    value = row.get(field + "_link", value)
                text = format_cell(value, kind, currency)
                item = cell(text,
                            align_right=kind in ("money", "number", "pct",
                                                 "pct_unit"),
                            color=(tone.get(value) if kind == "status" else
                                   T["info"] if is_link and text else None),
                            bold=kind == "status")
                if is_link and text:
                    font = item.font()
                    font.setUnderline(True)
                    item.setFont(font)
                    item.setToolTip("Click to open")
                self.report_table.setItem(row_index, column_index, item)
        self.report_table.resizeColumnsToContents()
        # fill the width rather than leaving a bare strip beside the last column
        self.report_table.horizontalHeader().setStretchLastSection(True)

        if report["totals"]:
            parts = []
            for heading, field, kind in report["columns"]:
                if field in report["totals"]:
                    parts.append("%s: %s" % (heading,
                                             format_cell(report["totals"][field],
                                                         kind, "INR")))
            self.report_totals.setText("Total — " + " · ".join(parts))
        else:
            self.report_totals.setText("")
        self.report_note.setText("%d row%s" % (len(report["rows"]),
                                               "" if len(report["rows"]) == 1
                                               else "s"))

    # ------------------------------------------------ links in the reports
    def on_report_cell(self, row_index, column_index):
        report = getattr(self, "current_report", None)
        if not report or row_index >= len(report["rows"]) or \
                column_index >= len(report["columns"]):
            return
        _heading, field, kind = report["columns"][column_index]
        row = report["rows"][row_index]
        if kind == "action" and field == "review":
            self.review_exception(row)
        elif kind == "link" and (row.get(field + "_link") or row.get(field)):
            self.open_audit_status(row)

    def reviewer_names(self):
        names = [str(a.get("name") or "").strip()
                 for a in self.db["settings"].get("auditors", [])]
        last = str(self.db["settings"].get("last_reviewer") or "").strip()
        ordered = ([last] if last else []) + [n for n in names if n != last]
        return [name for name in ordered if name]

    # ------------------------------------------- deciding a reply by hand
    def assign_reply(self, reply_id, target, amount=None, by="", note=""):
        """Record the reviewer's decision on one reply.

        target is a confirmation's id, SET_ASIDE (not a confirmation for any
        party), or "" to hand the reply back to automatic matching.  amount
        is the confirmed value the reviewer accepted.  The decision, who made
        it and when stay on the reply itself, beside the original e-mail's
        id, sender, date and link, so both can be traced later."""
        for reply in self.db.get("replies", []):
            if str(reply.get("id")) != str(reply_id):
                continue
            for field in ("assigned_to", "assigned_at", "accepted_amount",
                          "decided_by", "decided_at", "decision_note"):
                reply.pop(field, None)
            if target:
                stamp = datetime.now().isoformat(timespec="seconds")
                reply["assigned_to"] = target
                reply["assigned_at"] = stamp
                reply["decided_at"] = stamp
                reply["decided_by"] = str(by or "").strip()
                reply["decision_note"] = str(note or "").strip()
                if amount is not None and target != SET_ASIDE:
                    reply["accepted_amount"] = float(amount)
                if reply["decided_by"]:
                    self.db["settings"]["last_reviewer"] = reply["decided_by"]
            self.persist()
            self.refresh_recon()
            return True
        return False

    def assign_selected_reply(self):
        if self.report_combo.currentData() != REPORT_EXCEPTIONS:
            self.toast("Open the Exception Queue and select a reply first.",
                       "warn")
            return
        index = self.report_table.currentRow()
        queue = getattr(self, "recon_exceptions", [])
        if index < 0 or index >= len(queue):
            self.toast("Select a reply in the Exception Queue first.", "warn")
            return
        self.review_exception(queue[index])

    def review_exception(self, entry):
        """Review one reply from the queue and act on the decision."""
        if not entry.get("reply_id"):
            self.toast("That row has no reply to review.", "warn")
            return
        decision = self.choose_party_dialog(entry)
        if decision is None:
            return
        if not isinstance(decision, dict):          # a bare target
            decision = {"target": decision, "amount": entry.get("amount"),
                        "by": "", "note": ""}
        target = decision.get("target", "")
        self.assign_reply(entry["reply_id"], target,
                          decision.get("amount"), decision.get("by", ""),
                          decision.get("note", ""))
        if target == SET_ASIDE:
            self.toast("Reply set aside: it is kept on record but not "
                       "counted.", "ok")
        elif target:
            row = next((r for r in self.recon_rows
                        if r["document_id"] == target), None)
            self.toast("Accepted for %s: %s." % (
                row["party_name"] if row else "the party",
                row["status"] if row else "recorded"), "ok")
        else:
            self.toast("Reply handed back to automatic matching.", "ok")

    def choose_party_dialog(self, entry):
        """The review window for one reply.

        Shows the e-mail as received, offers the party the evidence suggests,
        and takes the reviewer's choice of party and request, the confirmed
        value, their name and a note.  Returns {target, amount, by, note},
        or None if cancelled."""
        reply = next((r for r in self.db.get("replies", [])
                      if str(r.get("id")) == str(entry.get("reply_id"))), {})
        dialog = QDialog(self)
        dialog.setWindowTitle("Review reply")
        dialog.setMinimumWidth(640)
        layout = QVBoxLayout(dialog)

        link = str(entry.get("message_link") or "")
        facts = QLabel(
            "<b>From:</b> %s %s<br><b>Received:</b> %s<br><b>Subject:</b> %s"
            "<br><b>Why it is here:</b> %s%s" % (
                xml_escape(entry.get("from_name") or ""),
                xml_escape("<%s>" % (entry.get("from_email") or "unknown")),
                xml_escape(fmt_date_long(str(entry.get("received_at")
                                             or "")[:10]) or
                           str(entry.get("received_at") or "")),
                xml_escape(entry.get("subject") or ""),
                xml_escape(entry.get("reason") or ""),
                ('<br><a href="%s" style="color: %s;">Open the original '
                 'e-mail</a>' % (xml_escape(link), T["info"]))
                if link else ""))
        facts.setWordWrap(True)
        facts.setOpenExternalLinks(True)
        layout.addWidget(facts)

        words = QPlainTextEdit()
        words.setReadOnly(True)
        words.setPlainText(strip_quoted(str(reply.get("body") or ""))
                           or "(the reply has no text of its own)")
        words.setMaximumHeight(120)
        layout.addWidget(QLabel("What the party wrote:"))
        layout.addWidget(words)

        hint = QLabel("")
        hint.setWordWrap(True)
        if entry.get("suggested_to"):
            hint.setText("<b>Suggested:</b> %s - %s." % (
                xml_escape(entry.get("suggested_party") or ""),
                xml_escape(entry.get("suggestion") or "")))
        elif entry.get("candidates"):
            hint.setText("<b>Evidence points to:</b> %s. No single party "
                         "can be suggested with confidence - choose one."
                         % xml_escape(entry["candidates"]))
        else:
            hint.setText("Nothing in the reply identifies a party - "
                         "choose one.")
        layout.addWidget(hint)

        form = QFormLayout()
        combo = QComboBox()
        combo.addItem("Choose the party and request…", None)
        for document in sorted(self.sent_documents(),
                               key=lambda d: (d.get("party_name", "").lower(),
                                              d.get("category", ""))):
            combo.addItem("%s — %s — %s — books %s" % (
                document.get("party_name", ""), document.get("category", ""),
                document.get("reference", "") or "no reference",
                fmt_amount(document.get("amount"),
                           document.get("currency") or "INR")),
                document_key(document))
        combo.addItem("Set aside — not a confirmation for any party",
                      SET_ASIDE)
        combo.addItem("Return it to automatic matching", "")
        if entry.get("suggested_to"):
            combo.setCurrentIndex(max(0, combo.findData(
                entry["suggested_to"])))
        combo.setObjectName("review_party")
        form.addRow("Belongs to", combo)

        amount = QLineEdit()
        if entry.get("amount") is not None:
            amount.setText("%.2f" % entry["amount"])
        amount.setPlaceholderText("the balance the party confirms")
        amount.setObjectName("review_amount")
        form.addRow("Confirmed value", amount)

        reviewer = QComboBox()
        reviewer.setEditable(True)
        reviewer.addItems(self.reviewer_names())
        if not self.reviewer_names():
            reviewer.setEditText("")
        reviewer.setObjectName("review_by")
        form.addRow("Reviewed by", reviewer)
        note = QLineEdit()
        note.setObjectName("review_note")
        note.setPlaceholderText("optional - why this party, or why set aside")
        form.addRow("Note", note)
        layout.addLayout(form)

        problem = QLabel("")
        problem.setObjectName("review_problem")
        problem.setWordWrap(True)
        problem.setStyleSheet("color: %s;" % T["err"])
        layout.addWidget(problem)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        accept = buttons.addButton("Accept",
                                   QDialogButtonBox.ButtonRole.AcceptRole)
        accept.setObjectName("review_accept")
        layout.addWidget(buttons)
        decision = {}

        def try_accept():
            target = combo.currentData()
            if target is None:
                problem.setText("Choose the party and request this reply "
                                "belongs to, or set it aside.")
                return
            value = None
            if target and target != SET_ASIDE:
                value = parse_amount(amount.text())[0] \
                    if amount.text().strip() else None
                if value is None:
                    problem.setText("Enter the confirmed value as a number, "
                                    "for example 2311786 or 23,11,786.00.")
                    return
            name = reviewer.currentText().strip()
            if target != "" and not name:
                problem.setText("Enter the name of the person reviewing "
                                "this reply.")
                return
            decision.update(target=target, amount=value, by=name,
                            note=note.text().strip())
            dialog.accept()

        accept.clicked.connect(try_accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted or not decision:
            return None
        return decision

    # ------------------------------------------------ audit-status records
    def audit_selected_row(self):
        report = getattr(self, "current_report", None)
        index = self.report_table.currentRow()
        if not report or index < 0 or index >= len(report["rows"]):
            self.toast("Select a confirmation in the table first.", "warn")
            return
        self.open_audit_status(report["rows"][index])

    def save_audit_status(self, row, state, nature, owner, notes, by=""):
        """Create the follow-up record for a confirmation, or update it.

        The record is tied to the party, the request sent and the reply
        received, and every change is added to its history."""
        records = self.db.setdefault("audit_status", [])
        record = audit_record_for(records, row.get("document_id"))
        stamp = datetime.now().isoformat(timespec="seconds")
        if record is None:
            record = {"id": new_id(), "created_at": stamp,
                      "created_by": str(by or owner or "").strip(),
                      "history": []}
            client, year = self.active_client(), self.active_fy()
            record["client_id"] = client["id"] if client else None
            record["fy_id"] = year["id"] if year else None
            records.append(record)
        record.update(audit_snapshot(row))
        record.update(state=state, nature=nature,
                      owner=str(owner or "").strip(),
                      notes=str(notes or "").strip(), updated_at=stamp)
        record["history"].append({
            "at": stamp, "by": str(by or owner or "").strip(),
            "state": state, "nature": nature,
            "confirmation_status": row.get("status", ""),
            "notes": str(notes or "").strip()})
        self.persist()
        self.refresh_recon()
        return record

    def open_audit_status(self, row):
        # a row of the audit report is the record itself; find the live row
        live = next((r for r in getattr(self, "recon_rows", [])
                     if r["document_id"] == row.get("document_id")), None)
        if live is None:
            self.toast("That confirmation is no longer on record.", "warn")
            return
        record = audit_record_for(self.audit_records(), live["document_id"])
        if record is None and not needs_audit_status(live):
            self.toast("An audit-status record is opened for a Mismatch or "
                       "a reply that Needs Review. %s is %s."
                       % (live["party_name"], live["status"]), "info")
            return
        result = self.audit_status_dialog(live, record)
        if result is None:
            return
        self.save_audit_status(live, result["state"], result["nature"],
                               result["owner"], result["notes"],
                               result["owner"])
        self.toast("Audit status saved for %s: %s."
                   % (live["party_name"], result["state"]), "ok")

    def audit_status_dialog(self, row, record):
        """Create or edit the follow-up record.  Returns {state, nature,
        owner, notes} or None if cancelled."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Audit status - %s" % row["party_name"])
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        money = lambda value: (fmt_amount(value, row.get("currency") or "INR")
                               if value is not None else "-")
        link = str(row.get("message_link") or "")
        facts = QLabel(
            "<b>Party:</b> %s (%s)<br>"
            "<b>Request:</b> reference %s, sent %s to %s<br>"
            "<b>Reply:</b> %s<br>"
            "<b>As per books:</b> %s &nbsp; <b>Confirmed:</b> %s &nbsp; "
            "<b>Variance:</b> %s<br><b>Confirmation status:</b> %s<br>%s%s"
            % (xml_escape(row["party_name"]), xml_escape(row["category"]),
               xml_escape(row.get("reference") or "-"),
               xml_escape(fmt_date_long(str(row.get("sent_at") or "")[:10])
                          or "-"),
               xml_escape(row.get("email") or "-"),
               xml_escape(("from %s, received %s%s" % (
                   row.get("reply_from") or "unknown sender",
                   fmt_date_long(str(row.get("received_at") or "")[:10])
                   or "date unknown",
                   " (%d replies on record)" % row["replies_count"]
                   if row.get("replies_count", 0) > 1 else ""))
                   if row.get("replies_count") else "none counted yet"),
               xml_escape(money(row.get("books_amount"))),
               xml_escape(money(row.get("confirmed_amount"))),
               xml_escape(money(row.get("variance"))),
               xml_escape(row.get("status", "")),
               xml_escape(row.get("note") or ""),
               ('<br><a href="%s" style="color: %s;">Open the original '
                'e-mail</a>' % (xml_escape(link), T["info"]))
               if link else ""))
        facts.setWordWrap(True)
        facts.setOpenExternalLinks(True)
        layout.addWidget(facts)

        form = QFormLayout()
        state = QComboBox()
        state.addItems(AUDIT_STATES)
        nature = QComboBox()
        nature.addItems(AUDIT_NATURES)
        owner = QComboBox()
        owner.setEditable(True)
        owner.addItems(self.reviewer_names())
        notes = QPlainTextEdit()
        notes.setPlaceholderText(
            "What was found, what was asked of the client or the party, "
            "what evidence was obtained, and the conclusion")
        notes.setMinimumHeight(110)
        if record:
            state.setCurrentIndex(max(0, state.findText(
                record.get("state", ""))))
            nature.setCurrentIndex(max(0, nature.findText(
                record.get("nature", ""))))
            owner.setEditText(record.get("owner", ""))
            notes.setPlainText(record.get("notes", ""))
        elif row.get("status") == STATUS_REVIEW:
            nature.setCurrentIndex(nature.findText(
                "Reply could not be matched or read"))
        state.setObjectName("audit_state")
        nature.setObjectName("audit_nature")
        owner.setObjectName("audit_owner")
        notes.setObjectName("audit_notes")
        form.addRow("Follow-up", state)
        form.addRow("Nature of difference", nature)
        form.addRow("Owner", owner)
        form.addRow("Notes", notes)
        layout.addLayout(form)

        if record and record.get("history"):
            past = QLabel("<b>History</b><br>" + "<br>".join(
                "%s - %s - %s" % (
                    xml_escape(str(h.get("at", "")).replace("T", " ")),
                    xml_escape(h.get("by") or "unnamed"),
                    xml_escape(h.get("state", "")))
                for h in record["history"][-6:]))
            past.setWordWrap(True)
            layout.addWidget(past)

        problem = QLabel("")
        problem.setObjectName("audit_problem")
        problem.setStyleSheet("color: %s;" % T["err"])
        layout.addWidget(problem)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        save = buttons.addButton("Save record",
                                 QDialogButtonBox.ButtonRole.AcceptRole)
        save.setObjectName("audit_save")
        layout.addWidget(buttons)
        result = {}

        def try_save():
            if not owner.currentText().strip():
                problem.setText("Enter who owns this follow-up.")
                return
            result.update(state=state.currentText(),
                          nature=nature.currentText(),
                          owner=owner.currentText().strip(),
                          notes=notes.toPlainText().strip())
            dialog.accept()

        save.clicked.connect(try_save)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted or not result:
            return None
        return result

    # --------------------------------------------------------- the exports
    def report_heading(self):
        client = self.active_client()
        year = self.active_fy()
        summary = getattr(self, "recon_summary", None) or summarise([])
        facts = [("Client", client["name"] if client else "—"),
                 ("Financial year", year["year"] if year else "—"),
                 ("Confirmations as at",
                  fmt_date_long(fy_as_at(year)) if year else "—"),
                 ("Type of audit", fy_audit_type(year) if year else "—"),
                 ("Audit firm", self.db["settings"].get("firm_name", "")),
                 ("Prepared on", fmt_date_long(date.today())),
                 ("Coverage by value", "%.2f%%" % summary["coverage_pct"])]
        return {"title": "Balance confirmation — reconciliation reports",
                "author": self.db["settings"].get("firm_name", ""),
                "facts": facts}

    def _export_path(self, extension, label):
        client = self.active_client()
        year = self.active_fy()
        base = sanitize_filename("%s - Balance confirmation %s - %s"
                                 % (client["name"] if client else "Client",
                                    label, year["year"] if year else ""))
        start = os.path.join(self.db["settings"].get("output_folder")
                             or os.path.expanduser("~"), base + extension)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save the reports", start,
            ("Excel workbook (*.xlsx)" if extension == ".xlsx"
             else "PDF document (*.pdf)"))
        return path

    def export_reports_excel(self):
        if not getattr(self, "recon_rows", None):
            self.toast("Nothing to report yet — send some confirmations "
                       "first.", "warn")
            return
        path = self._export_path(".xlsx", "reports")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            write_reports_xlsx(path, self.current_reports(),
                               self.report_heading())
            QApplication.restoreOverrideCursor()
            self.toast("Workbook written to %s" % path, "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.toast("The workbook could not be written: %s" % exc, "err")

    def export_reports_pdf(self):
        if not getattr(self, "recon_rows", None):
            self.toast("Nothing to report yet — send some confirmations "
                       "first.", "warn")
            return
        path = self._export_path(".pdf", "reports")
        if not path:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            write_reports_pdf(path, self.current_reports(),
                              self.report_heading())
            QApplication.restoreOverrideCursor()
            self.toast("PDF written to %s" % path, "ok")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self.toast("The PDF could not be written: %s" % exc, "err")

    def import_replies(self):
        """Load replies from a JSON file: a list of reply records, or the
        object the Gmail bridge writes ({"replies": [...]})."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import replies", os.path.expanduser("~"),
            "JSON files (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:
            self.toast("That file is not valid JSON: %s" % exc, "err")
            return
        incoming = payload.get("replies") if isinstance(payload, dict) \
            else payload
        if not isinstance(incoming, list):
            self.toast("That file does not hold a list of replies.", "err")
            return
        added, seen = self.merge_replies(incoming)
        self.toast("%d new repl%s imported (%d already on record)."
                   % (added, "y" if added == 1 else "ies", seen - added), "ok")

    def merge_replies(self, incoming):
        """Add replies that are not already on record.  Returns the number
        added and the number offered, so both the file import and the bridge
        sync can report the same way."""
        client = self.active_client()
        year = self.active_fy()
        store = self.db.setdefault("replies", [])
        for held in store:      # dates recorded a day early by older builds
            if held.get("received_at"):
                held["received_at"] = local_stamp(held["received_at"])
        known = {r.get("id") for r in store}
        added = offered = 0
        for reply in incoming:
            if not isinstance(reply, dict):
                continue
            offered += 1
            reply = dict(reply)
            reply.setdefault("id", new_id())
            if reply.get("received_at"):
                reply["received_at"] = local_stamp(reply["received_at"])
            if reply["id"] in known:            # never count a reply twice
                # ...but learn what is attached, if the bridge now says so
                if reply.get("files"):
                    for held in store:
                        if held.get("id") == reply["id"] and \
                                not held.get("files"):
                            held["files"] = list(reply["files"])
                continue
            reply.setdefault("client_id", client["id"] if client else None)
            reply.setdefault("fy_id", year["id"] if year else None)
            store.append(reply)
            known.add(reply["id"])
            added += 1
        self.persist()
        self.refresh_recon()
        return added, offered

    # ------------------------------------------------- the always-on bridge
    def sync_bridge(self, quiet=False):
        """Read the feed published by the Gmail Apps Script.  The script
        collects replies on Google's servers while this computer is off; this
        is the one call that brings them across."""
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        if not url:
            if not quiet:
                self.toast("No bridge address saved.  Settings > Gmail bridge.",
                           "warn")
            return
        if not url.lower().startswith("https://"):
            if not quiet:
                self.toast("The bridge address must begin with https://",
                           "err")
            return
        if getattr(self, "bridge_thread", None):      # one read at a time
            if not quiet:
                self.toast("The bridge is already being read.", "warn")
            return

        if not quiet:
            self.toast("Reading the bridge…", "info")
        self.bridge_thread = QThread(self)
        self.bridge_worker = BridgeWorker(url)
        self.bridge_worker.moveToThread(self.bridge_thread)
        self.bridge_thread.started.connect(self.bridge_worker.run)
        self.bridge_worker.finished.connect(
            lambda replies, error: self.on_bridge_finished(replies, error,
                                                           quiet))
        self.bridge_thread.start()

    def on_bridge_finished(self, replies, error, quiet):
        thread = getattr(self, "bridge_thread", None)
        if thread:
            thread.quit()
            thread.wait(3000)
        self.bridge_thread = None
        self.bridge_worker = None

        if error:
            if not quiet:
                self.toast("Bridge: %s" % error, "err")
            return
        added, offered = self.merge_replies(replies)
        self.db["settings"]["bridge_last_sync"] = \
            datetime.now().isoformat(timespec="seconds")
        self.persist()
        self.refresh_bridge_note()
        self.refresh_bridge_status()
        # every reply that brought a PDF or a scan is now opened and read
        self.read_reply_documents(quiet=True)
        if quiet and not added:
            return
        self.toast("Bridge synced: %d new repl%s (%d already on record)."
                   % (added, "y" if added == 1 else "ies", offered - added),
                   "ok")

    def refresh_bridge_note(self):
        if not hasattr(self, "bridge_note"):
            return
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        stamp = self.db["settings"].get("bridge_last_sync") or ""
        if not url:
            self.bridge_note.setText("Gmail bridge not connected")
        elif stamp:
            self.bridge_note.setText("Bridge last read %s" % stamp_text(stamp))
        else:
            self.bridge_note.setText("Bridge connected, not yet read")

    # ------------------------------------------- reading the reply's document
    def unread_document_replies(self, retry=False):
        """Replies of this engagement whose PDF or scan has not been read."""
        return [r for r in self.stored_replies()
                if reply_has_unread_files(r) and
                (retry or not r.get("files_error"))]

    def refresh_reader_note(self, text=None):
        if not hasattr(self, "reader_note"):
            return
        if text is None:
            ready, words = reader_status()
            waiting = len(self.unread_document_replies(retry=True))
            read = sum(1 for r in self.stored_replies() if r.get("files_read"))
            if ready:
                text = "%s. %d document%s read, %d waiting." % (
                    words, read, "" if read == 1 else "s", waiting)
            else:
                text = words
        self.reader_note.setText(text)

    def read_reply_documents(self, quiet=False, retry=False):
        """Open every unread PDF or scan and take the confirmed amount from
        it.  Runs after each sync, and on demand from the button."""
        if getattr(self, "reader_thread", None):
            if not quiet:
                self.toast("Documents are already being read.", "warn")
            return
        waiting = self.unread_document_replies(retry=retry)
        if not waiting:
            if not quiet:
                self.toast("No reply has a PDF or scan left to read.", "info")
            self.refresh_reader_note()
            return
        ready, words = reader_status()
        if not ready:
            self.refresh_reader_note(words)
            if not quiet:
                self.toast(words, "warn")
            return
        url = (self.db["settings"].get("bridge_feed_url") or "").strip()
        if not url.lower().startswith("https://"):
            if not quiet:
                self.toast("The documents are fetched through the Gmail "
                           "bridge, which is not connected. Use \"Add a reply "
                           "from a PDF or scan\" for a file you hold.", "warn")
            return
        self.btn_read_docs.setEnabled(False)
        self.refresh_reader_note("Reading %d document%s…" % (
            len(waiting), "" if len(waiting) == 1 else "s"))
        self.reader_thread = QThread(self)
        self.reader_worker = DocumentWorker(url, [r["id"] for r in waiting])
        self.reader_worker.moveToThread(self.reader_thread)
        self.reader_thread.started.connect(self.reader_worker.run)
        self.reader_worker.progress.connect(self.on_document_read)
        self.reader_worker.finished.connect(self.on_documents_finished)
        self.reader_thread.start()

    def store_reading(self, reply, entries, error=""):
        """Keep what was read with the reply it belongs to."""
        names = {entry["name"] for entry in entries}
        kept = [a for a in (reply.get("attachments") or [])
                if not (a.get("read_by") == "application" and
                        a.get("name") in names)]
        # what this computer read goes first: it is the fuller reading
        reply["attachments"] = [e for e in entries if e.get("text")] + kept
        problems = [e["name"] + ": " + e["error"] for e in entries
                    if e.get("error") and not e.get("text")]
        if error:
            problems.append(error)
        reply["files_error"] = "; ".join(problems)
        reply["files_read"] = any(e.get("text") for e in entries)
        reply["files_read_at"] = datetime.now().isoformat(timespec="seconds")

    def on_document_read(self, reply_id, entries, error, number, total):
        for reply in self.db.get("replies", []):
            if reply.get("id") == reply_id:
                self.store_reading(reply, entries, error)
                break
        self.refresh_reader_note("Read %d of %d…" % (number, total))

    def on_documents_finished(self, done, failed):
        thread = getattr(self, "reader_thread", None)
        if thread:
            thread.quit()
            thread.wait(5000)
        self.reader_thread = None
        self.reader_worker = None
        self.btn_read_docs.setEnabled(True)
        self.persist()
        self.refresh_recon()
        text = "%d document%s read" % (done, "" if done == 1 else "s")
        if failed:
            text += "; %d could not be read (see the exception queue)" % failed
        self.toast(text + ".", "warn" if failed else "ok")

    def add_reply_from_file(self, path=None):
        """A confirmation that did not come through the mailbox: the file is
        read here and matched to its party by reference code or name."""
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "The confirmation received", "",
                "PDFs and scans (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp)")
        if not path:
            return None
        ready, words = reader_status()
        if not ready:
            self.toast(words, "warn")
            return None
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except Exception as exc:
            self.toast("The file could not be opened: %s" % exc, "err")
            return None
        name = os.path.basename(path)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            reading = read_document(data, name)
        finally:
            QApplication.restoreOverrideCursor()
        if not reading.get("text"):
            self.toast("Nothing could be read from %s: %s"
                       % (name, reading.get("error") or "no text found"), "err")
            return None
        client, year = self.active_client(), self.active_fy()
        reply = {
            "id": "file-" + new_id(),
            "received_at": date.today().isoformat(),
            "from_email": "", "from_name": "",
            "subject": "Received as a file: " + name,
            "body": "", "thread_id": "", "in_reply_to": "",
            "reference": find_reference(reading["text"]) or "",
            "bounced": False, "manual": True,
            "client_id": client["id"] if client else None,
            "fy_id": year["id"] if year else None,
            "files": [name], "files_read": True, "files_error": "",
            "attachments": [attachment_entry(name, reading)],
        }
        self.db.setdefault("replies", []).append(reply)
        self.persist()
        self.refresh_recon()
        row = next((r for r in self.recon_rows
                    if r.get("extract_source") == name or
                    (reply["reference"] and
                     r.get("reference") == reply["reference"] and
                     r.get("received_at"))), None)
        if row:
            self.toast("%s read (%s) and matched to %s: %s."
                       % (name, reading["method"], row["party_name"],
                          row["status"]), "ok")
        else:
            self.toast("%s was read but could not be matched to a party; it "
                       "is in the exception queue." % name, "warn")
        return reply
