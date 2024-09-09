import threading
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
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
from random import randint


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


def setup_selenium() -> WebDriver:
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(
        10
    )  # Prevent infinite page loading due to network lost
    return driver


# Retry with increasing time interval up to 30 seconds
def get_retry_time_interval(status: str = None) -> int:
    global fetching_time_interval

    if status == "error":
        fetching_time_interval += 5
    elif status == "default":
        fetching_time_interval = 5

    return min(30, fetching_time_interval)


def input_cuhk_credential(driver: WebDriver, email: str, password: str):
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
    password_input.send_keys(password)

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
    currently_submitted_answer = driver.find_element(*span_locator).text.strip()

    # print("currently_submitted_answer:", currently_submitted_answer)
    # print("ureply_answer:", ureply_answer)

    if (
        question_type == "mc"
        and ureply_answer.lower() in currently_submitted_answer.lower()
    ) or (question_type == "typing" and ureply_answer == currently_submitted_answer):
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
    check_count = 0
    while (datetime.now() - start_time).seconds < afk_time_interval:
        # Received new ureply answers
        if received_new_answer_event.is_set():
            is_afk = False
            print_message("Received a new uReply. Stopping AFK checking...")
            break

        # Textbox content is changed manually
        if textbox_element.get_attribute("value") != ureply_answer:
            is_afk = False
            print_message("Detected answer change. Stopping AFK checking...")
            return

        # Print the checking message every 5 seconds
        if check_count % 5 == 0:
            print_message(
                f"Waiting for you to type your answer...{afk_time_interval - (datetime.now() - start_time).seconds} seconds left"
            )

        # Check every 1 second
        sleep(1)
        check_count += 1

    # Submit the answer if AFK is detected OR received a new uReply
    if (is_afk is True) or (received_new_answer_event.is_set()):
        print_message(
            f"{'AFK detected. ' if is_afk is True else 'Received a new uReply. '}Answering ureply question..."
        )

        xpath_expression = (
            f'//button[@class="text_btn mdl-button mdl-js-button mdl-button--raised "]'
        )
        submit_button_element = driver.find_element(By.XPATH, xpath_expression)
        submit_button_element.click()
        debug("submit button - xpath_expression:", xpath_expression)

        check_is_ureply_answer_submitted()


def answer_ureply_question():
    global ureply_answer, question_type, afk_checking_thread

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
            # print("testing textbox element with input tag")
            # sleep(20)

            # Input typing answers
            xpath_expression = f'//*[@class="mdl-textfield__input"]'  # "*" because the element is not always "textarea", it is "input" sometimes
            textbox_element = None
            try:
                textbox_element = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, xpath_expression))
                )
            except:
                raise Exception(
                    "Timeout waiting for the textbox to be ready in the typing question"
                )

            if (
                textbox_element.tag_name == "input"
                and textbox_element.get_attribute("type") == "number"
                and not ureply_answer.isnumeric()
            ):
                raise Exception(
                    "The textbox only accepts numeric value. You may need another valid answer."
                )

            driver.execute_script(  # to support unicode characters, such as emoji, avoid the error "ChromeDriver only supports characters in the BMP"
                f"arguments[0].value = '{ureply_answer}';", textbox_element
            )
            debug("textbox - xpath expression:", xpath_expression)

            # Check if the user is AFK and submit the answer only if necessary
            received_new_answer_event.clear()  # Set the internal flag to False
            afk_checking_thread = threading.Thread(
                target=check_afk_and_respond, args=(textbox_element,)
            )
            afk_checking_thread.start()
    except Exception as e:
        print_message("An error occurred while answering the uReply question")
        raise e  # Raise exception to retry in the main loop


def initialize_credential() -> tuple[str, str]:
    """
    Initialize CUHK credential from `credential.json` file
    """
    with open("./info/credential.json") as f:
        info = json.load(f)
        email = info["Login ID"]
        onepass_password = info["OnePass Password"]

    return email, onepass_password


def initialize_ureply_info() -> tuple[str, str, str]:
    """
    Initialize ureply info from `ureply_retrieve.json` file
    """
    with open("./info/ureply_retrieve.json") as f:
        info = json.load(f)
        session_id = info["Session ID"]
        ureply_answer = info["Ureply Answer"]
        question_type = info["Question Type"]

    return session_id, ureply_answer, question_type


def initialize_general_info() -> tuple[str, int, int]:
    """
    Initialize database url, afk time interval, and fetching time interval from `info.json` file
    """
    with open("./info/info.json") as f:
        info = json.load(f)
        database_url = info["Database URL"]
        afk_time_interval = info["AFK Time Interval"]
        fetching_time_interval = info["Fetching Time Interval"]

    return database_url, afk_time_interval, fetching_time_interval


def initialize_threads() -> tuple[threading.Event, threading.Thread]:
    return threading.Event(), None


def login_cusis(driver: WebDriver, email: str, password: str) -> None:
    print_message("Logging in CUSIS to establish the session...")
    try:
        driver.get("https://cusis.cuhk.edu.hk/")
        WebDriverWait(driver, 10).until(
            EC.url_contains("https://sts.cuhk.edu.hk/adfs/ls/")
        )
        input_cuhk_credential(driver, email, password)

        WebDriverWait(driver, 10).until(
            EC.any_of(
                EC.url_contains("https://api-08dc11c9.duosecurity.com"),
                EC.url_contains("https://cusis.cuhk.edu.hk/"),
            )
        )

        if driver.current_url.find("duosecurity.com") != -1:
            while (
                handle_duo_2fa(driver) is False
            ):  # Keep pushing DUO until it is approved
                pass

        print_message("Logged in CUSIS successfully")
    except:
        raise Exception("An error occurred while logging in CUSIS")


def handle_duo_2fa(driver: WebDriver) -> bool:
    print_message("Waiting for Duo 2FA...")
    try:
        WebDriverWait(driver, 70).until(  # DUO Push times out after 60 seconds
            EC.any_of(
                # Condition 1: DUO Push times out
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        ".button--primary.button--xlarge.try-again-button",
                    )
                ),
                # Condition 2: DUO Push approved, but prompted to trust the browser
                EC.element_to_be_clickable((By.ID, "trust-browser-button")),
                # Condition 3: DUO Push approved and redirected to CUSIS
                EC.url_contains("https://cusis.cuhk.edu.hk/"),
            )
        )

        if driver.current_url.startswith("https://cusis.cuhk.edu.hk/"):
            print_message("Duo Push approved, redirected to CUSIS")
            return True

        elif EC.element_to_be_clickable((By.ID, "trust-browser-button"))(driver):
            print_message("Duo Push approved, prompted to trust the browser")
            trust_browser_button = driver.find_element(By.ID, "trust-browser-button")
            trust_browser_button.click()
            return True

        else:
            print_message("Duo Push timed out. Initiating a new push...")
            try_again_button = driver.find_element(
                By.CSS_SELECTOR, ".button--primary.button--xlarge.try-again-button"
            )
            try_again_button.click()
            return False
    except Exception as e:
        raise e
    except:
        raise Exception("An error occurred while handling Duo 2FA")


if __name__ == "__main__":
    email, onepass_password = initialize_credential()
    session_id, ureply_answer, question_type = initialize_ureply_info()
    database_url, afk_time_interval, fetching_time_interval = initialize_general_info()

    received_new_answer_event, afk_checking_thread = initialize_threads()

    driver = setup_selenium()
    login_cusis(driver, email, onepass_password)

    take_attendance_now = input("\nDo you want to take attendance now? (y / [n]): ")
    with open("./info/last_retrieved_time.json", "w") as f:
        if take_attendance_now.lower() != "y":
            # Take attendance when later a newer ureply is published
            json.dump(
                {"Last Retrieved Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                f,
                indent=4,
            )
        else:
            # Take attendance immediately
            json.dump({"Last Retrieved Time": ""}, f, indent=4)

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
                        received_new_answer_event.set()  # Set the internal flag to True to stop AFK checking immediately
                        if afk_checking_thread is not None:
                            afk_checking_thread.join()  # Wait for the thread to finish answering the previous question

                        print_divider()

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

                        else:
                            raise Exception(
                                f"An error occurred while fetching ureply info: {response.text}"
                            )

                        # Only perform actions if the session requires login (i.e. attendance taking)
                        if session_id.startswith("L"):
                            if question_type == "typing":
                                message = "Remember to type your own answers!"
                            elif question_type == "mc":
                                message = "Note that the multiple choice answer may not be always correct."

                            print_message(  # for desktop notification
                                message,
                                notify=True,
                                title=f"New {question_type} uReply - {session_id}",
                            )

                            # Joining uReply with the specified session ID
                            driver.get(  # This url always require login
                                f"https://server4.ureply.mobi/student/cads/mobile_login_check.php?sessionid={session_id}"
                            )

                            # CUHK login page
                            try:
                                WebDriverWait(driver, 10).until(
                                    # Ensure the URL contains the specified string, i.e. it is on the CUHK login page
                                    EC.url_contains("https://sts.cuhk.edu.hk/adfs/ls/")
                                )
                                print_message("Redirected to CUHK login page")
                                input_cuhk_credential()  # input CUHK credential
                            except Exception as e:
                                print_message("An error occurred on CUHK login page")
                                raise e

                            # uReply page
                            try:
                                WebDriverWait(driver, 10).until(
                                    # Ensure the URL is exactly the specified URL, i.e. it is on the uReply page
                                    EC.url_to_be(
                                        "https://server4.ureply.mobi/student/cads/joinsession.php"
                                    )
                                )
                                print_message(f'Joined ureply session "{session_id}"')

                            # Invalid session number / session ended
                            except UnexpectedAlertPresentException as e:
                                print_message(
                                    f"[!] {e.alert_text} - The session may have ended."
                                )
                                if e.alert_text != "Invalid session number":
                                    print_message("An uncommon alert was present")
                                    raise e
                            except Exception as e:
                                print_message(
                                    "An error occurred while joining ureply session"
                                )
                                raise e

                            answer_ureply_question()
                        else:
                            print_message(
                                "This session does not require login. Skipping..."
                            )

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
            requests.ConnectionError,  # Network error from firebase request
            TimeoutException,  # Timeout error from selenium
        ) as e:
            print_message(f"[!] Error class name: {e.__class__.__name__}")
            print_message(f"\n\n{e}\n")
            print_message(
                f'Your network may be disconnected. Retry in {get_retry_time_interval("error")} seconds...',
                notify=True,
                title=f"{e.__class__.__name__}",
            )
        except Exception as e:
            print_message(f"[!] Error class name: {e.__class__.__name__}")
            print_message(
                message=f'Retry in {get_retry_time_interval("error")} seconds...\n{"-"*10}\n{e}',  # show error message in the notification
                notify=True,
                title=f"{e.__class__.__name__}",
            )

        sleep(
            get_retry_time_interval()
        )  # Retry with increasing interval up to 30 seconds
