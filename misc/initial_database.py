import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://facerecognition-5980a-default-rtdb.firebaseio.com/",
        # database URL
    },
)

ref = db.reference(
    "Students"
)  # reference path to our database... will create student directory in the database

data = {
    "777777": {  # id of student which is a key
        "id": "777777",
        "name": "Sowmi",
        "password": "January2001",
        "email": "sowmi@gmail.com"
    },
    
}


for key, value in data.items():
    ref.child(key).set(value)
