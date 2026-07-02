# Load test for EZID, N2T and ARKs using Locust

We use LOCUST [An open source load testing tool](https://locust.io/), [repo](https://github.com/locustio/locust) to perform load test for EZID, N2T and ARKs.

Testing scripts or locust files and data files are saved in the `locust_files` directory.

To run the load tests:

1. Create Python virtual environment using `venv`
```
python -m venv .venv
```
Activate the virtual environment
```
source .venv/bin/activate
```

2. Install `locust`
```
pip install locust
```

3. Create the load test scripts in the `locust_files` directory.

4. Run the load test in the `locust_files` directory
```
cd locust_files

locust -f locustfile.py
```


