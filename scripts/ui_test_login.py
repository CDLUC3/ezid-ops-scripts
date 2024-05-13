# ui_test_login.py
import time
import argparse

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


def ui_test_login_logout(base_url, user, password):
    driver = webdriver.Chrome()
    driver.get(base_url)

    # Find and click the login button
    login_button = driver.find_element(By.ID, "js-header__loginout-button")
    login_button.click()

    # Find the username and password input fields
    username_input = driver.find_element(By.ID, "username")
    password_input = driver.find_element(By.ID, "password")

    # Enter username and password
    username_input.send_keys(user)
    password_input.send_keys("")
    
    # submit login
    login_button = driver.find_element(By.ID, "login")
    login_button.click()
    
    wait = WebDriverWait(driver, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    assert "Password required" in alert_text.text

    password_input = driver.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
    password_input.clear()
    password_input.send_keys("xxxx")
    
    # submit login
    login_button = driver.find_element("xpath", "//button[@class='button__primary general__form-submit']")
    login_button.click()
    
    wait = WebDriverWait(driver, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    assert "Login failed" in alert_text.text

    password_input = driver.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
    password_input.clear()
    password_input.send_keys(password)

    time.sleep(3)

    login_button = driver.find_element("xpath", "//button[@class='button__primary general__form-submit']")
    login_button.click()

    wait = WebDriverWait(driver, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))

    assert "Login successful" in alert_text.text
    assert "Welcome apitest" in driver.page_source

    time.sleep(10)

    driver.close()

def main():
    parser = argparse.ArgumentParser(description='Get EZID records by identifier.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=False, help='user name')
    parser.add_argument('-p', '--password', type=str, required=False, help='password')
 
    args = parser.parse_args()
    env = args.env
    user = args.user
    password = args.password

    if user is None:
        user = "apitest"
    if password is None:
        password = "apitest"
  
    base_urls = {
        "test": "http://127.0.0.1:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    ui_test_login_logout(base_url, user, password)

if __name__ == '__main__':
    main()

