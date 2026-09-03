"""The desktop launcher.

The first version of the Windows launcher opened the browser before the
server had bound its port, and the user was shown ERR_CONNECTION_REFUSED
while the server was still starting several seconds behind it. These tests
exist so that cannot come back.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

from auditlens.launch import DEFAULT_PORT, find_free_port, is_listening, open_when_ready


def _hold(port: int) -> socket.socket:
    """Occupy a port the way another application would."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    return s


def test_a_free_port_is_returned_unchanged():
    port = find_free_port(8731)
    assert port == 8731


def test_an_occupied_port_is_stepped_over():
    """Port 8000 is popular. Another application holding it must move
    AuditLens along, not stop it."""
    held = _hold(8741)
    try:
        assert find_free_port(8741) == 8742
    finally:
        held.close()


def test_several_occupied_ports_are_stepped_over():
    held = [_hold(p) for p in (8751, 8752, 8753)]
    try:
        assert find_free_port(8751) == 8754
    finally:
        for s in held:
            s.close()


def test_no_free_port_is_reported_rather_than_hanging():
    held = [_hold(p) for p in range(8761, 8764)]
    try:
        with pytest.raises(SystemExit, match="Could not find a free port"):
            find_free_port(8761, attempts=3)
    finally:
        for s in held:
            s.close()


def test_is_listening_distinguishes_a_live_port_from_a_dead_one():
    held = _hold(8771)
    try:
        assert is_listening(8771)
    finally:
        held.close()
    assert not is_listening(8772)


def test_the_browser_opens_only_after_the_port_answers(monkeypatch):
    """The regression test for ERR_CONNECTION_REFUSED."""
    port = 8781
    opened_at: list[float] = []
    monkeypatch.setattr(
        "auditlens.launch.webbrowser.open", lambda url: opened_at.append(time.monotonic())
    )

    listening_at: list[float] = []
    server: list[socket.socket] = []

    def start_late() -> None:
        time.sleep(0.8)                      # the server takes a moment, as it does
        s = _hold(port)
        server.append(s)
        listening_at.append(time.monotonic())

    threading.Thread(target=start_late, daemon=True).start()
    try:
        open_when_ready(port, wait_seconds=10)
        assert opened_at, "the browser was never opened"
        assert listening_at, "the test server never came up"
        assert opened_at[0] >= listening_at[0], (
            "the browser opened before the port was listening - "
            "this is the connection-refused bug"
        )
    finally:
        for s in server:
            s.close()


def test_waiting_gives_up_rather_than_hanging_forever(monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr("auditlens.launch.webbrowser.open", lambda url: opened.append(url))
    started = time.monotonic()
    open_when_ready(8791, wait_seconds=1.0)      # nothing will ever listen here
    assert not opened
    assert time.monotonic() - started < 4.0


def test_the_default_port_is_the_one_the_documentation_promises():
    assert DEFAULT_PORT == 8000
