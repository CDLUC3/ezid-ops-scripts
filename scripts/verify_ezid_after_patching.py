import os

import argparse
import requests
import base64
import re
import subprocess
import time
import pdb
from requests.auth import HTTPBasicAuth
import shortuuid


class VerifyAfterPatching:
    BACKGROUND_JOBS_PRD = {
        "ezid-proc-cleanup-async-queues": True,
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
        "ezid-proc-cleanup-async-queues": True,
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

    @staticmethod
    def get_status(url, allow_redirects=False):
        success = False
        status_code = -1
        text = ""
        err_msg = ""
        location = ""
        try:
            r = requests.get(url=url, allow_redirects=allow_redirects)
            status_code = r.status_code
            r.raise_for_status()
            text = r.text
            success = True
            location = r.headers.get("Location", ""),
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
            err_msg = "HTTPError: " + str(e)[:200]
        return {
            'success': success,
            'status_code': status_code,
            'text': text,
            'err_msg': err_msg,
            'location': location,
            }

    @staticmethod
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

    @staticmethod
    def get_record(filename):
        record = {}
        with open(filename, 'r', encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.strip().split(':', 1)
                record[key] = value
        return record

    @staticmethod
    def _create_identifier(base_url, user, password, status='reserved'):
        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        file_path = os.path.join("./test_records/", filename)
        record = VerifyAfterPatching.get_record(file_path)
        data = f"_status: {status}\n".encode("UTF-8") + VerifyAfterPatching.toAnvl(record).encode("UTF-8")
        url = f"{base_url}/shoulder/{shoulder}"

        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password, data)

        id_created = None
        if http_success and text.strip().startswith("success"):
            list_1 = text.split(':', 1)
            if len(list_1) > 1:
                ids = list_1[1]
                list_2 = ids.split("|")
                if len(list_2) > 0:
                    id_created = list_2[0].strip()

        return shoulder, id_created, text

    @staticmethod
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
            record = VerifyAfterPatching.get_record(file_path)
            data = VerifyAfterPatching.toAnvl(record).encode("UTF-8")
            url = f"{base_url}/shoulder/{shoulder}"

            http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password, data)

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

    @staticmethod
    def escape(s, colonToo=False):
        if colonToo:
            p = "[%:\r\n]"
        else:
            p = "[%\r\n]"
        return re.sub(p, lambda c: "%%%02X" % ord(c.group(0)), str(s))

    @staticmethod
    def toAnvl(record):
        # record: metadata dictionary
        # returns: string
        return "".join("%s: %s\n" % (VerifyAfterPatching.escape(k, True), VerifyAfterPatching.escape(record[k])) for k in sorted(record.keys()))

    @staticmethod
    def verify_ezid_status(base_url, check_item_no):
        print ("## EZID status")
        status = VerifyAfterPatching.get_status(f"{base_url}/status")
        if status['success']:
            expected_text = "success: EZID is up"
            try:
                assert status['text'] == expected_text
                print(f"  ok - returned status {status['text']}")
            except AssertionError as e:
                print(f"  Error {check_item_no} - {item} - AssertionError: returned text \"{status['text']}\" does not match expected text: \"{expected_text}\"")
        else:
            print(f"  Error {check_item_no} - {item} - code({status['status_code']}): {status['err_msg']}")

    @staticmethod
    def verify_ezid_version(base_url, version, check_item_no):
        print("## EZID version")
        status = VerifyAfterPatching.get_status(f"{base_url}/version")
        if status['success']:
            try:
                if version:
                    assert status['text'] == version
                    print(f"  ok - version:{item} - {version}")
                else:
                    print(f"  Info {check_item_no} - EZID version - {status['text']}")
            except AssertionError as e:
                print(f"  Error {check_item_no} - {item} - AssertionError: returned text \"{status['text']}\" does not match expected text: \"{version}\"")
        else:
            print(f"  Error {check_item_no} - {item} - code({status['status_code']}): {status['err_msg']}")

    @staticmethod
    def verify_search_function(base_url, check_item_no):
        print("## Search function")
        search_url = "search?filtered=t&identifier=ark%3A%2F13030%2Fm5z94194"
        status = VerifyAfterPatching.get_status(f"{base_url}/{search_url}")
        if status['success'] and status['status_code'] == 200:
            print(f"  ok - search results")
        else:
            print(f"  Error {check_item_no} - {item} - code({status['status_code']}): {status['err_msg']}")

    @staticmethod
    def verify_one_time_login(base_url, user, password):
        print("## Verify one time login and denied access")
        login_url = f"{base_url}/login"
        test_url = f"{base_url}/shoulder/ark:/99999/fk4"  # try minting an identifier, w/ POST
        unauthorized_url = f"{base_url}/shoulder/ark:/99166/p9"  # try minting unauthorized identifier, w/ POST

        # Start a session to persist cookies
        session = requests.Session()

        # Perform login using HTTP Basic Auth
        response = session.get(login_url, auth=HTTPBasicAuth(user, password))

        if response.status_code != 200:
            print(f"  Error: Login failed -- {response.status_code} - {response.text.strip()}")
            return None

        # Session cookie is now stored in session.cookies
        print("  ok - Login successful. Session cookie obtained")

        # Perform a test request using the authenticated session
        verify_response = session.post(test_url)
        if verify_response.status_code == 201:
            print("  ok - Session verified")
        else:
            print(f"  error: authenticated session failed: {verify_response.status_code} - {verify_response.text.strip()}")

        # Perform a test request that should be unauthorized
        verify_response = session.post(unauthorized_url)
        if verify_response.status_code == 403:
            print("  ok - Correct response of permission denied for an unauthorized shoulder")
        else:
            print(f"  error:  unauthorized request failed - {verify_response.status_code} - {verify_response.text.strip()}")

        # try with a bad cookie and be sure it fails
        session.cookies.set("sessionid", "bad_cookie_value")

        # Perform a test request using the bad session
        verify_response = session.post(test_url)
        if verify_response.status_code == 401:
            print("  ok - Session gives bad request for bad cookie")
        else:
            print(f"  error: bad session should fail - {verify_response.status_code} - {verify_response.text.strip()}")

        # try with a cleared cookie to get a status code.  I believe it should be 401, but EZID seems to return 400
        # which may be a bug
        session.cookies.clear()
        verify_response = session.post(test_url)
        if verify_response.status_code == 401:
            print("  ok - Session gives bad request for cleared cookie")
        else:
            print(f"  error: cleared session should fail - {verify_response.status_code} - {verify_response.text.strip()}")

    @staticmethod
    def verify_create_identifier_status(user, password, base_url, check_item_no):
        print("## Mint (create) identifier")
        results = VerifyAfterPatching.create_identifers(base_url, user, password)
        i = 0
        created_ids = []
        for shoulder, id_created, text in results:
            if id_created:
                print(f"  ok - {id_created} created")
                created_ids.append(id_created)
            else:
                print(f"  Error - {text} on {shoulder}")
        return created_ids

    @staticmethod
    def verify_update_identifier_status(user, password, base_url, identifiers, check_item_no):
        print("## Update identifier")
        if identifiers:
            for index, id in enumerate(identifiers):
                data = {
                    "_target": "https://cdlib.org/services/"
                }
                data = VerifyAfterPatching.toAnvl(data).encode("UTF-8")
                url = f"{base_url}/id/{id}"
                http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password, data)
                if http_success and status_code == 200:
                    print(f"  ok - {id} updated with new data: {data}")
                else:
                    print(f"  Error - update {id} failed - status_code: {status_code}: {text}: {err_msg}")
        else:
            print(f"  Info {check_item_no} - no item to udpate")

    @staticmethod
    def verify_reserve_and_delete_identifier(user, password, base_url):
        print("## Reserve and delete identifier")
        shoulder, id_created, text = VerifyAfterPatching._create_identifier(base_url, user, password, status='reserved')
        if id_created:
            print(f"  ok - {id_created} reserved")
            # delete the identifier
            url = f"{base_url}/id/{id_created}"
            response = requests.delete(url, auth=(user, password))
            if response.status_code == 200:
                print(f"  ok - {id_created} deleted")
            else:
                print(f"  Error - delete {id_created} failed - status_code: {status_code}: {text}: {err_msg}")
        else:
            print(f"  Error - reserve {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")

    @staticmethod
    def verify_status_transitions_for_identifier(user, password, base_url):
        print("## Verify status transitions for identifier")
        shoulder, id_created, text = VerifyAfterPatching._create_identifier(base_url, user, password, status='reserved')

        if not id_created:
            print(f"  Error - reserve {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        print(f"  ok - {id_created} reserved")

        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        file_path = os.path.join("./test_records/", filename)
        record = VerifyAfterPatching.get_record(file_path)
        data = VerifyAfterPatching.toAnvl(record).encode("UTF-8")
        url = f"{base_url}/id/{id_created}"

        # update the identifier to public status
        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password,
                                                             f"_status: public\n".encode("UTF-8") + data)

        if http_success and status_code == 200:
            print(f"  ok - {id_created} made public")
        else:
            print(f"  Error - 'public' status change {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # update the identifier to unavailable status
        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password,
                                                             f"_status: unavailable | my cat has fleas\n".encode("UTF-8") + data)
        if http_success and status_code == 200:
            print(f"  ok - {id_created} made unavailable")
        else:
            print(f"  Error - 'unavailable' status change {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # make unavailable to public again
        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password,
                                                             f"_status: public\n".encode("UTF-8") + data)

        if http_success and status_code == 200:
            print(f"  ok - {id_created} made public from unavailable")
        else:
            print("  Error - 'public' status change after unavailable {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # update the identifier to reserved status and it should fail
        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password,
                                                             f"_status: reserved\n".encode("UTF-8") + data)

        if http_success and status_code == 400:
            print(f"  ok - {id_created} cannot be made reserved again once public")
        else:
            print(
                f"  Error - 'reserved' status shouldn't be allowed once public {id_created} - status_code: {status_code}: {text}: {err_msg}")

    @staticmethod
    def verify_create_or_update_identifier(user, password, base_url):
        print("## Create or update identifier")

        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        my_id = f'{shoulder}-{shortuuid.uuid()}'
        file_path = os.path.join("./test_records/", filename)
        record = VerifyAfterPatching.get_record(file_path)
        data = VerifyAfterPatching.toAnvl(record).encode("UTF-8")

        url = f"{base_url}/id/{my_id}"

        response = requests.put(url, params={'update_if_exists': 'yes'}, auth=(user, password))

        if response.status_code in  (200,201):
            print(f"  ok - {my_id} created")
        else:
            print(f"  Error - create {my_id} failed - status_code: {response.status_code}: {response.text.strip()}")
            return

        # now update the same identifier with the same call again, and it should exist now
        response = requests.put(url, params={'update_if_exists': 'yes'}, auth=(user, password))
        if response.status_code in (200,201):
            print(f"  ok - {my_id} updated")
        else:
            print(f"  Error - update {my_id} failed - status_code: {response.status_code}: {response.text.strip()}")


    @staticmethod
    def verify_prefix_matching(user, password, base_url):
        print("## Verify prefix matching")
        shoulder, id_created, text = VerifyAfterPatching._create_identifier(base_url, user, password, status='public')
        if not id_created:
            print(f"  Error - creating on {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        response = requests.get(f'{base_url}/{id_created}/andmore?prefix_match=yes')
        if response.status_code == 200:
            print(f"  ok - {id_created} prefix match worked with extra string on end of ID being ignored")
        else:
            print(f"  Error - prefix match failed with extra string on end of ID - status_code: {response.status_code}: {response.text.strip()}")

    @staticmethod
    def verify_introspection(user, password, base_url):
        print('## Verify introspection')
        shoulder, id_created, text = VerifyAfterPatching._create_identifier(base_url, user, password, status='public')
        if not id_created:
            print(f"  Error - creating on {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        response = requests.get(f'{base_url}/{id_created}??')
        if response.status_code == 200 and 'what: test record under shoulder - ark:/99999/fk4' in response.text:
            print(f"  ok - ?? for instrospection: {id_created} returned introspection request")
        else:
            print(
                f"  Error - ?? for instrospection - status_code: {response.status_code}: {response.text.strip()}")

        response = requests.get(f'{base_url}/{id_created}?info')
        if response.status_code == 200 and 'what: test record under shoulder - ark:/99999/fk4' in response.text:
            print(f"  ok - ?info for instrospection: {id_created} returned introspection request")
        else:
            print(
                f"  Error - ?info for instrospection - status_code: {response.status_code}: {response.text.strip()}")

    @staticmethod
    def check_background_jobs(env):
        print('## Background job status')
        if env in ['test', 'dev']:
            print(f"  On {env}: Skip Check background job status")
            return

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
                    print(f"  ok - {job} active running")
                else:
                    print(f"  Error - {job} should not be running")
            else:
                if should_be_running:
                    print(f"  Error  - {job} is not running")
                else:
                    print(f"  Info - {job} is not running")

    @staticmethod
    def check_batch_download(user, password, base_url, notify_email):
        print("## Check batch download from S3")
        data = {
            'format': 'csv',
            'type': 'ark',
            'column': '_id',
            'notify': notify_email,
        }
        url = f"{base_url}/download_request"

        # post download requst
        http_success, status_code, text, err_msg = VerifyAfterPatching.post_data(url, user, password, data, content_type="form")
        if http_success and status_code == 200:
            # download request was successfully processed with "success" and downloadable url in the response body
            # success: https://ezid-stg.cdlib.org/s3_download/xTqyrjZDJz9zYRMz.csv.gz
            part_1 = text[:7]
            s3_file_url = text[9:]
            assert part_1, "success"

            # batch download is processed asynchronously, wait until the file is ready for download
            count = 0
            success = False
            wait_time = 0
            while count < 60:
                status = VerifyAfterPatching.get_status(s3_file_url, allow_redirects=True)
                success = status['success']
                if success:
                    break
                time.sleep(5)
                wait_time += 5
                print(f"  waiting for file to become available: {wait_time}s passed")
                count += 1

            if success:
                print(f"  ok - batch download file is available at: {s3_file_url}")
                print(f"  Info: Please check account {notify_email} for email with Subject: Your EZID batch download link")
            else:
                print(f"  Error - batch download failed: {s3_file_url} - status_code: {status_code}: {text}: {err_msg}")
        else:
            print(f"  Error - batch download failed - status_code: {status_code}: {text}: {err_msg}")

    @staticmethod
    def check_resolver(base_url, check_item_no):
        item = "Verify Resolver function"
        id = "ark%3A%2F12345%2Ffk1234"
        status = VerifyAfterPatching.get_status(f"{base_url}/{id}", allow_redirects=False)
        if status['success'] and status['status_code'] == 302 and 'http://www.cdlib.org/services' in status['location']:
            print(f"  ok - {item}")
        else:
            print(f"  Error - {item} - code({status['status_code']}): {status['err_msg']}")


def main():

    VAP = VerifyAfterPatching()
    parser = argparse.ArgumentParser(description='Get EZID records by identifier.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=True, help='user name')
    parser.add_argument('-p', '--password', type=str, required=True, help='password')
    parser.add_argument('-v', '--version', type=str, required=False, help='version')
    parser.add_argument('-n', '--notify_email', type=str, required=True, help='Email address to receive download notification.')
 
    args = parser.parse_args()
    env = args.env
    user = args.user
    password = args.password
    version = args.version
    notify_email = args.notify_email
  
    base_urls = {
        "test": "http://127.0.0.1:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    VAP.verify_ezid_status(base_url, check_item_no="1.1")
    VAP.verify_ezid_version(base_url, version=version, check_item_no="1.2")

    VAP.verify_search_function(base_url, check_item_no="2")

    VAP.verify_one_time_login(base_url, user, password)

    created_ids = VAP.verify_create_identifier_status(user, password, base_url, check_item_no="3")
    VAP.verify_update_identifier_status(user, password, base_url, created_ids, check_item_no="4")

    VAP.verify_reserve_and_delete_identifier(user, password, base_url)

    VAP.verify_status_transitions_for_identifier(user, password, base_url)

    VAP.verify_create_or_update_identifier(user, password, base_url)

    VAP.verify_prefix_matching(user, password, base_url)

    VAP.verify_introspection(user, password, base_url)

    VAP.check_background_jobs(env)

    VAP.check_batch_download(user, password, base_url, notify_email)

    VAP.check_resolver(base_url)

if __name__ == "__main__":
    main()

