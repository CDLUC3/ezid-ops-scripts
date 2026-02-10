import os
import time
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import Select


class EzidUiTest:
    def __init__(self, base_url, user, password, email):
        self.base_url = base_url
        self.user = user
        self.password = password
        self.email = email

    def ui_test_page_load(self, driver):
        print("## Testing page load...")
        try:
            # Open a webpage
            driver.get(self.base_url)
            assert "EZID Home" in driver.title, "Page title does not contain 'EZID'"
            print("  ok - Load page - PASSED")
        except Exception as e:
            print(f"ERROR: An error occurred while loading the page: {e}")


    def ui_test_login_logout(self, driver):
        print("## Testing login/logout ... ")
        driver.get(self.base_url)

        # Find and click the login button
        login_button = driver.find_element(By.ID, "js-header__loginout-button")
        login_button.click()

        # Find the username and password input fields
        username_input = driver.find_element(By.ID, "username")
        password_input = driver.find_element(By.ID, "password")

        # Enter username and password
        username_input.send_keys(self.user)
        password_input.send_keys("")
        time.sleep(1)
        
        # submit login
        login_button = driver.find_element(By.ID, "login")
        login_button.click()
        time.sleep(1)

        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
        assert "Password required" in alert_text.text
        print("  ok - Password is required for login - PASSED")
        time.sleep(1)

        password_input = driver.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
        password_input.clear()
        password_input.send_keys("xxxx")
        time.sleep(1)
        
        # submit login
        login_button = driver.find_element("xpath", "//button[@class='button__primary general__form-submit']")
        login_button.click()
        
        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
        assert "Login failed" in alert_text.text
        print("  ok - Login failed due to wrong password - PASSED")
        time.sleep(2)

        password_input = driver.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
        password_input.clear()
        password_input.send_keys(self.password)
        time.sleep(2)

        login_button = driver.find_element("xpath", "//button[@class='button__primary general__form-submit']")
        login_button.click()

        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))

        assert "Login successful" in alert_text.text
        assert f"Welcome {self.user}" in driver.page_source
        print("  ok - Login successful - PASSED")
        time.sleep(2)

        logout_button = driver.find_element("xpath", "//button[@class='header__loginout-link']")
        logout_button.click()

        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
        assert "You have been logged out" in alert_text.text
        print("  ok - Logout successful - PASSED")
        
        time.sleep(3)
        print("  ok - Testing login/logout - PASSED")
        
    def ui_test_creator_ark(self, driver):
        print("## Testing create ARK ...")
        # Open a webpage
        driver.get(self.base_url)

        target_input = driver.find_element(By.ID, "target")
        target_input.send_keys("https://google.com")
        who_input = driver.find_element(By.ID, "erc.who")
        who_input.send_keys("test ark who")
        what_input = driver.find_element(By.ID, "erc.what")
        what_input.send_keys("test ark what")
        when_input = driver.find_element(By.ID, "erc.when")
        when_input.send_keys("2024")
        
        time.sleep(2)
        create_button = driver.find_element(By.XPATH, "//button[@class='home__button-primary']")
        create_button.click()

        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
        
        assert "Identifier Created" in alert_text.text
        assert "Identifier Details" in driver.page_source
        assert "ark:/99999/fk4" in driver.page_source

        time.sleep(2)
        print("  ok - Testing create ARK - PASSED")

    def ui_test_creator_doi(self, driver):
        print("## Testing create DOI ...")
        driver.get(self.base_url)

        radio_button = driver.find_element(By.XPATH, "//input[@type='radio' and @id='doi:10.5072/FK2']")
        assert radio_button.get_attribute('type') == 'radio'
        assert radio_button.get_attribute('id') == 'doi:10.5072/FK2'

        driver.execute_script("document.getElementById('doi:10.5072/FK2').click();")
        wait = WebDriverWait(driver, 10)
        creator = wait.until(EC.visibility_of_element_located((By.ID, "datacite.creator")))
    
        target_input = driver.find_element(By.ID, "target")
        target_input.send_keys("https://google.com")
        creator =driver.find_element(By.ID, "datacite.creator")
        creator.send_keys("test creator")
        title = driver.find_element(By.ID, "datacite.title")
        title.send_keys("test title")
        publisher = driver.find_element(By.ID, "datacite.publisher")
        publisher.send_keys("test publisher")
        pub_year = driver.find_element(By.ID, "datacite.publicationyear")
        pub_year.send_keys("2024")
        resource_type = driver.find_element(By.ID, "datacite.resourcetype")
        resource_type.send_keys("Book")
        
        time.sleep(2)

        create_button = driver.find_element(By.XPATH, "//button[@class='home__button-primary']")
        create_button.click()

        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
        
        assert "Identifier Created" in alert_text.text
        assert "Identifier Details" in driver.page_source
        assert "doi:10.5072/FK2" in driver.page_source

        time.sleep(2)
        print("  ok - Testing create DOI - PASSED")

    def ui_test_contact(self, driver, env):
        print("## Testing the contact EZID form ...")
        driver.get(self.base_url)

        time.sleep(1)

        contact_link = driver.find_element(By.XPATH, "//a[@class='header__nav-item-contact' and contains(text(), 'Contact') ]")
        contact_link.click()

        time.sleep(1)

        assert "contact" in driver.current_url
        assert "Fill out this form and EZID will get in touch with you" in driver.page_source

        time.sleep(1)

        resaon_select = driver.find_element(By.ID, "id_contact_reason")
        
        select = Select(resaon_select)
        selected_value = "Other"
        select.select_by_value(selected_value)

        selected_option = select.first_selected_option
        assert selected_option.text == selected_value
        
        your_name = driver.find_element(By.ID, "id_your_name")
        your_name.send_keys("test name")
        your_email = driver.find_element(By.ID, "id_email")
        your_email.send_keys(self.email)
        your_name = driver.find_element(By.ID, "id_your_name")
        your_name.send_keys("test name")
        your_inst = driver.find_element(By.ID, "id_affiliation")
        your_inst.send_keys("CDL")
        comment = driver.find_element(By.ID, "id_comment")
        comment.send_keys("Test contact EZID form")
        dropdown_lists = driver.find_element(By.ID, "id_question")
        dropdown_lists.send_keys("2")

        submit_button = driver.find_element(By.XPATH, "//button[@class='button__primary general__form-submit']")
        driver.execute_script("arguments[0].scrollIntoView();", submit_button)

        # use wait until didn't work - got error "Element is not clickable at point (367, 863)"
        # however using time.sleep() worked
        # so, need to figure out what is preventing the submit button become clickable
        #   wait = WebDriverWait(browser, 10)
        #   submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='button__primary general__form-submit']")))
            
        time.sleep(1)
        submit_button.click()

        time.sleep(2)
        if env == "test":
            assert "There was a problem sending your email" in driver.page_source
        else:
            assert "Thank you for your message. We will respond as soon as possible." in driver.page_source

        time.sleep(2)
        print("  ok - Testing the contact EZID form - PASSED")

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


def main():
    parser = argparse.ArgumentParser(description='Get EZID records by identifier.')

    # add input and output filename arguments to the parser
    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--user', type=str, required=True, help='user name')
    parser.add_argument('-p', '--password', type=str, required=True, help='password')
    parser.add_argument('-n', '--user_email', type=str, required=True, help='Email address for testing the Contact Us form.')
 
    args = parser.parse_args()
    env = args.env
    user = args.user
    password = args.password
    email = args.user_email
  
    base_urls = {
        "test": "http://host.docker.internal:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    ui_test = EzidUiTest(base_url, user, password, email)

    try:
        selenium_url = os.environ["SELENIUM_REMOTE_URL"]
    except KeyError:
        selenium_url = "http://localhost:4444/wd/hub"
    print("Selenium URL:", selenium_url)

    try:
        print("Initializing WebDriver...")
        driver = create_driver(selenium_url, options)
        print("WebDriver initialized successfully")

        print("Running UI tests...")
        ui_test.ui_test_page_load(driver)
        ui_test.ui_test_login_logout(driver)
        ui_test.ui_test_creator_ark(driver)
        ui_test.ui_test_creator_doi(driver)
        ui_test.ui_test_contact(driver, env)
        print("UI completed")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        driver.quit()
        return
    finally:
        driver.quit()




if __name__ == '__main__':
    main()
