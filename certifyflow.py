"""CertifyFlow & Saral Bridge - desktop app (Python / tkinter, no extra packages needed)."""
import datetime as dt
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

import cf_core as core

STATUS_LABEL = {"draft": "Draft", "pending_approval": "Pending approval",
                "approved": "Approved", "rejected": "Rejected"}


def open_path(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        messagebox.showinfo("Open", f"Saved at:\n{path}\n\n({e})")


class App:
    def __init__(self, root):
        self.root = root
        self.store = core.Store()
        root.title("CertifyFlow & Saral Bridge")
        root.geometry("1180x760")
        root.minsize(1000, 640)
        try:
            ttk.Style().theme_use("vista" if sys.platform.startswith("win") else "clam")
        except tk.TclError:
            pass
        self._q = queue.Queue()
        self.status = tk.StringVar(value=f"Data file: {core.STORAGE_FILE}")

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        tabs = [("Certificate Studio", self.build_studio), ("Party Master", self.build_parties),
                ("Approval Queue", self.build_approvals), ("Email Dispatch", self.build_email),
                ("Saral Invoicing", self.build_invoicing), ("Settings", self.build_settings)]
        self.frames = {}
        for name, builder in tabs:
            f = ttk.Frame(self.nb, padding=10)
            self.nb.add(f, text=name)
            self.frames[name] = f
            builder(f)
        ttk.Label(root, textvariable=self.status, anchor="w", relief="sunken").pack(fill="x", side="bottom")
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()
        root.after(150, self._poll)

    # ---------------------------------------------------------- utilities
    def say(self, msg):
        self.status.set(msg)

    def run_bg(self, fn, ok, label="Working..."):
        self.say(label)
        self.root.config(cursor="watch")

        def work():
            try:
                self._q.put((ok, fn(), None))
            except Exception as e:  # noqa
                self._q.put((ok, None, e))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        try:
            while True:
                ok, res, err = self._q.get_nowait()
                self.root.config(cursor="")
                if err:
                    self.say(f"Error: {err}")
                    messagebox.showerror("Error", str(err))
                else:
                    ok(res)
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    def safe(self, fn):
        def wrapper(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:  # noqa
                traceback.print_exc()
                self.say(f"Error: {e}")
                messagebox.showerror("Error", str(e))
        return wrapper

    @staticmethod
    def tree(parent, cols, widths, height=8):
        fr = ttk.Frame(parent)
        t = ttk.Treeview(fr, columns=[c[0] for c in cols], show="headings", height=height, selectmode="browse")
        for (cid, title), w in zip(cols, widths):
            t.heading(cid, text=title)
            t.column(cid, width=w, anchor="w")
        sb = ttk.Scrollbar(fr, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return fr, t

    @staticmethod
    def field(parent, label, var, row, col=0, width=28, show=None):
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="e", padx=(0, 6), pady=3)
        e = ttk.Entry(parent, textvariable=var, width=width, show=show)
        e.grid(row=row, column=col * 2 + 1, sticky="we", pady=3, padx=(0, 12))
        return e

    def ca_email(self):
        return self.store["caDetails"].get("commonEmail") or "caamruta21@gmail.com"

    def refresh_all(self):
        for fn in (self.refresh_studio_lists, self.refresh_parties, self.refresh_approvals,
                   self.refresh_email, self.refresh_invoicing):
            try:
                fn()
            except Exception:
                traceback.print_exc()

    # ------------------------------------------------- CERTIFICATE STUDIO
    def build_studio(self, f):
        f.columnconfigure(1, weight=1)
        f.rowconfigure(0, weight=1)
        left = ttk.Frame(f)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        right = ttk.LabelFrame(f, text="Live certificate preview", padding=6)
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(left, text="Client / Party").pack(anchor="w")
        self.st_party = ttk.Combobox(left, state="readonly", width=46)
        self.st_party.pack(fill="x", pady=(0, 8))
        ttk.Label(left, text="Certificate template").pack(anchor="w")
        self.st_tmpl = ttk.Combobox(left, state="readonly", width=46,
                                    values=[f"{t['code']} - {t['title']}" for t in core.TEMPLATES])
        self.st_tmpl.pack(fill="x", pady=(0, 4))
        self.st_tmpl_desc = ttk.Label(left, wraplength=330, foreground="#555")
        self.st_tmpl_desc.pack(anchor="w", pady=(0, 6))
        self.st_fields_frame = ttk.LabelFrame(left, text="Certificate details", padding=6)
        self.st_fields_frame.pack(fill="x")
        self.st_vars = {}
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="Save as Word (.docx)", command=self.safe(self.studio_save)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Send Word file to CA email", command=self.safe(self.studio_send)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Submit for approval", command=self.safe(self.studio_submit)).pack(fill="x", pady=2)
        self.st_msg = ttk.Label(left, wraplength=330, foreground="#0a6")
        self.st_msg.pack(anchor="w")

        self.st_preview = tk.Text(right, wrap="word", font=("Cambria", 11), padx=14, pady=10)
        sb = ttk.Scrollbar(right, command=self.st_preview.yview)
        self.st_preview.configure(yscrollcommand=sb.set, state="disabled")
        self.st_preview.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.st_party.bind("<<ComboboxSelected>>", lambda e: self.studio_preview())
        self.st_tmpl.bind("<<ComboboxSelected>>", lambda e: self.studio_template_changed())
        self.st_tmpl.current(0)
        self.studio_template_changed()

    def refresh_studio_lists(self):
        parties = self.store["parties"]
        cur = self.st_party.current()
        self.st_party["values"] = [f"{p['name']}  ({p['pan']})" for p in parties]
        if parties:
            self.st_party.current(cur if 0 <= cur < len(parties) else 0)
        self.studio_preview()

    def studio_template_changed(self):
        t = core.TEMPLATES[max(self.st_tmpl.current(), 0)]
        self.st_tmpl_desc.config(text=t["description"])
        for w in self.st_fields_frame.winfo_children():
            w.destroy()
        self.st_vars = {}
        self.st_fields_frame.columnconfigure(0, weight=1)
        for i, fd in enumerate(t["fields"]):
            ttk.Label(self.st_fields_frame, text=fd["label"]).grid(row=i * 2, column=0, sticky="w")
            var = tk.StringVar(value=fd.get("defaultValue", ""))
            var.trace_add("write", lambda *a: self.studio_preview())
            if fd.get("type") == "select" and fd.get("options"):
                w = ttk.Combobox(self.st_fields_frame, textvariable=var, values=fd["options"], state="readonly")
            else:
                w = ttk.Entry(self.st_fields_frame, textvariable=var, width=46)
            w.grid(row=i * 2 + 1, column=0, sticky="we", pady=(0, 4))
            self.st_vars[fd["id"]] = var
        self.studio_preview()

    def studio_current(self):
        parties = self.store["parties"]
        i = self.st_party.current()
        if i < 0 or i >= len(parties):
            raise ValueError("Please add/select a party first (Party Master tab).")
        t = core.TEMPLATES[self.st_tmpl.current()]
        return t, parties[i], {k: v.get() for k, v in self.st_vars.items()}

    def studio_preview(self):
        try:
            t, p, vals = self.studio_current()
            text = f"{t['title'].upper()}\n{t['subtitle']}\n\nRef: CERT-{dt.date.today().year}-XXXX\n\n"
            text += core.render_body(t, p, vals, self.store["caDetails"])
        except Exception as e:  # noqa
            text = str(e)
        self.st_preview.config(state="normal")
        self.st_preview.delete("1.0", "end")
        self.st_preview.insert("1.0", text)
        self.st_preview.config(state="disabled")

    def studio_save(self):
        t, p, vals = self.studio_current()
        cert, data, fn = core.make_certificate(self.store, t, p, vals, "draft")
        path = core.save_docx_file(data, fn)
        self.st_msg.config(text=f"Saved: {path}\nCertificate {cert['certificateNumber']} added as Draft.")
        self.say("Word certificate generated.")
        self.refresh_all()
        if messagebox.askyesno("Word file created", f"{fn}\n\nOpen it now?"):
            open_path(path)

    def studio_send(self):
        t, p, vals = self.studio_current()
        cert, data, fn = core.make_certificate(self.store, t, p, vals, "draft")
        subj, body = core.default_email(self.store, cert, "studio")
        to = self.ca_email()

        def done(res):
            self.st_msg.config(text=f"Sent to {to} ({res['mode']}). Ref {cert['certificateNumber']}")
            self.say("Email dispatched.")
            self.refresh_all()
            if res.get("note"):
                messagebox.showinfo("Email", res["note"])
        self.run_bg(lambda: core.dispatch_certificate(self.store, cert, to, subj, body), done, "Sending email...")

    def studio_submit(self):
        t, p, vals = self.studio_current()
        cert, _, _ = core.make_certificate(self.store, t, p, vals, "pending_approval")
        self.say(f"{cert['certificateNumber']} submitted for approval.")
        self.refresh_all()
        self.nb.select(self.frames["Approval Queue"])

    # ------------------------------------------------------- PARTY MASTER
    PARTY_FORM = [("name", "Legal name"), ("tradeName", "Trade name"), ("pan", "PAN"), ("gstin", "GSTIN"),
                  ("stateCode", "State code"), ("stateName", "State"), ("address", "Address"),
                  ("email", "Email"), ("phone", "Phone"), ("contactPerson", "Contact person"),
                  ("saralLedgerCode", "Saral ledger code"), ("defaultFee", "Default fee (₹)")]

    def build_parties(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)
        cols = [("name", "Party"), ("pan", "PAN"), ("gstin", "GSTIN"), ("state", "State"),
                ("email", "Email"), ("fee", "Default fee")]
        fr, self.pt_tree = self.tree(f, cols, [300, 110, 160, 110, 220, 90], 11)
        fr.grid(row=0, column=0, sticky="nsew")
        self.pt_tree.bind("<<TreeviewSelect>>", lambda e: self.party_selected())
        form = ttk.LabelFrame(f, text="Party details", padding=8)
        form.grid(row=1, column=0, sticky="ew", pady=8)
        self.pt_vars = {}
        for i, (k, lab) in enumerate(self.PARTY_FORM):
            self.pt_vars[k] = tk.StringVar()
            self.field(form, lab, self.pt_vars[k], i // 3, i % 3, 26)
        b = ttk.Frame(f)
        b.grid(row=2, column=0, sticky="w")
        for text, cmd in [("Add as new", self.party_add), ("Update selected", self.party_update),
                          ("Delete selected", self.party_delete), ("Clear form", self.party_clear),
                          ("Import CSV...", self.party_import), ("Export CSV...", self.party_export)]:
            ttk.Button(b, text=text, command=self.safe(cmd)).pack(side="left", padx=(0, 6))

    def refresh_parties(self):
        self.pt_tree.delete(*self.pt_tree.get_children())
        for p in self.store["parties"]:
            self.pt_tree.insert("", "end", iid=p["id"], values=(
                p["name"], p["pan"], p.get("gstin", ""), p.get("stateName", ""),
                p.get("email", ""), core.fmt_in(p.get("defaultFee") or 0)))

    def party_selected(self):
        sel = self.pt_tree.selection()
        p = self.store.party(sel[0]) if sel else None
        if p:
            for k, var in self.pt_vars.items():
                var.set(str(p.get(k, "") if p.get(k) is not None else ""))

    def party_from_form(self, base=None):
        d = {k: v.get().strip() for k, v in self.pt_vars.items()}
        if not d["name"] or not d["pan"]:
            raise ValueError("Party name and PAN are required.")
        d["pan"] = d["pan"].upper()
        d["gstin"] = d["gstin"].upper()
        if not d["stateCode"] and len(d["gstin"]) >= 2:
            d["stateCode"] = d["gstin"][:2]
        d["defaultFee"] = core.pf(d["defaultFee"], 15000) or 15000
        p = dict(base or {})
        p.update(d)
        return p

    def party_add(self):
        p = self.party_from_form()
        p["id"] = core.uid("pty")
        self.store["parties"].append(p)
        self.store.save()
        self.refresh_all()
        self.say(f"Added {p['name']}.")

    def party_update(self):
        sel = self.pt_tree.selection()
        if not sel:
            raise ValueError("Select a party in the list first.")
        old = self.store.party(sel[0])
        old.update(self.party_from_form(old))
        self.store.save()
        self.refresh_all()
        self.say(f"Updated {old['name']}.")

    def party_delete(self):
        sel = self.pt_tree.selection()
        if sel and messagebox.askyesno("Delete", "Delete the selected party?"):
            self.store.data["parties"] = [p for p in self.store["parties"] if p["id"] != sel[0]]
            self.store.save()
            self.refresh_all()

    def party_clear(self):
        for v in self.pt_vars.values():
            v.set("")

    def party_import(self):
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            new = core.parties_from_csv(path)
            ids = {p["id"] for p in self.store["parties"]}
            self.store["parties"].extend(p for p in new if p["id"] not in ids)
            self.store.save()
            self.refresh_all()
            self.say(f"Imported {len(new)} parties.")

    def party_export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="parties.csv")
        if path:
            core.parties_to_csv(path, self.store["parties"])
            self.say(f"Exported to {path}")

    # ----------------------------------------------------- APPROVAL QUEUE
    def build_approvals(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)
        top = ttk.Frame(f)
        top.grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(top, text="Show:").pack(side="left")
        self.ap_filter = ttk.Combobox(top, state="readonly", width=20,
                                      values=["All", "Pending approval", "Approved", "Draft", "Rejected"])
        self.ap_filter.current(0)
        self.ap_filter.pack(side="left", padx=6)
        self.ap_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_approvals())
        cols = [("no", "Certificate"), ("party", "Party"), ("tmpl", "Template"), ("status", "Status"),
                ("udin", "UDIN"), ("mail", "Email"), ("inv", "Invoice")]
        fr, self.ap_tree = self.tree(f, cols, [130, 260, 250, 120, 150, 80, 110], 12)
        fr.grid(row=1, column=0, sticky="nsew")
        self.ap_tree.bind("<<TreeviewSelect>>", lambda e: self.approval_selected())
        box = ttk.LabelFrame(f, text="Review selected certificate", padding=8)
        box.grid(row=2, column=0, sticky="ew", pady=8)
        box.columnconfigure(1, weight=1)
        self.ap_udin, self.ap_notes = tk.StringVar(), tk.StringVar()
        self.field(box, "UDIN (blank = auto)", self.ap_udin, 0, 0, 30)
        self.field(box, "Review notes", self.ap_notes, 1, 0, 60)
        b = ttk.Frame(box)
        b.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        for text, cmd in [("Approve", self.ap_approve), ("Reject", self.ap_reject),
                          ("Submit draft for approval", self.ap_submit),
                          ("Send to CA email", self.ap_send), ("Open Word file", self.ap_open),
                          ("Delete", self.ap_delete)]:
            ttk.Button(b, text=text, command=self.safe(cmd)).pack(side="left", padx=(0, 6))

    def ap_current(self):
        sel = self.ap_tree.selection()
        c = self.store.cert(sel[0]) if sel else None
        if not c:
            raise ValueError("Select a certificate in the list first.")
        return c

    def refresh_approvals(self):
        keep = self.ap_tree.selection()
        flt = {"All": None, "Pending approval": "pending_approval", "Approved": "approved",
               "Draft": "draft", "Rejected": "rejected"}[self.ap_filter.get() or "All"]
        self.ap_tree.delete(*self.ap_tree.get_children())
        for c in self.store["certificates"]:
            if flt and c["status"] != flt:
                continue
            self.ap_tree.insert("", "end", iid=c["id"], values=(
                c["certificateNumber"], c["partyName"], c["templateTitle"],
                STATUS_LABEL.get(c["status"], c["status"]), c.get("udin", ""),
                "Sent" if c.get("emailStatus") == "sent" else "-", c.get("invoiceNumber", "-")))
        if keep and self.ap_tree.exists(keep[0]):
            self.ap_tree.selection_set(keep[0])

    def approval_selected(self):
        sel = self.ap_tree.selection()
        c = self.store.cert(sel[0]) if sel else None
        if c:
            self.ap_udin.set(c.get("udin", ""))
            self.ap_notes.set(c.get("approvalNotes", ""))

    def ap_approve(self):
        c = self.ap_current()
        udin = core.approve(self.store, c, self.ap_udin.get(), self.ap_notes.get())
        self.say(f"{c['certificateNumber']} approved. UDIN {udin}. You can now invoice it.")
        self.refresh_all()

    def ap_reject(self):
        c = self.ap_current()
        core.reject(self.store, c, self.ap_notes.get())
        self.say(f"{c['certificateNumber']} rejected.")
        self.refresh_all()

    def ap_submit(self):
        c = self.ap_current()
        if c["status"] == "draft":
            c["status"] = "pending_approval"
            self.store.save()
            self.refresh_all()

    def ap_send(self):
        c = self.ap_current()
        subj, body = core.default_email(self.store, c, "dispatch")
        to = self.ca_email()

        def done(res):
            self.say(f"Dispatched to {to} ({res['mode']}).")
            self.refresh_all()
            if res.get("note"):
                messagebox.showinfo("Email", res["note"])
        self.run_bg(lambda: core.dispatch_certificate(self.store, c, to, subj, body), done, "Sending email...")

    def ap_open(self):
        c = self.ap_current()
        path = core.save_docx_file(core.regenerate_docx(self.store, c), core.cert_filename(c))
        open_path(path)

    def ap_delete(self):
        c = self.ap_current()
        if messagebox.askyesno("Delete", f"Delete certificate {c['certificateNumber']}?"):
            self.store["certificates"].remove(c)
            self.store.save()
            self.refresh_all()

    # ------------------------------------------------------ EMAIL DISPATCH
    def build_email(self, f):
        f.columnconfigure(1, weight=1)
        f.rowconfigure(5, weight=1)
        ttk.Label(f, text="Certificate").grid(row=0, column=0, sticky="e", padx=6, pady=3)
        self.em_cert = ttk.Combobox(f, state="readonly", width=70)
        self.em_cert.grid(row=0, column=1, sticky="w")
        self.em_cert.bind("<<ComboboxSelected>>", lambda e: self.email_fill())
        self.em_to, self.em_subj = tk.StringVar(), tk.StringVar()
        ttk.Label(f, text="To (CA email)").grid(row=1, column=0, sticky="e", padx=6, pady=3)
        ttk.Entry(f, textvariable=self.em_to, width=50).grid(row=1, column=1, sticky="w")
        ttk.Label(f, text="Subject").grid(row=2, column=0, sticky="e", padx=6, pady=3)
        ttk.Entry(f, textvariable=self.em_subj, width=90).grid(row=2, column=1, sticky="we")
        ttk.Label(f, text="Message").grid(row=3, column=0, sticky="ne", padx=6, pady=3)
        self.em_body = tk.Text(f, height=9, wrap="word")
        self.em_body.grid(row=3, column=1, sticky="we")
        ttk.Button(f, text="Send certificate (.docx attached)", command=self.safe(self.email_send)).grid(
            row=4, column=1, sticky="w", pady=8)
        fr, self.em_log = self.tree(
            f, [("time", "Time"), ("no", "Certificate"), ("party", "Party"), ("to", "Sent to"),
                ("status", "Status")], [160, 130, 260, 230, 100], 8)
        fr.grid(row=5, column=0, columnspan=2, sticky="nsew")
        self.em_ids = []

    def refresh_email(self):
        certs = self.store["certificates"]
        self.em_ids = [c["id"] for c in certs]
        cur = self.em_cert.current()
        self.em_cert["values"] = [f"{c['certificateNumber']} - {c['partyName']} ({STATUS_LABEL.get(c['status'])})" for c in certs]
        if certs:
            self.em_cert.current(cur if 0 <= cur < len(certs) else 0)
            if not self.em_subj.get():
                self.email_fill()
        self.em_log.delete(*self.em_log.get_children())
        for i, l in enumerate(self.store["emailLogs"]):
            self.em_log.insert("", "end", iid=f"{l['id']}-{i}", values=(
                l["timestamp"][:19].replace("T", " "), l["certificateNumber"], l["partyName"],
                l["recipientEmail"], l["status"]))

    def email_fill(self):
        i = self.em_cert.current()
        if i < 0:
            return
        c = self.store.cert(self.em_ids[i])
        subj, body = core.default_email(self.store, c, "dispatch")
        self.em_to.set(self.ca_email())
        self.em_subj.set(subj)
        self.em_body.delete("1.0", "end")
        self.em_body.insert("1.0", body)

    def email_send(self):
        i = self.em_cert.current()
        if i < 0:
            raise ValueError("Select a certificate first.")
        c = self.store.cert(self.em_ids[i])
        to, subj, body = self.em_to.get().strip(), self.em_subj.get(), self.em_body.get("1.0", "end").strip()

        def done(res):
            self.say(f"Email dispatched to {to} ({res['mode']}).")
            self.refresh_all()
            if res.get("note"):
                messagebox.showinfo("Email", res["note"])
        self.run_bg(lambda: core.dispatch_certificate(self.store, c, to, subj, body), done, "Sending email...")

    # ------------------------------------------------------ SARAL INVOICING
    def build_invoicing(self, f):
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)
        f.rowconfigure(4, weight=1)
        form = ttk.LabelFrame(f, text="New Saral sales invoice (approved certificates only)", padding=8)
        form.grid(row=0, column=0, sticky="ew")
        ttk.Label(form, text="Certificate").grid(row=0, column=0, sticky="e", padx=6, pady=3)
        self.iv_cert = ttk.Combobox(form, state="readonly", width=70)
        self.iv_cert.grid(row=0, column=1, columnspan=5, sticky="w")
        self.iv_cert.bind("<<ComboboxSelected>>", lambda e: self.invoice_cert_changed())
        self.iv_amt, self.iv_sac = tk.StringVar(value="15000"), tk.StringVar(value="998222")
        self.iv_desc = tk.StringVar(value="Chartered Accountant Certification Services")
        self.iv_date = tk.StringVar(value=dt.date.today().isoformat())
        self.field(form, "Taxable amount (₹)", self.iv_amt, 1, 0, 16)
        self.field(form, "SAC code", self.iv_sac, 1, 1, 12)
        self.field(form, "Invoice date", self.iv_date, 1, 2, 14)
        self.field(form, "Service description", self.iv_desc, 2, 0, 50)
        ttk.Label(form, text="Post to Saral login").grid(row=3, column=0, sticky="e", padx=(0, 6), pady=3)
        self.iv_prof = ttk.Combobox(form, state="readonly", width=40)
        self.iv_prof.grid(row=3, column=1, sticky="w")
        for v in (self.iv_amt,):
            v.trace_add("write", lambda *a: self.invoice_summary())
        self.iv_sum = ttk.Label(f, font=("Segoe UI", 10, "bold"))
        self.iv_sum.grid(row=1, column=0, sticky="w", pady=6)
        ttk.Button(f, text="Post invoice to Saral (generate SQL voucher)",
                   command=self.safe(self.invoice_post)).grid(row=2, column=0, sticky="w")
        fr, self.iv_tree = self.tree(
            f, [("no", "Invoice"), ("date", "Date"), ("party", "Party"), ("taxable", "Taxable ₹"),
                ("tax", "GST ₹"), ("total", "Total ₹"), ("voucher", "Saral voucher"), ("login", "Saral login")],
            [110, 85, 240, 90, 90, 90, 130, 140], 6)
        fr.grid(row=3, column=0, sticky="nsew", pady=(8, 4))
        self.iv_tree.bind("<<TreeviewSelect>>", lambda e: self.invoice_selected())
        sq = ttk.LabelFrame(f, text="Saral SQL script for selected invoice", padding=4)
        sq.grid(row=4, column=0, sticky="nsew")
        self.iv_sql = tk.Text(sq, height=8, font=("Consolas", 9), wrap="none")
        self.iv_sql.pack(fill="both", expand=True)
        ttk.Button(sq, text="Copy SQL", command=self.safe(self.invoice_copy)).pack(anchor="w", pady=3)
        self.iv_ids = []

    def approved_certs(self):
        return [c for c in self.store["certificates"] if c["status"] == "approved"]

    def refresh_invoicing(self):
        certs = self.approved_certs()
        self.iv_ids = [c["id"] for c in certs]
        cur = self.iv_cert.current()
        self.iv_cert["values"] = [
            f"{c['certificateNumber']} - {c['partyName']} (UDIN: {c.get('udin') or 'N/A'})"
            + ("  [invoiced]" if c.get("invoiceGenerated") else "") for c in certs]
        if certs:
            first = cur < 0
            self.iv_cert.current(cur if 0 <= cur < len(certs) else 0)
            if first:
                self.invoice_cert_changed()
        else:
            self.iv_cert.set("")
        self.iv_tree.delete(*self.iv_tree.get_children())
        for i in self.store["invoices"]:
            self.iv_tree.insert("", "end", iid=i["id"], values=(
                i["invoiceNumber"], i["invoiceDate"], i["partyName"], core.fmt_in(i["taxableAmount"]),
                core.fmt_in(i["cgstAmount"] + i["sgstAmount"] + i["igstAmount"]),
                core.fmt_in(i["totalAmount"]), i.get("saralVoucherNo", ""), i.get("saralProfile", "")))
        names = [x["name"] for x in core.saral_profiles(self.store)]
        keep = self.iv_prof.get()
        self.iv_prof["values"] = names
        self.iv_prof.set(keep if keep in names else (names[0] if names else ""))
        self.invoice_summary()

    def invoice_cert(self):
        i = self.iv_cert.current()
        return self.store.cert(self.iv_ids[i]) if 0 <= i < len(self.iv_ids) else None

    def invoice_cert_changed(self):
        c = self.invoice_cert()
        p = self.store.party(c["partyId"]) if c else None
        if p and p.get("defaultFee"):
            self.iv_amt.set(str(int(p["defaultFee"]) if float(p["defaultFee"]) == int(p["defaultFee"]) else p["defaultFee"]))
        self.invoice_summary()

    def invoice_tax(self):
        c = self.invoice_cert()
        if not c:
            return None
        p = self.store.party(c["partyId"]) or {}
        home = self.store["caDetails"].get("stateCode") or "27"
        ps = (c.get("partyGstin") or "")[:2] or p.get("stateCode") or "27"
        return core.calc_tax(core.pf(self.iv_amt.get()), home, ps), ps

    def invoice_summary(self):
        r = self.invoice_tax()
        if not r:
            self.iv_sum.config(text="No approved certificates yet - approve one in the Approval Queue.")
            return
        t, ps = r
        if t["isInterState"]:
            tax = f"Inter-state (party state {ps}): IGST 18% = ₹{core.fmt_in(t['igstAmount'])}"
        else:
            tax = f"Intra-state: CGST 9% = ₹{core.fmt_in(t['cgstAmount'])} + SGST 9% = ₹{core.fmt_in(t['sgstAmount'])}"
        self.iv_sum.config(text=f"{tax}   |   Invoice total: ₹{core.fmt_in(t['total'])}")

    def invoice_post(self):
        c = self.invoice_cert()
        inv = core.post_invoice(self.store, c, core.pf(self.iv_amt.get()), self.iv_sac.get().strip() or "998222",
                                self.iv_desc.get().strip(), self.iv_date.get().strip(), self.iv_prof.get())
        self.say(f"Invoice {inv['invoiceNumber']} created for Saral login '{inv['saralProfile']}'.")
        self.refresh_all()
        self.iv_tree.selection_set(inv["id"])
        messagebox.showinfo("Invoice posted", f"Invoice {inv['invoiceNumber']} created for {inv['partyName']}.\n"
                            f"Total: ₹{core.fmt_in(inv['totalAmount'])}\nSaral login: {inv['saralProfile']}\n\n"
                            "SQL script generated (direct database write is not enabled yet).")

    def invoice_selected(self):
        sel = self.iv_tree.selection()
        inv = next((i for i in self.store["invoices"] if sel and i["id"] == sel[0]), None)
        self.iv_sql.delete("1.0", "end")
        if inv:
            self.iv_sql.insert("1.0", inv.get("sqlScript", ""))

    def invoice_copy(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.iv_sql.get("1.0", "end").strip())
        self.say("SQL copied to clipboard.")

    # ------------------------------------------------------------ SETTINGS
    def build_settings(self, f):
        self.sv = {"caDetails": {}, "smtpConfig": {}}
        groups = [
            ("caDetails", "CA firm details", [
                ("firmName", "Firm name"), ("caName", "CA / Partner name"), ("membershipNumber", "Membership no."),
                ("firmRegNumber", "Firm reg. no."), ("commonEmail", "Common CA email"), ("phone", "Phone"),
                ("address", "Address"), ("city", "City"), ("state", "State"), ("stateCode", "State code"),
                ("gstin", "Firm GSTIN"), ("pan", "Firm PAN")]),
            ("smtpConfig", "Email (SMTP) - leave password blank to simulate", [
                ("host", "SMTP host"), ("port", "Port"), ("user", "User / email"),
                ("password", "Password (Gmail: app password)"), ("senderName", "Sender name")]),
        ]
        for gi, (key, title, fields) in enumerate(groups):
            lf = ttk.LabelFrame(f, text=title, padding=8)
            lf.grid(row=gi // 2, column=gi % 2, sticky="nsew", padx=6, pady=6)
            for i, (k, lab) in enumerate(fields):
                var = tk.StringVar()
                self.sv[key][k] = var
                self.field(lf, lab, var, i, 0, 34, show="*" if k == "password" else None)
        self.sv_secure = tk.BooleanVar()
        self.sv_auto = tk.BooleanVar()
        ttk.Checkbutton(f, text="SMTP uses SSL (port 465)", variable=self.sv_secure).grid(row=1, column=1, sticky="sw", padx=10)
        b = ttk.Frame(f)
        b.grid(row=3, column=0, columnspan=2, sticky="w", pady=8, padx=6)
        self.build_saral_profiles(f)
        for text, cmd in [("Save settings", self.settings_save), ("Test SMTP login", self.settings_test_smtp),
                          ("Backup data...", self.settings_backup),
                          ("Restore backup...", self.settings_restore), ("Open data folder", lambda: open_path(core.DATA_DIR))]:
            ttk.Button(b, text=text, command=self.safe(cmd)).pack(side="left", padx=(0, 6))
        self.settings_load()

    SP_FIELDS = [("name", "Login name (your label)"), ("host", "Server / host"), ("port", "Port"),
                 ("database", "Saral database"), ("username", "SQL username"), ("password", "SQL password")]

    def build_saral_profiles(self, f):
        lf = ttk.LabelFrame(f, text="Saral Accounts logins - add one per company/login", padding=8)
        lf.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
        self.sp_vars = {k: tk.StringVar() for k, _ in self.SP_FIELDS}
        self.sp_win = tk.BooleanVar()
        ttk.Label(lf, text="Saved logins").grid(row=0, column=0, sticky="e", padx=(0, 6))
        self.sp_combo = ttk.Combobox(lf, state="readonly", width=34)
        self.sp_combo.grid(row=0, column=1, sticky="w")
        self.sp_combo.bind("<<ComboboxSelected>>", lambda e: self.sp_selected())
        for i, (k, lab) in enumerate(self.SP_FIELDS):
            self.field(lf, lab, self.sp_vars[k], 1 + i // 3, i % 3, 26, show="*" if k == "password" else None)
        ttk.Checkbutton(lf, text="Use Windows login instead of SQL username/password",
                        variable=self.sp_win).grid(row=3, column=0, columnspan=4, sticky="w")
        b = ttk.Frame(lf)
        b.grid(row=4, column=0, columnspan=6, sticky="w", pady=(6, 0))
        for text, cmd in [("New login", self.sp_new), ("Save this login", self.sp_save),
                          ("Delete login", self.sp_delete), ("Test login", self.sp_test),
                          ("Export structure for support...", self.sp_export)]:
            ttk.Button(b, text=text, command=self.safe(cmd)).pack(side="left", padx=(0, 6))
        self.sp_refresh()

    def sp_refresh(self, select=None):
        names = [x["name"] for x in core.saral_profiles(self.store)]
        self.sp_combo["values"] = names
        pick = select if select in names else (self.sp_combo.get() if self.sp_combo.get() in names else (names[0] if names else ""))
        self.sp_combo.set(pick)
        self.sp_selected()

    def sp_selected(self):
        p = next((x for x in core.saral_profiles(self.store) if x["name"] == self.sp_combo.get()), None)
        for k, var in self.sp_vars.items():
            var.set(str((p or {}).get(k, "") or ""))
        self.sp_win.set(bool((p or {}).get("windowsAuth")))

    def sp_form(self):
        d = {k: v.get().strip() if k != "password" else v.get() for k, v in self.sp_vars.items()}
        d["windowsAuth"] = bool(self.sp_win.get())
        if not d["name"] or not d["database"]:
            raise ValueError("Login name and Saral database are required.")
        return d

    def sp_new(self):
        for v in self.sp_vars.values():
            v.set("")
        self.sp_vars["host"].set("localhost")
        self.sp_vars["port"].set("1433")
        self.sp_win.set(False)

    def sp_save(self):
        d = self.sp_form()
        profs = core.saral_profiles(self.store)
        old = self.sp_combo.get()
        target = next((x for x in profs if x["name"] == old), None) if old else None
        if target is None or (target["name"] != d["name"] and any(x["name"] == d["name"] for x in profs)):
            target = next((x for x in profs if x["name"] == d["name"]), None)
        if target is None:
            profs.append(d)
        else:
            if target["name"] != d["name"]:
                for inv in self.store["invoices"]:
                    if inv.get("saralProfile") == target["name"]:
                        inv["saralProfile"] = d["name"]
            target.update(d)
        self.store.save()
        self.sp_refresh(d["name"])
        self.refresh_all()
        self.say(f"Saral login '{d['name']}' saved.")

    def sp_delete(self):
        name = self.sp_combo.get()
        profs = core.saral_profiles(self.store)
        if len(profs) <= 1:
            raise ValueError("Keep at least one Saral login.")
        if messagebox.askyesno("Delete", f"Delete Saral login '{name}'?"):
            self.store.data["saralProfiles"] = [x for x in profs if x["name"] != name]
            self.store.save()
            self.sp_refresh()
            self.refresh_all()

    def sp_test(self):
        d = self.sp_form()
        self.run_bg(lambda: core.saral_test(d), lambda m: (self.say("Saral login OK."), messagebox.showinfo("Saral", m)),
                    "Testing Saral login...")

    def sp_export(self):
        d = self.sp_form()
        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            initialfile=f"saral_structure_{d['name'].replace(' ', '_')}.txt")
        if path:
            self.run_bg(lambda: core.saral_export_structure(d, path),
                        lambda m: (self.say(m), messagebox.showinfo("Saral", m)), "Reading Saral structure...")

    def settings_load(self):
        for key, vars_ in self.sv.items():
            for k, var in vars_.items():
                var.set(str(self.store[key].get(k, "") or ""))
        self.sv_secure.set(bool(self.store["smtpConfig"].get("secure")))

    def settings_collect(self):
        for key, vars_ in self.sv.items():
            for k, var in vars_.items():
                self.store[key][k] = var.get().strip() if k != "password" else var.get()
        self.store["smtpConfig"]["secure"] = bool(self.sv_secure.get())

    def settings_save(self):
        self.settings_collect()
        self.store.save()
        self.say("Settings saved.")
        self.refresh_all()
        messagebox.showinfo("Settings", "Settings saved to data/app_storage.json")

    def settings_test_smtp(self):
        self.settings_collect()
        self.run_bg(lambda: core.test_smtp(self.store["smtpConfig"]),
                    lambda m: (self.say(m), messagebox.showinfo("SMTP", m)), "Testing SMTP login...")

    def settings_backup(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            initialfile=f"certifyflow_backup_{dt.date.today().isoformat()}.json")
        if path:
            self.store.backup_to(path)
            self.say(f"Backup saved to {path}")

    def settings_restore(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path and messagebox.askyesno("Restore", "Replace ALL current data with this backup?"):
            self.store.restore_from(path)
            self.settings_load()
            self.refresh_all()
            self.say("Backup restored.")


def main():
    root = tk.Tk()
    try:
        App(root)
    except Exception:
        err = traceback.format_exc()
        messagebox.showerror("CertifyFlow failed to start", err)
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
