# ezid_ui_tests.py
import time
import argparse

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select


def ui_test_login_logout(base_url, user, password):
    print("Testing login/logout ...")
    browser = webdriver.Chrome()
    browser.get(base_url)

    # Find and click the login button
    login_button = browser.find_element(By.ID, "js-header__loginout-button")
    login_button.click()

    # Find the username and password input fields
    username_input = browser.find_element(By.ID, "username")
    password_input = browser.find_element(By.ID, "password")

    # Enter username and password
    username_input.send_keys(user)
    password_input.send_keys("")
    time.sleep(2)
    
    # submit login
    login_button = browser.find_element(By.ID, "login")
    login_button.click()
    
    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    assert "Password required" in alert_text.text
    time.sleep(2)

    password_input = browser.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
    password_input.clear()
    password_input.send_keys("xxxx")
    time.sleep(2)
    
    # submit login
    login_button = browser.find_element("xpath", "//button[@class='button__primary general__form-submit']")
    login_button.click()
    
    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    assert "Login failed" in alert_text.text
    time.sleep(2)

    password_input = browser.find_element("xpath", "//input[@type='password' and @class='fcontrol__text-field-inline']")
    password_input.clear()
    password_input.send_keys(password)
    time.sleep(2)

    login_button = browser.find_element("xpath", "//button[@class='button__primary general__form-submit']")
    login_button.click()

    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))

    assert "Login successful" in alert_text.text
    assert "Welcome apitest" in browser.page_source
    time.sleep(2)

    logout_button = browser.find_element("xpath", "//button[@class='header__loginout-link']")
    logout_button.click()

    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    assert "You have been logged out" in alert_text.text
    
    time.sleep(3)
    browser.quit()

def ui_test_creator_ark(base_url):
    print("Testing create ARK ...")
    browser = webdriver.Chrome()
    browser.get(base_url)

    target_input = browser.find_element(By.ID, "target")
    target_input.send_keys("https://google.com")
    who_input = browser.find_element(By.ID, "erc.who")
    who_input.send_keys("test ark who")
    what_input = browser.find_element(By.ID, "erc.what")
    what_input.send_keys("test ark what")
    when_input = browser.find_element(By.ID, "erc.when")
    when_input.send_keys("2024")
    
    time.sleep(2)

    create_button = browser.find_element(By.XPATH, "//button[@class='home__button-primary']")
    create_button.click()

    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    
    assert "Identifier Created" in alert_text.text
    assert "Identifier Details" in browser.page_source
    assert "ark:/99999/fk4" in browser.page_source

    time.sleep(3)
    browser.quit()

def ui_test_creator_doi(base_url):
    print("Testing create DOI ...")
    browser = webdriver.Chrome()
    browser.get(base_url)

    radio_button = browser.find_element(By.XPATH, "//input[@type='radio' and @id='doi:10.5072/FK2']")
    assert radio_button.get_attribute('type') == 'radio'
    assert radio_button.get_attribute('id') == 'doi:10.5072/FK2'

    browser.execute_script("document.getElementById('doi:10.5072/FK2').click();")
    wait = WebDriverWait(browser, 10)
    creator = wait.until(EC.visibility_of_element_located((By.ID, "datacite.creator")))
 
    target_input = browser.find_element(By.ID, "target")
    target_input.send_keys("https://google.com")
    creator =browser.find_element(By.ID, "datacite.creator")
    creator.send_keys("test creator")
    title = browser.find_element(By.ID, "datacite.title")
    title.send_keys("test title")
    publisher = browser.find_element(By.ID, "datacite.publisher")
    publisher.send_keys("test publisher")
    pub_year = browser.find_element(By.ID, "datacite.publicationyear")
    pub_year.send_keys("2024")
    resource_type = browser.find_element(By.ID, "datacite.resourcetype")
    resource_type.send_keys("Book")
    
    time.sleep(2)

    create_button = browser.find_element(By.XPATH, "//button[@class='home__button-primary']")
    create_button.click()

    wait = WebDriverWait(browser, 10)
    alert_text = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "alert-text")))
    
    assert "Identifier Created" in alert_text.text
    assert "Identifier Details" in browser.page_source
    assert "doi:10.5072/FK2" in browser.page_source

    time.sleep(3)
    browser.quit()

def ui_test_contact(base_url):
    print("Testing the contact EZID form ...")
    browser = webdriver.Chrome()
    browser.get(base_url)

    time.sleep(1)

    contact_link = browser.find_element(By.XPATH, "//a[@class='header__nav-item-contact' and contains(text(), 'Contact') ]")
    contact_link.click()

    assert "contact" in browser.current_url
    assert "Fill out this form and EZID will get in touch with you" in browser.page_source

    time.sleep(1)

    resaon_select = browser.find_element(By.ID, "id_contact_reason")
    
    select = Select(resaon_select)
    selected_value = "Other"
    select.select_by_value(selected_value)

    selected_option = select.first_selected_option
    assert selected_option.text == selected_value
    
    your_name = browser.find_element(By.ID, "id_your_name")
    your_name.send_keys("test name")
    your_email = browser.find_element(By.ID, "id_email")
    your_email.send_keys("ezid.test@cdl.org")
    your_name = browser.find_element(By.ID, "id_your_name")
    your_name.send_keys("test name")
    your_inst = browser.find_element(By.ID, "id_affiliation")
    your_inst.send_keys("CDL")
    comment = browser.find_element(By.ID, "id_comment")
    comment.send_keys("Test contact EZID form")
    dropdown_lists = browser.find_element(By.ID, "id_question")
    dropdown_lists.send_keys("2")

    submit_button = browser.find_element(By.XPATH, "//button[@class='button__primary general__form-submit']")
    browser.execute_script("arguments[0].scrollIntoView();", submit_button)

 # use wait until didn't work - got error "Element is not clickable at point (367, 863)"
 # however using time.sleep() worked
 # so, need to figure out what is preventing the submit button become clickable
 #   wait = WebDriverWait(browser, 10)
 #   submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='button__primary general__form-submit']")))
    
    time.sleep(1)
    submit_button.click()

    if base_url == "http://127.0.0.1:8000":
        assert "There was a problem sending your email" in browser.page_source
    else:
        assert "Thank you for your message. We will respond as soon as possible." in browser.page_source

    time.sleep(3)
    browser.quit()

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
        password = "apitest"
  
    base_urls = {
        "test": "http://127.0.0.1:8000",
        "dev": "https://ezid-dev.cdlib.org",
        "stg": "https://ezid-stg.cdlib.org",
        "prd": "https://ezid.cdlib.org"
    }
    base_url = base_urls.get(env)

    ui_test_login_logout(base_url, user, password)
    ui_test_creator_ark(base_url)
    ui_test_creator_doi(base_url)
    ui_test_contact(base_url)

if __name__ == '__main__':
    main()

