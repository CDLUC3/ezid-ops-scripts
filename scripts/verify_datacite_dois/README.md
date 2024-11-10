# DOI Verification Tool

Check DOIs against both DataCite and Crossref APIs and optionally test their resolution.

## How It Works

1. The script loads the default configuration or one provided as an argument
2. For each DOI in the input CSV file:
   - Normalizes and validates the DOI 
   - Queries either the DataCite or Crossref API to check if the DOI exists
   - Optionally checks DOI resolution
   - Optionally saves JSON and XML responses
3. Results are written to a CSV file

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python verify_doi.py -i INPUT_FILE [-p {datacite,crossref}] [-d OUTPUT_DIR] [-c CONFIG_FILE] 
                     [-v] [-t THREADS] [-j] [-x] [--check-resolution] 
                     [--resolution-timeout TIMEOUT] [--max-redirects REDIRECTS]
                     [--datacite-rate-limit-calls CALLS] [--datacite-rate-limit-period PERIOD]
                     [--crossref-rate-limit-calls CALLS] [--crossref-rate-limit-period PERIOD]
```

### Command-line Arguments

- `-i INPUT_FILE`, `--input_file INPUT_FILE`: CSV file containing DOIs to verify (required)
- `-p PROVIDER`, `--provider PROVIDER`: DOI provider to use ('datacite' or 'crossref')
- `-d OUTPUT_DIR`, `--output_dir OUTPUT_DIR`: Output directory for results (default: "results")
- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Configuration file path
- `-v`, `--verbose`: Enable verbose logging
- `-t THREADS`, `--threads THREADS`: Number of verification threads
- `-j`, `--json`: Save JSON responses from API
- `-x`, `--xml`: Save XML responses from API
- `--check-resolution`: Enable DOI resolution checking through doi.org
- `--resolution-timeout TIMEOUT`: Timeout for resolution checking in seconds
- `--max-redirects REDIRECTS`: Maximum number of redirects to follow
- `--datacite-rate-limit-calls`: Number of calls allowed for DataCite rate limiting
- `--datacite-rate-limit-period`: Period in seconds for DataCite rate limiting
- `--crossref-rate-limit-calls`: Number of calls allowed for Crossref rate limiting
- `--crossref-rate-limit-period`: Period in seconds for Crossref rate limiting

## Configuration

If no config file is provided, the below default config will be used:

```json
{
    "parallel": false,
    "max_threads": 1,
    "check_resolution": false,
    "resolution_timeout": 30,
    "max_redirects": 5,
    "save_xml": false,
    "save_json": false,
    "datacite_rate_limit_calls": 3000,
    "datacite_rate_limit_period": 300,
    "crossref_rate_limit_calls": 50,
    "crossref_rate_limit_period": 1
}
```

### Example Configuration File

```json
{
    "parallel": true,
    "max_threads": 4,
    "check_resolution": true,
    "resolution_timeout": 60,
    "max_redirects": 10,
    "save_xml": true,
    "save_json": true,
    "provider": "crossref",
    "datacite_rate_limit_calls": 3000,
    "datacite_rate_limit_period": 300,
    "crossref_rate_limit_calls": 50,
    "crossref_rate_limit_period": 1
}
```

## Output

### Files Generated

- `{output_dir}/verification_report.csv`: Main verification results
- `{output_dir}/error_log.log`: Detailed error logging
- `{output_dir}/application.log`: Application-level logging
- If JSON saving is enabled:
  - `{output_dir}/json_responses/datacite/{doi}.json`: JSON responses from DataCite
  - `{output_dir}/json_responses/crossref/{doi}.json`: JSON responses from Crossref
- If XML saving is enabled:
  - `{output_dir}/xml_responses/datacite/{doi}.xml`: XML responses from DataCite
  - `{output_dir}/xml_responses/crossref/{doi}.xml`: XML responses from Crossref

### Directory Structure
```
output_dir/
├── verification_report.csv
├── error_log.log
├── application.log
│
├── json_responses/ (if JSON saving is enabled)
│   ├── datacite/
│   │   ├── 10.1234_abc123.json
│   │   └── ...
│   └── crossref/
│       ├── 10.5678_def456.json
│       └── ...
│
└── xml_responses/ (if XML saving is enabled)
    ├── datacite/
    │   ├── 10.1234_abc123.xml
    │   └── ...
    └── crossref/
        ├── 10.5678_def456.xml
        └── ...
```

## Input File Format

The input CSV file must contain a column named 'doi'. An optional 'provider' column can specify the provider ('datacite' or 'crossref') for each DOI, allowing you to mix types. Be careful not to override with the provider arg, however (i.e. use one or the other).

Example input CSV:
```csv
doi,provider
10.1234/abc123,datacite
10.5678/def456,crossref
10.9012/ghi789,
```

## Verification Report Format

- `doi`: The normalized DOI
- `provider`: The provider used for verification ('datacite' or 'crossref')
- `exists`: Whether the DOI exists in the specified provider's database
- `http_code`: HTTP response code from the provider's API
- `error_message`: Any error messages encountered
- `json_path`: Path to saved JSON response (if enabled)
- `xml_path`: Path to saved XML response (if enabled)

When resolution checking is enabled, these additional columns are included:
- `resolves`: Whether the DOI resolves successfully
- `resolution_url`: Final URL after resolution
- `resolution_code`: HTTP response code from resolution
- `resolution_time`: Time taken for resolution in seconds
- `resolution_error`: Any resolution errors encountered

## Parallel Processing

- Use the `-t THREADS` option or set `max_threads` in the config file
- Rate limiting is maintained across all threads for both providers
- Each provider has its own rate limiting configuration

## Rate Limiting

### DataCite
- Default: 3000 requests per 300 seconds
- Configurable via `datacite_rate_limit_calls` and `datacite_rate_limit_period`
- Don't exceed DataCite's limits - they're our friends!

### Crossref
- Default: 50 requests per second
- Configurable lower via `crossref_rate_limit_calls` and `crossref_rate_limit_period`
- Higher limits are available for authenticated users (but not implemented in this script)

## Logging

- Two log files are generated:
  - `error_log.log`: Contains verification-specific errors
  - `application.log`: Contains application-level logging
- When verbose logging is disabled, only warnings and errors are logged