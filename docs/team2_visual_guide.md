# רביעייה 2 - Visual: מדריך מפורט

## התפקיד שלכם

אתם אחראים על הצגה ויזואלית של הנתונים וחילוץ תובנות. אתם הופכים רשימת מספרים לסיפור מודיעיני.

## חלוקת עבודה

| זוג | מודול | מה עושים |
|-----|-------|----------|
| A | timeline.py | ציר זמן ויזואלי של הצילומים |
| B | analyzer.py | זיהוי דפוסים, קשרים ותובנות |

---

## זוג A - timeline.py

### המטרה
לבנות מודול שמקבל רשימת מילונים ומייצר ציר זמן ויזואלי בHTML.

### הפלט שלכם
string של HTML שמציג ציר זמן כרונולוגי של כל התמונות.

### אפשרויות למימוש
1. **HTML/CSS טהור** - בנו ציר זמן עם div-ים וCSS
2. **matplotlib** - צרו גרף זמן ושמרו כתמונה, הטמיעו ב-HTML
3. **Plotly** - גרף אינטראקטיבי (יותר מתקדם אבל יותר יפה)

### טיפ קריטי
**אל תחכו לצוות 1!** עבדו עם נתונים מזויפים (ראו `docs/api_contract.md`).

### דוגמה בסיסית - HTML/CSS
```python
def create_timeline(images_data):
    dated_images = [img for img in images_data if img["datetime"]]
    dated_images.sort(key=lambda x: x["datetime"])
    
    html = '<div style="position:relative; padding:20px;">'
    html += '<div style="position:absolute; left:50%; width:2px; height:100%; background:#333;"></div>'
    
    for i, img in enumerate(dated_images):
        side = "left" if i % 2 == 0 else "right"
        html += f'''
        <div style="margin:20px 0; text-align:{side};">
            <strong>{img["datetime"]}</strong><br>
            {img["filename"]}<br>
            <small>{img.get("camera_model", "Unknown")}</small>
        </div>'''
    
    html += '</div>'
    return html
```

### שיפורים אפשריים
- צבע שונה לכל יום
- אייקון שונה לכל סוג מכשיר
- hover עם פרטים נוספים
- הדגשת פערי זמן גדולים ("12 שעות הפרש!")

### סדר עבודה מומלץ
1. צרו ציר זמן בסיסי עם HTML
2. סננו תמונות בלי תאריך
3. מיינו לפי תאריך
4. הוסיפו עיצוב ומידע
5. טפלו ב-edge cases: תמונה אחת, אין תמונות עם תאריך

---

## זוג B - analyzer.py

### המטרה
לנתח את הנתונים ולמצוא דפוסים מעניינים. אתם ה"מוח" של המערכת.

### הפלט שלכם (הפורמט המדויק!)
```python
{
    "total_images": 12,
    "images_with_gps": 10,
    "images_with_datetime": 11,
    "unique_cameras": ["Samsung Galaxy S23", "Apple iPhone 15 Pro", "Canon EOS R5"],
    "date_range": {"start": "2025-01-12", "end": "2025-01-16"},
    "insights": [
        "נמצאו 3 מכשירים שונים - ייתכן שהסוכן החליף מכשירים",
        "ב-13/01 הסוכן עבר ממכשיר Samsung ל-iPhone",
        "ריכוז של 3 תמונות באזור תל אביב",
        "המצלמה המקצועית (Canon) הופיעה רק פעם אחת - בנמל חיפה"
    ]
}
```

### אילו דפוסים לחפש?

**1. החלפת מכשירים:**
```python
def detect_camera_switches(images_data):
    sorted_images = sorted(
        [img for img in images_data if img["datetime"]],
        key=lambda x: x["datetime"]
    )
    switches = []
    for i in range(1, len(sorted_images)):
        prev_cam = sorted_images[i-1].get("camera_model")
        curr_cam = sorted_images[i].get("camera_model")
        if prev_cam and curr_cam and prev_cam != curr_cam:
            switches.append({
                "date": sorted_images[i]["datetime"],
                "from": prev_cam,
                "to": curr_cam
            })
    return switches
```

**2. ריכוז גיאוגרפי:** תמונות קרובות אחת לשנייה (מרחק < 1 ק"מ?)

**3. פערי זמן:** פער גדול בין תמונות רצופות (למשל 12 שעות+)

**4. חזרה למיקום:** הסוכן חזר למקום שכבר היה בו

### סדר עבודה מומלץ
1. חשבו סטטיסטיקות בסיסיות (כמה תמונות, כמה עם GPS, כמה מכשירים)
2. מצאו החלפות מכשירים
3. מצאו ריכוזים גיאוגרפיים
4. צרו רשימת insights כ-strings
5. טפלו ב-edge cases: אין תמונות, תמונה אחת, אין GPS בכלל

---

## עבודה עם Git

**זוג A:**
```bash
git checkout -b feature/timeline
```

**זוג B:**
```bash
git checkout -b feature/analyzer
```

**Code Review:** זוג A עושה Review לזוג B, ולהפך.

## צ'קליסט סיום

### זוג A:
- [ ] ציר זמן מציג תמונות לפי סדר כרונולוגי
- [ ] מציג שם קובץ, תאריך, מכשיר
- [ ] מטפל בתמונות בלי תאריך (מתעלם/מסמן)
- [ ] `create_timeline` מחזיר HTML string
- [ ] PR נפתח ונבדק

### זוג B:
- [ ] `analyze` מחזיר מילון בפורמט הנכון
- [ ] מזהה לפחות 2 סוגי דפוסים
- [ ] insights כתובים בעברית ברורה
- [ ] לא קורס על נתונים חסרים
- [ ] PR נפתח ונבדק
