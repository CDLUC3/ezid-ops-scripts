import os
import argparse
import requests
import json

CLIENT_IDS = [
    "cdl.ucb",
    "cdl.ucsb",
    "cdl.cdl",
    "cdl.ucla",
    "cdl.ucsd",
    "cdl.ucr",
    "cdl.uci",
    "cdl.ucsc",
    "cdl.ucd",
    "cdl.ucsf",
    "cdl.ucm",
]

DATACITE_BASE_URL = "https://api.datacite.org/dois?"

REQUIRED_KEYS = ["data", "meta", "links"]

QUERIES = {
    "v3": "schema-version=3", 
    "v3_wo_res_type_gen": "schema-version=3&query=NOT%20types.resourceTypeGeneral:*",
    "v3_wt_contrib_funder": "schema-version=3&query=contributors.contributorType:Funder",
}

def retrive_datacite_records(url, allow_redirects=False):
    success = False
    status_code = -1
    text = ""
    err_msg = ""
    try:
        r = requests.get(url=url, allow_redirects=allow_redirects)
        status_code = r.status_code
        r.raise_for_status()
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    return success, status_code, text, err_msg


def extract_dois(records):
    doi_list = []
    for record in records:
        doi_list.append(record.get("id"))
    return doi_list

def extract_dois_from_file(input_filename, output_filename):
    with open(input_filename, 'r') as input_file:
        try:
            results = json.load(input_file)
            missing_keys = [key for key in REQUIRED_KEYS if key not in results]
            if missing_keys:
                print(f"missing keys: {missing_keys}")
            else:
                doi_list = extract_dois(results.get("data"), output_filename)
                with open(output_filename, 'w') as output_file:
                    for item in doi_list:
                        output_file.write(f"{item}\n")

        except Exception as ex:
            print(f"JSON error: {ex}; input file: {input_filename}")

def main():

    parser = argparse.ArgumentParser(description='Retrieve DataCite JSON records and generate DOI list.')

    # add input and output filename arguments to the parser
    parser.add_argument('-f', '--filename', type=str, required=False, help='Input: DataCite JSON file')
    parser.add_argument('-o', '--output', type=str, required=False, help='Output: file with extracted DOIs')

    args = parser.parse_args()
    input_filename = args.filename
    output_filename = args.output
    if input_filename and output_filename:
        extract_dois_from_file(input_filename, output_filename)
        exit(0)

    next = None
    for client_id in CLIENT_IDS:
        for query_key, query in QUERIES.items():
            page_setting = "page[cursor]=1&page[size]=1000"
            next = f"{DATACITE_BASE_URL}client-id={client_id}&{query}&{page_setting}"
            doi_list = []
            page = 1
            while next:
                print(next)
                success, status_code, text, err_msg = retrive_datacite_records(next, allow_redirects=True)
                if success:
                    results = json.loads(text)
                    filename = f"{client_id}_{query_key}_page{page}.json"
                    with open(filename, 'w') as file:
                        json.dump(results, file)

                    missing_keys = [key for key in REQUIRED_KEYS if key not in results]
                    if missing_keys:
                        print(f"missing keys: {missing_keys}")
                    else:
                        data = results.get("data")
                        doi_list.extend(extract_dois(data))

                        total = results.get("meta").get("total")
                        total_pages = results.get("meta").get("totalPages")
                        print(results.get("meta"))
                        print(results.get("links"))
                        print(f"total: {total}, total_pages: {total_pages}, current_page: {page}")
                        page += 1
                        next = results.get("links").get("next")
                        if next:
                            next = f"{next}&{query}"
                else:
                    print(f"Failed with tatus_code: {status_code}, err_msg: {err_msg}")

            # write DOIs to a file by client-id and query
            filename = f"{client_id}_{query_key}.txt"
            with open(filename, 'w') as output_file:
                for item in doi_list:
                    output_file.write(f"{item}\n")

        print(f"end of processing client: {client_id}")


if __name__ == "__main__":
    main()