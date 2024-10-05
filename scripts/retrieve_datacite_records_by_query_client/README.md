# DataCite Record Retrieval Script

Retrieves DataCite records for specified queries and client IDs, extracts DOIs and their shoulders, and generates statistics files.

## Features

- Retrieves records from DataCite API based on configurable queries
- Supports multiple queries and client IDs
- Generates CSV files with DOIs and unique shoulders for each query and client
- Produces aggregate statistics
- Supports optional scaling parallel processing (based on number of clients) for faster execution
- Configurable logging

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python script.py -c CONFIG_FILE [-d OUTPUT_DIR] [-s STATS_FILE] [-v] [-p]
```

### Command-line Arguments

- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Configuration file containing QUERIES and CLIENT_IDS (required)
- `-d OUTPUT_DIR`, `--output_dir OUTPUT_DIR`: Output directory where files will be saved (default: "results")
- `-s STATS_FILE`, `--stats_file STATS_FILE`: Statistics file containing aggregate statistics (default: "aggregate_stats.csv")
- `-v`, `--verbose`: Enable verbose logging
- `-p`, `--parallel`: Enable parallel processing

## Configuration

Create a `config.json` file with the following structure:

```json
{
    "QUERIES": {
        "query_key": {
            "query": "query_string",
            "description": "Query description"
        },
        ...
    },
    "CLIENT_IDS": ["client1", "client2", ...],
    "CLIENT_DESCRIPTION": "Description of the clients"
}
```

### Example Configuration

```json
{
    "QUERIES": {
        "v3": {
            "query": "schema-version=3",
            "description": "Get all records using DataCite schema version 3 for the specified client."
        },
        "v3_wo_res_type_gen": {
            "query": "schema-version=3&query=NOT%20types.resourceTypeGeneral:*",
            "description": "Get records using DataCite schema version 3 that don't have a general resource type specified."
        },
        "v3_wt_contrib_funder": {
            "query": "schema-version=3&query=contributors.contributorType:Funder",
            "description": "Get records using DataCite schema version 3 that have a funder listed as a contributor."
        }
    },
    "CLIENT_IDS": ["cdl.ucsd","cdl.ucb","cdl.ucsb","cdl.cdl","cdl.ucla", "cdl.ucr","cdl.uci","cdl.ucsc","cdl.ucd","cdl.ucsf","cdl.ucm"],
    "CLIENT_DESCRIPTION": "All UC DataCite clients"
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

## Output

- For each client and query combination:
  - `{output_dir}/{client_id}/{query_key}.csv`: List of DOIs
  - `{output_dir}/{client_id}/{query_key}_unique_shoulders.csv`: Unique shoulders and their counts
- `{stats_file}`: Aggregate statistics for all clients and queries

## Performance Considerations

- Use the `-p` or `--parallel` flag to enable parallel processing, which can significantly speed up execution for multiple clients and queries.
- ThreadPoolExecutor is used for parallel processing, with the number of workers limited to the minimum of:
  - 32
  - Number of CPU cores + 4
  - Total number of work items (client_ids * queries)

## Logging

- Use the `-v` or `--verbose` flag to enable detailed logging, which can be helpful for debugging or monitoring the script's progress.
- When verbose logging is disabled, only warnings and errors will be logged.
