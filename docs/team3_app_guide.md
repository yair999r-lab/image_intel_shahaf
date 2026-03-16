# רביעייה 3 - App: מדריך מפורט

## התפקיד שלכם

אתם אחראים על החלק שהמשתמש רואה - ממשק הווב והדו"ח הסופי. אתם מחברים את כל החלקים למוצר אחד עובד.

## חלוקת עבודה

| זוג | מודול | מה עושים |
|-----|-------|----------|
| A | app.py | Flask server - routes, upload, חיבור כל המודולים |
| B | report.py | הרכבת דו"ח HTML יפה מכל החלקים |

---

## זוג A - app.py

### המטרה
לבנות שרת Flask שמאפשר למשתמש לבחור תיקיית תמונות ולקבל דו"ח.

### Routes שצריך לבנות
```python
from flask import Flask, render_template, request
import os

app = Flask(__name__)

@app.route('/')
def index():
    """דף הבית - טופס לבחירת תיקייה"""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze_images():
    """מקבל נתיב תיקייה, מריץ את כל המודולים, מחזיר דו"ח"""
    folder_path = request.form.get('folder_path')
    
    if not folder_path or not os.path.isdir(folder_path):
        return "תיקייה לא נמצאה", 400
    
    # שלב 1: שליפת נתונים
    from extractor import extract_all
    images_data = extract_all(folder_path)
    
    # שלב 2: יצירת מפה
    from map_view import create_map
    map_html = create_map(images_data)
    
    # שלב 3: ציר זמן
    from timeline import create_timeline
    timeline_html = create_timeline(images_data)
    
    # שלב 4: ניתוח
    from analyzer import analyze
    analysis = analyze(images_data)
    
    # שלב 5: הרכבת דו"ח
    from report import create_report
    report_html = create_report(images_data, map_html, timeline_html, analysis)
    
    return report_html

if __name__ == '__main__':
    app.run(debug=True)
```

### טיפ קריטי
**אל תחכו לצוותים האחרים!** בשלב ראשון, צרו פונקציות דמה:
```python
def fake_extract_all(folder):
    return [{"filename": "test.jpg", "has_gps": True, "latitude": 32.0, "longitude": 34.7, ...}]

def fake_create_map(data):
    return "<h2>Map placeholder</h2>"
```

כשהמודולים האמיתיים מוכנים, פשוט החליפו את ה-import.

### דף הבית - templates/index.html
```html
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Image Intel</title>
    <style>
        body { font-family: Arial; max-width: 600px; margin: 50px auto; text-align: center; }
        input, button { font-size: 18px; padding: 10px; margin: 10px; }
        button { background: #2E86AB; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>Image Intel</h1>
    <p>מערכת חילוץ מודיעין מתמונות</p>
    <form action="/analyze" method="POST">
        <input type="text" name="folder_path" placeholder="נתיב לתיקיית תמונות" size="40">
        <br>
        <button type="submit">נתח תמונות</button>
    </form>
</body>
</html>
```

### סדר עבודה מומלץ
1. הקימו Flask app בסיסי עם דף בית
2. צרו route של `/analyze` עם פונקציות דמה
3. וודאו שה-flow עובד מקצה לקצה עם דמה
4. החליפו לפונקציות אמיתיות כשהן מוכנות
5. טפלו בשגיאות (תיקייה לא קיימת, אין תמונות)

---

## זוג B - report.py

### המטרה
לבנות מודול שמרכיב את כל החלקים (מפה, ציר זמן, ניתוח) לדו"ח HTML אחד יפה.

### הפלט שלכם
string של HTML מלא - דף שנפתח בדפדפן ומציג את כל המידע.

### מבנה הדו"ח המומלץ
```
┌─────────────────────────────┐
│  Image Intel Report         │
│  כותרת + תאריך יצירה       │
├─────────────────────────────┤
│  סיכום                      │
│  X תמונות | Y עם GPS | Z מכשירים │
├─────────────────────────────┤
│  תובנות מרכזיות             │
│  • תובנה 1                  │
│  • תובנה 2                  │
├─────────────────────────────┤
│  מפה אינטראקטיבית           │
│  (HTML מ-map_view)          │
├─────────────────────────────┤
│  ציר זמן                    │
│  (HTML מ-timeline)          │
├─────────────────────────────┤
│  רשימת מכשירים              │
│  פירוט לפי מצלמה            │
└─────────────────────────────┘
```

### דוגמה בסיסית
```python
from datetime import datetime

def create_report(images_data, map_html, timeline_html, analysis):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    insights_html = ""
    for insight in analysis.get("insights", []):
        insights_html += f"<li>{insight}</li>"
    
    cameras_html = ""
    for cam in analysis.get("unique_cameras", []):
        cameras_html += f"<span class='badge'>{cam}</span> "
    
    html = f"""
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Image Intel Report</title>
        <style>
            body {{ font-family: Arial; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
            .header {{ background: #1B4F72; color: white; padding: 30px; border-radius: 10px; text-align: center; }}
            .section {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .stats {{ display: flex; gap: 20px; justify-content: center; }}
            .stat-card {{ background: #E8F4FD; padding: 15px 25px; border-radius: 8px; text-align: center; }}
            .stat-number {{ font-size: 2em; font-weight: bold; color: #1B4F72; }}
            .badge {{ background: #2E86AB; color: white; padding: 5px 10px; border-radius: 15px; margin: 3px; display: inline-block; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Image Intel Report</h1>
            <p>נוצר ב-{now}</p>
        </div>
        
        <div class="section">
            <h2>סיכום</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{analysis.get('total_images', 0)}</div>
                    <div>תמונות</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{analysis.get('images_with_gps', 0)}</div>
                    <div>עם GPS</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(analysis.get('unique_cameras', []))}</div>
                    <div>מכשירים</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>תובנות מרכזיות</h2>
            <ul>{insights_html}</ul>
        </div>
        
        <div class="section">
            <h2>מפה</h2>
            {map_html}
        </div>
        
        <div class="section">
            <h2>ציר זמן</h2>
            {timeline_html}
        </div>
        
        <div class="section">
            <h2>מכשירים</h2>
            {cameras_html}
        </div>
        
        <div style="text-align:center; color:#888; margin-top:30px;">
            Image Intel | האקתון 2025
        </div>
    </body>
    </html>
    """
    return html
```

### סדר עבודה מומלץ
1. בנו template HTML בסיסי עם placeholder
2. הכניסו נתונים מזויפים לבדיקה
3. שפרו את העיצוב
4. חברו למקורות אמיתיים
5. בדקו שהכל נראה טוב עם נתונים אמיתיים

---

## עבודה עם Git

**זוג A:**
```bash
git checkout -b feature/app
```

**זוג B:**
```bash
git checkout -b feature/report
```

## צ'קליסט סיום

### זוג A:
- [ ] Flask app רץ בלי שגיאות
- [ ] דף הבית מוצג
- [ ] route `/analyze` עובד עם נתיב תיקייה
- [ ] טיפול בשגיאות (תיקייה לא קיימת)
- [ ] כל המודולים מחוברים
- [ ] PR נפתח ונבדק

### זוג B:
- [ ] דו"ח HTML מציג סיכום, מפה, ציר זמן, תובנות
- [ ] עיצוב נקי וקריא
- [ ] `create_report` מחזיר HTML string מלא
- [ ] עובד עם נתונים מזויפים
- [ ] עובד עם נתונים אמיתיים
- [ ] PR נפתח ונבדק
