import os
import sys

import fnmatch
import bsddb3
import re
import datetime
import shutil
import json

def find_files(root, pattern):
    matches = []
    for path, dirnames, filenames in os.walk(root):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(path, filename))
    return matches

def dump_nog_file(db_path, output_dir):

    db = bsddb3.btopen(db_path, 'r')
    items = db.items()

    data = {}
    for key, value in items:
        data[key.decode()] = value.decode()
    
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    else:
        os.makedirs(output_dir)

    with open(os.path.join(output_dir, "nog_bdb.json"), 'w') as writer:
        json.dump(data, writer)

    db.close()

def find_minter_path(file_path):
    """Find minter path based on the dbd file path.
    
       For example when the file path  /apps/ezid/var/minters/minters/f9999/c5/nog.bdb, 
       the minter path is "/f9999/c5/".
    """
    minterpath = None
    start_substring = "minters"
    end_substring = "nog.bdb"
    pattern = r"%s(.*?)%s" % (re.escape(start_substring), re.escape(end_substring))
    match = re.search(pattern, file_path)
    if match:
        minterpath = match.group(1)
    
    return minterpath


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} minters_path output_dir_name")
        exit()

    minters_path = sys.argv[1]
    output_dir = sys.argv[2]
    file_pattern = 'nog.bdb' 
    ct_1 = datetime.datetime.now()
    print(f"start BDB dumping: {ct_1}")
    print(f"for Minters path: {minters_path}")

    ct = ct_1.strftime('%Y%m%d_%H%M%S')
    output_dir = f"{output_dir}/{ct}"
    print(f"save ouput files in: {output_dir}")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    else:
        os.makedirs(output_dir)

    nog_files = find_files(minters_path, file_pattern)
    print(f"number of nog files to dump: {len(nog_files)}")
    for nog_db_file in nog_files:
        print(f"dump db file: {nog_db_file}")
        minter_path = find_minter_path(nog_db_file)
        if minter_path:
            output_file_dir = f"{output_dir}{minter_path}"
            print(f"output file dir: {output_file_dir}")
            dump_nog_file(nog_db_file, output_file_dir)
        else:
            print(f"error: failed to create output filename based on nog db path {nog_db_file}")
    
    ct_2 = datetime.datetime.now()
    print(f"finished BDB dumping: {ct_2}")
    print(f"time taken: {ct_2 - ct_1}")

if __name__ == "__main__":
    main()

