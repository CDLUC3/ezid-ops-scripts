import csv
import requests
import argparse

def delete_identifier(identifier, api_base_url, username, password):
    url = f"{api_base_url}/{identifier}"

    try:
        response = requests.delete(
            url,
            auth=(username, password)
        )

        if response.status_code in (200, 204):
            print(f"Deleted: {identifier}")
        else:
            print(f"Failed: {identifier} | Status: {response.status_code} | {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error deleting {identifier}: {e}")


def process_csv(file_path, api_base_url, username, password, id_col):
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            identifier = row[id_col]
            delete_identifier(identifier, api_base_url, username, password)


def main():
    parser = argparse.ArgumentParser(description="Delete identifiers via API")

    parser.add_argument("--env", required=True, help="environment (e.g., dev, stg, prd)")
    parser.add_argument("--username", required=True, help="API username")
    parser.add_argument("--password", required=True, help="API password")
    parser.add_argument("--csv", required=True, help="CSV file containing identifiers")
    parser.add_argument("--id_col", required=True, help="Name of the column containing identifiers")

    args = parser.parse_args()

    if args.env == "dev":
        api_base_url = "https://ezid-dev.cdlib.org/id/"
    elif args.env == "stg":
        api_base_url = "https://ezid-stg.cdlib.org/id/"
    elif args.env == "prd":
        api_base_url = "https://ezid.cdlib.org/id/"
    else:
        raise ValueError("Invalid environment. Use 'dev', 'stg', or 'prd'.")

    process_csv(args.csv, api_base_url, args.username, args.password, args.id_col)


if __name__ == "__main__":
    main()