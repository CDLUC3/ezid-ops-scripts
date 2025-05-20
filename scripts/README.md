# Running scripts in this directory

## Prerequisites

- You need a version of Python installed, currently the latest version of 3.11 works fine
  and is the same version that the EZID app uses.  The version installed on the servers
  is probably fine for using the verify_ezid_status.py script but perhaps not some other scripts.
- If you need a version locally, you can use [pyenv](https://github.com/pyenv/pyenv) and
  install by using the instructions at the pyenv link or `brew install pyenv`.


```bash
# install the version of python you desire
pyenv install 3.11.10

# set the version of python to use
pyenv local 3.11.10

# create a virtual environment
python -m venv venv

# activate the virtual environment
source venv/bin/activate

# install the requirements
pip install -r requirements.txt
```

if coming back later, activate your python version and virtual environment
```bash
pyenv local 3.11.10
source venv/bin/activate
```

## Running the verify_ezid_status.py script

Use a line like the following (substituting your own values) to run the script and test the api.

```bash
# Run the test normally with download check and email to user, environments are test/dev/stg/prod
python verify_ezid_status.py -e <env> -u <user> -p <password> -n <email>

# in some environments dev/test it may be convenient to skip the download check because the daemon is not running
# the -s or --skip_download_check flag will skip the download check
python verify_ezid_status.py -e <env> -u <user> -p <password> -s
```

All tests should pass with an `ok` message if the api is working.
