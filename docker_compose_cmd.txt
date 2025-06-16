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


