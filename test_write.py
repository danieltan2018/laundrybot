import json
'''
usersfilepath = "/Users/IndieDa/Documents/GitHub/laundrybot/users.json"

# function to add to JSON 
def write_json(data, filename=usersfilepath): 
    with open(usersfilepath) as json_file: 
        json_full = json.load(json_file) 
        temp = json_full['people'] 
        # python object to be appended 
        y = {'id':data}
        # appending data  
        temp.append(y)

    with open(filename,'w') as f: 
        json.dump(json_full, f, indent=4) 


write_json("haha")
'''

test = { "bla":
    {
        "a":"ddsadsa",
        "b" : "dsadsadsa"
    }
}


data = '{"president": { "name": "Zaphod Beeblebrox","species": "Betelgeusian"}}'

k = json.loads(data)
d = {"name":"dsadas"}
k['president'].update(d)
print(k)

blah = {"Cendana":{"washer 1":{"state":"ds"},"washer 2":{"state":"lol"}}, "Elm":"blah"}

blah["Cendana"].update({"washer 3":{"state":"on"}})
print(blah)

h = "wash"
print(h[0:2])