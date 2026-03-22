from flask import Flask, request, render_template, jsonify
import os
import shutil
import uuid
from werkzeug.utils import secure_filename

# ייבוא ה"טבחים" שלנו - הקבצים האחרים שעושים את העבודה השחורה
from extractor import extract_all
from timeline import generate_camera_dashboard
from map_view import create_map
from analyze import analyze

app = Flask(__name__)

# הגדרת תיקיית בסיס זמנית להעלאת התמונות
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================
# זיכרון השרת (Cache) לטעינה אסינכרונית
# פה אנחנו שומרים את נתוני התמונות באופן זמני בין הבקשות של הדפדפן.
# המפתח (Key) יהיה מזהה ייחודי של המשתמש, והערך (Value) יהיה הנתונים שלו.
# ==========================================
session_cache = {}


@app.route('/', methods=['GET'])
def home():
    """טעינת עמוד הבית עם טופס העלאת התמונות"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_folder():
    """נקודת כניסה מהירה - מחזירה רק סיכום סטטיסטי ומיד טוענת את העמוד"""
    uploaded_files = request.files.getlist('files')

    if not uploaded_files or uploaded_files[0].filename == '':
        return render_template('error.html', error_msg="לא נבחרו קבצים להעלאה.")

    session_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(temp_dir, exist_ok=True)

    for file in uploaded_files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)

    images_data = extract_all(temp_dir)

    if len(images_data) == 0:
        shutil.rmtree(temp_dir)
        return render_template('error.html', error_msg="הסריקה הסתיימה: לא נמצאו קבצי תמונות נתמכים בתיקייה זו.")

    if len(images_data) == 1:
        shutil.rmtree(temp_dir)
        return render_template('single_image.html', data=images_data[0])

    else:
        # 1. מריצים אך ורק את הניתוח המהיר (ללא ציור מפה וגרפים בשלב זה)
        analysis_results = analyze(images_data)

        # 2. מאחסנים את הנתונים ב"מקרר" כדי שהדפדפן יוכל לבקש אותם עוד שנייה ברקע
        session_cache[session_id] = {
            'images_data': images_data,
            'temp_dir': temp_dir
        }

        # 3. מחזירים מיד את הדשבורד עם ה-session_id החדש!
        return render_template('dashboard.html',
                               analysis_results=analysis_results,
                               session_id=session_id)


# ==========================================
# נתיבי Microservices (API לטעינת רקע / AJAX)
# ==========================================

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
    """
    נתיב חדש עבור מערכת הסינון החכמה.
    מחזיר את הנתונים הגולמיים ל-JS לפני שניקוי השרת מתבצע.
    """
    data = session_cache.get(session_id)
    if not data: return jsonify({'available': False})

    return jsonify({'available': True, 'images_data': data['images_data']})


@app.route('/api/cleanup/<session_id>', methods=['POST'])
def api_cleanup(session_id):
    """פקודת הניקיון שמופעלת רק אחרי שהמפה, הגרף והנתונים הגולמיים נטענו בהצלחה אצל המשתמש"""
    data = session_cache.pop(session_id, None)
    if data and os.path.exists(data['temp_dir']):
        shutil.rmtree(data['temp_dir'])
    return jsonify({'status': 'cleaned'})


if __name__ == '__main__':
    app.run(debug=True)