#!/bin/bash

if [ $# -ne 1 ]; then
    echo "Usage: $0 action[restart|start|stop]"
    exit
fi

case $1 in
    restart|start|stop)
        ACTION=$1 ;;
    *) 
      echo "Action "$1" is not recognized."
      exit
esac

HOSTNSME=`hostname`

echo "On host: $HOSTNAME"

if [[ "$HOSTNAME" == *"ezid"* && "$HOSTNAME" == *"dev"* ]]; then
    ENV="dev"
elif [[ "$HOSTNAME" == *"ezid"* && "$HOSTNAME" == *"stg"* ]]; then
    ENV="stg"
elif [[ "$HOSTNAME" == *"ezid"* && "$HOSTNAME" == *"prd"* ]]; then
    ENV="prd"
else
    echo "Hostname "$HOSTNAME" is not recognized."
    exit
fi

job_list=("ezid")

job_list_1=(
"ezid-proc-binder" 
"ezid-proc-crossref" 
"ezid-proc-datacite" 
"ezid-proc-download" 
"ezid-proc-expunge" 
"ezid-proc-newsfeed"
"ezid-proc-search-indexer"
"ezid-proc-stats")

job_list_2=(
"ezid-proc-link-checker" 
"ezid-proc-link-checker-update")

if [[ $ENV == "stg" ]]; then
    job_list=("${job_list[@]}" "${job_list_1[@]}")
elif [[ $ENV == "prd" ]]; then
    job_list=("${job_list[@]}" "${job_list_1[@]}" "${job_list_2[@]}") 
fi

for job in "${job_list[@]}"; do
    CMD="sudo cdlsysctl ${ACTION} ${job}"
    echo "${CMD}"
    `${CMD}`
done

