# DataCite Record Retrieval

Retrieves DataCite records for specified queries and client IDs, extracts DOIs and their shoulders, generates statistics files, organizes DOIs by shoulders, and optionally saves JSON files.

## Features

- Retrieves records from DataCite API based on configurable queries
- Supports multiple queries and client IDs
- Generates CSV files with DOIs and unique shoulders for each query and client
- Organizes DOIs into separate files based on their shoulders for easy analysis
- Produces aggregate statistics across all queries and clients
- Supports optional parallel processing for faster execution
- Configurable logging levels
- Optional saving of raw JSON responses
- Configurable shoulder processing for detailed analysis

## Installation

```
pip install -r requirements.txt
```

## Usage

```
python retrieve_datacite_records_by_query_client.py -c CONFIG_FILE [-d OUTPUT_DIR] [-a STATS_FILE] [-v] [-p] [-j] [-s]
```

### Command-line Arguments

- `-c CONFIG_FILE`, `--config CONFIG_FILE`: Configuration file containing QUERIES and CLIENT_IDS (required)
- `-d OUTPUT_DIR`, `--output_dir OUTPUT_DIR`: Output directory where files will be saved (default: "results")
- `-a STATS_FILE`, `--aggregate_stats_file STATS_FILE`: Statistics file containing aggregate statistics (default: "aggregate_stats.csv")
- `-v`, `--verbose`: Enable verbose logging
- `-p`, `--parallel`: Enable parallel processing
- `-j`, `--save_json`: Enable saving of raw JSON responses
- `-s`, `--shoulder`: Enable shoulder-specific outputs

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
    "SAVE_JSON": false,
    "PROCESS_SHOULDERS": false
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
    "SAVE_JSON": true,
    "PROCESS_SHOULDERS": true
}
```

## How It Works

1. The script loads the configuration from the specified JSON file.
2. For each combination of query and client ID:
   - It constructs a URL to query the DataCite API.
   - It retrieves all pages of results for that query and client.
   - It extracts DOIs and their shoulders from the retrieved records.
3. For each query and client combination, it generates several types of outputs:
   - A file containing all DOIs retrieved.
   - If shoulder processing is enabled:
     - A file containing unique DOI shoulders and their counts.
     - A directory containing separate CSV files for each unique shoulder, with their respective DOIs.
4. It compiles aggregate statistics across all queries and clients.
5. If shoulder processing is enabled, it generates an aggregate file of unique shoulders across all queries and clients.
6. Optionally, it saves the raw JSON responses.

## Output

### Files Generated

- For each client and query combination:
  - `{output_dir}/{client_id}/{query_key}_{client_id}.csv`: List of DOIs
  - If shoulder processing is enabled:
    - `{output_dir}/{client_id}/{query_key}_{client_id}_unique_shoulders.csv`: Unique shoulders and their counts
    - `{output_dir}/{client_id}/{query_key}_by_shoulders/`: Directory containing CSV files for each unique shoulder
      - `{output_dir}/{client_id}/{query_key}_by_shoulders/{shoulder}.csv`: DOIs for each unique shoulder
- `{stats_file}`: Aggregate statistics for all clients and queries
- If shoulder processing is enabled:
  - `{output_dir}/aggregate_unique_shoulders.csv`: Aggregate unique shoulders across all clients and queries
- If JSON saving is enabled:
  - `{output_dir}/json/{client_id}/{query_key}/page_{number}.json`: Raw JSON responses

### Directory Structure

Output files are organized like the below:

```
output_dir/
│
├── aggregate_stats.csv
├── aggregate_unique_shoulders.csv (if shoulder processing is enabled)
│
├── client_id_1/
│   ├── query_key_1_client_id_1.csv
│   ├── query_key_1_client_id_1_unique_shoulders.csv (if shoulder processing is enabled)
│   ├── query_key_1_by_shoulders/ (if shoulder processing is enabled)
│   │   ├── shoulder_1.csv
│   │   ├── shoulder_2.csv
│   │   └── ...
│   │
│   ├── query_key_2_client_id_1.csv
│   ├── query_key_2_client_id_1_unique_shoulders.csv (if shoulder processing is enabled)
│   ├── query_key_2_by_shoulders/ (if shoulder processing is enabled)
│   │   ├── shoulder_1.csv
│   │   ├── shoulder_2.csv
│   │   └── ...
│   └── ...
│
├── client_id_2/
│   ├── query_key_1_client_id_2.csv
│   ├── query_key_1_client_id_2_unique_shoulders.csv (if shoulder processing is enabled)
│   ├── query_key_1_by_shoulders/ (if shoulder processing is enabled)
│   │   ├── shoulder_1.csv
│   │   ├── shoulder_2.csv
│   │   └── ...
│   │
│   ├── query_key_2_client_id_2.csv
│   ├── query_key_2_client_id_2_unique_shoulders.csv (if shoulder processing is enabled)
│   ├── query_key_2_by_shoulders/ (if shoulder processing is enabled)
│   │   ├── shoulder_1.csv
│   │   ├── shoulder_2.csv
│   │   └── ...
│   └── ...
│
├── json/ (if JSON saving is enabled)
│   ├── client_id_1/
│   │   ├── query_key_1/
│   │   │   ├── page_1.json
│   │   │   ├── page_2.json
│   │   │   └── ...
│   │   │
│   │   ├── query_key_2/
│   │   │   ├── page_1.json
│   │   │   ├── page_2.json
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── client_id_2/
│   │   ├── query_key_1/
│   │   │   ├── page_1.json
│   │   │   ├── page_2.json
│   │   │   └── ...
│   │   │
│   │   ├── query_key_2/
│   │   │   ├── page_1.json
│   │   │   ├── page_2.json
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

## Parallel Processing

- Use the `-p` or `--parallel` flag to enable parallel processing for multiple clients and queries.
- ThreadPoolExecutor is used for parallel processing, with the number of workers limited to the minimum of:
  - 32
  - Number of CPU cores + 4
  - Total number of work items (client_ids * queries)

## Logging

- Use the `-v` or `--verbose` flag to enable verbose logging.
- When verbose logging is disabled, only warnings and errors will be logged.

## Save JSON

- Use the `-j` or `--save_json` flag to enable saving of raw JSON responses.
- Alternatively, set `"SAVE_JSON": true` in the configuration file.
- JSON responses are saved in the `{output_dir}/json/{client_id}/{query_key}/` directory.

## Shoulder Processing

- Use the `-s` or `--shoulder` flag to enable shoulder-specific outputs.
- Alternatively, set `"PROCESS_SHOULDERS": true` in the configuration file.
- When enabled, the script generates additional files and directories for DOI shoulder analysis.
- Shoulder processing includes:
  - Creating unique shoulder files for each query and client
  - Organizing DOIs into separate files based on their shoulders
  - Generating an aggregate file of unique shoulders across all queries and clients