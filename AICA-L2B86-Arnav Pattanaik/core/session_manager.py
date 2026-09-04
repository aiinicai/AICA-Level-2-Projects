"""
Session Manager — handles auto-save, auto-restore, and clearing of compiled audit sessions.
"""

import json
from pathlib import Path
from dataclasses import asdict
import pandas as pd

from core.ingestion import DivisionLoadLog
from gui.app_state import AppState, UploadedFileEntry, AppSettings


def get_session_dir() -> Path:
    session_dir = Path.home() / ".discom_audit_compiler_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_session(state: AppState) -> bool:
    """Save current compiled state and DataFrame to local session cache."""
    if state.compiled_df is None or not state.is_compiled:
        return False

    try:
        session_dir = get_session_dir()
        df_path = session_dir / "compiled_data.pkl"
        meta_path = session_dir / "metadata.json"

        # Save DataFrame fast via pickle
        state.compiled_df.to_pickle(df_path)

        # Save metadata as JSON
        uploaded_files_data = [asdict(f) for f in state.uploaded_files]
        load_logs_data = [asdict(l) for l in state.load_logs]
        settings_data = asdict(state.settings)

        meta = {
            "billing_month": state.billing_month,
            "billing_year": state.billing_year,
            "compile_timestamp": state.compile_timestamp,
            "total_rows_read": state.total_rows_read,
            "total_rows_rejected": state.total_rows_rejected,
            "has_warnings_or_errors": state.has_warnings_or_errors,
            "warnings_acknowledged": state.warnings_acknowledged,
            "uploaded_files": uploaded_files_data,
            "load_logs": load_logs_data,
            "settings": settings_data,
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return True
    except Exception as exc:
        print(f"[SessionManager] Warning: failed to save session cache: {exc}")
        return False


def load_session(state: AppState) -> bool:
    """Load cached session if available into AppState."""
    try:
        session_dir = get_session_dir()
        df_path = session_dir / "compiled_data.pkl"
        meta_path = session_dir / "metadata.json"

        if not df_path.exists() or not meta_path.exists():
            return False

        df = pd.read_pickle(df_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        state.billing_month = meta.get("billing_month", "August")
        state.billing_year = meta.get("billing_year", 2026)
        state.compile_timestamp = meta.get("compile_timestamp")
        state.total_rows_read = meta.get("total_rows_read", len(df))
        state.total_rows_rejected = meta.get("total_rows_rejected", 0)
        state.has_warnings_or_errors = meta.get("has_warnings_or_errors", False)
        state.warnings_acknowledged = meta.get("warnings_acknowledged", True)

        uploaded_files = []
        for d in meta.get("uploaded_files", []):
            uploaded_files.append(UploadedFileEntry(**d))
        state.uploaded_files = uploaded_files

        load_logs = []
        for d in meta.get("load_logs", []):
            load_logs.append(DivisionLoadLog(**d))
        state.load_logs = load_logs

        if "settings" in meta:
            state.settings = AppSettings(**meta["settings"])

        state.compiled_df = df
        state.is_compiled = True
        state.notify()
        return True
    except Exception as exc:
        print(f"[SessionManager] Warning: failed to load session cache: {exc}")
        return False


def clear_session(state: AppState):
    """Delete session files and reset state."""
    try:
        session_dir = get_session_dir()
        df_path = session_dir / "compiled_data.pkl"
        meta_path = session_dir / "metadata.json"

        if df_path.exists():
            df_path.unlink()
        if meta_path.exists():
            meta_path.unlink()
    except Exception as exc:
        print(f"[SessionManager] Warning: failed to clear session files: {exc}")

    state.reset_compilation()
