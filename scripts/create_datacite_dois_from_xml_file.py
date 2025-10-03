import os

import argparse
import requests
import base64
import csv
from pathlib import Path
import re

class EZIDRecordCreator:
    def __init__(self, base_url, user, password, file_base_path, config_file):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.file_base_path = file_base_path
        self.config_file = config_file

    def _put_data(self, url, data, content_type=None):
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
            r = requests.put(url=url, headers=headers, data=data)
            status_code = r.status_code
            text = r.text
            success = True
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
            err_msg = "HTTPError: " + str(e)[:200]
        return success, status_code, text, err_msg

    def create_record(self, doi, record_metadata):
        url = f"{self.base_url}/id/{doi}"
        content_type = "text/plain; charset=UTF-8"
        success, status_code, text, err_msg = self._put_data(url, record_metadata, content_type)
        return success, status_code, text, err_msg


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
    

    def create_record_from_xml(self):
        csv_file = Path(self.file_base_path) / self.config_file

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record_id = f"doi:{row['doi']}"
                filename = row["filename"]
                target_url = row["url"]

                # Read the XML file contents
                xml_path = Path(self.file_base_path) / filename
                if not xml_path.exists():
                    print(f"Warning: File {filename} not found, skipping ID {record_id}")
                    continue

                xml_string = xml_path.read_text(encoding="utf-8")
                xml_string_no_newlines = xml_string.replace("\n", "").replace("\r", "")

                print(record_id)
                #print(target_url)
                #print(xml_string_no_newlines)
                record_metadata = {
                    '_profile': 'datacite',
                    '_target': target_url,
                    'datacite': xml_string_no_newlines
                }
                record_metadata = self._toAnvl(record_metadata).encode("UTF-8")
                ret = self.create_record(record_id, record_metadata)
                print(ret)

def main():

    parser = argparse.ArgumentParser(description='Create EZID records from XML files.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=True, help='user name')
    parser.add_argument('-p', '--password', type=str, required=True, help='password')
    parser.add_argument('-b', '--base_path', type=str, required=True, help='base path for data and config files')
    parser.add_argument('-c', '--config_file', type=str, required=True, help='config file')
 
    args = parser.parse_args()

    env = args.env
    user = args.user
    password = args.password
    base_path = args.base_path
    config_file = args.config_file
  
    base_urls = {
        "test": "http://127.0.0.1:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    record_creator = EZIDRecordCreator(base_url, user, password, base_path, config_file)
    record_creator.create_record_from_xml()


if __name__ == "__main__":
    main()