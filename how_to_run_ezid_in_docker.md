# How to run EZID tests in Docker
Here are the major components of the Docker version EZID test suite:

**Test scripts**
Test scripts are located in the `ezid-ops-scripts.git/scripts` directory.
* ezid_ui_tests_docker.py - test EZID UI
* verify_ezid_status.py - Verify EZID status including testing API endpoints

**The Dockerfile**
The `Dockerfile` is located in the `ezid-ops-scripts.git/scripts` directory.
It provides instructions on how to build a Docker image.

**The docker-compose file**
The `docker-compose.yml` file is located in the root directory of the `EZID-OPS-SCRIPTS` repo.
It defines and manages multiple Docker containers (services) in one file.

**The .env file***
The `.env` file is located in the root directory of the `EZID-OPS-SCRIPTS` repo.
It stores environment variables, which can be used in both docker-compose.yml and Dockerfiles.

**Services defined in the `docker-compose.yml` file**
* selenium - a standalone-chromium
* test-runner-ui - a sesrvice runs the `ezid_ui_tests_docker.py` script
* test-runner-ezid-status- a service runs the `verify_ezid_status.py` script

## Docker compose commands

Remove existing container by name:
```
docker rm -f selenium
```

Stop and remove all containers in the docker-compose file
```
docker compose down
```

Build docker images using the docker-compose file 
```
docker compose build
```

Build docker images using the docker-compose file and then start the containers
```
docker compose up --build
```
* The selenium container starts up and waits on port 4444.
* The test-runner-ui container installs selenium, runs `ezid_ui_tests_docker.py`
* The test-runner-ezid-status container runs `verify_ezid_status.py`

Pass an environment variable to the docker compose command
```
APITEST_PASSWORD=xxx docker compose up --build
```

Rerunning just the test-runner-ui , remove the container once the command finishes executing
```
docker compose run --rm test-runner-ui
```

Re-run everything (fresh)
```
docker compose up --force-recreate
```

## Test without using docker-compose file

Start docker standalone Chrome container
```
docker run -d -p 4444:4444 --name selenium seleniarm/standalone-chromium:latest
```

Run the test script
```
python ezid_ui_tests_docker.py -e stg -u apitest -p apitest_password -n ezid_test_email@ucop.edu
```


## Precedence Order for environment variables in Docker Compose

When using Docker Compose, environment variables can be set in various ways. The precedence order for these variables is as follows:
| Priority	| Source	| Example |
| --------- | --------- | ------- | 
|1 | Inline in docker compose call	| MY_SECRET_TOKEN=inline docker compose up |
|2 | Shell or GitHub Actions env: block	| `env: MY_SECRET_TOKEN: ${{ secrets.MY_SECRET_TOKEN }}` |
|3 | .env file | .env → MY_SECRET_TOKEN=dotenv_value |
|4 | Hardcoded in docker-compose.yml	| MY_SECRET_TOKEN: fallback_value |

## Run EZID tests using GitHub action
A GitHub action `Run EZID UI and functional tests in Docker` is defined in the `.github/workflow/ezid-tests.yml` file. The action is triggered by content changes to the `.env` file. It runs the `docker compose up --build` command to build the images, start the containers and then run the tests defined in the test scripts.

Sample `.github/workflow/ezid-tests.yml`:
```
nname: Run EZID UI and functional tests in Docker

on:
  workflow_dispatch:
  push:
    paths:
      - '.env'


jobs:
  ezid-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Run EZID Tests
        env:
          APITEST_PASSWORD: ${{ secrets.APITEST_PASSWORD }}
        run: docker compose up --build --abort-on-container-exit

      - name: Stop and remove containers
        if: always() 
        run: docker compose down --volumes --remove-orphans
```

We ran into problems with the `--abort-on-container-exit` option which stops all containers when one of them exits. Since we have two test containers, one for UI and one for functional tests, using the `--abort-on-container-exit` option will always result in an imcomplete test suite. However, without the `--abort-on-container-exit` option, the selenium container will be up and running until the job time out.

A wrapper Shell script `run_ezid_test.sh` was developed to resolve this issue. The script combines both the UI and funcitonal tests so we can use a single container for all types of tests.

## How to run `run_ezid_test.sh`
The `run_ezid_test.sh` script takes 5 or 6 positional parameters:

Usage: ./run_ezid_tests.sh <environment> <username> <password> <email> <version> <debug_flag>

The paramters are all required except the last one `debug_flag` which is optional.

1. To run the script with the debug option, for example:
```
./run_ezid_tests.sh stg apitest apitest_password ezid@ucop.edu v3.3.15 debug
```
The debug option will instruct the script to start a standalone Selenium Chrome container for you.

2. To run the script without the debug option:

First, manually start a standalone Selenium Chrome container:
```
docker run -d -p 4444:4444 --name selenium seleniarm/standalone-chromium:latest
```
Then run the tests:
```
./run_ezid_tests.sh stg apitest apitest_password ezid@ucop.edu v3.3.15
```
Last, remove the `selenium` container:
```
docker rm -f selenium
```

3. To run the script using docker compose command
The `docker-compose.yml` file is defined with the following command:
```
command: ["./run_ezid_tests.sh", "${ENV}", "apitest", "${APITEST_PASSWORD}", "${NOTIFICATION_EMAIL}", "${EZID_VER}"]
```

The following environment variables are defined in the `.env` file:
- ENV
- NOTIFICATION_EMAIL
- EZID_VER

Pass the API password in command line:
```
APITEST_PASSWORD=xxx docker compose up --build
```
