import json
from os import system, makedirs, path
from getpass import getpass
from datetime import datetime
from send2trash import send2trash

folder_path = "./info"
# Remove the info folder if it exists to start fresh
if path.exists(folder_path):
    send2trash(folder_path)
makedirs(folder_path, exist_ok=True)

print("Input Your CUHK Credentials for auto login (will be saved locally only)")
login_id = input("Login ID: ")
onepass_password = getpass("OnePass Password: ")
with open("./info/credential.json", "w") as f:
    json.dump({"Login ID": login_id, "OnePass Password": onepass_password}, f, indent=4)

print("\nInput your database info (will be saved locally only)")
database_url = getpass("Database URL: ")


print(
    '\nFetching Time Interval is set to be 5 seconds by default.\n'
    'AFK Checking Time Interval is set to be 30 seconds by default.\n'
    'You can change it in the "info.json" file if necessary.'
)

with open("./info/info.json", "w") as f:
    json.dump(
        {
            "Database URL": database_url,
            "Fetching Time Interval": 5,
            "AFK Time Interval": 30,
        },
        f,
        indent=4,
    )

with open("./info/ureply_retrieve.json", "w") as f:
    json.dump({"Session ID": "", "Ureply Answer": "", "Question Type": ""}, f, indent=4)
    
with open("./info/ureply_publish.json", "w") as f:
    json.dump({"Session ID": "", "Ureply Answer": "", "Question Type": ""}, f, indent=4)

print(
    '\nInitialization Completed! You can double check the information in the "info" folder.'
)

system("pause")
