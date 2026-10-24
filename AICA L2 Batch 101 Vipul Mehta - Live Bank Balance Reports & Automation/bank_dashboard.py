import os
import sys

# Suppress pycache generation across macOS & Windows
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

import re
import json
import time
import signal
import logging
import subprocess
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string

def get_screen_size():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080

SCREEN_WIDTH, SCREEN_HEIGHT = get_screen_size()
HALF_WIDTH = SCREEN_WIDTH // 2
WIN_HEIGHT = SCREEN_HEIGHT - 60

# Suppress verbose Flask development and access log messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
cli = sys.modules.get('flask.cli')
if cli:
    cli.show_server_banner = lambda *args, **kwargs: None

# Import our summary module
import generate_bank_summary

app = Flask(__name__)
PORT = 10001

from config import (
    SCRIPT_DIR,
    DATA_DIR,
    HDFC_BALANCES_FILE,
    HDFC_TRANSACTIONS_FILE,
    RBL_BALANCES_FILE,
    BANK_SUMMARY_HTML,
    BANK_SUMMARY_SNIPPET,
    CHROME_PATH,
    load_bank_accounts,
    save_bank_accounts,
    load_bank_config,
    save_bank_config,
    add_bank,
    delete_bank,
    get_entity_names
)

def get_dynamic_hdfc_accounts():
    """Dynamically get HDFC accounts from centralized bank_accounts.json."""
    data = load_bank_accounts()
    accs = [
        {"name": a.get("code") or a.get("name"), "id": a.get("id") or a.get("customer_id"), "full_name": a.get("name", "")}
        for a in data.get("HDFC", []) if a.get("active", True)
    ]
    if accs:
        return accs
    return [

    ]


def get_dynamic_rbl_accounts():
    """Dynamically get RBL accounts from centralized bank_accounts.json."""
    data = load_bank_accounts()
    accs = [
        {"name": a.get("code") or a.get("name"), "id": a.get("id") or a.get("user_id"), "full_name": a.get("name", "")}
        for a in data.get("RBL", []) if a.get("active", True)
    ]
    if accs:
        return accs
    return [

    ]


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bank Automation Dashboard & Summary</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root, body[data-theme="dark"] {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --card-bg: #1e293b;
            --card-hover: #27354a;
            --accent-blue: #3b82f6;
            --accent-hover: #2563eb;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
            --border-light: #243247;
            --table-hover: #26354d;
            --pill-bg: #28374d;
            --pill-text: #cbd5e1;
            --active-ring: #38bdf8;
            --stale-bg: rgba(239, 68, 68, 0.22);
            --stale-text: #f87171;
            --stale-border: #ef4444;
            --fresh-bg: rgba(16, 185, 129, 0.22);
            --fresh-text: #34d399;
            --fresh-border: #10b981;
        }

        body[data-theme="light"] {
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --card-bg: #ffffff;
            --card-hover: #f1f5f9;
            --accent-blue: #2563eb;
            --accent-hover: #1d4ed8;
            --accent-green: #059669;
            --accent-red: #dc2626;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border-color: #cbd5e1;
            --border-light: #e2e8f0;
            --table-hover: #f1f5f9;
            --pill-bg: #e2e8f0;
            --pill-text: #334155;
            --active-ring: #2563eb;
            --stale-bg: #fee2e2;
            --stale-text: #b91c1c;
            --stale-border: #f87171;
            --fresh-bg: #d1fae5;
            --fresh-text: #065f46;
            --fresh-border: #34d399;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body {
            background-color: var(--bg-primary);
            color: var(--text-main);
            padding: 10px 14px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            transition: background-color 0.2s, color 0.2s;
        }
        .container {
            width: 100%;
            max-width: 1560px;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        /* Top Header */
        .top-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 14px;
            background: var(--bg-secondary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .top-header h1 {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-theme {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-theme:hover { border-color: var(--accent-blue); }
        .shutdown-btn {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
        }
        .shutdown-btn:hover { background: var(--accent-red); color: white; }

        /* Summary Container */
        #summaryContainer {
            width: 100%;
        }

        /* Automation Runner Section */
        .runner-section {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 14px;
        }
        .runner-title {
            font-size: 0.92rem;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .main-layout {
            display: grid;
            grid-template-columns: 460px 1fr;
            gap: 12px;
            align-items: start;
        }
        @media (max-width: 1024px) {
            .main-layout { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--card-bg);
            border-radius: 8px;
            border: 1px solid var(--border-color);
            padding: 10px 12px;
        }
        .card-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .script-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
        }
        .radio-card {
            display: flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-primary);
            padding: 6px 8px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            font-size: 0.82rem;
        }
        .radio-card:hover { border-color: var(--accent-blue); }
        .radio-card input { accent-color: var(--accent-blue); cursor: pointer; }

        .accounts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
            gap: 5px;
            margin-top: 6px;
            max-height: 200px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .account-chip {
            display: flex;
            align-items: center;
            gap: 6px;
            background: var(--bg-primary);
            padding: 4px 7px;
            border-radius: 5px;
            border: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            font-size: 0.82rem;
            transition: border-color 0.15s, background-color 0.15s;
        }
        .account-chip:hover {
            border-color: var(--accent-blue);
        }
        .account-chip.selected {
            background: rgba(59, 130, 246, 0.15);
            border-color: var(--accent-blue);
        }
        .account-chip input { accent-color: var(--accent-blue); cursor: pointer; }

        .actions-bar {
            display: flex;
            gap: 6px;
            margin-bottom: 4px;
        }
        .btn-small {
            background: #334155;
            color: white;
            border: none;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
        }
        .btn-small:hover { background: #475569; }

        /* Sensitized Password Field with Toggle and Enter key support */
        .input-group { margin-top: 6px; }
        .input-group label {
            display: block;
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 3px;
        }
        .password-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }
        .password-wrapper input {
            width: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            padding: 6px 36px 6px 9px;
            border-radius: 5px;
            color: var(--text-main);
            font-size: 0.85rem;
        }
        .password-wrapper input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        .pwd-toggle-btn {
            position: absolute;
            right: 6px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px 6px;
            font-size: 13px;
            line-height: 1;
        }
        .pwd-toggle-btn:hover { color: var(--text-main); }

        .run-btn {
            width: 100%;
            background: var(--accent-blue);
            color: white;
            padding: 8px;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            cursor: pointer;
            margin-top: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }
        .run-btn:hover { background: var(--accent-hover); }
        .run-btn:disabled {
            background: #475569;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .stop-btn {
            width: 100%;
            background: var(--accent-red);
            color: white;
            padding: 8px;
            border-radius: 6px;
            font-size: 0.9rem;
            font-weight: 700;
            border: none;
            cursor: pointer;
            margin-top: 6px;
            display: none;
        }

        /* Terminal Console */
        .terminal-box {
            background: #090d16;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 10px;
            height: 230px;
            overflow-y: auto;
            font-family: "JetBrains Mono", "Cascadia Code", "Consolas", monospace;
            font-size: 0.78rem;
            line-height: 1.35;
            color: #cbd5e1;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* Output Files Banner */
        .output-files-box {
            display: none;
            margin-top: 8px;
            padding: 8px 12px;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .output-files-header {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--accent-green);
            display: flex;
            align-items: center;
            gap: 6px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .output-files-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .output-file-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s;
        }
        .output-file-btn:hover {
            border-color: var(--accent-green);
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
        }

        /* Toast notification */
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
            display: none;
            z-index: 1000;
        }

        /* Password Prompt Modal Dialog */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(3px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 2000;
        }
        .modal-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            width: 90%;
            max-width: 420px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
            animation: modalFadeIn 0.18s ease-out;
        }
        @keyframes modalFadeIn {
            from { opacity: 0; transform: translateY(-12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .modal-title {
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-main);
        }
        .modal-body {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-bottom: 14px;
        }
        .modal-input-wrap {
            position: relative;
            display: flex;
            align-items: center;
            margin-bottom: 16px;
        }
        .modal-input-wrap input {
            width: 100%;
            padding: 9px 36px 9px 12px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-main);
            font-size: 0.95rem;
            letter-spacing: 0.5px;
        }
        .modal-input-wrap input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }
        .modal-btn-cancel {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 7px 14px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
        }
        .modal-btn-cancel:hover {
            color: var(--text-main);
            border-color: var(--text-muted);
        }
        .modal-btn-confirm {
            background: var(--accent-blue);
            border: 1px solid var(--accent-blue);
            color: white;
            padding: 7px 18px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 700;
            cursor: pointer;
        }
        .modal-btn-confirm:hover {
            background: var(--accent-hover);
        }

        /* Settings Modal */
        #settingsModal {
            align-items: flex-start;
            padding-top: 45px;
        }
        .settings-modal-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 22px;
            width: 95%;
            max-width: 820px;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
            animation: modalFadeIn 0.18s ease-out;
        }
        .settings-top-tabs {
            display: flex;
            gap: 8px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 16px;
            padding-bottom: 8px;
        }
        .settings-tab {
            padding: 7px 15px;
            border-radius: 6px;
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            border: 1px solid transparent;
            background: transparent;
            transition: all 0.15s;
        }
        .settings-tab:hover { color: var(--text-main); }
        .settings-tab.active {
            color: var(--accent-blue);
            background: rgba(59, 130, 246, 0.12);
            border-color: rgba(59, 130, 246, 0.3);
        }
        .theme-selection-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin: 12px 0 20px 0;
        }
        .theme-card-option {
            border: 2px solid var(--border-color);
            border-radius: 8px;
            padding: 14px 16px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            background: var(--bg-primary);
            transition: all 0.15s ease;
        }
        .theme-card-option:hover {
            border-color: var(--accent-blue);
        }
        .theme-card-option.active {
            border-color: var(--accent-blue);
            background: rgba(59, 130, 246, 0.08);
            box-shadow: 0 0 0 1px var(--accent-blue);
        }
        .theme-preview-dot {
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
        }
        .modal-subnav {
            display: flex;
            gap: 8px;
            align-items: center;
            flex-wrap: wrap;
        }
        .modal-tab-btn {
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
        }
        .modal-tab-btn.active {
            background: var(--accent-blue);
            color: white;
            border-color: var(--accent-blue);
        }
        .add-bank-btn {
            background: transparent;
            border: 1px dashed var(--accent-blue);
            color: var(--accent-blue);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .add-bank-btn:hover {
            background: rgba(59, 130, 246, 0.1);
        }
        .accounts-table-container {
            overflow-y: auto;
            margin: 12px 0;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            max-height: 48vh;
        }
        .acc-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.82rem;
        }
        .acc-table th {
            background: var(--bg-primary);
            padding: 8px 10px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.76rem;
            text-transform: uppercase;
            position: sticky;
            top: 0;
            z-index: 2;
        }
        .acc-table td {
            padding: 6px 8px;
            border-bottom: 1px solid var(--border-color);
        }
        .acc-table input[type="text"] {
            width: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 5px 8px;
            color: var(--text-main);
            font-size: 0.82rem;
            box-sizing: border-box;
        }
        .acc-table input[type="text"]:focus {
            border-color: var(--accent-blue);
            outline: none;
        }
        .btn-del-row {
            background: none;
            border: none;
            color: var(--accent-red);
            font-size: 1.1rem;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .btn-del-row:hover {
            background: rgba(239, 68, 68, 0.15);
        }

        /* 4 Medium-Sized Task Selection Tiles */
        .task-tiles-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        @media (max-width: 600px) {
            .task-tiles-grid { grid-template-columns: 1fr; }
        }
        .task-tile {
            background: var(--bg-primary);
            border: 1.5px solid var(--border-color);
            border-radius: 8px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.18s ease;
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .task-tile:hover {
            border-color: var(--accent-blue);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        .task-tile.active {
            background: rgba(59, 130, 246, 0.08);
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 1px var(--accent-blue);
        }
        .tile-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .tile-title {
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-main);
            margin-top: 2px;
        }
        .tile-desc {
            font-size: 0.74rem;
            color: var(--text-muted);
            line-height: 1.25;
        }
        .tile-badge {
            font-size: 0.68rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 4px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }
        .task-tile.active .tile-badge {
            background: var(--accent-blue);
            color: white;
            border-color: var(--accent-blue);
        }

        /* Main Tabs Nav */
        .main-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0;
        }
        .main-tab {
            padding: 8px 18px;
            cursor: pointer;
            font-size: 0.92rem;
            font-weight: 600;
            color: var(--text-muted);
            border-bottom: 2px solid transparent;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .main-tab:hover { color: var(--text-main); }
        .main-tab.active {
            color: var(--accent-blue);
            border-bottom: 2px solid var(--accent-blue);
        }

        /* Statement Viewer Layout - Tiles Based */
        #statementsView { display: none; width: 100%; }
        
        /* Statement Filter Bar */
        .stmt-filter-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .stmt-search-input {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 6px 12px;
            color: var(--text-main);
            font-size: 0.84rem;
            width: 250px;
            transition: border-color 0.15s ease;
        }
        .stmt-search-input:focus {
            border-color: var(--accent-blue);
            outline: none;
        }
        .stmt-bank-pills {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stmt-pill-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 14px;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .stmt-pill-btn:hover {
            color: var(--text-main);
            border-color: var(--accent-blue);
        }
        .stmt-pill-btn.active {
            background: var(--accent-blue);
            color: white;
            border-color: var(--accent-blue);
        }

        #statementsIndex {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
            gap: 8px;
            align-items: stretch;
        }
        
        .stmt-account-tile {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 8px 10px;
            cursor: pointer;
            transition: all 0.15s ease;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 6px;
        }
        .stmt-account-tile:hover {
            border-color: var(--accent-blue);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .stmt-tile-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
        }
        .stmt-tile-bank-logo {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            min-width: 0;
        }
        .stmt-tile-nickname {
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 130px;
        }
        .stmt-tile-last4 {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: var(--text-muted);
            background: var(--bg-primary);
            padding: 1px 5px;
            border-radius: 3px;
            border: 1px solid var(--border-color);
            white-space: nowrap;
        }
        .stmt-tile-body {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-top: 2px;
        }
        .stmt-tile-balance {
            font-size: 1rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-main);
            line-height: 1.1;
        }
        .stmt-tile-refresh-btn {
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: var(--text-muted);
            transition: all 0.15s ease;
        }
        .stmt-tile-refresh-btn:hover {
            background: var(--accent-blue);
            color: white;
            border-color: var(--accent-blue);
            transform: rotate(45deg);
        }
        .stmt-tile-time {
            font-size: 0.68rem;
            font-weight: 600;
            padding: 1px 4px;
            border-radius: 3px;
            white-space: nowrap;
        }
        .stmt-tile-time.stale-red {
            color: var(--stale-text);
            background: var(--stale-bg);
            border: 1px solid var(--stale-border);
        }
        .stmt-tile-time.fresh-green {
            color: var(--fresh-text);
            background: var(--fresh-bg);
            border: 1px solid var(--fresh-border);
        }
        .stmt-tile-time.normal-time {
            color: var(--text-muted);
        }
        
        .index-refresh-btn {
            background: transparent;
            border: none;
            color: var(--accent-blue);
            cursor: pointer;
            padding: 2px;
            display: flex;
            align-items: center;
            gap: 4px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .index-refresh-btn:hover {
            color: var(--accent-hover);
            background: rgba(59,130,246,0.1);
        }

        #statementSheet {
            display: none;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }
        .sheet-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-secondary);
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
        }
        .btn-back-index {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-blue);
            border: 1px solid var(--accent-blue);
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .btn-back-index:hover {
            background: var(--accent-blue);
            color: white;
        }
        .sheet-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text-main);
            text-align: right;
        }
        .sheet-subtitle {
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .statement-table-wrap {
            overflow: auto;
            max-height: 65vh;
        }
        .statement-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .statement-table th {
            background: var(--bg-secondary);
            color: var(--text-muted);
            padding: 10px 16px;
            text-align: left;
            position: sticky;
            top: 0;
            border-bottom: 1px solid var(--border-color);
            z-index: 2;
        }
        .statement-table td {
            padding: 10px 16px;
            border-bottom: 1px solid var(--border-light);
            color: var(--text-main);
        }
        .statement-table tr:hover td { background: var(--table-hover); }
        .amount-col { text-align: right; font-family: "JetBrains Mono", "Cascadia Code", monospace; }
    </style>
</head>
<body data-theme="dark">
    <div class="container">
        <!-- Top Nav / Control Bar -->
        <div class="top-header">
            <h1>🏦 NetBanking Automation & Consolidated Balances</h1>
            <div class="header-actions">
                <button class="btn-theme" onclick="openSettingsModal()">⚙️ Settings</button>
                <button class="shutdown-btn" onclick="shutdownServer()">🛑 Exit Dashboard</button>
            </div>
        </div>

        <div class="main-tabs">
            <div class="main-tab active" onclick="switchMainTab('dashboard')" id="tab_dashboard">📊 Dashboard</div>
            <div class="main-tab" onclick="switchMainTab('bulk')" id="tab_bulk">⚡ Bulk Update</div>
            <div class="main-tab" onclick="switchMainTab('statements')" id="tab_statements">📄 Statements</div>
        </div>

        <!-- 1. MAIN DASHBOARD VIEW -->
        <div id="dashboardView">
            <!-- LIVE CONSOLIDATED BALANCES SUMMARY SECTION (Dynamic Component) -->
            <div id="summaryContainer">
                <div style="text-align: center; padding: 20px; color: var(--text-muted);">
                    Loading live bank balances...
                </div>
            </div>

            <!-- DASHBOARD LIVE TERMINAL CONSOLE -->
            <div class="card" style="margin-top: 14px; display: flex; flex-direction: column;">
                <div class="card-title" style="justify-content: space-between;">
                    <span>Terminal Output</span>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">
                        Real-time execution log
                    </div>
                </div>
                <div id="dashboardTerminal" class="terminal-box" style="height: 180px;">Waiting for automation execution...</div>
            </div>
        </div> <!-- End dashboardView -->

        <!-- 2. BULK UPDATE VIEW -->
        <div id="bulkView" style="display: none;">
            <div class="runner-section">
                <div class="runner-title">
                    <span>⚡ Automation Runner & Live Browser Logs</span>
                    <span id="runnerStatus" style="font-size: 0.75rem; color: var(--accent-green);">Ready</span>
                </div>

                <div class="main-layout">
                    <!-- Left: Script & Account Controls -->
                    <div class="card">
                        <div class="card-title">1. Select Task</div>
                        <input type="hidden" id="selectedScriptInput" value="">
                        
                        <div class="task-tiles-grid">
                            <div class="task-tile" id="tile_hdfc_balances" onclick="selectTaskTile('hdfc_balances', 'hdfc')">
                                <div class="tile-top">
                                    <span style="display:inline-flex; align-items:center; gap:6px;">
                                        {{ hdfc_logo_icon | safe }}
                                        <span class="tile-title">HDFC Balances</span>
                                    </span>
                                    <span class="tile-badge">Balances</span>
                                </div>
                                <div class="tile-desc">Fetch live consolidated balances for HDFC accounts</div>
                            </div>

                            <div class="task-tile" id="tile_hdfc_transactions" onclick="selectTaskTile('hdfc_transactions', 'hdfc')">
                                <div class="tile-top">
                                    <span style="display:inline-flex; align-items:center; gap:6px;">
                                        {{ hdfc_logo_icon | safe }}
                                        <span class="tile-title">HDFC Txns</span>
                                    </span>
                                    <span class="tile-badge">Txns</span>
                                </div>
                                <div class="tile-desc">Download latest monthly transaction statement</div>
                            </div>

                            <div class="task-tile" id="tile_rbl_balances" onclick="selectTaskTile('rbl_balances', 'rbl')">
                                <div class="tile-top">
                                    <span style="display:inline-flex; align-items:center; gap:6px;">
                                        {{ rbl_logo_icon | safe }}
                                        <span class="tile-title">RBL Balances</span>
                                    </span>
                                    <span class="tile-badge">Balances</span>
                                </div>
                                <div class="tile-desc">Fetch live consolidated balances for RBL accounts</div>
                            </div>

                            <div class="task-tile" id="tile_rbl_transactions" onclick="selectTaskTile('rbl_transactions', 'rbl')">
                                <div class="tile-top">
                                    <span style="display:inline-flex; align-items:center; gap:6px;">
                                        {{ rbl_logo_icon | safe }}
                                        <span class="tile-title">RBL Txns</span>
                                    </span>
                                    <span class="tile-badge">Txns</span>
                                </div>
                                <div class="tile-desc">Download latest transactions for RBL accounts</div>
                            </div>
                        </div>

                        <div style="margin-top: 14px;">
                            <div class="card-title" style="margin-bottom: 4px;">
                                <span>2. Target Accounts</span>
                                <span id="accountCountBadge" style="font-size: 0.72rem; color: var(--text-muted);">(None selected)</span>
                            </div>
                            <div id="accountsActionToolbar" class="actions-bar" style="display: none;">
                                <button type="button" class="btn-small" onclick="selectAllAccounts()">Select All</button>
                                <button type="button" class="btn-small" onclick="clearAllAccounts()">Clear</button>
                            </div>
                            
                            <div id="noTaskSelectedNotice" style="padding: 18px 12px; text-align: center; color: var(--text-muted); font-size: 0.82rem; border: 1px dashed var(--border-color); border-radius: 6px; margin-top: 6px;">
                                👆 Select a task above to choose target accounts
                            </div>

                            <!-- HDFC Accounts Grid -->
                            <div id="hdfcAccountsGrid" class="accounts-grid" style="display: none;">
                                {% for a in hdfc_accounts %}
                                <label class="account-chip selected" data-acc="{{ a.name }}" title="Customer ID: {{ a.id }}">
                                    <input type="checkbox" value="{{ a.name }}" checked onchange="onAccountToggled(this)">
                                    <strong>{{ a.name }}</strong>
                                </label>
                                {% endfor %}
                            </div>

                            <!-- RBL Accounts Grid -->
                            <div id="rblAccountsGrid" class="accounts-grid" style="display: none;">
                                {% for a in rbl_accounts %}
                                <label class="account-chip selected" data-acc="{{ a.name }}" title="User ID: {{ a.id }}">
                                    <input type="checkbox" value="{{ a.name }}" checked onchange="onAccountToggled(this)">
                                    <strong>{{ a.name }}</strong>
                                </label>
                                {% endfor %}
                            </div>
                        </div>

                        <div class="input-group">
                            <label for="passwordInput">3. NetBanking Password</label>
                            <div class="password-wrapper">
                                <input type="password" id="passwordInput" placeholder="Enter password (saved for session)..." onchange="savePasswordSession(this.value)" onkeydown="onPasswordKeyDown(event)">
                                <button type="button" class="pwd-toggle-btn" onclick="togglePasswordVisibility()" title="Show/Hide Password">👁</button>
                            </div>
                        </div>

                        <button id="runBtn" class="run-btn" onclick="triggerRun()">
                            <span>▶ Start Automation</span>
                        </button>
                        <button id="stopBtn" class="stop-btn" onclick="stopExecution()">
                            <span>⏹ Stop Process</span>
                        </button>
                    </div>

                    <!-- Right: Live Streaming Console -->
                    <div class="card" style="display: flex; flex-direction: column;">
                        <div class="card-title" style="justify-content: space-between;">
                            <span>Terminal Output</span>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">
                                Chrome runs on right half of screen
                            </div>
                        </div>
                        <div id="terminal" class="terminal-box">Waiting for automation execution...</div>
                        <div id="outputFilesBox" class="output-files-box" style="display: none;">
                            <div class="output-files-header">
                                <span>📁 Generated Output Files:</span>
                            </div>
                            <div id="outputFilesList" class="output-files-list"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div> <!-- End bulkView -->

        <!-- STATEMENTS VIEWER -->
        <div id="statementsView">
            <!-- INDEX MODE -->
            <div id="statementsIndexWrap">
                <div class="stmt-filter-bar">
                    <input type="text" id="stmtSearchInput" class="stmt-search-input" placeholder="🔍 Search nickname, bank, last 4 digits..." oninput="onStatementFilterChanged()">
                    <div class="stmt-bank-pills" id="stmtBankPills">
                        <button type="button" class="stmt-pill-btn active" data-bank="ALL" onclick="setStatementBankFilter('ALL')">ALL</button>
                        <!-- Dynamic Bank pills will be populated here -->
                    </div>
                </div>
                <div id="statementsIndex">
                    <!-- Compact statement tiles will be injected here -->
                </div>
            </div>

            <!-- SHEET MODE -->
            <div id="statementSheet">
                <div class="sheet-header">
                    <button class="btn-back-index" onclick="returnToIndex()">
                        <span>&#8592;</span> Return to Index
                    </button>
                    <div style="display:flex; flex-direction:column; align-items:flex-end;">
                        <div style="display:flex; align-items:center; gap: 8px;">
                            <div class="sheet-title" id="sheetTitle">Entity - Account</div>
                            <button id="sheetRefreshBtn" class="bbs-icon-btn" style="background:transparent; border:none; cursor:pointer; color:var(--text-muted); padding:4px; display:flex; align-items:center; gap:4px; border-radius:4px;" title="Refresh Transactions">
                                <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"/>
                                </svg>
                                <span style="font-size:0.75rem; font-weight:600;">Refresh Txns</span>
                            </button>
                        </div>
                        <div class="sheet-subtitle" id="sheetSubtitle">Bank Statement</div>
                    </div>
                </div>
                <div class="statement-table-wrap">
                    <table class="statement-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Description</th>
                                <th class="amount-col">Debit</th>
                                <th class="amount-col">Credit</th>
                                <th class="amount-col">Balance</th>
                            </tr>
                        </thead>
                        <tbody id="statementsTableBody">
                            <!-- Transactions will be injected here -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

    <div id="toast" class="toast">Balances updated!</div>

    <!-- Sensitized Password Prompt Modal Dialog -->
    <div id="pwdModal" class="modal-overlay">
        <div class="modal-card">
            <div class="modal-title">
                <span>🔐</span>
                <span id="pwdModalTitle">NetBanking Password</span>
            </div>
            <div class="modal-body" id="pwdModalPrompt">
                Please enter your NetBanking password to start automation:
            </div>
            <div class="modal-input-wrap">
                <input type="password" id="modalPasswordInput" placeholder="Password is masked..." autocomplete="off">
                <button type="button" class="pwd-toggle-btn" onclick="toggleModalPwdVisibility()" title="Show/Hide Password">👁</button>
            </div>
            <div class="modal-actions">
                <button type="button" class="modal-btn-cancel" onclick="closePasswordModal(null)">Cancel</button>
                <button type="button" class="modal-btn-confirm" onclick="confirmPasswordModal()">Continue</button>
            </div>
        </div>
    </div>

    <!-- SETTINGS MODAL (Theme, Accounts Manager, & Add Bank) -->
    <div id="settingsModal" class="modal-overlay">
        <div class="settings-modal-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div class="modal-title" style="margin-bottom:0;">⚙️ Dashboard Settings</div>
                <button type="button" class="btn-del-row" onclick="closeSettingsModal()" style="font-size: 1.4rem; color: var(--text-muted); line-height: 1;">&times;</button>
            </div>
            
            <div class="settings-top-tabs">
                <button type="button" class="settings-tab active" id="setTabAccounts" onclick="switchSettingsTab('accounts')">🏦 Bank Accounts</button>
                <button type="button" class="settings-tab" id="setTabTheme" onclick="switchSettingsTab('theme')">🎨 Appearance / Theme</button>
                <button type="button" class="settings-tab" id="setTabAddBank" onclick="switchSettingsTab('addbank')">➕ Add Bank</button>
            </div>

            <!-- TAB 1: ACCOUNTS MANAGER -->
            <div id="settingsAccountsPane">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                    <div class="modal-subnav" id="bankSubnavPills">
                        <!-- Dynamic Bank selector pills -->
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <button type="button" class="btn-del-row" onclick="deleteCurrentBank()" id="btnDeleteBank" style="font-size: 0.8rem; border: 1px solid var(--accent-red); padding: 5px 10px; border-radius: 6px;" title="Delete this bank">🗑 Delete Bank</button>
                        <button type="button" class="btn-theme" onclick="addAccountRow()" style="background: var(--accent-blue); color: white; border-color: var(--accent-blue);">+ Add Account</button>
                    </div>
                </div>

                <div class="accounts-table-container">
                    <table class="acc-table">
                        <thead>
                            <tr>
                                <th style="width: 110px;">Nickname</th>
                                <th>Entity / Company Name</th>
                                <th style="width: 180px;" id="thAccId">Customer ID</th>
                                <th style="width: 60px; text-align: center;">Active</th>
                                <th style="width: 45px; text-align: center;">Del</th>
                            </tr>
                        </thead>
                        <tbody id="accountsTableBody">
                        </tbody>
                    </table>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                    <span id="accountsSaveMsg" style="font-size: 0.8rem; color: var(--accent-green);"></span>
                    <div class="modal-actions" style="margin-top:0;">
                        <button type="button" class="modal-btn-cancel" onclick="closeSettingsModal()">Cancel</button>
                        <button type="button" class="modal-btn-confirm" onclick="saveAccountsModal()">💾 Save Changes</button>
                    </div>
                </div>
            </div>

            <!-- TAB 2: APPEARANCE / THEME -->
            <div id="settingsThemePane" style="display: none;">
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 12px;">
                    Choose the interface color theme for the consolidated dashboard:
                </div>
                <div class="theme-selection-grid">
                    <div class="theme-card-option" id="optThemeDark" onclick="setDashboardTheme('dark')">
                        <div class="theme-preview-dot" style="background:#0f172a; border: 1px solid #334155;">🌙</div>
                        <div>
                            <div style="font-weight: 700; color: var(--text-main);">Dark Mode</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">High-contrast dark palette for low light</div>
                        </div>
                    </div>
                    <div class="theme-card-option" id="optThemeLight" onclick="setDashboardTheme('light')">
                        <div class="theme-preview-dot" style="background:#ffffff; border: 1px solid #cbd5e1; color:#0f172a;">☀️</div>
                        <div>
                            <div style="font-weight: 700; color: var(--text-main);">Light Mode</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted);">Clean white background with soft borders</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB 3: ADD NEW BANK (Folder & Accounts) -->
            <div id="settingsAddBankPane" style="display: none;">
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-bottom: 14px;">
                    Register a new bank. This creates its dedicated subfolder (e.g. <code>YES/</code>) and adds it to your dashboard so you can add and manage accounts individually.
                </div>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; max-width: 550px;">
                    <div class="input-group">
                        <label for="newBankCode">Bank Code (Folder Name)</label>
                        <input type="text" id="newBankCode" placeholder="e.g. YES, ICICI, SBI" style="text-transform: uppercase;">
                    </div>
                    <div class="input-group">
                        <label for="newBankName">Full Bank Name</label>
                        <input type="text" id="newBankName" placeholder="e.g. Yes Bank Ltd">
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 12px; margin-top: 14px;">
                    <button type="button" class="btn-theme" onclick="submitAddNewBank()" style="background: var(--accent-blue); color: white; border-color: var(--accent-blue); padding: 8px 18px;">➕ Create Bank & Folder</button>
                    <span id="addBankMsg" style="font-size: 0.82rem;"></span>
                </div>
            </div>
        </div>
    </div>

    <script>

        let allTxnsData = null;

        function switchMainTab(tabName) {
            document.getElementById('tab_dashboard').classList.remove('active');
            document.getElementById('tab_bulk').classList.remove('active');
            document.getElementById('tab_statements').classList.remove('active');
            
            document.getElementById('dashboardView').style.display = 'none';
            document.getElementById('bulkView').style.display = 'none';
            document.getElementById('statementsView').style.display = 'none';

            document.getElementById('tab_' + tabName).classList.add('active');
            document.getElementById(tabName + 'View').style.display = 'block';

            if (tabName === 'statements') {
                if (!allTxnsData) {
                    fetchStatementsData();
                } else {
                    returnToIndex();
                }
            }
        }

        function selectTaskTile(scriptKey, bank) {
            document.querySelectorAll('.task-tile').forEach(t => t.classList.remove('active'));
            const tile = document.getElementById('tile_' + scriptKey);
            if (tile) tile.classList.add('active');
            document.getElementById('selectedScriptInput').value = scriptKey;
            switchBank(bank);
        }

        function fetchStatementsData() {
            fetch('/api/summary')
                .then(r => r.json())
                .then(data => {
                    allTxnsData = data.data;
                    renderIndex();
                });
        }

        function formatCurrency(val) {
            if (val === null || val === undefined) return '-';
            const num = parseFloat(val);
            if (isNaN(num)) return val;
            return '₹ ' + num.toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2});
        }

        function getBankLogoSvgOrImg(bank) {
            if (bank === 'HDFC') {
                return `{{ hdfc_logo_icon | safe }}`;
            } else if (bank === 'RBL') {
                return `{{ rbl_logo_icon | safe }}`;
            }
            return `<div style="width:20px; height:20px; border-radius:4px; background:#4f46e5; color:white; font-size:10px; font-weight:bold; display:flex; align-items:center; justify-content:center;">${(bank||'B').substring(0,2).toUpperCase()}</div>`;
        }

        let stmtBankFilter = 'ALL';

        function setStatementBankFilter(bank) {
            stmtBankFilter = bank;
            document.querySelectorAll('.stmt-pill-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-bank') === bank);
            });
            renderIndex();
        }

        function onStatementFilterChanged() {
            renderIndex();
        }

        function renderIndex() {
            if (!allTxnsData || !allTxnsData.rows) return;
            
            const idxContainer = document.getElementById('statementsIndex');
            const pillsContainer = document.getElementById('stmtBankPills');
            const searchInput = document.getElementById('stmtSearchInput');
            const query = (searchInput ? searchInput.value : '').trim().toLowerCase();

            // Populate bank filter pills dynamically if needed
            if (pillsContainer) {
                const uniqueBanks = Array.from(new Set(allTxnsData.rows.map(r => r.bank || 'HDFC')));
                let pillsHtml = `<button type="button" class="stmt-pill-btn ${stmtBankFilter === 'ALL' ? 'active' : ''}" data-bank="ALL" onclick="setStatementBankFilter('ALL')">ALL</button>`;
                uniqueBanks.forEach(b => {
                    pillsHtml += `<button type="button" class="stmt-pill-btn ${stmtBankFilter === b ? 'active' : ''}" data-bank="${b}" onclick="setStatementBankFilter('${b}')">${b}</button>`;
                });
                pillsContainer.innerHTML = pillsHtml;
            }

            let html = '';
            // Render statement account tiles (Direct tiles: Logo, Nickname, last 4 digits, balance, refresh button)
            const rowsWithTxns = allTxnsData.rows.filter(r => r.has_txns);
            
            rowsWithTxns.forEach(r => {
                const entName = r.account_name || r.name || 'Account';
                const bank = r.bank || 'HDFC';
                const accNum = String(r.account_number || '');
                const last4 = r.last4 || (accNum ? accNum.slice(-4) : '••••');

                // Bank filter
                if (stmtBankFilter !== 'ALL' && bank !== stmtBankFilter) {
                    return;
                }

                // Partial Search Filter (nicknames, banks, account numbers)
                if (query) {
                    const matchName = entName.toLowerCase().includes(query);
                    const matchBank = bank.toLowerCase().includes(query);
                    const matchAcc = accNum.toLowerCase().includes(query) || last4.toLowerCase().includes(query);
                    if (!matchName && !matchBank && !matchAcc) {
                        return;
                    }
                }

                const txn_key = entName.toUpperCase() + '_' + last4;
                const txns = allTxnsData.transactions_map[txn_key] || [];
                
                const fDate = txns.length > 0 ? txns[0].f_date : null;
                const fTime = txns.length > 0 ? txns[0].f_time : null;
                const dateObj = parseBankDate(fDate, fTime);
                const timeInfo = getRelativeTimeInfo(dateObj);
                const timeClass = timeInfo.status === 'stale' ? 'stale-red' : (timeInfo.status === 'fresh' ? 'fresh-green' : 'normal-time');
                const logoHtml = getBankLogoSvgOrImg(bank);

                html += `
                    <div class="stmt-account-tile" onclick="openStatement('${txn_key}', '${entName}', '${r.account_number}', '${r.account_type || 'Account'}', '${bank}')">
                        <div class="stmt-tile-header">
                            <div class="stmt-tile-bank-logo">
                                ${logoHtml}
                                <div>
                                    <div class="stmt-tile-nickname" title="${entName}">${entName}</div>
                                    <div style="font-size:0.68rem; color:var(--text-muted); display:flex; align-items:center; gap:5px; margin-top:1px;">
                                        <span>${bank} · ${last4}</span>
                                        <span class="stmt-tile-time ${timeClass}">⏱ ${timeInfo.text}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="stmt-tile-body">
                            <div class="stmt-tile-balance">${formatCurrency(r.balance)}</div>
                            <button class="stmt-tile-refresh-btn" onclick="event.stopPropagation(); if(window.onTransactionRefreshClicked) window.onTransactionRefreshClicked(event, '${entName}', '${bank}')" title="Refresh ${entName} Transactions">
                                <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round">
                                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                `;
            });
            
            if (!html) {
                html = '<div style="color:var(--text-muted); padding:20px; grid-column: 1 / -1;">No matching statement accounts found.</div>';
            }
            
            idxContainer.innerHTML = html;
        }

        // Helper to parse dates like "2026-10-05 12:00:00" or "05/10/2026 12:00"
        function parseBankDate(d, t) {
            if (!d) return null;
            let str = String(d).trim().split(' ')[0];
            let tStr = (t ? String(t).trim() : "00:00");
            
            // Try ISO (YYYY-MM-DD)
            if (str.includes('-') && str.split('-')[0].length === 4) {
                return new Date(`${str}T${tStr}:00`);
            }
            // Try DD/MM/YYYY or DD-MM-YYYY
            let parts = str.split(/[/-]/);
            if (parts.length === 3) {
                let y = parts[2].length === 2 ? "20" + parts[2] : parts[2];
                let m = parts[1].padStart(2, '0');
                let day = parts[0].padStart(2, '0');
                return new Date(`${y}-${m}-${day}T${tStr}:00`);
            }
            return new Date();
        }

        function getRelativeTimeInfo(dateObj) {
            if (!dateObj || isNaN(dateObj.getTime())) return { text: "Unknown time", status: "normal" };
            const diffSec = Math.floor((new Date() - dateObj) / 1000);
            
            let status = "normal";
            if (diffSec < 3600) {
                status = "fresh";
            } else if (diffSec >= 12 * 3600) {
                status = "stale";
            }

            if (diffSec < 0 || diffSec < 60) return { text: "Just now", status };
            const mins = Math.floor(diffSec / 60);
            if (mins < 60) return { text: `${mins} min${mins!==1?'s':''} ago`, status };
            const hours = Math.floor(mins / 60);
            if (hours < 24) return { text: `${hours} hour${hours!==1?'s':''} ago`, status };
            const days = Math.floor(hours / 24);
            return { text: days === 1 ? "1 day ago" : `${days} days ago`, status };
        }

        function getRelativeTimeStr(dateObj) {
            return getRelativeTimeInfo(dateObj).text;
        }

        function openStatement(txn_key, entName, accNum, accType, bank) {
            document.getElementById('statementsIndex').style.display = 'none';
            document.getElementById('statementSheet').style.display = 'block';
            
            document.getElementById('sheetTitle').innerText = `${entName} - ${accNum}`;
            
            const tbody = document.getElementById('statementsTableBody');
            const txns = allTxnsData.transactions_map[txn_key] || [];
            
            let subtitleHtml = `${bank} · ${accType} Statement`;
            
            if (txns.length > 0) {
                const fDate = txns[0].f_date;
                const fTime = txns[0].f_time;
                const dateObj = parseBankDate(fDate, fTime);
                const relTime = getRelativeTimeStr(dateObj);
                
                let prettyDate = String(fDate).split(' ')[0];
                if (dateObj && !isNaN(dateObj.getTime())) {
                    prettyDate = dateObj.toLocaleDateString('en-GB', {day:'numeric', month:'short', year:'numeric'}) + ' ' + (fTime ? fTime : '');
                }
                
                subtitleHtml += ` &bull; <strong>Pulled:</strong> ${prettyDate} <em>(${relTime})</em>`;
            } else {
                subtitleHtml += ` &bull; <em>No data available</em>`;
            }
            document.getElementById('sheetSubtitle').innerHTML = subtitleHtml;
            
            const btn = document.getElementById('sheetRefreshBtn');
            btn.onclick = (e) => {
                if (window.onTransactionRefreshClicked) {
                    window.onTransactionRefreshClicked(e, entName, bank);
                }
            };
            // Add hover effect
            btn.onmouseover = () => { btn.style.color = "var(--text-main)"; btn.style.background = "var(--card-hover)"; };
            btn.onmouseout = () => { btn.style.color = "var(--text-muted)"; btn.style.background = "transparent"; };
            
            if (txns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; color:var(--text-muted);">No transactions found.</td></tr>';
            } else {
                tbody.innerHTML = txns.map(t => `
                    <tr>
                        <td style="white-space: nowrap; font-family:'JetBrains Mono', monospace;">${t.date || '-'}</td>
                        <td>${t.desc || '-'}</td>
                        <td class="amount-col" style="color: ${t.debit ? 'var(--stale-text)' : 'inherit'}">${formatCurrency(t.debit)}</td>
                        <td class="amount-col" style="color: ${t.credit ? 'var(--fresh-text)' : 'inherit'}">${formatCurrency(t.credit)}</td>
                        <td class="amount-col" style="font-weight:600;">${formatCurrency(t.balance)}</td>
                    </tr>
                `).join('');
            }
        }

        function returnToIndex() {
            document.getElementById('statementsIndex').style.display = 'grid';
            document.getElementById('statementSheet').style.display = 'none';
            document.getElementById('statementsTableBody').innerHTML = ''; // clear for performance
        }

        // Hook into existing loadSummaryReport to also update statements Data if active
        const origLoadSummaryReport = loadSummaryReport;
        loadSummaryReport = function() {
            origLoadSummaryReport();
            if (document.getElementById('tab_statements').classList.contains('active')) {
                fetchStatementsData();
            }
        };

        let currentScript = 'hdfc_balances';
        let currentLogIndex = 0;
        let pollTimer = null;
        let isRunning = false;

        // Restore password from sessionStorage
        function loadSavedPassword() {
            const saved = sessionStorage.getItem('nb_password') || '';
            if (saved) {
                document.getElementById('passwordInput').value = saved;
            }
        }

        function savePasswordSession(pwd) {
            sessionStorage.setItem('nb_password', pwd);
        }

        // Pressing Enter in password box triggers Start Automation
        function onPasswordKeyDown(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                savePasswordSession(e.target.value);
                triggerRun();
            }
        }

        function togglePasswordVisibility() {
            const pwdInput = document.getElementById('passwordInput');
            if (pwdInput.type === 'password') {
                pwdInput.type = 'text';
            } else {
                pwdInput.type = 'password';
            }
        }

        // Theme management
        function initDashboardTheme() {
            const t = localStorage.getItem('bank_summary_theme') || 'dark';
            setDashboardTheme(t, false);
        }

        function setDashboardTheme(theme, save = true) {
            document.body.setAttribute('data-theme', theme);
            if (save) localStorage.setItem('bank_summary_theme', theme);

            // Update modal cards active state
            const darkOpt = document.getElementById('optThemeDark');
            const lightOpt = document.getElementById('optThemeLight');
            if (darkOpt) darkOpt.classList.toggle('active', theme === 'dark');
            if (lightOpt) lightOpt.classList.toggle('active', theme === 'light');

            // Also update embedded summary theme
            const roots = document.querySelectorAll('.bbs-root');
            roots.forEach(r => r.setAttribute('data-theme', theme));
        }

        function toggleDashboardTheme() {
            const cur = document.body.getAttribute('data-theme') || 'dark';
            const next = cur === 'dark' ? 'light' : 'dark';
            setDashboardTheme(next, true);
        }

        // Summary drill-down and filter state
        let currentBankFilter = 'ALL';
        let currentEntityFilter = 'ALL';

        // Load Live Summary Component
        function loadSummaryReport() {
            fetch('/api/summary')
                .then(r => r.json())
                .then(data => {
                    if (data && data.html) {
                        const container = document.getElementById('summaryContainer');
                        container.innerHTML = data.html;
                        
                        // Apply active theme to loaded summary
                        const curTheme = document.body.getAttribute('data-theme') || 'dark';
                        const roots = container.querySelectorAll('.bbs-root');
                        roots.forEach(r => r.setAttribute('data-theme', curTheme));

                        // Initialize summary filters and relative times
                        applySummaryFilters();
                        updateRelativeTimes();
                    }
                })
                .catch(err => {
                    console.error('Error loading summary:', err);
                });
        }

        // Global functions for Summary interactions (accessible by inline onclick handlers)
        window.filterByBank = function(bank) {
            currentBankFilter = (currentBankFilter === bank) ? 'ALL' : bank;
            applySummaryFilters();
        };

        window.resetFilters = function() {
            currentBankFilter = 'ALL';
            collapseAllSummaryDrawers();
            applySummaryFilters();
        };

        window.toggleTheme = function() {
            toggleDashboardTheme();
        };

        window.toggleEntityTree = function(entId) {
            const drawer = document.getElementById('drawer_' + entId);
            const toggle = document.getElementById('toggle_' + entId);
            const row = document.getElementById('row_' + entId);
            if (!drawer) return;

            const isHidden = (drawer.style.display === 'none' || drawer.style.display === '');
            drawer.style.display = isHidden ? 'table-row' : 'none';
            if (toggle) toggle.classList.toggle('open', isHidden);
            if (row) row.classList.toggle('bbs-expanded', isHidden);
            
            if (!isHidden) {
                drawer.querySelectorAll('.bbs-txns-drawer-row').forEach(r => { r.style.display = 'none'; });
                drawer.querySelectorAll('.bbs-account-row').forEach(r => { r.classList.remove('bbs-expanded'); });
                drawer.querySelectorAll('.bbs-tree-toggle-sm').forEach(t => { t.classList.remove('open'); });
            }
        };

        window.toggleAccountTxnsTree = function(accId, entity, last4, bank) {
            const drawer = document.getElementById('drawer_' + accId);
            const toggle = document.getElementById('toggle_' + accId);
            const row = document.getElementById('row_' + accId);
            if (!drawer) return;

            const isHidden = (drawer.style.display === 'none' || drawer.style.display === '');
            drawer.style.display = isHidden ? 'table-row' : 'none';
            if (toggle) toggle.classList.toggle('open', isHidden);
            if (row) row.classList.toggle('bbs-expanded', isHidden);
        };

        function collapseAllSummaryDrawers() {
            document.querySelectorAll('.bbs-entity-drawer-row').forEach(dr => {
                dr.style.display = 'none';
            });
            document.querySelectorAll('.bbs-txns-drawer-row').forEach(dr => {
                dr.style.display = 'none';
            });
            document.querySelectorAll('.bbs-tree-toggle').forEach(tg => {
                tg.classList.remove('open');
            });
            document.querySelectorAll('.bbs-tree-toggle-sm').forEach(tg => {
                tg.classList.remove('open');
            });
            document.querySelectorAll('.bbs-entity-row').forEach(r => {
                r.classList.remove('bbs-expanded');
            });
            document.querySelectorAll('.bbs-account-row').forEach(r => {
                r.classList.remove('bbs-expanded');
            });
        }

        window.onEntityRefreshClicked = function(e, entity, bank) {
            e.stopPropagation();
            window.quickRefreshEntity(entity, bank);
        };

        window.onBankRefreshClicked = function(e, bank) {
            e.stopPropagation();
            window.quickRefreshBank(bank);
        };

        window.onTransactionRefreshClicked = function(e, entity, bank) {
            e.stopPropagation();
            window.quickRefreshEntityTransactions(entity, bank);
        };

        function applySummaryFilters() {
            // 1. Bank card active states
            const hdfcCard = document.getElementById('bbsCardHDFC');
            const rblCard = document.getElementById('bbsCardRBL');
            if (hdfcCard) hdfcCard.classList.toggle('active', currentBankFilter === 'HDFC');
            if (rblCard) rblCard.classList.toggle('active', currentBankFilter === 'RBL');

            // 2. Bank chips
            document.querySelectorAll('.bbs-bank-chip').forEach(c => {
                c.classList.toggle('active', c.getAttribute('data-filter-bank') === currentBankFilter);
            });

            // 3. Filter Entity Rows
            let visibleEntities = 0;
            document.querySelectorAll('.bbs-entity-row').forEach(row => {
                const rowBank = row.getAttribute('data-bank');
                const bankMatch = (currentBankFilter === 'ALL' || rowBank === currentBankFilter);
                row.style.display = bankMatch ? '' : 'none';

                // If filtered out, hide open drawer
                const entId = row.id.replace('row_', '');
                const drawer = document.getElementById('drawer_' + entId);
                if (drawer && !bankMatch) {
                    drawer.style.display = 'none';
                    const toggle = document.getElementById('toggle_' + entId);
                    if (toggle) toggle.classList.remove('open');
                    row.classList.remove('bbs-expanded');
                }

                if (bankMatch) visibleEntities++;
            });

            // 4. Update Status Bar
            const countEl = document.getElementById('bbsFilteredCount');
            if (countEl) {
                if (currentBankFilter !== 'ALL') {
                    countEl.innerHTML = `Showing <strong>${currentBankFilter}</strong> entities (${visibleEntities} entities) · <em>Click any entity to view accounts & transactions</em>`;
                } else {
                    countEl.innerHTML = `All entities (${visibleEntities}) · <em>Click any entity to view accounts & transactions inline</em>`;
                }
            }
        }

        function updateRelativeTimes() {
            const now = new Date();
            document.querySelectorAll('.bbs-rel-time[data-iso]').forEach(el => {
                const iso = el.getAttribute('data-iso');
                if (!iso) return;
                const dt = new Date(iso.replace(' ', 'T'));
                if (isNaN(dt.getTime())) return;
                const diffSec = Math.floor((now - dt) / 1000);
                let str = 'Just now';

                const isFresh = (diffSec < 3600);
                const isStale = (diffSec >= 12 * 3600);

                if (diffSec >= 60) {
                    const mins = Math.floor(diffSec / 60);
                    if (mins < 60) {
                        str = `${mins} min${mins !== 1 ? 's' : ''} ago`;
                    } else {
                        const hours = Math.floor(mins / 60);
                        if (hours < 24) {
                            str = `${hours} hour${hours !== 1 ? \'s\' : \'\'} ago`;
                        } else {
                            const days = Math.floor(hours / 24);
                            str = days === 1 ? '1 day ago' : `${days} days ago`;
                        }
                    }
                }
                el.innerText = '⏱ ' + str;

                el.classList.toggle('bbs-fresh', isFresh);
                el.classList.toggle('bbs-stale', isStale);
            });
        }

        // Modal-based Sensitized Password Prompt
        let passwordModalResolver = null;

        function showPasswordModal(bank) {
            return new Promise((resolve) => {
                passwordModalResolver = resolve;
                const modal = document.getElementById('pwdModal');
                const title = document.getElementById('pwdModalTitle');
                const prompt = document.getElementById('pwdModalPrompt');
                const input = document.getElementById('modalPasswordInput');

                title.innerText = `${bank} NetBanking Password`;
                prompt.innerText = `Enter NetBanking Password for ${bank}:`;
                input.value = '';
                input.type = 'password';

                modal.style.display = 'flex';
                setTimeout(() => input.focus(), 50);

                input.onkeydown = function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        confirmPasswordModal();
                    } else if (e.key === 'Escape') {
                        e.preventDefault();
                        closePasswordModal(null);
                    }
                };
            });
        }

        function confirmPasswordModal() {
            const input = document.getElementById('modalPasswordInput');
            const val = input.value.trim();
            closePasswordModal(val || null);
        }

        function closePasswordModal(result) {
            const modal = document.getElementById('pwdModal');
            modal.style.display = 'none';
            if (passwordModalResolver) {
                const resolver = passwordModalResolver;
                passwordModalResolver = null;
                resolver(result);
            }
        }

        function toggleModalPwdVisibility() {
            const input = document.getElementById('modalPasswordInput');
            input.type = (input.type === 'password') ? 'text' : 'password';
        }

        async function getRequiredPassword(bank) {
            let pwd = document.getElementById('passwordInput').value.trim();
            if (!pwd) {
                pwd = await showPasswordModal(bank);
                if (pwd) {
                    document.getElementById('passwordInput').value = pwd;
                    savePasswordSession(pwd);
                }
            }
            return pwd;
        }

        // Quick Refresh by Bank (Exposed to global window for icon click)
        window.quickRefreshBank = async function(bank) {
            if (isRunning) { alert('An automation task is already running!'); return; }
            const pwd = await getRequiredPassword(bank);
            if (!pwd) return;

            const script = bank === 'HDFC' ? 'hdfc_balances' : 'rbl_balances';
            const gridId = bank === 'HDFC' ? 'hdfcAccountsGrid' : 'rblAccountsGrid';
            const accounts = [];
            document.querySelectorAll(`#${gridId} input[type="checkbox"]`).forEach(cb => {
                accounts.push(cb.value);
            });

            startExecution(script, accounts, pwd, `Refreshing all ${bank} accounts...`);
        };

        // Quick Refresh by Entity Balances (Exposed to global window for icon click)
        window.quickRefreshEntity = async function(entity, bank) {
            if (isRunning) { alert('An automation task is already running!'); return; }
            const pwd = await getRequiredPassword(bank);
            if (!pwd) return;

            const script = bank === 'HDFC' ? 'hdfc_balances' : 'rbl_balances';
            startExecution(script, [entity], pwd, `Refreshing ${bank} balance for: ${entity}...`);
        };

        // Quick Refresh by Entity Transactions (Exposed to global window for txn refresh icon)
        window.quickRefreshEntityTransactions = async function(entity, bank) {
            if (isRunning) { alert('An automation task is already running!'); return; }
            const pwd = await getRequiredPassword(bank);
            if (!pwd) return;

            const script = bank === 'HDFC' ? 'hdfc_transactions' : 'rbl_transactions';
            startExecution(script, [entity], pwd, `Refreshing recent transactions for ${entity}...`);
        };

        function switchBank(bankType) {
            const noTaskNotice = document.getElementById('noTaskSelectedNotice');
            if (noTaskNotice) noTaskNotice.style.display = 'none';

            const toolbar = document.getElementById('accountsActionToolbar');
            if (toolbar) toolbar.style.display = 'flex';

            const hdfcGrid = document.getElementById('hdfcAccountsGrid');
            const rblGrid = document.getElementById('rblAccountsGrid');

            if (bankType === 'hdfc') {
                if (hdfcGrid) hdfcGrid.style.display = 'grid';
                if (rblGrid) rblGrid.style.display = 'none';
            } else {
                if (hdfcGrid) hdfcGrid.style.display = 'none';
                if (rblGrid) rblGrid.style.display = 'grid';
            }
            selectAllAccounts();
        }

        function onAccountToggled(cb) {
            cb.parentElement.classList.toggle('selected', cb.checked);
            updateAccountCount();
        }

        function selectAllAccounts() {
            const visibleGrid = document.querySelector('.accounts-grid:not([style*="display: none"])');
            if (visibleGrid) {
                visibleGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = true;
                    cb.parentElement.classList.add('selected');
                });
            }
            updateAccountCount();
        }

        function clearAllAccounts() {
            const visibleGrid = document.querySelector('.accounts-grid:not([style*="display: none"])');
            if (visibleGrid) {
                visibleGrid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    cb.checked = false;
                    cb.parentElement.classList.remove('selected');
                });
            }
            updateAccountCount();
        }

        function updateAccountCount() {
            const visibleGrid = document.querySelector('.accounts-grid:not([style*="display: none"])');
            const badge = document.getElementById('accountCountBadge');
            if (!badge) return;
            if (!visibleGrid) {
                badge.innerText = '(None selected)';
                return;
            }
            const checked = visibleGrid.querySelectorAll('input[type="checkbox"]:checked').length;
            badge.innerText = `(${checked} selected)`;
        }

        // --- Settings Modal & Bank Management ---
        let currentModalBank = 'HDFC';
        let fullConfigData = { banks: { HDFC: { name: 'HDFC Bank', id_label: 'Customer ID' }, RBL: { name: 'RBL Bank', id_label: 'User ID' } }, accounts: { HDFC: [], RBL: [] } };

        async function openSettingsModal() {
            const modal = document.getElementById('settingsModal');
            document.getElementById('accountsSaveMsg').innerText = '';
            document.getElementById('addBankMsg').innerText = '';
            
            // Sync current theme state in settings modal
            const curTheme = document.body.getAttribute('data-theme') || 'dark';
            setDashboardTheme(curTheme, false);

            try {
                const res = await fetch('/api/config');
                const cfg = await res.json();
                if (cfg && cfg.banks && cfg.accounts) {
                    fullConfigData = cfg;
                }
            } catch (e) {
                console.error("Error loading config:", e);
            }

            renderBankSubnavPills();
            switchAccountsTab(currentModalBank, false); // false = do not sync from empty DOM table
            switchSettingsTab('accounts');
            modal.style.display = 'flex';
        }

        function closeSettingsModal() {
            document.getElementById('settingsModal').style.display = 'none';
        }

        function switchSettingsTab(tabName) {
            document.getElementById('setTabAccounts').classList.toggle('active', tabName === 'accounts');
            document.getElementById('setTabTheme').classList.toggle('active', tabName === 'theme');
            document.getElementById('setTabAddBank').classList.toggle('active', tabName === 'addbank');

            document.getElementById('settingsAccountsPane').style.display = (tabName === 'accounts') ? 'block' : 'none';
            document.getElementById('settingsThemePane').style.display = (tabName === 'theme') ? 'block' : 'none';
            document.getElementById('settingsAddBankPane').style.display = (tabName === 'addbank') ? 'block' : 'none';
        }

        function renderBankSubnavPills() {
            const container = document.getElementById('bankSubnavPills');
            const banks = fullConfigData.banks || {};
            const bankKeys = Object.keys(banks);
            if (!bankKeys.includes(currentModalBank) && bankKeys.length > 0) {
                currentModalBank = bankKeys[0];
            }
            container.innerHTML = bankKeys.map(k => `
                <button type="button" class="modal-tab-btn ${k === currentModalBank ? 'active' : ''}" onclick="switchAccountsTab('${k}', true)">
                    ${banks[k].name || k + ' Bank'}
                </button>
            `).join('');

            // Update Delete Bank button state
            const delBtn = document.getElementById('btnDeleteBank');
            if (delBtn) {
                delBtn.style.display = (bankKeys.length > 1) ? 'inline-block' : 'none';
            }
        }

        function switchAccountsTab(bank, syncBeforeSwitch = true) {
            if (syncBeforeSwitch) {
                syncCurrentTabValues();
            }
            currentModalBank = bank;
            renderBankSubnavPills();
            
            const bankMeta = (fullConfigData.banks && fullConfigData.banks[bank]) || {};
            const idLabel = bankMeta.id_label || (bank === 'HDFC' ? 'Customer ID' : 'User ID');
            document.getElementById('thAccId').innerText = idLabel;
            renderAccountsTable();
        }

        function syncCurrentTabValues() {
            const tbody = document.getElementById('accountsTableBody');
            const rows = tbody.querySelectorAll('tr');
            if (rows.length === 0) return; // Do not overwrite if table was not populated
            
            const updated = [];
            rows.forEach(tr => {
                const codeInput = tr.querySelector('.acc-input-code');
                const nameInput = tr.querySelector('.acc-input-name');
                const idInput = tr.querySelector('.acc-input-id');
                const activeInput = tr.querySelector('.acc-input-active');
                if (codeInput && idInput) {
                    const code = codeInput.value.trim();
                    const name = nameInput ? nameInput.value.trim() : '';
                    const id = idInput.value.trim();
                    const active = activeInput ? activeInput.checked : true;
                    if (code || id) {
                        updated.push({ code, name: name || code, id, active });
                    }
                }
            });
            if (!fullConfigData.accounts) fullConfigData.accounts = {};
            fullConfigData.accounts[currentModalBank] = updated;
        }

        function renderAccountsTable() {
            const tbody = document.getElementById('accountsTableBody');
            const accounts = (fullConfigData.accounts && fullConfigData.accounts[currentModalBank]) || [];
            if (accounts.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:15px; color:var(--text-muted);">No accounts configured yet for ${currentModalBank}. Click "+ Add Account" above.</td></tr>`;
                return;
            }
            const bankMeta = (fullConfigData.banks && fullConfigData.banks[currentModalBank]) || {};
            const idPlaceholder = bankMeta.id_label || 'ID / Customer No';

            tbody.innerHTML = accounts.map((acc, idx) => `
                <tr data-idx="${idx}">
                    <td><input type="text" class="acc-input-code" value="${acc.code || acc.name || ''}" placeholder="e.g. VI"></td>
                    <td><input type="text" class="acc-input-name" value="${acc.name || acc.code || ''}" placeholder="e.g. VI"></td>
                    <td><input type="text" class="acc-input-id" value="${acc.id || acc.customer_id || acc.user_id || ''}" placeholder="e.g. ${idPlaceholder}"></td>
                    <td style="text-align:center;"><input type="checkbox" class="acc-input-active" ${acc.active !== false ? 'checked' : ''}></td>
                    <td style="text-align:center;"><button type="button" class="btn-del-row" onclick="deleteAccountRow(${idx})" title="Remove account">&times;</button></td>
                </tr>
            `).join('');
        }

        function addAccountRow() {
            syncCurrentTabValues();
            if (!fullConfigData.accounts) fullConfigData.accounts = {};
            if (!fullConfigData.accounts[currentModalBank]) fullConfigData.accounts[currentModalBank] = [];
            fullConfigData.accounts[currentModalBank].push({ code: '', name: '', id: '', active: true });
            renderAccountsTable();
            const rows = document.querySelectorAll('#accountsTableBody tr');
            if (rows.length > 0) {
                const lastRowInput = rows[rows.length - 1].querySelector('.acc-input-code');
                if (lastRowInput) lastRowInput.focus();
            }
        }

        function deleteAccountRow(idx) {
            syncCurrentTabValues();
            if (fullConfigData.accounts && fullConfigData.accounts[currentModalBank] && fullConfigData.accounts[currentModalBank][idx]) {
                fullConfigData.accounts[currentModalBank].splice(idx, 1);
                renderAccountsTable();
            }
        }

        async function deleteCurrentBank() {
            if (!confirm(`Are you sure you want to remove ${currentModalBank} from the dashboard?`)) {
                return;
            }
            try {
                const res = await fetch(`/api/banks/${currentModalBank}`, { method: 'DELETE' });
                const result = await res.json();
                if (result.status === 'success') {
                    fullConfigData = result.config;
                    showToast(`Bank ${currentModalBank} removed.`);
                    const remaining = Object.keys(fullConfigData.banks || {});
                    currentModalBank = remaining.length > 0 ? remaining[0] : '';
                    renderBankSubnavPills();
                    if (currentModalBank) {
                        switchAccountsTab(currentModalBank, false);
                    }
                } else {
                    alert('Error: ' + (result.message || 'Could not delete bank'));
                }
            } catch (e) {
                alert('Connection error: ' + e);
            }
        }

        async function saveAccountsModal() {
            syncCurrentTabValues();
            const msgEl = document.getElementById('accountsSaveMsg');
            msgEl.style.color = 'var(--text-muted)';
            msgEl.innerText = 'Saving...';
            try {
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(fullConfigData)
                });
                const result = await res.json();
                if (result.status === 'success') {
                    msgEl.style.color = 'var(--accent-green)';
                    msgEl.innerText = '✅ Saved successfully!';
                    updateDashboardAccountChips(fullConfigData.accounts);
                    showToast('Bank accounts updated successfully!');
                    setTimeout(() => closeSettingsModal(), 600);
                } else {
                    msgEl.style.color = 'var(--accent-red)';
                    msgEl.innerText = '❌ ' + (result.message || 'Error saving');
                }
            } catch (e) {
                msgEl.style.color = 'var(--accent-red)';
                msgEl.innerText = '❌ Failed to connect: ' + e;
            }
        }

        async function submitAddNewBank() {
            const codeInput = document.getElementById('newBankCode');
            const nameInput = document.getElementById('newBankName');
            const msgEl = document.getElementById('addBankMsg');

            const code = codeInput.value.trim().toUpperCase();
            const name = nameInput.value.trim();

            if (!code) {
                msgEl.style.color = 'var(--accent-red)';
                msgEl.innerText = '⚠️ Please enter a bank code (e.g. YES)';
                return;
            }

            msgEl.style.color = 'var(--text-muted)';
            msgEl.innerText = 'Creating bank and folder...';

            try {
                const res = await fetch('/api/banks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code,
                        name: name || code + ' Bank'
                    })
                });
                const result = await res.json();
                if (result.status === 'success') {
                    msgEl.style.color = 'var(--accent-green)';
                    msgEl.innerText = `✅ Bank '${code}' created! Subfolder '${code}/' ready.`;
                    fullConfigData = result.config;
                    currentModalBank = code;
                    codeInput.value = '';
                    nameInput.value = '';
                    showToast(`Bank ${code} registered successfully!`);
                    setTimeout(() => {
                        switchSettingsTab('accounts');
                        renderBankSubnavPills();
                        switchAccountsTab(code, false);
                    }, 800);
                } else {
                    msgEl.style.color = 'var(--accent-red)';
                    msgEl.innerText = '❌ ' + (result.message || 'Error adding bank');
                }
            } catch (e) {
                msgEl.style.color = 'var(--accent-red)';
                msgEl.innerText = '❌ Error: ' + e;
            }
        }

        function updateDashboardAccountChips(data) {
            const hdfcGrid = document.getElementById('hdfcAccountsGrid');
            const rblGrid = document.getElementById('rblAccountsGrid');
            if (hdfcGrid && data.HDFC) {
                hdfcGrid.innerHTML = data.HDFC.filter(a => a.active !== false).map(a => {
                    const code = a.code || a.name;
                    const id = a.id || a.customer_id || '';
                    return `<label class="account-chip selected" data-acc="${code}" title="${a.name || code} (ID: ${id})">
                        <input type="checkbox" value="${code}" checked onchange="onAccountToggled(this)">
                        <strong>${code}</strong>
                    </label>`;
                }).join('');
            }
            if (rblGrid && data.RBL) {
                rblGrid.innerHTML = data.RBL.filter(a => a.active !== false).map(a => {
                    const code = a.code || a.name;
                    const id = a.id || a.user_id || '';
                    return `<label class="account-chip selected" data-acc="${code}" title="${a.name || code} (ID: ${id})">
                        <input type="checkbox" value="${code}" checked onchange="onAccountToggled(this)">
                        <strong>${code}</strong>
                    </label>`;
                }).join('');
            }
            updateAccountCount();
        }

        async function triggerRun() {
            const script = document.getElementById('selectedScriptInput') ? document.getElementById('selectedScriptInput').value : '';
            if (!script) {
                alert('Please select a task tile first (e.g., HDFC Balances, RBL Txns).');
                return;
            }
            const isHdfc = script.startsWith('hdfc');
            const gridId = isHdfc ? 'hdfcAccountsGrid' : 'rblAccountsGrid';
            const accounts = [];
            document.querySelectorAll(`#${gridId} input[type="checkbox"]:checked`).forEach(cb => {
                accounts.push(cb.value);
            });

            if (accounts.length === 0) {
                alert('Please select at least one account to run.');
                return;
            }

            const pwd = await getRequiredPassword(isHdfc ? 'HDFC' : 'RBL');
            if (!pwd) return;

            startExecution(script, accounts, pwd, 'Starting automation...');
        }

        let currentScriptRunning = '';

        function appendToBothTerminals(text, clear = false) {
            const term = document.getElementById('terminal');
            const dashTerm = document.getElementById('dashboardTerminal');
            if (term) {
                if (clear) term.innerText = text; else term.innerText += text;
                term.scrollTop = term.scrollHeight;
            }
            if (dashTerm) {
                if (clear) dashTerm.innerText = text; else dashTerm.innerText += text;
                dashTerm.scrollTop = dashTerm.scrollHeight;
            }
        }

        function startExecution(script, accounts, password, startMsg) {
            // Clear password from screen and session immediately for security
            document.getElementById('passwordInput').value = '';
            sessionStorage.removeItem('nb_password');
            
            isRunning = true;
            currentScriptRunning = script;
            document.getElementById('runBtn').disabled = true;
            document.getElementById('stopBtn').style.display = 'block';
            document.getElementById('runnerStatus').innerText = 'Running...';
            document.getElementById('runnerStatus').style.color = 'var(--accent-blue)';

            const outputBox = document.getElementById('outputFilesBox');
            if (outputBox) outputBox.style.display = 'none';

            const initialText = `[INFO] ${startMsg}\\n[INFO] Script: ${script} | Accounts: ${accounts.join(', ')}\\n`;
            appendToBothTerminals(initialText, true);
            currentLogIndex = 0;

            fetch('/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script, accounts, password })
            })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'started') {
                    startPollingLogs();
                } else {
                    appendToBothTerminals(`\\n[ERROR] ${data.message}\\n`);
                    endExecution(false);
                }
            })
            .catch(err => {
                appendToBothTerminals(`\\n[ERROR] Failed to start task: ${err}\\n`);
                endExecution(false);
            });
        }

        let logPollCount = 0;
        function startPollingLogs() {
            clearInterval(pollTimer);
            pollTimer = setInterval(() => {
                logPollCount++;
                if (logPollCount % 5 === 0) {
                    loadSummaryReport();
                }
                
                fetch(`/logs?after=${currentLogIndex}`)
                    .then(r => r.json())
                    .then(data => {
                        if (data.logs && data.logs.length > 0) {
                            appendToBothTerminals(data.logs.join('\\n') + '\\n');
                            currentLogIndex = data.next_index;
                        }

                        if (data.state === 'completed' || data.state === 'failed') {
                            clearInterval(pollTimer);
                            endExecution(data.state === 'completed');
                        }
                    })
                    .catch(() => {});
            }, 600);
        }

        function stopExecution() {
            fetch('/stop', { method: 'POST' });
        }

        function openOutputFile(filename) {
            fetch(`/open_file?name=${encodeURIComponent(filename)}`)
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'opened') {
                        showToast(`📄 Opened ${filename}`);
                    } else {
                        showToast(`⚠️ Could not open ${filename}`);
                    }
                })
                .catch(() => showToast(`⚠️ Error opening ${filename}`));
        }

        function endExecution(success) {
            isRunning = false;
            document.getElementById('runBtn').disabled = false;
            document.getElementById('stopBtn').style.display = 'none';

            const statusEl = document.getElementById('runnerStatus');

            if (success) {
                statusEl.innerText = 'Completed';
                statusEl.style.color = 'var(--accent-green)';
                showToast('✅ Balances updated successfully!');

                let filesToShow = [];
                if (currentScriptRunning.startsWith('rbl')) {
                    filesToShow = ['RBL Balances.xlsx', 'RBL Transactions.xlsx'];
                } else {
                    filesToShow = ['HDFC balances.xlsx', 'HDFC transactions.xlsx'];
                }

                let outMsg = `\\n============================================================\\n` +
                             `[OUTPUT] Generated / Updated Files:\\n`;
                filesToShow.forEach(f => {
                    outMsg += `  * Excel File:    ${f}\\n`;
                });
                outMsg += `  * HTML Summary:  bank_summary_latest.html\\n` +
                          `============================================================\\n`;
                appendToBothTerminals(outMsg);

                const outputBox = document.getElementById('outputFilesBox');
                const listEl = document.getElementById('outputFilesList');
                if (outputBox && listEl) {
                    listEl.innerHTML = filesToShow.map(f => `
                        <button type="button" class="output-file-btn" onclick="openOutputFile('${f}')" title="Click to open in Excel">
                            📊 Open ${f}
                        </button>
                    `).join('');
                    outputBox.style.display = 'flex';
                }

                setTimeout(loadSummaryReport, 800);
            } else {
                statusEl.innerText = 'Failed';
                statusEl.style.color = 'var(--accent-red)';
                
                // Inspect logs for actionable failure hints
                const term = document.getElementById('terminal');
                const text = term ? term.innerText : '';
                let hint = '';
                if (text.includes('password') || text.includes('Password') || text.includes('AUTH') || text.includes('Invalid')) {
                    hint = '⚠️ Password may be incorrect. Check your NetBanking password.';
                } else if (text.includes('Timeout') || text.includes('waiting for selector')) {
                    hint = '⏱ Bank portal took too long to respond. The bank server may be slow. Click Start to retry.';
                } else if (text.includes('Target closed') || text.includes('browser has been closed')) {
                    hint = 'Browser window was closed during execution.';
                }

                if (hint) {
                    appendToBothTerminals(`\\n[DIAGNOSTIC] ${hint}\\n`);
                }
            }
        }

        function showToast(msg) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 4000);
        }

        function shutdownServer() {
            if (confirm('Are you sure you want to stop the dashboard and exit?')) {
                fetch('/shutdown', { method: 'POST' });
                window.close();
                document.body.innerHTML = '<div style="text-align:center; padding:50px; color:#94a3b8;"><h2>Dashboard Server Closed</h2><p>You can close this tab now.</p></div>';
            }
        }

        // Periodic heartbeat ping to notify server that browser tab is alive
        setInterval(() => {
            fetch('/api/heartbeat').catch(() => {});
        }, 3000);

        // Global Escape Key Listener to dismiss modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const settingsModal = document.getElementById('settingsModal');
                const pwdModal = document.getElementById('pwdModal');
                if (settingsModal && settingsModal.style.display !== 'none' && settingsModal.style.display !== '') {
                    closeSettingsModal();
                } else if (pwdModal && pwdModal.style.display !== 'none' && pwdModal.style.display !== '') {
                    closePasswordModal(null);
                }
            }
        });

        // On Load
        document.addEventListener('DOMContentLoaded', () => {
            initDashboardTheme();
            loadSavedPassword();
            updateAccountCount();
            loadSummaryReport();
        });
    </script>
</body>
</html>
"""

# Process state
current_process = None
process_logs = []
process_state = 'idle'
process_lock = threading.Lock()


@app.route('/')
def index():
    hdfc_accounts = get_dynamic_hdfc_accounts()
    rbl_accounts = get_dynamic_rbl_accounts()
    hdfc_logo_icon = generate_bank_summary.get_bank_logo('HDFC', width=16, height=16)
    rbl_logo_icon = generate_bank_summary.get_bank_logo('RBL', width=16, height=16)
    return render_template_string(
        DASHBOARD_HTML,
        hdfc_accounts=hdfc_accounts,
        rbl_accounts=rbl_accounts,
        hdfc_logo_icon=hdfc_logo_icon,
        rbl_logo_icon=rbl_logo_icon
    )


@app.route('/api/summary')
def api_summary():
    """Returns the latest bank balances summary HTML snippet and JSON data."""
    data = generate_bank_summary.get_latest_data()
    html_snippet = generate_bank_summary.generate_html_content(data, standalone=False)
    return jsonify({
        'html': html_snippet,
        'data': data
    })


@app.route('/run', methods=['POST'])
def run_task():
    global current_process, process_logs, process_state
    with process_lock:
        if current_process and current_process.poll() is None:
            return jsonify({'status': 'busy', 'message': 'A script is already running!'}), 400

        data = request.json or {}
        script_key = data.get('script')
        selected_accounts = data.get('accounts', [])
        password = data.get('password', '')

        script_mapping = {
            'hdfc_balances': [SCRIPT_DIR / 'HDFC' / 'HDFC balances.py', SCRIPT_DIR / 'HDFC balances.py'],
            'hdfc_transactions': [SCRIPT_DIR / 'HDFC' / 'HDFC Transactions.py', SCRIPT_DIR / 'HDFC Transactions.py'],
            'rbl_balances': [SCRIPT_DIR / 'RBL' / 'RBL balances.py', SCRIPT_DIR / 'RBL balances.py'],
            'rbl_transactions': [SCRIPT_DIR / 'RBL' / 'RBL Transactions.py', SCRIPT_DIR / 'RBL Transactions.py']
        }

        candidates = script_mapping.get(script_key, [])
        target_file = None
        for cand in candidates:
            if cand.exists():
                target_file = cand
                break

        if not target_file and '_' in script_key:
            bank_prefix, action = script_key.split('_', 1)
            bank_upper = bank_prefix.upper()
            bank_dir = SCRIPT_DIR / bank_upper
            if bank_dir.exists():
                for pyf in bank_dir.glob("*.py"):
                    if action.lower() in pyf.name.lower():
                        target_file = pyf
                        break

        if not target_file:
            return jsonify({'status': 'error', 'message': f'Script file not found for: {script_key}'}), 404

        process_logs = []
        process_state = 'running'

        runner_code = generate_runner_code(target_file, script_key, selected_accounts, password)
        temp_runner = SCRIPT_DIR / "_temp_bank_runner.py"
        with open(temp_runner, "w", encoding="utf-8") as f:
            f.write(runner_code)

        try:
            child_env = os.environ.copy()
            child_env["PYTHONUNBUFFERED"] = "1"
            child_env["PYTHONIOENCODING"] = "utf-8"

            current_process = subprocess.Popen(
                [sys.executable, "-u", str(temp_runner)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(SCRIPT_DIR),
                env=child_env
            )

            threading.Thread(target=collect_output, args=(current_process, temp_runner), daemon=True).start()
            return jsonify({'status': 'started'})
        except Exception as e:
            process_state = 'failed'
            return jsonify({'status': 'error', 'message': str(e)}), 500


def generate_runner_code(target_path, script_key, selected_accounts, password):
    acc_json = json.dumps(selected_accounts)
    pwd_json = json.dumps(password)
    target_path_str = json.dumps(str(target_path))

    return f'''import sys
import os
import json
import importlib.util

os.environ['PYTHONUNBUFFERED'] = '1'
os.environ['PYTHONIOENCODING'] = 'utf-8'

desktop_path = os.path.dirname({target_path_str})
target_file = {target_path_str}
selected_accounts = {acc_json}
password = {pwd_json}

spec = importlib.util.spec_from_file_location("target_module", target_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# Override password fetcher (sensitized - never prints cleartext)
def custom_get_password():
    print("[AUTH] Using password provided from dashboard (hidden).")
    return password

mod.get_password = custom_get_password

# Resilient timeouts
if hasattr(mod, 'quick_fill'):
    original_quick_fill = mod.quick_fill
    def resilient_quick_fill(page, selectors, value, label, timeout=5000):
        return original_quick_fill(page, selectors, value, label, timeout=max(timeout, 5000))
    mod.quick_fill = resilient_quick_fill

if hasattr(mod, 'quick_click'):
    original_quick_click = mod.quick_click
    def resilient_quick_click(page, selectors, label, timeout=3000, use_js=False):
        return original_quick_click(page, selectors, label, timeout=max(timeout, 3000), use_js=use_js)
    mod.quick_click = resilient_quick_click

# Filter accounts
if hasattr(mod, 'ACCOUNTS'):
    mod.ACCOUNTS = [a for a in mod.ACCOUNTS if a["name"] in selected_accounts]

if hasattr(mod, 'select_accounts'):
    mod.select_accounts = lambda: mod.ACCOUNTS

if hasattr(mod, 'OUTPUT_FILE'):
    mod.OUTPUT_FILE = os.path.join(desktop_path, os.path.basename(mod.OUTPUT_FILE))

# Screen position Playwright to the right half
if hasattr(mod, 'sync_playwright'):
    original_sync_playwright = mod.sync_playwright
    import contextlib

    @contextlib.contextmanager
    def custom_sync_playwright():
        with original_sync_playwright() as p:
            original_launch = p.chromium.launch
            original_launch_persistent = p.chromium.launch_persistent_context

            def apply_right_half_args(kwargs):
                launch_args = list(kwargs.get('args', []))
                needed_flags = [
                    f'--window-position={HALF_WIDTH},0',
                    f'--window-size={HALF_WIDTH},{WIN_HEIGHT}',
                    '--no-first-run',
                    '--no-default-browser-check'
                ]
                for flag in needed_flags:
                    prefix = flag.split('=')[0]
                    if not any(a.startswith(prefix) for a in launch_args):
                        launch_args.append(flag)
                kwargs['args'] = launch_args
                return kwargs

            def custom_launch(*args, **kwargs):
                kwargs = apply_right_half_args(kwargs)
                browser = original_launch(*args, **kwargs)
                original_new_page = browser.new_page

                def custom_new_page(*p_args, **p_kwargs):
                    if 'no_viewport' not in p_kwargs and 'viewport' not in p_kwargs:
                        p_kwargs['no_viewport'] = True
                    return original_new_page(*p_args, **p_kwargs)

                browser.new_page = custom_new_page
                return browser

            def custom_launch_persistent(*args, **kwargs):
                kwargs = apply_right_half_args(kwargs)
                if 'no_viewport' not in kwargs and 'viewport' not in kwargs:
                    kwargs['no_viewport'] = True
                return original_launch_persistent(*args, **kwargs)

            p.chromium.launch = custom_launch
            p.chromium.launch_persistent_context = custom_launch_persistent
            yield p

    mod.sync_playwright = custom_sync_playwright

try:
    if hasattr(mod, 'main'):
        mod.main()
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''


def collect_output(proc, temp_file):
    global process_logs, process_state
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                cleaned = line.rstrip('\r\n')
                with process_lock:
                    process_logs.append(cleaned)
        proc.wait()
    except Exception as e:
        with process_lock:
            process_logs.append(f"[ERROR] {e}")
    finally:
        with process_lock:
            if proc.returncode == 0:
                process_state = 'completed'
            else:
                process_state = 'failed'
        try:
            if temp_file.exists():
                temp_file.unlink()
        except:
            pass


@app.route('/logs')
def get_logs():
    global process_logs, process_state
    after = request.args.get('after', 0, type=int)
    with process_lock:
        return jsonify({
            'logs': process_logs[after:],
            'next_index': len(process_logs),
            'state': process_state
        })


@app.route('/stop', methods=['POST'])
def stop_process():
    global current_process, process_state
    with process_lock:
        if current_process and current_process.poll() is None:
            try:
                current_process.terminate()
            except:
                pass
            process_state = 'failed'
            return jsonify({'status': 'stopped'})
    return jsonify({'status': 'idle'})


@app.route('/open_file')
def open_file():
    filename = request.args.get('name', '').strip()
    # Allow only specific desktop output files for security
    allowed_files = ['HDFC balances.xlsx', 'RBL Balances.xlsx', 'HDFC transactions.xlsx', 'RBL Transactions.xlsx', 'bank_summary_latest.html']
    if filename not in allowed_files:
        return jsonify({'status': 'error', 'message': 'Disallowed file'}), 400

    target = DATA_DIR / filename
    if not target.exists():
        for sub in DATA_DIR.iterdir():
            if sub.is_dir() and (sub / filename).exists():
                target = sub / filename
                break

    if target.exists():
        if sys.platform == 'win32':
            os.startfile(str(target))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(target)])
        else:
            subprocess.run(['xdg-open', str(target)])
        return jsonify({'status': 'opened', 'file': filename})
    return jsonify({'status': 'not_found', 'message': 'File does not exist yet'}), 404


@app.route('/api/accounts', methods=['GET', 'POST'])
def api_accounts():
    if request.method == 'POST':
        payload = request.json or {}
        if not isinstance(payload, dict):
            return jsonify({'status': 'error', 'message': 'Invalid payload format'}), 400
        if save_bank_accounts(payload):
            generate_bank_summary.ENTITY_NAMES = get_entity_names()
            return jsonify({'status': 'success', 'accounts': payload})
        return jsonify({'status': 'error', 'message': 'Failed to save accounts'}), 500
    return jsonify(load_bank_accounts())


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        payload = request.json or {}
        if not isinstance(payload, dict) or 'banks' not in payload or 'accounts' not in payload:
            return jsonify({'status': 'error', 'message': 'Invalid config payload'}), 400
        if save_bank_config(payload):
            generate_bank_summary.ENTITY_NAMES = get_entity_names()
            return jsonify({'status': 'success', 'config': payload})
        return jsonify({'status': 'error', 'message': 'Failed to save configuration'}), 500
    return jsonify(load_bank_config())


@app.route('/api/banks', methods=['POST'])
def api_add_bank():
    data = request.json or {}
    code = data.get('code', '').strip().upper()
    name = data.get('name', '').strip()
    balances_script = data.get('balances_script', '').strip()
    txns_script = data.get('txns_script', '').strip()
    balances_excel = data.get('balances_excel', '').strip()
    txns_excel = data.get('txns_excel', '').strip()
    
    if not code:
        return jsonify({'status': 'error', 'message': 'Bank code is required (e.g. YES, ICICI)'}), 400
    
    ok, result = add_bank(
        code, name,
        balances_script=balances_script,
        txns_script=txns_script,
        balances_excel=balances_excel,
        txns_excel=txns_excel
    )
    if ok:
        generate_bank_summary.ENTITY_NAMES = get_entity_names()
        return jsonify({'status': 'success', 'config': result})
    else:
        return jsonify({'status': 'error', 'message': str(result)}), 400


@app.route('/api/banks/<bank_code>', methods=['DELETE'])
def api_delete_bank(bank_code):
    ok, result = delete_bank(bank_code)
    if ok:
        generate_bank_summary.ENTITY_NAMES = get_entity_names()
        return jsonify({'status': 'success', 'config': result})
    else:
        return jsonify({'status': 'error', 'message': str(result)}), 400



last_heartbeat = time.time()
has_received_heartbeat = False
chrome_process = None


def quit_chrome():
    """Closes Chrome process and issues macOS AppleScript quit command."""
    global chrome_process
    if chrome_process and chrome_process.poll() is None:
        try:
            chrome_process.terminate()
        except Exception:
            pass
    if sys.platform == "darwin":
        try:
            subprocess.run(["osascript", "-e", 'tell application "Google Chrome" to quit'], capture_output=True)
        except Exception:
            pass


@app.route('/api/heartbeat')
def api_heartbeat():
    global last_heartbeat, has_received_heartbeat
    last_heartbeat = time.time()
    has_received_heartbeat = True
    return jsonify({'status': 'alive'})


@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown():
    def kill_self():
        time.sleep(0.5)
        global current_process
        if current_process and current_process.poll() is None:
            try:
                current_process.terminate()
            except:
                pass
        quit_chrome()
        time.sleep(0.3)
        try:
            if sys.platform != "win32":
                os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)
            else:
                os.kill(os.getpid(), signal.SIGTERM)
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=kill_self).start()
    return jsonify({'status': 'shutting_down'})


def monitor_browser_heartbeat():
    """Cleanly stop the background server only after the dashboard has been active and is closed."""
    # Wait 30 seconds initially so the user has plenty of time for Chrome to initialize
    time.sleep(30)
    while True:
        time.sleep(4)
        if has_received_heartbeat and (time.time() - last_heartbeat > 60):
            global current_process
            if current_process and current_process.poll() is None:
                try:
                    current_process.terminate()
                except:
                    pass
            quit_chrome()
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(os.getpid()), signal.SIGKILL)
                else:
                    os.kill(os.getpid(), signal.SIGTERM)
            except Exception:
                pass
            os._exit(0)
            break


def kill_existing_port(port):
    if sys.platform == "win32":
        try:
            cmd = f"netstat -ano | findstr :{port}"
            out = subprocess.check_output(cmd, shell=True, text=True)
            for line in out.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1]:
                    pid = parts[-1]
                    if pid != str(os.getpid()):
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
        except subprocess.CalledProcessError:
            pass
    else:
        try:
            out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True).strip()
            for p in out.split():
                if p.isdigit() and p != str(os.getpid()):
                    try:
                        os.kill(int(p), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass


if __name__ == '__main__':
    kill_existing_port(PORT)
    print("=" * 65)
    print(f"  [INFO] Bank Dashboard starting on http://localhost:{PORT}")
    print(f"  [INFO] Independent runner (existing run_dashboard remains untouched)")
    print("=" * 65)

    def open_browser():
        global chrome_process
        time.sleep(0.8)
        launched = False
        p = CHROME_PATH
        if os.path.exists(p):
            profile_dir = DATA_DIR / ".dashboard_profile"
            chrome_args = [
                p,
                f"--app=http://localhost:{PORT}",
                "--window-position=0,0",
                f"--window-size={HALF_WIDTH},{WIN_HEIGHT}",
                f"--user-data-dir={profile_dir}",
                "--disable-logging",
                "--log-level=3",
                "--disable-background-networking",
                "--disable-component-update",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            try:
                chrome_process = subprocess.Popen(
                    chrome_args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                launched = True
            except Exception:
                launched = False
        if not launched:
            import webbrowser
            webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()
    threading.Thread(target=monitor_browser_heartbeat, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False)

