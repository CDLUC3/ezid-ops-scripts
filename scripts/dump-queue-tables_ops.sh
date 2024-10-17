#!/usr/bin/env bash

# Copyright©2024, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#
# Script: dump-queue-tables_ops.sh
# Description: Dump EZID queue tables to files.
# Parameters: 
# param 1 (required): environment or RDS hostname
#   Sample values: dev, stg, prd, 
#   or rds-uc3-ezid1-dev.cmcguhglinoa.us-west-2.rds.amazonaws.com
# param 2 (required): password for the dba account
#   When password contains special characters, escape them or use quotes appropriately.
#   Sample values: "password contain spaces"
#   

if [ $# -lt 2 ]; then
    echo "Error: This script requires exactly two parameters."
    echo "Usage: $0 <env_or_host> <dba_password>"
    exit 1
fi

env="$1"
pw="$2"

if [[ "$env" == "dev" ]]; then
  host='rds-uc3-ezid1-dev.cmcguhglinoa.us-west-2.rds.amazonaws.com'
elif [[ "$env" == "stg" ]]; then
  host='rds-ias-ezid-search3-stg.cmcguhglinoa.us-west-2.rds.amazonaws.com'
elif [[ "$env" == "prd" ]]; then
  host='rds-uc3-ezid5-prd.cmcguhglinoa.us-west-2.rds.amazonaws.com'
else
  host=$env
fi

user='eziddba'
db='ezid'

timestamp=$(date +"%Y%m%d_%H%M%S")
dump_file_dir="$HOME/tmp/ezid_sql_dump_files"

if [ ! -d "$dump_file_dir" ]; then
  mkdir -p "$dump_file_dir"
fi

table_arr=(
  'ezidapp_binderqueue'
  'ezidapp_crossrefqueue'
  'ezidapp_datacitequeue'
  'ezidapp_searchindexerqueue'
)

dump() {
  for table in "${table_arr[@]}"; do
    file="$dump_file_dir/${table}_table_dump_${timestamp}.sql"
    printf "Dumping queue table ${table} to file: ${file}\n"
    cat /dev/null >"$file"
    mysqldump > "$file" "$db" "$table" --user="$user" --password="$pw" --host="$host" --no-tablespaces --set-gtid-purged=OFF
  done
}

dump

