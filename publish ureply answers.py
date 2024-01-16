import json
import requests
from datetime import datetime
import urllib.parse
from os import system

with open("./info/info.json") as f:
    info = json.load(f)
    database_url = info["Database URL"]


def validate_data(data):
    print("Validating data...")
    
    for key in data:
        if key not in ["Session ID", "Ureply Answer", "Question Type"]:
            raise Exception(f"[!] Invalid keys \"{key}\"")

    question_type = data["Question Type"].lower().strip()
    if question_type not in ["mc", "typing"]:
        raise Exception(f"[!] Invalid question type \"{question_type}\"")

    ureply_answer = data["Ureply Answer"].lower().strip()
    if question_type == "mc":
        if ureply_answer.isnumeric() and 1<=int(ureply_answer)<=26:  # Convert numbers to letters
            ureply_answer = chr(int(ureply_answer) - 1 + ord('a'))
        
        if len(ureply_answer)>1 or ureply_answer > "z" or ureply_answer < "a":
            raise Exception(f"[!] Invalid ureply answer \"{ureply_answer}\"")

    return {
        "Session ID": data["Session ID"],
        "Ureply Answer": ureply_answer,
        "Question Type": question_type,
    }


def publish_ureply_info(data):
    # Push new ureply info to the database
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = requests.patch(f"{database_url}/{urllib.parse.quote(current_time)}.json", json=data)

    if response.status_code == 200:
        print("Data written successfully.")
    else:
        print("Error writing data:", response.text)

    # Update last updated time
    data = {"Last Updated Time": current_time}
    response = requests.patch(f"{database_url}/Last Updated Time.json", json=data)
    if response.status_code == 200:
        print(f"{current_time} | Last updated time written successfully.")
    else:
        print("Error writing last updated time:", response.text)


def save_to_file(data):
    # Save the info to the local file
    with open("./info/ureply_publish.json", "w") as f:
        json.dump(data, f, indent=4)
        print("Data saved to file successfully.")

with open("./info/ureply_publish.json") as f:
    data = json.load(f)
    try:
        data = validate_data(data)
    except Exception as e:
        print(e)
        system("pause")
        exit()

    print(json.dumps(data, indent=4))

    confirm = input("Confirm publishing the info above? ([y]/n): ")

    if confirm == "y" or confirm == "Y" or confirm == "":
        publish_ureply_info(data)
        save_to_file(data)
    else:
        print('Publishing cancelled. You can modify the file "ureply_publish.json" in the "info" folder.')

system("pause")
