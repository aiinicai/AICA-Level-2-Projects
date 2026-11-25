"""HTTPS certificate helper for the intranet server (runs offline).

  python scripts/make_cert.py --csr        key + certificate request (server.csr) to send to IT.
                                           IT signs it with the company CA; save their reply as
                                           instance/certs/server.crt. Browsers then trust it.
  python scripts/make_cert.py --self-signed
                                           key + self-signed certificate for a trial. Each browser
                                           shows a warning until the certificate is trusted.
Options: --name cashflow.company.local (extra DNS names, repeatable), --out folder.
The server's own host name, full domain name and IP addresses are always included.
"""
from __future__ import annotations

import argparse
import ipaddress
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[1]


def server_names(extra: list[str]) -> tuple[list[str], list[str]]:
    host = socket.gethostname()
    dns = {host.lower(), socket.getfqdn().lower(), "localhost", *[n.lower() for n in extra]}
    ips = {"127.0.0.1"}
    try:
        ips |= {ip for ip in socket.gethostbyname_ex(host)[2] if not ip.startswith("169.254.")}
    except OSError:
        pass
    return sorted(dns), sorted(ips)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--csr", action="store_true", help="make a certificate request for IT")
    mode.add_argument("--self-signed", action="store_true", help="make a self-signed certificate (trial)")
    p.add_argument("--name", action="append", default=[], help="extra DNS name, e.g. cashflow.company.local")
    p.add_argument("--out", default=str(ROOT / "instance" / "certs"))
    p.add_argument("--days", type=int, default=825)
    a = p.parse_args(argv)

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    key_path = out / "server.key"
    if key_path.exists() and a.self_signed and (out / "server.crt").exists():
        sys.exit(f"{out / 'server.crt'} already exists. Delete it first to make a new one.")
    dns, ips = server_names(a.name)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, a.name[0] if a.name else dns[0]),
                         x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Cash Flow Forecast")])
    san = x509.SubjectAlternativeName([x509.DNSName(d) for d in dns] +
                                      [x509.IPAddress(ipaddress.ip_address(i)) for i in ips])
    if a.csr:
        csr = (x509.CertificateSigningRequestBuilder().subject_name(subject).add_extension(san, critical=False)
               .sign(key, hashes.SHA256()))
        (out / "server.csr").write_bytes(csr.public_bytes(serialization.Encoding.PEM))
        print(f"Key:     {key_path}  (keep it on this server; never send it)")
        print(f"Request: {out / 'server.csr'}  -> send to IT to sign with the company CA")
        print(f"Names:   {', '.join(dns + ips)}")
        print(f"Save IT's signed certificate as {out / 'server.crt'}, then run setup_server.ps1.")
        return
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=a.days)).add_extension(san, critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    (out / "server.crt").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print(f"Self-signed certificate: {out / 'server.crt'} (valid {a.days} days)")
    print(f"Key: {key_path}")
    print(f"Names: {', '.join(dns + ips)}")
    print("Browsers will warn until this certificate is trusted on each PC (or use --csr with IT instead).")


if __name__ == "__main__":
    main()
