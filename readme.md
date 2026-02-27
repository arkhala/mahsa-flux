# Mahsa-Flux

Large-scale, volunteer-driven VLESS Reality proxy donation system for
[MahsaNG](https://www.mahsaserver.com/) — a free proxy client used by millions
of Iranians to bypass internet censorship.

## Architecture

Each Flux Cloud node runs a single Docker container that:

1. Generates **x25519 Reality keys** and a configurable number of client UUIDs
   (default 8, tunable via `NUM_CONFIGS`).
2. Starts **Xray-core** with VLESS + Reality + xtls-rprx-vision on an internal
   port (default 10443, not directly exposed).
3. Runs a **base64-encoded subscription server** at `/sub?token=<SECRET>` on an
   internal port (default 10080, not directly exposed).
4. A **TCP port multiplexer** listens on a single exposed port (default 31443)
   and routes TLS traffic to Xray and plain HTTP requests to the subscription
   server.  This keeps the Flux app spec to **one port**, reducing instance cost.

A local batch script (`deploy_batch.py`) templates Flux v8 app specs, and a
collector script (`collect_mahsa.py`) fetches configs from all nodes in
parallel for donation to the Mahsa Server pool.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Alpine-based image with Xray-core and Flask |
| `entrypoint.py` | Key generation, config templating, process management |
| `sub_server.py` | Token-protected Flask subscription endpoint |
| `port_mux.py` | TCP multiplexer — single-port TLS/HTTP routing |
| `xray_template.json` | Xray inbound/outbound template |
| `deploy_batch.py` | Batch Flux app spec generator |
| `collect_mahsa.py` | Parallel subscription collector |

## Quick Start

### Build and push the Docker image

```bash
docker build -t ghcr.io/<owner>/flux-mahsa-multi-reality:latest .
docker push ghcr.io/<owner>/flux-mahsa-multi-reality:latest
```

### Generate Flux deployment specs

```bash
python3 deploy_batch.py --start 1 --count 50 --output deploy.json
```

### Collect subscriptions from running nodes

```bash
pip install aiohttp
python3 collect_mahsa.py --manifest deploy.json --output all_configs.txt
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NUM_CONFIGS` | `8` | Client UUIDs per node (6–12 recommended) |
| `SUB_TOKEN` | auto-generated | Secret token for `/sub` endpoint |
| `FLUX_APP_NAME` | `node` | Used in VLESS link remarks and hostname |
| `FLUX_HOST` | auto-derived | Override public hostname/IP |
| `LISTEN_PORT` | `31443` | Single exposed port (multiplexer) |
| `XRAY_INTERNAL_PORT` | `10443` | Internal Xray listen port (localhost) |
| `SUB_INTERNAL_PORT` | `10080` | Internal subscription server port (localhost) |

## Security

- `/sub` endpoint returns **403** without the correct `?token=` parameter.
- Private keys never leave the container or appear in subscription links.
- Reality + uTLS fingerprinting mimics real browser TLS to decoy sites.
- No persistent user data or traffic logs.

## License

See [LICENSE](LICENSE) for details.
