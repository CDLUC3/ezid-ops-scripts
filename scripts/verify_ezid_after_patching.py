import os

import argparse
import requests
import base64
import re
import subprocess

BACKGROUND_JOBS_PRD = {
    "ezid-proc-binder": True,
    "ezid-proc-cleanup-async-queues": True,
    "ezid-proc-celery": True,
    "ezid-proc-crossref": True,
    "ezid-proc-datacite": True,
    "ezid-proc-download": True,
    "ezid-proc-expunge": True,
    "ezid-proc-newsfeed": True,
    "ezid-proc-search-indexer": True,
    "ezid-proc-stats": True,
    "ezid-proc-link-checker": True,
    "ezid-proc-link-checker-update": True,
}

BACKGROUND_JOBS_STG = {
    "ezid-proc-binder": True,
    "ezid-proc-cleanup-async-queues": True,
    "ezid-proc-celery": True,
    "ezid-proc-crossref": True,
    "ezid-proc-datacite": True,
    "ezid-proc-download": True,
    "ezid-proc-expunge": True,
    "ezid-proc-newsfeed": True,
    "ezid-proc-search-indexer": True,
    "ezid-proc-stats": True,
    "ezid-proc-link-checker": False,
    "ezid-proc-link-checker-update": False,
}

def get_status(url):
    success = False
    status_code = -1
    text = ""
    err_msg = ""
    try:
        r = requests.get(url=url, allow_redirects=False)
        status_code = r.status_code
        r.raise_for_status()
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    return success, status_code, text, err_msg

def post_data(url, user, password, data, content_type=None):
    success = False
    status_code = -1
    text = ""
    err_msg = ""

    if content_type == "form":
        content_type = "application/x-www-form-urlencoded"
    else:
        content_type = "text/plain; charset=UTF-8"

    headers = {
        "Content-Type": content_type,
        "Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode('utf-8')).decode('utf-8'),
    }
    try:
        r = requests.post(url=url, headers=headers, data=data)
        status_code = r.status_code
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    return success, status_code, text, err_msg

def get_record(filename):
    record = {}
    with open(filename, 'r', encoding="utf-8") as file: 
        lines = file.readlines()
        for line in lines:
            key, value = line.strip().split(':', 1)
            record[key] = value
    return record

def create_identifers(base_url, user, password):
    shoulder_file_pairs = [
        ("doi:10.15697/", "crossref_doi_10.15697_posted_content.txt"),
        ("doi:10.15697/", "crossref_doi_10.15697_journal.txt"),
        ("ark:/99999/fk4", "datacite_ark_99999_fk4.txt"), 
        ("doi:10.5072/FK2", "datacite_xml_doi_10.5072_FK2.txt"), 
        ("doi:10.5072/FK2", "datacite_doi_10.5072_FK2.txt"),
        ("ark:/99999/fk4", "dc_ark_99999_fk4.txt"),
        ("doi:10.5072/FK2", "dc_doi_10.5072_FK2.txt"),
        ("ark:/99999/fk4", "erc_ark_99999_fk4.txt"),
    ]

    status = []
    for (shoulder, filename) in shoulder_file_pairs:
        file_path = os.path.join("./test_records/", filename)
        record = get_record(file_path)
        data = toAnvl(record).encode("UTF-8")
        url = f"{base_url}/shoulder/{shoulder}"

        http_success, status_code, text, err_msg = post_data(url, user, password, data)
    
        id_created = None
        if http_success:
            # should returned text as:
            # success: doi:10.15697/FK27S78 | ark:/c5697/fk27s78
            # success: ark:/99999/fk4m631r0h
            # error: bad request - no such shoulder created
            if text.strip().startswith("success"):
                list_1 = text.split(':', 1)
                if len(list_1) > 1:
                    ids = list_1[1]
                    list_2 = ids.split("|")
                    if len(list_2) > 0:
                        id_created = list_2[0].strip()
        
        status.append((shoulder, id_created, text))

    return status
        
def escape (s, colonToo=False):
    if colonToo:
      p = "[%:\r\n]"
    else:
      p = "[%\r\n]"
    return re.sub(p, lambda c: "%%%02X" % ord(c.group(0)), str(s))

def toAnvl (record):
  # record: metadata dictionary
  # returns: string
    return "".join("%s: %s\n" % (escape(k, True), escape(record[k])) for k in sorted(record.keys()))

def verify_ezid_status(base_url, check_item_no):
    item = "Verify EZID status"
    success, status_code, text, err_msg = get_status(f"{base_url}/status")
    if success:
        expected_text = "success: EZID is up"
        try:
            assert text == expected_text
            print(f"ok {check_item_no} - {item}")
        except AssertionError as e:
            print(f"error {check_item_no} - {item} - AssertionError: returned text \"{text}\" does not match expected text: \"{expected_text}\"")
    else:
        print(f"error {check_item_no} - {item} - code({status_code}): {err_msg}")

def verify_ezid_version(base_url, version, check_item_no):
    item = "Verify EZID version"
    success, status_code, text, err_msg = get_status(f"{base_url}/version")
    if success:
        try:
            if version:
                assert text == version
                print(f"ok {check_item_no} - {item} - {version}")
            else:
                print(f"info {check_item_no} - EZID version - {text}")
        except AssertionError as e:
            print(f"error {check_item_no} - {item} - AssertionError: returned text \"{text}\" does not match expected text: \"{version}\"")
    else:
        print(f"error {check_item_no} - {item} - code({status_code}): {err_msg}")

def verify_search_function(base_url, check_item_no):
    item = "Verify search function"
    search_url = "search?filtered=t&title=California+Digital+Library&object_type=Dataset"
    success, status_code, text, err_msg = get_status(f"{base_url}/{search_url}")
    if success:
        print(f"ok {check_item_no} - {item}")
    else:
        print(f"error {check_item_no} - {item} - code({status_code}): {err_msg}")

def verify_create_identifier_status(user, password, base_url, check_item_no):
    print("## Create identifier")
    results = create_identifers(base_url, user, password)
    i = 0
    created_ids = []
    for shoulder, id_created, text in results:
        i += 1
        if id_created:
            print(f"ok {check_item_no}.{i} - {id_created} created")
            created_ids.append(id_created)
        else:
            print(f"error {check_item_no}.{i} - {text} on {shoulder}")
    return created_ids

def verify_update_identifier_status(user, password, base_url, identifiers, check_item_no):
    print("## Update identifier")
    if identifiers:
        id = identifiers[-1]
        data = {
            "_target": "https://cdlib.org/services/"
        }
        data = toAnvl(data).encode("UTF-8")
        url = f"{base_url}/id/{id}"
        http_success, status_code, text, err_msg = post_data(url, user, password, data)
        if http_success and status_code == 200:
            print(f"ok {check_item_no} - {id} updated with new data: {data}")
        else:
            print(f"error {check_item_no} - update {id} failed - status_code: {status_code}: {text}: {err_msg}")
    else:
        print(f"info {check_item_no} - no item to udpate")

def check_background_jobs(env, check_item_no):
    if env in ['test', 'dev']:
        print(f"## On {env}: Skip Check background job status")
        return
   
    print("## Check background job status")
    if env == "prd":
        background_jobs = BACKGROUND_JOBS_PRD
    else:
        background_jobs = BACKGROUND_JOBS_STG
    
    i = 0
    for job, should_be_running in background_jobs.items():
        i += 1
        cmd = f"cdlsysctl status {job} | grep 'active (running)'"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            if should_be_running:
                print(f"ok {check_item_no}.{i} - {job} active running")
            else:
                print(f"error {check_item_no}.{i} - {job} should not be running")
        else:
            if should_be_running:
                print(f"error {check_item_no}.{i} - {job} is not running")
            else:
                print(f"info {check_item_no}.{i} - {job} is not running")

def check_batch_download(user, password, base_url, check_item_no):
    print("## Check batch download from S3")
    data = {
        'format': 'csv',
        'type': 'ark',
        'column': '_id',
    }
    url = f"{base_url}/download_request"

    http_success, status_code, text, err_msg = post_data(url, user, password, data, content_type="form")
    if http_success and status_code == 200:
        # returned text:
        # success: https://ezid-stg.cdlib.org/s3_download/xTqyrjZDJz9zYRMz.csv.gz
        part_1 = text[:7]
        s3_file_url = text[9:]
        assert part_1, "success"

        count = 0
        success = False
        while count < 5: 
            success, status_code, text, err_msg = get_status(s3_file_url)
            if success:
                break
            sleep(3)
            count += 1

        if success:
            print(f"ok {check_item_no} - batch download file is available at: {s3_file_url}")
        else:
            print(f"error {check_item_no} - batch download failed: {s3_file_url} - status_code: {status_code}: {text}: {err_msg}")
    else:
        print(f"error {check_item_no} - batch download failed - status_code: {status_code}: {text}: {err_msg}")

def main():

    parser = argparse.ArgumentParser(description='Get EZID records by identifier.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=False, help='user name')
    parser.add_argument('-p', '--password', type=str, required=False, help='password')
    parser.add_argument('-v', '--version', type=str, required=False, help='version')
 
    args = parser.parse_args()
    env = args.env
    user = args.user
    password = args.password
    version = args.version

    if user is None:
        user = "apitest"
    if password is None:
        password = "apitest"
  
    base_urls = {
        "test": "http://127.0.0.1:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)
    
    verify_ezid_status(base_url, check_item_no="1.1")
    verify_ezid_version(base_url, version=version, check_item_no="1.2")

    verify_search_function(base_url, check_item_no="2")

    created_ids = verify_create_identifier_status(user, password, base_url, check_item_no="3")
    verify_update_identifier_status(user, password, base_url, created_ids, check_item_no="4")

    check_background_jobs(env, check_item_no="5")

    check_batch_download(user, password, base_url, check_item_no="6")
 


if __name__ == "__main__":
    main()

