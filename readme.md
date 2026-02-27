# Mahsa-Flux

Large-scale, volunteer-driven VLESS Reality proxy donation system for
[MahsaNG](https://www.mahsaserver.com/) — a free proxy client used by millions
of Iranians to bypass internet censorship.

## Architecture

Each Flux Cloud node runs a single Docker container that:

1. Generates **x25519 Reality keys** and a configurable number of client UUIDs
   (default 8, tunable via `NUM_CONFIGS`).
2. Starts **Xray-core** with VLESS + Reality + xtls-rprx-vision on port 443.
3. Serves a **base64-encoded subscription file** at `/sub?token=<SECRET>` on
   port 8080, protected by a per-node secret token.

A local batch script (`deploy_batch.py`) templates Flux v8 app specs, and a
collector script (`collect_mahsa.py`) fetches configs from all nodes in
parallel for donation to the Mahsa Server pool.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Alpine-based image with Xray-core and Flask |
| `entrypoint.py` | Key generation, config templating, process management |
| `sub_server.py` | Token-protected Flask subscription endpoint |
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
| `LISTEN_PORT` | `443` | Xray listen port |

## Security

- `/sub` endpoint returns **403** without the correct `?token=` parameter.
- Private keys never leave the container or appear in subscription links.
- Reality + uTLS fingerprinting mimics real browser TLS to decoy sites.
- No persistent user data or traffic logs.

## License

See [LICENSE](LICENSE) for details.
