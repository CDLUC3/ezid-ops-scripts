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


class VerifyEzidStatus:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password

    def _get_status(self, url, allow_redirects=False):
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

    def _parse_id_created(self, text):
        if text.strip().startswith("success"):
            list_1 = text.split(':', 1)
            if len(list_1) > 1:
                ids = list_1[1]
                list_2 = ids.split("|")
                if len(list_2) > 0:
                    return list_2[0].strip()
        return None


    def _post_data(self, url, data, content_type=None):
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
            "Authorization": "Basic " + base64.b64encode(f"{self.user}:{self.password}".encode('utf-8')).decode('utf-8'),
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


    def _get_record(self, filename):
        record = {}
        with open(filename, 'r', encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.strip().split(':', 1)
                record[key] = value
        return record


    def _create_identifier(self, status='reserved'):
        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        file_path = os.path.join("./test_records/", filename)
        record = self._get_record(file_path)
        data = f"_status: {status}\n".encode("UTF-8") + self._toAnvl(record).encode("UTF-8")
        url = f"{self.base_url}/shoulder/{shoulder}"

        http_success, status_code, text, err_msg = self._post_data(url, data)

        id_created = self._parse_id_created(text) if http_success else None

        return shoulder, id_created, text

    def _create_identifiers(self):
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
            record = self._get_record(file_path)
            data = self._toAnvl(record).encode("UTF-8")
            url = f"{self.base_url}/shoulder/{shoulder}"

            http_success, status_code, text, err_msg = self._post_data(url, data)

            id_created = self._parse_id_created(text) if http_success else None

            status.append((shoulder, id_created, text))

        return status

    def _escape(self, s, colonToo=False):
        if colonToo:
            p = "[%:\r\n]"
        else:
            p = "[%\r\n]"
        return re.sub(p, lambda c: "%%%02X" % ord(c.group(0)), str(s))

    def _toAnvl(self, record):
        # record: metadata dictionary
        # returns: string
        return "".join("%s: %s\n" % (self._escape(k, True), self._escape(record[k])) for k in sorted(record.keys()))

    def verify_ezid_status(self):
        print ("## EZID status")
        status = self._get_status(f"{self.base_url}/status")
        if status['success']:
            expected_text = "success: EZID is up"
            try:
                assert status['text'] == expected_text
                print(f"  ok - returned status {status['text']}")
            except AssertionError as e:
                print(f"  Error - AssertionError: returned text \"{status['text']}\" does not match expected text: \"{expected_text}\"")
        else:
            print(f"  Error - code({status['status_code']}): {status['err_msg']}")

    def verify_ezid_version(self, version):
        print("## EZID version")
        status = self._get_status(f"{self.base_url}/version")
        if status['success']:
            try:
                if version:
                    assert status['text'] == version
                    print(f"  ok - version: {version}")
                else:
                    print(f"  Info - EZID version - {status['text']}")
            except AssertionError as e:
                print(f"  Error - AssertionError: returned text \"{status['text']}\" does not match expected text: \"{version}\"")
        else:
            print(f"  Error - code({status['status_code']}): {status['err_msg']}")

    def verify_search_function(self):
        print("## Search function")
        search_url = "search?filtered=t&identifier=ark%3A%2F13030%2Fm5z94194"
        status = self._get_status(f"{self.base_url}/{search_url}")
        if status['success'] and status['status_code'] == 200:
            print(f"  ok - search results")
        else:
            print(f"  Error - code({status['status_code']}): {status['err_msg']}")


    def verify_one_time_login(self):
        print("## Verify one time login and denied access")
        login_url = f"{self.base_url}/login"
        test_url = f"{self.base_url}/shoulder/ark:/99999/fk4"  # try minting an identifier, w/ POST
        unauthorized_url = f"{self.base_url}/shoulder/ark:/99166/p9"  # try minting unauthorized identifier, w/ POST

        # Start a session to persist cookies
        session = requests.Session()

        # Perform login using HTTP Basic Auth
        response = session.get(login_url, auth=HTTPBasicAuth(self.user, self.password))

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


    def verify_create_identifier_status(self):
        print("## Mint (create) identifier")
        results = self._create_identifiers()
        i = 0
        created_ids = []
        for shoulder, id_created, text in results:
            if id_created:
                print(f"  ok - {id_created} created")
                created_ids.append(id_created)
            else:
                print(f"  Error - {text} on {shoulder}")
        return created_ids


    def verify_update_identifier_status(self, identifiers):
        print("## Update identifier")
        if identifiers:
            for index, id in enumerate(identifiers):
                data = {
                    "_target": "https://cdlib.org/services/"
                }
                data = self._toAnvl(data).encode("UTF-8")
                url = f"{self.base_url}/id/{id}"
                http_success, status_code, text, err_msg = self._post_data(url, data)
                if http_success and status_code == 200:
                    print(f"  ok - {id} updated with new data: {data}")
                else:
                    print(f"  Error - update {id} failed - status_code: {status_code}: {text}: {err_msg}")
        else:
            print(f"  Info - no item to update")


    def verify_reserve_and_delete_identifier(self):
        print("## Reserve and delete identifier")
        shoulder, id_created, text = self._create_identifier(status='reserved')
        if id_created:
            print(f"  ok - {id_created} reserved")
            # delete the identifier
            url = f"{self.base_url}/id/{id_created}"
            response = requests.delete(url, auth=(self.user, self.password))
            if response.status_code == 200:
                print(f"  ok - {id_created} deleted")
            else:
                print(f"  Error - delete {id_created} failed - status_code: {status_code}: {text}: {err_msg}")
        else:
            print(f"  Error - reserve {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")


    def verify_status_transitions_for_identifier(self):
        print("## Verify status transitions for identifier")
        shoulder, id_created, text = self._create_identifier(status='reserved')

        if not id_created:
            print(f"  Error - reserve {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        print(f"  ok - {id_created} reserved")

        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        file_path = os.path.join("./test_records/", filename)
        record = self._get_record(file_path)
        data = self._toAnvl(record).encode("UTF-8")
        url = f"{self.base_url}/id/{id_created}"

        # update the identifier to public status
        http_success, status_code, text, err_msg = self._post_data(url,
                                                             f"_status: public\n".encode("UTF-8") + data)

        if http_success and status_code == 200:
            print(f"  ok - {id_created} made public")
        else:
            print(f"  Error - 'public' status change {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # update the identifier to unavailable status
        http_success, status_code, text, err_msg = self._post_data(url,
                                                             f"_status: unavailable | my cat has fleas\n".encode("UTF-8") + data)
        if http_success and status_code == 200:
            print(f"  ok - {id_created} made unavailable")
        else:
            print(f"  Error - 'unavailable' status change {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # make unavailable to public again
        http_success, status_code, text, err_msg = self._post_data(url,
                                                             f"_status: public\n".encode("UTF-8") + data)

        if http_success and status_code == 200:
            print(f"  ok - {id_created} made public from unavailable")
        else:
            print("  Error - 'public' status change after unavailable {id_created} failed - status_code: {status_code}: {text}: {err_msg}")

        # update the identifier to reserved status and it should fail
        http_success, status_code, text, err_msg = self._post_data(url,
                                                             f"_status: reserved\n".encode("UTF-8") + data)

        if http_success and status_code == 400:
            print(f"  ok - {id_created} cannot be made reserved again once public")
        else:
            print(
                f"  Error - 'reserved' status shouldn't be allowed once public {id_created} - status_code: {status_code}: {text}: {err_msg}")


    def verify_create_or_update_identifier(self):
        print("## Create or update identifier with ?update_if_exists=yes")

        shoulder, filename = ("ark:/99999/fk4", "erc_ark_99999_fk4.txt")
        my_id = f'{shoulder}-{shortuuid.uuid()}'
        file_path = os.path.join("./test_records/", filename)
        record = self._get_record(file_path)
        data = self._toAnvl(record).encode("UTF-8")

        url = f"{self.base_url}/id/{my_id}"

        response = requests.put(url, params={'update_if_exists': 'yes'}, auth=(self.user, self.password))

        if response.status_code in  (200,201):
            print(f"  ok - {my_id} created")
        else:
            print(f"  Error - create {my_id} failed - status_code: {response.status_code}: {response.text.strip()}")
            return

        # now update the same identifier with the same call again, and it should exist now
        response = requests.put(url, params={'update_if_exists': 'yes'}, auth=(self.user, self.password))
        if response.status_code in (200,201):
            print(f"  ok - {my_id} updated")
        else:
            print(f"  Error - update {my_id} failed - status_code: {response.status_code}: {response.text.strip()}")



    def verify_prefix_matching(self):
        print("## Verify prefix matching")
        shoulder, id_created, text = self._create_identifier(status='public')
        if not id_created:
            print(f"  Error - creating on {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        response = requests.get(f'{self.base_url}/{id_created}/andmore?prefix_match=yes')
        if response.status_code == 200:
            print(f"  ok - {id_created} prefix match worked with extra string on end of ID being ignored")
        else:
            print(f"  Error - prefix match failed with extra string on end of ID - status_code: {response.status_code}: {response.text.strip()}")


    def verify_introspection(self):
        print('## Verify introspection')
        shoulder, id_created, text = self._create_identifier(status='public')
        if not id_created:
            print(f"  Error - creating on {shoulder} failed - status_code: {status_code}: {text}: {err_msg}")
            return

        response = requests.get(f'{self.base_url}/{id_created}??')
        if response.status_code == 200 and 'what: test record under shoulder - ark:/99999/fk4' in response.text:
            print(f"  ok - ?? for instrospection: {id_created} returned introspection request")
        else:
            print(
                f"  Error - ?? for instrospection - status_code: {response.status_code}: {response.text.strip()}")

        response = requests.get(f'{self.base_url}/{id_created}?info')
        if response.status_code == 200 and 'what: test record under shoulder - ark:/99999/fk4' in response.text:
            print(f"  ok - ?info for instrospection: {id_created} returned introspection request")
        else:
            print(
                f"  Error - ?info for instrospection - status_code: {response.status_code}: {response.text.strip()}")


    def check_batch_download(self, notify_email):
        print("## Check batch download from S3")
        data = {
            'format': 'csv',
            'type': 'ark',
            'column': '_id',
            'notify': notify_email,
        }
        url = f"{self.base_url}/download_request"

        # post download requst
        http_success, status_code, text, err_msg = self._post_data(url, data, content_type="form")
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
                status = self._get_status(s3_file_url, allow_redirects=True)
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


    def check_resolver(self):
        print("## Verify Resolver function")
        id = "ark%3A%2F12345%2Ffk1234"
        status = self._get_status(f"{self.base_url}/{id}", allow_redirects=False)
        if status['success'] and status['status_code'] == 302 and 'http://www.cdlib.org/services' in status['location']:
            print(f"  ok - resolver function worked for {id}")
        else:
            print(f"  Error - resolver - code({status['status_code']}): {status['err_msg']}")


def main():

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

    ves = VerifyEzidStatus(base_url, user, password)

    ves.verify_ezid_status()
    ves.verify_ezid_version(version)

    ves.verify_search_function()

    ves.verify_one_time_login()

    created_ids = ves.verify_create_identifier_status()
    ves.verify_update_identifier_status(created_ids)

    ves.verify_reserve_and_delete_identifier()

    ves.verify_status_transitions_for_identifier()

    ves.verify_create_or_update_identifier()

    ves.verify_prefix_matching()

    ves.verify_introspection()

    ves.check_batch_download(notify_email)

    ves.check_resolver()

if __name__ == "__main__":
    main()
