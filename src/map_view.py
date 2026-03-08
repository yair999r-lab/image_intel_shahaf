"""
map_view.py - יצירת מפה אינטראקטיבית
צוות 1, זוג B

ראו docs/api_contract.md לפורמט הקלט והפלט.

=== תיקונים ===
1. חישוב מרכז המפה - היה עובר על images_data (כולל תמונות בלי GPS) במקום gps_image, נופל עם None
2. הסרת CustomIcon שלא עובד (filename זה לא נתיב שהדפדפן מכיר)
3. הסרת m.save() - לפי API contract צריך להחזיר HTML string, לא לשמור קובץ
4. הסרת fake_data מגוף הקובץ - הועבר ל-if __name__
5. תיקון color_index - היה מתקדם על כל תמונה במקום רק על מכשיר חדש
6. הוספת מקרא מכשירים
"""

import folium

def sort_by_time(arr):
    """
    פונקציית עזר למיונים:
    המטרה כאן היא לסדר את התמונות על ציר הזמן (מהישנה לחדשה).
    השתמשנו בפונקציית 'sorted' המובנית של פייתון.
    ה-'key' אומר לפייתון לפי איזה שדה למיין - במקרה שלנו "datetime".
    השתמשנו ב-.get("datetime", "") כדי שאם חסר תאריך לתמונה מסוימת,
    הקוד לא יקרוס אלא פשוט יתייחס אליה כמחרוזת ריקה.
    """
    return sorted(arr, key=lambda x: x.get("datetime", ""))


def create_map(images_data):
    """
    הפונקציה המרכזית של המודול - לוקחת את המידע הגולמי מהתמונות
    ומייצרת מפה אינטראקטיבית עם סמנים מקודדי-צבע ומקרא.

    Args:
        images_data: רשימת מילונים מ-extract_all

    Returns:
        string של HTML (המפה)
    """
    # 1. סינון נתונים קריטי (מניעת קריסות):
    # אנחנו עוברים על כל רשימת התמונות שקיבלנו.
    # שומרים אך ורק תמונות שיש להן 'has_gps' וגם ערכים תקינים של קווי רוחב ואורך.
    gps_images = [
        img for img in images_data
        if img.get("has_gps") and img.get("latitude") and img.get("longitude")
    ]

    # הגנה מפני קריסה (Edge Case):
    # אם אחרי הסינון מסתבר שאין אף תמונה עם מיקום במערכת,
    # אי אפשר לחשב מרכז מפה (זה יגרום לשגיאת חלוקה באפס).
    # לכן אנחנו עוצרים כאן ומחזירים הודעת שגיאה נקייה ומעוצבת.
    if not gps_images:
        return "<h3 style='text-align: center; color: red;'>No valid GPS data found</h3>"

    # 2. סידור כרונולוגי:
    # קוראים לפונקציית העזר שלנו כדי שהתמונות יופיעו בצורה מסודרת.
    gps_images = sort_by_time(gps_images)

    # 3. מציאת מרכז המפה (Centering):
    # כדי שהמפה תיפתח בדיוק מעל אזור הצילום, מחשבים ממוצע של כל המיקומים.
    # סוכמים את כל קווי הרוחב ומחלקים במספר התמונות (len). אותו כנ"ל לקווי האורך.
    avg_lat = sum(img["latitude"] for img in gps_images) / len(gps_images)
    avg_lon = sum(img["longitude"] for img in gps_images) / len(gps_images)

    # מאתחלים את אובייקט המפה של Folium עם מרכז המפה שחישבנו וזום התחלתי נוח.
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

    # 4. מנגנון חלוקת צבעים חכמה למכשירים:
    # הכנו מראש רשימה של צבעים ש-Folium תומכת בהם.
    available_colors = [
        "red", "blue", "green", "purple", "orange", "darkred",
        "lightred", "beige", "darkblue", "darkgreen", "cadetblue"
    ]
    # מילון ריק שישמור בזיכרון איזה מכשיר (Key) קיבל איזה צבע (Value).
    device_colors = {}
    # אינדקס שיעזור לנו לרוץ על רשימת הצבעים בצורה עוקבת.
    color_index = 0

    # 5. הצבת סמנים (Markers) לכל תמונה:
    for img in gps_images:
        # מנסים למשוך את יצרן ודגם המצלמה.
        # שימוש ב-get עם ערך ברירת מחדל ("Unknown") מבטיח שלא נקרוס אם המידע חסר.
        make = img.get("camera_make", "Unknown")
        model = img.get("camera_model", "Device")
        # מחברים את השם והדגם למחרוזת אחת נקייה.
        device_name = f"{make} {model}".strip()

        # בדיקה: האם זה מכשיר חדש שטרם נתקלנו בו בלולאה?
        if device_name not in device_colors:
            # אם כן, נותנים לו צבע חדש מהרשימה.
            # השימוש במודולו (%) מבטיח שגם אם יגמרו הצבעים ברשימה, נתחיל למחזר אותם מההתחלה ולא נקרוס.
            device_colors[device_name] = available_colors[color_index % len(available_colors)]
            # מקדמים את המונה *רק* כשמצאנו מכשיר חדש. כך כל תמונות האייפון, למשל, יקבלו אותו צבע.
            color_index += 1

            # שולפים מתוך המילון את הצבע שנשמר למכשיר הספציפי הזה.
        color = device_colors[device_name]

        # 6. בניית חלונית מידע קופצת (Popup):
        # בונים חלונית HTML מעוצבת שתוצג כשילחצו על הסמן במפה.
        # שימוש ב-direction:ltr מבטיח שהטקסט באנגלית ייושר נכון לשמאל.
        popup_content = f"""
        <div style='direction:ltr; font-family:sans-serif;'>
            <b>File:</b> {img.get("filename", "Unknown")}<br>
            <b>Device:</b> {device_name}<br>
            <b>Time:</b> {img.get("datetime", "N/A")}
        </div>
        """

        # מייצרים את הסמן הסטנדרטי של Folium ומוסיפים אותו למפה (add_to).
        # משתמשים באייקון מצלמה של font-awesome (prefix="fa").
        folium.Marker(
            location=[img["latitude"], img["longitude"]],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=img.get("filename", "View"),
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(m)

    # 7. יצירת מקרא מכשירים צף (Legend):
    # זו תיבת HTML שתמוקם באופן קבוע בפינה השמאלית התחתונה ותסביר את חלוקת הצבעים.
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; width: max-content; height: auto; 
                border:2px solid grey; z-index:9999; font-size:14px; background-color:white; 
                opacity: 0.9; padding: 10px; border-radius: 5px; direction: ltr;">
        <h4 style="margin-top: 0; margin-bottom: 5px; text-align: center;">Devices</h4>
    """

    # רצים על המילון שלנו ומוסיפים שורה חדשה למקרא עבור כל מכשיר והצבע שלו.
    for dev, col in device_colors.items():
        legend_html += f'<div style="margin-bottom: 3px;"><i class="fa fa-map-marker fa-1x" style="color:{col}"></i> {dev}</div>'
    legend_html += '</div>'

    # "מזריקים" את המקרא שבנינו ישירות לתוך עץ ה-HTML הראשי של המפה.
    m.get_root().html.add_child(folium.Element(legend_html))

    # 8. החזרת התוצאה:
    # חוזה הממשקים (API Contract) מחייב להחזיר מחרוזת HTML טהורה ולא לשמור קובץ,
    # כדי שהאפליקציה של הצוות המקביל תוכל להציג את זה ברשת בצורה חלקה.
    return m.get_root().render()


if __name__ == "__main__":
    # אזור בדיקות (Testing):
    # הנתונים כאן משמשים אותנו רק לבדיקה מקומית של הקובץ בזמן הפיתוח.
    # בלוק זה לא ירוץ כאשר צוות אחר יעשה import לקובץ שלנו.
    fake_data = [
        {"filename": "test1.jpg", "latitude": 32.0853, "longitude": 34.7818,
         "has_gps": True, "camera_make": "Samsung", "camera_model": "Galaxy S23",
         "datetime": "2025-01-12 08:30:00"},
        {"filename": "test2.jpg", "latitude": 31.7683, "longitude": 35.2137,
         "has_gps": True, "camera_make": "Apple", "camera_model": "iPhone 15 Pro",
         "datetime": "2025-01-13 09:00:00"},
    ]
    html = create_map(fake_data)
    with open("test_map.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Map saved to test_map.html")