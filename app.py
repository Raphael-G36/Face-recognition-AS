import cv2
import sqlite3
import os
import base64
import numpy as np
from deepface import DeepFace


from flask import Flask, request, render_template, redirect
app = Flask(__name__)

captured_faces_dir = 'captured_students_faces'
recognition_dir = 'recognition_image'
os.makedirs(captured_faces_dir, exist_ok=True)
os.makedirs(recognition_dir, exist_ok = True)

# Loads up HaarCasacdeClassifer objects for face recognition 
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') 

@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error.html'), 500

@app.route('/register', methods=['GET','POST'])
def open_camera():
    if request.method == 'POST':
        name = request.form.get('name')
        mat_no = request.form.get('mat_no')
        image_b64 = request.form.get('imageData')
        
        image = image_b64.split(",")[1]  
        
        image_bytes = base64.b64decode(image)
        np_array = np.frombuffer(image_bytes, np.uint8)
        student_img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        student_image_path = os.path.join(captured_faces_dir, f"{mat_no}.jpg")
        
        cv2.imwrite(student_image_path, student_img)

        # Save the captured face image path as well as other details, to the database
        db_connection = sqlite3.connect('face_recognition.db')
        cursor = db_connection.cursor()
        cursor.execute('''
                        INSERT INTO students( name, mat_number, image_path)
                        Values(?,?,?)
                        ''',(name, mat_no, student_image_path))
        db_connection.commit()
        db_connection.close()
        return redirect('/')
    return render_template('register.html')

@app.route('/mark', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        course = request.form.get('course_code')
        image_b64 = request.form.get('imageData')
        
        image = image_b64.split(",")[1]  
        
        image_bytes = base64.b64decode(image)
        np_array = np.frombuffer(image_bytes, np.uint8)
        recognition_img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        
        captured_image_path = os.path.join(recognition_dir, "captured.jpg")
        
        cv2.imwrite(captured_image_path, recognition_img)
        
        if image_b64:
            try:
                result = DeepFace.find(img_path=captured_image_path, db_path=captured_faces_dir)
                if isinstance(result, list)and len(result)>0:
                    result_df = result[0]
                    if not result_df.empty:
                        recognized_file = result_df.iloc[0]['identity']
                        recognized_mat_number = os.path.basename(recognized_file).split('.')[0]
            
            except Exception as e:
                return render_template('error.html'), 500
            
        db_connection = sqlite3.connect('face_recognition.db')
        cursor = db_connection.cursor()
        cursor.execute('''
                       SELECT name FROM students WHERE mat_number = ?
                       ''', (recognized_mat_number,))
        result = cursor.fetchone()
        db_connection.commit()
        db_connection.close()
        
        return render_template('cam.html', name = result[0], mat_number = recognized_mat_number, course = course )
    return render_template('recognize.html')


if __name__ == '__main__':
    db_connection = sqlite3.connect('face_recognition.db')
    cursor = db_connection.cursor()
    cursor.execute(''' 
                    CREATE TABLE IF NOT EXISTS students(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        mat_number TEXT NOT NULL,
                        image_path TEXT NOT NULL)''')
    
    db_connection.commit()
    db_connection.close()
    app.run(host="0.0.0.0", port=5001, debug=False, ssl_context=('cert.pem', 'key.pem'))
