#!/bin/bash
# script name: run_ezid_tests.sh
# This script runs the EZID test suite, including functional and UI tests.
# Usage: ./run_ezid_tests.sh <environment> <username> <password> <email> <version> <debug_flag>
#  <environment>: required, the environment to test; should be test, dev, stg, or prd
#  <username>: required, an username of EZID
#  <password>: required, the password for the EZID user
#  <email>: required, the email address used to receive notifications
#  <version>: required, the EZID version to test
#  <debug_flag>: optional, if set to "debug", the script will start the standalone Chrome container "selenium"
#  Example: ./run_ezid_tests.sh dev apitest apitest_password ezid@ucop.edu v3.3.15 debug

set -e  # Exit on first failure

if [ $# -ne 5 ] && [ $# -ne 6 ]; then
  echo "Error: You must provide either 5 or 6 arguments."
  echo "Usage: $0 <environment test|dev|stg|prd> <username> <password> <email> <version> <optional_debug_flag>"
  exit 1
fi

ENV=$1
USER=$2
PASSWORD=$3
EMAIL=$4
VERSION=$5
DEBUG=$6

if [[ "$ENV" != "test" && "$ENV" != "dev" && "$ENV" != "stg" && "$ENV" != "prd" ]]; then
  echo "Error: Environment must be one of 'test', 'dev', 'stg', or 'prd'."
  exit 1
fi

echo "Starting the EZID test suite..."

echo "Running functional tests..."
if [[ "$ENV" == "stg" || "$ENV" == "prd" ]]; then
  python verify_ezid_status.py -e $ENV -u $USER -p $PASSWORD -n $EMAIL -v $VERSION
else
  python verify_ezid_status.py -e $ENV -u $USER -p $PASSWORD -n $EMAIL -v $VERSION -s
fi


# Start standalone Chrome container
if [ "$DEBUG" == "debug" ]; then
  if docker ps -a --format '{{.Names}}' | grep -Eq '^selenium$'; then
    echo "# Debug: Removing existing 'selenium' container..."
    docker rm -f selenium
  fi
  echo "# Debug: Starting Selenium standalone Chrome container..."
  docker run -d -p 4444:4444 --name selenium seleniarm/standalone-chromium:latest
  echo "# Debug: Waiting for Selenium to be ready..."
  until curl -sf http://localhost:4444/wd/hub/status | grep -q '"ready": true'; do
    sleep 2
    echo "# Debug: Waiting..."
  done
else
  echo "Selenium container should have been started. Otherwise, UI tests will fail."
fi

echo "Running UI tests..."
python ezid_ui_tests_docker.py -e $ENV -u $USER -p $PASSWORD -n $EMAIL

if [ "$DEBUG" == "debug" ]; then
  echo "# Debug: Removing 'selenium' container..."
  docker rm -f selenium
fi

echo "EZID tests completed successfully!"