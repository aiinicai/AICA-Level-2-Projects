import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDialog,QDialogButtonBox,QFormLayout,QGroupBox,QHBoxLayout,QLabel,QLineEdit,QListWidget,QListWidgetItem,QMessageBox,QPlainTextEdit,QSpinBox,QVBoxLayout)

from app.data_sources.manager import get_credential, set_credential
from app.services.gemini import get_gemini_api_key, set_gemini_api_key


class RuleDialog(QDialog):
    def __init__(self,db,engine,rule=None,parent=None):
        super().__init__(parent)
        self.db,self.engine,self.rule=db,engine,rule or {}
        self.setWindowTitle("Notification rule · Finstock EventScope")
        self.resize(570,660)
        layout=QVBoxLayout(self)
        intro=QLabel("Choose the events you want. Blank filters mean any value.\nFilters combine; comma-separated values within a filter are alternatives.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form=QFormLayout()
        self.name=QLineEdit(self.rule.get("name","My event alerts"))
        form.addRow("Rule name",self.name)
        self.enabled=QCheckBox("Enabled")
        self.enabled.setChecked(bool(self.rule.get("enabled",True)))
        form.addRow("",self.enabled)
        self.fields={}
        for key,title in (("countries","Countries / regions"),("companies","Companies, symbols or ISINs"),("categories","Categories"),("authorities","Authorities"),("importance","Importance"),("kinds","Event types")):
            edit=QLineEdit(", ".join(self.rule.get("filters",{}).get(key,[])))
            edit.setPlaceholderText({"importance":"Low, Medium, High, Unknown","kinds":"Economic, Corporate, Regulatory"}.get(key,"Any (or comma-separated exact names)"))
            self.fields[key]=edit
            form.addRow(title,edit)
        self.watchlists=QListWidget()
        self.watchlists.setMaximumHeight(75)
        for row in db.rows("SELECT * FROM watchlists ORDER BY name"):
            item=QListWidgetItem(row["name"])
            item.setData(Qt.UserRole,row["id"])
            item.setCheckState(Qt.Checked if row["id"] in self.rule.get("filters",{}).get("watchlists",[]) else Qt.Unchecked)
            self.watchlists.addItem(item)
        form.addRow("Watchlists",self.watchlists)
        self.offsets=QLineEdit(", ".join(str(v/60).rstrip("0").rstrip(".") if v%60 else str(v//60) for v in self.rule.get("offsets",[900,3600])))
        self.offsets.setPlaceholderText("15, 30, 60, 1440 (minutes)")
        form.addRow("Advance intervals in minutes",self.offsets)
        self.grace=QSpinBox()
        self.grace.setRange(0,1440)
        self.grace.setValue(int(self.rule.get("grace_seconds",300))//60)
        self.grace.setSuffix(" min")
        form.addRow("Catch-up grace period",self.grace)
        self.triggers={}
        for key,title in (("reminder","Advance reminders"),("new","Newly detected publications"),("updated","Material updates / schedule changes")):
            checkbox=QCheckBox(title)
            checkbox.setChecked(key in self.rule.get("triggers",["reminder","new"]))
            self.triggers[key]=checkbox
            form.addRow("",checkbox)
        self.samples=QCheckBox("Include clearly labelled sample events")
        self.samples.setChecked(bool(self.rule.get("include_samples",False)))
        form.addRow("",self.samples)
        layout.addLayout(form)
        layout.addWidget(QLabel("Channel: Windows desktop. Monitoring continues in the tray.\nFully quitting or shutting down stops monitoring; missed reminders are recorded."))
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        try:
            filters={key:[v.strip() for v in edit.text().split(",") if v.strip()] for key,edit in self.fields.items()}
            filters["watchlists"]=[self.watchlists.item(i).data(Qt.UserRole) for i in range(self.watchlists.count()) if self.watchlists.item(i).checkState()==Qt.Checked]
            offsets=[int(float(v.strip())*60) for v in self.offsets.text().split(",") if v.strip()]
            self.engine.save_rule(self.name.text(),filters,offsets,[k for k,v in self.triggers.items() if v.isChecked()],self.enabled.isChecked(),self.grace.value()*60,self.samples.isChecked(),self.rule.get("id"))
            self.accept()
        except (ValueError,TypeError) as exc:
            QMessageBox.warning(self,"Rule not saved",str(exc))


class SourceDialog(QDialog):
    def __init__(self,db,source,parent=None):
        super().__init__(parent)
        self.db,self.source=db,source
        self.setWindowTitle("Configure data source")
        self.resize(620,420)
        layout=QVBoxLayout(self)
        title=QLabel(source["name"])
        title.setStyleSheet("font-size:20px;font-weight:600")
        layout.addWidget(title)
        note=QLabel(source["rights_note"])
        note.setWordWrap(True)
        layout.addWidget(note)
        link=QLabel(f'<a style="color:#78AFFF" href="{source["terms_url"]}">Source documentation and usage terms ↗</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)
        form=QFormLayout()
        self.enabled=QCheckBox("Enable automatic checks")
        self.enabled.setChecked(bool(source["enabled"]))
        self.enabled.setEnabled(source["adapter"]!="import")
        form.addRow("",self.enabled)
        self.interval=QSpinBox()
        self.interval.setRange(1,86400)
        self.interval.setValue(max(1, source["interval_seconds"]))
        self.interval.setSuffix(" sec")
        form.addRow("Refresh interval",self.interval)
        self.credential=QLineEdit()
        existing_cred = get_credential(source["id"]) or self.db.setting(f"{source['id']}_api_key") or source["config"].get("api_key", "")
        if existing_cred:
            self.credential.setText(str(existing_cred))
        self.credential.setEchoMode(QLineEdit.Password)
        self.credential.setPlaceholderText("Enter API key (or leave blank to retain saved)")
        self.countries=QLineEdit(source["config"].get("countries","india"))
        self.back=QSpinBox(); self.back.setRange(0,180); self.back.setValue(source["config"].get("days_back",7))
        self.ahead=QSpinBox(); self.ahead.setRange(1,180); self.ahead.setValue(source["config"].get("days_ahead",30))
        if source["adapter"] in ("trading_economics", "finnhub"):
            form.addRow("API credential / token",self.credential)
            if source["adapter"]=="trading_economics":
                form.addRow("Provider country names",self.countries)
            form.addRow("Days to reconcile in past",self.back)
            form.addRow("Days ahead",self.ahead)
        layout.addLayout(form)
        self.permission=QCheckBox("My intended access and local storage are permitted by the source terms")
        self.permission.setChecked(bool(source["config"].get("usage_confirmed", True)))
        self.permission.setVisible(source["adapter"]!="import")
        layout.addWidget(self.permission)
        status=QLabel(f"Status: {source['status']}\nLast result: {source['last_error'] or 'No error recorded'}")
        status.setWordWrap(True)
        layout.addWidget(status)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        key_text = self.credential.text().strip().strip('"\'')
        if key_text:
            self.permission.setChecked(True)
        if self.enabled.isChecked() and not self.permission.isChecked():
            QMessageBox.warning(self,"Source access","Review the source usage terms before enabling access.")
            return
        config=dict(self.source["config"])
        config["usage_confirmed"]=self.permission.isChecked()
        try:
            if self.source["adapter"] in ("trading_economics", "finnhub"):
                if self.source["adapter"]=="trading_economics":
                    if not self.countries.text().strip():
                        raise ValueError("Enter at least one provider country name")
                    config.update(countries=self.countries.text().strip())
                config.update(days_back=self.back.value(),days_ahead=self.ahead.value())
                if key_text:
                    config["api_key"] = key_text
                    self.db.set_setting(f"{self.source['id']}_api_key", key_text)
                    try:
                        set_credential(self.source["id"], key_text)
                    except Exception:
                        pass
            range_changed=any(config.get(k)!=self.source["config"].get(k) for k in ("countries","days_back","days_ahead"))
            new_status = "Connected" if self.enabled.isChecked() and self.source["last_success"] else ("Stale" if self.enabled.isChecked() else "Disabled")
            self.db.execute(
                "UPDATE data_sources SET enabled=?,interval_seconds=?,config=?,next_attempt=NULL,status=?,last_error='',checkpoint=? WHERE id=?",
                (int(self.enabled.isChecked()), self.interval.value(), json.dumps(config), new_status, None if range_changed else self.source["checkpoint"], self.source["id"])
            )
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self,"Source not saved",f"Could not save configuration: {exc}")


class ImportDialog(QDialog):
    def __init__(self,db,path,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import event records")
        self.resize(520,280)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel(Path(path).name))
        layout.addWidget(QLabel("CSV / JSON imports use the documented event schema.\nImports preserve revisions and do not trigger new-publication alerts."))
        self.source=QComboBox()
        for row in db.rows("SELECT id,name FROM data_sources WHERE adapter='import' ORDER BY name"):
            self.source.addItem(row["name"],row["id"])
        index=self.source.findData("manual")
        self.source.setCurrentIndex(index)
        layout.addWidget(self.source)
        self.samples=QCheckBox("Treat all imported records as synthetic samples")
        self.samples.setChecked("synthetic" in Path(path).name.lower())
        layout.addWidget(self.samples)
        self.rights=QCheckBox("I have permission to import and store these source records")
        layout.addWidget(self.rights)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.confirm); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def confirm(self):
        if not self.samples.isChecked() and not self.rights.isChecked():
            QMessageBox.warning(self,"Import permission","Confirm permitted use, or identify the dataset as synthetic samples.")
            return
        self.accept()


class ApiKeyDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("API Keys & Live Integration · Finstock EventScope")
        self.resize(580, 420)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("API & Live Data Configuration")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #38BDF8;")
        layout.addWidget(header)

        sub = QLabel("Configure your free API tokens for real-time market data and Gemini AI intelligence. Keys are safely stored locally and synchronized with API.txt.")
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        layout.addWidget(sub)

        form = QFormLayout()
        form.setSpacing(12)

        # 1. Finnhub API Key
        self.finnhub_key = QLineEdit()
        self.finnhub_key.setEchoMode(QLineEdit.Password)
        curr_finnhub = get_credential("finnhub") or db.setting("finnhub_api_key") or ""
        self.finnhub_key.setText(str(curr_finnhub))
        self.finnhub_key.setPlaceholderText("Paste Finnhub API Key (from finnhub.io)")
        form.addRow("Finnhub API Key:", self.finnhub_key)
        
        finnhub_link = QLabel('<a style="color:#60A5FA; text-decoration:none;" href="https://finnhub.io/register">Get free Finnhub Key at finnhub.io ↗</a> (Corporate earnings, IPOs & global calendars)')
        finnhub_link.setOpenExternalLinks(True)
        form.addRow("", finnhub_link)

        # 2. Gemini AI API Key
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        curr_gemini = get_gemini_api_key(db)
        self.gemini_key.setText(str(curr_gemini))
        self.gemini_key.setPlaceholderText("Paste Google Gemini API Key (starts with AIzaSy...)")
        form.addRow("Google Gemini API Key:", self.gemini_key)

        gemini_link = QLabel('<a style="color:#60A5FA; text-decoration:none;" href="https://aistudio.google.com/">Get free Gemini Key at aistudio.google.com ↗</a> (1.5 Flash - 15 RPM / 1M TPM free)')
        gemini_link.setOpenExternalLinks(True)
        form.addRow("", gemini_link)

        layout.addLayout(form)

        info_box = QLabel("💡 <b>Tip</b>: You can also paste your keys directly into <code>API.txt</code> in the application folder. EventScope automatically reads both at runtime.")
        info_box.setWordWrap(True)
        info_box.setStyleSheet("background: #0D1C33; border: 1px solid #1E3A63; border-radius: 6px; padding: 10px; font-size: 11px; color: #CBD5E1;")
        layout.addWidget(info_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self):
        f_key = self.finnhub_key.text().strip().strip('"\'')
        g_key = self.gemini_key.text().strip().strip('"\'')

        if f_key:
            self.db.set_setting("finnhub_api_key", f_key)
            try:
                set_credential("finnhub", f_key)
            except Exception:
                pass
            try:
                rows = self.db.rows("SELECT config FROM data_sources WHERE id='finnhub'")
                cfg = json.loads(rows[0]["config"]) if rows and rows[0]["config"] else {}
                cfg["usage_confirmed"] = True
                cfg["api_key"] = f_key
                self.db.execute("UPDATE data_sources SET enabled=1, status='Connected', last_error='', config=? WHERE id='finnhub'", (json.dumps(cfg),))
            except Exception:
                pass

        if g_key:
            set_gemini_api_key(self.db, g_key)

        self.accept()
