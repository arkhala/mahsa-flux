import os, json, uuid, subprocess, base64, secrets
from threading import Thread

NUM_CONFIGS = int(os.getenv("NUM_CONFIGS", "8"))
SUB_TOKEN = os.getenv("SUB_TOKEN")  # Required
DECOY_SNIS = ["www.microsoft.com", "www.apple.com", "www.google.com", "login.live.com"]

# Generate shared Reality keys
keys = subprocess.check_output(["/usr/local/bin/xray", "x25519"]).decode()
private_key = keys.split("Private key: ")[1].splitlines()[0].strip()
public_key = keys.split("Public key: ")[1].splitlines()[0].strip()
short_id = os.urandom(8).hex()

clients = []
vless_links = []

for i in range(NUM_CONFIGS):
    uid = str(uuid.uuid4())
    sni = DECOY_SNIS[i % len(DECOY_SNIS)]
    remark = f"Flux-Mahsa-{os.getenv('FLUX_APP_NAME','node')}-{i+1}"
    link = f"vless://{uid}@{{IP}}:443?security=reality&encryption=none&pbk={public_key}&fp=chrome&sni={sni}&sid={short_id}&type=tcp&flow=xtls-rprx-vision&headerType=none#{remark}"
    vless_links.append(link)
    clients.append({"id": uid, "flow": "xtls-rprx-vision", "level": 0})

# Fill Xray config
with open("/xray_template.json") as f:
    config = json.load(f)
config["inbounds"][0]["settings"]["clients"] = clients
config["inbounds"][0]["streamSettings"]["realitySettings"]["privateKey"] = private_key
config["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"] = [short_id]

with open("/xray_config.json", "w") as f:
    json.dump(config, f, indent=2)

# Base64 sub content (Mahsa parses each line as separate config)
sub_content = base64.b64encode("\n".join(vless_links).encode()).decode()
with open("/sub_content.txt", "w") as f:
    f.write(sub_content)

print(f"✅ Generated {NUM_CONFIGS} configs. Token-protected sub ready.")

# Start Xray
Thread(target=lambda: os.system("/usr/local/bin/xray run -c /xray_config.json")).start()

# Start protected sub server
os.system("python3 /sub_server.py")