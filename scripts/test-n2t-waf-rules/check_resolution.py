#!/usr/bin/env python3
"""Check ARK resolution against n2t (staging or production).

Reads ark_spt_sample.jsonl, resolves each base_ark and full_ark via the chosen
n2t resolver, reports pass/fail per ARK plus a summary. Designed for verifying
WAF rule behavior across staging and production.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ENVIRONMENTS = {
    "production": "https://n2t.net",
    "staging": "https://n2t-stg.cdlib.org",
}
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 ark-spt-checker/0.1"
)
DEFAULT_TIMEOUT = 30
DEFAULT_WORKERS = 10

logger = logging.getLogger("ark_check")


def build_url(resolver: str, ark: str) -> str:
    return f"{resolver.rstrip('/')}/{urllib.parse.quote(ark, safe='/:%')}"


def _request(url: str, *, method: str, user_agent: str, timeout: int) -> tuple[int | None, str | None, str | None]:
    """Issue one request, following redirects via urllib's default handler.

    Returns (status, final_url, error). status is None on network/transport failure."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.url, None
    except urllib.error.HTTPError as e:
        final_url = getattr(e, "url", None) or url
        return e.code, final_url, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, None, f"URLError: {e.reason}"
    except (TimeoutError, ConnectionError) as e:
        return None, None, f"{type(e).__name__}: {e}"
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def check_ark(*, resolver: str, ark: str, ark_kind: str, ctx: dict,
              user_agent: str, timeout: int) -> dict:
    """Resolve <resolver>/<ark> via HEAD (with GET fallback on 405). Pass = status < 400."""
    url = build_url(resolver, ark)
    started = time.monotonic()
    status, final_url, err = _request(url, method="HEAD", user_agent=user_agent, timeout=timeout)
    if status == 405:
        status, final_url, err = _request(url, method="GET", user_agent=user_agent, timeout=timeout)
    elapsed_ms = int((time.monotonic() - started) * 1000)
    ok = status is not None and status < 400
    return {
        "ark": ark,
        "ark_kind": ark_kind,
        "request_url": url,
        "status": status,
        "final_url": final_url,
        "elapsed_ms": elapsed_ms,
        "ok": ok,
        "error": err,
        "institution": ctx.get("institution"),
        "naan": ctx.get("naan"),
        "source_method": ctx.get("source_method"),
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning("Bad JSONL line: %s", e)
    return records


def build_work(records: list[dict], check: str) -> list[tuple[str, str, dict]]:
    work: list[tuple[str, str, dict]] = []
    seen: set[tuple[str, str]] = set()
    for r in records:
        ctx = {k: r.get(k) for k in ("institution", "source_method", "naan")}
        if check in ("base", "both"):
            ark = r.get("base_ark")
            if isinstance(ark, str) and ark and ("base", ark) not in seen:
                seen.add(("base", ark))
                work.append((ark, "base", ctx))
        if check in ("full", "both"):
            ark = r.get("full_ark")
            if isinstance(ark, str) and ark and ("full", ark) not in seen:
                seen.add(("full", ark))
                work.append((ark, "full", ctx))
    return work


SCHEMA = [
    "ark", "ark_kind", "request_url", "status", "final_url",
    "elapsed_ms", "ok", "error",
    "institution", "naan", "source_method", "checked_at",
]


def write_results(jsonl_path: Path, csv_path: Path, results: list[dict]) -> None:
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMA)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in SCHEMA})


def print_summary(resolver: str, env_label: str, results: list[dict]) -> None:
    total = len(results)
    passes = sum(1 for r in results if r["ok"])
    fails = total - passes
    logger.info("=" * 64)
    logger.info("Resolver: %s  (env=%s)", resolver, env_label)
    logger.info("Total: %d  Pass: %d (%.1f%%)  Fail: %d (%.1f%%)",
                total, passes,
                100 * passes / total if total else 0.0,
                fails,
                100 * fails / total if total else 0.0)
    status_counts = Counter((r["status"], r["ok"]) for r in results)
    logger.info("By status:")
    for (status, ok), count in sorted(status_counts.items(), key=lambda x: -x[1]):
        tag = "PASS" if ok else "FAIL"
        logger.info("  %s  status=%-5s  count=%d", tag, status, count)
    if fails:
        by_inst_kind = Counter((r["institution"], r["ark_kind"]) for r in results if not r["ok"])
        logger.info("Failures by institution + ark_kind:")
        for (inst, kind), count in by_inst_kind.most_common():
            logger.info("  %s [%s]: %d", inst, kind, count)
        sample = [r for r in results if not r["ok"]][:5]
        logger.info("Sample failures:")
        for r in sample:
            logger.info("  status=%s ark=%s err=%s", r["status"], r["ark"], r["error"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check ARK resolution against n2t.")
    here = Path(__file__).resolve().parent
    parser.add_argument("--input", type=Path, default=here / "data" / "ark_spt_sample.jsonl",
                        help="JSONL dataset to check (default: data/ark_spt_sample.jsonl)")
    parser.add_argument("--env", choices=list(ENVIRONMENTS.keys()), default="production",
                        help=f"resolver environment; sets default --resolver. {ENVIRONMENTS}")
    parser.add_argument("--resolver", type=str, default=None,
                        help="resolver URL override; if unset, derived from --env")
    parser.add_argument("--check", choices=["base", "full", "both"], default="both")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--user-agent", type=str, default=DEFAULT_USER_AGENT)
    parser.add_argument("--limit", type=int, default=0, help="max records (0 = all)")
    parser.add_argument("--output-dir", type=Path, default=here / "data")
    parser.add_argument("--log-level", type=str, default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(message)s")

    resolver = args.resolver or ENVIRONMENTS[args.env]
    env_label = args.env if not args.resolver else "custom"
    logger.info("Resolver: %s (env=%s)", resolver, env_label)

    if not args.input.exists():
        logger.error("Input not found: %s", args.input)
        return 2
    records = load_records(args.input)
    if args.limit > 0:
        records = records[: args.limit]
    logger.info("Loaded %d records from %s", len(records), args.input)

    work = build_work(records, args.check)
    logger.info("Total ARK checks: %d (workers=%d)", len(work), args.workers)
    if not work:
        logger.warning("Nothing to check.")
        return 0

    results: list[dict] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [
            ex.submit(check_ark, resolver=resolver, ark=ark, ark_kind=kind, ctx=ctx,
                      user_agent=args.user_agent, timeout=args.timeout)
            for ark, kind, ctx in work
        ]
        for i, fut in enumerate(as_completed(futures), 1):
            results.append(fut.result())
            if i % 100 == 0 or i == len(work):
                pass_count = sum(1 for x in results if x["ok"])
                logger.info("Progress: %d/%d (pass: %d, fail: %d)",
                            i, len(work), pass_count, i - pass_count)
    elapsed = time.monotonic() - started
    logger.info("Completed %d checks in %.1fs", len(results), elapsed)

    results.sort(key=lambda x: (x["ark_kind"], x["ark"]))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = args.output_dir / f"resolution_results_{env_label}.jsonl"
    out_csv = args.output_dir / f"resolution_results_{env_label}.csv"
    write_results(out_jsonl, out_csv, results)
    logger.info("Wrote results to %s and %s", out_jsonl, out_csv)

    print_summary(resolver, env_label, results)
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
