from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from datetime import datetime
import json
import requests
import urllib.parse


def print_divider():
    print("\n========================================\n")


debug_mode = False


def debug(*args):
    if debug_mode is True:
        message = " ".join(str(arg) for arg in args)
        print(message)


def print_message(message, write_to_log=True):
    # Show the timestamps for the corresponding status code
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    # print timestamps with the message
    print(formatted_datetime, "|", message)

    if write_to_log:
        with open("./info/log.txt", "a") as log:
            log.write(formatted_datetime + " | " + message + "\n")


# Initialize CUHK credential from local file
with open("./info/credential.json") as f:
    info = json.load(f)
    email = info["Login ID"]
    onepass_password = info["OnePass Password"]

# Initialize ureply info from local file (may be outdated)
with open("./info/ureply_retrieve.json") as f:
    info = json.load(f)
    session_id = info["Session ID"]
    ureply_answer = info["Ureply Answer"]
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
    if question_type == "MC":
        xpath_expression = f'//button[@class="mc_choice_btn choice_btn mdl-button choice_{ureply_answer.lower()} mdl-js-button mdl-button--raised "]'
        option_element = driver.find_element(By.XPATH, xpath_expression)
        option_element.click()
    elif question_type == "Typing":
        # Input typing answers
        xpath_expression = f'//textarea[@class="mdl-textfield__input"]'
        textbox_element = driver.find_element(By.XPATH, xpath_expression)
        textbox_element.clear()
        textbox_element.send_keys(ureply_answer)
        debug("textbox - xpath expression:", xpath_expression)

        # Click submit button
        xpath_expression = f'//button[@class="text_btn mdl-button mdl-js-button mdl-button--raised "]'
        submit_button_element = driver.find_element(By.XPATH, xpath_expression)
        submit_button_element.click()
        debug("submit button - xpath_expression:", xpath_expression)

    print_message(f"Answered ureply question with answer \"{ureply_answer}\"")


with open("./info/info.json") as f:
    info = json.load(f)
    database_url = info["Database URL"]

while True:
    response = requests.get(f"{database_url}/Last Updated Time.json")
    if response.status_code == 200:
        last_updated_time = response.json()["Last Updated Time"]

        # Get the last retrieved time from the local file
        with open("./info/last_retrieved_time.json") as f:
            last_retrieved_time = json.load(f)["Last Retrieved Time"]

        # Handle new ureplies
        if last_updated_time > last_retrieved_time:
            print_divider()
            
            # Get ureply info from database
            response = requests.get(f"{database_url}/{urllib.parse.quote(last_updated_time)}.json")
            if response.status_code == 200:
                info = response.json()
                session_id = info["Session ID"]
                ureply_answer = info["Ureply Answer"]
                question_type = info["Question Type"]

                # Update ureply info in local file
                with open("./info/ureply_retrieve.json", "w") as f:
                    data = {"Session ID": session_id, "Ureply Answer": ureply_answer, "Question Type": question_type}
                    json.dump(data, f, indent=4)
            else:
                print_message("Error retrieving ureply info:", response.text)
                continue

            # Navigate to ureply and join the specified session
            driver = webdriver.Chrome()
            navigate_to_ureply()

            # Wait for the cuhk login page to load
            login_page_url_prefix = "https://sts.cuhk.edu.hk/adfs/ls/"
            try:
                WebDriverWait(driver, 10).until(EC.url_contains(login_page_url_prefix))
                debug("Loaded CUHK login page")
            except:
                print_message("Timeout waiting for redirect")
                continue

            # Check if it redirected to CUHK login page
            debug("Current URL:", driver.current_url)
            if login_page_url_prefix in driver.current_url:
                # Handle CUHK login (enter credentials)
                print_message("Redirected to CUHK login page")
                login_cuhk()
            else:
                print_message("Error redirecting to CUHK login page")
                continue

            # Wait for the ureply page to load
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//body")))
                debug("Loaded ureply page")
            except:
                print_message("Timeout waiting for redirect")
                continue

            # Anwer ureply questions (MC only for now)
            debug("Current URL:", driver.current_url)
            if driver.current_url == "https://server4.ureply.mobi/student/cads/joinsession.php":
                print_message(f"Joined ureply session \"{session_id}\"")
                answer_ureply_question()
            else:
                print_message("Error joining ureply session")
                continue

            # Update last retrieved time
            with open("./info/last_retrieved_time.json", "w") as f:
                data = {"Last Retrieved Time": last_updated_time}
                json.dump(data, f, indent=4)

            print_divider()

        else:
            print_message(f"No new ureply since {last_updated_time}")

    else:
        print_message("Error retrieving last updated time:", response.text)

    sleep(10)