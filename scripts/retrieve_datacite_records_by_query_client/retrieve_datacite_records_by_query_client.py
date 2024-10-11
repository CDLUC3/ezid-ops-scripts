import os
import csv
import json
import logging
import argparse
import requests
import threading
import concurrent.futures
from collections import defaultdict, Counter
from urllib.parse import urlparse, parse_qs, urlencode
from tqdm import tqdm


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
    save_json = config.get('SAVE_JSON', False)
    process_shoulders = config.get('PROCESS_SHOULDERS', False)
    return queries, client_ids, len(client_ids), save_json, process_shoulders


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


def save_json_response(json_data, client_id, query_key, page_number, base_dir):
    dir_path = os.path.join(base_dir, 'json', client_id, query_key)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, f'page_{page_number}.json')
    try:
        with open(file_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        logging.info(f"Saved JSON response for client {client_id}, query {query_key}, page {page_number}")
    except IOError as e:
        logging.error(f"Error saving JSON response: {str(e)}")


def fetch_all_pages(params, client_id, query_key, save_json, output_dir):
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
        if save_json:
            save_json_response(results, client_id, query_key,
                               page_number, output_dir)
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


def organize_dois_by_shoulder(dois, client_id, query_key, output_dir, process_shoulders):
    if not process_shoulders:
        return 0
    shoulder_dir = os.path.join(output_dir, client_id, f"{query_key}_by_shoulders")
    os.makedirs(shoulder_dir, exist_ok=True)
    shoulders = defaultdict(list)
    for doi in dois:
        shoulder = extract_shoulder(doi)
        if shoulder:
            shoulders[shoulder].append(doi)
        else:
            logging.warning(f"Invalid shoulder for DOI: {doi}")
    for shoulder, doi_list in shoulders.items():
        safe_shoulder = shoulder.replace('/', '_')
        shoulder_file = os.path.join(shoulder_dir, f"{safe_shoulder}.csv")
        with open(shoulder_file, 'w') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["DOI"])
            for doi in doi_list:
                writer.writerow([doi])
    logging.info(f"Organized DOIs by shoulder for client {client_id}, query {query_key}")
    return len(shoulders)


def process_client(client_id, query_key, query, output_dir, save_json, process_shoulders):
    params = {
        'client-id': client_id,
        'page[size]': 1000
    }
    params.update(dict(param.split('=') for param in query.split('&')))
    all_records = fetch_all_pages(
        params, client_id, query_key, save_json, output_dir)
    dois = extract_dois(all_records)
    if not dois:
        logging.info(f"Client {client_id}, Query {query_key}: No results. Skipping file creation.")
        return 0, 0, {}
    client_dir = os.path.join(output_dir, client_id)
    os.makedirs(client_dir, exist_ok=True)
    doi_filename = os.path.join(client_dir, f"{query_key}_{client_id}.csv")
    with open(doi_filename, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["DOI"])
        for doi in dois:
            writer.writerow([doi])
    logging.info(f"Client {client_id}, Query {query_key}: Processed. DOIs in {doi_filename}")
    if process_shoulders:
        shoulders = [extract_shoulder(doi)
                     for doi in dois if extract_shoulder(doi)]
        unique_shoulders = sorted(set(shoulders))
        shoulder_counts = Counter(shoulders)
        shoulder_filename = os.path.join(client_dir, f"{query_key}_{client_id}_unique_shoulders.csv")
        with open(shoulder_filename, 'w') as f_out:
            writer = csv.writer(f_out)
            writer.writerow(["Unique_Shoulder", "Count"])
            for shoulder in unique_shoulders:
                writer.writerow([shoulder, shoulder_counts[shoulder]])
        num_shoulder_files = organize_dois_by_shoulder(
            dois, client_id, query_key, output_dir, process_shoulders)
        logging.info(f"Shoulders in {shoulder_filename}")
        logging.info(f"Created {num_shoulder_files} shoulder-specific files in {os.path.join(client_dir, f'{query_key}_by_shoulders')}")
        return len(dois), len(unique_shoulders), shoulder_counts
    else:
        logging.info(
            f"Client {client_id}, Query {query_key}: Shoulder processing is disabled. Skipping shoulder-specific outputs.")
        return len(dois), 0, {}


def process_client_query(client_id, queries, output_dir, save_json, process_shoulders):
    client_stats = {}
    client_shoulders = {}
    for query_key, query in queries.items():
        doi_count, shoulder_count, shoulder_data = process_client(
            client_id, query_key, query, output_dir, save_json, process_shoulders)
        client_stats[(client_id, query_key)] = [doi_count, shoulder_count]
        if process_shoulders:
            client_shoulders[(client_id, query_key)] = shoulder_data
    return client_stats, client_shoulders if process_shoulders else None


def log_aggregate_statistics(stats, stats_file):
    with open(stats_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(
            ["Client", "Query", "DOI Count", "Unique Shoulder Count"])
        for (client_id, query_key), (doi_count, shoulder_count) in stats.items():
            writer.writerow([client_id, query_key, doi_count, shoulder_count])
    logging.info(f"Aggregate statistics written to {stats_file}")


def aggregate_shoulders(all_shoulder_data):
    aggregated_shoulders = defaultdict(int)
    for (client_id, query_key), shoulder_counts in all_shoulder_data.items():
        for shoulder, count in shoulder_counts.items():
            aggregated_shoulders[(client_id, query_key, shoulder)] += count
    return aggregated_shoulders


def write_aggregate_shoulders(aggregated_shoulders, output_file):
    with open(output_file, 'w') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["Client", "Query", "Unique_Shoulder", "Count"])
        for (client_id, query_key, shoulder), count in sorted(aggregated_shoulders.items()):
            writer.writerow([client_id, query_key, shoulder, count])
    logging.info(f"Aggregate unique shoulders written to {output_file}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Retrieve DataCite JSON records and generate DOI list.')
    parser.add_argument('-d', '--output_dir', default="results", type=str,
                        help='Output directory: directory where files will be saved.')
    parser.add_argument('-a', '--aggregate_stats_file', default="aggregate_stats.csv", type=str,
                        help='Statistics file: output file containing aggregate statistics.')
    parser.add_argument('-c', '--config', default="config.json", required=True,
                        type=str, help='Configuration file containing QUERIES and CLIENT_IDS')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('-p', '--parallel', action='store_true',
                        help='Enable parallel processing')
    parser.add_argument('-j', '--save_json', action='store_true',
                        help='Enable saving of raw JSON responses')
    parser.add_argument('-s', '--shoulder', action='store_true',
                        help='Enable shoulder-specific outputs')
    return parser.parse_args()


def main():
    args = parse_arguments()
    setup_logging(args.verbose)
    os.makedirs(args.output_dir, exist_ok=True)
    if not os.path.isabs(args.aggregate_stats_file):
        args.aggregate_stats_file = os.path.join(
            args.output_dir, args.aggregate_stats_file)
    QUERIES, CLIENT_IDS, num_clients, save_json, config_shoulders = load_config(
        args.config)
    save_json = save_json or args.save_json
    process_shoulders = args.shoulder or config_shoulders
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
    logging.info(f"Saving JSON responses: {'Yes' if save_json else 'No'}")
    logging.info(f"Processing shoulders: {'Yes' if process_shoulders else 'No'}")
    stats = defaultdict(lambda: [0, 0])
    all_shoulder_data = {}
    if args.parallel:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_client = {
                executor.submit(process_client_query, client_id, QUERIES, args.output_dir, save_json, process_shoulders): client_id
                for client_id in CLIENT_IDS
            }
            with tqdm(total=total_work, desc="Processing clients and queries") as pbar:
                for future in concurrent.futures.as_completed(future_to_client):
                    client_id = future_to_client[future]
                    try:
                        client_stats, client_shoulders = future.result()
                        stats.update(client_stats)
                        if process_shoulders and client_shoulders is not None:
                            all_shoulder_data.update(client_shoulders)
                        pbar.update(len(QUERIES))
                    except Exception as exc:
                        logging.error(f'{client_id} generated an exception: {exc}')
                        pbar.update(len(QUERIES))
    else:
        with tqdm(total=total_work, desc="Processing clients and queries") as pbar:
            for client_id in CLIENT_IDS:
                try:
                    client_stats, client_shoulders = process_client_query(
                        client_id, QUERIES, args.output_dir, save_json, process_shoulders)
                    stats.update(client_stats)
                    if process_shoulders and client_shoulders is not None:
                        all_shoulder_data.update(client_shoulders)
                    pbar.update(len(QUERIES))
                except Exception as exc:
                    logging.error(f'{client_id} generated an exception: {exc}')
                    pbar.update(len(QUERIES))

    log_aggregate_statistics(stats, args.aggregate_stats_file)

    if process_shoulders:
        aggregated_shoulders = aggregate_shoulders(all_shoulder_data)
        aggregate_shoulders_file = os.path.join(
            args.output_dir, "aggregate_unique_shoulders.csv")
        write_aggregate_shoulders(
            aggregated_shoulders, aggregate_shoulders_file)

    logging.info("Processing complete. Results are in the following files:")
    for client_id in CLIENT_IDS:
        for query_key in QUERIES.keys():
            logging.info(f"- {os.path.join(args.output_dir, client_id, f'{query_key}_{client_id}.csv')}")
            if process_shoulders:
                logging.info(f"- {os.path.join(args.output_dir, client_id, f'{query_key}_{client_id}_unique_shoulders.csv')}")
                logging.info(f"- {os.path.join(args.output_dir, client_id, f'{query_key}_by_shoulders')} (directory)")
    if save_json:
        logging.info(f"JSON responses saved in: {os.path.join(args.output_dir, 'json')}")
    logging.info(f"Aggregate statistics: {args.aggregate_stats_file}")
    if process_shoulders:
        logging.info(f"Aggregate unique shoulders: {aggregate_shoulders_file}")
    else:
        logging.info(
            "Shoulder processing was disabled. No shoulder-specific outputs were generated.")


if __name__ == "__main__":
    main()
