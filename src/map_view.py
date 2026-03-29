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
7. הוספת לוגואים דינמיים של יצרניות (כמו בציר הזמן) לתוך ה-Popup
"""
from extractor import *
import folium
from folium.plugins import MarkerCluster
import base64
from pathlib import Path

# === מנוע שליפת הלוגואים (יובא מציר הזמן) ===
BASE_DIR = Path(__file__).resolve().parent
ICONS_DIR = BASE_DIR / "icons"

LOGO_FILES = {
    "Apple": "Apple-Logo.png",
    "Samsung": "Samsung-Logo-2.png",
    "Canon": "Canon-Logo.png",
    "LG Electronics": "LG-Logo.png",
    "Xiaomi": "Xiaomi-logo.png",
    "Unknown": "purepng.com-camera-iconsymbolsiconsapple-iosiosios-8-iconsios-8-72152259602494tzv.png"
}
LOGO_FILES_LOWER = {key.lower(): value for key, value in LOGO_FILES.items()}


def get_device_logo_b64(make):
    """מקבל יצרן (Make) ומחזיר את הלוגו בפורמט Base64 להטמעה ישירה במפה"""
    make_lower = str(make).lower()
    logo_key = make_lower if make_lower in LOGO_FILES_LOWER else "unknown"
    full_path = ICONS_DIR / LOGO_FILES_LOWER[logo_key]

    if full_path.exists():
        try:
            with open(full_path, "rb") as img_file:
                return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')
        except Exception:
            return None
    return None


# ============================================

def sort_by_time(arr):
    """
    פונקציית עזר למיונים:
    המטרה כאן היא לסדר את התמונות על ציר הזמן (מהישנה לחדשה).
    השתמשנו בפונקציית 'sorted' המובנית של פייתון.
    ה-'key' אומר לפייתון לפי איזה שדה למיין - במקרה שלנו "datetime".
    השתמשנו ב-.get("datetime", "") כדי שאם חסר תאריך לתמונה מסוימת,
    הקוד לא יקרוס אלא פשוט יתייחס אליה כמחרוזת ריקה.
    """
    return sorted(arr, key=lambda x: x.get("datetime") or "")


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
        if img.get("latitude") and img.get("longitude")
    ]

    # הגנה מפני קריסה (Edge Case):
    # אם אחרי הסינון מסתבר שאין אף תמונה עם מיקום במערכת,
    # אי אפשר לחשב מרכז מפה (זה יגרום לשגיאת חלוקה באפס).
    # לכן אנחנו עוצרים כאן ומחזירים הודעת שגיאה נקייה ומעוצבת.
    if not gps_images:
        return False, ""

    # 2. סידור כרונולוגי:
    # קוראים לפונקציית העזר שלנו כדי שהתמונות יופיעו בצורה מסודרת.
    gps_images = sort_by_time(gps_images)

    # 3. מציאת מרכז המפה (Centering):
    # כדי שהמפה תיפתח בדיוק מעל אזור הצילום, מחשבים ממוצע של כל המיקומים.
    # סוכמים את כל קווי הרוחב ומחלקים במספר התמונות (len). אותו כנ"ל לקווי האורך.
    avg_lat = sum(img["latitude"] for img in gps_images) / len(gps_images)
    avg_lon = sum(img["longitude"] for img in gps_images) / len(gps_images)

    # מאתחלים את אובייקט המפה של Folium עם מרכז המפה שחישבנו וזום התחלתי נוח.
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=9)

    # *** התוספת שלנו: יוצרים אובייקט "אשכולות" ומוסיפים למפה ***
    marker_cluster = MarkerCluster().add_to(m)

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

    # הכנת מערך הנתונים שישמש אותנו במנגנון המיקוד מהדשבורד
    js_map_data = "<script>\nwindow.cyberMapData = [\n"

    # 5. הצבת סמנים (Markers) לכל תמונה:
    for img in gps_images:
        # מנסים למשוך את יצרן ודגם המצלמה.
        # שימוש ב-get עם ערך ברירת מחדל ("Unknown") מבטיח שלא נקרוס אם המידע חסר.
        make = img.get("camera_make", "Unknown")
        model = img.get("camera_model", "Device")
        # מחברים את השם והדגם למחרוזת אחת נקייה.
        device_name = f"{make} {model}".strip()
        city_name = img.get("city", "Unknown")

        # בדיקה: האם זה מכשיר חדש שטרם נתקלנו בו בלולאה?
        if device_name not in device_colors:
            # אם כן, נותנים לו צבע חדש מהרשימה.
            # השימוש במודולו (%) מבטיח שגם אם יגמרו הצבעים ברשימה, נתחיל למחזר אותם מההתחלה ולא נקרוס.
            device_colors[device_name] = available_colors[color_index % len(available_colors)]
            # מקדמים את המונה *רק* כשמצאנו מכשיר חדש. כך כל תמונות האייפון, למשל, יקבלו אותו צבע.
            color_index += 1

        # שולפים מתוך המילון את הצבע שנשמר למכשיר הספציפי הזה.
        color = device_colors[device_name]

        # === שליפת תמונת הלוגו ===
        logo_b64 = get_device_logo_b64(make)
        if logo_b64:
            logo_img_html = f"<div style='background-color:#ffffff; padding:3px; border-radius:4px; margin-left:10px; display:flex; align-items:center;'><img src='{logo_b64}' style='height:25px; width:auto; display:block;' /></div>"
        else:
            logo_img_html = ""

        # 6. בניית חלונית מידע קופצת (Popup):
        # הוספנו את הלוגו לצד הטקסט של המכשיר והזמן
        popup_content = f"""
        <div style='direction:ltr; font-family:sans-serif; text-align:center; min-width: 180px;'>
            <b style='color:#0078A8;'>{img.get("filename", "Unknown")}</b><br>

            <div class="cyber-map-popup-img" data-filename="{img.get("filename", "")}" style="margin: 8px 0; min-height: 100px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #e9ecef; border-radius: 5px;">
                 <i class="fas fa-cloud-download-alt fa-fade" style="color: #888; font-size: 24px;"></i>
                 <span style="font-size: 11px; color: #888; margin-top: 5px;">ממתין לסנכרון...</span>
            </div>

            <div style="display:flex; justify-content:center; align-items:center; margin-bottom: 5px;">
                {logo_img_html}
                <div style="text-align: left;">
                    <b>Device:</b> {device_name}<br>
                    <b>Time:</b> {img.get("datetime", "N/A")}
                </div>
            </div>
        </div>
        """

        tooltip_content = f"""
        <div class="cyber-map-tooltip-img" data-filename="{img.get("filename", "")}" style="text-align:center; min-width: 120px;">
            <b>{img.get("filename", "")}</b><br>
            <div style="margin-top: 5px;"><i class="fas fa-image fa-fade" style="color: #888;"></i></div>
        </div>
        """

        # מייצרים את הסמן הסטנדרטי של Folium ומוסיפים אותו למפה (add_to).
        # משתמשים באייקון מצלמה של font-awesome (prefix="fa").
        folium.Marker(
            location=[img["latitude"], img["longitude"]],
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=folium.Tooltip(tooltip_content),
            icon=folium.Icon(color=color, icon="camera", prefix="fa")
        ).add_to(marker_cluster)

        # עדכון המערך ל-JS
        search_text = f"{device_name} {city_name}".replace("'", "").lower()
        city_safe = city_name.replace("'", "\\'")
        dev_safe = device_name.replace("'", "\\'")
        js_map_data += f"  {{ lat: {img['latitude']}, lon: {img['longitude']}, text: '{search_text}', city: '{city_safe}', device: '{dev_safe}' }},\n"

    # סגירת המערך ופריצת מסגרת ה-iframe כדי לאפשר לדשבורד לשלוט במפה
    js_map_data += "];\n"
    js_map_data += """
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() {
            for (var key in window) {
                if (key.startsWith("map_") && window[key] instanceof L.Map) {
                    if (window.parent) {
                        window.parent.myCyberMap = window[key];
                        window.parent.cyberMapData = window.cyberMapData;
                    }
                    window.myCyberMap = window[key];
                    break;
                }
            }
        }, 500);
    });
    </script>
    """
    m.get_root().html.add_child(folium.Element(js_map_data))

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
    return True, m.get_root()._repr_html_()


if __name__ == "__main__":
    # ייבוא זמני רק בשביל הבדיקה המקומית
    from extractor import extract_all

    MY_PHOTOS_PATH = r"C:/Intel/pycharm/pythonProject12/images"
    print("מתחיל שאיבת נתונים לבדיקת מפה...")

    test_data = extract_all(MY_PHOTOS_PATH)

    # תופסים את ה-Tuple
    success, map_html = create_map(test_data)

    if success:
        print("✅ המפה נוצרה בהצלחה!")
        # שומרים קובץ רק לבדיקה מקומית
        with open("test_map.html", "w", encoding="utf-8") as f:
            f.write(map_html)
    else:
        print("🛑 אין תמונות עם GPS בתיקייה (חזר False).")