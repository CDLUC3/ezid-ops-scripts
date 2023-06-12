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

def dump_nog_file(db_path, output_file):

    db = bsddb3.btopen(db_path, 'r')
    items = db.items()

    data = {}
    for key, value in items:
        data[key.decode()] = value.decode()
    
    with open(output_file, 'w') as writer:
        json.dump(data, writer)

    db.close()

def create_output_filename(file_path):
    """Create output filename based on file path.
    
       Find the "shoulder_and_id" part from the file_path, for example /apps/ezid/var/minters/minters/f9999/c5/nog.bdb.
       The "shoulder_and_id" is "/f9999/c5/" in this case.
       Replace "/" with "_" in the matched string.
       Return matched string as filename, "_f9999_c5" in this case.

    """
    filename = None
    start_substring = "minters"
    end_substring = "nog.bdb"
    pattern = r"%s(.*?)%s" % (re.escape(start_substring), re.escape(end_substring))
    match = re.search(pattern, file_path)
    if match:
        filename = match.group(1)
        filename = filename.replace("/", "_")
        filename = f"{filename}nogdb.out"
    
    return filename 


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} minters_path")
        exit()

    minters_path = sys.argv[1]
    file_pattern = 'nog.bdb' 
    ct_1 = datetime.datetime.now()
    print(f"start BDB dumping: {ct_1}")
    print(f"for Minters path: {minters_path}")

    ct = ct_1.strftime('%Y%m%d_%H%M%S')
    output_dir = f"./nog_db_output/{ct}"
    print(f"save ouput files in: {output_dir}")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    else:
        os.makedirs(output_dir)

    nog_files = find_files(minters_path, file_pattern)
    print(f"number of nog files to dump: {len(nog_files)}")
    for nog_db_file in nog_files:
        print(f"dump db file: {nog_db_file}")
        output_filename = create_output_filename(nog_db_file)
        if output_filename:
            output_filename =  f"{output_dir}/{output_filename}"
            print(f"output filename: {output_filename}")
            dump_nog_file(nog_db_file, output_filename)
        else:
            print(f"error: failed to create output filename based on nog db path {nog_db_file}")
    
    ct_2 = datetime.datetime.now()
    print(f"finished BDB dumping: {ct_2}")
    print(f"time taken: {ct_2 - ct_1}")

if __name__ == "__main__":
    main()

