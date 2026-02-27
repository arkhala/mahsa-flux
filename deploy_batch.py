#!/usr/bin/env python3
"""
deploy_batch.py — Batch-deploy Mahsa proxy nodes on Flux Cloud.

Generates Flux app specs (version 8) for multiple instances and prints
the API payloads. Actual deployment requires Flux wallet signature via
the Flux API; this script templates the specs.

Usage:
    python3 deploy_batch.py --start 1 --count 50 --image ghcr.io/arkhala/flux-mahsa-multi-reality:latest

Environment:
    FLUX_OWNER   — Flux wallet owner address (required for real deployment)
"""

import argparse
import json
import os
import secrets
import sys


def make_flux_spec(app_name, image, num_configs, sub_token):
    """Return a Flux compose-style v8 spec for a single node."""
    return {
        "version": 8,
        "name": app_name,
        "description": f"Mahsa proxy donation node {app_name}",
        "owner": "",  # Fill via FLUX_OWNER or wallet
        "compose": [
            {
                "name": app_name,
                "description": f"VLESS Reality proxy — {num_configs} configs",
                "repotag": image,
                "ports": ["443:443", "8080:8080"],
                "domains": [],
                "environmentParameters": [
                    f"NUM_CONFIGS={num_configs}",
                    f"FLUX_APP_NAME={app_name}",
                    f"SUB_TOKEN={sub_token}",
                ],
                "commands": [],
                "containerPorts": [443, 8080],
                "containerData": "",
                "cpu": 0.5,
                "ram": 300,
                "hdd": 1,
                "tiered": False,
            }
        ],
        "instances": 1,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate Flux app specs for Mahsa proxy nodes"
    )
    parser.add_argument(
        "--start", type=int, default=1, help="Starting node number (default: 1)"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of nodes to deploy (default: 10)"
    )
    parser.add_argument(
        "--image",
        default="ghcr.io/arkhala/flux-mahsa-multi-reality:latest",
        help="Docker image tag",
    )
    parser.add_argument(
        "--configs", type=int, default=8, help="NUM_CONFIGS per node (default: 8)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file for specs JSON (default: stdout)",
    )
    args = parser.parse_args()

    specs = []
    manifest = []  # app_name → token mapping for collect_mahsa.py

    for i in range(args.start, args.start + args.count):
        app_name = f"mahsa-donor-{i:04d}"
        sub_token = secrets.token_urlsafe(32)
        spec = make_flux_spec(app_name, args.image, args.configs, sub_token)
        specs.append(spec)
        manifest.append(
            {
                "app_name": app_name,
                "sub_token": sub_token,
                "sub_url": (
                    f"http://{app_name}_8080.app.runonflux.io"
                    f"/sub?token={sub_token}"
                ),
            }
        )

    result = {"specs": specs, "manifest": manifest}

    if args.output:
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2)
        print(
            f"✅ Generated {args.count} specs → {args.output}",
            file=sys.stderr,
        )

        # Also write individual spec files for manual Flux upload
        out_dir = args.output.rsplit(".", 1)[0] + "_specs"
        os.makedirs(out_dir, exist_ok=True)
        for spec in specs:
            spec_path = os.path.join(out_dir, f"{spec['name']}.json")
            with open(spec_path, "w") as f:
                json.dump(spec, f, indent=2)
        print(
            f"📂 Individual specs → {out_dir}/",
            file=sys.stderr,
        )
    else:
        json.dump(result, sys.stdout, indent=2)
        print(file=sys.stdout)

    print(
        f"📋 {args.count} nodes: "
        f"{specs[0]['name']} … {specs[-1]['name']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
