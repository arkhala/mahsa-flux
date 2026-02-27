#!/usr/bin/env python3
"""
Entrypoint for Flux-Mahsa proxy node.
Generates Reality keys, client UUIDs, Xray config, subscription file,
then starts Xray and the protected subscription HTTP server.
"""

import json
import os
import secrets
import socket
import subprocess
import sys
import uuid
from base64 import b64encode
from threading import Thread
from urllib.parse import quote

NUM_CONFIGS = int(os.getenv("NUM_CONFIGS", "8"))
SUB_TOKEN = os.getenv("SUB_TOKEN") or secrets.token_urlsafe(32)
FLUX_APP_NAME = os.getenv("FLUX_APP_NAME", "node")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "31443"))
XRAY_INTERNAL_PORT = int(os.getenv("XRAY_INTERNAL_PORT", "10443"))
SUB_INTERNAL_PORT = int(os.getenv("SUB_INTERNAL_PORT", "10080"))

DECOY_SNIS = [
    "www.microsoft.com",
    "www.apple.com",
    "www.google.com",
    "login.live.com",
    "www.cloudflare.com",
    "www.amazon.com",
]

FINGERPRINTS = ["chrome", "firefox", "safari", "edge"]


def resolve_host():
    """Determine the public hostname or IP for VLESS links."""
    host = os.getenv("FLUX_HOST")
    if host:
        return host
    # Flux apps get a hostname like <appname>_<port>.app.runonflux.io
    if FLUX_APP_NAME != "node":
        return f"{FLUX_APP_NAME}_{LISTEN_PORT}.app.runonflux.io"
    # Fallback: try to get the machine's hostname
    return socket.getfqdn()


def generate_keys():
    """Generate x25519 key pair using Xray."""
    try:
        output = subprocess.check_output(
            ["/usr/local/bin/xray", "x25519"], stderr=subprocess.STDOUT
        ).decode()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"❌ Failed to generate keys: {exc}", file=sys.stderr)
        sys.exit(1)
    private_key = output.split("Private key: ")[1].splitlines()[0].strip()
    public_key = output.split("Public key: ")[1].splitlines()[0].strip()
    return private_key, public_key


def build_configs(public_key, short_id, host):
    """Generate client entries and VLESS subscription links."""
    clients = []
    vless_links = []
    for i in range(NUM_CONFIGS):
        uid = str(uuid.uuid4())
        sni = DECOY_SNIS[i % len(DECOY_SNIS)]
        fp = FINGERPRINTS[i % len(FINGERPRINTS)]
        remark = quote(f"Flux-Mahsa-{FLUX_APP_NAME}-{i + 1}")
        link = (
            f"vless://{uid}@{host}:{LISTEN_PORT}"
            f"?security=reality&encryption=none&pbk={public_key}"
            f"&fp={fp}&sni={sni}&sid={short_id}"
            f"&type=tcp&flow=xtls-rprx-vision&headerType=none"
            f"#{remark}"
        )
        vless_links.append(link)
        clients.append({"id": uid, "flow": "xtls-rprx-vision", "level": 0})
    return clients, vless_links


def write_xray_config(clients, private_key, short_id):
    """Load the template, fill in keys/clients, write final config."""
    with open("/xray_template.json") as f:
        config = json.load(f)
    inbound = config["inbounds"][0]
    inbound["listen"] = "127.0.0.1"
    inbound["port"] = XRAY_INTERNAL_PORT
    inbound["settings"]["clients"] = clients
    reality = inbound["streamSettings"]["realitySettings"]
    reality["privateKey"] = private_key
    reality["shortIds"] = [short_id]
    reality["serverNames"] = DECOY_SNIS[:]
    with open("/xray_config.json", "w") as f:
        json.dump(config, f, indent=2)


def write_subscription(vless_links):
    """Write base64-encoded subscription file (one link per line)."""
    raw = "\n".join(vless_links)
    encoded = b64encode(raw.encode()).decode()
    with open("/sub_content.txt", "w") as f:
        f.write(encoded)


def start_xray():
    """Run Xray in a background thread."""
    def _run():
        proc = subprocess.Popen(
            ["/usr/local/bin/xray", "run", "-c", "/xray_config.json"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        proc.wait()
        print("⚠️  Xray process exited", file=sys.stderr)
        sys.exit(proc.returncode)

    thread = Thread(target=_run, daemon=True)
    thread.start()
    return thread


def main():
    host = resolve_host()
    private_key, public_key = generate_keys()
    short_id = os.urandom(8).hex()

    clients, vless_links = build_configs(public_key, short_id, host)
    write_xray_config(clients, private_key, short_id)
    write_subscription(vless_links)

    # Export token and internal port so sub_server.py can read them
    os.environ["SUB_TOKEN"] = SUB_TOKEN
    os.environ["SUB_INTERNAL_PORT"] = str(SUB_INTERNAL_PORT)

    print(f"✅ Generated {NUM_CONFIGS} independent configs for {host}")
    print(f"   (each instance generates its own keys and UUIDs)")
    print(f"📋 Sub URL: http://{host}:{LISTEN_PORT}/sub?token={SUB_TOKEN}")

    start_xray()

    # Run Flask sub server on internal port (localhost only)
    sub_thread = Thread(
        target=lambda: subprocess.run(
            [sys.executable, "/sub_server.py"], check=False
        ),
        daemon=True,
    )
    sub_thread.start()

    # Run port multiplexer in foreground (keeps container alive)
    subprocess.run([sys.executable, "/port_mux.py"], check=False)


if __name__ == "__main__":
    main()