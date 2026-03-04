# Running scripts in this directory

## Prerequisites

- You need a version of Python installed, currently the latest version of 3.11 works fine
  and is the same version that the EZID app uses. 

- Create a Python virtual environment using python built-in `venv`

- Install required Python packages listed in the `requirements.txt` file

```bash
# create a virtual environment
python -m venv venv

# activate the virtual environment
source venv/bin/activate

# install the requirements
pip install -r requirements.txt
```

If coming back later, activate your python version and virtual environment
```bash
source venv/bin/activate
```

## Running the run_ezid_tests.sh script

The `run_ezid_tests.sh` script performs two sets of tests:
1. The EZID functional and API tests done by the `verify_ezid_status.py` script.
2. The EZID UI tests doen by the `ezid_ui_tests.py` script.

There are three ways to run this script:

1. Use a command line like the following (substituting your own values) to run the script and perform the tests.

```bash
# environments are test/dev/stg/prod
# set the docker_flag to "docker" to start a Selenium Chrome container for UI tests
./run_ezid_tests.sh <env> <user> <password> <email> <version> docker_flag
```

2. Perform the tests in Docker containers

The Docker containers and workflow are defined in the `docker-compose.yml` file. 
Environment variables are defined in the `.env` file.

```bash
APITEST_PASSWORD=xxx docker compose up --build
```

3. Another way to perform the combined tests is to update the `.env` file then push the change to GitHub.
This will trigger a GitHub action defined in the `.github/workflows/ezid-tests.yml` file.

A branch `testing_ezid_app` was created for this workflow. Maintain this branch on a regular base
* merge the `main` to this branch to keep it up-to-date
* update the `.env` file for a specific test

The `.env` file defines the following environment variables:
```
ENV=stg or prd
EZID_VER=ezid version to test
NOTIFICATION_EMAIL="notification email"
```

## Running the verify_ezid_status.py script

The `verify_ezid_status.py` can be used by itself to perform functional and API tests (substituting your own values).

```bash
# Run the test normally with download check and email to user, environments are test/dev/stg/prod
python verify_ezid_status.py -e <env> -u <user> -p <password> -n <email>

# in some environments dev/test it may be convenient to skip the download check because the daemon is not running
# the -s or --skip_download_check flag will skip the download check
python verify_ezid_status.py -e <env> -u <user> -p <password> -s
```

All tests should pass with an `ok` message if the api is working.

## Running the ezid_ui_tests.py script
The `ezid_ui_tests.py` script relies on a Selenium Chrome driver to work. There are two options to run this UI test script.

1. Test using your local installer Google Chrome with Graphical User Interface.
```bash
# the l, --local_browser option uses local Chrome browser for UI test
python ezid_ui_tests.py -e <env> -u <user> -p <password> -n <email> -l
```

2. Test using a standalone Selenium Chrome server running in a Docker container. You need to manually start the Chrome server in this case. Otherwise tests will fail.

```bash
# start a standalone Selenium Chrome server with url: http://localhost:4444/wd/hub
docker run -d -p 4444:4444 --name selenium selenium/standalone-chromium:latest

# perform the test
python ezid_ui_tests.py -e <env> -u <user> -p <password> -n <email>

# if Selenium is running on a different URL, provide the url with command option -s/--selenium_url
# or define it in the environment variable SELENIUM_REMOTE_URL
python ezid_ui_tests.py -e <env> -u <user> -p <password> -n <email> -s <selenium_url>
```
