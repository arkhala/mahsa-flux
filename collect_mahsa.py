#!/usr/bin/env python3
"""
collect_mahsa.py — Collect subscription configs from deployed Mahsa proxy nodes.

Reads a manifest JSON (produced by deploy_batch.py) and fetches each node's
/sub?token=... endpoint in parallel.  Outputs a combined base64 subscription
or individual VLESS links.

Usage:
    python3 collect_mahsa.py --manifest manifest.json
    python3 collect_mahsa.py --manifest manifest.json --raw  # raw VLESS links
"""

import argparse
import asyncio
import json
import sys
from base64 import b64decode, b64encode

try:
    import aiohttp
except ImportError:
    aiohttp = None


async def fetch_sub(session, entry, timeout):
    """Fetch a single node's subscription."""
    url = entry["sub_url"]
    name = entry["app_name"]
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                body = await resp.text()
                try:
                    decoded = b64decode(body).decode()
                except Exception:
                    decoded = body
                links = [l.strip() for l in decoded.splitlines() if l.strip()]
                print(f"  ✅ {name}: {len(links)} configs", file=sys.stderr)
                return links
            else:
                print(
                    f"  ❌ {name}: HTTP {resp.status}", file=sys.stderr
                )
                return []
    except Exception as exc:
        print(f"  ⚠️  {name}: {exc}", file=sys.stderr)
        return []


async def collect_all(manifest, timeout, concurrency):
    """Fetch all nodes concurrently."""
    sem = asyncio.Semaphore(concurrency)
    all_links = []

    async def _bounded(session, entry):
        async with sem:
            return await fetch_sub(session, entry, timeout)

    async with aiohttp.ClientSession() as session:
        tasks = [_bounded(session, e) for e in manifest]
        results = await asyncio.gather(*tasks)
        for links in results:
            all_links.extend(links)
    return all_links


def main():
    if aiohttp is None:
        print(
            "❌ aiohttp is required: pip install aiohttp",
            file=sys.stderr,
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Collect subscription links from Mahsa proxy nodes"
    )
    parser.add_argument(
        "--manifest", required=True, help="Path to manifest JSON from deploy_batch.py"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw VLESS links instead of base64",
    )
    parser.add_argument(
        "--timeout", type=int, default=15, help="HTTP timeout per node in seconds"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Max concurrent requests (default: 20)",
    )
    parser.add_argument(
        "--output", default=None, help="Output file (default: stdout)"
    )
    args = parser.parse_args()

    with open(args.manifest) as f:
        data = json.load(f)

    # Accept both full deploy_batch output and plain manifest list
    manifest = data.get("manifest", data) if isinstance(data, dict) else data

    print(
        f"🔍 Collecting from {len(manifest)} nodes …", file=sys.stderr
    )
    links = asyncio.run(collect_all(manifest, args.timeout, args.concurrency))

    if not links:
        print("⚠️  No configs collected.", file=sys.stderr)
        sys.exit(1)

    if args.raw:
        output = "\n".join(links) + "\n"
    else:
        output = b64encode("\n".join(links).encode()).decode() + "\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(
            f"✅ {len(links)} configs → {args.output}", file=sys.stderr
        )
    else:
        sys.stdout.write(output)

    print(f"📊 Total configs collected: {len(links)}", file=sys.stderr)


if __name__ == "__main__":
    main()
