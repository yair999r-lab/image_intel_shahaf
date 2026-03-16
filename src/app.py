from flask import Flask, request, render_template
import os
import shutil
import uuid
from werkzeug.utils import secure_filename

from extractor import extract_all
from timeline import generate_camera_dashboard
from map_view import create_map
from analyze import analyze

app = Flask(__name__)

# הגדרת תיקיית בסיס זמנית להעלאת התמונות
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def home():
    # טעינת עמוד הבית עם טופס החיפוש
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_folder():
    # 1. קליטת הקבצים שהמשתמש העלה דרך הדפדפן
    uploaded_files = request.files.getlist('files')

    if not uploaded_files or uploaded_files[0].filename == '':
        return render_template('error.html', error_msg="לא נבחרו קבצים להעלאה.")

    # 2. יצירת תיקייה זמנית ייחודית לסשן הנוכחי (כדי למנוע התנגשויות בין משתמשים)
    session_id = str(uuid.uuid4())
    temp_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # 3. שמירת כל התמונות לתוך התיקייה הזמנית בשרת
        for file in uploaded_files:
            if file and file.filename:
                # secure_filename מגן על השרת מנתיבים זדוניים
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)

        # 4. חילוץ הנתונים מהתיקייה הזמנית (בדיוק כמו שהיה קודם!)
        images_data = extract_all(temp_dir)

        # בדיקה 2: האם יש תמונות בתיקייה?
        if len(images_data) == 0:
            return render_template('error.html', error_msg="הסריקה הסתיימה: לא נמצאו קבצי תמונות נתמכים בתיקייה זו.")

        # בדיקה 3: האם יש רק תמונה אחת?
        if len(images_data) == 1:
            return render_template('single_image.html', data=images_data[0])

        # מצב רגיל: יש הרבה תמונות, מכינים את הדשבורד המלא
        else:
            analysis_results = analyze(images_data)
            map_available, map_html = create_map(images_data)
            timeline_available, timeline_html = generate_camera_dashboard(images_data)

            return render_template('dashboard.html',
                                   timeline_available=timeline_available,
                                   timeline_html=timeline_html,
                                   map_available=map_available,
                                   map_html=map_html,
                                   analysis_results=analysis_results)

    finally:
        # 5. ניקיון אוטומטי! הבלוק הזה ירוץ תמיד, וימחק את התמונות מהשרת בסיום הניתוח
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == '__main__':
    app.run(debug=True)