import threading
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    TimeoutException,
    WebDriverException,
)
from time import sleep
from datetime import datetime
from plyer import notification
import json
import requests
import urllib.parse

received_new_answer_event = threading.Event()

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

# Initialize database URL from local file
with open("./info/info.json") as f:
    info = json.load(f)
    database_url = info["Database URL"]
    afk_time_interval = info["AFK Time Interval"]
    fetching_time_interval = info["Fetching Time Interval"]


def print_divider():
    print("\n========================================\n")


debug_mode = False


def debug(*args):
    if debug_mode is True:
        message = " ".join(str(arg) for arg in args)
        print(message)


def print_message(message, write_to_log=True, notify=False, title=""):
    # Show the timestamps for the corresponding status code
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S")
    # print timestamps with the message
    print(formatted_datetime, "|", message)

    if write_to_log:
        with open("./info/log.txt", "a", encoding="utf-8") as log:
            log.write(formatted_datetime + " | " + message + "\n")

    if notify is True:
        notification.notify(title=title, message=message, timeout=5)

# Retry with increasing time interval up to 30 seconds
def get_retry_time_interval(status: str = None) -> int:
    global retry_count
    if (status == "error"): retry_count += 1
    elif (status == "default"): retry_count = 0
    
    return min(30, fetching_time_interval + retry_count * 5)


def login_cuhk():
    global email, onepass_password

    # Ensure the input area is clickable before sending keys
    try:
        login_id_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "userNameInput"))
        )
        password_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "passwordInput"))
        )
    except:
        raise Exception(
            "Timeout waiting for the input area in CUHK login page to be clickable."
        )

    login_id_input.send_keys(email)
    password_input.send_keys(onepass_password)

    password_input.send_keys(Keys.RETURN)


def check_is_ureply_answer_submitted():
    # Define the locator for the element
    span_locator = (By.XPATH, "//p[@class='title']/span[@style='color:red;']")

    # Wait for the element's text to change
    WebDriverWait(driver, 10).until(
        lambda driver: ureply_answer.lower()
        in driver.find_element(*span_locator).text.lower()
    )

    # After the wait, retrieve the element again and check its text
    result = driver.find_element(*span_locator)
    current_value = result.text.strip()

    if ureply_answer.lower() in current_value.lower():
        print_message(f'Answered uReply question with answer "{ureply_answer}"')
    else:
        raise Exception(
            f'An error occurred while answering uReply question with answer "{ureply_answer}"'
        )


def check_afk_and_respond(textbox_element):
    global ureply_answer
    is_afk = True
    start_time = datetime.now()

    print_message(
        f"Checking whether you are AFK in the following {afk_time_interval} seconds..."
    )

    # Check if the textbox content is changed during the specified time interval
    while (datetime.now() - start_time).seconds < afk_time_interval:
        # Received new ureply answers
        if received_new_answer_event.is_set():
            print_message("Received a new uReply. Stopping AFK checking...")
            return

        # Textbox content is changed manually
        if textbox_element.get_attribute("value") != ureply_answer:
            is_afk = False
            print_message("Detected answer change. Stopping AFK checking...")
            return

        print_message(
            f"Waiting for you to type your answer...{afk_time_interval - (datetime.now() - start_time).seconds} seconds left"
        )
        sleep(5)

    # Click submit button if AFK is detected and no new answer is received
    if (is_afk is True) and (received_new_answer_event.is_set() is False):
        print_message("AFK detected. Answering ureply question...")

        xpath_expression = (
            f'//button[@class="text_btn mdl-button mdl-js-button mdl-button--raised "]'
        )
        submit_button_element = driver.find_element(By.XPATH, xpath_expression)
        submit_button_element.click()
        debug("submit button - xpath_expression:", xpath_expression)

        check_is_ureply_answer_submitted()


def answer_ureply_question():
    global ureply_answer, question_type

    try:
        if question_type == "mc":
            xpath_expression = f'//button[@class="mc_choice_btn choice_btn mdl-button choice_{ureply_answer.lower()} mdl-js-button mdl-button--raised "]'
            try:
                choice_element = WebDriverWait(
                    driver, 10
                ).until(  # ensure the button is clickable before clicking
                    EC.element_to_be_clickable((By.XPATH, xpath_expression))
                )
            except:
                raise Exception(
                    f'Timeout waiting for the mc choice button "{ureply_answer}" to be clickable. Check if this choice is valid.'
                )
            choice_element.click()

            check_is_ureply_answer_submitted()

        elif question_type == "typing":
            # Input typing answers
            xpath_expression = f'//textarea[@class="mdl-textfield__input"]'
            try:
                textbox_element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_expression))
                )
            except:
                raise Exception(
                    "Timeout waiting for the textbox to be ready in the typing question"
                )
            driver.execute_script(
                f"arguments[0].value = '{ureply_answer}';", textbox_element
            )
            debug("textbox - xpath expression:", xpath_expression)

            # Check if the user is AFK and respond if necessary
            received_new_answer_event.clear()  # Set the internal flag to False
            afk_checking_thread = threading.Thread(
                target=check_afk_and_respond, args=(textbox_element,)
            )
            afk_checking_thread.start()
    except Exception as e:
        print_message("An error occurred while answering the uReply question")
        raise e  # Raise exception to retry in the main loop


take_attendance_now = input("\nDo you want to take attendance now? (y/[n]): ")
with open("./info/last_retrieved_time.json", "w") as f:
    if (
        take_attendance_now == "n"
        or take_attendance_now == "N"
        or take_attendance_now == ""
    ):
        # The script "ureply auto take attendance" will take attendance when a newer ureply is published later
        json.dump(
            {"Last Retrieved Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            f,
            indent=4,
        )
    else:
        # The script "ureply auto take attendance" will take attendance immediately
        json.dump({"Last Retrieved Time": ""}, f, indent=4)

retry_count = 0
while True:
    try:
        response = requests.get(f"{database_url}/Last Updated Time.json")
        if response.status_code == 200:
            last_updated_time = response.json()["Last Updated Time"]

            # Get the last retrieved time from the local file
            with open("./info/last_retrieved_time.json") as f:
                last_retrieved_time = json.load(f)["Last Retrieved Time"]

            # Handle new ureplies
            if last_updated_time > last_retrieved_time:
                try:
                    print_divider()

                    received_new_answer_event.set()  # Set the internal flag to True

                    # Get ureply info from database
                    response = requests.get(
                        f"{database_url}/{urllib.parse.quote(last_updated_time)}.json"
                    )
                    if response.status_code == 200:
                        info = response.json()
                        session_id = info["Session ID"]
                        ureply_answer = info["Ureply Answer"]
                        question_type = info["Question Type"]

                        # Update ureply info in local file
                        with open("./info/ureply_retrieve.json", "w") as f:
                            data = {
                                "Session ID": session_id,
                                "Ureply Answer": ureply_answer,
                                "Question Type": question_type,
                            }
                            json.dump(data, f, indent=4)

                        print_message(
                            f"Received a new {question_type} uReply - {session_id}"
                        )

                        if question_type == "typing":
                            message = "Remember to type your own answers!"
                        elif question_type == "mc":
                            message = f"You may update the answer if necessary."

                        print_message(
                            message,
                            notify=True,
                            title=f"New {question_type} uReply - {session_id}",
                        )
                    else:
                        raise Exception(
                            f"An error occurred while fetching ureply info: {response.text}"
                        )

                    # Joining uReply with the specified session ID
                    driver = webdriver.Chrome()
                    driver.set_page_load_timeout(10) # Prevent infinite page loading due to network lost
                    driver.get(
                        f"https://server4.ureply.mobi/student/cads/mobile_login_check.php?sessionid={session_id}"
                    )

                    # CUHK login page
                    if session_id.startswith("L"):  # session that requires login
                        try:
                            WebDriverWait(driver, 10).until(
                                # ensure the URL contains the specified string, i.e. it is on the CUHK login page
                                EC.url_contains("https://sts.cuhk.edu.hk/adfs/ls/")
                            )
                            print_message("Redirected to CUHK login page")
                            login_cuhk()  # input CUHK credential
                        except Exception as e:
                            print_message("An error occurred on CUHK login page")
                            raise e

                    # uReply page
                    try:
                        WebDriverWait(driver, 10).until(
                            # ensure the URL is exactly the specified URL, i.e. it is on the uReply page
                            EC.url_to_be(
                                "https://server4.ureply.mobi/student/cads/joinsession.php"
                            )
                        )
                        print_message(f'Joined ureply session "{session_id}"')
                        answer_ureply_question()

                    # Invalid session number / session ended
                    except UnexpectedAlertPresentException as e:
                        print_message(
                            f"[!] {e.alert_text} - The session may have ended."
                        )
                        if e.alert_text != "Invalid session number":
                            print_message("An uncommon alert was present")
                            raise e
                    except Exception as e:
                        print_message("An error occurred while joining ureply session")
                        raise e

                    # Update last retrieved time
                    with open("./info/last_retrieved_time.json", "w") as f:
                        data = {"Last Retrieved Time": last_updated_time}
                        json.dump(data, f, indent=4)

                    print_divider()
                except Exception as e:
                    print_message("An error occurred while handling the new uReply")
                    raise e

            else:
                print_message(
                    f"No new ureply since {last_updated_time}", write_to_log=False
                )

        else:
            raise Exception(
                f"[!] An error occurred while retrieving last updated time: {response.text}"
            )
    except (
        requests.ConnectionError,
        TimeoutException,
    ) as e:  # Network error from firebase request or selenium timeout
        print_message(f"[!] Error class name: {e.__class__.__name__}")
        print_message(f"\n\n{e}\n")
        print_message(
            f"Your network may be disconnected. Retry in {get_retry_time_interval("error")} seconds...",
            notify=True,
            title=f"{e.__class__.__name__}",
        )
    except Exception as e:
        print_message(f"[!] Error class name: {e.__class__.__name__}")
        print_message(f"\n\n{e}\n")
        print_message(
            message=f"Retry in {get_retry_time_interval("error")} seconds...",
            notify=True,
            title=f"{e.__class__.__name__}",
        )

    sleep(get_retry_time_interval())  # Retry with increasing interval up to 30 seconds
