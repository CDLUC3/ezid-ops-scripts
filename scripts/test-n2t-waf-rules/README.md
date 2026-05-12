# ARK SPT resolution checker

Script for testing WAF rules on N2T. Attempts to resolve each `base_ark` and `full_ark` in `data/ark_spt_sample.jsonl` against N2T and reports pass/fail. 

## Prerequisites

- Python 3 (stdlib only, no deps)
- `data/ark_spt_sample.jsonl`

## Usage

```bash
# n2t.net (production)
python3 check_resolution.py

# n2t-stg.cdlib.org (staging)
python3 check_resolution.py --env n2t-staging

# arks.org (production)
python3 check_resolution.py --env arks

# arks-stg.cdlib.org (staging)
python3 check_resolution.py --env arks-staging

# Custom resolver (overrides --env)
python3 check_resolution.py --resolver https://custom.example.com

# Only the file-passthrough ARKs (skip base ARK lookups)
python3 check_resolution.py --check full

# Limit checks
python3 check_resolution.py --limit 50
```

Defaults: `--env n2t-production`, `--check both`, `--workers 10`, `--timeout 30`.

| Env              | URL                            |
| ---------------- | ------------------------------ |
| `n2t-production` | `https://n2t.net`              |
| `n2t-staging`    | `https://n2t-stg.cdlib.org`    |
| `arks`           | `https://arks.org`             |
| `arks-staging`   | `https://arks-stg.cdlib.org`   |

## Behavior

- HEAD with GET fallback on 405; follows redirects via urllib's default handler.
- Pass = final status `< 400`. Fail = 4xx/5xx or transport error.
- URL-encodes spaces and other unsafe chars in suffixes.
- 10 threads by default.

## Output

Per-environment files in `data/`, sorted by `(ark_kind, ark)`:

- `resolution_results_<env>.jsonl` — one record per ARK with
  `ark, ark_kind (base|full), request_url, status, final_url, elapsed_ms, ok,
  error, institution, naan, source_method, checked_at`.
- `resolution_results_<env>.csv` — same fields, flattened.

Console prints a summary: pass/fail counts, status-code histogram, and
failure breakdown by institution + ark_kind with sample errors.

Diff staging vs production:

```bash
diff <(jq -c '{ark,status,ok}' data/resolution_results_n2t-staging.jsonl) \
     <(jq -c '{ark,status,ok}' data/resolution_results_n2t-production.jsonl)
```

Exit code: `0` if all pass, `1` if any failed.
