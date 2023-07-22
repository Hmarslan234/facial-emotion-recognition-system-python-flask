from flask import Flask, flash, render_template, request,redirect, url_for, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_bcrypt import Bcrypt
import numpy as np
import matplotlib.pyplot as plt
import cv2
import csv
import datetime
import pandas as pd
import re
import urllib.request
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Flatten
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import os
app=Flask(__name__)
app.config["SECRET_KEY"]='65b0b774279de460f1cc5c92'
app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///ums.sqlite"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config["SESSION_PERMANENT"]=False
app.config["SESSION_TYPE"]='filesystem'
db=SQLAlchemy(app)
bcrypt=Bcrypt(app)
Session(app)

camera = cv2.VideoCapture(0)

# Create the "Emotions" folder if it doesn't exist
if not os.path.exists("Emotions"):
    os.makedirs("Emotions")

# Assuming you have the 'emotion_dict' and 'model' defined somewhere in your code

def create_csv_file():
    # Generate the file name using the current date
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = os.path.join("Emotions", f"emotions_{today_date}.csv")

    # Create the CSV file and write the header row if the file doesn't exist
    if not os.path.exists(file_name):
        with open(file_name, 'w', newline='') as csvfile:
            fieldnames = ['Time', 'Username', 'Emotion']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    return file_name

# Create the model
model = Sequential()

model.add(Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(48,48,1)))
model.add(Conv2D(64, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.25))

model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Conv2D(128, kernel_size=(3, 3), activation='relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.25))

model.add(Flatten())
model.add(Dense(1024, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(7, activation='softmax'))

model.load_weights('model.h5')

# prevents openCL usage and unnecessary logging messages
cv2.ocl.setUseOpenCL(False)

# dictionary which assigns each label an emotion (alphabetical order)
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful", 3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}

# User Class
class User(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    fname=db.Column(db.String(255), nullable=False)
    lname=db.Column(db.String(255), nullable=False)
    email=db.Column(db.String(255), nullable=False)
    username=db.Column(db.String(255), nullable=False)
    edu=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)
    status=db.Column(db.Integer,default=0, nullable=False)

    def __repr__(self):
        return f'User("{self.id}","{self.fname}","{self.lname}","{self.email}","{self.edu}","{self.username}","{self.status}")'

# create admin Class
class Admin(db.Model):
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(255), nullable=False)
    password=db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'Admin("{self.username}","{self.id}")'

# create table
with app.app_context():
    db.create_all()

# insert admin data one time only one time insert this data
# latter will check the condition
    # admin=Admin(username='arslan234',password=bcrypt.generate_password_hash('arslan234',10))
    # db.session.add(admin)
    # db.session.commit()

# main index 
@app.route('/')
def index():
    return render_template('index.html',title="")


# admin loign
@app.route('/admin/',methods=["POST","GET"])
def adminIndex():
    # chect the request is post or not
    if request.method == 'POST':
        # get the value of field
        username = request.form.get('username')
        password = request.form.get('password')
        # check the value is not empty
        if username=="" and password=="":
            flash('Please fill all the field','danger')
            return redirect('/admin/')
        else:
            # login admin by username 
            admins=Admin().query.filter_by(username=username).first()
            if admins and bcrypt.check_password_hash(admins.password,password):
                session['admin_id']=admins.id
                session['admin_name']=admins.username
                flash('Login Successfully','success')
                return redirect('/admin/dashboard')
            else:
                flash('Invalid Email and Password','danger')
                return redirect('/admin/')
    else:
        return render_template('admin/index.html',title="Admin Login")

# admin Dashboard
@app.route('/admin/dashboard')
def adminDashboard():
    if not session.get('admin_id'):
        return redirect('/admin/')
    totalUser=User.query.count()
    totalApprove=User.query.filter_by(status=1).count()
    NotTotalApprove=User.query.filter_by(status=0).count()
    return render_template('admin/dashboard.html',title="Admin Dashboard",totalUser=totalUser,totalApprove=totalApprove,NotTotalApprove=NotTotalApprove)

# admin get all user
@app.route('/admin/get-all-user', methods=["POST", "GET"])
def adminGetAllUser():
    if not session.get('admin_id'):
        return redirect('/admin/')
    if request.method == "POST":
        search = request.form.get('search')
        users = User.query.filter(User.username.like('%' + search + '%')).all()
        return render_template('admin/all-user.html', title='Approve User', users=users)
    else:
        users = User.query.all()
        return render_template('admin/all-user.html', title='Approve User', users=users)

@app.route('/admin/approve-user/<int:id>')
def adminApprove(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    user = User.query.get(id)
    if user:
        user.status = 1
        db.session.commit()
        flash('User Approved Successfully', 'success')
    else:
        flash('User not found', 'error')
    return redirect('/admin/get-all-user')

@app.route('/admin/update-user/<int:id>', methods=["GET", "POST"])
def adminUpdateUser(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    user = User.query.get(id)
    if user:
        if request.method == "POST":
            user.fname = request.form.get('fname')
            user.lname = request.form.get('lname')
            user.email = request.form.get('email')
            user.contact_no = request.form.get('contact_no')
            db.session.commit()
            flash('User Updated Successfully', 'success')
            return redirect('/admin/get-all-user')
        else:
            return render_template('admin/update-user.html', title='Update User', user=user)
    else:
        flash('User not found', 'error')
    return redirect('/admin/get-all-user')

@app.route('/admin/remove-user/<int:id>')
def adminRemoveUser(id):
    if not session.get('admin_id'):
        return redirect('/admin/')
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash('User Removed Successfully', 'success')
    else:
        flash('User not found', 'error')
    return redirect('/admin/get-all-user')


# change admin password
@app.route('/admin/change-admin-password',methods=["POST","GET"])
def adminChangePassword():
    admin=Admin.query.get(1)
    if request.method == 'POST':
        username=request.form.get('username')
        password=request.form.get('password')
        if username == "" or password=="":
            flash('Please fill the field','danger')
            return redirect('/admin/change-admin-password')
        else:
            Admin().query.filter_by(username=username).update(dict(password=bcrypt.generate_password_hash(password,10)))
            db.session.commit()
            flash('Admin Password update successfully','success')
            return redirect('/admin/change-admin-password')
    else:
        return render_template('admin/admin-change-password.html',title='Admin Change Password',admin=admin)

# admin logout
@app.route('/admin/logout')
def adminLogout():
    if not session.get('admin_id'):
        return redirect('/admin/')
    if session.get('admin_id'):
        session['admin_id']=None
        session['admin_name']=None
        return redirect('/')
# -------------------------user area----------------------------


# User login
@app.route('/user/',methods=["POST","GET"])
def userIndex():
    if  session.get('user_id'):
        return redirect('/user/dashboard')
    if request.method=="POST":
        # get the name of the field
        username=request.form.get('username')
        password=request.form.get('password')
        # check user exist in this email or not
        users=User().query.filter_by(username=username).first()
        if users and bcrypt.check_password_hash(users.password,password):
            # check the admin approve your account are not
            is_approve=User.query.filter_by(id=users.id).first()
            # first return the is_approve:
            if is_approve.status == 0:
                flash('Your Account is not approved by Admin','danger')
                return redirect('/user/')
            else:
                session['user_id']=users.id
                session['username']=users.username
                flash('Login Successfully','success')
                return redirect('/user/dashboard')
        else:
            flash('Invalid Email and Password','danger')
            return redirect('/user/')
    else:
        return render_template('user/index.html',title="User Login")

# User Register
@app.route('/user/signup',methods=['POST','GET'])
def userSignup():
    if  session.get('user_id'):
        return redirect('/user/dashboard')
    if request.method=='POST':
        # get all input field name
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        username=request.form.get('username')
        edu=request.form.get('edu')
        password=request.form.get('password')
        # check all the field is filled are not
        if fname =="" or lname=="" or email=="" or password=="" or username=="" or edu=="":
            flash('Please fill all the field','danger')
            return redirect('/user/signup')
        else:
            is_username=User().query.filter_by(username=username).first()
            if is_username:
                flash('Username already Exist, Try another','danger')
                return redirect('/user/signup')
            else:
                hash_password=bcrypt.generate_password_hash(password,10)
                user=User(fname=fname,lname=lname,email=email,password=hash_password,edu=edu,username=username)
                db.session.add(user)
                db.session.commit()
                flash('Account Create Successfully, Admin Will approve your account shortly..! ','success')
                return redirect('/user/')
    else:
        return render_template('user/signup.html',title="User Signup")

def read_emotions_from_csv(username):
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    file_name = os.path.join("Emotions", f"emotions_{today_date}.csv")

    # Read the CSV file and filter rows based on the username
    df = pd.read_csv(file_name)
    emotions = df[df['Username'] == username][['Time', 'Emotion']].values.tolist()

    return emotions

# user dashboard
@app.route('/user/dashboard')
def userDashboard():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id = session.get('user_id')
    users = User().query.filter_by(id=id).first()
    username = users.username

    # Get the emotions for the current user
    emotions = read_emotions_from_csv(username)

    return render_template('user/dashboard.html', title="User Dashboard", users=users, emotions=emotions)


@app.route('/user/detect')
def userDetect():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id=session.get('user_id')
    users=User().query.filter_by(id=id).first()
    return render_template('user/detect.html',title="Detect Emotion")

# user logout
@app.route('/user/logout')
def userLogout():
    if not session.get('user_id'):
        return redirect('/user/')

    if session.get('user_id'):
        session['user_id'] = None
        session['username'] = None
        return redirect('/user/')

@app.route('/user/change-password',methods=["POST","GET"])
def userChangePassword():
    if not session.get('user_id'):
        return redirect('/user/')
    if request.method == 'POST':
        email=request.form.get('email')
        password=request.form.get('password')
        if email == "" or password == "":
            flash('Please fill the field','danger')
            return redirect('/user/change-password')
        else:
            users=User.query.filter_by(email=email).first()
            if users:
               hash_password=bcrypt.generate_password_hash(password,10)
               User.query.filter_by(email=email).update(dict(password=hash_password))
               db.session.commit()
               flash('Password Change Successfully','success')
               return redirect('/user/change-password')
            else:
                flash('Invalid Email','danger')
                return redirect('/user/change-password')

    else:
        return render_template('user/change-password.html',title="Change Password")

# user update profile
@app.route('/user/update-profile', methods=["POST","GET"])
def userUpdateProfile():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id=session.get('user_id')
    users=User.query.get(id)
    if request.method == 'POST':
        # get all input field name
        fname=request.form.get('fname')
        lname=request.form.get('lname')
        email=request.form.get('email')
        username=request.form.get('username')
        edu=request.form.get('edu')
        if fname =="" or lname=="" or email=="" or username=="" or edu=="":
            flash('Please fill all the field','danger')
            return redirect('/user/update-profile')
        else:
            session['username']=None
            User.query.filter_by(id=id).update(dict(fname=fname,lname=lname,email=email,edu=edu,username=username))
            db.session.commit()
            session['username']=username
            flash('Profile update Successfully','success')
            return redirect('/user/dashboard')
    else:
        return render_template('user/update-profile.html',title="Update Profile",users=users)
    
# def gen_frames(username):  
#     while True:
#         success, frame = camera.read()  # read the camera frame
#         if not success:
#             break
#         else:
#             facecasc = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
#             gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#             faces = facecasc.detectMultiScale(gray,scaleFactor=1.3, minNeighbors=5)

#             for (x, y, w, h) in faces:
#                 cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)
#                 roi_gray = gray[y:y + h, x:x + w]
#                 cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
#                 prediction = model.predict(cropped_img)
#                 maxindex = int(np.argmax(prediction))
#                 emotion = emotion_dict[maxindex]
#                 cv2.putText(frame, emotion_dict[maxindex], (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                
#                 # Append the detected emotion and timestamp to the daily CSV file
#                 file_name = create_csv_file()
#                 with open(file_name, 'a', newline='') as csvfile:
#                     writer = csv.DictWriter(csvfile, fieldnames=['Time', 'Username', 'Emotion'])
#                     writer.writerow({'Time': datetime.datetime.now().strftime('%H:%M:%S'), 'Username': username, 'Emotion': emotion})
                    
#                 break


def gen_frames(username):
    # Read the camera frame once outside the loop
    success, frame = camera.read()
    if not success:
        return

    facecasc = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = facecasc.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    emotions = []  # To store all detected emotions in the frame

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)
        roi_gray = gray[y:y + h, x:x + w]
        cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
        prediction = model.predict(cropped_img)
        maxindex = int(np.argmax(prediction))
        emotion = emotion_dict[maxindex]
        cv2.putText(frame, emotion_dict[maxindex], (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        emotions.append(emotion)  # Store the emotion in the list

    # Append the detected emotions and timestamp to the daily CSV file
    file_name = create_csv_file()
    with open(file_name, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['Time', 'Username', 'Emotion'])
        for emotion in emotions:
            writer.writerow({'Time': datetime.datetime.now().strftime('%H:%M:%S'), 'Username': username, 'Emotion': emotion})
        csvfile.close()

    # Start the loop to continue real-time emotion detection
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            break
        else:
            facecasc = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = facecasc.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

            emotions = []  # Reset emotions list for each frame

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (255, 0, 0), 2)
                roi_gray = gray[y:y + h, x:x + w]
                cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray, (48, 48)), -1), 0)
                prediction = model.predict(cropped_img)
                maxindex = int(np.argmax(prediction))
                emotion = emotion_dict[maxindex]
                cv2.putText(frame, emotion_dict[maxindex], (x+20, y-60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

                emotions.append(emotion)  # Store the emotion in the list

            # Append the detected emotions and timestamp to the daily CSV file (optional)
            # file_name = create_csv_file()
            # with open(file_name, 'a', newline='') as csvfile:
            #     writer = csv.DictWriter(csvfile, fieldnames=['Time', 'Username', 'Emotion'])
            #     for emotion in emotions:
            #         writer.writerow({'Time': datetime.datetime.now().strftime('%H:%M:%S'), 'Username': username, 'Emotion': emotion})
            #     csvfile.close()

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    if not session.get('user_id'):
        return redirect('/user/')
    if session.get('user_id'):
        id = session.get('user_id')
        users = User().query.filter_by(id=id).first()
        username = users.username  # Get the username of the logged-in user
        return Response(gen_frames(username), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__=="__main__":
    app.run(debug=True)