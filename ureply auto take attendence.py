from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import os


def print_divider():
    print("\n========================================\n")


with open("./info/credential.json") as f:
    info = json.load(f)
    email = info["Login ID"]
    onepass_password = info["OnePass Password"]
    
with open("./info/ureply.json") as f:
    info = json.load(f)
    session_id = info["Session ID"]
    ureply_answer = info["Ureply Anwswer"]
    question_type = info["Question Type"]


def login_cuhk():
    login_id_input = driver.find_element(By.ID, "userNameInput")
    login_id_input.send_keys(email)

    password_input = driver.find_element(By.ID, "passwordInput")
    password_input.send_keys(onepass_password)

    password_input.send_keys(Keys.RETURN)


def navigate_to_ureply():
    driver.get("https://server4.ureply.mobi/")
    session_input = driver.find_element(
        By.ID, "sessionid"
    )  # https://selenium-python.readthedocs.io/locating-elements.html
    session_input.send_keys(session_id)
    session_input.send_keys(Keys.RETURN)


def answer_ureply_question():
    if (question_type == "MC"):
        xpath_expression = f'//button[@class="mc_choice_btn choice_btn mdl-button choice_{ureply_answer.lower()} mdl-js-button mdl-button--raised "]'
        option_element = driver.find_element(By.XPATH, xpath_expression)
        option_element.click()
    elif (question_type == "Typing"):
        xpath_expression = f'//textarea[@class="mdl-textfield__input"]'
        textbox_element = driver.find_element(By.XPATH, xpath_expression)
        textbox_element.clear()
        textbox_element.send_keys(ureply_answer)
        print("textbox - xpath expression:", xpath_expression)
        
        xpath_expression = f'//button[@class="text_btn mdl-button mdl-js-button mdl-button--raised "]'
        submit_button_element = driver.find_element(By.XPATH, xpath_expression)
        submit_button_element.click()
        print("submit button - xpath_expression:", xpath_expression)

# Navigate to ureply and join the specified session
driver = webdriver.Chrome()
navigate_to_ureply()

# Wait for the cuhk login page to load
login_page_url_prefix = "https://sts.cuhk.edu.hk/adfs/ls/"
try:
    WebDriverWait(driver, 10).until(EC.url_contains(login_page_url_prefix))
except:
    print("Timeout waiting for redirect")

# Check if it redirected to CUHK login page
print_divider()
print("Current URL:", driver.current_url)
if login_page_url_prefix in driver.current_url:
    # Handle CUHK login (enter credentials)
    print("Redirected to CUHK login page")
    login_cuhk()

# Wait for the ureply page to load
try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//body")))
    print("Loaded ureply page")
except:
    print("Timeout waiting for redirect")

# Anwer ureply questions (MC only for now)
print_divider()
print("Current URL:", driver.current_url)
if driver.current_url == "https://server4.ureply.mobi/student/cads/joinsession.php":
    print("Joined ureply session")
    answer_ureply_question()

os.system("pause")  # Prevent the browser from closing immediately
