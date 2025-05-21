import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

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

options = Options()
options.add_argument("--headless")  # This is preferred over options.headless = True
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

print("Initializing WebDriver...")
try:
    selenium_url = os.environ["SELENIUM_REMOTE_URL"]
except KeyError:
    selenium_url = "http://localhost:4444/wd/hub"
print("Selenium URL:", selenium_url)

#driver = create_driver(selenium_url, options)
driver = webdriver.Remote(command_executor=selenium_url,options=options)
print("Driver initialized")

try:
    # Open a webpage
    driver.get("https://ezid.cdlib.org")

    print("Page loaded")

    # Example: Print the page title
    print("Page title is:", driver.title)

finally:
    # Close the browser
    driver.quit()

