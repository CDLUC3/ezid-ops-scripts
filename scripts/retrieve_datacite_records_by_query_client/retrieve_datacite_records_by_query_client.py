import os
import argparse
import requests
import json
import logging
import csv
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs, urlencode
from tqdm import tqdm
import concurrent.futures
import threading


def setup_logging(verbose):
    if verbose:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.StreamHandler()])
    else:
        logging.basicConfig(level=logging.WARNING,
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.StreamHandler()])


def load_config(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    queries = {k: v['query'] for k, v in config.get('QUERIES', {}).items()}
    client_ids = config.get('CLIENT_IDS', [])
    return queries, client_ids, len(client_ids)


def get_total_work(client_ids, queries):
    return len(client_ids) * len(queries)


def retrieve_datacite_records(url="https://api.datacite.org/dois", params=None, allow_redirects=False):
    try:
        response = requests.get(url=url, params=params,
                                allow_redirects=allow_redirects)
        response.raise_for_status()
        return True, response.status_code, response.text, ""
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if hasattr(
            e, 'response') and e.response is not None else -1
        err_msg = f"HTTPError: {str(e)[:200]}"
        logging.error(f"Failed to retrieve data from {url}. Status code: {status_code}. Error: {err_msg}")
        return False, status_code, "", err_msg


def fetch_all_pages(params, client_id, query_key):
    all_data = []
    cursor = '1'
    page_number = 1
    base_url = "https://api.datacite.org/dois"
    while True:
        current_params = params.copy()
        current_params['page[cursor]'] = cursor
        query_url = f"{base_url}?{urlencode(current_params)}"
        logging.info(f"Client {client_id}, Query {query_key}: Fetching page {page_number}. Query URL: {query_url}")
        success, status_code, text, err_msg = retrieve_datacite_records(
            params=current_params)
        if not success:
            logging.error(f"Client {client_id}, Query {query_key}: Failed to fetch page {page_number}. Status: {status_code}, Error: {err_msg}")
            break
        results = json.loads(text)
        current_page_data = results.get('data', [])
        if not current_page_data:
            logging.info(f"Client {client_id}, Query {query_key}: No more data received. Ending pagination.")
            break
        all_data.extend(current_page_data)
        logging.info(f"Client {client_id}, Query {query_key}: Processed page {page_number}")
        next_link = results.get('links', {}).get('next')
        if not next_link:
            logging.info(f"Client {client_id}, Query {query_key}: No next link found. Ending pagination.")
            break
        next_url = urlparse(next_link)
        next_params = parse_qs(next_url.query)
        cursor = next_params.get('page[cursor]', [None])[0]
        if not cursor:
            logging.error(f"Client {client_id}, Query {query_key}: Failed to extract next cursor. Ending pagination.")
            break
        page_number += 1
    logging.info(f"Client {client_id}, Query {query_key}: Finished fetching all pages. Total pages processed: {page_number}")
    return all_data


def extract_dois(records):
    return [record.get("id") for record in records if "id" in record]


def extract_shoulder(doi):
    parts = doi.split('/')
    if len(parts) >= 2:
        prefix = parts[0]
        suffix = parts[1][:2]
        return f"{prefix}/{suffix}"
    return None


def process_client(client_id, query_key, query, output_dir):
    params = {
        'client-id': client_id,
        'page[size]': 1000
    }
    params.update(dict(param.split('=') for param in query.split('&')))
    all_records = fetch_all_pages(params, client_id, query_key)
    dois = extract_dois(all_records)
    if not dois:
        logging.info(f"Client {client_id}, Query {query_key}: No results. Skipping file creation.")
        return 0, 0

    client_dir = os.path.join(output_dir, client_id)
    os.makedirs(client_dir, exist_ok=True)
    doi_filename = os.path.join(client_dir, f"{query_key}.csv")
    with open(doi_filename, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["DOI"])
        for doi in dois:
            writer.writerow([doi])

    shoulders = [extract_shoulder(doi)
                 for doi in dois if extract_shoulder(doi)]
    unique_shoulders = sorted(set(shoulders))
    shoulder_counts = Counter(shoulders)

    shoulder_filename = os.path.join(client_dir, f"{query_key}_unique_shoulders.csv")
    with open(shoulder_filename, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Unique_Shoulder", "Count"])
        for shoulder in unique_shoulders:
            writer.writerow([shoulder, shoulder_counts[shoulder]])

    logging.info(f"Client {client_id}, Query {query_key}: Processed. DOIs in {doi_filename}, Shoulders in {shoulder_filename}")

    return len(dois), len(unique_shoulders)


def process_client_query(client_id, queries, output_dir):
    client_stats = {}
    for query_key, query in queries.items():
        doi_count, shoulder_count = process_client(
            client_id, query_key, query, output_dir)
        client_stats[(client_id, query_key)] = [doi_count, shoulder_count]
    return client_stats


def log_aggregate_statistics(stats, stats_file):
    with open(stats_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(
            ["Client", "Query", "DOI Count", "Unique Shoulder Count"])
        for (client_id, query_key), (doi_count, shoulder_count) in stats.items():
            writer.writerow([client_id, query_key, doi_count, shoulder_count])
    logging.info(f"Aggregate statistics written to {stats_file}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Retrieve DataCite JSON records and generate DOI list.')
    parser.add_argument('-d', '--output_dir', default="results", type=str,
                        help='Output directory: directory where files will be saved.')
    parser.add_argument('-s', '--stats_file', default="aggregate_stats.csv", type=str,
                        help='Statistics file: output file containing aggregate statistics.')
    parser.add_argument('-c', '--config', default="config.json", required=True,
                        type=str, help='Configuration file containing QUERIES and CLIENT_IDS')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('-p', '--parallel', action='store_true',
                        help='Enable parallel processing')
    return parser.parse_args()


def main():
    args = parse_arguments()
    setup_logging(args.verbose)
    os.makedirs(args.output_dir, exist_ok=True)
    if not os.path.isabs(args.stats_file):
        args.stats_file = os.path.join(args.output_dir, args.stats_file)

    QUERIES, CLIENT_IDS, num_clients = load_config(args.config)
    total_work = get_total_work(CLIENT_IDS, QUERIES)

    if args.parallel:
        max_workers = min(32, os.cpu_count() + 4, total_work)
        logging.info(f"Using {max_workers} workers")
    else:
        max_workers = 1
        logging.info("Running in sequential mode")

    logging.info(f"Total clients: {num_clients}")
    logging.info(f"Total queries: {len(QUERIES)}")
    logging.info(f"Total work items: {total_work}")

    stats = defaultdict(lambda: [0, 0])

    if args.parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_client = {
                executor.submit(process_client_query, client_id, QUERIES, args.output_dir): client_id
                for client_id in CLIENT_IDS
            }

            completed_tasks = 0
            with tqdm(total=total_work, desc="Processing clients and queries") as pbar:
                for future in concurrent.futures.as_completed(future_to_client):
                    client_id = future_to_client[future]
                    try:
                        client_stats = future.result()
                        stats.update(client_stats)
                        completed_tasks += len(QUERIES)
                        pbar.update(len(QUERIES))
                    except Exception as exc:
                        logging.error(f'{client_id} generated an exception: {exc}')
                        completed_tasks += 1
                        pbar.update(1)
    else:
        with tqdm(total=total_work, desc="Processing clients and queries") as pbar:
            for client_id in CLIENT_IDS:
                try:
                    client_stats = process_client_query(
                        client_id, QUERIES, args.output_dir)
                    stats.update(client_stats)
                    pbar.update(len(QUERIES))
                except Exception as exc:
                    logging.error(f'{client_id} generated an exception: {exc}')
                    pbar.update(len(QUERIES))

    log_aggregate_statistics(stats, args.stats_file)
    logging.info("Processing complete. Results are in the following files:")
    for client_id in CLIENT_IDS:
        for query_key in QUERIES.keys():
            logging.info(f"- {os.path.join(args.output_dir, client_id, query_key + '.csv')}")
            logging.info(f"- {os.path.join(args.output_dir, client_id, query_key + '_unique_shoulders.csv')}")
    logging.info(f"Aggregate statistics: {args.stats_file}")


if __name__ == "__main__":
    main()
