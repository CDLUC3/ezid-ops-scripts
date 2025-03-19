import os
import re
import csv
import sys
import signal
import logging
import argparse
import requests
from datetime import datetime
from urllib.parse import urlencode

interrupted = False

def signal_handler(sig, frame):
    global interrupted
    print("\nGracefully shutting down... (Processed rows have been saved)")
    interrupted = True

signal.signal(signal.SIGINT, signal_handler)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Transform grant data from one CSV format to another.')
    parser.add_argument('-i', '--input', required=True, help='Path to the input CSV file')
    parser.add_argument('-o', '--output', required=True, help='Path to the output CSV file')
    parser.add_argument('-m', '--match-affiliations', action='store_true', help='Enable ROR affiliation matching for Institution Names')
    return parser.parse_args()

def get_template_row():
    return [
        {'name': 'Location', 'value': ''},
        {'name': 'Creator', 'value': 'University of California Office of the President'},
        {'name': 'Name Identifier', 'value': 'https://ror.org/00dmfq477'},
        {'name': 'Name Identifier Scheme', 'value': 'ROR'},
        {'name': 'Name Identifier Scheme URI', 'value': 'https://ror.org/'},
        {'name': 'Title', 'value': ''},
        {'name': 'Publisher', 'value': 'University of California Office of the President'},
        {'name': 'Publisher Identifier', 'value': 'https://ror.org/00dmfq477'},
        {'name': 'Publisher Identifier Scheme', 'value': 'ROR'},
        {'name': 'Publisher Identifier Scheme URI', 'value': 'https://ror.org/'},
        {'name': 'Publication Year', 'value': ''},
        {'name': 'Resource Type General', 'value': 'Other'},
        {'name': 'Resource Type', 'value': 'Grant'},
        {'name': 'Description', 'value': ''},
        {'name': 'Description Type', 'value': ''},
        {'name': 'Contributor Type', 'value': 'ProjectLeader'},
        {'name': 'Contributor Name', 'value': ''},
        {'name': 'Name Identifier', 'value': ''},
        {'name': 'Identifier Scheme', 'value': ''},
        {'name': 'Scheme URI', 'value': ''},
        {'name': 'Affiliation', 'value': ''},
        {'name': 'Affiliation Identifier', 'value': ''},
        {'name': 'Affiliation Identifier Scheme', 'value': ''},
        {'name': 'Affiliation Identifier Scheme URI', 'value': ''},
        {'name': 'Date', 'value': ''},
        {'name': 'Date Type', 'value': ''},
        {'name': 'Date Information', 'value': ''},
        {'name': 'Alternate Identifier', 'value': ''},
        {'name': 'Alternate Identifier Type', 'value': 'award-number'},
        {'name': 'Related Identifier', 'value': ''},
        {'name': 'Related Identifier Type', 'value': ''},
        {'name': 'Relation Type', 'value': ''},
        {'name': 'Funder Name', 'value': ''},
        {'name': 'Funder Identifier', 'value': ''},
        {'name': 'Funder Identifier Type', 'value': ''}
    ]

def get_target_fieldnames():
    template = get_template_row()
    return [field['name'] for field in template]

def read_input_csv(input_file_path):
    if not os.path.exists(input_file_path):
        sys.exit(f"Error: Input file '{input_file_path}' not found.")
    try:
        with open(input_file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            required_columns = ['Application ID', 'Project Title']
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                sys.exit(f"Error: Input CSV is missing required columns: {', '.join(missing_columns)}")
            return csvfile, reader
    except csv.Error as e:
        sys.exit(f"Error reading CSV file: {e}")
    except Exception as e:
        sys.exit(f"Error: {e}")

def normalize_abstract_text(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def query_affiliation(affiliation, version='2', use_quotes=False):
    chosen_result = None
    query_url = None
    try:
        base_url = f"https://api.ror.org/v{version}/organizations"
        query_value = f'"{affiliation}"' if use_quotes else affiliation
        params = {"affiliation": query_value}
        query_url = f"{base_url}?{urlencode(params)}"
        r = requests.get(base_url, params=params)
        r.raise_for_status()
        if not r.text:
            logging.error(f'Empty response received for affiliation: {affiliation}')
            return None, query_url
        try:
            api_response = r.json()
        except ValueError as json_err:
            logging.error(f'Invalid JSON response for affiliation: {affiliation}')
            logging.error(f'Response status code: {r.status_code}')
            logging.error(f'Response content: {r.text[:500]}')
            return None, query_url
        results = api_response.get('items', [])
        if results:
            for result in results:
                if result.get('chosen'):
                    chosen_id = result['organization']['id']
                    score = result['score']
                    chosen_result = chosen_id, score
                    break
    except requests.exceptions.RequestException as req_err:
        logging.error(f'Request error for affiliation: {affiliation}')
        logging.error(f'Error details: {req_err}')
    except Exception as e:
        logging.error(f'Unexpected error for affiliation: {affiliation}')
        logging.error(f'Error type: {type(e).__name__}')
        logging.error(f'Error details: {str(e)}')
    return chosen_result, query_url

def transform_row(input_row, template, match_affiliations=False):
    output_fields = [field.copy() for field in template]
    application_id = input_row.get('Application ID', '')
    affiliation = input_row.get('Institution Name', '')
    affiliation_identifier = None
    
    if match_affiliations and affiliation:
        chosen_result, _ = query_affiliation(affiliation, '2')
        if chosen_result:
            affiliation_identifier, _ = chosen_result
    
    for i, field in enumerate(output_fields):
        field_name = field['name']
        if field_name == 'Location' and application_id:
            output_fields[i]['value'] = f"https://rgpogrants.ucop.edu/files/1614305/f480589/index.html?appid={application_id}"
        elif field_name == 'Title':
            output_fields[i]['value'] = input_row.get('Project Title', '')
        elif field_name == 'Contributor Name':
            output_fields[i]['value'] = input_row.get('Principal Investigator', '')
        elif field_name == 'Affiliation':
            output_fields[i]['value'] = affiliation
        elif field_name == 'Affiliation Identifier':
            if match_affiliations and affiliation_identifier:
                output_fields[i]['value'] = affiliation_identifier
        elif field_name == 'Affiliation Identifier Scheme':
            if match_affiliations and affiliation_identifier:
                output_fields[i]['value'] = 'ROR'
        elif field_name == 'Affiliation Identifier Scheme URI':
            if match_affiliations and affiliation_identifier:
                output_fields[i]['value'] = 'https://ror.org/'
        elif field_name == 'Description':
            output_fields[i]['value'] = normalize_abstract_text(input_row.get('Lay Abstract', ''))
        elif field_name == 'Description Type':
            description_value = ''
            for f in output_fields:
                if f['name'] == 'Description':
                    description_value = f['value']
                    break
            if description_value:
                output_fields[i]['value'] = 'Abstract'
        elif field_name == 'Date':
            output_fields[i]['value'] = input_row.get('Start Date', '')
        elif field_name == 'Date Type':
            date_value = ''
            for f in output_fields:
                if f['name'] == 'Date':
                    date_value = f['value']
                    break
            if date_value:
                output_fields[i]['value'] = 'Issued'
        elif field_name == 'Alternate Identifier' and application_id:
            output_fields[i]['value'] = application_id
    return [field['value'] for field in output_fields]

def initialize_output_csv(output_file_path, fieldnames):
    try:
        with open(output_file_path, 'w', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(fieldnames)
        return True
    except Exception as e:
        sys.exit(f"Error initializing output CSV: {e}")

def append_to_output_csv(output_file_path, row_data):
    try:
        with open(output_file_path, 'a', encoding='utf-8', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(row_data)
        return True
    except Exception as e:
        logging.error(f"Error appending to output CSV: {e}")
        return False

def main():
    global interrupted
    args = parse_arguments()
    template = get_template_row()
    target_fieldnames = get_target_fieldnames()
    
    if args.match_affiliations:
        now = datetime.now()
        script_start = now.strftime("%Y%m%d_%H%M%S")
        logging.basicConfig(filename=f'{script_start}_affiliation_matching.log',
                          level=logging.DEBUG,
                          format='%(asctime)s %(levelname)s %(message)s')
        logging.info("Starting transformation with affiliation matching enabled")
    
    initialize_output_csv(args.output, target_fieldnames)
    
    csv_file, reader = read_input_csv(args.input)
    
    try:
        total_rows = 0
        processed_rows = 0
        with open(args.input, 'r', encoding='utf-8-sig') as f:
            total_rows = sum(1 for _ in csv.reader(f)) - 1
        
        print(f"Processing {total_rows} rows...")
        for row in reader:
            if interrupted:
                break
                
            transformed_row = transform_row(row, template, args.match_affiliations)
            append_to_output_csv(args.output, transformed_row)
            
            processed_rows += 1
            if processed_rows % 10 == 0 or processed_rows == total_rows:
                progress = (processed_rows / total_rows) * 100
                print(f"Progress: {processed_rows}/{total_rows} rows ({progress:.1f}%)", end='\r')
        
        print("\nTransformation complete. Output written to", args.output)
        if interrupted:
            print(f"Process was interrupted. {processed_rows}/{total_rows} rows were processed.")
        
    except Exception as e:
        logging.error(f"Error during processing: {e}")
        print(f"Error during processing: {e}")
        print(f"Partial results saved to {args.output} ({processed_rows} rows processed)")
    finally:
        csv_file.close()

if __name__ == "__main__":
    main()