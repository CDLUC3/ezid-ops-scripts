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
    provider: str = None
    json_path: str = None
    xml_path: str = None
    resolves: bool = None
    resolution_url: str = None
    resolution_code: int = None
    resolution_time: float = None
    resolution_error: str = None


class VerifyDOI:
    def __init__(self, provider, output_dir, save_json, save_xml,
                 check_resolution, resolution_timeout, max_redirects,
                 datacite_rate_limit_calls, datacite_rate_limit_period,
                 crossref_rate_limit_calls, crossref_rate_limit_period):
        self.output_dir = output_dir
        self.save_json = save_json
        self.save_xml = save_xml
        self.check_resolution = check_resolution
        self.resolution_timeout = resolution_timeout
        self.max_redirects = max_redirects
        self.provider = provider

        self.datacite_rate_limit_calls = datacite_rate_limit_calls
        self.datacite_rate_limit_period = datacite_rate_limit_period
        self.request_times_datacite = []

        self.crossref_rate_limit_calls = crossref_rate_limit_calls
        self.crossref_rate_limit_period = crossref_rate_limit_period
        self.request_times_crossref = []

        self.counter_lock = Lock()
        self.writer_lock = Lock()
        self.session_local = local()
        self.datacite_rate_limit_lock = Lock()
        self.crossref_rate_limit_lock = Lock()

        self._successful = 0
        self._failed = 0
        self._resolution_successful = 0
        self._resolution_failed = 0

        self.setup_directories()
        self.setup_logging()

    def setup_directories(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if self.save_json:
            self.json_dir = os.path.join(self.output_dir, 'json_responses')
            self.datacite_json_dir = os.path.join(
                self.json_dir, 'datacite')
            os.makedirs(self.datacite_json_dir, exist_ok=True)
            self.crossref_json_dir = os.path.join(
                self.json_dir, 'crossref')
            os.makedirs(self.crossref_json_dir, exist_ok=True)
        if self.save_xml:
            self.xml_dir = os.path.join(self.output_dir, 'xml_responses')
            self.datacite_xml_dir = os.path.join(self.xml_dir, 'datacite')
            os.makedirs(self.datacite_xml_dir, exist_ok=True)
            self.crossref_xml_dir = os.path.join(self.xml_dir, 'crossref')
            os.makedirs(self.crossref_xml_dir, exist_ok=True)

    def setup_logging(self):
        log_file = os.path.join(self.output_dir, 'error_log.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _get_session(self):
        if not hasattr(self.session_local, 'session'):
            self.session_local.session = self._setup_session()
        return self.session_local.session

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

    def detect_provider(self, doi):
        with self.provider_cache_lock:
            if doi in self.provider_cache:
                return self.provider_cache[doi]
        try:
            session = self._get_session()
            url = f"https://api.crossref.org/works/{doi}/agency"
            response = session.get(url)

            if response.status_code == 200:
                data = response.json()
                provider = data["message"]["agency"]["id"].lower()
                with self.provider_cache_lock:
                    self.provider_cache[doi] = provider

                return provider
            else:
                logging.warning(f"Could not detect provider for DOI {doi}. Status code: {response.status_code}")
                return "datacite"

        except Exception as e:
            logging.error(f"Error detecting provider for DOI {doi}: {str(e)}")
            return "datacite"

    def _rate_limit_datacite(self):
        with self.datacite_rate_limit_lock:
            current_time = time.time()
            self.request_times_datacite = [
                t for t in self.request_times_datacite
                if current_time - t < self.datacite_rate_limit_period
            ]
            if len(self.request_times_datacite) >= self.datacite_rate_limit_calls:
                sleep_time = (self.request_times_datacite[0] +
                              self.datacite_rate_limit_period - current_time)
                if sleep_time > 0:
                    jitter = random.uniform(0, 0.1)
                    time.sleep(sleep_time + jitter)
                    current_time = time.time()
                    self.request_times_datacite = [
                        t for t in self.request_times_datacite
                        if current_time - t < self.datacite_rate_limit_period
                    ]

            self.request_times_datacite.append(current_time)

    def _rate_limit_crossref(self):
        with self.crossref_rate_limit_lock:
            current_time = time.time()
            self.request_times_crossref = [
                t for t in self.request_times_crossref
                if current_time - t < self.crossref_rate_limit_period
            ]
            if len(self.request_times_crossref) >= self.crossref_rate_limit_calls:
                sleep_time = (self.request_times_crossref[0] +
                              self.crossref_rate_limit_period - current_time)
                if sleep_time > 0:
                    jitter = random.uniform(0, 0.1)
                    time.sleep(sleep_time + jitter)
                    current_time = time.time()
                    self.request_times_crossref = [
                        t for t in self.request_times_crossref
                        if current_time - t < self.crossref_rate_limit_period
                    ]
            self.request_times_crossref.append(current_time)

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

    def verify_doi(self, doi, provider=None):
        try:
            normalized_doi = self.normalize_doi(doi)
            provider = provider or self.provider
            if provider.lower() == "crossref":
                return self.verify_crossref_doi(normalized_doi)
            else:
                return self.verify_datacite_doi(normalized_doi)
        except Exception as e:
            self._increment_counter('failed')
            return VerificationResult(
                doi=doi,
                exists=False,
                http_code=-1,
                error_message=f"Verification error: {str(e)}",
                provider=provider
            )

    def verify_datacite_doi(self, doi):
        self._rate_limit_datacite()
        session = self._get_session()
        try:
            url = f"https://api.datacite.org/works/{doi}"
            response = session.get(url)
            exists = response.status_code == 200

            result = VerificationResult(
                doi=doi,
                exists=exists,
                http_code=response.status_code,
                error_message="",
                provider="datacite"
            )

            if exists:
                if self.save_json or self.save_xml:
                    json_data = response.json()
                    if self.save_json:
                        with self.writer_lock:
                            json_path = os.path.join(
                                self.datacite_json_dir,
                                f"{doi.replace('/', '_')}.json"
                            )
                            with open(json_path, 'w') as f:
                                json.dump(json_data, f, indent=2)
                            result.json_path = json_path

                    if self.save_xml:
                        try:
                            xml_content = self.extract_xml_from_datacite_json(
                                json_data)
                            if xml_content:
                                with self.writer_lock:
                                    xml_path = os.path.join(
                                        self.datacite_xml_dir,
                                        f"{doi.replace('/', '_')}.xml"
                                    )
                                    with open(xml_path, 'w', encoding='utf-8') as f:
                                        f.write(xml_content)
                                    result.xml_path = xml_path
                        except ValueError as e:
                            result.error_message = f"XML extraction error: {str(e)}"
                            logging.warning(f"XML extraction failed for DOI {doi}: {str(e)}")

                self._increment_counter('successful')
            else:
                self._increment_counter('failed')

            if self.check_resolution:
                resolution_info = self.verify_resolution(doi)
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
                error_message=f"Verification error: {str(e)}",
                provider="datacite"
            )

    def verify_crossref_doi(self, doi):
        self._rate_limit_crossref()
        session = self._get_session()
        try:
            url = f"https://api.crossref.org/works/{doi}"
            response = session.get(url)
            exists = response.status_code == 200
            result = VerificationResult(
                doi=doi,
                exists=exists,
                http_code=response.status_code,
                error_message="",
                provider="crossref"
            )
            if exists:
                if self.save_json:
                    json_data = response.json()
                    with self.writer_lock:
                        json_path = os.path.join(
                            self.crossref_json_dir,
                            f"{doi.replace('/', '_')}.json"
                        )
                        with open(json_path, 'w') as f:
                            json.dump(json_data, f, indent=2)
                        result.json_path = json_path
                if self.save_xml:
                    try:
                        xml_content = self.fetch_crossref_xml(doi)
                        if xml_content:
                            with self.writer_lock:
                                xml_path = os.path.join(
                                    self.crossref_xml_dir,
                                    f"{doi.replace('/', '_')}.xml"
                                )
                                with open(xml_path, 'w', encoding='utf-8') as f:
                                    f.write(xml_content)
                                result.xml_path = xml_path
                    except Exception as e:
                        result.error_message = f"XML fetch error: {str(e)}"

                self._increment_counter('successful')

            else:
                self._increment_counter('failed')

            if self.check_resolution:
                resolution_info = self.verify_resolution(doi)
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
                error_message=f"Verification error: {str(e)}",
                provider="crossref"
            )

    def fetch_crossref_xml(self, doi):
        self._rate_limit_crossref()
        session = self._get_session()
        url = f"https://api.crossref.org/works/{doi}/transform/application/vnd.crossref.unixsd+xml"
        response = session.get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise ValueError(f"Failed to fetch Crossref XML. Status code: {response.status_code}")

    def extract_xml_from_datacite_json(self, json_data):
        try:
            xml_base64 = json_data['data']['attributes']['xml']
            xml_content = base64.b64decode(xml_base64).decode('utf-8')
            return xml_content
        except KeyError:
            raise ValueError("XML content not found in the JSON data")
        except base64.binascii.Error:
            raise ValueError("Invalid base64 encoding for XML content")

    def verify_resolution(self, doi):
        self._rate_limit_datacite()
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
                headers={'User-Agent': 'EZID - https://ezid.cdlib.org'}
            )

            if response.status_code >= 400:
                response = session.get(
                    url,
                    allow_redirects=True,
                    timeout=self.resolution_timeout,
                    headers={'User-Agent': 'EZID - https://ezid.cdlib.org'}
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

    def process_csv(self, csv_file, max_workers=1):
        report_path = os.path.join(self.output_dir, 'verification_report.csv')
        total_dois = sum(1 for line in open(csv_file)) - 1

        with open(report_path, 'w') as report_file:
            headers = [
                'doi', 'provider', 'exists', 'http_code',
                'error_message', 'json_path', 'xml_path'
            ]
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
                result.provider,
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
            has_provider = 'provider' in reader.fieldnames
            doi_data = []
            for row in reader:
                if row['doi']:
                    provider = row.get(
                        'provider') if has_provider else None
                    doi_data.append((row['doi'], provider))
        batch_size = 1000
        with tqdm(total=len(doi_data), desc="Verifying DOIs") as pbar:
            for i in range(0, len(doi_data), batch_size):
                batch = doi_data[i:i + batch_size]
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_doi = {
                        executor.submit(self.verify_doi, doi, provider): doi
                        for doi, provider in batch
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
            has_provider = 'provider' in reader.fieldnames
            with tqdm(total=total_dois, desc="Verifying DOIs") as pbar:
                for row in reader:
                    if row['doi']:
                        provider = row.get(
                            'provider') if has_provider else None
                        result = self.verify_doi(row['doi'], provider)
                        self._write_result(writer, result)
                        pbar.update(1)
                        time.sleep(0.1)


def get_default_config():
    return {
        'parallel': True,
        'max_threads': 2,
        'check_resolution': False,
        'resolution_timeout': 30,
        'max_redirects': 5,
        'save_xml': False,
        'save_json': False,
        'datacite_rate_limit_calls': 3000,
        'datacite_rate_limit_period': 300,
        'crossref_rate_limit_calls': 50,
        'crossref_rate_limit_period': 1
    }


def load_config(config_file=None):
    if config_file is None:
        logging.info(
            "No config file specified, using default configuration")
        return get_default_config()
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            default_config = get_default_config()
            default_config.update(config)
            return default_config
    except Exception as e:
        logging.error(f"Error loading config file: {str(e)}")
        return get_default_config()


def validate_provider_setup(input_file, provider_arg):
    if provider_arg is not None:
        if provider_arg.lower() not in ['datacite', 'crossref']:
            raise ValueError(f"Invalid provider specified: {provider_arg}. Must be either 'datacite' or 'crossref'")
        return False, provider_arg.lower()
    with open(input_file, 'r') as f:
        header = f.readline().strip().split(',')
        has_provider_column = 'provider' in header
        
        if not has_provider_column:
            raise ValueError(
                "No provider specified. Must either specify provider via --provider argument "
                "or include 'provider' column in input CSV"
            )
        if has_provider_column:
            providers = set()
            for line in f:
                row = line.strip().split(',')
                if len(row) > header.index('provider'):
                    provider = row[header.index('provider')].lower()
                    if provider and provider not in ['datacite', 'crossref']:
                        raise ValueError(
                            f"Invalid provider '{provider}' found in CSV. "
                            "Must be either 'datacite' or 'crossref'"
                        )
                    providers.add(provider)
            if not providers:
                raise ValueError("Provider column exists but contains no valid providers")
    return True, None


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='DOI Verification Tool for DataCite and Crossref')
    parser.add_argument('-i', '--input_file', required=True,
                        help='Input CSV file containing DOIs to verify (must have "doi" column, optional "provider" column)')
    parser.add_argument('-p', '--provider', choices=['datacite', 'crossref'],
                        help='DOI provider to use (crossref or datacite)', default=None)
    parser.add_argument('-d', '--output_dir', default="results",
                        help='Output directory for results')
    parser.add_argument('-c', '--config', help='Configuration file path')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
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
    parser.add_argument('--datacite-rate-limit-calls', type=int,
                        help='Number of calls allowed for DataCite rate limiting (overrides config)')
    parser.add_argument('--datacite-rate-limit-period', type=int,
                        help='Period in seconds for DataCite rate limiting (overrides config)')
    parser.add_argument('--crossref-rate-limit-calls', type=int,
                        help='Number of calls allowed for Crossref rate limiting (overrides config)')
    parser.add_argument('--crossref-rate-limit-period', type=int, help='Period in seconds for Crossref rate limiting (overrides config)'
                        )

    return parser.parse_args()


def setup_logging(output_dir, verbose):
    os.makedirs(output_dir, exist_ok=True)
    log_level = logging.INFO if verbose else logging.WARNING
    log_file = os.path.join(output_dir, 'application.log')
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )


def main():
    args = parse_arguments()
    try:
        os.makedirs(args.output_dir, exist_ok=True)
        setup_logging(args.output_dir, args.verbose)
        has_provider_column, provider_to_use = validate_provider_setup(
            args.input_file, args.provider
        )
        config = load_config(args.config)
        verifier_args = {
            'output_dir': args.output_dir,
            'save_json': args.json if args.json else config['save_json'],
            'save_xml': args.xml if args.xml else config['save_xml'],
            'check_resolution': args.check_resolution if args.check_resolution else config['check_resolution'],
            'resolution_timeout': args.resolution_timeout or config['resolution_timeout'],
            'max_redirects': args.max_redirects or config['max_redirects'],
            'provider': provider_to_use,
            'datacite_rate_limit_calls': args.datacite_rate_limit_calls or config['datacite_rate_limit_calls'],
            'datacite_rate_limit_period': args.datacite_rate_limit_period or config['datacite_rate_limit_period'],
            'crossref_rate_limit_calls': args.crossref_rate_limit_calls or config['crossref_rate_limit_calls'],
            'crossref_rate_limit_period': args.crossref_rate_limit_period or config['crossref_rate_limit_period']
        }
        verifier = VerifyDOI(**verifier_args)
        max_workers = args.threads if args.threads is not None else (
            config['max_threads'] if config['parallel'] else 1
        )
        if has_provider_column:
            verifier.provider = None
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