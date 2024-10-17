#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#

# Script: restore-database-tables_ops.sh
# Description: restore database tables from mysqldump created files.
# Parameters: 
# param 1 (required): environment or RDS hostname
#   Sample values: dev, stg, prd, 
#   or rds-uc3-ezid1-dev.cmcguhglinoa.us-west-2.rds.amazonaws.com
# param 2 (required): password for the dba account
#   When password contains special characters, escape them or use quotes appropriately.
#   Sample values: "password contain spaces"
# param 3 (required): full path to the mysqldump file 

if [ $# -lt 3 ]; then
    echo "Error: This script requires exactly three parameters."
    echo "Usage: $0 <env_or_host> <dba_password> dump_file"
    exit 1
fi

env="$1"
pw="$2"
file="$3"

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

load() {
  printf 'Loading database tables from file: %s\n' "$file"
  mysql < "$file" "$db" --user="$user" --password="$pw" --host="$host"
}

load
