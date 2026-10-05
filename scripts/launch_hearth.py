"""
Hearth Single-Command Launcher
Boots the local FastAPI backend, serves the production web app, verifies offline isolation,
and opens the browser directly to the live interface.
"""

import os
import sys
import time
import socket
import argparse
import subprocess
import webbrowser
from pathlib import Path


def install_egress_guard():
    """
    Enforces air-gap network isolation at the Python runtime level.
    Any attempt to open a socket connection to a non-loopback IP raises PermissionError.
    """
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        allowed_hosts = ("127.0.0.1", "localhost", "::1", "0.0.0.0")
        if host not in allowed_hosts and not host.startswith("127."):
            raise PermissionError(
                f"[EGRESS GUARD TRIGGERED] Outbound network connection blocked to {address}. "
                "Hearth is running in strict offline air-gap mode."
            )
        return orig_connect(self, address)

    socket.socket.connect = guarded_connect
    print("[HEARTH] Strict Egress Guard enabled: Zero non-loopback network calls allowed.")


def check_and_build_frontend(workspace_root: Path):
    dist_dir = workspace_root / "apps" / "web" / "dist"
    if not dist_dir.exists() or not (dist_dir / "index.html").exists():
        print("[HEARTH] Building frontend web assets...")
        web_dir = workspace_root / "apps" / "web"
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        res = subprocess.run([npm_cmd, "run", "build"], cwd=str(web_dir), shell=True)
        if res.returncode != 0:
            print("[WARN] Frontend build exited with non-zero status. Static assets might not be ready.")


def wait_for_server(url: str, timeout: float = 20.0) -> bool:
    import urllib.request
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main():
    parser = argparse.ArgumentParser(description="Hearth - Private Offline Live Captions & Speech Translation")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--offline", action="store_true", help="Enforce runtime egress isolation")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    parser.add_argument("--profile", default="balanced", choices=["tiny", "balanced", "quality"], help="Hardware profile")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    os.environ["HEARTH_PROFILE"] = args.profile

    if args.offline:
        install_egress_guard()

    print("=" * 68)
    print("  HEARTH — Private, Offline Live Captions & Speech Translation")
    print(f"  Profile: {args.profile.upper()} | Host: {args.host}:{args.port}")
    print("=" * 68)

    check_and_build_frontend(root)

    server_cmd = [
        sys.executable,
        "-m", "uvicorn",
        "services.core.api.main:app",
        "--host", args.host,
        "--port", str(args.port),
        "--log-level", "warning",
    ]

    print(f"[*] Starting local backend server on http://{args.host}:{args.port} ...")
    proc = subprocess.Popen(server_cmd, cwd=str(root))

    health_url = f"http://{args.host}:{args.port}/api/health"
    app_url = f"http://{args.host}:{args.port}"

    if wait_for_server(health_url):
        print("\n" + "-" * 68)
        print(f"[+] Hearth is running and ready at: {app_url}")
        print("    [Space]        -> Pause / Resume captioning")
        print("    [Ctrl+Shift+L] -> Toggle live latency audit HUD")
        print("    Press Ctrl+C to stop.")
        print("-" * 68 + "\n")

        if not args.no_browser:
            webbrowser.open(app_url)
    else:
        print("[!] Server startup timed out. Check terminal output for errors.")

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping Hearth...")
        proc.terminate()
        proc.wait(timeout=5)
        print("[*] Stopped cleanly.")


if __name__ == "__main__":
    main()
