# LAN HTTPS Pairing & Table-Mic Guide

This guide details how to pair a secondary device (e.g., placing a smartphone in the center of the dining table as a microphone) while using a tablet or laptop as the primary large caption display.

---

## 1. Why HTTPS is Required for Local Network Mics

Modern mobile browsers (Safari on iOS, Chrome on Android) implement the W3C Secure Contexts specification:
- The `navigator.mediaDevices.getUserMedia()` API is **strictly blocked** on any remote non-localhost origin unless accessed over **`https://`**.
- Local loopback (`http://localhost:8000`) works without TLS, but when accessing across the home Wi-Fi via a LAN IP (e.g. `http://192.168.1.50:8000`), the browser will refuse to request mic permission.
- Hearth solves this completely offline without third-party cloud relays by generating a local self-signed TLS certificate with Subject Alternative Names (SAN) for both `localhost` and your local LAN IP address.

---

## 2. Generating the Local TLS Certificate (1-Step)

Run the built-in certificate generator:

```bash
# Windows
.\venv\Scripts\python.exe scripts/generate_lan_cert.py

# Linux / macOS
python3 scripts/generate_lan_cert.py
```

Output:
```text
[*] Detected Local LAN IP: 192.168.1.42
[*] Generating private key...
[+] Success! Certificate generated:
    Certificate: certs/cert.pem
    Private Key: certs/key.pem
```

---

## 3. Starting Hearth in LAN HTTPS Mode

Start the FastAPI backend with the generated certificates, binding to all local interfaces (`0.0.0.0`):

```bash
uvicorn services.core.api.main:app \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-keyfile certs/key.pem \
  --ssl-certfile certs/cert.pem
```

---

## 4. Pairing Your Phone on the Table

1. **Ensure both devices are connected to the same local home Wi-Fi network.**
2. Open Hearth on the primary display (e.g. tablet or laptop) at `https://localhost:8443` or `https://<YOUR_LAN_IP>:8443`.
3. Click the **Table-Mic** button in the header (or open Settings $\rightarrow$ Table-Mic Mode).
4. Point your phone camera at the displayed QR code (or navigate on the phone to `https://<YOUR_LAN_IP>:8443/?room=<ROOM_ID>&role=mic`).
5. **Accept the self-signed certificate warning** (tap *Advanced* $\rightarrow$ *Proceed to 192.168.x.x*).
6. Grant microphone permission when prompted.
7. Place the phone in the middle of the table. Audio frames will stream directly over local WebSockets to the host with zero internet packets sent.
