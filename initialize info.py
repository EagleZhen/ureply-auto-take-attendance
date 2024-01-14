import json
from os import system, makedirs
from getpass import getpass
from datetime import datetime

makedirs("./info", exist_ok=True)

print("Input Your CUHK Credentials for auto login (will be saved locally only)")
login_id = input("Login ID: ")
onepass_password = getpass("OnePass Password: ")
with open("./info/credential.json", "w") as f:
    json.dump({"Login ID": login_id, "OnePass Password": onepass_password}, f, indent=4)

print("\nInput your database info (will be saved locally only)")
database_url = getpass("Database URL: ")
with open("./info/info.json", "w") as f:
    json.dump({"Database URL": database_url}, f, indent=4)

with open("./info/ureply_retrieve.json", "w") as f:
    json.dump({"Session ID": "", "Ureply Answer": "", "Question Type": ""}, f, indent=4)

with open("./info/ureply_publish.json", "w") as f:
    json.dump({"Session ID": "", "Ureply Answer": "", "Question Type": ""}, f, indent=4)

print('\nInitialization Completed! You can double check the information in the "info" folder.')

system("pause")
