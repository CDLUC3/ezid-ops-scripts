import os
import time
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

class EzidUiTest:
    def __init__(self, base_url, user, password):
        self.base_url = base_url
        self.user = user
        self.password = password

def create_driver(selenium_url, options):
    retries = 5
    for attempt in range(retries):
        try:
            return webdriver.Remote(
                command_executor=selenium_url,
                options=options
            )
        except WebDriverException as e:
            print(f"Retry {attempt+1}/{retries} failed: {e}")
            time.sleep(5)
    raise RuntimeError("Failed to connect to Selenium server.")


def test_page_load(driver, base_url):
    print("Testing page load...")
    try:
        # Open a webpage
        driver.get(base_url)

        # Example: Print the page title
        print("Page title is:", driver.title)
    except Exception as e:
        print(f"An error occurred while loading the page: {e}")


def main():
    parser = argparse.ArgumentParser(description='Get EZID records by identifier.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=True, help='user name')
    parser.add_argument('-p', '--password', type=str, required=True, help='password')
    parser.add_argument('-m', '--user_email', type=str, required=True, help='Email address for testing the Contact Us form.')
    parser.add_argument('-l', '--headless', action='store_true', required=False, help='Enable headless mode.')
 
    args = parser.parse_args()
    env = args.env
    user = args.user
    password = args.password
    email = args.user_email
    headless = args.headless
  
    base_urls = {
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    options = Options()

    if headless == True:
        print("Running UI tests in headless mode")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")


    ui_test = EzidUiTest(base_url, user, password)

    try:
        selenium_url = os.environ["SELENIUM_REMOTE_URL"]
    except KeyError:
        selenium_url = "http://localhost:4444/wd/hub"
    print("Selenium URL:", selenium_url)

    try:
        print("Initializing WebDriver...")
        driver = create_driver(selenium_url, options)
        print("WebDriver initialized successfully")
        test_page_load(driver, base_url)
    except Exception as e:
        print(f"An error occurred: {e}")
        driver.quit()
        return
    finally:
        driver.quit()




if __name__ == '__main__':
    main()
