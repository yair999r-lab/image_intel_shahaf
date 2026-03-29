from flask import Flask, request, render_template, jsonify
import os
import shutil
import uuid
import threading
import hashlib  # *** התוספת שלך ליצירת טביעת אצבע ***
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from extractor import extract_all
from timeline import generate_camera_dashboard
from map_view import create_map
from analyze import analyze
from image_manager_natan import process_and_upload_image

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

session_cache = {}
upload_status_cache = {}


# === המשימה של נתן: פונקציית טביעת האצבע ===
def get_file_hash(filepath):
    """קורא את הקובץ ומייצר מזהה SHA-256 ייחודי לפני העלאה"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # קורא במנות של 4K כדי לא להקריס את הזיכרון
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def upload_to_cloud_async(session_id, temp_dir, images_data):
    """
    מנוע הענן של נתן - רץ ברקע:
    1. מייצר Hash.
    2. בודק כפילויות.
    3. מעלה ל-Cloudinary.
    4. מבצע 'תפוח לוהט' ומוחק את התמונה ספציפית מהשרת.
    """
    upload_status_cache[session_id] = {
        'total': len(images_data),
        'uploaded': 0,
        'status': 'uploading',
        'cloud_images': []
    }

    for data in images_data:
        file_path = os.path.join(temp_dir, data['filename'])

        if os.path.exists(file_path):
            try:
                # 1. טביעת אצבע (Hashing) מוקדמת לפני שנוגעים בענן!
                file_hash = get_file_hash(file_path)
                data['hash'] = file_hash

                # 2. מניעת כפילויות: כאן יאיר יחבר את שאילתת ה-DB שלו
                # existing_url = db.check_if_hash_exists(file_hash)
                existing_url = None  # כרגע מניחים שאין כפילות

                if existing_url:
                    # התמונה כבר בענן! חוסכים העלאה.
                    print(f"[{data['filename']}] Hash exists! Skipping Cloudinary upload.")
                    data['cloud_url'] = existing_url
                    upload_status_cache[session_id]['cloud_images'].append({
                        'filename': data['filename'],
                        'url': existing_url
                    })
                else:
                    # 3. תמונה חדשה: מעלים ל-Cloudinary
                    with open(file_path, "rb") as f:
                        file_storage = FileStorage(f, filename=data['filename'])
                        result = process_and_upload_image(file_storage)

                        if result and result.get('success'):
                            data['cloud_url'] = result['url']
                            upload_status_cache[session_id]['cloud_images'].append({
                                'filename': data['filename'],
                                'url': result['url']
                            })
                            print(f"[{data['filename']}] Uploaded successfully.")

            except Exception as e:
                print(f"Error in background upload for {data['filename']}: {e}")

            finally:
                # 4. שיטת 'התפוח הלוהט': מחיקה מיידית של הקובץ הבודד מהשרת של Render!
                # לא מחכים שכל הלולאה תסתיים!
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"[{data['filename']}] Hot Apple: File deleted from temp.")
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

        upload_status_cache[session_id]['uploaded'] += 1

    # ניקוי סופי של תיקיית המעטפת הריקה
    if os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
        except OSError:
            shutil.rmtree(temp_dir, ignore_errors=True)

    upload_status_cache[session_id]['status'] = 'complete'


@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_folder():
    uploaded_files = request.files.getlist('files')
    if not uploaded_files or uploaded_files[0].filename == '':
        return render_template('error.html', error_msg="לא נבחרו קבצים להעלאה.")

    session_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(temp_dir, exist_ok=True)

    # 1. שמירה מהירה לדיסק
    for file in uploaded_files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(temp_dir, filename))

    # 2. חילוץ מהיר של עובדות (EXIF)
    images_data = extract_all(temp_dir)

    if len(images_data) == 0:
        shutil.rmtree(temp_dir)
        return render_template('error.html', error_msg="לא נמצאו תמונות.")

    # 3. מפעילים את מנוע הענן של נתן בתהליך רקע
    bg_thread = threading.Thread(target=upload_to_cloud_async, args=(session_id, temp_dir, images_data))
    bg_thread.start()

    if len(images_data) == 1:
        return render_template('single_image.html', data=images_data[0])

    # 4. הכנת הנתונים לדשבורד
    analysis_results = analyze(images_data)
    session_cache[session_id] = {
        'images_data': images_data,
        'temp_dir': temp_dir
    }

    return render_template('dashboard.html', analysis_results=analysis_results, session_id=session_id)


# --- נתיבי API לממשק הלקוח ---

@app.route('/api/upload_status/<session_id>', methods=['GET'])
def api_upload_status(session_id):
    status = upload_status_cache.get(session_id, {'status': 'not_found'})
    return jsonify(status)


@app.route('/api/map/<session_id>', methods=['GET'])
def api_map(session_id):
    data = session_cache.get(session_id)
    if not data: return jsonify({'available': False})
    map_available, map_html = create_map(data['images_data'])
    return jsonify({'available': map_available, 'html': map_html})


@app.route('/api/timeline/<session_id>', methods=['GET'])
def api_timeline(session_id):
    data = session_cache.get(session_id)
    if not data: return jsonify({'available': False})
    timeline_available, timeline_html = generate_camera_dashboard(data['images_data'])
    return jsonify({'available': timeline_available, 'html': timeline_html})


@app.route('/api/raw_data/<session_id>', methods=['GET'])
def api_raw_data(session_id):
    data = session_cache.get(session_id)
    if not data: return jsonify({'available': False})
    return jsonify({'available': True, 'images_data': data['images_data']})


@app.route('/api/cleanup/<session_id>', methods=['POST'])
def api_cleanup(session_id):
    session_cache.pop(session_id, None)
    return jsonify({'status': 'cleaned'})


if __name__ == '__main__':
    app.run(debug=True)