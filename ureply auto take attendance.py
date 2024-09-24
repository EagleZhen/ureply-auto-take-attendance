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


def initialize_credential(file_directory: str) -> tuple[str, str]:
    """
    Initialize CUHK credential from file
    """
    with open(file_directory) as f:
        info = json.load(f)
        email = info["Login ID"]
        onepass_password = info["OnePass Password"]

    return email, onepass_password


def initialize_general_info(file_directory: str) -> tuple[str, int, int]:
    """
    Initialize database url, afk time interval, and fetching time interval from file
    """
    with open(file_directory) as f:
        info = json.load(f)
        database_url = info["Database URL"]
        afk_time_interval = info["AFK Time Interval"]
        fetching_time_interval = info["Fetching Time Interval"]

    return database_url, afk_time_interval, fetching_time_interval


def initialize_last_retrieved_time(take_attendance_now: str) -> str:
    """
    Initialize last retrieved time based on user input.

    If the user wants to take attendance now, return `0001-01-01 00:00:00` (minimum datetime). Any uReply will be later than this time, so it will be handled immediately.

    If the user does not want to take attendance now, return the current datetime. No uReply will be earlier than this time, so only newer uReply will be handled.
    """
    if take_attendance_now.lower() != "y":
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        return datetime.min.strftime("%Y-%m-%d %H:%M:%S")  # 0001-01-01 00:00:00


def initialize_threads() -> tuple[threading.Event, threading.Thread]:
    return threading.Event(), None


def get_retry_time_interval(status: str = "default") -> int:
    """
    Retry with increasing time interval up to 30 seconds if an error occurs.
    """
    global fetching_time_interval
    if status == "error":
        fetching_time_interval = min(30, fetching_time_interval + 5)
    elif status == "default":
        fetching_time_interval = initial_fetching_time_interval

    return fetching_time_interval


def get_latest_ureply_from_database(database_url: str) -> tuple[str, str, str]:
    try:
        response = requests.get(f"{database_url}/Last Updated Time.json")
        if response.status_code == 200:
            last_updated_time = response.json()["Last Updated Time"]

            response = requests.get(
                f"{database_url}/{urllib.parse.quote(last_updated_time)}.json"
            )
            if response.status_code == 200:
                info = response.json()
                return (
                    last_updated_time,
                    info["Session ID"],
                    info["Ureply Answer"],
                    info["Question Type"],
                )
            else:
                raise Exception(
                    f"An error occurred while fetching ureply info: {response.text}"
                )
        else:
            raise Exception(
                f"[!] An error occurred while retrieving last updated time: {response.text}"
            )
    except Exception as e:
        print_message("An error occurred while requesting the database")
        raise e


def save_ureply_info_to_file(
    file_directory: str,
    last_updated_time: str,
    session_id: str,
    ureply_answer: str,
    question_type: str,
):
    with open(file_directory, "w") as f:
        data = {
            "Received Time": last_updated_time,
            "Session ID": session_id,
            "Ureply Answer": ureply_answer,
            "Question Type": question_type,
        }
        json.dump(data, f, indent=4)


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


def handle_duo_2fa(driver: WebDriver) -> bool:
    print_message("Waiting for Duo 2FA...")
    try:
        condition_trust_browser = EC.element_to_be_clickable(
            (By.ID, "trust-browser-button")
        )
        condition_try_again_button_appear = EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".button--primary.button--xlarge.try-again-button")
        )
        condition_skip_update_browser_button_appear = EC.element_to_be_clickable(
            (By.XPATH, "//button[text()='Skip for now']")
        )

        WebDriverWait(driver, 70).until(  # DUO Push times out after 60 seconds
            EC.any_of(
                # Condition 1: DUO Push approved, but prompted to trust the browser
                condition_trust_browser,
                # Condition 2: DUO Push times out
                condition_try_again_button_appear,
                # Condition 3: Duo prompted to update the browser before pushing
                condition_skip_update_browser_button_appear,
            )
        )

        if condition_trust_browser(driver):
            print_message("Duo Push approved")
            trust_browser_button = condition_trust_browser(driver)
            trust_browser_button.click()
            return True

        elif condition_try_again_button_appear(driver):
            print_message("Duo Push timed out. Initiating a new push...")
            try_again_button = condition_try_again_button_appear(driver)
            try_again_button.click()
            return False

        else:
            print_message("Skip updating the browser for now")
            skip_for_now_button = condition_skip_update_browser_button_appear(driver)
            skip_for_now_button.click()
            return False
    except Exception as e:
        raise e
    except:
        raise Exception("An error occurred while handling Duo 2FA")


def login_cusis(driver: WebDriver, email: str, password: str) -> None:
    print_message("Logging in CUSIS to establish the session...", notify=True, title="Logging in CUSIS")
    try:
        driver.get("https://cusis.cuhk.edu.hk/")
        WebDriverWait(driver, 10).until(
            EC.url_contains("https://sts.cuhk.edu.hk/adfs/ls/")
        )
        input_cuhk_credential(driver, email, password)

        while handle_duo_2fa(driver) is False:  # Keep pushing DUO until it is approved
            pass

        WebDriverWait(driver, 10).until(
            EC.url_contains("https://cusis.cuhk.edu.hk/")
        )  # Wait for the redirection to CUSIS to ensure the login session has been established properly
    except Exception as e:
        print_message(f"An error occurred while logging in CUSIS")
        raise e


def send_notification_for_new_ureply(question_type: str) -> None:
    if question_type == "typing":
        message = "Remember to type your own answers!"
    elif question_type == "mc":
        message = "Note that the multiple choice answer may not be always correct."

    print_message(
        message,
        notify=True,
        title=f"New {question_type} uReply - {session_id}",
        write_to_log=False,
    )


def join_ureply_session(driver: WebDriver, session_id: str) -> bool:
    try:
        WebDriverWait(driver, 10).until(
            # Ensure it is on the uReply page
            EC.url_to_be("https://server4.ureply.mobi/student/cads/joinsession.php")
        )
        print_message(f'Joined uReply session "{session_id}"')
        return True

    # Invalid session number / session ended
    except UnexpectedAlertPresentException as e:
        # Close the alert
        alert = driver.switch_to.alert
        alert.accept()

        if e.alert_text != "Invalid session number":
            print_message("An uncommon alert was present")
            raise e
        else:
            print_message(
                f"[!] {e.alert_text} - The session may have ended. Skipping..."
            )
            return False
    except Exception as e:
        print_message("An error occurred while joining ureply session")
        raise e


def handle_new_ureply(
    driver: WebDriver, session_id: str, question_type: str, ureply_answer: str
) -> None:
    print_message(
        f"Received a new uReply : {session_id} | {question_type} | {ureply_answer}"
    )

    try:
        # Only perform actions if the session requires login (i.e. attendance taking)
        # Turns out some courses like to use uReply without login
        # if session_id.startswith("L") is False:
        #     print_message("This session does not require login. Skipping...")
        #     return

        received_new_answer_event.set()  # Set the internal flag to True to stop AFK checking immediately
        if afk_checking_thread is not None:
            afk_checking_thread.join()  # Wait for the thread to finish answering the previous question

        print_divider()

        send_notification_for_new_ureply(question_type)

        # Join uReply with the specified session ID in a new tab
        driver.switch_to.new_window("tab")
        driver.get(  # This url always require login
            f"https://server4.ureply.mobi/student/cads/mobile_login_check.php?sessionid={session_id}"
        )

        # uReply page
        if join_ureply_session(driver, session_id) is False:
            return

        answer_ureply_question()

        print_divider()

    except Exception as e:
        print_message("An error occurred while handling the new uReply")
        raise e


if __name__ == "__main__":
    try:
        email, onepass_password = initialize_credential("./info/credential.json")

        database_url, afk_time_interval, initial_fetching_time_interval = (
            initialize_general_info("./info/info.json")
        )
        fetching_time_interval = initial_fetching_time_interval

        last_retrieved_time = initialize_last_retrieved_time(
            input("\nDo you want to take attendance now? (y / [n]): ")
        )

        received_new_answer_event, afk_checking_thread = initialize_threads()

        driver = setup_selenium()
        login_cusis(driver, email, onepass_password)
    except Exception as e:
        print_message(
            f"An error occurred during initialization | {e.__class__.__name__}\n\n{e}"
        )
        input("\nPress any key to exit...")
        exit()

    while True:
        try:
            last_database_update_time, session_id, ureply_answer, question_type = (
                get_latest_ureply_from_database(database_url)
            )

            # Update ureply info in local file
            save_ureply_info_to_file(
                "./info/ureply_retrieve.json",
                last_database_update_time,
                session_id,
                ureply_answer,
                question_type,
            )

            if last_database_update_time <= last_retrieved_time:
                print_message(
                    f"No new ureply since {last_database_update_time}",
                    write_to_log=False,
                )
            else:
                handle_new_ureply(driver, session_id, question_type, ureply_answer)
                last_retrieved_time = last_database_update_time

        except (
            requests.ConnectionError,  # Network error from firebase request
            TimeoutException,  # Timeout error from selenium
            WebDriverException,  # WebDriver error from selenium, e.g. cannot resolve hostname
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

        sleep(get_retry_time_interval("default"))
