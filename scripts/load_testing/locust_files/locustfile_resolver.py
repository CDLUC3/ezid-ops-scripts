import logging
import random
import gevent
import locust
import csv

L = logging.getLogger("resolver_test")

def load_identifiers():
    # 1.8K identifiers imported from scripts/test-n2t-waf-rules/sample_data/ark_spt_sample.jsonl
    # including base identifiers that will be resolved to a target URL
    # and identifiers that will be resolved through suffix pass through
    csv_file = "data/identifiers_resolver.csv"
    # List to store identifiers
    identifiers = []

    # Read the CSV file
    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        # Verify the required column exists
        if "identifier" not in reader.fieldnames:
            raise ValueError("CSV file must contain a column named 'identifier'.")

        # Read identifiers into the list
        for row in reader:
            identifiers.append(row["identifier"])

    return identifiers

class EzidUser(locust.HttpUser):
    wait_time = locust.between(0.1, 0.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_identifiers = []

    def on_start(self):
        self.test_identifiers = load_identifiers()
        if not self.test_identifiers:
            raise RuntimeError("No test identifiers loaded")

    @locust.task
    def get_id(self):
        t_interval = 0.01 #seconds
        num_reps = 10
        headers = {
            #"No-Redirect":"true"
        }
        for _ in range(num_reps):
            url = random.choice(self.test_identifiers)
            res = self.client.get(url, headers=headers, allow_redirects=False)
            # L.info("%s %s %s", res.status_code, url, res.history)
            gevent.sleep(t_interval)


