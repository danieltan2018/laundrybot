import json

usersfilepath = "/Users/IndieDa/Documents/GitHub/laundrybot/users.json"

users = {"id": "5678"}
with open(usersfilepath,"w") as usersfile:
    json.dump(users, usersfile)