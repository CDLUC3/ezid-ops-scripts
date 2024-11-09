import os
import re
import csv
import json
import time
import base64
import logging
import argparse
from tqdm import tqdm
from requests import Session
from requests.adapters import HTTPAdapter, Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote
from threading import Lock, local
from dataclasses import dataclass


@dataclass
class VerificationResult:
    doi: str
    exists: bool
    http_code: int
    error_message: str
    json_path: str = None
    xml_path: str = None
    resolves: bool = None
    resolution_url: str = None
    resolution_code: int = None
    resolution_time: float = None
    resolution_error: str = None


class VerifyDOI:
    def __init__(self, output_dir="results", save_json=False, save_xml=False,
                 check_resolution=False, resolution_timeout=30, max_redirects=5,
                 rate_limit_calls=3000, rate_limit_period=300):
        self.output_dir = output_dir
        self.save_json = save_json
        self.save_xml = save_xml
        self.check_resolution = check_resolution
        self.resolution_timeout = resolution_timeout
        self.max_redirects = max_redirects
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_period = rate_limit_period
        self.counter_lock = Lock()
        self.writer_lock = Lock()
        self.session_local = local()
        self.rate_limit_lock = Lock()
        self.request_times = []
        self._successful = 0
        self._failed = 0
        self._resolution_successful = 0
        self._resolution_failed = 0

        self.setup_directories()
        self.setup_logging()

    def _setup_session(self):
        session = Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,
            pool_maxsize=1
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get_session(self):
        if not hasattr(self.session_local, 'session'):
            self.session_local.session = self._setup_session()
        return self.session_local.session

    def setup_directories(self):
        self.verify_dir = os.path.join(self.output_dir, 'verify_results')
        os.makedirs(self.verify_dir, exist_ok=True)
        if self.save_json:
            self.json_dir = os.path.join(self.verify_dir, 'json_responses')
            os.makedirs(self.json_dir, exist_ok=True)
        if self.save_xml:
            self.xml_dir = os.path.join(self.verify_dir, 'xml_responses')
            os.makedirs(self.xml_dir, exist_ok=True)

    def setup_logging(self):
        log_file = os.path.join(self.verify_dir, 'error_log.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _increment_counter(self, counter_name):
        with self.counter_lock:
            if counter_name == 'successful':
                self._successful += 1
            elif counter_name == 'failed':
                self._failed += 1
            elif counter_name == 'resolution_successful':
                self._resolution_successful += 1
            elif counter_name == 'resolution_failed':
                self._resolution_failed += 1

    def _rate_limit(self):
        with self.rate_limit_lock:
            current_time = time.time()
            self.request_times = [t for t in self.request_times
                                  if current_time - t < self.rate_limit_period]
            if len(self.request_times) >= self.rate_limit_calls:
                sleep_time = self.request_times[0] + \
                    self.rate_limit_period - current_time
                if sleep_time > 0:
                    jitter = random.uniform(0, 0.1)
                    total_sleep = sleep_time + jitter
                    time.sleep(total_sleep)
                    current_time = time.time()
                    self.request_times = [t for t in self.request_times
                                          if current_time - t < self.rate_limit_period]
            self.request_times.append(current_time)

    def normalize_doi(self, doi):
        if not doi:
            raise ValueError("DOI cannot be empty")
        doi = unquote(doi).strip()
        doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', doi)
        if not doi_match:
            raise ValueError(f"Invalid DOI format: {doi}")
        doi = doi_match.group(1)
        prefixes = [
            'http://doi.org/',
            'https://doi.org/',
            'http://dx.doi.org/',
            'https://dx.doi.org/',
            '//doi.org/',
            'doi:'
        ]
        for prefix in prefixes:
            if doi.lower().startswith(prefix):
                doi = doi[len(prefix):]

        return doi.strip().lower()

    def verify_resolution(self, doi):
        self._rate_limit()
        session = self._get_session()
        resolution_info = {
            'resolves': False,
            'resolution_url': None,
            'resolution_code': None,
            'resolution_time': None,
            'resolution_error': None
        }

        try:
            start_time = time.time()
            url = f"https://doi.org/{doi}"
            response = session.head(
                url,
                allow_redirects=True,
                timeout=self.resolution_timeout,
                headers={'User-Agent': 'ezid@ucop.edu'}
            )

            if response.status_code >= 400:
                response = session.get(
                    url,
                    allow_redirects=True,
                    timeout=self.resolution_timeout,
                    headers={'User-Agent': 'ezid@ucop.edu'}
                )

            resolution_time = time.time() - start_time
            resolution_info.update({
                'resolves': 200 <= response.status_code < 400,
                'resolution_url': response.url,
                'resolution_code': response.status_code,
                'resolution_time': round(resolution_time, 3),
                'resolution_error': None
            })

            if resolution_info['resolves']:
                self._increment_counter('resolution_successful')
            else:
                self._increment_counter('resolution_failed')
                resolution_info['resolution_error'] = f"Resolution failed with status code {response.status_code}"

        except Exception as e:
            self._increment_counter('resolution_failed')
            resolution_info['resolution_error'] = f"Resolution error: {str(e)}"

        return resolution_info

    def verify_doi(self, doi):
        self._rate_limit()
        session = self._get_session()

        try:
            normalized_doi = self.normalize_doi(doi)
            url = f"https://api.datacite.org/works/{normalized_doi}"
            response = session.get(url)
            exists = response.status_code == 200

            result = VerificationResult(
                doi=normalized_doi,
                exists=exists,
                http_code=response.status_code,
                error_message=""
            )

            if exists:
                if self.save_json or self.save_xml:
                    json_data = response.json()
                    if self.save_json:
                        with self.writer_lock:
                            json_path = os.path.join(self.json_dir, f"{normalized_doi.replace('/', '_')}.json")
                            with open(json_path, 'w') as f:
                                json.dump(json_data, f, indent=2)
                            result.json_path = json_path

                    if self.save_xml:
                        try:
                            xml_content = self.extract_xml_from_json(json_data)
                            with self.writer_lock:
                                xml_path = os.path.join(self.xml_dir, f"{normalized_doi.replace('/', '_')}.xml")
                                with open(xml_path, 'w', encoding='utf-8') as f:
                                    f.write(xml_content)
                                result.xml_path = xml_path
                        except ValueError as e:
                            result.error_message = f"XML extraction error: {str(e)}"

                self._increment_counter('successful')
            else:
                self._increment_counter('failed')

            if self.check_resolution:
                resolution_info = self.verify_resolution(normalized_doi)
                result.resolves = resolution_info['resolves']
                result.resolution_url = resolution_info['resolution_url']
                result.resolution_code = resolution_info['resolution_code']
                result.resolution_time = resolution_info['resolution_time']
                result.resolution_error = resolution_info['resolution_error']

            return result

        except Exception as e:
            self._increment_counter('failed')
            return VerificationResult(
                doi=doi,
                exists=False,
                http_code=-1,
                error_message=f"Verification error: {str(e)}"
            )

    def extract_xml_from_json(self, json_data):
        try:
            xml_base64 = json_data['data']['attributes']['xml']
            xml_content = base64.b64decode(xml_base64).decode('utf-8')
            return xml_content
        except KeyError:
            raise ValueError("XML content not found in the JSON data")
        except base64.binascii.Error:
            raise ValueError("Invalid base64 encoding for XML content")

    def process_csv(self, csv_file, max_workers=1):
        report_path = os.path.join(self.verify_dir, 'verification_report.csv')
        total_dois = sum(1 for line in open(csv_file)) - 1
        with open(report_path, 'w') as report_file:
            headers = ['doi', 'exists', 'http_code',
                       'error_message', 'json_path', 'xml_path']
            if self.check_resolution:
                headers.extend([
                    'resolves',
                    'resolution_url',
                    'resolution_code',
                    'resolution_time',
                    'resolution_error'
                ])
            writer = csv.writer(report_file)
            writer.writerow(headers)
            if max_workers > 1:
                self._process_parallel(
                    csv_file, writer, total_dois, max_workers)
            else:
                self._process_sequential(csv_file, writer, total_dois)
        return {
            'total': total_dois,
            'successful': self._successful,
            'failed': self._failed,
            'resolution_successful': self._resolution_successful if self.check_resolution else None,
            'resolution_failed': self._resolution_failed if self.check_resolution else None
        }

    def _write_result(self, writer, result):
        with self.writer_lock:
            row = [
                result.doi,
                result.exists,
                result.http_code,
                result.error_message,
                result.json_path or '',
                result.xml_path or ''
            ]
            if self.check_resolution:
                row.extend([
                    result.resolves,
                    result.resolution_url or '',
                    result.resolution_code or '',
                    result.resolution_time or '',
                    result.resolution_error or ''
                ])
            writer.writerow(row)

    def _process_parallel(self, csv_file, writer, total_dois, max_workers):
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            if 'doi' not in reader.fieldnames:
                raise ValueError("CSV file must contain a 'doi' column")
            dois = [row['doi'] for row in reader if row['doi']]

        batch_size = 1000
        with tqdm(total=len(dois), desc="Verifying DOIs") as pbar:
            for i in range(0, len(dois), batch_size):
                batch = dois[i:i + batch_size]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_doi = {
                        executor.submit(self.verify_doi, doi): doi
                        for doi in batch
                    }
                    for future in as_completed(future_to_doi):
                        try:
                            result = future.result()
                            self._write_result(writer, result)
                        except Exception as e:
                            logging.error(
                                f"Error processing DOI {future_to_doi[future]}: {str(e)}"
                            )
                        pbar.update(1)

    def _process_sequential(self, csv_file, writer, total_dois):
        with open(csv_file, 'r') as f_in:
            reader = csv.DictReader(f_in)
            if 'doi' not in reader.fieldnames:
                raise ValueError("CSV file must contain a 'doi' column")
            with tqdm(total=total_dois, desc="Verifying DOIs") as pbar:
                for row in reader:
                    if row['doi']:
                        result = self.verify_doi(row['doi'])
                        self._write_result(writer, result)
                        pbar.update(1)
                        time.sleep(0.1)


def get_default_config():
    return {
        'parallel': False,
        'max_threads': 1,
        'check_resolution': False,
        'resolution_timeout': 30,
        'max_redirects': 5,
        'save_xml': False,
        'save_json': False
    }


def load_config(config_file=None):
    if config_file is None:
        logging.info(
            "No config file specified, using single-threaded default configuration")
        return get_default_config()
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Error loading config file: {str(e)}")
        return get_default_config()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='DataCite DOI Verification Tool')
    parser.add_argument(
        '-i', '--input_file', required=True, help='Input CSV file containing DOIs to verify')
    parser.add_argument(
        '-d', '--output_dir', default="results", help='Output directory for results'
    )
    parser.add_argument('-c', '--config', help='Configuration file path')
    parser.add_argument('-v', '--verbose',
                        action='store_true', help='Verbose logging')
    parser.add_argument('-t', '--threads', type=int,
                        help='Number of verification threads (overrides config)')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Save JSON responses (overrides config)')
    parser.add_argument('-x', '--xml', action='store_true',
                        help='Save XML responses (overrides config)')
    parser.add_argument('--check-resolution', action='store_true',
                        help='Enable DOI resolution checking (overrides config)')
    parser.add_argument('--resolution-timeout', type=int,
                        help='Timeout for resolution checking in seconds (overrides config)')
    parser.add_argument('--max-redirects', type=int,
                        help='Maximum number of redirects to follow (overrides config)')

    return parser.parse_args()


def setup_logging(output_dir, verbose):
    log_level = logging.INFO if verbose else logging.WARNING
    log_file = os.path.join(output_dir, 'application.log')
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler(log_file), logging.StreamHandler()])


def main():
    args = parse_arguments()
    setup_logging(args.output_dir, args.verbose)
    try:
        config = load_config(args.config)
        verifier_args = {
            'output_dir': args.output_dir,
            'save_json': args.json if args.json else config['save_json'],
            'save_xml': args.xml if args.xml else config['save_xml'],
            'check_resolution': args.check_resolution if args.check_resolution else config['check_resolution'],
            'resolution_timeout': args.resolution_timeout or config['resolution_timeout'],
            'max_redirects': args.max_redirects or config['max_redirects']
        }
        verifier = VerifyDOI(**verifier_args)
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"Input file not found: {args.input_file}")
        max_workers = args.threads if args.threads is not None else (
            config['max_threads'] if config['parallel'] else 1
        )
        results = verifier.process_csv(
            args.input_file,
            max_workers=max_workers
        )
        logging.info(f"Verification complete. Results: {results}")
    except Exception as e:
        logging.error(f"Error during verification: {str(e)}")
        raise


if __name__ == '__main__':
    main()
