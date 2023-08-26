import requests


url = "https://discord.com/api/v10/applications/<Application ID>/guilds/<GUILD ID>/commands"

json = {
    "name": "mod",
    "description": "mod",
    "options": [
        {
            "name": "start_prediction",
            "description": "start_prediction",
            "type": 1,
        }
    ]
}

# For authorization, you can use either your bot token
headers = {
    "Authorization": "Bot <TOKEN>"
}

r = requests.post(url, headers=headers, json=json)
