import cv2
import os
import base64
import numpy as np
import gc
from deepface import DeepFace

from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# Configure TensorFlow to use less memory
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'

app = Flask(__name__)

# Configure TensorFlow to limit memory growth (must be done after import)
try:
    import tensorflow as tf
    # Limit GPU memory growth (if GPU available)
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError as e:
            print(f"GPU memory config error: {e}")
except Exception as e:
    print(f"TensorFlow config warning: {e}")

# Database configuration: prefer DATABASE_URL, fallback to local sqlite
# Railway provides DATABASE_URL with postgres://, but SQLAlchemy needs postgresql://
# Using pg8000 (pure Python) instead of psycopg2 to avoid segmentation faults in Nix environment
database_url = os.environ.get('DATABASE_URL') or 'sqlite:///face_recognition.db'
if database_url.startswith('postgres://'):
    # Convert Railway's postgres:// to postgresql+pg8000://
    database_url = database_url.replace('postgres://', 'postgresql+pg8000://', 1)
elif database_url.startswith('postgresql://'):
    # Convert postgresql:// to postgresql+pg8000:// if not already using a driver
    if '+pg8000' not in database_url and '+' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+pg8000://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Configure connection pool to prevent segmentation faults
# pg8000 has different connection arguments than psycopg2
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Verify connections before using
    'pool_recycle': 300,    # Recycle connections after 5 minutes
    'pool_size': 5,         # Connection pool size
    'max_overflow': 10      # Maximum overflow connections
}
db = SQLAlchemy(app)


captured_faces_dir = 'captured_students_faces'
recognition_dir = 'recognition_image'
os.makedirs(captured_faces_dir, exist_ok=True)
os.makedirs(recognition_dir, exist_ok = True)

# Loads up HaarCasacdeClassifer objects for face recognition 
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml') 


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    mat_number = db.Column(db.String(255), nullable=False, unique=True)
    image_path = db.Column(db.String(1024), nullable=False)

# Initialize database tables on startup (after models are defined)
with app.app_context():
    try:
        db.create_all()
        print("Database tables created/verified successfully")
    except Exception as e:
        print(f"ERROR: Could not create database tables: {e}")
        import traceback
        traceback.print_exc()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/init-db')
def init_db():
    """Manually initialize database tables (useful for troubleshooting)"""
    try:
        with app.app_context():
            db.create_all()
            return "Database tables created/verified successfully!", 200
    except Exception as e:
        import traceback
        error_msg = f"Error creating tables: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg, 500


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
        
        # Validate that a face is detected in the image before saving
        try:
            # Use OpenCV to detect face before saving
            gray = cv2.cvtColor(student_img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return render_template('error.html', message="No face detected in the image. Please ensure your face is clearly visible and try again."), 400
            
            # Save image temporarily for DeepFace validation
            temp_path = os.path.join(captured_faces_dir, f"temp_{mat_no}.jpg")
            cv2.imwrite(temp_path, student_img)
            
            # Also validate with DeepFace (lightweight check)
            try:
                DeepFace.extract_faces(img_path=temp_path, enforce_detection=True, detector_backend='opencv')
                # If successful, rename to final path
                if os.path.exists(temp_path):
                    if os.path.exists(student_image_path):
                        os.remove(student_image_path)
                    os.rename(temp_path, student_image_path)
                    # Verify the file was saved correctly
                    if not os.path.exists(student_image_path) or os.path.getsize(student_image_path) == 0:
                        print(f"Warning: Image file not saved correctly: {student_image_path}")
                        return render_template('error.html', message="Failed to save image. Please try again."), 500
                    print(f"Successfully saved student image: {student_image_path} ({os.path.getsize(student_image_path)} bytes)")
            except Exception as e:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                print(f"DeepFace validation failed: {e}")
                return render_template('error.html', message="Face could not be properly detected. Please ensure your face is clearly visible and try again."), 400
        except Exception as e:
            print(f"Face validation error: {e}")
            return render_template('error.html', message="Error processing image. Please try again."), 500

        # Save the captured face image path as well as other details, to the database
        try:
            student = Student(name=name, mat_number=mat_no, image_path=student_image_path)
            db.session.add(student)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            print(f"Integrity error: {e}")
            return render_template('error.html', message="Student with this matriculation number already exists."), 400
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
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
                # Check if there are any registered students (images in the directory)
                if not os.path.exists(captured_faces_dir):
                    os.makedirs(captured_faces_dir, exist_ok=True)
                    return render_template('error.html', message="No students registered yet. Please register students first."), 404
                
                # Get list of image files in the directory
                try:
                    image_files = [f for f in os.listdir(captured_faces_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    # Filter out temp files
                    image_files = [f for f in image_files if not f.startswith('temp_')]
                except Exception as e:
                    print(f"Error listing directory: {e}")
                    image_files = []
                
                if len(image_files) == 0:
                    # Also check database to see if students are registered
                    student_count = Student.query.count()
                    if student_count == 0:
                        return render_template('error.html', message="No students registered yet. Please register students first."), 404
                    else:
                        return render_template('error.html', message=f"Found {student_count} students in database but no images. Please re-register students."), 404
                
                print(f"Found {len(image_files)} registered student images: {image_files[:5]}")  # Log first 5 files
                
                # Verify images actually exist and are readable
                valid_images = []
                for img_file in image_files:
                    img_path = os.path.join(captured_faces_dir, img_file)
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                        valid_images.append(img_path)
                
                if len(valid_images) == 0:
                    return render_template('error.html', message="Registered images not found. Please re-register students."), 404
                
                print(f"Verified {len(valid_images)} valid image files")
                
                # Use absolute paths for DeepFace
                abs_captured_faces_dir = os.path.abspath(captured_faces_dir)
                abs_captured_image_path = os.path.abspath(captured_image_path)
                
                # Force garbage collection before heavy operation
                gc.collect()
                
                # Use lighter settings to reduce memory usage
                # enforce_detection=False allows processing even if face detection is uncertain
                # detector_backend='opencv' is faster and uses less memory than default
                # distance_metric='cosine' is lighter than 'euclidean'
                result = DeepFace.find(
                    img_path=abs_captured_image_path, 
                    db_path=abs_captured_faces_dir,
                    enforce_detection=False,  # Don't fail if face detection is uncertain
                    detector_backend='opencv',  # Use OpenCV (lighter than default)
                    model_name='Facenet',  # Facenet is lighter than VGG-Face
                    distance_metric='cosine',  # Cosine is lighter than euclidean
                    silent=True  # Reduce logging
                )
                
                # Clean up memory immediately after DeepFace operation
                gc.collect()
                
                if isinstance(result, list) and len(result) > 0:
                    result_df = result[0]
                    if not result_df.empty:
                        # Check if similarity is high enough (distance threshold)
                        # Lower distance = higher similarity
                        # Typical threshold: distance < 0.4 means good match
                        distance_threshold = 0.4  # Adjust as needed (lower = stricter)
                        if 'distance' in result_df.columns:
                            if result_df.iloc[0]['distance'] < distance_threshold:
                                recognized_file = result_df.iloc[0]['identity']
                                recognized_mat_number = os.path.basename(recognized_file).split('.')[0]
                        else:
                            # If no distance column, use first result (DeepFace may return different format)
                            recognized_file = result_df.iloc[0]['identity']
                            recognized_mat_number = os.path.basename(recognized_file).split('.')[0]
                
                # Clean up result to free memory
                del result
                gc.collect()
                
                # Clear TensorFlow session to free memory
                try:
                    import tensorflow as tf
                    tf.keras.backend.clear_session()
                except:
                    pass
                gc.collect()
            except MemoryError as e:
                print(f"Memory error during face recognition: {e}")
                gc.collect()
                return render_template('error.html', message="System is busy. Please try again in a moment."), 503
            except ValueError as e:
                # Handle DeepFace-specific errors
                error_msg = str(e)
                if "No item found" in error_msg:
                    print(f"DeepFace error: {error_msg}")
                    print(f"Directory: {captured_faces_dir}")
                    print(f"Absolute directory: {os.path.abspath(captured_faces_dir)}")
                    print(f"Directory exists: {os.path.exists(captured_faces_dir)}")
                    if os.path.exists(captured_faces_dir):
                        try:
                            files = os.listdir(captured_faces_dir)
                            print(f"Files in directory: {files}")
                        except:
                            pass
                    return render_template('error.html', message="No registered students found. Please register students first."), 404
                else:
                    print(f"Face recognition error: {e}")
                    import traceback
                    traceback.print_exc()
                    gc.collect()
                    return render_template('error.html', message="Face recognition failed. Please try again."), 500
            except Exception as e:
                print(f"Face recognition error: {e}")
                import traceback
                traceback.print_exc()
                gc.collect()
                return render_template('error.html', message="Face recognition failed. Please try again."), 500

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
