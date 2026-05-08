#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
import time
from typing import Callable, Optional
from urllib.parse import urlsplit

try:
    import requests
except ImportError:
    sys.stderr.write("This script requires `requests`. Install with: pip install requests\n")
    sys.exit(2)


DEFAULT_TIMEOUT = 15
USER_AGENT = "n2t-api-tests/1.0"

IDENTIFIERS = {
    "ark":   "ark:/13030/tf5p30086k",
    "doi":   "doi:10.1000/182",
    "hdl":   "hdl:20.1000/100",
    "urn":   "urn:isbn:0451450523",
    "pmid":  "pmid:26171158",
    "orcid": "orcid:0000-0001-5109-3700",
    "isbn":  "isbn:9780553573404",
    "issn":  "issn:1476-4687",
    "pdb":   "pdb:1A3N",
    "arxiv": "arXiv:1501.00001",
}

INFLECTIONS = ["?", "??", "???", "?info"]

ACCEPT_FAMILIES = [
    ("text/html",                 "html"),
    ("application/json",          "json"),
    ("text/turtle",               "turtle"),
    ("application/rdf+xml",       "rdf"),
    ("application/citeproc+json", "citeproc"),
]


class _CIDict(dict):
    def __init__(self, items):
        super().__init__()
        self._lc = {}
        for k, v in items.items() if hasattr(items, "items") else items:
            self[k] = v
            self._lc[k.lower()] = v

    def get(self, key, default=None):
        return self._lc.get(key.lower(), default)

    def __contains__(self, key):
        return key.lower() in self._lc

    def __getitem__(self, key):
        return self._lc[key.lower()]


@dataclasses.dataclass
class Response:
    url: str
    method: str
    status: int
    headers: _CIDict
    body_excerpt: str
    redirect_chain: list
    elapsed_ms: int


def http_request(method: str, url: str, *, accept: Optional[str] = None,
                 timeout: int = DEFAULT_TIMEOUT, follow: bool = False) -> Response:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    t0 = time.time()
    r = requests.request(method, url, headers=headers,
                         allow_redirects=follow, timeout=timeout)
    elapsed = int((time.time() - t0) * 1000)
    chain = [(h.status_code, h.headers.get("Location", "")) for h in r.history]
    body = ""
    if method != "HEAD":
        try:
            body = r.text[:500]
        except Exception:
            body = "<unreadable body>"
    return Response(url, method, r.status_code, _CIDict(r.headers),
                    body, chain, elapsed)


@dataclasses.dataclass
class Result:
    name: str
    status: str
    detail: str
    response: Optional[Response] = None


@dataclasses.dataclass
class TestCase:
    name: str
    fn: Callable[[str], Result]

    def run(self, base_url: str) -> Result:
        try:
            return self.fn(base_url)
        except requests.RequestException as e:
            return Result(self.name, "FAIL", f"network error: {e}")
        except AssertionError as e:
            return Result(self.name, "FAIL", str(e))
        except Exception as e:
            return Result(self.name, "FAIL", f"unexpected: {type(e).__name__}: {e}")


def _build_url(base: str, identifier: str, inflection: str = "") -> str:
    return f"{base.rstrip('/')}/{identifier}{inflection}"


def t_resolve(scheme: str, ident: str) -> TestCase:
    name = f"resolve/{scheme}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url)
        if r.status == 429:
            return Result(name, "SKIP", "rate-limited (429)", r)
        if r.status == 404:
            return Result(name, "SKIP",
                          "404 — id or scheme unsupported on this host", r)
        if r.status not in (301, 302, 303, 307, 308):
            return Result(name, "FAIL",
                          f"expected redirect, got {r.status} for {url}", r)
        loc = r.headers.get("Location", "")
        if not loc:
            return Result(name, "FAIL", "redirect without Location header", r)
        if not re.match(r"^https?://", loc):
            return Result(name, "FAIL",
                          f"Location not absolute http(s): {loc!r}", r)
        return Result(name, "PASS",
                      f"{r.status} -> {loc} ({r.elapsed_ms}ms)", r)

    return TestCase(name, fn)


def t_inflection(scheme: str, ident: str, inflection: str) -> TestCase:
    safe_inf = inflection.replace("?", "Q")
    name = f"inflection/{scheme}/{safe_inf}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident, inflection)
        r = http_request("GET", url, follow=False)
        if r.status not in (200, 301, 302, 303, 307, 308):
            return Result(name, "FAIL",
                          f"expected 2xx/3xx, got {r.status}", r)
        ctype = r.headers.get("Content-Type", "")
        loc = r.headers.get("Location", "")
        return Result(name, "PASS",
                      f"{r.status} ctype={ctype!r} loc={loc[:80]!r}", r)

    return TestCase(name, fn)


def t_content_negotiation(scheme: str, ident: str, accept: str, label: str) -> TestCase:
    name = f"negotiate/{scheme}/{label}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url, accept=accept, follow=False)
        if r.status not in (200, 301, 302, 303, 307, 308):
            return Result(name, "FAIL", f"Accept={accept} got {r.status}", r)
        ctype = r.headers.get("Content-Type", "")
        loc = r.headers.get("Location", "")
        return Result(name, "PASS",
                      f"Accept={accept} -> {r.status} loc={loc[:80]!r} ctype={ctype!r}", r)

    return TestCase(name, fn)


def t_suffix_passthrough() -> TestCase:
    name = "suffix_passthrough/ark"
    ident = "ark:/99999/fk4f30n/doc1"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url)
        if r.status not in (301, 302, 303):
            return Result(name, "FAIL", f"expected redirect, got {r.status}", r)
        loc = r.headers.get("Location", "")
        if "doc1" not in loc:
            return Result(name, "FAIL",
                          f"suffix 'doc1' not present in Location: {loc}", r)
        return Result(name, "PASS", f"-> {loc}", r)

    return TestCase(name, fn)


def t_hierarchical_fallback() -> TestCase:
    name = "hierarchical_fallback/ark"
    ident = "ark:/13030/tf5p30086k/no/such/path"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url)
        if r.status >= 500:
            return Result(name, "FAIL",
                          f"server error on hierarchical fallback: {r.status}", r)
        if r.status in (200, 301, 302, 303):
            return Result(name, "PASS",
                          f"{r.status} (ancestor lookup honored)", r)
        return Result(name, "FAIL",
                      f"unexpected status {r.status} on hierarchical fallback", r)

    return TestCase(name, fn)


def t_prefix_introspection(prefix: str) -> TestCase:
    name = f"prefix_info/{prefix}"

    def fn(base: str) -> Result:
        url = f"{base.rstrip('/')}/{prefix}:"
        r = http_request("GET", url, follow=True)
        if r.status == 429:
            return Result(name, "SKIP", "rate-limited (429)", r)
        if r.status == 404:
            return Result(name, "SKIP",
                          "prefix not registered on this host (404)", r)
        if r.status != 200:
            return Result(name, "FAIL",
                          f"expected 200 for prefix listing, got {r.status}", r)
        if len(r.body_excerpt) == 0:
            return Result(name, "FAIL", "empty prefix listing body", r)
        return Result(name, "PASS", f"200 ({len(r.body_excerpt)}c excerpt)", r)

    return TestCase(name, fn)


def t_error_malformed() -> TestCase:
    name = "error/malformed_ark"
    ident = "ark:/notanaan/foo"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url, follow=True)
        if 500 <= r.status < 600:
            return Result(name, "FAIL",
                          f"server error {r.status} on malformed id", r)
        return Result(name, "PASS", f"{r.status} (graceful)", r)

    return TestCase(name, fn)


def t_error_unknown_scheme() -> TestCase:
    name = "error/unknown_scheme"
    ident = "zzzznotascheme:foo"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url, follow=True)
        if 500 <= r.status < 600:
            return Result(name, "FAIL",
                          f"server error {r.status} on unknown scheme", r)
        return Result(name, "PASS", f"{r.status} (graceful)", r)

    return TestCase(name, fn)


def t_idempotency(scheme: str, ident: str) -> TestCase:
    name = f"idempotency/{scheme}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        a = http_request("GET", url)
        b = http_request("GET", url)
        if a.status != b.status:
            return Result(name, "FAIL",
                          f"status differs: {a.status} vs {b.status}", a)
        if a.headers.get("Location") != b.headers.get("Location"):
            return Result(name, "FAIL",
                          f"Location differs: {a.headers.get('Location')} vs "
                          f"{b.headers.get('Location')}", a)
        return Result(name, "PASS",
                      f"stable: {a.status} {a.headers.get('Location')}", a)

    return TestCase(name, fn)


def t_head_vs_get(scheme: str, ident: str) -> TestCase:
    name = f"head_vs_get/{scheme}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        g = http_request("GET", url)
        h = http_request("HEAD", url)
        if g.status != h.status:
            return Result(name, "FAIL",
                          f"status differs GET={g.status} HEAD={h.status}", g)
        if g.headers.get("Location") != h.headers.get("Location"):
            return Result(name, "FAIL",
                          "Location differs between HEAD and GET", g)
        return Result(name, "PASS", f"GET=HEAD={g.status}", g)

    return TestCase(name, fn)


def t_https_upgrade() -> TestCase:
    name = "protocol/https_upgrade"

    def fn(base: str) -> Result:
        parts = urlsplit(base)
        if parts.scheme != "https":
            return Result(name, "SKIP",
                          "base-url is not https; skipping upgrade test")
        http_url = f"http://{parts.netloc}/ark:/13030/tf5p30086k"
        r = http_request("GET", http_url)
        if r.status not in (301, 302, 307, 308):
            return Result(name, "FAIL",
                          f"expected http->https redirect, got {r.status}", r)
        loc = r.headers.get("Location", "")
        if not loc.startswith("https://"):
            return Result(name, "FAIL",
                          f"http upgrade did not go to https: {loc}", r)
        return Result(name, "PASS", f"{r.status} -> {loc}", r)

    return TestCase(name, fn)


def t_response_headers(scheme: str, ident: str) -> TestCase:
    name = f"headers/{scheme}"

    def fn(base: str) -> Result:
        url = _build_url(base, ident)
        r = http_request("GET", url)
        if "Server" not in r.headers:
            return Result(name, "FAIL", "missing Server header", r)
        cc = r.headers.get("Cache-Control", "<absent>")
        return Result(name, "PASS",
                      f"Server={r.headers.get('Server')!r} Cache-Control={cc!r}", r)

    return TestCase(name, fn)


def all_tests() -> list[TestCase]:
    tests: list[TestCase] = []
    for scheme, ident in IDENTIFIERS.items():
        tests.append(t_resolve(scheme, ident))
    for scheme in ("ark", "doi"):
        for inf in INFLECTIONS:
            tests.append(t_inflection(scheme, IDENTIFIERS[scheme], inf))
    for scheme in ("ark", "doi"):
        for accept, label in ACCEPT_FAMILIES:
            tests.append(t_content_negotiation(scheme, IDENTIFIERS[scheme], accept, label))
    tests.append(t_suffix_passthrough())
    tests.append(t_hierarchical_fallback())
    for prefix in ("ark", "doi", "urn", "hdl", "pmid"):
        tests.append(t_prefix_introspection(prefix))
    tests.append(t_error_malformed())
    tests.append(t_error_unknown_scheme())
    tests.append(t_https_upgrade())
    for scheme in ("ark", "doi"):
        tests.append(t_idempotency(scheme, IDENTIFIERS[scheme]))
        tests.append(t_head_vs_get(scheme, IDENTIFIERS[scheme]))
        tests.append(t_response_headers(scheme, IDENTIFIERS[scheme]))
    return tests


COLOR = {
    "PASS":  "\033[32m",
    "FAIL":  "\033[31m",
    "SKIP":  "\033[33m",
    "RESET": "\033[0m",
}


def fmt(status: str, use_color: bool) -> str:
    if not use_color:
        return status
    return f"{COLOR.get(status, '')}{status}{COLOR['RESET']}"


def run(tests: list[TestCase], base_url: str, verbose: bool, use_color: bool) -> list[Result]:
    results = []
    width = max(len(t.name) for t in tests)
    for t in tests:
        res = t.run(base_url)
        results.append(res)
        print(f"  {fmt(res.status, use_color):>4}  {t.name:<{width}}  {res.detail}")
        if verbose and res.response is not None:
            r = res.response
            print(f"        url: {r.url}")
            print(f"        status: {r.status}  elapsed: {r.elapsed_ms}ms")
            for k, v in r.headers.items():
                print(f"        {k}: {v}")
            if r.redirect_chain:
                print(f"        chain: {r.redirect_chain}")
            if r.body_excerpt:
                excerpt = r.body_excerpt.replace("\n", " ")[:200]
                print(f"        body: {excerpt!r}")
    return results


def summarize(results: list[Result]) -> tuple[int, int, int]:
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    return passed, failed, skipped


def main() -> int:
    global DEFAULT_TIMEOUT
    p = argparse.ArgumentParser(description="Test the N2T resolver API.")
    p.add_argument("--base-url", required=True,
                   help="N2T base URL, e.g. https://n2t.net or https://n2t-stg.n2t.net")
    p.add_argument("--filter", default=None, help="Regex to select test names.")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--json", action="store_true",
                   help="Emit JSON results to stdout.")
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args()
    DEFAULT_TIMEOUT = args.timeout

    tests = all_tests()
    if args.filter:
        rx = re.compile(args.filter)
        tests = [t for t in tests if rx.search(t.name)]
        if not tests:
            print(f"No tests matched filter {args.filter!r}", file=sys.stderr)
            return 2

    use_color = sys.stdout.isatty() and not args.no_color and not args.json

    if args.json:
        results = [t.run(args.base_url) for t in tests]
        out = {
            "base_url": args.base_url,
            "summary": dict(zip(("pass", "fail", "skip"), summarize(results))),
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "detail": r.detail,
                    "response": dataclasses.asdict(r.response) if r.response else None,
                }
                for r in results
            ],
        }
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"Running {len(tests)} tests against {args.base_url}\n")
        results = run(tests, args.base_url, args.verbose, use_color)
        passed, failed, skipped = summarize(results)
        print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
        if failed:
            print("\nFailures:")
            for r in results:
                if r.status == "FAIL":
                    print(f"  - {r.name}: {r.detail}")

    _, failed, _ = summarize(results)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
