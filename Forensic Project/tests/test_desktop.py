"""
Unit tests for the standalone desktop application wrapper (desktop_app.py).
"""
import os
import sys
import socket
import pytest
from desktop_app import find_free_port

def test_desktop_app_port_allocation():
    port = find_free_port(8600)
    assert 8600 <= port <= 8650

def test_pywebview_installed_and_functional():
    import webview
    assert callable(webview.create_window)
    assert callable(webview.start)

def test_desktop_app_file_exists():
    assert os.path.exists("desktop_app.py")
    assert os.path.exists("run_desktop.bat")
