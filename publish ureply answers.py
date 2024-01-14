import json
import requests
from datetime import datetime
import urllib.parse

with open("./info/info.json") as f:
    info = json.load(f)
    database_url = info["Database URL"]

with open("./info/ureply.json") as f:
    data = json.load(f)
    
    # Push new ureply answers to the database
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = requests.patch(f"{database_url}/{urllib.parse.quote(current_time)}.json", json=data)

    if response.status_code == 200:
        print("Data written successfully.")
        print(json.dumps(data, indent=4))
    else:
        print("Error writing data:", response.text)
        
    # Update last updated time
    data = {"Last Updated Time": current_time}
    response = requests.patch(f"{database_url}/Last Updated Time.json", json=data)
    if response.status_code == 200:
        print(f"{current_time} | Last updated time written successfully.")
    else:
        print("Error writing last updated time:", response.text)