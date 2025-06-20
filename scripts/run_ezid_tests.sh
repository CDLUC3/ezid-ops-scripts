#!/bin/bash
# script name: run_ezid_tests.sh
# This script runs the EZID test suite, including functional and UI tests.
# Usage: ./run_ezid_tests.sh <environment> <username> <password> <email> <debug_flag>
#  <environment>: required, the environment to test; should be dev, stg, or prd
#  <username>: required, an username of EZID
#  <password>: required, the password for the EZID user
#  <email>: required, the email address used to recieve notifications
#  <debug_flag>: optional, if set to "debug", the script will start the standalone Chrome container "selenium"
#  Example: ./run_ezid_tests.sh dev apitest apitest_password ezid@ucop.edu debug

set -e  # Exit on first failure

if [ $# -ne 4 ] && [ $# -ne 5 ]; then
  echo "Error: You must provide either 4 or 5 arguments."
  echo "Usage: $0 <environment dev|stg|prd> <username> <password> <email> <optional_debug_flag>"
  exit 1
fi

ENV=$1
USER=$2
PASSWORD=$3
EMAIL=$4

if [[ "$ENV" != "dev" && "$ENV" != "stg" && "$ENV" != "prd" ]]; then
  echo "Error: Environment must be one of 'dev', 'stg', or 'prd'."
  exit 1
fi

echo "Starting the EZID test suite..."

echo "Running functional tests..."
python verify_ezid_status.py -e $ENV -u $USER -p $PASSWORD -n $EMAIL

# Start standalone Chrome container
if [ "$5" == "debug" ]; then
  echo "Removing Selenium container in case it is up and running"
  docker rm -f selenium
  echo "Starting Selenium standalone Chrome container..."
  docker run -d -p 4444:4444 --name selenium seleniarm/standalone-chromium:latest
  echo "Waiting for Selenium to be ready..."
  until curl -sf http://localhost:4444/wd/hub/status | grep -q '"ready": true'; do
    sleep 2
    echo "Waiting..."
  done
else
  echo "Selenium container should have been started. Otherwise, UI tests will fail."
fi

echo "Running UI tests..."
python ezid_ui_tests_docker.py -e $ENV -u $USER -p $PASSWORD -n $EMAIL

echo "EZID tests completed successfully!"