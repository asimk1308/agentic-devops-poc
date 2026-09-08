#!/usr/bin/env python3
"""
Traffic generator for the Order Service (Spec Section 17/21).

Fault injection alone (scripts/inject_latency.sh / inject_failure.sh)
doesn't move Prometheus's rate()-based queries -- get_latency_metrics()
and get_error_rate() are windowed rates over real request traffic, so
there needs to be actual traffic for a fault to show up in them. This
generates a steady stream of real POST/GET /orders requests, stdlib-only
(no ai-agent venv needed) since it's meant to run standalone during a
demo, from a second terminal, while the fault is active.

Usage:
    python3 scripts/generate_load.py                  # 30s, ~5 req/s
    python3 scripts/generate_load.py --duration 60 --rate 10
"""
import argparse
import json
import random
import threading
import time
import urllib.error
import urllib.request

ITEMS = ["widget", "gadget", "gizmo", "sprocket"]


def _request(base_url: str, results: list) -> None:
    try:
        body = json.dumps(
            {"item": random.choice(ITEMS), "quantity": random.randint(1, 5)}
        ).encode()
        req = urllib.request.Request(
            f"{base_url}/orders",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception as exc:  # noqa: BLE001 -- connection refused, timeout, etc.
        status = f"ERROR: {exc}"
    finally:
        elapsed_ms = (time.monotonic() - start) * 1000 if "start" in locals() else 0
        results.append((status, elapsed_ms))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--duration", type=float, default=30, help="seconds")
    parser.add_argument("--rate", type=float, default=5, help="requests/second")
    args = parser.parse_args()

    interval = 1.0 / args.rate
    results: list = []
    threads: list[threading.Thread] = []
    deadline = time.monotonic() + args.duration

    print(
        f"Generating load against {args.base_url} for {args.duration:.0f}s "
        f"at ~{args.rate}/s ... (Ctrl+C to stop early)"
    )
    try:
        while time.monotonic() < deadline:
            t = threading.Thread(target=_request, args=(args.base_url, results))
            t.start()
            threads.append(t)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nstopping early...")

    for t in threads:
        t.join(timeout=15)

    total = len(results)
    errors = sum(1 for status, _ in results if status != 201)
    latencies = sorted(ms for _, ms in results)
    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0

    print(f"\nsent: {total}  errors: {errors} ({errors / total:.1%})" if total else "sent: 0")
    if latencies:
        print(f"client-observed latency: p50={p50:.0f}ms p95={p95:.0f}ms")


if __name__ == "__main__":
    main()
