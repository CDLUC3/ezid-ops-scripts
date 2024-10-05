# DataCite Record Retrieval

Retrieves DataCite records for specified queries and client IDs, extracts DOIs and their shoulders, generates statistics files, and saves JSON files.

## Features

- Retrieves records from DataCite API based on configurable queries
- Supports multiple queries and client IDs
- Generates CSV files with DOIs and unique shoulders for each query and client
- Produces aggregate statistics
- Supports optional parallel processing for faster execution
- Configurable logging
- Optional saving of raw JSON responses

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python retrieve_datacite_records_by_query_client.py -c CONFIG_FILE [-d OUTPUT_DIR] [-s STATS_FILE] [-v] [-p] [-j]
```

### Command-line Arguments

- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Configuration file containing QUERIES and CLIENT_IDS (required)
- `-d OUTPUT_DIR`, `--output_dir OUTPUT_DIR`: Output directory where files will be saved (default: "results")
- `-s STATS_FILE`, `--stats_file STATS_FILE`: Statistics file containing aggregate statistics (default: "aggregate_stats.csv")
- `-v`, `--verbose`: Enable verbose logging
- `-p`, `--parallel`: Enable parallel processing
- `-j`, `--save_json`: Enable saving of raw JSON responses

## Configuration

Create a `config.json` file with the following structure:

```json
{
    "QUERIES": {
        "query_key": {
            "query": "query_string"
        },
        ...
    },
    "CLIENT_IDS": ["client1", "client2", ...],
    "SAVE_JSON": false
}
```

### Example Configuration

```json
{
    "QUERIES": {
        "v3": {
            "query": "schema-version=3"
        },
        "v3_wo_res_type_gen": {
            "query": "schema-version=3&query=NOT%20types.resourceTypeGeneral:*"
        },
        "v3_wt_contrib_funder": {
            "query": "schema-version=3&query=contributors.contributorType:Funder"
        }
    },
    "CLIENT_IDS": ["cdl.ucsd","cdl.ucb","cdl.ucsb","cdl.cdl","cdl.ucla", "cdl.ucr","cdl.uci","cdl.ucsc","cdl.ucd","cdl.ucsf","cdl.ucm"],
    "SAVE_JSON": true
}
```

## How It Works

1. The script loads the configuration from the specified JSON file.
2. For each combination of query and client ID:
   - It constructs a URL to query the DataCite API.
   - It retrieves all pages of results for that query and client.
   - It extracts DOIs and their shoulders from the retrieved records.
3. For each query and client combination, it generates two CSV files:
   - A file containing all DOIs retrieved.
   - A file containing unique DOI shoulders and their counts.
4. It compiles aggregate statistics across all queries and clients.
5. Optionally, it saves the raw JSON responses.

## Output

- For each client and query combination:
  - `{output_dir}/{client_id}/{query_key}.csv`: List of DOIs
  - `{output_dir}/{client_id}/{query_key}_unique_shoulders.csv`: Unique shoulders and their counts
- `{stats_file}`: Aggregate statistics for all clients and queries
- If JSON saving is enabled:
  - `{output_dir}/json/{client_id}/{query_key}/page_{number}.json`: Raw JSON responses

## Parallel Processing

- Use the `-p` or `--parallel` flag to enable parallel processing for multiple clients and queries.
- ThreadPoolExecutor is used for parallel processing, with the number of workers limited to the minimum of:
  - 32
  - Number of CPU cores + 4
  - Total number of work items (client_ids * queries)

## Logging

- Use the `-v` or `--verbose` flag to enable logging.
- When verbose logging is disabled, only warnings and errors will be logged.

## Save JSON

- Use the `-j` or `--save_json` flag to enable saving of raw JSON responses.
- Alternatively, set `"SAVE_JSON": true` in the configuration file.
- JSON responses are saved in the `{output_dir}/json/{client_id}/{query_key}/` directory.