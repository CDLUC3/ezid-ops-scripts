# DOI Verification Tool

Check DOIs against the DataCite API and optionally test their resolution.

## How It Works

1. The script loads the default configuration or one provided as an argument
2. For each DOI in the input CSV file:
   - Normalizes and validates the DOI 
   - Queries the DataCite API to check if the DOI exists
   - Optionally checks DOI resolution
   - Optionally saves JSON and XML responses
3. Results are written to a CSV file


## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python verify_doi.py -i INPUT_FILE [-d OUTPUT_DIR] [-c CONFIG_FILE] [-v] [-t THREADS] 
                     [-j] [-x] [--check-resolution] [--resolution-timeout TIMEOUT] 
                     [--max-redirects REDIRECTS]
```

### Command-line Arguments

- `-i INPUT_FILE`, `--input_file INPUT_FILE`: CSV file containing DOIs to verify (required)
- `-d OUTPUT_DIR`, `--output_dir OUTPUT_DIR`: Output directory for results (default: "results")
- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Configuration file path
- `-v`, `--verbose`: Enable verbose logging
- `-t THREADS`, `--threads THREADS`: Number of verification threads
- `-j`, `--json`: Save JSON responses from DataCite API
- `-x`, `--xml`: Save XML responses from DataCite API
- `--check-resolution`: Enable DOI resolution checking through doi.org
- `--resolution-timeout TIMEOUT`: Timeout for resolution checking in seconds
- `--max-redirects REDIRECTS`: Maximum number of redirects to follow

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
    "save_json": false
}
```
Otherwise, will follow what is passed in as an argument.

### Example Configuration File

```json
{
    "parallel": true,
    "max_threads": 2,
    "check_resolution": true,
    "resolution_timeout": 60,
    "max_redirects": 10,
    "save_xml": true,
    "save_json": true
}
```

## Output

### Files Generated

- `{output_dir}/verify_results/verification_report.csv`: Main verification results
- `{output_dir}/verify_results/error_log.log`: Detailed error logging
- `{output_dir}/verify_results/application.log`: Application-level logging
- If JSON saving is enabled:
  - `{output_dir}/verify_results/json_responses/{doi}.json`: JSON responses from DataCite
- If XML saving is enabled:
  - `{output_dir}/verify_results/xml_responses/{doi}.xml`: XML responses from DataCite

### Directory Structure
```
output_dir/
│
├── verify_results/
│   ├── verification_report.csv
│   ├── error_log.log
│   ├── application.log
│   │
│   ├── json_responses/ (if JSON saving is enabled)
│   │   ├── 10.1234_abc123.json
│   │   ├── 10.5678_def456.json
│   │   └── ...
│   │
│   └── xml_responses/ (if XML saving is enabled)
│       ├── 10.1234_abc123.xml
│       ├── 10.5678_def456.xml
│       └── ...
```

## Input File Format

The input CSV file must contain a column named 'doi'. Additional columns are allowed but will be ignored. 

## Verification Report Format

- `doi`: The normalized DOI
- `exists`: Whether the DOI exists in DataCite (true/false)
- `http_code`: HTTP response code from DataCite API
- `error_message`: Any error messages encountered
- `json_path`: Path to saved JSON response (if enabled)
- `xml_path`: Path to saved XML response (if enabled)

When resolution checking is enabled, the below columns are also included:

- `resolves`: Whether the DOI resolves successfully
- `resolution_url`: Final URL after resolution
- `resolution_code`: HTTP response code from resolution
- `resolution_time`: Time taken for resolution in seconds
- `resolution_error`: Any resolution errors encountered

## Parallel Processing

- Use the `-t THREADS` option or set `max_threads` in the config file
- Rate limiting is maintained across all threads. 

## Rate Limiting

- Default: 3000 requests per 300 seconds
- DataCite upper limit. Configurable, but don't run in excess of this. It's very rude and they're our friends!

## Logging

- Two log files are generated:
  - `error_log.log`: Contains verification-specific errors
  - `application.log`: Contains application-level logging
- When verbose logging is disabled, only warnings and errors are logged

