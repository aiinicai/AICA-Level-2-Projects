"""AI Assistant provider configuration panel, embedded in the Settings tab.

Handles provider/model selection and API key storage (via the OS credential
store -- see :mod:`core.ai_provider`) so every AI Assistant feature across
the app reads a single, consistently-configured provider.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.ai_provider import (
    AIProvider,
    AIProviderError,
    AIProviderKind,
    AIRequest,
    DEFAULT_MODELS,
    delete_api_key,
    is_configured,
    ping_ollama,
    save_api_key,
)


class ApiKeyDialog(QDialog):
    def __init__(self, provider_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Set API Key — {provider_name}")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Enter your {provider_name} API key. It will be stored using the Windows "
            "Credential Manager, never in a plain-text settings file."
        ))
        self.edit_key = QLineEdit()
        self.edit_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.edit_key)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def key(self) -> str:
        return self.edit_key.text().strip()


class AISettingsWidget(QGroupBox):
    def __init__(self, ctx, parent=None):
        super().__init__("AI Assistant", parent)
        self.ctx = ctx
        self._build_ui()
        self._load_from_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "AI features (classification, summarization, structured extraction, Ask Document) are "
            "opt-in and only run when you click an AI Assistant action. Ollama runs entirely on this "
            "computer with no API key and no data leaving your machine; the cloud providers send the "
            "document text you submit to that provider's servers."
        ))
        for lbl in layout.findChildren(QLabel):
            lbl.setWordWrap(True)

        form = QFormLayout()
        self.combo_provider = QComboBox()
        self.combo_provider.addItems([p.value for p in AIProviderKind])
        form.addRow("Provider:", self.combo_provider)

        self.edit_model = QLineEdit()
        form.addRow("Model:", self.edit_model)

        self.edit_ollama_url = QLineEdit()
        form.addRow("Ollama server URL:", self.edit_ollama_url)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.btn_set_key = QPushButton("Set / Update API Key")
        self.btn_remove_key = QPushButton("Remove API Key")
        self.btn_remove_key.setObjectName("DangerButton")
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.setObjectName("SecondaryButton")
        button_row.addWidget(self.btn_set_key)
        button_row.addWidget(self.btn_remove_key)
        button_row.addWidget(self.btn_test)
        layout.addLayout(button_row)

        self.lbl_status = QLabel()
        layout.addWidget(self.lbl_status)

        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)
        self.btn_set_key.clicked.connect(self._set_key)
        self.btn_remove_key.clicked.connect(self._remove_key)
        self.btn_test.clicked.connect(self._test_connection)

    def _current_provider_kind(self) -> AIProviderKind:
        return AIProviderKind(self.combo_provider.currentText())

    def _on_provider_changed(self, _text: str) -> None:
        kind = self._current_provider_kind()
        is_ollama = kind == AIProviderKind.OLLAMA
        self.edit_ollama_url.setEnabled(is_ollama)
        self.btn_set_key.setEnabled(not is_ollama)
        self.btn_remove_key.setEnabled(not is_ollama)
        if not self.edit_model.text().strip():
            self.edit_model.setPlaceholderText(DEFAULT_MODELS[kind])
        self._refresh_status()

    def _refresh_status(self) -> None:
        kind = self._current_provider_kind()
        if kind == AIProviderKind.OLLAMA:
            reachable = ping_ollama(self.edit_ollama_url.text().strip() or "http://localhost:11434")
            self.lbl_status.setText(
                "Status: Ollama server reachable." if reachable else "Status: Ollama server not reachable (is it running?)"
            )
        else:
            configured = is_configured(kind)
            self.lbl_status.setText("Status: API key configured." if configured else "Status: Not configured -- no API key set.")

    def _set_key(self) -> None:
        kind = self._current_provider_kind()
        dlg = ApiKeyDialog(kind.value, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.key():
            save_api_key(kind, dlg.key())
            self._refresh_status()
            QMessageBox.information(self, "Saved", f"API key saved for {kind.value}.")

    def _remove_key(self) -> None:
        kind = self._current_provider_kind()
        delete_api_key(kind)
        self._refresh_status()

    def _test_connection(self) -> None:
        kind = self._current_provider_kind()
        model = self.edit_model.text().strip() or DEFAULT_MODELS[kind]
        provider = AIProvider(kind, model=model, ollama_base_url=self.edit_ollama_url.text().strip() or "http://localhost:11434")
        try:
            response = provider.complete(AIRequest(system_prompt="Reply with exactly one word: OK.", user_prompt="Ping.", max_tokens=10))
            QMessageBox.information(self, "Connection OK", f"{kind.value} responded: {response.text.strip()!r}")
        except AIProviderError as exc:
            QMessageBox.critical(self, "Connection Failed", str(exc))
        self._refresh_status()

    def _load_from_settings(self) -> None:
        s = self.ctx.config.settings
        self.combo_provider.setCurrentText(s.ai_provider)
        self.edit_model.setText(s.ai_model)
        self.edit_ollama_url.setText(s.ai_ollama_base_url)
        self._on_provider_changed(s.ai_provider)

    def save_to_settings(self) -> None:
        s = self.ctx.config.settings
        s.ai_provider = self.combo_provider.currentText()
        s.ai_model = self.edit_model.text().strip()
        s.ai_ollama_base_url = self.edit_ollama_url.text().strip() or "http://localhost:11434"

    def get_configured_provider(self) -> AIProvider:
        """Build an AIProvider from current (possibly unsaved) form state."""
        kind = self._current_provider_kind()
        model = self.edit_model.text().strip() or DEFAULT_MODELS[kind]
        return AIProvider(kind, model=model, ollama_base_url=self.edit_ollama_url.text().strip() or "http://localhost:11434")
