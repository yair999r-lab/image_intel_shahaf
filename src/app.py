from flask import Flask, request, render_template
import os

from extractor import extract_all
from timeline import generate_camera_dashboard
from map_view import create_map
from analyze import analyze

app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    # טעינת עמוד הבית עם טופס החיפוש
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_folder():
    user_folder_path = request.form.get('folder_input_name')

    # בדיקה 1: האם הנתיב תקין?
    if not os.path.isdir(user_folder_path):
        return render_template('error.html', error_msg="הנתיב שהוזן שגוי או שהתיקייה לא קיימת במחשב.")

    # חילוץ הנתונים מכל התמונות בתיקייה
    images_data = extract_all(user_folder_path)

    # בדיקה 2: האם יש תמונות בתיקייה?
    if len(images_data) == 0:
        return render_template('error.html', error_msg="הסריקה הסתיימה: לא נמצאו קבצי תמונות נתמכים בתיקייה זו.")

    # בדיקה 3: האם יש רק תמונה אחת?
    if len(images_data) == 1:
        return render_template('single_image.html', data=images_data[0])

    # מצב רגיל: יש הרבה תמונות, מכינים את הדשבורד המלא
    else:
        # הפעלת מודול הניתוח (Analyzer)
        analysis_results = analyze(images_data)

        # הפעלת מודול המפה (מקבלים tuple של זמינות וקוד HTML)
        map_available, map_html = create_map(images_data)

        # הפעלת מודול ציר הזמן (מקבלים tuple של זמינות וקוד HTML)
        timeline_available, timeline_html = generate_camera_dashboard(images_data)

        # שליחת כל הנתונים לעמוד הדשבורד המרכזי
        return render_template('dashboard.html',
                               timeline_available=timeline_available,
                               timeline_html=timeline_html,
                               map_available=map_available,
                               map_html=map_html,
                               analysis_results=analysis_results)


if __name__ == '__main__':
    app.run(debug=True)