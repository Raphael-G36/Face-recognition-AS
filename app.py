import cv2
import os
import base64
import numpy as np
from deepface import DeepFace

from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

# Database configuration: prefer DATABASE_URL, fallback to local sqlite
# Railway provides DATABASE_URL with postgres://, but SQLAlchemy needs postgresql://
database_url = os.environ.get('DATABASE_URL') or 'sqlite:///face_recognition.db'
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configure connection pool to prevent segmentation faults
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Verify connections before using
    'pool_recycle': 300,    # Recycle connections after 5 minutes
    'pool_size': 5,         # Connection pool size
    'max_overflow': 10,     # Maximum overflow connections
    'connect_args': {
        'connect_timeout': 10,
        'application_name': 'uibras_app'
    }
}
db = SQLAlchemy(app)


captured_faces_dir = 'captured_students_faces'
recognition_dir = 'recognition_image'
os.makedirs(captured_faces_dir, exist_ok=True)
os.makedirs(recognition_dir, exist_ok = True)

# Initialize database tables on startup
with app.app_context():
    try:
        db.create_all()
        print("Database tables created/verified successfully")
    except Exception as e:
        print(f"Warning: Could not create database tables: {e}")

# Loads up HaarCasacdeClassifer objects for face recognition 
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') 


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    mat_number = db.Column(db.String(255), nullable=False, unique=True)
    image_path = db.Column(db.String(1024), nullable=False)

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
        try:
            student = Student(name=name, mat_number=mat_no, image_path=student_image_path)
            db.session.add(student)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            print(f"Integrity error: {e}")
            # Student with this mat_number already exists
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
            # Return error page or redirect with error message
            return render_template('error.html', message="Failed to save student. Please try again."), 500
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
        
        recognized_mat_number = None
        if image_b64:
            try:
                result = DeepFace.find(img_path=captured_image_path, db_path=captured_faces_dir)
                if isinstance(result, list) and len(result) > 0:
                    result_df = result[0]
                    if not result_df.empty:
                        recognized_file = result_df.iloc[0]['identity']
                        recognized_mat_number = os.path.basename(recognized_file).split('.')[0]
            except Exception:
                return render_template('error.html'), 500

        if not recognized_mat_number:
            return render_template('error.html'), 404

        student = Student.query.filter_by(mat_number=recognized_mat_number).first()
        if not student:
            return render_template('error.html'), 404

        return render_template('cam.html', name=student.name, mat_number=recognized_mat_number, course=course)
    return render_template('recognize.html')


if __name__ == '__main__':
    # Ensure tables exist (works for SQLite and most SQL DBs)
    db.create_all()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)
