# Load test setup for EZID

Uses https://github.com/locustio/locust.

The `getid/locust.py` script gathers identifiers from MySQL and hits the
resolve endpoint as a simple load test for resolve.

Uses environment variables like:

```
$ cat test.env
EZID_DB_PORT="database port"
EZID_DB_USER="database user"
EZID_DB_PASS="database password"
EZID_DB="database name"
```
e.g. in a shell, open a tunnel to dev mysql like:
```
ssh -L3306:dev-database-server-host-name:3306 ezid-dev-server
```

Then run this script like:
```
poetry run locust -f getid/locustfile.py
```

And set the URL to the resolve endpoint.

This same pattern can be used for other get ops that use identifiers.
