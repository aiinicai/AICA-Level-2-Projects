import socket

import pytest

from app.security.network import OutboundNetworkBlocked, install_outbound_network_guard, network_guard_installed


def test_guard_blocks_remote_connection_and_dns():
    install_outbound_network_guard()
    assert network_guard_installed()
    with pytest.raises(OutboundNetworkBlocked):
        socket.getaddrinfo("example.com", 443)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(OutboundNetworkBlocked):
            sock.connect(("198.51.100.10", 443))
    finally:
        sock.close()


def test_guard_allows_loopback_connection():
    install_outbound_network_guard()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0)); server.listen(1)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(("127.0.0.1", server.getsockname()[1]))
        accepted, _ = server.accept()
        accepted.close()
    finally:
        client.close(); server.close()
