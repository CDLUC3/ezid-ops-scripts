import os
import random
import time
import locust
import pymysql


def get_mysql_connection():
    dbconn = pymysql.connect(
        host="127.0.0.1",
        port=int(os.environ["EZID_DB_PORT"]),
        user=os.environ["EZID_DB_USER"],
        password=os.environ["EZID_DB_PASS"],
        database=os.environ["EZID_DB"],
        cursorclass=pymysql.cursors.DictCursor,
    )
    return dbconn


def load_identifiers(num_to_get=100):
    result = []
    dbconn = get_mysql_connection()
    with dbconn.cursor() as cursor:
        sql = (
            "SELECT identifier FROM ezidapp_identifier "
            "WHERE identifier like 'ark:%%' AND isTest=False AND status='P' "
            "ORDER BY createTime DESC limit %s;"
        )
        cursor.execute(sql, (num_to_get))
        for row in cursor.fetchall():
            result.append(row["identifier"])
    dbconn.close()
    return result


class EzidUser(locust.HttpUser):
    wait_time = locust.between(0.1, 0.5)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_identifiers = []
        self.current_id = 0
        self.client.allow_redirects = False


    @locust.task
    def get_id(self):
        num_ids = 1000
        t_interval = 0.01 #seconds
        num_reps = 100
        headers = {
            "No-Redirect":"true"
        }
        test_identifiers = load_identifiers(num_ids)
        for i in range(0,num_reps):
            current_id = random.randrange(0, num_ids)
            url = f"{test_identifiers[current_id]}"
            self.client.get(url, headers=headers)
            time.sleep(t_interval)

    def on_start(self):
        pass
