"""
Hearth Local Area Network (LAN) SSL/TLS Certificate Generator
Generates a self-signed TLS certificate for localhost and your local Wi-Fi IP address.
This enables mobile browsers (Safari on iOS, Chrome on Android) to grant microphone
permissions when using a smartphone as a remote table microphone.
"""

import os
import sys
import socket
import datetime
from pathlib import Path
from ipaddress import ip_address

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def get_local_ip() -> str:
    """Detect the host's primary local IP address on the Wi-Fi or LAN subnet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just resolves routing
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_certificates(output_dir: str = "certs"):
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    cert_file = out_path / "cert.pem"
    key_file = out_path / "key.pem"

    local_ip = get_local_ip()
    print(f"[*] Detected Local LAN IP: {local_ip}")

    # Generate RSA private key (2048-bit)
    print("[*] Generating private key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Subject and Issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hearth Local Voice"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
    ])

    # Subject Alternative Names (SAN) for localhost + LAN IP
    san_list = [
        x509.DNSName("localhost"),
        x509.IPAddress(ip_address("127.0.0.1")),
    ]
    if local_ip != "127.0.0.1":
        san_list.append(x509.IPAddress(ip_address(local_ip)))

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )

    # Write private key
    with open(key_file, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"\n[+] Success! Certificate generated:")
    print(f"    Certificate: {cert_file.resolve()}")
    print(f"    Private Key: {key_file.resolve()}")
    print("\n" + "=" * 65)
    print("HOW TO RUN HEARTH WITH HTTPS FOR PHONE TABLE-MIC:")
    print("=" * 65)
    print(f"  uvicorn services.core.api.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile certs/key.pem --ssl-certfile certs/cert.pem")
    print(f"\nThen on your phone or tablet on the same Wi-Fi network, navigate to:")
    print(f"  https://{local_ip}:8443")
    print("Accept the self-signed local certificate, and the browser will enable the microphone!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    generate_certificates()
