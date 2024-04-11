from pymongo import MongoClient
import bcrypt

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['footballDB']
users = db['users']

user_list = [
    {
        "name" : "Homer Simpson",
        "username" : "homer",
        "password" : b"homer_s",
        "email" : "homer@springfield.net",
        "admin" : True
    },
    {
        "name" : "Marge Simpson",
        "username" : "marge",
        "password" : b"marge_s",
        "email" : "marge@springfield.net",
        "admin" : False

    }
]

for new_user in user_list:
    new_user["password"] = bcrypt.hashpw(new_user["password"], bcrypt.gensalt())
    users.insert_one(new_user)