import requests
import time
import argparse

# A simple script to test if a WAF is blocking requests, though you could do something similar with curl (see the docs for that)
# but this code may be useful. Also, does one request after another rather than all in parallel like the curl example.
def test_waf_blocking(domain, endpoint="/account/pwreset", num_requests=100, delay=1):
    url = f"https://{domain}{endpoint}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    for i in range(num_requests):
        try:
            response = requests.get(url, headers=headers)
            print(f"Request {i+1}: Status Code {response.status_code}")
            if response.status_code == 403:
                print("Blocked by WAF!")
                break  # Stop testing once blocked
        except requests.exceptions.RequestException as e:
            print(f"Error on request {i+1}: {e}")
            break

        time.sleep(delay)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WAF blocking by sending repeated requests.")
    parser.add_argument("domain", help="The domain to test, e.g., ezid-stg.cdlib.org")
    parser.add_argument("--num_requests", type=int, default=300, help="Number of requests to send (default: 300)")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between requests in seconds (default: 0.25)")

    args = parser.parse_args()
    test_waf_blocking(args.domain, num_requests=args.num_requests, delay=args.delay)