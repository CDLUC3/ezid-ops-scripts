# Batch delete EZID identifiers
Script name: batch_delete.py

Description: A Python script to batch delete identifiers via EZID API.
* Authentication is required to run this script.
* The super user (admin) can delete any identifiers without restrictions.
* Regular users can only delete their own identifiers with a status of "reserved". See [EZID API Guide](https://ezid.cdlib.org/doc/apidoc.html#operation-delete-identifier) for details on DELETE API and identifier status.

Usage
```
usage: batch_delete.py [-h] --env ENV --username USERNAME --password PASSWORD --csv CSV --id_col ID_COL
```

Sample command:
```
python batch_delete.py --env dev --username admin --password admin_password --csv test_del.csv --id_col _id
```
