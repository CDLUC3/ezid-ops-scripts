# N2T API Tests

Read-only test suite for the [N2T](https://n2t.net/api) (Name-to-Thing) resolver.

## Install

```sh
pip install requests
```

## Usage

```sh
python3 test_n2t_api.py --base-url https://n2t.net
python3 test_n2t_api.py --base-url https://n2t-stg.cdlib.org
```

Exits non-zero if any test fails.

### Flags

| Flag | Description |
|---|---|
| `--base-url URL` | Required. N2T host to test. |
| `--filter REGEX` | Run only tests whose names match. |
| `--verbose` | Dump full headers, body excerpt, redirect chain. |
| `--timeout N` | Per-request timeout in seconds (default 15). |
| `--json` | Emit JSON results to stdout. |
| `--no-color` | Disable ANSI color. |

## Coverage

- Resolution across schemes `ark`, `doi`, `hdl`, `urn`, `pmid`, `orcid`, `isbn`, `issn`, `pdb`, `arxiv`
- Inflections `?`, `??`, `???`, `?info` (ARK + DOI)
- Content negotiation for `text/html`, `application/json`, `text/turtle`, `application/rdf+xml`, `application/citeproc+json`
- Suffix passthrough (ARK)
- Hierarchical ancestor fallback (ARK)
- Prefix introspection (`/<prefix>:`)
- Error handling of malformed identifiers and unknown scheme
- HTTPS upgrade, HEAD vs GET parity, idempotency, response headers

## Result codes

- `PASS` — assertions held
- `FAIL` — unexpected status, missing header, or network error
- `SKIP` — endpoint unsupported on this host (404) or rate-limited (429)

## Examples

```sh
python3 test_n2t_api.py --base-url https://n2t.net --filter inflection --verbose
python3 test_n2t_api.py --base-url https://n2t.net --json > results.json
python3 test_n2t_api.py --base-url https://n2t.net --filter 'resolve/(ark|doi)'
```