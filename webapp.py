from flask import Flask, render_template, Response, redirect, url_for, request
import cv2
import os
import pickle
import face_recognition
import numpy as np
import cvzone
from datetime import datetime
import json

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage


app = Flask(__name__)  # initializing


# database credentials
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(
    cred,
    {
        "databaseURL": "https://facerecognition-5980a-default-rtdb.firebaseio.com/",
        "storageBucket": "facerecognition-5980a.appspot.com",
    },
)

bucket = storage.bucket()


def dataset(id):
    studentInfo = db.reference(f"Students/{id}").get()
    blob = bucket.get_blob(f"static/Files/Images/{id}.jpg")
    array = np.frombuffer(blob.download_as_string(), np.uint8)
    imgStudent = cv2.imdecode(array, cv2.COLOR_BGRA2BGR)
    return studentInfo, imgStudent


already_marked_id_student = []
already_marked_id_admin = []


def generate_frame():
    # Background and Different Modes

    # video camera
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    imgBackground = cv2.imread("static/Files/Resources/background.png")

    folderModePath = "static/Files/Resources/Modes/"
    modePathList = os.listdir(folderModePath)
    imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

    # encoding loading ---> to identify if the person is in our database or not.... to detect faces that are known or not
    file = open("EncodeFile.p", "rb")
    encodeListKnownWithIds = pickle.load(file)
    file.close()
    encodedFaceKnown, studentIDs = encodeListKnownWithIds

    while True:
        success, img = capture.read()

        if not success:
            break

        imgSmall = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgSmall = cv2.cvtColor(imgSmall, cv2.COLOR_BGR2RGB)

        faceCurrentFrame = face_recognition.face_locations(imgSmall)
        encodeCurrentFrame = face_recognition.face_encodings(imgSmall, faceCurrentFrame)

        imgBackground[162:162 + 480, 55:55 + 640] = img

        if faceCurrentFrame:
            for encodeFace, faceLocation in zip(encodeCurrentFrame, faceCurrentFrame):
                matches = face_recognition.compare_faces(encodedFaceKnown, encodeFace)
                faceDistance = face_recognition.face_distance(encodedFaceKnown, encodeFace)

                matchIndex = np.argmin(faceDistance)

                y1, x2, y2, x1 = faceLocation
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

                bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)

                if matches[matchIndex]:
                    id = studentIDs[matchIndex]

                    studentInfo, imgStudent = dataset(id)

                    ref = db.reference(f"Students/{id}")

                    modeType = 3

                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                    (w, h), _ = cv2.getTextSize(
                        str(studentInfo["name"]), cv2.FONT_HERSHEY_COMPLEX, 1, 1
                    )
                    offset = (414 - w) // 2

                    cv2.putText(
                        imgBackground,
                        str(studentInfo["name"]),
                        (808 + offset, 445),
                        cv2.FONT_HERSHEY_COMPLEX,
                        1,
                        (50, 50, 50),
                        1,
                    )

                    imgStudentResize = cv2.resize(imgStudent, (216, 216))
                    imgBackground[175:175 + 216, 909:909 + 216] = imgStudentResize

                else:
                    cvzone.putTextRect(
                        imgBackground, "Face Detected", (65, 200), thickness=2
                    )
                    cv2.waitKey(3)
                    cvzone.putTextRect(
                        imgBackground, "Face Not Found", (65, 200), thickness=2
                    )
                    modeType = 4
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

        else:
            modeType = 0

        ret, buffer = cv2.imencode(".jpeg", imgBackground)
        frame = buffer.tobytes()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg \r\n\r\n" + frame + b"\r\n")



#########################################################################################################################


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video")
def video():
    return Response(
        generate_frame(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )

#########################################################################################################################

def add_image_database():
    folderPath = "static/Files/Images"
    imgPathList = os.listdir(folderPath)
    imgList = []
    studentIDs = []

    for path in imgPathList:
        imgList.append(cv2.imread(os.path.join(folderPath, path)))
        studentIDs.append(os.path.splitext(path)[0])

        fileName = f"{folderPath}/{path}"
        bucket = storage.bucket()
        blob = bucket.blob(fileName)
        blob.upload_from_filename(fileName)

    return studentIDs, imgList


def findEncodings(images):
    encodeList = []

    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)

    return encodeList


@app.route("/admin/add_user", methods=["GET", "POST"])
def add_user():
    id = request.form.get("id", False)
    name = request.form.get("name", False)
    password = request.form.get("password", False)
    email = request.form.get("email", False)

    if request.method == "POST":
        image = request.files["image"]
        filename = f"{'static/Files/Images'}/{id}.jpg"
        image.save(os.path.join(filename))

    encodeListKnown = findEncodings(imgList)

    encodeListKnownWithIds = [encodeListKnown, studentIDs]

    file = open("EncodeFile.p", "wb")
    pickle.dump(encodeListKnownWithIds, file)
    file.close()

    if id and name and password and email and image:
        add_student = db.reference(f"Students")
        add_student.child(id).set(
            {
                "id": id,
                "name": name,
                "password": password,
                "email": email
            }
        )
        studentIDs, imgList = add_image_database()
        return render_template("index.html")

    return render_template("add_user.html")

#########################################################################################################################
if __name__ == "__main__":
    app.run(debug=True, port=1600)
